"""
Automated Test Runner for Pakka Collection Brain.
Loads collection scenarios and holdout scenarios, executes through CollectionFSM,
verifies dispositions, dates, and safety rules, and generates reports/collection_results.json.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.brain.collection import CollectionFSM

COLLECTION_SCENARIOS_PATH = Path(__file__).parent / "scenarios" / "collection.yaml"
HOLDOUT_COLLECTION_PATH = Path(__file__).parent / "scenarios" / "holdout_collection.yaml"
REPORT_PATH = Path(__file__).parent.parent / "reports" / "collection_results.json"


def load_yaml(path: Path) -> list[dict[str, Any]]:
    assert path.exists(), f"Scenario file not found at {path}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


@pytest.fixture(scope="module")
def collection_scenarios() -> list[dict[str, Any]]:
    data = load_yaml(COLLECTION_SCENARIOS_PATH)
    assert len(data) >= 20, f"Expected >= 20 collection scenarios, got {len(data)}"
    return data


def test_collection_scenario_count(collection_scenarios: list[dict[str, Any]]) -> None:
    """Ensure at least 20 collection scenarios are defined."""
    assert len(collection_scenarios) >= 20


def test_execute_all_collection_scenarios(collection_scenarios: list[dict[str, Any]]) -> None:
    """Execute all 25 main collection scenarios through CollectionFSM."""
    results: list[dict[str, Any]] = []
    passed_count = 0

    for sc in collection_scenarios:
        sc_id = sc["id"]
        customer_name = sc.get("customer_name", "Ramesh")
        balance = sc.get("balance", 500)
        tone_level = sc.get("tone_level", 1)
        dialogue = sc.get("dialogue", [])
        expected = sc.get("expected", {})

        fsm = CollectionFSM(
            customer_name=customer_name,
            balance=balance,
            tone_level=tone_level,
        )

        last_res = None
        turn_logs = []
        for turn in dialogue:
            last_res = fsm.process_utterance(turn["user"])
            turn_logs.append(
                {
                    "user": turn["user"],
                    "bot": last_res.bot_reply,
                    "state": last_res.current_state.value,
                }
            )

        assert last_res is not None, f"Scenario {sc_id} has empty dialogue"

        # Check Expectations
        exp_disp = expected.get("disposition")
        exp_date = expected.get("captured_date")
        exp_term = expected.get("is_terminal", True)
        exp_suppress = expected.get("suppress_number", False)
        exp_owner = expected.get("needs_owner", False)

        actual_disp = last_res.disposition.value if last_res.disposition else None
        disp_ok = actual_disp == exp_disp if exp_disp else True
        date_ok = fsm.captured_date == exp_date if exp_date else True
        term_ok = last_res.is_terminal == exp_term
        suppress_ok = last_res.suppress_number == exp_suppress
        owner_ok = last_res.needs_owner == exp_owner

        is_passed = all([disp_ok, date_ok, term_ok, suppress_ok, owner_ok])
        if is_passed:
            passed_count += 1

        results.append(
            {
                "id": sc_id,
                "name": sc.get("name"),
                "passed": is_passed,
                "disposition": actual_disp,
                "expected_disposition": exp_disp,
                "captured_date": fsm.captured_date,
                "expected_date": exp_date,
                "turns": turn_logs,
            }
        )

    # Execute Holdout Scenarios Separately
    holdout_scenarios = load_yaml(HOLDOUT_COLLECTION_PATH)
    holdout_results: list[dict[str, Any]] = []
    holdout_passed = 0

    for h_sc in holdout_scenarios:
        fsm_h = CollectionFSM(
            customer_name=h_sc.get("customer_name", "Customer"),
            balance=h_sc.get("balance", 500),
            tone_level=h_sc.get("tone_level", 1),
        )
        h_last = None
        for turn in h_sc.get("dialogue", []):
            h_last = fsm_h.process_utterance(turn["user"])

        h_exp = h_sc.get("expected", {})
        h_actual_disp = h_last.disposition.value if h_last and h_last.disposition else None
        h_disp_ok = h_actual_disp == h_exp.get("disposition")
        h_date_ok = (
            fsm_h.captured_date == h_exp.get("captured_date")
            if h_exp.get("captured_date")
            else True
        )
        h_pass = bool(h_disp_ok and h_date_ok)
        if h_pass:
            holdout_passed += 1

        holdout_results.append(
            {
                "id": h_sc.get("id"),
                "passed": h_pass,
                "disposition": h_actual_disp,
                "expected_disposition": h_exp.get("disposition"),
                "captured_date": fsm_h.captured_date,
            }
        )

    # Save to report JSON
    total_main = len(collection_scenarios)
    report_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_scenarios": total_main,
        "passed_scenarios": passed_count,
        "pass_rate_percent": round((passed_count / total_main * 100), 2),
        "holdout": {
            "total_scenarios": len(holdout_scenarios),
            "passed_scenarios": holdout_passed,
            "pass_rate_percent": round((holdout_passed / len(holdout_scenarios) * 100), 2)
            if holdout_scenarios
            else 0.0,
            "results": holdout_results,
        },
        "results": results,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    assert passed_count == total_main, f"{total_main - passed_count} main scenarios failed"
