"""
Deterministic Booking Finite State Machine (FSM).
Coordinates caller turns, slot filling, quotes, handoffs, and terminal states.
No LLM involved in call-flow decisions. Response latency < 10 ms.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.brain.extractor import ExtractionResult, RuleBasedExtractor
from app.brain.replies import (
    ASK_ADDRESS,
    ASK_PROBLEM,
    ASK_SLOT,
    BARGAINING_HOLD,
    BOOKING_SUCCESS,
    CALL_ABANDONED,
    HANDOFF_MESSAGE,
    REASK_ADDRESS,
    REASK_PROBLEM,
    REASK_SLOT,
    ROBOT_DISCLOSURE,
    SILENCE_PROMPT_1,
    SILENCE_PROMPT_2,
    format_confirm_readback,
    format_quote_reply,
    format_quote_unknown,
)

logger = logging.getLogger(__name__)

DEFAULT_PRICING: dict[str, tuple[int, int]] = {
    "geyser_not_heating": (450, 750),
    "geyser_leak": (350, 600),
    "tap_leak": (150, 250),
    "pipe_burst": (300, 500),
    "drain_blocked": (400, 800),
    "motor_pump": (500, 1200),
}


class BookingState(str, Enum):
    """Explicit states of the booking conversation."""

    GREETING = "GREETING"
    ASK_PROBLEM = "ASK_PROBLEM"
    ASK_ADDRESS = "ASK_ADDRESS"
    ASK_SLOT = "ASK_SLOT"
    QUOTE = "QUOTE"
    CONFIRM_READBACK = "CONFIRM_READBACK"
    BOOKED = "BOOKED"
    HANDOFF = "HANDOFF"
    ABANDONED = "ABANDONED"


@dataclass
class BookingSlots:
    """Slots gathered across the conversation."""

    problem: str | None = None
    problem_key: str | None = None
    landmark_address: str | None = None
    time_slot: str | None = None
    customer_name: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    price_estimate: str | None = None


@dataclass
class BrainTurnResult:
    """Output generated from processing one caller utterance."""

    bot_reply: str
    current_state: BookingState
    slots: BookingSlots
    is_terminal: bool = False
    needs_handoff: bool = False
    ai_disclosure_triggered: bool = False
    job_payload: dict[str, Any] | None = None


class BookingFSM:
    """
    Finite State Machine driving the booking dialogue.
    Handles multiple slots in single utterance, corrections, bargaining,
    robot inquiries, re-ask thresholds, and silence timeouts.
    """

    def __init__(
        self,
        handoff_phone: str = "+91 98765 43210",
        price_catalog: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        self.state: BookingState = BookingState.GREETING
        self.slots = BookingSlots()
        self.extractor = RuleBasedExtractor()
        self.handoff_phone = handoff_phone
        self.pricing = price_catalog or DEFAULT_PRICING

        self.reask_counts: dict[str, int] = {
            "problem": 0,
            "address": 0,
            "slot": 0,
        }
        self.silence_count: int = 0
        self.turns_count: int = 0
        self.asked_quote_once: bool = False
        self.ai_disclosure_given: bool = False

    def process_utterance(self, utterance: str) -> BrainTurnResult:
        """Process one caller turn and return the deterministic response."""
        self.turns_count += 1

        # If already in terminal state, stay terminal
        if self.state in (BookingState.BOOKED, BookingState.HANDOFF, BookingState.ABANDONED):
            reply = (
                BOOKING_SUCCESS
                if self.state == BookingState.BOOKED
                else (
                    HANDOFF_MESSAGE.format(phone=self.handoff_phone)
                    if self.state == BookingState.HANDOFF
                    else CALL_ABANDONED
                )
            )
            return BrainTurnResult(
                bot_reply=reply,
                current_state=self.state,
                slots=self.slots,
                is_terminal=True,
                needs_handoff=(self.state == BookingState.HANDOFF),
            )

        extraction = self.extractor.extract(utterance, state=self.state)

        # 1. Handle Silence
        if "silence" in extraction.intents:
            self.silence_count += 1
            if self.silence_count == 1:
                return BrainTurnResult(
                    bot_reply=SILENCE_PROMPT_1,
                    current_state=self.state,
                    slots=self.slots,
                )
            self.state = BookingState.ABANDONED
            return BrainTurnResult(
                bot_reply=SILENCE_PROMPT_2,
                current_state=self.state,
                slots=self.slots,
                is_terminal=True,
            )

        # Reset silence counter on speech
        self.silence_count = 0

        # 2. Priority: Sincere Robot/AI Inquiry -> Answer Honestly
        if "are_you_a_robot" in extraction.intents and not self.ai_disclosure_given:
            self.ai_disclosure_given = True
            logger.info("AI non-denial disclosure triggered by caller inquiry.")
            return BrainTurnResult(
                bot_reply=ROBOT_DISCLOSURE,
                current_state=self.state,
                slots=self.slots,
                ai_disclosure_triggered=True,
            )

        # 3. Priority: Human Request
        if "human_request" in extraction.intents:
            self.state = BookingState.HANDOFF
            return BrainTurnResult(
                bot_reply=HANDOFF_MESSAGE.format(phone=self.handoff_phone),
                current_state=self.state,
                slots=self.slots,
                is_terminal=True,
                needs_handoff=True,
            )

        # 4. Priority: Explicit Refusal / Cancellation
        if "no" in extraction.intents:
            self.state = BookingState.ABANDONED
            return BrainTurnResult(
                bot_reply=CALL_ABANDONED,
                current_state=self.state,
                slots=self.slots,
                is_terminal=True,
            )

        # 5. Slot Ingestion (multi-slot supported at any state)
        if extraction.problem_key:
            self.slots.problem_key = extraction.problem_key
            self.slots.problem = extraction.problem
            self._apply_pricing()

        if extraction.landmark_address:
            self.slots.landmark_address = extraction.landmark_address

        if extraction.time_slot:
            self.slots.time_slot = extraction.time_slot

        if extraction.name:
            self.slots.customer_name = extraction.name

        # 6. Priority: Bargaining Handling
        if "bargaining" in extraction.intents:
            return BrainTurnResult(
                bot_reply=BARGAINING_HOLD,
                current_state=self.state,
                slots=self.slots,
            )

        # 7. State Transitions based on Missing Slots
        return self._transition(extraction)

    def _apply_pricing(self) -> None:
        """Lookup price range from pricing catalog."""
        if self.slots.problem_key and self.slots.problem_key in self.pricing:
            p_min, p_max = self.pricing[self.slots.problem_key]
            self.slots.price_min = p_min
            self.slots.price_max = p_max
            self.slots.price_estimate = f"₹{p_min} – ₹{p_max}"
        else:
            self.slots.price_min = None
            self.slots.price_max = None
            self.slots.price_estimate = "Inspection visit quote"

    def _transition(self, extraction: ExtractionResult) -> BrainTurnResult:
        """Determine next state and formulate reply."""
        # Check missing slots in order: Problem -> Address -> Slot
        missing_problem = not self.slots.problem
        missing_address = not self.slots.landmark_address
        missing_slot = not self.slots.time_slot

        # If problem missing
        if missing_problem:
            self.reask_counts["problem"] += 1
            if self.reask_counts["problem"] > 2:
                self.state = BookingState.HANDOFF
                return BrainTurnResult(
                    bot_reply=HANDOFF_MESSAGE.format(phone=self.handoff_phone),
                    current_state=self.state,
                    slots=self.slots,
                    is_terminal=True,
                    needs_handoff=True,
                )
            self.state = BookingState.ASK_PROBLEM
            reply = ASK_PROBLEM if self.reask_counts["problem"] == 1 else REASK_PROBLEM
            return BrainTurnResult(bot_reply=reply, current_state=self.state, slots=self.slots)

        # If address missing
        if missing_address:
            self.reask_counts["address"] += 1
            if self.reask_counts["address"] > 2:
                self.state = BookingState.HANDOFF
                return BrainTurnResult(
                    bot_reply=HANDOFF_MESSAGE.format(phone=self.handoff_phone),
                    current_state=self.state,
                    slots=self.slots,
                    is_terminal=True,
                    needs_handoff=True,
                )
            self.state = BookingState.ASK_ADDRESS
            reply = ASK_ADDRESS if self.reask_counts["address"] == 1 else REASK_ADDRESS
            return BrainTurnResult(bot_reply=reply, current_state=self.state, slots=self.slots)

        # If time slot missing
        if missing_slot:
            self.reask_counts["slot"] += 1
            if self.reask_counts["slot"] > 2:
                self.state = BookingState.HANDOFF
                return BrainTurnResult(
                    bot_reply=HANDOFF_MESSAGE.format(phone=self.handoff_phone),
                    current_state=self.state,
                    slots=self.slots,
                    is_terminal=True,
                    needs_handoff=True,
                )
            self.state = BookingState.ASK_SLOT
            reply = ASK_SLOT if self.reask_counts["slot"] == 1 else REASK_SLOT
            return BrainTurnResult(bot_reply=reply, current_state=self.state, slots=self.slots)

        # All slots collected! Now quote price if not done yet
        if not self.asked_quote_once:
            self.asked_quote_once = True
            self.state = BookingState.QUOTE
            if self.slots.price_min and self.slots.price_max:
                reply = format_quote_reply(self.slots.price_min, self.slots.price_max)
            else:
                reply = format_quote_unknown()
            return BrainTurnResult(bot_reply=reply, current_state=self.state, slots=self.slots)

        # If caller said yes or confirm after quote
        if "yes" in extraction.intents or self.state == BookingState.QUOTE:
            if self.state == BookingState.QUOTE:
                # Transition to Confirm Readback
                self.state = BookingState.CONFIRM_READBACK
                reply = format_confirm_readback(
                    problem=self.slots.problem or "Repair",
                    address=self.slots.landmark_address or "Apke address",
                    slot=self.slots.time_slot or "Scheduled time",
                )
                return BrainTurnResult(bot_reply=reply, current_state=self.state, slots=self.slots)

            if self.state == BookingState.CONFIRM_READBACK:
                # Confirmed! Booked state reached
                self.state = BookingState.BOOKED
                job_payload = {
                    "title": self.slots.problem,
                    "problem": self.slots.problem,
                    "landmark_address": self.slots.landmark_address,
                    "time_slot": self.slots.time_slot,
                    "customer_name": self.slots.customer_name or "Caller",
                    "price_estimate": self.slots.price_estimate or "Standard rates",
                    "price_min": self.slots.price_min or 250,
                    "price_max": self.slots.price_max or 500,
                    "status": "booked",
                }
                return BrainTurnResult(
                    bot_reply=BOOKING_SUCCESS,
                    current_state=self.state,
                    slots=self.slots,
                    is_terminal=True,
                    job_payload=job_payload,
                )

        # Fallback readback
        reply = format_confirm_readback(
            problem=self.slots.problem or "Repair",
            address=self.slots.landmark_address or "Apke address",
            slot=self.slots.time_slot or "Scheduled time",
        )
        return BrainTurnResult(bot_reply=reply, current_state=self.state, slots=self.slots)
