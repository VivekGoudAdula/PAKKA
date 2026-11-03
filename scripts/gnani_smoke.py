#!/usr/bin/env python3
"""
scripts/gnani_smoke.py
Gnani Vachana Voice Smoke Test.

Synthesizes a short test phrase with Timbre TTS, saves to samples/smoke_tts.wav,
then streams that audio into Prisma STT and prints transcripts with latencies.

Usage:
  python scripts/gnani_smoke.py [--live] [--dry-run]
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


async def run_smoke_test(is_live: bool = False) -> None:
    """Run end-to-end TTS synthesis followed by STT transcription."""
    print("=" * 65)
    print("  PAKKA — GNANI VACHANA VOICE PIPELINE SMOKE TEST")
    print("=" * 65)

    key_is_set = bool(
        settings.gnani_api_key
        and settings.gnani_api_key.strip()
        and settings.gnani_api_key not in ("mock", "placeholder", "")
    )

    if is_live and not key_is_set:
        print("[AUTH] GNANI_API_KEY is not configured.")
        print("PENDING USER: key not set")
        sys.exit(0)

    is_dry = not is_live
    mode_str = (
        "LIVE (wss://api.vachana.ai)"
        if is_live
        else "DRY RUN (SYNTHETIC offline audio)"
    )
    print(f"Mode:             {mode_str}")
    print("Target format:    8000 Hz, 16-bit mono linear PCM")
    print(f"API Key present:  {key_is_set}")
    print("-" * 65)

    tts_passed = False
    stt_passed = False
    tts_ttfb_ms = 0.0
    stt_latency_ms = 0.0
    final_text = ""

    overall_start = time.monotonic()

    try:
        # Enforce strict 20.0s overall smoke test timeout
        async with asyncio.timeout(20.0):
            # ── STAGE 1: TTS Synthesis ─────────────────────────────────
            test_phrase = "Namaste, geyser repair ke liye call kiya tha."
            print(f"[1/2] Requesting TTS synthesis: '{test_phrase}'")
            tts_client = GnaniTTSClient(dry_run=is_dry)

            tts_start = time.monotonic()
            first_chunk_time = None
            pcm_chunks: list[bytes] = []

            try:
                async for chunk in tts_client.synthesize(test_phrase):
                    if first_chunk_time is None:
                        first_chunk_time = time.monotonic()
                    pcm_chunks.append(chunk)

                full_pcm = b"".join(pcm_chunks)
                if not full_pcm:
                    raise RuntimeError("TTS returned empty audio stream")

                total_tts_ms = (time.monotonic() - tts_start) * 1000
                tts_ttfb_ms = (
                    (first_chunk_time - tts_start) * 1000 if first_chunk_time else 0.0
                )
                tag = "[SYNTHETIC]" if is_dry else "[LIVE]"
                print(
                    f"  >> [STAGE 1: TTS] PASS {tag} | TTFB: {tts_ttfb_ms:.1f}ms | "
                    f"Total: {total_tts_ms:.1f}ms | Bytes: {len(full_pcm)}"
                )
                tts_passed = True

                # Save synthesized PCM to samples/smoke_tts.wav
                samples_dir = Path(__file__).resolve().parent.parent / "samples"
                samples_dir.mkdir(parents=True, exist_ok=True)
                out_wav_path = samples_dir / "smoke_tts.wav"

                with wave.open(str(out_wav_path), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(8000)
                    wav.writeframes(full_pcm)
                print(f"     Saved artifact: {out_wav_path.relative_to(Path.cwd())}")

            except Exception as exc:  # noqa: BLE001
                print(f"  >> [STAGE 1: TTS] FAIL: {exc}")
                return

            # ── STAGE 2: STT Transcription ─────────────────────────────
            print("-" * 65)
            print(f"[2/2] Streaming audio to STT: {out_wav_path.name}")
            stt_client = GnaniSTTClient(sample_rate=8000, dry_run=is_dry)
            await stt_client.connect()

            rechunker = Rechunker(target_chunk_size=1024)
            pacer = PacedSender(sample_rate=8000)

            all_frames = list(rechunker.add(full_pcm))
            rem = rechunker.flush()
            if rem:
                all_frames.append(rem + b"\x00" * (1024 - len(rem)))

            print(f"     Pumping {len(all_frames)} 1024-byte frames (64ms cadence)...")

            async def pump_audio() -> None:
                try:
                    for f in all_frames:
                        await pacer.wait_for_cadence(len(f))
                        await stt_client.send_frame(f)
                    await stt_client.commit()
                except Exception as e:  # noqa: BLE001
                    print(f"     Audio stream warning: {e}")

            pump_task = asyncio.create_task(pump_audio())

            try:
                # 10s timeout for STT recognition phase
                async with asyncio.timeout(10.0):
                    async for tr in stt_client.receive_transcripts():
                        kind = "FINAL" if tr.is_final else "PARTIAL"
                        tag = "[SYNTHETIC]" if is_dry else "[LIVE]"
                        print(
                            f"     {tag} [{kind}] latency={tr.latency_ms:.1f}ms: '{tr.text}'"
                        )
                        if tr.is_final:
                            final_text = tr.text
                            stt_latency_ms = tr.latency_ms
                            stt_passed = True
                            break
            finally:
                await pump_task
                await stt_client.close()

            if stt_passed:
                tag = "[SYNTHETIC]" if is_dry else "[LIVE]"
                print(
                    f"  >> [STAGE 2: STT] PASS {tag} | Final: '{final_text}' | Latency: {stt_latency_ms:.1f}ms"
                )
            else:
                print(
                    "  >> [STAGE 2: STT] FAIL: No final transcript received within timeout"
                )

    except TimeoutError:
        print("  >> ERROR: Smoke test overall timeout (20s exceeded)")
    except Exception as exc:  # noqa: BLE001
        print(f"  >> ERROR: Unexpected failure: {exc}")

    overall_ms = (time.monotonic() - overall_start) * 1000
    print("-" * 65)
    print("Smoke Test Summary:")
    print(f"  Stage 1 (TTS): {'PASS' if tts_passed else 'FAIL'}")
    print(f"  Stage 2 (STT): {'PASS' if stt_passed else 'FAIL'}")
    print(f"  Total Duration: {overall_ms:.1f} ms")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gnani Vachana Voice Smoke Test")
    parser.add_argument(
        "--live", action="store_true", help="Run live against wss://api.vachana.ai"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Force synthetic dry-run mode (default)"
    )
    args = parser.parse_args()

    is_live = args.live and not args.dry_run
    asyncio.run(run_smoke_test(is_live=is_live))


if __name__ == "__main__":
    main()
