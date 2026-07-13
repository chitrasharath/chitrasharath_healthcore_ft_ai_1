# Telemetry — Phase 3 (Storage) — Build Spec

> Instructions for a coding agent. Reconciles `telemetry_storage_screenshot.md`,
> `telemetry_storage_readme.md`, and `telemetry_storage_context.md` against the codebase.
> Replaces the Phase 2 stub with a real, persisting endpoint. **The frontend does not change.**

---

## 1. Overview

Turn the stub `POST /api/v1/telemetry/events` into the real endpoint: validate each event individually,
persist the valid ones to a Supabase table in a **single bulk insert**, and return
`{ "received": N, "stored": M, "rejected": R }`. Same URL, same request body, same `200` — the frontend is untouched.

## 2. Tech stack / ground truth

- Supabase/Postgres is reached via **SQLModel + `create_engine(settings.database_url)`** (`app/core/db.py`,
  `supabase_engine`). Existing inventory tables are SQLModel `table=True` models auto-created by
  `SQLModel.metadata.create_all(supabase_engine)` in `app/main.py` `on_startup`.
- Reuse the **`TelemetryEvent`** Pydantic model from Phase 2 (`app/domains/telemetry/schemas.py`) **unchanged**.
- Endpoint lives in `app/domains/telemetry/router.py` (already wired at `/api/v1/telemetry/events`).

## 3. Phase 3a — `telemetry_events` table

Follow the **existing SQLModel pattern** (not raw dashboard SQL) so the table is created consistently with the
rest of the app, then add the indexes that SQLModel can't express via raw SQL at startup.

Add a `table=True` model in `app/domains/telemetry/models.py`:

| Column | SQLModel type | Constraint | Source |
| --- | --- | --- | --- |
| `id` | `uuid` (`sa_column` default `gen_random_uuid()`) | PK | generated |
| `timestamp` | `datetime` (timestamptz) | NOT NULL | `event.timestamp` |
| `service` | `str` | NOT NULL | `event.service` (`"backoffice"`) |
| `event_type` | `str` | NOT NULL | `event.event_type` |
| `level` | `str` | default `"info"` | derived: `warn` for `*_failed` / `session_expired`, else `info` |
| `value` | `float`/`numeric` | nullable | `properties.quantity` when present (`supply_delivery_created`, `supply_consumption_created`), else null |
| `message` | `str` | nullable | optional short summary, else null |
| `tags` | `jsonb` | default `{}` | see §3.1 |

Register the model import in `app/main.py` (like the inventory/incident model imports) so `create_all` builds it.

Add the three indexes. `create_all` will not create a GIN index, so run raw SQL in `on_startup` (idempotent
`CREATE INDEX IF NOT EXISTS`) or a migration:

```sql
CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp ON telemetry_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_event_type ON telemetry_events (event_type);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_tags ON telemetry_events USING GIN (tags);
```

**Immutability:** no UPDATE or DELETE code paths for this table anywhere in the app. Append-only.

### 3.1 `tags` mapping

`tags` stores the event's allowlisted `properties` **plus** the envelope fields that have no dedicated column
(`eventId`, `sessionId`, `userId`, `schemaVersion`, `requestId`) — these live in `tags` per the reference
solution. Do this consistently for every event. Example rows (from `telemetry_storage_context.md`, adjusted to real fields):

| `event_type` | `tags` (properties portion) |
| --- | --- |
| `supply_delivery_created` | `{ "supply_id": ..., "quantity": 500, "clinic_id": 1, "jurisdiction": "us" }` |
| `supply_consumption_created` | `{ "supply_id": ..., "quantity": 20, "consumption_type": "clinical_use", "clinic_id": 10, "jurisdiction": "uk" }` |
| `supply_consumption_failed` | `{ "error_code": "INSUFFICIENT_STOCK", "supply_id": ..., "clinic_id": 5, "jurisdiction": "us" }` |
| `supply_list_viewed` | `{ "item_count": 6 }` |
| `user_login_failed` | `{ "reason": "invalid_credentials" }` |
| `session_expired` | `{}` |

> Note vs the context doc: there is **no `emergency_dispensing_flagged`** and no `clinical_context`. Outbound
> uses `consumption_type ∈ {clinical_use, expiry_waste}`. `clinic_id` is an integer. `jurisdiction` was derived
> client-side from supply `country` in Phase 2 — it arrives already in `properties`.

## 4. Phase 3b — real endpoint (partial validation + bulk insert)

Replace the stub body of `POST /telemetry/events`:

1. Accept `{ "events": [...] }` as **loose dicts** (`TelemetryBatch.events: list[dict]`). **Do not** type the
   body as `list[TelemetryEvent]` — that would 422 the entire batch if one event is bad.
2. Loop; for each raw item call `TelemetryEvent.model_validate(raw)` inside `try/except ValidationError`.
   - valid → map to a `telemetry_events` row (§3, §3.1) and append to a list
   - invalid → increment `rejected`, continue (do **not** abort the batch)
3. If any valid rows: insert them in **one bulk operation / single transaction** (SQLModel
   `session.add_all(rows); session.commit()`, or `bulk_insert_mappings`). Not one INSERT per event.
4. Return `200` with `{ "received": len(events), "stored": <inserted>, "rejected": <count> }`.

Indicative:

```python
valid_rows: list[TelemetryEventRow] = []
rejected = 0
for raw in payload.events:
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
return {"received": len(payload.events), "stored": stored, "rejected": rejected}
```

**Frontend compatibility:** path unchanged, still `200` on success, and **still unauthenticated** — keep the
route wired without `get_current_user` (Phase 2 §3). The `TelemetryService` only checks the HTTP status, not the
body, so adding `stored`/`rejected` is safe and requires **zero frontend changes**. `userId` continues to come
from the envelope payload (self-reported), never from a token.

## 5. Phase 3c — end-to-end verification

- With the real endpoint live + `database_url` set, use the backoffice to create ≥1 inbound and ≥1 outbound order.
- Query Supabase:
  ```sql
  SELECT event_type, timestamp, tags FROM telemetry_events ORDER BY timestamp DESC LIMIT 20;
  ```
  Expect ≥5 rows with populated `event_type`, `timestamp`, `tags`.
- Mixed-batch curl test against `$API/api/v1/telemetry/events` with one valid + one invalid event; expect
  `{ "received": 2, "stored": 1, "rejected": 1 }` and one new row.
- Confirm no UPDATE/DELETE paths exist for the table.

## 6. Business constraints (verify)

- Every clinic-operation row has `jurisdiction` (`us`/`uk`) and `clinic_id` in `tags` — else rejectable/unusable for compliance.
- `supply_consumption_created` rows carry `consumption_type` in `tags`.
- **No patient identifiers** anywhere in any column or `tags` (HIPAA/UK GDPR hard boundary).
- `userId` (in `tags`) is an opaque TinyDB UUID — never a name/email/role title.

## 7. Dependencies & workflow

- No new Python packages (SQLModel + psycopg2-binary already present; managed with **uv** in `services/api/`).
- Requires `DATABASE_URL` configured (the app skips inventory/telemetry seeding & table creation without it).
- PR: title `[W16D48] Telemetry Storage`; description includes a Supabase screenshot (≥5 real rows), the JSON
  response of a mixed valid/invalid batch, and an explicit statement that the frontend did not change.

## 8. Definition of done (maps to `telemetry_storage_eval_criteria.md`)

- [ ] `telemetry_events` table: 8 columns + 3 indexes (incl. GIN on `tags`), write-only.
- [ ] Endpoint does per-event `model_validate`, partial acceptance, single bulk insert.
- [ ] Returns `{ received, stored, rejected }`; still `200`.
- [ ] `TelemetryEvent` reused unchanged from Phase 2.
- [ ] Zero frontend diffs.
- [ ] Rows show `event_type`, `timestamp`, `tags`; `tags` preserves the allowlists + `jurisdiction`/`clinic_id`.
- [ ] No UPDATE/DELETE paths; no patient data.
