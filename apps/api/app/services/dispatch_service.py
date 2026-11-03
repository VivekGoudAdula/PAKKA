"""
apps/api/app/services/dispatch_service.py
Technician Cascading Dispatch Service.
Coordinates ranking, outbound dialing, cascading fallback across specialists (max 3 attempts),
and synchronization with the database and live dashboard WebSocket hub.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlmodel import Session, select

from app.brain.dispatch import (
    DISPATCH_ACCEPT_REPLY,
    DISPATCH_DISCLOSURE_GREETING,
    rank_technicians_for_job,
)
from app.db import engine
from app.models.domain import Job, Technician
from app.voice.dispatch_registry import dispatch_registry
from app.voice.outbound import exotel_connect_outbound
from app.voice.session import hub

logger = logging.getLogger(__name__)


class DispatchService:
    """Service managing technician voice dispatch cascades."""

    @staticmethod
    def get_dispatch_status(job_id: str) -> dict[str, Any]:
        """Return the current dispatch status and attempt trail for a job."""
        attempts = dispatch_registry.get_all_by_job(job_id)
        latest = dispatch_registry.get_latest_by_job(job_id)

        attempts_data = [
            {
                "technician_id": a.technician_id,
                "technician_name": a.technician_name,
                "technician_phone": a.technician_phone,
                "attempt_number": a.attempt_number,
                "status": a.status,
                "confirmation_phrase": a.confirmation_phrase,
                "confirmed_at": a.confirmed_at,
            }
            for a in attempts
        ]

        return {
            "job_id": job_id,
            "status": latest.status if latest else "unassigned",
            "technician_id": latest.technician_id if latest else None,
            "technician_name": latest.technician_name if latest else None,
            "attempts": attempts_data,
            "confirmed_phrase": latest.confirmation_phrase if latest else None,
            "confirmed_at": latest.confirmed_at if latest else None,
        }

    @staticmethod
    async def dispatch_job(
        job_id: str,
        preferred_tech_id: str | None = None,
        simulate_dialogue: bool = True,
    ) -> dict[str, Any]:
        """
        Initiates voice dispatch for a booked job.
        Ranks technicians, dials the top specialist, and cascades if declined.
        """
        with Session(engine) as db:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            all_technicians = db.exec(select(Technician)).all()

        # Find existing declined technicians for this job
        prior_attempts = dispatch_registry.get_all_by_job(job_id)
        declined_ids = {a.technician_id for a in prior_attempts if a.status in ("declined", "unreachable")}
        attempt_number = len(prior_attempts) + 1

        if attempt_number > 3:
            logger.warning("Job %s reached maximum dispatch attempts (3). Halting cascade.", job_id)
            with Session(engine) as db:
                job = db.get(Job, job_id)
                if job:
                    job.status = "needs_owner"
                    db.add(job)
                    db.commit()

            await hub.broadcast(
                "dispatch.failed",
                {
                    "job_id": job_id,
                    "reason": "Sabhi 3 technician ne mana kar diya. Owner manual intervention required.",
                    "timestamp": time.time(),
                },
            )
            return {
                "status": "failed",
                "job_id": job_id,
                "reason": "Max attempts reached (3/3 declined)",
            }

        # Select target technician
        target_technician: Technician | None = None
        if preferred_tech_id:
            target_technician = next((t for t in all_technicians if t.id == preferred_tech_id), None)

        if not target_technician:
            ranked = rank_technicians_for_job(all_technicians, job, declined_technician_ids=declined_ids)
            if not ranked:
                logger.warning("No available technicians found for job %s", job_id)
                with Session(engine) as db:
                    job = db.get(Job, job_id)
                    if job:
                        job.status = "needs_owner"
                        db.add(job)
                        db.commit()

                await hub.broadcast(
                    "dispatch.failed",
                    {
                        "job_id": job_id,
                        "reason": "Koi technician uplabdh nahi hai.",
                        "timestamp": time.time(),
                    },
                )
                return {
                    "status": "failed",
                    "job_id": job_id,
                    "reason": "No available technicians",
                }
            target_technician = ranked[0]

        logger.info(
            "Selected technician %s (%s) for job %s (attempt %d/3)",
            target_technician.name,
            target_technician.specialty,
            job_id,
            attempt_number,
        )

        # Call outbound Exotel
        call_res = await exotel_connect_outbound(
            to_phone=target_technician.phone,
            job_id=job_id,
            technician_id=target_technician.id,
            technician_name=target_technician.name,
            problem=job.problem,
            address=job.landmark_address,
            slot=job.time_slot,
            attempt_number=attempt_number,
        )

        call_sid = call_res.get("call_sid", f"dispatch_{int(time.time())}")

        # Broadcast dispatch.started
        await hub.broadcast(
            "dispatch.started",
            {
                "job_id": job_id,
                "call_id": call_sid,
                "technician": {
                    "id": target_technician.id,
                    "name": target_technician.name,
                    "phone": target_technician.phone,
                    "specialty": target_technician.specialty,
                },
                "attempt_number": attempt_number,
                "timestamp": time.time(),
            },
        )

        # If in dry-run/simulation mode, spawn background task to simulate call
        if simulate_dialogue and call_res.get("mode") == "dry_run":
            asyncio.create_task(
                DispatchService._run_simulated_dispatch(
                    job_id=job_id,
                    technician=target_technician,
                    problem=job.problem,
                    address=job.landmark_address,
                    slot=job.time_slot,
                    attempt_number=attempt_number,
                )
            )

        return {
            "status": "initiated",
            "job_id": job_id,
            "call_sid": call_sid,
            "technician": {
                "id": target_technician.id,
                "name": target_technician.name,
                "phone": target_technician.phone,
                "specialty": target_technician.specialty,
            },
            "attempt_number": attempt_number,
        }

    @staticmethod
    async def _run_simulated_dispatch(
        job_id: str,
        technician: Technician,
        problem: str,
        address: str,
        slot: str,
        attempt_number: int,
    ) -> None:
        """Simulate realistic technician voice dialogue for demo/dry-run."""
        pending = dispatch_registry.get_latest_by_job(job_id)

        # 1. Ringing
        await asyncio.sleep(1.0)
        if pending:
            pending.status = "ringing"
        await hub.broadcast(
            "dispatch.ringing",
            {
                "job_id": job_id,
                "technician": technician.name,
                "timestamp": time.time(),
            },
        )

        # 2. Call Answered & Bot Greeting Readout
        await asyncio.sleep(1.2)
        if pending:
            pending.status = "in_progress"
        greeting = DISPATCH_DISCLOSURE_GREETING.format(
            name=technician.name,
            problem=problem,
            address=address,
            slot=slot,
        )
        await hub.broadcast(
            "dispatch.transcript",
            {
                "job_id": job_id,
                "role": "bot",
                "text": greeting,
                "is_disclosure": True,
                "timestamp": time.time(),
            },
        )

        # 3. Technician Speaks Acceptance
        await asyncio.sleep(1.8)
        technician_reply = "Haan ji, pakka. Main time par pahunch jaunga."
        await hub.broadcast(
            "dispatch.transcript",
            {
                "job_id": job_id,
                "role": "technician",
                "text": technician_reply,
                "timestamp": time.time(),
            },
        )

        # 4. Bot Acknowledges & Terminates
        await asyncio.sleep(0.8)
        await hub.broadcast(
            "dispatch.transcript",
            {
                "job_id": job_id,
                "role": "bot",
                "text": DISPATCH_ACCEPT_REPLY,
                "timestamp": time.time(),
            },
        )

        # 5. Mark Accepted in DB and Hub
        confirmed_time = time.strftime("%I:%M %p")
        if pending:
            pending.status = "accepted"
            pending.confirmation_phrase = technician_reply
            pending.confirmed_at = confirmed_time

        with Session(engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = "dispatched"
                job.technician_id = technician.id
                db.add(job)

            db_tech = db.get(Technician, technician.id)
            if db_tech:
                db_tech.status = "on_job"
                db_tech.active_jobs_count += 1
                db.add(db_tech)

            db.commit()

        await hub.broadcast(
            "dispatch.accepted",
            {
                "job_id": job_id,
                "technician_id": technician.id,
                "technician_name": technician.name,
                "confirmation_phrase": technician_reply,
                "confirmed_at": confirmed_time,
                "timestamp": time.time(),
            },
        )
        logger.info(
            "Simulated dispatch completed: job %s assigned to %s",
            job_id,
            technician.name,
        )
