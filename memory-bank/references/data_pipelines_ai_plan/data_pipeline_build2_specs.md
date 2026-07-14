# Data Pipeline — Part 3 (Build 2: Subflows & Tests) — Build Spec

> **Instructions for a coding agent.** Bring the Build 1 pipeline to production level: refactor the flow
> into subflows, add isolated unit tests for the transforms, keep it runnable as a script.
> Everything you need is in this spec and the HealthCore monorepo. **Build on Build 1 — do not rewrite it.**
>
> **Deliverables:** refactored `data/pipelines/pipeline.py` (main flow → ≥3 subflows) and
> `tests/pipelines/test_pipeline.py` (≥3 transform tests + ≥1 defensive test), both passing.

---

## Branch & workflow

- Continue on **`feature/data_pipeline`** (created off **`main`** in Part 1) — all Build 2 work lands here.
- Every code reference in this spec reflects the state of **`main`** (plus the Build 1 changes already on
  this branch).
- Commit with `feat: refactor pipeline into subflows and add unit tests`, then **open the pull request
  against `main`**.

---

## 1. Ground truth (read before writing)

- **Starting point** = Build 1's `data/pipelines/pipeline.py`: flow `telemetry_etl_flow`, tasks
  `extract_telemetry_events` / `transform_kpi_aggregates` / `load_reporting_tables` + one optional task,
  writing `pipeline_runs` and the `reporting_*` tables.
- **Transforms** live in `services/api/app/domains/telemetry/analysis.py`, reused as-is. The pure,
  DB-free DataFrame helpers are `_prepare_timestamps`, `_expand_tags`, `_ensure_columns`, `_records`
  (each takes/returns a `pd.DataFrame` or `list[dict]`). These are the unit-test targets.
- **Repo pytest config** (`pyproject.toml`): `testpaths=["services/api/tests"]`,
  `pythonpath=["services/api"]`. The assignment runs `python -m pytest tests/pipelines/test_pipeline.py`
  from repo root — **this will not collect or import correctly out of the box; §4 fixes it.**

## 2. Phase 1 — refactor into subflows

Split the main flow into **≥3 subflows** (`@flow`), one per stage, each with **explicit typed
inputs/outputs** — no module-level globals, no inline ETL logic left in the main flow body. The subflows
wrap the **existing Build 1 tasks** (do not move logic out of the tasks):

```python
@flow(name="extract-telemetry-events")
def extract_telemetry_subflow(session, event_types, start, end) -> pd.DataFrame:
    return extract_telemetry_events(session, event_types, start, end)

@flow(name="transform-kpi-aggregates")
def transform_kpi_subflow(session, start, end) -> dict[str, list[dict]]:
    return transform_kpi_aggregates(session, start, end)

@flow(name="load-reporting-tables")
def load_reporting_subflow(metrics: dict, run_id: str) -> int:
    return load_reporting_tables(metrics, run_id)

@flow(name="export-snapshot")           # optional / non-critical
def export_snapshot_subflow(metrics: dict) -> str | None:
    return export_snapshot_optional(metrics)
```

Main flow becomes a pure coordinator:

```python
@flow
def telemetry_etl_flow(start=None, end=None):
    run_id = start_run()                       # inserts pipeline_runs row, status='running'
    w_from, w_to = resolve_window(start, end)
    df = extract_telemetry_subflow(session, EVENT_TYPES, w_from, w_to)
    metrics = transform_kpi_subflow(session, w_from, w_to)
    loaded = load_reporting_subflow(metrics, run_id)
    state = export_snapshot_subflow(metrics, return_state=True)   # failure must NOT abort
    finish_run(run_id, loaded, partial=state.is_failed())
    return loaded
```

Data passes **only through return values / parameters**. The optional subflow is invoked with
`return_state=True` and its failure is tolerated (log + continue, mark run `partial`).

## 3. Phase 2 — unit tests (`tests/pipelines/test_pipeline.py`)

Tests run **without a DB or network** — in-memory Pandas fixtures only. Because the transforms take a
`Session`, target the **pure helpers** in `analysis.py` (honors "reuse as-is": no logic reimplemented).

**Preparatory step (allowed, no behavior change):** promote the four helpers to a stable importable
surface — either drop the leading underscore (`prepare_timestamps`, `expand_tags`, `ensure_columns`,
`records`, updating call sites) **or** add a thin public re-export / `__all__`. Do not change what they
compute.

Write **≥3 transform tests + ≥1 defensive test**. Each with an arrange/act/assert:

| test | arrange (in-memory) | assert |
| --- | --- | --- |
| `test_expand_tags_flattens_jurisdiction_and_clinic` | `DataFrame([{ "id":"1","tags":{"clinic_id":3,"jurisdiction":"us"} }])` | result has `clinic_id==3`, `jurisdiction=="us"` columns; `tags` dropped |
| `test_prepare_timestamps_derives_utc_date` | rows with ISO string `timestamp` | `date` column equals the expected `datetime.date`; tz-aware UTC |
| `test_ensure_columns_backfills_missing_keys` | frame lacking `consumption_type` | column added, filled `pd.NA` (matches the real dropna path) |
| `test_records_serializes_date_to_string` | grouped frame with a `date` column | returns `list[dict]`; each `date` is a `str` |
| `test_prepare_timestamps_handles_malformed` **(defensive)** | a row with `timestamp=None` / `"not-a-date"` | does **not** raise unexpectedly — asserts NaT coercion (or a deliberate `ValueError`), matching Build 1's chosen behavior |

Example skeleton:

```python
import pandas as pd
from app.domains.telemetry.analysis import expand_tags, prepare_timestamps  # promoted names

def test_expand_tags_flattens_jurisdiction_and_clinic():
    df = pd.DataFrame([{"id": "1", "timestamp": "2025-01-13T00:00:00Z",
                        "event_type": "supply_consumption_created",
                        "tags": {"clinic_id": 3, "jurisdiction": "us"}}])
    out = expand_tags(df)
    assert out.loc[0, "clinic_id"] == 3 and out.loc[0, "jurisdiction"] == "us"
    assert "tags" not in out.columns
```

At least one test **must** exercise invalid/malformed input (the defensive row). If Build 1 extracted any
pure grain helper into `data/process/`, add an aggregation test for it too.

## 4. Phase 3 — make the tests actually run (repo trap — do not skip)

`python -m pytest tests/pipelines/test_pipeline.py` must pass. Pick **one** fix:

**Option A — pyproject:**
```toml
[tool.pytest.ini_options]
testpaths = ["services/api/tests", "tests"]
pythonpath = ["services/api", "."]   # "." so repo-root packages resolve; services/api so `app.*` resolves
```

**Option B — conftest:** add `tests/pipelines/conftest.py`:
```python
import sys, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "services" / "api"))
sys.path.insert(0, str(root))
```

Add `tests/__init__.py` / `tests/pipelines/__init__.py` if collection needs them. **Verify the existing
`services/api/tests` suite still passes** after the config change — do not break current tests.

## 5. Phase 4 — script execution (re-verify)

- Keep `if __name__ == "__main__": telemetry_etl_flow()` (with the Build 1 fail-fast on missing DB URL).
- `python data/pipelines/pipeline.py` runs the full flow (now via subflows) without errors.
- Run command documented in `docs/data_pipelines/pipeline-design.md` or an inline comment.

## 6. Manual testing walkthrough (run these by hand; capture output for the PR)

**Prerequisites:** `uv sync` (Prefect already added in Build 1). The unit tests need **no** DB or network;
the pipeline run in Step 4 needs `DATABASE_URL` set (see Build 1 §8 prerequisites for token/seed if you
also want to re-exercise the endpoints).

**Step 1 — new unit tests pass.**
```bash
uv run python -m pytest tests/pipelines/test_pipeline.py -v
```
Expect all ≥3 transform tests + the defensive test to pass. Capture the output for the PR.

**Step 2 — prove the tests are DB-free.** Run them with **no** database configured — they must still pass,
which demonstrates the transforms are tested in isolation:
```bash
env -u DATABASE_URL uv run python -m pytest tests/pipelines/test_pipeline.py -q
```

**Step 3 — no regressions.** The pre-existing suite still passes after the pytest-config change (§4):
```bash
uv run python -m pytest services/api/tests -q
```

**Step 4 — full pipeline via subflows.** With `DATABASE_URL` set:
```bash
uv run python data/pipelines/pipeline.py
```
Expect exit 0, the main flow driving all subflows in sequence, and one new `pipeline_runs` row.

**Step 5 — optional-subflow isolation (partial-failure tolerance).** Temporarily make the optional
subflow raise (e.g. `raise RuntimeError("boom")` inside `export_snapshot_subflow`), re-run Step 4, and
confirm the **main flow still completes**, the reporting tables are still loaded, and the run is recorded
`status='partial'`. **Revert the edit afterward.**

**Step 6 — subflow visibility (optional).** With a local Prefect server (`prefect server start`), confirm
the three subflows appear as distinct flow runs nested under `telemetry_etl_flow`.

## 7. Definition of done

- [ ] Main flow invokes ≥3 subflows (`@flow`); no inline ETL logic in the main flow body.
- [ ] Each subflow has explicit typed inputs/outputs and can run independently (no globals).
- [ ] Optional subflow invoked with `return_state=True`; flow continues (marks run `partial`) on its failure.
- [ ] `tests/pipelines/test_pipeline.py` has ≥3 transform tests + ≥1 defensive/malformed-input test.
- [ ] Tests use in-memory fixtures — no DB/network.
- [ ] `python -m pytest tests/pipelines/test_pipeline.py` passes (config/conftest fixed per §4).
- [ ] Existing `services/api/tests` suite still passes.
- [ ] `python data/pipelines/pipeline.py` runs the full ETL without errors.
- [ ] Subflow/task/test names use HealthCore domain vocabulary (no `extract_data`/`test_transform`).
- [ ] Transforms still reused from `analysis.py` (helpers promoted, not reimplemented).
- [ ] Manual testing walkthrough (§6) run and captured in the PR (pytest output, DB-free run, no regressions).
- [ ] Commit message: `feat: refactor pipeline into subflows and add unit tests`. Open a PR.
