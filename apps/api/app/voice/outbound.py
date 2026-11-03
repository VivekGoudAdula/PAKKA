"""
apps/api/app/voice/outbound.py
Exotel Outbound Calling Client for Technician Voice Dispatch.
Initiates outbound telephony calls to technicians using Exotel REST API.
Exempt from customer outbound calling hours restrictions (night emergency dispatch).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import settings
from app.voice.dispatch_registry import PendingDispatch, dispatch_registry

logger = logging.getLogger(__name__)


async def exotel_connect_outbound(
    to_phone: str,
    job_id: str,
    technician_id: str,
    technician_name: str,
    problem: str,
    address: str,
    slot: str,
    attempt_number: int = 1,
) -> dict[str, Any]:
    """
    Initiate an outbound call to a technician via Exotel AgentStream.
    In DEMO / DRY-RUN mode or when credentials are not configured,
    returns a simulated call_sid and registers the session.
    """
    has_exotel_auth = bool(
        getattr(settings, "exotel_api_key", None)
        and getattr(settings, "exotel_api_token", None)
        and getattr(settings, "exotel_account_sid", None)
    )

    # 1. DRY-RUN or Credentials Missing Mode
    if getattr(settings, "gnani_dry_run", True) or not has_exotel_auth:
        synthetic_call_sid = f"dry_dispatch_{job_id}_{int(time.time())}"
        logger.info(
            "[SYNTHETIC OUTBOUND] Dispatching job %s to %s (%s) with call_sid=%s",
            job_id,
            technician_name,
            to_phone,
            synthetic_call_sid,
        )

        pending = PendingDispatch(
            job_id=job_id,
            technician_id=technician_id,
            technician_name=technician_name,
            technician_phone=to_phone,
            problem=problem,
            address=address,
            slot=slot,
            attempt_number=attempt_number,
            call_sid=synthetic_call_sid,
        )
        dispatch_registry.register(pending)

        return {
            "call_sid": synthetic_call_sid,
            "status": "queued",
            "mode": "dry_run",
            "job_id": job_id,
            "technician": technician_name,
        }

    # 2. LIVE Exotel Outbound API Mode
    account_sid = settings.exotel_account_sid
    api_key = settings.exotel_api_key
    api_token = settings.exotel_api_token
    caller_id = getattr(settings, "exotel_caller_id", "+918045678901")

    # Construct public StreamUrl with dual correlation parameters
    public_wss = getattr(settings, "public_wss_url", "wss://localhost:8000")
    stream_url = (
        f"{public_wss}/ws/exotel?dispatch=true&job_id={job_id}&tech_id={technician_id}"
    )

    url = f"https://api.in.exotel.com/v1/Accounts/{account_sid}/Calls/connect.json"
    data = {
        "From": to_phone,
        "CallerId": caller_id,
        "StreamUrl": stream_url,
        "StreamType": "bidirectional",
        "CustomField": f"job_id={job_id}&dispatch=true",
    }

    logger.info(
        "Initiating live Exotel outbound call to %s (job_id=%s, attempt=%d)",
        to_phone,
        job_id,
        attempt_number,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                data=data,
                auth=(api_key, api_token),
            )
            resp.raise_for_status()
            res_json = resp.json()

            call_sid = res_json.get("Call", {}).get("Sid") or f"exotel_{int(time.time())}"
            logger.info("Exotel outbound call queued successfully: call_sid=%s", call_sid)

            pending = PendingDispatch(
                job_id=job_id,
                technician_id=technician_id,
                technician_name=technician_name,
                technician_phone=to_phone,
                problem=problem,
                address=address,
                slot=slot,
                attempt_number=attempt_number,
                call_sid=call_sid,
            )
            dispatch_registry.register(pending)

            return {
                "call_sid": call_sid,
                "status": "initiated",
                "mode": "live",
                "job_id": job_id,
                "technician": technician_name,
            }
    except Exception as exc:
        logger.error("Failed to connect outbound Exotel call: %s", exc)
        raise RuntimeError(f"Exotel Outbound Call Failed: {exc}") from exc
