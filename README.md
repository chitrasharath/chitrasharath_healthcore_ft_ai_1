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

## Milestones (course roadmap)

| Milestone | Focus | Typical deliverables | Status |
| --------- | ----- | -------------------- | ------ |
| 0 | Prework | Environment setup, first prompts | **Implementation complete** |
| 1 | Web | Corporate website, forms, SEO | **Implementation complete** |
| 2 | Programming | Business logic, scoring, calculations | **Implementation complete** |
| 3 | AI-driven UI | AI-generated interfaces | **Implementation complete** |
| 4 | Next.js | Portals, loyalty app, operations UI | **Implementation complete** |
| 5 | Backend | Central API (locations, menus, sales, etc.) | **Implementation complete** |
| 6 | Telemetry | Data pipeline, dashboards | Not started |
| 7 | RAG & Memory | Semantic knowledge base, search | Not started |
| 8 | Agents | Support, onboarding, training agents | Not started |
| 9 | Workflows | n8n automations | Not started |
| 10 | Real-time | Live dashboards, alerts, streaming | Not started |

**HealthCore mapping (M0–M5):** M1/M4 → `uis/website`; M2 → `apps/src` + `/backoffice-functions`; M3 → `/talent-tracker`; M5 → `services/api` + backoffice platform. Detail: [memory-bank/progress.md](./memory-bank/progress.md).

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
| [memory-bank/](./memory-bank/) | Project brief, tech context, progress, decisions, conventions |
| [AGENTS.md](./AGENTS.md) | Mandatory agent bootstrap and commit workflow |

Monorepo conventions (lockfiles, env naming, npm version checks): [memory-bank/conventions.md](./memory-bank/conventions.md).

---

## Contributors

Built as part of the [4Geeks Academy AI Engineering](https://4geeksacademy.com/en/career-programs/ai-engineering) Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo), [@alezanchezr](https://x.com/alesanchezr), and contributors. More templates: [4Geeks Academy GitHub](https://github.com/4geeksacademy).
