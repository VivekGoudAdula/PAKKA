"""
apps/api/tests/test_audio.py
Unit tests for audio processing primitives: Rechunker, ExotelAudioAccumulator,
PacedSender math, base64 helpers, and Hindi number phonetization.
"""

from app.voice.audio import (
    ExotelAudioAccumulator,
    PacedSender,
    Rechunker,
    base64_to_pcm,
    calculate_pcm_duration_ms,
    number_to_spoken_words,
    pcm_to_base64,
)


class TestRechunker:
    def test_rechunker_exact_1024_bytes(self) -> None:
        """Exotel delivers ~1600-byte chunks. Rechunker must only yield exact 1024-byte frames."""
        rechunker = Rechunker(target_chunk_size=1024)

        # Feed 1600 bytes
        chunk1 = b"\x01" * 1600
        frames1 = list(rechunker.add(chunk1))

        assert len(frames1) == 1
        assert len(frames1[0]) == 1024
        assert rechunker.buffered_bytes == 1600 - 1024  # 576 bytes

        # Feed another 1600 bytes -> total in buffer 576 + 1600 = 2176
        # -> two 1024 frames (2048) + 128 left
        chunk2 = b"\x02" * 1600
        frames2 = list(rechunker.add(chunk2))

        assert len(frames2) == 2
        assert len(frames2[0]) == 1024
        assert len(frames2[1]) == 1024
        assert rechunker.buffered_bytes == 128

        # Flush returns remaining 128 bytes
        rem = rechunker.flush()
        assert len(rem) == 128
        assert rechunker.buffered_bytes == 0

    def test_rechunker_never_short_frame(self) -> None:
        """Inputs smaller than target_chunk_size must yield nothing until threshold is reached."""
        rechunker = Rechunker(target_chunk_size=1024)
        for _ in range(10):
            frames = list(rechunker.add(b"\x00" * 100))
            assert len(frames) == 0

        assert rechunker.buffered_bytes == 1000

        # Adding 24 more bytes crosses 1024
        frames = list(rechunker.add(b"\x00" * 24))
        assert len(frames) == 1
        assert len(frames[0]) == 1024
        assert rechunker.buffered_bytes == 0


class TestExotelAudioAccumulator:
    def test_accumulator_min_and_multiple_constraints(self) -> None:
        """
        Exotel requires:
        - Chunk size at least 3200 bytes.
        - Chunk size EXACT multiple of 320 bytes.
        """
        accumulator = ExotelAudioAccumulator(min_bytes=3200, multiple_of=320, max_bytes=100000)

        # 1000 bytes: below minimum 3200, should not yield
        chunks1 = list(accumulator.add(b"\xaa" * 1000))
        assert len(chunks1) == 0

        # Feed 2500 bytes -> total 3500 bytes.
        # Greatest multiple of 320 <= 3500 is 320 * 10 = 3200 bytes.
        # Remainder = 300 bytes.
        chunks2 = list(accumulator.add(b"\xbb" * 2500))
        assert len(chunks2) == 1
        assert len(chunks2[0]) == 3200
        assert len(chunks2[0]) % 320 == 0
        assert accumulator.buffered_bytes == 300

    def test_accumulator_flush_padding(self) -> None:
        """Flushing trailing audio must pad up to minimum bytes and multiple of 320."""
        accumulator = ExotelAudioAccumulator(min_bytes=3200, multiple_of=320)
        accumulator.add(b"\x11" * 1500)

        # 1500 bytes flushed with padding
        flushed = accumulator.flush(pad_to_multiple=True)
        assert flushed is not None
        assert len(flushed) >= 3200
        assert len(flushed) % 320 == 0
        # 3200 is both >= 3200 and multiple of 320
        assert len(flushed) == 3200


class TestAudioPacingAndConversions:
    def test_pcm_duration_math(self) -> None:
        """Verify 8 kHz 16-bit mono duration calculations."""
        # 1600 bytes = 800 samples @ 8000 Hz = 0.1s = 100 ms
        assert calculate_pcm_duration_ms(1600, 8000) == 100.0
        # 1024 bytes = 512 samples @ 8000 Hz = 0.064s = 64 ms
        assert calculate_pcm_duration_ms(1024, 8000) == 64.0

    def test_base64_pcm_roundtrip(self) -> None:
        """Ensure byte-accurate Base64 encoding/decoding."""
        raw_pcm = bytes([i % 256 for i in range(1600)])
        b64 = pcm_to_base64(raw_pcm)
        recovered = base64_to_pcm(b64)
        assert recovered == raw_pcm

    def test_pacer_initialization(self) -> None:
        """PacedSender correctly initializes and resets."""
        pacer = PacedSender(sample_rate=8000)
        assert pacer.sample_rate == 8000
        assert pacer._next_send_time is None
        pacer.reset()
        assert pacer._next_send_time is None


class TestNumberToSpokenWords:
    def test_spoken_hindi_numbers(self) -> None:
        """Test numbers converted to spoken Hindi words for TTS."""
        assert number_to_spoken_words(0) == "zero"
        assert number_to_spoken_words(5) == "paanch"
        assert number_to_spoken_words(10) == "das"
        assert number_to_spoken_words(15) == "pandrah"
        assert number_to_spoken_words(50) == "pachaas"
        assert number_to_spoken_words(100) == "ek sau"
        assert number_to_spoken_words(150) == "ek sau pachaas"
        assert number_to_spoken_words(450) == "chaar sau pachaas"
        assert number_to_spoken_words(1200) == "ek hazaar do sau"
