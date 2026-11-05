"""
scripts/live_check.py
Pakka Live Readiness & Telephony Pre-flight Diagnostic Tool.

Evaluates live readiness across:
1. Environment Variable Verification (Boolean presence check only; never logs secrets)
2. Gnani TTS Live Synthesis (Timbre v2.5 WebSocket -> samples/live_check_tts.wav)
3. Gnani STT Live Streaming (Prisma v3.0 WebSocket streaming that WAV)
4. Telephony Tunnel Verification (PUBLIC_WSS_URL -> HTTPS GET /health)
5. Manual Phone Verification Instructions

Truth in reporting rule:
Writes reports/live_check.json with mode='live' ONLY if TTS & STT hit real external network.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure apps/api is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.config import settings
from app.voice.gnani_stt import GnaniSTTClient
from app.voice.gnani_tts import GnaniTTSClient


def print_header(title: str) -> None:
    print(f"\n{'=' * 65}")
    print(f" {title}")
    print(f"{'=' * 65}")


def check_env_vars() -> tuple[dict[str, bool], bool]:
    """Check required env vars presence. Print strictly True/False, never secrets."""
    print_header("Step 1: Environment Variables Presence Check")
    checked_vars = [
        "GNANI_API_KEY",
        "EXOTEL_API_KEY",
        "EXOTEL_API_TOKEN",
        "EXOTEL_ACCOUNT_SID",
        "EXOPHONE_NUMBER",
        "PUBLIC_WSS_URL",
    ]
    results: dict[str, bool] = {}
    all_present = True

    for var in checked_vars:
        val = os.environ.get(var) or getattr(settings, var.lower(), None)
        is_set = bool(val and str(val).strip() and not str(val).startswith("your_"))
        results[var] = is_set
        status_str = "PRESENT (True)" if is_set else "MISSING / DEFAULT (False)"
        print(f"  [{'PASS' if is_set else 'WARN'}] {var:<22}: {status_str}")
        if not is_set:
            all_present = False

    return results, all_present


async def test_live_tts(
    output_wav_path: Path, timeout_s: float = 20.0
) -> dict[str, Any]:
    """
    Synthesize test phrase with Gnani TTS.
    Records TTFC and audio duration.
    """
    print_header("Step 2: Gnani TTS Synthesis Test (Timbre v2.5)")
    text = "Namaste, main Pakka ki digital sahayak bol rahi hoon."
    print(f"  Synthesizing text: '{text}'")
    print(f"  Target file: {output_wav_path}")

    has_key = bool(settings.gnani_api_key and not settings.gnani_api_key.startswith("your_"))
    is_live = has_key and not settings.gnani_dry_run

    result: dict[str, Any] = {
        "step": "tts_synthesis",
        "status": "PENDING",
        "is_live_network": is_live,
        "ttfc_ms": 0.0,
        "duration_seconds": 0.0,
        "total_bytes": 0,
        "error": None,
    }

    if not has_key and is_live:
        print("  [SKIP] GNANI_API_KEY is not set. Cannot run live TTS network check.")
        result["status"] = "SKIP"
        result["error"] = "GNANI_API_KEY missing"
        return result

    client = GnaniTTSClient(sample_rate=8000, dry_run=not is_live)
    t0 = time.monotonic()
    pcm_bytes = bytearray()
    first_chunk_time: float | None = None

    try:
        async with asyncio.timeout(timeout_s):
            async for chunk in client.synthesize(text):
                if first_chunk_time is None:
                    first_chunk_time = time.monotonic()
                pcm_bytes.extend(chunk)

        if not pcm_bytes:
            print("  [FAIL] TTS produced 0 bytes of audio.")
            result["status"] = "FAIL"
            result["error"] = "Zero bytes received from TTS"
            return result

        ttfc_ms = ((first_chunk_time or t0) - t0) * 1000.0
        # 8000 Hz * 16-bit mono = 16000 bytes/sec
        duration_s = len(pcm_bytes) / 16000.0

        output_wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(pcm_bytes)

        result["status"] = "PASS"
        result["ttfc_ms"] = round(ttfc_ms, 2)
        result["duration_seconds"] = round(duration_s, 2)
        result["total_bytes"] = len(pcm_bytes)

        mode_tag = "LIVE NETWORK" if is_live else "SYNTHETIC SIMULATION"
        print(f"  [PASS] TTS Succeeded ({mode_tag})")
        print(f"         Time to First Chunk (TTFC): {ttfc_ms:.1f} ms")
        print(f"         Audio Duration: {duration_s:.2f} s ({len(pcm_bytes)} PCM bytes)")
        print(f"         Saved WAV: {output_wav_path}")
        return result

    except TimeoutError:
        print(f"  [FAIL] TTS timed out after {timeout_s}s.")
        result["status"] = "FAIL"
        result["error"] = f"TimeoutError ({timeout_s}s exceeded)"
        return result
    except ssl.SSLError as exc:
        print(f"  [FAIL] TLS/SSL Handshake Error: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"TLS Error: {exc}"
        return result
    except socket.gaierror as exc:
        print(f"  [FAIL] DNS Resolution Error: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"DNS Resolution Error: {exc}"
        return result
    except Exception as exc:
        print(f"  [FAIL] TTS Exception: {type(exc).__name__}: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


async def test_live_stt(
    input_wav_path: Path, timeout_s: float = 20.0
) -> dict[str, Any]:
    """
    Stream test WAV file into Gnani STT client in 1024-byte frames.
    Records transcript and latency.
    """
    print_header("Step 3: Gnani STT Streaming Test (Prisma v3.0)")
    has_key = bool(settings.gnani_api_key and not settings.gnani_api_key.startswith("your_"))
    is_live = has_key and not settings.gnani_dry_run

    result: dict[str, Any] = {
        "step": "stt_streaming",
        "status": "PENDING",
        "is_live_network": is_live,
        "transcript": "",
        "latency_ms": 0.0,
        "error": None,
    }

    if not input_wav_path.exists():
        print(f"  [SKIP] Audio input file not found at {input_wav_path}")
        result["status"] = "SKIP"
        result["error"] = "Input WAV missing"
        return result

    if not has_key and is_live:
        print("  [SKIP] GNANI_API_KEY is not set. Cannot run live STT network check.")
        result["status"] = "SKIP"
        result["error"] = "GNANI_API_KEY missing"
        return result

    # Read raw PCM frames from WAV
    with wave.open(str(input_wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        raw_frames = wf.readframes(wf.getnframes())

    client = GnaniSTTClient(sample_rate=framerate, dry_run=not is_live)
    t0 = time.monotonic()

    try:
        async with asyncio.timeout(timeout_s):
            await client.connect()

            # Stream in 1024-byte frames at fast simulated cadence
            stream_task = asyncio.create_task(_stream_pcm_frames(client, raw_frames))

            transcript_text = ""
            async for item in client.receive_transcripts():
                if item.text:
                    transcript_text = item.text
                    if item.is_final:
                        break

            await stream_task
            await client.close()

            lat_ms = (time.monotonic() - t0) * 1000.0

            result["status"] = "PASS"
            result["transcript"] = transcript_text
            result["latency_ms"] = round(lat_ms, 2)

            mode_tag = "LIVE NETWORK" if is_live else "SYNTHETIC SIMULATION"
            print(f"  [PASS] STT Succeeded ({mode_tag})")
            print(f"         Final Transcript: '{transcript_text}'")
            print(f"         Total Latency: {lat_ms:.1f} ms")
            return result

    except TimeoutError:
        print(f"  [FAIL] STT timed out after {timeout_s}s.")
        result["status"] = "FAIL"
        result["error"] = f"TimeoutError ({timeout_s}s exceeded)"
        return result
    except ssl.SSLError as exc:
        print(f"  [FAIL] TLS/SSL Handshake Error: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"TLS Error: {exc}"
        return result
    except socket.gaierror as exc:
        print(f"  [FAIL] DNS Resolution Error: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"DNS Resolution Error: {exc}"
        return result
    except Exception as exc:
        print(f"  [FAIL] STT Exception: {type(exc).__name__}: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


async def _stream_pcm_frames(client: GnaniSTTClient, pcm: bytes) -> None:
    """Helper to stream 1024-byte frames with minimal pacing."""
    for i in range(0, len(pcm), 1024):
        frame = pcm[i : i + 1024]
        if len(frame) < 1024:
            frame = frame + b"\x00" * (1024 - len(frame))
        await client.send_frame(frame)
        await asyncio.sleep(0.01)
    await client.commit()


def check_tunnel_health(timeout_s: float = 5.0) -> dict[str, Any]:
    """
    Derive HTTPS URL from PUBLIC_WSS_URL and perform GET /health check.
    """
    print_header("Step 4: Public Telephony Tunnel Verification")
    wss_url = settings.public_wss_url or ""
    print(f"  PUBLIC_WSS_URL: {wss_url or '(not configured)'}")

    result: dict[str, Any] = {
        "step": "tunnel_health",
        "status": "PENDING",
        "target_url": None,
        "response_code": None,
        "error": None,
    }

    if not wss_url or "ngrok" in wss_url and "your" in wss_url:
        print("  [SKIP] PUBLIC_WSS_URL is not configured with an active public tunnel.")
        result["status"] = "SKIP"
        result["error"] = "PUBLIC_WSS_URL not configured"
        return result

    # Derive HTTPS endpoint from WSS
    http_url = wss_url.replace("wss://", "https://").replace("ws://", "http://").rstrip("/")
    target_health_url = f"{http_url}/health"
    result["target_url"] = target_health_url
    print(f"  Target Health Check URL: {target_health_url}")

    try:
        req = urllib.request.Request(
            target_health_url,
            headers={"User-Agent": "Pakka-LiveCheck/1.0"},
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout_s, context=ctx) as response:
            code = response.getcode()
            body = response.read().decode("utf-8")
            result["response_code"] = code

            if code == 200:
                print(f"  [PASS] Tunnel /health returned HTTP 200: {body[:80]}")
                result["status"] = "PASS"
            else:
                print(f"  [FAIL] Tunnel /health returned HTTP {code}: {body[:80]}")
                result["status"] = "FAIL"
                result["error"] = f"Unexpected HTTP status {code}"
            return result

    except urllib.error.HTTPError as exc:
        print(f"  [FAIL] Tunnel returned HTTP {exc.code}: {exc.reason}")
        result["status"] = "FAIL"
        result["response_code"] = exc.code
        result["error"] = f"HTTP {exc.code}: {exc.reason}"
        return result
    except urllib.error.URLError as exc:
        print(f"  [FAIL] Tunnel connection failed: {exc.reason}")
        result["status"] = "FAIL"
        result["error"] = f"URLError: {exc.reason}"
        return result
    except TimeoutError:
        print(f"  [FAIL] Tunnel timed out after {timeout_s}s.")
        result["status"] = "FAIL"
        result["error"] = "Connection Timeout"
        return result
    except Exception as exc:
        print(f"  [FAIL] Unexpected tunnel error: {type(exc).__name__}: {exc}")
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def print_manual_phone_test_guide() -> None:
    """Print exact actionable instructions for live telephony verification."""
    print_header("Step 5: Live Phone Carrier Test Protocol")
    phone = settings.exophone_number or "+91-XXXXXXXXXX (Configure EXOPHONE_NUMBER)"
    print(
        f"""
  To test live end-to-end voice telephony with a real phone:
  
  1. DIAL: Call your configured Exotel virtual number:
     >>> {phone} <<<
  
  2. LISTEN FOR GREETING:
     Verify the bot starts with the required AI disclosure:
     "...ki digital sahayak bol rahi hoon. Aapko kis cheez ki service chahiye?"
  
  3. SPEAK A REALISTIC PROBLEM:
     Say in clear Hindi or Hinglish:
     "Mera geyser kharab hai, paani garam nahi kar raha."
  
  4. PROVIDE LANDMARK & TIME:
     - When asked for area: "Mayur Vihar Phase 1 ke paas"
     - When asked for time: "Kal subah 10 baje aa jao"
  
  5. BARGE-IN CHECK (OPTIONAL):
     Interrupt the bot while it is speaking to verify immediate cutoff (< 500 ms).
  
  6. VERIFY IN DASHBOARD:
     Open http://localhost:3000/app/calls to watch the live call transcript,
     extracted slots, and job confirmation update in real time.
"""
    )


async def main() -> None:
    print_header("Pakka Live Telephony & Speech Stack Pre-flight Check")
    start_time = datetime.now(UTC).isoformat()

    # Step 1: Env check
    env_results, _ = check_env_vars()

    # Step 2: TTS check
    samples_dir = REPO_ROOT / "samples"
    wav_path = samples_dir / "live_check_tts.wav"
    tts_result = await test_live_tts(output_wav_path=wav_path, timeout_s=20.0)

    # Step 3: STT check
    stt_result = await test_live_stt(input_wav_path=wav_path, timeout_s=20.0)

    # Step 4: Tunnel check
    tunnel_result = check_tunnel_health(timeout_s=5.0)

    # Step 5: Manual steps
    print_manual_phone_test_guide()

    # Truth in reporting: mode is "live" ONLY if TTS and STT hit external live network
    tts_is_live = tts_result.get("is_live_network", False) and tts_result["status"] == "PASS"
    stt_is_live = stt_result.get("is_live_network", False) and stt_result["status"] == "PASS"
    overall_mode = "live" if (tts_is_live and stt_is_live) else ("dry_run" if settings.gnani_dry_run else "mock")

    report_payload = {
        "mode": overall_mode,
        "generated_at": start_time,
        "environment_variables": env_results,
        "steps": {
            "tts": tts_result,
            "stt": stt_result,
            "tunnel": tunnel_result,
        },
        "summary": {
            "tts_status": tts_result["status"],
            "stt_status": stt_result["status"],
            "tunnel_status": tunnel_result["status"],
            "is_fully_live": overall_mode == "live",
        },
    }

    report_path = REPO_ROOT / "reports" / "live_check.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print_header(f"Live Check Complete: Mode = {overall_mode.upper()}")
    print(f"Saved pre-flight report to: {report_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
