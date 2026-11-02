# Agent Rules

These rules apply to every phase of the Pakka project. An agent working on this codebase must follow them without exception.

---

## Start-of-Phase Protocol

Before writing any code at the start of a phase:

1. **Re-read all files in `/docs/`** to restore full context.
2. **Restate the phase goal** and its acceptance criteria in your working notes or phase report.
3. **List all files** you will create or modify before making any changes.
4. **Only then begin building.**

---

## End-of-Phase Protocol

Before declaring a phase complete:

1. Run `pnpm typecheck`, `pnpm lint`, and `pnpm build` in `/apps/web` — fix all failures.
2. Run `pytest -v` in `/apps/api` — fix all failures.
3. **Update the checkbox** in `/docs/PHASES.md` for the completed phase.
4. **Do not start the next phase.**
5. **Do not rewrite earlier phases** except to fix confirmed bugs.

---

## Phase Report Format

End every phase with a **PHASE REPORT** in exactly this format:

```
## PHASE REPORT — Phase N: [Name]

### 1. What Was Built
[Description of everything built]

### 2. Files Created / Changed
[Bulleted list with paths]

### 3. Commands to Run
[Exact commands for the user to reproduce/verify]

### 4. Test / Build Results
[Paste actual output from typecheck, lint, build, pytest]

### 5. Decisions and Deviations
[Any assumptions made; any deviations from docs/spec with justification]

### 6. Problems and Open Questions
[Anything blocked, uncertain, or requiring user input]

### 7. Acceptance Criteria Checklist
- [ ] criterion 1 — PASS/FAIL
- [ ] criterion 2 — PASS/FAIL
...
```

---

## Coding Standards

### General
- Follow clean, readable, and consistent coding practices.
- Use meaningful variable and function names.
- Add docstrings or comments for all functions and non-obvious logic.
- Keep functions short and focused on a single responsibility.
- Avoid deep nesting and overly complex logic.
- Maintain consistent formatting and structure across files.

### TypeScript / Next.js
- Strict TypeScript (`"strict": true`) at all times.
- No `any` types; use proper types or `unknown` with guards.
- Use `type` over `interface` for object shapes (consistency); use `interface` only for extendable contracts.
- All server components are async by default; client components use `"use client"` only when necessary.
- TanStack Query for all server-state fetching; Zustand for client-only UI state.
- ESLint + Prettier must pass with zero warnings.

### Python / FastAPI
- Python 3.11+ syntax; use `asyncio` throughout.
- Pydantic v2 for all data validation.
- `pydantic-settings` for all configuration (loaded from `.env`).
- `ruff` for linting and formatting — must pass with zero errors.
- All routes have typed request/response models.
- All async functions use `async def`.
- pytest for all tests; aim for ≥ 80% coverage on business logic.

### UI / Design
- Every UI change must be visually verified at 360, 768, 1024, and 1440 px.
- Never mix two UI libraries inside a single component.
- All interactive elements must have ARIA labels and visible focus rings.
- Touch targets ≥ 44 px.
- All motion uses Framer Motion springs and respects `prefers-reduced-motion`.
- Keep the UI premium and responsive at every step — never ship a rough WIP UI.

---

## Non-Negotiable Product Rules

(See `/docs/PROJECT_CONTEXT.md` Section 3 for full detail)

- Assistant always identifies as a digital assistant at call start.
- Assistant never denies being an AI; offers human callback when asked.
- Never threaten or abuse anyone.
- Stop calling on "wrong number".
- Outbound hours enforced server-side from owner settings (default 9 AM – 8 PM IST).
- Inbound answering is always 24/7.
- No real personal data anywhere in repo or demo.
- No secrets in the repo.
- No bought engagement or bots.
- All metrics from our own test runs only.
- No new libraries without explicit owner approval.

---

## Secrets & Environment

- All secrets via environment variables from `.env`.
- `.env` is in `.gitignore`.
- `.env.example` must always be up to date with every new variable added.
- Never log or print actual secret values.

---

## DEMO Mode

- Dashboard always supports DEMO mode with seeded synthetic data.
- DEMO mode must work completely without telephony credentials.
- Scripted call simulations use pre-recorded synthetic transcripts.
- Simulated clock can be fast-forwarded via UI control.
- DEMO mode is the primary vehicle for the competition demo video.

