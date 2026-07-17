# Background Processes (DEV-53: Nightly Telemetry Script) — Build Spec

> **Instructions for a coding agent.** Build a nightly job that exports the previous day's telemetry to
> CSV, triggers the Milestone 6 data pipeline as a subprocess, and records every execution in a new
> `job_runs` table with a `pending → processing → completed | failed` state machine. Everything you need
> is in this spec and the HealthCore monorepo.
>
> **Deliverables:** `services/api/app/domains/jobs/` (model + `job_runner`), `scripts/nightly_export.py`,
> an argparse CLI on `data/pipelines/pipeline.py`, cron docs in the README, and tests in
> `services/api/tests/test_job_runner.py` + `tests/jobs/test_nightly_export.py`.
>
> **§1 is mandatory reading.** The ticket was written against assumptions this repo does not satisfy.
> Following the ticket's reference command literally will not work.

---

## Branch & workflow

- Continue on **`feature/data_pipeline`** — this work lands there.
- Every code reference in this spec reflects the current state of that branch.
- Commit with `feat: add nightly telemetry export job with job_runs state machine`, then **open the pull
  request against `main`** and add the **`cronjob`** label.

---

## 1. Deviations from the ticket (read before writing any code)

The ticket describes a repo that differs from this one in eight ways. Each entry gives the requirement as
written, what the repo actually has, and the resolution — all resolutions are decided; do not re-litigate.

### 1.1 The pipeline entry point does not exist as written

Ticket says `python -m data.pipelines.telemetry_kpi_daily.run --no-prefect`. There is no
`data/pipelines/telemetry_kpi_daily/` package. The real Milestone 6 entry point is
`data/pipelines/pipeline.py`, whose `__main__` calls `telemetry_etl_flow()`.

**Resolution:** the subprocess target is `data/pipelines/pipeline.py` (see §4.4 for the exact argv).

### 1.2 `--no-prefect` has nothing to disable

Prefect 3 is a hard dependency (`prefect>=3` in `services/api/pyproject.toml`) and the flow runs
local-ephemeral — no Prefect server, no Cloud, no agent. There is no mode to turn off.

**Resolution:** do **not** add a no-op `--no-prefect` flag to satisfy the ticket's wording. The PR body
states that the flag is inapplicable to a local-ephemeral setup and names the real command instead.

### 1.3 The pipeline cannot accept a target date — this is the load-bearing gap

`data/pipelines/extract/window.py::resolve_window` derives its window from the last successful
`pipeline_runs` watermark minus `REPROCESS_WINDOW_DAYS`, up to *now* — or `now - LOOKBACK_DAYS` on a cold
start. It ignores any notion of "yesterday". If the script resolves `target_date` and then shells out to
`pipeline.py` with no arguments, **`TARGET_DATE` would control the CSV export but silently not the
pipeline**, and the rubric's "idempotent per `target_date`" claim would be false.

`telemetry_etl_flow(start, end)` already accepts an explicit window; nothing exposes it on the CLI.

**Resolution:** add an argparse CLI to `pipeline.py` (§3) and pass the target day's UTC bounds. This is the
**only** sanctioned change to Milestone 6 code — do not touch `resolve_window`, the subflows, or the
tasks.

### 1.4 There is no migration system

Ticket says "add the migration or SQL statement". There is no Alembic, no migrations directory, no
`.sql` schema file. Every table in this repo is created by `SQLModel.metadata.create_all()`, called from
`services/api/app/main.py:57` (startup), `app/domains/telemetry/seed_reporting.py:265`, and
`data/pipelines/pipeline.py:91`.

**Resolution:** declare `JobRun` as a SQLModel `table=True` model. Do not introduce Alembic. Do not
hand-write a `.sql` file. See §2 for how creation is guaranteed for a script that runs without the API.

### 1.5 `services/` cannot host the status logic

Ticket says "put the status logic in `services/`". `services/` is not a Python package — it has no
`__init__.py` and contains only `Dockerfile`, `.dockerignore`, and `api/`. Creating `services/jobs/`
would require new package markers and a second import root for one module.

**Resolution:** the module lives at **`services/api/app/domains/jobs/`**, alongside the seven existing
domains (`auth`, `incidents`, `inventory`, `procurement`, `reporting`, `telemetry`, `users`). It is still
under `services/`, and it follows the convention the repo actually uses.

**Constraint this creates — do not violate it.** The first eval criterion is that the script "does not
import or execute FastAPI code on the application's main thread." Because `job_runner` now sits inside the
`app.*` package, it must import **only** `app.core.db`, `app.core.config`, `sqlmodel`, and stdlib. Never
`app.main`, never a router, never `fastapi`, never anything that transitively constructs the `FastAPI()`
object. The script is a separate OS process regardless, so the criterion holds — but the PR body must
state that reasoning explicitly rather than leave a reviewer to infer it from the import path.

### 1.6 The two status vocabularies deliberately do not match

`pipeline_runs` (`app/domains/telemetry/reporting_models.py:82`) already uses
`running` / `success` / `partial` / `quarantined` / `failed`. The ticket's state machine for `job_runs` is
`pending` / `processing` / `completed` / `failed`.

**Resolution:** implement the ticket's vocabulary verbatim for `job_runs` and **do not harmonize the two**.
They are different layers, and the rubric grades both the ticket's state machine *and* the two tables'
independence. Do not add a foreign key between them, do not merge them, do not rename either set.

### 1.7 Stale-lock reclaim vs. "no second locking mechanism"

The ticket forbids a separate lock table, column, or flag. Taken literally with no timeout, a `SIGKILL`ed
run strands its row in `processing` forever and **silently blocks every future night** — the failure mode
the ticket's own "no zombie records" clause is trying to prevent.

**Resolution:** implement a staleness timeout (§2.3). It acts on the same `status` column and adds no
table, column, or flag, so the rubric's constraint holds. The PR body notes it as a deliberate,
documented extension.

### 1.8 `data/raw/` is not gitignored

`.gitignore` covers `data/process/snapshots/` and `data/pipelines/load/snapshots/`, but not `data/raw/`.
A full-dump CSV writes raw `tags` — the exact field the pipeline's own PHI circuit-breaker
(`data/pipelines/extract/phi.py`) exists to guard — into a tracked directory.

**Resolution:** add `data/raw/*.csv` to `.gitignore` as part of this change. The CSV is a local
backup/audit artifact; the PR shows an excerpt rather than committing the file.

---

## 2. Phase 1 — the `jobs` domain (`services/api/app/domains/jobs/`)

Create the package: `__init__.py`, `models.py`, `job_runner.py`.

### 2.1 `models.py` — the `job_runs` table

```python
class JobRun(SQLModel, table=True):
    __tablename__ = "job_runs"
```

Fields (all required by the ticket's data model checklist):

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | primary key, `default_factory=uuid4` |
| `job_name` | `str` | `"nightly_export"` for this job |
| `target_date` | `date` | **required** — the idempotency key, never nullable |
| `status` | `str` | `pending` \| `processing` \| `completed` \| `failed` |
| `started_at` | `datetime \| None` | tz-aware; set on the `processing` transition |
| `finished_at` | `datetime \| None` | tz-aware; set on `completed` / `failed` |
| `error_message` | `str \| None` | truncate to 500 chars, matching `PipelineRun.error_summary` |
| `created_at` | `datetime` | tz-aware; set on the `pending` insert |

- Use `Column(sa.DateTime(timezone=True))` for every datetime — copy the pattern from
  `reporting_models.py`. Naive datetimes will silently corrupt the UTC day-boundary logic.
- Add the composite index on `(job_name, target_date)` via
  `__table_args__ = (sa.Index("ix_job_runs_job_name_target_date", "job_name", "target_date"),)`.
- Do **not** make it unique — failed runs and retries legitimately produce multiple rows per
  `(job_name, target_date)`.

### 2.2 Table creation

The model must be imported somewhere in the `app.*` chain so the API's startup `create_all` picks it up
(free table creation in the normal flow). **The script must not depend on that** — it may run before the
API has ever booted. `scripts/nightly_export.py` imports `JobRun` and calls
`SQLModel.metadata.create_all(engine)` itself, exactly as `pipeline.py:91` does.

### 2.3 `job_runner.py` — the status service

Import ceiling: `app.core.db`, `app.core.config`, `sqlmodel`, `sqlalchemy`, stdlib. Nothing else (§1.5).

Required functions:

- `create_pending(session, job_name, target_date) -> JobRun` — inserts with `status="pending"` and
  `created_at`. The row exists **before** any work begins.
- `mark_processing(session, run) -> None` — sets `status="processing"` and `started_at`. This transition
  **is** the lock; it happens before any work.
- `mark_completed(session, run) -> None` — sets `status="completed"` and `finished_at`.
- `mark_failed(session, run, error) -> None` — sets `status="failed"`, `finished_at`, and
  `error_message` (truncated to 500).
- `has_processing_lock(session, job_name) -> bool` — true if any **non-stale** `processing` row exists for
  `job_name`, across all dates. A concurrent run for a *different* date is still a conflicting run.
- `has_completed_for_date(session, job_name, target_date) -> bool` — true if a `completed` row exists for
  that exact `(job_name, target_date)`. Checking `job_name` alone is explicitly insufficient per the
  rubric.
- `reclaim_stale_locks(session, job_name) -> int` — transitions `processing` rows whose `started_at` is
  older than the staleness threshold to `failed`, with
  `error_message="reclaimed: stale processing lock (no heartbeat for >Nh)"`. Returns the count. Called
  **before** `has_processing_lock`. Threshold: module-level constant `STALE_LOCK_HOURS = 6`, overridable
  via a `STALE_LOCK_HOURS` env var.

Every function takes an existing `Session` — the script owns the session lifecycle, not the service.

---

## 3. Phase 2 — argparse CLI on `data/pipelines/pipeline.py`

Minimal, additive change to the `if __name__ == "__main__":` block only. Do not alter the flows or tasks.

- Add `--start` and `--end`, both `YYYY-MM-DDTHH:MM:SS+00:00`-parseable ISO 8601 datetimes.
- Both provided → pass straight through to `telemetry_etl_flow(start=..., end=...)`. The existing
  `resolve_window` already honours an explicit window and short-circuits the watermark path.
- Neither provided → call `telemetry_etl_flow()` exactly as today. **Existing behaviour must not change**
  — `uv run python data/pipelines/pipeline.py` with no args stays byte-for-byte equivalent.
- Only one provided → `parser.error(...)`, exit non-zero.
- Parse to tz-aware UTC; reject naive input rather than assuming a timezone.
- Keep the existing `DATABASE_URL` guard and its `sys.exit(1)` ahead of any flow invocation.
- Exit code must be non-zero when the flow raises — the script depends on it (§4.4).

---

## 4. Phase 3 — `scripts/nightly_export.py`

Runnable as `python scripts/nightly_export.py` from the repo root.

### 4.1 Bootstrap

Copy the `sys.path` pattern from `data/pipelines/pipeline.py:27-33` — insert both `services/api` (for
`app.*`) and the repo root (for `data.*`) before any first-party import. Guard the engine: if
`app.core.db.supabase_engine` is `None`, log an actionable error naming `DATABASE_URL` and exit `1`
**before** touching `job_runs`. Never create a row you cannot later transition.

### 4.2 Target date resolution

- `TARGET_DATE` env var (`YYYY-MM-DD`) if set — parse strictly; on a malformed value, exit non-zero with
  a clear message. Do not fall back to yesterday.
- Otherwise `datetime.now(timezone.utc).date() - timedelta(days=1)`.
- Day bounds: `start = midnight UTC of target_date`, `end = start + 1 day`. Half-open `[start, end)` —
  matches `load_events`, which already uses `timestamp >= start` and `timestamp < end`.

### 4.3 Guard order (exact sequence — the rubric grades this)

1. `reclaim_stale_locks(session, "nightly_export")` — log a WARNING per reclaimed row.
2. `has_processing_lock(session, "nightly_export")` → if true, **log at INFO and exit `0` silently**. Not
   an error; a second instance aborting is correct behaviour. No row is created.
3. `has_completed_for_date(session, "nightly_export", target_date)` → if true, log
   "skipped as duplicate" at INFO and exit `0`. No CSV, no pipeline, no new row.
4. `create_pending(...)` → then `mark_processing(...)`, committed **before** any work.

### 4.4 Work

**CSV export.** Target `data/raw/telemetry_<target_date>.csv` (e.g. `telemetry_2026-07-14.csv`). If the
file already exists, skip the export and log at INFO — do not overwrite, do not re-query. Otherwise
`SELECT * FROM telemetry_events` for `[start, end)` — a **full dump**: `id`, `timestamp`, `service`,
`event_type`, `level`, `value`, `message`, `tags`. All event types, not just `KPI_EVENT_TYPES`.

Do **not** reuse `app.domains.telemetry.repository.load_events` — it filters to four event types and
projects four columns, which is the pipeline's need, not the backup's. Write a dedicated query in the
script.

Serialize `tags` (JSONB) with `json.dumps` so the CSV is round-trippable. Write to a temp file in
`data/raw/` and `os.replace()` into place, so a crash mid-write cannot leave a truncated CSV that the
"file exists" check would later treat as complete. `mkdir(parents=True, exist_ok=True)` first.

**Pipeline trigger.** After the export, `subprocess.run` with an argv list (never `shell=True`):

```
["uv", "run", "python", "data/pipelines/pipeline.py",
 "--start", start.isoformat(), "--end", end.isoformat()]
```

`cwd` = repo root, `check=True`, capture stdout/stderr. On `CalledProcessError`, include the captured
stderr tail in the error that propagates. This runs the Build 2 telemetry ETL — the only pipeline that
exists. The Build 2 v2 "Monthly Clinic Supply Performance" pipeline is **not** implemented; do not
reference it.

**The CSV is a backup, not pipeline input.** The pipeline reads `telemetry_events` from the database via
its own watermark/window. Do not wire it to consume the export file.

### 4.5 Failure handling

Wrap steps 4.4 in `try` / `except Exception` / `finally`:

- `except` → `mark_failed(session, run, str(exc))`, log at ERROR with the traceback, exit non-zero.
- Success → `mark_completed(session, run)`, log at INFO.
- The `finally` must guarantee no row is left in `processing` — including on `KeyboardInterrupt` /
  `SystemExit`, which do **not** inherit from `Exception`. Catch `BaseException` for the safety net or
  add explicit handlers. A row stranded in `processing` fails the rubric outright.
- Use a **fresh session** for the failure write — if the exception was a DB error, the working session may
  be poisoned and the `mark_failed` write will itself fail, re-creating the zombie you are preventing.

### 4.6 Logging

`logging.basicConfig` at INFO. Every line carries a timestamp, the job name, and the resulting status.
INFO for start / finish / skipped-as-duplicate / lock-abort; ERROR for exceptions; WARNING for stale-lock
reclaim. Format: `%(asctime)s %(levelname)s [nightly_export] %(message)s`, with `asctime` in UTC.

---

## 5. Phase 4 — trigger (OS crontab) and README

No `APScheduler`, no `@repeat_every`, no lifespan hook, no FastAPI `BackgroundTasks`. The trigger is OS
crontab; the script is its own process.

Add a **"Background Processing"** section to the root `README.md` covering:

- The cron expression — `0 2 * * *` (02:00 UTC), matching the "nightly cron `0 2 * * *`" already
  documented in `data/pipelines/pipeline.py`'s docstring and `docs/data_pipelines/pipeline-design.md`.
  Keep them consistent.
- The crontab line, with the `cd` and the log redirect:

  ```
  0 2 * * * cd /path/to/chitrasharath_healthcore_ft_ai_1 && /usr/local/bin/uv run python scripts/nightly_export.py >> /tmp/nightly_export.log 2>&1
  ```

- **The cwd trap — call this out prominently.** `Settings` uses
  `SettingsConfigDict(env_file=".env")` (`services/api/app/core/config.py:5`), which resolves **relative to
  the current working directory**. Cron runs from `$HOME`, so without the `cd` the script loads no `.env`,
  gets `database_url=""`, and dies on a confusing `None` engine instead of a missing-config error. The
  `cd` is mandatory, not cosmetic.
- Cron's `PATH` is minimal — `uv` must be an absolute path (`which uv` to find it).
- How to run manually and how to backfill a specific day via `TARGET_DATE`.

---

## 6. Phase 5 — tests

Both paths are already collected by the root `pyproject.toml`
(`testpaths = ["services/api/tests", "tests"]`, `pythonpath = ["services/api", "."]`). Unlike the Build 2
pipeline tests, **no pytest config change is needed** — do not modify `testpaths` or `pythonpath`.

**`services/api/tests/test_job_runner.py`** (flat `test_*.py`, matching the thirteen files already there),
against an in-memory SQLite session — no Supabase, no network:

- the full `pending → processing → completed` transition sets each timestamp;
- `pending → processing → failed` records `error_message` and never leaves `processing`;
- `has_completed_for_date` is true for a matching date and **false for a different date with the same
  `job_name`** — this is the assertion that proves the rubric's per-date idempotency;
- `has_processing_lock` sees an active row and ignores a `completed` one;
- `reclaim_stale_locks` flips a row past the threshold to `failed` and leaves a fresh one untouched.

**`tests/jobs/test_nightly_export.py`** (mirrors the existing `tests/pipelines/test_pipeline.py`), with
`subprocess.run` mocked — the pipeline must never actually execute in tests:

- a `completed` row for `target_date` → no CSV written, `subprocess.run` not called;
- an active `processing` row → exits `0`, creates no row, `subprocess.run` not called;
- an existing CSV → export skipped but the pipeline still triggers;
- `subprocess.run` raising `CalledProcessError` → the row ends `failed` with the stderr tail, and **no row
  remains in `processing`**;
- `TARGET_DATE` set → the CSV filename and the `--start`/`--end` argv both reflect that date, not
  yesterday. This is the test that proves §1.3 was actually fixed.

Add `tests/jobs/__init__.py` if `tests/pipelines/` has one; match whatever that directory does.

---

## 7. Manual testing walkthrough (run these by hand; capture output for the PR)

1. **Happy path** — `TARGET_DATE=<a day with events> python scripts/nightly_export.py`. Expect: CSV in
   `data/raw/`, a `job_runs` row `completed`, a new `pipeline_runs` row from the subprocess.
2. **Idempotency** — run the exact same command again. Expect: "skipped as duplicate" at INFO, exit `0`,
   no second CSV, no new `pipeline_runs` row. Confirms the rubric's "twice = once".
3. **Lock** — launch two instances simultaneously (`python scripts/nightly_export.py &` twice, or add a
   temporary sleep). Expect: one runs, the other logs the abort and exits `0`. Exactly one `processing`
   row existed at any moment.
4. **Failure** — force an error (e.g. point the subprocess at a bad module, or temporarily raise inside
   the export). Expect: row ends `failed` with `error_message` populated, **nothing left in
   `processing`**, non-zero exit.
5. **Stale reclaim** — hand-insert a `processing` row with `started_at` 12h ago, then run. Expect: the
   WARNING reclaim line, the stale row flipped to `failed`, and the new run proceeding normally.

For the PR body, capture: the cron expression and the crontab-vs-scheduler justification, a successful log
sample, a failed **or** blocked log sample, and the first few rows of the generated CSV.

---

## 8. Anti-patterns (reject these — each one fails a specific eval criterion)

- A `lock` table, an `is_locked` column, a `.lock` file, or `flock` — the `processing` status **is** the
  lock.
- Merging `job_runs` into `pipeline_runs`, or adding a foreign key between them.
- Checking idempotency on `job_name` alone, without `target_date`.
- `APScheduler`, `@repeat_every`, a lifespan hook, or FastAPI `BackgroundTasks`.
- Importing `app.main`, a router, or `fastapi` from `job_runner` or the script.
- Wiring the pipeline to read the exported CSV.
- A bare `except: pass` anywhere in the failure path, or a `mark_failed` on a poisoned session.
- Changing `resolve_window`, the subflows, or the tasks in `data/pipelines/` — the argparse block in
  `__main__` is the only sanctioned edit there.
- Adding Alembic, or a no-op `--no-prefect` flag.
- Committing the generated CSV.

---

## 9. Definition of done

- [ ] `job_runs` exists with all eight fields and the `(job_name, target_date)` index; `pipeline_runs` is
      untouched.
- [ ] `app/domains/jobs/job_runner.py` exposes create/update/query plus `has_processing_lock`,
      `has_completed_for_date`, `reclaim_stale_locks` — and imports no FastAPI.
- [ ] `python scripts/nightly_export.py` runs standalone and honours `TARGET_DATE`.
- [ ] `pipeline.py` accepts `--start`/`--end`; the no-arg invocation is unchanged.
- [ ] The five manual scenarios in §7 all behave as described; no row ever strands in `processing`.
- [ ] CSV lands in `data/raw/telemetry_YYYY-MM-DD.csv` as a full dump; `data/raw/*.csv` is gitignored.
- [ ] `uv run pytest` passes, including both new test files.
- [ ] README documents the cron expression, the crontab line, and the `cd`/`.env` trap.
- [ ] PR opened against `main` with the `cronjob` label, the cron justification, log samples, a CSV
      excerpt, and the §1.2 / §1.5 / §1.7 notes (no-op flag, domain placement, stale-lock reclaim).
