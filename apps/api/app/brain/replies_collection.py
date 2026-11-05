"""
Hinglish conversational reply templates for Pakka Collection Brain.
Natural, respectful, zero-pressure phone utterances for payment reminders.
Amounts are spoken in words (e.g. 'paanch sau rupaye') using number_to_spoken_words.
"""

from __future__ import annotations

from app.voice.audio import number_to_spoken_words


def get_collection_greeting(
    customer_name: str,
    business_name: str = "Sharma Plumbing",
    job_type: str = "repair",
    amount: int = 500,
    tone_level: int = 1,
) -> str:
    """Initial greeting identifying assistant, business, and balance."""
    amount_words = number_to_spoken_words(amount)
    if tone_level == 3:
        return (
            f"Namaste {customer_name} ji, main {business_name} ki digital sahayak bol rahi hoon. "
            f"Aapke {job_type} ke {amount_words} rupaye baaki hain. "
            f"Agar aap chahein to malik aapko khud phone kar lenge. Main ab aapko reminder call nahi karungi."
        )
    if tone_level == 2:
        return (
            f"Namaste {customer_name} ji, main {business_name} ki digital sahayak bol rahi hoon. "
            f"Aapke {job_type} ke {amount_words} rupaye abhi baaki dikh rahe hain. "
            f"Kya aap bata sakte hain ki payment kab tak ho sakti hai?"
        )
    return (
        f"Namaste {customer_name} ji, main {business_name} ki digital sahayak bol rahi hoon. "
        f"Aapke {job_type} ke {amount_words} rupaye baaki hain. "
        f"Yeh payment aap kab tak kar payenge?"
    )


def get_balance_statement(
    amount: int,
    tone_level: int = 1,
) -> str:
    """State remaining balance in spoken Hindi words and ask when payment will be made."""
    amount_words = number_to_spoken_words(amount)
    if tone_level == 3:
        return (
            f"Aapke {amount_words} rupaye baaki hain. "
            f"Agar aap chahein to malik aapko khud phone kar lenge. Main ab aapko reminder call nahi karungi."
        )
    if tone_level == 2:
        return (
            f"Aapke {amount_words} rupaye abhi baaki dikh rahe hain. "
            f"Kya aap bata sakte hain ki payment kab tak ho sakti hai?"
        )
    return (
        f"Aapke {amount_words} rupaye baaki hain. "
        f"Yeh payment aap kab tak kar payenge?"
    )


def get_promise_confirmation(
    customer_name: str,
    promise_date_spoken: str,
    tone_level: int = 1,
) -> str:
    """Confirmation of agreed Promise to Pay (PTP)."""
    return f"Theek hai ji, shukriya. Maine note kar liya hai ki aap {promise_date_spoken} tak kar denge."


# Exact Standard Disposition Responses (Zero-pressure, truthful)
WRONG_NUMBER_REPLY = (
    "Maaf kijiyega, lagta hai galat number par call lag gaya. "
    "Main aapka number list se turant hata rahi hoon, aage se koi call nahi aayegi. Dhanyawaad."
)

DISPUTE_REPLY = (
    "Maaf kijiye, aapko pareshani hui. "
    "Main malik ko bata deti hoon, woh aapse baat karenge. Tab tak main payment ke liye call nahi karungi."
)

LINK_REQUEST_REPLY = (
    "Ji, main malik ko bata deti hoon, woh aapko payment ka tareeka bhej denge."
)

CALLBACK_REPLY = (
    "Theek hai ji, lagta hai aap abhi busy hain. "
    "Main baad mein call karwa lungi. Dhanyawaad."
)

ALREADY_PAID_REPLY = (
    "Accha, theek hai ji. Main malik ko bata deti hoon, woh check kar lenge. Shukriya."
)


def get_refused_reply(owner_name: str = "Ramesh") -> str:
    """Refusal reply referencing dynamic owner name."""
    return (
        f"Theek hai ji, koi baat nahi. Main shop owner {owner_name} ji ko inform kar deti hoon ki aapse direct baat kar lein. "
        f"Dhanyawaad."
    )


def get_owner_handoff_reply(owner_name: str = "Ramesh") -> str:
    """Handoff reply referencing dynamic owner name."""
    return (
        f"Theek hai ji, main shop owner {owner_name} ji ko aapka number bhej rahi hoon, "
        f"woh aapse seedhe phone par baat kar lenge."
    )


def get_robot_disclosure_reply(business_name: str = "Sharma Plumbing") -> str:
    """AI disclosure stating digital assistant identity and offering human callback."""
    return (
        f"Ji haan, main {business_name} ki digital sahayak bol rahi hoon. "
        f"Agar aap kisi insaan se baat karna chahte hain to main turant malik ko connect karwa sakti hoon."
    )


REFUSED_REPLY = get_refused_reply("Ramesh")
OWNER_HANDOFF_REPLY = get_owner_handoff_reply("Ramesh")
ROBOT_DISCLOSURE_REPLY = get_robot_disclosure_reply("Sharma Plumbing")

REASK_DATE_REPLY = (
    "Main date theek se samajh nahi paayi. Kya aap kal, parson, ya koi specific din bata sakte hain?"
)

SILENCE_REPLY = "Hello? Kya aap mujhe sun pa rahe hain?"
