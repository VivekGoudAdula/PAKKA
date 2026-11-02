# Phase Plan

> Last updated: 2026-11-02  
> Deadline: **Nov 10, 2026, 11:59 PM IST**

---

## Phases

- [x] **Phase 0 — Foundation**  
  Monorepo setup, docs, design tokens, fonts, component library smoke-tests, `/design` QA page, FastAPI health endpoint, tooling.

- [ ] **Phase 1 — Voice Pipeline + Exotel Echo Test**  
  Read Exotel Voicebot docs, implement bidirectional WS audio bridge, proxy Gnani STT, Gnani TTS echo test (speak → transcribe → speak back), VAD tuning.

- [ ] **Phase 2 — Brand + Landing Page**  
  Full landing page: hero (with Stamp), features bento, how-it-works timeline, pricing/CTA, footer. Sera + shadcn components. Mobile-first. Fully responsive.

- [ ] **Phase 3 — App Shell + Dashboard Skeleton + Seed Data**  
  Authenticated layout shell, sidebar nav, bottom nav (mobile), LIVE/DEMO mode toggle. Dashboard skeleton with stat cards, call log, job list — all populated with seeded synthetic data. WebSocket event stream wired up.

- [ ] **Phase 4 — Booking Brain (FSM, Rule-Based Extractor, Price List)**  
  Booking conversation FSM (states: greeting → problem → address → slot → price_confirm → confirm → done). Rule-based slot extractor. Owner price list config. Booking record saved to DB. Full unit tests.

- [ ] **Phase 5 — Live Call Console**  
  Real-time call console page: live waveform, rolling transcript (daisyUI chat bubbles), booking slot-fill progress bar, Stamp animation on confirm. Streams from WebSocket events.

- [ ] **Phase 6 — Technician Voice Dispatch**  
  Dispatch FSM: call technician, read job, capture "haan pakka" / "nahi", fallback chain, `dispatch.*` events. Dispatch log in dashboard. Full tests.

- [ ] **Phase 7 — Money Loop (Promises, Reminder Trail, Simulated Clock)**  
  Collection FSM: post-job payment follow-up, objection handling, promise-to-pay capture. APScheduler for callback scheduling. Simulated clock with fast-forward in DEMO mode. Reminder trail UI.

- [ ] **Phase 8 — Evon Integration**  
  Swap rule-based extractor with Evon v3.3-backed implementation behind `Extractor` interface. Measure accuracy vs rule-based baseline. Keep fallback always active.

- [ ] **Phase 9 — Test Harness + Metrics Page**  
  Scripted call replay harness (plays pre-recorded synthetic audio through the pipeline). Metrics dashboard: booking success rate, dispatch acceptance rate, collection rate, latency. Results from our own test runs only.

- [ ] **Phase 10 — Polish + Demo Mode**  
  Final UI polish. Demo mode: seeded data, scripted call playback, clock fast-forward. Onboarding flow. Accessibility audit. Performance audit. Error states. Empty states.

- [ ] **Phase 11 — Demo Video + Post + Submission Pack**  
  60-second demo video. LinkedIn/Twitter post draft. Submission pack: README, video, live demo URL (if applicable), one-page project summary.

---

## Notes

- Phases are sequential; do not start the next phase until the current one's acceptance criteria pass.
- Each phase ends with a PHASE REPORT (see `AGENT_RULES.md`).
- Phase 0 acceptance criteria are in the project spec (Section 9).

