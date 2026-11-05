"""
Interactive Terminal CLI for Testing Pakka Collection Brain.
Allows running simulated phone conversations with CollectionFSM.

Usage:
    python scripts/text_collection.py [--name "Ramesh"] [--balance 500] [--tone 1]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from app.brain.collection import CollectionFSM
from app.brain.replies_collection import get_collection_greeting


def run_interactive_collection() -> None:
    parser = argparse.ArgumentParser(description="Test Pakka Collection FSM Interactively")
    parser.add_argument("--name", default="Ramesh Kumar", help="Customer name")
    parser.add_argument("--balance", type=int, default=500, help="Outstanding balance")
    parser.add_argument("--tone", type=int, default=1, choices=[1, 2, 3], help="Tone level (1-3)")
    args = parser.parse_args()

    print("=" * 60)
    print("  PAKKA COLLECTION ASSISTANT — INTERACTIVE CLI")
    print(f"  Customer: {args.name} | Balance: ₹{args.balance} | Tone: Level {args.tone}")
    print("  Type your response, or 'exit' / 'quit' to end.")
    print("=" * 60)

    fsm = CollectionFSM(
        customer_name=args.name,
        balance=args.balance,
        tone_level=args.tone,
    )

    # Initial Greeting
    greeting = get_collection_greeting(
        customer_name=args.name,
        tone_level=args.tone,
    )
    print(f"\n[BOT (Sahayak)]: {greeting}")

    while not fsm.state.name == "TERMINAL":
        try:
            user_input = input("\n[CUSTOMER]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Session ended.")
            break

        res = fsm.process_utterance(user_input)
        print(f"[BOT (Sahayak)]: {res.bot_reply}")
        print(
            f"   ↳ [State: {res.current_state.value} | "
            f"Disposition: {res.disposition.value if res.disposition else 'None'} | "
            f"Captured Date: {res.captured_date or 'None'}]"
        )

        if res.is_terminal:
            print("\n" + "-" * 60)
            print("  CALL TERMINATED")
            print(f"  Final Disposition: {res.disposition.value if res.disposition else 'None'}")
            if res.captured_date:
                print(f"  Agreed Promise Date: {res.captured_date}")
            if res.suppress_number:
                print("  [ALERT] Number marked WRONG_NUMBER and permanently SUPPRESSED.")
            if res.needs_owner:
                print("  [ALERT] Flagged for OWNER CALLBACK / ESCALATION.")
            print("-" * 60)
            break


if __name__ == "__main__":
    run_interactive_collection()

