"""
scripts/make_test_audio.py
Generates 30 synthetic test audio files at 3 SNR levels:
- Clean (clean PCM)
- 15 dB SNR (moderate street/background noise)
- 5 dB SNR (heavy background noise)

Generates Linear16 PCM (8000 Hz, mono, 16-bit) and writes .wav / .raw audio files
to apps/api/data/test_audio/.
Dry-run mode by default; uses Timbre TTS when --live is specified and API key is set.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import random
import struct
import sys
import wave
from pathlib import Path
from typing import Any

# Force UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import yaml

from app.config import settings
from app.voice.gnani_tts import GnaniTTSClient

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_FILE = BASE_DIR / "apps" / "api" / "tests" / "scenarios" / "stt_noisy.yaml"
AUDIO_DIR = BASE_DIR / "apps" / "api" / "data" / "test_audio"


def generate_synthetic_pcm_sine(text: str, duration_sec: float = 2.0, sample_rate: int = 8000) -> bytes:
    """Generate synthetic modulated tone PCM in dry-run mode."""
    num_samples = int(duration_sec * sample_rate)
    samples = []
    base_freq = 200 + (hash(text) % 300)

    for i in range(num_samples):
        t = i / sample_rate
        val = int(2500 * math.sin(2 * math.pi * base_freq * t) * (0.8 + 0.2 * math.sin(2 * math.pi * 5 * t)))
        samples.append(max(-32768, min(32767, val)))

    return struct.pack(f"<{len(samples)}h", *samples)


def add_noise_to_pcm(clean_pcm: bytes, snr_db: float | None) -> bytes:
    """Add Gaussian noise to achieve target Signal-to-Noise Ratio (SNR in dB)."""
    if snr_db is None or snr_db > 90:
        return clean_pcm

    sample_count = len(clean_pcm) // 2
    samples = list(struct.unpack(f"<{sample_count}h", clean_pcm))

    # Calculate signal power (RMS squared)
    signal_power = sum(s * s for s in samples) / max(sample_count, 1)
    if signal_power == 0:
        return clean_pcm

    # SNR = 10 * log10(signal_power / noise_power)
    # noise_power = signal_power / (10 ** (snr_db / 10))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise_std = math.sqrt(noise_power)

    noisy_samples = []
    for s in samples:
        n = random.gauss(0, noise_std)
        noisy_val = int(s + n)
        noisy_samples.append(max(-32768, min(32767, noisy_val)))

    return struct.pack(f"<{len(noisy_samples)}h", *noisy_samples)


def save_wav(pcm_data: bytes, path: Path, sample_rate: int = 8000) -> None:
    """Save raw PCM to standard WAV container."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


async def synthesize_or_generate_pcm(text: str, live: bool = False) -> bytes:
    """Synthesize audio via Timbre TTS or generate synthetic PCM."""
    if live and settings.gnani_api_key and not settings.gnani_dry_run:
        try:
            tts = GnaniTTSClient(voice="Poorvi", sample_rate=8000)
            chunks = []
            async for chunk in tts.synthesize(text):
                chunks.append(chunk)
            if chunks:
                return b"".join(chunks)
        except Exception as exc:
            print(f"  [!] Live TTS error: {exc}; falling back to synthetic audio")

    return generate_synthetic_pcm_sine(text)


async def build_dataset(live: bool = False, count: int = 30) -> None:
    """Generate audio files at Clean, 15 dB SNR, and 5 dB SNR."""
    print("==================================================================")
    print(f"PAKKA AUDIO GENERATOR: 30 test utterances × 3 SNR levels ({'LIVE Timbre TTS' if live else 'DRY RUN'})")
    print("==================================================================")

    with open(SCENARIOS_FILE, encoding="utf-8") as f:
        scenarios = yaml.safe_load(f)[:count]

    snr_levels = [
        ("clean", None),
        ("15db", 15.0),
        ("5db", 5.0),
    ]

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    metadata = []

    for idx, sc in enumerate(scenarios, start=1):
        sc_id = sc.get("id", f"sample_{idx:02d}")
        utterance = sc.get("utterance", "")
        print(f"[{idx:02d}/{count}] Generating audio for: '{utterance[:50]}...'")

        clean_pcm = await synthesize_or_generate_pcm(utterance, live=live)

        sample_meta = {
            "id": sc_id,
            "utterance": utterance,
            "expected": sc.get("expected", {}),
            "audio_files": {},
        }

        for snr_label, snr_val in snr_levels:
            out_pcm = add_noise_to_pcm(clean_pcm, snr_val)
            wav_path = AUDIO_DIR / f"{sc_id}_{snr_label}.wav"
            save_wav(out_pcm, wav_path)
            sample_meta["audio_files"][snr_label] = str(wav_path.relative_to(BASE_DIR)).replace("\\", "/")

        metadata.append(sample_meta)

    # Save audio dataset manifest
    manifest_file = AUDIO_DIR / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        import json
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Audio dataset generated successfully at: {AUDIO_DIR}")
    print(f"[+] Total files generated: {len(scenarios) * len(snr_levels)} audio files")
    print(f"[+] Manifest saved to: {manifest_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Pakka test audio at multiple SNR levels")
    parser.add_argument("--live", action="store_true", help="Use live Gnani Timbre TTS (requires GNANI_API_KEY)")
    parser.add_argument("--count", type=int, default=30, help="Number of scenarios to process (default 30)")
    args = parser.parse_args()

    asyncio.run(build_dataset(live=args.live, count=args.count))


if __name__ == "__main__":
    main()
