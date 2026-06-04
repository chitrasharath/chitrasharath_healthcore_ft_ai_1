# HealthCore Platform Architecture Proposal

**Status:** Approved target-state architecture (derived from `architecture_proposal_plan.md`)  
**Audience:** Engineering, product, and operations stakeholders  
**Scope:** FastAPI backend structure, API domains, frontend/backend boundaries, and integration with the existing monorepo. This document is not a full infrastructure or deployment runbook.

---

## 1. Executive Summary

HealthCore operates 12 outpatient clinics across the US and UK. Milestones 1–4 delivered a public bilingual website, TypeScript operational utilities, a recruiting app, and Next.js migrations—but **there is no FastAPI backend today**. Persisted workflows (patient enquiry, appointments, claims, audit) need a single authoritative API.

This proposal recommends:

- A **modular monolith** FastAPI application at **`services/api`**, organized by **business** and **technology** domains.
- **Supabase PostgreSQL** for application data and append-only compliance audit storage.
- **Auth** as a technology domain issuing **JWTs with coarse roles**; **Compliance** for HIPAA policy and audit (after Auth).
- **Native Python** business rules per domain—the backend **does not port** Milestone 2 (`apps/src`) utilities; backoffice and CLI keep M2 unchanged.
- Clear boundaries: Scheduling (*when*), Clinical (*what happened*), Billing (*what we charge*), Workforce (*who*), Compliance (*controls and evidence*).

Phased delivery starts with Auth/JWT and Supabase, then Compliance audit, Intake, Scheduling/Billing, Workforce, Clinical (mock EHR), and auto-claim on encounter complete.

---

## 2. Context and Current Landscape

| Area | Current state |
|------|----------------|
| **Public web** | `uis/website` — landing (`/`), enquiry form (`/enquiry-form`); validation in Next.js; submit not yet wired to a live API |
| **M2 utilities** | `apps/src` — TypeScript CLI, tests, legacy browser page; **`uis/backoffice`** imports M2 for manual test UI only |
| **Recruiting** | `apps/talent-pipeline-tracker` — Talent Tracker API; primary candidate UX stays here |
| **Legacy portal** | `apps/healthcore_web_portal/` — superseded by `uis/website` for M4 |
| **Backend** | **None** — target is new `services/api` (uv + FastAPI + Pydantic v2) |

Alignment with memory-bank milestones: M1 structured intake → **Intake** domain; M2 KPI concepts → **Billing**, **Scheduling**, **Compliance**, **Reporting** (Python implementations); M3 recruiting → **Workforce** hiring via **Talent Tracker adapter-only**.

---

## 3. Architectural Pattern

### 3.1 Recommendation

| Pattern | Fit for HealthCore |
|---------|-------------------|
| **Modular monolith** | One deployable API; modules bounded by domain. Matches phased milestones and team size. |
| **Layered per domain** | `router` → `service` → `repository`. Thin HTTP handlers. |
| **Not microservices (yet)** | 12 clinics do not justify operational split until scale or team structure requires it. |
| **Ports and adapters (light)** | EHR and Talent Tracker behind protocols; eases testing and future extraction. |

### 3.2 System context

```
┌────────────────────────── uis (Next.js) ──────────────────────────┐
│                                                                     │
│   website (public) ──────────────────────────────┐                  │
│                                                   │                  │
│   backoffice (M2 manual test) ──────► apps/src (M2 TS utils)        │
│              │                         ▲                           │
│              └──── M2 utils only ──────┘                           │
│                                                                     │
│   talent-pipeline-tracker ──────────► Talent Tracker API (M3)      │
│              │                                                     │
└──────────────┼─────────────────────────────────────────────────────┘
               │ HTTPS (website → API; intake via server proxy)
               ▼
┌────────────────────── services/api (FastAPI monolith) ────────────────┐
│                                                                     │
│   ┌─ Technology ─┐     ┌─ Business domains ─────────────────────┐  │
│   │ Auth (JWT)    │     │ Reference  Intake  Scheduling        │  │
│   └───────┬───────┘     │ Clinical   Billing  Workforce        │  │
│           │ coarse roles│ Compliance Reporting                 │  │
│           ▼             │     ▲ EHR adapters (mock) in Clinical│  │
│   Compliance ─────────┼─────┘ PolicyEnforcer after Auth       │  │
│   (audit, CME, HIPAA)  │                                        │  │
│                        │  Scheduling ──appointment_id──► Clinical │  │
│                        │  Clinical ──encounter / billable──► Billing│
│                        │  Scheduling ──no-show KPIs────────► Billing│
│                        │  Workforce ──active clinician_id──► Clinical│
│                        │  Compliance ──CME reports──────────► Workforce│
│                        │  Compliance ──audit + policy on PHI domains │  │
│                        └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
               ▲
               │ Talent Tracker adapter (hiring sync)
               └──────── talent-pipeline-tracker (primary recruiting UI)
```

### 3.3 Request pipeline (PHI routes)

1. **Auth** — authenticate caller; enforce coarse role on route.  
2. **Compliance** — `PolicyEnforcer` (HIPAA: minimum necessary, purpose of use, break-glass with audit).  
3. **Domain handler** — business logic.  
4. **Compliance audit** — record event (resource IDs only, not full PHI bodies).

Valid JWT does **not** imply HIPAA-allowed access.

### 3.4 Domain one-liners

| Domain | Answers |
|--------|---------|
| **Reference** | What codes and sites exist? |
| **Intake** | Who expressed interest before a visit? |
| **Scheduling** | When is the patient expected? |
| **Clinical** | What happened during care? |
| **Billing / RCM** | What do we charge and what did payers do? |
| **Workforce** | Who are we hiring, onboarding, and rostering? |
| **Compliance** | Who may access PHI, what must we record, CME evidence? |
| **Reporting** | What are cross-domain KPIs for ops leadership? |
| **Integrations** | How do we connect to EHR and Talent Tracker safely? |
| **Auth** | Who is calling the API (technology)? |

---

## 4. Domain Model

Domains live under `app/domains/` with **router → service → repository** layering. **Business** domains own HealthCore workflows; **Technology** domains own platform capabilities.

### 4.1 Domain catalog

| Domain | Layer | API prefix | Primary responsibility |
|--------|-------|------------|-------------------------|
| **Reference** | Business | `/api/v1/reference` | Master data: locations, service types, enums |
| **Intake** | Business | `/api/v1/intake` | Public enquiries and callback workflow |
| **Scheduling** | Business | `/api/v1/scheduling` | Appointments, no-show metrics |
| **Clinical** | Business | `/api/v1/clinical` | Encounters, notes, EHR mock adapter (v1) |
| **Billing / RCM** | Business | `/api/v1/billing` | Claims (auto from encounter), denial KPIs |
| **Workforce** | Business | `/api/v1/workforce` | Roster, hiring, onboarding |
| **Compliance** | Business | `/api/v1/compliance` | Supabase audit log, CME, code-first HIPAA |
| **Reporting** | Business | `/api/v1/reporting` | Read-only KPI orchestration |
| **Integrations** | Supporting | *(no public prefix)* | Shared HTTP/contracts; adapters in Clinical & Workforce |
| **Auth** | Technology | `/api/v1/auth` | Users, coarse roles, JWT issuance |

### 4.2 Business domain summary

| Domain | Responsibility | Key links |
|--------|----------------|-----------|
| **Reference** | `Location`, `ServiceType`, shared enums | Read by all domains |
| **Intake** | Enquiries; no clinical/billing data | → Scheduling; Compliance on submit |
| **Scheduling** | `Appointment` lifecycle | → Clinical; → Billing (no-show KPIs); ← Workforce |
| **Clinical** | `Encounter`, notes, EHR adapter | → Billing (auto-claim); → Compliance (audit) |
| **Billing** | `Claim`, denial metrics | ← Clinical, Scheduling, Reference |
| **Workforce** | Roster, hiring, single onboarding checklist | ↔ Talent Tracker adapter; → Clinical, Compliance |
| **Compliance** | Audit, CME calculators, HIPAA policies | Audits PHI domains; reads Workforce for CME |
| **Reporting** | Weekly/executive read models | Reads other domains; no writes |
| **Integrations** | Transport and adapter contracts | EHR under Clinical; Talent Tracker under Workforce |

### 4.3 Separation criteria

1. **Bounded context** — One owner per entity lifecycle (e.g. only Billing mutates `Claim.status` after rules).  
2. **Change frequency** — Billing changes often; Reference rarely.  
3. **Audience** — Public Intake vs internal PHI routes (auth and rate limits differ).  
4. **Regulatory sensitivity** — Compliance centralizes audit, CME reporting, HIPAA—not reimplemented per router.  
5. **Reuse without coupling** — `ReferenceService` interfaces, not cross-domain SQL.

**Anti-pattern:** a single `operations` router bundling unrelated endpoints.

---

### 4.4 Reference

**Purpose:** Canonical master data and enums for the 12-clinic network.

| Submodule | Responsibility |
|-----------|----------------|
| `locations/` | `Location`: country (US/UK), timezone, active flag |
| `service_types/` | Schedulable/billable catalog |
| `enums/` | Aligned with `app/schemas/enums.py` |

**Rules:** Does not own patients, appointments, or claims. UK/US payer and CME parameters derive from `Location.country`. Infrequent writes; cache-friendly reads in v1.

**API (v1):** `GET /reference/locations`, `GET /reference/service-types`; admin `POST/PATCH` with `admin` role.

**Auth:** Optional public read for website dropdowns; admin for writes.

---

### 4.5 Intake

**Purpose:** Structured public patient interest before a visit—replaces client-only submit on `uis/website`.

| Submodule | Responsibility |
|-----------|----------------|
| `enquiries/` | `Enquiry` CRUD and status |
| `callback_queue/` | Staff queue filters |

**Entity:** `Enquiry` with PII, preferences, `status` (`new`, `contacted`, `scheduled`, `closed`); optional `appointment_id` after Scheduling books. **No** encounters or claims.

**API (v1):**

- `POST /intake/enquiries` — public, rate-limited, `extra="forbid"` on schema  
- `GET /intake/enquiries`, `PATCH /intake/enquiries/{id}` — internal (`front_desk`, `admin`)

**Frontend:** `uis/website` proxies via Next server route (no browser JWT). API is authoritative; Next validation mirrors `lib/enquiry-validation.ts`.

**Compliance:** `PolicyEnforcer` on POST; audit `intake.enquiry.created` (IDs only).

---

### 4.6 Scheduling

**Purpose:** **When** the patient is expected—not clinical notes or claim status.

| Submodule | Responsibility |
|-----------|----------------|
| `appointments/` | `Appointment` with `location_id`, `clinician_id`, `service_type_id`, `status` |
| `metrics/` | No-show rates/cost (native Python) |

**Statuses:** e.g. `scheduled`, `checked_in`, `completed`, `cancelled`, `no_show`. `clinician_id` must be **active** in Workforce. `checked_in` triggers Clinical to open/link encounter via **service call**.

**API (v1):** `GET/POST /scheduling/appointments`, `PATCH .../status`, `GET /scheduling/metrics/no-show`.

**Boundaries:** No note text, EHR IDs, or claims. Clinical updates appointment to `completed` when encounter completes.

---

### 4.7 Clinical Operations

**Purpose:** **What happened** during and after the visit.

| Submodule | Responsibility |
|-----------|----------------|
| `encounters/` | Lifecycle linked to `appointment_id`, `clinician_id`, `patient_id` |
| `notes/` | Documentation; never on public Intake routes |
| `adapters/` | **EHR** — v1 **mock only** (`EHR_ADAPTER=mock`) |

**API (v1):** Encounters CRUD; `PATCH .../status` with **completed** → in-process `EncounterCompleted` → Billing **auto-create claim** (idempotent on `encounter_id`); notes; internal `ehr-sync` and adapter health.

**EHR pattern:** `EhrAdapter` protocol in `adapters/base.py`; anti-corruption layer to Pydantic schemas; vendor JSON never in Billing routers.

**Boundaries:** Does not set `Claim.status`. Billing may call `get_encounter_summary` read-only only.

---

### 4.8 Billing / RCM

**Purpose:** **What we charge** and payer outcomes.

| Submodule | Responsibility |
|-----------|----------------|
| `claims/` | `Claim` linked to `encounter_id`, `appointment_id`, `patient_id` |
| `metrics/` | Denial rates, high-denial payers (native Python) |

**Auto-claim (decided):** On encounter complete, `BillingService.create_claim_from_encounter` creates claim if none exists for `encounter_id`. Clinical supplies billable snapshot; Billing owns denial and status transitions (`draft` → `submitted` → `paid` / `denied`).

**API (v1):** `GET /billing/claims`, `PATCH /billing/claims/{id}`, KPI subpaths (`denial-rates`, `payers/high-denial`). No public patient `POST /claims` in v1.

**Auth:** `billing_analyst`, `admin`. HIPAA via `PolicyEnforcer`, not inline in `billing/service.py`.

---

### 4.9 Workforce

**Purpose:** Hire → onboard → active roster. **Not** audit/CME ownership (Compliance).

| Submodule | Responsibility |
|-----------|----------------|
| `clinicians/` | Roster: licence dates, CME hour fields on record, `active` \| `inactive` |
| `hiring/` | Pipeline + **Talent Tracker adapter-only** |
| `onboarding/` | **Single checklist** for all roles (v1) |

**Hiring:** Primary UI remains `apps/talent-pipeline-tracker`. HealthCore DB owns hiring state for reporting; adapter syncs `talent_candidate_id`. On **hired** → onboarding; not `active` clinician until onboarding completes.

**API (v1):** Clinicians, `hiring/candidates`, `onboarding` tasks; adapter sync internal only.

**Links:** Active clinicians only in Clinical picklists; Compliance reads roster for CME; Workforce does not write audit rows.

---

### 4.10 Compliance

**Purpose:** Regulatory controls and evidence across domains.

| Submodule | Responsibility |
|-----------|----------------|
| `audit/` | Append-only log in **same Supabase project** as app data |
| `cme/` | Reports, at-risk, expiring licences (native Python; not M2 port) |
| `policies/` | **Code-first** HIPAA `PolicyEnforcer` |

**Audit:** Middleware/dependency on PHI routes; explicit events (`clinical.note.viewed`, `billing.claim.denied`); never store full note body or SSN in payload. No UPDATE/DELETE via API.

**CME split:** Workforce owns clinician hour fields; Compliance owns calculators and reports (US/UK via Reference `country`).

**API (v1):** `GET /compliance/audit-events`, CME report endpoints, internal `GET /policies`.

---

### 4.11 Reporting

**Purpose:** Read-only cross-domain KPIs—does not own source tables.

Calls domain services (`BillingService.get_denial_summary`, etc.)—no cross-domain SQL in `reporting/repository.py`. KPI parity with `apps/src` / backoffice **not guaranteed**.

**API (v1):** `GET /reporting/kpis/weekly` with `location_id`, `week_start`.

**Auth:** `read_only_ops`, `billing_analyst`, `admin`, `compliance_officer` as appropriate.

---

### 4.12 Integrations

**Purpose:** Shared connectivity patterns—not a standalone product API.

| Piece | Location |
|-------|----------|
| HTTP client, webhook verification | `domains/integrations/` (contracts, `http/`) |
| **EHR** | `domains/clinical/adapters/` — mock v1 |
| **Talent Tracker** | `domains/workforce/adapters/` — hiring sync |

Service accounts and API keys via Auth; secrets never in frontends. Vendor payloads stop at adapter boundary.

---

### 4.13 Auth (Technology)

**Purpose:** Identity and **coarse-role** route authorization before Compliance HIPAA checks.

| Submodule | Responsibility |
|-----------|----------------|
| `users/`, `roles/`, `tokens/` | Login, JWT issue/validate, optional denylist |
| `permissions/` | *Deferred v1* |

**JWT claims:** `sub`, `roles[]`, `exp`, `iat`, optional `location_scope[]`—no PHI in payload.

**Endpoints:** `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `GET /me`. Validation via `Depends(get_current_user)` and `require_role(...)` in `core/dependencies.py` → **AuthService**.

#### JWT implications

| Topic | Implication |
|-------|-------------|
| Stateless validation | Logout/revocation needs short access TTL, refresh rotation, and/or denylist |
| Signing keys | Server-only; plan rotation (RS256 preferred in production) |
| Stolen token | HTTPS, short TTL, prefer httpOnly cookie for internal UIs |
| Stale roles | Offboarding: refresh, denylist, or wait for expiry |
| Compliance | Auth first, then `PolicyEnforcer`; audit uses `sub`, not raw JWT |

**v1 defaults:** Access TTL 15–60 minutes; refresh with rotation; RS256 in production.

**Frontends:** Website mostly anonymous; backoffice/dashboards Bearer or server-set cookie after server-side login.

---

## 5. Cross-Domain Linking

Use **shared IDs** and **domain service calls**—not cross-domain repository imports.

```
  Scheduling              Clinical                 Billing
  ┌─────────────┐         ┌─────────────┐          ┌─────────┐
  │ Appointment │────────►│  Encounter  │─────────►│  Claim  │
  └─────────────┘         │      │      │          └─────────┘
       │                  │      ▼      │               ▲
       │                  │ Clinical  │               │
       │                  │   Note    │               │
       │                  └───────────┘               │
       │                                               │
       └──────── no_show (no encounter) ───────────────┘
                 KPIs / metrics only

  Clinical ──complete encounter──► auto-create Claim (idempotent on encounter_id)
  Billing ──read-only──► Encounter summary (appeals); no writes to notes
```

| Link | Rule |
|------|------|
| Scheduling → Clinical | Check-in creates/links `Encounter` with `appointment_id` |
| Clinical → Scheduling | Complete encounter → appointment `completed` |
| Clinical → Billing | Complete encounter → **auto-create claim** (idempotent) |
| Scheduling → Billing | No-show KPIs without encounter |
| Billing → Clinical | Read-only `get_encounter_summary` for appeals |

**Implementation rules:**

1. Foreign keys as IDs; clear table owner per domain.  
2. No `billing/repository` queries on clinical tables—use `ClinicalService`.  
3. v1: in-process `EncounterCompleted` handler (awaited, not fire-and-forget).  
4. Nested aggregates (appointment + encounter + claim) → **Reporting** or dedicated read endpoint.

---

## 6. Repository Layout

Stay in the **existing monorepo**; add backend as first-class:

```
healthcore-monorepo/
├── services/
│   └── api/                 # FastAPI + uv (sole Python project)
├── apps/
│   ├── src/                 # M2 TS — CLI, tests, backoffice only
│   ├── talent-pipeline-tracker/
│   └── healthcore_web_portal/   # legacy
├── uis/
│   ├── website/
│   └── backoffice/
├── docs/
│   └── architecture_proposal.md
└── memory-bank/
```

**No uv workspace members**—one `pyproject.toml` and `uv.lock` under `services/api/`.

---

## 7. Backend Structure (`services/api`)

### 7.1 Toolchain: uv

| Concern | Approach |
|---------|----------|
| Root | `services/api/pyproject.toml` |
| Lockfile | `services/api/uv.lock` (committed) |
| Python | 3.12 (`.python-version` + `requires-python`) |
| Run | `uv run uvicorn app.main:app --reload`, `uv run pytest` |
| CI | `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` |

Do not mix `pip install -r requirements.txt` with uv for this app.

### 7.2 Module tree (abbreviated)

```
services/api/
├── pyproject.toml
├── uv.lock
├── alembic/
├── tests/{unit,api}/
└── app/
    ├── main.py
    ├── core/{config,dependencies,exceptions,middleware,audit_middleware,security}.py
    ├── api/v1/{router,health}.py
    ├── schemas/{common,enums,errors}.py
    └── domains/
        ├── technology/auth/
        ├── reference/
        ├── intake/
        ├── scheduling/
        ├── clinical/{encounters,notes,adapters}/
        ├── billing/
        ├── workforce/{clinicians,hiring,onboarding,adapters}/
        ├── compliance/{audit,cme,policies}/
        └── reporting/
```

### 7.3 Layer rules

| Layer | Responsibility |
|-------|----------------|
| `router.py` | HTTP only |
| `schemas.py` | Pydantic `*Create`, `*Update`, `*Read` |
| `service.py` | Business rules (native Python) |
| `repository.py` | Persistence |
| ORM `models.py` | Never exposed as API responses |

### 7.4 Schema layout

| Location | Contents |
|----------|----------|
| `app/schemas/` | Pagination, IDs, enums, coarse roles, errors |
| `domains/*/schemas.py` | Domain request/response models |
| OpenAPI | Generated from FastAPI + Pydantic |

Domains import shared schemas only—not each other’s `schemas.py` (use service interfaces).

### 7.5 Configuration

`pydantic-settings` in `core/config.py`: `APP_ENV`, `DATABASE_URL` (Supabase), `SUPABASE_URL`, `CORS_ORIGINS`, `JWT_*`, `EHR_ADAPTER`, `TALENT_TRACKER_*`. Fail fast on misconfiguration at startup. Secrets in `.env.example`, never committed.

---

## 8. Python, FastAPI, and Pydantic Best Practices

Enforced in CI for all `services/api` code.

### 8.1 Style (PEP 8 + Ruff)

- [PEP 8](https://peps.python.org/pep-0008/): 4 spaces, 88-char lines.  
- **Ruff** for lint (`ruff check`) and format (`ruff format`).  
- [PEP 484](https://peps.python.org/pep-0484/) type hints on public APIs; optional **mypy** in CI.  
- Absolute imports; no wildcard imports; no PHI or tokens in logs.

### 8.2 Pydantic v2

- Separate API schemas from ORM; `model_validate` + `from_attributes=True` for reads.  
- Shared enums in `app/schemas/enums.py`.  
- `extra="forbid"` on public Intake creates.  
- UTC datetimes in DB; ISO-8601 in API.

### 8.3 FastAPI

- App factory + `lifespan`; one `APIRouter` per domain.  
- `Depends(get_db)`, `get_current_user`, `require_role`, `PolicyEnforcer`.  
- `response_model` on routes; explicit status codes.  
- Auto-claim and audit: **await** in service path, not unverified `BackgroundTasks`.  
- Tests: `httpx.AsyncClient`; happy path + auth failure on sensitive routes.

---

## 9. API Routes and Versioning

All business routes under **`/api/v1/`**.

| Prefix | Domain | Notes |
|--------|--------|-------|
| `/api/v1/auth` | Auth | login, refresh, logout, me |
| `/api/v1/reference` | Reference | locations, service-types |
| `/api/v1/intake` | Intake | enquiries |
| `/api/v1/scheduling` | Scheduling | appointments, no-show metrics |
| `/api/v1/clinical` | Clinical | encounters, notes, ehr-sync |
| `/api/v1/billing` | Billing | claims, denial KPIs |
| `/api/v1/workforce` | Workforce | clinicians, hiring, onboarding |
| `/api/v1/compliance` | Compliance | audit-events, cme/*, policies |
| `/api/v1/reporting` | Reporting | kpis/weekly |

**Grouping:** REST collections; KPIs as subpaths; OpenAPI tags for public vs internal; pagination via query params.

Each domain exports `APIRouter`; `api/v1/router.py` mounts all in `main.py`.

---

## 10. Frontend and Backend Boundaries

| System | Location | Role |
|--------|----------|------|
| Public UI | `uis/website` | Intake via server-side proxy to API |
| Internal ops | `uis/backoffice` + future dashboards | M2 test today; APIs later with JWT |
| Recruiting | `apps/talent-pipeline-tracker` | Primary UX; Workforce adapter sync |
| Backend | `services/api` | Authoritative persisted data (Supabase) |

**Communication:** HTTPS JSON REST; OpenAPI at `/docs` and `/openapi.json`. Server-only `API_URL` for public forms; `NEXT_PUBLIC_API_URL` only if browser must call API directly.

**CORS:** Prefer **no** browser CORS for public website (Next proxy). Internal apps: explicit `CORS_ORIGINS`; no `*` with credentials.

See `.env.example` per app for `DATABASE_URL`, `JWT_*`, `EHR_*`, `TALENT_TRACKER_*`, `CORS_ORIGINS`, `API_URL`.

---

## 11. Relationship to M2 TypeScript Utilities

The FastAPI backend **does not import, port, or mirror** the 22 M2 operations in `apps/src`.

| System | M2 usage |
|--------|----------|
| `services/api` | **Ignore M2** — native Python per domain |
| `uis/backoffice` | Imports M2 via `@healthcore/src/*` |
| `apps/src` CLI/tests | Unchanged |
| `uis/website` | Next validation only unless separately scheduled |

Backend KPIs are validated against **business requirements**, not automatic parity with backoffice manual tests. Optional future: shared JSON fixture tests for alignment.

---

## 12. Phased Rollout

Recommended sequence (each phase shippable behind feature flags where needed):

| Phase | Deliverables |
|-------|----------------|
| **1** | Scaffold `services/api`; uv, Ruff, pytest; Auth (login, JWT, coarse roles); health check |
| **2** | Supabase + Alembic; Reference seed; settings validation |
| **3** | Compliance audit middleware + append-only tables; `PolicyEnforcer` skeleton |
| **4** | Intake `POST /enquiries`; website server proxy |
| **5** | Scheduling appointments + status; Workforce active roster read |
| **6** | Clinical encounters + mock EHR; encounter complete event |
| **7** | Billing auto-claim (idempotent); claims list/PATCH; denial KPIs |
| **8** | Workforce hiring/onboarding + Talent Tracker adapter |
| **9** | Compliance CME reports; Reporting weekly KPIs |
| **10** | Hardening: rate limits, audit export, operational runbooks in `services/api/README.md` |

Auth/JWT and Supabase precede PHI domains. Auto-claim ships with Clinical + Billing in the same phase window.

---

## 13. Risks and Mitigations

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Duplicated logic (Python, Next, M2) | API authoritative for persisted data; document known backoffice divergence |
| 2 | God router / mixed domains | One router per domain; code review on `api/v1/router.py` |
| 3 | Public CORS to API | Next server proxy for Intake |
| 4 | Unversioned API breaks clients | `/api/v1` prefix; breaking changes only in v2 |
| 5 | Logic in routers | Layer discipline + tests on services |
| 6 | pip + uv drift | uv only; frozen lockfile in CI and Docker |
| 7 | PHI in wrong module | Domain boundaries in §4; reviews on imports |
| 8 | EHR logic outside adapters | Protocol + mock-only v1 |
| 9 | Scattered audit/HIPAA | Compliance owns audit writer and `PolicyEnforcer` |
| 10 | Mutable audit rows | Append-only DB policies; no delete API |
| 11 | JWT decode in business domains | Central `AuthService` + dependencies |

**Operational notes:** Audit partition/retention; UK vs US CME parameters from Reference; PHI retention on enquiries aligned with policy module.

---

## 14. Resolved Decisions

| # | Topic | Decision |
|---|--------|----------|
| 1 | Database | **Supabase** PostgreSQL via `DATABASE_URL` |
| 2 | Auth | **Auth technology domain** — local users + JWT v1; no external IdP day one |
| 3 | Recruiting | **Talent Tracker adapter-only** under Workforce `hiring/` |
| 4 | API path | **`services/api`** |
| 5 | M2 / backend | **Ignore M2** for backend; backoffice + CLI unchanged |
| 6 | Onboarding | **Single checklist** for all roles in v1 |
| 7 | EHR | **Mock adapter only** (`EHR_ADAPTER=mock`) |
| 8 | Encounter → claim | **Auto-create claim** on encounter complete (idempotent on `encounter_id`) |
| 9 | Audit store | **Supabase** append-only, same project as app data |
| 10 | HIPAA policies | **Code-first** in `domains/compliance/policies/` |
| 11 | Permissions | **Coarse roles only** in v1 |

---

## 15. Document History

| Date | Change |
|------|--------|
| 2026-05-28 | Initial `docs/architecture_proposal.md` from approved `architecture_proposal_plan.md` |

**Related:** Planning draft at repository root: `architecture_proposal_plan.md` (may be archived after team review).
