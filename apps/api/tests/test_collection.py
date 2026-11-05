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
        "mode": "live",
        "generated_at": datetime.now(UTC).isoformat(),
        "timestamp": datetime.now(UTC).isoformat(),
        "total_scenarios": total_main,
        "passed_scenarios": passed_count,
        "pass_rate_percent": round((passed_count / total_main * 100), 2),
        "holdout": {
            "label": "Development set (previously probed)",
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


def test_collection_ai_inquiry_all_phrasings() -> None:
    """Inquiries about AI return digital sahayak disclosure and continue dialog."""
    phrasings = [
        "kya aap robot ho?",
        "are you an AI?",
        "kya ye machine bol rahi hai?",
        "recording hai kya?",
        "asli insaan ho?",
        "क्या आप रोबोट हो?",
    ]
    for text in phrasings:
        fsm = CollectionFSM(business_name="Aggarwal Sanitation", balance=600)
        res = fsm.process_utterance(text)
        assert "Aggarwal Sanitation ki digital sahayak" in res.bot_reply
        assert res.is_terminal is False
        assert res.current_state.value == "CAPTURE_DATE"


def test_collection_dynamic_owner_and_business() -> None:
    """Collection brain respects dynamic business_name and owner_name."""
    fsm = CollectionFSM(business_name="Verma Plumbing", owner_name="Vikram")
    res_esc = fsm.process_utterance("mujhe malik se baat karni hai")
    assert "Vikram ji" in res_esc.bot_reply

    fsm_ref = CollectionFSM(business_name="Verma Plumbing", owner_name="Vikram")
    res_ref = fsm_ref.process_utterance("nahi dunga paise")
    assert "Vikram ji" in res_ref.bot_reply


def test_scheduler_suppression_tone3_and_disputes() -> None:
    """Tone 3, paused, and disputed promises are strictly suppressed from automated calls."""
    from app.models.domain import Promise
    from app.services.collection_scheduler import is_promise_eligible_for_call

    p1 = Promise(
        id="p1",
        customer_id="cust1",
        customer_name="A",
        customer_phone_raw="9800000001",
        customer_phone_masked="98XXXXXX01",
        amount=500,
        due_date="2020-01-01",
        status="broken",
        tone_level=3,
    )
    assert is_promise_eligible_for_call(p1) is False

    p2 = Promise(
        id="p2",
        customer_id="cust2",
        customer_name="B",
        customer_phone_raw="9800000002",
        customer_phone_masked="98XXXXXX02",
        amount=500,
        due_date="2020-01-01",
        status="disputed",
        tone_level=1,
    )
    assert is_promise_eligible_for_call(p2) is False

    p3 = Promise(
        id="p3",
        customer_id="cust3",
        customer_name="C",
        customer_phone_raw="9800000003",
        customer_phone_masked="98XXXXXX03",
        amount=500,
        due_date="2020-01-01",
        status="paused",
        tone_level=1,
    )
    assert is_promise_eligible_for_call(p3) is False

    p4 = Promise(
        id="p4",
        customer_id="cust4",
        customer_name="D",
        customer_phone_raw="9800000004",
        customer_phone_masked="98XXXXXX04",
        amount=500,
        due_date="2020-01-01",
        status="broken",
        tone_level=1,
    )
    assert is_promise_eligible_for_call(p4) is True

    # Suppressed phone check
    assert is_promise_eligible_for_call(p4, suppressed_phones={"9800000004"}) is False

    # Outbound hours check
    assert is_promise_eligible_for_call(p4, is_outbound_open=False) is False



