---
name: Telemetry Storage (Phase 3)
overview: "Replace Phase 2 stub with persisting POST /api/v1/telemetry/events — SQLModel telemetry_events on milestone5_inventory, per-event validation for all 10 instrumentable v1.1.0 events, partial acceptance, bulk insert. Zero frontend changes."
todos:
  - id: step0-prereq
    content: Confirm Phase 2 stub + TelemetryService on feature/telemetry; DATABASE_URL for milestone5_inventory
    status: pending
  - id: step1-model
    content: Create app/domains/telemetry/models.py (TelemetryEventRow) with UUID PK + jsonb tags
    status: pending
  - id: step2-startup
    content: Import telemetry models in main.py; create_all + idempotent GIN/B-tree indexes
    status: pending
  - id: step3-mapper
    content: Add map_event_to_row() + per-event-type property allowlist validator (11 types from event-schemas.json)
    status: pending
  - id: step4-endpoint
    content: Replace stub with validate-loop, bulk insert, return received/stored/rejected
    status: pending
  - id: step5-tests
    content: Add tests/test_telemetry_storage.py — all event types incl. v1.1 abandon + incident filter
    status: pending
  - id: step6-e2e-verify
    content: Backoffice activity (incl. abandon + filter) + Supabase query; mixed curl batch
    status: pending
isProject: false
---

# Telemetry — Phase 3 (Storage) Implementation Plan

**Plan file:** [`memory-bank/references/telemetry_ai_plan/telemetry_storage_implementation_plan.md`](telemetry_storage_implementation_plan.md)

**Requirements source:** [`telemetry_storage_specs.md`](telemetry_storage_specs.md), [`docs/telemetry/telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md) (v1.1.0), [`docs/telemetry/event-schemas.json`](../../../../docs/telemetry/event-schemas.json)

**Branch:** `feature/telemetry` (third commit on same branch)

**Working directory:** `services/api/`

**Status:** Not started — no `telemetry_events` table or persistence layer

---

## Executive summary

Phase 3 upgrades `POST /api/v1/telemetry/events` from a log-only stub to a **persisting, append-only ingest pipeline**. Valid events are written to `telemetry_events` on **`milestone5_inventory`** in one bulk insert per request.

Must persist all **10 instrumentable event types** from design v1.1.0, including:

- `supply_consumption_form_abandoned` (v1.1)
- `incident_list_filter_applied` (v1.1)

Frontend **does not change** — same URL, body, and `200` on success.

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Design reference | [`docs/telemetry/telemetry-plan.md`](../../../../docs/telemetry/telemetry-plan.md) + `event-schemas.json` v1.1.0 |
| `schemaVersion` in tags | Store client value (`1.1.0`); reject unknown versions in allowlist validator if desired |
| Database | Reuse **`milestone5_inventory`** |
| Auth on ingest | **Public** (sendBeacon compatibility) |
| `TelemetryEvent` pydantic model | **Unchanged** from Phase 2 `schemas.py` |
| Property allowlist | **Recommended** — reject events whose `properties` keys don't match `event-schemas.json` per `event_type` |
| `level` column | `warn` for `*_failed` and `session_expired`; `info` for all others (incl. v1.1 abandon + filter) |
| `value` column | `properties.quantity` as float when present (`supply_delivery_created`, `supply_consumption_created` only) |
| Frontend diffs | **Zero** |

---

## Per-event property allowlists (storage validation)

Align with `event-schemas.json` — reject unknown keys in `properties`:

| `event_type` | Allowed `properties` keys |
|--------------|---------------------------|
| `supply_delivery_created` | `supply_id`, `quantity`, `clinic_id`, `jurisdiction` |
| `supply_consumption_created` | `supply_id`, `quantity`, `consumption_type`, `clinic_id`, `jurisdiction` |
| `supply_consumption_failed` | `error_code`, `supply_id`, `clinic_id`, `jurisdiction` |
| `supply_consumption_form_abandoned` | `clinic_id`, `had_supply_selected`, `had_quantity`, `jurisdiction`, `abandon_trigger` |
| `supply_list_viewed` | `item_count` |
| `orders_list_viewed` | `item_count` |
| `incident_list_filter_applied` | `filter_dimension`, `filter_value`, `active_filter_count` |
| `user_login_succeeded` | `jurisdiction` (optional) |
| `user_login_failed` | `reason` |
| `session_expired` | *(empty)* |
| `product_created` | `supply_id`, `category`, `jurisdiction` *(API-only; may appear if backend emits later)* |

**Note:** `supply_consumption_form_abandoned` — `jurisdiction` is optional (omit when no supply selected). `had_supply_selected`/`had_quantity` are booleans, not `supply_id`.

---

## Table design

Same as prior plan — `TelemetryEventRow` with `id`, `timestamp`, `service`, `event_type`, `level`, `value`, `message`, `tags` (JSONB).

### `tags` composition

Envelope fields in `tags`: `eventId`, `sessionId`, `userId`, `schemaVersion`, `requestId`  
Plus all allowlisted `properties`.

**v1.1 example — `supply_consumption_form_abandoned`:**

```json
{
  "eventId": "...",
  "sessionId": "...",
  "userId": "1",
  "schemaVersion": "1.1.0",
  "requestId": "...",
  "clinic_id": 1,
  "had_supply_selected": true,
  "had_quantity": true,
  "jurisdiction": "us",
  "abandon_trigger": "navigation"
}
```

**v1.1 example — `incident_list_filter_applied`:**

```json
{
  "eventId": "...",
  "sessionId": "...",
  "userId": "1",
  "schemaVersion": "1.1.0",
  "requestId": "...",
  "filter_dimension": "status",
  "filter_value": "open",
  "active_filter_count": 1
}
```

**Clinic-operation example — `supply_consumption_created`:**

```json
{
  "schemaVersion": "1.1.0",
  "supply_id": 3,
  "quantity": 20,
  "consumption_type": "clinical_use",
  "clinic_id": 10,
  "jurisdiction": "uk"
}
```

---

## Endpoint implementation

Same partial-acceptance loop as prior plan:

```python
return {
    "received": len(body.events),
    "stored": stored,
    "rejected": rejected,
}
```

After `TelemetryEvent.model_validate`, run **allowlist check** on `properties` for the `event_type`. Invalid → increment `rejected`.

`map_event_to_row` rules:

| `event_type` pattern | `level` | `value` |
|---------------------|---------|---------|
| ends with `_failed` | `warn` | null |
| `session_expired` | `warn` | null |
| `supply_delivery_created`, `supply_consumption_created` | `info` | `float(quantity)` |
| `supply_consumption_form_abandoned` | `info` | null |
| `incident_list_filter_applied` | `info` | null |
| all others | `info` | null |

---

## Tests (`tests/test_telemetry_storage.py`)

Add cases beyond original plan:

| Case | Assert |
|------|--------|
| `supply_consumption_form_abandoned` without `jurisdiction` | `stored: 1` when supply not selected |
| `supply_consumption_form_abandoned` with extra `supply_id` in properties | `rejected: 1` (allowlist) |
| `incident_list_filter_applied` | `stored: 1`, `tags.filter_dimension`, `tags.active_filter_count` |
| `schemaVersion` `1.1.0` in tags | preserved on row |
| `incident_list_filter_applied` | `level == "info"` |

---

## End-to-end verification

Generate events via backoffice (Phase 2 must be live):

1. Login
2. Products + orders lists
3. Inbound + outbound orders; insufficient stock attempt
4. **Abandon outbound form** with dirty fields
5. **Change incident list filter**

Supabase query — expect ≥7 distinct `event_type` values including v1.1:

```sql
SELECT event_type, count(*) FROM telemetry_events GROUP BY event_type;
```

---

## PR checklist

- **Title:** `[W16D48] Telemetry Storage`
- **Description:** Supabase screenshot with v1.1 rows, mixed-batch JSON, frontend unchanged

---

## Definition of done

- [ ] `telemetry_events` table + indexes, write-only
- [ ] All **10 instrumentable** event types store correctly in `tags`
- [ ] v1.1 events: abandon booleans + filter dimensions persisted
- [ ] `schemaVersion` **1.1.0** in tags
- [ ] Partial acceptance; `{ received, stored, rejected }`
- [ ] Zero frontend diffs
- [ ] pytest passing

---

## Handoff to Phase 4

Report metrics use existing KPI event types. v1.1 events (`supply_consumption_form_abandoned`, `incident_list_filter_applied`) are **stored and queryable** but **not** in default report response unless Phase 4 adds optional supplementary metrics (out of scope per `telemetry_report_specs.md`).

`tags` dimensions for future use: `abandon_trigger`, `had_quantity`, `filter_dimension`, `filter_value`, `active_filter_count`.
