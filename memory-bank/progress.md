# Project Progress

## Current Status Summary

The project is organized into milestone-based delivery.
Milestone 1, milestone 2, and milestone 3 establish the current implementation baseline.
Milestone 4 public portal migration is **delivered** at `uis/website` (`/` landing, `/enquiry-form` enquiry). Legacy `apps/healthcore_web_portal/` remains unchanged. Milestone 2 internal manual test UI is **delivered** at `uis/backoffice/backoffice_functions` (Next.js 16, imports from `apps/src` utils/types). `uis/backoffice/` is the parent folder for internal ops apps. Legacy `apps/src/index.html` + CLI + tests remain unchanged.

## Major Milestones

### Milestone 1: Public Website and Structured Enquiry Intake

- Goal: establish a credible bilingual public presence and reduce unstructured intake.
- Delivered focus: landing page content, service and location presentation, and patient enquiry workflow.
- Technical approach: static HTML, JavaScript, and Tailwind CSS.
- Business outcome target: improve trust, accessibility, and front-desk intake quality.

### Milestone 2: Operational Programming Foundation

- Goal: deliver reliable operational business logic for key healthcare workflows.
- Delivered focus: typed data modeling, filtering/search utilities, denial and no-show calculations, CME compliance logic, and validations.
- Technical approach: modular TypeScript utilities executed and verified in Node.js context.
- Business outcome target: trusted weekly KPI generation for billing, clinical, and compliance teams.

### Milestone 3: Talent Pipeline Tracker

- Goal: deliver a mobile-first internal recruiting application.
- Delivered focus: candidate list/detail/edit/new flows, filtering/search/pagination, notes workflows, and API integration.
- Technical approach: Next.js 16 with App Router, TypeScript, and Tailwind CSS.
- Business outcome target: faster and clearer candidate lifecycle management.

### Milestone 4: Public Portal Migration (In Progress)

- Goal: migrate milestone 1 public web portal to the same stack as milestone 3 without retiring the legacy static app yet.
- **Delivered (initial):**
	- `uis/website` — Next.js 16, App Router, TypeScript, Tailwind v4 (PostCSS build, no CDN).
	- Routes: `/` (from `index.html`), `/enquiry-form` (from `application.html`).
	- Shared layout: header, footer, EN/ES via `?lang=` and `localStorage` (`healthcore_lang`).
	- Form validation ported to `lib/enquiry-validation.ts` + `hooks/use-enquiry-form.ts` (no `apps/src` imports yet).
	- Schema.org JSON-LD on landing and enquiry routes.
	- `npm run verify` (lint + build) passes in `uis/website`.
- **Retained:** `apps/healthcore_web_portal/` (static HTML/JS) — not modified.
- **Deferred:** Import `apps/src` utilities into the enquiry form (future phase).
- **Next:** Stakeholder sign-off per UAT checklists in `memory-bank/references/milestone4_ai_plan/m4_portal_migration_plan.md`; optional legacy retirement after cutover.

### Milestone 2 Backoffice Manual Test UI (Delivered)

- Goal: replace the browser workflow of the M2 manual test page with a Next.js internal app.
- **Delivered:**
  - `uis/backoffice/backoffice_functions` — Next.js 16, App Router, TypeScript, Tailwind v4; sky/teal brand aligned with `uis/website`.
  - Parent folder `uis/backoffice/` reserved for additional internal apps.
  - Single route `/` — function selector, dynamic params, run selected/all, results + history (parity with `apps/src/index.html`).
  - Imports business logic from `apps/src/utils/*` and types from `apps/src/types/models` via `@healthcore/src/*` path alias.
  - Registry and sample fixtures in `uis/backoffice/backoffice_functions/lib/` (copy-only; `apps/src/main.ts` unchanged).
  - `npm run verify` (lint + webpack build) passes in `uis/backoffice/backoffice_functions`.
- **Retained:** `apps/src/main.ts` (CLI), `apps/src/index.html` (legacy browser), `apps/src/tests/run-tests.ts`.
- Plan: `memory-bank/references/backoffice_cleanup_ai-plan/backoffice_functions_cleanup_plan.md`.

## Architecture (target state — documented)

- **`docs/architecture_proposal.md`** — Approved proposal for FastAPI modular monolith at `services/api`, Supabase, domain boundaries, Auth/JWT, M2 backend exclusion. **Initial slice delivered** (incidents reporting only).
- Planning source: `architecture_proposal_plan.md` at repo root.

### Incident Analyzer (Delivered)

- Goal: analyze patient incident CSV exports with HIPAA-safe aggregates for Patient Experience reporting.
- **Delivered:**
  - `uis/incident_analyzer/analysis_core.py` + `analyze.py` — pandas CLI via `uv run analyze`; verified against `incidents-healthcore.csv` (100 rows, 94 valid, average 3.58).
  - `services/api` — FastAPI + Pydantic v2; `POST /api/v1/incidents/analyze`, `GET /api/v1/incidents/results/export`; imports shared `analysis_core`. Managed with `uv sync` / `uv run pytest`.
  - `uis/incident_analyzer` — Next.js 16 dashboard (port 3002): CSV upload, JSON dashboard, CSV export button; CLI uses `uv.lock` + `uv sync`.
  - `npm run verify` passes in `uis/incident_analyzer`; `uv run pytest` passes in `services/api`.
- Plan: `memory-bank/references/incident_analyzer_ai_plan/incident_analyzer_plan.md`.

### Supplier Directory (Delivered)

- Goal: replace departmental supplier spreadsheets with a centralized registry API and internal directory UI.
- **Delivered:**
  - `services/api/app/domains/procurement/suppliers/` — TinyDB store, Pydantic schemas, CRUD + soft-delete API under `/api/v1/suppliers`.
  - `app/seed.py` — idempotent seeder for 15 suppliers (`uv run seed`).
  - `uis/supplier_directory` — Next.js 16 dashboard (port 3003): list, API-driven country/category filters, add form, Actions-column rate/status controls, compliance column.
  - `uv.lock` + `uv sync` for backend dependency management; seed via `uv run seed`.
  - `pytest` (29 tests) passes in `services/api`; `npm run verify` passes in `uis/supplier_directory`.
- Plan: `memory-bank/references/supplier_directory_ai_plan/IMPLEMENTATION_PLAN.md`.


### Authentication (AUTH-01) (Delivered)

- Goal: add JWT-based authentication and route protection to `services/api`.
- **Delivered:**
  - `app/core/db.py` — shared TinyDB singleton; suppliers store refactored to use it.
  - `app/domains/auth/` — register, login, `/auth/me`; JWT HS256 via `python-jose`; bcrypt password hashing.
  - `app/domains/users/` — user CRUD in TinyDB `users` table; selective route protection via `get_current_user`.
  - `app/core/dependencies.py` — reusable `OAuth2PasswordBearer` dependency.
  - `tests/test_auth.py` — 18 SPECS test cases; full suite 49 tests passing.
  - `services/api/.env.example` — `SECRET_KEY`, `JWT_EXPIRE_MINUTES`.
- `/suppliers` and `/incidents` remain unprotected; commented wiring example for future milestones.
- Plan: `memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN.md`.

## Future Feature Additions

- Expand `services/api` per architecture proposal (Supabase, remaining domains in doc §12); opaque session tokens for HIPAA (SPECS follow-up).
- Expand reusable shared logic and typing between migrated milestone 1 and existing milestone 3 apps.
- Extend milestone 2 function usage in UI workflows where validated logic improves data quality.
- Improve cross-app bilingual consistency and content governance.
- Integrate `apps/src` validators into `/enquiry-form` when milestone 2 wiring is scheduled.
- Legacy portal retirement and redirect strategy after stakeholder cutover approval.
- Optional: extract shared operations registry from `apps/src/main.ts` and `uis/backoffice/backoffice_functions/lib/operations-registry.ts` to reduce drift.
