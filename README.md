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
- [Phase Plan](docs/PHASES.md)
- [Agent Rules](docs/AGENT_RULES.md)

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

