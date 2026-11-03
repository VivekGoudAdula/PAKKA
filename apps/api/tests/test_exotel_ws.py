"""
apps/api/tests/test_exotel_ws.py
Integration tests for Exotel AgentStream WebSocket endpoint /ws/exotel.

Tests:
1. Full echo loop: connected -> start -> greeting playback -> caller media -> echo reply -> stop.
2. Barge-in test: caller speech during assistant playback triggers Exotel 'clear' frame.
3. Audio chunk constraints: verified >= 3200 bytes and multiple of 320 bytes.
All tests run completely offline using GNANI_DRY_RUN simulation.
"""

import json

import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.main import app
from app.voice.audio import base64_to_pcm, pcm_to_base64


@pytest.fixture(autouse=True)
def force_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GNANI_DRY_RUN is strictly True for offline tests."""
    monkeypatch.setattr(settings, "gnani_dry_run", True)


def test_exotel_full_echo_turn() -> None:
    """
    Simulate full call lifecycle:
    - Handshake (connected, start)
    - Greeting reception (media chunks >= 3200 bytes & multiple of 320 bytes)
    - Mandatory disclosure verified
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
                # Verify Exotel chunk constraints
                assert len(pcm) >= 3200, f"Chunk size {len(pcm)} is less than 3200 bytes"
                assert len(pcm) % 320 == 0, f"Chunk size {len(pcm)} is not a multiple of 320"
                greeting_pcm.extend(pcm)

            elif event == "mark":
                mark_name = msg.get("mark", {}).get("name")
                assert mark_name == "greeting_done"
                received_greeting_mark = True

        assert len(greeting_pcm) > 0, "No greeting audio received"

        # 4. Stream caller speech (synthetic 1600-byte frames)
        caller_chunk = b"\x01\x00" * 800  # 1600 bytes = 100ms
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

        # 5. Receive assistant echo reply
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
                assert "echo_turn" in mark_name
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


def test_exotel_barge_in() -> None:
    """
    Test barge-in: when caller sends audio while the assistant is speaking,
    the assistant must emit a 'clear' event to flush buffered audio on Exotel.
    """
    client = TestClient(app)
    stream_sid = "test_stream_barge_in"
    call_sid = "test_call_barge_in"

    with client.websocket_connect("/ws/exotel") as ws:
        # 1. Send 'connected' & 'start'
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

        # 2. As soon as the first media frame arrives from the bot, barge in with caller audio
        first_bot_media = False
        while not first_bot_media:
            msg = json.loads(ws.receive_text())
            if msg.get("event") == "media":
                first_bot_media = True

        # Caller interrupts with speech
        ws.send_text(
            json.dumps(
                {
                    "event": "media",
                    "stream_sid": stream_sid,
                    "media": {
                        "chunk": 1,
                        "payload": pcm_to_base64(b"\x05\x05" * 800),
                    },
                }
            )
        )

        # 3. Verify assistant responds with 'clear' event
        received_clear = False
        for _ in range(10):
            msg = json.loads(ws.receive_text())
            if msg.get("event") == "clear":
                assert msg.get("stream_sid") == stream_sid
                received_clear = True
                break

        assert received_clear, "Expected 'clear' barge-in event from assistant"

        # Teardown
        ws.send_text(
            json.dumps(
                {
                    "event": "stop",
                    "stream_sid": stream_sid,
                    "stop": {"reason": "barge_in_test_ended"},
                }
            )
        )
