# Technical Context

## Monorepo layout

| Path | Role |
|------|------|
| `uis/website/` | Public Next.js portal (M1/M4) |
| `uis/backoffice/landing/` | Backoffice hub — auth + all internal tool routes (M5) |
| `uis/backoffice/*` | Feature modules aliased into landing (inventory, incident-manager, talent-tracker, etc.) |
| `uis/incident_analyzer/` | Shared Python analysis core + deprecated standalone UI |
| `uis/supplier_directory/` | Supplier UI components (served via landing) |
| `services/api/` | FastAPI modular monolith (M5) |
| `apps/` | Legacy M1 static portal, M2 TypeScript utils, frozen M3 tracker copy |
| `packages/shared/` | Shared TypeScript and Python validation/types |
| `scripts/` | Seeding, version checks, utilities |
| `memory-bank/` | Agent bootstrap and milestone context |
| `docs/` | Cross-cutting architecture documentation |

Docker Compose: `api` + `ui` services; optional `test` profile for pytest. Root env template: `.example.env` → copy to `.env`.

## Local development ports

| Port | Service |
|------|---------|
| **3000** | `uis/website` (public) |
| **3001** | `uis/backoffice/landing` (hub + all tool routes) |
| **8000** | `services/api` (FastAPI) |

Do not run Docker UI and local `npm run dev` on the same ports simultaneously. See [README.md](../README.md) § Manual development.

## Manual development workflow

Three local processes (API required for backoffice):

1. **API** — `cd services/api && cp .example.env .env && uv sync --extra dev && uv run uvicorn app.main:app --reload --port 8000`
2. **Backoffice** — `cd uis/backoffice/landing && cp .example.env .env.local && npm install && npm run dev`
3. **Website** — `cd uis/website && npm install && npm run dev`

Env files: manual API uses `services/api/.env`; backoffice landing uses `.env.local` (from `cp .example.env .env.local`); `uis/website` needs no env file. Docker uses root `.env` from `cp .example.env .env`.

## Docker testing

| Use case | Command |
|----------|---------|
| One-off pytest (stack not required) | `docker compose --profile test run --rm test` |
| With coverage | `docker compose --profile test run --rm test uv run pytest --cov=app --cov-report=term-missing` |
| Against running stack | `docker compose exec api uv run pytest` |

Inventory tests use in-memory SQLite (`DATABASE_URL=""` in test config); live Supabase is not required for pytest. See [TESTING.md](../TESTING.md) for local and Jest commands.

## Tech Stack

### Milestone 1 (Legacy — retained)
- HTML, JavaScript, and Tailwind CSS (via CDN)
- Static pages: `apps/healthcore_web_portal/index.html`, `application.html`, `validation.js`
- No framework; client-side validation only

### Milestone 1 / Milestone 4 (Primary public app — `uis/website`)
- Next.js 16 (App Router) with TypeScript and Tailwind CSS v4 via PostCSS
- React 19 functional components (≤80 lines per component file)
- Routes: `/` (landing), `/enquiry-form` (patient enquiry)
- Bilingual EN/ES: `lib/i18n/translations.ts`, `LanguageProvider`, `?lang=` + `localStorage`
- No backend; form submit shows success modal only (parity with legacy)
- Verification: `cd uis/website && npm run verify`

### Milestone 2
- TypeScript for all business logic utilities
- Node.js for CLI/test execution
- Modular code structure: models, collections, search, transformations, validations
- Location: `apps/src/` — CLI, tests, legacy browser page (`index.html` + compiled `dist/main.js`)
- **Internal manual test UI:** served via landing `/backoffice-functions` (`uis/backoffice/backoffice_functions/`); imports utils via `@healthcore/src/*`

### Milestone 3
- Next.js 16 (App Router) with TypeScript and Tailwind CSS
- React functional components; mobile-first responsive design
- API integration with Talent Tracker API (`NEXT_PUBLIC_TRACKER_API_URL`)
- **Canonical location:** `uis/backoffice/talent-tracker/` via landing `/talent-tracker`
- **Frozen legacy:** `apps/talent-pipeline-tracker/` — unmaintained, not part of Docker

### Milestone 5 (Backend and internal ops platform)
- **API:** `services/api` — FastAPI + Pydantic v2; managed with `uv sync` / `uv run pytest`
- **Databases:** TinyDB (`db.json`) for users, auth, suppliers; Supabase PostgreSQL for inventory and incident manager
- **Auth:** JWT HS256; `healthcoreFetch` in `uis/backoffice/shared/` for Bearer injection
- **Backoffice:** landing on `:3001` with hybrid `externalDir` imports from sibling feature folders
- **Incident analysis:** shared `uis/incident_analyzer/analysis_core.py` (CLI + API)
- **Shared validation:** `packages/shared/python/` and `packages/shared/lib/`
- **Docker:** Compose `ui` + `api`; `test` profile for one-shot pytest

## Architectural Decisions Made

### Milestone 1 (Legacy)
- Two-page static site: landing page and application form with shared navigation
- Client-side validation and Schema.org markup

### Milestone 1 / Milestone 4 (`uis/website`)
- App Router; enquiry route `/enquiry-form` (not `/application`)
- Validation in `lib/enquiry-validation.ts`; M2 `apps/src` import deferred

### Milestone 2
- Typed utility modules with pure functions and deterministic calculations
- Manual test UI reuses `apps/src` via `@healthcore/src/*` path alias

### Milestone 3
- URL-driven filtering/search; custom components only; async/await API calls

### Milestone 5
- Same-origin backoffice on landing `:3001` — single `AuthGuard`, no cross-port tokens
- Dual-database API: TinyDB + Supabase
- Feature modules as sibling folders aliased into landing webpack build
- See [decisions.md](decisions.md) for full decision log

## Technical Constraints

- Accessibility and responsive design required throughout
- All styling via Tailwind CSS (no custom CSS unless necessary)
- **No backend** for public portal / enquiry form — client-side only
- M2 logic must be deterministic and testable
- Next.js components ≤80 lines and functional; no third-party UI libraries
- Python toolchain: `uv` only for `services/api` and incident CLI — no `requirements.txt`
