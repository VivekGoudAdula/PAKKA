"""
CallSession state and lifecycle coordinator.

Manages:
- Exotel stream state (stream_sid, call_sid, caller info).
- Mandatory digital assistant disclosure greeting.
- Echo test: "Aapne kaha: <text>" via Gnani TTS.
- Barge-in detection: caller speech interrupts bot playback with Exotel `clear` frame.
- Structured latency metrics table: STT first-final, TTS first-chunk, full turn.
- Emits realtime events to the EventHub (call.started, transcript, bot.speaking, call.ended).
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlmodel import Session

from app.brain.dispatch import DispatchFSM
from app.brain.fsm import BookingFSM, BookingState
from app.config import settings
from app.db import engine
from app.events.hub import hub
from app.models.domain import CallRecord, Job
from app.voice.audio import EnergyVAD, ExotelAudioAccumulator, Rechunker, pcm_to_base64
from app.voice.gnani_stt import GnaniSTTClient
from app.voice.gnani_tts import GnaniTTSClient

logger = logging.getLogger(__name__)

MANDATORY_GREETING = (
    "Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?"
)


@dataclass
class TurnLatency:
    """Tracks latency components for a single conversational turn."""

    turn_id: int
    user_text: str
    stt_first_final_ms: float = 0.0
    tts_first_chunk_ms: float = 0.0
    total_turn_ms: float = 0.0


@dataclass
class CallSessionMetrics:
    """Aggregated call metrics for observability."""

    call_sid: str
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    turns: list[TurnLatency] = field(default_factory=list)
    total_caller_audio_bytes: int = 0
    total_bot_audio_bytes: int = 0
    barge_in_count: int = 0


class CallSession:
    """
    Coordinates one call stream between Exotel, Gnani STT, and Gnani TTS.
    """

    def __init__(
        self,
        call_sid: str,
        stream_sid: str,
        caller_number: str = "unknown",
        send_to_exotel: Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
        stt_client: GnaniSTTClient | None = None,
        tts_client: GnaniTTSClient | None = None,
        dispatch_fsm: DispatchFSM | None = None,
        dispatch_context: Any | None = None,
    ) -> None:
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.caller_number = caller_number
        self.send_to_exotel = send_to_exotel
        self.dispatch_fsm = dispatch_fsm
        self.dispatch_context = dispatch_context

        self.stt = stt_client or GnaniSTTClient()
        self.tts = tts_client or GnaniTTSClient()

        self.rechunker = Rechunker(target_chunk_size=1024)
        self.vad = EnergyVAD(
            rms_threshold=settings.vad_energy_threshold,
            required_consecutive_chunks=2,
        )
        self.metrics = CallSessionMetrics(call_sid=call_sid)
        self.brain = BookingFSM(handoff_phone=settings.telephony_handoff_number)
        self.transcript_messages: list[dict[str, Any]] = []
        self._is_urgent_call = False

        self._bot_is_speaking = False
        self._bot_utterance_start_time: float = 0.0
        self._barge_in_triggered_for_utterance: bool = False
        self._barge_in_active: bool = False
        self._last_playback_finished_time: float = 0.0

        self._current_tts_task: asyncio.Task[None] | None = None
        self._current_turn_id = 0
        self._is_active = True
        self._stt_consumer_task: asyncio.Task[None] | None = None

    @property
    def bot_is_speaking(self) -> bool:
        return self._bot_is_speaking

    async def start(self) -> None:
        """Initialize session, connect STT, emit call.started, speak greeting."""
        logger.info(
            "CallSession started: call_sid=%s, stream_sid=%s, caller=%s",
            self.call_sid,
            self.stream_sid,
            self.caller_number,
        )

        # Broadcast call.started event to frontend hub
        await hub.broadcast(
            "call.started",
            {
                "call_id": self.call_sid,
                "stream_sid": self.stream_sid,
                "caller_number_masked": self._mask_number(self.caller_number),
                "timestamp": time.time(),
            },
        )

        # Connect STT
        await self.stt.connect()

        # Start background consumer for incoming transcripts
        self._stt_consumer_task = asyncio.create_task(self._consume_stt_stream())

        greeting_text = (
            self.dispatch_fsm.get_initial_greeting()
            if self.dispatch_fsm
            else MANDATORY_GREETING
        )

        # Speak mandatory disclosure greeting concurrently so WebSocket loop handles caller events
        self.transcript_messages.append(
            {
                "id": "turn_0_bot",
                "role": "bot",
                "text": greeting_text,
                "timestamp": time.strftime("%H:%M:%S"),
                "is_disclosure": True,
            }
        )
        asyncio.create_task(self.speak(greeting_text, mark_name="greeting_done"))

    async def handle_caller_audio(self, pcm_chunk: bytes) -> None:
        """
        Handle audio received from Exotel (caller).
        - Analyzes chunk energy via VAD.
        - Checks for barge-in ONLY if speech is detected (2 consecutive speech chunks)
          and the 500 ms initial utterance grace period has passed.
        - Rechunks to 1024 bytes and streams to Gnani STT.
        """
        if not self._is_active or not pcm_chunk:
            return

        self.metrics.total_caller_audio_bytes += len(pcm_chunk)

        # Check for barge-in if assistant is speaking
        if self._bot_is_speaking:
            elapsed = time.monotonic() - self._bot_utterance_start_time
            if elapsed >= 0.500:
                # After 500 ms grace period, evaluate energy VAD
                is_speech = self.vad.process_chunk(pcm_chunk)
                if is_speech and not self._barge_in_triggered_for_utterance:
                    logger.info("Barge-in triggered via energy VAD on call_sid=%s", self.call_sid)
                    await self.barge_in()
            else:
                # Within initial 500 ms, ignore barge-in and reset VAD counter
                self.vad.reset()

        # Rechunk and send to Gnani STT
        for frame in self.rechunker.add(pcm_chunk):
            await self.stt.send_frame(frame)

    async def barge_in(self) -> None:
        """
        Interrupt ongoing bot speech:
        - Sends Exotel 'clear' event to flush telephony buffer.
        - Cancels ongoing TTS task.
        - Guarantees triggering at most once per utterance.
        """
        if self._barge_in_triggered_for_utterance:
            return

        self._barge_in_triggered_for_utterance = True
        self._barge_in_active = True
        self._bot_is_speaking = False
        self.metrics.barge_in_count += 1
        logger.info("Barge-in triggered on call_sid=%s: clearing Exotel buffer", self.call_sid)

        if self._current_tts_task and not self._current_tts_task.done():
            self._current_tts_task.cancel()
            self._current_tts_task = None

        if self.send_to_exotel:
            await self.send_to_exotel(
                {
                    "event": "clear",
                    "stream_sid": self.stream_sid,
                }
            )

    async def speak(self, text: str, mark_name: str | None = None) -> None:
        """
        Synthesize text via Gnani TTS and stream audio chunks to Exotel.
        Follows Exotel constraints: >= 3200 bytes and multiple of 320 bytes.
        """
        if not self._is_active:
            return

        # Cancel any prior TTS task if active
        if self._current_tts_task and not self._current_tts_task.done():
            self._current_tts_task.cancel()

        self._current_tts_task = asyncio.create_task(self._stream_speech(text, mark_name=mark_name))
        await self._current_tts_task

    async def _stream_speech(self, text: str, mark_name: str | None = None) -> None:
        """Internal speech streamer."""
        self._bot_is_speaking = True
        self._bot_utterance_start_time = time.monotonic()
        self._barge_in_triggered_for_utterance = False
        self._barge_in_active = False
        self.vad.reset()

        logger.info("Bot speaking on %s: '%s'", self.call_sid, text[:60])

        await hub.broadcast(
            "bot.speaking",
            {
                "call_id": self.call_sid,
                "text": text,
                "timestamp": time.time(),
            },
        )

        accumulator = ExotelAudioAccumulator(min_bytes=3200, multiple_of=320)
        tts_start_time = time.monotonic()
        first_chunk_sent = False

        try:
            async for pcm_chunk in self.tts.synthesize(text):
                if not self._bot_is_speaking or not self._is_active:
                    break

                for sendable_chunk in accumulator.add(pcm_chunk):
                    if not first_chunk_sent:
                        first_chunk_sent = True
                        ttfc = (time.monotonic() - tts_start_time) * 1000.0
                        logger.info("TTS first chunk to Exotel latency: %.1f ms", ttfc)

                    await self._send_media_to_exotel(sendable_chunk)

            # Flush any remaining audio
            final_chunk = accumulator.flush(pad_to_multiple=True)
            if final_chunk and self._bot_is_speaking and self._is_active:
                await self._send_media_to_exotel(final_chunk)

            # Send playback completion mark
            if mark_name and self.send_to_exotel and self._is_active:
                await self.send_to_exotel(
                    {
                        "event": "mark",
                        "stream_sid": self.stream_sid,
                        "mark": {"name": mark_name},
                    }
                )

        except asyncio.CancelledError:
            logger.info("TTS speech streaming cancelled (barge-in)")
        finally:
            self._bot_is_speaking = False
            if not self._barge_in_active:
                # Approximate end of playback buffer if mark is delayed
                self._last_playback_finished_time = time.monotonic()

    async def _send_media_to_exotel(self, pcm_data: bytes) -> None:
        """Helper to send a media frame to Exotel."""
        if not self.send_to_exotel:
            return
        self.metrics.total_bot_audio_bytes += len(pcm_data)
        b64_audio = pcm_to_base64(pcm_data)
        await self.send_to_exotel(
            {
                "event": "media",
                "stream_sid": self.stream_sid,
                "media": {
                    "payload": b64_audio,
                },
            }
        )

    async def _consume_stt_stream(self) -> None:
        """Reads transcripts from Gnani STT and processes turns."""
        try:
            async for transcript in self.stt.receive_transcripts():
                if not self._is_active:
                    break

                # Broadcast live transcript event to dashboard
                await hub.broadcast(
                    "transcript",
                    {
                        "call_id": self.call_sid,
                        "role": "caller",
                        "text": transcript.text,
                        "language": transcript.language,
                        "is_final": transcript.is_final,
                        "timestamp": time.time(),
                    },
                )

                # STT-based barge-in: non-empty text arriving after 500 ms while bot is speaking
                if self._bot_is_speaking:
                    elapsed = time.monotonic() - self._bot_utterance_start_time
                    if (
                        elapsed >= 0.500
                        and transcript.text.strip()
                        and not self._barge_in_triggered_for_utterance
                    ):
                        logger.info(
                            "Barge-in triggered via STT transcript on %s: '%s'",
                            self.call_sid,
                            transcript.text,
                        )
                        await self.barge_in()

                if transcript.is_final:
                    # Echo-loop guard: while bot is speaking or until 400 ms after playback ends,
                    # discard STT finals, unless barge-in was explicitly triggered by user speech.
                    now = time.monotonic()
                    time_since_playback = now - self._last_playback_finished_time
                    in_echo_guard = self._bot_is_speaking or (time_since_playback < 0.400)

                    if in_echo_guard and not self._barge_in_active:
                        logger.info(
                            "Echo-loop guard: Discarded STT final '%s' on %s "
                            "(bot_speaking=%s, time_since_end=%.3fs)",
                            transcript.text,
                            self.call_sid,
                            self._bot_is_speaking,
                            time_since_playback,
                        )
                        continue

                    # Clear turn barge-in flag as we begin responding to caller's input
                    self._barge_in_active = False

                    self._current_turn_id += 1
                    turn_start = time.monotonic()
                    logger.info(
                        "Final transcript on %s [Turn %d]: '%s'",
                        self.call_sid,
                        self._current_turn_id,
                        transcript.text,
                    )

                    # Record caller turn
                    self.transcript_messages.append(
                        {
                            "id": f"turn_{self._current_turn_id}_caller",
                            "role": "caller",
                            "text": transcript.text,
                            "timestamp": time.strftime("%H:%M:%S"),
                        }
                    )

                    if getattr(settings, "log_transcripts", False):
                        try:
                            log_path = (
                                Path(__file__).resolve().parent.parent.parent
                                / "reports"
                                / "live_transcripts.jsonl"
                            )
                            log_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(log_path, "a", encoding="utf-8") as f:
                                f.write(
                                    json.dumps(
                                        {
                                            "timestamp": time.time(),
                                            "call_id": self.call_sid,
                                            "turn_id": self._current_turn_id,
                                            "text": transcript.text,
                                            "confidence": transcript.confidence,
                                        }
                                    )
                                    + "\n"
                                )
                        except Exception as log_err:
                            logger.warning("Failed to write to live_transcripts.jsonl: %s", log_err)

                    # Phase 4 Dispatch vs Phase 3 Booking Brain
                    if self.dispatch_fsm:
                        dispatch_turn = self.dispatch_fsm.process_utterance(transcript.text)
                        self.transcript_messages.append(
                            {
                                "id": f"turn_{self._current_turn_id}_bot",
                                "role": "bot",
                                "text": dispatch_turn.bot_reply,
                                "timestamp": time.strftime("%H:%M:%S"),
                            }
                        )
                        job_id = getattr(self.dispatch_context, "job_id", "")
                        tech_id = getattr(self.dispatch_context, "technician_id", "")
                        tech_name = getattr(self.dispatch_context, "technician_name", "")

                        await hub.broadcast(
                            "dispatch.transcript",
                            {
                                "job_id": job_id,
                                "role": "technician",
                                "text": transcript.text,
                                "timestamp": time.time(),
                            },
                        )
                        await hub.broadcast(
                            "dispatch.transcript",
                            {
                                "job_id": job_id,
                                "role": "bot",
                                "text": dispatch_turn.bot_reply,
                                "timestamp": time.time(),
                            },
                        )
                        await self.speak(
                            dispatch_turn.bot_reply,
                            mark_name=f"dispatch_turn_{self._current_turn_id}",
                        )

                        if dispatch_turn.is_terminal:
                            if dispatch_turn.is_accepted:
                                if self.dispatch_context:
                                    self.dispatch_context.status = "accepted"
                                    self.dispatch_context.confirmation_phrase = (
                                        dispatch_turn.confirmation_phrase
                                    )
                                    self.dispatch_context.confirmed_at = time.strftime("%I:%M %p")

                                with Session(engine) as db:
                                    if job_id:
                                        db_job = db.get(Job, job_id)
                                        if db_job:
                                            db_job.status = "dispatched"
                                            db_job.technician_id = tech_id
                                            db.add(db_job)
                                    if tech_id:
                                        from app.models.domain import Technician

                                        db_tech = db.get(Technician, tech_id)
                                        if db_tech:
                                            db_tech.status = "on_job"
                                            db_tech.active_jobs_count += 1
                                            db.add(db_tech)
                                    db.commit()

                                await hub.broadcast(
                                    "dispatch.accepted",
                                    {
                                        "job_id": job_id,
                                        "technician_id": tech_id,
                                        "technician_name": tech_name,
                                        "confirmation_phrase": dispatch_turn.confirmation_phrase,
                                        "confirmed_at": time.strftime("%I:%M %p"),
                                        "timestamp": time.time(),
                                    },
                                )
                            elif dispatch_turn.is_declined:
                                if self.dispatch_context:
                                    self.dispatch_context.status = "declined"
                                await hub.broadcast(
                                    "dispatch.declined",
                                    {
                                        "job_id": job_id,
                                        "technician_id": tech_id,
                                        "technician_name": tech_name,
                                        "timestamp": time.time(),
                                    },
                                )
                                from app.services.dispatch_service import DispatchService

                                asyncio.create_task(DispatchService.dispatch_job(job_id=job_id))
                        continue

                    # Phase 3: Process turn via Booking Brain FSM
                    brain_result = self.brain.process_utterance(transcript.text)

                    # Record bot turn
                    self.transcript_messages.append(
                        {
                            "id": f"turn_{self._current_turn_id}_bot",
                            "role": "bot",
                            "text": brain_result.bot_reply,
                            "timestamp": time.strftime("%H:%M:%S"),
                            "is_disclosure": brain_result.ai_disclosure_triggered,
                        }
                    )

                    # Broadcast slot updates to frontend
                    if brain_result.slots.problem:
                        await hub.broadcast(
                            "slot.updated",
                            {
                                "call_id": self.call_sid,
                                "field": "problem",
                                "value": brain_result.slots.problem,
                            },
                        )
                    if brain_result.slots.landmark_address:
                        await hub.broadcast(
                            "slot.updated",
                            {
                                "call_id": self.call_sid,
                                "field": "landmark_address",
                                "value": brain_result.slots.landmark_address,
                            },
                        )
                    if brain_result.slots.time_slot:
                        await hub.broadcast(
                            "slot.updated",
                            {
                                "call_id": self.call_sid,
                                "field": "time_slot",
                                "value": brain_result.slots.time_slot,
                            },
                        )

                    # Speak bot reply
                    await self.speak(
                        brain_result.bot_reply,
                        mark_name=f"brain_turn_{self._current_turn_id}",
                    )

                    # Broadcast booking or handoff events
                    if (
                        brain_result.current_state == BookingState.BOOKED
                        and brain_result.job_payload
                    ):
                        job_id = f"job_{int(time.time())}"
                        await hub.broadcast(
                            "job.booked",
                            {
                                "job_id": job_id,
                                "call_id": self.call_sid,
                                "summary": brain_result.slots.problem,
                                **brain_result.job_payload,
                            },
                        )

                        # Auto-dispatch if enabled in BusinessSettings
                        try:
                            from sqlmodel import select

                            from app.models.domain import BusinessSettings
                            from app.services.dispatch_service import DispatchService

                            with Session(engine) as db:
                                b_settings = db.exec(select(BusinessSettings)).first()
                                if b_settings and b_settings.auto_dispatch:
                                    logger.info(
                                        "Auto-dispatch enabled; triggering dispatch for job %s",
                                        job_id,
                                    )
                                    asyncio.create_task(DispatchService.dispatch_job(job_id=job_id))
                        except Exception as auto_err:
                            logger.warning("Auto-dispatch trigger failed: %s", auto_err)

                    if brain_result.needs_handoff:
                        if brain_result.is_urgent:
                            self._is_urgent_call = True
                        await hub.broadcast(
                            "call.handoff",
                            {
                                "call_id": self.call_sid,
                                "reason": "emergency_hazard"
                                if brain_result.is_urgent
                                else "human_requested_or_unresolved",
                                "urgent": brain_result.is_urgent,
                            },
                        )

                    total_turn_ms = (time.monotonic() - turn_start) * 1000.0
                    turn_metric = TurnLatency(
                        turn_id=self._current_turn_id,
                        user_text=transcript.text,
                        stt_first_final_ms=transcript.latency_ms,
                        total_turn_ms=total_turn_ms,
                    )
                    self.metrics.turns.append(turn_metric)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Error in STT stream consumer: %s", exc)

    async def handle_mark(self, mark_name: str) -> None:
        """Acknowledge mark event from Exotel (playback reached end)."""
        self._last_playback_finished_time = time.monotonic()
        logger.info(
            "Mark reached on %s: %s (playback finished at %.3f)",
            self.call_sid,
            mark_name,
            self._last_playback_finished_time,
        )

    async def close(self, reason: str = "callended") -> None:
        """Tear down session, close STT, print observability latency table."""
        if not self._is_active:
            return
        self._is_active = False
        self.metrics.end_time = time.monotonic()

        logger.info("Closing CallSession %s (reason: %s)", self.call_sid, reason)

        if self._current_tts_task and not self._current_tts_task.done():
            self._current_tts_task.cancel()

        if self._stt_consumer_task and not self._stt_consumer_task.done():
            self._stt_consumer_task.cancel()

        await self.stt.close()

        # Emit call.ended event
        await hub.broadcast(
            "call.ended",
            {
                "call_id": self.call_sid,
                "reason": reason,
                "total_turns": len(self.metrics.turns),
                "timestamp": time.time(),
            },
        )

        # Persist CallRecord and Job to SQLite database
        try:
            with Session(engine) as db_session:
                slots_dict = {
                    "problem": self.brain.slots.problem,
                    "problem_key": self.brain.slots.problem_key,
                    "landmark_address": self.brain.slots.landmark_address,
                    "time_slot": self.brain.slots.time_slot,
                    "customer_name": self.brain.slots.customer_name,
                    "price_estimate": self.brain.slots.price_estimate,
                }
                status_str = (
                    "booked"
                    if self.brain.state == BookingState.BOOKED
                    else (
                        "urgent"
                        if self._is_urgent_call
                        else (
                            "needs_human"
                            if self.brain.state == BookingState.HANDOFF
                            else "completed"
                        )
                    )
                )
                duration_s = int(
                    (self.metrics.end_time or time.monotonic()) - self.metrics.start_time
                )
                call_record = CallRecord(
                    id=self.call_sid,
                    caller_number=self.caller_number,
                    caller_number_masked=self._mask_number(self.caller_number),
                    customer_name=self.brain.slots.customer_name or "Caller",
                    timestamp=time.strftime("%I:%M %p"),
                    status=status_str,
                    duration_seconds=max(duration_s, 1),
                    summary=self.brain.slots.problem or "Inbound customer call",
                    extracted_slots_json=json.dumps(slots_dict),
                    transcript_json=json.dumps(self.transcript_messages),
                )
                db_session.add(call_record)

                if self.brain.state == BookingState.BOOKED:
                    job_id = f"job_{int(time.time())}"
                    job = Job(
                        id=job_id,
                        call_id=self.call_sid,
                        title=self.brain.slots.problem or "Service Repair",
                        problem=self.brain.slots.problem or "Service Repair",
                        landmark_address=self.brain.slots.landmark_address or "Customer address",
                        time_slot=self.brain.slots.time_slot or "Standard slot",
                        price_estimate=self.brain.slots.price_estimate or "Standard rates",
                        price_min=self.brain.slots.price_min or 250,
                        price_max=self.brain.slots.price_max or 500,
                        status="booked",
                        confirmed_at=time.strftime("%I:%M %p"),
                        customer_name=self.brain.slots.customer_name or "Caller",
                        customer_phone_masked=self._mask_number(self.caller_number),
                    )
                    db_session.add(job)

                db_session.commit()
        except Exception as db_err:
            logger.error("Failed to persist call record to DB: %s", db_err)

        self._log_latency_table()

    def _log_latency_table(self) -> None:
        """Print structured call summary & latency table for observability."""
        duration_s = (self.metrics.end_time or time.monotonic()) - self.metrics.start_time
        logger.info("════════════════════════════════════════════════════════════════")
        logger.info(" CALL SUMMARY & LATENCY TABLE: %s", self.call_sid)
        logger.info(" Duration: %.1fs | Barge-ins: %d", duration_s, self.metrics.barge_in_count)
        logger.info(
            " Caller Audio: %d bytes | Bot Audio: %d bytes",
            self.metrics.total_caller_audio_bytes,
            self.metrics.total_bot_audio_bytes,
        )
        logger.info("----------------------------------------------------------------")
        logger.info(" TURN | STT FINAL (ms) | TOTAL TURN (ms) | TEXT")
        logger.info("----------------------------------------------------------------")
        for turn in self.metrics.turns:
            logger.info(
                " %4d | %14.1f | %15.1f | %s",
                turn.turn_id,
                turn.stt_first_final_ms,
                turn.total_turn_ms,
                turn.user_text[:35],
            )
        logger.info("════════════════════════════════════════════════════════════════")

    @staticmethod
    def _mask_number(phone: str) -> str:
        """Mask middle digits of phone number for privacy."""
        if len(phone) > 6:
            return phone[:4] + "XXXX" + phone[-2:]
        return phone
