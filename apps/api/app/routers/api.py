"""
REST API endpoints for Pakka jobs, calls, technicians, and settings.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models.domain import (
    BusinessSettings,
    CallRecord,
    Job,
    PriceItem,
    Technician,
)

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
