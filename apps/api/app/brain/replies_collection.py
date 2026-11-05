"""
Hinglish conversational reply templates for Pakka Collection Brain.
Natural, respectful, zero-pressure phone utterances for payment reminders.
Amounts are spoken in words (e.g. 'aath sau rupaye') using number_to_spoken_words.
"""

from __future__ import annotations

from app.voice.audio import number_to_spoken_words


def get_collection_greeting(
    customer_name: str,
    business_name: str = "Sharma Plumbing",
    tone_level: int = 1,
) -> str:
    """Initial greeting identifying assistant and business."""
    if tone_level == 3:
        return (
            f"Namaste {customer_name} ji, {business_name} ki digital sahayak bol rahi hoon. "
            f"Aapki service payment ke baare mein baat karni thi."
        )
    if tone_level == 2:
        return (
            f"Namaste {customer_name} ji, {business_name} ki digital sahayak bol rahi hoon. "
            f"Aapne pehle payment ka waada kiya tha, usi baare mein follow-up call hai."
        )
    return (
        f"Namaste {customer_name} ji, {business_name} ki digital sahayak bol rahi hoon. "
        f"Aapka jo repair ka kaam hua tha, usi ke baare mein baat karni thi."
    )


def get_balance_statement(
    amount: int,
    tone_level: int = 1,
) -> str:
    """State remaining balance in spoken Hindi words and ask when payment will be made."""
    amount_words = number_to_spoken_words(amount)
    if tone_level == 3:
        return (
            f"Aapka {amount_words} rupaye ka hisaab baaki hai. "
            f"Agar koi pareshani hai, toh main shop owner se callback karwa sakti hoon, ya reminders thodi der ke liye pause kar dete hain."
        )
    if tone_level == 2:
        return (
            f"Aapka {amount_words} rupaye ka hisaab abhi baaki hai. "
            f"Aap yeh payment kab tak clear kar denge?"
        )
    return (
        f"Aapka {amount_words} rupaye ka hisaab baaki tha. "
        f"Toh yeh payment aap kab tak kar payenge?"
    )


def get_promise_confirmation(
    customer_name: str,
    promise_date_spoken: str,
    tone_level: int = 1,
) -> str:
    """Confirmation of agreed Promise to Pay (PTP)."""
    return (
        f"Theek hai {customer_name} ji, main {promise_date_spoken} ka waada note kar leti hoon. "
        f"Aapka bohot bohot dhanyawaad!"
    )


# Standard Disposition Responses
WRONG_NUMBER_REPLY = (
    "Maaf kijiyega, lagta hai galat number par call lag gaya. "
    "Main aapka number list se turant hata rahi hoon, aage se koi call nahi aayegi. Dhanyawaad."
)

DISPUTE_REPLY = (
    "Achha, kaam mein koi dikkat ya shikayat hai kya? "
    "Main abhi payment hold par daal rahi hoon aur owner Ramesh ji ko bolti hoon ki aapse direct baat karein."
)

CALLBACK_REPLY = (
    "Theek hai ji, lagta hai aap abhi busy hain. "
    "Main baad mein thodi der baad call karwa lungi. Dhanyawaad."
)

ALREADY_PAID_REPLY = (
    "Aapne payment kar di hai? Bahut accha! "
    "Main ledger check karke status update kar deti hoon. Pareshaan hone ke liye maaf kijiyega."
)

REFUSED_REPLY = (
    "Theek hai ji, koi baat nahi. Main shop owner Ramesh ji ko inform kar deti hoon ki aapse direct baat kar lein. "
    "Dhanyawaad."
)

OWNER_HANDOFF_REPLY = (
    "Theek hai ji, main shop owner Ramesh ji ko aapka number bhej rahi hoon, "
    "woh aapse seedhe phone par baat kar lenge."
)

ROBOT_DISCLOSURE_REPLY = (
    "Ji haan, main Pakka ki automated digital sahayak bol rahi hoon. "
    "Kya aap human owner se baat karna chahenge?"
)

REASK_DATE_REPLY = (
    "Main date theek se samajh nahi paayi. Kya aap kal, parson, ya koi specific din bata sakte hain?"
)

SILENCE_REPLY = "Hello? Kya aap mujhe sun pa rahe hain?"

