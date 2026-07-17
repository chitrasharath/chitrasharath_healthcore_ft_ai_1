# Data Pipeline — Part 2 (Build 1: Resilient Pipeline) — Build Spec

> **Instructions for a coding agent.** Implement the pipeline designed in Part 1
> (`docs/data_pipelines/pipeline-design.md`). Everything you need is in this spec and the HealthCore monorepo.
>
> **Deliverables:** `data/pipelines/pipeline.py` (Prefect flow + tasks), four `reporting_*` tables + a
> `pipeline_runs` table, a repointed `GET /api/v1/telemetry/report`, a preserved
> `GET /api/v1/telemetry/raw-report`, and two pipeline endpoints. Runnable via
> `python data/pipelines/pipeline.py`. **Do not change the frontend.**

---

## Branch & workflow

- Continue on the same branch **`feature/data_pipeline`** (created off **`main`** in Part 1) — all Build 1
  work lands here.
- Every code reference in this spec reflects the state of **`main`**: the telemetry domain
  (`app/domains/telemetry/*`), the `data/` folders, `app/main.py`, and `pyproject.toml` all exist there.
- Commit with `feat: implement resilient prefect pipeline`. The PR (opened after Build 2) targets **`main`**.

---

## 1. Ground truth (read the real code before writing)

| Concern | Where it lives | What to reuse |
| --- | --- | --- |
| DB engine | `services/api/app/core/db.py` | `supabase_engine = create_engine(settings.database_url)`; is `None` if no `DATABASE_URL`. Session dep `get_supabase_db()`. |
| Table creation | `app/main.py` `on_startup` | `SQLModel.metadata.create_all(supabase_engine)` + `ensure_telemetry_indexes(supabase_engine)`. New models must be imported in `main.py` before `create_all`. |
| Raw-SQL / index pattern | `app/domains/telemetry/indexes.py` | `with engine.begin() as conn: conn.execute(text("CREATE INDEX IF NOT EXISTS ..."))`. Idempotent. Extend it (or add a sibling) for new indexes. |
| Existing model style | `app/domains/telemetry/models.py` | `TelemetryEventRow(SQLModel, table=True)`; JSONB via `sa.JSON().with_variant(JSONB, "postgresql")`. |
| Transforms (reuse as-is) | `app/domains/telemetry/analysis.py` | `build_metrics(session, start, end) -> dict[str, list[dict]]`. **Do not reimplement.** |
| Event reader | `app/domains/telemetry/repository.py` | `load_events(session, event_types, start, end) -> DataFrame`. |
| Report endpoint | `app/domains/telemetry/router.py` | `GET /telemetry/report` calls `build_metrics` inside `get_cached_or_compute` (`cache.py`); auth `get_current_user`. |
| Ingest reference | `app/domains/telemetry/router.py` | `POST /telemetry/events` returns `{received, stored, rejected}` — mirror this partial-acceptance philosophy. |

**KPI grains** (produced by `analysis.py`; these become the reporting-table keys/columns):

| KPI key in `build_metrics` output | grain (unique key) | value columns |
| --- | --- | --- |
| `consumption_volume_per_day` | `(report_date, clinic_id, jurisdiction)` | `count` |
| `waste_rate_per_day` | `(report_date, jurisdiction)` | `waste_rate`, `total` |
| `insufficient_stock_failures_per_day` | `(report_date, clinic_id, jurisdiction, supply_id)` | `count`, `attempts`, `rejection_rate` |
| `auth_failure_rate` | `(report_date)` | `failed`, `succeeded`, `failure_rate` |

> Note each KPI dict uses `date` (string) as the day field; map it to a `report_date (date)` column on load.
> `clinic_id` is an **integer**; `jurisdiction ∈ {us, uk}`; `supply_id` is a string.

**Install Prefect:** `uv add "prefect>=3"` on the `healthcore-api` package (`services/api/pyproject.toml`)
so the workspace venv resolves it.

## 2. Suggested file layout

```
data/
  __init__.py
  pipelines/
    __init__.py
    pipeline.py            # flow + tasks + CLI entry point (main deliverable)
    config.py              # watermark/reprocess-window/version constants or Prefect Block loader
  process/
    __init__.py
    reporting_repository.py # upsert writers + reporting-table readers (pure SQL/SQLModel, no Prefect)
services/api/app/domains/telemetry/
    reporting_models.py    # the 4 reporting_* + pipeline_runs SQLModel tables
    pipeline_router.py     # (optional split) the runs/latest + trigger endpoints
```

Keep ETL logic in `data/`; keep HTTP + models in `services/api` (models must be import-registered in
`main.py`). The endpoints import the flow from `data/pipelines/pipeline.py` — see §7 for the import trap.

## 3. Phase 1 — tables (SQLModel `table=True`)

Define these in `services/api/app/domains/telemetry/reporting_models.py` and **import them in `app/main.py`**
(alongside the existing `telemetry_models` import) so `create_all` builds them.

**Reporting tables** — one per KPI. Columns = grain key + value columns (§1) **plus** provenance
`run_id (uuid)` and `updated_at (timestamptz)`. Each needs a **unique constraint on the grain** (this is
what the upsert conflicts on). Example (write the other three analogously):

```python
class ReportingConsumptionVolumeDaily(SQLModel, table=True):
    __tablename__ = "reporting_consumption_volume_daily"
    __table_args__ = (UniqueConstraint("report_date", "clinic_id", "jurisdiction",
                                        name="uq_rcv_grain"),)
    id: int | None = Field(default=None, primary_key=True)
    report_date: date = Field(index=True)
    clinic_id: int
    jurisdiction: str
    count: int
    run_id: UUID
    updated_at: datetime = Field(sa_column=Column(sa.DateTime(timezone=True)))
```

- `reporting_waste_rate_daily` — key `(report_date, jurisdiction)`; cols `waste_rate: float`, `total: int`.
- `reporting_stock_failures_daily` — key `(report_date, clinic_id, jurisdiction, supply_id)`;
  cols `count: int`, `attempts: int`, `rejection_rate: float`.
- `reporting_auth_failure_daily` — key `(report_date)`; cols `failed: int`, `succeeded: int`,
  `failure_rate: float`.

**`pipeline_runs`** — the audit/execution log (≥5 fields required; this exceeds it — keep all):

| column | type | notes |
| --- | --- | --- |
| `run_id` | `UUID` (pk) | one per execution |
| `started_at` | `timestamptz` | set at flow start |
| `finished_at` | `timestamptz?` | null while running |
| `watermark_from` / `watermark_to` | `timestamptz?` | event-time window processed |
| `rows_extracted` / `rows_loaded` / `rows_quarantined` | `int` default 0 | reconciliation |
| `status` | `str` | `running` → `success` \| `partial` \| `failed` \| `quarantined` |
| `error_summary` | `str?` | human-readable failure, no stack traces |
| `pipeline_version` | `str` | git sha / semver for reproducibility |
| `checkpoint` | `str?` | last completed phase (`extract`\|`transform`\|`load`) |

Add `CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs (started_at DESC)` via the
`indexes.py` pattern (powers the "latest run" query). **No UPDATE/DELETE of reporting/telemetry rows except
the idempotent upsert** — the load is the only writer.

## 4. Phase 2 — Prefect flow & tasks (`data/pipelines/pipeline.py`)

One `@flow telemetry_etl_flow(start: datetime | None = None, end: datetime | None = None)` orchestrating
≥3 `@task` stages with explicit typed inputs/outputs:

```python
@task(retries=3, retry_delay_seconds=[10, 30, 60], retry_condition_fn=is_transient)
def extract_telemetry_events(session, event_types, start, end) -> pd.DataFrame:
    # 3 retries w/ backoff: absorbs transient Supabase/connection blips without paging on-call.
    # retry_condition_fn -> retry only OperationalError/connection resets, NOT ValidationError.
    return load_events(session, event_types, start, end)

@task(cache_key_fn=window_cache_key, cache_expiration=timedelta(hours=1))
def transform_kpi_aggregates(session, start, end) -> dict[str, list[dict]]:
    # cache key = (start, end) window; valid 1h so a re-run within the hour reuses results.
    return build_metrics(session, start, end)

@task
def load_reporting_tables(metrics, run_id) -> int: ...   # §5, returns rows loaded

@task
def export_snapshot_optional(metrics) -> str | None: ...  # optional, non-critical
```

- **Watermark resolution** (`resolve_window`): `watermark_from` = the max `watermark_to` of the latest
  `status='success'` run, minus a **reprocess-window** (default 2 days, from `config.py`) to re-aggregate
  late cross-jurisdiction events; on first run fall back to a configured lookback. `watermark_to` =
  `end or datetime.now(UTC)`. Pass these as the extract/transform window.
- **Optional task with partial tolerance:** call the optional export/notify with `return_state=True`;
  inspect the returned state, log a warning and continue if it failed (do **not** let it abort the flow).

## 5. Phase 3 — idempotent load, run log, PHI guard

**Idempotent upsert** (in `data/process/reporting_repository.py`). Use Postgres upsert keyed on each
table's grain:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

def upsert_consumption_volume(conn, rows, run_id):
    if not rows: return 0
    stmt = pg_insert(ReportingConsumptionVolumeDaily).values(
        [{**r, "report_date": r["date"], "run_id": run_id, "updated_at": now_utc()} for r in rows]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["report_date", "clinic_id", "jurisdiction"],
        set_={"count": stmt.excluded.count, "run_id": run_id, "updated_at": now_utc()},
    )
    conn.execute(stmt); return len(rows)
```

- Run **all four upserts inside one transaction** (`with supabase_engine.begin() as conn:`) so a mid-load
  crash rolls back with **no partial reporting rows**. Running twice over the same window yields identical
  rows — no duplicates (verify in §8).
- **Advance the watermark only after the load transaction commits** (write `watermark_to` into the
  `pipeline_runs` row in/after the same commit).
- **Run-log lifecycle:** insert a `pipeline_runs` row with `status='running'` at flow start; on success set
  `status='success'`, `finished_at`, `rows_*`; set `status='partial'` if an optional/isolated step failed;
  on a critical exception set `status='failed'` + `error_summary` (catch, log, re-raise after recording).

**HIPAA PHI circuit breaker (required, fail closed).** Before load, validate every event's `tags` against
the allowlist:

- **Allowed keys:** `supply_id, quantity, clinic_id, jurisdiction, consumption_type, item_count, reason,
  error_code` + envelope keys `eventId, sessionId, userId, schemaVersion, requestId`.
- Trip the breaker if a `tags` object contains **any key outside the allowlist**, or a value that looks
  patient-identifiable (e.g. an email regex, a free-text personal-name string, a DOB-shaped value).
- On trip: **do not load** that batch — set `status='quarantined'`, `error_summary='possible PHI in tags'`,
  increment `rows_quarantined`, log at WARNING, and stop the load stage. (This is stricter than the rubric;
  it is required for HealthCore.)

## 6. Phase 4 — script execution

```python
if __name__ == "__main__":
    if supabase_engine is None:
        raise SystemExit("DATABASE_URL is not set — refusing to run against no database.")
    telemetry_etl_flow()
```

- `python data/pipelines/pipeline.py` runs the full ETL without errors when `DATABASE_URL` is set. **Fail
  fast with a clear message otherwise** — never silently emit empty output.
- Document the run command + intended schedule (nightly `0 2 * * *`) in `docs/data_pipelines/pipeline-design.md`.

## 7. Phase 5 — report endpoints + pipeline endpoints

All under the telemetry router (`prefix="/telemetry"` → `/api/v1/telemetry/...`), auth `get_current_user`,
responses following existing conventions. Both report endpoints return the **same JSON shape**:

```json
{ "period": { "from": "2025-01-13T00:00:00+00:00", "to": "2025-01-20T00:00:00+00:00" },
  "metrics": {
    "consumption_volume_per_day": [ { "date": "2025-01-13", "clinic_id": 3, "jurisdiction": "us", "count": 42 } ],
    "waste_rate_per_day": [ { "date": "2025-01-13", "jurisdiction": "uk", "waste_rate": 0.08, "total": 25 } ],
    "insufficient_stock_failures_per_day": [ { "date": "2025-01-13", "clinic_id": 3, "jurisdiction": "us", "supply_id": "s1", "count": 2, "attempts": 40, "rejection_rate": 0.05 } ],
    "auth_failure_rate": [ { "date": "2025-01-13", "failed": 3, "succeeded": 120, "failure_rate": 0.024 } ]
  } }
```

- **`GET /telemetry/raw-report`** — the **old** report behavior, preserved and renamed: computes live from
  `telemetry_events` via `build_metrics(session, start, end)`. The only HTTP endpoint that reads the **raw**
  table; keep for live/ad-hoc reads and to reconcile against the materialized tables. Keep the `cache.py`
  wrapper + auth.
- **`GET /telemetry/report`** — **new, frontend-facing:** reads the `reporting_*` tables (a reader in
  `reporting_repository.py` that `SELECT`s each table between `report_date` bounds and shapes rows into the
  KPI lists above). Keep the `cache.py` wrapper + auth. URL/shape/auth unchanged → **zero frontend change**.
  Empty reporting tables → empty lists (serve-last-good otherwise).

> Net effect: `/report` is fast and as-fresh-as-the-last-run (materialized); `raw-report` is live but
> recomputes each call. Both reuse `build_metrics`/the reporting reader — no KPI logic duplicated.

Plus the two pipeline endpoints:

- **`GET /telemetry/pipelines/runs/latest`** — returns the newest `pipeline_runs` row:
  `{ run_id, status, started_at, finished_at, rows_extracted, rows_loaded, rows_quarantined, error_summary }`.
  404/`null` if no runs yet.
- **`POST /telemetry/pipelines/runs/trigger`** — triggers a manual run by **importing the flow** from
  `data/pipelines/pipeline.py` (no duplicated ETL). Return `{ "message": "Pipeline run submitted",
  "run_id": "<uuid>" }`. Run synchronously or via a background task — document which.

## 8. Manual testing walkthrough (run these by hand; capture output for the PR)

**Prerequisites**

- `DATABASE_URL` set to the Supabase Postgres connection string (the app skips all DB work without it).
- Dependencies synced incl. Prefect: `uv sync` then `uv add "prefect>=3"` (in `services/api`).
- API running locally from `services/api`: `uv run uvicorn app.main:app --port 8000`.
  Base URL below is `API=http://localhost:8000`.
- A bearer token for the authed endpoints (auth is `/api/v1/auth`):
  ```bash
  API=http://localhost:8000
  TOKEN=$(curl -s -X POST $API/api/v1/auth/register \
    -H 'content-type: application/json' \
    -d '{"email":"pipe-test@example.com","password":"password123","name":"Pipe Test"}' \
    | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
  # (use POST /api/v1/auth/login the same way if the user already exists)
  ```

**Step 1 — tables created.** Start the API once (startup builds them), then in Supabase / psql:
```sql
SELECT tablename FROM pg_tables
WHERE tablename LIKE 'reporting_%' OR tablename = 'pipeline_runs';
```
Expect the four `reporting_*` tables + `pipeline_runs`.

**Step 2 — get some source events.** Either use the backoffice to create supply deliveries/consumptions,
or ingest a batch directly (ingest is unauthenticated):
```bash
curl -s -X POST $API/api/v1/telemetry/events -H 'content-type: application/json' -d '{
  "events":[
    {"eventId":"e1","timestamp":"2025-01-13T09:00:00Z","sessionId":"s1","userId":"u1",
     "event_type":"supply_consumption_created","schemaVersion":"1","requestId":"r1","service":"backoffice",
     "properties":{"supply_id":"sup-1","quantity":5,"consumption_type":"clinical_use","clinic_id":3,"jurisdiction":"us"}}
  ]}'
```
Expect `{"received":1,"stored":1,"rejected":0}` and a new `telemetry_events` row.

**Step 3 — run the pipeline from the CLI.**
```bash
uv run python data/pipelines/pipeline.py
```
Expect exit 0 and one `pipeline_runs` row with `status='success'`, `rows_loaded > 0`. Inspect:
```sql
SELECT run_id,status,rows_extracted,rows_loaded,rows_quarantined,started_at,finished_at FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;
SELECT * FROM reporting_consumption_volume_daily ORDER BY report_date DESC LIMIT 10;
```

**Step 4 — idempotency (the key check).** Record a count, run again over the same window, re-count:
```sql
SELECT count(*) FROM reporting_consumption_volume_daily;   -- before
```
```bash
uv run python data/pipelines/pipeline.py                    # second run
```
```sql
SELECT count(*) FROM reporting_consumption_volume_daily;   -- after — MUST be identical (upsert, not append)
```

**Step 5 — report parity.** Both report endpoints, same window, must return the **same metric values**:
```bash
curl -s "$API/api/v1/telemetry/report?start_date=2025-01-13&end_date=2025-01-20"     -H "Authorization: Bearer $TOKEN" > /tmp/report.json
curl -s "$API/api/v1/telemetry/raw-report?start_date=2025-01-13&end_date=2025-01-20" -H "Authorization: Bearer $TOKEN" > /tmp/raw.json
diff <(jq .metrics /tmp/report.json) <(jq .metrics /tmp/raw.json)   # expect no diff
```

**Step 6 — pipeline endpoints.**
```bash
curl -s $API/api/v1/telemetry/pipelines/runs/latest -H "Authorization: Bearer $TOKEN"          # last-run metadata
curl -s -X POST $API/api/v1/telemetry/pipelines/runs/trigger -H "Authorization: Bearer $TOKEN" # -> {message, run_id}
```
Confirm the trigger creates a **new** `pipeline_runs` row.

**Step 7 — fail-fast.** `unset DATABASE_URL; uv run python data/pipelines/pipeline.py` → clear one-line
error, non-zero exit, **no** traceback spew and **no** empty "success" run.

**Step 8 — PHI circuit breaker.** The ingest endpoint rejects non-allowlisted properties, so simulate
already-stored bad data by inserting a row directly, then run the pipeline:
```sql
INSERT INTO telemetry_events (id,timestamp,service,event_type,tags)
VALUES (gen_random_uuid(), now(), 'backoffice', 'supply_consumption_created',
        '{"supply_id":"x","clinic_id":3,"jurisdiction":"us","patient_name":"Jane Doe"}');
```
```bash
uv run python data/pipelines/pipeline.py
```
Expect the run to end `status='quarantined'`, `rows_quarantined > 0`, an `error_summary` mentioning PHI, and
**no** new reporting rows from that batch. (Delete the test row afterward.)

**Step 9 — frontend unchanged.** Confirm no diffs under the frontend app and that `/report`'s response
shape is byte-compatible with before the change.

## 9. Edge cases to handle

- Empty extract window → `status='success'`, `rows_loaded=0`, empty reporting write (not an error).
- Rows with null `clinic_id`/`jurisdiction`/`supply_id` → already dropped by `analysis.py`; count them as
  `rows_quarantined` if you surface them, don't crash.
- `supply_id` present as int vs string → normalize to string before upsert to keep the grain stable.
- Concurrent manual trigger during the nightly run → acceptable to serialize; a run-lock is **[roadmap]**.
- Late-arriving events → covered by the reprocess-window re-aggregation + upsert.

## 10. Definition of done

- [ ] `data/pipelines/pipeline.py`: ≥1 flow, ≥3 tasks; typed inputs/outputs.
- [ ] ≥1 task has `retries>0` + justification comment (extract).
- [ ] ≥1 optional task invoked `return_state=True`; flow continues on its failure.
- [ ] ≥1 transform task has `cache_key_fn` + `cache_expiration`.
- [ ] Four `reporting_*` tables + `pipeline_runs` created via SQLModel + registered in `main.py`.
- [ ] Load is a single-transaction idempotent upsert — second run over same window = **no duplicates** (§8 Step 4).
- [ ] Each run logs ≥5 metadata fields in `pipeline_runs`; status transitions running→success/partial/failed/quarantined.
- [ ] HIPAA PHI guard present (allowlist scan → `quarantined`, load blocked).
- [ ] Watermark advances only after a committed load.
- [ ] `python data/pipelines/pipeline.py` runs the full flow; fails fast if no DB URL.
- [ ] `GET /telemetry/report` reads reporting tables; `GET /telemetry/raw-report` preserves live compute; **frontend unchanged**.
- [ ] `GET …/pipelines/runs/latest` + `POST …/pipelines/runs/trigger` (imports the flow, no duplicated logic).
- [ ] Transforms reuse `analysis.py` (not reimplemented).
- [ ] Manual testing walkthrough (§8) run and captured (Supabase screenshot, idempotency counts, JSON parity) in the PR.
- [ ] Commit message: `feat: implement resilient prefect pipeline`.
