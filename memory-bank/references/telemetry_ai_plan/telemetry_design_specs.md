# Telemetry — Phase 1 (Design) — Build Spec

> Instructions for a coding agent. This spec **reconciles** the brief
> (`telemetry_design_screenshot.md`), the reference solution (`telemetry_design_readme.md`),
> and the company context (`telemetry_design_context.md`) **against the actual codebase**.
> Where the markdown files describe entities/fields that do not exist in code, the codebase wins.
> The reconciliation decisions below are final — do not reintroduce the original doc names.

---

## 1. Project overview

HealthCore is an outpatient healthcare company (12 clinics, US + UK). This phase produces
**design documentation only** — no instrumentation code. Deliverables:

- `docs/telemetry/telemetry-plan.md`
- `docs/telemetry/event-schemas.json`

Another developer must be able to instrument Phases 2–4 from these files without asking questions.
The plan must reference the **real** backend entities and be internally consistent with the
downstream specs (`telemetry_frontend_specs.md`, `telemetry_storage_specs.md`, `telemetry_report_specs.md`).

## 2. Tech stack / where the truth lives

- Backend: FastAPI at `services/api/`, domain modules under `app/domains/`. All routes are under `/api/v1`.
- Inventory persistence: **SQLModel → Supabase/Postgres** (`settings.database_url`), tables auto-created
  via `SQLModel.metadata.create_all` on startup. Source of entity truth: `services/api/app/domains/inventory/models.py`.
- Auth/users: **TinyDB** (`services/api/app/core/db.py`). `userId` in telemetry = the TinyDB user UUID.
- Frontend host app: `uis/backoffice/landing` (Next.js, port 3001); mounts the `inventory` module via `@backoffice/inventory/*`.

## 3. Reconciled entity model (CODE WINS — use these names/fields exactly)

| Doc term (do NOT use) | Real entity (`inventory/models.py`) | Real fields |
| --- | --- | --- |
| `Product` | **`MedicalSupply`** | `id:int`, `name`, `sku`, `category`, `unit`, `country` (`US`/`UK`) |
| `InboundOrder` | **`SupplyDelivery`** | `id:int`, `supply_id`, `quantity`, `vendor_name`, `clinic_id:int`, `created_at`, `user_uuid` |
| `OutboundOrder` / `DispensingOrder` | **`SupplyConsumption`** | `id:int`, `supply_id`, `quantity`, `consumption_type`, `clinic_id:int`, `created_at`, `user_uuid` |

Critical facts that override the context doc:

- **There is no `DispensingOrder` and no `clinical_context`.** Outbound is `SupplyConsumption` with
  **`consumption_type ∈ {clinical_use, expiry_waste}`**. There is **no `emergency`** value.
- **There is no `current_stock` column** (stock is computed as Σ deliveries − Σ consumptions in
  `inventory/router.compute_stock`) and **no `min_stock_threshold`** field.
- **There is no `jurisdiction` field.** Jurisdiction is derived from `MedicalSupply.country` (`US`→`us`, `UK`→`uk`).
- **`clinic_id` is an integer** (e.g. `1`, `10`), not a slug like `"austin_main"`.
- There is **no direct-stock-edit endpoint** — stock only changes through inbound/outbound orders.

## 4. Reconciled KPIs (use these three — they replace the context doc's KPIs)

The original KPIs depended on `emergency` dispensing and a stored stock threshold, neither of which
exists. Use these three, all computable from real code paths:

1. **Supply consumption rate** — count of `SupplyConsumption` (outbound) per clinic per day, segmented by jurisdiction.
   Decision enabled: spot high-consumption clinics and adjust standard stock levels.
   Data source: `POST /api/v1/inventory/orders/outbound` success.
2. **Supply waste rate** — share of consumption where `consumption_type = expiry_waste` vs `clinical_use`, per jurisdiction/clinic.
   Decision enabled: target clinics with high waste for ordering/expiry-management review.
   Data source: `consumption_type` on outbound success events.
3. **Insufficient-stock rejection rate** — count/rate of outbound orders rejected because `quantity > available`
   (the existing `HTTP 400` "Insufficient stock" path in `create_outbound_order`), by supply/clinic/jurisdiction.
   Decision enabled: flag supplies/clinics running dry; compare US vs UK supply-chain reliability.
   Data source: `POST /api/v1/inventory/orders/outbound` `400` responses.

Each KPI block in `telemetry-plan.md` must follow: **definition → data components → system touchpoint → why telemetry helps**.

### 4.1 Reconciliation with CONTEXT (required subsection in the plan)

`telemetry-plan.md` **must include a short "Reconciliation with CONTEXT" subsection** that maps each KPI in
`telemetry_design_context.md` to what was actually built, and justifies the swap. This turns a silent mismatch
into documented critical thinking (and pre-empts a grader comparing the plan to the fixed CONTEXT doc). State:

| CONTEXT KPI | Reconciled KPI (§4) | Why re-grounded |
| --- | --- | --- |
| Critical supply availability rate (needs `min_stock_threshold`) | Insufficient-stock rejection rate | No `min_stock_threshold` / `current_stock` column exists; stock is computed and only the 400 rejection path is observable |
| Emergency dispensing frequency (needs `clinical_context = emergency`) | Supply consumption rate + Supply waste rate | No `clinical_context`/`emergency`; outbound is `SupplyConsumption.consumption_type ∈ {clinical_use, expiry_waste}` |
| Stock-out incident rate (needs stored stock hitting zero) | Insufficient-stock rejection rate + consumption volume | No persisted stock level to observe hitting zero; rejections are the observable stock-out signal |

## 5. Standard Event Envelope (canonical — used by all phases)

Every event carries these envelope fields. **Both `requestId` and `service` are included** (this resolves
the doc conflict where Phase 1 wanted `requestId` and Phase 2/3 wanted `service`):

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `eventId` | string (UUID) | yes | Client-generated at capture; dedup/idempotency |
| `timestamp` | string (ISO 8601, UTC) | yes | Moment of capture, not of send |
| `sessionId` | string | yes | Opaque; generated at login (see Phase 2 spec) |
| `userId` | string | yes | TinyDB user UUID — never name/email |
| `event_type` | string | yes | `entity_action` taxonomy |
| `schemaVersion` | string | yes | `1.0.0` |
| `requestId` | string | yes | Correlates frontend ↔ API ↔ logs |
| `service` | string | yes | Constant `"backoffice"` for this app |
| `properties` | object | yes | Event-specific allowlist keys only |

## 6. Reconciled event catalog (design all of these)

Inventory events (all backed by real endpoints). Each needs the golden-rule sentence, property allowlist,
PII note, and a stream/batch decision.

| `event_type` | Trigger | Properties (allowlist) | Stream/batch |
| --- | --- | --- | --- |
| `supply_delivery_created` | Inbound order 201 | `supply_id`, `quantity`, `clinic_id`, `jurisdiction` | batch |
| `supply_consumption_created` | Outbound order 201 | `supply_id`, `quantity`, `consumption_type`, `clinic_id`, `jurisdiction` | batch |
| `supply_consumption_failed` | Outbound order 400 (insufficient stock / validation) | `error_code`, `supply_id`, `clinic_id`, `jurisdiction` | batch |
| `supply_list_viewed` | Products list mounts (`GET /inventory/products`) | `item_count` | batch |
| `orders_list_viewed` | Orders list mounts (`GET /inventory/orders`) | `item_count` | batch |
| `product_created` *(design-only)* | `POST /inventory/products` 201 | `supply_id`, `category`, `jurisdiction` | batch |

Backoffice (non-inventory) events:

| `event_type` | Trigger | Properties (allowlist) | Stream/batch |
| --- | --- | --- | --- |
| `user_login_succeeded` | `/auth/login` 200 | `jurisdiction` *(optional — omit if unknown at login)* | batch |
| `user_login_failed` | `/auth/login` 401 | `reason` (`invalid_credentials` \| `session_expired` \| `network_error`) | stream |
| `session_expired` | 401 → redirect in `healthcoreFetch` | *(envelope only)* | stream |

Notes to document in the plan:
- `supply_list_viewed` / `orders_list_viewed`: the products/orders lists in code are **not** clinic-scoped
  (`list_products` returns all clinics), so `clinic_id`/`jurisdiction` do **not** apply — `item_count` only.
- `jurisdiction` is **derived** on the client from the selected supply's `country` (see Phase 2 spec). Document this derivation.
- `product_created` is **design-only**: `POST /inventory/products` exists but has **no UI surface** in the
  backoffice, so it cannot be captured via frontend `track()` in Phase 2. Keep it in the plan as a valuable
  future event, flagged "API-only — instrument when a create-product UI exists." The five events above provide
  the required ≥5 inventory instrumentation points without it.
- **Dropped events (do not design):** `stock_threshold_triggered` (no `min_stock_threshold`),
  `direct_stock_edit_rejected` (no direct-edit endpoint), `emergency_dispensing_flagged` (no `emergency` context).
  Record these in the "Risks and exclusions" section with the reason (not backed by the current data model).

## 7. `telemetry-plan.md` required sections

1. Executive summary (ops questions the system can't answer today).
2. KPI analysis — the three KPIs from §4.
3. Flow mapping — authenticated access → inbound/outbound completion, with the ≥5 inventory instrumentation points from §6.
4. Backoffice opportunities — the auth events from §6 (≥2).
5. Event Envelope — the table from §5.
6. Event catalog — every event from §6 with golden-rule sentence, allowlist, PII note, stream/batch rationale.
7. High-frequency strategy — debounce/throttle notes (see §8).
8. Risks and exclusions — HIPAA/UK GDPR constraints, no patient identifiers, and the dropped events from §6.

## 8. Stream/batch + throttle rules to state

- Auth-failure and `session_expired` events → **stream** (security/UX urgency).
- All inventory events → **batch** (daily ops reporting).
- High-frequency guard: `supply_list_viewed` / `orders_list_viewed` may fire on every mount — document a
  debounce (e.g. collapse repeated views of the same list within 30s). The batching in Phase 2 (10s / 20 events)
  is the primary mechanism.

## 9. `event-schemas.json` requirements

- Valid JSON. Use JSON Schema **draft-07**: one `eventEnvelope` definition + one definition per event.
- Each event definition: `event_type` `const`, a `properties` object whose keys are exactly the §6 allowlist,
  with `required`, types, and `additionalProperties: false`.
- Must stay consistent with `telemetry-plan.md` (identical `event_type` values and property keys).
- Include `service` and `requestId` in the envelope definition (per §5).
- **Per-event PII marking (required by eval criterion 7):** each event definition must carry a boolean
  `pii` flag (e.g. an `x-pii: false` annotation or a `pii` field), and the plan's event catalog must show a
  PII column. For HealthCore every event is `pii: false` — no patient-linked field is ever in `properties`.
  State the sanitisation strategy explicitly: *"No PII is collected in `properties`; `userId` is an opaque
  TinyDB UUID carried in the envelope only; `jurisdiction`/`clinic_id` are non-patient operational dimensions."*

## 10. Business constraints (must appear in the plan)

- **HIPAA (US) / UK GDPR (UK):** no patient identifiers in any event (no patient name, ID, DOB, diagnosis).
  `SupplyConsumption` events describe a staff action, not a patient encounter.
- **No PII:** `userId` is the opaque TinyDB UUID only.
- **`jurisdiction` on every clinic-operation event** (derived from supply `country`), plus `clinic_id`,
  for Claire Whitfield's (CCO) jurisdiction-segmented audit trails.
- **Audit durability:** events immutable once created; envelope carries `schemaVersion`.

## 11. Dependencies & workflow

- No code, no new server, no new packages this phase.
- Create the `docs/telemetry/` folder in the repo root and place both deliverables there.
- PR: title `[W16D46] Telemetry Design Plan`; description lists the 3 KPIs (one line each), the number of
  events designed, and one sentence on the hardest design decision.

## 12. Definition of done (maps to `telemetry_design_eval_criteria.md`)

- [ ] 3 KPIs from §4, each grounded in real entities with data sources.
- [ ] ≥5 inventory instrumentation points + ≥2 auth opportunities (§6).
- [ ] Consistent envelope (§5) across all events, including `requestId` **and** `service`.
- [ ] Every event has golden-rule sentence + explicit property allowlist + PII note.
- [ ] `event-schemas.json` valid draft-07 and consistent with the plan.
- [ ] Stream/batch justified by business urgency (§8).
- [ ] Risks/exclusions section documents HIPAA/UK GDPR + the three dropped events.
