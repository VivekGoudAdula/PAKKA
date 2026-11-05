"""
Extractor interface and deterministic rule-based extractor for Pakka booking brain.
Handles both Latin transliteration and Devanagari script (STT codemix).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

AREAS_FILE = Path(__file__).parent / "data" / "areas.json"


def _load_default_areas() -> list[str]:
    """Load areas from data/areas.json with fallback."""
    if AREAS_FILE.exists():
        try:
            with open(AREAS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(a).lower() for a in data]
        except Exception:
            pass
    return [
        "mayur vihar",
        "karol bagh",
        "lajpat nagar",
        "saket",
        "rohini",
        "malviya nagar",
        "dwarka",
        "janakpuri",
        "patel nagar",
        "connaught place",
        "pitampura",
        "hauz khas",
        "laxmi nagar",
        "noida",
        "chhatarpur",
        "मयूर विहार",
        "करोल बाग",
        "लाजपत नगर",
        "साकेत",
        "रोहिणी",
    ]


@dataclass
class ExtractionResult:
    """Structured extraction outcome from caller utterance."""

    problem: str | None = None
    problem_key: str | None = None
    landmark_address: str | None = None
    time_slot: str | None = None
    name: str | None = None
    intents: list[str] = field(default_factory=list)
    confidence: float = 0.0
    updated_fields: list[str] = field(default_factory=list)
    is_emergency: bool = False
    emergency_type: str | None = None


class Extractor(Protocol):
    """Protocol for intent and slot extractors."""

    def extract(self, utterance: str, state: Any = None) -> ExtractionResult:
        """Extract slots and intents from utterance."""
        ...


class RuleBasedExtractor:
    """
    Deterministic rule-based extractor for Hinglish conversations.
    Supports both Latin transliteration and Devanagari script.
    Zero external network calls; executes in < 5 ms.
    """

    # Keyword mappings for Problem Detection
    PROBLEM_PATTERNS: list[tuple[str, str, list[str]]] = [
        (
            "geyser_not_heating",
            "Geyser Heating Issue",
            [
                r"(geyser|geezer|gijar|geeger|gizar|गीज़र|गीजर|गीज़र).*?(thanda|garam nahi|coil|element|heat|heating|चालू नहीं|ठंडा|गर्म नहीं)",
                r"(paani|pani|पानी).*?(thanda|garam nahi|ठंडा|गर्म नहीं).*?(geyser|geezer|gijar|गीज़र|गीजर)",
                r"(coil|heating element|थर्मोस्टेट).*?(kharab|dead|tripped|खराब)",
            ],
        ),
        (
            "geyser_leak",
            "Geyser Water Leakage",
            [
                r"(geyser|geezer|gijar|गीज़र|गीजर).*?(leak|leek|tapak|boond|paani gir|leakage|टपक|लीक|पानी गिर)",
                r"(leak|leek|tapak|लीक).*?(geyser|geezer|gijar|गीज़र|गीजर)",
            ],
        ),
        (
            "pipe_burst",
            "Pipe Burst Emergency",
            [
                r"(pipe|paip|पाइप).*?(burst|phat|flood|bahot paani|beh raha|फूट|फट|बह)",
                r"(burst|flooding|flood|पानी भर गया).*?(pipe|paip|bathroom|kitchen|पाइप)",
            ],
        ),
        (
            "tap_leak",
            "Tap Leakage",
            [
                r"(tap|nal|nalle|toti|totie|नल|टोटी).*?(leak|leek|tapak|boond|paani tapak|खराब|लीक|टपक)",
                r"(leak|leek|टपक).*?(tap|nal|nalle|toti|नल|टोटी)",
            ],
        ),
        (
            "drain_blocked",
            "Drain Blockage",
            [
                r"(drain|naali|nali|sink|sewer|नाली|ड्रेन|सिंक).*?(block|choke|chok|jaam|ruk gaya|जाम|चोक|अटका)",
                r"(paani jama|water logged|paani nikal nahi|पानी रुक).*?(naali|drain|kitchen|bathroom|नाली)",
            ],
        ),
        (
            "motor_pump",
            "Motor / Pump Issue",
            [
                r"(motor|motar|pump|submersible|मोटर|पंप).*?(chal|chalu|aawaz|pani nahi|kheench|kharab|खराब|आवाज)",
                r"(submersible|टुल्लू).*?(kharab|chal|खराब)",
            ],
        ),
    ]

    # Time slot regexes - specific kal/aaj combinations first
    TIME_PATTERNS: list[tuple[str, str]] = [
        (r"(turant|urgent|jaldi|abhi|right now|तुरंत|जल्दी|अभी)", "Immediate / Emergency"),
        (r"(kal subah|subah subah|tomorrow morning|कल सुबह)", "Kal Subah (9 AM – 11 AM)"),
        (r"(kal shaam|tomorrow evening|कल शाम)", "Kal Shaam (5 PM – 7 PM)"),
        (r"(kal dopahar|tomorrow afternoon|कल दोपहर)", "Kal Dopahar (1 PM – 3 PM)"),
        (r"(aaj shaam|shaam ko|sham ko|today evening|आज शाम|शाम को)", "Aaj Shaam (5 PM – 7 PM)"),
        (r"(aaj dopahar|dopahar ko|today afternoon|आज दोपहर)", "Aaj Dopahar (1 PM – 3 PM)"),
        (r"(parso|parson|day after tomorrow|परसों)", "Parso"),
        (r"(kal\b|tomorrow|कल\b)", "Kal"),
        (r"(aaj\b|today|आज\b)", "Aaj"),
        (
            r"(\b(\d{1,2}|chhe|saat|aath|nau|das|gyarah|barah|paanch|chaar|char|do|teen)\s*(baje|pm|am|बजे))",
            "",
        ),
    ]

    HINDI_NUMS: dict[str, str] = {
        "ek": "1",
        "do": "2",
        "teen": "3",
        "chaar": "4",
        "char": "4",
        "paanch": "5",
        "panch": "5",
        "chhe": "6",
        "saat": "7",
        "aath": "8",
        "nau": "9",
        "das": "10",
        "gyarah": "11",
        "barah": "12",
    }

    # Landmark address indicators
    LANDMARK_KEYWORDS: list[str] = [
        "ke paas",
        "ke peeche",
        "ke samne",
        "ke saamne",
        "ke bagal mein",
        "wali gali",
        "near",
        "behind",
        "opposite",
        "opp",
        "flat",
        "pocket",
        "block",
        "house",
        "sector",
        "gali no",
        "road",
        "के पास",
        "के पीछे",
        "के सामने",
        "वाली गली",
        "के बगल",
        "फ्लैट",
        "ब्लॉक",
        "पॉकेट",
        "गली",
    ]

    KNOWN_AREAS: list[str] = _load_default_areas()

    EMERGENCY_ELECTRIC_PATTERNS: list[str] = [
        r"(current aa raha|current lag raha|current lag|करंट)",
        r"(shock lag|electric shock|शॉक|बिजली का झटका)",
        r"(spark ho raha|sparking|sparks|चिनगारी|स्पार्क)",
    ]

    EMERGENCY_FIRE_GAS_PATTERNS: list[str] = [
        r"(aag lag gayi|aag lag|aag\b|आग लग|आग\b|fire)",
        r"(dhuan nikal raha|dhuan aa raha|dhuan\b|धुआं|धुआँ|smoke)",
        r"(gas smell|gas ki badbu|gas leak|गैस लीक|गैस की बदबू)",
        r"(cylinder|सिलेंडर)",
    ]

    EMERGENCY_FLOODING_PATTERNS: list[str] = [
        r"(pipe phat gaya.*?flood|pipe burst.*?flood)",
        r"(paani bhar gaya|पानी भर गया)",
        r"(flooding|flood\b)",
        r"(overflow|ओवरफ्लो)",
    ]

    EMERGENCY_PATTERNS: list[str] = (
        EMERGENCY_ELECTRIC_PATTERNS + EMERGENCY_FIRE_GAS_PATTERNS + EMERGENCY_FLOODING_PATTERNS
    )

    def __init__(self, custom_areas: list[str] | None = None) -> None:
        default_areas = _load_default_areas()
        if custom_areas:
            self.known_areas = list(
                dict.fromkeys(
                    default_areas + [a.lower().strip() for a in custom_areas if a.strip()]
                )
            )
        else:
            self.known_areas = default_areas

    def extract(self, utterance: str, state: Any = None) -> ExtractionResult:
        """Analyze caller utterance and extract slots and intent flags."""
        text = utterance.strip()
        text_lower = text.lower()
        res = ExtractionResult()

        if not text or text == "__silence__":
            res.intents.append("silence")
            return res

        # 1. Check Global Intents
        # 1a. Emergency Danger Hazard (Danger to life/property)
        emergency_type = self._check_emergency_type(text_lower)
        if emergency_type:
            res.intents.append("emergency_hazard")
            res.is_emergency = True
            res.emergency_type = emergency_type

        # 1b. Are you a robot / AI
        if self._check_robot_intent(text_lower):
            res.intents.append("are_you_a_robot")

        # 1c. Human / Owner request
        if self._check_human_request(text_lower):
            res.intents.append("human_request")

        # 1d. Bargaining / Price objection
        if self._check_bargaining(text_lower):
            res.intents.append("bargaining")

        # 1e. Correction
        if self._check_correction(text_lower):
            res.intents.append("correction")

        # 1f. Yes / Confirmation
        if self._check_yes(text_lower) and "correction" not in res.intents:
            res.intents.append("yes")

        # 1g. No / Refusal
        if self._check_no(text_lower) and "correction" not in res.intents:
            res.intents.append("no")

        # 2. Extract Problem
        problem_key, problem_title = self._extract_problem(text_lower)
        if problem_key:
            res.problem_key = problem_key
            res.problem = problem_title
            res.updated_fields.append("problem")

        # 3. Extract Time Slot
        time_slot = self._extract_time(text_lower)
        if time_slot:
            res.time_slot = time_slot
            res.updated_fields.append("time_slot")

        # 4. Extract Address
        address = self._extract_address(text, text_lower)
        if address:
            res.landmark_address = address
            res.updated_fields.append("landmark_address")

        # 5. Extract Customer Name (if asked in state or pattern detected)
        name = self._extract_name(text, text_lower, state)
        if name:
            res.name = name
            res.updated_fields.append("name")

        res.confidence = 0.9 if res.updated_fields or res.intents else 0.4
        return res

    def _check_emergency_type(self, text: str) -> str | None:
        """Categorize emergency danger into fire_gas, electric, or flooding."""
        if any(re.search(p, text) for p in self.EMERGENCY_FIRE_GAS_PATTERNS):
            return "fire_gas"
        if any(re.search(p, text) for p in self.EMERGENCY_ELECTRIC_PATTERNS):
            return "electric"
        if any(re.search(p, text) for p in self.EMERGENCY_FLOODING_PATTERNS):
            return "flooding"
        return None

    def _check_emergency(self, text: str) -> bool:
        return self._check_emergency_type(text) is not None

    def _check_robot_intent(self, text: str) -> bool:
        patterns = [
            r"are you (a |an )?(robot|ai|machine)",
            r"(kya )?(aap|tum) (robot|ai|machine|computer|बॉट|रोबोट|एआई)",
            r"(robot|machine|computer) bol raha",
            r"asli (insaan|aadmi) ho ya",
        ]
        return any(re.search(p, text) for p in patterns)

    def _check_human_request(self, text: str) -> bool:
        patterns = [
            r"(owner|malik|manager|insaan|human|aadmi|person).*?(se baat|ko phone|se milwao|bulao)",
            r"(kisi )?(insaan|human|owner) se baat karwa",
            r"talk to (a )?(human|manager|owner|person|agent)",
            r"(मालिक|ओनर|इंसान).*?(से बात)",
        ]
        return any(re.search(p, text) for p in patterns)

    def _check_bargaining(self, text: str) -> bool:
        patterns = [
            r"(kam karo|thoda kam|kuch kam|itna zyada|itna kyun|discount|mehenga|mehnga)",
            r"(कम करो|थोड़ा कम|ज्यादा है|महंगा|डिस्काउंट)",
            r"(\b\d{3,4}\b).*?(zyada|jyada|bahut)",
        ]
        return any(re.search(p, text) for p in patterns)

    def _check_correction(self, text: str) -> bool:
        patterns = [
            r"(nahi|na|no|गलत|नहीं)[,\s]+.*?(shaam nahi|subah|aaj nahi|kal|ye nahi|nahi ye)",
            r"(badlo|change karo|galat bola|galat hai|galat address|sahi karo)",
            r"\b(pocket \d+|geyser|nal|tap|shaam|subah)\s+nahi\s+\w+\b",
        ]
        return any(re.search(p, text) for p in patterns)

    def _check_yes(self, text: str) -> bool:
        clean = re.sub(r"\s+", " ", re.sub(r"[,।!?.]", " ", text)).strip()
        patterns = [
            r"^(haan|ha|haanji|ji haan|pakka|theek hai|thik hai|chalega|kar do|bhej do|sahi hai|confirm|yes|yep|sure|ok|okay)$",
            r"(हाँ|जी हाँ|पक्का|ठीक है|कर दो|भेज दो|सही है|हाँ जी)",
            r"\b(haan pakka|theek hai bhej do|haan bhej dijiye|pakka confirm)\b",
            r"\b(haan ji|ji haan|bilkul|kar do confirm|theek hai bhej do|haan bhej do)\b",
        ]
        return any(re.search(p, clean) for p in patterns)

    def _check_no(self, text: str) -> bool:
        patterns = [
            r"^(nahi|na|no|nope|nahi chahiye|mat karo|rehne do|cancel)$",
            r"^(नहीं|ना|मत करो|रहने दो|कैंसल)$",
            r"\b(nahi chahiye|rehne dijiye|mat bhejo|ab nahi)\b",
        ]
        return any(re.search(p, text) for p in patterns)

    def _extract_problem(self, text: str) -> tuple[str | None, str | None]:
        # Strip negated keywords like "geyser nahi" or "tap nahi" so they don't falsely match
        filtered_text = re.sub(
            r"\b(geyser|geezer|gijar|tap|nal|pipe|motor)\s+nahi\b", "", text, flags=re.IGNORECASE
        )

        for key, title, patterns in self.PROBLEM_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, filtered_text):
                    return key, title

        # Check for generic repair words without specific category
        if any(
            w in filtered_text
            for w in ["plumber", "repair", "kharab", "theek karwana", "theek karna"]
        ):
            return "unknown", "General Plumbing / Repair Issue"

        return None, None

    def _extract_time(self, text: str) -> str | None:
        for pattern, label in self.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                if label:
                    return label
                # Dynamic matching for "X baje"
                baje_match = re.search(
                    r"(\d{1,2}|chhe|saat|aath|nau|das|gyarah|barah|paanch|chaar|char|do|teen)\s*(baje|बजे)",
                    text,
                )
                if baje_match:
                    raw_val = baje_match.group(1).lower()
                    num_val = self.HINDI_NUMS.get(raw_val, raw_val)
                    return f"{num_val} Baje"
        return None

    def _extract_address(self, raw_text: str, text_lower: str) -> str | None:
        has_landmark = any(kw in text_lower for kw in self.LANDMARK_KEYWORDS)
        has_area = any(area in text_lower for area in self.known_areas)

        if has_landmark or has_area:
            # Check if text contains multiple clauses separated by comma / punctuation
            clauses = [c.strip() for c in re.split(r"[,;।\n]", raw_text) if c.strip()]
            problem_words = [
                "geyser",
                "geezer",
                "gijar",
                "leak",
                "pipe",
                "paip",
                "garam",
                "burst",
                "motor",
                "drain",
                "naali",
                "sink",
                "nal",
            ]
            has_problem_in_text = any(p in text_lower for p in problem_words)

            if len(clauses) > 1 and has_problem_in_text:
                # Find the clause containing landmark or area that doesn't mention problem keywords
                for c in clauses:
                    c_low = c.lower()
                    c_has_land = any(kw in c_low for kw in self.LANDMARK_KEYWORDS)
                    c_has_area = any(area in c_low for area in self.known_areas)
                    if (c_has_land or c_has_area) and not any(p in c_low for p in problem_words):
                        return c

            # Clean unwanted leading/trailing words
            cleaned = re.sub(
                r"^(mera address hai|address hai|hum rehte hain|yahan aa jao|address note karo|galat address[,\s]*|wrong address[,\s]*|sahi address[,\s]*)\s*",
                "",
                raw_text,
                flags=re.IGNORECASE,
            ).strip()
            # If long enough to be an address
            if len(cleaned) >= 8:
                return cleaned

        return None

    def _extract_name(self, raw_text: str, text_lower: str, state: Any) -> str | None:
        # If explicitly in ASK_NAME state
        state_str = str(state) if state else ""
        if "ASK_NAME" in state_str:
            clean = re.sub(
                r"^(mera naam|naam hai|naam|my name is)\s*", "", raw_text, flags=re.IGNORECASE
            ).strip()
            if (
                clean
                and len(clean.split()) <= 3
                and not any(kw in clean.lower() for kw in ["haan", "nahi", "pakka"])
            ):
                return clean.title()

        # In-line pattern: "mera naam X hai"
        match = re.search(r"(mera naam|naam)\s+([a-zA-Z\u0900-\u097F]+)\s+(hai)?", text_lower)
        if match:
            return match.group(2).title()

        return None
