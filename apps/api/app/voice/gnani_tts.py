"""
Gnani Vachana Timbre TTS WebSocket Client.

Endpoint: wss://api.vachana.ai/api/v1/tts
Auth header: X-API-Key-ID: <key>
Output format: 8000 Hz, raw PCM linear16 mono.
"""

import asyncio
import contextlib
import json
import logging
import math
import socket
import ssl
import time
from collections.abc import AsyncGenerator

import websockets

try:
    from websockets.asyncio.client import ClientConnection as WebSocketClientProtocol
except ImportError:
    from websockets.client import WebSocketClientProtocol

from app.config import settings
from app.voice.audio import base64_to_pcm

logger = logging.getLogger(__name__)


def generate_synthetic_pcm(
    duration_ms: int = 1000, sample_rate: int = 8000, frequency: float = 440.0
) -> bytes:
    """
    Generate synthetic 16-bit linear PCM mono sine wave for dry-run/offline testing.
    """
    num_samples = int((sample_rate * duration_ms) / 1000)
    pcm = bytearray()
    for i in range(num_samples):
        # Sine wave sampled at sample_rate, amplitude 6000 (clear audible tone)
        sample = int(6000 * math.sin(2 * math.pi * frequency * (i / sample_rate)))
        # Convert signed 16-bit little-endian
        pcm.extend(sample.to_bytes(2, byteorder="little", signed=True))
    return bytes(pcm)


class GnaniTTSClient:
    """
    Client for Gnani Vachana Timbre realtime TTS.
    """

    def __init__(
        self,
        api_key: str | None = None,
        ws_url: str | None = None,
        model: str = "timbre-v2.5",
        voice: str = "Poorvi",
        language: str = "hi-en",
        speed: float = 1.0,
        sample_rate: int = 8000,
        dry_run: bool = False,
        realtime_cadence: bool = True,
    ) -> None:
        self.api_key = api_key or settings.gnani_api_key
        self.ws_url = ws_url or settings.gnani_tts_ws_url
        self.model = model
        self.voice = voice
        self.language = language
        self.speed = speed
        self.sample_rate = sample_rate
        self.dry_run = dry_run or settings.gnani_dry_run
        self.realtime_cadence = realtime_cadence

    async def synthesize(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text to raw linear16 PCM bytes chunks.
        Yields raw bytes as they arrive.
        """
        if not text or not text.strip():
            return

        start_time = time.monotonic()
        first_chunk_received = False

        if self.dry_run:
            logger.info("GnaniTTSClient: [SYNTHETIC] synthesizing text: '%s'", text[:60])
            if self.realtime_cadence:
                await asyncio.sleep(0.25)
            # Yield ~2.4s of synthetic PCM in 3200-byte chunks
            synth_pcm = generate_synthetic_pcm(duration_ms=2400, sample_rate=self.sample_rate)
            chunk_size = 3200
            for i in range(0, len(synth_pcm), chunk_size):
                chunk = synth_pcm[i : i + chunk_size]
                yield chunk
                if self.realtime_cadence:
                    await asyncio.sleep(0.18)
            return

        headers = {"X-API-Key-ID": self.api_key}
        logger.info(
            "Connecting to Gnani TTS (%s): model=%s voice=%s lang=%s",
            self.ws_url,
            self.model,
            self.voice,
            self.language,
        )

        ws: WebSocketClientProtocol | None = None
        try:
            async with asyncio.timeout(10.0):
                ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    open_timeout=10.0,
                )
        except TimeoutError as exc:
            err_type = "Connection Timeout (10s exceeded)"
            logger.error("Failed to connect to Gnani TTS: %s", err_type)
            raise RuntimeError(f"Gnani TTS Failure: {err_type}") from exc
        except websockets.InvalidStatusCode as exc:
            err_type = f"Auth / HTTP Rejected (HTTP {exc.status_code})"
            logger.error("Failed to connect to Gnani TTS: %s", err_type)
            raise RuntimeError(f"Gnani TTS Failure: {err_type}") from exc
        except ssl.SSLError as exc:
            err_type = f"TLS / SSL Handshake Error ({type(exc).__name__})"
            logger.error("Failed to connect to Gnani TTS: %s", err_type)
            raise RuntimeError(f"Gnani TTS Failure: {err_type}") from exc
        except (socket.gaierror, OSError) as exc:
            err_type = f"DNS Resolution / Network Unreachable ({type(exc).__name__})"
            logger.error("Failed to connect to Gnani TTS: %s", err_type)
            raise RuntimeError(f"Gnani TTS Failure: {err_type}") from exc
        except Exception as exc:
            err_type = f"Connection Failed ({type(exc).__name__})"
            logger.error("Failed to connect to Gnani TTS: %s", err_type)
            raise RuntimeError(f"Gnani TTS Failure: {err_type}") from exc

        try:
            # Build synthesis payload
            request_payload = {
                "text": text.strip(),
                "voice": self.voice,
                "model": self.model,
                "language": self.language,
                "speed": self.speed,
                "audio_config": {
                    "sample_rate": self.sample_rate,
                    "container": "raw",
                    "encoding": "linear_pcm",
                },
            }

            await ws.send(json.dumps(request_payload))

            async for msg in ws:
                if isinstance(msg, bytes):
                    yield msg
                    continue

                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue

                status = data.get("status", "")
                if status == "complete":
                    break

                # Extract base64 audio chunk
                b64_audio = data.get("audio") or data.get("audio_content")
                if b64_audio:
                    pcm_chunk = base64_to_pcm(b64_audio)
                    if pcm_chunk:
                        if not first_chunk_received:
                            first_chunk_received = True
                            ttfc = (time.monotonic() - start_time) * 1000
                            logger.info("TTS first chunk latency (TTFC): %.1f ms", ttfc)
                        yield pcm_chunk

        except websockets.ConnectionClosed:
            logger.info("Gnani TTS WebSocket connection closed by remote")
        except Exception as exc:
            logger.error("Error during Gnani TTS synthesis: %s", exc)
            raise
        finally:
            if ws:
                with contextlib.suppress(Exception):
                    await ws.close()
