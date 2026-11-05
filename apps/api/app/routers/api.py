"""
REST API endpoints for Pakka jobs, calls, technicians, and settings.
"""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.events.hub import hub
from app.models.domain import (
    BusinessSettings,
    CallRecord,
    Job,
    PriceItem,
    Promise,
    ReminderEvent,
    SuppressedNumber,
    Technician,
)
from app.services.clock_service import clock
from app.services.collection_scheduler import evaluate_promises, record_reminder_event
from app.services.ledger_parser import parse_ledger_entry

router = APIRouter(prefix="/api", tags=["dashboard-api"])


class SettingsUpdateSchema(BaseModel):
    """Schema for updating business settings and calling window."""

    business_name: str | None = None
    handoff_phone: str | None = None
    outbound_start: str | None = None
    outbound_end: str | None = None
    auto_stop_wrong_number: bool | None = None
    never_deny_ai: bool | None = None
    custom_areas: list[str] | None = None
    auto_dispatch: bool | None = None


@router.get("/jobs")
def list_jobs(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """Fetch all recorded jobs ordered by creation date."""
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    return [job.model_dump() for job in jobs]


@router.get("/calls")
def list_calls(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """Fetch all recorded voice calls with parsed transcripts and slots."""
    records = session.exec(select(CallRecord).order_by(CallRecord.created_at.desc())).all()
    result = []
    for rec in records:
        data = rec.model_dump()
        try:
            data["extracted_slots"] = json.loads(rec.extracted_slots_json)
        except Exception:
            data["extracted_slots"] = {}
        try:
            data["transcript"] = json.loads(rec.transcript_json)
        except Exception:
            data["transcript"] = []
        result.append(data)
    return result


@router.get("/technicians")
def list_technicians(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """Fetch registered technicians and dispatch availability."""
    techs = session.exec(select(Technician)).all()
    return [t.model_dump() for t in techs]


@router.get("/settings")
def get_settings(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Fetch current business settings and price list catalog."""
    settings = session.exec(select(BusinessSettings)).first()
    if not settings:
        settings = BusinessSettings()
        session.add(settings)
        session.commit()
        session.refresh(settings)

    price_items = session.exec(select(PriceItem)).all()
    return {
        "settings": settings.model_dump(),
        "price_list": [p.model_dump() for p in price_items],
    }


@router.put("/settings")
def update_settings(
    payload: SettingsUpdateSchema,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Update business settings (hours, handoff phone, policy toggles)."""
    settings = session.exec(select(BusinessSettings)).first()
    if not settings:
        settings = BusinessSettings()
        session.add(settings)

    if payload.business_name is not None:
        settings.business_name = payload.business_name
    if payload.handoff_phone is not None:
        settings.handoff_phone = payload.handoff_phone
    if payload.outbound_start is not None:
        settings.outbound_start = payload.outbound_start
    if payload.outbound_end is not None:
        settings.outbound_end = payload.outbound_end
    if payload.auto_stop_wrong_number is not None:
        settings.auto_stop_wrong_number = payload.auto_stop_wrong_number
    if payload.never_deny_ai is not None:
        settings.never_deny_ai = payload.never_deny_ai
    if payload.custom_areas is not None:
        settings.custom_areas_json = json.dumps(payload.custom_areas)
    if payload.auto_dispatch is not None:
        settings.auto_dispatch = payload.auto_dispatch

    session.commit()
    session.refresh(settings)
    return {"status": "ok", "settings": settings.model_dump()}


class DispatchRequestSchema(BaseModel):
    """Payload for manual or automatic dispatch trigger."""

    technician_id: str | None = None
    simulate: bool = True


@router.post("/jobs/{job_id}/dispatch")
async def trigger_dispatch(
    job_id: str,
    payload: DispatchRequestSchema | None = None,
) -> dict[str, Any]:
    """
    Trigger voice dispatch for a booked job.
    Ranks technicians and initiates outbound phone call to specialist.
    """
    from app.services.dispatch_service import DispatchService

    tech_id = payload.technician_id if payload else None
    simulate = payload.simulate if payload else True

    try:
        return await DispatchService.dispatch_job(
            job_id=job_id,
            preferred_tech_id=tech_id,
            simulate_dialogue=simulate,
        )
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/jobs/{job_id}/dispatch")
def get_dispatch_details(job_id: str) -> dict[str, Any]:
    """
    Fetch the dispatch status, assigned technician, and confirmation history.
    """
    from app.services.dispatch_service import DispatchService

    return DispatchService.get_dispatch_status(job_id)


# ── Clock & Simulated Time Endpoints ──────────────────────────────────────────


class ClockAdvanceSchema(BaseModel):
    """Payload to advance simulated clock."""

    hours: float = 0.0
    days: float = 0.0


@router.get("/clock")
def get_clock_state() -> dict[str, Any]:
    """Get current simulated clock time, offset, and outbound calling status."""
    return clock.to_dict()


@router.post("/clock/advance")
async def advance_clock(
    payload: ClockAdvanceSchema,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Advance simulated clock by hours/days.
    Automatically re-evaluates all promises, transitions statuses,
    and broadcasts clock.tick and promise updates.
    """
    clock.advance(hours=payload.hours, days=payload.days)
    clock_state = clock.to_dict()

    # Broadcast clock.tick
    await hub.broadcast("clock.tick", clock_state)

    # Re-evaluate all promises against new simulated date
    eval_result = await evaluate_promises(session)

    return {
        "status": "ok",
        "clock": clock_state,
        "evaluation": eval_result,
    }


@router.post("/clock/reset")
async def reset_clock(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Reset simulated clock back to initial baseline time."""
    clock.reset()
    clock_state = clock.to_dict()
    await hub.broadcast("clock.tick", clock_state)
    eval_result = await evaluate_promises(session)
    return {
        "status": "ok",
        "clock": clock_state,
        "evaluation": eval_result,
    }


# ── Promises & Collections Endpoints ──────────────────────────────────────────


@router.get("/promises")
def list_promises(
    status: str | None = None,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Fetch collection promises, optionally filtered by status."""
    query = select(Promise)
    if status:
        query = query.where(Promise.status == status)
    promises = session.exec(query).all()
    return [p.model_dump() for p in promises]


@router.get("/customers/{customer_id}/trail")
def get_customer_reminder_trail(
    customer_id: str,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Fetch chronological reminder event audit trail for a customer."""
    events = session.exec(
        select(ReminderEvent)
        .where(ReminderEvent.customer_id == customer_id)
        .order_by(ReminderEvent.created_at.desc())
    ).all()
    return [e.model_dump() for e in events]


@router.get("/suppressed")
def list_suppressed_numbers(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """List numbers excluded from automated voice reminders."""
    records = session.exec(select(SuppressedNumber)).all()
    return [r.model_dump() for r in records]


@router.post("/promises/{promise_id}/call-now")
async def trigger_collection_call(
    promise_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Manually trigger an automated collection call for a promise.
    Enforces calling hours and phone suppression before placing call.
    """
    promise = session.get(Promise, promise_id)
    if not promise:
        return {"status": "error", "message": f"Promise {promise_id} not found"}

    # Check suppression
    if promise.customer_phone_raw:
        suppressed = session.exec(
            select(SuppressedNumber).where(SuppressedNumber.phone_raw == promise.customer_phone_raw)
        ).first()
        if suppressed:
            return {
                "status": "blocked",
                "message": "Number is on the permanent suppression list (Wrong Number/Opt-out). Cannot call.",
            }

    # Check calling hours
    settings = session.exec(select(BusinessSettings)).first()
    start = settings.outbound_start if settings else "09:00"
    end = settings.outbound_end if settings else "20:00"
    if not clock.is_within_outbound_hours(start, end):
        return {
            "status": "outside_hours",
            "message": f"Current simulated time is outside outbound calling hours ({start} - {end} IST). Call not dialed.",
        }

    # Record reminder event
    event = record_reminder_event(
        session=session,
        promise_id=promise_id,
        customer_id=promise.customer_id,
        disposition="PTP",
        snippet="Manual call dialed by owner. Customer agreed to pay.",
        tone_level=promise.tone_level,
    )

    # Broadcast event
    await hub.broadcast(
        "collection.call_initiated",
        {
            "promise_id": promise_id,
            "customer_name": promise.customer_name,
            "amount": promise.amount,
            "tone_level": promise.tone_level,
        },
    )

    return {
        "status": "dialed",
        "promise_id": promise_id,
        "customer_name": promise.customer_name,
        "reminder_event": event.model_dump(),
    }


# ── Owner Quick Entry Ledger Endpoint ─────────────────────────────────────────


class LedgerEntryRequestSchema(BaseModel):
    """Payload for natural Hinglish ledger text entry."""

    text: str


@router.post("/ledger/entry")
async def create_ledger_quick_entry(
    payload: LedgerEntryRequestSchema,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Parse owner quick voice/text note (e.g. 'Ramesh ke kaam ho gaya 800 mile 500 baaki')
    and update customer ledger, jobs, and promises.
    """
    parsed = parse_ledger_entry(payload.text)

    # Create Job record
    import uuid
    job_id = f"job_{uuid.uuid4().hex[:6]}"
    cust_id = f"cust_{uuid.uuid4().hex[:6]}"

    job = Job(
        id=job_id,
        call_id="quick_entry",
        title=parsed.job_summary,
        problem=parsed.raw_text,
        landmark_address="Entered via Ledger Note",
        time_slot="Completed",
        price_estimate=f"₹{parsed.paid_amount + parsed.balance}",
        price_min=parsed.paid_amount + parsed.balance,
        price_max=parsed.paid_amount + parsed.balance,
        status="paid" if parsed.is_fully_paid else "done",
        customer_name=parsed.customer_name,
        customer_phone_masked="+91 98XXXXXX99",
        paid_amount=parsed.paid_amount,
        balance=parsed.balance,
    )
    session.add(job)

    # If remaining balance, create a Promise to Pay
    created_promise = None
    if parsed.balance > 0:
        sim_now = clock.now()
        # Compute due date based on parsed date or default +2 days
        import datetime as dt
        due_date_str = (sim_now + dt.timedelta(days=2)).strftime("%Y-%m-%d")
        if parsed.promise_date == "kal":
            due_date_str = (sim_now + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        elif parsed.promise_date == "parson":
            due_date_str = (sim_now + dt.timedelta(days=2)).strftime("%Y-%m-%d")

        prom_id = f"prom_{uuid.uuid4().hex[:6]}"
        created_promise = Promise(
            id=prom_id,
            customer_id=cust_id,
            customer_name=parsed.customer_name,
            customer_phone_masked="+91 98XXXXXX99",
            customer_phone_raw="+919800000099",
            job_id=job_id,
            amount=parsed.balance,
            due_date=due_date_str,
            status="pending",
            tone_level=1,
        )
        session.add(created_promise)

        # Record initial reminder event
        record_reminder_event(
            session=session,
            promise_id=prom_id,
            customer_id=cust_id,
            disposition="PTP",
            snippet=f"Ledger note recorded: ₹{parsed.paid_amount} received, ₹{parsed.balance} balance promised for {parsed.promise_date or 'soon'}.",
            kind="note",
        )

    session.commit()

    # Broadcast event
    await hub.broadcast(
        "ledger.entry_created",
        {
            "customer_name": parsed.customer_name,
            "paid_amount": parsed.paid_amount,
            "balance": parsed.balance,
            "is_fully_paid": parsed.is_fully_paid,
        },
    )

    return {
        "status": "created",
        "parsed": {
            "customer_name": parsed.customer_name,
            "job_summary": parsed.job_summary,
            "paid_amount": parsed.paid_amount,
            "balance": parsed.balance,
            "is_fully_paid": parsed.is_fully_paid,
            "promise_date": parsed.promise_date,
        },
        "job_id": job_id,
        "promise_id": created_promise.id if created_promise else None,
    }


@router.get("/metrics")
def get_metrics() -> dict[str, Any]:
    """
    Returns consolidated system metrics for dashboard:
    - Booking FSM performance (main + holdout)
    - Technician Dispatch acceptance
    - Collection recovery & PTP tracking
    - Extractor benchmark comparison (Rules vs Evon vs Hybrid)
    - Audio SNR pipeline evaluation
    """
    from pathlib import Path

    reports_dir = Path(__file__).resolve().parent.parent.parent / "reports"

    def read_report(name: str) -> dict[str, Any]:
        p = reports_dir / name
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    booking_data = read_report("booking_results.json")
    dispatch_data = read_report("dispatch_results.json")
    collection_data = read_report("collection_results.json")
    extractor_data = read_report("extractor_comparison.json")
    audio_data = read_report("audio_eval.json")
    holdout_v2_data = read_report("holdout_v2_results.json")

    return {
        "status": "ok",
        "generated_at": datetime.now(UTC).isoformat(),
        "booking": booking_data,
        "dispatch": dispatch_data,
        "collection": collection_data,
        "extractor_comparison": extractor_data,
        "audio_eval": audio_data,
        "holdout_v2": holdout_v2_data,
    }



