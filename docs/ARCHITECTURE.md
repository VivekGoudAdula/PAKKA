# Architecture

## Stack Overview

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15 (App Router), TypeScript strict | `/apps/web` |
| Styling | Tailwind CSS v3, shadcn/ui, Sera UI, daisyUI | See Design System |
| Animation | Framer Motion | Springs, prefers-reduced-motion aware |
| State | Zustand (client), TanStack Query (server) | |
| Backend | Python 3.11+, FastAPI, asyncio | `/apps/api` |
| Realtime | WebSockets (FastAPI native) | Bidirectional events hub |
| Database | SQLite via SQLModel | File: `pakka.db` |
| Scheduler | APScheduler | Outbound call scheduling, reminders |
| STT | Gnani Vachana Prisma v3.0 | Raw WebSocket PCM |
| TTS | Gnani Vachana Timbre v3.0 | WebSocket base64 audio |
| LLM | Evon v3.3 via vLLM | Extraction/classification ONLY |
| Telephony | Exotel (Voicebot applet) | Bidirectional WebSocket audio (Phase 1+) |

---

## Monorepo Layout

```
pakka/
├── apps/
│   ├── web/                  # Next.js 15 App Router frontend
│   │   ├── app/              # App Router pages/layouts
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui primitives
│   │   │   ├── sera/         # Sera UI components (re-themed)
│   │   │   ├── daisy/        # daisyUI wrappers
│   │   │   └── pakka/        # Composed brand components
│   │   ├── lib/              # Utilities, types, hooks
│   │   └── public/
│   └── api/                  # FastAPI backend
│       ├── app/
│       │   ├── main.py       # FastAPI app entry
│       │   ├── config.py     # pydantic-settings Config
│       │   ├── events/       # WebSocket event hub
│       │   ├── routers/      # API route modules
│       │   ├── models/       # SQLModel database models
│       │   └── services/     # Business logic (Phase 4+)
│       ├── tests/
│       └── requirements.txt
├── docs/                     # All project documentation
├── scripts/                  # Dev helpers (run-all, seed, etc.)
├── samples/                  # Synthetic audio/data samples
├── .env.example
├── .gitignore
└── README.md
```

---

## Dashboard Modes

The dashboard operates in two modes from Day 1:

### LIVE Mode
- Real Exotel telephony integration
- Real Gnani STT/TTS on active calls
- Real-time WebSocket event stream from API
- Requires telephony credentials in `.env`

### DEMO Mode
- Seeded synthetic data (no real phone numbers/recordings)
- Scripted call simulations (pre-recorded transcripts played back)
- Simulated clock with **fast-forward control** (e.g., 1× → 10× → skip)
- No telephony dependency — suitable for presentations/demos
- Switch via UI toggle or `?mode=demo` query param

---

## Realtime Event Schema

All events flow over a single WebSocket connection from API to web:  
`ws://localhost:8000/ws/events`

Events are JSON objects with a `type` field and optional `payload`.

### Event Types

| Event | Direction | Payload Fields | Description |
|---|---|---|---|
| `call.started` | API → Web | `call_id, caller_number_masked, timestamp` | Inbound call picked up |
| `transcript` | API → Web | `call_id, role, text, language, is_final` | Live transcript segment |
| `slot.updated` | API → Web | `call_id, field, value` | Booking field captured (name, address, slot, etc.) |
| `job.booked` | API → Web | `job_id, call_id, summary` | Booking confirmed and saved |
| `dispatch.started` | API → Web | `job_id, technician_id` | Starting technician dispatch call |
| `dispatch.accepted` | API → Web | `job_id, technician_id` | Technician accepted ("haan, pakka") |
| `dispatch.declined` | API → Web | `job_id, technician_id` | Technician declined, trying next |
| `dispatch.failed` | API → Web | `job_id` | All technicians declined/unreachable |
| `promise.captured` | API → Web | `job_id, promise_date, amount` | Payment promise recorded |
| `promise.kept` | API → Web | `job_id` | Payment confirmed received |
| `promise.broken` | API → Web | `job_id, attempt` | Follow-up failed, next attempt scheduled |
| `clock.tick` | API → Web | `ts, mode` | Simulated clock heartbeat (DEMO mode) |

### Web → API Events (client actions)

Sent as JSON messages on the same WebSocket:

| Message | Payload | Description |
|---|---|---|
| `demo.clock.set_speed` | `{ speed: number }` | Set simulated clock speed (1-100×) |
| `demo.trigger_call` | `{ script_id: string }` | Trigger a scripted demo call |
| `subscribe` | `{ topics: string[] }` | Subscribe to specific event types |

---

## Voice Pipeline (Phase 1+)

```
Exotel ──PCM 8kHz──► API WebSocket handler
                           │
                    ┌──────▼──────┐
                    │  STT proxy  │  raw PCM → Gnani Vachana STT WS
                    └──────┬──────┘
                           │ transcript
                    ┌──────▼──────┐
                    │ Booking FSM │  rule-based extractor (+ Evon v3.3)
                    └──────┬──────┘
                           │ response text
                    ┌──────▼──────┐
                    │  TTS proxy  │  text → Gnani Vachana TTS WS → base64 PCM
                    └──────┬──────┘
                           │ PCM audio
                    Exotel ◄──────
```

### STT Notes
- STT WebSocket is proxied through the API (browsers cannot set WS headers)
- Audio: raw PCM s16le mono, 8 kHz, exactly 1024-byte frames at real-time cadence (64 ms)
- Session max: 15 minutes; concurrent session cap applies

### TTS Notes
- Audio arrives as base64 chunks; "complete" message signals end of stream
- Write numbers/amounts as spoken words, not digits
- Use voice configured per language/persona

---

## Evon v3.3 Usage Rules

- Self-hosted via vLLM on a separate process
- **ONLY used for:** extraction and classification tasks (slot filling from transcript, intent detection)
- **NEVER used for:** real-time call-flow control, direct telephony decisions
- Always behind an `Extractor` interface with a rule-based fallback implementation
- Fallback is always available so the system works without Evon running

