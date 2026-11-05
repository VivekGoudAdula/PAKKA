"""
FastAPI WebSocket endpoint for Exotel Voicebot Stream.

Endpoint: /ws/exotel
Protocol: Exotel AgentStream bidirectional WebSocket protocol.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.voice.audio import base64_to_pcm
from app.voice.dispatch_registry import dispatch_registry
from app.voice.session import CallSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telephony"])

# Active sessions registry: stream_sid -> CallSession
active_sessions: dict[str, CallSession] = {}


@router.websocket("/ws/exotel")
async def exotel_ws_endpoint(ws: WebSocket) -> None:
    """
    WebSocket endpoint that Exotel AgentStream / Voicebot connects to.
    Handles full-duplex bidirectional audio streaming.
    """
    await ws.accept()
    logger.info("Exotel WebSocket connected from %s", ws.client)

    session: CallSession | None = None
    stream_sid: str | None = None
    first_media_chunk_logged = False
    call_sample_rate = 8000

    async def send_to_exotel(payload: dict[str, Any]) -> None:
        """Helper callback passed to CallSession to send JSON messages to Exotel."""
        try:
            await ws.send_text(json.dumps(payload))
        except Exception as exc:
            logger.warning("Failed to send message to Exotel: %s", exc)

    try:
        while True:
            raw_text = await ws.receive_text()
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning("Non-JSON message received from Exotel: %s", raw_text[:100])
                continue

            event = data.get("event")

            # ── 1. connected event ─────────────────────────
            if event == "connected":
                protocol = data.get("protocol", "Call")
                version = data.get("version", "1.0.0")
                logger.info("Exotel handshake: protocol=%s, version=%s", protocol, version)

            # ── 2. start event ─────────────────────────────
            elif event == "start":
                stream_sid = data.get("stream_sid", "unknown_stream")
                call_sid = data.get("call_sid", f"call_{stream_sid}")
                from_num = data.get("from", "unknown")
                media_format = data.get("media_format", {})
                call_sample_rate = media_format.get("sample_rate", 8000)

                # Check for live Gnani override via custom_parameters or query params
                custom_params = data.get("custom_parameters", {})
                query_live = ws.query_params.get("live_gnani", "").lower() in ("true", "1")
                custom_live = str(custom_params.get("live_gnani", "")).lower() in ("true", "1")
                use_live_gnani = query_live or custom_live

                # Check for dispatch call correlation
                query_dispatch = ws.query_params.get("dispatch", "").lower() in ("true", "1")
                custom_dispatch = str(custom_params.get("dispatch", "")).lower() in ("true", "1")
                job_id_param = ws.query_params.get("job_id") or custom_params.get("job_id")

                pending = dispatch_registry.get_by_call_sid(call_sid)
                if not pending and job_id_param:
                    pending = dispatch_registry.get_latest_by_job(job_id_param)
                    if pending:
                        dispatch_registry.link_call_sid(call_sid, job_id_param)

                is_dispatch = query_dispatch or custom_dispatch or (pending is not None)

                query_collect = ws.query_params.get("collect", "").lower() in ("true", "1")
                custom_collect = str(custom_params.get("collect", "")).lower() in ("true", "1")
                promise_id_param = ws.query_params.get("promise_id") or custom_params.get("promise_id")
                is_collect = query_collect or custom_collect or (promise_id_param is not None)

                collection_fsm = None
                if is_collect:
                    from sqlmodel import Session

                    from app.brain.collection import CollectionFSM
                    from app.db import engine
                    from app.models.domain import Promise
                    cust_name = "Customer"
                    bal = 500
                    tone = 1
                    if promise_id_param:
                        with Session(engine) as s:
                            p = s.get(Promise, promise_id_param)
                            if p:
                                cust_name = p.customer_name
                                bal = p.amount
                                tone = p.tone_level
                    collection_fsm = CollectionFSM(
                        customer_name=cust_name,
                        balance=bal,
                        tone_level=tone,
                    )

                dispatch_fsm = pending.fsm if pending else None
                dispatch_context = pending if pending else None

                logger.info(
                    "[Exotel Call Start] call_sid=%s, stream_sid=%s, from=%s, "
                    "sample_rate=%d, live_gnani=%s, is_dispatch=%s",
                    call_sid,
                    stream_sid,
                    from_num,
                    call_sample_rate,
                    use_live_gnani,
                    is_dispatch,
                )

                stt_client = None
                tts_client = None
                if use_live_gnani:
                    from app.voice.gnani_stt import GnaniSTTClient
                    from app.voice.gnani_tts import GnaniTTSClient

                    stt_client = GnaniSTTClient(sample_rate=call_sample_rate, dry_run=False)
                    tts_client = GnaniTTSClient(sample_rate=call_sample_rate, dry_run=False)
                elif ws.query_params.get("fast_cadence") == "true":
                    from app.voice.gnani_stt import GnaniSTTClient
                    from app.voice.gnani_tts import GnaniTTSClient

                    stt_client = GnaniSTTClient(sample_rate=call_sample_rate, dry_run=True, realtime_cadence=False)
                    tts_client = GnaniTTSClient(sample_rate=call_sample_rate, dry_run=True, realtime_cadence=False)

                session = CallSession(
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                    caller_number=from_num,
                    send_to_exotel=send_to_exotel,
                    stt_client=stt_client,
                    tts_client=tts_client,
                    dispatch_fsm=dispatch_fsm,
                    dispatch_context=dispatch_context,
                    collection_fsm=collection_fsm,
                    promise_id=promise_id_param,
                )
                active_sessions[stream_sid] = session
                await session.start()

            # ── 3. media event ─────────────────────────────
            elif event == "media":
                if not session:
                    continue
                media_obj = data.get("media", {})
                b64_payload = media_obj.get("payload")
                if b64_payload:
                    pcm_chunk = base64_to_pcm(b64_payload)
                    if not first_media_chunk_logged:
                        first_media_chunk_logged = True
                        logger.info(
                            "[Exotel Format Check] call_sid=%s, first media chunk: "
                            "raw_base64_len=%d bytes, decoded_pcm_len=%d bytes, sample_rate=%d Hz",
                            session.call_sid,
                            len(b64_payload),
                            len(pcm_chunk),
                            call_sample_rate,
                        )
                    await session.handle_caller_audio(pcm_chunk)

            # ── 4. mark event ──────────────────────────────
            elif event == "mark":
                if not session:
                    continue
                mark_obj = data.get("mark", {})
                mark_name = mark_obj.get("name", "")
                await session.handle_mark(mark_name)

            # ── 5. dtmf event ──────────────────────────────
            elif event == "dtmf":
                dtmf_obj = data.get("dtmf", {})
                digit = dtmf_obj.get("digit")
                logger.info("DTMF digit received on stream %s: %s", stream_sid, digit)

            # ── 6. stop event ──────────────────────────────
            elif event == "stop":
                reason = data.get("stop", {}).get("reason", "stopped")
                logger.info("Exotel call stop: stream_sid=%s, reason=%s", stream_sid, reason)
                if session:
                    await session.close(reason=reason)
                break

            else:
                logger.debug("Unhandled Exotel event: %s", event)

    except WebSocketDisconnect:
        logger.info("Exotel WebSocket disconnected (stream_sid=%s)", stream_sid)
    except Exception as exc:
        logger.error("Error in Exotel WebSocket loop: %s", exc, exc_info=True)
    finally:
        if stream_sid and stream_sid in active_sessions:
            del active_sessions[stream_sid]
        if session:
            await session.close(reason="ws_closed")
