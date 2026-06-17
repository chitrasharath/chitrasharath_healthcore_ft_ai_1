# Plan: `docs/architecture_proposal.md`

Draft outline for review before writing the file. Grounded in memory-bank (12-clinic network, M1 intake, M2 operational logic, M3 recruiting API, M4 Next.js migration, existing monorepo with `apps/` + `uis/`).

---

## 1. Document purpose and audience

| Section | Content |
|--------|---------|
| **Title** | HealthCore Platform Architecture Proposal |
| **Purpose** | Target-state architecture for a FastAPI backend and its relationship to existing Next.js apps |
| **Scope** | Backend structure, API domains, frontend/backend boundaries; not a full infra/deployment runbook |
| **Audience** | Engineering, product, operations stakeholders |
| **Current state** | Brief snapshot: no FastAPI today; M2 logic in `apps/src` (TS); UIs in `uis/` and `apps/talent-pipeline-tracker`; M1 enquiry still client-only |

---

## 2. Recommended architectural pattern

**Primary recommendation: modular monolith (FastAPI) with domain-oriented modules**

| Pattern | Fit for HealthCore |
|---------|-------------------|
| **Modular monolith** | One deployable API service, modules bounded by **business** and **technology** domains (clinical, billing, auth, etc.). Matches milestone delivery and a small team. |
| **Layered within each domain** | `router` → `service` (business rules) → `repository` (persistence). Keeps FastAPI handlers thin. |
| **Not microservices (yet)** | 12 clinics, phased milestones—operational complexity does not justify many services until scale or team split demands it. |
| **Hexagonal / ports-adapters (light)** | Services depend on interfaces for DB/external systems; eases testing and future extraction of a domain. |

**Alignment with existing work**

- M2 TypeScript utilities in `apps/src` remain for **CLI, tests, and `uis/backoffice`** only—the **backend does not port or depend on M2**; business rules in `services/api` are implemented in Python per domain (see §8, §11).
- M3 Talent Pipeline = **external API** today; treat as **integration boundary** (BFF or dedicated recruiting module), not duplicate recruiting inside HealthCore API unless product requires consolidation.

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

---

## 3. Domain identification and separation criteria

Domains are grouped into **Business** (HealthCore operations) and **Technology** (platform capabilities). Both live under `app/domains/` with the same router → service → repository layering.

### All domains (catalog)

| Domain | Layer | API prefix | Primary responsibility |
|--------|-------|------------|-------------------------|
| **Reference** | Business | `/api/v1/reference` | Shared master data (locations, service types, enums) — **§3.1** |
| **Intake** | Business | `/api/v1/intake` | Public patient enquiries and callback workflow — **§3.2** |
| **Scheduling** | Business | `/api/v1/scheduling` | Appointments, visit planning, no-show metrics — **§3.3** |
| **Clinical** | Business | `/api/v1/clinical` | Encounters, notes, **EHR mock adapter** (v1) — **§3.4** |
| **Billing / RCM** | Business | `/api/v1/billing` | Claims (**auto from encounter**), denials, payer KPIs — **§3.5** |
| **Workforce** | Business | `/api/v1/workforce` | Clinician roster, hiring pipeline, onboarding — **§3.6** |
| **Compliance** | Business | `/api/v1/compliance` | **Supabase** audit log, CME, **code-first** HIPAA — **§3.7** |
| **Reporting** | Business | `/api/v1/reporting` | Cross-domain KPIs and exports (read-only orchestration) — **§3.8** |
| **Integrations** | Business (supporting) | *(no standalone public prefix)* | External adapters; embedded under Clinical & Workforce — **§3.9** |
| **Auth** | Technology | `/api/v1/auth` | Users, **coarse roles**, JWT issuance (see §3.10) |

### Business domains (full)

Derived from project brief and operational workflows across 12 clinics (backend rules are native Python—see §8, §11):

| Domain | Category | Responsibility | Primary entities / capabilities | Links to other domains |
|--------|----------|----------------|--------------------------------|-------------------------|
| **Reference** | Master data | Canonical codes and site metadata used by all domains | `Location`, `ServiceType`, shared enums (`ClaimStatus`, `AppointmentStatus`, etc.) | Read by Intake, Scheduling, Clinical, Billing, Workforce, Compliance, Reporting |
| **Intake** | Patient access | Structured **public** interest before a visit; no clinical documentation | Enquiries, enquiry status, callback queue; replaces mock submit on `uis/website` | → Scheduling (book appointment); Compliance (PHI policy + audit on submit); Auth optional for staff review routes |
| **Scheduling** | Visit operations | **When** the patient is expected; calendar and appointment lifecycle | `Appointment`, status transitions, no-show rates/costs | → Clinical; → Billing (no-show); ← Workforce |
| **Clinical** | Clinical Operations | **What happened** during care | `Encounter`, notes; **EHR mock adapter** (v1) | ← Scheduling; → Billing (**auto-claim**); → Compliance; ← Auth |
| **Billing / RCM** | Revenue cycle | **What we charge** | `Claim` (auto from encounter), denial KPIs | ← Clinical; ← Scheduling; ← Reference; ← Auth |
| **Workforce** | People operations | Hire → onboard → roster | Roster, **hiring pipeline** (Talent Tracker **adapter-only**), **single onboarding checklist** | → Clinical; → Compliance; ↔ talent-pipeline-tracker |
| **Compliance** | Regulatory | Controls & evidence | **Supabase audit log**; CME (Python); **code-first HIPAA** | ← Auth; ← Workforce; audits PHI domains |
| **Reporting** | Analytics | Weekly ops and executive **read models** across domains | Composed KPIs (denial, no-show, CME, intake volume); export jobs | Reads Scheduling, Billing, Compliance, Workforce, Reference; does not own source entities |
| **Integrations** | Supporting | Shared external connectivity patterns (not a product surface) | HTTP client config; webhook verification; adapter contracts | **EHR** implementations under `clinical/adapters/`; **Talent Tracker** under `workforce/adapters/`; service accounts via **Auth** |

### Domain details (all domains)

Full design notes below follow **operational order** (master data → patient flow → revenue → people → regulatory → analytics → adapters → platform auth). Summary tables above remain the quick reference.

| Domain | Section |
|--------|---------|
| Reference | §3.1 |
| Intake | §3.2 |
| Scheduling | §3.3 |
| Clinical | §3.4 |
| Billing / RCM | §3.5 |
| Workforce | §3.6 |
| Compliance | §3.7 |
| Reporting | §3.8 |
| Integrations | §3.9 |
| Auth (Technology) | §3.10 |

---

### 3.1 Reference domain (detail)

**Purpose:** Canonical **master data** and shared enums so Intake, Scheduling, Clinical, Billing, Workforce, Compliance, and Reporting use the same codes—no duplicated location lists or status strings per domain.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `locations/` | `Location`: id, name, country (US/UK), address, timezone, active flag; 12-clinic network alignment |
| `service_types/` | Billable / schedulable service catalog (codes, descriptions, default duration) |
| `enums/` | Re-export or mirror `app/schemas/enums.py`: `AppointmentStatus`, `ClaimStatus`, `EnquiryStatus`, payer flags, etc. |
| `router.py` | Read-heavy `GET` endpoints; admin `POST/PATCH` behind `admin` role only |

**Entities and rules**

- **Locations** are the scope key for most KPIs (`location_id` on appointments, claims, enquiries).
- **UK vs US** rules (payer sets, licence/CME parameters) read `Location.country`—Compliance and Billing parameterize calculators from Reference, not hard-coded strings.
- Reference **does not** own patients, appointments, or claims—only codes and site metadata.
- Writes are infrequent; cache-friendly reads OK in v1 (in-process cache or short TTL)—document invalidation on admin PATCH.

**API (v1 examples)**

- `GET /api/v1/reference/locations`, `GET /api/v1/reference/locations/{id}`
- `GET /api/v1/reference/service-types`
- Internal admin: `POST /api/v1/reference/locations` (seed + admin maintenance)

**Links**

| Domain | Rule |
|--------|------|
| All business domains | Read via `ReferenceService`—no cross-domain SQL to `locations` table |
| Intake | Enquiry `preferred_location_id` must validate against active locations |
| Reporting | Dimension keys for location/payer breakdowns |

**Auth:** Public read of active locations optional for website dropdowns; admin writes require `admin`.

---

### 3.2 Intake domain (detail)

**Purpose:** Structured **public patient interest** before a visit—replaces client-only mock submit on `uis/website`; no clinical documentation or billing.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `enquiries/` | `Enquiry` CRUD: contact fields, preferred location/service, status, source, created_at |
| `callback_queue/` | Staff-facing queue views (filter by status, location, age) |
| `router.py` | Public create + internal list/update |

**Entities**

- `Enquiry`: PII fields (name, phone, email, message, language preference, appointment preferences); `status` (`new`, `contacted`, `scheduled`, `closed`); optional link `appointment_id` once Scheduling books.
- **No** `Encounter`, `Claim`, or clinical note types in this domain.

**API (v1)**

- `POST /api/v1/intake/enquiries` — public (rate-limited); body validated with Pydantic `extra="forbid"`; returns id + acknowledgment only (no internal fields).
- `GET /api/v1/intake/enquiries` — internal (`front_desk`, `admin`); filters: `status`, `location_id`, date range.
- `PATCH /api/v1/intake/enquiries/{id}` — status transitions, assignee notes (metadata only, not clinical notes).

**Frontend**

- `uis/website` `/enquiry-form` → **Next server route** proxies to `POST /intake/enquiries` (no browser JWT, minimal CORS)—see §7.
- Validation: port rules from `uis/website/lib/enquiry-validation.ts`; API is authoritative on submit.

**Compliance & Auth**

- **Compliance** `PolicyEnforcer` on POST (retention, purpose of use) + **audit** `intake.enquiry.created` (resource id only, no full body in audit payload).
- **Auth** optional on public POST; required on staff queue routes.

**Links**

| Domain | Rule |
|--------|------|
| → Scheduling | Staff converts enquiry → `Appointment` (stores `enquiry_id` optional) |
| Reference | Validate `preferred_location_id`, service type codes |
| Clinical / Billing | **No** direct imports |

---

### 3.3 Scheduling domain (detail)

**Purpose:** **When** the patient is expected—appointment calendar and lifecycle; not clinical content or claim status.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `appointments/` | `Appointment`: patient/enquiry reference, `location_id`, `clinician_id`, `service_type_id`, `scheduled_at`, `status` |
| `metrics/` | No-show rates/cost helpers (native Python KPIs for API/Reporting—not M2 port) |
| `router.py` | List/filter appointments; PATCH status |

**Entities**

- `Appointment.status`: e.g. `scheduled`, `checked_in`, `completed`, `cancelled`, `no_show`—enum in Reference-aligned schemas.
- Required links: `location_id`; `clinician_id` must reference **active** Workforce clinician when assigned.
- Optional: `enquiry_id`, `patient_id` (define patient identity model in Intake or shared `patients` table owned by Intake/Reference—document in final proposal).

**API (v1)**

- `GET /api/v1/scheduling/appointments` — filters: `location_id`, `status`, `clinician_id`, date range.
- `POST /api/v1/scheduling/appointments` — staff create (from enquiry or walk-in).
- `PATCH /api/v1/scheduling/appointments/{id}/status` — transitions; **checked_in** triggers Clinical to open/link encounter (service call, not router cross-import).
- `GET /api/v1/scheduling/metrics/no-show` — KPI endpoint (query params: location, window).

**Boundaries**

- Scheduling **does not** store note text, EHR external ids, or `Claim` rows.
- On **encounter complete**, Clinical service updates appointment to `completed` (see §3.4 / linking).
- **No-show** without encounter: metrics consumed by Billing KPIs / Reporting—no Clinical write.

**Auth & Compliance**

- PHI routes: `front_desk`, `clinician`, `admin` (coarse roles); Compliance enforcer on read/write lists with patient context.

**Links:** → Clinical (`appointment_id`); → Billing (no-show metrics); ← Workforce (active clinicians); ← Reference.

---

### 3.4 Clinical Operations domain (detail)

**Purpose:** Own everything that happens **during and after the patient is seen**—distinct from Scheduling (booking a slot) and Billing (getting paid).

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `encounters/` | Encounter lifecycle: opened from appointment, in-progress, completed, cancelled; links `patient_id`, `appointment_id`, `location_id`, `clinician_id` |
| `notes/` | Clinical documentation: progress notes, SOAP, attachments metadata; versioning and author; **never** on public Intake routes |
| `adapters/` | **EHR integration** — mock (v1) and future vendor modules; maps external IDs to HealthCore IDs |

**Entities**

- `Encounter`: required `appointment_id` when visit is scheduled; `clinician_id` from active Workforce roster; `status` drives Scheduling sync and Billing trigger.
- `ClinicalNote`: author `user_id`, encounter link, metadata + body storage policy (DB vs EHR-synced on read).

**API (v1)**

- `GET/POST /api/v1/clinical/encounters`, `GET /api/v1/clinical/encounters/{id}`
- `PATCH /api/v1/clinical/encounters/{id}/status` — **completed** emits in-process `EncounterCompleted` → Billing auto-claim (idempotent on `encounter_id`)
- `POST /api/v1/clinical/encounters/{id}/notes`, `GET .../notes` — Compliance audit on view/create
- `POST /api/v1/clinical/encounters/{id}/ehr-sync` — internal; invokes mock adapter
- `GET /api/v1/clinical/integrations/ehr/health` — adapter health (internal)

**EHR adapter pattern (ports & adapters)**

- `EhrAdapter` protocol in `adapters/base.py`: `get_patient`, `pull_encounter`, `push_note`, `sync_document`, health check.
- **v1: mock only** (`EHR_ADAPTER=mock`)—see §11.
- Injected via `core/dependencies.py`; vendor JSON never leaks into Billing routers.
- Adapter failures may log `ehr.sync` to Compliance audit—distinct from HIPAA `PolicyEnforcer`.

**Boundaries**

- Clinical **does not** set `Claim.status` or denial rules; provides billable snapshot to Billing on complete.
- Only **Billing** may call `ClinicalService.get_encounter_summary` read-only for appeals.

**Auth & Compliance:** `clinician`, `admin`; PolicyEnforcer on all note/encounter routes; audit `clinical.note.viewed` etc.

**Links:** ← Scheduling, Workforce, Auth; → Billing (auto-claim), Compliance (audit).

---

### 3.5 Billing / RCM domain (detail)

**Purpose:** **What we charge** and payer outcomes—claims lifecycle, denial KPIs, payer/location flags; does not own clinical documentation.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `claims/` | `Claim` CRUD, status transitions, link `encounter_id`, `appointment_id`, `patient_id`, payer, amounts, denial reason |
| `metrics/` | Denial rates, high-denial payer flags, thresholds (native Python—not M2 port) |
| `router.py` | Claims list/detail; KPI subpaths; no clinical note routes |

**Entities**

- `Claim`: created **automatically** on `EncounterCompleted` via `BillingService.create_claim_from_encounter` (**idempotent** on `encounter_id`); initial status e.g. `draft` → `submitted` → `paid` / `denied`.
- `Claim` may exist for no-show paths sourced from Scheduling metrics without an encounter—separate creation rules, no auto-encounter link.

**API (v1)**

- `GET /api/v1/billing/claims` — filters: `location_id`, `status`, `payer_name`, date range
- `GET /api/v1/billing/claims/{id}`
- `PATCH /api/v1/billing/claims/{id}` — status and denial fields (**only Billing** mutates `Claim.status` after rules)
- `GET /api/v1/billing/denial-rates`, `GET /api/v1/billing/payers/high-denial?threshold=8` — analytics subpaths
- **No** public `POST /claims` for v1 patient flows—create via Clinical event or internal admin exception documented in service

**Auto-claim (decided)**

- On encounter complete: Billing receives billable snapshot (service types, codes from encounter/Reference); creates claim if none exists for `encounter_id`.
- Clinical service **does not** implement denial logic or payer submission.

**Auth & Compliance**

- `billing_analyst`, `admin`; Compliance audit on claim view/export; HIPAA policies **not** implemented inside `billing/service.py`—use `PolicyEnforcer`.

**Links:** ← Clinical (auto-create), Scheduling (no-show KPIs), Reference (payer/location enums); → Compliance (audit); → Reporting (KPIs).

---

### 3.6 Workforce domain (detail)

**Purpose:** End-to-end **people ops** for clinicians and clinical staff—from candidate pipeline through onboarding to active roster—not regulatory audit/CME (those stay in **Compliance**).

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `clinicians/` | Active roster: CRUD/read `Clinician` master data (role, `location_id`, licence dates, CME hour fields on record); status `active` \| `inactive` |
| `hiring/` | **Hiring pipeline**: candidates, stage transitions (e.g. applied → screen → interview → offer → hired), requisitions by location/role; links to external `talent_candidate_id` when synced from Talent Tracker |
| `onboarding/` | **Onboarding**: checklist/tasks after offer accepted (licence verification, HR paperwork, system access, initial CME baseline) until clinician promoted to `active` roster |
| `adapters/` (optional) | `TalentTrackerAdapter` — pull/push candidate updates; used by `hiring/` only |

**Hiring pipeline**

- Align stages with Milestone 3 **Talent Pipeline Tracker** semantics where possible (same stage names/enums in shared schemas or OpenAPI).
- **Default:** `apps/talent-pipeline-tracker` remains the primary recruiting UI; HealthCore API **Workforce** exposes hiring endpoints for internal HR dashboards and for **server-side sync** (webhook or poll via Talent Tracker adapter).
- Workforce **owns** hiring state inside HealthCore DB for reporting across clinics; adapter keeps external system in sync—do not fork candidate logic into Billing/Clinical.
- On transition to **hired**: create onboarding record; do not create full `Clinician` as `active` until onboarding completes.
- **Recruiting integration (decided):** **Talent Tracker adapter-only** under `workforce/hiring/`—HealthCore stores hiring state for reporting; primary UI remains `apps/talent-pipeline-tracker`; no duplicate full pipeline in Billing/Clinical.

**Onboarding**

- `OnboardingCase` keyed to pending `clinician_id` (draft) or `candidate_id` → final `clinician_id` on completion.
- **Single onboarding checklist** for all roles in v1 (same task template; no per-`ClinicianRole` variants until a later phase)—see §11.
- Tasks: licence upload, background check flag, orientation, EHR provisioning ticket (template shared across hires).
- Completion triggers: activate clinician on roster, emit event for **Compliance** (audit `workforce.onboarding.completed`), optional **Clinical** scheduling eligibility.
- **Compliance** runs CME/at-risk only after clinician is on roster with logged hours—onboarding may set initial `cmeHoursRequired` / `cmeHoursLogged` via Workforce PATCH, not via Compliance writes.

**Workforce ↔ Talent Tracker (M3)**

| Approach | When |
|----------|------|
| **Adapter in `workforce/adapters/`** | API needs candidate list/detail from Talent Tracker contract |
| **Event on hire** | `POST /workforce/onboarding` created from webhook or manual “mark hired” in pipeline |
| **UI split** | Recruiters keep using `apps/talent-pipeline-tracker`; ops HR uses future internal portal calling `/api/v1/workforce/hiring` |

**Workforce ↔ Compliance ↔ Clinical**

| Link | Rule |
|------|------|
| **Workforce → Compliance** | Compliance reads clinicians for CME; onboarding completion may trigger Compliance audit event |
| **Workforce → Clinical** | Only `active` clinicians with valid licence dates appear in encounter attribution picklists |
| **Compliance → Workforce** | No hiring/onboarding writes; policy enforcer may gate `/workforce/*` HR routes |

**API (v1)**

- `GET/PATCH /api/v1/workforce/clinicians`, `GET /api/v1/workforce/clinicians/{id}`
- `GET/POST /api/v1/workforce/hiring/candidates`, `PATCH /api/v1/workforce/hiring/candidates/{id}/stage`
- `GET/POST /api/v1/workforce/onboarding`, `PATCH /api/v1/workforce/onboarding/{id}/tasks`
- Adapter sync endpoints internal only (webhook or job)—not public website

**Auth:** `hr_recruiter`, `admin` for hiring; `admin` for roster PATCH; Compliance reads roster via service interface.

---

### 3.7 Compliance domain (detail)

**Purpose:** Central place for **regulatory operations** that apply across HealthCore—not duplicated inside Clinical, Billing, or Workforce routers.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `audit/` | Append-only **audit log**: who (`user_id` / service principal), what (`action`, `resource_type`, `resource_id`), when (`occurred_at`), context (`ip`, `request_id`, `domain`, `outcome`). Immutable store; no update/delete via API. |
| `cme/` | **CME tracking**: native Python rules in Compliance (not ported from M2); reads clinician records via **WorkforceService**; stores compliance snapshots or computes on read per performance needs. |
| `policies/` | **HIPAA policy enforcement**: policy definitions (minimum necessary, role-based access to PHI routes, retention flags); evaluators used by dependencies/middleware—not business rules scattered in handlers. |
| `licensing/` (optional) | Licence expiry alerts tied to `clinician_id`; may merge with `cme/` if small |

**Audit log — how it works**

- **`app/core/audit_middleware.py`** (or dependency) captures mutating and sensitive **read** requests on PHI routes; calls `ComplianceService.record_audit_event(...)`.
- Domains may emit explicit events for domain actions (e.g. `clinical.note.viewed`, `billing.claim.denied`)—single writer path through Compliance repository.
- Fields: never store full note body or SSN in audit payload; use resource IDs and action verbs only.
- Retention and export for compliance officers: `GET /api/v1/compliance/audit-events` (internal, heavily authorized).

**CME tracking — split from Workforce**

| Concern | Owner |
|---------|--------|
| Clinician record (`cmeHoursRequired`, `cmeHoursLogged`, licence dates) | **Workforce** (master data) |
| CME report generation, at-risk/overdue classification, expiry windows | **Compliance** (native Python calculators; align with ops expectations, not `apps/src` parity) |
| Encounter attribution (`clinician_id` on encounter) | **Clinical** (references Workforce ID) |

**HIPAA policy enforcement**

- **`PolicyEnforcer`** dependency injected on routers touching PHI: Intake (enquiry PII), Scheduling (appointments), Clinical (notes/encounters), Billing (claims with patient context).
- **Code-first** policy definitions in `domains/compliance/policies/` (not external OPA/IAM in v1)—see §11.
- Checks: runs **after Auth** has established identity; enforces HIPAA rules (minimum necessary, purpose of use, break-glass with mandatory audit entry)—**not** a replacement for Auth coarse roles.
- Policies live in `domains/compliance/policies/` (config/code); changing a policy does not require editing Clinical/Billing services—only enforcer rules and tests.
- Public `uis/website` routes proxy through Next server; API still enforces policy on Intake POST even without browser CORS.

**Compliance ↔ other domains (summary)**

| Link | Rule |
|------|------|
| **Compliance → all PHI domains** | Middleware/dependencies run **before** handler; deny with 403 + audit `policy.denied` |
| **Compliance → Workforce** | Read clinicians for CME; Workforce does not write audit rows |
| **Clinical → Compliance** | Note view/create triggers audit; EHR adapter may log `ehr.sync` events to Compliance |
| **Billing → Compliance** | Claim view/export audited; no HIPAA policies implemented inside `billing/service.py` |
| **Reporting → Compliance** | May read aggregated audit stats; not raw note content |

**API (v1)**

- `GET /api/v1/compliance/audit-events` — filtered export (`compliance_officer`, `admin`); immutable store
- `GET /api/v1/compliance/cme/reports`, `GET .../cme/clinicians/at-risk`, `GET .../cme/clinicians/expiring-licences`
- `GET /api/v1/compliance/policies` — internal policy metadata (code-first module)

**Persistence:** Audit tables in **same Supabase project** as app data—append-only, no UPDATE/DELETE via API (§11).

---

### 3.8 Reporting domain (detail)

**Purpose:** **Read-only orchestration** of cross-domain KPIs for weekly ops and executive views—does not own source entities (claims, appointments, clinicians).

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `kpis/` | Composed metrics: denial rates, no-show cost/rates, CME summary, intake volume by location |
| `exports/` | Optional CSV/JSON export jobs (async later); v1 may be synchronous `GET` only |
| `router.py` | Read endpoints only—no writes to Clinical, Billing, or Workforce tables |

**Design rules**

- Reporting **calls domain services** (`BillingService.get_denial_summary`, `SchedulingService.get_no_show_metrics`, `ComplianceService.get_cme_report`, etc.)—no cross-domain SQL in `reporting/repository.py`.
- Aggregates that need appointment + encounter + claim belong here (or a dedicated `GET /reporting/visit-outcomes/{appointment_id}` read model)—not embedded in single-domain CRUD unless UX requires it.
- Numbers are **Python-native** implementations; parity with `apps/src` M2 or `uis/backoffice` manual tests is **not** guaranteed (§8).

**API (v1)**

- `GET /api/v1/reporting/kpis/weekly` — query: `location_id`, `week_start`, optional metric toggles
- Future: `GET /api/v1/reporting/exports/{job_id}` when async exports added

**Auth:** `read_only_ops`, `billing_analyst`, `admin`, `compliance_officer` (coarse roles per metric family).

**Links:** Reads Scheduling, Billing, Compliance, Workforce, Reference, Intake (volume); never writes; may read aggregated audit stats from Compliance, not raw notes.

---

### 3.9 Integrations domain (detail)

**Purpose:** Shared **external connectivity patterns**—not a standalone product API prefix. Concrete adapters live under Clinical and Workforce; Integrations provides contracts and shared HTTP utilities.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `contracts/` | Shared protocols: webhook signature verification, retry policy interfaces, correlation ids |
| `http/` | Configured async HTTP client (timeouts, retries base); used by domain adapters only |
| `webhooks/` | Optional central webhook ingress that dispatches to domain handlers (EHR mock, Talent Tracker) |

**Embedded adapters (not under `domains/integrations/` tree alone)**

| Adapter | Location | v1 |
|---------|----------|-----|
| **EHR** | `domains/clinical/adapters/` | **Mock only** |
| **Talent Tracker** | `domains/workforce/adapters/` (hiring) | Sync candidates; primary UI `apps/talent-pipeline-tracker` |

**Service accounts**

- Webhooks and poll jobs authenticate via **Auth** service principals or API keys (`TALENT_TRACKER_API_KEY`, `EHR_*` secrets)—never in frontends.

**Rules**

- No business PHI stored in Integrations module—only transport, auth headers, and mapping helpers.
- Vendor payload shapes stop at adapter boundary (anti-corruption layer into domain Pydantic schemas).

---

### 3.10 Auth domain (Technology — detail)

**Purpose:** Single place for **who** calls the API and whether their **coarse role** allows the route—before Compliance applies HIPAA-specific rules.

| Submodule / folder | Responsibility |
|--------------------|----------------|
| `users/` | Staff accounts; link to Workforce `clinician_id` / HR identity where applicable |
| `roles/` | Named coarse roles (`admin`, `billing_analyst`, `clinician`, `front_desk`, `hr_recruiter`, `compliance_officer`, `read_only_ops`) |
| `permissions/` | *(Deferred v1)* Fine-grained `resource.action` |
| `tokens/` | JWT issuance, validation, optional denylist |
| `router.py` | `/auth/login`, `/auth/refresh`, `/auth/logout`, `GET /me` only |

**JWT issuance**

- `POST /api/v1/auth/login` → `access_token` (+ optional `refresh_token`), type `bearer`.
- Claims: `sub`, `roles[]`, `exp`, `iat`, optional `location_scope[]`—**coarse roles only** (§11).
- `POST /api/v1/auth/refresh` — rotate access token when enabled.
- Signing: `JWT_SECRET` or key pair; document rotation.
- Routes use `Depends(get_current_user)` / `require_role(...)` via **AuthService** in `core/dependencies.py`.

**JWT implications (design consequences)**

| Topic | Implication for HealthCore |
|-------|---------------------------|
| **Stateless validation** | Signature + `exp` per request; logout/revocation needs short TTL, refresh rotation, and/or denylist |
| **Signing keys** | Server-only; leak = forged tokens; plan key rotation |
| **Payload visibility** | Signed, not encrypted—no PHI in claims |
| **Stolen token** | Short access TTL, HTTPS, prefer httpOnly cookie for internal UIs |
| **Stale roles** | DB role changes lag until refresh/expiry—critical for offboarding |
| **Revocation (v1)** | Recommend short access TTL + refresh rotation + optional denylist on logout |
| **Compliance boundary** | Auth → Compliance `PolicyEnforcer` → handler → audit (`sub` in audit, not raw JWT) |
| **Service accounts** | EHR/Talent Tracker webhooks use API key or scoped JWT |
| **Phased dependency** | Auth/JWT before PHI domains in rollout |

**v1 defaults:** access TTL 15–60 min; refresh days with rotation; RS256 preferred in production.

**Roles vs permissions:** Roles only in v1; permissions deferred.

**Auth ↔ Compliance:** Auth = identity + coarse route role; Compliance = HIPAA policy on PHI routes.

**Auth ↔ frontends:** Website mostly anonymous; backoffice/dashboards Bearer or server-set cookie; Talent Tracker maps to HealthCore user or service account.

**`core/security.py`:** Thin wrappers → `domains/technology/auth/service.py`.

### Technology domains (summary)

| Domain | Category | Responsibility |
|--------|----------|----------------|
| **Auth** | Identity & access | Users, coarse roles, JWT—see §3.10 |

---

### Cross-domain linking: Clinical ↔ Scheduling ↔ Billing

Use **shared identifiers** and **domain service calls**—not shared database tables across modules.

```
  Scheduling              Clinical                      Billing
  ┌─────────────┐         ┌─────────────┐               ┌─────────┐
  │ Appointment │────────►│  Encounter  │──────────────►│  Claim  │
  └─────────────┘         │      │      │               └─────────┘
       │                  │      ├──────► Clinical Note       ▲
       │                  │      │                          │
       │                  │  EHR Adapter ~~sync~~► Encounter │
       │                  └─────────────┘                    │
       │                                                    │
       └──────── no_show (no encounter) ────────────────────┘

  encounter_id + service_type + codes on auto-claim path
```

| Link | Direction | Rule |
|------|-----------|------|
| **Scheduling → Clinical** | Appointment spawns or links Encounter | On check-in / start visit: Clinical creates `Encounter` with required `appointment_id` (1:1 or 1:0 if walk-in rules allow null). Scheduling **does not** store note text or EHR external IDs. |
| **Clinical → Scheduling** | Status alignment | When encounter completes, Clinical calls **Scheduling service** to set appointment `completed`; when cancelled at door, coordinate `cancelled` / no-show per policy. |
| **Clinical → Billing** | Billable context + **auto-claim** | On encounter complete, emit billable snapshot; **Billing auto-creates Claim** with `encounter_id` + `appointment_id` + `patient_id` (event handler or `BillingService.create_claim_from_encounter`)—no manual billing queue in v1. Clinical **does not** set `Claim.status` or denial logic. |
| **Scheduling → Billing** | No-show path | No-show appointments without an encounter feed no-show KPIs—Billing/Reporting reads Scheduling (+ Reference), not Clinical notes. |
| **Billing → Clinical** | Read-only reference | Billing may fetch encounter **summary** via `ClinicalService.get_encounter_summary(encounter_id)` for denial appeals; no writes to notes or EHR. |

**Implementation rules (monolith)**

1. **Foreign keys as IDs only** — `appointment_id`, `encounter_id`, `patient_id` on schemas; enforce referential integrity in application layer or DB constraints with clear owning table per domain.
2. **No cross-domain repository imports** — `billing/repository.py` must not query `clinical_notes` table; use `ClinicalService` interface injected into `BillingService`.
3. **In-process events (v1)** — `EncounterCompleted` → **`BillingService.create_claim_from_encounter`** (auto-create claim; idempotent on `encounter_id`)—keeps routers thin; document ordering/retries.
4. **API surface** — Cross-domain links appear in JSON (`encounter.appointment_id`, `claim.encounter_id`); nested aggregates (appointment + encounter + claim) belong in **Reporting** or a dedicated read endpoint, not buried inside single-domain CRUD unless needed for UX.
5. **EHR is source of truth for notes (when integrated)** — HealthCore stores encounter header + note metadata; full note body may sync from EHR adapter on read; document conflict resolution in final proposal.

**Scheduling vs Clinical boundary (one line for the doc):** Scheduling answers *when*; Clinical answers *what happened clinically*; Billing answers *what we charge*; **Compliance** answers *who may access what and what we must record*; **Workforce** answers *who we are hiring, how we onboard them, and who is on the clinical roster*.

**Separation criteria** (when to split modules vs merge)

1. **Bounded context** — Entity lifecycle owned in one place (e.g. only Billing mutates `Claim.status` after business rules). **Technology** domains (Auth) do not own clinical or billing entities.
2. **Change frequency** — Billing rules change weekly; Reference data changes rarely.
3. **Audience** — Public Intake vs internal Billing/Workforce/Compliance (auth and rate limits differ).
4. **Regulatory sensitivity** — PHI/PII in **Intake, Clinical, Scheduling, Billing**; **Compliance** owns cross-cutting audit retention, CME regulatory reporting, and HIPAA enforcement—not reimplemented per domain.
5. **Reuse without coupling** — Reference data read by many domains via service interfaces, not direct cross-module DB access.

**Anti-pattern to call out:** “God module” `operations` that bundles unrelated domain endpoints in one router—use domain routers instead.

---

## 4. Proposed repo layout (monorepo extension)

**Recommendation: stay in current monorepo** (consistent with `apps/README.md`), add backend as a first-class app:

```
healthcore-monorepo/
├── services/
│   └── api/                     # DECIDED: FastAPI + Pydantic (uv project root)
│       ├── pyproject.toml
│       ├── uv.lock
│       ├── .python-version
│       └── app/
├── apps/
│   ├── src/                     # M2 TS utilities (CLI, tests, backoffice only—not backend)
│   ├── talent-pipeline-tracker/
│   └── healthcore_web_portal/   # legacy
├── uis/
│   ├── website/
│   └── backoffice/
├── docs/
│   └── architecture_proposal.md
└── memory-bank/
```

**No separate Python workspace members** — one `services/api` project keeps FastAPI routes, services, and schemas in one tree and one lockfile.

**Alternative (document, not recommend initially):** separate API repo—only if compliance or release cadence forces split.

---

## 5. FastAPI backend folder and module structure

### Python package management: [uv](https://docs.astral.sh/uv/) (single project)

Use **uv** for one Python project at **`services/api/`** only—no uv workspace, no extra members, no shared schema package elsewhere in the monorepo.

| Concern | Approach |
|---------|----------|
| **Project root** | `services/api/pyproject.toml` — sole `[project]` definition |
| **Lockfile** | `services/api/uv.lock` committed alongside the app |
| **Python version** | `services/api/.python-version` (e.g. `3.12`) + `requires-python` in `pyproject.toml` |
| **Virtual env** | `cd services/api && uv sync`; CI uses `uv sync --frozen` in that directory |
| **Run commands** | `uv run uvicorn app.main:app --reload`, `uv run pytest`, `uv run alembic upgrade head` |
| **Add dependency** | `uv add fastapi pydantic-settings` (dev: `uv add --dev pytest ruff mypy`) |

**Why one directory (not multiple uv members)**

- FastAPI routers, services, and **Pydantic schemas** stay importable as normal Python modules under `app/` without cross-package publishing or `{ workspace = true }` wiring.
- OpenAPI is generated from the same codebase that defines the models—no drift between `services-api` and a separate schemas package.
- TypeScript clients for Next.js apps (optional) can still be generated from `/openapi.json` into `uis/*` or a JS `packages/api-client` folder—that is **not** a Python uv member.

**CI / docs commands to standardize**

```bash
cd services/api
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Optional root `Makefile` target: `make api-test` → runs the above. See **§5.1** for PEP 8, FastAPI, and Pydantic conventions.

**Python toolchain:** use **uv only** for `services/api` and `uis/incident_analyzer` CLI — committed lockfiles (`services/api/uv.lock`, `uis/incident_analyzer/uv.lock`), `uv sync`, and `uv run …`. Do not add `requirements.txt` or manual `python3 -m venv` workflows.

### Pydantic & FastAPI schema layout (same app)

| Location | Contents |
|----------|----------|
| `app/schemas/` | **Shared** Pydantic models: pagination, common IDs, domain enums (aligned with Reference), coarse **role** names, error bodies |
| `app/domains/<domain>/schemas.py` | **Domain** request/response models: `ClaimCreate`, `EncounterRead`, `EnquiryCreate`, etc. |
| `app/domains/<domain>/models.py` or `app/db/models/` | ORM entities (if used)—**never** exposed directly as API responses |
| OpenAPI | Auto-generated from FastAPI + Pydantic in this app; export for frontend codegen when needed |

Import rule: domains import shared types from `app.schemas.*`; domains do not import each other’s `schemas.py`—use service interfaces for cross-domain data.

Proposed tree for `services/api/` (FastAPI + Pydantic v2 + pydantic-settings; **all** Python backend code here):

```
services/api/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── README.md
├── alembic/
├── tests/
│   ├── unit/
│   └── api/
└── app/
    ├── main.py                 # FastAPI app factory, lifespan, mount routers
    ├── core/
    │   ├── config.py           # Settings (BaseSettings)
    │   ├── dependencies.py     # DB session; get_current_user, require_role; PHI: PolicyEnforcer
    │   ├── exceptions.py       # HTTP exception handlers
    │   ├── middleware.py       # CORS, request ID, logging
    │   ├── audit_middleware.py # delegates to Compliance audit (PHI routes)
    │   └── security.py         # thin wrappers → Auth domain (JWT validate)
    ├── api/
    │   └── v1/
    │       ├── router.py
    │       └── health.py
    ├── schemas/                  # shared Pydantic models (cross-domain)
    │   ├── common.py             # pagination, IDs, dates
    │   ├── enums.py              # domain enums (Reference-aligned)
    │   └── errors.py
    └── domains/
        ├── technology/
        │   └── auth/             # users, coarse roles, JWT issuance
        │       ├── router.py
        │       ├── schemas.py
        │       ├── service.py
        │       ├── repository.py
        │       ├── users/
        │       ├── roles/
        │       └── permissions/
        ├── reference/
        │   ├── router.py
        │   ├── schemas.py        # Pydantic request/response
        │   ├── service.py
        │   └── repository.py
        ├── intake/
        ├── scheduling/
        ├── clinical/
        │   ├── router.py
        │   ├── schemas.py
        │   ├── service.py
        │   ├── repository.py
        │   ├── encounters/       # encounter lifecycle (optional package)
        │   ├── notes/            # clinical documentation (optional package)
        │   └── adapters/         # EHR integration (required)
        │       ├── base.py       # EhrAdapter protocol
        │       ├── mock.py
        │       └── ...           # vendor-specific modules
        ├── billing/
        ├── workforce/
        │   ├── router.py
        │   ├── schemas.py
        │   ├── service.py
        │   ├── repository.py
        │   ├── clinicians/       # active roster
        │   ├── hiring/           # hiring pipeline
        │   ├── onboarding/       # post-offer onboarding
        │   └── adapters/         # optional Talent Tracker adapter
        ├── compliance/
        │   ├── router.py
        │   ├── schemas.py
        │   ├── service.py
        │   ├── repository.py
        │   ├── audit/            # append-only audit log
        │   ├── cme/              # CME tracking (native Python)
        │   └── policies/         # HIPAA rules + PolicyEnforcer
        └── reporting/            # optional
```

**Layer rules**

| Layer | Responsibility |
|-------|----------------|
| `router.py` | HTTP only: path, status codes, call service, map to response schema |
| `schemas.py` | Pydantic models: `*Create`, `*Update`, `*Read`, filters, pagination |
| `service.py` | Business rules, orchestration, validation (native Python—not `apps/src` M2) |
| `repository.py` | DB queries; no business rules |
| `models.py` (per domain or `db/`) | SQLAlchemy / DB models if ORM used |

**Configuration (`core/config.py`)**

- `Settings` via `pydantic-settings`: `APP_ENV`, **`DATABASE_URL` (Supabase Postgres)**, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (optional), `CORS_ORIGINS`, `API_V1_PREFIX`, JWT and adapter secrets
- **Persistence:** Supabase PostgreSQL for domain tables; **Compliance audit log** in the **same Supabase project** (append-only table + RLS/immutability policies)—see §11
- Load from `.env`; never commit secrets
- Separate `Settings` subsets only if needed (e.g. `TestSettings`)

**Pydantic practices (summary)** — expanded in **§5.1**.

---

### 5.1 Python, FastAPI, and Pydantic best practices

Standards for all code under `services/api/`. Enforce in CI; document in `services/api/README.md` when the project is scaffolded.

#### Style and layout (PEP 8 and tooling)

| Topic | Practice |
|-------|----------|
| **PEP 8** | Follow [PEP 8](https://peps.python.org/pep-0008/) for layout, naming, imports, and whitespace. Use **4 spaces**, no tabs; **88-character** line length (Ruff default, compatible with Black). |
| **Linter / formatter** | **[Ruff](https://docs.astral.sh/ruff/)** as the single tool: `ruff check` (pycodestyle/pyflakes/isort rules + selected flake8 plugins) and `ruff format` (Black-compatible). Do not add separate Black + isort + flake8 unless a rule truly requires it. |
| **Import order** | Stdlib → third party → `app.*` (isort via Ruff). No wildcard imports (`from x import *`). |
| **Naming** | `snake_case` modules/functions/variables; `PascalCase` classes; `UPPER_SNAKE` constants. Domain packages match domain names (`clinical`, `billing`). |
| **Type hints** | [PEP 484](https://peps.python.org/pep-0484/) on all public functions and service/repository methods; prefer `list[str]`, `dict[str, Any]` (3.9+) over `List`/`Dict` from `typing` unless needed for forward refs. |
| **Docstrings** | [PEP 257](https://peps.python.org/pep-0257/) on public modules and non-obvious service methods; one-line summary for routers is enough when behavior is obvious from types and route name. |
| **Optional static check** | `mypy` or `pyright` in CI on `app/` (strict gradually per domain)—catches drift between Pydantic models and service signatures. |

**CI baseline (extend §5 uv block)**

```bash
cd services/api
uv run ruff check .
uv run ruff format --check .
uv run pytest
# optional: uv run mypy app
```

#### Project layout and imports

- Keep **one responsibility per module**; if `service.py` grows past ~300 lines, split by sub-resource (`encounters/service.py`, `notes/service.py`) not by layer duplication.
- **No circular imports** between domains: cross-domain calls go through explicit service interfaces or small `app/events` handlers, not `from app.domains.billing.schemas import ...` in Clinical.
- **Absolute imports** only (`from app.domains.clinical.service import EncounterService`).
- **Secrets and PHI**: never log tokens, passwords, full enquiry payloads, or clinical note bodies; use structured logging with request ID and resource IDs only.

#### Layer discipline (reinforces §5 layer rules)

| Layer | Do | Don't |
|-------|-----|--------|
| `router.py` | Parse path/query/body into Pydantic models; call `service`; return `response_model` | SQL, business rules, direct ORM commits |
| `schemas.py` | Validation, serialization, OpenAPI shapes | DB access, HIPAA policy decisions |
| `service.py` | Rules, orchestration, call repositories/adapters | Raw SQL strings in routers |
| `repository.py` | Queries, transactions, mapping ORM → domain types | HTTP concepts, JWT checks |

#### Pydantic v2 practices

| Topic | Practice |
|-------|----------|
| **Version** | Pydantic **v2** only (`model_validate`, `model_dump`, not v1 `parse_obj` / `.dict()`). |
| **API vs persistence** | **Never** return SQLAlchemy (or raw dict) rows as API responses. Use `*Create`, `*Update`, `*Read` (and `*Filter`) in `schemas.py`; map ORM with `ModelRead.model_validate(orm_obj)` and `model_config = ConfigDict(from_attributes=True)`. |
| **Field definitions** | Use `Field(..., description=..., ge=..., max_length=...)` for constraints that belong in the contract; put cross-field rules in `@model_validator(mode="after")`. |
| **Enums** | `str, Enum` in `app/schemas/enums.py` (Reference-aligned); reuse in domain schemas—do not duplicate string literals for status fields. |
| **Immutability** | Prefer frozen read models where updates are not needed (`model_config = ConfigDict(frozen=True)` on `*Read` if helpful). |
| **Settings** | `pydantic-settings` `BaseSettings` with explicit field types; validate `DATABASE_URL` and JWT settings at startup—fail fast in `lifespan` if misconfigured. |
| **Partial updates** | `*Update` models with optional fields (`field: str \| None = None`) or dedicated `Patch*` schemas; avoid reusing `*Create` for PATCH. |
| **JSON schema / OpenAPI** | Set `json_schema_extra` examples on public request bodies (Intake enquiry) for `/docs` clarity. |
| **Datetime** | Store UTC in DB; expose ISO-8601 with timezone in API (`datetime` fields, not naive local strings). |

#### FastAPI practices

| Topic | Practice |
|-------|----------|
| **App factory** | `create_app()` in `main.py` with `lifespan` for DB pool and settings; mount `api/v1/router.py` once. |
| **Routers** | One `APIRouter` per domain; `tags=[...]` and `prefix` on mount for OpenAPI grouping (see §6). |
| **Dependencies** | `Depends(get_db)`, `Depends(get_current_user)`, `Depends(require_role(...))` in `core/dependencies.py`—**not** inline auth in every handler. |
| **Response models** | Always set `response_model=` on routes that return bodies; use `response_model_exclude_unset=True` for PATCH reads when appropriate. |
| **Status codes** | Explicit `status_code=` on `POST` (201), `DELETE` (204); use `HTTPException` with stable `detail` codes documented for UIs. |
| **Async** | `async def` route handlers when using async SQLAlchemy/HTTP clients; keep CPU-only work sync or offload—do not block the event loop on heavy sync I/O. |
| **Background work** | `BackgroundTasks` only for non-critical side effects; **auto-create claim** and audit writes should be **awaited** in the service path (or transactional outbox later)—not fire-and-forget if consistency matters. |
| **Validation errors** | Rely on FastAPI’s 422 for body/query validation; do not catch `ValidationError` in routers unless translating to domain errors. |
| **OpenAPI** | `summary` / `description` on public and compliance-sensitive routes; mark `include_in_schema=False` for internal health/debug if needed. |
| **Testing** | `httpx.AsyncClient` + `app` fixture; test services with mocked repositories; one API test per critical route (auth, intake, encounter→claim idempotency). |

#### Security and compliance hooks

- Validate and authorize in **dependencies** before handler body runs on PHI routes.
- Compliance `PolicyEnforcer` runs **after** Auth identity is known (see §3.10)—do not duplicate role checks inside HIPAA policy code.
- Use Pydantic to **strip** unknown fields on input (`model_config = ConfigDict(extra="forbid")` on public create schemas where feasible).

#### Testing and quality bar

- **pytest** layout mirrors `app/`: `tests/unit/domains/...`, `tests/api/v1/...`.
- Prefer **factory functions** or minimal fixtures over huge JSON blobs; seed Reference enums in fixtures.
- Any new domain endpoint ships with at least one happy-path API test and one auth/validation failure test where security matters.

---

## 6. FastAPI routes and endpoint organization

**API versioning:** `/api/v1/...` on all business routes.

**Domain prefixes and grouping**

| Router prefix | Domain | Example route groups |
|---------------|--------|----------------------|
| `/api/v1/auth` | **Auth** (Technology) | `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`; admin: `GET/POST /roles` (internal); **no** fine-grained permissions API in v1 |
| `/api/v1/reference` | Reference | `GET /locations`, `GET /locations/{id}` |
| `/api/v1/intake` | Intake | `POST /enquiries`, `GET /enquiries` (internal) |
| `/api/v1/scheduling` | Scheduling | `GET /appointments`, `PATCH /appointments/{id}/status`; no-show KPIs; **no** clinical note routes |
| `/api/v1/clinical` | Clinical Operations | `GET/POST /encounters`, `POST /encounters/{id}/notes`, `GET /encounters/{id}/ehr-sync`; adapter health under `/clinical/integrations/ehr` (internal) |
| `/api/v1/billing` | Billing | `GET /claims`, `POST /claims` (from encounter), denial rates, payer flags; `claim.encounter_id` required when sourced from visit |
| `/api/v1/workforce` | Workforce | `GET/PATCH /clinicians`; `GET/POST /hiring/candidates`, `PATCH /hiring/candidates/{id}/stage`; `GET/POST /onboarding`, `PATCH /onboarding/{id}/tasks`; **no** CME or audit routes |
| `/api/v1/compliance` | Compliance | `GET /audit-events`, `GET /cme/reports`, `GET /cme/clinicians/at-risk`, `GET /cme/clinicians/expiring-licences`; `GET /policies` (internal); enforcement is mostly middleware, not public RPC |
| `/api/v1/reporting` | Reporting | `GET /kpis/weekly` (composed read models) |

**Route grouping criteria**

1. **Resource noun** — REST collections (`/claims`, `/appointments`).
2. **Action sub-resource** — KPI/analytics as subpaths: `GET /billing/denial-rates`, `GET /billing/payers/high-denial?threshold=8`
3. **Audience** — Public vs internal tags on OpenAPI; stricter auth on **clinical** (notes), **compliance** (audit export), workforce, and billing; EHR webhook endpoints separate tag + API key.
4. **Idempotency** — `POST /intake/enquiries` for create; KPI endpoints are `GET` with query params.
5. **Pagination/filter** — Query params on list endpoints (`location_id`, `status`, `payer_name`)

**`api/v1/router.py` pattern**

- Each domain exports `APIRouter(tags=[...])`
- Single mount in `main.py` with prefix and tags for OpenAPI grouping

---

## 7. Frontend ↔ backend as separate systems

### 7.1 Monorepo boundaries

| System | Location | Role |
|--------|----------|------|
| **Public UI** | `uis/website` | Marketing + enquiry; calls Intake API (prefer server-side from Next Route Handler or Server Action) |
| **Internal ops UI** | Future dashboards + `uis/backoffice` (today: M2 test only) | Eventually Clinical, Billing, Scheduling, Workforce, **Compliance** (CME + audit) APIs |
| **Recruiting UI** | `apps/talent-pipeline-tracker` | Primary candidate UX; syncs with Workforce hiring via Talent Tracker API / adapter (not duplicate pipeline in Billing or Clinical) |
| **Backend** | `services/api` | Source of persisted data (Supabase) and authoritative API |

### 7.2 API communication

- **Protocol:** HTTPS JSON REST, OpenAPI 3 from FastAPI (`/docs`, `/openapi.json`)
- **Client pattern in Next.js:**
  - **Server-only** calls for public forms (`API_URL` without `NEXT_PUBLIC_`) to avoid exposing internal URLs and simplify CORS
  - **Client fetch** only for authenticated internal apps with short-lived tokens
- **Contract:** OpenAPI from this app (`/openapi.json`); optional TypeScript client generated into a **frontend** folder (npm package), not a second Python uv project
- **Error shape:** Consistent problem+json or `{ "detail": [...] }` FastAPI default—document standard for UIs

### 7.3 Environment variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | API | **Supabase** Postgres connection string (SQLAlchemy/async driver) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | API | Supabase project URL + server-side key (if using Supabase client features beyond raw Postgres) |
| `CORS_ORIGINS` | API | Comma-separated allowed origins |
| `API_URL` | Next server | Server-side base URL (`http://services-api:8000` dev) |
| `NEXT_PUBLIC_API_URL` | Next client | Only if browser must call API directly |
| `APP_ENV` | Both | `development` / `staging` / `production` |
| `EHR_ADAPTER` | API (Clinical) | `mock` \| vendor key; selects adapter implementation |
| `EHR_*_BASE_URL`, `EHR_*_CLIENT_SECRET` | API (Clinical) | Per-vendor EHR credentials (never in frontend) |
| `TALENT_TRACKER_BASE_URL`, `TALENT_TRACKER_API_KEY` | API (Workforce) | Talent Tracker adapter for hiring pipeline sync (never in frontend) |
| `JWT_SECRET` or `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` | API (Auth) | Token signing; never expose to frontends except as issued bearer token |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | API (Auth) | Token lifetimes |
| `JWT_ALGORITHM` | API (Auth) | e.g. `HS256` or `RS256` |

Provide `.env.example` per app; document in architecture doc, not duplicated secrets.

### 7.4 CORS

- **Public website:** Prefer **no browser CORS** to API—submit enquiry via Next server route proxying to FastAPI.
- **Internal apps:** Explicit `CORS_ORIGINS` (localhost ports for `uis/backoffice`, talent tracker dev server).
- **Production:** Separate origins per app; no `*` with credentials.
- **Methods/headers:** Minimal allow list (`GET`, `POST`, `PATCH`, `Authorization`, `Content-Type`).

---

## 8. M2 TypeScript utilities — backend scope (decided)

**The FastAPI backend does not import, port, or mirror the 22 M2 operations from `apps/src`.**

| System | M2 (`apps/src`) usage |
|--------|------------------------|
| **`services/api` (backend)** | **Ignore M2**—implement domain business rules natively in Python (`service.py` per domain) |
| **`uis/backoffice`** | Continues to import M2 utils via `@healthcore/src/*` for manual test UI |
| **`apps/src` CLI/tests** | Unchanged (`tsx main.ts`, `run-tests.ts`) |
| **`uis/website`** | No M2 in enquiry form (validation in Next.js) unless separately scheduled |

**Implications for the architecture doc**

- Do **not** include an endpoint mapping table for all 22 M2 functions in the backend proposal.
- Billing/Scheduling/Compliance KPIs in the API are **new Python implementations**—ops should validate against business requirements, not automatic parity with `apps/src/tests`.
- Risk: backend KPIs may differ from backoffice manual test output until explicitly reconciled—document as known boundary, not a bug in either system.

**Optional later:** shared JSON fixture tests if product requires numerical alignment between backoffice and API—out of scope for initial backend delivery.

---

## 9. Risks and points of attention

**Minimum two risks** (doc will expand each with mitigation):

| # | Risk | If structure not followed |
|---|------|---------------------------|
| **1** | **Duplicated business logic across layers** | Backend Python, Next validation, and M2 backoffice utils diverge on KPIs and rules—ops see conflicting numbers. |
| **2** | **Flat or mixed domain routers** | All endpoints in one `routes.py` → cross-domain imports, untestable handlers, unsafe auth boundaries (public hitting billing). |
| **3** | **CORS + public client direct to API** | Misconfigured origins or exposing internal routes → data leaks or CSRF-like abuse on intake endpoints. |
| **4** | **Skipping API versioning** | Breaking changes break `uis/website` and future mobile clients without migration path. |
| **5** | **Repository logic in routers** | Untestable endpoints, Pydantic models bypassed, inconsistent validation. |
| **6** | **Mixed Python toolchains (pip + uv)** | Unpinned deps in CI, “works on my machine” installs, lockfile bypassed in production images. |
| **7** | **Clinical notes in Billing or Scheduling modules** | PHI leakage into wrong routes, EHR sync logic duplicated, claims missing encounter context or tied to wrong visit. |
| **8** | **Bypassing EHR adapters** | Vendor-specific code in routers/services → untestable integrations and unsafe upgrades when EHR API changes. |
| **9** | **Audit/CME/HIPAA scattered across domains** | Incomplete audit trail, inconsistent CME reporting, HIPAA checks missing on some PHI routes. |
| **10** | **Mutable or deletable audit records** | Regulatory non-compliance; inability to prove who accessed PHI during an incident review. |
| **11** | **Auth logic embedded in business domains** | Inconsistent JWT validation, permission strings duplicated, Compliance HIPAA checks without stable identity. |

**Points of attention**

- Document `uv` install in `services/api/README.md`
- Contributors run `uv sync` inside **`services/api/`** before API work
- Docker/production: build from `services/api` with `uv sync --frozen --no-dev`
- Commit `uv.lock` with dependency changes in the same PR

- PHI in enquiry payloads: retention, encryption, audit logging
- UK vs US location rules in Reference domain
- Talent Tracker: **adapter-only** under Workforce `hiring/` (decided)—webhook and `talent_candidate_id` mapping
- Onboarding: **single checklist** for all roles (decided)
- EHR: **mock adapter only** in v1 (decided)
- Encounter complete → **auto-create claim** (decided); idempotent on `encounter_id`
- Audit log: **Supabase** append-only tables in same project as app data (decided)
- Audit log storage growth: partition by month, retention job aligned with HIPAA policy module
- CME and licence rules differ US vs UK locations—parameterize Compliance calculators with Reference location country

---

## 10. Proposed `architecture_proposal.md` section order

1. Executive summary
2. Context and current landscape (memory-bank alignment)
3. Architectural pattern (modular monolith + layering)
4. Domain model: Business vs Technology separation criteria + **per-domain detail** (§3.1–§3.10)
5. Reference, Intake, Scheduling, Clinical, Billing, Workforce, Compliance, Reporting, Integrations (each: purpose, modules, API, boundaries, links)
6. Auth (Technology): coarse roles, JWT issuance, JWT implications (§3.10)
7. Cross-domain linking: Clinical ↔ Scheduling ↔ Billing; Auth → Compliance → PHI domains
8. Repository layout (monorepo; `services/api`)
9. Backend structure (FastAPI + colocated Pydantic schemas)
10. Python toolchain (uv single project: sync, lockfile, run, CI)
11. **Python, FastAPI, and Pydantic best practices** (PEP 8 via Ruff, typing, layer rules, v2 models, dependencies, testing)
12. FastAPI routes, versioning, grouping
13. Pydantic layout, settings, and schema naming (`*Create` / `*Read`)
14. Frontend/backend boundaries (communication, env, CORS)
15. Backend scope vs `apps/src` M2 (backend ignores M2; backoffice retains M2 utils)
16. Phased rollout (Auth/JWT → Supabase → Compliance audit → Intake → Scheduling/Billing → Workforce hiring/onboarding → Clinical mock EHR → auto-claim)
17. Risks and points of attention
18. Resolved decisions (§11)

---

## 11. Resolved decisions (team sign-off)

| # | Topic | **Decision** |
|---|--------|--------------|
| **1** | **Database** | **Supabase** (PostgreSQL) — `DATABASE_URL` to Supabase project; use Supabase for managed Postgres in all environments |
| **2** | **Auth** | Use the **Auth technology domain** in `services/api` (`domains/technology/auth/`)—local users + **JWT issuance** in v1; not external IdP/OAuth on day one |
| **3** | **Recruiting** | **Talent Tracker adapter-only** under Workforce `hiring/`—sync via adapter; primary UI stays `apps/talent-pipeline-tracker` |
| **4** | **API path** | **`services/api`** (not `apps/healthcore-api`) |
| **5** | **M2 / backend** | **Ignore M2 for backend**—no port of 22 M2 operations; no M2 endpoint mapping table in architecture doc; `apps/src` + backoffice unchanged |
| **6** | **Onboarding** | **Single checklist** for all roles in v1 |
| **7** | **EHR** | **Mock adapter only** in v1 (`EHR_ADAPTER=mock`) |
| **8** | **Encounter → claim** | **Auto-create claim** when encounter completes (idempotent on `encounter_id`) |
| **9** | **Audit store** | **Supabase** — append-only audit tables in the **same Supabase project** as application data where possible |
| **10** | **HIPAA policies** | **Code-first** policy module in `domains/compliance/policies/` (not external OPA/IAM in v1) |
| **11** | **Permissions** | **Coarse roles only** in v1—no fine-grained `resource.action` permissions in JWT or enforcement |

---

## Next step

**Done:** Full proposal written to [`docs/architecture_proposal.md`](docs/architecture_proposal.md). Next: scaffold `services/api` per phased rollout (§12 of proposal) when implementation is requested.
