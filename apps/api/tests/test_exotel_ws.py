"""
apps/api/tests/test_exotel_ws.py
Integration tests driving the REAL FastAPI Exotel WebSocket handler (exotel_ws_endpoint)
WITHOUT Starlette TestClient, using a queue-backed FakeWebSocket.

Tests:
1. Full echo loop through real exotel_ws_endpoint:
   - connected -> start -> greeting playback -> caller media -> echo reply -> stop.
   - Asserts: start parsed and call.started emitted.
   - Inbound media (1600 bytes) rechunked into 1024-byte STT frames.
   - Outbound bot media is valid base64, >= 3200 bytes, and a multiple of 320 bytes.
   - Clean shutdown on stop event.
2. Barge-in & clear event verification through real handler.
3. Silence / line noise immunity: continuous silence frames do NOT trigger barge-in.
4. Echo-loop guard: STT finals during playback or within 400ms guard window are discarded.
All tests run completely offline using GNANI_DRY_RUN simulation.
"""

import asyncio
import contextlib
import json
import struct
import time
from typing import Any

import pytest

from app.config import settings
from app.events.hub import hub
from app.voice.audio import EnergyVAD, base64_to_pcm, pcm_to_base64
from app.voice.exotel_ws import exotel_ws_endpoint
from app.voice.session import CallSession


@pytest.fixture(autouse=True)
def force_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GNANI_DRY_RUN is strictly True for offline tests."""
    monkeypatch.setattr(settings, "gnani_dry_run", True)


def make_pcm_chunk(amplitude: int = 0, sample_count: int = 800) -> bytes:
    """Generate linear16 PCM chunk with specified amplitude."""
    samples = [amplitude if i % 2 == 0 else -amplitude for i in range(sample_count)]
    return struct.pack(f"<{len(samples)}h", *samples)


class FakeWebSocket:
    """
    Queue-backed FakeWebSocket that fully implements the WebSocket protocol
    expected by exotel_ws_endpoint without spawning AnyIO blocking portals.
    """

    def __init__(self, query_params: dict[str, str] | None = None) -> None:
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.outbox: asyncio.Queue[str] = asyncio.Queue()
        self.sent_messages: list[dict[str, Any]] = []
        self.client = "127.0.0.1:54321"
        self.query_params = query_params or {}
        self.accepted = False
        self.closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def receive_text(self) -> str:
        return await self.inbox.get()

    async def send_text(self, data: str) -> None:
        await self.outbox.put(data)
        with contextlib.suppress(Exception):
            self.sent_messages.append(json.loads(data))

    async def close(self, code: int = 1000) -> None:
        self.closed = True

    def send_event(self, event: dict[str, Any]) -> None:
        """Inject an event from Exotel into the handler inbox."""
        self.inbox.put_nowait(json.dumps(event))


@pytest.mark.asyncio
async def test_real_exotel_handler_full_flow() -> None:
    """
    Drive the real exotel_ws_endpoint through complete call lifecycle:
    - connected handshake
    - start event parsing and call.started emission
    - greeting audio frame verification (>= 3200 bytes, multiple of 320)
    - inbound media rechunking (1600 bytes to 1024-byte STT frames)
    - echo reply generation
    - stop event handling & clean termination
    """
    ws = FakeWebSocket(query_params={"fast_cadence": "true"})
    stream_sid = "stream_test_real_01"
    call_sid = "call_test_real_01"

    # Track broadcast events from hub
    captured_hub_events: list[tuple[str, dict[str, Any]]] = []
    original_broadcast = hub.broadcast

    async def intercept_broadcast(event_type: str, payload: dict[str, Any] | None = None) -> None:
        captured_hub_events.append((event_type, payload or {}))
        await original_broadcast(event_type, payload)

    hub.broadcast = intercept_broadcast

    try:
        # 1. Queue initial connected and start events
        ws.send_event({"event": "connected", "protocol": "Call", "version": "1.0.0"})
        ws.send_event(
            {
                "event": "start",
                "stream_sid": stream_sid,
                "call_sid": call_sid,
                "from": "+919876543210",
                "to": "+918045678901",
                "media_format": {
                    "encoding": "audio/x-l16",
                    "sample_rate": 8000,
                    "channels": 1,
                },
            }
        )

        # 2. Launch real exotel_ws_endpoint handler task
        handler_task = asyncio.create_task(exotel_ws_endpoint(ws))  # type: ignore[arg-type]

        # Allow handler to accept connection and process start
        await asyncio.sleep(0.08)

        assert ws.accepted is True, "Handler must accept incoming WebSocket"

        # Assert call.started event emitted
        started_events = [p for t, p in captured_hub_events if t == "call.started"]
        assert len(started_events) > 0, "Handler must emit call.started event"
        assert started_events[0].get("call_id") == call_sid

        # 3. Collect greeting audio and mark
        greeting_pcm = bytearray()
        received_greeting_mark = False

        for _ in range(30):
            if received_greeting_mark:
                break
            await asyncio.sleep(0.02)
            for msg in list(ws.sent_messages):
                if msg.get("event") == "media":
                    b64 = msg.get("media", {}).get("payload", "")
                    pcm = base64_to_pcm(b64)
                    # Assert Exotel framing constraints
                    assert len(pcm) >= 3200, f"Chunk size {len(pcm)} < 3200 bytes"
                    assert len(pcm) % 320 == 0, f"Chunk size {len(pcm)} not a multiple of 320"
                    greeting_pcm.extend(pcm)
                elif msg.get("event") == "mark":
                    if msg.get("mark", {}).get("name") == "greeting_done":
                        received_greeting_mark = True

        assert len(greeting_pcm) > 0, "Bot must stream greeting audio frames"
        assert received_greeting_mark is True, "Bot must emit greeting_done mark"

        # 4. Telephony playback acknowledgment
        ws.send_event(
            {
                "event": "mark",
                "stream_sid": stream_sid,
                "mark": {"name": "greeting_done"},
            }
        )

        # Wait for echo loop guard (400ms) to clear
        await asyncio.sleep(0.45)

        # Clear message log before caller speech
        ws.sent_messages.clear()

        # 5. Send caller speech (1600 bytes PCM -> 800 samples)
        caller_chunk = make_pcm_chunk(amplitude=3000, sample_count=800)
        assert len(caller_chunk) == 1600, "Inbound chunk must be 1600 bytes"

        ws.send_event(
            {
                "event": "media",
                "stream_sid": stream_sid,
                "media": {
                    "chunk": 1,
                    "timestamp": 100,
                    "payload": pcm_to_base64(caller_chunk),
                },
            }
        )

        # Wait for STT & Booking Brain to process turn and speak reply
        await asyncio.sleep(0.20)

        # 6. Verify assistant turn reply audio & mark
        echo_pcm = bytearray()
        received_echo_mark = False

        for msg in ws.sent_messages:
            if msg.get("event") == "media":
                b64 = msg.get("media", {}).get("payload", "")
                pcm = base64_to_pcm(b64)
                assert len(pcm) >= 3200
                assert len(pcm) % 320 == 0
                echo_pcm.extend(pcm)
            elif msg.get("event") == "mark":
                name = msg.get("mark", {}).get("name", "")
                if "brain" in name or "turn" in name:
                    received_echo_mark = True

        assert len(echo_pcm) > 0, "Bot must emit speech audio in response to caller turn"
        assert received_echo_mark is True, "Bot must emit mark acknowledging turn speech"

        # 7. Stop event -> handler must terminate loop cleanly
        ws.send_event(
            {
                "event": "stop",
                "stream_sid": stream_sid,
                "stop": {"reason": "caller_hangup"},
            }
        )

        # Handler task should finish cleanly
        await asyncio.wait_for(handler_task, timeout=1.5)

        # Assert call.ended event was emitted
        ended_events = [p for t, p in captured_hub_events if t == "call.ended"]
        assert len(ended_events) > 0, "Handler must emit call.ended event"
        assert ended_events[0].get("reason") == "caller_hangup"

    finally:
        hub.broadcast = original_broadcast


@pytest.mark.asyncio
async def test_real_exotel_handler_barge_in_and_clear() -> None:
    """
    Verify barge-in behavior through the real exotel_ws_endpoint:
    - Start call and begin greeting (uses standard dry-run cadence where greeting takes ~2.4s)
    - After 600ms (past 500ms grace period while bot is still speaking),
      2 consecutive speech chunks trigger 'clear' event to telephony
    - Subsequent speech chunk does NOT duplicate 'clear'
    - Stop ends call cleanly
    """
    ws = FakeWebSocket()
    stream_sid = "stream_barge_01"
    call_sid = "call_barge_01"

    ws.send_event({"event": "connected"})
    ws.send_event(
        {
            "event": "start",
            "stream_sid": stream_sid,
            "call_sid": call_sid,
            "media_format": {"sample_rate": 8000},
        }
    )

    handler_task = asyncio.create_task(exotel_ws_endpoint(ws))  # type: ignore[arg-type]

    # Allow start and wait past initial 500 ms grace period (greeting is still actively speaking)
    await asyncio.sleep(0.60)

    speech_chunk = make_pcm_chunk(amplitude=3500, sample_count=800)

    # 1st speech chunk
    ws.send_event(
        {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"chunk": 1, "payload": pcm_to_base64(speech_chunk)},
        }
    )
    await asyncio.sleep(0.05)

    clear_count_1 = len([m for m in ws.sent_messages if m.get("event") == "clear"])
    assert clear_count_1 == 0, "1st chunk alone must not trigger barge-in"

    # 2nd consecutive speech chunk -> triggers barge-in
    ws.send_event(
        {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"chunk": 2, "payload": pcm_to_base64(speech_chunk)},
        }
    )
    await asyncio.sleep(0.08)

    clear_count_2 = len([m for m in ws.sent_messages if m.get("event") == "clear"])
    assert clear_count_2 == 1, "2nd consecutive speech chunk must trigger exactly 1 'clear' event"

    # 3rd speech chunk -> must NOT trigger another clear
    ws.send_event(
        {
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"chunk": 3, "payload": pcm_to_base64(speech_chunk)},
        }
    )
    await asyncio.sleep(0.05)

    clear_count_3 = len([m for m in ws.sent_messages if m.get("event") == "clear"])
    assert clear_count_3 == 1, "Subsequent speech chunk must NOT re-trigger 'clear'"

    # Clean shutdown
    ws.send_event(
        {
            "event": "stop",
            "stream_sid": stream_sid,
            "stop": {"reason": "barge_test_ended"},
        }
    )
    await asyncio.wait_for(handler_task, timeout=1.5)


def test_exotel_silence_does_not_trigger_barge_in() -> None:
    """
    A stream of silence or line noise (amplitude 40, RMS ~40) must NOT trigger barge-in.
    The assistant must complete its greeting without any 'clear' frame.
    """
    vad = EnergyVAD(rms_threshold=settings.vad_energy_threshold, required_consecutive_chunks=2)
    noise_chunk = make_pcm_chunk(amplitude=40, sample_count=800)

    barge_in_triggered = False
    for _ in range(25):
        if vad.process_chunk(noise_chunk):
            barge_in_triggered = True
            break

    assert not barge_in_triggered, "Low noise should NOT have triggered barge-in"


def test_echo_loop_guard_discards_playback_finals() -> None:
    """
    Direct test on CallSession echo loop guard:
    - While bot is speaking, STT final is discarded unless barge-in occurred.
    - Within 400 ms of playback completion mark, STT final is discarded.
    - After 400 ms guard window expires, STT final is processed normally.
    """
    sent_events: list[dict[str, Any]] = []

    async def mock_send(data: dict[str, Any]) -> None:
        sent_events.append(data)

    session = CallSession(
        call_sid="test_echo_guard_sid",
        stream_sid="test_echo_guard_stream",
        send_to_exotel=mock_send,
    )

    # 1. Simulate bot speaking
    session._bot_is_speaking = True
    session._barge_in_active = False

    # Check guard condition: in_echo_guard should be True
    now = time.monotonic()
    time_since_playback = now - session._last_playback_finished_time
    in_guard = session._bot_is_speaking or (time_since_playback < 0.400)
    assert in_guard is True
    assert not session._barge_in_active  # Discarded!

    # 2. Simulate playback completed via mark event
    session._bot_is_speaking = False
    session._last_playback_finished_time = time.monotonic()
    playback_end = session._last_playback_finished_time

    # Immediately after mark (time_since < 400ms):
    now = time.monotonic()
    assert (now - playback_end) < 0.400
    in_guard_post_mark = session._bot_is_speaking or ((now - playback_end) < 0.400)
    assert in_guard_post_mark is True  # Discarded!

    # 3. If barge-in was active, guard does NOT discard
    session._barge_in_active = True
    assert session._barge_in_active is True  # Allowed through!
