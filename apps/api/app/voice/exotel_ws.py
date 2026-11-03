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
                sample_rate = media_format.get("sample_rate", 8000)

                logger.info(
                    "Exotel call start: call_sid=%s, stream_sid=%s, from=%s, sample_rate=%d",
                    call_sid,
                    stream_sid,
                    from_num,
                    sample_rate,
                )

                session = CallSession(
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                    caller_number=from_num,
                    send_to_exotel=send_to_exotel,
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
