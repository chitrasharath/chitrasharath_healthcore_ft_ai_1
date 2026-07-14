# Data Pipeline — Part 3 (Build 2: Subflows, Tests & Reporting UI) — Build Spec

> **Instructions for a coding agent.** Bring the Build 1 pipeline to production level: refactor the flow
> into subflows, add isolated unit tests for the transforms, keep it runnable as a CLI script, and ship
> the authenticated Reporting dashboard. Everything you need is in this spec, `docs/data_pipelines/pipeline-design.md`
> §12–§12.1, and the HealthCore monorepo. **Build on Build 1 — do not rewrite the ETL.**
>
> **Deliverables:**
> 1. Refactored `data/pipelines/pipeline.py` (main flow → ≥3 subflows)
> 2. `tests/pipelines/test_pipeline.py` (≥3 transform tests + ≥1 defensive test), both passing
> 3. Backoffice **Reporting** UI at `/reporting` (four KPI tabs + Pipeline health) reading materialized `/telemetry/report`
> 4. CLI run command kept accurate in `docs/data_pipelines/pipeline-design.md`
>
> **One commit** then open the PR against **`main`**. Eval criteria file is unchanged (subflows/tests/CLI);
> dashboard is an additive SPECS requirement.

---

## Branch & workflow

- Continue on **`feature/data_pipeline`** (created off **`main`** in Part 1) — all Build 2 work lands here.
- Every code reference in this spec reflects the state of **`main`** (plus the Build 1 changes already on
  this branch).
- Commit with `feat: refactor pipeline into subflows, add reporting UI and unit tests`, then **open the pull request
  against `main`**.

---

## 1. Ground truth (read before writing)

- **Starting point** = Build 1's `data/pipelines/` layout: `pipeline.py` orchestrator; tasks in
  `extract/tasks.py`, `transform/tasks.py`, `load/tasks.py`; upserts/readers in `load/repository.py`.
- **Transforms** live in `services/api/app/domains/telemetry/analysis.py`, reused as-is. The pure,
  DB-free DataFrame helpers are `_prepare_timestamps`, `_expand_tags`, `_ensure_columns`, `_records`
  (each takes/returns a `pd.DataFrame` or `list[dict]`). These are the unit-test targets.
- **Report API:** `GET /api/v1/telemetry/report` returns daily grains from `reporting_*` (materialized).
  Dashboard uses this only — not `/raw-report`.
- **Repo pytest config** (`pyproject.toml`): `testpaths=["services/api/tests"]`,
  `pythonpath=["services/api"]`. The assignment runs `python -m pytest tests/pipelines/test_pipeline.py`
  from repo root — **this will not collect or import correctly out of the box; §4 fixes it.**
- **Backoffice pattern:** sibling feature module + landing route aliases (see inventory / incident-manager).

## 2. Phase 1 — refactor into subflows

Split the main flow into **≥3 subflows** (`@flow`), one per stage, each with **explicit typed
inputs/outputs** — no module-level globals, no inline ETL logic left in the main flow body. The subflows
wrap the **existing Build 1 tasks** (do not move logic out of the tasks):

```python
@flow(name="extract-telemetry-events")
def extract_telemetry_subflow(...) -> pd.DataFrame:
    return extract_telemetry_events(...)

@flow(name="transform-kpi-aggregates")
def transform_kpi_subflow(...) -> dict[str, list[dict]]:
    return transform_kpi_aggregates(...)

@flow(name="load-reporting-tables")
def load_reporting_subflow(metrics: dict, run_id: str) -> int:
    return load_reporting_tables(metrics, run_id)

@flow(name="export-snapshot")           # optional / non-critical
def export_snapshot_subflow(metrics: dict) -> str | None:
    return export_snapshot_optional(metrics)
```

Main flow becomes a pure coordinator that calls subflows; optional subflow uses
`return_state=True` (failure → continue + `status=partial`).

Data passes **only through return values / parameters**.

## 3. Phase 2 — unit tests (`tests/pipelines/test_pipeline.py`)

Tests run **without a DB or network** — in-memory Pandas fixtures only. Target the **pure helpers**
in `analysis.py` (honors "reuse as-is": no logic reimplemented).

**Preparatory step (allowed, no behavior change):** promote the four helpers to a stable importable
surface — either drop the leading underscore (`prepare_timestamps`, `expand_tags`, `ensure_columns`,
`records`, updating call sites) **or** add a thin public re-export / `__all__`. Do not change what they
compute (Build 1 already uses `errors="coerce"` on timestamps).

Write **≥3 transform tests + ≥1 defensive test**. Each with an arrange/act/assert:

| test | arrange (in-memory) | assert |
| --- | --- | --- |
| `test_expand_tags_flattens_jurisdiction_and_clinic` | `DataFrame([{ "id":"1","tags":{"clinic_id":3,"jurisdiction":"us"} }])` | result has `clinic_id==3`, `jurisdiction=="us"` columns; `tags` dropped |
| `test_prepare_timestamps_derives_utc_date` | rows with ISO string `timestamp` | `date` column equals the expected `datetime.date`; tz-aware UTC |
| `test_ensure_columns_backfills_missing_keys` | frame lacking `consumption_type` | column added, filled `pd.NA` (matches the real dropna path) |
| `test_records_serializes_date_to_string` | grouped frame with a `date` column | returns `list[dict]`; each `date` is a `str` |
| `test_prepare_timestamps_handles_malformed` **(defensive)** | a row with `timestamp=None` / `"not-a-date"` | asserts NaT coercion (does not raise unexpectedly) |

Optional: unit-test the **monthly rollup helpers** (pure TS or shared util) with fixtures — recommended but not a substitute for the Pandas helper tests above.

## 4. Phase 3 — make the tests actually run (repo trap — do not skip)

`python -m pytest tests/pipelines/test_pipeline.py` must pass. Pick **one** fix:

**Option A — pyproject:**
```toml
[tool.pytest.ini_options]
testpaths = ["services/api/tests", "tests"]
pythonpath = ["services/api", "."]
```

**Option B — conftest:** add `tests/pipelines/conftest.py` with `sys.path` inserts for repo root + `services/api`.

**Verify** existing `services/api/tests` still passes.

## 5. Phase 4 — script execution (re-verify)

- Keep `if __name__ == "__main__": telemetry_etl_flow()` (Build 1 fail-fast on missing DB URL).
- Canonical command (document in design §12):

```bash
uv run python data/pipelines/pipeline.py
```

This is the **only** ops/cron entrypoint (no shorter alias). Intended cron: `0 2 * * *`.

## 6. Phase 5 — Reporting dashboard (additive)

Implement per `docs/data_pipelines/pipeline-design.md` §12.1.

**Suggested layout:**

```
uis/backoffice/reporting/          # feature module
  components/ ...                  # ≤80 lines / file
  lib/                             # monthly rollup helpers, API client wrappers
  hooks/
uis/backoffice/landing/
  app/(protected)/reporting/...    # route(s)
  next.config.ts / tsconfig        # @backoffice/reporting alias
  lib/nav-apps.ts                  # hub card "Reporting" → /reporting
```

**Requirements:**

| Item | Spec |
| --- | --- |
| Route | `/reporting` |
| Auth | Protected; JWT via `healthcoreFetch` |
| API | `GET /api/v1/telemetry/report` with a date window covering at least the last 12 months of daily data |
| Tabs | Consumption volume · Waste rate · Stock failures · Auth failure rate · Pipeline health (`?tab=…`) |
| Default grain | **Monthly** series for **last 12 calendar months** (UI rollup — do not average rates) |
| Drill-down | Selecting a month → **daily** table/chart for **that month only** |
| KPI tab body | Definition blurb + headline + table + simple custom chart (no chart library) |
| Health tab | Latest run via `GET …/pipelines/runs/latest`; **Run pipeline** button → `POST …/pipelines/runs/trigger`; then refresh latest. No history list in Build 2 |
| Styling | Tailwind; ToolToolbar; sky/teal brand consistency; no third-party UI kits |

**Monthly rollup math (must match design):**

- Consumption: sum `count` by `YYYY-MM` · `clinic_id` · `jurisdiction`
- Waste: derive daily waste count ≈ `waste_rate * total`, then month rates = Σwaste / Σtotal by jurisdiction
- Stock failures: Σ`count` / Σ`attempts`; `rejection_rate` = count/attempts
- Auth: Σ`failed` / Σ`succeeded`; `failure_rate` = failed/(failed+succeeded)

## 7. Manual testing walkthrough

**Prerequisites:** `uv sync`; `DATABASE_URL` for pipeline/API/UI checks; landing on `:3001` with API on `:8000`.

**Pipeline / tests**

1. `uv run python -m pytest tests/pipelines/test_pipeline.py -v`
2. `env -u DATABASE_URL uv run python -m pytest tests/pipelines/test_pipeline.py -q` (still pass)
3. `uv run python -m pytest services/api/tests -q`
4. `uv run python data/pipelines/pipeline.py` → exit 0; new `pipeline_runs` row
5. Optional-subflow isolation (`return_state=True` / `partial`) as in prior Build 2 steps; revert after

**Reporting UI**

6. Log into backoffice → hub card **Reporting** → `/reporting`
7. Confirm default shows **12 months** monthly view for a KPI tab; select a month → daily for that month only
8. Spot-check rollups (e.g. monthly consumption sum equals sum of that month's daily counts)
9. Pipeline health tab: latest run fields visible; **Run pipeline** submits trigger and latest refreshes
10. Confirm empty/error states when report/latest fail (network toast / message)

## 8. Definition of done

- [ ] Main flow invokes ≥3 subflows (`@flow`); no inline ETL logic in the main flow body.
- [ ] Each subflow has explicit typed inputs/outputs and can run independently (no globals).
- [ ] Optional subflow invoked with `return_state=True`; flow continues (marks run `partial`) on its failure.
- [ ] `tests/pipelines/test_pipeline.py` has ≥3 transform tests + ≥1 defensive/malformed-input test.
- [ ] Tests use in-memory fixtures — no DB/network.
- [ ] `python -m pytest tests/pipelines/test_pipeline.py` passes (config/conftest fixed per §4).
- [ ] Existing `services/api/tests` suite still passes.
- [ ] `uv run python data/pipelines/pipeline.py` runs the full ETL without errors; design §12 documents this cron command.
- [ ] Subflow/task/test names use HealthCore domain vocabulary.
- [ ] Transforms still reused from `analysis.py` (helpers promoted, not reimplemented).
- [ ] `/reporting` dashboard delivered per §6 (4 KPI tabs + health; monthly→daily; materialized report only).
- [ ] Health tab trigger button calls `POST …/pipelines/runs/trigger`.
- [ ] Hub nav card **Reporting** present; `npm run verify` (or landing lint/build) passes.
- [ ] Manual testing walkthrough (§7) run and captured in the PR.
- [ ] Commit message: `feat: refactor pipeline into subflows, add reporting UI and unit tests`. Open a PR.
