"""
Audio processing utilities for the Pakka voice pipeline.

Handles:
- Base64 encoding/decoding of linear16 PCM.
- Rechunker: buffers variable audio streams and yields EXACTLY 1024-byte frames for Gnani STT.
- ExotelAudioAccumulator: buffers TTS output and yields chunks >= 3200 bytes & multiple of 320.
- Pacing math: real-time cadence calculation for telephony audio (8000 Hz, 16-bit linear PCM).
- Number to spoken Hindi/English words for TTS prompting.
"""

import asyncio
import base64
import time
from collections.abc import Iterator


def pcm_to_base64(pcm_bytes: bytes) -> str:
    """Encode raw linear16 PCM bytes to base64 string."""
    return base64.b64encode(pcm_bytes).decode("ascii")


def base64_to_pcm(b64_str: str) -> bytes:
    """Decode base64 string to raw linear16 PCM bytes."""
    return base64.b64decode(b64_str)


def calculate_pcm_duration_ms(byte_count: int, sample_rate: int = 8000) -> float:
    """
    Calculate duration of 16-bit linear PCM mono audio in milliseconds.
    Formula: bytes / (sample_rate * 2 bytes_per_sample) * 1000
    """
    bytes_per_second = sample_rate * 2
    return (byte_count / bytes_per_second) * 1000.0


class Rechunker:
    """
    Buffers incoming PCM bytes of arbitrary chunk sizes (e.g. Exotel's ~1600-byte chunks)
    and yields frames of an EXACT target size (e.g. 1024 bytes for Gnani STT).
    Guarantees never to yield a short frame. Remainder is kept in the buffer.
    """

    def __init__(self, target_chunk_size: int = 1024) -> None:
        if target_chunk_size <= 0:
            raise ValueError("target_chunk_size must be positive")
        self.target_chunk_size = target_chunk_size
        self._buffer = bytearray()

    def add(self, chunk: bytes) -> Iterator[bytes]:
        """
        Add new PCM audio to buffer and yield all complete frames of target_chunk_size.
        """
        if not chunk:
            return
        self._buffer.extend(chunk)
        while len(self._buffer) >= self.target_chunk_size:
            frame = bytes(self._buffer[: self.target_chunk_size])
            del self._buffer[: self.target_chunk_size]
            yield frame

    def flush(self) -> bytes:
        """
        Return whatever remains in the buffer and reset it.
        (Note: for Gnani STT, remainder should generally NOT be sent as a short frame).
        """
        remaining = bytes(self._buffer)
        self._buffer.clear()
        return remaining

    @property
    def buffered_bytes(self) -> int:
        """Current number of buffered bytes."""
        return len(self._buffer)


class ExotelAudioAccumulator:
    """
    Accumulates TTS audio chunks and emits slices suitable for Exotel media events:
    - Must be at least `min_bytes` (default 3200 bytes = 200 ms at 8 kHz mono 16-bit).
    - Must be an EXACT multiple of `multiple_of` (default 320 bytes = 20 ms).
    - Must not exceed `max_bytes` (default 100,000 bytes).
    """

    def __init__(
        self,
        min_bytes: int = 3200,
        multiple_of: int = 320,
        max_bytes: int = 100000,
    ) -> None:
        self.min_bytes = min_bytes
        self.multiple_of = multiple_of
        self.max_bytes = max_bytes
        self._buffer = bytearray()

    def add(self, chunk: bytes) -> list[bytes]:
        """
        Add incoming audio bytes and return chunks that meet Exotel size constraints.
        """
        if not chunk:
            return []
        self._buffer.extend(chunk)

        result: list[bytes] = []
        while len(self._buffer) >= self.min_bytes:
            # Determine maximum slice that is a multiple of multiple_of up to max_bytes
            available = min(len(self._buffer), self.max_bytes)
            sendable_len = (available // self.multiple_of) * self.multiple_of
            if sendable_len < self.min_bytes:
                break
            result.append(bytes(self._buffer[:sendable_len]))
            del self._buffer[:sendable_len]
        return result

    @property
    def buffered_bytes(self) -> int:
        """Current number of buffered bytes."""
        return len(self._buffer)

    def flush(self, pad_to_multiple: bool = True) -> bytes | None:
        """
        Flush remaining audio at end of utterance.
        If remainder < min_bytes or not a multiple of 320, optionally pads with silence (0x00).
        """
        if not self._buffer:
            return None

        remaining = bytes(self._buffer)
        self._buffer.clear()

        if pad_to_multiple:
            # Ensure it is at least min_bytes and multiple of multiple_of
            target_len = max(len(remaining), self.min_bytes)
            remainder = target_len % self.multiple_of
            if remainder != 0:
                target_len += self.multiple_of - remainder
            padding_needed = target_len - len(remaining)
            if padding_needed > 0:
                remaining += b"\x00" * padding_needed

        return remaining


class PacedSender:
    """
    Helper to pace streaming of audio frames at real-time wall-clock cadence.
    For 8 kHz 16-bit mono: 1024 bytes = 512 samples = 64 ms.
    """

    def __init__(self, sample_rate: int = 8000, bytes_per_sample: int = 2) -> None:
        self.sample_rate = sample_rate
        self.bytes_per_sample = bytes_per_sample
        self._next_send_time: float | None = None

    def reset(self) -> None:
        """Reset the pacing clock."""
        self._next_send_time = None

    async def wait_for_cadence(self, chunk_size: int) -> None:
        """
        Sleep asynchronously until the scheduled wall-clock time for the chunk.
        """
        duration_s = chunk_size / (self.sample_rate * self.bytes_per_sample)
        now = time.monotonic()

        if self._next_send_time is None:
            self._next_send_time = now + duration_s
            return

        delay = self._next_send_time - now
        if delay > 0:
            await asyncio.sleep(delay)

        self._next_send_time += duration_s


_NUMBER_MAP: dict[int, str] = {
    0: "zero",
    1: "ek",
    2: "do",
    3: "teen",
    4: "chaar",
    5: "paanch",
    6: "chhah",
    7: "saat",
    8: "aath",
    9: "nau",
    10: "das",
    11: "gyaarah",
    12: "baarah",
    13: "terah",
    14: "chaudah",
    15: "pandrah",
    16: "solah",
    17: "satrah",
    18: "athaarah",
    19: "unnees",
    20: "bees",
    25: "pachhees",
    30: "tees",
    40: "chaalees",
    50: "pachaas",
    60: "saath",
    70: "sattar",
    80: "assee",
    90: "nabbe",
    100: "ek sau",
    200: "do sau",
    300: "teen sau",
    400: "chaar sau",
    500: "paanch sau",
    600: "chhah sau",
    700: "saat sau",
    800: "aath sau",
    900: "nau sau",
    1000: "ek hazaar",
}


def number_to_spoken_words(amount: int) -> str:
    """
    Format common amounts as spoken Hinglish words for Timbre TTS.
    Example: 150 -> 'ek sau pachaas', 500 -> 'paanch sau', 1200 -> 'ek hazaar do sau'.
    """
    if amount in _NUMBER_MAP:
        return _NUMBER_MAP[amount]

    if amount < 100:
        tens = (amount // 10) * 10
        rem = amount % 10
        if tens in _NUMBER_MAP and rem in _NUMBER_MAP:
            return f"{_NUMBER_MAP[tens]} {number_to_spoken_words(rem)}"
        return str(amount)

    if amount < 1000:
        hundreds = amount // 100
        rem = amount % 100
        h_str = f"{_NUMBER_MAP.get(hundreds, str(hundreds))} sau"
        if rem == 0:
            return h_str
        return f"{h_str} {number_to_spoken_words(rem)}"

    if amount < 100000:
        thousands = amount // 1000
        rem = amount % 1000
        t_str = f"{_NUMBER_MAP.get(thousands, str(thousands))} hazaar"
        if rem == 0:
            return t_str
        return f"{t_str} {number_to_spoken_words(rem)}"

    return str(amount)
    return str(amount)
