#!/usr/bin/env python3
"""
Interactive Text-Mode Telephony Simulator for Pakka Booking Brain.
Allows testing the full Hinglish booking conversation without audio or Gnani STT/TTS.

Usage:
    python scripts/text_call.py
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

# Add apps/api to PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.brain.fsm import BookingFSM
from app.brain.replies import MANDATORY_GREETING


def run_interactive_call() -> None:
    print("=" * 70)
    print(" PAKKA VOICE ASSISTANT — TEXT MODE TELEPHONY SIMULATOR")
    print(" Type caller replies in Hinglish or Devanagari. Type 'exit' to quit.")
    print(" Type '__silence__' to simulate 8s line silence.")
    print("=" * 70)

    fsm = BookingFSM()

    print(f"\nBot: {MANDATORY_GREETING}")
    print(f"State: {fsm.state.value}\n")

    while True:
        try:
            line = input("Caller > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCall interrupted.")
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit"):
            print("Session ended.")
            break

        turn = fsm.process_utterance(line)

        print(f"\nBot: {turn.bot_reply}")
        print(f"State: {turn.current_state.value}")
        print(
            f"Slots: problem='{turn.slots.problem}' | "
            f"address='{turn.slots.landmark_address}' | "
            f"slot='{turn.slots.time_slot}' | "
            f"quote='{turn.slots.price_estimate}'"
        )

        if turn.ai_disclosure_triggered:
            print(" [NOTICE: AI Non-Denial Disclosure Stated]")

        if turn.needs_handoff:
            print(" [EVENT: CALL HANDOFF FLAGGED]")

        if turn.is_terminal:
            print(f"\n[CALL FINISHED: {turn.current_state.value}]")
            if turn.job_payload:
                print(f"[JOB PAYLOAD: {turn.job_payload}]")
            break
        print("-" * 50)


if __name__ == "__main__":
    run_interactive_call()
