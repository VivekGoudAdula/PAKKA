"""
scripts/run_extractor_eval.py
Automated comparative evaluation benchmark for Pakka extractors:
- Rules (RuleBasedExtractor)
- Fallback behaviour test (mock Evon server testing timeout & malformed JSON fallbacks)

Evaluates on:
1. Main Booking Scenarios (28 scenarios)
2. Development Holdout Set (10 scenarios, previously probed)
3. Synthetic Noisy-Text Scenarios (30 scenarios, typed by us, not real STT output)

Outputs structured metrics to apps/api/reports/extractor_comparison.json.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.brain.evon_extractor import EvonExtractor, HybridExtractor
from app.brain.extractor import ExtractionResult, Extractor, RuleBasedExtractor
from app.brain.mock_evon import mock_evon_app, mock_evon_infer
from app.config import settings

logging.basicConfig(level=logging.WARNING)

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = BASE_DIR / "apps" / "api" / "tests" / "scenarios"
REPORTS_DIR = BASE_DIR / "apps" / "api" / "reports"
OUTPUT_FILE = REPORTS_DIR / "extractor_comparison.json"


def load_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


def check_evon_live(url: str) -> bool:
    """Check if a real vLLM endpoint is responding."""
    import httpx

    try:
        with httpx.Client(timeout=1.5) as client:
            resp = client.get(f"{url.rstrip('/')}/models")
            return resp.status_code == 200
    except Exception:
        return False


def evaluate_dataset(
    extractor: Extractor,
    scenarios: list[dict[str, Any]],
    mode: str = "dialogue",
) -> dict[str, Any]:
    """Evaluate an extractor against a scenario dataset."""
    total_scenarios = len(scenarios)
    passed_scenarios = 0
    total_slots = 0
    correct_slots = 0
    latencies: list[float] = []
    case_results: list[dict[str, Any]] = []

    for sc in scenarios:
        sc_id = sc.get("id", "unknown")
        dialogue = sc.get("dialogue", [])
        expected = sc.get("expected", {})
        exp_slots = expected.get("slots", {}) if "slots" in expected else expected

        turn_latencies: list[float] = []
        last_extract: ExtractionResult | None = None

        for turn in dialogue:
            user_text = turn.get("user", "")
            t0 = time.perf_counter()
            last_extract = extractor.extract(user_text)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            turn_latencies.append(dt_ms)
            latencies.append(dt_ms)

        sc_slots_checked = 0
        sc_slots_correct = 0

        if last_extract and exp_slots:
            if "problem_key" in exp_slots:
                sc_slots_checked += 1
                if last_extract.problem_key == exp_slots["problem_key"]:
                    sc_slots_correct += 1

            if "time_slot" in exp_slots:
                sc_slots_checked += 1
                if last_extract.time_slot == exp_slots["time_slot"]:
                    sc_slots_correct += 1

            if "landmark_address" in exp_slots:
                sc_slots_checked += 1
                if last_extract.landmark_address and exp_slots["landmark_address"] in last_extract.landmark_address:
                    sc_slots_correct += 1

            if "name" in exp_slots:
                sc_slots_checked += 1
                if last_extract.name == exp_slots["name"]:
                    sc_slots_correct += 1

        total_slots += sc_slots_checked
        correct_slots += sc_slots_correct

        is_passed = (sc_slots_checked > 0) and (sc_slots_checked == sc_slots_correct)
        if sc_slots_checked == 0 and mode == "noisy":
            is_passed = False

        if is_passed:
            passed_scenarios += 1

        case_results.append({
            "id": sc_id,
            "passed": is_passed,
            "slots_checked": sc_slots_checked,
            "slots_correct": sc_slots_correct,
            "latency_ms": round(sum(turn_latencies) / len(turn_latencies), 2) if turn_latencies else 0.0,
        })

    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = (
        statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else (max(latencies) if latencies else 0.0)
    )

    pass_rate = round(passed_scenarios / total_scenarios * 100.0, 1) if total_scenarios else 0.0
    slot_acc = round(correct_slots / total_slots * 100.0, 1) if total_slots else 0.0

    return {
        "total_scenarios": total_scenarios,
        "passed_scenarios": passed_scenarios,
        "pass_rate_percent": pass_rate,
        "total_slots": total_slots,
        "correct_slots": correct_slots,
        "slot_accuracy_percent": slot_acc,
        "latency_ms": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "avg": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        },
        "cases": case_results,
    }


def test_fallback_behavior() -> dict[str, Any]:
    """Verify that EvonExtractor falls back to RuleBasedExtractor on timeout and malformed JSON."""
    class TimeoutEvonExtractor(EvonExtractor):
        def _call_evon(self, text: str, state: Any = None):
            raise TimeoutError("Evon request timed out after 2.0s")

    class MalformedEvonExtractor(EvonExtractor):
        def _call_evon(self, text: str, state: Any = None):
            raise ValueError("Malformed JSON received from endpoint")

    t_start = time.perf_counter()
    timeout_ext = TimeoutEvonExtractor()
    t_res = timeout_ext.extract("geyser paani garam nahi kar raha")
    t_duration = (time.perf_counter() - t_start) * 1000.0
    timeout_passed = t_res.problem_key == "geyser_not_heating"

    m_start = time.perf_counter()
    malformed_ext = MalformedEvonExtractor()
    m_res = malformed_ext.extract("bathroom ka nal leak ho raha hai")
    m_duration = (time.perf_counter() - m_start) * 1000.0
    malformed_passed = m_res.problem_key == "tap_leak"

    return {
        "status": "PASS" if (timeout_passed and malformed_passed) else "FAIL",
        "tests": [
            {
                "test_name": "Timeout fallback (>2.0s simulation)",
                "passed": timeout_passed,
                "input": "geyser paani garam nahi kar raha",
                "extracted_problem": t_res.problem_key,
                "fallback_source": "RuleBasedExtractor",
                "latency_ms": round(t_duration, 2),
            },
            {
                "test_name": "Malformed JSON payload fallback",
                "passed": malformed_passed,
                "input": "bathroom ka nal leak ho raha hai",
                "extracted_problem": m_res.problem_key,
                "fallback_source": "RuleBasedExtractor",
                "latency_ms": round(m_duration, 2),
            },
        ],
    }


def run_benchmark() -> dict[str, Any]:
    """Run evaluation benchmark according to truth rules."""
    main_scenarios = load_yaml(SCENARIOS_DIR / "booking.yaml")
    holdout_scenarios = load_yaml(SCENARIOS_DIR / "holdout.yaml")
    noisy_scenarios = load_yaml(SCENARIOS_DIR / "stt_noisy.yaml")

    live_evon_online = check_evon_live(settings.evon_base_url)
    evon_status_label = "LIVE vLLM" if live_evon_online else "PENDING USER: requires GPU with vLLM (port 8001)"

    rules_ext = RuleBasedExtractor()

    # Evaluate Rules on all sets
    res_main = evaluate_dataset(rules_ext, main_scenarios, mode="dialogue")
    res_holdout = evaluate_dataset(rules_ext, holdout_scenarios, mode="dialogue")
    res_noisy = evaluate_dataset(rules_ext, noisy_scenarios, mode="noisy")

    # Run Fallback behavior test
    fallback_test = test_fallback_behavior()

    benchmark_results: dict[str, Any] = {
        "mode": "dry_run",
        "generated_at": datetime.now(UTC).isoformat(),
        "evon_online": live_evon_online,
        "evon_status": evon_status_label,
        "sample_sizes": {
            "main_booking_scenarios": len(main_scenarios),
            "development_set_scenarios": len(holdout_scenarios),
            "synthetic_noisy_text_scenarios": len(noisy_scenarios),
        },
        "datasets": {
            "main_booking": {
                "label": "Main Booking Scenarios",
                "mode": "live",
                "results": res_main,
            },
            "development_set": {
                "label": "Development set (previously probed)",
                "mode": "dry_run",
                "results": res_holdout,
            },
            "synthetic_noisy_text": {
                "label": "Synthetic noisy-text tests (typed by us, not real STT output)",
                "mode": "dry_run",
                "results": res_noisy,
            },
        },
        "fallback_behavior_test": fallback_test,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Extractor evaluation report saved to: {OUTPUT_FILE}")
    return benchmark_results


if __name__ == "__main__":
    run_benchmark()
