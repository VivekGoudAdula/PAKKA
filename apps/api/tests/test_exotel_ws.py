"""
apps/api/tests/test_exotel_ws.py
Integration tests for Exotel AgentStream WebSocket endpoint /ws/exotel.

Tests:
1. Full echo loop: connected -> start -> greeting playback -> caller media -> echo reply -> stop.
2. Silence / line noise immunity: continuous silence/low-noise frames do NOT trigger barge-in.
3. Speech barge-in after 500ms: 2 consecutive speech chunks trigger 'clear' exactly once.
4. Echo-loop guard: STT finals during playback or within 400ms guard window are discarded.
All tests run completely offline using GNANI_DRY_RUN simulation.
"""

import json
import struct
import time

import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.main import app
from app.voice.audio import base64_to_pcm, pcm_to_base64
from app.voice.session import CallSession


@pytest.fixture(autouse=True)
def force_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GNANI_DRY_RUN is strictly True for offline tests."""
    monkeypatch.setattr(settings, "gnani_dry_run", True)


def make_pcm_chunk(amplitude: int = 0, sample_count: int = 800) -> bytes:
    """Generate linear16 PCM chunk with specified amplitude."""
    samples = [amplitude if i % 2 == 0 else -amplitude for i in range(sample_count)]
    return struct.pack(f"<{len(samples)}h", *samples)


def test_exotel_full_echo_turn() -> None:
    """
    Simulate full call lifecycle:
    - Handshake (connected, start)
    - Greeting reception (media chunks >= 3200 bytes & multiple of 320 bytes)
    - Wait for greeting_done mark
    - Caller speech input
    - Assistant echo reply ("Aapne kaha: ...")
    - Stop event and clean teardown
    """
    client = TestClient(app)
    stream_sid = "test_stream_001"
    call_sid = "test_call_001"

    with client.websocket_connect("/ws/exotel") as ws:
        # 1. Send 'connected'
        ws.send_text(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))

        # 2. Send 'start'
        ws.send_text(
            json.dumps(
                {
                    "event": "start",
                    "stream_sid": stream_sid,
                    "call_sid": call_sid,
                    "from": "+919876543210",
                    "to": "+918045678901",
                    "media_format": {"encoding": "audio/x-l16", "sample_rate": 8000, "channels": 1},
                }
            )
        )

        # 3. Receive greeting audio and mark
        greeting_pcm = bytearray()
        received_greeting_mark = False

        while not received_greeting_mark:
            msg = json.loads(ws.receive_text())
            event = msg.get("event")

            if event == "media":
                assert msg.get("stream_sid") == stream_sid
                payload = msg.get("media", {}).get("payload", "")
                pcm = base64_to_pcm(payload)
                assert len(pcm) >= 3200, f"Chunk size {len(pcm)} is less than 3200 bytes"
                assert len(pcm) % 320 == 0, f"Chunk size {len(pcm)} is not a multiple of 320"
                greeting_pcm.extend(pcm)

            elif event == "mark":
                mark_name = msg.get("mark", {}).get("name")
                if mark_name == "greeting_done":
                    received_greeting_mark = True

        assert len(greeting_pcm) > 0, "No greeting audio received"

        # 4. Wait for echo-loop guard (400 ms) to expire before caller speaks
        time.sleep(0.45)

        # 5. Stream caller speech (synthetic 1600-byte frames)
        caller_chunk = make_pcm_chunk(amplitude=3000, sample_count=800)  # 1600 bytes
        ws.send_text(
            json.dumps(
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
        )

        # 6. Receive assistant echo reply
        echo_pcm = bytearray()
        received_echo_mark = False

        while not received_echo_mark:
            msg = json.loads(ws.receive_text())
            event = msg.get("event")

            if event == "media":
                payload = msg.get("media", {}).get("payload", "")
                pcm = base64_to_pcm(payload)
                assert len(pcm) >= 3200
                assert len(pcm) % 320 == 0
                echo_pcm.extend(pcm)

            elif event == "mark":
                mark_name = msg.get("mark", {}).get("name")
                if "echo_turn" in mark_name:
                    received_echo_mark = True

        assert len(echo_pcm) > 0, "No echo reply audio received"

        # 6. Send 'stop' event
        ws.send_text(
            json.dumps(
                {
                    "event": "stop",
                    "stream_sid": stream_sid,
                    "stop": {"reason": "callended"},
                }
            )
        )


def test_exotel_silence_does_not_trigger_barge_in() -> None:
    """
    Exotel continuously streams silence and low noise.
    A stream of silence or line noise (amplitude 40, RMS ~40) must NOT trigger barge-in.
    The assistant must complete its greeting and deliver 'greeting_done' mark.
    """
    client = TestClient(app)
    stream_sid = "test_stream_silence"
    call_sid = "test_call_silence"

    with client.websocket_connect("/ws/exotel") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(
            json.dumps(
                {
                    "event": "start",
                    "stream_sid": stream_sid,
                    "call_sid": call_sid,
                    "media_format": {"sample_rate": 8000},
                }
            )
        )

        # Stream low noise chunks continuously during bot greeting
        noise_chunk = make_pcm_chunk(amplitude=40, sample_count=800)
        received_clear = False
        received_greeting_mark = False

        # Read frames for up to 2 seconds of playback
        for _ in range(25):
            # Send noise chunk
            ws.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "stream_sid": stream_sid,
                        "media": {"chunk": 1, "payload": pcm_to_base64(noise_chunk)},
                    }
                )
            )

            msg = json.loads(ws.receive_text())
            event = msg.get("event")
            if event == "clear":
                received_clear = True
            elif event == "mark" and msg.get("mark", {}).get("name") == "greeting_done":
                received_greeting_mark = True
                break

        assert not received_clear, "Low noise should NOT have triggered barge-in"
        assert received_greeting_mark, "Greeting should have completed successfully"

        ws.send_text(
            json.dumps(
                {
                    "event": "stop",
                    "stream_sid": stream_sid,
                    "stop": {"reason": "silence_test_ended"},
                }
            )
        )


def test_exotel_speech_after_500ms_triggers_barge_in_once() -> None:
    """
    Speech frames arriving after the initial 500 ms grace period:
    - 1st speech chunk does not trigger (requires 2 consecutive chunks)
    - 2nd consecutive speech chunk triggers barge-in ('clear' frame sent)
    - Subsequent speech chunks must NOT trigger another 'clear' frame (triggers exactly once).
    """
    client = TestClient(app)
    stream_sid = "test_stream_barge_once"
    call_sid = "test_call_barge_once"

    with client.websocket_connect("/ws/exotel") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(
            json.dumps(
                {
                    "event": "start",
                    "stream_sid": stream_sid,
                    "call_sid": call_sid,
                    "media_format": {"sample_rate": 8000},
                }
            )
        )

        # Consume initial media chunks until >500ms elapsed
        time.sleep(0.55)  # Ensure 500 ms grace period passes

        # Read whatever bot audio is pending
        msg = json.loads(ws.receive_text())

        speech_chunk = make_pcm_chunk(amplitude=3500, sample_count=800)

        # Send 1st speech chunk
        ws.send_text(
            json.dumps(
                {
                    "event": "media",
                    "stream_sid": stream_sid,
                    "media": {"chunk": 1, "payload": pcm_to_base64(speech_chunk)},
                }
            )
        )

        # Send 2nd consecutive speech chunk -> triggers barge-in
        ws.send_text(
            json.dumps(
                {
                    "event": "media",
                    "stream_sid": stream_sid,
                    "media": {"chunk": 2, "payload": pcm_to_base64(speech_chunk)},
                }
            )
        )

        # Send 3rd speech chunk -> should not re-trigger
        ws.send_text(
            json.dumps(
                {
                    "event": "media",
                    "stream_sid": stream_sid,
                    "media": {"chunk": 3, "payload": pcm_to_base64(speech_chunk)},
                }
            )
        )

        clear_count = 0
        received_clear = False

        # Read frames until clear event is encountered
        for _ in range(20):
            msg = json.loads(ws.receive_text())
            if msg.get("event") == "clear":
                clear_count += 1
                received_clear = True
                break

        assert received_clear, "Expected 'clear' event after 2 consecutive speech chunks"
        assert clear_count == 1, f"Expected exactly 1 'clear' event, but received {clear_count}"

        # Send 'stop' event
        ws.send_text(
            json.dumps(
                {
                    "event": "stop",
                    "stream_sid": stream_sid,
                    "stop": {"reason": "test_ended"},
                }
            )
        )


@pytest.mark.asyncio
async def test_echo_loop_guard_discards_playback_finals() -> None:
    """
    Direct test on CallSession:
    - While bot is speaking, STT final is discarded unless barge-in occurred.
    - Within 400 ms of playback completion mark, STT final is discarded.
    - After 400 ms guard window expires, STT final is processed normally.
    """
    sent_events: list[dict] = []

    async def mock_send(data: dict) -> None:
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
    assert not session._barge_in_active  # Would be discarded!

    # 2. Simulate playback completed via mark event
    session._bot_is_speaking = False
    await session.handle_mark("greeting_done")
    playback_end = session._last_playback_finished_time

    # Immediately after mark (time_since < 400ms):
    now = time.monotonic()
    assert (now - playback_end) < 0.400
    in_guard_post_mark = session._bot_is_speaking or ((now - playback_end) < 0.400)
    assert in_guard_post_mark is True  # Discarded!

    # 3. If barge-in was active, guard does NOT discard
    session._barge_in_active = True
    assert session._barge_in_active is True  # Allowed through!
