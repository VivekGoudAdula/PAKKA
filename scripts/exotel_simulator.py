#!/usr/bin/env python3
"""
scripts/exotel_simulator.py
Simulates Exotel Voicebot bidirectional WebSocket telephony client.

Connects to /ws/exotel, executes the handshake, listens to the assistant's greeting,
streams caller WAV audio as 100 ms chunks (~1600 bytes at 8 kHz mono linear16),
records the assistant's response, and saves it to samples/reply.wav.

Usage:
  python scripts/exotel_simulator.py [--url ws://localhost:8000/ws/exotel] [--audio samples/sample_plumber_request.wav]
"""

import argparse
import asyncio
import base64
import json
import logging
import time
import wave
from pathlib import Path

import websockets

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("exotel_sim")


def load_wav_pcm(path: Path) -> tuple[bytes, int]:
    """Load raw PCM bytes and verify sample rate from a WAV file."""
    with wave.open(str(path), "rb") as wav:
        nchannels = wav.getnchannels()
        sampwidth = wav.getsampwidth()
        framerate = wav.getframerate()
        nframes = wav.getnframes()
        frames = wav.readframes(nframes)

        logger.info(
            "Loaded WAV %s: %d channels, %d-byte width, %d Hz, %d frames (%d bytes)",
            path.name,
            nchannels,
            sampwidth,
            framerate,
            nframes,
            len(frames),
        )
        return frames, framerate


def save_pcm_wav(path: Path, pcm_data: bytes, sample_rate: int = 8000) -> None:
    """Save raw 16-bit mono PCM bytes to a WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    logger.info("Saved %d bytes of received bot audio to %s", len(pcm_data), path)


async def run_simulator(
    ws_url: str = "ws://localhost:8000/ws/exotel",
    audio_path: str = "samples/sample_plumber_request.wav",
    output_path: str = "samples/reply.wav",
    test_barge_in: bool = False,
    live_gnani: bool = False,
) -> None:
    """Run full Exotel simulated call loop."""
    print("=" * 65)
    print("  PAKKA — EXOTEL TELEPHONY PROTOCOL SIMULATOR")
    print("=" * 65)
    mode_str = "LIVE GNANI (api.vachana.ai)" if live_gnani else "DRY RUN (SYNTHETIC)"
    print(f"Mode:            {mode_str}")
    print(f"Target WebSocket:{ws_url}")
    print(f"Input audio:     {audio_path}")
    print(f"Output audio:    {output_path}")
    print(f"Barge-in test:   {test_barge_in}")
    print("-" * 65)

    if live_gnani and "?" not in ws_url:
        ws_url = f"{ws_url}?live_gnani=true"

    audio_file = Path(audio_path)
    if not audio_file.exists():
        fallback_file = Path("samples/smoke_tts.wav")
        if fallback_file.exists():
            logger.warning(
                "Audio %s not found, falling back to %s", audio_path, fallback_file
            )
            audio_file = fallback_file
        else:
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

    caller_pcm, sample_rate = load_wav_pcm(audio_file)

    stream_sid = f"sim_stream_{int(time.time())}"
    call_sid = f"sim_call_{int(time.time())}"

    received_bot_pcm = bytearray()
    events_received: list[str] = []
    greeting_done_event = asyncio.Event()
    echo_done_event = asyncio.Event()
    clear_received_event = asyncio.Event()

    async with websockets.connect(ws_url) as ws:
        # Receiver task to listen for bot responses
        async def listen_loop() -> None:
            nonlocal received_bot_pcm
            try:
                async for message in ws:
                    data = json.loads(message)
                    event_type = data.get("event")
                    events_received.append(event_type)

                    if event_type == "media":
                        media_obj = data.get("media", {})
                        payload_b64 = media_obj.get("payload", "")
                        if payload_b64:
                            pcm_chunk = base64.b64decode(payload_b64)
                            received_bot_pcm.extend(pcm_chunk)

                    elif event_type == "mark":
                        mark_name = data.get("mark", {}).get("name", "")
                        logger.info(">> Received MARK from assistant: '%s'", mark_name)
                        if mark_name == "greeting_done":
                            greeting_done_event.set()
                        elif "echo" in mark_name:
                            echo_done_event.set()

                    elif event_type == "clear":
                        logger.info(
                            ">> Received CLEAR from assistant (barge-in confirmed)"
                        )
                        clear_received_event.set()

                    else:
                        logger.info(">> Received event from assistant: %s", event_type)
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning("Listen loop terminated: %s", exc)

        listener_task = asyncio.create_task(listen_loop())

        try:
            # 1. Send 'connected' event
            logger.info("<< Sending 'connected' handshake")
            await ws.send(
                json.dumps(
                    {"event": "connected", "protocol": "Call", "version": "1.0.0"}
                )
            )
            await asyncio.sleep(0.05)

            # 2. Send 'start' event
            logger.info(
                "<< Sending 'start' event (stream_sid=%s, call_sid=%s, live_gnani=%s)",
                stream_sid,
                call_sid,
                live_gnani,
            )
            await ws.send(
                json.dumps(
                    {
                        "event": "start",
                        "stream_sid": stream_sid,
                        "call_sid": call_sid,
                        "from": "+919876543210",
                        "to": "+918045678901",
                        "custom_parameters": {
                            "live_gnani": "true" if live_gnani else "false"
                        },
                        "media_format": {
                            "encoding": "audio/x-l16",
                            "sample_rate": sample_rate,
                            "channels": 1,
                        },
                    }
                )
            )

            if test_barge_in:
                # Barge-in scenario: immediately stream caller speech while bot is greeting
                logger.info(
                    "<< [Barge-in test] Streaming caller speech immediately while bot is speaking..."
                )
            else:
                # Normal scenario: wait for greeting to complete
                logger.info("Waiting for assistant greeting to complete...")
                try:
                    await asyncio.wait_for(greeting_done_event.wait(), timeout=6.0)
                    logger.info(
                        "Greeting finished. Current bot audio received: %d bytes",
                        len(received_bot_pcm),
                    )
                except TimeoutError:
                    logger.warning(
                        "Timed out waiting for greeting mark, proceeding to speak..."
                    )

            # 3. Stream caller audio in 100 ms chunks (~1600 bytes at 8 kHz 16-bit)
            chunk_size = 1600
            total_chunks = (len(caller_pcm) + chunk_size - 1) // chunk_size
            logger.info(
                "<< Streaming %d bytes of caller audio (%d chunks of 100ms)...",
                len(caller_pcm),
                total_chunks,
            )

            start_stream_time = time.monotonic()
            for idx in range(total_chunks):
                chunk = caller_pcm[idx * chunk_size : (idx + 1) * chunk_size]
                b64_payload = base64.b64encode(chunk).decode("ascii")

                media_msg = {
                    "event": "media",
                    "stream_sid": stream_sid,
                    "media": {
                        "chunk": idx + 1,
                        "timestamp": int(idx * 100),
                        "payload": b64_payload,
                    },
                }
                await ws.send(json.dumps(media_msg))
                # Pace at 100 ms (0.10s)
                await asyncio.sleep(0.10)

            logger.info(
                "Caller audio stream completed in %.2fs",
                time.monotonic() - start_stream_time,
            )

            if test_barge_in:
                try:
                    await asyncio.wait_for(clear_received_event.wait(), timeout=3.0)
                    logger.info("PASS: Assistant sent 'clear' event during barge-in!")
                except TimeoutError:
                    logger.warning("Did not receive 'clear' event within 3s")

            # 4. Wait for echo turn response
            logger.info("Waiting for assistant echo response...")
            try:
                await asyncio.wait_for(echo_done_event.wait(), timeout=8.0)
                logger.info(
                    "Echo reply completed! Total bot audio received: %d bytes",
                    len(received_bot_pcm),
                )
            except TimeoutError:
                logger.info(
                    "Echo wait finished. Total bot audio received: %d bytes",
                    len(received_bot_pcm),
                )

            # 5. Send 'stop' event
            logger.info("<< Sending 'stop' event")
            await ws.send(
                json.dumps(
                    {
                        "event": "stop",
                        "stream_sid": stream_sid,
                        "stop": {"reason": "callended"},
                    }
                )
            )
            await asyncio.sleep(0.2)

        finally:
            listener_task.cancel()

    # Save received assistant audio to WAV
    out_path = Path(output_path)
    save_pcm_wav(out_path, bytes(received_bot_pcm), sample_rate=8000)

    print("-" * 65)
    print("Simulator Summary:")
    print(f"  Events received from bot: {set(events_received)}")
    print(
        f"  Total bot audio captured: {len(received_bot_pcm)} bytes ({len(received_bot_pcm) / 16000:.2f}s)"
    )
    print(f"  Saved response to:        {out_path.resolve()}")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exotel Telephony Protocol Simulator")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/ws/exotel",
        help="WebSocket URL of /ws/exotel",
    )
    parser.add_argument(
        "--audio",
        default="samples/sample_plumber_request.wav",
        help="WAV file to stream",
    )
    parser.add_argument(
        "--output", default="samples/reply.wav", help="Path to save bot response WAV"
    )
    parser.add_argument(
        "--barge-in", action="store_true", help="Test barge-in interruption"
    )
    parser.add_argument(
        "--live-gnani",
        action="store_true",
        help="Run real Gnani STT/TTS pipeline instead of synthetic dry-run",
    )
    args = parser.parse_args()

    asyncio.run(
        run_simulator(
            ws_url=args.url,
            audio_path=args.audio,
            output_path=args.output,
            test_barge_in=args.barge_in,
            live_gnani=args.live_gnani,
        )
    )


if __name__ == "__main__":
    main()
