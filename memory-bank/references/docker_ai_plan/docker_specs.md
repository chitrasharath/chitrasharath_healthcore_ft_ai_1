# Spec: Company Monorepo Containerization (Ticket #infra-40)

> **Audience:** autonomous coding agent working in this repository.
> **Branch:** work on the current branch of this fork (`feature/milestone5` or a branch cut from it) — this is the team's fork of `4GeeksAcademy/ai-engineering-company-project-monorepo`. Do **not** create a new repository.
> **Deliverable:** a fully dockerized development environment. Acceptance test: a fresh clone + `cp .env.example .env` + `docker compose up` from the repo root runs the whole platform with zero additional manual steps.

---

## 0. Cleanup Prior to Starting the Project

Do this small dependency cleanup first, as a standalone commit, before any Docker work:

**Remove the redundant `pandas` dependency from `services/api/pyproject.toml`.** Nothing under `services/api/app/` imports pandas — the only consumer is `packages/shared/python/healthcore_incidents/csv_validation.py`, and that package already declares `pandas>=2.0.0` in its own `pyproject.toml`. The API keeps pandas transitively through its `healthcore-incidents-shared` dependency; the direct declaration is duplication that can drift.

Steps:

1. Delete the `"pandas>=2.0.0",` line from the `[project] dependencies` list in `services/api/pyproject.toml`. Touch nothing else in that file.
2. Re-lock **both** lockfiles — this repo intentionally keeps two (`services/api/uv.lock` is the canonical backend lock; the root `uv.lock` serves the workspace-level `uv run pytest` documented in `TESTING.md`):
   - `cd services/api && uv lock`
   - `uv lock` from the repo root. Note: the root lock is currently stale (it predates the `healthcore-incidents-shared` editable dependency), so expect a larger diff there — that's the fix, not a problem.
3. Verify: `uv run pytest` passes from `services/api`, and `uv sync --group dev && uv run pytest` passes from the repo root. Confirm `pandas` still appears in both lockfiles (pulled in by `healthcore-incidents-shared`) and `import pandas` still works inside the API environment.
4. Add a short note to `README.md` (in the Backend/FastAPI section) documenting the **intentional uv redundancy** in this repo, so future contributors don't "fix" it:
   - There are **two lockfiles on purpose**: `services/api/uv.lock` is the canonical backend lock (used by the package-only workflow and the Docker build); the root `uv.lock` exists solely so `uv run pytest` works from the repository root (workspace defined in the root `pyproject.toml`).
   - Test dependencies are declared **twice** for the same reason: in `services/api`'s `[project.optional-dependencies] dev` and in the root `[dependency-groups] dev` — keep them aligned.
   - After any backend dependency change, **re-lock both**: `uv lock` inside `services/api` *and* `uv lock` at the repo root.
5. Add a short note to `README.md` about the **duplicate talent-tracker apps**, which are being kept intentionally for now:
   - `uis/backoffice/talent-tracker/` is the **active, canonical** version (served through the backoffice landing app).
   - `apps/talent-pipeline-tracker/` is the **legacy pre-relocation copy** — frozen, unmaintained, and diverged from the canonical one. It is not part of the Docker setup and must not receive changes; any fixes go to the backoffice copy only.
   Do **not** delete `apps/talent-pipeline-tracker/` as part of this ticket.
6. Add an **npm dependency drift guardrail** (the six active apps each keep their own `package-lock.json` for now; a full npm-workspaces conversion is deliberately deferred until after this ticket lands):
   - Create `scripts/check_ui_dep_versions.py` — stdlib-only Python 3 (follow the shebang/docstring style of `scripts/seed_incidents.py`, no third-party imports). It loads `package.json` from the six active apps (`uis/website`, `uis/backoffice/landing`, `uis/backoffice/backoffice_functions`, `uis/backoffice/talent-tracker`, `uis/incident_analyzer`, `uis/supplier_directory` — **excluding** the frozen `apps/talent-pipeline-tracker`), merges `dependencies` + `devDependencies`, and for every package name present in more than one app compares the version specs. Exit 0 with a short OK summary when all match; exit 1 listing each mismatched package with the per-app specs. Packages that appear in only one app are not an error.
   - Run it and make it pass against the current tree (versions are aligned today; the check exists to keep them that way).
   - Document it in `TESTING.md` (run `python3 scripts/check_ui_dep_versions.py` before committing any `package.json` change) and add a line to the README note from step 5's area: per-app lockfiles are the intentional convention for now, version alignment is enforced by this script, and the planned follow-up (post #infra-40) is an npm-workspaces conversion rooted at `uis/` with the legacy app excluded.
7. Pin the Node version for the non-Docker workflow:
   - Create `.nvmrc` at the repo root containing `22`.
   - Add `"engines": { "node": ">=20.9" }` to the `package.json` of the six active apps (same list as step 6; do **not** touch the frozen `apps/talent-pipeline-tracker`). Next.js 16 requires Node ≥ 20.9, and the Docker UI image is `node:22-alpine`, so this codifies what already has to be true. Engines is warning-only by default — do **not** add `engine-strict` anywhere.
   - Sync each touched lockfile with `npm install --package-lock-only` (metadata-only; verify the diff contains no dependency version changes).
8. Consolidate the env-example file conventions (the root `.env.example` created later in §5.7 becomes the canonical env documentation; this step just cleans up the per-app files feeding into it):
   - Delete `uis/supplier_directory/.example.env` — the app ships two example files in two conventions; keep only its `.env.local.example` (matches Next.js's `.env.local` loading).
   - Note: the `NEXT_PUBLIC_API_URL` entries in `uis/incident_analyzer/.env.local.example` and `uis/supplier_directory/.env.local.example` are **stale** — no code in either app reads that variable (verified: zero references outside the example files). Do not copy them into the root `.env.example` on their account; the root file defines `NEXT_PUBLIC_API_URL` for the backoffice landing app only (§6).
   - Add a top comment to `services/api/.example.env`: it serves the **local non-Docker** workflow only (its 3004/3005 ports are correct there); the root `.env.example` is canonical for the Docker workflow. Do not change its values.
   - Leave `apps/talent-pipeline-tracker/.example.env` untouched (frozen legacy, step 5).
   - Naming going forward: root uses `.env.example`; per-app Next.js examples use `.env.local.example`. Note this convention in the README alongside the step 5/6 notes. (Compose-injected environment variables take precedence over the backend's own `services/api/.env` in pydantic-settings, so the local and Docker configurations coexist without conflict.)
9. Add a short README note about `packages/shared/package.json` (known quirk, deliberately not fixed in this ticket): its `name` is `@repo/shared-types`, but consumers import it via the `@repo/shared` **alias** defined in `tsconfig.json` paths and the `next.config.ts` webpack aliases. The package is never npm-installed — no lockfile, no dependencies, raw `.ts` exports — so don't try to `npm install` it, and don't trust the `name` field. Follow-up (whenever convenient): rename it to `@repo/shared`; the literal name `@repo/shared-types` is referenced nowhere else in the repo, so the rename is a one-word change. Do not modify the file itself as part of this ticket.

---

## 1. Project Overview

**HealthCore** is an outpatient healthcare company (6 clinics across Texas, Florida, and Georgia). Its platform lives in this monorepo:

- `uis/website/` — public-facing Next.js site.
- `uis/backoffice/` — internal admin panel. This is a **multi-app Next.js monorepo**: `landing/` is the host app that serves all routes; sibling directories (`backoffice_functions/`, `talent-tracker/`, `inventory/`, `incident-manager/`, `shared/`) are feature modules aliased into `landing` via `landing/next.config.ts`.
- `services/api/` — FastAPI backend (auth, inventory, incidents, suppliers domains) with a TinyDB file store and optional Postgres/Supabase via `DATABASE_URL`.
- `packages/shared/` — cross-cutting shared code: TypeScript (`lib/`, `types/`) consumed by the UIs **and** a Python package (`python/`) installed as an editable dependency by the backend.
- `uis/incident_analyzer/` and `uis/supplier_directory/` — **backoffice tools served through the landing app**: `landing/next.config.ts` aliases them (`@backoffice/incident-analyzer`, `@backoffice/supplier-directory`) and landing's protected routes `/incident-analyzer` and `/supplier-directory` import their components directly. They get **no container or port of their own** (their standalone dev servers on 3002/3003 are a local-only convenience), but their source **must** be available inside the UI container — the `./uis` bind mount covers this — and they must compile as part of the backoffice app.

**The problem:** the platform only runs on machines that have been hand-configured. Onboarding a new developer takes hours due to Node/Python version conflicts and undocumented setup steps.

**The goal (Ticket #infra-40):** define the development environment as code. Dockerize the monorepo for **development** (not production): a single UI container running both Next.js apps with hot reloading, a separate FastAPI container with `--reload`, orchestrated by Docker Compose, configured entirely through environment variables, communicating over an explicitly named Docker network **by service name — never `localhost`** for container-to-container traffic.

---

## 2. Tech Stack

| Layer | Technology | Version / Image | Notes |
|-------|-----------|-----------------|-------|
| UI framework | Next.js (App Router) | 16.2.6 | Backoffice dev uses `--webpack` (not Turbopack) |
| UI language | TypeScript + React 19 | TS ^5, React 19.2.4 | |
| UI base image | `node:22-alpine` | Node 22 LTS | Next.js 16 requires Node ≥ 20.9; brief requires an official Alpine Node image |
| Backend framework | FastAPI + Uvicorn | fastapi ≥ 0.115, uvicorn[standard] ≥ 0.32 | |
| Backend language | Python | ≥ 3.12 (`requires-python` in `services/api/pyproject.toml`) | |
| Backend base image | `python:3.12-slim` | | `psycopg2-binary` and `pandas` install from wheels; no build toolchain needed |
| Python package manager | **uv** | latest | `services/api/` has `pyproject.toml` + `uv.lock`. **There is no `requirements.txt` and you must not create one** — install with `uv sync` in the Dockerfile (decision confirmed with the tech lead; supersedes the ticket's mention of requirements.txt) |
| Node package manager | npm | bundled with Node 22 | Each app has its own `package.json` + `package-lock.json`; no root workspace. Use `npm ci` |
| Database | TinyDB (JSON file at `services/api/db.json`) | tinydb ≥ 4.8 | No database container required. Optional Postgres via `DATABASE_URL` (leave empty in dev) |
| Orchestration | Docker Compose v2 | `docker-compose.yml` at repo root | |

### Port map (inside containers = on host)

| Service | App | Port |
|---------|-----|------|
| `ui` | website (`next dev --port 3000`) | 3000 |
| `ui` | backoffice landing (`next dev --webpack --port 3001`) | 3001 |
| `api` | FastAPI/Uvicorn | 8000 |

> ⚠️ The apps' `package.json` scripts currently use ports **3005** (website) and **3004** (backoffice). **Do not edit the `package.json` files** — the local non-Docker workflow must keep working. Instead, `start.sh` passes `--port 3000` / `--port 3001` explicitly, and the backend's CORS/frontend-URL settings are overridden through `.env` (see §6).

---

## 3. Business Constraints

1. **Zero-step onboarding.** A new developer must get the full platform with `docker compose up` from the repo root. No global installs, no manual config beyond copying `.env.example` to `.env`.
2. **Secrets never touch versioned files.** No secret, API key, or password may appear in `docker-compose.yml`, any `Dockerfile`, `start.sh`, or `.env.example`. Real values live only in `.env`, which is already covered by `.gitignore` (`.env` and `.env.*` entries — verify, don't just trust this spec). A committed secret is a compromised secret.
3. **Development environment, not production.** Both containers run dev servers with hot reloading (Next.js dev mode; Uvicorn `--reload`). No production builds, no multi-stage optimization required.
4. **Service-name networking.** Any URL one *container* uses to reach another *container* must use the Docker Compose service name as host (e.g. `http://api:8000`). `localhost` is only acceptable in URLs consumed by the developer's **browser** (which runs on the host), such as `NEXT_PUBLIC_API_URL` and CORS origins. Audit every inter-service URL before sign-off (see §7, step 5).
5. **Single UI container.** Website and backoffice both run in one container from one Dockerfile; the API runs in its own container. Exactly two services in Compose.
6. **Don't break the existing local workflow.** Developers who run `npm run dev` / `uv run` directly must be unaffected: no changes to `package.json` scripts, app source code, or `pyproject.toml` beyond what §0 prescribes. Config changes go through environment variables only. **One sanctioned source edit:** the hardcoded website URL in `uis/backoffice/landing/lib/nav-apps.ts` becomes env-driven with its current value as the fallback (see `NEXT_PUBLIC_WEBSITE_URL` in §6) — local behavior is identical.
7. **Everything as code, in this fork.** All infrastructure files are committed to this repository (except `.env`).

---

## 4. Dependencies

### 4.1 Critical cross-directory dependencies (read this before writing any Dockerfile)

These are the traps in this repo. Both build contexts and runtime mounts must account for them:

1. **Backend → `packages/shared/python`.** `services/api/pyproject.toml` declares:
   ```toml
   [tool.uv.sources]
   healthcore-incidents-shared = { path = "../../packages/shared/python", editable = true }
   ```
   A build context of `./services` **cannot see this path**, so the backend service in Compose must use the **repo root as build context** with `dockerfile: services/Dockerfile`. The Dockerfile still lives in `/services/` as the ticket requires.
2. **Backoffice → repo-root paths.** `uis/backoffice/landing/next.config.ts` and `tsconfig.json` alias `@repo/shared/*` → `packages/shared/*` and `@healthcore/src/*` → `apps/src/*` (both relative to the **repo root**, outside `/uis`). The UI container must bind-mount `./packages` and `./apps` at the correct locations relative to the mounted `./uis` so these aliases resolve at runtime (see §5.3).
3. **Backoffice module layout.** Only `uis/backoffice/landing/` runs a dev server; the other backoffice tools are compiled as source by landing's webpack via aliases — the siblings inside `uis/backoffice/` (`backoffice_functions/`, `talent-tracker/`, `incident-manager/`, `inventory/`) **and** the two tools that live one level up: `uis/incident_analyzer/` and `uis/supplier_directory/`. Install npm dependencies for `uis/website/` and `uis/backoffice/landing/` (separately, per the ticket). If the backoffice fails at runtime with unresolved modules imported by any aliased module (`backoffice_functions/`, `talent-tracker/`, `incident_analyzer/`, `supplier_directory/` each have their own `package.json`), additionally run `npm ci` in the failing module's directory and add a matching anonymous volume for its `node_modules`.

### 4.2 Service dependencies

- `ui` `depends_on: api` (start ordering only — the UIs tolerate the API briefly being unavailable; no healthcheck required, though adding one to `api` is a welcome bonus).
- Both services join one explicitly named network (e.g. `healthcore_net`).

### 4.3 Runtime data

- TinyDB persists to `services/api/db.json`. Because `./services` is bind-mounted, data written inside the container lands in the developer's working tree — this is intended for dev. No named volume needed.
- `services/api/app/seed.py` exists (script `seed`); do **not** run it automatically on container start.

### 4.4 Tooling prerequisites (document in the spec output, not installed by you)

- Docker Desktop, or Docker Engine + Docker Compose CLI v2.

---

## 5. Deliverables

Create exactly these files. Do not modify application source code.

### 5.1 `/uis/Dockerfile`

- Base: `node:22-alpine`.
- Install dependencies **separately** for `website` and `backoffice/landing`: copy each app's `package.json` + `package-lock.json` first, run `npm ci` per app (layer-cache friendly), e.g. into `/app/uis/website` and `/app/uis/backoffice/landing`.
- Copy `start.sh` and make it executable.
- `EXPOSE 3000 3001`.
- Default `CMD` invokes `start.sh`.

### 5.2 `/uis/start.sh`

- POSIX-sh compatible (Alpine has no bash by default; use `#!/bin/sh` or install bash explicitly).
- Starts **both** dev servers:
  - website: `npm run dev -- --port ${WEBSITE_PORT:-3000} --hostname 0.0.0.0` from `uis/website`
  - backoffice: `npm run dev -- --port ${BACKOFFICE_PORT:-3001} --hostname 0.0.0.0` from `uis/backoffice/landing`
  (`--hostname 0.0.0.0` is required — Next dev binds to localhost by default, which is unreachable through Docker port mapping.)
- Run one in the background, then `wait`, so the container stays alive and both processes' logs stream to compose output.

### 5.3 `/uis/.dockerignore`

At minimum: `node_modules`, `.next`, `.env*`, `*.log`. Add `**/node_modules` and `**/.next` so nested app directories are covered.

### 5.4 `/services/Dockerfile`

- Base: `python:3.12-slim`.
- Install uv (e.g. `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/`).
- Set `UV_PROJECT_ENVIRONMENT=/opt/venv` (or equivalent) so the virtualenv lives **outside** the paths that get bind-mounted at runtime — otherwise the mount shadows the installed packages.
- Copy `services/api/pyproject.toml`, `services/api/uv.lock`, and `packages/shared/python/` into the image at paths that preserve the `../../packages/shared/python` relative layout (e.g. `/app/services/api/` and `/app/packages/shared/python/`). Remember: build context is the **repo root** (see §4.1), so COPY paths are relative to the repo root.
- `WORKDIR /app/services/api`, then `uv sync --frozen --no-install-project` (installs all deps including the editable shared package; the app itself runs from the bind-mounted source).
- `EXPOSE 8000`.
- `CMD` starts Uvicorn with reload, binding all interfaces: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (or activate `/opt/venv` on PATH and call `uvicorn` directly).

### 5.5 `/services/.dockerignore`

At minimum: `__pycache__`, `*.pyc`, `.env*`, `tests/`, `*.log`. Also create a **root-level `.dockerignore`**: because the backend build context is the repo root, the root file is the one Docker actually applies — it must exclude at least `**/node_modules`, `**/.next`, `**/__pycache__`, `**/*.pyc`, `.env*`, `**/tests/`, `**/*.log`, `.git`. Keep the `/services/.dockerignore` too (ticket checklist requirement, and it protects anyone building with `./services` as context).

### 5.6 `/docker-compose.yml` (repo root)

Two services on one explicitly named network:

- **`ui`**: `build: { context: ./uis, dockerfile: Dockerfile }`; ports `3000:3000`, `3001:3001`; bind mounts `./uis:/app/uis`, `./packages:/app/packages`, `./apps:/app/apps`; **anonymous volumes** to protect image-installed artifacts from being shadowed by the bind mount: `/app/uis/website/node_modules`, `/app/uis/backoffice/landing/node_modules`, `/app/uis/website/.next`, `/app/uis/backoffice/landing/.next`; `env_file: .env`; `depends_on: api`.
- **`api`**: `build: { context: ., dockerfile: services/Dockerfile }`; port `8000:8000`; bind mounts `./services:/app/services`, `./packages:/app/packages`; `env_file: .env`; environment values (CORS, secret, etc.) referenced from `.env` — **no literal values in the YAML**.
- `networks:` block defining e.g. `healthcore_net`, attached to both services.
- No `version:` key (obsolete in Compose v2).

### 5.7 `/.env` and `/.env.example` (repo root)

Create `.env` **before** writing `docker-compose.yml` (ticket requirement). Also commit `.env.example` with the same keys and safe placeholder/dev values (`.gitignore` already whitelists `!.env.example`). Verify `.env` is matched by `.gitignore` (`git check-ignore .env` must succeed).

---

## 6. Environment Variables

All values flow from the root `.env` via `env_file:`. Nothing hardcoded in YAML or Dockerfiles.

| Variable | Dev value | Consumed by | Purpose |
|----------|-----------|-------------|---------|
| `SECRET_KEY` | generate a random dev string | api | JWT signing — **required, no default in `app/core/config.py`**; the API crashes without it |
| `JWT_EXPIRE_MINUTES` | `60` | api | token lifetime — required, no default |
| `APP_ENV` | `development` | api | |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001` | api | browser origins — must match the **new** ports, overriding the 3004/3005 defaults in `config.py` |
| `FRONTEND_URL` | `http://localhost:3001` | api | links generated for the backoffice (browser-facing → localhost is correct) |
| `EMAIL_API_KEY` | empty | api | optional (Resend) |
| `DATABASE_URL` | empty | api | optional Postgres; empty ⇒ TinyDB |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | ui (browser) | consumed by the **browser** on the host — `localhost` is correct and unavoidable here; browsers cannot resolve Docker service names |
| `API_URL_INTERNAL` | `http://api:8000/api/v1` | ui (server-side) | **service-name URL** for any container-to-container call (Next.js server-side fetches, route handlers). Audit `uis/` for server-side API calls; wire any you find to this variable |
| `WEBSITE_PORT` | `3000` | ui (`start.sh`) | |
| `BACKOFFICE_PORT` | `3001` | ui (`start.sh`) | |
| `NEXT_PUBLIC_WEBSITE_URL` | `http://localhost:3000` | ui (browser) | the "Public Website" card on the backoffice hub. **Requires the one sanctioned source edit of this ticket:** `uis/backoffice/landing/lib/nav-apps.ts` hardcodes `url: "http://localhost:3005"` — change it to `` process.env.NEXT_PUBLIC_WEBSITE_URL ?? "http://localhost:3005" `` (keep the 3005 fallback so the local non-Docker workflow is unchanged). Without this, the hub's website link 404s in Docker and the "no hardcoded values" checklist fails |

> The two-URL split (`NEXT_PUBLIC_API_URL` for the browser, `API_URL_INTERNAL` for container-to-container) is the agreed interpretation of the ticket's "service name, not localhost" rule: every URL used *by a container* uses the service name; URLs used *by the browser* necessarily use `localhost`.

---

## 7. Development Workflow

### First run (this is the onboarding path being sold to the infra team)

```bash
git clone <fork> && cd <repo>
cp .env.example .env        # fill SECRET_KEY with any random string
docker compose up --build
```

Expected result: website at `http://localhost:3000`, backoffice at `http://localhost:3001`, API docs at `http://localhost:8000/docs`.

### Verification checklist (run all of these before considering the task done)

1. **Cold build:** `docker compose build --no-cache` succeeds for both services.
2. **Startup:** `docker compose up` → `docker compose ps` shows both containers `running`; no crash loops in logs.
3. **Endpoints respond:** `curl -f http://localhost:3000`, `curl -f http://localhost:3001`, and `curl -f http://localhost:8000/docs` all return successfully from the host. Also hit the aliased backoffice tool routes `http://localhost:3001/incident-analyzer` and `http://localhost:3001/supplier-directory` — an auth redirect (3xx) or 200 is a pass (proves the aliased modules compiled); a 500 or webpack module-resolution error is a fail (see §4.1 item 3).
4. **Hot reload, all three apps:** touch a file in `uis/website/app/`, `uis/backoffice/landing/app/`, and `services/api/app/` — logs must show Next.js recompiling and Uvicorn reloading. If Next.js misses file events on macOS bind mounts, set `WATCHPACK_POLLING=true` in the ui service environment (via `.env`).
5. **Service-name audit:** `grep -rn "localhost" docker-compose.yml .env.example uis/ services/ --include='*.yml' --include='*.ts' --include='*.py' --include='*.sh'` (excluding `node_modules`) and confirm every hit is browser-facing (`NEXT_PUBLIC_*`, CORS origins, `FRONTEND_URL`) — zero `localhost` in container-to-container URLs. The `?? "http://localhost:3005"` fallback in `nav-apps.ts` is acceptable (local-only default; Docker overrides it via `NEXT_PUBLIC_WEBSITE_URL`). Verify in the running stack that the backoffice hub's "Public Website" card points to `http://localhost:3000`. From inside the ui container, `wget -qO- http://api:8000/docs` must succeed, proving service-name resolution on the named network.
6. **Secret hygiene:** `git check-ignore .env` succeeds; `grep -i "secret\|key\|password" docker-compose.yml uis/Dockerfile services/Dockerfile uis/start.sh` shows variable *references* only, never values.
7. **Clean-slate rerun:** `docker compose down -v && docker compose up` still works (anonymous volumes rebuild from the image layers).

### Day-to-day commands (document these in a short section of the repo README or a `docs/` note)

- `docker compose up` / `docker compose up -d` / `docker compose down`
- `docker compose logs -f ui` / `api`
- `docker compose exec api uv run pytest` (tests run inside the container)
- `docker compose exec api uv run seed` — populate a fresh TinyDB (first run starts empty; seeding is idempotent and **must not** run automatically on container start, per §4.3). Document this as the post-first-`up` step for developers who want sample data.
- After changing dependencies (`package.json` / `pyproject.toml`): `docker compose up --build`; if node_modules look stale, `docker compose down -v` first (anonymous volumes cache them).

### Troubleshooting notes to leave in the docs

- Port already in use → another local dev server is holding 3000/3001/8000; stop it or change host-side mappings in `docker-compose.yml`.
- Backoffice module-resolution errors for `backoffice_functions`/`talent-tracker` imports → see §4.1 item 3.
- API exits immediately → `SECRET_KEY`/`JWT_EXPIRE_MINUTES` missing from `.env`.

### Submission

Capture a screenshot of `docker compose ps` (or the running `docker compose up` output) showing both containers up, and save the reference in the repo per the course's screenshot convention (see `docker_screenshot.md`).

---

## 8. Acceptance Criteria (ticket checklist, restated against this repo)

- [ ] Cleanup commit landed first: redundant `pandas` removed from `services/api/pyproject.toml`, both lockfiles re-locked, pytest green from both `services/api` and the repo root, README notes added documenting the intentional dual-lockfile uv setup and the kept legacy `apps/talent-pipeline-tracker` copy, npm dep-drift guardrail script added and passing, Node version pinned via `.nvmrc` + `engines`, env-example conventions consolidated, shared-package naming quirk documented (§0)
- [ ] `Dockerfile` + `.dockerignore` in `/uis/` — Node Alpine image, deps installed separately for website and backoffice/landing, `CMD` → `start.sh` running both apps (website 3000, backoffice 3001)
- [ ] `Dockerfile` + `.dockerignore` in `/services/` — official Python image, deps via **uv** from `pyproject.toml`/`uv.lock` (agreed deviation from the ticket's requirements.txt wording), Uvicorn with `--reload`
- [ ] Root `.dockerignore` (needed because the api build context is the repo root)
- [ ] `docker-compose.yml` at repo root: exactly two services, bind mounts, correct ports exposed, explicitly named network
- [ ] `.env` created at root before the compose file; `.env.example` committed; `.env` confirmed git-ignored
- [ ] Zero hardcoded config in YAML/Dockerfiles — everything via `.env`
- [ ] Hot reloading verified in website, backoffice, and API
- [ ] Container-to-container URLs use service names; audit performed and passing (§7 step 5)
- [ ] `docker compose up` from a clean checkout (plus `cp .env.example .env`) brings up the full platform with no additional steps
- [ ] Existing local (non-Docker) workflows untouched: no edits to `package.json`, `pyproject.toml`, or application source
