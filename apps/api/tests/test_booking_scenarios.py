"""
Automated Scenario Runner for Pakka Booking Brain.
Loads YAML test scenarios, executes conversations through BookingFSM,
verifies terminal states and extracted slots, and saves structured
metrics to apps/api/reports/booking_results.json.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.brain.fsm import BookingFSM

SCENARIOS_PATH = Path(__file__).parent / "scenarios" / "booking.yaml"
REPORT_PATH = Path(__file__).parent.parent / "reports" / "booking_results.json"


def load_scenarios() -> list[dict[str, Any]]:
    """Load test scenarios from YAML."""
    assert SCENARIOS_PATH.exists(), f"Scenario file missing at {SCENARIOS_PATH}"
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, list) and len(data) >= 20, (
        f"Expected >= 20 scenarios, found {len(data)}"
    )
    return data


@pytest.fixture(scope="module")
def scenarios() -> list[dict[str, Any]]:
    return load_scenarios()


def test_scenario_count(scenarios: list[dict[str, Any]]) -> None:
    """Ensure at least 20 diverse scenarios are loaded."""
    assert len(scenarios) >= 20


def test_execute_all_booking_scenarios(scenarios: list[dict[str, Any]]) -> None:
    """Execute each scenario through BookingFSM and verify expected outputs."""
    results: list[dict[str, Any]] = []
    total_slots_checked = 0
    correct_slots_count = 0
    passed_scenarios_count = 0

    for scenario in scenarios:
        sc_id = scenario["id"]
        sc_name = scenario.get("name", sc_id)
        dialogue = scenario.get("dialogue", [])
        expected = scenario.get("expected", {})

        fsm = BookingFSM(handoff_phone="+91 98765 43210")
        turn_results = []

        import time

        start_time = time.perf_counter()

        last_turn_res = None
        for turn in dialogue:
            user_text = turn["user"]
            res = fsm.process_utterance(user_text)
            last_turn_res = res
            turn_results.append(
                {
                    "user": user_text,
                    "bot": res.bot_reply,
                    "state": res.current_state.value,
                }
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        assert last_turn_res is not None, f"Scenario {sc_id} had empty dialogue"

        # Check Final State
        expected_state = expected.get("final_state")
        actual_state = last_turn_res.current_state.value
        state_match = actual_state == expected_state

        # Check Terminal Flag
        if "is_terminal" in expected:
            assert last_turn_res.is_terminal == expected["is_terminal"], (
                f"Scenario {sc_id} terminal mismatch: expected {expected['is_terminal']}, got {last_turn_res.is_terminal}"
            )

        # Check Expected Slots
        slot_checks = {}
        scenario_slots_ok = True
        expected_slots = expected.get("slots", {})
        for slot_k, exp_v in expected_slots.items():
            total_slots_checked += 1
            act_v = getattr(fsm.slots, slot_k, None)
            matches = act_v == exp_v
            slot_checks[slot_k] = {
                "expected": exp_v,
                "actual": act_v,
                "match": matches,
            }
            if matches:
                correct_slots_count += 1
            else:
                scenario_slots_ok = False

        passed = state_match and scenario_slots_ok
        if passed:
            passed_scenarios_count += 1

        results.append(
            {
                "id": sc_id,
                "name": sc_name,
                "passed": passed,
                "turns_count": len(dialogue),
                "final_state": actual_state,
                "expected_state": expected_state,
                "duration_ms": round(duration_ms, 2),
                "slot_checks": slot_checks,
                "extracted_slots": {
                    "problem": fsm.slots.problem,
                    "problem_key": fsm.slots.problem_key,
                    "landmark_address": fsm.slots.landmark_address,
                    "time_slot": fsm.slots.time_slot,
                    "price_estimate": fsm.slots.price_estimate,
                },
            }
        )

        assert state_match, (
            f"Scenario {sc_id} state mismatch: expected {expected_state}, got {actual_state}"
        )
        assert scenario_slots_ok, f"Scenario {sc_id} slot checks failed: {slot_checks}"

    total_scenarios = len(scenarios)
    pass_rate = (passed_scenarios_count / total_scenarios) * 100
    slot_accuracy = (
        (correct_slots_count / total_slots_checked * 100) if total_slots_checked else 100.0
    )

    # Save structured results to JSON
    report_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_scenarios": total_scenarios,
        "passed_scenarios": passed_scenarios_count,
        "pass_rate_percent": round(pass_rate, 2),
        "total_slots_checked": total_slots_checked,
        "correct_slots": correct_slots_count,
        "slot_accuracy_percent": round(slot_accuracy, 2),
        "extractor_type": "RuleBasedExtractor",
        "results": results,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    assert pass_rate == 100.0
    assert slot_accuracy == 100.0
