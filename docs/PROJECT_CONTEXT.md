# Project Context

## 2. What is Pakka?

**Pakka** ("pakka" = confirmed, for sure in Hindi) is a voice assistant for small Indian service businesses, starting with plumbers and geyser repair technicians.

**Tagline:** "Every missed call has a cost."  
**Sub-tagline:** "Pakka picks up, books the job, tells the technician, and chases the payment."

### The Full Loop

Pakka handles end-to-end from missed call → money collected across three core flows:

#### A) BOOKING (Inbound, 24/7)
- Answers inbound calls in **Hinglish** (handles noisy lines)
- Captures: problem description, landmark-style address, time slot ("shaam ko")
- Gives a price range from the owner's configured price list
- Reads the booking back and confirms
- Identifies itself as a digital assistant at the start of every call

#### B) DISPATCH (Outbound, any hour to technicians)
- Calls the assigned technician
- Reads the job aloud in his language
- Takes voice confirmation: "haan, pakka" = accept, "nahi" = decline
- Falls back to the next technician if declined

#### C) COLLECTION (Outbound, within owner-set hours)
- After job completion, follows up on payment
- Handles objections: "kal dunga", "maine to 150 hi liya tha", "galat number"
- Saves a promise-to-pay date
- Calls back on that date
- Keeps a dated reminder trail

---

## 3. Non-Negotiable Rules

### Identity & AI Disclosure
- The assistant **must** identify itself as a digital assistant at the start of calls  
  (example: "...ki digital sahayak bol rahi hoon")
- It **must never deny being an AI** if sincerely asked
- When asked, it offers a **human callback**

### Conduct
- Never threaten or abuse anyone
- Stop calling a number immediately on "wrong number"
- **Outbound call hours** are an OWNER SETTING (default 9 AM – 8 PM IST); this is enforced server-side
- Inbound answering is 24/7
- Technician dispatch may go out at any hour

### Data & Privacy
- **Synthetic data only.** No real phone numbers, Aadhaar, PAN, or real recordings anywhere in the repo or demo
- All samples must be clearly labelled as synthetic

### Secrets & Security
- **No secrets in the repo.** Use `.env` and ship `.env.example`
- All API keys go via environment variables only

### Integrity
- No bought engagement or bots
- Do not claim results we have not measured; all metrics must come from our own test runs

### Competition
- Built for the **Great Indian AI Internship Challenge by Gnani AI**
- Deadline: **Nov 10, 2026, 11:59 PM IST**
- Must visibly use Gnani models: Prisma v3.0 (STT), Timbre (TTS), Evon v3.3 (LLM)

### Libraries
- Do not add libraries beyond the approved stack without explicit approval

