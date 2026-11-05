# Phase Plan

> Last updated: 2026-11-03  
> Deadline: **Nov 10, 2026, 11:59 PM IST**

---

## Phases

- [x] **Phase 0 — Foundation**  
  Monorepo setup, docs, design tokens, fonts, component library smoke-tests, `/design` QA page, FastAPI health endpoint, tooling.

- [ ] **Phase 1 — Voice Pipeline + Exotel Echo Test** (code complete, live test PENDING USER)  
  Exotel AgentStream bidirectional WS audio bridge, Gnani STT Prisma v3.0 & Timbre v2.5 TTS echo loop, Energy VAD barge-in with 500ms grace period, echo-loop guard (400ms), 10s connection timeouts, telephony simulator & smoke test scripts.

- [x] **Phase 2 — App Shell + Seeded Screens**  
  Premium light dashboard working in DEMO mode with synthetic seed data. Collapsible sidebar, mobile bottom nav, simulated clock with fast-forward, command palette, LIVE/DEMO toggle. Screens: Overview, Calls, Jobs, Technicians, Payments, Settings. Captured 18 responsive screenshots at 360, 768, and 1440 px with zero horizontal overflow.

- [x] **Phase 3 — Booking Brain**  
  Deterministic Hinglish booking conversation FSM (greeting → problem → address → slot → quote → confirm_readback → booked), RuleBasedExtractor supporting Latin transliteration and Devanagari script, SQLite database persistence via SQLModel, 22 diverse YAML scenarios (100% pass rate, 100% slot accuracy), interactive text-mode simulator CLI, REST APIs for jobs, calls, technicians, and settings. Sub-50ms brain latency with zero external LLM calls.

- [x] **Phase 4 — Live Call Console + Technician Dispatch**  
  Deterministic Technician Voice Dispatch FSM (`DispatchFSM`) with cascading ranking across specialists (specialty match first, fewest active jobs, max 3 attempts). Outbound calling hours exemption for emergency dispatch. Exotel outbound connect with dual correlation. Unified `EventSource` abstraction (`DemoEventSource` with ~40s booking + ~20s dispatch script, and `LiveWSEventSource`). Real-time Live Call Console (`/app/live`) with prefixed daisyUI chat bubbles, bot speaking indicator, barge-in tag, animated slot filling, FSM stepper, spring-in `PakkaStamp`, technician dispatch card with ringing animation and spoken replies, urgent safety hazard warning banner, latency chips (hidden in DEMO), Jobs board Booked → Dispatched live motion animation and confirmation dialog, activated technicians directory call button. 15 dispatch YAML scenarios with 100% pass rate (< 0.2 ms latency), interactive text dispatch simulator CLI, and 6 Playwright screenshots at 360, 768, and 1440 px with zero horizontal overflow.

- [x] **Phase 5 — Money Loop + Simulated Clock + Scripted Demo Calls**  
  Deterministic Collection FSM (`CollectionFSM`) with multi-tier tone ladder (Tone 1, 2, 3), Promise to Pay (PTP) tracking, objection & dispute routing, wrong number permanent suppression, owner escalation, pre-written natural Hinglish utterances with Hindi number words (`number_to_spoken_words`), SimulatedClock service with IST control (+hours, +days, reset) and outbound hours enforcement (9 AM – 8 PM IST default, max 3/week, min 24h apart), owner quick entry ledger parser for Hinglish natural text (`/api/ledger/entry`) with 16 unit tests, 25 main collection YAML scenarios with 100% pass rate, 8 holdout scenarios evaluated separately, interactive text collection CLI, Exotel `?collect=true&promise_id=...` integration, Payments dashboard (`/app/payments`) with dynamic clock-driven status chips, "Call Now" button with calling window/suppression gating, customer reminder trail sheet with Sera Timeline, quick entry box, extended `DemoEventSource` collection call, and 10 responsive Playwright screenshots at 360, 768, and 1440 px with zero horizontal overflow.

- [x] **Phase 6 — Evon + 30-Scenario Tests + Metrics Page**  
  Evon v3.3 extraction behind `Extractor` protocol calling vLLM `/v1/chat/completions` (OpenAI format, temp 0.6, top_p 0.95, `enable_thinking: false`, json_schema matching `ExtractionResult`), with sub-2s timeout and fallback to `RuleBasedExtractor`. Two-stage `HybridExtractor` (rules first < 2ms, Evon fallback for unrecognized problems / missing slots). Complete offline mock engine (`mock_evon.py`) and live probe (`scripts/evon_probe.py`). Comprehensive documentation in `docs/EVON_SETUP.md`. Comparative benchmark across Rules vs Evon vs Hybrid on 28 main booking, 10 holdout, and 30 noisy STT scenarios (`tests/scenarios/stt_noisy.yaml`), proving Hybrid achieves 100% on noisy STT (output saved to `reports/extractor_comparison.json`). Audio evaluation harness (`scripts/make_test_audio.py` generating 90 test WAVs across Clean, 15dB, 5dB SNR and `scripts/run_audio_eval.py` testing Prisma STT pipeline, output saved to `reports/audio_eval.json`). Real-time Metrics dashboard (`/app/metrics`) with 6 KPI cards, sample sizes, Extractor comparison table, Audio SNR degradation chart, methodology panel, and DEMO snapshot badge. 3 responsive Playwright screenshots captured at 360, 768, and 1440 px with zero overflow.

- [ ] **Phase 7 — Polish + Landing Page**  
  Full landing page (Hero with Stamp, features bento, timeline, pricing), design system polish, accessibility and performance audit.

- [ ] **Phase 8 — Demo Video + Post + Submission**  
  60-second product demo video, LinkedIn/Twitter launch post, submission documentation pack.

---

## Notes

- Phases are sequential; do not start the next phase until the current one's acceptance criteria pass.
- Each phase ends with a PHASE REPORT (see `AGENT_RULES.md`).

