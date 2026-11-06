"""
apps/api/app/routers/voice_browser.py
FastAPI router for Phase 8 "Talk to Pakka" Browser Voice Dialog.

Endpoints:
1. POST /api/voice/start: Initialize 15-minute dialogue session (booking / collection)
2. POST /api/voice/turn: Process audio utterance (WAV validation -> STT REST -> FSM -> TTS REST)
3. POST /api/voice/text-turn: Typed fallback route without STT
4. GET /api/voice/usage: Usage tracker statistics and hourly budget guard
"""

from __future__ import annotations

import base64
import json
import logging
import time
import uuid
import wave
from io import BytesIO
from typing import Any, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.brain.collection import CollectionFSM, CollectionState
from app.brain.fsm import BookingFSM, BookingState
from app.brain.replies import MANDATORY_GREETING
from app.config import settings
from app.db import engine
from app.events.hub import hub
from app.models.domain import BusinessSettings, CallRecord, Job
from app.voice.audio import number_to_spoken_words
from app.voice.gnani_rest import (
    GnaniQuotaExceededError,
    GnaniRateLimitError,
    GnaniRestClient,
    GnaniRestError,
    usage_tracker,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["browser_voice"])


# ─── In-Memory Session Store with 15-Minute TTL ────────────────────────────────


class BrowserVoiceSession:
    """Represents an active in-browser dialogue session."""

    def __init__(
        self,
        session_id: str,
        flow: Literal["booking", "collection"],
        fsm: BookingFSM | CollectionFSM,
        business_name: str,
        owner_name: str,
    ) -> None:
        self.session_id = session_id
        self.flow = flow
        self.fsm = fsm
        self.business_name = business_name
        self.owner_name = owner_name
        self.created_at = time.monotonic()
        self.last_active = time.monotonic()
        self.turn_count = 0
        self.history: list[dict[str, Any]] = []

    def is_expired(self, ttl_seconds: float = 900.0) -> bool:
        """Check if 15-minute inactivity window has expired."""
        return (time.monotonic() - self.last_active) > ttl_seconds

    def touch(self) -> None:
        self.last_active = time.monotonic()
        self.turn_count += 1


_SESSIONS: dict[str, BrowserVoiceSession] = {}


def _cleanup_expired_sessions() -> None:
    """Prunes expired sessions."""
    expired = [sid for sid, s in _SESSIONS.items() if s.is_expired()]
    for sid in expired:
        del _SESSIONS[sid]


def _get_business_info() -> tuple[str, str, str]:
    """Retrieve business name, owner name, and handoff phone from DB or defaults."""
    try:
        with Session(engine) as db:
            bs = db.exec(select(BusinessSettings)).first()
            if bs:
                return (
                    bs.business_name or "Sharma Plumbing",
                    bs.owner_name or "Ramesh Sharma",
                    bs.phone or settings.telephony_handoff_number,
                )
    except Exception as exc:
        logger.warning("Failed to fetch business settings: %s", exc)
    return "Sharma Plumbing", "Ramesh Sharma", settings.telephony_handoff_number


def _build_collection_greeting(fsm: CollectionFSM, business_name: str) -> str:
    cust = fsm.customer_name or "Customer"
    bal_words = number_to_spoken_words(fsm.balance)
    if fsm.tone_level == 1:
        return (
            f"Namaste {cust} ji, main {business_name} ki digital sahayak bol rahi hoon. "
            f"Aapka {bal_words} rupaye ka bill baki hai. Kya aap aaj payment kar sakte hain?"
        )
    if fsm.tone_level == 2:
        return (
            f"Namaste {cust} ji, main {business_name} ki digital sahayak bol rahi hoon. "
            f"Pichhli baar baat hui thi, aapka {bal_words} rupaye ka payment pending hai. Kab tak ho payega ji?"
        )
    return (
        f"Namaste {cust} ji, main {business_name} ki digital sahayak bol rahi hoon. "
        f"Aapka {bal_words} rupaye ka hisaab kaafi samay se baki hai. Kya main malik se callback karwaun ya aap aaj clear kar rahe hain?"
    )


# ─── WAV Audio Validation ─────────────────────────────────────────────────────


def validate_wav_audio(audio_bytes: bytes) -> tuple[float, int]:
    """
    Validates audio file constraints:
    - Must be valid WAV container
    - Signed 16-bit PCM (sample_width == 2)
    - Mono (1 channel)
    - Sample rate: 8000 Hz to 48000 Hz
    - Duration: 0.3 s to 30.0 s
    Returns (duration_seconds, sample_rate).
    """
    if len(audio_bytes) < 44:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file too small to be a valid WAV header",
        )

    try:
        with wave.open(BytesIO(audio_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            frames = wf.getnframes()
            duration_s = frames / float(framerate) if framerate > 0 else 0.0
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid WAV audio format: {exc}",
        ) from exc

    if channels != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio must be mono (1 channel), got {channels} channels",
        )

    if sample_width != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio must be 16-bit PCM (2 bytes per sample), got {sample_width} bytes",
        )

    if not (8000 <= framerate <= 48000):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sample rate must be between 8000 Hz and 48000 Hz, got {framerate} Hz",
        )

    if not (0.3 <= duration_s <= 30.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio duration must be between 0.3s and 30.0s, got {duration_s:.2f}s",
        )

    return duration_s, framerate


# ─── Pydantic Request / Response Models ───────────────────────────────────────


class VoiceStartRequest(BaseModel):
    flow: Literal["booking", "collection"] = Field(default="booking")
    customer: str | None = Field(default=None, description="Customer name for collection flow")
    tone_level: int | None = Field(default=1, ge=1, le=3, description="Tone level (1-3) for collection")


class VoiceStartResponse(BaseModel):
    session_id: str
    flow: str
    greeting_text: str
    greeting_audio_b64: str
    state: str
    mode: str


class TextTurnRequest(BaseModel):
    session_id: str
    text: str


class VoiceTurnResponse(BaseModel):
    transcript: str
    detected_language: str
    reply_text: str
    audio_b64: str
    state: str
    slots: dict[str, Any]
    is_terminal: bool
    is_urgent: bool
    needs_human: bool
    latency_ms: dict[str, float]
    cached: bool
    mode: str
    typed: bool = False


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/start", response_model=VoiceStartResponse)
async def start_voice_session(req: VoiceStartRequest) -> VoiceStartResponse:
    """
    Initialize a new 15-minute voice session with mandatory digital sahayak greeting.
    """
    _cleanup_expired_sessions()
    business_name, owner_name, handoff_phone = _get_business_info()
    session_id = f"vses_{uuid.uuid4().hex[:12]}"

    if req.flow == "collection":
        fsm = CollectionFSM(
            customer_name=req.customer or "Customer",
            balance=500,
            tone_level=req.tone_level or 1,
            business_name=business_name,
            owner_name=owner_name,
        )
        greeting_text = _build_collection_greeting(fsm, business_name)
        initial_state = fsm.state.value
    else:
        fsm = BookingFSM(
            business_name=business_name,
            handoff_phone=handoff_phone,
        )
        greeting_text = (
            f"Namaste, {business_name} ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?"
        )
        initial_state = fsm.state.value

    # Synthesize greeting via GnaniRestClient
    client = GnaniRestClient()
    try:
        wav_bytes, was_cached, mode = await client.text_to_speech(
            text=greeting_text,
            voice="Poorvi",
            model="timbre-v2.5",
            language="hi-en",
            speed=1.0,
            sample_rate=16000,
        )
    except GnaniQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GnaniRestError as exc:
        logger.error("TTS greeting failed: %s", exc)
        wav_bytes = b""
        mode = "dry_run" if settings.gnani_dry_run else "error"

    audio_b64 = base64.b64encode(wav_bytes).decode("ascii") if wav_bytes else ""

    session_obj = BrowserVoiceSession(
        session_id=session_id,
        flow=req.flow,
        fsm=fsm,
        business_name=business_name,
        owner_name=owner_name,
    )
    session_obj.history.append({"role": "bot", "text": greeting_text, "timestamp": time.time()})
    _SESSIONS[session_id] = session_obj

    # Broadcast initial session start to hub
    await hub.broadcast(
        "voice.started",
        {
            "session_id": session_id,
            "flow": req.flow,
            "greeting_text": greeting_text,
            "timestamp": time.time(),
        },
    )

    return VoiceStartResponse(
        session_id=session_id,
        flow=req.flow,
        greeting_text=greeting_text,
        greeting_audio_b64=audio_b64,
        state=initial_state,
        mode=mode,
    )


@router.post("/turn", response_model=VoiceTurnResponse)
async def process_voice_turn(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
) -> VoiceTurnResponse:
    """
    Process spoken audio turn:
    1. Validates uploaded WAV file (16-bit mono 8-48kHz 0.3-30s).
    2. Transcribes via Gnani STT REST.
    3. Feeds transcript to active FSM (BookingFSM or CollectionFSM).
    4. Synthesizes reply via Gnani TTS REST (cache-first).
    5. Emits hub events and persists to database if completed.
    """
    _cleanup_expired_sessions()
    session_obj = _SESSIONS.get(session_id)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found or expired. Please start a new session.",
        )
    session_obj.touch()

    # Read and validate audio
    audio_bytes = await audio.read()
    validate_wav_audio(audio_bytes)

    client = GnaniRestClient()
    t_start = time.monotonic()

    # 1. STT REST
    t0_stt = time.monotonic()
    try:
        stt_res = await client.speech_to_text(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.wav",
            content_type=audio.content_type or "audio/wav",
            model="prisma-v3.0",
            language_code="hi-IN",
        )
    except GnaniQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GnaniRestError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    stt_latency_ms = (time.monotonic() - t0_stt) * 1000.0
    transcript_text = stt_res.get("transcript", "")
    detected_lang = stt_res.get("detected_language", "hi-IN")
    stt_mode = stt_res.get("mode", "dry_run")

    session_obj.history.append({"role": "caller", "text": transcript_text, "timestamp": time.time()})

    # Broadcast caller transcript to frontend
    await hub.broadcast(
        "voice.transcript",
        {
            "session_id": session_id,
            "role": "caller",
            "text": transcript_text,
            "timestamp": time.time(),
        },
    )

    # 2. Process Dialogue Turn via FSM
    turn_outcome = await _process_fsm_turn(session_obj, transcript_text)

    # 3. TTS REST (Cache-first)
    t0_tts = time.monotonic()
    try:
        reply_wav_bytes, was_cached, tts_mode = await client.text_to_speech(
            text=turn_outcome["reply_text"],
            voice="Poorvi",
            model="timbre-v2.5",
            language="hi-en",
            speed=1.0,
            sample_rate=16000,
        )
    except GnaniQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GnaniRestError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    tts_latency_ms = (time.monotonic() - t0_tts) * 1000.0
    total_latency_ms = (time.monotonic() - t_start) * 1000.0

    session_obj.history.append({"role": "bot", "text": turn_outcome["reply_text"], "timestamp": time.time()})
    audio_b64 = base64.b64encode(reply_wav_bytes).decode("ascii") if reply_wav_bytes else ""

    # Broadcast bot reply
    await hub.broadcast(
        "voice.transcript",
        {
            "session_id": session_id,
            "role": "bot",
            "text": turn_outcome["reply_text"],
            "timestamp": time.time(),
        },
    )

    effective_mode = "live" if (stt_mode == "live" and tts_mode == "live") else "dry_run"

    return VoiceTurnResponse(
        transcript=transcript_text,
        detected_language=detected_lang,
        reply_text=turn_outcome["reply_text"],
        audio_b64=audio_b64,
        state=turn_outcome["state"],
        slots=turn_outcome["slots"],
        is_terminal=turn_outcome["is_terminal"],
        is_urgent=turn_outcome["is_urgent"],
        needs_human=turn_outcome["needs_human"],
        latency_ms={
            "stt": round(stt_latency_ms, 1),
            "tts": round(tts_latency_ms, 1),
            "total": round(total_latency_ms, 1),
        },
        cached=was_cached,
        mode=effective_mode,
        typed=False,
    )


@router.post("/text-turn", response_model=VoiceTurnResponse)
async def process_text_turn(req: TextTurnRequest) -> VoiceTurnResponse:
    """
    Typed fallback turn: bypasses STT, executes FSM step, synthesizes TTS reply.
    """
    _cleanup_expired_sessions()
    session_obj = _SESSIONS.get(req.session_id)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found or expired. Please start a new session.",
        )
    session_obj.touch()

    text_input = req.text.strip()
    if not text_input:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Input text cannot be empty.")

    t_start = time.monotonic()
    session_obj.history.append({"role": "caller", "text": text_input, "timestamp": time.time()})

    await hub.broadcast(
        "voice.transcript",
        {
            "session_id": req.session_id,
            "role": "caller",
            "text": text_input,
            "timestamp": time.time(),
            "typed": True,
        },
    )

    # 1. Process Dialogue Turn via FSM
    turn_outcome = await _process_fsm_turn(session_obj, text_input)

    # 2. TTS REST (Cache-first)
    client = GnaniRestClient()
    t0_tts = time.monotonic()
    try:
        reply_wav_bytes, was_cached, tts_mode = await client.text_to_speech(
            text=turn_outcome["reply_text"],
            voice="Poorvi",
            model="timbre-v2.5",
            language="hi-en",
            speed=1.0,
            sample_rate=16000,
        )
    except GnaniQuotaExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GnaniRestError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    tts_latency_ms = (time.monotonic() - t0_tts) * 1000.0
    total_latency_ms = (time.monotonic() - t_start) * 1000.0

    session_obj.history.append({"role": "bot", "text": turn_outcome["reply_text"], "timestamp": time.time()})
    audio_b64 = base64.b64encode(reply_wav_bytes).decode("ascii") if reply_wav_bytes else ""

    await hub.broadcast(
        "voice.transcript",
        {
            "session_id": req.session_id,
            "role": "bot",
            "text": turn_outcome["reply_text"],
            "timestamp": time.time(),
        },
    )

    return VoiceTurnResponse(
        transcript=text_input,
        detected_language="hi-IN",
        reply_text=turn_outcome["reply_text"],
        audio_b64=audio_b64,
        state=turn_outcome["state"],
        slots=turn_outcome["slots"],
        is_terminal=turn_outcome["is_terminal"],
        is_urgent=turn_outcome["is_urgent"],
        needs_human=turn_outcome["needs_human"],
        latency_ms={
            "stt": 0.0,
            "tts": round(tts_latency_ms, 1),
            "total": round(total_latency_ms, 1),
        },
        cached=was_cached,
        mode=tts_mode,
        typed=True,
    )


@router.get("/usage")
def get_voice_usage() -> dict[str, Any]:
    """Retrieve usage telemetry, cached hit rates, and hourly quota limits."""
    return usage_tracker.get_stats()


# ─── FSM Helper & Persistence ──────────────────────────────────────────────────


async def _process_fsm_turn(session_obj: BrowserVoiceSession, utterance: str) -> dict[str, Any]:
    """
    Feeds utterance to BookingFSM or CollectionFSM, handles hub broadcasts,
    and persists records upon terminal outcomes.
    """
    if session_obj.flow == "collection":
        col_fsm: CollectionFSM = session_obj.fsm  # type: ignore[assignment]
        res = col_fsm.process_utterance(utterance)

        # Broadcast collection disposition
        disposition_val = col_fsm.disposition.value if col_fsm.disposition else col_fsm.state.value
        await hub.broadcast(
            "collection.disposition",
            {
                "session_id": session_obj.session_id,
                "customer_name": col_fsm.customer_name,
                "disposition": disposition_val,
                "ptp_date": col_fsm.captured_date,
                "is_terminal": res.is_terminal,
            },
        )

        return {
            "reply_text": res.bot_reply,
            "state": col_fsm.state.value,
            "slots": {
                "ptp_date": col_fsm.captured_date,
                "disposition": disposition_val,
            },
            "is_terminal": res.is_terminal,
            "is_urgent": False,
            "needs_human": bool(res.needs_owner),
        }

    # Booking flow
    book_fsm: BookingFSM = session_obj.fsm  # type: ignore[assignment]
    turn_res = book_fsm.process_utterance(utterance)

    # Broadcast slot updates
    if turn_res.slots.problem:
        await hub.broadcast(
            "slot.updated",
            {"session_id": session_obj.session_id, "field": "problem", "value": turn_res.slots.problem},
        )
    if turn_res.slots.landmark_address:
        await hub.broadcast(
            "slot.updated",
            {"session_id": session_obj.session_id, "field": "landmark_address", "value": turn_res.slots.landmark_address},
        )
    if turn_res.slots.time_slot:
        await hub.broadcast(
            "slot.updated",
            {"session_id": session_obj.session_id, "field": "time_slot", "value": turn_res.slots.time_slot},
        )

    # Booking confirmation or handoff
    if turn_res.current_state == BookingState.BOOKED and turn_res.job_payload:
        job_id = f"job_{int(time.time())}"
        await hub.broadcast(
            "job.booked",
            {
                "job_id": job_id,
                "session_id": session_obj.session_id,
                "summary": turn_res.slots.problem,
                **turn_res.job_payload,
            },
        )

    if turn_res.needs_handoff:
        await hub.broadcast(
            "call.handoff",
            {
                "session_id": session_obj.session_id,
                "reason": "emergency_hazard" if turn_res.is_urgent else "human_requested_or_unresolved",
                "urgent": turn_res.is_urgent,
            },
        )

    # Persist CallRecord and Job to database upon terminal state
    if turn_res.is_terminal:
        try:
            with Session(engine) as db_session:
                status_str = (
                    "booked"
                    if turn_res.current_state == BookingState.BOOKED
                    else ("urgent" if turn_res.is_urgent else "completed")
                )
                slots_dict = {
                    "problem": turn_res.slots.problem,
                    "problem_key": turn_res.slots.problem_key,
                    "landmark_address": turn_res.slots.landmark_address,
                    "time_slot": turn_res.slots.time_slot,
                    "customer_name": turn_res.slots.customer_name or "Web Caller",
                    "price_estimate": turn_res.slots.price_estimate,
                }
                call_record = CallRecord(
                    id=session_obj.session_id,
                    caller_number="+91-Web-Browser",
                    caller_number_masked="Web Browser",
                    customer_name=turn_res.slots.customer_name or "Web User",
                    timestamp=time.strftime("%I:%M %p"),
                    status=status_str,
                    duration_seconds=int(time.monotonic() - session_obj.created_at),
                    summary=turn_res.slots.problem or "Web voice demo call",
                    extracted_slots_json=json.dumps(slots_dict),
                    transcript_json=json.dumps(session_obj.history),
                )
                db_session.add(call_record)

                if turn_res.current_state == BookingState.BOOKED:
                    job_id = f"job_{int(time.time())}"
                    job = Job(
                        id=job_id,
                        call_id=session_obj.session_id,
                        customer_name=turn_res.slots.customer_name or "Web User",
                        phone="+91-Web-Browser",
                        address=turn_res.slots.landmark_address or "Delhi NCR",
                        problem=turn_res.slots.problem or "Plumbing request",
                        status="booked",
                        scheduled_time=turn_res.slots.time_slot or "Kal Subah",
                        price_estimate=turn_res.slots.price_estimate or 500,
                        created_at=time.strftime("%I:%M %p"),
                    )
                    db_session.add(job)

                db_session.commit()
        except Exception as db_err:
            logger.warning("Failed to persist browser voice call to DB: %s", db_err)

    return {
        "reply_text": turn_res.bot_reply,
        "state": turn_res.current_state.value,
        "slots": {
            "problem": turn_res.slots.problem,
            "problem_key": turn_res.slots.problem_key,
            "landmark_address": turn_res.slots.landmark_address,
            "time_slot": turn_res.slots.time_slot,
            "customer_name": turn_res.slots.customer_name,
            "price_estimate": turn_res.slots.price_estimate,
        },
        "is_terminal": turn_res.is_terminal,
        "is_urgent": turn_res.is_urgent,
        "needs_human": turn_res.needs_handoff,
    }
