# Project Progress

## Current Status Summary

The project is organized into milestone-based delivery (M1–M5 **delivered**).
Milestone 4 public portal migration is **delivered** at `uis/website`. Milestone 5 backend and internal ops platform is **delivered** (`services/api`, backoffice landing on :3001, Docker Compose). Legacy `apps/healthcore_web_portal/` and `apps/src` remain unchanged.

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

### Milestone 4: Public Portal Migration (Delivered)

- Goal: migrate milestone 1 public web portal to the same stack as milestone 3 without retiring the legacy static app yet.
- **Delivered:**
	- `uis/website` — Next.js 16, App Router, TypeScript, Tailwind v4 (PostCSS build, no CDN).
	- Routes: `/` (from `index.html`), `/enquiry-form` (from `application.html`).
	- Shared layout: header, footer, EN/ES via `?lang=` and `localStorage` (`healthcore_lang`).
	- Form validation ported to `lib/enquiry-validation.ts` + `hooks/use-enquiry-form.ts` (no `apps/src` imports yet).
	- Schema.org JSON-LD on landing and enquiry routes.
	- `npm run verify` (lint + build) passes in `uis/website`.
- **Retained:** `apps/healthcore_web_portal/` (static HTML/JS) — not modified.
- **Deferred:** Import `apps/src` utilities into the enquiry form (future phase).
- **Next:** Optional legacy retirement after stakeholder cutover per `memory-bank/references/milestone4_ai_plan/m4_portal_migration_plan.md`.

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

### Milestone 5: Backend and Internal Operations Platform (Delivered)

FastAPI monolith, JWT auth, internal tool consolidation, inventory, incident management, and Docker dev environment. Architecture proposal: `docs/architecture_proposal.md`.

#### Incident Analyzer (Delivered)

- Goal: analyze patient incident CSV exports with HIPAA-safe aggregates for Patient Experience reporting.
- **Delivered:**
  - `uis/incident_analyzer/analysis_core.py` + `analyze.py` — pandas CLI via `uv run analyze`; verified against `incidents-healthcore.csv` (100 rows, 94 valid, average 3.58).
  - `services/api` — FastAPI + Pydantic v2; `POST /api/v1/incidents/analyze`, `GET /api/v1/incidents/results/export`; imports shared `analysis_core`. Managed with `uv sync` / `uv run pytest`.
  - `uis/incident_analyzer` — Next.js 16 dashboard (port 3002): CSV upload, JSON dashboard, CSV export button; CLI uses `uv.lock` + `uv sync`.
  - `npm run verify` passes in `uis/incident_analyzer`; `uv run pytest` passes in `services/api`.
- Plan: `memory-bank/references/incident_analyzer_ai_plan/incident_analyzer_plan.md`.

#### Supplier Directory (Delivered)

- Goal: replace departmental supplier spreadsheets with a centralized registry API and internal directory UI.
- **Delivered:**
  - `services/api/app/domains/procurement/suppliers/` — TinyDB store, Pydantic schemas, CRUD + soft-delete API under `/api/v1/suppliers`.
  - `app/seed.py` — idempotent seeder for 15 suppliers (`uv run seed`).
  - `uis/supplier_directory` — Next.js 16 dashboard (port 3003): list, API-driven country/category filters, add form, Actions-column rate/status controls, compliance column.
  - `uv.lock` + `uv sync` for backend dependency management; seed via `uv run seed`.
  - `pytest` (29 tests) passes in `services/api`; `npm run verify` passes in `uis/supplier_directory`.
- Plan: `memory-bank/references/supplier_directory_ai_plan/IMPLEMENTATION_PLAN.md`.


#### Authentication (AUTH-01) (Delivered)

- Goal: add JWT-based authentication and route protection to `services/api`.
- **Delivered:**
  - `app/core/db.py` — shared TinyDB singleton; suppliers store refactored to use it.
  - `app/domains/auth/` — register, login, `/auth/me`; JWT HS256 via `python-jose`; bcrypt password hashing.
  - `app/domains/users/` — user CRUD in TinyDB `users` table; selective route protection via `get_current_user`.
  - `app/core/dependencies.py` — reusable `OAuth2PasswordBearer` dependency.
  - `tests/test_auth.py` — 26 auth test cases; full suite 57 tests passing.
  - `services/api/.example.env` — `SECRET_KEY`, `JWT_EXPIRE_MINUTES` (copy to `.env` before run).
  - `services/api/README.md` — setup, auth endpoints, example flow.
- `/suppliers` and `/incidents` protected in AUTH-02 Step 10; see router wiring in `app/api/v1/router.py`.
- Plan: `memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN_auth_1.md`.

#### Authentication (AUTH-02 / AUTH-03) (Delivered)

- Goal: backoffice landing app, auth flows, password reset, same-origin internal tool routes.
- **Delivered:** `uis/backoffice/landing/` on port **3001**; public website on **3000**; CORS defaults `3000`/`3001`.
- Login, register, profile, change-password, forgot/reset password flows; `AuthGuard` + `(protected)` routes.
- All internal tools as landing same-origin routes; talent tracker at `uis/backoffice/talent-tracker/`; `healthcoreFetch` for Bearer API calls.
- Plan: `memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN_auth_2_3.md`.

#### Critical Error Handling (Delivered)

- Goal: fix the 10 CRITICAL findings from `memory-bank/references/error_handling_test/error_handling_specs.md` without adding features.
- **Delivered on branch `feature/critical_error_handling`:**
  - **Backend (#1–#2):** Global FastAPI exception handler in `app/main.py`; UTF-8 decode guard in incidents `service.py`; `tests/test_error_handling.py`.
  - **Frontend (#5–#10):** Network error handling in `uis/backoffice/landing/lib/api.ts`; change-password hook try/catch/finally; talent-tracker `lib/api.ts` network guard + sanitized API errors.
  - **Scripts (#3–#4):** `skills/data-analysis/scripts/pandas_clean.py` refactored to `main()` with validation, scoped exceptions, and `sys.exit`.
  - **Verified:** `uv run pytest` — 72 passed; `npm run build` — landing app (includes talent-tracker via path aliases); `pandas_clean.py` smoke test — exit 1 + stderr on missing file.
- **Deferred:** 61 non-critical findings (HIGH/MEDIUM/LOW) per `error_handling_IMPLEMENTATION_PLAN.md` follow-up section.
- Plan: `memory-bank/references/error_handling_test/error_handling_IMPLEMENTATION_PLAN.md`.

#### Medical Supply Inventory API (Delivered)

- Goal: centralised medical supply inventory REST API with computed stock levels and order history.
- **Delivered:**
  - `services/api/app/domains/inventory/` — SQLModel ORM (`MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`) on Supabase PostgreSQL via `get_supabase_db()`; TinyDB auth unchanged.
  - Six endpoints under `/api/v1/inventory/` — products CRUD (GET public, POST auth), inbound/outbound orders (POST auth), combined order history (GET public).
  - Stock computed as `SUM(deliveries) − SUM(consumptions)`; negative stock rejected with HTTP 400.
  - Idempotent inventory seed (6 supplies, 4 deliveries, 3 consumptions) wired into `uv run seed`.
  - Supabase project **`milestone5_inventory`** (`wqvklsghwmwylucfhzax`, `us-west-2`).
  - `tests/test_inventory.py` — 12 test cases; full suite **82 passed**.
- Plan: `memory-bank/references/milestone5_ai_plan/milestone5_backend_implementation_plan.md`.

#### Medical Supply Inventory Frontend (Delivered)

- Goal: backoffice UI for stock visibility, delivery logging, consumption logging, and order history.
- **Delivered:**
  - `uis/backoffice/inventory/` — feature module with API layer, hooks, and components (≤80 lines per file).
  - Landing routes at `/inventory`, `/inventory/products`, `/inventory/orders`, `/inventory/orders/inbound`, `/inventory/orders/outbound`.
  - `@backoffice/inventory` alias in `landing/next.config.ts` and `landing/tsconfig.json`; Tailwind `@source` in `globals.css`.
  - Hub nav card after Supplier Directory; `ToolToolbar` layout; "Back to Inventory" on sub-pages.
  - `npm run verify` passes in `uis/backoffice/landing`.
- Plan: `memory-bank/references/milestone5_ai_plan/milestone5_frontend_implementation_plan.md`.

#### Centralized Incident Manager (Delivered)

- Goal: log, track, and manage patient incidents in the browser with CRUD API and summary dashboard.
- **Delivered:**
  - `services/api/app/domains/incidents/` — SQLModel `Incident` on Supabase; five endpoints under `/api/v1/incidents/`; lifecycle validation; `incident_id` column for seed dedupe only.
  - `scripts/seed_incidents.py` — idempotent CSV seed from plan-folder `incidents-healthcore.csv` (94 valid rows).
  - Merged `feature/critical_error_handling` global 500 handler into `feature/milestone5`.
  - `uis/backoffice/incident-manager/` — landing, form, filterable list (status/origin/branch/category), summary dashboard.
  - Landing routes `/incident-manager/*`; hub nav card after Incident Analyzer.
  - `tests/test_incidents_mgmt.py` — 16 cases; `tests/test_seed_incidents.py` — 4 cases; backend incidents domain **~90%** coverage; `npm run verify` passes.
  - **Eval gap fixes:** shared validation in `packages/shared/python/healthcore_incidents/` (API + seed); client form validation in `packages/shared/lib/incident-validation.ts`; seed/idempotency tests; 500 message aligned to spec.
- Plan: `memory-bank/references/centralized_incident_manager_ai_plan/centralized_incident_manager_implementation_plan.md`.

#### Unit test gap coverage (Delivered)

- Goal: close pytest and Jest gaps per `memory-bank/references/unit_tests/unit_test_SPECS.md`.
- **Delivered:**
  - Root `TESTING.md` — run commands, test plan, coverage results, bugs/AI log.
  - `services/api/tests/` — 18 new pytest cases (`test_auth.py` +8, `test_incidents.py` +5, `test_suppliers.py` +3 parametrized); **88 passed**, **97%** line coverage.
  - `uis/website` — Jest + `__tests__/enquiry-validation.test.ts` (22 cases).
  - `uis/supplier_directory` — Jest + `format.test.ts` and `supplier-filter-params.test.ts` (17 cases).
  - BUG-001 fixed: weekend preferred-date validation added to `enquiry-validation.ts`.
- Plan: `memory-bank/references/unit_tests/unit_test_IMPLEMENTATION_PLAN.md`.

#### Docker development environment (#infra-40) (Delivered)

- Goal: containerize the monorepo for local development with zero-step onboarding via Docker Compose.
- **Delivered:**
  - Docker Compose stack: `ui` (website :3000 + backoffice landing :3001) and `api` (FastAPI :8000) on `healthcore_net`.
  - Root `.example.env` → `.env` for Docker; `services/api/.example.env` for manual local API workflow.
  - Compose `test` profile: `docker compose --profile test run --rm test` for one-shot pytest; `docker compose exec api uv run pytest` when stack is running.
  - Manual run documented in README § Manual development.
  - Proactive `npm ci` for six UI apps in the UI image; `scripts/check_ui_dep_versions.py`; `TESTING.md` guardrails.
- Plan: `memory-bank/references/docker_ai_plan/docker_implementation_plan.md`.

#### Telemetry Design (Phase 1) (Delivered)

- Goal: design documentation for backoffice inventory, incident filters, and auth telemetry (no instrumentation code).
- **Delivered:**
  - `docs/telemetry/telemetry-plan.md` — 3 reconciled KPIs, flow mapping, envelope (`schemaVersion` 1.1.0), 11-event catalog (10 instrumentable + 1 design-only).
  - `docs/telemetry/event-schemas.json` — JSON Schema draft-07 with `eventEnvelope` + per-event definitions (`x-pii: false` on all).
  - v1.1 events: `supply_consumption_form_abandoned`, `incident_list_filter_applied`.
- **Next:** Phase 2 frontend capture + stub endpoint per `telemetry_frontend_implementation_plan.md`.
- Plan: `memory-bank/references/telemetry_ai_plan/telemetry_design_implementation_plan.md`.

## Future Feature Additions

- Expand `services/api` per architecture proposal (remaining domains in doc §12); opaque session tokens for HIPAA (SPECS follow-up).
- Expand reusable shared logic and typing between migrated milestone 1 and existing milestone 3 apps.
- Extend milestone 2 function usage in UI workflows where validated logic improves data quality.
- Improve cross-app bilingual consistency and content governance.
- Integrate `apps/src` validators into `/enquiry-form` when milestone 2 wiring is scheduled.
- Legacy portal retirement and redirect strategy after stakeholder cutover approval.
- Optional: extract shared operations registry from `apps/src/main.ts` and `uis/backoffice/backoffice_functions/lib/operations-registry.ts` to reduce drift.
