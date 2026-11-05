"""
apps/api/app/brain/mock_evon.py
Mock OpenAI-compatible HTTP server and direct helper simulating Gnani Evon v3.3 vLLM endpoint.
Used for offline benchmarking and unit testing fallback behavior when no GPU is available.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import FastAPI, HTTPException, Request

mock_evon_app = FastAPI(title="Mock Evon vLLM Endpoint")

# Simulation flags for tests
simulated_timeout = False
simulated_error = False


def mock_evon_infer(utterance: str) -> dict[str, Any]:
    """Pure Python mock extraction logic matching Evon v3.3 extraction schema."""
    u_lower = utterance.lower().strip()

    problem_key = "unknown"
    problem = None
    landmark = None
    slot = None
    name = None
    is_emergency = False
    emergency_type = None
    intents = []

    # 1. Problem detection
    if any(k in u_lower for k in ["garam nahi", "thanda", "coil", "element", "heating", "गर्म नहीं", "ठंडा"]):
        problem_key = "geyser_not_heating"
        problem = "Geyser Heating Issue"
    elif any(k in u_lower for k in ["leak", "leek", "tapak", "boond", "pani gir", "टपक", "लीक"]):
        problem_key = "geyser_leak"
        problem = "Geyser Water Leakage"
    elif any(k in u_lower for k in ["pipe phat", "pipe burst"]):
        problem_key = "pipe_burst"
        problem = "Pipe Burst Repair"
    elif any(k in u_lower for k in ["nal", "toti", "नल"]):
        problem_key = "tap_leak"
        problem = "Tap Leakage Fix"
    elif any(k in u_lower for k in ["sink", "naali", "drain", "jam", "चोक"]):
        problem_key = "drain_blocked"
        problem = "Drain Blockage"
    elif any(k in u_lower for k in ["motor", "pump", "tanki", "मोटर"]):
        problem_key = "motor_pump"
        problem = "Motor Pump Issue"

    # 2. Emergency hazard detection
    if any(k in u_lower for k in ["current", "shock", "jhatka", "करंट", "झटका"]):
        is_emergency = True
        emergency_type = "electric"
        intents.append("emergency_hazard")
    elif any(k in u_lower for k in ["aag", "dhuan", "gas", "smoke", "fire", "आग", "धुआं"]):
        is_emergency = True
        emergency_type = "fire_gas"
        intents.append("emergency_hazard")
    elif any(k in u_lower for k in ["flood", "paani bhar gaya", "पानी भर गया"]):
        is_emergency = True
        emergency_type = "flooding"
        intents.append("emergency_hazard")

    # 3. Global intents
    if any(k in u_lower for k in ["robot", "ai", "machine", "रोबोट"]):
        intents.append("are_you_a_robot")
    if any(k in u_lower for k in ["malik", "owner", "human", "मालिक"]):
        intents.append("human_request")
    if any(k in u_lower for k in ["mehenga", "kam karo", "sau mein", "kitna lagega"]):
        intents.append("bargaining")
    if any(k in u_lower for k in ["haan", "theek hai", "pakka", "bhej do", "confirm"]):
        intents.append("yes")
    if any(k in u_lower for k in ["rehne do", "cancel", "nahi chahiye"]):
        intents.append("no")
    if any(k in u_lower for k in ["nahi nahi", "galat", "badal do"]):
        intents.append("correction")
    if any(k in u_lower for k in ["ek minute", "ruko", "hold"]):
        intents.append("wait")

    # 4. Landmark detection
    areas = [
        "saket", "mayur vihar", "karol bagh", "lajpat nagar", "dwarka", "pitampura",
        "janakpuri", "malviya nagar", "noida", "laxmi nagar", "साकेत", "करोल बाग", "मयूर विहार"
    ]
    for a in areas:
        if a in u_lower:
            landmark = a.title()
            if "ke peeche" in u_lower or "के पीछे" in u_lower:
                landmark += " ke peeche"
            elif "pocket" in u_lower:
                landmark += " Pocket"
            elif "block" in u_lower:
                landmark += " Block A"
            elif "metro" in u_lower:
                landmark += " near metro"
            break

    # 5. Slot detection
    if "kal shaam" in u_lower:
        slot = "Kal Shaam (5 PM – 7 PM)"
    elif "aaj shaam" in u_lower or "आज शाम" in u_lower:
        slot = "Aaj Shaam (5 PM – 7 PM)"
    elif "kal subah" in u_lower:
        slot = "Kal Subah (9 AM – 11 AM)"
    elif "aaj dopahar" in u_lower:
        slot = "Aaj Dopahar (1 PM – 3 PM)"
    elif "chhe baje" in u_lower:
        slot = "6 Baje"
    elif "turant" in u_lower or "emergency" in u_lower:
        slot = "Immediate / Emergency"
    elif "kal" in u_lower:
        slot = "Kal"
    elif "aaj" in u_lower:
        slot = "Aaj"

    return {
        "problem": problem,
        "problem_key": problem_key,
        "landmark_address": landmark,
        "time_slot": slot,
        "name": name,
        "intents": intents,
        "confidence": 0.94 if problem_key != "unknown" else 0.55,
        "is_emergency": is_emergency,
        "emergency_type": emergency_type,
    }


@mock_evon_app.post("/v1/chat/completions")
async def chat_completions(req: Request) -> dict[str, Any]:
    """Simulate vLLM /v1/chat/completions endpoint for Evon v3.3."""
    global simulated_timeout, simulated_error

    if simulated_timeout:
        import asyncio
        await asyncio.sleep(5.0)  # Exceeds 2.0s timeout

    if simulated_error:
        raise HTTPException(status_code=500, detail="Simulated GPU CUDA OOM")

    body = await req.json()
    messages = body.get("messages", [])
    user_prompt = ""
    for m in messages:
        if m.get("role") == "user":
            user_prompt = m.get("content", "")

    # Parse utterance from prompt
    match = re.search(r'caller utterance: "(.*?)"', user_prompt, re.IGNORECASE)
    utterance = match.group(1) if match else user_prompt
    result_json = mock_evon_infer(utterance)

    return {
        "id": "mock_chatcmpl_001",
        "object": "chat.completion",
        "model": "gnani/gnani-evon-v3.3-30B-A3B",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(result_json),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 45,
            "total_tokens": 165,
        },
    }
