# SPECS — Supplier Directory · HealthCore Digital

> **Milestone:** 09 — Lightweight Storage API
> **Backend:** `services/api` (FastAPI + TinyDB + Pydantic)
> **Frontend:** `uis/supplier_directory` (Next.js 16 + TypeScript + Tailwind CSS v4)
> **Context source:** `CONTEXT-healthcore.md`
> **Status:** Starts from scratch — no starter code

---

## 1. Project overview

HealthCore Digital operates 12 outpatient clinics across the USA (Texas, Florida, Georgia) and the UK (London, Manchester). Their procurement team currently manages supplier information in scattered departmental spreadsheets. This project replaces those spreadsheets with a centralized supplier registry API and frontend directory.

The tech lead (James Osei, CTO) has chosen **TinyDB** as a deliberate lightweight database — no SQL, minimal resources, deployable immediately — with a planned future migration to Postgres once the ORM is ready. The system must start with real data from day one via a seeder script and must reject any input that does not match the defined structure.

Key stakeholders: Diane Foster (VP People), Claire Whitfield (Chief Compliance Officer).

---

## 2. Monorepo location and structure

Work inside the existing monorepo fork. Two directories:

```
services/api/          ← Backend (FastAPI + TinyDB + Pydantic)
uis/supplier_directory/  ← Frontend (Next.js 16 App Router)
```

**Important:** `services/api/` may already contain incident analyzer routes from a prior milestone. Supplier routes must coexist alongside any existing routes without breaking them. If `services/api/` does not yet exist, create it from scratch.

---

## 3. Tech stack

### Backend

| Layer        | Technology           | Notes                                        |
|-------------|----------------------|----------------------------------------------|
| Framework   | FastAPI              | Existing pattern in monorepo                 |
| Database    | TinyDB               | Lightweight JSON document store; no SQL      |
| Validation  | Pydantic v2          | All input validated before touching database |
| Runtime     | Python 3.x with `uv` | Seeder runs via `uv run seed`                |

### Frontend

| Layer       | Technology                    | Notes                                                  |
|------------|-------------------------------|--------------------------------------------------------|
| Framework  | Next.js 16 (App Router)       | Consistent with milestones 3 and 4                     |
| Language   | TypeScript                    | Strict typing throughout                               |
| Styling    | Tailwind CSS v4 (PostCSS)     | No CDN; build pipeline only                            |
| Components | React 19 functional           | `const` declarations, ≤80 lines per component file     |
| UI libs    | None (custom components only) | No third-party UI component libraries                  |
| Design     | Mobile-first responsive       | Accessibility and responsive design required throughout |

---

## 4. Data model

### 4.1 Supplier fields

Define a Pydantic `Supplier` model with these exact field names and types. Field names, valid categories, allowed statuses, and enum values **must match CONTEXT-healthcore.md exactly**. A generic implementation that ignores the company context will not be accepted.

| Field                   | Type                                 | Required | Description                                                                               |
|------------------------|--------------------------------------|----------|-------------------------------------------------------------------------------------------|
| `name`                 | string                               | Yes      | Supplier or platform trade name                                                           |
| `country`              | string                               | Yes      | Contract country: `"USA"` or `"UK"` only                                                  |
| `categories`           | list of strings                      | Yes      | Minimum 1 item; each must be from `VALID_CATEGORIES`                                     |
| `monthly_rate`         | float                                | Yes      | Current monthly cost; must be > 0 (reject zero and negatives)                             |
| `currency`             | string                               | Yes      | `"USD"` for USA suppliers, `"GBP"` for UK suppliers                                       |
| `rate_updated_at`      | datetime                             | No       | **System-generated** — never sent by client; set on rate update                           |
| `status`               | string                               | Yes      | `"active"` or `"suspended"` only; use `Enum` or field validator                           |
| `compliance_agreement` | string or None                       | No       | `"BAA"`, `"DPA"`, `"both"`, or `None`                                                     |
| `contract_renewal_date`| string or null                       | No       | Format `YYYY-MM-DD`                                                                       |
| `contact_email`        | string or null                       | No       | Supplier account manager email                                                            |
| `notes`                | string or null                       | No       | Internal notes                                                                            |

### 4.2 Valid categories

```python
VALID_CATEGORIES = [
    "medical_supplies",
    "laboratory_services",
    "pharmaceutical",
    "clinical_software",
    "it_infrastructure",
    "hr_and_payroll_software",
    "cleaning_and_facilities",
    "patient_communication",
    "billing_and_coding_software",
    "training_platforms"
]
```

### 4.3 Valid statuses

```python
VALID_STATUSES = ["active", "suspended"]
```

### 4.4 Pydantic model architecture

Create **separate input and response models**:

- **Input model** (for `POST /api/v1/suppliers`): accepts client-provided fields only. `rate_updated_at` is **not** included — it is system-generated. `currency` may be auto-derived from `country` or validated against it.
- **Response model** (for all responses): includes all fields plus the TinyDB-assigned `id` (typically `doc_id`) and `rate_updated_at`.
- **Rate update model** (for `PATCH .../rate`): accepts only `monthly_rate`.
- **Status update model** (for `PATCH .../status`): accepts only `status`.

### 4.5 Validation rules (Pydantic layer — reject before database)

1. `country` must be exactly `"USA"` or `"UK"`. Reject anything else with `422`.
2. `status` must be exactly `"active"` or `"suspended"`. Reject anything else with `422`.
3. `monthly_rate` must be a positive number (`> 0`). Reject zero, negatives, and non-numeric with `422`.
4. `categories` must be a non-empty list. Every item must be in `VALID_CATEGORIES`. Reject unknown categories with `422`.
5. `currency` must match `country`: `"USA"` → `"USD"`, `"UK"` → `"GBP"`. Reject mismatched combinations with `422`.
6. `compliance_agreement`, if provided, must be one of: `"BAA"`, `"DPA"`, `"both"`, or `None`.

---

## 5. Database (TinyDB)

- Use TinyDB as the JSON document store.
- Store the database file at a consistent path within `services/api/` (e.g., `db.json` or `data/suppliers.json`).
- TinyDB assigns its own integer `doc_id` to each document — use this as the supplier ID in API responses and URL paths.
- No SQL, no migrations. TinyDB reads/writes a flat JSON file.

---

## 6. Seeder

### 6.1 Script: `seed.py`

Create a `seed.py` script in `services/api/` that loads all 15 suppliers from `CONTEXT-healthcore.md` into TinyDB.

### 6.2 Execution

The seeder **must be executable** with:

```bash
uv run seed
```

This means configuring the appropriate script entry point (e.g., in `pyproject.toml` under `[project.scripts]`) so `uv run seed` works without modifying the code.

### 6.3 Idempotency

- If the database already has data, the seeder **must not create duplicates**.
- Check before inserting (e.g., by supplier `name` or another unique identifier).
- Print to the console how many records were inserted when finished.

### 6.4 Seed data

Load exactly these 15 suppliers. The data below is the authoritative source:

```python
SUPPLIERS_SEED = [
    {
        "name": "McKesson Medical Supplies",
        "country": "USA",
        "categories": ["medical_supplies"],
        "monthly_rate": 4200.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2025-06-30",
        "contact_email": "accounts@mckesson.com",
        "notes": "Primary clinical supplies provider for the 9 USA clinics."
    },
    {
        "name": "NHS Supply Chain",
        "country": "UK",
        "categories": ["medical_supplies"],
        "monthly_rate": 2800.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "enquiries@supplychain.nhs.uk"
    },
    {
        "name": "Quest Diagnostics",
        "country": "USA",
        "categories": ["laboratory_services"],
        "monthly_rate": 3100.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2025-12-15",
        "contact_email": "business@questdiagnostics.com",
        "notes": "Laboratory processing for Texas and Florida clinics."
    },
    {
        "name": "Synnovis UK",
        "country": "UK",
        "categories": ["laboratory_services"],
        "monthly_rate": 1950.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "contracts@synnovis.co.uk"
    },
    {
        "name": "Epic Systems",
        "country": "USA",
        "categories": ["clinical_software"],
        "monthly_rate": 8500.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2026-01-01",
        "contact_email": "enterprise@epic.com",
        "notes": "Primary EHR for USA clinics. Long-term contract."
    },
    {
        "name": "EMIS Health",
        "country": "UK",
        "categories": ["clinical_software"],
        "monthly_rate": 3400.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contract_renewal_date": "2025-09-01",
        "contact_email": "accounts@emishealth.com",
        "notes": "EHR for London and Manchester clinics."
    },
    {
        "name": "Availity",
        "country": "USA",
        "categories": ["billing_and_coding_software"],
        "monthly_rate": 1200.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contact_email": "enterprise@availity.com",
        "notes": "Eligibility verification and claims submission platform."
    },
    {
        "name": "Twilio",
        "country": "USA",
        "categories": ["patient_communication"],
        "monthly_rate": 680.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contract_renewal_date": "2025-10-31",
        "contact_email": "healthcare@twilio.com",
        "notes": "Automated SMS and email for appointment reminders."
    },
    {
        "name": "AWS Healthcare",
        "country": "USA",
        "categories": ["it_infrastructure"],
        "monthly_rate": 5600.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": "BAA",
        "contact_email": "aws-health@amazon.com",
        "notes": "Primary cloud infrastructure. BAA signed and audited annually."
    },
    {
        "name": "Microsoft Azure UK",
        "country": "UK",
        "categories": ["it_infrastructure"],
        "monthly_rate": 2100.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "enterprise@microsoft.com"
    },
    {
        "name": "Workday",
        "country": "USA",
        "categories": ["hr_and_payroll_software"],
        "monthly_rate": 2400.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": None,
        "contract_renewal_date": "2025-08-15",
        "contact_email": "enterprise@workday.com",
        "notes": "HRIS for the entire USA workforce. Does not handle PHI."
    },
    {
        "name": "Sage Payroll UK",
        "country": "UK",
        "categories": ["hr_and_payroll_software"],
        "monthly_rate": 890.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "business@sage.co.uk"
    },
    {
        "name": "ServiceMaster Clean",
        "country": "USA",
        "categories": ["cleaning_and_facilities"],
        "monthly_rate": 3800.0,
        "currency": "USD",
        "status": "active",
        "compliance_agreement": None,
        "contact_email": "healthcare@servicemaster.com",
        "notes": "Clinical cleaning for the 9 USA locations."
    },
    {
        "name": "Healthstream LMS",
        "country": "USA",
        "categories": ["training_platforms"],
        "monthly_rate": 1100.0,
        "currency": "USD",
        "status": "suspended",
        "compliance_agreement": "BAA",
        "contact_email": "enterprise@healthstream.com",
        "notes": "Suspended. Diane is evaluating replacing it with an in-house solution."
    },
    {
        "name": "Nuffield Health Supplies",
        "country": "UK",
        "categories": ["medical_supplies", "cleaning_and_facilities"],
        "monthly_rate": 1650.0,
        "currency": "GBP",
        "status": "active",
        "compliance_agreement": "DPA",
        "contact_email": "procurement@nuffieldhealth.com"
    }
]
```

Note: one supplier (Healthstream LMS) has `status: "suspended"`. One supplier (Nuffield Health Supplies) has multiple categories. Two suppliers (Workday, ServiceMaster Clean) have `compliance_agreement: None`. Optional fields omitted from a seed record should be stored as `None`.

---

## 7. API endpoints

Base path: `/api/v1/suppliers` — consistent with the existing versioned routing pattern (the incident analyzer uses `/api/v1/incidents/`). Define the supplier router in `domains/procurement/suppliers/routes.py` and register it in `main.py` with prefix `/api/v1/suppliers`.

### 7.1 `POST /api/v1/suppliers` — Register a new supplier

- **Request body:** Input model fields (see §4.4). `rate_updated_at` is not accepted from the client.
- **Validation:** Apply all rules from §4.5. Reject invalid input with `422 Unprocessable Entity` and a descriptive error message.
- **Behavior:** Insert into TinyDB. Return the created supplier with TinyDB-assigned ID.
- **Response:** `201 Created` with the full supplier response model (including `id`).

### 7.2 `GET /api/v1/suppliers` — List all suppliers

- **Behavior:** Return every supplier in the database.
- **Response:** `200 OK` with a list of supplier response models.

### 7.3 `GET /api/v1/suppliers?country={country}` — Filter suppliers by country

- **Query parameter:** `country` — `"USA"` or `"UK"`.
- **Behavior:** Return only suppliers whose `country` matches the parameter value.
- **Response:** `200 OK` with a filtered list of supplier response models.

### 7.4 `GET /api/v1/suppliers?category={category}` — Filter suppliers by product category

- **Query parameter:** `category` — Must be a value from `VALID_CATEGORIES`.
- **Behavior:** Return only suppliers whose `categories` list contains the parameter value.
- **Response:** `200 OK` with a filtered list of supplier response models.

> **Implementation note:** Endpoints 7.2–7.4 can share a single route handler on `GET /api/v1/suppliers` with optional query parameters. When no parameters are provided, return all. When `country` is provided, filter by country. When `category` is provided, filter by category. Both parameters may be combined. The tech lead considers these two search capabilities non-negotiable.

### 7.5 `GET /api/v1/suppliers/{id}` — Get supplier detail

- **Path parameter:** `id` — TinyDB document ID (integer).
- **Behavior:** Look up the supplier by ID.
- **Response:** `200 OK` with the supplier response model, or `404 Not Found` if the ID does not exist.

### 7.6 `PATCH /api/v1/suppliers/{id}/rate` — Update supplier rate

- **Path parameter:** `id` — TinyDB document ID.
- **Request body:** `{ "monthly_rate": <float> }`
- **Validation:** `monthly_rate` must be > 0. Reject zero, negatives with `422`.
- **Behavior:** Update the supplier's `monthly_rate` and automatically record `rate_updated_at` with the current timestamp (server-side, not client-provided). This is critical for Claire's audit trail.
- **Response:** `200 OK` with the updated supplier response model, or `404 Not Found` if ID does not exist.

### 7.7 `PATCH /api/v1/suppliers/{id}/status` — Activate or suspend a supplier

- **Path parameter:** `id` — TinyDB document ID.
- **Request body:** `{ "status": "<string>" }`
- **Validation:** `status` must be exactly `"active"` or `"suspended"`. Reject any other value with `422`.
- **Behavior:** Update the supplier's status in TinyDB.
- **Response:** `200 OK` with the updated supplier response model, or `404 Not Found` if ID does not exist.

### 7.8 `DELETE /api/v1/suppliers/{id}` — Suspend a supplier

- **Path parameter:** `id` — TinyDB document ID.
- **Behavior:** Do **not** remove the supplier from TinyDB. Instead, set the supplier's `status` to `"suspended"`. This preserves the record for regulatory audits — HealthCore operates in a compliance environment where an audit may ask which suppliers were used in a given period.
- **Response:** `200 OK` with the updated supplier response model (showing `status: "suspended"`), or `404 Not Found` if the ID does not exist.

---

## 8. Business constraints (enforced in API)

1. **Currency locked to country:** `"USA"` → `"USD"`, `"UK"` → `"GBP"`. The API rejects inconsistent combinations with `422`.
2. **Rate traceability:** Every update to `monthly_rate` must record `rate_updated_at` with the current server timestamp. Claire uses this for audits.
3. **Suspension, not deletion:** Suppliers are never removed from the directory — they are suspended. The `DELETE` endpoint sets `status` to `"suspended"` rather than deleting the record. Preserving history is required due to HealthCore's regulatory environment.
4. **Compliance agreement:** The `compliance_agreement` field is optional. Suppliers with categories `clinical_software`, `it_infrastructure`, `patient_communication`, or `billing_and_coding_software` *should* have it recorded — but this is a registration responsibility, not an automatic API validation. Do **not** reject a supplier missing `compliance_agreement`.
5. **No empty database:** The seeder must load all 15 suppliers on startup. The demo must never show an empty directory.

---

## 9. Backend file structure (suggested)

```
services/api/
├── pyproject.toml              # Dependencies + [project.scripts] for `uv run seed`
├── main.py                     # FastAPI app entry point (registers domain routers)
├── seed.py                     # Seeder script
├── domains/
│   ├── reporting/
│   │   └── incidents/          # Existing incident analyzer domain
│   └── procurement/
│       └── suppliers/
│           ├── models.py       # Pydantic models (input, response, rate update, status update)
│           ├── routes.py       # All /api/v1/suppliers endpoints
│           └── database.py     # TinyDB connection/instance for suppliers
└── db.json                     # TinyDB data file (created at runtime, gitignored)
```

This follows the existing two-level domain nesting pattern: `domains/{domain_group}/{domain}`. The incident analyzer lives at `domains/reporting/incidents` — supplier endpoints belong at `domains/procurement/suppliers`. Register the supplier router in `main.py` alongside the existing incident router without breaking it.

---

## 10. Frontend specification

### 10.1 App setup

Create a new standalone Next.js 16 application at `uis/supplier_directory/` using:
- App Router
- TypeScript
- Tailwind CSS v4 (PostCSS build pipeline, no CDN)
- React 19 functional components

This is a **standalone app** for now. It will not have its own navigation menu linking to other apps. Navigation into this app will be added later when the backoffice landing page is created to serve as the entry point for all internal tools (alongside `uis/backoffice/backoffice_functions`, `uis/incident_analyzer`, etc.).

### 10.2 Visual design — match incident analyzer

The supplier directory must use the **same color palette, typography, and styling patterns** as the existing `uis/incident_analyzer` app to maintain visual consistency across HealthCore internal tools. Before building any UI, reference the incident analyzer's:
- Color palette (background, surface, accent, text, and status colors)
- Typography (font families, sizes, weights, heading hierarchy)
- Component styling (cards, tables, buttons, badges, form inputs, spacing)
- Layout patterns (page structure, section padding, responsive breakpoints)

Copy or mirror the relevant Tailwind theme values and CSS custom properties from `uis/incident_analyzer` so both apps feel like part of the same product family.

### 10.3 Supplier directory page

Create a supplier directory page as the primary route (`/`). This page displays the full supplier list, filter controls, and access to the add-supplier form.

### 10.4 Supplier list display

Display the full list of suppliers in a **table or list** showing these fields per row:
- Name
- Country
- Categories (display all; a supplier can have multiple)
- Current monthly rate (with currency symbol: `$` for USD, `£` for GBP)
- `rate_updated_at` timestamp (showing when the rate was last changed — required for Claire's audit visibility)
- Status (with visual distinction — see §10.8)

### 10.5 Filtering

Provide filter controls for:
- **Country:** filter by `"USA"` or `"UK"` (or show all)
- **Category:** filter by product category (from `VALID_CATEGORIES`)

Filters must update the displayed list **without reloading the page** (client-side filtering of fetched data, or re-fetching with query parameters — either is acceptable as long as no full page reload occurs).

### 10.6 Add new supplier form

Implement a form that consumes `POST /api/v1/suppliers`:
- Collect all required fields: name, country, categories (multi-select from `VALID_CATEGORIES`), monthly_rate, currency, status.
- Optional fields: compliance_agreement, contract_renewal_date, contact_email, notes.
- **Compliance agreement prompting:** When the selected categories include `clinical_software`, `it_infrastructure`, `patient_communication`, or `billing_and_coding_software`, the form should surface the `compliance_agreement` field prominently and indicate it should be recorded. This is a UI-level prompt to guide the registrant — the API does not enforce it, but Claire's compliance team expects it to be filled in for these supplier types.
- On successful creation, add the new supplier to the displayed list immediately.
- If the API rejects the input (422), **display the error message** returned by the API to the user. Do not silently fail.

### 10.7 Update supplier rate

Allow updating a supplier's `monthly_rate` from the interface:
- Provide an inline edit control, modal, or dedicated UI element per row.
- Call `PATCH /api/v1/suppliers/{id}/rate` with the new rate.
- Reflect the updated rate **and** the new `rate_updated_at` timestamp in the list **immediately** after the API responds successfully. Every rate change must visibly show when it was last updated.

### 10.8 Toggle supplier status

Allow changing a supplier's status (activate / suspend):
- Provide a **visible control on each row** or in a detail view (toggle, button, or dropdown).
- Call `PATCH /api/v1/suppliers/{id}/status`.
- Update the displayed status immediately after the API responds.

### 10.9 Visual status distinction

**Visually distinguish active suppliers from suspended ones.** Examples:
- Color-coded badge (e.g., green for active, amber/red for suspended)
- Differentiated row background or text style
- Status icon

The suspended state must be immediately recognizable at a glance.

### 10.10 API integration patterns

- Use `async/await` for all API calls (consistent with milestone 3 patterns).
- Handle **loading**, **success**, and **error** states explicitly.
- Use the backend's base URL for all fetch calls (configurable, e.g., via environment variable or constant).
- CORS must be configured on the FastAPI backend to allow requests from the frontend dev server.

---

## 11. Frontend component constraints

Per monorepo conventions:
- Every component file must be **≤80 lines** and use **`const` functional components**.
- No third-party UI component libraries. Build all UI elements (tables, forms, badges, buttons, filters) as custom components.
- All styling via Tailwind CSS utility classes. No custom CSS unless absolutely necessary.
- Mobile-first responsive design throughout.
- Accessibility: semantic HTML, keyboard navigability, appropriate ARIA attributes.

---

## 12. CORS configuration

The FastAPI backend must allow cross-origin requests from the frontend development server. Add CORS middleware to `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 13. Verification checklist

### Backend

- [ ] `uv run seed` loads all 15 suppliers into TinyDB without duplicates and prints insert count
- [ ] Running `uv run seed` a second time inserts 0 records (idempotent)
- [ ] `POST /api/v1/suppliers` with valid data returns `201` and the created supplier with an `id`
- [ ] `POST /api/v1/suppliers` with missing `country` returns `422`
- [ ] `POST /api/v1/suppliers` with `country: "USA"` and `currency: "GBP"` returns `422`
- [ ] `POST /api/v1/suppliers` with `monthly_rate: 0` returns `422`
- [ ] `POST /api/v1/suppliers` with `monthly_rate: -50` returns `422`
- [ ] `POST /api/v1/suppliers` with `status: "deleted"` returns `422`
- [ ] `POST /api/v1/suppliers` with `categories: []` (empty list) returns `422`
- [ ] `POST /api/v1/suppliers` with `categories: ["unknown_thing"]` returns `422`
- [ ] `GET /api/v1/suppliers` returns all 15 seeded suppliers
- [ ] `GET /api/v1/suppliers?country=USA` returns only USA suppliers
- [ ] `GET /api/v1/suppliers?category=clinical_software` returns only suppliers with that category
- [ ] `GET /api/v1/suppliers/{id}` with a valid ID returns the supplier
- [ ] `GET /api/v1/suppliers/{id}` with a nonexistent ID returns `404`
- [ ] `PATCH /api/v1/suppliers/{id}/rate` with `monthly_rate: 5000` updates the rate and sets `rate_updated_at`
- [ ] `PATCH /api/v1/suppliers/{id}/rate` with `monthly_rate: 0` returns `422`
- [ ] `PATCH /api/v1/suppliers/{id}/rate` with `monthly_rate: -100` returns `422`
- [ ] `PATCH /api/v1/suppliers/{id}/status` with `status: "suspended"` updates the status
- [ ] `PATCH /api/v1/suppliers/{id}/status` with `status: "archived"` returns `422`
- [ ] `DELETE /api/v1/suppliers/{id}` with a valid ID suspends the supplier (sets status to `"suspended"`, does not remove the record)
- [ ] `DELETE /api/v1/suppliers/{id}` with a nonexistent ID returns `404`

### Frontend

- [ ] Supplier directory is a standalone app at `uis/supplier_directory/` with primary route `/`
- [ ] Visual design (colors, typography, component styles) matches the `uis/incident_analyzer` app
- [ ] Full supplier list displays with name, country, categories, rate, `rate_updated_at`, and status columns
- [ ] Country filter shows only USA or UK suppliers without page reload
- [ ] Category filter shows only suppliers matching the selected category without page reload
- [ ] New supplier form submits to the API and adds the supplier to the list on success
- [ ] New supplier form surfaces `compliance_agreement` prominently when categories include `clinical_software`, `it_infrastructure`, `patient_communication`, or `billing_and_coding_software`
- [ ] New supplier form displays the API error message on `422` rejection
- [ ] Rate update control modifies the rate and reflects both the new rate and `rate_updated_at` timestamp immediately
- [ ] Status toggle changes active ↔ suspended and reflects the change immediately
- [ ] Active and suspended suppliers are visually distinguishable (badge, color, or style)
- [ ] All components are ≤80 lines, `const` functional, no third-party UI libraries
- [ ] Layout is responsive (mobile-first) and accessible

---

## 14. Dependencies

### Backend (`pyproject.toml`)

Required packages:
- `fastapi`
- `uvicorn`
- `tinydb`
- `pydantic` (v2)

### Frontend (`package.json`)

Required packages:
- `next` (v16)
- `react` / `react-dom` (v19)
- `typescript`
- `tailwindcss` (v4)
- `@tailwindcss/postcss`

---

## 15. Development workflow

1. **Seed the database:**
   ```bash
   cd services/api
   uv run seed
   ```

2. **Start the API server:**
   ```bash
   cd services/api
   uv run uvicorn main:app --reload --port 8000
   ```

3. **Start the frontend:**
   ```bash
   cd uis/supplier_directory
   npm run dev
   ```

4. **Verify the frontend connects** to `http://localhost:8000` (or configured API base URL) and displays all 15 seeded suppliers.
