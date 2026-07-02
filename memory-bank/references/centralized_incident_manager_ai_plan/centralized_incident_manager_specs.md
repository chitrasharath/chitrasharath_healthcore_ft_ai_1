# Centralized Incident Manager — Implementation Spec

> **Branch:** `feature/milestone5` (extends existing work)
> **Working directory (backend):** `services/api/`
> **Working directory (frontend):** `uis/backoffice/`

---

## 1. Project Overview

HealthCore's previous milestone delivered a CSV-based incident analyzer (`uis/incident_analyzer/`) that validates and summarizes uploaded incident files. The support team now needs to **log incidents directly from the browser** — no more manual file exports.

This milestone builds a **Centralized Incident Manager** that:
- Provides a full CRUD lifecycle for incidents: `open → in_progress → resolved → discarded`
- Captures who reported an incident, what happened, from where (origin/branch), and when
- Seeds the database with historical CSV data (100 rows from `incidents-healthcore.csv`, origin = `customer`)
- Displays a filterable incident list with inline status updates
- Shows aggregated summary metrics for leadership (totals by status, category, origin, branch)
- Handles errors gracefully: slow API, 500 responses, validation failures — all with user-friendly messages

The old Incident Analyzer remains available in the backoffice hub. The new module appears as a separate nav card labeled **"Incident Manager"** to allow both versions to coexist, with the old one deprecated later.

---

## 2. Tech Stack

| Layer | Technology | Version / Detail |
|-------|-----------|-----------------|
| Backend framework | FastAPI | existing in `services/api/` |
| Backend ORM | SQLModel | same as inventory models |
| Backend DB | Supabase (PostgreSQL) | project: `milestone5_inventory`, via `supabase_engine` in `app/core/db.py` |
| Backend validation | Pydantic v2 | via SQLModel/FastAPI schemas |
| Frontend framework | Next.js (App Router) | 16.2.6 |
| Language | TypeScript | ^5 |
| React | React | 19.2.4 |
| Styling | Tailwind CSS | ^4 |
| Build | Webpack | via `next dev --webpack` |
| Port | localhost:3004 | `npm run dev` from `uis/backoffice/landing` |
| API base | `http://localhost:8000/api/v1` | via `NEXT_PUBLIC_API_URL` |
| Seed script | Python | uses `analysis_core.py` validation logic |

### CSS Design Tokens (defined in `landing/app/globals.css`)

```css
--hc-brand: #0369a1;
--hc-brand-strong: #0c4a6e;
--hc-surface: #ffffff;
--hc-surface-muted: #f8fafc;
--hc-border: #cbd5e1;
--hc-text: #0f172a;
--hc-text-muted: #475569;
--hc-success: #166534;
--hc-warning: #a16207;
--hc-danger: #b91c1c;
```

No component library (no shadcn, Radix, MUI). Use raw Tailwind classes matching existing backoffice patterns.

---

## 3. Business Constraints Enforced in API

These rules are enforced server-side. The frontend must handle responses correctly but does NOT re-implement the logic — only provides UX guards where specified.

1. **Incident lifecycle is strictly ordered.** Valid transitions:
   - `open` → `in_progress` or `discarded`
   - `in_progress` → `resolved` or `discarded`
   - `resolved` and `discarded` are **final states** — no further transitions allowed
   - The API returns `400` with a descriptive message for invalid transitions (e.g., `"Cannot transition from 'resolved' to 'open'. Resolved is a final state."`)

2. **All fields are validated server-side.** Missing required fields or invalid enum values return `400` with a JSON body identifying the problematic field and a plain-language description.

3. **`created_at` and `updated_at` are server-managed.** The frontend does NOT send these fields.

4. **`id` is auto-generated.** The frontend does NOT send `id` in POST bodies.

5. **Category must be one of the 5 valid HealthCore categories:** `APPOINTMENT`, `BILLING`, `CLINICAL_CARE`, `ACCESSIBILITY`, `ADMINISTRATIVE`.

6. **Status must be one of:** `open`, `in_progress`, `resolved`, `discarded`. New incidents default to `open`.

7. **Origin must be one of:** `customer`, `branch`, `internal`.

8. **Branch must be one of the 12 valid HealthCore clinic codes** (e.g., `US-TX-01`, `UK-LON-02`) **or `"Central"`** for incidents not specific to a branch.

9. **Empty database is valid.** Read endpoints return empty lists/zero metrics, never errors.

10. **Unhandled exceptions return `500` with a generic message** — never the full stack trace.

11. **All incident endpoints require `Authorization: Bearer <token>`.** The `healthcoreFetch` helper already handles token injection.

---

## 4. Backend Error Handling

This section defines exactly how the API must respond to every error scenario. The tech lead's requirement: **"I want to see error messages that users understand, not stack traces."**

### 4.1 Global Exception Handler

Register a FastAPI exception handler that catches all unhandled exceptions and returns a safe `500` response. Never expose internal details, file paths, or stack traces.

```python
# In router.py or as middleware
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )
```

### 4.2 Validation Errors (`400`)

Every validation error must return `400` with a JSON body containing a `detail` field that:
- Identifies the problematic field by name
- Describes the error in plain language
- Lists valid options when the value is an invalid enum

**Required error messages by scenario:**

| Scenario | Response `detail` |
|----------|------------------|
| Missing `title` | `"Title is required."` |
| Missing `description` | `"Description is required."` |
| Empty `title` (blank string) | `"Title cannot be empty."` |
| Empty `description` (blank string) | `"Description cannot be empty."` |
| Invalid `category` | `"Invalid category '{value}'. Must be one of: APPOINTMENT, BILLING, CLINICAL_CARE, ACCESSIBILITY, ADMINISTRATIVE."` |
| Invalid `status` | `"Invalid status '{value}'. Must be one of: open, in_progress, resolved, discarded."` |
| Invalid `origin` | `"Invalid origin '{value}'. Must be one of: customer, branch, internal."` |
| Invalid `branch` | `"Invalid branch '{value}'. Must be one of the 12 clinic codes (e.g., US-TX-01) or 'Central'."` |
| Missing required field (generic) | `"Field '{field_name}' is required."` |

### 4.3 Lifecycle Transition Errors (`400`)

Invalid status transitions must return a clear message explaining the constraint.

| Scenario | Response `detail` |
|----------|------------------|
| Final state transition | `"Cannot transition from '{current}' to '{requested}'. {Current} is a final state."` |
| Invalid transition path | `"Cannot transition from '{current}' to '{requested}'. Valid transitions: {valid_list}."` |

**Examples:**
- `"Cannot transition from 'resolved' to 'open'. Resolved is a final state."`
- `"Cannot transition from 'open' to 'resolved'. Valid transitions: in_progress, discarded."`

### 4.4 Not Found Errors (`404`)

| Scenario | Response `detail` |
|----------|------------------|
| Incident not found by ID | `"Incident not found."` |

### 4.5 Empty Database Behavior

Read endpoints must **never** fail on an empty database:

| Endpoint | Empty DB Response |
|----------|------------------|
| `GET /incidents` | `200` with `[]` (empty array) |
| `GET /incidents?status=open` | `200` with `[]` (empty array) |
| `GET /incidents/summary` | `200` with all counts as `0` |
| `GET /incidents/{id}` | `404` with `"Incident not found."` (this is correct, not an error) |

### 4.6 Authentication Errors (`401`)

Handled by the existing `get_current_user` dependency — no additional implementation needed. Returns:
```json
{"detail": "Not authenticated"}
```
or
```json
{"detail": "Could not validate credentials"}
```

### 4.7 Slow API / Timeout Handling

The backend itself does not need timeout logic, but:
- Database queries must not block indefinitely — use standard SQLModel session patterns (already handled by `get_supabase_db`)
- The frontend handles slow responses with loading indicators and disabled submit buttons (see Section 12)

---

## 5. API Contract

Base URL: `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api/v1`).

All endpoints require authentication via `get_current_user` dependency.

### `POST /incidents`

Creates a new incident. Returns `201` on success, `400` on validation failure.

**Request body:**
```json
{
  "title": "Patient registration error at Austin North",
  "description": "Patient registration data contains error from onboarding process, leading to incorrect insurance information on file.",
  "category": "ADMINISTRATIVE",
  "origin": "branch",
  "branch": "US-TX-02"
}
```

**Response (201):**
```json
{
  "id": 1,
  "title": "Patient registration error at Austin North",
  "description": "Patient registration data contains error from onboarding process...",
  "category": "ADMINISTRATIVE",
  "status": "open",
  "origin": "branch",
  "branch": "US-TX-02",
  "created_at": "2026-07-01T10:00:00Z",
  "updated_at": "2026-07-01T10:00:00Z"
}
```

**Error (400):**
```json
{
  "detail": "Invalid category 'UNKNOWN'. Must be one of: APPOINTMENT, BILLING, CLINICAL_CARE, ACCESSIBILITY, ADMINISTRATIVE."
}
```

### `GET /incidents`

Returns all incidents. Supports optional query filters.

**Query parameters (all optional):**
- `status` — filter by status (e.g., `?status=open`)
- `origin` — filter by origin (e.g., `?origin=customer`)
- `branch` — filter by branch (e.g., `?branch=US-TX-01`)
- `category` — filter by category (e.g., `?category=BILLING`)

**Response:** `Incident[]`
```json
[
  {
    "id": 1,
    "title": "Patient registration error",
    "description": "Patient registration data contains error...",
    "category": "ADMINISTRATIVE",
    "status": "open",
    "origin": "branch",
    "branch": "US-TX-02",
    "created_at": "2026-07-01T10:00:00Z",
    "updated_at": "2026-07-01T10:00:00Z"
  }
]
```

### `GET /incidents/{id}`

Returns a single incident. Returns `404` if not found.

**Response:** Same shape as single item in the list above.

**Error (404):**
```json
{
  "detail": "Incident not found."
}
```

### `PATCH /incidents/{id}/status`

Updates only the status of an incident. Validates lifecycle transitions.

**Request body:**
```json
{
  "status": "in_progress"
}
```

**Response (200):** Full incident object with updated status and `updated_at`.

**Error (400):**
```json
{
  "detail": "Cannot transition from 'resolved' to 'open'. Resolved is a final state."
}
```

**Error (404):**
```json
{
  "detail": "Incident not found."
}
```

### `GET /incidents/summary`

Returns aggregated metrics across all incidents.

**Response:**
```json
{
  "by_status": {
    "open": 28,
    "in_progress": 0,
    "resolved": 52,
    "discarded": 14
  },
  "by_category": {
    "APPOINTMENT": 30,
    "BILLING": 20,
    "CLINICAL_CARE": 14,
    "ACCESSIBILITY": 17,
    "ADMINISTRATIVE": 13
  },
  "by_origin": {
    "customer": 94,
    "branch": 0,
    "internal": 0
  },
  "by_branch": {
    "US-TX-01": 10,
    "US-TX-02": 8,
    "Central": 5
  }
}
```

---

## 6. Dependencies & Prerequisites

### Backend

1. **Supabase database must be configured** via `DATABASE_URL` in `services/api/.env`. The `Incident` model uses SQLModel + Supabase, same as inventory.
2. **Existing auth system** (`get_current_user` dependency) is already functional. All incident routes must be protected.
3. **The `analysis_core.py` module** at `uis/incident_analyzer/analysis_core.py` contains the validation logic (valid clinic codes, categories, statuses). The seed script must reuse this for CSV validation — import from this module or extract shared constants to `packages/shared/`.
4. **CSV seed file** is at `incidents-healthcore.csv` (repo root) — 100 rows of historical incident data.

### Frontend

1. **Backend API must be running** at `http://localhost:8000` with seed data loaded.
2. **Existing auth system** — login, token storage in `localStorage`, `AuthGuard` component — is already functional. Do not modify it.
3. **`healthcoreFetch`** from `@backoffice/shared/lib/healthcore-api.ts` handles `Authorization` header injection and 401 redirect. All incident API calls must go through it.
4. **No new npm dependencies.** Use only what is already in `landing/package.json`.

### Key existing files (read-only references)

| File | Purpose |
|------|---------|
| `shared/lib/healthcore-api.ts` | `healthcoreFetch` — auth header injection, 401 redirect |
| `landing/lib/api.ts` | `apiFetch`, `getStoredToken`, `fetchCurrentUser` — auth utilities |
| `landing/components/auth/auth-guard.tsx` | `<AuthGuard>` — session verification + redirect |
| `landing/app/(protected)/layout.tsx` | Wraps all protected routes in `<AuthGuard>` |
| `landing/components/layout/tool-toolbar.tsx` | `<ToolToolbar>` — "Back to hub" + logout bar |
| `landing/components/layout/landing-footer.tsx` | `<LandingFooter>` — copyright footer |
| `landing/components/layout/healthcore-logo.tsx` | `<HealthcoreLogo>` — SVG logo |
| `landing/components/landing/nav-card.tsx` | `<NavCard>` — card component for hub |
| `landing/lib/nav-apps.ts` | `NAV_APPS` array — hub navigation entries |
| `landing/app/globals.css` | CSS tokens + Tailwind `@source` directives |
| `landing/next.config.ts` | Feature module alias registration |
| `uis/incident_analyzer/analysis_core.py` | Validation logic, valid clinics/categories/statuses |
| `incidents-healthcore.csv` | Historical incident data (100 rows) for seeding |

---

## 7. Development Workflow

```bash
# 1. Install frontend dependencies
cd uis/backoffice/landing && npm install

# 2. Start backend (separate terminal)
cd services/api && uv run uvicorn app.main:app --reload

# 3. Run seed script (once, after backend is up)
cd scripts && python seed_incidents.py

# 4. Start frontend
cd uis/backoffice/landing && npm run dev

# 5. Verify build
npm run verify   # runs lint + build
```

- Frontend runs on `http://localhost:3004`
- Backend runs on `http://localhost:8000`
- All new files must pass TypeScript strict mode and ESLint
- All frontend components use `"use client"` since they rely on `useState`, `useEffect`, `useSearchParams`, and `localStorage`

---

## 8. Data Model — `Incident` (SQLModel)

**File:** `services/api/app/domains/incidents/models.py`

```python
class Incident(SQLModel, table=True):
    __tablename__ = "incident"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    category: str          # APPOINTMENT | BILLING | CLINICAL_CARE | ACCESSIBILITY | ADMINISTRATIVE
    status: str = "open"   # open | in_progress | resolved | discarded
    origin: str            # customer | branch | internal
    branch: str            # clinic code (US-TX-01, etc.) or "Central"
    created_at: datetime   # auto-set on creation
    updated_at: datetime   # auto-set on creation, updated on modification
```

### Integrity constraints (enforced in API layer, not DB constraints):
- `title` — required, non-empty string
- `description` — required, non-empty string
- `category` — must be one of the 5 valid categories
- `status` — must be one of: `open`, `in_progress`, `resolved`, `discarded`
- `origin` — must be one of: `customer`, `branch`, `internal`
- `branch` — must be one of the 12 valid clinic codes or `"Central"`

---

## 9. Backend File Structure

### New domain: `services/api/app/domains/incidents/`

```
services/api/app/domains/incidents/
├── __init__.py
├── models.py        # SQLModel Incident table definition
├── schemas.py       # Pydantic request/response schemas
├── router.py        # FastAPI route handlers
├── service.py       # Business logic (validation, lifecycle transitions)
└── constants.py     # Valid categories, statuses, origins, branches (shared with analysis_core)
```

### Seed script: `scripts/seed_incidents.py`

Single Python script that:
1. Reads `incidents-healthcore.csv` from repo root
2. Validates each row using the same rules as `analysis_core.validate_record()`
3. Inserts valid rows into the `incident` table with `origin = "customer"`
4. Maps CSV fields to the Incident model:
   - `incident_id` → used for idempotency check (do NOT insert if already exists)
   - `date` → `created_at` (parse as datetime)
   - `clinic_id` → `branch`
   - `category` → `category`
   - `description` → `description`
   - `status` → map CSV statuses (`OPEN` → `open`, `CLOSED` → `resolved`, `DISCARDED` → `discarded`)
   - `title` → generate from category + branch (e.g., `"ADMINISTRATIVE incident at US-TX-02"`)
5. Reports invalid rows to console (count per rule, no PHI)
6. Is **idempotent**: running twice does not duplicate records (check `title` + `branch` + `created_at`, or store `incident_id` from CSV as a reference)

### Router registration

Add to `services/api/app/api/v1/router.py`:
```python
from app.domains.incidents.router import router as incidents_mgmt_router
api_v1_router.include_router(incidents_mgmt_router, dependencies=[Depends(get_current_user)])
```

**Important:** The existing `incidents_router` (CSV analysis endpoints at `/incidents/analyze`) must remain unchanged. The new incident manager router should use prefix `/incidents` for CRUD — coordinate the URL namespace so there are no conflicts. The summary endpoint must be registered **before** the `{id}` path parameter route to avoid FastAPI treating `"summary"` as an ID.

### Model registration

Import the new model in `services/api/app/main.py` so SQLModel creates the table on startup:
```python
from app.domains.incidents import models as incident_models  # noqa: F401
```

---

## 10. Frontend File Structure

### New feature module: `uis/backoffice/incident-manager/`

```
uis/backoffice/incident-manager/
├── lib/
│   ├── incidents-api.ts     # Centralized API calls using healthcoreFetch
│   └── constants.ts         # Branches, categories, origins, statuses, status transitions
├── components/
│   ├── incident-landing.tsx      # Landing page with hero + nav cards
│   ├── incident-form.tsx         # Create incident form
│   ├── incident-list.tsx         # Filterable incident list with inline status updates
│   └── incident-summary.tsx      # Aggregated metrics dashboard
└── types/
    └── incidents.ts              # TypeScript types matching API schemas
```

### New route pages: `uis/backoffice/landing/app/(protected)/incident-manager/`

```
landing/app/(protected)/incident-manager/
├── layout.tsx          # ToolToolbar + footer wrapper
├── page.tsx            # Incident manager landing (hero + nav cards)
├── new/
│   └── page.tsx        # Create incident form page
├── list/
│   └── page.tsx        # Incident list page
└── summary/
    └── page.tsx        # Summary metrics page
```

---

## 11. Configuration Changes

### 10.1 Register alias in `landing/next.config.ts`

Add to the variable declarations:
```ts
const incidentManager = path.join(landingDir, "../incident-manager");
```

Add to the `featureAliases` object:
```ts
"@backoffice/incident-manager": incidentManager,
```

### 10.2 Add Tailwind source in `landing/app/globals.css`

Add alongside the other `@source` directives:
```css
@source "../../incident-manager/**/*";
```

### 10.3 Add nav card in `landing/lib/nav-apps.ts`

Add to the `NAV_APPS` array (place it after the existing "Incident Analyzer" entry):
```ts
{
  title: "Incident Manager",
  description: "Log, track, and manage patient incidents across all clinics",
  url: "/incident-manager",
  protected: true,
},
```

---

## 12. Static Data: Branches, Categories, Origins

### Valid Branches (clinic codes + Central)

Define in `incident-manager/lib/constants.ts`. These match `analysis_core.VALID_CLINICS`.

| Code | Country | Location |
|------|---------|----------|
| `US-TX-01` | US | Austin, TX — Main |
| `US-TX-02` | US | Austin, TX — North |
| `US-TX-03` | US | Houston, TX |
| `US-FL-01` | US | Miami, FL |
| `US-FL-02` | US | Orlando, FL |
| `US-FL-03` | US | Tampa, FL |
| `US-GA-01` | US | Atlanta, GA — Midtown |
| `US-GA-02` | US | Atlanta, GA — Buckhead |
| `US-GA-03` | US | Savannah, GA |
| `UK-LON-01` | UK | London — Canary Wharf |
| `UK-LON-02` | UK | London — Kensington |
| `UK-MAN-01` | UK | Manchester |
| `Central` | — | HQ / not branch-specific |

### Valid Categories

| Value | Display Label |
|-------|--------------|
| `APPOINTMENT` | Appointment |
| `BILLING` | Billing |
| `CLINICAL_CARE` | Clinical Care |
| `ACCESSIBILITY` | Accessibility |
| `ADMINISTRATIVE` | Administrative |

### Valid Origins

| Value | Display Label |
|-------|--------------|
| `customer` | Customer |
| `branch` | Branch |
| `internal` | Internal |

### Valid Statuses

| Value | Display Label |
|-------|--------------|
| `open` | Open |
| `in_progress` | In Progress |
| `resolved` | Resolved |
| `discarded` | Discarded |

### Status Transitions (for frontend UX guards)

```ts
export const STATUS_TRANSITIONS: Record<string, string[]> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],      // final state
  discarded: [],     // final state
};
```

---

## 13. Implementation Details

### 12.1 TypeScript Types — `incident-manager/types/incidents.ts`

```ts
export type Incident = {
  id: number;
  title: string;
  description: string;
  category: string;
  status: string;
  origin: string;
  branch: string;
  created_at: string;
  updated_at: string;
};

export type IncidentCreate = {
  title: string;
  description: string;
  category: string;
  origin: string;
  branch: string;
};

export type StatusUpdate = {
  status: string;
};

export type IncidentSummary = {
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
};
```

### 12.2 API Layer — `incident-manager/lib/incidents-api.ts`

- Import `healthcoreFetch` from `@backoffice/shared/lib/healthcore-api`.
- Create a wrapper `incidentFetch<T>(path, init?)` that:
  - Calls `healthcoreFetch(path, init)`
  - On non-OK response: parses JSON body, extracts `detail`, throws `Error(detail)`
  - On success: returns parsed JSON as `T`
- Export these functions:
  - `createIncident(body: IncidentCreate)` → `POST /incidents`
  - `listIncidents(filters?)` → `GET /incidents` with optional query params
  - `getIncident(id: number)` → `GET /incidents/{id}`
  - `updateIncidentStatus(id: number, status: string)` → `PATCH /incidents/{id}/status`
  - `getIncidentSummary()` → `GET /incidents/summary`

**No component may call `fetch` or `healthcoreFetch` directly.** All incident API access goes through this module.

### 12.3 Incident Landing Page — `/incident-manager`

**Route:** `landing/app/(protected)/incident-manager/page.tsx`
**Component:** `incident-manager/components/incident-landing.tsx`

Styled like the main backoffice landing:

**Hero section** — same gradient as other modules:
- `rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10`
- Include `<HealthcoreLogo />`
- Title: **"Incident Manager"**
- Subtitle: "Log, track, and manage patient incidents across all HealthCore clinics."

**Nav cards grid** — 3 cards:

| Card Title | Description | Link |
|-----------|-------------|------|
| Log Incident | Report a new patient or operational incident | `/incident-manager/new` |
| Incident List | View and filter all registered incidents | `/incident-manager/list` |
| Summary Dashboard | Aggregated metrics by status, category, origin, and branch | `/incident-manager/summary` |

### 12.4 Incident Form — `/incident-manager/new`

**Route:** `landing/app/(protected)/incident-manager/new/page.tsx`
**Component:** `incident-manager/components/incident-form.tsx`

**Form fields (all required):**

| Field | Input Type | Options/Behavior |
|-------|-----------|-----------------|
| Title | `<input type="text">` | Required, non-empty |
| Description | `<textarea>` | Required, non-empty |
| Category | `<select>` dropdown | 5 valid HealthCore categories |
| Origin | `<select>` dropdown | `customer`, `branch`, `internal` |
| Branch | `<select>` dropdown | 12 clinic codes + `Central`. Always visible and required. |

**UX behaviors:**
- When `origin` is `"branch"`, visually highlight the Branch field (e.g., amber border or background) to remind the user they are reporting from a specific location.
- Show a **loading indicator** on the submit button while the request is in flight. Disable the button during that time.
- **On success (201):** Clear the form. Show a green confirmation banner (e.g., "Incident logged successfully").
- **On error (400):** Display the API `detail` message in a user-friendly format. If the error identifies a specific field, show the message near that field. Never display raw server error text.
- **On error (500):** Show a generic red banner: "Something went wrong. Please try again later."

### 12.5 Incident List — `/incident-manager/list`

**Route:** `landing/app/(protected)/incident-manager/list/page.tsx`
**Component:** `incident-manager/components/incident-list.tsx`

- Fetch `listIncidents()` on mount. Show a loading indicator while data is being fetched.
- **Filters** — dropdowns at the top of the page for:
  - Status (all statuses + "All" default)
  - Origin (all origins + "All" default)
  - Branch (all branches + "All" default)
- Filters update the API call with query parameters and re-fetch.

**Table columns:** Title, Category, Status, Origin, Branch, Created At

**Inline status update:**
- Each row shows the current status as a badge and a dropdown/buttons showing valid next transitions (based on `STATUS_TRANSITIONS`).
- Final states (`resolved`, `discarded`) show no transition options.
- On status change: call `updateIncidentStatus(id, newStatus)`.
  - **Success:** Update the row in place.
  - **Failure:** Revert the visual state to the previous value and show an error notification.

**Empty state:** If no incidents match the filters (or DB is empty), display an informative message — never an empty table without context.

**Error state:** If the fetch fails, show an error message with a **Retry** button. The page does not go blank or break.

**Date formatting:** Display `created_at` in a human-readable format (e.g., `Jul 1, 2026 10:30 AM`).

### 12.6 Summary Dashboard — `/incident-manager/summary`

**Route:** `landing/app/(protected)/incident-manager/summary/page.tsx`
**Component:** `incident-manager/components/incident-summary.tsx`

- Fetch `getIncidentSummary()` on mount.
- Display 4 metric sections:
  1. **By Status** — card/table showing count for each status (`open`, `in_progress`, `resolved`, `discarded`)
  2. **By Category** — card/table showing count for each of the 5 categories
  3. **By Origin** — card/table showing count for each origin (`customer`, `branch`, `internal`)
  4. **By Branch** — card/table showing count per branch (only branches with incidents > 0)

**Loading state:** Show a loading indicator while fetching. The rest of the page remains intact.
**Error state:** Show an error message in the summary area without breaking the rest of the page.

### 12.7 Route Protection

All pages live under `landing/app/(protected)/incident-manager/`, inside the `(protected)` route group. The existing `(protected)/layout.tsx` wraps all children in `<AuthGuard>`. **No additional auth code is needed.**

---

## 14. Styling Guide

**Match the existing Incident Analyzer UI** (`uis/incident_analyzer/`), not the generic backoffice patterns. The incident analyzer has its own visual language that the new Incident Manager must follow for consistency.

### Layout & Container

| Pattern | Tailwind Classes | Source |
|---------|-----------------|--------|
| Page container | `mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8` | `incident-dashboard.tsx` |
| Section spacing | `space-y-5` within sections | `analysis-summary.tsx` |
| Metric cards grid | `grid gap-5 sm:grid-cols-3` | `analysis-summary.tsx` |
| Breakdown grid | `grid gap-5 lg:grid-cols-2` | `incident-dashboard.tsx` |

### Header (Hero)

| Pattern | Tailwind Classes | Source |
|---------|-----------------|--------|
| Header container | `rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-white shadow-xl md:p-8` | `incident-header.tsx` |
| Logo + badge row | `flex items-center gap-3` with `<HealthcoreLogo />` | `incident-header.tsx` |
| Badge text | `text-xs font-semibold uppercase tracking-[0.2em] text-sky-100` — content: "HealthCore Digital" | `incident-header.tsx` |
| Title | `mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl` | `incident-header.tsx` |
| Subtitle | `mt-2 max-w-3xl text-sm leading-6 text-sky-100` | `incident-header.tsx` |

### Cards & Sections

| Pattern | Tailwind Classes | Source |
|---------|-----------------|--------|
| Card | `rounded-xl border border-slate-200 bg-white p-6 shadow-sm` | `analysis-summary.tsx`, `breakdown-section.tsx` |
| Section heading | `text-sm font-bold text-sky-800` | `breakdown-section.tsx` |
| Metric value (large) | `text-3xl font-extrabold tracking-tight text-sky-800` | `analysis-summary.tsx` |
| Metric label | `text-sm text-slate-600` | `analysis-summary.tsx` |
| List item row | `flex justify-between border-b border-slate-100 pb-2 text-sm text-slate-700 last:border-0` | `analysis-summary.tsx` |
| List item value | `font-semibold text-slate-900` | `analysis-summary.tsx` |

### Progress Bars (for breakdown/summary metrics)

| Pattern | Tailwind Classes | Source |
|---------|-----------------|--------|
| Bar track | `h-2 rounded-full bg-slate-100` | `breakdown-section.tsx` |
| Bar fill (primary) | `h-2 rounded-full bg-sky-700` with `style={{ width: \`${pct}%\` }}` | `breakdown-section.tsx` |
| Bar fill (accent) | `h-1.5 rounded-full bg-teal-600` | `satisfaction-section.tsx` |
| Highlighted item | `rounded-lg px-3 py-2 border-l-4 border-teal-500 bg-sky-50` | `breakdown-section.tsx` |

### Buttons

| Pattern | Tailwind Classes | Source |
|---------|-----------------|--------|
| Primary button | `rounded-md bg-sky-700 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-sky-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300` | `export-button.tsx` |

### Forms (new — match incident analyzer card style)

| Pattern | Tailwind Classes |
|---------|-----------------|
| Form label | `text-sm font-medium text-slate-700` |
| Form input/select | `w-full rounded-lg border border-slate-300 px-3 py-2 text-sm` with focus ring |
| Textarea | Same as input, plus `min-h-[100px]` |

### Feedback Banners

| Pattern | Tailwind Classes | Source |
|---------|-----------------|--------|
| Error banner | `rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700` | `incident-dashboard.tsx` |
| Success banner | `rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700` | (match error pattern with green) |
| Warning banner | `rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700` | (match error pattern with amber) |
| Loading text | `text-sm font-medium text-sky-800` | `incident-dashboard.tsx` |

### Status Badges (new — for incident list)

| Pattern | Tailwind Classes |
|---------|-----------------|
| Status badge (open) | `rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800` |
| Status badge (in_progress) | `rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800` |
| Status badge (resolved) | `rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800` |
| Status badge (discarded) | `rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800` |

### Tables (new — for incident list, match card + list item style)

| Pattern | Tailwind Classes |
|---------|-----------------|
| Table wrapper | Inside a `rounded-xl border border-slate-200 bg-white p-6 shadow-sm` card |
| Table header | `text-left text-xs font-semibold uppercase tracking-wide text-slate-500` |
| Table row | `border-b border-slate-100` with `hover:bg-slate-50` |

### Origin Highlight (branch)

| Pattern | Tailwind Classes |
|---------|-----------------|
| Branch field highlight | `border-l-4 border-teal-500 bg-sky-50 rounded-lg px-3 py-2` on the branch field when origin = "branch" (reuses the incident analyzer highlight pattern) |

### Nav Cards (landing page)

| Pattern | Tailwind Classes |
|---------|-----------------|
| Nav card | `rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-sky-300 hover:shadow-md` |
| Nav card grid | `grid gap-5 sm:grid-cols-3` |

---

## 15. Acceptance Checklist

### Backend — Data Model
- [ ] `Incident` SQLModel defined with all required fields
- [ ] Model imported in `main.py` so table is auto-created on startup
- [ ] Valid enum values enforced for `category`, `status`, `origin`, `branch`

### Backend — API Endpoints
- [ ] `POST /api/v1/incidents` — creates incident, validates all fields, returns 400 with descriptive messages
- [ ] `GET /api/v1/incidents` — returns list with optional filters (`status`, `origin`, `branch`, `category`)
- [ ] `GET /api/v1/incidents/{id}` — returns single incident or 404
- [ ] `PATCH /api/v1/incidents/{id}/status` — validates lifecycle transitions, returns 400 on invalid transition
- [ ] `GET /api/v1/incidents/summary` — returns aggregated counts by status, category, origin, branch
- [ ] All endpoints protected by `get_current_user` auth dependency
- [ ] Unhandled exceptions return generic 500 (no stack traces)
- [ ] Validation errors return 400 with field-specific plain-language messages
- [ ] Empty database returns empty list / zero metrics (no errors)

### Backend — Seed Script
- [ ] `scripts/seed_incidents.py` reads `incidents-healthcore.csv`
- [ ] Reuses validation logic from `analysis_core.py` (valid clinics, categories, etc.)
- [ ] Inserts valid rows with `origin = "customer"`
- [ ] Maps CSV fields correctly (status mapping: OPEN→open, CLOSED→resolved, DISCARDED→discarded)
- [ ] Is idempotent — running twice does not duplicate records
- [ ] Reports invalid rows to console (count per rule, no PHI)

### Frontend — Configuration
- [ ] `@backoffice/incident-manager` alias registered in `next.config.ts`
- [ ] `@source "../../incident-manager/**/*"` added to `globals.css`
- [ ] "Incident Manager" card added to `NAV_APPS` in `nav-apps.ts`

### Frontend — API Layer
- [ ] `incident-manager/lib/incidents-api.ts` exists and uses `healthcoreFetch` — no raw `fetch` in components
- [ ] Error extraction: non-OK responses throw `Error` with the API `detail` message

### Frontend — Incident Landing (`/incident-manager`)
- [ ] Hero section with logo, title, subtitle — same gradient as backoffice landing
- [ ] 3 nav cards linking to new, list, summary
- [ ] Header (ToolToolbar) and footer (LandingFooter) present

### Frontend — Incident Form (`/incident-manager/new`)
- [ ] 5 fields: title, description, category dropdown, origin dropdown, branch dropdown
- [ ] Branch always visible and required; highlighted when origin = "branch"
- [ ] Loading indicator on submit button; button disabled during request
- [ ] Clears form + shows green confirmation on success
- [ ] Shows user-friendly error messages on 400 (field-specific where possible)
- [ ] Shows generic error on 500

### Frontend — Incident List (`/incident-manager/list`)
- [ ] Loads all incidents on mount with loading indicator
- [ ] Filters by status, origin, branch — updates API call
- [ ] Table shows title, category, status badge, origin, branch, date
- [ ] Inline status update via dropdown/buttons with valid transitions only
- [ ] Failed status update reverts visual state and shows error notification
- [ ] Empty state message when no incidents match
- [ ] Error state with retry button on fetch failure

### Frontend — Summary Dashboard (`/incident-manager/summary`)
- [ ] Fetches and displays totals by status, category, origin, branch
- [ ] Loading state while fetching
- [ ] Error state without breaking rest of page

### Auth & Build
- [ ] All pages under `(protected)` route group — unauthenticated users redirected to `/login`
- [ ] `npm run verify` passes (lint + build)
- [ ] No new npm dependencies added
- [ ] Existing Incident Analyzer remains functional and unchanged

---

## 16. Seed Data Reference

### Source file

**Path:** `incidents-healthcore.csv` (repo root, also copied at `uis/incident_analyzer/incidents-healthcore.csv`)
**Rows:** 100 (plus 1 header row)
**Encoding:** UTF-8, comma-separated

### CSV columns

| Column | Type | Example |
|--------|------|---------|
| `incident_id` | string | `HC-000001` — unique, used as idempotency key |
| `date` | string | `2024-01-13` — maps to `created_at` |
| `clinic_id` | string | `US-TX-02` — maps to `branch` |
| `country` | string | `US` — used for validation only, not stored |
| `category` | string | `ADMINISTRATIVE` — maps directly |
| `description` | string | free text — maps directly |
| `status` | string | `OPEN`, `CLOSED`, `DISCARDED` — mapped (see below) |
| `patient_id` | string | `PAT-735605` — **DO NOT store or expose** (HIPAA/GDPR) |
| `satisfaction_score` | integer or empty | `3` — not stored in new model |

### Status mapping (CSV → Incident model)

| CSV value | Incident model value |
|-----------|---------------------|
| `OPEN` | `open` |
| `CLOSED` | `resolved` |
| `DISCARDED` | `discarded` |

### Title generation

The CSV has no `title` field. The seed script must generate one per row:
- Format: `"{category} incident at {clinic_id}"` (e.g., `"ADMINISTRATIVE incident at US-TX-02"`)

### Known invalid rows (6 of 100)

The seed script must validate each row using the same rules as `analysis_core.validate_record()` and skip invalid rows. These are the 6 invalid rows in the file:

| Row | `incident_id` | Rule violated | Detail |
|-----|---------------|--------------|--------|
| 41 | `HC-000041` | Invalid clinic_id | `clinic_id = "XX-INVALID"` |
| 43 | `HC-000043` | Country/clinic mismatch | `clinic_id = "UK-LON-01"` but `country = "US"` |
| 58 | `HC-000058` | Missing category | `category` is empty |
| 63 | `HC-000063` | Empty description | `description` is empty |
| 79 | `HC-000079` | Missing patient_id | `patient_id` is empty |
| 85 | `HC-000085` | Closed, no score | `status = "CLOSED"` but `satisfaction_score` is empty |

**Result:** 94 valid rows inserted, 6 skipped with console report.

### Fields NOT carried over to the new model

- `patient_id` — protected health information, must never be stored or displayed
- `satisfaction_score` — not part of the incident manager model
- `country` — used only for validation; the `branch` (clinic_id) implicitly carries country info
- `incident_id` — used only for idempotency check; the new model uses auto-increment `id`

### Sample rows (first 5 valid records as they map to the Incident model)

```
| title                                  | description                                                    | category       | status   | origin   | branch   | created_at          |
|----------------------------------------|----------------------------------------------------------------|----------------|----------|----------|----------|---------------------|
| ADMINISTRATIVE incident at US-TX-02    | Patient registration data contains error from onboarding       | ADMINISTRATIVE | resolved | customer | US-TX-02 | 2024-01-13T00:00:00 |
| APPOINTMENT incident at UK-LON-02      | Patient not informed of appointment reschedule by clinic        | APPOINTMENT    | open     | customer | UK-LON-02| 2024-01-17T00:00:00 |
| ACCESSIBILITY incident at US-FL-01     | Patient communications sent only in English despite preference | ACCESSIBILITY  | discarded| customer | US-FL-01 | 2024-01-09T00:00:00 |
| ADMINISTRATIVE incident at UK-LON-02   | Patient unable to obtain copy of test results                  | ADMINISTRATIVE | resolved | customer | UK-LON-02| 2024-01-15T00:00:00 |
| ACCESSIBILITY incident at US-GA-01     | Online booking portal not compatible with screen reader         | ACCESSIBILITY  | open     | customer | US-GA-01 | 2024-01-20T00:00:00 |
```

### Expected seed data distribution (94 valid records)

**By category:**
| Category | Count |
|----------|-------|
| APPOINTMENT | 30 |
| BILLING | 20 |
| ACCESSIBILITY | 17 |
| CLINICAL_CARE | 14 |
| ADMINISTRATIVE | 13 |

**By status (after mapping):**
| Status | Count |
|--------|-------|
| resolved | 52 |
| open | 28 |
| discarded | 14 |

**By origin:**
| Origin | Count |
|--------|-------|
| customer | 94 |
| branch | 0 |
| internal | 0 |

**By branch (top clinics):**
| Branch | Count |
|--------|-------|
| UK-MAN-01 | 15 |
| US-GA-01 | 10 |
| US-TX-02 | 10 |
| US-GA-03 | 8 |
| UK-LON-02 | 8 |
| US-FL-01 | 7 |
| UK-LON-01 | 7 |
| US-FL-03 | 6 |
| US-TX-01 | 7 |
| US-FL-02 | 5 |
| US-TX-03 | 5 |
| US-GA-02 | 3 |
| US-FL-03 | 3 |

---

## 17. What NOT to Change

- Do NOT modify `shared/lib/healthcore-api.ts`
- Do NOT modify `landing/lib/api.ts` or `landing/components/auth/auth-guard.tsx`
- Do NOT modify the existing `uis/incident_analyzer/` module or its backend routes
- Do NOT modify any other existing feature module (`talent-tracker`, `backoffice_functions`, `supplier-directory`, `inventory`)
- Do NOT add npm dependencies
- Do NOT create a parallel auth system
- Do NOT call `fetch` directly from components — all API access through `incidents-api.ts`
- Do NOT expose patient identifiers (`patient_id`) in any frontend display or API response
