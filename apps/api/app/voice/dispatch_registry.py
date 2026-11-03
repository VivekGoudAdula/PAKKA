"""
apps/api/app/voice/dispatch_registry.py
In-memory registry for pending and active technician dispatch calls.
Provides dual correlation between Exotel call_sid, job_id, and DispatchFSM.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.brain.dispatch import DispatchFSM


@dataclass
class PendingDispatch:
    """Record of an outbound dispatch attempt to a technician."""

    job_id: str
    technician_id: str
    technician_name: str
    technician_phone: str
    problem: str
    address: str
    slot: str
    attempt_number: int = 1
    call_sid: str | None = None
    created_at: float = field(default_factory=time.time)
    fsm: DispatchFSM = field(init=False)
    status: str = "pending"  # "pending", "ringing", "in_progress", "accepted", "declined", "failed"
    confirmation_phrase: str | None = None
    confirmed_at: str | None = None

    def __post_init__(self) -> None:
        self.fsm = DispatchFSM(
            technician_name=self.technician_name,
            problem=self.problem,
            address=self.address,
            slot=self.slot,
        )


class DispatchRegistry:
    """Thread-safe in-memory store for pending technician dispatch sessions."""

    def __init__(self) -> None:
        self._by_call_sid: dict[str, PendingDispatch] = {}
        self._by_job_id: dict[str, list[PendingDispatch]] = {}
        self._latest_by_job: dict[str, PendingDispatch] = {}

    def register(self, pending: PendingDispatch) -> None:
        """Register a new pending dispatch."""
        if pending.call_sid:
            self._by_call_sid[pending.call_sid] = pending
        self._by_job_id.setdefault(pending.job_id, []).append(pending)
        self._latest_by_job[pending.job_id] = pending

    def link_call_sid(self, call_sid: str, job_id: str) -> PendingDispatch | None:
        """Link an allocated call_sid to an existing pending dispatch."""
        pending = self._latest_by_job.get(job_id)
        if pending:
            pending.call_sid = call_sid
            self._by_call_sid[call_sid] = pending
        return pending

    def get_by_call_sid(self, call_sid: str) -> PendingDispatch | None:
        """Retrieve pending dispatch by Exotel call_sid."""
        return self._by_call_sid.get(call_sid)

    def get_latest_by_job(self, job_id: str) -> PendingDispatch | None:
        """Retrieve most recent dispatch attempt for a job."""
        return self._latest_by_job.get(job_id)

    def get_all_by_job(self, job_id: str) -> list[PendingDispatch]:
        """Retrieve all dispatch attempts for a job."""
        return self._by_job_id.get(job_id, [])


# Global singleton registry
dispatch_registry = DispatchRegistry()
