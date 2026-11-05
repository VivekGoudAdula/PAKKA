"""
Ledger Quick Entry Parser for Pakka.
Deterministic Hinglish parser for owner voice / text quick entries such as:
'Ramesh ke kaam ho gaya 800 mile 500 baaki'
Extracts customer name, job summary, paid amount, remaining balance, and promise date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class LedgerEntryParsed:
    """Structured extraction outcome from owner quick entry utterance."""

    raw_text: str
    customer_name: str
    job_summary: str
    paid_amount: int
    balance: int
    is_fully_paid: bool = False
    promise_date: str | None = None
    confidence: float = 0.9


def parse_ledger_entry(text: str) -> LedgerEntryParsed:
    """Parse Hinglish owner ledger entry text into structured financial record."""
    clean = text.strip()
    clean_lower = clean.lower()

    # 1. Extract Amounts (paid and balance)
    paid_amount = 0
    balance = 0
    is_fully_paid = False

    # Check for "full payment", "pura mila", "clear", "kuch baki nahi"
    is_full = bool(
        re.search(
            r"(full payment|pura mila|poora mila|clear|kuch baaki nahi|kuch baki nahi|poora ho gaya|sab mil gaya)",
            clean_lower,
        )
    )

    # Patterns for: "800 mile 500 baaki" / "800 mila 500 baki"
    match_mile_baki = re.search(
        r"(\d{2,6})\s*(mile|mila|mil gaye|de diye|diye)\s*(aur)?\s*(\d{2,6})\s*(baaki|baki|pending|rehte hain)",
        clean_lower,
    )
    if match_mile_baki:
        paid_amount = int(match_mile_baki.group(1))
        balance = int(match_mile_baki.group(4))
    else:
        # Check: "(\d+) baaki" or "(\d+) baki"
        match_baki = re.search(
            r"(\d{2,6})\s*(baaki|baki|pending|rehte hain)",
            clean_lower,
        )
        # Check: "(\d+) mile" or "(\d+) mila"
        match_mila = re.search(
            r"(\d{2,6})\s*(mile|mila|mil gaye|de diye|cash|online|pay kiye)",
            clean_lower,
        )

        if match_baki:
            balance = int(match_baki.group(1))
        if match_mila:
            paid_amount = int(match_mila.group(1))

        # Check total amount if full payment
        if is_full:
            is_fully_paid = True
            balance = 0
            if paid_amount == 0:
                nums = [int(n) for n in re.findall(r"\b\d{2,6}\b", clean)]
                if nums:
                    paid_amount = nums[0]
        elif paid_amount == 0 and balance == 0:
            # Fallback numeric extraction
            nums = [int(n) for n in re.findall(r"\b\d{2,6}\b", clean)]
            if len(nums) == 2:
                paid_amount = nums[0]
                balance = nums[1]
            elif len(nums) == 1:
                if "baaki" in clean_lower or "baki" in clean_lower:
                    balance = nums[0]
                else:
                    paid_amount = nums[0]

    if balance == 0 and paid_amount > 0 and (is_full or "baaki" not in clean_lower):
        is_fully_paid = True

    # 2. Extract Customer Name
    # Look for name at the start before "ke", "ka", "ji", or job keywords
    name = "Customer"
    name_match = re.match(
        r"^([A-Z\u0900-\u097F][a-z\u0900-\u097F]+(?:\s+[A-Z\u0900-\u097F][a-z\u0900-\u097F]+)?)\s*(?:ji|bhai|sahab|ke|ka)?",
        clean,
    )
    if name_match:
        extracted = name_match.group(1).strip()
        # Ensure not a service keyword
        if extracted.lower() not in ("geyser", "plumbing", "pipe", "tap", "motor", "drain"):
            name = extracted.title()

    # 3. Extract Job Summary
    job_summary = "Service Repair"
    jobs_map = [
        (r"(geyser coil change|coil change)", "Geyser Coil Replacement"),
        (r"(geyser repair|geezer repair|geyser)", "Geyser Repair"),
        (r"(bathroom fitting|fitting)", "Bathroom Fitting"),
        (r"(tap repair|tap|nal repair|nalle)", "Tap Repair"),
        (r"(kitchen pipe|pipe leak|pipe)", "Pipe Repair"),
        (r"(drainage clean|drain clean|naali)", "Drainage Cleaning"),
        (r"(motor fitting|motor pump|submersible)", "Motor Pump Fitting"),
        (r"(plumbing kaam|plumbing)", "General Plumbing"),
        (r"(kaam ho gaya|kaam)", "General Service"),
    ]
    for pattern, summary in jobs_map:
        if re.search(pattern, clean_lower):
            job_summary = summary
            break

    # 4. Extract Promise Date
    promise_date = None
    date_patterns = [
        (r"\b(kal shaam|kal subah|kal)\b", "kal"),
        (r"\b(parson)\b", "parson"),
        (r"\b(somwar|mangalwar|budhwar|guruwar|shukrawar|shaniwar|itwar|ravivar)\b", None),
        (r"(\d{1,2}\s*(?:tareekh|tarikh))", None),
        (r"(\w+\s*din baad)", None),
    ]
    for p, def_val in date_patterns:
        m = re.search(p, clean_lower)
        if m:
            promise_date = def_val or m.group(1)
            break

    return LedgerEntryParsed(
        raw_text=clean,
        customer_name=name,
        job_summary=job_summary,
        paid_amount=paid_amount,
        balance=balance,
        is_fully_paid=is_fully_paid,
        promise_date=promise_date,
    )

