---
name: Docker Milestone 5 Plan
overview: "Containerize the HealthCore monorepo for local development: §0 dependency/env cleanup, then Docker Compose with a single UI container (website + backoffice landing) and a FastAPI API container. Acceptance: fresh clone + cp .env.example .env + docker compose up."
todos:
  - id: branch-setup
    content: Cut feature/docker_milestone5 from feature/milestone5
    status: completed
  - id: commit1-cleanup
    content: "§0 cleanup: pandas removal, dual lockfiles, README notes, check_ui_dep_versions.py, .nvmrc, engines, env-example consolidation"
    status: completed
  - id: commit2-docker
    content: "Docker infra + root .env.example + nav-apps.ts env edit (Dockerfiles, dockerignore, start.sh, compose, .env.example)"
    status: completed
  - id: commit3-docs
    content: "README Docker section, TESTING.md guardrail note, screenshot image + docker_screenshot.md, memory-bank progress/decisions"
    status: completed
  - id: verify-full
    content: Run full §7 verification checklist (cold build, endpoints, hot reload, service-name audit, secret hygiene)
    status: completed
isProject: false
---

# Docker Containerization — Implementation Plan

**Plan file:** [`memory-bank/references/docker_ai_plan/docker_implementation_plan.md`](docker_implementation_plan.md)

**Requirements source:** [`docker_specs.md`](docker_specs.md) (Ticket #infra-40)

**Branch:** `feature/docker_milestone5` (cut from `feature/milestone5`)

**Status:** Delivered on `feature/docker_milestone5`

---

## Executive summary

HealthCore's monorepo currently requires hand-configured Node/Python toolchains. This plan delivers a **development-only** Docker Compose stack:

| Service | Contents | Host ports |
|---------|----------|------------|
| `ui` | `uis/website` (port 3000) + `uis/backoffice/landing` (port 3001) in one container | 3000, 3001 |
| `api` | FastAPI + Uvicorn `--reload` | 8000 |

**Aliased backoffice modules** (inventory, incident-manager, talent-tracker, backoffice_functions, incident_analyzer, supplier_directory) compile inside the `ui` container via landing's webpack aliases — they get **no separate container or port**. Source is available through bind mounts (`./uis`, `./packages`, `./apps`).

**Acceptance test:** `git clone` → `cp .env.example .env` → fill placeholders → `docker compose up --build` → website, backoffice, and API docs respond on localhost.

Work lands in **three logical commits** on `feature/docker_milestone5`.

---

## Planning decisions (locked)

These resolve ambiguities between `docker_specs.md`, the current codebase, and stakeholder answers.

| Topic | Decision |
|-------|----------|
| Branch | `feature/docker_milestone5` cut from `feature/milestone5` |
| Commits | **3 total:** (1) §0 cleanup, (2) Docker infra + `.env.example` + `nav-apps.ts`, (3) docs + screenshot + memory-bank |
| Python deps in Docker | **uv only** — `uv sync --frozen` in Dockerfile; **no `requirements.txt`** |
| `pandas` in API | Remove direct declaration from `services/api/pyproject.toml` (§0); keep transitive via `healthcore-incidents-shared` |
| Lockfiles | Re-lock **both** `services/api/uv.lock` and root `uv.lock` after any backend dep change |
| UI `npm ci` | **Proactive** — install deps for website, landing, **and** all four aliased modules with own `package.json` |
| Aliased modules (`npm ci`) | `uis/backoffice/backoffice_functions/`, `uis/backoffice/talent-tracker/`, `uis/incident_analyzer/`, `uis/supplier_directory/` |
| Modules without `package.json` | `uis/backoffice/inventory/`, `uis/backoffice/incident-manager/` — bundled via landing aliases only; **no** separate `npm ci` |
| Legacy app | `apps/talent-pipeline-tracker/` — frozen; exclude from Docker, dep guardrail, and Node pinning |
| `package.json` scripts | **Do not edit** — Docker passes `--port 3000` / `--port 3001` via `start.sh` |
| Application source edits | **One exception only:** `uis/backoffice/landing/lib/nav-apps.ts` → `NEXT_PUBLIC_WEBSITE_URL` |
| `JWT_EXPIRE_MINUTES` | **15** in root `.env` / `.env.example` (overrides spec default of 60) |
| `DATABASE_URL` | Include in root env; `.env.example` uses **commented placeholder only** — full platform (inventory + incident-manager) needs Supabase |
| Secret handling | Real values live only in gitignored root `.env`; **never** commit or document actual secrets in plan, README, or `.env.example` |
| Root `.env` creation (implementer) | Merge keys from existing local env files (see table below) into gitignored root `.env` for local verification — do not copy those values into committed files |
| Per-app `.env.local` in Docker | **Not required** — Compose `env_file` injects process env; no code changes beyond `nav-apps.ts` |
| `API_URL_INTERNAL` | Add to root env / `.env.example` (commented placeholder); wire any server-side consumers if found during audit (none today) |
| `NEXT_PUBLIC_TRACKER_API_URL` | Include in root env (from `uis/backoffice/landing/.env`) |
| API healthcheck | **Skip** — `depends_on` ordering only |
| `WATCHPACK_POLLING` | **Commented** line in `.env.example` + README troubleshooting (enable only if hot reload fails on bind mounts) |
| Route verification | **All** hub routes: `/incident-analyzer`, `/supplier-directory`, `/inventory`, `/incident-manager`, `/talent-tracker`, `/backoffice-functions` |
| Screenshot | Image at `memory-bank/references/docker_ai_plan/docker_compose_ps.png`; pointer in `docker_screenshot.md` |
| Platform | **Linux-first** (Codespaces / Docker Engine on Linux); README warns about port conflicts with local non-Docker dev |
| Seed on startup | **Never** auto-run `uv run seed` or `scripts/seed_incidents.py` on container start |
| Incident CSV seed | Optional post-`up` step when `DATABASE_URL` configured: `docker compose exec api uv run python /app/scripts/seed_incidents.py` (or equivalent path) |

### Local env files to merge into root `.env` (implementer only — values stay gitignored)

| File | Keys to lift |
|------|----------------|
| `services/api/.env` | `SECRET_KEY`, `JWT_EXPIRE_MINUTES`, `EMAIL_API_KEY`, `DATABASE_URL`, etc. |
| `uis/backoffice/landing/.env` | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_TRACKER_API_URL` |
| `uis/backoffice/talent-tracker/.env.local` | `NEXT_PUBLIC_API_URL` (if not already set) |
| `uis/incident_analyzer/.env.local` | Skip stale `NEXT_PUBLIC_API_URL` unless needed |
| `uis/supplier_directory/.env.local` | Skip stale `NEXT_PUBLIC_API_URL` unless needed |

**Exclude:** `apps/talent-pipeline-tracker/.env.local` (frozen legacy).

**Docker overrides** applied on top when building root `.env`:

| Variable | Docker value |
|----------|--------------|
| `JWT_EXPIRE_MINUTES` | `15` |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` |
| `FRONTEND_URL` | `http://localhost:3001` |
| `WEBSITE_PORT` | `3000` |
| `BACKOFFICE_PORT` | `3001` |
| `NEXT_PUBLIC_WEBSITE_URL` | `http://localhost:3000` |
| `API_URL_INTERNAL` | `http://api:8000/api/v1` |
| `APP_ENV` | `development` |

---

## Commit 1 — §0 cleanup (standalone, before any Docker files)

Complete this commit **before** adding Dockerfiles or `docker-compose.yml`.

### Step 1.1 — Remove redundant `pandas` from API

1. Delete `"pandas>=2.0.0",` from `[project] dependencies` in `services/api/pyproject.toml` only.
2. Re-lock both lockfiles:
   ```bash
   cd services/api && uv lock
   cd ../.. && uv lock
   ```
3. Verify:
   ```bash
   cd services/api && uv run pytest
   cd ../.. && uv sync --group dev && uv run pytest
   ```
4. Confirm `pandas` still appears in both lockfiles (via `healthcore-incidents-shared`) and `uv run python -c "import pandas"` works from `services/api`.

### Step 1.2 — README notes (Backend / monorepo section)

Add short notes to root `README.md`:

- **Dual uv lockfiles on purpose:** `services/api/uv.lock` = canonical backend lock (package workflow + Docker build); root `uv.lock` = workspace pytest from repo root. Re-lock **both** after backend dependency changes.
- **Test deps declared twice:** `services/api` `[project.optional-dependencies] dev` and root `[dependency-groups] dev` — keep aligned.
- **Duplicate talent-tracker:** `uis/backoffice/talent-tracker/` is canonical (served via landing); `apps/talent-pipeline-tracker/` is frozen legacy — not part of Docker, do not modify.
- **Env naming:** root `.env.example` for Docker; per-app Next.js apps use `.env.local.example`. `services/api/.example.env` is local non-Docker only (ports 3004/3005).
- **Per-app npm lockfiles:** six active apps each keep `package-lock.json`; alignment enforced by `scripts/check_ui_dep_versions.py`; npm-workspaces conversion deferred post-#infra-40.
- **`packages/shared/package.json` quirk:** `name` is `@repo/shared-types` but imports use `@repo/shared` alias — never npm-install it; rename follow-up deferred.

### Step 1.3 — `scripts/check_ui_dep_versions.py`

Create stdlib-only Python 3 script (shebang/docstring style of `scripts/seed_incidents.py`):

- Load `package.json` from six active apps:
  - `uis/website`
  - `uis/backoffice/landing`
  - `uis/backoffice/backoffice_functions`
  - `uis/backoffice/talent-tracker`
  - `uis/incident_analyzer`
  - `uis/supplier_directory`
- Merge `dependencies` + `devDependencies`; for each package name in **more than one** app, compare version specs.
- Exit 0 with OK summary when aligned; exit 1 listing mismatches.
- Run and fix any drift (tree should pass today).

### Step 1.4 — Node version pinning

1. Create root `.nvmrc` containing `22`.
2. Add `"engines": { "node": ">=20.9" }` to `package.json` of the six active apps (not legacy `apps/talent-pipeline-tracker`).
3. Sync lockfiles metadata only:
   ```bash
   for dir in uis/website uis/backoffice/landing uis/backoffice/backoffice_functions \
              uis/backoffice/talent-tracker uis/incident_analyzer uis/supplier_directory; do
     (cd "$dir" && npm install --package-lock-only)
   done
   ```
4. **Accept metadata-only churn** in lockfiles; do not change dependency versions. If unexpected version bumps appear, investigate before committing.

### Step 1.5 — Env-example consolidation

1. **Delete** `uis/supplier_directory/.example.env` — keep only `.env.local.example`.
2. Add top comment to `services/api/.example.env`: local non-Docker workflow only; root `.env.example` is canonical for Docker. Do not change values.
3. Leave `apps/talent-pipeline-tracker/.example.env` untouched.
4. Do **not** copy stale `NEXT_PUBLIC_API_URL` from `uis/incident_analyzer/.env.local.example` or `uis/supplier_directory/.env.local.example` into root `.env.example`.

### Step 1.6 — Commit 1 message (example)

```
chore(infra): pre-Docker dependency and env convention cleanup (#infra-40 §0)

Remove redundant pandas from API deps, re-lock both uv lockfiles, add npm
dep-drift guardrail and Node pinning, consolidate env-example conventions.
```

---

## Commit 2 — Docker infrastructure + environment + sanctioned source edit

### Step 2.1 — Create gitignored root `.env` (before `docker-compose.yml`)

1. Verify `.env` is gitignored: `git check-ignore .env` must succeed.
2. Create root `.env` by merging local env files per **Planning decisions** table (implementer workstation only).
3. Apply Docker port overrides (`CORS_ORIGINS`, `FRONTEND_URL`, `JWT_EXPIRE_MINUTES=15`, etc.).
4. **Do not commit** root `.env`.

### Step 2.2 — Root `.env.example` (committed)

Create `/.env.example` with **commented placeholders only** — same keys as root `.env`, no real secrets:

```bash
# API (FastAPI)
# SECRET_KEY=your-dev-secret-here
JWT_EXPIRE_MINUTES=15
APP_ENV=development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
FRONTEND_URL=http://localhost:3001
# EMAIL_API_KEY=
# DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-1-us-west-2.pooler.supabase.com:6543/postgres

# UI — browser-facing (localhost is correct for host browser)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WEBSITE_URL=http://localhost:3000
NEXT_PUBLIC_TRACKER_API_URL=https://playground.4geeks.com/tracker/api/v1

# UI — container-to-container (service name, not localhost)
API_URL_INTERNAL=http://api:8000/api/v1

# UI — dev server ports (start.sh)
WEBSITE_PORT=3000
BACKOFFICE_PORT=3001

# Optional — enable if Next.js hot reload fails on Docker bind mounts (common on macOS)
# WATCHPACK_POLLING=true
```

Adjust comment style as needed; **never** embed real `SECRET_KEY`, `EMAIL_API_KEY`, or `DATABASE_URL` credentials.

### Step 2.3 — `/uis/Dockerfile`

```dockerfile
FROM node:22-alpine

WORKDIR /app

# Layer-cache friendly: copy lockfiles first, npm ci per app
# 1) website
COPY uis/website/package.json uis/website/package-lock.json ./uis/website/
RUN cd uis/website && npm ci

# 2) backoffice landing
COPY uis/backoffice/landing/package.json uis/backoffice/landing/package-lock.json ./uis/backoffice/landing/
RUN cd uis/backoffice/landing && npm ci

# 3–6) proactive aliased modules
COPY uis/backoffice/backoffice_functions/package.json uis/backoffice/backoffice_functions/package-lock.json ./uis/backoffice/backoffice_functions/
RUN cd uis/backoffice/backoffice_functions && npm ci

COPY uis/backoffice/talent-tracker/package.json uis/backoffice/talent-tracker/package-lock.json ./uis/backoffice/talent-tracker/
RUN cd uis/backoffice/talent-tracker && npm ci

COPY uis/incident_analyzer/package.json uis/incident_analyzer/package-lock.json ./uis/incident_analyzer/
RUN cd uis/incident_analyzer && npm ci

COPY uis/supplier_directory/package.json uis/supplier_directory/package-lock.json ./uis/supplier_directory/
RUN cd uis/supplier_directory && npm ci

COPY uis/start.sh ./uis/start.sh
RUN chmod +x ./uis/start.sh

EXPOSE 3000 3001
CMD ["./uis/start.sh"]
```

> Build context for `ui` service is `./uis` — COPY paths above are relative to `uis/` context. Adjust COPY paths if context is `./uis` (use `website/...` not `uis/website/...`). **Critical:** when `context: ./uis`, paths are `COPY website/package.json ...`, not `COPY uis/website/...`.

**Corrected paths for `context: ./uis`:**

```dockerfile
COPY website/package.json website/package-lock.json ./website/
RUN cd website && npm ci
# ... etc.
COPY start.sh ./start.sh
RUN chmod +x ./start.sh
WORKDIR /app
CMD ["./start.sh"]
```

### Step 2.4 — `/uis/start.sh`

```sh
#!/bin/sh
set -e

WEBSITE_PORT="${WEBSITE_PORT:-3000}"
BACKOFFICE_PORT="${BACKOFFICE_PORT:-3001}"

cd /app/website
npm run dev -- --port "$WEBSITE_PORT" --hostname 0.0.0.0 &

cd /app/backoffice/landing
npm run dev -- --port "$BACKOFFICE_PORT" --hostname 0.0.0.0 &

wait
```

Paths assume bind mount places repo at `/app/uis` — **align WORKDIR and paths with compose mount layout** (see Step 2.7). Spec uses `/app/uis/website`; mount `./uis:/app/uis` and run from `/app/uis`.

### Step 2.5 — `/uis/.dockerignore`

Minimum:

```
node_modules
**/node_modules
.next
**/.next
.env*
*.log
```

### Step 2.6 — `/services/Dockerfile`

Build context = **repo root** (`context: .`).

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Preserve ../../packages/shared/python relative layout
COPY services/api/pyproject.toml services/api/uv.lock ./services/api/
COPY packages/shared/python ./packages/shared/python/

WORKDIR /app/services/api
RUN uv sync --frozen --no-install-project

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

`UV_PROJECT_ENVIRONMENT=/opt/venv` keeps the venv outside bind-mounted `./services`, preventing mount shadowing.

### Step 2.7 — `/services/.dockerignore` and root `/.dockerignore`

**`services/.dockerignore`** (minimum):

```
__pycache__
*.pyc
.env*
tests/
*.log
```

**Root `.dockerignore`** (applied to api build context):

```
**/.git
**/node_modules
**/.next
**/__pycache__
**/*.pyc
.env*
**/tests/
**/*.log
```

### Step 2.8 — `/docker-compose.yml`

```yaml
services:
  api:
    build:
      context: .
      dockerfile: services/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./services:/app/services
      - ./packages:/app/packages
    env_file:
      - .env
    networks:
      - healthcore_net

  ui:
    build:
      context: ./uis
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
      - "3001:3001"
    volumes:
      - ./uis:/app/uis
      - ./packages:/app/packages
      - ./apps:/app/apps
      - /app/uis/website/node_modules
      - /app/uis/backoffice/landing/node_modules
      - /app/uis/backoffice/backoffice_functions/node_modules
      - /app/uis/backoffice/talent-tracker/node_modules
      - /app/uis/incident_analyzer/node_modules
      - /app/uis/supplier_directory/node_modules
      - /app/uis/website/.next
      - /app/uis/backoffice/landing/.next
    env_file:
      - .env
    depends_on:
      - api
    networks:
      - healthcore_net

networks:
  healthcore_net:
    name: healthcore_net
```

- No `version:` key.
- No literal secrets in YAML — all via `env_file: .env`.
- Align `start.sh` WORKDIR with mount: if `WORKDIR` in Dockerfile is `/app` and mount is `./uis:/app/uis`, `start.sh` lives at `/app/uis/start.sh` and CMD should be `["./uis/start.sh"]` with `WORKDIR /app`, **or** set `WORKDIR /app/uis` and CMD `["./start.sh"]`.

**Recommended layout:**

| Dockerfile `WORKDIR` | Compose mount | `start.sh` path | CMD |
|---------------------|---------------|-----------------|-----|
| `/app/uis` | `./uis:/app/uis` | `/app/uis/start.sh` | `["./start.sh"]` |

Image build copies deps into `/app/uis/website`, etc.; runtime mount overlays `./uis` but anonymous volumes preserve `node_modules`.

### Step 2.9 — Sanctioned source edit: `nav-apps.ts`

In `uis/backoffice/landing/lib/nav-apps.ts`, change the Public Website card:

```typescript
url: process.env.NEXT_PUBLIC_WEBSITE_URL ?? "http://localhost:3005",
```

Keep `3005` fallback so local non-Docker workflow is unchanged.

### Step 2.10 — Server-side API audit

```bash
rg -n "fetch\(|localhost:8000|API_URL" uis/ --glob '*.{ts,tsx}' --glob '!node_modules'
```

- Browser/client calls: keep `NEXT_PUBLIC_API_URL` (localhost from host browser).
- Any **server-side** fetch (RSC, route handlers, `getServerSideProps`): wire to `process.env.API_URL_INTERNAL`.
- As of planning, **no server-side HealthCore API consumers** — adding `API_URL_INTERNAL` to env is sufficient; no further code changes unless audit finds one.

### Step 2.11 — Commit 2 message (example)

```
feat(infra): add Docker Compose dev stack for UI and API (#infra-40)

Dockerfiles, compose, start.sh, root .env.example, and env-driven website
URL in backoffice nav. Proactive npm ci for aliased UI modules.
```

---

## Commit 3 — Documentation, guardrails, screenshot

### Step 3.1 — Root `README.md` — Docker development section

Add a **Docker Development** section covering:

**Prerequisites:** Docker Engine + Compose v2 (or Docker Desktop).

**First run:**

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY and DATABASE_URL (see commented placeholders)
docker compose up --build
```

**URLs:**

| URL | Service |
|-----|---------|
| http://localhost:3000 | Public website |
| http://localhost:3001 | Backoffice landing (hub + all tool routes) |
| http://localhost:8000/docs | API Swagger |

**Day-to-day:**

```bash
docker compose up          # foreground
docker compose up -d       # detached
docker compose down
docker compose logs -f ui
docker compose logs -f api
docker compose exec api uv run pytest
docker compose exec api uv run seed    # optional — TinyDB suppliers + inventory if DATABASE_URL set
```

**After dependency changes:** `docker compose up --build`; if `node_modules` stale → `docker compose down -v` then `up --build`.

**Post-first-up seeding (optional):**

- `docker compose exec api uv run seed` — suppliers (+ inventory when `DATABASE_URL` configured).
- Incident CSV seed (Supabase): run `scripts/seed_incidents.py` inside api container when `DATABASE_URL` is set.

**Port conflict warning:** Local non-Docker dev uses ports **3004/3005** (backoffice/website) and **8000** (API). Do **not** run `npm run dev` / `uv run uvicorn` on the same ports while Docker is up. Stop local servers or change Docker host port mappings.

**Troubleshooting:**

| Symptom | Fix |
|---------|-----|
| Port already in use | Stop conflicting local dev server |
| API exits immediately | `SECRET_KEY` / `JWT_EXPIRE_MINUTES` missing from `.env` |
| Backoffice webpack module errors | Rebuild: `docker compose up --build`; if persistent, `docker compose down -v` |
| Hot reload not working | Uncomment `WATCHPACK_POLLING=true` in `.env`, restart `ui` |
| Inventory / incident-manager 500 | Set `DATABASE_URL` in `.env`, restart `api`, run seed |

**Coexistence with local workflow:** `package.json` scripts unchanged; `services/api/.env` remains valid for non-Docker API dev; Docker uses root `.env` only.

### Step 3.2 — `TESTING.md`

Add under guardrails / pre-commit:

```bash
python3 scripts/check_ui_dep_versions.py
```

Run before committing any `package.json` change.

Add Docker test command:

```bash
docker compose exec api uv run pytest
```

### Step 3.3 — Screenshot deliverable

1. Run `docker compose up` until both services healthy.
2. Capture `docker compose ps` (or equivalent `up` output showing both containers running).
3. Save image: `memory-bank/references/docker_ai_plan/docker_compose_ps.png`
4. Create `memory-bank/references/docker_ai_plan/docker_screenshot.md`:

```markdown
# Docker Compose verification screenshot

![docker compose ps output](./docker_compose_ps.png)

Captured after successful `docker compose up` on branch `feature/docker_milestone5`.
Both `ui` and `api` services running.
```

### Step 3.4 — Memory-bank updates

After verification passes, update:

- `memory-bank/progress.md` — Docker milestone delivered under #infra-40
- `memory-bank/decisions.md` — locked decisions from this plan (uv in Docker, proactive npm ci, root env, JWT 15 min, etc.)

### Step 3.5 — Commit 3 message (example)

```
docs(infra): Docker workflow README, testing guardrails, verification screenshot

Document compose workflow, port-conflict warnings, and seed steps. Add npm
dep-drift note to TESTING.md and docker compose ps screenshot to memory-bank.
```

---

## Verification checklist (must pass before merge)

Run from repo root on `feature/docker_milestone5` with root `.env` populated.

### Build and startup

- [ ] `docker compose build --no-cache` succeeds for `ui` and `api`
- [ ] `docker compose up` → `docker compose ps` shows both containers `running`
- [ ] No crash loops in logs

### Endpoints (host)

```bash
curl -f http://localhost:3000
curl -f http://localhost:3001
curl -f http://localhost:8000/docs
```

### All hub routes (auth redirect 3xx or 200 — not 500)

```bash
for path in /incident-analyzer /supplier-directory /inventory /incident-manager /talent-tracker /backoffice-functions; do
  echo "=== $path ==="
  curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:3001$path"
done
```

### Hot reload

- Touch `uis/website/app/` → Next.js recompile in `ui` logs
- Touch `uis/backoffice/landing/app/` → recompile
- Touch `services/api/app/` → Uvicorn reload in `api` logs

### Service-name audit

```bash
docker compose exec ui wget -qO- http://api:8000/docs | head -c 200
```

```bash
rg -n "localhost" docker-compose.yml .env.example uis/ services/ \
  --glob '*.yml' --glob '*.ts' --glob '*.py' --glob '*.sh' \
  --glob '!node_modules' --glob '!.next'
```

Confirm every `localhost` hit is browser-facing (`NEXT_PUBLIC_*`, CORS, `FRONTEND_URL`, `nav-apps.ts` fallback). Zero container-to-container `localhost`.

Verify backoffice hub "Public Website" card links to `http://localhost:3000`.

### Secret hygiene

- [ ] `git check-ignore .env` succeeds
- [ ] `grep -iE 'secret|key|password' docker-compose.yml uis/Dockerfile services/Dockerfile uis/start.sh` shows variable **references** only

### Clean-slate rerun

```bash
docker compose down -v && docker compose up --build
```

### §0 regression

- [ ] `python3 scripts/check_ui_dep_versions.py` exits 0
- [ ] `uv run pytest` from repo root and `services/api` pass
- [ ] Local non-Docker: `cd uis/website && npm run dev` still defaults to port 3005; `cd uis/backoffice/landing && npm run dev` still uses 3004

---

## Files created or modified (summary)

| Path | Action |
|------|--------|
| `services/api/pyproject.toml` | §0: remove pandas line |
| `services/api/uv.lock`, `uv.lock` | §0: re-lock |
| `scripts/check_ui_dep_versions.py` | §0: create |
| `.nvmrc` | §0: create (`22`) |
| Six active apps' `package.json` | §0: add `engines` |
| Six apps' `package-lock.json` | §0: metadata sync |
| `uis/supplier_directory/.example.env` | §0: delete |
| `services/api/.example.env` | §0: add comment |
| `README.md` | §0 notes + Docker section |
| `TESTING.md` | dep guardrail + docker pytest |
| `uis/Dockerfile` | create |
| `uis/start.sh` | create |
| `uis/.dockerignore` | create |
| `services/Dockerfile` | create |
| `services/.dockerignore` | create |
| `.dockerignore` | create (root) |
| `docker-compose.yml` | create |
| `.env.example` | create (placeholders) |
| `.env` | create locally, gitignored |
| `uis/backoffice/landing/lib/nav-apps.ts` | env-driven website URL |
| `memory-bank/references/docker_ai_plan/docker_compose_ps.png` | screenshot |
| `memory-bank/references/docker_ai_plan/docker_screenshot.md` | create |
| `memory-bank/progress.md`, `memory-bank/decisions.md` | update after verify |

**Not modified:** `package.json` scripts, `apps/talent-pipeline-tracker/`, application source except `nav-apps.ts`.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Bind mount shadows `node_modules` | Anonymous volumes per app with proactive `npm ci` |
| Bind mount shadows Python venv | `UV_PROJECT_ENVIRONMENT=/opt/venv` outside mount |
| Backend build context can't see `packages/shared/python` | Repo root context for `api` service |
| Backoffice aliases need `packages/` and `apps/` | Bind mount both into `ui` container |
| macOS file watcher misses changes | Document `WATCHPACK_POLLING=true` |
| Developer runs local + Docker on same ports | README port-conflict warning |
| Supabase routes fail without `DATABASE_URL` | Document in README; `.env.example` commented placeholder |
| Accidental secret commit | `.env` gitignored; `.env.example` placeholders only; pre-commit grep check |

---

## Out of scope

- Production Docker images / multi-stage builds
- npm workspaces conversion (post-#infra-40)
- Deleting `apps/talent-pipeline-tracker/`
- Renaming `@repo/shared-types` → `@repo/shared`
- Auto-seed on container start
- API healthcheck in Compose
- Modifying `packages/shared/package.json`

---

## Agent execution order

1. Cut `feature/docker_milestone5` from `feature/milestone5`
2. Complete **Commit 1** (§0) — verify pytest + dep script
3. Complete **Commit 2** — build images, create root `.env` locally, verify `compose up`
4. Complete **Commit 3** — docs, screenshot, memory-bank
5. Run full verification checklist
6. Request developer acknowledgement before merge (per `AGENTS.md`)
