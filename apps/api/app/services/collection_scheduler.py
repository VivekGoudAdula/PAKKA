"""
Collection Scheduler Service for Pakka.
Evaluates Promise to Pay deadlines on clock ticks, triggers state transitions
(pending -> due_today -> broken), enforces outbound calling windows,
rate limits (max 3/week, min 24h apart), and respects number suppression.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.events.hub import hub
from app.models.domain import (
    BusinessSettings,
    Promise,
    ReminderEvent,
    SuppressedNumber,
)
from app.services.clock_service import clock

logger = logging.getLogger("pakka.scheduler")


async def evaluate_promises(session: Session) -> dict[str, Any]:
    """
    Evaluate all promises against current simulated clock time.
    Transitions pending -> due_today -> broken, and audits eligible follow-ups.
    """
    current_time = clock.now()

    # Load business settings for calling bounds
    settings = session.exec(select(BusinessSettings)).first()
    outbound_start = settings.outbound_start if settings else "09:00"
    outbound_end = settings.outbound_end if settings else "20:00"

    is_outbound_open = clock.is_within_outbound_hours(outbound_start, outbound_end)

    # Load suppressed numbers
    suppressed_rows = session.exec(select(SuppressedNumber)).all()
    suppressed_phones = {row.phone_raw for row in suppressed_rows}

    promises = session.exec(select(Promise)).all()

    transitions: list[dict[str, Any]] = []
    queued_calls: list[str] = []

    for p in promises:
        if p.status in ("kept", "disputed", "cancelled"):
            continue

        prev_status = p.status
        try:
            due_dt = datetime.strptime(p.due_date, "%Y-%m-%d").date()
            sim_date = current_time.date()
        except Exception:
            continue

        # Status Transitions
        if sim_date < due_dt:
            new_status = "pending"
        elif sim_date == due_dt:
            new_status = "due_today"
        else:  # sim_date > due_dt
            new_status = "broken"

        if new_status != prev_status:
            p.status = new_status
            session.add(p)
            transitions.append(
                {
                    "promise_id": p.id,
                    "customer_name": p.customer_name,
                    "from_status": prev_status,
                    "to_status": new_status,
                }
            )

        # Calling Eligibility Check for due_today or broken
        if p.status in ("due_today", "broken"):
            # Check suppression
            if p.customer_phone_raw and p.customer_phone_raw in suppressed_phones:
                logger.info("Skipping call for suppressed phone %s", p.customer_phone_masked)
                continue

            # Check outbound calling window
            if not is_outbound_open:
                continue

            # Check frequency limits: max 3 attempts / week, min 24h apart
            if p.attempts_count >= 3:
                continue

            if p.last_attempt_at:
                try:
                    last_attempt_dt = datetime.fromisoformat(p.last_attempt_at)
                    if (current_time - last_attempt_dt) < timedelta(hours=24):
                        continue
                except Exception:
                    pass

            queued_calls.append(p.id)

    session.commit()

    # Broadcast event if any transitions occurred
    if transitions:
        await hub.broadcast(
            "promises.evaluated",
            {
                "timestamp": current_time.isoformat(),
                "transitions": transitions,
                "total_transitions": len(transitions),
            },
        )

    return {
        "evaluated_at": current_time.isoformat(),
        "is_outbound_open": is_outbound_open,
        "transitions_count": len(transitions),
        "transitions": transitions,
        "eligible_for_call_count": len(queued_calls),
        "eligible_promise_ids": queued_calls,
    }


def record_reminder_event(
    session: Session,
    promise_id: str,
    customer_id: str,
    disposition: str,
    snippet: str,
    tone_level: int = 1,
    kind: str = "call",
) -> ReminderEvent:
    """Record an audit trail event for payment collections."""
    sim_now = clock.now()
    event_id = f"rem_{int(sim_now.timestamp())}_{promise_id[:6]}"
    event = ReminderEvent(
        id=event_id,
        promise_id=promise_id,
        customer_id=customer_id,
        timestamp=sim_now.strftime("%d %b %Y, %I:%M %p"),
        kind=kind,
        disposition=disposition,
        snippet=snippet,
        tone_level=tone_level,
    )
    session.add(event)

    # Update promise record
    promise = session.get(Promise, promise_id)
    if promise:
        promise.attempts_count += 1
        promise.last_attempt_at = sim_now.isoformat()
        if disposition == "PTP":
            promise.status = "pending"
        elif disposition == "PAID":
            promise.status = "kept"
        elif disposition == "DISPUTE":
            promise.status = "disputed"
        elif disposition in ("REFUSED", "NEEDS_OWNER"):
            promise.tone_level = min(3, promise.tone_level + 1)
        session.add(promise)

    session.commit()
    session.refresh(event)
    return event

