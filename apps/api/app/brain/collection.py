"""
Collection Brain FSM for Pakka Payment Reminders.
Deterministic state machine handling debt recovery phone conversations.
Employs a multi-tier tone ladder, extracts payment commitments,
and gracefully routes disputes, callbacks, and wrong numbers.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.brain.replies_collection import (
    ALREADY_PAID_REPLY,
    CALLBACK_REPLY,
    DISPUTE_REPLY,
    OWNER_HANDOFF_REPLY,
    REASK_DATE_REPLY,
    REFUSED_REPLY,
    ROBOT_DISCLOSURE_REPLY,
    SILENCE_REPLY,
    WRONG_NUMBER_REPLY,
    get_balance_statement,
    get_collection_greeting,
    get_promise_confirmation,
)

logger = logging.getLogger("pakka.collection")


class CollectionState(str, Enum):
    """Dialogue states for debt collection call flow."""

    GREETING = "GREETING"
    CONFIRM_IDENTITY = "CONFIRM_IDENTITY"
    STATE_BALANCE = "STATE_BALANCE"
    CAPTURE_DATE = "CAPTURE_DATE"
    CONFIRM_PROMISE = "CONFIRM_PROMISE"
    TERMINAL = "TERMINAL"


class CollectionDisposition(str, Enum):
    """Final outcome classification of collection interaction."""

    PTP = "PTP"  # Promise to Pay agreed
    PAID = "PAID"  # Customer claims already paid
    DISPUTE = "DISPUTE"  # Service quality dispute
    WRONG_NUMBER = "WRONG_NUMBER"  # Number is incorrect / reassigned
    CALLBACK = "CALLBACK"  # Customer busy, requested callback
    REFUSED = "REFUSED"  # Customer explicitly refuses payment
    NEEDS_OWNER = "NEEDS_OWNER"  # Escalation requested to human owner
    NO_ANSWER = "NO_ANSWER"


@dataclass
class CollectionTurnResult:
    """Outcome of processing one utterance in Collection Brain."""

    bot_reply: str
    current_state: CollectionState
    is_terminal: bool = False
    disposition: CollectionDisposition | None = None
    captured_date: str | None = None
    suppress_number: bool = False
    needs_owner: bool = False


class CollectionFSM:
    """
    Deterministic Finite State Machine managing conversational payment recovery.
    Runs in < 5 ms with zero LLM dependence.
    """

    def __init__(
        self,
        customer_name: str = "Ramesh",
        balance: int = 500,
        tone_level: int = 1,
        business_name: str = "Sharma Plumbing",
    ) -> None:
        self.customer_name = customer_name
        self.balance = balance
        self.tone_level = tone_level
        self.business_name = business_name
        self.state: CollectionState = CollectionState.GREETING
        self.disposition: CollectionDisposition | None = None
        self.captured_date: str | None = None
        self.turn_count: int = 0
        self.ai_disclosure_given: bool = False

    def process_utterance(self, utterance: str) -> CollectionTurnResult:
        """Process caller turn through state transitions."""
        self.turn_count += 1
        text = utterance.strip().lower()

        # Handle Terminal State
        if self.state == CollectionState.TERMINAL:
            return CollectionTurnResult(
                bot_reply="Dhanyawaad ji.",
                current_state=self.state,
                is_terminal=True,
                disposition=self.disposition,
                captured_date=self.captured_date,
            )

        # 1. Global Silence
        if not text or text == "__silence__":
            return CollectionTurnResult(
                bot_reply=SILENCE_REPLY,
                current_state=self.state,
                is_terminal=False,
            )

        # 2. Global AI / Robot Inquiry
        if re.search(r"(are you (a |an )?(robot|ai)|kya aap robot ho|machine ho|computer ho)", text):
            if not self.ai_disclosure_given:
                self.ai_disclosure_given = True
                return CollectionTurnResult(
                    bot_reply=ROBOT_DISCLOSURE_REPLY,
                    current_state=self.state,
                    is_terminal=False,
                )

        # 3. Global Wrong Number
        if re.search(
            r"(galat number|wrong number|wrong no|galat lag gaya|kisi aur ka hai|galat number hai|galat phone)",
            text,
        ):
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.WRONG_NUMBER
            return CollectionTurnResult(
                bot_reply=WRONG_NUMBER_REPLY,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.WRONG_NUMBER,
                suppress_number=True,
            )

        # 4. Global Already Paid Claim
        if re.search(
            r"(pay kar diya|paise de diye|maine to de diya|already paid|payment ho gaya|online bhej diya|cash de diya|de chuka hoon|transfer kar diya)",
            text,
        ):
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.PAID
            return CollectionTurnResult(
                bot_reply=ALREADY_PAID_REPLY,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.PAID,
            )

        # 5. Global Dispute / Work Quality Complaint
        if re.search(
            r"(kaam theek nahi|kharab kar diya|phir se kharab|paani abhi bhi tapak|bekaar|bilkul bekaar|band pada hai|shikayat|problem aa rahi|dispute|thik se nahi banaya)",
            text,
        ):
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.DISPUTE
            return CollectionTurnResult(
                bot_reply=DISPUTE_REPLY,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.DISPUTE,
                needs_owner=True,
            )

        # 6. Global Callback / Currently Busy
        if re.search(
            r"(busy hoon|baad mein baat|drive kar raha|meeting mein|baad mein phone|shaam ko call|abhi nahi|call back|baad mein karo)",
            text,
        ):
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.CALLBACK
            return CollectionTurnResult(
                bot_reply=CALLBACK_REPLY,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.CALLBACK,
            )

        # 7. Global Escalation to Human / Owner Request
        if re.search(
            r"(malik se baat|owner se baat|kisi insaan se|kisi aadmi se|talk to owner|sharma ji se baat)",
            text,
        ):
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.NEEDS_OWNER
            return CollectionTurnResult(
                bot_reply=OWNER_HANDOFF_REPLY,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.NEEDS_OWNER,
                needs_owner=True,
            )

        # 8. Global Refusal
        if re.search(
            r"(nahi dunga|nahi deta|paisa nahi hai|koi payment nahi|bhul jao|ek rupaya nahi|nahi dena)",
            text,
        ):
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.REFUSED
            return CollectionTurnResult(
                bot_reply=REFUSED_REPLY,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.REFUSED,
                needs_owner=True,
            )

        # Date Detection (supported at any dialogue state)
        extracted_date = self._extract_promise_date(text)
        if extracted_date:
            self.captured_date = extracted_date
            self.state = CollectionState.TERMINAL
            self.disposition = CollectionDisposition.PTP
            reply = get_promise_confirmation(
                self.customer_name,
                self.captured_date,
                tone_level=self.tone_level,
            )
            return CollectionTurnResult(
                bot_reply=reply,
                current_state=self.state,
                is_terminal=True,
                disposition=CollectionDisposition.PTP,
                captured_date=self.captured_date,
            )

        # State-based Dialogue Navigation
        if self.state == CollectionState.GREETING:
            # Caller responds to greeting (e.g. "haan bolo", "haan main bol raha hoon", "kya baat hai")
            # State the balance and ask when they can pay
            self.state = CollectionState.CAPTURE_DATE
            reply = get_balance_statement(self.balance, tone_level=self.tone_level)
            return CollectionTurnResult(
                bot_reply=reply,
                current_state=self.state,
            )

        if self.state in (CollectionState.STATE_BALANCE, CollectionState.CAPTURE_DATE):
            # If user just agreed generally without specific date (e.g. "haan kar dunga", "ho jayegi")
            if re.search(r"^(haan|ho jayegi|kar dunga|theek hai|yes|bilkul)$", text):
                self.state = CollectionState.CAPTURE_DATE
                return CollectionTurnResult(
                    bot_reply=REASK_DATE_REPLY,
                    current_state=self.state,
                )

            # Unrecognized date input
            return CollectionTurnResult(
                bot_reply=REASK_DATE_REPLY,
                current_state=self.state,
            )

        return CollectionTurnResult(
            bot_reply="Dhanyawaad.",
            current_state=CollectionState.TERMINAL,
            is_terminal=True,
            disposition=self.disposition,
        )

    def _extract_promise_date(self, text: str) -> str | None:
        """Parse natural Hinglish date references into normalized spoken dates."""
        if re.search(r"\b(aaj|aaj shaam|aaj raat|today)\b", text):
            return "aaj shaam"
        if re.search(r"\b(kal subah|kal morning)\b", text):
            return "kal subah"
        if re.search(r"\b(kal shaam|kal sham|kal evening)\b", text):
            return "kal shaam"
        if re.search(r"\b(kal|tomorrow)\b", text):
            return "kal"
        if re.search(r"\b(parson|day after tomorrow)\b", text):
            return "parson"
        if re.search(r"\b(somwar|monday)\b", text):
            return "somwar"
        if re.search(r"\b(mangalwar|tuesday)\b", text):
            return "mangalwar"
        if re.search(r"\b(budhwar|wednesday)\b", text):
            return "budhwar"
        if re.search(r"\b(guruwar|veervar|thursday)\b", text):
            return "guruwar"
        if re.search(r"\b(shukrawar|friday)\b", text):
            return "shukrawar"
        if re.search(r"\b(shaniwar|saturday)\b", text):
            return "shaniwar"
        if re.search(r"\b(itwar|ravivar|sunday)\b", text):
            return "ravivar"
        if re.search(r"\b(weekend|hafte ke aakhir)\b", text):
            return "weekend"

        # Explicit numeric date e.g. "15 tareekh", "10 ko", "do din baad"
        date_match = re.search(r"(\d{1,2})\s*(tareekh|tarikh|ko|date)", text)
        if date_match:
            return f"{date_match.group(1)} tareekh"

        days_later = re.search(r"(\w+|\d+)\s*din baad", text)
        if days_later:
            return f"{days_later.group(1)} din baad"

        return None
