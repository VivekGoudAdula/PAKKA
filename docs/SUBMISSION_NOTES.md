# Pakka — Submission Notes & Truth in Engineering Report

**Project**: Pakka — Voice Assistant for Small Indian Service Businesses  
**Challenge**: Great Indian AI Internship Challenge by Gnani AI  
**Generated**: November 6, 2026 (Phase 8 Truth Revision)  
**System Mode**: Dual Mode (LIVE / DEMO)  
**Strict Safety Principle**: No LLM in call-flow control. 100% deterministic Hinglish State Machines.

---

## 1. Capability & Component Status Matrix

Every capability in Pakka is categorized strictly into one of five verified statuses:
- **VERIFIED LIVE**: Proven with external live network services during this run, verified by a file in `reports/` with mode `"live"`.
- **CODE COMPLETE - NOT VERIFIED LIVE**: Code fully implemented and structured for live execution, but external live network calls have not completed or succeeded.
- **TESTED AGAINST FAKES**: Fully tested and verified offline against mock, simulated, or fake test harnesses (e.g. `FakeWebSocket`, offline mock transport, synthetic dry-run audio).
- **SCRIPTED DEMO**: Deterministic simulation with seeded synthetic data and clock simulation.
- **PENDING USER**: Requires manual external credentials or human execution (e.g., active Exotel virtual number trunk / live Gnani API key / physical mic).

| Component / Subsystem | Capability | Status | Evidence File | Implementation Details & Truth Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Booking Brain** | Inbound Dialogue FSM | **TESTED AGAINST FAKES** | `reports/booking_results.json` | 100% deterministic FSM (`BookingFSM`) in `apps/api/app/brain/fsm.py`. 0 LLM hallucination. Average turn latency < 20 ms against offline test harnesses. |
| **Rule Extractor** | Slot Extraction | **TESTED AGAINST FAKES** | `reports/extractor_comparison.json` | Broad regex parser covering 6 problem categories, 5 slot timings, landmark address cleanup (leading prefix removal), bargaining floors, and declination across all states. |
| **Emergency Safety** | Hazard Triage | **TESTED AGAINST FAKES** | `reports/logs/pytest_phase7_1.txt` | Priority triage: electrical shock, fire/gas leak, and pipe burst flooding evaluated *before* routine booking. Emits `call.handoff` with urgent=True. |
| **AI Disclosure** | Identity & Transparency | **TESTED AGAINST FAKES** | `reports/logs/pytest_phase7_1.txt` | Mandatory greeting: *"...ki digital sahayak bol rahi hoon"*. 20 distinct regression test phrasings across Booking, Dispatch, and Collection FSMs. |
| **Dispatch Brain** | Technician Ranking | **TESTED AGAINST FAKES** | `reports/dispatch_results.json` | Multi-factor ranker: trade specialty (geyser, pipe, motor, tap) + active job load penalty. Deterministic FSM (`DispatchFSM`). Precompiled regex eliminates latency spikes. |
| **Dispatch Cascade** | Outbound Voice Confirmation | **CODE COMPLETE - NOT VERIFIED LIVE** | `reports/logs/pytest_phase7_1.txt` | Automated cascade code complete (`dispatch_service.py`), but no live phone call has ever succeeded without external telephony trunk. |
| **Collection Brain** | Tone Ladder Recovery | **TESTED AGAINST FAKES** | `reports/collection_results.json` | Multi-tier tone ladder (Tone 1 Friendly → Tone 2 Reminder → Tone 3 offers an owner callback and pauses reminders). Captures Promise-to-Pay (PTP) dates. |
| **Collection Safety** | Wrong Number & Tone 3 Suppress | **TESTED AGAINST FAKES** | `reports/logs/pytest_phase7_1.txt` | Tone 3, disputed, paused, and wrong numbers permanently suppressed from automated calls in `collection_scheduler.py`. |
| **Calling Hours** | Strict Telephony Windows | **TESTED AGAINST FAKES** | `reports/logs/pytest_phase7_1.txt` | Outbound calls restricted to owner settings (default 9:00 AM – 8:00 PM IST). Inbound answered 24/7. |
| **Gnani Realtime STT** | Prisma v3.0 WebSocket | **CODE COMPLETE - NOT VERIFIED LIVE** | `reports/logs/live_check.txt` | Real raw PCM streaming client (`GnaniSTTClient`) conforming to `wss://api.vachana.ai/stt/v3/stream`. Offline dry-run simulation verified; live network connection timed out in preflight. |
| **Gnani Realtime TTS** | Timbre v2.5 WebSocket | **CODE COMPLETE - NOT VERIFIED LIVE** | `reports/logs/live_check.txt` | Real streaming client (`GnaniTTSClient`) conforming to `wss://api.vachana.ai/api/v1/tts` with 8kHz PCM output. Offline dry-run simulation verified; live network connection timed out in preflight. |
| **Evon Extractor** | Evon v3.3 Modular Slotting | **TESTED AGAINST FAKES** | `reports/extractor_comparison.json` | Abstract interface designed for drop-in replacement. Tested against offline mock engine (`mock_evon.py`) with zero LLM hallucinations. |
| **Exotel Telephony** | AgentStream Bidirectional WS | **TESTED AGAINST FAKES** | `reports/logs/pytest_exotel_handler.txt` | `/ws/exotel` route handler tested via `FakeWebSocket` driving connected, start, media, mark, clear, and stop events with energy VAD and echo-loop guard. |
| **Live Telephony Call** | Real Phone Carrier Trunk | **PENDING USER** | `reports/live_check.json` | Live calls require user-provided Exotel virtual number and SIP trunk webhook URL pointing to Pakka server. |
| **Browser Voice Demo** | REST STT + TTS ("Talk to Pakka") | **PENDING USER** | `reports/live_rest_check.json` | Browser voice dialogue over Gnani REST endpoints with typed fallback, TTS audio cache, and concurrency guard. PENDING USER until `reports/live_rest_check.json` shows mode "live". |
| **Frontend Dashboard** | Next.js App Router | **CODE COMPLETE - NOT VERIFIED LIVE** | `reports/logs/build_phase7_1.txt` | Responsive, accessible light-themed dashboard (App, Live Console, Dispatch, Payments, Metrics, Design QA, Talk to Pakka). |
| **Demo Director** | Scripted 5-Beat Storyline | **SCRIPTED DEMO** | `apps/web/lib/stores/demo-director-store.ts` | Interactive floating director bar with Play/Pause, Restart, Recording mode, and instant beat jumping. |
| **Data Integrity** | Synthetic Seed Data | **TESTED AGAINST FAKES** | `reports/logs/pytest_phase7_1.txt` | 100% synthetic fictional names, masked phone numbers (`98XXXXXX00`), fictional Delhi NCR landmarks, and simulated SQLite ledger. |

---

## 2. Test & Verification Log Evidence (Phase 7.1)

All test executions follow the mandatory output log capture protocol (`... 2>&1 | Tee-Object -FilePath reports/logs/...`).
Verifiable raw log files generated during Phase 7.1:

1. **Pytest Full Suite (`reports/logs/pytest_phase7_1.txt`)**:
   - `test_audio.py`: **10 passed**
   - `test_booking_scenarios.py`: **2 passed**
   - `test_brain.py`: **54 passed**
   - `test_collection.py`: **5 passed**
   - `test_dispatch.py`: **4 passed**
   - `test_exotel_ws.py`: **4 passed**
   - `test_health.py`: **3 passed**
   - `test_ledger_parser.py`: **14 passed**
   - **Total**: **96 passed in 18.80 seconds**.

2. **Exotel Real Route Handler Test (`reports/logs/pytest_exotel_handler.txt`)**:
   - `test_real_exotel_handler_full_flow`: **PASSED**
   - `test_real_exotel_handler_barge_in_and_clear`: **PASSED**
   - `test_exotel_silence_does_not_trigger_barge_in`: **PASSED**
   - `test_echo_loop_guard_discards_playback_finals`: **PASSED**
   - **Total**: **4 passed in 16.37 seconds**.

3. **Ruff Linter (`reports/logs/ruff_phase7_1.txt`)**:
   - `All checks passed!` (0 lint errors across all backend modules).

4. **Frontend Quality Checks**:
   - Strict TypeScript compiler check (`tsc --noEmit`): **0 errors** (`reports/logs/tsc_phase7_1.txt`).
   - ESLint validation (`pnpm exec eslint .`): **0 errors, 0 warnings** (`reports/logs/eslint_phase7_1.txt`).
   - Next.js production build (`pnpm exec next build`): **14 static/dynamic routes compiled** (`reports/logs/build_phase7_1.txt`).

5. **Live Preflight Tool (`reports/logs/live_check.txt`)**:
   - Output saved to `reports/live_check.json` (mode: `"mock"`). Live external WebSocket connection timed out; marked truthfully.

---

## 3. Truthful Architecture & Deviations

1. **No External LLM in the Call Loop**:
   - In customer service telephony, hallucinations (inventing non-existent technicians, quoting ₹50 for a motor overhaul, or agreeing to unrealistic promises) destroy business trust.
   - All conversation state transitions use deterministic Finite State Machines (FSMs) with explicit error recovery.
2. **Holdout V2 Contamination Transparency**:
   - Holdout V2 scenarios were probed and logged in `docs/HOLDOUT_LOG.md` as Development Set 3. They are permanently treated as regression test cases rather than blind holdout benchmarks.
3. **Synthetic Audio Tones Relocation**:
   - Mathematical test sine tones were relocated from test fixtures to `samples/synthetic_tones/` with clear labeling. Real telephony audio is never synthesized into unverified binary fixtures.
