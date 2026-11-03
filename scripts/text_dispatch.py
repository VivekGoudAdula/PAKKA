#!/usr/bin/env python3
"""
scripts/text_dispatch.py
Interactive Text-Mode Simulator for Pakka Technician Voice Dispatch.
Simulates outbound voice dispatch call to a technician.

Usage:
    python scripts/text_dispatch.py
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

from app.brain.dispatch import DispatchFSM


def run_interactive_dispatch() -> None:
    """Run an interactive CLI session simulating a technician dispatch call."""
    print("=" * 70)
    print(" PAKKA VOICE ASSISTANT — TECHNICIAN DISPATCH SIMULATOR")
    print(" You are acting as the technician. Spoken inputs in Hinglish or Devanagari.")
    print(" Examples: 'haan, pakka', 'nahi ho payega', 'dobara bolo', '__silence__'")
    print(" Type 'exit' to quit.")
    print("=" * 70)

    tech_name = "Ramesh Kumar"
    problem = "Geyser water heating issue"
    address = "Pocket B, Mayur Vihar Phase 2"
    slot = "Kal Subah 10 Baje"

    fsm = DispatchFSM(
        technician_name=tech_name,
        problem=problem,
        address=address,
        slot=slot,
    )

    greeting = fsm.get_initial_greeting()
    print(f"\n[Ringing... Connected!]")
    print(f"Bot: {greeting}")
    print(f"State: {fsm.state.value}\n")

    while True:
        try:
            line = input("Technician > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCall hung up.")
            break

        if not line:
            continue

        if line.lower() in ("exit", "quit"):
            print("Session ended.")
            break

        res = fsm.process_utterance(line)

        print(f"\nBot: {res.bot_reply}")
        print(f"State: {res.current_state.value}")
        if res.confirmation_phrase:
            print(f"Confirmed phrase: '{res.confirmation_phrase}'")
        print("-" * 50)

        if res.is_terminal:
            if res.is_accepted:
                print("\n[SUCCESS] Technician ACCEPTED the dispatch. Job confirmed!")
            elif res.is_declined:
                print("\n[DECLINED] Technician DECLINED the dispatch. Cascading to next specialist...")
            break


if __name__ == "__main__":
    run_interactive_dispatch()
