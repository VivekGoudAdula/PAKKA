"""
Hinglish conversational reply templates for Pakka voice assistant.
Short, natural phone utterances with a female digital sahayak persona ('bol rahi hoon').
"""

from app.voice.audio import number_to_spoken_words

MANDATORY_GREETING = (
    "Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?"
)

ASK_PROBLEM = "Aapko kya problem aa rahi hai? Plumber ya geyser repair ke liye bataiye."

REASK_PROBLEM = "Main samajh nahi paayi. Kya aap dobara bata sakte hain ki geyser, tap ya pipe mein kya dikkat hai?"

ASK_ADDRESS = (
    "Theek hai. Aapka landmark-style address bata dijiye, taaki technician aasani se pahunch sake."
)

REASK_ADDRESS = (
    "Address theek se samajh nahi aaya. Kripya apna area ya koi nazdeeki landmark bata dijiye."
)

ASK_SLOT = "Technician ke aane ke liye kaun sa time theek rahega? Jaise aaj shaam ya kal subah?"

REASK_SLOT = "Kaun sa time slot rakhein? Aaj shaam paanch se saat, ya kal subah?"

ASK_NAME = "Aapka shubh naam kya hai ji?"

ROBOT_DISCLOSURE = "Ji haan, main Pakka ki digital sahayak bol rahi hoon. Kya aap human owner se baat karna chahenge?"

BARGAINING_HOLD = "Yeh hamare dukaan ke standard rates hain. Agar aap chahein toh main shop owner se keh kar callback karwa sakti hoon."

HANDOFF_MESSAGE = "Maaf kijiyega, main samajh nahi paayi. Main Ramesh bhai ko aapka number de rahi hoon, ya aap unhe {phone} par call kar sakte hain."

EMERGENCY_SAFETY_INSTRUCTION = (
    "Kripya pehle main switch band kar dijiye aur geyser se door rahiye. "
    "Main abhi malik ko bata rahi hoon, woh turant aapko phone karenge. "
    "Agar aag ya gas ki badbu hai to turant 112 par phone kijiye."
)

EMERGENCY_112_INSTRUCTION = "Agar aag ya gas ki badbu hai to turant 112 par phone kijiye."

SILENCE_PROMPT_1 = "Hello? Kya aap mujhe sun pa rahe hain?"

SILENCE_PROMPT_2 = (
    "Aapki aawaz nahi aa rahi hai. Kripya thodi der baad dobara call karein. Dhanyawaad."
)

CALL_ABANDONED = (
    "Theek hai ji, koi baat nahi. Jab bhi repair ki zaroorat ho, call kijiyega. Dhanyawaad."
)

BOOKING_SUCCESS = (
    "Aapki booking pakki ho gayi hai! Technician ko details bhej di gayi hain. Dhanyawaad!"
)


def format_quote_reply(min_price: int, max_price: int) -> str:
    """Format price quote in spoken Hindi numerals."""
    min_spoken = number_to_spoken_words(min_price)
    max_spoken = number_to_spoken_words(max_price)
    return (
        f"Is kaam ka kharcha lagbhag {min_spoken} se {max_spoken} rupaye hoga. "
        "Kya main yeh booking confirm kar doon?"
    )


def format_quote_unknown() -> str:
    """Reply when problem has no explicit rate card match."""
    return (
        "Is problem ke liye technician aakar check karega aur sahi estimate bata dega. "
        "Inspection visit standard rates par hogi. Kya main booking confirm kar doon?"
    )


def format_confirm_readback(problem: str, address: str, slot: str) -> str:
    """Construct readback confirmation line."""
    return (
        f"Maine note kar liya: {problem}, {address}, {slot} ka time. "
        "Kya main pakka confirm kar doon?"
    )
