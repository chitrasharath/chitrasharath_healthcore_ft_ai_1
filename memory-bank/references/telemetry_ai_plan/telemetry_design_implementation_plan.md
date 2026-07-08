---
name: Telemetry Design (Phase 1)
overview: "Documentation-only phase: produce docs/telemetry/telemetry-plan.md and event-schemas.json grounded in real inventory/auth entities, reconciled KPIs, and the standard event envelope — no application code."
todos:
  - id: step0-branch
    content: Create feature/telemetry branch from main; confirm inventory/auth baseline matches spec reconciliation table
    status: pending
  - id: step1-baseline-audit
    content: Audit services/api inventory models/router and backoffice inventory hooks against telemetry_design_specs.md §3–§6
    status: pending
  - id: step2-telemetry-plan
    content: Write docs/telemetry/telemetry-plan.md with all 8 required sections (§7) including Reconciliation with CONTEXT (§4.1)
    status: pending
  - id: step3-event-schemas
    content: Write docs/telemetry/event-schemas.json (draft-07 envelope + per-event definitions with x-pii flags)
    status: pending
  - id: step4-consistency-pass
    content: Cross-check plan event catalog vs JSON schemas (event_type values, property allowlists, envelope fields)
    status: pending
  - id: step5-verify
    content: Validate JSON with python -m json.tool; manual checklist against spec §12 Definition of done
    status: pending
  - id: step6-docs-commit
    content: Commit on feature/telemetry with PR title [W16D46] Telemetry Design Plan
    status: pending
isProject: false
---

# Telemetry — Phase 1 (Design) Implementation Plan

**Plan file:** [`memory-bank/references/telemetry_ai_plan/telemetry_design_implementation_plan.md`](telemetry_design_implementation_plan.md)

**Requirements source:** [`telemetry_design_specs.md`](telemetry_design_specs.md)

**Branch:** `feature/telemetry` (single branch for all four phases; Phase 1 is first commit)

**Working directory:** `docs/telemetry/` (new)

**Status:** Not started — no `docs/telemetry/` folder exists yet

---

## Executive summary

HealthCore's backoffice inventory module (`uis/backoffice/inventory` via landing `:3001`) and FastAPI inventory API (`services/api/app/domains/inventory/`) are **delivered** but produce **no operational telemetry**. Leadership cannot answer jurisdiction-segmented questions about consumption volume, waste rates, or stock-out rejections without manual spreadsheet work.

Phase 1 delivers **design documentation only** — two files another developer uses to implement capture (Phase 2), storage (Phase 3), and reporting (Phase 4) without ambiguity:

1. `docs/telemetry/telemetry-plan.md` — KPIs, flows, envelope, event catalog, risks
2. `docs/telemetry/event-schemas.json` — JSON Schema draft-07 definitions

No servers, packages, or instrumentation code in this phase.

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Entity names | **Code wins** — `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption` (not Product/InboundOrder/DispensingOrder) |
| KPIs | Three reconciled KPIs from spec §4 (consumption rate, waste rate, insufficient-stock rejection rate) |
| Dropped events | `stock_threshold_triggered`, `direct_stock_edit_rejected`, `emergency_dispensing_flagged` — document in Risks/exclusions |
| `product_created` | Design-only (API exists, no UI); flag as future instrumentation |
| Envelope | Include **both** `requestId` and `service: "backoffice"` |
| `userId` | Opaque TinyDB user id as **string** (`str(user.id)` — matches inventory `user_uuid` convention; not a UUID v4) |
| `jurisdiction` | Derived client-side from `MedicalSupply.country`: `US`→`us`, `UK`→`uk` |
| Branch | `feature/telemetry` — sequential commits per phase |
| Supabase (downstream) | Reuse **`milestone5_inventory`** project (locked for Phases 3–4) |
| Report auth (downstream) | `GET /telemetry/report` will be **JWT-protected** (locked for Phase 4) |

---

## Current codebase baseline (spec reconciliation)

Exploration confirms the spec's reconciliation table is accurate:

| Spec claim | Codebase state | Path |
|------------|----------------|------|
| `MedicalSupply` with `country` US/UK | Confirmed | `inventory/models.py` |
| `SupplyConsumption.consumption_type` ∈ `{clinical_use, expiry_waste}` | Confirmed + validated | `inventory/schemas.py` validator |
| No `emergency`, no `clinical_context` | Confirmed | — |
| Stock computed, not stored | Confirmed | `inventory/router.compute_stock()` |
| Insufficient stock → HTTP 400 | Confirmed | `create_outbound_order` detail message |
| `POST /inventory/products` exists, no create UI | Confirmed | `inventory-api.ts` has GET + order POSTs only |
| Products/orders lists not clinic-scoped | Confirmed | `list_products`, `list_orders` return all |
| `clinic_id` is integer | Confirmed | models + `CLINICS` constants (ids 1–6; seed uses 10) |
| Auth: login, `/auth/me`, JWT in localStorage | Confirmed | `auth/router.py`, `landing/lib/api.ts` |
| No telemetry domain or docs | Confirmed | grep finds specs only |

**Instrumentation call sites (for Phase 2 plan reference — document in Flow mapping):**

| Future `event_type` | Nearest code location |
|---------------------|----------------------|
| `supply_delivery_created` | `inventory/lib/inbound-form-logic.ts` → `submitInboundOrder` success |
| `supply_consumption_created` | `inventory/lib/outbound-form-logic.ts` → `submitOutboundOrder` success |
| `supply_consumption_failed` | `outbound-form-logic` catch path / `classifyOutboundError` |
| `supply_list_viewed` | `inventory/hooks/use-products.ts` after `listProducts` resolves |
| `orders_list_viewed` | `inventory/hooks/use-orders.ts` after `listOrders` resolves |
| `user_login_succeeded` | `landing/hooks/use-login-form.ts` after 200 |
| `user_login_failed` | `use-login-form.ts` failure branches |
| `session_expired` | `shared/lib/healthcore-api.ts` 401 redirect (and `landing/lib/api.ts` for non-inventory routes) |

---

## Implementation steps

### Step 1 — Create `docs/telemetry/` folder

```bash
mkdir -p docs/telemetry
```

No other repo changes in this step.

### Step 2 — Write `telemetry-plan.md`

Use the eight sections required by spec §7. Suggested outline with content guidance:

#### 2.1 Executive summary

State what ops cannot answer today: per-clinic consumption trends, US vs UK waste rates, stock-out rejection patterns by supply/clinic. Reference the inventory backoffice as the primary instrumentation surface.

#### 2.2 KPI analysis (three KPIs)

For each KPI from spec §4, use the template: **definition → data components → system touchpoint → why telemetry helps**.

| KPI | Primary `event_type` sources |
|-----|------------------------------|
| Supply consumption rate | `supply_consumption_created` |
| Supply waste rate | `supply_consumption_created` (`consumption_type`) |
| Insufficient-stock rejection rate | `supply_consumption_failed` |

#### 2.3 Reconciliation with CONTEXT (§4.1 — mandatory)

Include the three-row mapping table from spec §4.1 verbatim (CONTEXT KPI → reconciled KPI → why re-grounded).

#### 2.4 Flow mapping

Mermaid or numbered flow: login → hub → inventory products → inbound/outbound forms → success/failure. Mark ≥5 inventory instrumentation points and note list views are global (no `clinic_id` on view events).

#### 2.5 Backoffice opportunities

Document the three auth events (`user_login_succeeded`, `user_login_failed`, `session_expired`) with stream/batch rationale.

#### 2.6 Event Envelope

Reproduce spec §5 table. Note `schemaVersion: "1.0.0"`.

#### 2.7 Event catalog

For **every** event in spec §6:

- Golden-rule sentence ("When X happens, we record Y so Z")
- Property allowlist table
- PII column (`false` for all)
- Stream vs batch with business justification

Include `product_created` as design-only / API-only.

#### 2.8 High-frequency strategy

- Auth failures + `session_expired` → stream
- Inventory → batch
- List views: document 30s debounce recommendation; Phase 2 batching (10s / 20 events) is primary guard

#### 2.9 Risks and exclusions

- HIPAA / UK GDPR: no patient identifiers
- `userId` opaque string only
- Three dropped events with reasons (spec §6 notes)
- Self-reported `userId` on unauthenticated ingest endpoint (Phase 2 design note for downstream)

### Step 3 — Write `event-schemas.json`

Structure:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "eventEnvelope": { ... },
    "supply_delivery_created": { ... },
    ...
  }
}
```

**Envelope definition** must require: `eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId`, `service`, `properties`.

**Per-event definitions:**

- `event_type` as `const`
- `properties` keys exactly match spec §6 allowlists
- `additionalProperties: false` on `properties`
- `x-pii: false` on each event definition

Events to define (8 instrumentable + 1 design-only):

1. `supply_delivery_created`
2. `supply_consumption_created`
3. `supply_consumption_failed`
4. `supply_list_viewed`
5. `orders_list_viewed`
6. `product_created` (design-only annotation in plan; still schema-defined for completeness)
7. `user_login_succeeded`
8. `user_login_failed`
9. `session_expired` (empty `properties` object)

Property types (locked):

| Property | Type | Events |
|----------|------|--------|
| `supply_id` | integer | delivery, consumption, failed |
| `quantity` | integer | delivery, consumption |
| `clinic_id` | integer | delivery, consumption, failed |
| `jurisdiction` | string enum `us` \| `uk` | delivery, consumption, failed, product_created, login_succeeded (optional) |
| `consumption_type` | string enum `clinical_use` \| `expiry_waste` | consumption_created |
| `error_code` | string | consumption_failed |
| `item_count` | integer | list views |
| `reason` | string enum per event | login_failed |
| `category` | string | product_created |

### Step 4 — Consistency pass

Checklist:

- [ ] Every `event_type` in plan appears in JSON with matching property keys
- [ ] Envelope fields identical in plan §6 and JSON `eventEnvelope`
- [ ] Stream/batch decisions match between plan and auth/inventory sections
- [ ] PII strategy stated in plan matches `x-pii: false` on all JSON definitions
- [ ] Reconciliation table present and matches spec §4.1

### Step 5 — Verification

```bash
python3 -m json.tool docs/telemetry/event-schemas.json > /dev/null
```

Manual review against spec §12 Definition of done (all 7 items).

---

## PR checklist

- **Title:** `[W16D46] Telemetry Design Plan`
- **Description must include:**
  - One line per reconciled KPI
  - Count of events designed (8 instrumentable + 1 design-only)
  - Hardest design decision: reconciling CONTEXT KPIs to observable code paths (no threshold/emergency fields)

---

## Definition of done (maps to spec §12)

- [ ] 3 KPIs grounded in real entities with data sources
- [ ] ≥5 inventory instrumentation points + ≥2 auth opportunities documented
- [ ] Consistent envelope with `requestId` and `service`
- [ ] Every event: golden-rule + allowlist + PII note
- [ ] `event-schemas.json` valid draft-07, consistent with plan
- [ ] Stream/batch justified
- [ ] Risks/exclusions: HIPAA/UK GDPR + three dropped events

---

## Handoff to Phase 2

Phase 2 (`telemetry_frontend_implementation_plan.md`) consumes:

- Event catalog and envelope from this phase (no renames)
- `event-schemas.json` as validation reference for Pydantic model shape
- Jurisdiction derivation rule documented in plan §6 notes
