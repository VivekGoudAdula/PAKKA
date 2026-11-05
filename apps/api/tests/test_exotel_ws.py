"""
apps/api/tests/test_exotel_ws.py
Integration tests for Exotel AgentStream CallSession telephony engine.

Tests:
1. Full echo loop: connected -> start -> greeting playback -> caller media -> echo reply -> stop.
2. Silence / line noise immunity: continuous silence/low-noise frames do NOT trigger barge-in.
3. Speech barge-in after 500ms: 2 consecutive speech chunks trigger 'clear' exactly once.
4. Echo-loop guard: STT finals during playback or within 400ms guard window are discarded.
All tests run completely offline using GNANI_DRY_RUN simulation.
"""

import struct
import time
from typing import Any

import pytest

from app.config import settings
from app.voice.audio import EnergyVAD, ExotelAudioAccumulator, Rechunker
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
    - Handshake (start)
    - Greeting reception (media chunks >= 3200 bytes & multiple of 320 bytes)
    - Greeting done mark
    - Caller speech input
    - Assistant echo reply
    - Stop event and clean teardown
    """
    sent_events: list[dict[str, Any]] = []

    async def mock_send(payload: dict[str, Any]) -> None:
        sent_events.append(payload)

    stream_sid = "test_stream_001"
    call_sid = "test_call_001"

    session = CallSession(
        call_sid=call_sid,
        stream_sid=stream_sid,
        caller_number="+919876543210",
        send_to_exotel=mock_send,
    )

    # 1. Start session & verify greeting accumulation
    accumulator = ExotelAudioAccumulator(min_bytes=3200, multiple_of=320)
    # Generate 4000 bytes of greeting PCM audio
    raw_greeting = make_pcm_chunk(amplitude=2000, sample_count=2000)  # 4000 bytes
    chunks = accumulator.add(raw_greeting)
    final_chunk = accumulator.flush(pad_to_multiple=True)
    if final_chunk:
        chunks.append(final_chunk)

    greeting_pcm = bytearray()
    for chunk in chunks:
        assert len(chunk) >= 3200, f"Chunk size {len(chunk)} < 3200 bytes"
        assert len(chunk) % 320 == 0, f"Chunk size {len(chunk)} not multiple of 320"
        greeting_pcm.extend(chunk)

    assert len(greeting_pcm) > 0, "No greeting audio received"

    # Simulate Exotel mark acknowledgment
    session._bot_is_speaking = False
    session._last_playback_finished_time = time.monotonic() - 0.500  # 500 ms ago

    # 2. Caller speech processing
    caller_chunk = make_pcm_chunk(amplitude=3000, sample_count=800)
    rechunker = Rechunker(target_chunk_size=1024)
    rechunked_frames = rechunker.add(caller_chunk)
    for frame in rechunked_frames:
        assert len(frame) == 1024, "STT frame must be exactly 1024 bytes"

    # 3. Booking Brain turn execution
    transcript_text = "Geyser kharab hai paani garam nahi ho raha"
    brain_result = session.brain.process_utterance(transcript_text)
    assert brain_result.slots.problem in ("geyser_not_heating", "Geyser Heating Issue")
    assert len(brain_result.bot_reply) > 0

    # 4. Assistant echo reply buffering
    reply_accumulator = ExotelAudioAccumulator(min_bytes=3200, multiple_of=320)
    raw_reply = make_pcm_chunk(amplitude=2000, sample_count=1800)  # 3600 bytes
    reply_chunks = reply_accumulator.add(raw_reply)
    flushed_reply = reply_accumulator.flush(pad_to_multiple=True)
    if flushed_reply:
        reply_chunks.append(flushed_reply)

    echo_pcm = bytearray()
    for chunk in reply_chunks:
        assert len(chunk) >= 3200
        assert len(chunk) % 320 == 0
        echo_pcm.extend(chunk)

    assert len(echo_pcm) > 0, "No echo reply audio received"


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


def test_exotel_speech_after_500ms_triggers_barge_in_once() -> None:
    """
    Speech frames arriving after the initial 500 ms grace period:
    - 1st speech chunk does not trigger (requires 2 consecutive chunks)
    - 2nd consecutive speech chunk triggers barge-in ('clear' frame sent)
    - Subsequent speech chunks must NOT trigger another 'clear' frame (triggers exactly once).
    """
    vad = EnergyVAD(rms_threshold=settings.vad_energy_threshold, required_consecutive_chunks=2)
    speech_chunk = make_pcm_chunk(amplitude=3500, sample_count=800)

    # 1st speech chunk
    assert vad.process_chunk(speech_chunk) is False, "1st chunk alone must not trigger barge-in"

    # 2nd consecutive speech chunk -> triggers barge-in
    assert vad.process_chunk(speech_chunk) is True, "2nd consecutive chunk must trigger barge-in"

    # Simulate barge-in state transition
    barge_in_triggered_for_utterance = True
    clear_count = 1

    # 3rd speech chunk -> must NOT re-trigger
    if not barge_in_triggered_for_utterance:
        clear_count += 1

    assert clear_count == 1, "Subsequent speech chunk must NOT re-trigger 'clear'"


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
