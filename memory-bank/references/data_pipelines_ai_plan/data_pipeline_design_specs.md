# Data Pipeline — Part 1 (Design) — Build Spec

> **Instructions for a coding agent.** Your deliverable is a **design document**, not code.
> Everything you need is in this spec and the HealthCore monorepo itself.
>
> **What you produce:** `docs/data_pipelines/pipeline-design.md` — Markdown design only. **No** Prefect
> flows, Python, SQL migrations, or runnable ETL in this part.
>
> **What this spec does:** tells you *which sections to write, to what quality bar, and against which
> real entity/table/path names.* It does **not** contain the finished design — you author that.

---

## Branch & workflow

- Create branch **`feature/data_pipeline`** off **`main`** and do **all** Part 1–3 work there — not off
  `feature/telemetry` or any other branch.
- Every code reference in this spec (`services/api/app/…`, `data/…`, `pyproject.toml`) reflects the state of
  **`main`**; the telemetry domain is already merged there. Verify against `main` if in doubt.
- Commit this part on that branch with `feat: add pipeline design document`. The pull request (opened after
  Build 2) targets **`main`**.

---

## 1. Objective

Document the design of an auditable, resilient ETL that turns raw telemetry in Supabase
(`telemetry_events`) into **materialized KPI reporting tables** that the dashboard reads — replacing the
current "recompute with Pandas on every request" approach.

**This is Part 1 of a 3-part milestone.** Write the design as the blueprint the later parts implement:

- **Part 1 — Design (this deliverable):** author `docs/data_pipelines/pipeline-design.md`. No code.
- **Build 1 (Part 2):** implements the Prefect flow + tasks, the `reporting_*` and `pipeline_runs`
  tables, idempotent load, and the pipeline endpoints — directly from your design.
- **Build 2 (Part 3):** refactors the flow into subflows and adds unit tests — without redesigning.

Another engineer must be able to build **Build 1** from your document without follow-up questions, and
**Build 2** must be a refactor of it, not a rework. Design at that altitude: name the flows, tasks, tables,
grains, and resilience choices concretely enough to implement, but do not write the code here.

## 2. Ground truth — use these real names (do NOT invent generic ones)

Use the entity, event, and column names below **exactly** as they appear in the codebase. Do not invent
generic or alternative names — the design must reference the real data model verbatim.

**Source table** — `telemetry_events` (Supabase/Postgres), SQLModel `TelemetryEventRow`
(`services/api/app/domains/telemetry/models.py`): columns `id (uuid)`, `timestamp (timestamptz)`,
`service`, `event_type`, `level`, `value (float?)`, `message (str?)`, `tags (jsonb)`. Append-only /
immutable. Read today via `load_events()` in `.../telemetry/repository.py`.

**Real event types:** `supply_delivery_created`, `supply_consumption_created`,
`supply_consumption_failed`, `supply_list_viewed`, `user_login_succeeded`, `user_login_failed`,
`session_expired`. Outbound uses `consumption_type ∈ {clinical_use, expiry_waste}`. `clinic_id` is an
**integer**; `jurisdiction ∈ {us, uk}`; both live inside `tags`.

**Existing transforms (the "current state"):** `services/api/app/domains/telemetry/analysis.py` computes
four KPIs with Pandas — `consumption_volume_per_day`, `waste_rate_per_day`,
`insufficient_stock_failures_per_day`, `auth_failure_rate` — aggregated by `build_metrics()` and served
**inside the request path** of `GET /api/v1/telemetry/report` (`.../telemetry/router.py`), with a 60s
in-memory cache (`cache.py`). These are the KPI grains the pipeline must preserve:

| KPI function | grain | outputs |
| --- | --- | --- |
| `consumption_volume_per_day` | `date · clinic_id · jurisdiction` | `count` |
| `waste_rate_per_day` | `date · jurisdiction` | `waste_rate`, `total` |
| `insufficient_stock_failures_per_day` | `date · clinic_id · jurisdiction · supply_id` | `count`, `attempts`, `rejection_rate` |
| `auth_failure_rate` | `date` | `failed`, `succeeded`, `failure_rate` |

**Data access pattern:** SQLModel + `create_engine(settings.database_url)` → `supabase_engine`
(`app/core/db.py`); session dep `get_supabase_db`. Tables are created at FastAPI startup via
`SQLModel.metadata.create_all(supabase_engine)` + raw idempotent SQL in `indexes.py`. The app **silently
skips** all Supabase work when `DATABASE_URL` is unset — call this out as a design risk.

**Decisions already made (encode these in the doc):**
1. **Load target:** pipeline materializes `reporting_*` tables; `GET /telemetry/report` reads **them**
   (same JSON shape → zero frontend change). The old live compute from `telemetry_events` is preserved
   under a renamed `GET /telemetry/raw-report` (the only HTTP endpoint that reads the raw table).
2. **Transform:** reuse `analysis.py`/`build_metrics` as-is.
3. **Prefect scope:** local ephemeral execution (`python data/pipelines/pipeline.py`), no server/Cloud;
   Supabase via existing `settings.database_url`; Prefect Blocks used only for config.
4. **Run log:** new Supabase `pipeline_runs` table.

## 3. Required sections of `docs/data_pipelines/pipeline-design.md` (map to eval criteria)

Instruct-level requirements — write each section; the content is yours.

1. **Current State** — the four `analysis.py` KPIs, storage in `telemetry_events`, the recompute-on-every-
   request path via `/telemetry/report`, and explicit limitations: no run log, no idempotent
   materialization, dropped rows silently discarded (`dropna`), no way to tell what a failed run
   processed. *(eval: current-state)*
2. **Purpose** — one concrete sentence tying the pipeline to HealthCore value (e.g. per-clinic supply
   visibility for Dr. Reid without ad-hoc Pandas). *(eval: purpose)*
3. **Extraction format** — source `telemetry_events`, JSONB `tags`, append-only, refresh cadence
   (nightly + on-demand), rough volume across 12 clinics / 2 jurisdictions, **watermark on `timestamp`**
   (not full-table scans). *(eval: extraction)*
4. **Data-flow diagram** — Mermaid, ≥3 stages, **real names**: `telemetry_events` → extract (watermark) →
   transform (`build_metrics`) → load (upsert) → `reporting_*` → read by `/telemetry/report`; plus
   `pipeline_runs` audit. *(eval: diagram)*
5. **Update / dedup strategy** — telemetry is append-only but KPI rows are recomputed on late arrivals.
   Specify **upsert on the KPI grain** (list the grains from §2) + a reprocess-window for late cross-
   jurisdiction events. Not "use DISTINCT". *(eval: dedup)*
6. **Idempotency strategy** — describe the **second run after a load-phase failure**: unique `run_id`,
   transactional upsert (no partial commits), `checkpoint` of last completed phase, **watermark advanced
   only after a committed load**. *(eval: idempotency)*
7. **Execution log** — `pipeline_runs` table with **≥5 fields**, each with name, type, audit
   justification. Cover at least: `run_id (uuid)`, `started_at`/`finished_at (timestamptz)`,
   `watermark_from`/`watermark_to`, `rows_extracted`/`rows_loaded`/`rows_quarantined (int)`,
   `status (enum success|partial|failed|quarantined)`, `error_summary (text?)`, `pipeline_version`. *(eval: exec-log)*
8. **Prefect mapping** — ≥2 flows (`telemetry_etl_flow`, `backfill_flow`), ≥3 tasks
   (`extract_telemetry_events`, `transform_kpi_aggregates`, `load_reporting_tables`), states
   (Running/Completed/Failed), and Blocks for config (`SupabaseConfig`/`PipelineConfig`). *(eval: prefect)*
9. **Build roadmap / handoff** — a short closing subsection stating how this design maps to the two build
   phases: **Build 1** implements the flow, tasks, `reporting_*` + `pipeline_runs` tables, idempotent load,
   the CLI entry point, the status/trigger endpoints, the materialized `GET /telemetry/report`, and the
   preserved live `GET /telemetry/raw-report`; **Build 2** refactors the flow into per-stage
   subflows and adds unit tests — no redesign. Name the flows/tasks/tables here so both builds inherit the
   same vocabulary. This makes the design document self-describe the sequence it feeds.

### 3.10 Interfaces & fields the doc must specify (design-level — describe, don't code)

These are the concrete artifacts the design must pin down so Build 1 has no open questions. Present them as
tables/prose in the doc, not as Python.

- **Watermark strategy.** Define `watermark_from` / `watermark_to` precisely: `watermark_to = now (UTC)` at
  run start; `watermark_from = ` the latest successful run's `watermark_to` **minus a reprocess-window**;
  first-run fallback = a configured lookback. State the exact rule you choose.
- **Reprocess-window.** Define the term — re-aggregate the last *N* days so late cross-jurisdiction events
  (US morning vs. UK mid-day) correct already-loaded aggregates via upsert. State the default (e.g. 2 days)
  and why.
- **Reporting tables.** One materialized table per KPI; list each table's **name, grain (unique key), and
  value columns** using the grains in §2, plus provenance (`run_id`, `updated_at`). This is the upsert
  conflict target.
- **`pipeline_runs` field template** — present a table with **name · type · audit justification** for each
  field (`run_id`, `started_at`/`finished_at`, `watermark_from`/`watermark_to`,
  `rows_extracted`/`rows_loaded`/`rows_quarantined`, `status`, `error_summary`, `pipeline_version`,
  `checkpoint`). ≥5 required; justify each.
- **Prefect Blocks** — specify the config Blocks and their fields: e.g. `SupabaseConfig { database_url }`
  and `PipelineConfig { event_types, reprocess_window_days, lookback_days, batch_size, pipeline_version }`.
- **Endpoints** — name the reporting/pipeline endpoints Build 1 adds (`GET /telemetry/report` materialized,
  `GET /telemetry/raw-report` live, `GET /telemetry/pipelines/runs/latest`, `POST …/runs/trigger`) and note
  each returns the existing JSON conventions.

## 4. Resilient, Observable, and Recoverable pipeline features

The rubric only names retries/idempotency; HealthCore is a healthcare pipeline, so the design **must** also
document defense-in-depth. Organize by ETL stage + cross-cutting, and mark each as **[rubric]**,
**[required-here]**, or **[roadmap]** so Build 1 knows what to actually build. For every item, the doc must
state **(a) the concrete failure scenario it defends against** and **(b) a 1–2 sentence rationale** — a bare
list of mechanism names is not sufficient.

- **Extract:** smart retries with `retry_condition_fn` (retry only transient/connection errors, never
  validation) **[rubric+]**, backoff+jitter, `timeout_seconds`, chunked reads **[roadmap]**.
- **Transform:** schema validation + defensive coercion (`errors="coerce"`) **[required-here]**;
  **row quarantine / dead-letter with reason + count** (don't silently `dropna`) **[required-here]**;
  per-KPI isolation via `return_state=True` so one broken metric can't blank the others **[required-here]**;
  **HIPAA compliance circuit breaker** — scan `tags` against the allowlist, on suspected PHI **halt the
  run, set `status=quarantined`, escalate, block the load** (fail closed) **[required-here]**.
- **Load:** transactional all-or-nothing upsert **[rubric]**; watermark-after-commit **[required-here]**;
  savepoints for sub-batch, advisory run-lock / Prefect concurrency limit **[roadmap]**.
- **Cross-cutting:** `on_failure`/`on_crashed` state hooks + structured `error_summary` + `run_id`
  correlation **[required-here]**; volume/freshness anomaly check **[roadmap]**; **fail-fast if
  `database_url` missing** (never silently report empty KPIs) **[required-here]**;
  serve-last-good (a failed run leaves prior committed reporting rows in place) **[required-here]**.
- **Recovery:** `checkpoint`/resume, `backfill_flow`, reprocess-window for late data **[roadmap]**.

**Run states.** Define the `pipeline_runs.status` lifecycle and when each is set: `running` (in progress) →
`success` (all stages committed, watermark advanced) · `partial` (an optional/isolated step failed, the
rest loaded — serve-last-good holds) · `failed` (a critical stage crashed, nothing committed, on-call
paged) · `quarantined` (PHI/schema breach tripped the circuit breaker, load blocked, compliance escalated).

Also document the **batch/transaction tradeoff**: one big transaction (atomic but fragile) vs. chunked
idempotent upserts (recoverable, needs upsert to be safe on replay). State the chosen approach and why.

## 5. Repo traps to note in the doc

- Package management is **uv**; Prefect isn't installed yet (Build 1 adds it via `uv add "prefect>=3"`).
- The pipeline will live at repo-root `data/pipelines/` but must import app code from `services/api`
  (`app.core.db`, `app.domains.telemetry.analysis`) — a cross-root import. Note that Build 1 must make
  `services/api` importable from the script (sys.path / workspace), and endpoints in `services/` must
  import the flow from `data/pipelines/` (repo root importable, `data/__init__.py`).

## 6. Anti-patterns (reject these — they mark an incomplete design)

- Generic or invented table/entity names (`events`, `metrics`, etc.) instead of the real §2 vocabulary.
- A data-flow diagram with only two stages, or missing the real source/destination names.
- Idempotency written as a wish ("should be idempotent") without describing the **second run** after a load
  failure.
- Execution-log fields listed **without types or audit justification**.
- Prefect section naming a single flow/task, or listing Prefect concepts without pipeline-specific names.
- No Current State section — jumping straight to the ideal architecture, ignoring the existing Pandas path.
- Resilience listed as bare mechanism names with no failure scenario or rationale (see §4).
- **Any orchestration code, SQL migrations, or `pipeline.py`** committed in this part — design only.

For the meatier sections (Current State, Purpose, Update/dedup, Idempotency), include a brief **strong-vs-weak
example** in your own words so the quality bar is unambiguous, but keep the doc itself a design, not a tutorial.

## 7. Definition of done

- [ ] `docs/data_pipelines/pipeline-design.md` exists; **design only**, no orchestration code.
- [ ] Purpose is one concrete HealthCore sentence.
- [ ] Diagram shows extract→transform→load with real table/entity names.
- [ ] Update/dedup uses a concrete mechanism (upsert on named grain), not DISTINCT.
- [ ] Idempotency describes the second run after a load failure.
- [ ] Execution log ≥5 fields with name, type, justification (§3.10 template).
- [ ] Prefect mapping ≥2 flows + ≥3 tasks with concrete names + Blocks (§3.10).
- [ ] Watermark strategy, reprocess-window, reporting tables, and run states all specified.
- [ ] Consistent with the four `analysis.py` KPIs and real event/entity names.
- [ ] Includes the "Resilient, Observable, and Recoverable pipeline features" section (§4), each item with a failure scenario + rationale and a rubric/required/roadmap tag.
- [ ] Includes the Build roadmap / handoff subsection (§3.9) naming what Build 1 and Build 2 each do.
- [ ] Commit message: `feat: add pipeline design document`.
