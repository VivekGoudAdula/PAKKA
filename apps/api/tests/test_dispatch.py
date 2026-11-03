"""
Automated Scenario Runner for Technician Voice Dispatch FSM.
Executes all 15 scenarios in tests/scenarios/dispatch.yaml,
validates state transitions, acceptance/rejection terminal outcomes,
and saves metrics to apps/api/reports/dispatch_results.json.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.brain.dispatch import DispatchFSM, rank_technicians_for_job
from app.models.domain import Job, Technician

SCENARIOS_PATH = Path(__file__).parent / "scenarios" / "dispatch.yaml"
REPORT_PATH = Path(__file__).parent.parent / "reports" / "dispatch_results.json"


def load_dispatch_scenarios() -> list[dict[str, Any]]:
    """Load the 15 dispatch scenarios from YAML."""
    assert SCENARIOS_PATH.exists(), f"Scenario file missing at {SCENARIOS_PATH}"
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    scenarios = data.get("scenarios", [])
    assert len(scenarios) >= 15, f"Expected >= 15 scenarios, found {len(scenarios)}"
    return scenarios


@pytest.fixture(scope="module")
def dispatch_scenarios() -> list[dict[str, Any]]:
    return load_dispatch_scenarios()


def test_scenario_count(dispatch_scenarios: list[dict[str, Any]]) -> None:
    """Ensure at least 15 scenarios are loaded."""
    assert len(dispatch_scenarios) >= 15


def test_execute_all_dispatch_scenarios(dispatch_scenarios: list[dict[str, Any]]) -> None:
    """Execute each dispatch scenario through DispatchFSM and verify outputs."""
    results: list[dict[str, Any]] = []
    passed_scenarios = 0
    total_turns = 0
    total_latency_ms = 0.0

    for sc in dispatch_scenarios:
        sc_id = sc["id"]
        sc_name = sc.get("name", sc_id)
        tech_name = sc.get("technician", "Ramesh Kumar")
        problem = sc.get("problem", "Geyser repair")
        address = sc.get("address", "Mayur Vihar")
        slot = sc.get("slot", "Kal Subah")
        turns = sc.get("turns", [])

        fsm = DispatchFSM(
            technician_name=tech_name,
            problem=problem,
            address=address,
            slot=slot,
        )

        scenario_passed = True
        failure_reasons: list[str] = []
        turn_traces: list[dict[str, Any]] = []

        for turn in turns:
            caller_text = turn["caller"]
            expected_state = turn.get("expected_state")
            expected_terminal = turn.get("expected_terminal", False)
            expected_accepted = turn.get("expected_accepted")
            expected_repeat = turn.get("expected_repeat", False)

            t0 = time.monotonic()
            turn_res = fsm.process_utterance(caller_text)
            lat_ms = (time.monotonic() - t0) * 1000.0

            total_turns += 1
            total_latency_ms += lat_ms

            # Latency SLA check (< 10 ms for deterministic state machine)
            if lat_ms > 20.0:
                failure_reasons.append(f"FSM latency exceeded SLA: {lat_ms:.2f}ms > 20ms")
                scenario_passed = False

            if expected_state and turn_res.current_state.value != expected_state:
                failure_reasons.append(
                    f"State mismatch: expected {expected_state}, got {turn_res.current_state.value}"
                )
                scenario_passed = False

            if turn_res.is_terminal != expected_terminal:
                failure_reasons.append(
                    f"Terminal mismatch: expected {expected_terminal}, got {turn_res.is_terminal}"
                )
                scenario_passed = False

            if expected_accepted is not None and turn_res.is_accepted != expected_accepted:
                failure_reasons.append(
                    f"Acceptance mismatch: expected {expected_accepted}, got {turn_res.is_accepted}"
                )
                scenario_passed = False

            if expected_repeat and not turn_res.is_repeat:
                failure_reasons.append("Expected repeat request to be handled, but was not")
                scenario_passed = False

            turn_traces.append(
                {
                    "technician_input": caller_text,
                    "bot_reply": turn_res.bot_reply,
                    "state": turn_res.current_state.value,
                    "is_terminal": turn_res.is_terminal,
                    "is_accepted": turn_res.is_accepted,
                    "latency_ms": round(lat_ms, 3),
                }
            )

        if scenario_passed:
            passed_scenarios += 1

        results.append(
            {
                "id": sc_id,
                "name": sc_name,
                "passed": scenario_passed,
                "failures": failure_reasons,
                "turns": turn_traces,
            }
        )

    # Calculate overall metrics
    total_count = len(dispatch_scenarios)
    accuracy_pct = (passed_scenarios / total_count) * 100.0
    avg_latency_ms = total_latency_ms / total_turns if total_turns > 0 else 0.0

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_scenarios": total_count,
        "passed_scenarios": passed_scenarios,
        "failed_scenarios": total_count - passed_scenarios,
        "scenario_accuracy_pct": round(accuracy_pct, 2),
        "total_turns_evaluated": total_turns,
        "average_fsm_latency_ms": round(avg_latency_ms, 3),
        "scenarios": results,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nSaved dispatch test report to {REPORT_PATH}")
    print(f"Dispatch Accuracy: {accuracy_pct:.1f}% ({passed_scenarios}/{total_count})")
    print(f"Average FSM Latency: {avg_latency_ms:.3f} ms")

    assert passed_scenarios == total_count, (
        f"{total_count - passed_scenarios} dispatch scenarios failed: "
        f"{[r['id'] for r in results if not r['passed']]}"
    )


def test_technician_ranking_specialty_and_load() -> None:
    """
    Test technician ranking:
    1. Geyser problem -> Geyser specialist ranked before general plumber.
    2. Same specialty -> technician with fewest active jobs ranked first.
    3. Declined technician is excluded.
    """
    t1 = Technician(id="t1", name="Ramesh", phone_masked="98XXXXXX01", trade="Geyser Specialist", active_jobs_count=2, status="available")
    t2 = Technician(id="t2", name="Mohan", phone_masked="98XXXXXX02", trade="Geyser Specialist", active_jobs_count=0, status="available")
    t3 = Technician(id="t3", name="Suresh", phone_masked="98XXXXXX03", trade="General Plumbing", active_jobs_count=0, status="available")
    t4 = Technician(id="t4", name="Inactive", phone_masked="98XXXXXX04", trade="Geyser Specialist", status="off_duty")

    job = Job(id="j1", call_id="c1", title="Geyser Repair", customer_name="Test", customer_phone_masked="98XXXXXX99", problem="Geyser heating problem", landmark_address="Mayur Vihar", time_slot="Kal Subah", price_estimate="₹350 - ₹500", price_min=350, price_max=500, status="booked")

    ranked = rank_technicians_for_job([t1, t2, t3, t4], job)
    # t4 is inactive so excluded
    assert len(ranked) == 3
    # t2 has 0 active jobs and geyser specialty -> rank 0
    assert ranked[0].id == "t2"
    # t1 has 2 active jobs but geyser specialty -> rank 1
    assert ranked[1].id == "t1"
    # t3 is general plumbing -> rank 2
    assert ranked[2].id == "t3"

    # If t2 declined:
    ranked_after_decline = rank_technicians_for_job([t1, t2, t3, t4], job, declined_technician_ids={"t2"})
    assert len(ranked_after_decline) == 2
    assert ranked_after_decline[0].id == "t1"

