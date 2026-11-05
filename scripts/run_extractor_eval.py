"""
scripts/run_extractor_eval.py
Automated comparative evaluation benchmark for Pakka extractors:
- Rules (RuleBasedExtractor)
- Evon v3.3 (EvonExtractor: live if reachable, else mock with PENDING USER note)
- Hybrid (HybridExtractor: rules first, Evon on unrecognized turns)

Evaluates on:
1. Main Booking Scenarios (28 scenarios)
2. Holdout Evaluation Set (10 scenarios)
3. Noisy STT Scenarios (30 scenarios)

Outputs structured metrics to apps/api/reports/extractor_comparison.json.
"""

from __future__ import annotations

import argparse
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
from app.brain.mock_evon import mock_evon_app
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
    items: list[dict[str, Any]],
    mode: str = "dialogue",
) -> dict[str, Any]:
    """Run an extractor across a scenario dataset and measure accuracy and latency."""
    latencies: list[float] = []
    total_slots = 0
    correct_slots = 0
    total_items = len(items)
    passed_items = 0

    for item in items:
        if mode == "dialogue":
            # Multi-turn dialogue: accumulate extracted slots across turns
            dialogue = item.get("dialogue", [])
            expected = item.get("expected", {})
            accumulated: dict[str, Any] = {
                "problem": None,
                "problem_key": None,
                "landmark_address": None,
                "time_slot": None,
                "name": None,
                "is_emergency": False,
                "intents": set(),
            }
            item_slots_ok = True

            for turn in dialogue:
                user_text = turn.get("user", "")
                t0 = time.perf_counter()
                res = extractor.extract(user_text)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(elapsed_ms)

                if res.problem:
                    accumulated["problem"] = res.problem
                if res.problem_key:
                    accumulated["problem_key"] = res.problem_key
                if res.landmark_address:
                    accumulated["landmark_address"] = res.landmark_address
                if res.time_slot:
                    accumulated["time_slot"] = res.time_slot
                if res.name:
                    accumulated["name"] = res.name
                if res.is_emergency:
                    accumulated["is_emergency"] = True
                accumulated["intents"].update(res.intents)

            # Check expected slots against accumulated turn slots
            exp_slots = expected.get("slots", {})
            for k, exp_val in exp_slots.items():
                total_slots += 1
                act_val = accumulated.get(k)
                if act_val == exp_val:
                    correct_slots += 1
                else:
                    item_slots_ok = False

            if expected.get("is_urgent"):
                total_slots += 1
                if accumulated["is_emergency"] or "emergency_hazard" in accumulated["intents"]:
                    correct_slots += 1
                else:
                    item_slots_ok = False

            if item_slots_ok:
                passed_items += 1

        elif mode == "noisy":
            # Single utterance with intent/problem check
            utterance = item.get("utterance", "")
            expected = item.get("expected", {})
            t0 = time.perf_counter()
            res = extractor.extract(utterance)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

            item_ok = True
            if "problem_key" in expected:
                total_slots += 1
                if res.problem_key == expected["problem_key"]:
                    correct_slots += 1
                else:
                    item_ok = False

            if "is_emergency" in expected:
                total_slots += 1
                if res.is_emergency == expected["is_emergency"]:
                    correct_slots += 1
                else:
                    item_ok = False

            if "emergency_type" in expected:
                total_slots += 1
                if res.emergency_type == expected["emergency_type"]:
                    correct_slots += 1
                else:
                    item_ok = False

            if "intent" in expected:
                total_slots += 1
                if expected["intent"] in res.intents:
                    correct_slots += 1
                else:
                    item_ok = False

            if "landmark_contains" in expected:
                total_slots += 1
                if res.landmark_address and expected["landmark_contains"].lower() in res.landmark_address.lower():
                    correct_slots += 1
                else:
                    item_ok = False

            if item_ok:
                passed_items += 1

    slot_acc = (correct_slots / total_slots * 100.0) if total_slots else 100.0
    pass_rate = (passed_items / total_items * 100.0) if total_items else 100.0
    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies or [0.0])
    mean_lat = statistics.mean(latencies) if latencies else 0.0

    return {
        "total_items": total_items,
        "passed_items": passed_items,
        "pass_rate_percent": round(pass_rate, 1),
        "total_slots": total_slots,
        "correct_slots": correct_slots,
        "slot_accuracy_percent": round(slot_acc, 1),
        "latency_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
        },
    }


def run_benchmark() -> dict[str, Any]:
    """Run full comparative suite."""
    print("==================================================================")
    print("PAKKA EXTRACTOR COMPARATIVE BENCHMARK: Rules vs Evon vs Hybrid")
    print("==================================================================")

    main_scenarios = load_yaml(SCENARIOS_DIR / "booking.yaml")
    holdout_scenarios = load_yaml(SCENARIOS_DIR / "holdout.yaml")
    noisy_scenarios = load_yaml(SCENARIOS_DIR / "stt_noisy.yaml")

    print(f"Loaded {len(main_scenarios)} main booking scenarios")
    print(f"Loaded {len(holdout_scenarios)} holdout scenarios")
    print(f"Loaded {len(noisy_scenarios)} noisy STT scenarios")

    # Check live Evon
    live_evon_online = check_evon_live(settings.evon_base_url)
    evon_status_label = "LIVE vLLM" if live_evon_online else "PENDING USER: requires GPU with vLLM (port 8001)"
    print(f"\nEvon Service Status: {evon_status_label}")

    # Build extractors
    rules_ext = RuleBasedExtractor()

    # For offline testing when no GPU is present, use mock Evon extractor
    if not live_evon_online:
        from app.brain.mock_evon import mock_evon_infer

        class MockEvonExtractor(EvonExtractor):
            def _call_evon(self, text: str, state: Any = None):
                # Simulate realistic LLM inference delay (~25ms)
                time.sleep(0.025)
                parsed = mock_evon_infer(text)
                return ExtractionResult(
                    problem=parsed.get("problem"),
                    problem_key=parsed.get("problem_key"),
                    landmark_address=parsed.get("landmark_address"),
                    time_slot=parsed.get("time_slot"),
                    name=parsed.get("name"),
                    intents=parsed.get("intents", []),
                    confidence=float(parsed.get("confidence", 0.90)),
                    is_emergency=bool(parsed.get("is_emergency", False)),
                    emergency_type=parsed.get("emergency_type"),
                    updated_fields=["problem"] if parsed.get("problem_key") != "unknown" else [],
                )

        evon_ext = MockEvonExtractor(base_url="http://mock-evon:8001/v1")
        hybrid_ext = HybridExtractor(rules_extractor=rules_ext, evon_extractor=evon_ext)
    else:
        evon_ext = EvonExtractor()
        hybrid_ext = HybridExtractor(rules_extractor=rules_ext, evon_extractor=evon_ext)

    extractors = [
        ("rules", "RuleBasedExtractor", rules_ext, "LIVE: deterministic regex"),
        ("evon", "Evon v3.3 (vLLM)", evon_ext, evon_status_label),
        ("hybrid", "HybridExtractor", hybrid_ext, "LIVE: rules-first with Evon fallback"),
    ]

    benchmark_results: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "evon_online": live_evon_online,
        "evon_status": evon_status_label,
        "sample_sizes": {
            "main_booking_scenarios": len(main_scenarios),
            "holdout_scenarios": len(holdout_scenarios),
            "noisy_stt_scenarios": len(noisy_scenarios),
        },
        "extractors": {},
    }

    for ext_key, ext_name, extractor, status_desc in extractors:
        print(f"\n>>> Evaluating {ext_name} [{status_desc}] ...")
        res_main = evaluate_dataset(extractor, main_scenarios, mode="dialogue")
        res_holdout = evaluate_dataset(extractor, holdout_scenarios, mode="dialogue")
        res_noisy = evaluate_dataset(extractor, noisy_scenarios, mode="noisy")

        # Overall aggregate score
        total_slots_all = res_main["total_slots"] + res_holdout["total_slots"] + res_noisy["total_slots"]
        correct_slots_all = res_main["correct_slots"] + res_holdout["correct_slots"] + res_noisy["correct_slots"]
        overall_accuracy = (correct_slots_all / total_slots_all * 100.0) if total_slots_all else 100.0

        benchmark_results["extractors"][ext_key] = {
            "name": ext_name,
            "status": status_desc,
            "overall_slot_accuracy_percent": round(overall_accuracy, 1),
            "main_scenarios": res_main,
            "holdout_scenarios": res_holdout,
            "noisy_stt_scenarios": res_noisy,
        }

        print(f"  Main Scenarios Pass Rate:    {res_main['pass_rate_percent']}% (Slot Acc: {res_main['slot_accuracy_percent']}%, Latency p50: {res_main['latency_ms']['p50']} ms)")
        print(f"  Holdout Scenarios Pass Rate: {res_holdout['pass_rate_percent']}% (Slot Acc: {res_holdout['slot_accuracy_percent']}%)")
        print(f"  Noisy STT Pass Rate:         {res_noisy['pass_rate_percent']}% (Accuracy: {res_noisy['slot_accuracy_percent']}%, Latency p50: {res_noisy['latency_ms']['p50']} ms)")
        print(f"  --> Combined Slot Accuracy:  {overall_accuracy:.1f}%")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Benchmark results saved to: {OUTPUT_FILE}")
    return benchmark_results


if __name__ == "__main__":
    run_benchmark()
