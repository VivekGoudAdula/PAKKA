"""
scripts/warm_tts_cache.py
Pre-generates fixed reply WAV audio files into apps/api/cache/tts using GnaniRestClient.

Safety:
- Calculates how many calls will be made BEFORE making them.
- Requires `--yes` flag to actually execute.
- Respects existing cache: skips phrases that are already cached on disk.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add apps/api to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.brain.replies import (
    ASK_ADDRESS,
    ASK_NAME,
    ASK_PROBLEM,
    ASK_SLOT,
    BARGAINING_HOLD,
    EMERGENCY_ELECTRIC_INSTRUCTION,
    EMERGENCY_FIRE_GAS_INSTRUCTION,
    EMERGENCY_FLOODING_INSTRUCTION,
    MANDATORY_GREETING,
    REASK_ADDRESS,
    REASK_PROBLEM,
    REASK_SLOT,
    ROBOT_DISCLOSURE,
    SILENCE_PROMPT_1,
    SILENCE_PROMPT_2,
)
from app.voice.gnani_rest import GnaniRestClient, tts_cache

FIXED_PHRASES = [
    MANDATORY_GREETING,
    ASK_PROBLEM,
    REASK_PROBLEM,
    ASK_ADDRESS,
    REASK_ADDRESS,
    ASK_SLOT,
    REASK_SLOT,
    ASK_NAME,
    ROBOT_DISCLOSURE.format(business_name="Sharma Plumbing"),
    BARGAINING_HOLD,
    EMERGENCY_ELECTRIC_INSTRUCTION,
    EMERGENCY_FIRE_GAS_INSTRUCTION,
    EMERGENCY_FLOODING_INSTRUCTION,
    SILENCE_PROMPT_1,
    SILENCE_PROMPT_2,
    "Namaste, main Sharma Plumbing ki digital sahayak bol rahi hoon. Ek zaroori payment ke silsile mein phone kiya hai.",
    "Theek hai ji, main malik ko bol kar callback karwa deti hoon. Dhanyawaad.",
]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-generate fixed TTS replies into local cache.")
    parser.add_argument("--yes", action="store_true", help="Confirm execution of TTS generation")
    parser.add_argument("--dry-run", action="store_true", help="Force synthetic dry-run generation")
    args = parser.parse_args()

    client = GnaniRestClient(dry_run=args.dry_run)

    # 1. Inspect cache status for each phrase
    to_generate: list[str] = []
    already_cached: list[str] = []

    voice = "Poorvi"
    model = "timbre-v2.5"
    language = "hi-en"
    speed = 1.0
    sample_rate = 16000

    for phrase in FIXED_PHRASES:
        key = tts_cache.compute_key(phrase, voice, model, language, speed, sample_rate)
        if tts_cache.get(key) is not None:
            already_cached.append(phrase)
        else:
            to_generate.append(phrase)

    print("\n" + "=" * 60)
    print(" Pakka TTS Cache Warming Plan")
    print("=" * 60)
    print(f"Total fixed phrases      : {len(FIXED_PHRASES)}")
    print(f"Already cached on disk   : {len(already_cached)}")
    print(f"Calls needed to generate : {len(to_generate)}")
    print("=" * 60)

    if not to_generate:
        print("All phrases are already cached! No API calls needed.\n")
        return

    print("\nPhrases scheduled for TTS synthesis:")
    for i, p in enumerate(to_generate, 1):
        print(f"  {i}. {p[:70]}...")

    if not args.yes:
        print("\n[ABORTED] Dry run only. Pass '--yes' to execute these calls.\n")
        sys.exit(0)

    print(f"\nExecuting {len(to_generate)} TTS synthesis calls...\n")
    generated_count = 0

    for i, phrase in enumerate(to_generate, 1):
        try:
            print(f"[{i}/{len(to_generate)}] Synthesizing: {phrase[:50]}...")
            _, was_cached, mode = await client.text_to_speech(
                text=phrase,
                voice=voice,
                model=model,
                language=language,
                speed=speed,
                sample_rate=sample_rate,
            )
            print(f"       -> Done (mode={mode}, cached={was_cached})")
            generated_count += 1
            await asyncio.sleep(0.1)
        except Exception as exc:
            print(f"       -> [ERROR] Failed to synthesize: {exc}")

    print("\n" + "=" * 60)
    print(f"Cache warming complete! Successfully generated {generated_count}/{len(to_generate)} items.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
