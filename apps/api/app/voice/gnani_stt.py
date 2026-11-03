"""
Gnani Vachana Prisma v3.0 Realtime STT WebSocket Client.

Endpoint: wss://api.vachana.ai/stt/v3/stream
Audio format: raw PCM s16le mono, exactly 1024-byte binary frames at real-time cadence.
"""

import asyncio
import contextlib
import json
import logging
import socket
import ssl
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import websockets

try:
    from websockets.asyncio.client import ClientConnection as WebSocketClientProtocol
except ImportError:
    from websockets.client import WebSocketClientProtocol

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class STTTranscript:
    """Represents a speech-to-text transcript item."""

    text: str
    is_final: bool
    language: str = "hi-IN"
    confidence: float = 1.0
    latency_ms: float = 0.0


class GnaniSTTClient:
    """
    Manages raw WebSocket connection to Gnani Vachana STT Prisma v3.0.
    """

    def __init__(
        self,
        api_key: str | None = None,
        ws_url: str | None = None,
        sample_rate: int = 8000,
        language_code: str = "hi-IN,en-IN",
        model: str = "prisma-v3.0",
        vad_threshold: float = 0.7,
        min_speech_ms: int = 200,
        min_silence_ms: int = 500,
        format_mode: str = "codemix",
        keyterms: str = "geyser,tap,leak,motor,pipe,bathroom,kitchen",
        dry_run: bool = False,
    ) -> None:
        self.api_key = api_key or settings.gnani_api_key
        self.ws_url = ws_url or settings.gnani_stt_ws_url
        self.sample_rate = sample_rate
        self.language_code = language_code
        self.model = model
        self.vad_threshold = vad_threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.format_mode = format_mode
        self.keyterms = keyterms
        self.dry_run = dry_run or settings.gnani_dry_run

        self._ws: WebSocketClientProtocol | None = None
        self._connected = False
        self._first_audio_sent_time: float | None = None
        self._first_transcript_time: float | None = None
        self._audio_received_event = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _build_headers(self) -> dict[str, str]:
        """Construct upgrade headers as documented in GNANI_API_NOTES.md."""
        return {
            "x-api-key-id": self.api_key,
            "model": self.model,
            "language_code": self.language_code,
            "x-sample-rate": str(self.sample_rate),
            "x-vad-threshold": str(self.vad_threshold),
            "x-min-speech-ms": str(self.min_speech_ms),
            "x-min-silence-ms": str(self.min_silence_ms),
            "format": self.format_mode,
            "keyterms": self.keyterms,
        }

    async def connect(self) -> None:
        """Open the WebSocket connection to Gnani STT with a 10s connect timeout."""
        if self.dry_run:
            logger.info("GnaniSTTClient: [SYNTHETIC] mode active. External connection skipped.")
            self._connected = True
            return

        headers = self._build_headers()
        logger.info(
            "Connecting to Gnani STT Prisma v3.0: %s (model=%s, lang=%s)",
            self.ws_url,
            self.model,
            self.language_code,
        )

        try:
            async with asyncio.timeout(10.0):
                self._ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    open_timeout=10.0,
                )
                self._connected = True
                logger.info("Gnani STT WebSocket connected successfully")
        except TimeoutError as exc:
            self._connected = False
            err_type = "Connection Timeout (10s exceeded)"
            logger.error("Failed to connect to Gnani STT: %s", err_type)
            raise RuntimeError(f"Gnani STT Failure: {err_type}") from exc
        except websockets.InvalidStatusCode as exc:
            self._connected = False
            err_type = f"Auth / HTTP Rejected (HTTP {exc.status_code})"
            logger.error("Failed to connect to Gnani STT: %s", err_type)
            raise RuntimeError(f"Gnani STT Failure: {err_type}") from exc
        except ssl.SSLError as exc:
            self._connected = False
            err_type = f"TLS / SSL Handshake Error ({type(exc).__name__})"
            logger.error("Failed to connect to Gnani STT: %s", err_type)
            raise RuntimeError(f"Gnani STT Failure: {err_type}") from exc
        except (socket.gaierror, OSError) as exc:
            self._connected = False
            err_type = f"DNS Resolution / Network Unreachable ({type(exc).__name__})"
            logger.error("Failed to connect to Gnani STT: %s", err_type)
            raise RuntimeError(f"Gnani STT Failure: {err_type}") from exc
        except Exception as exc:
            self._connected = False
            err_type = f"Connection Failed ({type(exc).__name__})"
            logger.error("Failed to connect to Gnani STT: %s", err_type)
            raise RuntimeError(f"Gnani STT Failure: {err_type}") from exc

    async def send_frame(self, pcm_frame: bytes) -> None:
        """
        Send exactly one raw PCM audio frame (must be 1024 bytes).
        """
        if not self._connected:
            raise RuntimeError("STT client is not connected")

        if len(pcm_frame) != 1024:
            logger.warning(
                "STT frame size is %d bytes, expected exactly 1024 bytes. Frame ignored.",
                len(pcm_frame),
            )
            return

        if self._first_audio_sent_time is None:
            self._first_audio_sent_time = time.monotonic()

        self._audio_received_event.set()

        if self.dry_run:
            # In dry run mode, frames are absorbed into the simulator
            return

        if self._ws:
            await self._ws.send(pcm_frame)

    async def commit(self) -> None:
        """Send commit control frame to signal end of utterance."""
        if not self._connected:
            return

        if self.dry_run:
            return

        if self._ws:
            control_msg = json.dumps({"type": "commit"})
            await self._ws.send(control_msg)

    async def receive_transcripts(self) -> AsyncGenerator[STTTranscript, None]:
        """
        Async generator yielding STTTranscript objects from the STT stream.
        """
        if not self._connected:
            return

        if self.dry_run:
            # In dry-run mode, wait until caller audio has been received
            try:
                await self._audio_received_event.wait()
            except asyncio.CancelledError:
                return

            # Simulate realistic VAD + model latency (~200ms)
            await asyncio.sleep(0.2)
            logger.info(
                "[SYNTHETIC] Gnani STT generated simulated transcript: '%s'",
                "Geyser kharab hai paani garam nahi ho raha",
            )
            yield STTTranscript(
                text="Geyser kharab hai paani garam nahi ho raha",
                is_final=True,
                language="hi-IN",
                confidence=0.95,
                latency_ms=200.0,
            )
            return

        if not self._ws:
            return

        try:
            async for raw_msg in self._ws:
                now = time.monotonic()
                if self._first_transcript_time is None and self._first_audio_sent_time is not None:
                    self._first_transcript_time = now
                    latency_ms = (
                        self._first_transcript_time - self._first_audio_sent_time
                    ) * 1000.0
                else:
                    latency_ms = 0.0

                if isinstance(raw_msg, bytes):
                    # Control binary message (unlikely, but ignore safely)
                    continue

                try:
                    payload = json.loads(raw_msg)
                except json.JSONDecodeError:
                    continue

                # Parse Gnani v3 format: {"transcript": "...", "is_final": bool, ...}
                text = (
                    payload.get("transcript")
                    or payload.get("text")
                    or payload.get("data", {}).get("transcript", "")
                )
                if not text:
                    continue

                is_final = bool(payload.get("is_final", False))
                confidence = float(payload.get("confidence", 1.0))
                language = str(payload.get("language", "hi-IN"))

                yield STTTranscript(
                    text=text.strip(),
                    is_final=is_final,
                    language=language,
                    confidence=confidence,
                    latency_ms=latency_ms,
                )

        except websockets.ConnectionClosed:
            logger.info("Gnani STT WebSocket connection closed by remote")
        finally:
            self._connected = False

    async def close(self) -> None:
        """Close the WebSocket connection."""
        self._connected = False
        self._audio_received_event.set()
        if self._ws:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None
