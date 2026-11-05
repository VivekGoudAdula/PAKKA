"""
scripts/evon_probe.py
Connectivity and inference probe for Gnani Evon v3.3 vLLM server.
Tests connectivity, verifies temperature/top_p parameters, and parses structured output.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install via 'pip install httpx'.")
    sys.exit(1)

from app.brain.evon_extractor import EXTRACTION_JSON_SCHEMA, SYSTEM_PROMPT


def probe_evon(base_url: str = "http://localhost:8001/v1", model: str = "gnani/gnani-evon-v3.3-30B-A3B") -> bool:
    """Probe the vLLM server for Evon v3.3 health and structured extraction."""
    print(f"[*] Probing Evon vLLM server at: {base_url}")
    print(f"[*] Target model: {model}")

    clean_url = base_url.rstrip("/")

    # 1. Test /models endpoint
    try:
        t0 = time.perf_counter()
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{clean_url}/models")
            ping_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code == 200:
            models_data = resp.json()
            available = [m.get("id") for m in models_data.get("data", [])]
            print(f"  [+] Server reachable ({ping_ms:.1f} ms)")
            print(f"  [+] Available models: {available}")
        else:
            print(f"  [-] Server responded with HTTP {resp.status_code}")
            return False
    except Exception as exc:
        print(f"  [-] Server unreachable at {clean_url}: {type(exc).__name__}")
        print("  [!] Status: PENDING USER (requires GPU instance with vLLM serving Evon v3.3 on port 8001)")
        return False

    # 2. Test extraction completion
    test_utterance = "bhaiya geyser thanda paani de raha hai, Saket Block A mein rehte hain"
    print(f"\n[*] Sending test utterance: '{test_utterance}'")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract slots from caller utterance: \"{test_utterance}\""},
        ],
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 512,
        "enable_thinking": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": EXTRACTION_JSON_SCHEMA,
        },
    }

    try:
        t0 = time.perf_counter()
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{clean_url}/chat/completions", json=payload)
            inf_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code == 200:
            res_data = resp.json()
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            print(f"  [+] Inference succeeded in {inf_ms:.1f} ms")
            print(f"  [+] Structured Output:\n{json.dumps(parsed, indent=2)}")
            return True
        else:
            print(f"  [-] Inference failed with HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as exc:
        print(f"  [-] Inference error: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Evon vLLM server")
    parser.add_argument("--url", default="http://localhost:8001/v1", help="Evon base URL")
    parser.add_argument("--model", default="gnani/gnani-evon-v3.3-30B-A3B", help="Model name")
    args = parser.parse_args()

    ok = probe_evon(base_url=args.url, model=args.model)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

