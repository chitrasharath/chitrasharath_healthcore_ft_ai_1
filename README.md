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

## Backoffice Functions (M2 manual test)

Internal dashboard for running HealthCore Milestone 2 utility functions against sample data. Lives at `uis/backoffice/backoffice_functions/` under the `uis/backoffice/` parent folder.

```bash
cd uis/backoffice/backoffice_functions
npm install
npm run dev
```

Open **http://localhost:3001**. Verify: `npm run verify`

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

Local dev works without a `.env` file. Uvicorn uses port **8000**; frontends run on **3002** (incident analyzer) and **3003** (supplier directory). CORS for those origins is configured by default in `app/core/config.py`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/api/v1/incidents/analyze` | POST | Upload CSV (`multipart/form-data`, field `file`) |
| `/api/v1/incidents/results/export` | GET | Download last analysis as CSV |
| `/api/v1/suppliers` | GET, POST | List or register suppliers (`?country=`, `?category=` on GET) |
| `/api/v1/suppliers/{id}` | GET, DELETE | Supplier detail; DELETE soft-suspends |
| `/api/v1/suppliers/{id}/rate` | PATCH | Update monthly rate |
| `/api/v1/suppliers/{id}/status` | PATCH | Activate or suspend supplier |
| `/api/v1/suppliers/{id}/details` | PATCH | Update optional fields (compliance, renewal, email, notes) |
| `/api/v1/auth/register` | POST | Register user; returns JWT |
| `/api/v1/auth/login` | POST | Login; returns JWT |
| `/api/v1/auth/me` | GET | Current user (Bearer token) |
| `/api/v1/users` | GET, POST | List users (auth) or create user (public) |
| `/api/v1/users/{id}` | GET, PUT, DELETE | User CRUD (auth; PUT owner-only) |

### Dashboard (Next.js)

From `uis/incident_analyzer/`:

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:3002**, upload an incidents CSV, and view the analysis dashboard. Use **Export results to CSV** to download via the API (requires the backend running on port 8000). Set `NEXT_PUBLIC_API_URL` in `.env.local` (default: `http://localhost:8000`).

Test file: `uis/incident_analyzer/incidents-healthcore.csv` (100 rows; expected: 94 valid, 6 invalid, satisfaction average **3.58**).

---

## Supplier Directory

Centralized supplier registry for HealthCore procurement and compliance. TinyDB-backed API at `services/api`; standalone Next.js dashboard at `uis/supplier_directory/` (port **3003**).

### Seed database

From `services/api/`:

```bash
uv sync --extra dev
uv run seed
```

Loads 15 suppliers idempotently (skips existing names). Plan: `memory-bank/references/supplier_directory_ai_plan/IMPLEMENTATION_PLAN.md`.

### Dashboard (Next.js)

From `uis/supplier_directory/`:

```bash
cp .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:3003**. Requires the API on port 8000 with seeded data. Verify: `npm run verify`

---

## Authentication (AUTH-01)

JWT-based authentication and user management at `services/api`. Passwords are bcrypt-hashed; protected routes require `Authorization: Bearer <token>`.

Plan: `memory-bank/references/authentication_backend_ai_plan/IMPLEMENTATION_PLAN_auth_1.md`.

### Environment variables

Copy `services/api/.example.env` to `services/api/.env` before starting the API (required):

```bash
SECRET_KEY=change-me-before-production
JWT_EXPIRE_MINUTES=30
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
| `/api/v1/users` | POST | No | Create user (no token returned) |
| `/api/v1/users` | GET | Yes | List all users |
| `/api/v1/users/{id}` | GET | Yes | Get user by id |
| `/api/v1/users/{id}` | PUT | Yes | Update own record only (`403` otherwise) |
| `/api/v1/users/{id}` | DELETE | Yes | Delete user (`204`) |

`/api/v1/suppliers` and `/api/v1/incidents` remain **unprotected** in this milestone.

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
