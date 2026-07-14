# HealthCore Digital — Monorepo

HealthCore outpatient healthcare network — internal tools, public website, and FastAPI backend for HealthCore Digital milestone delivery.

Business context: [CONTEXT.md](./CONTEXT.md). Delivery status: [memory-bank/progress.md](./memory-bank/progress.md).

---

## Quick start (Docker)

```bash
cp .example.env .env
# Edit .env: set SECRET_KEY and, for full platform features, DATABASE_URL
docker compose up --build
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Public website |
| http://localhost:3001 | Backoffice landing (hub + all tool routes) |
| http://localhost:8000/docs | API Swagger |

---

## Docker development

Prerequisites: Docker Engine + Compose v2 (or Docker Desktop).

### First run

```bash
cp .example.env .env
# Edit .env: set SECRET_KEY and, for full platform features, DATABASE_URL
docker compose up --build
```

### Day-to-day

```bash
docker compose up
docker compose up -d
docker compose down
docker compose logs -f ui
docker compose logs -f api
docker compose exec api uv run seed

# Tests — one-off (stack not required)
docker compose --profile test run --rm test

# Tests — stack already running
docker compose exec api uv run pytest
```

After dependency changes (`package.json` / `pyproject.toml`): `docker compose up --build`. If `node_modules` look stale, run `docker compose down -v` first.

### Optional seeding (post-first-up)

Requires `DATABASE_URL` in `.env` for Supabase tables (inventory, reporting KPIs, incidents).

```bash
# Suppliers (TinyDB) + inventory + Reporting demo KPIs / pipeline_runs
docker compose exec api uv run seed

# Reporting demo only (re-runnable; truncates reporting_* + pipeline_runs, then reloads)
docker compose exec api uv run python -m app.domains.telemetry.seed_reporting

# Incident CSV seed
docker compose exec api uv run python /app/scripts/seed_incidents.py
```

See [Data pipeline (Build 2)](#data-pipeline-milestone-6--build-2) for what the reporting seed loads and how to run the ETL.

### Port conflicts

Local non-Docker dev and Docker both use ports **3000** (website), **3001** (backoffice), and **8000** (API). Do not run `npm run dev`, `docker compose up`, or `uv run uvicorn` on the same ports at the same time.

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

Docker uses the root `.env` only (from `cp .example.env .env`). The local non-Docker API workflow uses `services/api/.env`.

Plan: [memory-bank/references/docker_ai_plan/docker_implementation_plan.md](./memory-bank/references/docker_ai_plan/docker_implementation_plan.md).

---

## Manual development

Run without Docker when iterating on UI or API code. **Stop Docker first** if ports 3000, 3001, or 8000 are in use (`docker compose down`).

**Prerequisites:** Node.js per [`.nvmrc`](./.nvmrc); [uv](https://docs.astral.sh/uv/) for Python.

### 1. API (required for backoffice) — port 8000

```bash
cd services/api
cp .example.env .env
# Edit .env: SECRET_KEY, JWT_EXPIRE_MINUTES; optional DATABASE_URL for inventory/incident-manager
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: http://localhost:8000/docs
- Seed (optional; needs `DATABASE_URL` for inventory + reporting demo): `uv run seed`
  - Reporting demo only: `uv run python -m app.domains.telemetry.seed_reporting`
  - Details: [Data pipeline (Build 2)](#data-pipeline-milestone-6--build-2)

### 2. Backoffice landing (hub + all tools) — port 3001

Only the **landing** app needs a local env file. Feature modules (`/inventory`, `/incident-analyzer`, etc.) are compiled through landing and use its `NEXT_PUBLIC_*` variables.

```bash
cd uis/backoffice/landing
cp .example.env .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
# NEXT_PUBLIC_TRACKER_API_URL for /talent-tracker (see .example.env)
npm install
npm run dev
```

Hub: http://localhost:3001 — routes include `/incident-analyzer`, `/supplier-directory`, `/inventory`, `/talent-tracker`, `/backoffice-functions`, `/incident-manager/*`, `/reporting`, `/account/*`. Full route table: [uis/backoffice/README.md](./uis/backoffice/README.md).

### 3. Public website — port 3000

No env file required.

```bash
cd uis/website
npm install
npm run dev
```

http://localhost:3000 (no auth).

### 4. Run tests locally

```bash
# Backend — from repo root
uv sync --group dev
uv run pytest

# Frontend spot checks
cd uis/website && npm test
cd uis/backoffice/landing && npm run verify
```

See [TESTING.md](./TESTING.md) for coverage and pre-commit guardrails.

### Env notes

| Topic | Note |
|-------|------|
| vs Docker | Same ports — choose **one** workflow at a time |
| API env | Manual API: `services/api/.example.env` → `.env` |
| Backoffice env | **Landing only:** `uis/backoffice/landing/.example.env` → `.env.local` |
| Website env | None — `uis/website` has no `NEXT_PUBLIC_*` vars |
| Docker env | Root `cp .example.env .env` for `docker compose` only |
| Supabase features | `DATABASE_URL` in `services/api/.env` for inventory, incident manager, telemetry, and reporting pipeline |

---

## Telemetry

Backoffice telemetry spans four phases: design docs, client capture, Supabase persistence, and a JWT-protected report API. **Materialized KPI ETL + Reporting dashboard** are Milestone 6 Build 1–2 (see [Data pipeline (Build 2)](#data-pipeline-milestone-6--build-2)). Design reference: [`docs/telemetry/telemetry-plan.md`](./docs/telemetry/telemetry-plan.md) and [`docs/telemetry/event-schemas.json`](./docs/telemetry/event-schemas.json).

**Prerequisites for Phases 2–4:** API on port 8000, backoffice landing on port 3001, and `DATABASE_URL` set (Phases 3–4 persist to `telemetry_events`). In `uis/backoffice/landing/.env.local`, set `NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/api/v1/telemetry/events`.

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /api/v1/telemetry/events` | None | Ingest batched events |
| `GET /api/v1/telemetry/report` | Bearer JWT | KPI metrics from materialized `reporting_*` (Build 1+) |
| `GET /api/v1/telemetry/raw-report` | Bearer JWT | Live recompute from `telemetry_events` (debug / parity) |
| `GET /api/v1/telemetry/pipelines/runs/latest` | Bearer JWT | Latest ETL run metadata |
| `GET /api/v1/telemetry/pipelines/runs?limit=14` | Bearer JWT | Recent ETL runs (Reporting → Pipeline health) |
| `POST /api/v1/telemetry/pipelines/runs/trigger` | Bearer JWT | Async on-demand ETL run |

### Phase 1 — Design (docs only)

```bash
git checkout 52d141e  # [W16D46] Telemetry Design Plan
```

No running stack required.

1. Open [`docs/telemetry/telemetry-plan.md`](./docs/telemetry/telemetry-plan.md) and confirm §2 lists three reconciled KPIs plus instrumentation scope (inventory, auth, incident filters).
2. Confirm §6 catalogs **11** event types (10 instrumentable + 1 design-only) including v1.1 `supply_consumption_form_abandoned` and `incident_list_filter_applied`.
3. Validate the JSON schema:

```bash
python3 -m json.tool docs/telemetry/event-schemas.json > /dev/null
```

4. Spot-check that every `event_type` in the plan appears in `event-schemas.json` with matching property allowlists and `schemaVersion` **1.1.0**.

### Phase 2 — Frontend capture

```bash
git checkout 7ce0da5  # [W16D47] Telemetry Frontend Capture
```

Stub ingest only (no DB writes until Phase 3). Use DevTools → **Network** filtered by `telemetry/events`.

1. Log in at http://localhost:3001 — expect `user_login_succeeded` in a batched POST.
2. Open **Inventory** → products list and orders list — `supply_list_viewed`, `orders_list_viewed`.
3. Create an inbound delivery and a successful outbound consumption — `supply_delivery_created`, `supply_consumption_created`.
4. Submit an outbound order that fails for insufficient stock — `supply_consumption_failed`.
5. Start an outbound form, enter data, then navigate away — `supply_consumption_form_abandoned` (try supply-only and quantity-only cases).
6. Open **Incident Manager** list and change a filter — `incident_list_filter_applied`.
7. Confirm request bodies use `schemaVersion: "1.1.0"` and batched envelopes (`events` array).
8. Close the tab after activity — a `keepalive` fetch should flush the queue (not `sendBeacon`).

Failed login and session expiry use immediate (stream) flush: wrong password → `user_login_failed`; let JWT expire or force 401 → `session_expired`.

### Phase 3 — Storage

```bash
git checkout e429c2a  # [W16D48] Telemetry Storage
```

Requires `DATABASE_URL`. Phase 2 UI flows should return `{ "received", "stored", "rejected" }` instead of `{ "received" }` only.

1. Repeat the Phase 2 backoffice flows (login, lists, inbound/outbound, insufficient stock, form abandon ×2, incident filter).
2. In Supabase SQL editor (or any Postgres client on the same DB), run:

```sql
SELECT event_type, count(*) FROM telemetry_events GROUP BY event_type ORDER BY event_type;
```

Expect multiple event types with populated `tags` JSON (including v1.1 abandon booleans and filter dimensions).

3. **Mixed-batch partial acceptance** — one valid event, one malformed envelope, one allowlist violation:

```bash
curl -s -X POST http://localhost:8000/api/v1/telemetry/events \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "eventId": "evt-valid",
        "timestamp": "2026-07-08T12:00:00Z",
        "sessionId": "sess-001",
        "userId": "42",
        "event_type": "supply_list_viewed",
        "schemaVersion": "1.1.0",
        "requestId": "req-001",
        "service": "backoffice",
        "properties": { "item_count": 5 }
      },
      { "event_type": "broken", "properties": {} },
      {
        "eventId": "evt-extra",
        "timestamp": "2026-07-08T12:00:00Z",
        "sessionId": "sess-001",
        "userId": "42",
        "event_type": "supply_consumption_form_abandoned",
        "schemaVersion": "1.1.0",
        "requestId": "req-002",
        "service": "backoffice",
        "properties": {
          "clinic_id": 1,
          "had_supply_selected": true,
          "had_quantity": false,
          "supply_id": 99,
          "abandon_trigger": "navigation"
        }
      }
    ]
  }' | jq .
```

Expect `{ "received": 3, "stored": 1, "rejected": 2 }` — only `supply_list_viewed` is persisted (`supply_id` is not allowlisted on abandon events).

4. Optional index check: `uv run python scripts/verify_telemetry_indexes.py` (from repo root, with `DATABASE_URL` set).

### Phase 4 — Report

```bash
git checkout feature/telemetry  # [W17D49] Telemetry Report — KPI 3 rejection_rate + auth counts (HEAD)
```

Seed **KPI-relevant** events via backoffice (at minimum: successful outbound consumptions, expiry-waste outbound, insufficient-stock failures, and login success/failure). v1.1 events (abandon, filter) should appear in the DB but **not** change report metric counts.

1. Obtain a JWT:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"password123"}' | jq -r .access_token)
```

(Use a registered user from seed or register via `/api/v1/auth/register`.)

2. Request the default 7-day report:

```bash
curl -s "http://localhost:8000/api/v1/telemetry/report" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

3. Confirm response shape: `period.from` / `period.to` and **four** metric arrays — `consumption_volume_per_day` (count/day/clinic), `waste_rate_per_day` (`waste_rate` + `total`), `insufficient_stock_failures_per_day` (`count`, `attempts`, `rejection_rate` per supply/clinic), `auth_failure_rate` (`failed`, `succeeded`, `failure_rate`).
4. Optional date window:

```bash
curl -s "http://localhost:8000/api/v1/telemetry/report?start_date=2026-07-01T00:00:00Z&end_date=2026-07-09T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

5. Without a token, expect **401** on `GET /api/v1/telemetry/report`. `POST /api/v1/telemetry/events` stays public.

**Note:** If KPI arrays are empty, the DB likely lacks `supply_consumption_created`, `supply_consumption_failed`, or login events in the selected window — list views and filters alone do not populate consumption metrics.

Further detail: [`memory-bank/references/telemetry_ai_plan/`](./memory-bank/references/telemetry_ai_plan/).

---

## Data pipeline (Milestone 6 — Build 2)

Prefect ETL materializes clinic / jurisdiction KPIs from `telemetry_events` into `reporting_*` tables. Build 2 adds **subflows**, **unit tests**, and the authenticated **Reporting** dashboard at `/reporting`.

Design (authoritative): [`docs/data_pipelines/pipeline-design.md`](./docs/data_pipelines/pipeline-design.md). Code layout: [`data/pipelines/README.md`](./data/pipelines/README.md).

### What Build 2 delivers

| Area | Attributes (as implemented) |
|------|-----------------------------|
| **Layout** | `data/pipelines/{extract,transform,load}/` + orchestrator `pipeline.py` |
| **Main flow** | `telemetry_etl_flow` coordinates ≥3 **subflows** (`extract-telemetry-events`, `transform-kpi-aggregates`, `load-reporting-tables`; optional `export-snapshot`) |
| **Also** | `backfill_flow(start, end)` — same tasks with an explicit event-time window |
| **Extract** | Watermark on `timestamp`; KPI event types only; `retries=3` + backoff + transient-only `retry_condition_fn`; PHI / null-grain quarantine before load |
| **Transform** | Reuses `build_metrics` in `analysis.py`; Prefect `cache_key_fn` + 1h `cache_expiration` on the window |
| **Load** | Transactional upsert into four grains; watermark advances only after success; optional JSON snapshot with `return_state=True` (`partial` if snapshot fails) |
| **Config** | `REPROCESS_WINDOW_DAYS=2`, `LOOKBACK_DAYS=7`, `PIPELINE_VERSION=1.0.0` (`data/pipelines/config.py`) |
| **Run log** | `pipeline_runs`: `run_id`, times, watermarks, `rows_extracted` / `rows_loaded` / `rows_quarantined`, `status`, `error_summary`, `pipeline_version`, `checkpoint` |
| **Statuses** | `running` → `success` \| `partial` \| `failed` \| `quarantined` |
| **Tests** | `tests/pipelines/test_pipeline.py` — transform helpers + KPI value assertion; `uv run pytest tests/pipelines/test_pipeline.py` |
| **Dashboard** | `uis/backoffice/reporting/` → http://localhost:3001/reporting (JWT). Tabs: Summary, Consumption, Waste, Stock, Auth, Pipeline health |

### KPI grains (materialized tables)

| Table | Grain (unique key) | Value columns |
|-------|--------------------|---------------|
| `reporting_consumption_volume_daily` | `(report_date, clinic_id, jurisdiction)` | `count` |
| `reporting_waste_rate_daily` | `(report_date, jurisdiction)` | `waste_rate`, `total` |
| `reporting_stock_failures_daily` | `(report_date, clinic_id, jurisdiction, supply_id)` | `count`, `attempts`, `rejection_rate` |
| `reporting_auth_failure_daily` | `(report_date)` | `failed`, `succeeded`, `failure_rate` |

Dashboard filters: **waste** is jurisdiction-level (no clinic grain); **supply** applies on the Stock tab only.

### Run the ETL (CLI)

Requires `DATABASE_URL` (process env or `services/api/.env`). From **repository root**:

```bash
uv run python data/pipelines/pipeline.py
```

Fail-fast if `DATABASE_URL` is missing (exit `1`, no false success). Intended cron: `0 2 * * *` with cwd = repo root.

On-demand from the UI: Reporting → **Pipeline health** → **Run pipeline** (`POST /api/v1/telemetry/pipelines/runs/trigger`).

### Seed the database

`DATABASE_URL` must point at the Supabase project used for inventory / telemetry (same DB as `milestone5_inventory`).

#### Full platform seed (recommended once)

Seeds TinyDB **suppliers**, Supabase **inventory** (if empty), and the **Reporting demo** (`reporting_*` + `pipeline_runs`).

```bash
# Manual API workflow
cd services/api
uv sync --extra dev
uv run seed

# Docker (stack up)
docker compose exec api uv run seed
```

#### Reporting demo only (dashboard charts / health)

Idempotent demo loader: truncates `reporting_*` and `pipeline_runs`, then inserts ~12 months of KPI grains (clinics 1–9, US/UK) plus ~14 mixed-status pipeline runs (latest = full success).

```bash
# Manual
cd services/api
uv run python -m app.domains.telemetry.seed_reporting

# Docker
docker compose exec api uv run python -m app.domains.telemetry.seed_reporting
```

Then open http://localhost:3001/reporting (logged in). Pipeline health shows the latest run and a recent-runs table.

#### Other seeds

| Seed | Command | Notes |
|------|---------|-------|
| Incidents CSV | `uv run python scripts/seed_incidents.py` (repo root) or `docker compose exec api uv run python /app/scripts/seed_incidents.py` | Needs `DATABASE_URL` |
| Live KPI path | Capture real telemetry in backoffice, then `uv run python data/pipelines/pipeline.py` | Materializes from `telemetry_events` instead of demo grains |

Plans: [`memory-bank/references/data_pipelines_ai_plan/`](./memory-bank/references/data_pipelines_ai_plan/).

---

## Milestones (course roadmap)

| Milestone | Focus | Typical deliverables | Status |
| --------- | ----- | -------------------- | ------ |
| 0 | Prework | Environment setup, first prompts | **Implementation complete** |
| 1 | Web | Corporate website, forms, SEO | **Implementation complete** |
| 2 | Programming | Business logic, scoring, calculations | **Implementation complete** |
| 3 | AI-driven UI | AI-generated interfaces | **Implementation complete** |
| 4 | Next.js | Portals, loyalty app, operations UI | **Implementation complete** |
| 5 | Backend | Central API (locations, menus, sales, etc.) | **Implementation complete** |
| 6 | Telemetry | Data pipeline, dashboards | **In progress** (Build 1–2 on `feature/data_pipeline`: ETL + `/reporting`) |
| 7 | RAG & Memory | Semantic knowledge base, search | Not started |
| 8 | Agents | Support, onboarding, training agents | Not started |
| 9 | Workflows | n8n automations | Not started |
| 10 | Real-time | Live dashboards, alerts, streaming | Not started |

**HealthCore mapping (M0–M6):** M1/M4 → `uis/website`; M2 → `apps/src` + `/backoffice-functions`; M3 → `/talent-tracker`; M5 → `services/api` + backoffice platform; **M6** → telemetry + Prefect ETL (`data/pipelines/`) + Reporting UI (`/reporting`) — see [Telemetry](#telemetry) and [Data pipeline (Build 2)](#data-pipeline-milestone-6--build-2). Detail: [memory-bank/progress.md](./memory-bank/progress.md).

---

## Repository structure

```text
healthcore-monorepo/
├── README.md
├── CONTEXT.md                 # Business and stakeholder context
├── AGENTS.md                  # Agent workflow policy
├── .example.env               # Docker env template → copy to .env
├── docker-compose.yml
├── data/pipelines/            # Prefect KPI ETL (Milestone 6)
├── services/api/              # FastAPI backend
├── uis/
│   ├── website/               # Public portal (port 3000)
│   └── backoffice/
│       ├── landing/           # Backoffice hub (port 3001)
│       ├── inventory/
│       ├── incident-manager/
│       ├── reporting/         # KPI dashboard → /reporting
│       └── talent-tracker/
├── apps/                      # Legacy M1 portal, M2 utils, frozen M3 copy
├── packages/shared/           # Shared TypeScript and Python types/validation
├── memory-bank/               # Agent bootstrap and milestone records
├── docs/                      # Architecture, telemetry, data pipeline design
├── scripts/
├── tests/pipelines/           # ETL unit tests
└── TESTING.md
```

---

## Documentation map

| Document | Contents |
| -------- | -------- |
| [services/api/README.md](./services/api/README.md) | API setup, auth, endpoints, seed, pytest |
| [uis/backoffice/README.md](./uis/backoffice/README.md) | Backoffice routes, modules, inventory/incident-manager setup |
| [uis/incident_analyzer/README.md](./uis/incident_analyzer/README.md) | Incident CSV CLI and analysis module |
| [TESTING.md](./TESTING.md) | pytest, Jest, pre-commit guardrails, Docker test commands |
| [docs/telemetry/telemetry-plan.md](./docs/telemetry/telemetry-plan.md) | Telemetry design, KPIs, event catalog |
| [docs/data_pipelines/pipeline-design.md](./docs/data_pipelines/pipeline-design.md) | KPI ETL design, run command, Reporting UI (§12.1) |
| [data/pipelines/README.md](./data/pipelines/README.md) | Pipeline package layout and CLI entry |
| [memory-bank/](./memory-bank/) | Project brief, tech context, progress, decisions, conventions |
| [AGENTS.md](./AGENTS.md) | Mandatory agent bootstrap and commit workflow |

Monorepo conventions (lockfiles, env naming, npm version checks): [memory-bank/conventions.md](./memory-bank/conventions.md).

---

## Contributors

Built as part of the [4Geeks Academy AI Engineering](https://4geeksacademy.com/en/career-programs/ai-engineering) Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo), [@alezanchezr](https://x.com/alesanchezr), and contributors. More templates: [4Geeks Academy GitHub](https://github.com/4geeksacademy).
