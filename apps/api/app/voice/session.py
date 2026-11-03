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
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from app.events.hub import hub
from app.voice.audio import ExotelAudioAccumulator, Rechunker, pcm_to_base64
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
    ) -> None:
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.caller_number = caller_number
        self.send_to_exotel = send_to_exotel

        self.stt = stt_client or GnaniSTTClient()
        self.tts = tts_client or GnaniTTSClient()

        self.rechunker = Rechunker(target_chunk_size=1024)
        self.metrics = CallSessionMetrics(call_sid=call_sid)

        self._bot_is_speaking = False
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

        # Speak mandatory disclosure greeting concurrently so WebSocket loop handles caller events
        asyncio.create_task(self.speak(MANDATORY_GREETING, mark_name="greeting_done"))

    async def handle_caller_audio(self, pcm_chunk: bytes) -> None:
        """
        Handle audio received from Exotel (caller).
        - Rechunks to 1024 bytes and streams to Gnani STT.
        - Checks for barge-in if bot is speaking.
        """
        if not self._is_active or not pcm_chunk:
            return

        self.metrics.total_caller_audio_bytes += len(pcm_chunk)

        # Check for barge-in: caller spoke while assistant was speaking
        if self._bot_is_speaking:
            await self.barge_in()

        # Rechunk and send to Gnani STT
        for frame in self.rechunker.add(pcm_chunk):
            await self.stt.send_frame(frame)

    async def barge_in(self) -> None:
        """
        Interrupt ongoing bot speech:
        - Sends Exotel 'clear' event to flush telephony buffer.
        - Cancels ongoing TTS task.
        """
        logger.info("Barge-in triggered on call_sid=%s: clearing Exotel buffer", self.call_sid)
        self.metrics.barge_in_count += 1
        self._bot_is_speaking = False

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

                if transcript.is_final:
                    self._current_turn_id += 1
                    turn_start = time.monotonic()
                    logger.info(
                        "Final transcript on %s [Turn %d]: '%s'",
                        self.call_sid,
                        self._current_turn_id,
                        transcript.text,
                    )

                    # Phase 1 Echo Test: "Aapne kaha: <text>"
                    echo_reply = f"Aapne kaha: {transcript.text}"
                    await self.speak(echo_reply, mark_name=f"echo_turn_{self._current_turn_id}")

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
        logger.info("Mark reached on %s: %s", self.call_sid, mark_name)

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
