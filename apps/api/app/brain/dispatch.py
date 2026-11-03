"""
Deterministic Technician Voice Dispatch FSM and Cascading Dispatch Coordinator.
Handles outbound call dialogue with technicians, job readout, voice acceptance/rejection,
and cascading fallback across available specialists.
Zero LLM in dispatch dialogue control; response latency < 5 ms.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum

from app.models.domain import Job, Technician

logger = logging.getLogger(__name__)


class DispatchState(str, Enum):
    """Explicit states of the technician dispatch dialogue."""

    DISPATCH_GREETING = "DISPATCH_GREETING"
    LISTENING = "LISTENING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    UNCLEAR = "UNCLEAR"
    UNREACHABLE = "UNREACHABLE"


DISPATCH_DISCLOSURE_GREETING = (
    "Namaste {name} ji, Pakka demo shop ki digital sahayak bol rahi hoon. "
    "Ek naya kaam hai. {problem}, {address}, {slot}. Kya aap kar sakte hain?"
)

DISPATCH_REPEAT_READOUT = (
    "Main dobara bata deti hoon: {problem}, {address}, {slot}. "
    "Kya aap yeh kaam kar sakte hain?"
)

DISPATCH_UNCLEAR_REASK = (
    "Main theek se sun nahi paayi. Kya aap yeh kaam kar sakte hain? "
    "Haan ya nahi mein bataiye."
)

DISPATCH_ACCEPT_REPLY = "Dhanyavaad. Pakka. Main customer ko bata dungi."
DISPATCH_DECLINE_REPLY = "Theek hai ji, koi baat nahi. Agle kaam ke liye call karenge."


@dataclass
class DispatchTurnResult:
    """Outcome of processing one turn in technician dispatch dialogue."""

    bot_reply: str
    current_state: DispatchState
    is_terminal: bool = False
    is_accepted: bool = False
    is_declined: bool = False
    is_repeat: bool = False
    confidence: float = 0.95
    confirmation_phrase: str | None = None


class DispatchFSM:
    """
    Finite State Machine driving the outbound technician dispatch call.
    Reads job details aloud, recognizes haan/nahi/repeat, and terminates cleanly.
    """

    # Acceptance intents in Hinglish and Devanagari
    ACCEPT_PATTERNS: list[str] = [
        r"\b(haan|ha|haanji|ji haan|pakka|theek hai|thik hai|kar dunga|aa jaunga|chalega|bilkul|ho jayega|kar lenge|ok|okay|yes|sure|i will do it)\b",
        r"(हाँ|जी हाँ|पक्का|ठीक है|कर दूंगा|आ जाऊंगा|बिल्कुल|हो जाएगा|हाँ जी)",
    ]

    # Decline intents
    DECLINE_PATTERNS: list[str] = [
        r"^(nahi|na|no|nahi ji|ji nahi)$",
        r"\b(busy hoon|nahi ho payega|nahi ho paye|nahi kar sakta|nahi kar paunga|dusre ko bhej do|abhi possible nahi|possible nahi|mushkil hai|fursat nahi|dusri jagah|aaj nahi|abhi nahi|time nahi)\b",
        r"^(नहीं|ना|नहीं जी|जी नहीं)$",
        r"(व्यस्त हूँ|मुश्किल है|नहीं हो पाएगा|अभी नहीं|आज नहीं|फुर्सत नहीं)",
    ]

    # Repeat readout request
    REPEAT_PATTERNS: list[str] = [
        r"(dobara bolo|repeat karo|phir se bolo|kya bola|address kya tha|kya kaam tha|sunai nahi diya|ek baar aur|repeat)",
        r"(दोबारा बोलो|फिर से बोलो|सुनाई नहीं दिया|एड्रेस क्या था|क्या काम था|एक बार और)",
    ]

    def __init__(
        self,
        technician_name: str,
        problem: str,
        address: str,
        slot: str,
    ) -> None:
        self.technician_name = technician_name
        self.problem = problem
        self.address = address
        self.slot = slot

        self.state: DispatchState = DispatchState.DISPATCH_GREETING
        self.unclear_count: int = 0
        self.turns_count: int = 0
        self.confirmation_phrase: str | None = None
        self.confirmed_at: str | None = None

    def get_initial_greeting(self) -> str:
        """Return the mandatory AI disclosure greeting reading the job."""
        return DISPATCH_DISCLOSURE_GREETING.format(
            name=self.technician_name,
            problem=self.problem,
            address=self.address,
            slot=self.slot,
        )

    def process_utterance(self, utterance: str) -> DispatchTurnResult:
        """Process technician's spoken response."""
        self.turns_count += 1
        text = utterance.strip()
        text_lower = text.lower()
        clean = re.sub(r"[,।!?.]", " ", text_lower).strip()
        clean = re.sub(r"\s+", " ", clean)

        # 1. Check Repeat Request
        if self._matches(clean, self.REPEAT_PATTERNS):
            reply = DISPATCH_REPEAT_READOUT.format(
                problem=self.problem,
                address=self.address,
                slot=self.slot,
            )
            return DispatchTurnResult(
                bot_reply=reply,
                current_state=DispatchState.LISTENING,
                is_repeat=True,
            )

        # 2. Check Acceptance
        if self._matches(clean, self.ACCEPT_PATTERNS):
            self.state = DispatchState.ACCEPTED
            self.confirmation_phrase = text
            self.confirmed_at = time.strftime("%I:%M %p")
            logger.info(
                "Dispatch ACCEPTED by %s with phrase: '%s'",
                self.technician_name,
                text,
            )
            return DispatchTurnResult(
                bot_reply=DISPATCH_ACCEPT_REPLY,
                current_state=self.state,
                is_terminal=True,
                is_accepted=True,
                confirmation_phrase=text,
            )

        # 3. Check Decline
        if self._matches(clean, self.DECLINE_PATTERNS):
            self.state = DispatchState.DECLINED
            logger.info("Dispatch DECLINED by %s: '%s'", self.technician_name, text)
            return DispatchTurnResult(
                bot_reply=DISPATCH_DECLINE_REPLY,
                current_state=self.state,
                is_terminal=True,
                is_declined=True,
            )

        # 4. Handle Silence or Garbled / Unclear
        if not text or text == "__silence__":
            self.unclear_count += 1
        else:
            self.unclear_count += 1

        if self.unclear_count == 1:
            self.state = DispatchState.UNCLEAR
            return DispatchTurnResult(
                bot_reply=DISPATCH_UNCLEAR_REASK,
                current_state=self.state,
                is_terminal=False,
            )

        # Unclear twice -> treat as UNREACHABLE
        self.state = DispatchState.UNREACHABLE
        logger.warning(
            "Dispatch UNREACHABLE for %s after 2 unclear turns", self.technician_name
        )
        return DispatchTurnResult(
            bot_reply=DISPATCH_DECLINE_REPLY,
            current_state=self.state,
            is_terminal=True,
            is_declined=True,
        )

    def _matches(self, text: str, patterns: list[str]) -> bool:
        return any(re.search(p, text) for p in patterns)


# ==============================================================================
# Technician Cascading Selection Logic
# ==============================================================================


def rank_technicians_for_job(
    technicians: list[Technician],
    job: Job,
    declined_technician_ids: set[str] | None = None,
) -> list[Technician]:
    """
    Ranks available technicians for dispatch:
    1. Specialty match first (problem mentions geyser -> geyser specialist first).
    2. Then by fewest active jobs today.
    3. Excludes technicians who already declined this job or are off-duty.
    """
    declined_ids = declined_technician_ids or set()
    available = [
        t
        for t in technicians
        if t.status != "off_duty" and t.id not in declined_ids
    ]

    prob_low = (job.problem or "").lower()

    def sort_key(t: Technician) -> tuple[int, int]:
        spec = (getattr(t, "trade", "") or getattr(t, "specialty", "")).lower()
        # Specialty match rank: 0 is exact match, 1 is all-rounder, 2 is other
        if "geyser" in prob_low and "geyser" in spec or (
            "tap" in prob_low
            or "leak" in prob_low
            or "pipe" in prob_low
            or "drain" in prob_low
            or "water" in prob_low
        ) and ("plumb" in spec or "pipe" in spec):
            specialty_rank = 0
        elif "all" in spec or "general" in spec:
            specialty_rank = 1
        else:
            specialty_rank = 2

        active_jobs = getattr(t, "active_jobs_count", 0)
        return (specialty_rank, active_jobs)

    available.sort(key=sort_key)
    return available
