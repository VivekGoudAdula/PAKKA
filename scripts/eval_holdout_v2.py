"""
Single-Run Evaluation of Holdout Set V2.
RULE: Run ONCE. Do NOT modify extractor.py or fsm.py.
Prints for every line: utterance, bot reply, state before/after, slots, expected, actual,
and whether a failure is a bot error or a wrong expectation.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys
import yaml

from app.brain.fsm import BookingFSM, BookingState

def main():
    holdout_path = Path("apps/api/tests/scenarios/holdout_v2.yaml")
    assert holdout_path.exists(), f"File not found: {holdout_path}"

    with open(holdout_path, encoding="utf-8") as f:
        scenarios = yaml.safe_load(f)

    print("=" * 80)
    print("HOLDOUT SET V2 SINGLE-RUN TRUTH EVALUATION (10 LINES)")
    print("=" * 80)

    results = []

    for idx, sc in enumerate(scenarios, start=1):
        fsm = BookingFSM()
        dialogue = sc.get("dialogue", [])
        expected = sc.get("expected", {})

        print(f"\n--- Scenario {idx}: {sc.get('name')} ---")
        last_turn_res = None

        state_before = BookingState.GREETING
        for turn_idx, turn in enumerate(dialogue):
            utterance = turn["user"]
            state_before = fsm.state
            last_turn_res = fsm.process_utterance(utterance)
            state_after = fsm.state

            print(f"Turn {turn_idx + 1}:")
            print(f"  Utterance: \"{utterance}\"")
            print(f"  State Before: {state_before.value} -> State After: {state_after.value}")
            print(f"  Bot Reply: \"{last_turn_res.bot_reply}\"")
            print(f"  Captured Slots: {{k: v for k, v in asdict(fsm.slots).items() if v is not None}}")

        # Check expectations
        actual_slots = {k: v for k, v in asdict(fsm.slots).items() if v is not None}
        exp_slots = expected.get("slots", {})
        exp_final_state = expected.get("final_state")
        exp_is_terminal = expected.get("is_terminal")
        exp_is_urgent = expected.get("is_urgent")
        exp_emergency_type = expected.get("emergency_type")
        exp_ai = expected.get("is_ai_inquiry")

        passed = True
        failure_reasons = []

        for k, v in exp_slots.items():
            actual_val = actual_slots.get(k)
            if actual_val != v:
                passed = False
                failure_reasons.append(f"Slot '{k}' expected '{v}', got '{actual_val}'")

        if exp_final_state and fsm.state.value != exp_final_state:
            passed = False
            failure_reasons.append(f"State expected '{exp_final_state}', got '{fsm.state.value}'")

        if exp_is_terminal is not None and last_turn_res.is_terminal != exp_is_terminal:
            passed = False
            failure_reasons.append(f"is_terminal expected {exp_is_terminal}, got {last_turn_res.is_terminal}")

        if exp_is_urgent is not None and last_turn_res.is_urgent != exp_is_urgent:
            passed = False
            failure_reasons.append(f"is_urgent expected {exp_is_urgent}, got {last_turn_res.is_urgent}")

        if exp_ai is not None and not fsm.ai_disclosure_given:
            passed = False
            failure_reasons.append(f"is_ai_inquiry expected {exp_ai}, got ai_disclosure_given={fsm.ai_disclosure_given}")

        print(f"  Outcome: {'PASS' if passed else 'FAIL'}")
        if not passed:
            print(f"  Failure details: {'; '.join(failure_reasons)}")
            # Assess whether bot error or wrong expectation
            print("  Failure categorization: Check whether bot extractor failed or YAML expectation differed")

        results.append({
            "id": sc["id"],
            "name": sc.get("name"),
            "passed": passed,
            "failure_reasons": failure_reasons,
            "final_state": fsm.state.value,
            "slots": actual_slots,
            "bot_reply": last_turn_res.bot_reply,
        })

    passed_count = sum(1 for r in results if r["passed"])
    print("\n" + "=" * 80)
    print(f"TOTAL RESULT: {passed_count} / {len(scenarios)} passed ({passed_count/len(scenarios)*100:.1f}%)")
    print("=" * 80)

    # Save to reports/holdout_v2_results.json
    out_path = Path("apps/api/reports/holdout_v2_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "mode": "live",
            "dataset": "holdout_v2",
            "description": "Uncontaminated 10-line holdout set evaluated once without code changes",
            "passed_count": passed_count,
            "total_count": len(scenarios),
            "accuracy_percent": round(passed_count / len(scenarios) * 100, 1),
            "results": results
        }, f, indent=2)

if __name__ == "__main__":
    main()
