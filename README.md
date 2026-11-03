# Pakka

> **"Every missed call has a cost."**
> Pakka picks up, books the job, tells the technician, and chases the payment.

A voice assistant for small Indian service businesses (plumbers, geyser repair) built for the **Great Indian AI Internship Challenge by Gnani AI** (deadline: Nov 10, 2026, 11:59 PM IST).

---

## Monorepo Structure

```
pakka/
├── apps/
│   ├── web/          # Next.js frontend (App Router)
│   └── api/          # FastAPI backend
├── docs/             # Architecture, design, phase plans
├── scripts/          # Dev helpers
├── samples/          # Synthetic audio/data samples
├── .env.example      # Environment variable template
└── README.md
```

---

## Quick Start

### Prerequisites

- **Node.js** ≥ 20 (LTS)
- **Python** 3.11+
- **pnpm** ≥ 9

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd pakka

cp .env.example .env
# Fill in your secrets in .env
```

### 2. Run the API (FastAPI)

```bash
cd apps/api
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Health check: http://localhost:8000/health

### 3. Run the Web app (Next.js)

```bash
cd apps/web
pnpm install
pnpm dev
```

Open: http://localhost:3000

Design QA page: http://localhost:3000/design

### 4. Run both concurrently (from repo root)

```bash
# From repo root — requires pnpm workspace or concurrent runner
pnpm run dev
```

---

## Running Tests

### API tests

```bash
cd apps/api
pytest -v
```

### Web type-check + lint + build

```bash
cd apps/web
pnpm typecheck
pnpm lint
pnpm build
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 App Router, TypeScript strict, Tailwind CSS v3, shadcn/ui, Framer Motion, Zustand, TanStack Query |
| Backend | Python 3.11, FastAPI, asyncio, WebSockets, SQLModel (SQLite), APScheduler |
| Voice STT | Gnani Vachana Prisma v3.0 — raw WebSocket PCM |
| Voice TTS | Gnani Vachana Timbre v3.0 — WebSocket base64 audio |
| LLM | Evon v3.3 via vLLM — extraction/classification only |
| Telephony | Exotel (Phase 1+) |

See `/docs/ARCHITECTURE.md` for full details.

---

## Docs

- [Project Context](docs/PROJECT_CONTEXT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Design System](docs/DESIGN_SYSTEM.md)
- [Gnani API Notes](docs/GNANI_API_NOTES.md)
- [Exotel Notes](docs/EXOTEL_NOTES.md)
- [Phase Plan](docs/PHASES.md)
- [Agent Rules](docs/AGENT_RULES.md)

---

## Phase 1: Voice Pipeline & Telephony Guide

### Architecture & Bridging Rules
1. **Exotel -> Gnani STT**: Exotel delivers ~1600-byte raw PCM chunks every ~100 ms. The internal `Rechunker` strictly buffers and yields exact 1024-byte frames at real-time 64 ms cadence (at 8000 Hz linear16 mono) to Gnani Prisma v3.0 (`wss://api.vachana.ai/stt/v3/stream`).
2. **Gnani TTS -> Exotel**: Audio from Gnani Timbre (`wss://api.vachana.ai/api/v1/tts`) is accumulated via `ExotelAudioAccumulator` into frames that meet Exotel's strict constraints: **minimum 3200 bytes** and **exact multiple of 320 bytes**.
3. **Barge-in Support**: When a caller speaks while the assistant is speaking, the server interrupts TTS synthesis and dispatches an Exotel `clear` frame to immediately flush buffered audio on the telephony line.
4. **Mandatory Disclosure**: Every call opens with: *"Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?"*.

---

### Exotel Dashboard Setup (Click-by-Click)

1. Log in to your [Exotel Dashboard](https://my.exotel.com).
2. Navigate to **App Bazaar** > **Create Flow** (or **Installed Apps**).
3. Drag the **Voicebot** (or **Stream**) applet into your call flow.
4. In the applet configuration panel:
   - **Stream URL**: Set to `wss://<YOUR_PUBLIC_TUNNEL_DOMAIN>/ws/exotel` (e.g. `wss://xxxx.ngrok-free.app/ws/exotel`).
   - **Stream Type / Direction**: `Bidirectional`.
   - **Media Format**: `audio/x-l16` (Linear PCM), `8000 Hz`, `1 channel (mono)`.
5. Connect the start node to the Voicebot applet and connect the hangup / completed node.
6. Click **Save** and assign this flow to your virtual **ExoPhone** number under **Numbers / Call Routing**.

---

### Tunnel Setup (Windows / Local Dev)

To allow Exotel to connect to your local development machine:

```powershell
# Using Cloudflare Tunnel:
cloudflared tunnel --url http://localhost:8000

# OR using ngrok:
ngrok http 8000
```

Copy the assigned HTTPS/WSS domain and update `.env`:
```ini
PUBLIC_WSS_URL=wss://your-subdomain.ngrok-free.app/ws/exotel
```

---

### 6-Step Manual Test Guide

1. **Start the API Server**:
   ```powershell
   cd apps/api
   uvicorn app.main:app --reload --port 8000
   ```
2. **Run the Gnani Voice Smoke Test**:
   ```powershell
   python scripts/gnani_smoke.py
   # Or offline dry-run:
   python scripts/gnani_smoke.py --dry-run
   ```
   *Verifies Timbre TTS synthesis and Prisma STT transcription with latency tracking.*

3. **Run the Exotel Telephony Simulator**:
   ```powershell
   python scripts/exotel_simulator.py --url ws://localhost:8000/ws/exotel
   ```
   *Connects to `/ws/exotel`, listens to greeting audio, streams `samples/sample_plumber_request.wav`, captures echo reply, and saves to `samples/reply.wav`.*

4. **Verify Barge-in Interruption**:
   ```powershell
   python scripts/exotel_simulator.py --barge-in
   ```
   *Interprets assistant speech immediately with caller speech; verifies server returns `clear` event.*

5. **Trigger an Outbound Call** (Optional / Live Telephony):
   ```powershell
   python scripts/exotel_connect_outbound.py --to +919876543210
   ```
   *Triggers Exotel's `Calls/connect` API using your credentials and routes audio to `PUBLIC_WSS_URL`.*

6. **Inbound Call Test**:
   - Dial your virtual ExoPhone number from your mobile.
   - Verify greeting disclosure: *"Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?"*.
   - Speak your issue (e.g. *"Mera geyser kharab hai paani leak ho raha hai"*).
   - Hear Pakka repeat: *"Aapne kaha: Mera geyser kharab hai paani leak ho raha hai"*.
   - Inspect call summary and latency metrics printed in the API console.

---

## Demo Modes

The dashboard supports two modes:

- **LIVE** — real calls via Exotel + Gnani APIs
- **DEMO** — seeded data, scripted calls, simulated clock with fast-forward control (no telephony dependency)

---

## Ethical Commitments

- The assistant identifies itself as a digital assistant at the start of every call.
- It never denies being an AI; it offers a human callback.
- Outbound calls respect owner-configured hours (default 9 AM – 8 PM IST).
- Inbound answering is 24/7.
- No real personal data (phone numbers, Aadhaar, PAN) anywhere in the repo or demo.
- All samples are synthetic.

