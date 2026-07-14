---
name: Data Pipeline Build 1 (Part 2)
overview: "Implement resilient Prefect ETL from pipeline-design.md: reporting_* + pipeline_runs tables, idempotent load, PHI guard, CLI, materialized report + raw-report + pipeline endpoints. Pause before Build 2."
todos:
  - id: b1-prereq
    content: Confirm Design signed off (docs/data_pipelines/pipeline-design.md) on feature/data_pipeline; DATABASE_URL for milestone5_inventory
    status: pending
  - id: b1-deps
    content: uv add prefect>=3 to services/api; re-lock services/api/uv.lock and root uv.lock
    status: pending
  - id: b1-models
    content: Add reporting_models.py (4 reporting_* + pipeline_runs); import in main.py; index on pipeline_runs.started_at
    status: pending
  - id: b1-repo
    content: Add data/process/reporting_repository.py (upserts + report readers) and data/pipelines/config.py
    status: pending
  - id: b1-flow
    content: Implement data/pipelines/pipeline.py — flows, tasks, watermark, PHI, run log, CLI fail-fast; return_state=True on snapshot
    status: pending
  - id: b1-endpoints
    content: Repoint GET /telemetry/report; add raw-report + pipelines/runs/latest + runs/trigger; no frontend changes
    status: pending
  - id: b1-design-doc
    content: Update docs/data_pipelines/pipeline-design.md with run command + nightly schedule confirmation
    status: pending
  - id: b1-manual
    content: Run Build 1 specs §8 walkthrough against live Supabase; capture evidence for PR
    status: pending
  - id: b1-commit
    content: Commit feat: implement resilient prefect pipeline; pause for review before Build 2
    status: pending
isProject: false
---

# Data Pipeline — Part 2 (Build 1) Implementation Plan

**Plan file:** [`data_pipeline_build1_implementation_plan.md`](data_pipeline_build1_implementation_plan.md)

**Requirements sources:**

- [`data_pipeline_build1_specs.md`](data_pipeline_build1_specs.md)
- [`data_pipeline_build1_eval_criteria.md`](data_pipeline_build1_eval_criteria.md)
- Design artifact: [`docs/data_pipelines/pipeline-design.md`](../../../docs/data_pipelines/pipeline-design.md) (must exist / signed off before coding)
- Design plan (locked decisions): [`data_pipeline_design_implementation_plan.md`](data_pipeline_design_implementation_plan.md)

**Branch:** `feature/data_pipeline` (continue; do not branch off `feature/telemetry`)

**Status:** **Implemented on branch** — pending manual Supabase walkthrough + commit acknowledgement. **Pause** before Build 2.

**Frontend:** Do not change any UI apps.

---

## Executive summary

Build 1 turns the design into a runnable local Prefect ETL:

1. Materialize four KPI grains into `reporting_*` tables via idempotent upsert  
2. Audit every run in `pipeline_runs`  
3. CLI entry `python data/pipelines/pipeline.py` (fail-fast without `DATABASE_URL`)  
4. Repoint `GET /telemetry/report` to reporting tables; preserve live compute as `GET /telemetry/raw-report`  
5. Add latest-run + trigger endpoints that import the flow (no duplicated ETL)

Transforms **reuse** `build_metrics` / `analysis.py` — do not reimplement KPIs.

---

## Prerequisites

- [ ] Design delivered: `docs/data_pipelines/pipeline-design.md` committed on `feature/data_pipeline`
- [ ] Stakeholder Design sign-off received
- [ ] Working on `feature/data_pipeline` off `main`
- [ ] `DATABASE_URL` for Supabase project **`milestone5_inventory`** available for §8 manual tests
- [ ] Vocabulary in code matches design (flows/tasks/tables/states)

---

## Locked decisions (carry forward)

| Topic | Decision |
|---|---|
| Design / run-command path | **Only** `docs/data_pipelines/pipeline-design.md` (eval mentions `data/pipelines/PIPELINE_DESIGN.md` — do not create that file; document run command in the docs path + brief inline CLI comment) |
| Config | `data/pipelines/config.py` constants (= Prefect Block field equivalents from design) |
| Flows | `telemetry_etl_flow` + thin `backfill_flow(start, end)` calling same tasks |
| Transform | One `transform_kpi_aggregates` → `build_metrics`; per-KPI isolation = roadmap |
| Checkpoint | Write audit phases only; no resume |
| PHI | Fail-closed: union of `EVENT_PROPERTY_ALLOWLIST` keys + envelope keys; value heuristics (email / DOB-shaped); trip → `quarantined`, no load |
| Extract event types | KPI-only (see below) |
| Quarantine counts | Count null-grain / invalid rows around load; do not change KPI math in `analysis.py` except optional coerce on a prepare helper if needed for NaT |
| Timestamps | Prefer `errors="coerce"` → NaT where Build 1 touches prepare |
| Snapshot task | **Required.** `export_snapshot_optional` writes JSON under `data/process/`; invoked with **`return_state=True`**; failure → continue + `status=partial` |
| Trigger | FastAPI `BackgroundTasks`; import flow from `data.pipelines.pipeline` |
| Latest run mapping | Eval fields: `started_at`, `finished_at`, `rows_loaded` (records processed), `status`, `error_summary` |
| uv | `uv add "prefect>=3"` on `healthcore-api`; re-lock **both** lockfiles |
| Consistency | Implement only design items tagged **Build 1**; leave roadmap items undocumented-as-implemented |

### KPI-only extract `event_types`

Definitive list from current `analysis.py` `load_events` calls (re-confirm in Step 1):

```text
supply_consumption_created
supply_consumption_failed
user_login_succeeded
user_login_failed
```

Do **not** include v1.1 abandon/filter, `supply_delivery_created`, `supply_list_viewed`, or `session_expired` — they are not inputs to `build_metrics`. Put this list in `config.py` as `KPI_EVENT_TYPES`.

---

## Eval criteria crosswalk (Build 1)

| Eval criterion | Implementation |
|---|---|
| `data/pipelines/pipeline.py` ≥1 flow, ≥3 tasks | `telemetry_etl_flow` + extract / transform / load (+ snapshot) |
| Task `retries>0` + justifying comment | `extract_telemetry_events`: retries=3, delays `[10,30,60]`, `retry_condition_fn`, comment |
| Non-critical task + **`return_state=True`**, flow continues | `export_snapshot_optional`; on fail → `partial` |
| Transform `cache_key_fn` + `cache_expiration` | `transform_kpi_aggregates` (window key, 1h) |
| Idempotent load | Single-tx Postgres upsert on grains; §8 Step 4 proves no duplicate count |
| ≥5 run metadata fields | `pipeline_runs`: `started_at`, `finished_at`, `rows_loaded`, `status`, `error_summary` (+ extras) |
| Script runs full ETL | `__main__` → `telemetry_etl_flow()` when DB configured |
| Run command documented | Update **`docs/data_pipelines/pipeline-design.md`** (+ short inline comment in `pipeline.py`) |
| Latest-run endpoint in `services/` | `GET /api/v1/telemetry/pipelines/runs/latest` |
| Trigger endpoint imports flow | `POST /api/v1/telemetry/pipelines/runs/trigger` |
| Consistent with design | Stages/entities/resilience tagged Build 1 in design = coded |

---

## Suggested file layout

```text
data/
  __init__.py
  pipelines/
    __init__.py
    pipeline.py              # flows + tasks + CLI
    config.py                # watermark / reprocess / event_types / version
  process/
    __init__.py
    reporting_repository.py  # upserts + SELECT readers (no Prefect)
services/api/app/domains/telemetry/
  reporting_models.py        # 4 reporting_* + pipeline_runs
  pipeline_router.py         # optional split for runs/latest + trigger
  router.py                  # report + raw-report (or include all)
```

Import traps (must solve in Build 1):

- Script under `data/` imports `app.core.db`, `app.domains.telemetry.*` → make `services/api` importable (`sys.path` / run via `uv run` from workspace with `pythonpath`)
- API endpoints import flow from `data.pipelines.pipeline` → repo root on `sys.path`; ensure `data/__init__.py` exists

---

## Implementation steps

### Step 0 — Prerequisites check

Confirm design doc exists and lists Build 1 vs roadmap tags. Stay on `feature/data_pipeline`.

### Step 1 — Dependency + baseline audit

```bash
cd services/api && uv add "prefect>=3"
# re-lock root workspace as well (conventions: dual lockfiles)
cd ../.. && uv lock   # or equivalent workspace lock so root uv.lock updates
```

Audit:

- `analysis.py` `load_events` event-type lists → finalize `KPI_EVENT_TYPES` in `config.py`
- `mapper.EVENT_PROPERTY_ALLOWLIST` → build PHI key union + envelope keys
- Current `GET /telemetry/report` shape (must remain byte-compatible for frontend)

### Step 2 — SQLModel tables (`reporting_models.py`)

Define and import in `app/main.py` next to `telemetry_models` so `create_all` builds them.

| Table | Unique grain | Value columns + provenance |
|---|---|---|
| `reporting_consumption_volume_daily` | `(report_date, clinic_id, jurisdiction)` | `count`; `run_id`; `updated_at` |
| `reporting_waste_rate_daily` | `(report_date, jurisdiction)` | `waste_rate`, `total`; `run_id`; `updated_at` |
| `reporting_stock_failures_daily` | `(report_date, clinic_id, jurisdiction, supply_id)` | `count`, `attempts`, `rejection_rate`; `run_id`; `updated_at` |
| `reporting_auth_failure_daily` | `(report_date)` | `failed`, `succeeded`, `failure_rate`; `run_id`; `updated_at` |
| `pipeline_runs` | `run_id` PK | See design; include all locked columns |

Map KPI `date` string → `report_date (date)` on load. Normalize `supply_id` to `str`.

Add index via `indexes.py` (or sibling):

```sql
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs (started_at DESC)
```

### Step 3 — `config.py` + `reporting_repository.py`

**`config.py`:** `REPROCESS_WINDOW_DAYS=2`, `LOOKBACK_DAYS` (e.g. 7), `PIPELINE_VERSION`, `KPI_EVENT_TYPES`, snapshot path under `data/process/`.

**`reporting_repository.py`:**

- `upsert_*` helpers using `sqlalchemy.dialects.postgresql.insert` + `on_conflict_do_update` on grain columns
- `load_all_reporting(...)` → all four upserts inside **`with supabase_engine.begin() as conn:`** (one transaction)
- Readers that `SELECT` between `report_date` bounds and reshape to the existing report JSON metric lists (`date` as string keys)

### Step 4 — Prefect flow & tasks (`pipeline.py`)

```text
telemetry_etl_flow(start=None, end=None)
  start_run() → pipeline_runs status=running, run_id
  resolve_window() → watermark_from / watermark_to
  extract_telemetry_events  @task(retries=3, retry_delay_seconds=[10,30,60], retry_condition_fn=...)
  PHI scan on extracted tags → on trip: status=quarantined, rows_quarantined, no load, stop
  transform_kpi_aggregates  @task(cache_key_fn=window_cache_key, cache_expiration=1h) → build_metrics
  load_reporting_tables     # transactional upsert; checkpoint=load; watermark only after commit
  export_snapshot_optional(..., return_state=True)  # REQUIRED wiring
  finish_run success | partial (snapshot failed) | failed (critical, recorded then re-raise)

backfill_flow(start, end) → same pipeline with explicit window (thin wrapper)
```

**Watermark:**  
`watermark_from` = max `watermark_to` of latest `status='success'` run minus reprocess-window; first run → lookback.  
`watermark_to` = `end or now(UTC)`.

**PHI circuit breaker (before load):**

- Allowed keys = ∪ of all `EVENT_PROPERTY_ALLOWLIST` property keys + envelope keys  
- Trip on unknown key or PHI-like value  
- Do not load; `error_summary` mentions PHI; WARNING log  

**CLI:**

```python
if __name__ == "__main__":
    if supabase_engine is None:
        raise SystemExit("DATABASE_URL is not set — refusing to run against no database.")
    telemetry_etl_flow()
```

Document: `uv run python data/pipelines/pipeline.py` and nightly `0 2 * * *` in **`docs/data_pipelines/pipeline-design.md`**.

**Edge cases (specs §9):** empty window → `success`, `rows_loaded=0`; null grain dims counted quarantined / not crash; concurrent trigger acceptable without run-lock (roadmap).

### Step 5 — HTTP endpoints

All under `/api/v1/telemetry`, auth `get_current_user` (same as current report).

| Endpoint | Behavior |
|---|---|
| `GET /telemetry/report` | Read `reporting_*` via repository; keep `cache.py` wrapper; same JSON shape |
| `GET /telemetry/raw-report` | Former report: `build_metrics` live + cache |
| `GET /telemetry/pipelines/runs/latest` | Newest `pipeline_runs` row; include eval fields; 404 or null if none |
| `POST /telemetry/pipelines/runs/trigger` | Create/run via BackgroundTasks importing `telemetry_etl_flow`; `{ "message": "Pipeline run submitted", "run_id": "<uuid>" }` |

Register new router (or extend existing) in `app/api/v1/router.py` if split. Import `reporting_models` in `main.py` for `create_all`.

**Zero frontend change** — URL/shape/auth of `/report` unchanged.

### Step 6 — Manual testing walkthrough (specs §8)

Prerequisites: `DATABASE_URL`, `uv sync`, API on `:8000`, bearer token via register/login.

| Step | Expect |
|---|---|
| 1 Tables | Four `reporting_%` + `pipeline_runs` after API startup |
| 2 Seed event | Ingest or UI activity → `telemetry_events` row |
| 3 CLI run | Exit 0; `pipeline_runs.status=success`; `rows_loaded>0` |
| 4 Idempotency | Second run → **same** `reporting_*` row counts |
| 5 Parity | `jq .metrics` of `/report` vs `/raw-report` equal for same window |
| 6 Pipeline endpoints | latest + trigger create new run row |
| 7 Fail-fast | unset `DATABASE_URL` → clear exit ≠0, no false success |
| 8 PHI | Direct SQL insert with `patient_name` → `quarantined`, no new reporting rows from that batch |
| 9 Frontend | No diffs under `uis/`; response shape compatible |

Capture SQL counts, curl/jq parity, and run metadata for the eventual PR.

### Step 7 — Commit and pause

```text
feat: implement resilient prefect pipeline
```

**Stop.** Do not start Build 2 (subflows / `tests/pipelines`) until Build 1 sign-off.

---

## Out of scope (Build 1)

- Prefect server/Cloud; real Prefect Block registration (constants only)
- Subflow refactor and `tests/pipelines/test_pipeline.py` (Build 2)
- Frontend changes
- Roadmap: chunked reads, run-lock, resume, per-KPI task isolation, anomaly detection
- Changing ingest allowlist behavior (pipeline PHI is defense-in-depth for already-stored rows)

---

## Definition of done

- [ ] All Build 1 eval checkboxes satisfied (run command documented under **`docs/data_pipelines/pipeline-design.md`**)
- [ ] Specs §10 checklist complete (tables, upsert, PHI, endpoints, reuse `analysis.py`, manual §8)
- [ ] Design **Build 1** resilience items reflected in code; roadmap items not falsely claimed
- [ ] Dual uv lockfiles updated for Prefect
- [ ] Commit message: `feat: implement resilient prefect pipeline`
- [ ] Stakeholder pause before Build 2 plan / implementation

---

## Residual risks

| Risk | Mitigation |
|---|---|
| Cross-root imports fail under `uv run` | Explicit path bootstrap in `pipeline.py` and API import of `data.*`; smoke CLI early |
| Postgres-only upsert vs SQLite tests | Build 1 verification on live Supabase; no SQLite upsert unit tests required in this phase |
| Eval path `PIPELINE_DESIGN.md` | Stakeholder accepted docs path only; document clearly in design + this plan |
| PHI union vs flat Build 1 spec list | Stakeholder locked mapper ∪ envelope — note in design so consistency holds |
| Background trigger overlaps nightly | Acceptable serialization; run-lock roadmap |
