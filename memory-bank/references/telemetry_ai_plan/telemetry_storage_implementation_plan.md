---
name: Telemetry Storage (Phase 3)
overview: "Replace Phase 2 stub with persisting POST /api/v1/telemetry/events — SQLModel telemetry_events table on milestone5_inventory, per-event validation, partial acceptance, single bulk insert. Zero frontend changes."
todos:
  - id: step0-prereq
    content: Confirm Phase 2 stub + TelemetryService on feature/telemetry; DATABASE_URL configured for milestone5_inventory
    status: pending
  - id: step1-model
    content: Create app/domains/telemetry/models.py (TelemetryEventRow table) with UUID PK + jsonb tags
    status: pending
  - id: step2-startup
    content: Import telemetry models in main.py; create_all + idempotent GIN/B-tree indexes on startup
    status: pending
  - id: step3-mapper
    content: Add map_event_to_row() — level derivation, value from quantity, tags envelope+properties
    status: pending
  - id: step4-endpoint
    content: Replace stub with validate-loop, bulk insert, return received/stored/rejected
    status: pending
  - id: step5-tests
    content: Add tests/test_telemetry_storage.py — SQLite override, partial batch, immutability, tags shape
    status: pending
  - id: step6-e2e-verify
    content: Backoffice activity + Supabase query; mixed curl batch test
    status: pending
isProject: false
---

# Telemetry — Phase 3 (Storage) Implementation Plan

**Plan file:** [`memory-bank/references/telemetry_ai_plan/telemetry_storage_implementation_plan.md`](telemetry_storage_implementation_plan.md)

**Requirements source:** [`telemetry_storage_specs.md`](telemetry_storage_specs.md)

**Branch:** `feature/telemetry` (third commit on same branch)

**Working directory:** `services/api/`

**Status:** Not started — no `telemetry_events` table or persistence layer

---

## Executive summary

Phase 3 upgrades `POST /api/v1/telemetry/events` from a log-only stub to a **persisting, append-only ingest pipeline**. Valid events are written to `telemetry_events` on the existing **`milestone5_inventory`** Supabase project in one bulk insert per request. Invalid events are counted in `rejected` without failing the batch.

The frontend **does not change** — same URL, same request body, same `200` on success.

---

## Planning decisions (locked)

| Topic | Decision |
|-------|----------|
| Database | Reuse **`milestone5_inventory`** via existing `DATABASE_URL` / `supabase_engine` |
| ORM | SQLModel `table=True` model + `create_all` (matches inventory/incidents) |
| Primary key | UUID with Postgres `gen_random_uuid()` via `sa_column` (first UUID table in repo) |
| Indexes | B-tree on `timestamp`, `event_type`; GIN on `tags` — raw SQL `IF NOT EXISTS` in `on_startup` |
| Auth on ingest | **Remain public** (no JWT) — `sendBeacon` compatibility from Phase 2 |
| `TelemetryEvent` schema | **Unchanged** from Phase 2 `schemas.py` |
| Immutability | No UPDATE/DELETE code paths — append-only |
| Tests | pytest with in-memory SQLite override (same pattern as inventory/incidents) |
| Frontend diffs | **Zero** |

---

## Table design

### `app/domains/telemetry/models.py`

```python
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlmodel import Field, SQLModel
import uuid as uuid_pkg

class TelemetryEventRow(SQLModel, table=True):
    __tablename__ = "telemetry_events"

    id: uuid_pkg.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    timestamp: datetime  # timestamptz
    service: str
    event_type: str
    level: str = "info"
    value: float | None = None
    message: str | None = None
    tags: dict = Field(default_factory=dict, sa_column=Column(JSONB))
```

**SQLite test note:** For pytest, use `StaticPool` in-memory engine; JSONB maps acceptably in SQLite tests via SQLAlchemy JSON type fallback, or use `sa.JSON` for cross-dialect compatibility in tests only. Prefer same pattern as incident tests — verify JSON column round-trip.

### Column mapping (`map_event_to_row`)

| Row column | Source |
|------------|--------|
| `timestamp` | `event.timestamp` (UTC) |
| `service` | `event.service` |
| `event_type` | `event.event_type` |
| `level` | `"warn"` if `event_type` ends with `_failed` or equals `session_expired`; else `"info"` |
| `value` | `properties.get("quantity")` cast to float when present; else `None` |
| `message` | `None` (v1 — optional short summary deferred) |
| `tags` | See §3.1 below |

### §3.1 `tags` composition

Merge into one JSON object:

**From envelope** (no dedicated columns):

- `eventId`, `sessionId`, `userId`, `schemaVersion`, `requestId`

**From `properties`** (allowlisted keys only — pass through as validated by `TelemetryEvent`):

- Event-specific keys per Phase 1 catalog

Example `supply_consumption_created` tags:

```json
{
  "eventId": "...",
  "sessionId": "...",
  "userId": "1",
  "schemaVersion": "1.0.0",
  "requestId": "...",
  "supply_id": 3,
  "quantity": 20,
  "consumption_type": "clinical_use",
  "clinic_id": 10,
  "jurisdiction": "uk"
}
```

---

## Startup wiring

### `app/main.py`

```python
from app.domains.telemetry import models as telemetry_models  # noqa: F401
```

In `on_startup()` after `create_all`:

```python
def _ensure_telemetry_indexes(engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp ON telemetry_events (timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_telemetry_events_event_type ON telemetry_events (event_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_telemetry_events_tags ON telemetry_events USING GIN (tags)"))
        conn.commit()
```

Guard: only run when `supabase_engine` is not None (same as `create_all` guard).

---

## Endpoint implementation

Replace stub in `router.py`:

```python
@router.post("/events")
def ingest_events(
    body: TelemetryBatch,
    session: Session = Depends(get_supabase_db),
) -> dict[str, int]:
    valid_rows: list[TelemetryEventRow] = []
    rejected = 0
    for raw in body.events:
        try:
            event = TelemetryEvent.model_validate(raw)
            valid_rows.append(map_event_to_row(event))
        except ValidationError:
            rejected += 1
    stored = 0
    if valid_rows:
        session.add_all(valid_rows)
        session.commit()
        stored = len(valid_rows)
    return {
        "received": len(body.events),
        "stored": stored,
        "rejected": rejected,
    }
```

**Behaviour locks:**

- Always `200` when handler completes (DB errors → global 500 handler)
- Partial acceptance — one bad event does not reject the batch
- Single transaction per request (`add_all` + one `commit`)
- Still log `event_type` counts at INFO for ops visibility

### Optional: property allowlist hardening (recommended)

After `model_validate`, optionally reject events whose `properties` keys are not in the Phase 1 allowlist for that `event_type`. Count as `rejected`. This prevents tag pollution — document in tests.

---

## Tests (`tests/test_telemetry_storage.py`)

Use `conftest.py` SQLite `get_supabase_db` override (existing pattern).

| Case | Assert |
|------|--------|
| Single valid `supply_delivery_created` | `stored: 1`, row exists with `tags.jurisdiction` |
| Batch 1 valid + 1 missing `eventId` | `received: 2, stored: 1, rejected: 1` |
| `supply_consumption_failed` | `level == "warn"` |
| `session_expired` | `level == "warn"`, empty properties in tags |
| `value` column | Set from `quantity` on delivery event |
| No delete endpoint | grep `delete` / `update` on telemetry domain — none |
| Immutability | No PATCH/DELETE routes registered |

---

## End-to-end verification

### 1. Generate real events

With API + landing running and `DATABASE_URL` set:

1. Login (auth events)
2. View products + orders lists
3. Create inbound order
4. Create outbound order (clinical_use)
5. Attempt outbound exceeding stock (failure event)

### 2. Supabase query

```sql
SELECT event_type, timestamp, level, value, tags
FROM telemetry_events
ORDER BY timestamp DESC
LIMIT 20;
```

Expect ≥5 rows with populated `tags` including `jurisdiction` on clinic-operation events.

### 3. Mixed curl test

```bash
curl -s -X POST http://localhost:8000/api/v1/telemetry/events \
  -H "Content-Type: application/json" \
  -d '{"events": [<valid>, {"event_type": "bad"}]}'
```

Expect `{"received":2,"stored":1,"rejected":1}`.

### 4. Frontend unchanged

```bash
git diff uis/backoffice/  # should be empty for Phase 3 commit
```

---

## PR checklist

- **Title:** `[W16D48] Telemetry Storage`
- **Description:** Supabase screenshot (≥5 rows), mixed-batch JSON response, explicit "frontend unchanged"

---

## Definition of done (maps to spec §8)

- [ ] `telemetry_events`: 8 columns + 3 indexes, write-only
- [ ] Per-event validation, partial acceptance, single bulk insert
- [ ] Returns `{ received, stored, rejected }`, still `200`
- [ ] `TelemetryEvent` unchanged from Phase 2
- [ ] Zero frontend diffs
- [ ] Rows show correct `tags` with jurisdiction/clinic_id on clinic events
- [ ] No UPDATE/DELETE; no patient data
- [ ] pytest passing

---

## Handoff to Phase 4

Phase 4 reads `telemetry_events` via SQLModel/SQLAlchemy session — `tags` JSONB is the dimension source for `clinic_id`, `jurisdiction`, `consumption_type`, `error_code`. Report endpoint will be **JWT-protected** (stakeholder decision).
