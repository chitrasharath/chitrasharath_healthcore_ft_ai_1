# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

> _Instrucciones disponibles en español en [README.es.md](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## Current status of the template

The repository currently provides a **base folder structure and documentation skeleton**. It does not include runnable apps or global scripts yet.

- `CONTEXT.md` is a placeholder and must be replaced with your assigned company context.
- There is no root `AGENTS.md` yet.
- Shared package metadata exists in `packages/shared/package.json` (`@repo/shared-types`), but no workspace runner is configured at root.

---

## Repository structure

```text
ai-engineering-company-project-template/
├── README.md
├── README.es.md
├── CONTEXT.md                # Placeholder to be replaced with assigned context
├── agents/                   # Agent patterns/templates and tools docs
├── apps/                     # Product apps (web, APIs, dashboards)
├── data/                     # raw, process, pipelines, eval
├── docs/                     # Project and architecture documentation
├── packages/
│   └── shared/               # Shared package (@repo/shared-types)
├── scripts/                  # Script conventions/documentation
├── shared/                   # Shared assets/conventions at repo level
├── skills/                   # Reusable agent skills
└── workflows/                # Automation/orchestration documentation
```

---

## How to start

1. **Use this repository as a template** and create your own project repo.
2. **Clone** your repository (or open it in Codespaces).
3. **Replace** `CONTEXT.md` with the full context for your assigned company.
4. **Review** each top-level folder `README.md` to understand intended responsibilities (`apps/`, `data/`, `skills/`, etc.).
5. **Start implementing** milestone deliverables in `apps/`, reusing `packages/shared/` and `data/` as needed.

---

## Milestones (reference)

| Milestone | Focus        | Typical deliverables                        |
| --------- | ------------ | ------------------------------------------- |
| 0         | Prework      | Environment setup, first prompts            |
| 1         | Web          | Corporate website, forms, SEO               |
| 2         | Programming  | Business logic, scoring, calculations       |
| 3         | AI-driven UI | AI-generated interfaces                     |
| 4         | Next.js      | Portals, loyalty app, operations UI         |
| 5         | Backend      | Central API (locations, menus, sales, etc.) |
| 6         | Telemetry    | Data pipeline, dashboards                   |
| 7         | RAG & Memory | Semantic knowledge base, search             |
| 8         | Agents       | Support, onboarding, training agents        |
| 9         | Workflows    | n8n automations                             |
| 10        | Real-time    | Live dashboards, alerts, streaming          |

---

## HealthCore Backoffice (landing — port 3004)

All internal tools run as **same-origin routes** on the backoffice landing app. Log in once at the hub; no cross-port token passing.

```bash
cd uis/backoffice/landing
cp .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:3004**. Requires API on port **8000** (and `NEXT_PUBLIC_TRACKER_API_URL` for talent tracker).

| Route | Tool |
|-------|------|
| `/` | Hub (login, register, nav cards) |
| `/incident-analyzer` | Incident CSV analysis |
| `/supplier-directory` | Supplier registry |
| `/inventory` | Medical supply inventory (stock, deliveries, consumption) |
| `/talent-tracker` | Talent pipeline (external tracker API) |
| `/backoffice-functions` | M2 manual test dashboard |
| `/account/profile` | Profile |
| `/account/change-password` | Change password |

Public website: `uis/website/` on port **3005**.

```bash
cd uis/website
npm install
npm run dev
```

Open **http://localhost:3005** (no auth).

---

## Docker development

Prerequisites: Docker Engine + Compose v2 (or Docker Desktop).

### First run

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY and, for full platform features, DATABASE_URL
docker compose up --build
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Public website |
| http://localhost:3001 | Backoffice landing (hub + all tool routes) |
| http://localhost:8000/docs | API Swagger |

### Day-to-day

```bash
docker compose up
docker compose up -d
docker compose down
docker compose logs -f ui
docker compose logs -f api
docker compose exec api uv run pytest
docker compose exec api uv run seed
```

After dependency changes (`package.json` / `pyproject.toml`): `docker compose up --build`. If `node_modules` look stale, run `docker compose down -v` first.

### Optional seeding (post-first-up)

- `docker compose exec api uv run seed` — TinyDB suppliers (+ inventory when `DATABASE_URL` is set).
- Incident CSV seed (Supabase): `docker compose exec api uv run python /app/scripts/seed_incidents.py` when `DATABASE_URL` is configured.

### Port conflicts

Local non-Docker dev uses ports **3004/3005** (backoffice/website) and **8000** (API). Do not run `npm run dev` or `uv run uvicorn` on the same ports while Docker is up.

### Disk space

The UI image runs `npm ci` for six apps and needs several GB free during `docker compose up --build`. On small Codespaces disks, failed builds can fill the volume with cache and anonymous volumes.

Keep **at least 5–6 GB free** before building. When done with Docker for the day:

```bash
docker compose down -v
```

If a build fails with `ENOSPC: no space left on device`, prune unused Docker data from the repo root:

```bash
docker compose down -v          # stop stack and remove anonymous volumes
docker builder prune -af        # clear build cache (largest win after failed builds)
docker volume prune -f          # remove unused volumes
docker image prune -af          # optional — remove unused images if still tight
df -h /workspaces               # confirm free space before rebuilding
docker compose up --build
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port already in use | Stop the conflicting local dev server or run `docker compose down` |
| Build fails with `ENOSPC` / no space left on device | See [Disk space](#disk-space) — prune, then `docker compose up --build` |
| API exits immediately | Ensure `SECRET_KEY` and `JWT_EXPIRE_MINUTES` are set in `.env` |
| Backoffice webpack module errors | `docker compose up --build`; if persistent, `docker compose down -v` |
| Hot reload not working | Uncomment `WATCHPACK_POLLING=true` in `.env`, restart `ui` |
| Inventory / incident-manager errors | Set `DATABASE_URL` in `.env`, restart `api`, run seed |

Docker uses the root `.env` only. The local non-Docker API workflow continues to use `services/api/.env`.

Plan: `memory-bank/references/docker_ai_plan/docker_implementation_plan.md`.

---

## Monorepo conventions

Notes for contributors working across backend and UI apps:

- **Dual uv lockfiles (intentional):** `services/api/uv.lock` is the canonical backend lock (package-only workflow and Docker builds). Root `uv.lock` exists so `uv run pytest` works from the repository root. After any backend dependency change, re-lock **both**: `uv lock` inside `services/api` and `uv lock` at the repo root.
- **Test dependencies declared twice:** `services/api` `[project.optional-dependencies] dev` and root `[dependency-groups] dev` — keep them aligned.
- **Duplicate talent-tracker apps:** `uis/backoffice/talent-tracker/` is the active canonical copy (served through the backoffice landing app). `apps/talent-pipeline-tracker/` is a frozen legacy pre-relocation copy — unmaintained, not part of Docker, and must not receive changes.
- **Environment file naming:** Root `.env.example` is canonical for Docker. Per-app Next.js examples use `.env.local.example`. `services/api/.example.env` is for the local non-Docker API workflow only.
- **Per-app npm lockfiles:** Six active UI apps each keep their own `package-lock.json`. Version alignment is enforced by `python3 scripts/check_ui_dep_versions.py` (run before committing `package.json` changes). A root npm-workspaces conversion is deferred until after Docker lands.
- **`packages/shared/package.json` quirk:** Its `name` is `@repo/shared-types`, but consumers import via the `@repo/shared` alias in `tsconfig.json` paths and `next.config.ts` webpack aliases. The package is never npm-installed — no lockfile, raw `.ts` exports. Do not trust the `name` field; a rename follow-up is deferred.

---

## Backoffice Functions (M2 manual test)

Feature module at `uis/backoffice/backoffice_functions/` — **imported by landing** at `/backoffice-functions`. Standalone dev on port 3001 is deprecated.

```bash
cd uis/backoffice/landing && npm run dev
```

---

## Incident Analyzer

HealthCore patient incident CSV analysis with HIPAA-safe aggregate reporting. Shared logic lives in `uis/incident_analyzer/analysis_core.py`; the CLI, FastAPI backend, and Next.js dashboard all use the same calculations.

### CLI script

From `uis/incident_analyzer/`:

```bash
uv sync
uv run analyze incidents-healthcore.csv
```

The script prints a summary to the console and prompts `Export results to CSV? [y / n]:`. Answer `y` to write `incident-analysis-export.csv` in the current directory.

### Backend (FastAPI)

From `services/api/`:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API base URL: `http://localhost:8000`

Local dev works without a `.env` file. Uvicorn uses port **8000**; backoffice landing runs on **3004** and public website on **3005**. CORS defaults: `3004`, `3005`.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/docs` | GET | No | Swagger UI |
| `/api/v1/incidents/analyze` | POST | Yes | Upload CSV (`multipart/form-data`, field `file`) |
| `/api/v1/incidents/results/export` | GET | Yes | Download last analysis as CSV |
| `/api/v1/suppliers` | GET, POST | Yes | List or register suppliers |
| `/api/v1/suppliers/{id}` | GET, DELETE | Yes | Supplier detail; DELETE soft-suspends |
| `/api/v1/suppliers/{id}/rate` | PATCH | Yes | Update monthly rate |
| `/api/v1/suppliers/{id}/status` | PATCH | Yes | Activate or suspend supplier |
| `/api/v1/suppliers/{id}/details` | PATCH | Yes | Update optional fields |
| `/api/v1/inventory/products` | GET | No | List supplies with computed `current_stock` |
| `/api/v1/inventory/products` | POST | Yes | Register a new supply |
| `/api/v1/inventory/products/{id}` | GET | No | Single supply with computed stock |
| `/api/v1/inventory/orders/inbound` | POST | Yes | Log vendor delivery (increases stock) |
| `/api/v1/inventory/orders/outbound` | POST | Yes | Log consumption (decreases stock) |
| `/api/v1/inventory/orders` | GET | No | Combined delivery + consumption history |
| `/api/v1/auth/register` | POST | Register user; returns JWT |
| `/api/v1/auth/login` | POST | Login; returns JWT |
| `/api/v1/auth/me` | GET | Current user (Bearer token) |
| `/api/v1/auth/forgot-password` | POST | Request password reset link |
| `/api/v1/auth/reset-password` | POST | Set new password with reset token |
| `/api/v1/users` | GET, POST | List users (auth) or create user (public) |
| `/api/v1/users/{id}` | GET, PUT, DELETE | User CRUD (auth; PUT owner-only) |

### Dashboard (via landing)

Use `/incident-analyzer` on the backoffice landing app (`uis/backoffice/landing/`, port **3004**). Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in landing `.env.local`.

Standalone `uis/incident_analyzer/` on port 3002 is deprecated.

---

## Supplier Directory

Centralized supplier registry for HealthCore procurement and compliance. TinyDB-backed API at `services/api`; UI at `/supplier-directory` on the backoffice landing app (port **3004**).

### Seed database

From `services/api/`:

```bash
uv sync --extra dev
uv run seed
```

Loads 15 suppliers idempotently (skips existing names). Plan: `memory-bank/references/supplier_directory_ai_plan/IMPLEMENTATION_PLAN.md`.

When `DATABASE_URL` is set, the same command also seeds inventory data in Supabase (6 supplies, 4 deliveries, 3 consumptions). See [Inventory Management](#inventory-management-milestone-5) below.

### Dashboard (via landing)

Use `/supplier-directory` on the backoffice landing app (port **3004**). Standalone `uis/supplier_directory/` is deprecated.

Plan: `memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN_auth_2_3.md`.

---

## Inventory Management (Milestone 5)

Centralised medical supply inventory for HealthCore clinic operations: **REST API** at `services/api` and **backoffice UI** at `/inventory` on the landing app (port **3004**).

### Architecture

- **TinyDB** — users and authentication (unchanged).
- **Supabase (PostgreSQL)** — `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption` tables in project **`milestone5_inventory`**.
- Stock is computed on read: `SUM(deliveries) − SUM(consumptions)`; no direct stock mutation endpoint.
- **Frontend module** — `uis/backoffice/inventory/`, aliased as `@backoffice/inventory` into `uis/backoffice/landing/`.

### Backend environment

Add to `services/api/.env` (copy exact URI from Supabase Dashboard → Database → Transaction pooler):

```bash
DATABASE_URL=postgresql://postgres.[ref]:[url-encoded-password]@aws-1-us-west-2.pooler.supabase.com:6543/postgres
```

Tables are created automatically on API startup. URL-encode special characters in the database password.

### Seed and run API

From `services/api/`:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run seed
```

Swagger UI: http://localhost:8000/docs → `/api/v1/inventory/` routes.

POST inventory endpoints require Bearer auth (register via `/api/v1/auth/register` first). GET product and order endpoints are public.

### Dashboard (via landing)

From `uis/backoffice/landing/`:

```bash
npm install
npm run dev
```

Log in at **http://localhost:3004**, then open **Inventory Management** from the hub or navigate directly:

| Route | Description |
|-------|-------------|
| `/inventory` | Section landing (hero + nav cards) |
| `/inventory/products` | All supplies with color-coded stock levels |
| `/inventory/orders/inbound` | Log vendor delivery (4 fields) |
| `/inventory/orders/outbound` | Log clinical consumption (reactive stock display) |
| `/inventory/orders` | Order history (deliveries + consumptions) |

Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in `uis/backoffice/landing/.env.local`. POST requests use `healthcoreFetch` (Bearer token from login).

**Order history timestamps** — API stores UTC; the UI parses naive ISO strings as UTC and displays them in a user-selected timezone (default Eastern). The timezone dropdown appears on pages that show dates; preference is saved in `localStorage` (`healthcore_inventory_timezone`).

**TypeScript** — the inventory module symlinks `node_modules` from landing for type resolution:

```bash
ln -sf ../landing/node_modules uis/backoffice/inventory/node_modules
```

Verify: `cd uis/backoffice/landing && npm run verify`

Plans: `memory-bank/references/milestone5_ai_plan/milestone5_backend_implementation_plan.md`, `milestone5_frontend_implementation_plan.md`.

---

## Authentication (AUTH-01 / AUTH-02 / AUTH-03)

JWT-based authentication, backoffice landing, password reset, and user management at `services/api`. Passwords are bcrypt-hashed; protected routes require `Authorization: Bearer <token>`.

Plans: `IMPLEMENTATION_PLAN_auth_1.md`, `IMPLEMENTATION_PLAN_auth_2_3.md` under `memory-bank/references/authentication_backend_ai_plan/`.

### Environment variables

Copy `services/api/.example.env` to `services/api/.env` before starting the API (required):

```bash
SECRET_KEY=change-me-before-production
JWT_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3004,http://localhost:3005
EMAIL_API_KEY=
FRONTEND_URL=http://localhost:3004
# DATABASE_URL=postgresql://...  # Supabase pooler URI for inventory (see Inventory Management section)
```

Override `SECRET_KEY` in any non-local environment.

### Quick start

From `services/api/`:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Auth endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | No | Register; returns JWT (`201`) |
| `/api/v1/auth/login` | POST | No | Login; returns JWT (`200`) |
| `/api/v1/auth/me` | GET | Yes | Current user profile |
| `/api/v1/auth/forgot-password` | POST | No | Request reset link (generic response) |
| `/api/v1/auth/reset-password` | POST | No | Set new password with reset token |
| `/api/v1/users` | POST | No | Create user (no token returned) |
| `/api/v1/users` | GET | Yes | List all users |
| `/api/v1/users/{id}` | GET | Yes | Get user by id |
| `/api/v1/users/{id}` | PUT | Yes | Update own record only (`403` otherwise) |
| `/api/v1/users/{id}` | DELETE | Yes | Delete user (`204`) |

`/api/v1/suppliers` and `/api/v1/incidents` require **Bearer auth** (Step 10).

### Example flow

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"password123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"password123"}' | jq -r .access_token)

# Protected route
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

Use `/docs` → **Authorize** to paste the token for interactive testing.


## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alezanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._
