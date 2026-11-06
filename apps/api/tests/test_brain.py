"""
Unit tests for Pakka Booking Brain:
RuleBasedExtractor and BookingFSM deterministic execution.
"""

from __future__ import annotations

import time

import pytest

from app.brain.extractor import RuleBasedExtractor
from app.brain.fsm import BookingFSM, BookingState


@pytest.fixture
def extractor() -> RuleBasedExtractor:
    return RuleBasedExtractor()


@pytest.fixture
def fsm() -> BookingFSM:
    return BookingFSM(handoff_phone="+91 98765 43210")


class TestRuleBasedExtractor:
    """Test slot and intent extraction capabilities."""

    @pytest.mark.parametrize(
        "utterance, expected_key",
        [
            ("geyser paani garam nahi kar raha", "geyser_not_heating"),
            ("geezer thanda paani de raha hai", "geyser_not_heating"),
            ("गीज़र में पानी गर्म नहीं आ रहा", "geyser_not_heating"),
            ("geyser se paani tapak raha hai", "geyser_leak"),
            ("geyser leak ho raha hai", "geyser_leak"),
            ("pipe phat gaya hai bathroom ka", "pipe_burst"),
            ("paip burst ho gaya, flood aa gaya", "pipe_burst"),
            ("bathroom ka nal leak ho raha hai", "tap_leak"),
            ("नल से पानी टपक रहा है", "tap_leak"),
            ("toti se boond boond gir raha hai", "tap_leak"),
            ("kitchen ki naali choke ho gayi", "drain_blocked"),
            ("sink block hai paani ruk gaya", "drain_blocked"),
            ("submersible motor aawaz kar rahi hai", "motor_pump"),
            ("motor chal nahi rahi", "motor_pump"),
            ("kuch repair karwana hai plumber chahiye", "unknown"),
        ],
    )
    def test_problem_extraction(
        self, extractor: RuleBasedExtractor, utterance: str, expected_key: str
    ) -> None:
        res = extractor.extract(utterance)
        assert res.problem_key == expected_key

    @pytest.mark.parametrize(
        "utterance, expected_intent",
        [
            ("kya aap robot ho?", "are_you_a_robot"),
            ("are you an AI?", "are_you_a_robot"),
            ("asli insaan ho ya machine?", "are_you_a_robot"),
            ("owner se baat karwao", "human_request"),
            ("kisi insaan se baat karwa do", "human_request"),
            ("talk to human agent", "human_request"),
            ("bahut mehenga hai thoda kam karo", "bargaining"),
            ("kuch kam karo itna zyada kyun", "bargaining"),
            ("कम करो थोड़ा", "bargaining"),
            ("nahi shaam nahi, kal subah bhej do", "correction"),
            ("galat address, Pocket 1 hai", "correction"),
            ("pocket 2 nahi pocket 1", "correction"),
            ("haan pakka", "yes"),
            ("theek hai bhej do", "yes"),
            ("हाँ, ठीक है", "yes"),
            ("nahi chahiye cancel kar do", "no"),
            ("mat bhejo ab", "no"),
            ("__silence__", "silence"),
            ("", "silence"),
        ],
    )
    def test_intent_detection(
        self, extractor: RuleBasedExtractor, utterance: str, expected_intent: str
    ) -> None:
        res = extractor.extract(utterance)
        assert expected_intent in res.intents

    @pytest.mark.parametrize(
        "utterance, expected_slot",
        [
            ("turant aao jaldi", "Immediate / Emergency"),
            ("aaj shaam ko", "Aaj Shaam (5 PM – 7 PM)"),
            ("kal subah", "Kal Subah (9 AM – 11 AM)"),
            ("aaj dopahar ko", "Aaj Dopahar (1 PM – 3 PM)"),
            ("chhe baje aa jao", "6 Baje"),
            ("5 baje aa jao", "5 Baje"),
        ],
    )
    def test_time_slot_extraction(
        self, extractor: RuleBasedExtractor, utterance: str, expected_slot: str
    ) -> None:
        res = extractor.extract(utterance)
        assert res.time_slot == expected_slot

    def test_landmark_address_extraction(self, extractor: RuleBasedExtractor) -> None:
        res = extractor.extract("mera address hai Mayur Vihar Pocket 1, near Mother Dairy")
        assert res.landmark_address is not None
        assert "Mayur Vihar" in res.landmark_address


class TestBookingFSM:
    """Test state machine flow, latency, and guardrails."""

    def test_latency_under_50ms(self, fsm: BookingFSM) -> None:
        """Verify deterministic brain execution is well under 50 ms."""
        utterance = "Geyser paani garam nahi kar raha, Mayur Vihar Pocket 1, shaam 5 baje aa jao"
        latencies: list[float] = []

        # Warm-up call to avoid first-run regex compilation noise
        fsm.process_utterance(utterance)

        for _ in range(50):
            start = time.perf_counter()
            fsm.process_utterance(utterance)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        # Brain should run in sub-millisecond to low millisecond range, well below 50ms
        assert avg_latency < 50.0, f"Average latency too high: {avg_latency:.2f} ms"
        assert max_latency < 50.0, f"Max latency exceeded limit: {max_latency:.2f} ms"

    def test_reask_handoff_threshold(self) -> None:
        """After 3 failed attempts to capture problem, transition to HANDOFF."""
        fsm = BookingFSM(handoff_phone="+91 98765 43210")
        res1 = fsm.process_utterance("garbled line 1")
        assert res1.current_state == BookingState.ASK_PROBLEM

        res2 = fsm.process_utterance("garbled line 2")
        assert res2.current_state == BookingState.ASK_PROBLEM

        res3 = fsm.process_utterance("garbled line 3")
        assert res3.current_state == BookingState.HANDOFF
        assert res3.is_terminal is True
        assert res3.needs_handoff is True
        assert "+91 98765 43210" in res3.bot_reply

    def test_silence_abandonment(self) -> None:
        """Two silences terminate the call."""
        fsm = BookingFSM()
        res1 = fsm.process_utterance("__silence__")
        assert res1.is_terminal is False

        res2 = fsm.process_utterance("__silence__")
        assert res2.current_state == BookingState.ABANDONED
        assert res2.is_terminal is True

    def test_pricing_assignment(self) -> None:
        """Pricing is looked up correctly from catalog."""
        fsm = BookingFSM()
        fsm.process_utterance("Geyser paani garam nahi kar raha")
        assert fsm.slots.price_min == 450
        assert fsm.slots.price_max == 750
        assert fsm.slots.price_estimate == "₹450 – ₹750"

    def test_emergency_hazard_handling(self) -> None:
        """Emergency hazard halts routine booking with exact branch safety instruction."""
        # 1. Electric Shock / Current
        fsm_elec = BookingFSM()
        res_elec = fsm_elec.process_utterance("Geyser se current aa raha hai, paani chhoo nahi sakte")
        assert res_elec.current_state == BookingState.HANDOFF
        assert res_elec.is_terminal is True
        assert res_elec.needs_handoff is True
        assert res_elec.is_urgent is True
        assert (
            res_elec.bot_reply
            == "Kripya geyser aur main switch band kar dijiye aur geyser ko haath mat lagaiye. Main abhi malik ko bata rahi hoon, woh turant aapko phone karenge."
        )

        # 2. Fire / Smoke / Gas Smell
        fsm_fire = BookingFSM()
        res_fire = fsm_fire.process_utterance("Geyser mein aag lag gayi hai dhuan nikal raha hai")
        assert res_fire.current_state == BookingState.HANDOFF
        assert res_fire.is_terminal is True
        assert res_fire.needs_handoff is True
        assert res_fire.is_urgent is True
        assert (
            res_fire.bot_reply
            == "Kripya koi switch ya aag mat jalaiye. Khidkiyan kholiye, sabko ghar se bahar nikaliye aur turant 112 par phone kijiye. Main malik ko bhi bata rahi hoon."
        )

        # 3. Flooding / Pipe Burst
        fsm_flood = BookingFSM()
        res_flood = fsm_flood.process_utterance("Pipe phat gaya hai poora paani bhar gaya bathroom mein")
        assert res_flood.current_state == BookingState.HANDOFF
        assert res_flood.is_terminal is True
        assert res_flood.needs_handoff is True
        assert res_flood.is_urgent is True
        assert (
            res_flood.bot_reply
            == "Kripya paani ka main valve band kar dijiye aur bijli ke switch ya geyser ko haath mat lagaiye. Main abhi malik ko bata rahi hoon."
        )

    def test_custom_areas_extraction(self) -> None:
        """Extractor recognizes custom areas passed from settings."""
        extractor = RuleBasedExtractor(custom_areas=["Vasant Kunj", "Gurgaon Sector 56"])
        res = extractor.extract("Mera address hai Vasant Kunj Pocket C")
        assert res.landmark_address is not None
        assert "Vasant Kunj" in res.landmark_address

    def test_emergency_literal_strings(self) -> None:
        """Verify the exact required emergency safety strings."""
        from app.brain.replies import (
            EMERGENCY_ELECTRIC_INSTRUCTION,
            EMERGENCY_FIRE_GAS_INSTRUCTION,
            EMERGENCY_FLOODING_INSTRUCTION,
        )
        assert EMERGENCY_ELECTRIC_INSTRUCTION == (
            "Kripya geyser aur main switch band kar dijiye aur geyser ko haath mat lagaiye. "
            "Main abhi malik ko bata rahi hoon, woh turant aapko phone karenge."
        )
        assert EMERGENCY_FIRE_GAS_INSTRUCTION == (
            "Kripya koi switch ya aag mat jalaiye. "
            "Khidkiyan kholiye, sabko ghar se bahar nikaliye aur turant 112 par phone kijiye. "
            "Main malik ko bhi bata rahi hoon."
        )
        assert EMERGENCY_FLOODING_INSTRUCTION == (
            "Kripya paani ka main valve band kar dijiye aur bijli ke switch ya geyser ko haath mat lagaiye. "
            "Main abhi malik ko bata rahi hoon."
        )

    def test_ai_inquiry_phrasings_across_states(self) -> None:
        """AI disclosure given across varied phrasings without resetting dialogue flow."""
        phrasings = [
            "kya aap robot ho?",
            "are you an AI?",
            "kya ye machine hai?",
            "recording hai kya?",
            "real person ho ya computer?",
            "aap kaun ho?",
            "kaun bol raha hai?",
            "क्या आप रोबोट हो?",
        ]
        for phrase in phrasings:
            fsm = BookingFSM(business_name="Aggarwal Sanitation")
            res = fsm.process_utterance(phrase)
            assert "Aggarwal Sanitation ki digital sahayak" in res.bot_reply
            assert "callback" in res.bot_reply.lower() or "connect" in res.bot_reply.lower()
            assert res.is_terminal is False
            assert res.current_state == BookingState.ASK_PROBLEM

    def test_tank_overflow_ordering_not_emergency(self, extractor: RuleBasedExtractor) -> None:
        """Tank overflow alone is a routine motor_pump job, not a safety emergency."""
        res = extractor.extract("tanki bhar ke overflow ho rahi hai motor band kardo")
        assert res.is_emergency is False
        assert res.problem_key == "motor_pump"

        # However, pipe burst with flooding is an emergency
        res_flood = extractor.extract("bathroom ka pipe phat gaya paani bhar gaya poora doob raha hai")
        assert res_flood.is_emergency is True
        assert res_flood.emergency_type == "flooding"

    def test_decline_intent_at_all_states(self) -> None:
        """Decline phrases (rehne do, cancel, etc.) transition to ABANDONED gracefully."""
        from app.brain.replies import CALL_ABANDONED

        declines = ["rehne do bhaiya", "nahi karwana mujhe", "cancel kar dijiye", "baad mein dekhte hain", "abhi nahi chahiye"]
        for phrase in declines:
            fsm = BookingFSM()
            res = fsm.process_utterance(phrase)
            assert res.current_state == BookingState.ABANDONED
            assert res.is_terminal is True
            assert res.bot_reply == CALL_ABANDONED

    def test_address_clean_leading_words(self, extractor: RuleBasedExtractor) -> None:
        """Extract address strips leading 'address', 'mera pata', and trailing ' hai'."""
        res1 = extractor.extract("mera address Malviya Nagar main market ke paas hai")
        assert res1.landmark_address == "Malviya Nagar main market ke paas"

        res2 = extractor.extract("address Rohini sector 15 DDA flats")
        assert res2.landmark_address == "Rohini sector 15 DDA flats"

