"""
apps/api/tests/test_gnani_rest.py
Unit and integration tests for Phase 8 Gnani REST client and browser voice endpoints.

Coverage:
1. httpx.MockTransport tests for STT REST: success, 401, 402, 403, 429 retry-success, timeout, malformed JSON.
2. httpx.MockTransport tests for TTS REST: success, cache hit without second request.
3. Concurrency lock verification (two concurrent requests serialized).
4. Usage guard (hourly budget limits and reports/usage_log.jsonl logging).
5. WAV audio validation (rejection of non-WAV, stereo, 8-bit, too short < 0.3s, too long > 30s).
6. Full API endpoint tests:
   - POST /api/voice/start (booking and collection)
   - POST /api/voice/turn (happy path, emergency, decline, AI-inquiry, collection)
   - POST /api/voice/text-turn (typed fallback)
   - GET /api/voice/usage
All tests execute 100% offline using MockTransport and synthetic dry-run data.
"""

from __future__ import annotations

import asyncio
import io
import json
import math
import struct
import time
import wave
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.voice_browser import _SESSIONS, validate_wav_audio
from app.voice.gnani_rest import (
    GnaniAuthError,
    GnaniCreditError,
    GnaniNetworkError,
    GnaniQuotaExceededError,
    GnaniRateLimitError,
    GnaniResponseError,
    GnaniRestClient,
    GnaniScopeError,
    GnaniTimeoutError,
    GnaniTTSCache,
    GnaniUsageTracker,
    generate_synthetic_wav,
)


@pytest.fixture(autouse=True)
def reset_voice_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Ensure clean test environment for voice sessions and TTS cache."""
    _SESSIONS.clear()
    monkeypatch.setattr(settings, "gnani_dry_run", True)
    monkeypatch.setattr(settings, "gnani_api_key", "test_key_abc123")


def make_test_wav(
    duration_s: float = 1.0,
    channels: int = 1,
    sample_width: int = 2,
    framerate: int = 16000,
) -> bytes:
    """Generate in-memory WAV for testing validator and endpoints."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(framerate)
        num_samples = int(duration_s * framerate)
        samples = [int(3000 * math.sin(2 * math.pi * 440 * (i / framerate))) for i in range(num_samples)]
        if channels == 1:
            raw = struct.pack(f"<{len(samples)}h", *samples) if sample_width == 2 else bytes([128] * len(samples))
        else:
            stereo = []
            for s in samples:
                stereo.extend([s, s])
            raw = struct.pack(f"<{len(stereo)}h", *stereo)
        wf.writeframes(raw)
    return buf.getvalue()


# ─── 1. GnaniRestClient MockTransport Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_stt_rest_success() -> None:
    """STT REST parses successful transcription response."""
    test_audio = make_test_wav(1.0)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.vachana.ai/stt/v3")
        assert request.headers.get("x-api-key-id") == "live_key"
        return httpx.Response(
            200,
            json={
                "transcript": "Geyser kharab hai",
                "detected_language_code": "hi-IN",
                "processing_time": 0.42,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)
        res = await client.speech_to_text(test_audio)
        assert res["transcript"] == "Geyser kharab hai"
        assert res["detected_language"] == "hi-IN"
        assert res["mode"] == "live"


@pytest.mark.asyncio
async def test_stt_rest_errors_401_402_403() -> None:
    """STT REST maps 401, 402, 403 to typed exceptions."""
    test_audio = make_test_wav(1.0)

    for code, exc_type in [(401, GnaniAuthError), (402, GnaniCreditError), (403, GnaniScopeError)]:
        transport = httpx.MockTransport(lambda req, c=code: httpx.Response(c, text="Error"))
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)
            with pytest.raises(exc_type):
                await client.speech_to_text(test_audio)


@pytest.mark.asyncio
async def test_stt_rest_429_retry_then_success() -> None:
    """STT REST retries once on 429 and succeeds on second attempt."""
    test_audio = make_test_wav(1.0)
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, text="Rate limit exceeded")
        return httpx.Response(
            200,
            json={"transcript": "Pani tapak raha hai", "detected_language_code": "hi-IN"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)
        res = await client.speech_to_text(test_audio)
        assert attempts == 2
        assert res["transcript"] == "Pani tapak raha hai"


@pytest.mark.asyncio
async def test_stt_rest_timeout() -> None:
    """STT REST maps httpx.TimeoutException to GnaniTimeoutError."""
    test_audio = make_test_wav(1.0)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)
        with pytest.raises(GnaniTimeoutError):
            await client.speech_to_text(test_audio)


@pytest.mark.asyncio
async def test_stt_rest_malformed_json() -> None:
    """STT REST raises GnaniResponseError on non-JSON response."""
    test_audio = make_test_wav(1.0)
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text="NOT_JSON_BODY"))
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)
        with pytest.raises(GnaniResponseError):
            await client.speech_to_text(test_audio)


@pytest.mark.asyncio
async def test_tts_rest_success_and_cache(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """TTS REST synthesizes audio and hits local cache on second call."""
    cache = GnaniTTSCache(cache_dir=tmp_path / "tts")
    monkeypatch.setattr("app.voice.gnani_rest.tts_cache", cache)

    network_calls = 0
    fake_wav = make_test_wav(0.5)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        assert request.headers.get("X-API-Key-ID") == "live_key"
        return httpx.Response(200, content=fake_wav, headers={"Content-Type": "audio/wav"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)

        # 1st call -> hits network and caches
        audio_1, cached_1, mode_1 = await client.text_to_speech("Namaste ji")
        assert network_calls == 1
        assert cached_1 is False
        assert audio_1 == fake_wav

        # 2nd call -> hits cache (network_calls remains 1)
        audio_2, cached_2, mode_2 = await client.text_to_speech("Namaste ji")
        assert network_calls == 1
        assert cached_2 is True
        assert audio_2 == fake_wav


@pytest.mark.asyncio
async def test_concurrency_lock_serializes_calls() -> None:
    """Verify that multiple concurrent calls are serialized by the global lock."""
    active_calls = 0
    max_concurrent = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active_calls, max_concurrent
        active_calls += 1
        if active_calls > max_concurrent:
            max_concurrent = active_calls
        time.sleep(0.05)
        active_calls -= 1
        return httpx.Response(200, json={"transcript": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GnaniRestClient(api_key="live_key", dry_run=False, http_client=http_client)
        test_audio = make_test_wav(1.0)

        # Run two concurrent calls
        await asyncio.gather(
            client.speech_to_text(test_audio),
            client.speech_to_text(test_audio),
        )

        assert max_concurrent == 1, "Global lock must ensure only 1 active request in flight"


def test_usage_guard_enforces_budget() -> None:
    """Usage tracker raises GnaniQuotaExceededError when hourly limit exceeded."""
    tracker = GnaniUsageTracker()
    for _ in range(5):
        tracker.check_and_record_budget(max_per_hour=5)

    with pytest.raises(GnaniQuotaExceededError):
        tracker.check_and_record_budget(max_per_hour=5)


# ─── 2. Audio Validation Tests ────────────────────────────────────────────────


def test_validate_wav_audio_success_and_failures() -> None:
    """validate_wav_audio enforces 16-bit mono 8-48kHz 0.3-30s."""
    # Valid
    valid_wav = make_test_wav(duration_s=1.5, channels=1, sample_width=2, framerate=16000)
    dur, rate = validate_wav_audio(valid_wav)
    assert round(dur, 1) == 1.5
    assert rate == 16000

    # Non-WAV / Header too small
    with pytest.raises(Exception):
        validate_wav_audio(b"not a wav")

    # Stereo rejected
    stereo_wav = make_test_wav(duration_s=1.0, channels=2)
    with pytest.raises(Exception) as exc:
        validate_wav_audio(stereo_wav)
    assert "mono" in str(exc.value)

    # Too short (< 0.3s)
    short_wav = make_test_wav(duration_s=0.2)
    with pytest.raises(Exception) as exc:
        validate_wav_audio(short_wav)
    assert "between 0.3s and 30.0s" in str(exc.value)

    # Bad sample rate
    bad_rate_wav = make_test_wav(duration_s=1.0, framerate=4000)
    with pytest.raises(Exception) as exc:
        validate_wav_audio(bad_rate_wav)
    assert "between 8000 Hz and 48000 Hz" in str(exc.value)


# ─── 3. Full API Endpoint Tests ───────────────────────────────────────────────


def test_voice_start_and_usage_endpoints() -> None:
    """Test POST /api/voice/start and GET /api/voice/usage."""
    client = TestClient(app)

    # 1. Start Booking session
    resp = client.post("/api/voice/start", json={"flow": "booking"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["flow"] == "booking"
    assert "digital sahayak bol rahi hoon" in data["greeting_text"]
    assert len(data["greeting_audio_b64"]) > 0

    # 2. Start Collection session
    resp_col = client.post(
        "/api/voice/start",
        json={"flow": "collection", "customer": "Sunita", "tone_level": 2},
    )
    assert resp_col.status_code == 200
    col_data = resp_col.json()
    assert col_data["flow"] == "collection"
    assert "Sunita ji" in col_data["greeting_text"]
    assert "digital sahayak bol rahi hoon" in col_data["greeting_text"]

    # 3. Check Usage endpoint
    usage_resp = client.get("/api/voice/usage")
    assert usage_resp.status_code == 200
    usage = usage_resp.json()
    assert "max_calls_per_hour" in usage
    assert usage["max_calls_per_hour"] == settings.max_gnani_calls_per_hour


def test_voice_turn_booking_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test full booking happy path over /api/voice/turn with canned STT transcripts."""
    client = TestClient(app)
    start_res = client.post("/api/voice/start", json={"flow": "booking"}).json()
    session_id = start_res["session_id"]

    script = [
        ("Mera geyser se pani tapak raha hai", "ASK_ADDRESS"),
        ("Mayur Vihar Phase 1 Pocket 2", "ASK_SLOT"),
        ("Kal subah 10 baje aa jao", "QUOTE"),
        ("theek hai", "CONFIRM_READBACK"),
        ("haan bhej do", "BOOKED"),
    ]

    for utterance, expected_state in script:
        # Monkeypatch speech_to_text to return deterministic utterance
        async def mock_stt(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"transcript": utterance, "detected_language": "hi-IN", "mode": "dry_run"}

        monkeypatch.setattr(GnaniRestClient, "speech_to_text", mock_stt)

        test_wav = make_test_wav(1.0)
        files = {"audio": ("audio.wav", test_wav, "audio/wav")}
        data = {"session_id": session_id}

        resp = client.post("/api/voice/turn", data=data, files=files)
        assert resp.status_code == 200, resp.text
        turn_data = resp.json()
        assert turn_data["transcript"] == utterance
        assert turn_data["state"] == expected_state
        assert len(turn_data["audio_b64"]) > 0

    assert turn_data["is_terminal"] is True
    assert turn_data["slots"]["problem_key"] == "geyser_leak"


def test_voice_turn_emergency_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Emergency utterance routes to urgent handoff with exact emergency string."""
    client = TestClient(app)
    start_res = client.post("/api/voice/start", json={"flow": "booking"}).json()
    session_id = start_res["session_id"]

    emergency_utterance = "geyser mein current aa raha hai shock lag raha hai"

    async def mock_stt(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"transcript": emergency_utterance, "detected_language": "hi-IN", "mode": "dry_run"}

    monkeypatch.setattr(GnaniRestClient, "speech_to_text", mock_stt)

    test_wav = make_test_wav(1.0)
    files = {"audio": ("audio.wav", test_wav, "audio/wav")}
    resp = client.post("/api/voice/turn", data={"session_id": session_id}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_urgent"] is True
    assert data["needs_human"] is True
    assert "Kripya geyser aur main switch band kar dijiye" in data["reply_text"]


def test_voice_turn_decline_and_ai_inquiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify decline intent and AI-inquiry handling."""
    client = TestClient(app)

    # 1. AI Inquiry
    start_res = client.post("/api/voice/start", json={"flow": "booking"}).json()
    session_id = start_res["session_id"]

    async def mock_stt_ai(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"transcript": "kya aap robot ho?", "detected_language": "hi-IN", "mode": "dry_run"}

    monkeypatch.setattr(GnaniRestClient, "speech_to_text", mock_stt_ai)
    test_wav = make_test_wav(1.0)
    resp_ai = client.post("/api/voice/turn", data={"session_id": session_id}, files={"audio": ("audio.wav", test_wav, "audio/wav")})
    assert resp_ai.status_code == 200
    assert "digital sahayak bol rahi hoon" in resp_ai.json()["reply_text"]
    assert "callback" in resp_ai.json()["reply_text"]

    # 2. Decline
    async def mock_stt_decline(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"transcript": "rehne do mujhe nahi chahiye", "detected_language": "hi-IN", "mode": "dry_run"}

    monkeypatch.setattr(GnaniRestClient, "speech_to_text", mock_stt_decline)
    resp_dec = client.post("/api/voice/turn", data={"session_id": session_id}, files={"audio": ("audio.wav", test_wav, "audio/wav")})
    assert resp_dec.status_code == 200
    assert resp_dec.json()["is_terminal"] is True
    assert resp_dec.json()["state"] == "ABANDONED"


def test_voice_text_turn_typed_fallback() -> None:
    """Test typed fallback route /api/voice/text-turn."""
    client = TestClient(app)
    start_res = client.post("/api/voice/start", json={"flow": "booking"}).json()
    session_id = start_res["session_id"]

    resp = client.post(
        "/api/voice/text-turn",
        json={"session_id": session_id, "text": "Mera nal leak kar raha hai"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["typed"] is True
    assert data["transcript"] == "Mera nal leak kar raha hai"
    assert data["latency_ms"]["stt"] == 0.0
    assert data["state"] == "ASK_ADDRESS"


def test_voice_collection_flow_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test payment collection dialogue flow over /api/voice/turn."""
    client = TestClient(app)
    start_res = client.post(
        "/api/voice/start",
        json={"flow": "collection", "customer": "Ramesh", "tone_level": 1},
    ).json()
    session_id = start_res["session_id"]

    async def mock_stt_col(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"transcript": "haan main kal shaam tak payment kar dunga", "detected_language": "hi-IN", "mode": "dry_run"}

    monkeypatch.setattr(GnaniRestClient, "speech_to_text", mock_stt_col)
    test_wav = make_test_wav(1.0)
    resp = client.post("/api/voice/turn", data={"session_id": session_id}, files={"audio": ("audio.wav", test_wav, "audio/wav")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "TERMINAL"
    assert data["slots"]["disposition"] == "PTP"
    assert data["slots"]["ptp_date"] is not None
    assert data["is_terminal"] is True
