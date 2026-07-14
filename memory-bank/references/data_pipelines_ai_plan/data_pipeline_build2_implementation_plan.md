---
name: Data Pipeline Build 2 (Part 3)
overview: "Refactor Build 1 into ≥3 Prefect subflows; promote analysis helpers; add DB-free unit tests; fix pytest collection; open PR to main. Final phase."
todos:
  - id: b2-prereq
    content: Confirm Build 1 signed off on feature/data_pipeline (pipeline.py, reporting tables, endpoints)
    status: pending
  - id: b2-subflows
    content: Refactor telemetry_etl_flow into ≥3 typed subflows wrapping existing tasks; return_state=True on snapshot subflow
    status: pending
  - id: b2-promote-helpers
    content: Promote analysis.py helpers to public names (or re-export); wire coerce for malformed timestamps per Build 1
    status: pending
  - id: b2-tests
    content: Add tests/pipelines/test_pipeline.py ≥3 transform tests + ≥1 defensive test (in-memory only)
    status: pending
  - id: b2-pytest-config
    content: Fix root pytest collection (prefer Option A pyproject); verify services/api/tests still pass
    status: pending
  - id: b2-manual
    content: Run Build 2 specs §6 walkthrough (pytest, DB-free, regressions, CLI, partial isolation)
    status: pending
  - id: b2-commit-pr
    content: Commit feat: refactor pipeline into subflows and add unit tests; open PR against main
    status: pending
isProject: false
---

# Data Pipeline — Part 3 (Build 2) Implementation Plan

**Plan file:** [`data_pipeline_build2_implementation_plan.md`](data_pipeline_build2_implementation_plan.md)

**Requirements sources:**

- [`data_pipeline_build2_specs.md`](data_pipeline_build2_specs.md)
- [`data_pipeline_build2_eval_criteria.md`](data_pipeline_build2_eval_criteria.md)
- Design artifact: [`docs/data_pipelines/pipeline-design.md`](../../../docs/data_pipelines/pipeline-design.md)
- Prior plans: [`data_pipeline_design_implementation_plan.md`](data_pipeline_design_implementation_plan.md), [`data_pipeline_build1_implementation_plan.md`](data_pipeline_build1_implementation_plan.md)

**Branch:** `feature/data_pipeline` (continue — do not rewrite Build 1)

**Status:** Planned — implement only after Build 1 pause is cleared. This phase ends with commit **and open PR → `main`**.

**Rule:** Build on Build 1. Refactor structure + tests only — no redesign of grains, tables, PHI, or endpoints.

---

## Executive summary

Build 2 productionizes the Build 1 ETL:

1. Split `telemetry_etl_flow` into **≥3 typed subflows** that wrap existing tasks (extract / transform / load + snapshot)  
2. Promote pure `analysis.py` helpers to a stable import surface  
3. Add **DB-free** unit tests under `tests/pipelines/test_pipeline.py`  
4. Fix root pytest collection so `python -m pytest tests/pipelines/test_pipeline.py` works without breaking `services/api/tests`  
5. Re-verify CLI; open PR to `main`

---

## Prerequisites

- [ ] Build 1 delivered and signed off on `feature/data_pipeline`
- [ ] `data/pipelines/pipeline.py` has `telemetry_etl_flow`, ≥3 tasks, snapshot with **`return_state=True`**, `pipeline_runs` + `reporting_*`
- [ ] Prefect already in `services/api` deps (dual lockfiles from Build 1)
- [ ] `docs/data_pipelines/pipeline-design.md` exists (canonical design; run command documented there)

---

## Locked decisions (carry forward)

| Topic | Decision |
|---|---|
| Design / run-command path | **`docs/data_pipelines/pipeline-design.md` only** (eval text may say `PIPELINE_DESIGN.md` — do not create it; keep docs path + inline CLI comment) |
| Subflows | Wrap **existing** Build 1 `@task`s; do not move ETL logic out of tasks into subflow bodies |
| Snapshot | Subflow `export_snapshot_subflow` must be called with **`return_state=True`**; failure → continue + `status=partial` (hard require) |
| Helper promotion | Prefer rename to public names (`prepare_timestamps`, `expand_tags`, `ensure_columns`, `records`) updating call sites **or** thin `__all__` re-export — no compute change |
| Malformed timestamps | Assert **NaT coercion** (`errors="coerce"`) per Build 1 locked choice |
| Pytest fix | Prefer **Option A** (`pyproject.toml` `testpaths` + `pythonpath`); fall back to Option B conftest only if A regresses existing suite |
| Naming | Domain vocabulary from design: `extract_telemetry_*`, `transform_kpi_*`, `load_reporting_*`, test names as in specs table |
| PR | After commit, **open PR against `main`** (this phase owns the PR) |

---

## Eval criteria crosswalk (Build 2)

| Eval criterion | Implementation |
|---|---|
| Main flow invokes ≥3 subflows | `extract_telemetry_subflow`, `transform_kpi_subflow`, `load_reporting_subflow` (+ snapshot) |
| Typed I/O; independently runnable | Explicit params/returns; no module globals driving ETL |
| `tests/pipelines/test_pipeline.py` ≥3 transform tests | Specs table tests for expand/prepare/ensure/records |
| ≥1 defensive invalid-input test | `test_prepare_timestamps_handles_malformed` |
| `pytest tests/pipelines/test_pipeline.py` passes | Option A (or B) collection fix |
| `python data/pipelines/pipeline.py` runs | Keep CLI + fail-fast; now via subflows |
| Run command documented | **`docs/data_pipelines/pipeline-design.md`** (+ inline comment) |
| Domain vocabulary from design | Same names as Design/Build 1 |

---

## Implementation steps

### Step 0 — Prerequisites check

Confirm Build 1 artifacts on branch. Diff should not rewrite `reporting_models`, upsert semantics, or endpoint contracts unless a tiny glue fix is required for imports.

### Step 1 — Refactor into subflows (`data/pipelines/pipeline.py`)

Add ≥3 `@flow` wrappers around existing tasks:

| Subflow | Wraps task | Returns |
|---|---|---|
| `extract_telemetry_subflow` | `extract_telemetry_events` | `pd.DataFrame` |
| `transform_kpi_subflow` | `transform_kpi_aggregates` | `dict[str, list[dict]]` |
| `load_reporting_subflow` | `load_reporting_tables` | `int` (rows loaded) |
| `export_snapshot_subflow` | `export_snapshot_optional` | `str \| None` |

Main `telemetry_etl_flow` becomes a **coordinator only**:

- `start_run` / `resolve_window` / `finish_run` (run-log helpers — not inline KPI/upsert logic)
- Call subflows in order; pass data **only** via return values / parameters
- **`state = export_snapshot_subflow(..., return_state=True)`** — on failed state: log, continue, `finish_run(..., partial=True)`
- Preserve PHI gate, watermark, and transactional load behavior from Build 1 (still inside tasks / helpers they already use)

Keep `backfill_flow` as thin wrapper calling `telemetry_etl_flow` (or the same subflow sequence with explicit window).

**Do not** leave critical ETL steps as inline code in the main flow body.

### Step 2 — Promote analysis helpers

In `services/api/app/domains/telemetry/analysis.py`:

1. Promote `_prepare_timestamps` → `prepare_timestamps`, etc. (or re-export public aliases)
2. Ensure `prepare_timestamps` uses `pd.to_datetime(..., utc=True, errors="coerce")` so malformed → NaT (Build 1 lock; satisfies defensive test)
3. Update internal call sites in the same module
4. Do **not** reimplement KPI aggregations

### Step 3 — Unit tests (`tests/pipelines/test_pipeline.py`)

Create `tests/__init__.py` / `tests/pipelines/__init__.py` if needed.

**≥3 transform + ≥1 defensive** (arrange / act / assert):

| Test | Assert |
|---|---|
| `test_expand_tags_flattens_jurisdiction_and_clinic` | `clinic_id`, `jurisdiction` columns; `tags` dropped |
| `test_prepare_timestamps_derives_utc_date` | `date` is expected `datetime.date`; UTC tz-aware timestamps |
| `test_ensure_columns_backfills_missing_keys` | Missing col added as `pd.NA` |
| `test_records_serializes_date_to_string` | `list[dict]` with `date` as `str` |
| `test_prepare_timestamps_handles_malformed` | `None` / `"not-a-date"` → NaT path; **does not raise unexpectedly** |

In-memory Pandas only — **no** `Session`, DB, or network.

Optional: if Build 1 extracted a pure grain helper under `data/process/`, add one aggregation test for it.

### Step 4 — Fix pytest collection (repo trap)

Prefer **Option A** in root `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["services/api/tests", "tests"]
pythonpath = ["services/api", "."]
```

If that breaks `services/api/tests`, use **Option B** (`tests/pipelines/conftest.py` path inserts) and document why.

Verify:

```bash
uv run python -m pytest tests/pipelines/test_pipeline.py -v
env -u DATABASE_URL uv run python -m pytest tests/pipelines/test_pipeline.py -q
uv run python -m pytest services/api/tests -q
```

### Step 5 — Script re-verify + docs

- Keep `if __name__ == "__main__":` fail-fast + `telemetry_etl_flow()`
- Confirm run command still accurate in **`docs/data_pipelines/pipeline-design.md`**
- Update design “Build roadmap / handoff” if subflow names need to be listed for consistency

### Step 6 — Manual testing walkthrough (specs §6)

| Step | Command / action | Expect |
|---|---|---|
| 1 | `pytest tests/pipelines/test_pipeline.py -v` | All new tests pass |
| 2 | Same with `env -u DATABASE_URL` | Still pass (DB-free) |
| 3 | `pytest services/api/tests -q` | No regressions |
| 4 | `uv run python data/pipelines/pipeline.py` (`DATABASE_URL` set) | Exit 0; new `pipeline_runs` row |
| 5 | Temporarily raise in `export_snapshot_subflow`; re-run; **revert** | Flow completes; reporting loaded; `status=partial` |
| 6 | (Optional) Prefect UI shows nested subflows | Nice-to-have |

Capture pytest output and Step 5 partial evidence for the PR body.

### Step 7 — Commit and open PR

```text
feat: refactor pipeline into subflows and add unit tests
```

Open PR **against `main`** covering Design + Build 1 + Build 2 commits on `feature/data_pipeline`.

Suggested PR summary bullets:

- Design: `docs/data_pipelines/pipeline-design.md`
- Build 1: Prefect ETL, `reporting_*`, endpoints, PHI, idempotent load
- Build 2: subflows + unit tests + pytest path fix

Suggested test plan checklist mirrors §6 above + Build 1 §8 highlights if not already recorded.

---

## Out of scope (Build 2)

- Redesigning watermark / grains / PHI / endpoint contracts  
- Prefetch Prefect Cloud / Blocks registration  
- Roadmap items (run-lock, per-KPI isolation tasks, checkpoint resume)  
- Frontend changes  

---

## Definition of done

- [ ] All Build 2 eval checkboxes satisfied (run command / vocabulary via **`docs/data_pipelines/pipeline-design.md`**)
- [ ] Specs §7 checklist complete  
- [ ] Existing `services/api/tests` still green  
- [ ] Commit + **PR opened to `main`**  
- [ ] Manual §6 evidence captured in PR  

---

## Residual risks

| Risk | Mitigation |
|---|---|
| `pythonpath = "."` breaks API tests | Prefer A; roll back to Option B conftest if needed |
| Promoting helpers causes import cycles | Keep promotions local to `analysis.py`; tests import `app.domains.telemetry.analysis` |
| `return_state=True` on subflow vs task | Specs show it on **subflow** call; keep task optional semantics; ensure Prefect 3 API matches docs — verify during Step 5 |
| Eval path `PIPELINE_DESIGN.md` | Stakeholder docs-only path; PR notes the canonical file |
