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

- `docker compose exec api uv run seed` — TinyDB suppliers (+ inventory when `DATABASE_URL` is set).
- Incident CSV seed (Supabase): `docker compose exec api uv run python /app/scripts/seed_incidents.py` when `DATABASE_URL` is configured.

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
- Seed (optional): `uv run seed`

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

Hub: http://localhost:3001 — routes include `/incident-analyzer`, `/supplier-directory`, `/inventory`, `/talent-tracker`, `/backoffice-functions`, `/incident-manager/*`, `/account/*`. Full route table: [uis/backoffice/README.md](./uis/backoffice/README.md).

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
| Supabase features | `DATABASE_URL` in `services/api/.env` for inventory and incident manager |

---

## Telemetry

Backoffice telemetry spans four phases: design docs, client capture, Supabase persistence, and a JWT-protected report API (**Milestone 6 pipeline scope** — dashboard UI is out of scope for these phases). Design reference: [`docs/telemetry/telemetry-plan.md`](./docs/telemetry/telemetry-plan.md) and [`docs/telemetry/event-schemas.json`](./docs/telemetry/event-schemas.json).

**Prerequisites for Phases 2–4:** API on port 8000, backoffice landing on port 3001, and `DATABASE_URL` set (Phases 3–4 persist to `telemetry_events`). In `uis/backoffice/landing/.env.local`, set `NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/api/v1/telemetry/events`.

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /api/v1/telemetry/events` | None | Ingest batched events |
| `GET /api/v1/telemetry/report` | Bearer JWT | KPI metrics (7-day default window) |

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
git checkout c6fba5b  # [W17D49] Telemetry Report
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

3. Confirm response shape: `period.from` / `period.to` and **four** metric arrays — `consumption_volume_per_day`, `waste_rate_per_day`, `insufficient_stock_failures_per_day`, `auth_failure_rate`.
4. Optional date window:

```bash
curl -s "http://localhost:8000/api/v1/telemetry/report?start_date=2026-07-01T00:00:00Z&end_date=2026-07-09T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

5. Without a token, expect **401** on `GET /api/v1/telemetry/report`. `POST /api/v1/telemetry/events` stays public.

**Note:** If KPI arrays are empty, the DB likely lacks `supply_consumption_created`, `supply_consumption_failed`, or login events in the selected window — list views and filters alone do not populate consumption metrics.

Further detail: [`memory-bank/references/telemetry_ai_plan/`](./memory-bank/references/telemetry_ai_plan/).

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
| 6 | Telemetry | Data pipeline, dashboards | **Partially complete** (pipeline: Phases 1–4 on `feature/telemetry`; dashboards not built) |
| 7 | RAG & Memory | Semantic knowledge base, search | Not started |
| 8 | Agents | Support, onboarding, training agents | Not started |
| 9 | Workflows | n8n automations | Not started |
| 10 | Real-time | Live dashboards, alerts, streaming | Not started |

**HealthCore mapping (M0–M6):** M1/M4 → `uis/website`; M2 → `apps/src` + `/backoffice-functions`; M3 → `/talent-tracker`; M5 → `services/api` + backoffice platform; **M6 (partial)** → telemetry pipeline on `feature/telemetry` (see [Telemetry](#telemetry) — no ops dashboard UI yet). Detail: [memory-bank/progress.md](./memory-bank/progress.md).

---

## Repository structure

```text
healthcore-monorepo/
├── README.md
├── CONTEXT.md                 # Business and stakeholder context
├── AGENTS.md                  # Agent workflow policy
├── .example.env               # Docker env template → copy to .env
├── docker-compose.yml
├── services/api/              # FastAPI backend
├── uis/
│   ├── website/               # Public portal (port 3000)
│   └── backoffice/
│       ├── landing/           # Backoffice hub (port 3001)
│       ├── inventory/
│       ├── incident-manager/
│       └── talent-tracker/
├── apps/                      # Legacy M1 portal, M2 utils, frozen M3 copy
├── packages/shared/           # Shared TypeScript and Python types/validation
├── memory-bank/               # Agent bootstrap and milestone records
├── docs/                      # Architecture and cross-cutting docs
├── scripts/
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
| [memory-bank/](./memory-bank/) | Project brief, tech context, progress, decisions, conventions |
| [AGENTS.md](./AGENTS.md) | Mandatory agent bootstrap and commit workflow |

Monorepo conventions (lockfiles, env naming, npm version checks): [memory-bank/conventions.md](./memory-bank/conventions.md).

---

## Contributors

Built as part of the [4Geeks Academy AI Engineering](https://4geeksacademy.com/en/career-programs/ai-engineering) Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo), [@alezanchezr](https://x.com/alesanchezr), and contributors. More templates: [4Geeks Academy GitHub](https://github.com/4geeksacademy).
