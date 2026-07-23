---
name: HealthCore CV & Fit Diagnosis
overview: "Validation and diagnosis pass on the shipped revenue forecaster: raise MLForecast selection CV to ≥5 folds, run temporal 5×6mo CV (RF→TimeSeriesSplit, AutoETS→StatsForecast), learning curves, fit classification, report, and chronological-order tests on feature/eval_metrics."
todos:
  - id: p0-branch
    content: Cut feature/eval_metrics from up-to-date feature/sales_forecast; uv sync --group forecast
    status: pending
  - id: p0-baseline
    content: Record shipped n_windows=3 selection CV as the report "before"; note classical_backtest already at 5
    status: pending
  - id: p1-bump-cv
    content: Bump models_mlforecast defaults to n_windows=5, h=6, step_size=6 (back-compatible); re-run train; pin prior winner, note any flip
    status: pending
  - id: p2-diagnostics-cv
    content: Add diagnostics.py — date-first 5×6 folds; RF causal matrix + fold-local Differences + recursive predict; AutoETS via classical_backtest(h=6); align engines; write cv_folds.json
    status: pending
  - id: p3-learning-curve
    content: Expanding-window learning curve (s∈{36,48,60,72}, fixed 2023 val); PNGs + learning_curve.json; ElasticNet side curve if ML winner overfits
    status: pending
  - id: p4-classify
    content: Classify each diagnosed model from curve + CV spread; follow numbers; report-only corrective actions
    status: pending
  - id: p5-wireup
    content: Extend train_revenue_forecast.py + add scripts/run_diagnostics.py; seed 42; commit pickles + eval artifacts
    status: pending
  - id: p6-report
    content: Write cv_fit_diagnosis_report.md per specs §10 (CONTEXT-healthcore.en.md §3 for RMSE)
    status: pending
  - id: p7-test
    content: tests/pipelines/test_temporal_cv_order.py for both engines + alignment + determinism + negative control
    status: pending
  - id: p8-stretch
    content: Optional after must-haves — gap=1 A/B, fold strip plot, SeasonalNaive-in-CV skill
    status: pending
  - id: p9-verify
    content: pytest temporal + full pipelines; deterministic rerun; update progress/decisions when delivering
    status: pending
isProject: false
---

# HealthCore — Temporal CV & Fit Diagnosis Implementation Plan

**Plan file:** [`healthcore_cv_diagnosis_IMPLEMENTATION_PLAN.md`](healthcore_cv_diagnosis_IMPLEMENTATION_PLAN.md)

**Requirements sources:**

- [`healthcore_cv_diagnosis_specs.md`](healthcore_cv_diagnosis_specs.md)
- [`healthcore_cv_diagnosis_eval_criteria.md`](healthcore_cv_diagnosis_eval_criteria.md)

**Branch:** `feature/eval_metrics` (cut from `feature/sales_forecast`; PR base = `feature/sales_forecast`)

**Working directory:** repository root (`chitrasharath_healthcore_ft_ai_1/`)

**Status:** Implemented on `feature/eval_metrics` — awaiting developer commit acknowledgement.

**Out of scope:** Re-implementing forecast models; Docker / Compose; FastAPI / backoffice; PHI / patient-level data; nested CV; NeuralForecast; diagnosing `MLForecast_exog` as primary (exog learning curve deferred).

---

## Executive summary

This is a **validation and diagnosis pass** on the shipped revenue forecaster (`data/forecast/` on `feature/sales_forecast`). It does not rebuild models from scratch.

Deliverables:

1. **MLForecast selection CV** raised from `n_windows=3` → **≥5** (`h=6`, `step_size=6`), signatures back-compatible  
2. **`data/forecast/diagnostics.py`** — per-model temporal CV, learning curves, train/val MAE+RMSE, fit classification helpers  
3. **Artifacts** under `data/eval/revenue_forecast/` (JSON, PNGs, `cv_fit_diagnosis_report.md`) + **committed** regenerated `data/process/models/*.pkl`  
4. **`tests/pipelines/test_temporal_cv_order.py`** — proves both CV engines preserve chronology  

**Diagnosed models (default expectation):** 5-fold MLForecast **winner** (typically `MLForecast_uni` RF) via sklearn `TimeSeriesSplit`, and **AutoETS** via existing `classical_backtest`. If 5-fold selection flips the ML winner, **diagnose that winner** while **pinning** the prior shipped selection in narrative/artifacts and noting the change.

---

## Prerequisites

- [ ] `feature/sales_forecast` checked out and up to date (`git pull`)
- [ ] New branch `feature/eval_metrics` cut from `feature/sales_forecast` (not `main`)
- [ ] `uv sync --group forecast` succeeds at repo root
- [ ] Specs + eval criteria read end-to-end before coding
- [ ] Local `data/raw/healthcore_sales.csv` available (gitignored)

---

## Locked decisions (clarifying Q&A + recommendations)

| Topic | Decision |
|-------|----------|
| Branch | `feature/eval_metrics` off `feature/sales_forecast`; PR base `feature/sales_forecast` |
| Fold config | **5 folds × 6-month** non-overlapping blocks on train window only (2016–2023) |
| Selection CV bump | `cross_validation_select` / `light_param_sweep` (+ interval helper where sensible) defaults → `n_windows=5, h=6, step_size=6`; keep overridable |
| Winner change | **Pin** prior shipped selection for continuity; **note** in report if 5-fold would pick a different learner |
| Diagnostic target | **Diagnose the 5-fold winner** (ML path) + AutoETS — not hard-wired to RF if selection flips |
| RF / ML params | Load winner params from **post-rerun** `metrics.json`; quote **pre-bump** params for the pinned prior winner in the report |
| Engines | ML winner (sklearn-style trees/linear) → causal feature matrix + `TimeSeriesSplit`; AutoETS → reuse `classical_backtest(..., n_windows=5, h=6)` |
| Date alignment | Define five validation windows **by `ds` first**; assert both engines hit the same calendar months |
| RF / ML within-fold predict | **Recursive** month-by-month (feed predictions into lags); never one-shot `predict(X[test_idx])` |
| Target transform | `Differences([12])` (+ scaler no-op for trees) **fit per fold on train only**; invert for scoring |
| Embargo (`gap`) | Required path: **`gap=0`**. Optional stretch: `gap=1` A/B in report |
| Learning curve | Expanding prefixes `s ∈ {36, 48, 60, 72}`; **fixed** val block = last 12 months of train (**2023-01…2023-12**) |
| Entrypoints | **Both:** extend `scripts/train_revenue_forecast.py` **and** add `scripts/run_diagnostics.py` |
| Fit verdict | **Follow the numbers** (curve + CV spread); do not force RF-overfit / AutoETS-well-fit narrative |
| Corrective actions | **Report-only** — do not retune shipped hyperparameters in code beyond the CV default bump |
| Tests | Only required gate: `test_temporal_cv_order.py` (both engines + alignment + determinism + negative control) |
| Artifacts to commit | Report, PNGs, `cv_folds.json`, `learning_curve.json`, updated `metrics.json`, **and regenerated `.pkl`s** |
| Seed | `random_state=42` everywhere |
| §13 extras | **None required.** Stretch after must-haves: purged `gap=1` A/B, fold strip/boxplot, SeasonalNaive-in-CV skill. Skip nested CV, seed sweeps, t-CI, exog learning curve |
| §14 alternatives | If ML winner overfits: add **ElasticNet learning-curve** side check. Mention HistGB / seasonal linear / NeuralForecast only — do not implement |

---

## Repository layout (edit / create)

```
data/forecast/
  models_mlforecast.py        # EDIT: defaults n_windows=5, h=6, step_size=6
  models_statsforecast.py     # REUSE: classical_backtest(h=6)
  diagnostics.py              # NEW
scripts/
  train_revenue_forecast.py   # EDIT: call diagnostics after training
  run_diagnostics.py          # NEW: standalone diagnostics entrypoint
tests/pipelines/
  test_temporal_cv_order.py   # NEW
data/eval/revenue_forecast/
  diagnostics/
    cv_folds.json
    learning_curve_mlforecast_uni.png   # name after diagnosed ML model if winner ≠ uni RF
    learning_curve_autoets.png
    learning_curve_elasticnet.png       # stretch / if overfit side check
    learning_curve.json
    fold_rmse_strip.png                 # stretch
  cv_fit_diagnosis_report.md
data/process/models/*.pkl               # COMMIT regenerated
```

No new `src/`, no second `pyproject.toml`, no new deps expected (`uv sync --group forecast` only).

---

## Eval criteria crosswalk

| # | Criterion | Plan coverage |
|---|-----------|---------------|
| 0 | Correct branch | Phase 0; PR base `feature/sales_forecast` |
| 1 | ≥5 folds confirmed | Phase 1 (selection) + Phase 2 (diagnostic); report notes classical already 5 |
| 1a | Shipped / winner params from metrics.json | Phase 1–2; post-rerun winner params + pre-bump quote |
| 1b | AutoETS reuses `classical_backtest` | Phase 2 |
| 2 | Chronological, no shuffle | Phase 2 + Phase 7 test |
| 3 | Per-model engine | Phase 2 |
| 4 | Date-aligned folds | Phase 2 date-first windows + assert |
| 5 | Recursive ML prediction | Phase 2 gotcha #3 |
| 6 | Fold-local transforms | Phase 2 gotcha #2 |
| 7 | RMSE mean ± std | Phase 2 `cv_folds.json` + report |
| 8 | MAE & RMSE, train & val | Phase 2–3 |
| 9 | Learning curves | Phase 3 |
| 10 | Business-cost metric | Phase 6 — `rag_assignments/CONTEXT-healthcore.en.md` §3 |
| 11 | Fit classification | Phase 4 |
| 12 | Interpretation guardrails | Phase 4 + report § method note |
| 13 | Corrective actions match | Phase 4 report-only |
| 14 | Temporal-order test | Phase 7 |
| 15 | Deterministic | Phase 5 / 9 |

---

## Implementation phases

### Phase 0 — Branch & baseline

1. `git checkout feature/sales_forecast && git pull`
2. `git checkout -b feature/eval_metrics`
3. `uv sync --group forecast`
4. Confirm current MLForecast selection defaults are `n_windows=3` (and classical `classical_backtest` already `n_windows=5`). Record this as the report **before** snapshot (cite `metrics.json` / code defaults). Do **not** re-train yet until Phase 1 defaults land.

### Phase 1 — Raise selection CV to ≥5

1. In `models_mlforecast.py`, change defaults on `cross_validation_select`, `light_param_sweep`, and the interval helper where sensible to `n_windows=5, h=6, step_size=6`. Keep parameters overridable; preserve call signatures.
2. Selection CV stays **MLForecast-native** (not sklearn) so rf/xgb/elasticnet compare fairly with per-fold feature regen.
3. Run `uv run python scripts/train_revenue_forecast.py`.
4. Compare new selection vs pre-bump winner:
   - **Pin** prior shipped selection for “what we continue to treat as the shipped baseline” in the report.
   - If the 5-fold winner differs, **note the flip** and set the **diagnostic ML target** to the **new winner** (and its `best_params` from updated `metrics.json`).
   - If the winner is unchanged, diagnose that model with post-rerun params; still quote pre-bump params for continuity.

### Phase 2 — `diagnostics.py`: temporal 5-fold CV

Train window only (2016–2023). Single source of truth for fold dates:

1. **Define** the five contiguous 6-month validation `ds` blocks as the last 30 usable months of the training window (document exact month ranges in `cv_folds.json` and the report).
2. **ML path (5-fold winner):**
   - Build causal feature matrix via `features.py` (`add_engineered_features` / `FEATURE_COLUMNS`); sort by `ds`; drop rows lacking `lag_12`.
   - Assert no feature column equals same-month target (gotcha #1).
   - `TimeSeriesSplit(n_splits=5, test_size=6, gap=0)` on the ordered matrix; **assert** test `ds` blocks equal the date-defined windows.
   - Per fold: fit `Differences([12])` (+ scaler) on **train rows only**; fit winner learner with params from `metrics.json`; **recursively** forecast the 6-month block; invert transform; score train (in-sample on train rows) and val MAE/RMSE.
   - If winner is ElasticNet (or other sklearn regressor in the set), same matrix/`TimeSeriesSplit`/recursive path; if somehow classical-only, document engine choice (should not happen for MLForecast selection).
3. **AutoETS path:**
   - Call existing `classical_backtest(train_df, n_windows=5, h=6)` (ensure `step_size=6`); narrow to AutoETS if the helper returns multiple models.
   - Collect per-fold val MAE/RMSE; in-sample train error from fitted values for that fold’s train span.
4. **Align** the five validation calendar months across engines; fail loudly if mismatched.
5. Emit `data/eval/revenue_forecast/diagnostics/cv_folds.json` with per model: engine, `n_splits`/`n_windows`, `h`/`test_size`, fold date ranges, per-fold train/val MAE+RMSE, mean ± std, min/max.
6. Honor interpretation rules when later classifying: read **val − train gap** for trees; do not compare tree ~0 train error to AutoETS in-sample residuals as like-for-like; keep `Differences([12])` so trend-extrapolation is not mislabeled as underfitting.

### Phase 3 — Learning curves

1. Fixed validation block: **2023-01…2023-12** (never in any training prefix).
2. Prefixes `s ∈ {36, 48, 60, 72}` ending before 2023-01.
3. For each diagnosed model (ML winner + AutoETS): fit on prefix; train MAE/RMSE in-sample; val MAE/RMSE on the fixed 12-month forecast (ML path: recursive; AutoETS: native horizon).
4. Write `learning_curve_*.png` (matplotlib `Agg`) and `learning_curve.json`.
5. Note small-prefix noise (~36 months) in report — do not over-read.
6. **If** ML winner shows overfitting: add ElasticNet learning-curve side check on the same prefixes/val block; save separate PNG + JSON entries. Otherwise skip.

### Phase 4 — Fit classification & corrective actions

For each diagnosed model, classify **well-fitted / underfitting / overfitting** using **both** learning curve (gap, plateau, convergence) **and** CV fold spread (std, min/max).

- Follow empirics even if they contradict the “likely RF overfit / AutoETS well-fit” expectation.
- Corrective actions **report-only**, matched to verdict (specs §11). Explicitly rule out “collect more data” (fixed 120 months).
- Do **not** change shipped `max_depth` / leaf / feature set in code on this branch.

### Phase 5 — Wire-up & artifacts

1. Add `diagnostics.run_all(...)` (or equivalent) that writes all diagnostic artifacts.
2. Call it at the end of `scripts/train_revenue_forecast.py` after training/metrics.
3. Add `scripts/run_diagnostics.py` that loads cleaned data / needed artifacts and runs the same `run_all` (usable without a full retrain when models already exist).
4. Seed 42; confirm reruns reproduce JSON (and PNGs as closely as matplotlib allows).
5. Commit paths: diagnostics JSON/PNGs, `cv_fit_diagnosis_report.md`, updated `metrics.json`, **regenerated `data/process/models/*.pkl`**.

### Phase 6 — Report (`cv_fit_diagnosis_report.md`)

Structure per specs §10:

1. Summary — verdict, `RMSE = mean ± std`, one-line corrective action per model  
2. CV setup & integrity — ≥5 folds, 5×6 design, chronology evidence, 3→5 selection change + pin/note  
3. Metrics table — train & val MAE/RMSE (mean ± std)  
4. Learning curves — embed PNGs; read gap/plateau  
5. Business-cost metric — **RMSE**, grounded in **`rag_assignments/CONTEXT-healthcore.en.md` §3** (not repo `CONTEXT.md`); also RMSE as % of average monthly revenue; MAE alongside for interpretability  
6. Fit diagnosis — curve **and** CV spread; guardrails #5–#6  
7. Method note — causal features, fold-local transforms, recursive predict, date-aligned folds  
8. Corrective actions — matched to verdicts  
9. Limitations — 120 points, ~84 effective rows, 6-month horizon, small-sample std  

### Phase 7 — Unit test (`test_temporal_cv_order.py`)

Match repo style (`from __future__ import annotations`, typed, docstrings, import `data.forecast.*`). Load via real pipeline (`clean_sales` / `load_raw`, `split_train_test`, `prepare_frame`, diagnostics splitter helpers).

**ML / `TimeSeriesSplit`:** ≥5 folds; `max(train ds) < min(val ds)` every fold; contiguous monthly val blocks; forward-rolling non-overlapping; no shuffle.

**AutoETS / StatsForecast:** ≥5 distinct increasing cutoffs spaced by `step_size`; every val `ds` > cutoff; contiguous months after cutoff.

**Both:** same calendar months across engines; identical boundaries on second run; negative control (shuffled frame still sorted by `ds` before split, or order asserts would fail); never construct `KFold(shuffle=True)`.

No extra numeric smoke tests beyond this required file.

### Phase 8 — Stretch (after must-haves only)

| Item | Action |
|------|--------|
| Purged `gap=1` | Re-run ML CV with `gap=1`; report whether mean±std moves |
| Fold strip/boxplot | Per-fold RMSE plot for both models |
| SeasonalNaive-in-CV | Per-fold naive RMSE / skill vs each model |
| Nested CV / seed sweeps / t-CI / exog curve | **Skip** this PR |

### Phase 9 — Verification

```bash
uv run python scripts/train_revenue_forecast.py
uv run python scripts/run_diagnostics.py
uv run pytest tests/pipelines/test_temporal_cv_order.py -v
uv run pytest tests/pipelines/ -v
```

- Second diagnostics run: `cv_folds.json` / `learning_curve.json` stable.  
- Existing pipeline tests remain green (back-compatible signatures).  
- When delivering: update `memory-bank/progress.md` and `memory-bank/decisions.md`; request explicit developer acknowledgement before commit (per AGENTS.md).

---

## Correctness checklist (RF / ML via `TimeSeriesSplit`)

| # | Gotcha | Required approach |
|---|--------|-------------------|
| 1 | Future leak in features | `features.py` `.shift()` builder; assert no same-month target |
| 2 | Global target transform | Fit `Differences([12])` per fold on train only; invert for score |
| 3 | One-shot block predict | Recursive month-by-month within fold |
| 4 | Index vs date misalignment | Date-first windows; assert cross-engine match |
| 5 | Train RMSE ≈ 0 misread | Diagnose on val−train gap |
| 6 | Trees vs trend | Keep seasonal differencing; label trend-extrapolation if diagnosing raw revenue (not default) |

---

## Risk notes

- **Silent optimism:** one-shot `predict(X[test])` looks correct but leaks within-block actuals via lags — treat recursive predict as a hard review gate.  
- **Apples-to-oranges folds:** without date-first alignment, RF matrix rows (~72–84) and StatsForecast’s 96-row series can score different months.  
- **Winner flip:** pinning prior selection while diagnosing the new winner can confuse readers — report must state both clearly in Summary + CV setup.  
- **Small-sample std:** 5 folds → always report min/max and caveat.  
- **Pickle churn:** committing regenerated `.pkl`s may create large diffs even when diagnosis is the focus — expected per stakeholder choice.

---

## Done when

- [ ] Work lives only on `feature/eval_metrics` off `feature/sales_forecast`
- [ ] Selection CV defaults ≥5; report contrasts with prior 3-fold and notes classical was already 5
- [ ] Prior winner pinned + any flip noted; diagnostics target = 5-fold winner + AutoETS
- [ ] `cv_folds.json` has mean±std (and min/max) RMSE/MAE train+val for both
- [ ] Learning-curve PNGs + JSON for both (ElasticNet side curve if ML overfits)
- [ ] Report completes §10 including CONTEXT-healthcore §3 RMSE justification
- [ ] Fit labels follow numbers; corrective actions report-only and consistent
- [ ] `test_temporal_cv_order.py` green; full `tests/pipelines/` green
- [ ] Artifacts + pickles committed on the branch; PR aimed at `feature/sales_forecast`
