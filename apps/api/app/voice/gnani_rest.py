"""
apps/api/app/voice/gnani_rest.py
Async Gnani Vachana REST API client for STT (Prisma v3.0) and TTS (Timbre v2.5).

Implements:
1. Strict concurrency guard: Global asyncio.Lock ensuring only ONE Gnani request in flight.
2. 429 backoff: On HTTP 429 Rate Limited, wait 1.5s and retry once.
3. Disk TTS caching: SHA-256 keyed WAV cache in apps/api/cache/tts.
4. Usage guard: Rolling 1-hour rate limit guard and audit log in reports/usage_log.jsonl.
5. Typed error taxonomy without leaking secret keys in error messages.
6. Offline dry-run fallback when GNANI_DRY_RUN is enabled.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import struct
import time
import wave
from collections import deque
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Global single-flight lock for all outbound Gnani REST requests
_GNANI_GLOBAL_LOCK: asyncio.Lock | None = None


def _get_gnani_lock() -> asyncio.Lock:
    """Return the single-flight asyncio lock bound to the active event loop."""
    global _GNANI_GLOBAL_LOCK
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _GNANI_GLOBAL_LOCK is None or getattr(_GNANI_GLOBAL_LOCK, "_loop", None) != current_loop:
        _GNANI_GLOBAL_LOCK = asyncio.Lock()
    return _GNANI_GLOBAL_LOCK


# ─── Typed Exceptions ──────────────────────────────────────────────────────────


class GnaniRestError(Exception):
    """Base exception for all Gnani REST client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class GnaniAuthError(GnaniRestError):
    """HTTP 401 Unauthorized: Invalid or missing API key."""

    def __init__(self, message: str = "Invalid or missing Gnani API key") -> None:
        super().__init__(message, status_code=401)


class GnaniCreditError(GnaniRestError):
    """HTTP 402 Payment Required: Insufficient account credit."""

    def __init__(self, message: str = "Insufficient Gnani account credit") -> None:
        super().__init__(message, status_code=402)


class GnaniScopeError(GnaniRestError):
    """HTTP 403 Forbidden: Scope or action not allowed."""

    def __init__(self, message: str = "Gnani action forbidden: scope not allowed") -> None:
        super().__init__(message, status_code=403)


class GnaniRateLimitError(GnaniRestError):
    """HTTP 429 Too Many Requests from Gnani API."""

    def __init__(self, message: str = "Gnani rate limit reached: only 1 active request allowed") -> None:
        super().__init__(message, status_code=429)


class GnaniQuotaExceededError(GnaniRestError):
    """App-level guard: Hourly call budget exceeded."""

    def __init__(self, message: str = "App limit exceeded: MAX_GNANI_CALLS_PER_HOUR reached") -> None:
        super().__init__(message, status_code=429)


class GnaniServiceError(GnaniRestError):
    """HTTP 5xx Server / Gateway Error."""

    def __init__(self, message: str = "Gnani service temporarily unavailable", status_code: int = 500) -> None:
        super().__init__(message, status_code=status_code)


class GnaniTimeoutError(GnaniRestError):
    """Network connection or read timeout."""

    def __init__(self, message: str = "Gnani REST request timed out") -> None:
        super().__init__(message, status_code=504)


class GnaniNetworkError(GnaniRestError):
    """DNS resolution, TLS handshake, or connection error."""

    def __init__(self, message: str = "Network connection to Gnani failed") -> None:
        super().__init__(message, status_code=502)


class GnaniResponseError(GnaniRestError):
    """Malformed JSON or unexpected payload format."""

    def __init__(self, message: str = "Unexpected response format from Gnani") -> None:
        super().__init__(message, status_code=502)


# ─── Usage Tracker & Guard ────────────────────────────────────────────────────


class GnaniUsageTracker:
    """Tracks hourly Gnani calls and persists usage telemetry."""

    def __init__(self) -> None:
        self.call_timestamps: deque[float] = deque()
        self.total_stt_calls: int = 0
        self.total_tts_calls: int = 0
        self.cached_tts_hits: int = 0
        self.failed_calls: int = 0

    def check_and_record_budget(self, max_per_hour: int) -> None:
        """Check if rolling 1-hour window budget is exceeded."""
        now = time.monotonic()
        one_hour_ago = now - 3600.0

        # Prune calls older than 1 hour
        while self.call_timestamps and self.call_timestamps[0] < one_hour_ago:
            self.call_timestamps.popleft()

        if len(self.call_timestamps) >= max_per_hour:
            raise GnaniQuotaExceededError(
                f"Hourly rate limit exceeded: {len(self.call_timestamps)} calls in the last hour "
                f"(max {max_per_hour})"
            )

        self.call_timestamps.append(now)

    def log_call(
        self,
        kind: str,
        ok: bool,
        latency_ms: float,
        cached: bool = False,
    ) -> None:
        """Log event in-memory and append to reports/usage_log.jsonl."""
        if kind == "tts":
            if cached:
                self.cached_tts_hits += 1
            else:
                self.total_tts_calls += 1
        elif kind == "stt":
            self.total_stt_calls += 1

        if not ok:
            self.failed_calls += 1

        try:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            log_path = repo_root / "reports" / "usage_log.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)

            entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "kind": kind,
                "ok": ok,
                "latency_ms": round(latency_ms, 2),
                "cached": cached,
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.warning("Failed to write to usage_log.jsonl: %s", exc)

    def get_stats(self) -> dict[str, Any]:
        """Return usage telemetry snapshot."""
        now = time.monotonic()
        one_hour_ago = now - 3600.0
        recent = [t for t in self.call_timestamps if t >= one_hour_ago]

        return {
            "calls_last_hour": len(recent),
            "max_calls_per_hour": settings.max_gnani_calls_per_hour,
            "total_stt_calls": self.total_stt_calls,
            "total_tts_calls": self.total_tts_calls,
            "cached_tts_hits": self.cached_tts_hits,
            "failed_calls": self.failed_calls,
        }


# Singleton usage tracker
usage_tracker = GnaniUsageTracker()


# ─── TTS Disk Cache ───────────────────────────────────────────────────────────


class GnaniTTSCache:
    """Manages disk-cached synthesized WAV audio files."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        if cache_dir is None:
            base = Path(__file__).resolve().parent.parent.parent
            self.cache_dir = base / "cache" / "tts"
        else:
            self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_key(
        text: str,
        voice: str,
        model: str,
        language: str,
        speed: float,
        sample_rate: int,
    ) -> str:
        """Deterministic sha256 hash across speech generation parameters."""
        raw = f"{text.strip()}|{voice}|{model}|{language}|{speed:.2f}|{sample_rate}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> bytes | None:
        """Retrieve cached WAV bytes if available."""
        file_path = self.cache_dir / f"{cache_key}.wav"
        if file_path.exists():
            try:
                return file_path.read_bytes()
            except Exception as exc:
                logger.warning("Failed to read TTS cache file %s: %s", file_path, exc)
                return None
        return None

    def put(self, cache_key: str, wav_bytes: bytes) -> Path:
        """Store WAV bytes in cache directory."""
        file_path = self.cache_dir / f"{cache_key}.wav"
        try:
            file_path.write_bytes(wav_bytes)
        except Exception as exc:
            logger.warning("Failed to write TTS cache file %s: %s", file_path, exc)
        return file_path


# Singleton TTS cache
tts_cache = GnaniTTSCache()


# ─── Synthetic Audio Generator for Dry-run ─────────────────────────────────────


def generate_synthetic_wav(
    duration_ms: int = 1500,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> bytes:
    """Generate in-memory valid WAV bytes containing a gentle sine wave tone."""
    num_samples = int((sample_rate * duration_ms) / 1000)
    pcm = bytearray()
    for i in range(num_samples):
        sample = int(4500 * math.sin(2 * math.pi * frequency * (i / sample_rate)))
        pcm.extend(struct.pack("<h", sample))

    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)

    return buf.getvalue()


# ─── Gnani REST Client ────────────────────────────────────────────────────────


class GnaniRestClient:
    """
    High-level async REST client for Gnani STT (Prisma v3.0) and TTS (Timbre v2.5).
    Enforces concurrency lock, 429 retries, audio caching, and usage tracking.
    """

    def __init__(
        self,
        api_key: str | None = None,
        stt_url: str | None = None,
        tts_url: str | None = None,
        dry_run: bool | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.gnani_api_key
        self.stt_url = stt_url or settings.gnani_stt_rest_url
        self.tts_url = tts_url or settings.gnani_tts_rest_url
        self.dry_run = dry_run if dry_run is not None else settings.gnani_dry_run
        self._custom_client = http_client

    def _is_dry_run(self) -> bool:
        return bool(self.dry_run or not self.api_key or self.api_key.startswith("your_"))

    async def _execute_with_lock_and_retry(
        self,
        req_fn: Any,
        kind: str,
        timeout: float,
    ) -> httpx.Response:
        """
        Executes an HTTP request inside the global lock with 429 retry backoff.
        """
        lock = _get_gnani_lock()
        async with lock:
            usage_tracker.check_and_record_budget(settings.max_gnani_calls_per_hour)

            for attempt in range(2):
                try:
                    if self._custom_client:
                        resp = await req_fn(self._custom_client)
                    else:
                        async with httpx.AsyncClient(timeout=timeout) as client:
                            resp = await req_fn(client)

                    if resp.status_code == 429 and attempt == 0:
                        logger.warning("Gnani returned 429 Rate Limited; waiting 1.5s to retry once")
                        await asyncio.sleep(1.5)
                        continue

                    return resp

                except httpx.TimeoutException as exc:
                    raise GnaniTimeoutError(f"Gnani {kind.upper()} request timed out after {timeout}s") from exc
                except httpx.NetworkError as exc:
                    raise GnaniNetworkError(f"Gnani {kind.upper()} network error: {type(exc).__name__}") from exc
                except Exception as exc:
                    if isinstance(exc, GnaniRestError):
                        raise
                    raise GnaniNetworkError(f"Gnani {kind.upper()} request failed: {type(exc).__name__}") from exc

            return resp

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        model: str = "prisma-v3.0",
        language_code: str = "hi-IN",
        format_mode: str = "codemix",
    ) -> dict[str, Any]:
        """
        Transcribe audio via Gnani Prisma v3.0 REST API.
        Returns: {transcript: str, detected_language: str, processing_time: float, mode: str}
        """
        t0 = time.monotonic()

        # Offline Dry-Run Mode
        if self._is_dry_run():
            await asyncio.sleep(0.05)  # brief async yield
            lat_ms = (time.monotonic() - t0) * 1000.0
            usage_tracker.log_call(kind="stt", ok=True, latency_ms=lat_ms, cached=False)
            return {
                "transcript": "Geyser kharab hai paani garam nahi ho raha",
                "detected_language": "hi-IN",
                "processing_time": round(lat_ms / 1000.0, 3),
                "mode": "dry_run",
            }

        headers = {
            "X-API-Key-ID": self.api_key,
        }
        files = {
            "audio_file": (filename, audio_bytes, content_type),
        }
        data = {
            "model": model,
            "language_code": language_code,
            "format": format_mode,
        }

        async def _do_req(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                self.stt_url,
                headers=headers,
                files=files,
                data=data,
            )

        try:
            resp = await self._execute_with_lock_and_retry(_do_req, kind="stt", timeout=15.0)
            lat_ms = (time.monotonic() - t0) * 1000.0

            if resp.status_code == 200:
                try:
                    payload = resp.json()
                except Exception as json_err:
                    raise GnaniResponseError("STT response was not valid JSON") from json_err

                transcript = payload.get("transcript") or payload.get("text") or ""
                detected_lang = payload.get("detected_language_code") or payload.get("language") or language_code
                proc_time = float(payload.get("processing_time") or (lat_ms / 1000.0))

                usage_tracker.log_call(kind="stt", ok=True, latency_ms=lat_ms, cached=False)
                return {
                    "transcript": transcript,
                    "detected_language": detected_lang,
                    "processing_time": proc_time,
                    "mode": "live",
                }

            # Handle Typed Errors
            usage_tracker.log_call(kind="stt", ok=False, latency_ms=lat_ms, cached=False)

            if resp.status_code == 401:
                raise GnaniAuthError("Invalid or missing Gnani API key (401)")
            if resp.status_code == 402:
                raise GnaniCreditError("Insufficient Gnani account credits (402)")
            if resp.status_code == 403:
                raise GnaniScopeError("Access to STT model not permitted for this key (403)")
            if resp.status_code == 429:
                raise GnaniRateLimitError("Gnani rate limit reached (429)")
            if resp.status_code >= 500:
                raise GnaniServiceError(f"Gnani STT service error ({resp.status_code})", status_code=resp.status_code)

            raise GnaniRestError(f"STT request failed with status {resp.status_code}", status_code=resp.status_code)

        except Exception:
            lat_ms = (time.monotonic() - t0) * 1000.0
            usage_tracker.log_call(kind="stt", ok=False, latency_ms=lat_ms, cached=False)
            raise

    async def text_to_speech(
        self,
        text: str,
        voice: str = "Poorvi",
        model: str = "timbre-v2.5",
        language: str = "hi-en",
        speed: float = 1.0,
        sample_rate: int = 16000,
    ) -> tuple[bytes, bool, str]:
        """
        Synthesize text to speech via Gnani Timbre REST API.
        Cache-first: Returns (wav_bytes, was_cached, mode).
        """
        t0 = time.monotonic()
        cache_key = tts_cache.compute_key(
            text=text,
            voice=voice,
            model=model,
            language=language,
            speed=speed,
            sample_rate=sample_rate,
        )

        # 1. Check disk cache first (never hits lock or external network)
        cached_bytes = tts_cache.get(cache_key)
        if cached_bytes is not None:
            lat_ms = (time.monotonic() - t0) * 1000.0
            usage_tracker.log_call(kind="tts", ok=True, latency_ms=lat_ms, cached=True)
            return cached_bytes, True, "live"

        # 2. Offline Dry-Run Mode
        if self._is_dry_run():
            await asyncio.sleep(0.04)
            syn_bytes = generate_synthetic_wav(duration_ms=1800, sample_rate=sample_rate)
            # Store in cache
            tts_cache.put(cache_key, syn_bytes)
            lat_ms = (time.monotonic() - t0) * 1000.0
            usage_tracker.log_call(kind="tts", ok=True, latency_ms=lat_ms, cached=False)
            return syn_bytes, False, "dry_run"

        # 3. Live External Call
        headers = {
            "X-API-Key-ID": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "voice": voice,
            "model": model,
            "language": language,
            "speed": speed,
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

        async def _do_req(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                self.tts_url,
                headers=headers,
                json=body,
            )

        try:
            resp = await self._execute_with_lock_and_retry(_do_req, kind="tts", timeout=20.0)
            lat_ms = (time.monotonic() - t0) * 1000.0

            if resp.status_code == 200:
                audio_bytes = resp.content
                if not audio_bytes:
                    raise GnaniResponseError("TTS returned empty audio response")

                # Cache newly synthesized audio
                tts_cache.put(cache_key, audio_bytes)
                usage_tracker.log_call(kind="tts", ok=True, latency_ms=lat_ms, cached=False)
                return audio_bytes, False, "live"

            # Handle Typed Errors
            usage_tracker.log_call(kind="tts", ok=False, latency_ms=lat_ms, cached=False)
            if resp.status_code == 401:
                raise GnaniAuthError("Invalid or missing Gnani API key (401)")
            if resp.status_code == 402:
                raise GnaniCreditError("Insufficient Gnani account credits (402)")
            if resp.status_code == 403:
                raise GnaniScopeError("Access to TTS model not permitted for this key (403)")
            if resp.status_code == 429:
                raise GnaniRateLimitError("Gnani rate limit reached (429)")
            if resp.status_code >= 500:
                raise GnaniServiceError(f"Gnani TTS service error ({resp.status_code})", status_code=resp.status_code)

            raise GnaniRestError(f"TTS request failed with status {resp.status_code}", status_code=resp.status_code)

        except Exception:
            lat_ms = (time.monotonic() - t0) * 1000.0
            usage_tracker.log_call(kind="tts", ok=False, latency_ms=lat_ms, cached=False)
            raise
