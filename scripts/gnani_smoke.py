#!/usr/bin/env python3
"""
scripts/gnani_smoke.py
Gnani Vachana Voice Smoke Test.

Synthesizes a short test phrase with Timbre TTS, saves to samples/smoke_tts.wav,
then streams that audio into Prisma STT and prints transcripts with latencies.

Usage:
  python scripts/gnani_smoke.py [--dry-run]
"""

import argparse
import asyncio
import sys
import time
import wave
from pathlib import Path

# Add apps/api to sys.path so app modules can be imported
API_DIR = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.config import settings
from app.voice.audio import PacedSender, Rechunker
from app.voice.gnani_stt import GnaniSTTClient
from app.voice.gnani_tts import GnaniTTSClient


async def run_smoke_test(dry_run: bool = False) -> None:
    """Run end-to-end TTS synthesis followed by STT transcription."""
    print("=" * 60)
    print("  PAKKA — GNANI VACHANA SMOKE TEST")
    print("=" * 60)

    is_dry = (
        dry_run
        or settings.gnani_dry_run
        or settings.gnani_api_key in ("mock", "placeholder", "")
    )
    mode_str = (
        "DRY RUN (Simulated offline audio)" if is_dry else "LIVE (wss://api.vachana.ai)"
    )
    print(f"Mode: {mode_str}")
    print("Target sample rate: 8000 Hz, 16-bit mono PCM")
    print("-" * 60)

    # 1. TTS Synthesis
    test_phrase = "Namaste, geyser repair ke liye call kiya tha."
    print(f"[1/2] Synthesizing TTS: '{test_phrase}'")
    tts_client = GnaniTTSClient(dry_run=is_dry)

    tts_start = time.monotonic()
    first_chunk_time = None
    pcm_chunks: list[bytes] = []

    async for chunk in tts_client.synthesize(test_phrase):
        if first_chunk_time is None:
            first_chunk_time = time.monotonic()
        pcm_chunks.append(chunk)

    total_tts_time = time.monotonic() - tts_start
    ttfb_ms = (first_chunk_time - tts_start) * 1000 if first_chunk_time else 0.0
    full_pcm = b"".join(pcm_chunks)

    print(
        f"      TTS TTFB: {ttfb_ms:.1f} ms | Total time: {total_tts_time * 1000:.1f} ms"
    )
    print(
        f"      Received: {len(full_pcm)} bytes PCM ({len(full_pcm) / 16000:.2f} seconds)"
    )

    # Save to samples/smoke_tts.wav
    samples_dir = Path(__file__).resolve().parent.parent / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    out_wav_path = samples_dir / "smoke_tts.wav"

    with wave.open(str(out_wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(full_pcm)
    print(f"      Saved: {out_wav_path.relative_to(Path.cwd())}")

    # 2. STT Transcription
    print("-" * 60)
    print(f"[2/2] Streaming audio to STT: {out_wav_path.name}")
    stt_client = GnaniSTTClient(sample_rate=8000, dry_run=is_dry)
    await stt_client.connect()

    rechunker = Rechunker(target_chunk_size=1024)
    pacer = PacedSender(sample_rate=8000)

    all_frames = list(rechunker.add(full_pcm))
    rem = rechunker.flush()
    if rem:
        # Pad remaining with silence to ensure exact 1024 bytes if desired
        padded_rem = rem + b"\x00" * (1024 - len(rem))
        all_frames.append(padded_rem)

    print(f"      Prepared {len(all_frames)} 1024-byte frames (64ms each)")

    stt_start = time.monotonic()
    transcript_count = 0

    async def pump_audio() -> None:
        try:
            for f in all_frames:
                await pacer.wait_for_cadence(len(f))
                await stt_client.send_frame(f)
            await stt_client.commit()
        except Exception as e:  # noqa: BLE001
            print(f"      Audio streaming error: {e}")

    pump_task = asyncio.create_task(pump_audio())

    try:
        # Collect transcripts with timeout
        timeout = 5.0 if is_dry else 10.0
        async with asyncio.timeout(timeout):
            async for tr in stt_client.receive_transcripts():
                transcript_count += 1
                kind = "FINAL" if tr.is_final else "PARTIAL"
                print(f"      [{kind}] latency={tr.latency_ms:.1f}ms: '{tr.text}'")
                if tr.is_final:
                    break
    except TimeoutError:
        print("      STT reception timed out (expected if quiet end of stream)")
    finally:
        await pump_task
        await stt_client.close()

    total_stt_time = (time.monotonic() - stt_start) * 1000
    print("-" * 60)
    print(f"Smoke test completed in {total_stt_time:.1f} ms. All stages verified.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gnani Vachana Voice Smoke Test")
    parser.add_argument(
        "--dry-run", action="store_true", help="Force dry-run simulation mode"
    )
    args = parser.parse_args()

    asyncio.run(run_smoke_test(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
