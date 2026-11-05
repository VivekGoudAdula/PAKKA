"""
apps/api/app/brain/evon_extractor.py
Evon v3.3 Extractor and Hybrid Extractor implementations for Pakka.

Integrates Gnani Evon v3.3 (running via vLLM OpenAI-compatible /v1/chat/completions)
behind the standard Extractor protocol.
Strict constraints:
1. Evon is ONLY an extractor: it never generates caller replies or drives FSM transitions.
2. Evon call parameters: temperature 0.6, top_p 0.95, enable_thinking: false, structured JSON output.
3. Fallback: On network error, invalid JSON, or timeout (> 2.0s), gracefully falls back to RuleBasedExtractor.
4. Hybrid mode: Rules run first in < 2ms; Evon is queried ONLY if problem is unrecognized or required slots are missing.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.brain.extractor import ExtractionResult, Extractor, RuleBasedExtractor
from app.config import settings

logger = logging.getLogger("pakka.evon_extractor")

# Structured JSON Schema for Evon extraction
EXTRACTION_JSON_SCHEMA = {
    "name": "ExtractionResult",
    "schema": {
        "type": "object",
        "properties": {
            "problem": {"type": ["string", "null"]},
            "problem_key": {
                "type": ["string", "null"],
                "enum": [
                    "geyser_not_heating",
                    "geyser_leak",
                    "pipe_burst",
                    "tap_leak",
                    "drain_blocked",
                    "motor_pump",
                    "unknown",
                    None,
                ],
            },
            "landmark_address": {"type": ["string", "null"]},
            "time_slot": {"type": ["string", "null"]},
            "name": {"type": ["string", "null"]},
            "intents": {
                "type": "array",
                "items": {"type": "string"},
            },
            "confidence": {"type": "number"},
            "is_emergency": {"type": "boolean"},
            "emergency_type": {
                "type": ["string", "null"],
                "enum": ["electric", "fire_gas", "flooding", None],
            },
        },
        "required": ["problem_key", "intents", "confidence", "is_emergency"],
        "additionalProperties": False,
    },
    "strict": True,
}

SYSTEM_PROMPT = """You are a specialized intent and entity slot extractor for Pakka, an Indian plumbing and geyser repair service assistant.
Analyze caller utterances (spoken in Hinglish, Hindi, or English codemix) and extract structured slots.

Slots to extract:
- problem_key: one of ["geyser_not_heating", "geyser_leak", "pipe_burst", "tap_leak", "drain_blocked", "motor_pump", "unknown"]
- problem: Human-readable problem summary
- landmark_address: Delhi NCR locality or landmark address (e.g. "Saket ke peeche", "Mayur Vihar Pocket 1")
- time_slot: Preferred service time (e.g. "Aaj Shaam", "Kal Subah", "6 Baje")
- name: Customer name if provided
- intents: List of flags among ["emergency_hazard", "are_you_a_robot", "human_request", "bargaining", "correction", "yes", "no"]
- is_emergency: true if immediate danger (electric shock/current/sparks, gas smell/smoke/fire, or severe flooding/pipe burst)
- emergency_type: "electric", "fire_gas", "flooding", or null
- confidence: float between 0.0 and 1.0

Return ONLY valid JSON matching the specified schema. Do NOT talk to the caller. Do NOT generate conversational replies."""


class EvonExtractor:
    """
    Extractor powered by Gnani Evon v3.3 served via vLLM OpenAI-compatible endpoint.
    Safely falls back to RuleBasedExtractor on any timeout, connection failure, or JSON parse error.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        fallback_extractor: Extractor | None = None,
    ) -> None:
        self.base_url = (base_url or settings.evon_base_url).rstrip("/")
        self.model = model or settings.evon_model
        self.timeout_seconds = timeout_seconds or settings.evon_timeout_seconds
        self.fallback = fallback_extractor or RuleBasedExtractor()
        self.last_latency_ms: float = 0.0
        self.last_fallback_triggered: bool = False

    def extract(self, utterance: str, state: Any = None) -> ExtractionResult:
        """Extract slots and intents from caller utterance using Evon v3.3 with rule fallback."""
        text = utterance.strip()
        if not text or text == "__silence__":
            return self.fallback.extract(utterance, state=state)

        start_time = time.perf_counter()
        try:
            result = self._call_evon(text, state)
            self.last_latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.last_fallback_triggered = False
            return result
        except Exception as exc:
            self.last_latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.last_fallback_triggered = True
            logger.warning(
                "Evon extraction failed or timed out (%.1f ms): %s; falling back to RuleBasedExtractor",
                self.last_latency_ms,
                exc,
            )
            return self.fallback.extract(utterance, state=state)

    def _call_evon(self, text: str, state: Any = None) -> ExtractionResult:
        """Synchronous HTTP call to vLLM OpenAI-compatible completions endpoint."""
        url = f"{self.base_url}/chat/completions"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract slots from caller utterance: \"{text}\""},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": 512,
            "enable_thinking": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": EXTRACTION_JSON_SCHEMA,
            },
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Empty choices array received from Evon server")

        raw_content = choices[0].get("message", {}).get("content", "")
        parsed = json.loads(raw_content)

        updated_fields = []
        if parsed.get("problem_key") and parsed.get("problem_key") != "unknown":
            updated_fields.append("problem")
        if parsed.get("landmark_address"):
            updated_fields.append("landmark_address")
        if parsed.get("time_slot"):
            updated_fields.append("time_slot")
        if parsed.get("name"):
            updated_fields.append("name")

        return ExtractionResult(
            problem=parsed.get("problem"),
            problem_key=parsed.get("problem_key"),
            landmark_address=parsed.get("landmark_address"),
            time_slot=parsed.get("time_slot"),
            name=parsed.get("name"),
            intents=parsed.get("intents", []),
            confidence=float(parsed.get("confidence", 0.85)),
            updated_fields=updated_fields,
            is_emergency=bool(parsed.get("is_emergency", False)),
            emergency_type=parsed.get("emergency_type"),
        )


class HybridExtractor:
    """
    Hybrid Extractor: Runs RuleBasedExtractor first (< 2ms).
    If a problem is recognized and required slots for the turn are present, returns immediately.
    Invokes Evon v3.3 ONLY if the problem is unrecognized or a required slot remains missing.
    """

    def __init__(
        self,
        rules_extractor: RuleBasedExtractor | None = None,
        evon_extractor: EvonExtractor | None = None,
    ) -> None:
        self.rules = rules_extractor or RuleBasedExtractor()
        self.evon = evon_extractor or EvonExtractor(fallback_extractor=self.rules)
        self.last_latency_ms: float = 0.0
        self.evon_invoked: bool = False

    def extract(self, utterance: str, state: Any = None) -> ExtractionResult:
        """Execute hybrid two-stage extraction."""
        t0 = time.perf_counter()

        # Step 1: Run fast deterministic rules first
        rule_res = self.rules.extract(utterance, state=state)

        # Check if rules found emergency or clear intents
        if rule_res.is_emergency or "emergency_hazard" in rule_res.intents:
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
            self.evon_invoked = False
            return rule_res

        # If rules captured problem or address/time, evaluate whether Evon is needed
        problem_missing = not rule_res.problem_key or rule_res.problem_key == "unknown"
        has_user_speech = bool(utterance.strip()) and utterance.strip() != "__silence__"

        # If rules succeeded with a recognized problem or slots, don't waste LLM cycle
        if not problem_missing and rule_res.confidence >= 0.8:
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
            self.evon_invoked = False
            return rule_res

        # Step 2: Query Evon only if caller spoke and rules left critical fields missing
        if has_user_speech and (problem_missing or not rule_res.updated_fields):
            self.evon_invoked = True
            evon_res = self.evon.extract(utterance, state=state)

            # Merge: Prefer Evon for problem if rules missed it; preserve rule landmarks/intents
            merged_res = ExtractionResult(
                problem=evon_res.problem or rule_res.problem,
                problem_key=evon_res.problem_key
                if evon_res.problem_key and evon_res.problem_key != "unknown"
                else rule_res.problem_key,
                landmark_address=evon_res.landmark_address or rule_res.landmark_address,
                time_slot=evon_res.time_slot or rule_res.time_slot,
                name=evon_res.name or rule_res.name,
                intents=list(dict.fromkeys(rule_res.intents + evon_res.intents)),
                confidence=max(rule_res.confidence, evon_res.confidence),
                is_emergency=rule_res.is_emergency or evon_res.is_emergency,
                emergency_type=rule_res.emergency_type or evon_res.emergency_type,
            )
            merged_res.updated_fields = list(
                dict.fromkeys(rule_res.updated_fields + evon_res.updated_fields)
            )
            self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
            return merged_res

        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0
        self.evon_invoked = False
        return rule_res


def get_extractor(extractor_type: str | None = None) -> Extractor:
    """
    Factory function returning the configured Extractor instance:
    - 'rules': Fast deterministic rule-based extractor (< 2ms)
    - 'evon': Evon LLM extractor with rule-based fallback
    - 'hybrid': Rules first, Evon on unrecognized turns
    """
    choice = (extractor_type or settings.extractor).lower().strip()
    if choice == "evon":
        return EvonExtractor()
    if choice == "hybrid":
        return HybridExtractor()
    return RuleBasedExtractor()

