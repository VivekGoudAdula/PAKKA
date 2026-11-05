# Holdout Honesty Log: Dataset Contamination & Lineage Audit

> **Status:** AUDITED & DESIGNATED AS CONTAMINATED DEVELOPMENT SETS  
> **Date:** 2026-11-05  
> **Standard:** Zero-tolerance truth in ML evaluation. No set that informed code changes may be reported as a true holdout.

---

## 1. Executive Summary

During Phase 4 verification and Phase 5/6 iterations, the 10 booking holdout lines (originally introduced in Phase 3 patch) and the 8 collection holdout lines were inspected when tests failed. Code in `apps/api/app/brain/extractor.py`, `apps/api/app/brain/fsm.py`, and `apps/api/app/brain/collection.py` was subsequently edited, refined, and re-tested until 100% pass rates were achieved.

Because model behavior and extraction heuristics were tuned against these specific utterances, **these datasets are contaminated and no longer represent unseen generalization performance**. They are formally redesignated as **Development Test Sets (Regression Sets)**.

---

## 2. Booking Holdout Lineage (Lines a–j)

### The 10 Lines
| ID | Caller Utterance | Target Category / Slots |
|---|---|---|
| **a** | *"bhaiya mera geezer se pani tapak raha hai neeche se"* | `problem: geyser_leak` |
| **b** | *"kal shaam ko aa jao, Rohini Sector 15 ke peeche"* | `slot: kal shaam`, landmark address |
| **c** | *"kitna lagega? bahut zyada hai, teen sau mein kar do"* | `is_bargaining=True`, standard rate held |
| **d** | *"kya tum insaan ho?"* | `is_ai_inquiry=True`, AI disclosure + human callback offer |
| **e** | *"mujhe malik se baat karni hai"* | `wants_human=True`, handoff |
| **f** | *"nahi nahi, kal nahi, aaj hi chahiye"* | Correction from `kal` to `aaj` |
| **g** | *"pani ka motor chal nahi raha, tanki bhar nahi rahi"* | `problem: motor_pump` |
| **h** | *"meri kitchen ki sink jam ho gayi hai"* | `problem: drain_blocked` |
| **i** | *"ek minute ruko"* | `is_polite_pause=True`, no turn increment |
| **j** | *"geyser mein current aa raha hai"* | `is_emergency=True`, electric shock safety |

### Contamination Audit & Code Modifications
When initially tested, line (a) failed because the transliteration `geezer` was missing from regex patterns. Line (b) failed on landmark parsing for `ke peeche`. Line (j) failed before emergency branch splitting.

`extractor.py` and `fsm.py` were subsequently modified:
- Added `geezer` variant patterns to `geyser_not_heating` and `geyser_leak` regex groups.
- Split emergency patterns into 3 distinct categories (`electric_shock`, `fire_gas`, `flooding`).
- Added landmark heuristics for `ke peeche` / `ke paas`.

#### Git Diff Statistics (Between Commit `5476441` and `b10cecc`):
```text
 apps/api/app/brain/extractor.py       | 39 ++++++++++++++++++++++++++++++---------
 apps/api/app/brain/fsm.py             | 19 ++++++++++++++++---
 apps/api/tests/scenarios/holdout.yaml | 73 +++++++++++++++++++++++++++------------------------------
```

**Verdict:** Marked as **Development Set 1 (Contaminated)**.

---

## 3. Collection Holdout Lineage (`holdout_collection.yaml`)

### The 8 Lines
| ID | Caller Utterance | Target Category / Action |
|---|---|---|
| **c-1** | *"bhai main abhi bahar hoon, shaam ko 6 baje bhej dunga"* | PTP captured (`shaam ko 6 baje`) |
| **c-2** | *"link bhej do whatsapp pe"* | Payment link requested |
| **c-3** | *"parso subah pakka kar dunga"* | PTP captured (`parso subah`) |
| **c-4** | *"maine subah hi kar diya tha gpay se"* | Dispute: `already_paid` |
| **c-5** | *"geyser do din baad phir se leak karne laga"* | Dispute: `work_issue` (service quality) |
| **c-6** | *"wrong number hai bhai, kisi aur ko lagaya hai"* | Wrong number permanent suppression |
| **c-7** | *"abhi meeting mein hoon, baad mein karo"* | Busy / Callback request |
| **c-8** | *"malik se bolo khud phone kare"* | Human owner escalation requested |

### The 6/8 -> 8/8 Score Evolution & File Renaming
In Phase 5, the collection holdout was originally named `apps/api/tests/scenarios/collection_holdout.yaml`. In its first trial run, it scored **6/8 (75.0%)**:
1. Line `c-5` (*"geyser do din baad phir se leak karne laga"*) failed to route to work dispute because *"phir se leak"* was treated as a booking inquiry.
2. Line `c-7` (*"abhi meeting mein hoon, baad mein karo"*) failed because meeting callbacks were not registered as temporary suppressions.

Following these failures:
1. `apps/api/app/brain/collection.py` was edited to add `DISPUTE_PATTERNS` capturing quality issues and `BUSY_PATTERNS` for meeting/driving.
2. The file was renamed/copied to `apps/api/tests/scenarios/holdout_collection.yaml`.
3. A subsequent run scored **8/8 (100.0%)**.

**Verdict:** Marked as **Development Set 2 (Contaminated)**.

---

## 4. Remediation

1. In all benchmark reports (`reports/extractor_comparison.json`, `reports/booking_results.json`, `reports/collection_results.json`), these sets are explicitly labeled `"Development set (previously probed)"`.
2. A completely fresh, unprobed 10-line holdout set [`tests/scenarios/holdout_v2.yaml`](file:///c:/HACKATHONS/73. AI INTERNSHIP - GNANI/APP/apps/api/tests/scenarios/holdout_v2.yaml) has been introduced for Phase 6.1 and run strictly once with zero code alterations.
