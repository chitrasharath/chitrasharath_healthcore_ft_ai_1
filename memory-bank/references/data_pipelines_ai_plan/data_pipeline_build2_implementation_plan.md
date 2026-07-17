---
name: Data Pipeline Build 2 (Part 3)
overview: "Subflows + unit tests + CLI cron docs + Reporting dashboard (/reporting) with monthly→daily KPI tabs and Pipeline health (latest run + trigger). One commit; PR to main."
todos:
  - id: b2-prereq
    content: Confirm Build 1 signed off on feature/data_pipeline; design §12–§12.1 current
    status: pending
  - id: b2-subflows
    content: Refactor telemetry_etl_flow into ≥3 typed subflows wrapping existing tasks; return_state=True on snapshot
    status: pending
  - id: b2-promote-helpers
    content: Promote analysis.py helpers; keep coerce; add DB-free pipeline unit tests
    status: pending
  - id: b2-pytest-config
    content: Fix root pytest collection (Option A preferred); verify services/api/tests still pass
    status: pending
  - id: b2-reporting-ui
    content: Build /reporting dashboard module — 4 KPI tabs + health; monthly UI rollup; trigger button
    status: pending
  - id: b2-manual
    content: Run Build 2 specs §7 walkthrough (tests, CLI, UI monthly/daily, trigger)
    status: pending
  - id: b2-commit-pr
    content: One commit feat: refactor pipeline into subflows, add reporting UI and unit tests; open PR to main
    status: pending
isProject: false
---

# Data Pipeline — Part 3 (Build 2) Implementation Plan

**Plan file:** [`data_pipeline_build2_implementation_plan.md`](data_pipeline_build2_implementation_plan.md)

**Requirements sources:**

- [`data_pipeline_build2_specs.md`](data_pipeline_build2_specs.md) (updated for Reporting UI)
- [`data_pipeline_build2_eval_criteria.md`](data_pipeline_build2_eval_criteria.md) (**unchanged** — still subflows/tests/CLI)
- Design artifact: [`docs/data_pipelines/pipeline-design.md`](../../../docs/data_pipelines/pipeline-design.md) §§12–12.1, §13 Build 2

**Branch:** `feature/data_pipeline` (continue — do not rewrite Build 1 ETL)

**Status:** Implemented on `feature/data_pipeline` — pending one commit + PR → `main`.

**Rule:** Build on Build 1. Subflows wrap existing tasks; dashboard reads materialized report only.

---

## Executive summary

Build 2 adds three finish-line concerns:

1. **Subflows** — `telemetry_etl_flow` coordinates ≥3 typed `@flow` stages wrapping Build 1 tasks  
2. **Tests** — DB-free Pandas helper tests + pytest path fix; re-verify CLI  
3. **Reporting UI** — `/reporting` with four KPI tabs (monthly last-12 → daily for selected month) + Pipeline health (latest run + **Run pipeline** trigger)

Official cron/ops run path remains:

```bash
uv run python data/pipelines/pipeline.py
```

---

## Prerequisites

- [ ] Build 1 delivered on `feature/data_pipeline`
- [ ] Design §12 / §12.1 matches stakeholder locks (CLI, monthly UI rollup, tabs, health + trigger)
- [ ] Prefect in dual lockfiles; landing hybrid import pattern known

---

## Locked decisions

| Topic | Decision |
|---|---|
| CLI | One command: `uv run python data/pipelines/pipeline.py` — no alias; cron `0 2 * * *` |
| Trigger API | Keep Build 1 endpoint; **wire Run pipeline button** on health tab; cron must not depend on it |
| Module | `uis/backoffice/reporting/` → landing `@backoffice/reporting` |
| Route / nav | `/reporting`; hub card **Reporting** |
| Data | `GET /telemetry/report` only |
| Grain UX | Default **last 12 months monthly** (UI rollup); select month → **daily for that month only** |
| Rollup | Client-side; **never average rates** — recompute from sums (design §12.1) |
| Tabs | Consumption · Waste · Stock failures · Auth failure · **Pipeline health** |
| Health | **Latest run only** + trigger button; no history list in Build 2 |
| Auth | Protected + `healthcoreFetch` |
| Eval criteria | **Do not** edit eval file; SPECS/plan/design carry dashboard |
| Commit | **One** Build 2 commit (message below) then PR |

---

## Eval criteria crosswalk (unchanged file)

| Eval criterion | Implementation |
|---|---|
| ≥3 subflows | extract / transform / load (+ snapshot) |
| Typed independent subflows | Explicit I/O; wrap tasks only |
| ≥3 transform unit tests | Promoted `analysis.py` helpers |
| ≥1 defensive test | Malformed timestamps → NaT |
| pytest path works | Option A (or B) |
| CLI runs | `uv run python data/pipelines/pipeline.py` |
| Run command documented | Design §12 |
| Domain vocabulary | Design names |

Dashboard is **additive SPECS** beyond eval.

---

## Implementation steps

### Step 0 — Prerequisites

Confirm branch artifacts; re-read design §12.1.

### Step 1 — Subflows (`data/pipelines/pipeline.py`)

Add `@flow` wrappers around existing tasks; main flow = coordinator only; snapshot subflow `return_state=True` → `partial` on failure. Preserve PHI / watermark / upsert behavior inside tasks.

### Step 2 — Promote helpers + pipeline unit tests

Promote `prepare_timestamps` / `expand_tags` / `ensure_columns` / `records` (or re-export). Add `tests/pipelines/test_pipeline.py` (≥3 + defensive). Prefer pure helpers for any monthly-rollup unit tests if extracted to `lib/`.

### Step 3 — Pytest collection

Option A in root `pyproject.toml`; verify `services/api/tests` still green.

### Step 4 — CLI re-verify + design §12

Keep fail-fast CLI; ensure design documents the single cron command (already updated).

### Step 5 — Reporting feature module

1. Create `uis/backoffice/reporting/` (components ≤80 lines, hooks, `lib/monthly-rollup.ts` (or similar), API helpers using `healthcoreFetch`).
2. Landing route `app/(protected)/reporting/page.tsx` (+ layout with ToolToolbar).
3. Aliases in `next.config.ts` / `tsconfig.json`; Tailwind `@source` if required.
4. Hub card in `nav-apps.ts`: **Reporting** → `/reporting`.
5. Tabs via search params; fetch report with window ≥ first day of (current month − 11) through now.
6. Monthly view → month select → daily for that month.
7. Health tab: latest run panel + **Run pipeline** → `POST /api/v1/telemetry/pipelines/runs/trigger` → refresh latest.
8. `npm run verify` (or landing lint + webpack build).

### Step 6 — Manual walkthrough

Follow Build 2 specs §7 (tests, CLI, UI monthly/daily parity spot-check, trigger).

### Step 7 — Commit + PR

```text
feat: refactor pipeline into subflows, add reporting UI and unit tests
```

PR against `main` covering Design + Build 1 + Build 2.

---

## Out of scope

- Monthly `reporting_*` tables / server `?grain=month`  
- `/raw-report` in UI  
- Pipeline run history list API  
- Prefetch Cloud / Blocks / roadmap resilience  
- Eval criteria file edits  

---

## Definition of done

- [ ] Specs §8 checklist complete (subflows, tests, CLI, Reporting UI, trigger button)  
- [ ] Eval criteria still satisfiable  
- [ ] Design §12 / §12.1 accurate  
- [ ] One commit + PR to `main`  
- [ ] Manual §7 evidence in PR  

---

## Residual risks

| Risk | Mitigation |
|---|---|
| Rate rollup bugs | Shared pure rollup helper + spot-check vs sum of dailies |
| Large `/report` payload for 12 months | Single fetch; client filter; enlarge window only as needed |
| Trigger overlaps nightly | Acceptable (run-lock still roadmap); show latest status after submit |
| Pytest `pythonpath` regressions | Option A then fall back to Option B |
