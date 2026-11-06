"""
scripts/live_rest_check.py
Preflight Diagnostic for Gnani REST APIs (STT Prisma v3.0 + TTS Timbre v2.5).

Evaluates:
1. TTS REST synthesis of mandatory digital sahayak disclosure line.
   Saves output to samples/live_rest_tts.wav.
2. STT REST transcription of that audio file.
3. Latency, processing time, and typed error diagnostics.
4. Writes reports/live_rest_check.json (mode="live" ONLY if both calls hit the live network and returned 200).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure apps/api is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import settings
from app.voice.gnani_rest import (
    GnaniAuthError,
    GnaniCreditError,
    GnaniNetworkError,
    GnaniRateLimitError,
    GnaniRestClient,
    GnaniRestError,
    GnaniScopeError,
    GnaniServiceError,
    GnaniTimeoutError,
)

DISCLOSURE_LINE = "Namaste, main Pakka ki digital sahayak bol rahi hoon."


def print_header(title: str) -> None:
    print(f"\n{'=' * 65}")
    print(f" {title}")
    print(f"{'=' * 65}")


async def main() -> None:
    print_header("Pakka Gnani REST Speech Stack Preflight Diagnostic")
    start_time = datetime.now(UTC).isoformat()
    samples_dir = REPO_ROOT / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    tts_wav_path = samples_dir / "live_rest_tts.wav"

    has_key = bool(settings.gnani_api_key and not settings.gnani_api_key.startswith("your_"))
    is_live_configured = has_key and not settings.gnani_dry_run

    client = GnaniRestClient(dry_run=not is_live_configured)

    tts_step: dict[str, Any] = {
        "status": "PENDING",
        "is_live_network": is_live_configured,
        "latency_ms": 0.0,
        "bytes_received": 0,
        "error": None,
    }
    stt_step: dict[str, Any] = {
        "status": "PENDING",
        "is_live_network": is_live_configured,
        "transcript": "",
        "latency_ms": 0.0,
        "processing_time": 0.0,
        "error": None,
    }

    # ── Step 1: TTS REST Synthesis ─────────────────────────────────────────────
    print_header("Step 1: Gnani TTS REST Synthesis (Timbre v2.5)")
    print(f"  Target Text: '{DISCLOSURE_LINE}'")
    print(f"  Endpoint   : {settings.gnani_tts_rest_url}")

    if not has_key and is_live_configured:
        print("  [SKIP] GNANI_API_KEY is not set or placeholder.")
        tts_step["status"] = "SKIP"
        tts_step["error"] = "GNANI_API_KEY not configured"
    else:
        t0 = time.monotonic()
        try:
            wav_bytes, was_cached, mode = await client.text_to_speech(
                text=DISCLOSURE_LINE,
                voice="Poorvi",
                model="timbre-v2.5",
                language="hi-en",
                speed=1.0,
                sample_rate=16000,
            )
            lat_ms = (time.monotonic() - t0) * 1000.0
            tts_wav_path.write_bytes(wav_bytes)

            tts_step["status"] = "PASS"
            tts_step["latency_ms"] = round(lat_ms, 2)
            tts_step["bytes_received"] = len(wav_bytes)
            tts_step["was_cached"] = was_cached
            tts_step["mode"] = mode

            print(f"  [PASS] TTS Succeeded ({mode.upper()})")
            print(f"         Latency: {lat_ms:.1f} ms | Saved: {tts_wav_path} ({len(wav_bytes)} bytes)")
        except GnaniAuthError as exc:
            print(f"  [FAIL] Authentication Error (401): {exc}")
            tts_step["status"] = "FAIL"
            tts_step["error"] = str(exc)
        except GnaniCreditError as exc:
            print(f"  [FAIL] Insufficient Credit (402): {exc}")
            tts_step["status"] = "FAIL"
            tts_step["error"] = str(exc)
        except GnaniRateLimitError as exc:
            print(f"  [FAIL] Rate Limited (429): {exc}")
            tts_step["status"] = "FAIL"
            tts_step["error"] = str(exc)
        except GnaniTimeoutError as exc:
            print(f"  [FAIL] Timeout Error: {exc}")
            tts_step["status"] = "FAIL"
            tts_step["error"] = str(exc)
        except GnaniNetworkError as exc:
            print(f"  [FAIL] Network / DNS Error: {exc}")
            tts_step["status"] = "FAIL"
            tts_step["error"] = str(exc)
        except Exception as exc:
            print(f"  [FAIL] Unexpected Error: {type(exc).__name__}: {exc}")
            tts_step["status"] = "FAIL"
            tts_step["error"] = f"{type(exc).__name__}: {exc}"

    # ── Step 2: STT REST Transcription ─────────────────────────────────────────
    print_header("Step 2: Gnani STT REST Transcription (Prisma v3.0)")
    print(f"  Endpoint : {settings.gnani_stt_rest_url}")

    if not tts_wav_path.exists() or tts_step["status"] != "PASS":
        print("  [SKIP] Skipping STT: TTS audio sample was not generated.")
        stt_step["status"] = "SKIP"
        stt_step["error"] = "Input WAV missing"
    else:
        audio_data = tts_wav_path.read_bytes()
        t0 = time.monotonic()
        try:
            stt_res = await client.speech_to_text(
                audio_bytes=audio_data,
                filename="live_rest_tts.wav",
                content_type="audio/wav",
                model="prisma-v3.0",
                language_code="hi-IN",
            )
            lat_ms = (time.monotonic() - t0) * 1000.0

            stt_step["status"] = "PASS"
            stt_step["transcript"] = stt_res["transcript"]
            stt_step["detected_language"] = stt_res.get("detected_language")
            stt_step["processing_time"] = stt_res.get("processing_time", 0.0)
            stt_step["latency_ms"] = round(lat_ms, 2)
            stt_step["mode"] = stt_res.get("mode", "dry_run")

            print(f"  [PASS] STT Succeeded ({stt_res.get('mode', '').upper()})")
            print(f"         Transcript: '{stt_res['transcript']}'")
            print(f"         Processing Time: {stt_res.get('processing_time', 0.0)}s | Latency: {lat_ms:.1f} ms")
        except GnaniAuthError as exc:
            print(f"  [FAIL] Authentication Error (401): {exc}")
            stt_step["status"] = "FAIL"
            stt_step["error"] = str(exc)
        except GnaniCreditError as exc:
            print(f"  [FAIL] Insufficient Credit (402): {exc}")
            stt_step["status"] = "FAIL"
            stt_step["error"] = str(exc)
        except GnaniRateLimitError as exc:
            print(f"  [FAIL] Rate Limited (429): {exc}")
            stt_step["status"] = "FAIL"
            stt_step["error"] = str(exc)
        except GnaniTimeoutError as exc:
            print(f"  [FAIL] Timeout Error: {exc}")
            stt_step["status"] = "FAIL"
            stt_step["error"] = str(exc)
        except GnaniNetworkError as exc:
            print(f"  [FAIL] Network / DNS Error: {exc}")
            stt_step["status"] = "FAIL"
            stt_step["error"] = str(exc)
        except Exception as exc:
            print(f"  [FAIL] Unexpected Error: {type(exc).__name__}: {exc}")
            stt_step["status"] = "FAIL"
            stt_step["error"] = f"{type(exc).__name__}: {exc}"

    # Truth in reporting: mode is "live" ONLY if both calls hit external live network and returned 200
    tts_is_live = is_live_configured and tts_step["status"] == "PASS" and tts_step.get("mode") == "live"
    stt_is_live = is_live_configured and stt_step["status"] == "PASS" and stt_step.get("mode") == "live"
    overall_mode = "live" if (tts_is_live and stt_is_live) else ("dry_run" if settings.gnani_dry_run else "mock")

    report_payload = {
        "mode": overall_mode,
        "generated_at": start_time,
        "steps": {
            "tts": tts_step,
            "stt": stt_step,
        },
        "summary": {
            "tts_status": tts_step["status"],
            "stt_status": stt_step["status"],
            "is_fully_live": overall_mode == "live",
        },
    }

    report_path = REPO_ROOT / "reports" / "live_rest_check.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print_header(f"Live REST Diagnostic Complete: Mode = {overall_mode.upper()}")
    print(f"Saved preflight report to: {report_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
