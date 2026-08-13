---
name: HealthCore Sales Revenue Forecast
overview: "Local Nixtla pipeline (MLForecast + StatsForecast) for monthly consolidated revenue: two-stage visits→revenue regression, classical SARIMA/AutoARIMA/AutoETS baselines, ablation, metrics, plots, report, and leakage-safe tests."
todos:
  - id: p0-branch-scaffold
    content: Create feature/sales_forecast; scaffold data/forecast/ + scripts/train_revenue_forecast.py + test stubs; place deps group in root pyproject.toml
    status: pending
  - id: p0-deps
    content: Add forecast dependency-group; uv sync --group forecast; update root uv.lock only
    status: pending
  - id: p1-clean
    content: Implement data/forecast/clean.py — load, filter consolidated, validate 120 rows, long format + visits exog, write parquet
    status: pending
  - id: p2-split-features
    content: Implement chronological 8/2 split + features.py FEATURE_COLUMNS (Groups A–C) with causality
    status: pending
  - id: p3-baseline
    content: Fit SeasonalNaive; record test RMSE/MAE as relative baseline
    status: pending
  - id: p4a-visits
    content: Stage-1 StatsForecast visits forecast (AutoARIMA/AutoETS); pick by visits CV RMSE; build X_df from forecast only
    status: pending
  - id: p4b-mlf
    content: MLForecast RF+XGB+ElasticNet; rolling-origin CV select; light param sweep; predict h=24 with X_df + conformal intervals
    status: pending
  - id: p4c-ablation
    content: Univariate ablation (Groups A+B only); compare to exogenous; ensure ≥1 regression model for recommendation
    status: pending
  - id: p5-classical
    content: StatsForecast SARIMA + AutoARIMA + AutoETS + AutoTheta + AutoCES; pin named SARIMA order; intervals level=[80,95]
    status: pending
  - id: p6-metrics
    content: metrics.py — MSE/RMSE/%/MAE/MAPE/MASE, PSI, Gini, K2, extras; write metrics.json
    status: pending
  - id: p7-plots
    content: plotting.py — predictions_combined, prediction_interval, residual_diagnostics PNGs
    status: pending
  - id: p8-report
    content: Write data/eval/revenue_forecast/report.md with embedded figures + business interpretations
    status: pending
  - id: p9-extras
    content: Perfect-foresight diagnostic, conformal miscoverage, rolling-origin backtest n_windows=4–6, PSI drift stub, pattern-recovery test
    status: pending
  - id: p10-tests
    content: test_revenue_split / no_leakage / data_validation (+ pattern-recovery); pytest tests/pipelines/ -v
    status: pending
  - id: p11-verify
    content: Idempotent train script twice; commit models + report + figures; update progress/decisions when delivering
    status: pending
isProject: false
---

# HealthCore — Monthly Revenue Forecast Implementation Plan

**Plan file:** [`healthcore_sales_regression_IMPLEMENTATION_PLAN.md`](healthcore_sales_regression_IMPLEMENTATION_PLAN.md)

**Requirements sources:**

- [`healthcore_sales_regression_specs.md`](healthcore_sales_regression_specs.md)
- [`healthcore_sales_regression_eval_criteria.md`](healthcore_sales_regression_eval_criteria.md)

**Branch:** `feature/sales_forecast`

**Working directory:** repository root (`chitrasharath_healthcore_ft_ai_1/`)

**Status:** Implemented on `feature/sales_forecast` — awaiting developer commit acknowledgement.

**Out of scope:** Docker / Compose `test` profile wiring; FastAPI / backoffice UI; TimeGPT / NeuralForecast; Prophet / `statsmodels` SARIMA; patient-level / PHI data.

---

## Executive summary

Build a fully local Nixtla forecasting pipeline that answers Sandra’s question: *can monthly consolidated revenue be predicted well enough for an executive dashboard?*

Deliverables:

1. **`data/forecast/`** package — clean, features, MLForecast (two-stage exogenous + univariate ablation), StatsForecast classical models, metrics, plotting  
2. **`scripts/train_revenue_forecast.py`** — idempotent end-to-end entrypoint (`random_state=42`)  
3. **Artifacts** under `data/process/` (clean parquet + **committed** `models/*.pkl`) and `data/eval/revenue_forecast/` (metrics, report, figures)  
4. **Leakage-safe tests** in `tests/pipelines/`  

Stack: **MLForecast** (tree + linear learners) + **StatsForecast** (SARIMA / Auto\* / SeasonalNaive). No API keys; no data leaves the environment.

---

## Prerequisites

- [ ] Working on branch `feature/sales_forecast` off `main`
- [ ] CSV present at `data/raw/healthcore_sales.csv` (120 consolidated monthly rows; gitignored — local only)
- [ ] Python 3.12+ and `uv` available at repo root
- [ ] Spec + eval criteria read end-to-end before coding

---

## Locked decisions (stakeholder Q&A + recommendations)

| Topic | Decision |
|-------|----------|
| PSI target | PSI on **model score distribution** (train vs test predictions), 10 quantile bins; report CONTEXT US/UK visit-mix **caveat** |
| Regression requirement | Must ship **≥1 regression model**. Exogenous two-stage is primary; univariate ablation always run. Report may recommend univariate if lift is weak — still counts as the regression model |
| Log / Box-Cox | **Off** for required path. Optional one-shot diagnostic in report (MAPE delta); do not make default `target_transforms` |
| Docker / CI | **Local only** — `uv sync --group forecast` + `uv run pytest tests/pipelines/`; do not touch Compose |
| uv lockfiles | Add `forecast` group to **root** `pyproject.toml`; `uv sync --group forecast`; update **root** `uv.lock` only; leave `services/api` untouched |
| Param sweep | **Light** `RandomizedSearchCV`-style on CV winner only (few trials) |
| Committed artifacts | Commit `data/process/models/*.pkl`, `data/eval/revenue_forecast/report.md`, figures, `metrics.json`. Do **not** commit raw CSV or clean parquet (parquet may be regenerated; optional gitignore if noisy) |
| Branch | `feature/sales_forecast` |
| Stage-1 visits | Forecast with StatsForecast AutoARIMA + AutoETS; pick by visits rolling-origin CV RMSE; `X_df.visits_count` = forecast only |
| SARIMA orders | Start `(1,1,1)(1,1,1)₁₂`; confirm `d`/`D` (ADF + seasonal strength); **prefer pinning named SARIMA to AutoARIMA’s order** when sensible; else keep hand-tuned and document both |
| Extra classical (§13) | **Include** `AutoTheta` + `AutoCES` in StatsForecast model list |
| Extra ML learners (§13) | **Include** `ElasticNet` (or `HistGradientBoosting` if ElasticNet is awkward with Nixtla wrappers) in same `models={...}` dict; primary CV still RF vs XGB (+ linear as third candidate) |
| Skip | `MSTL`, LightGBM, NeuralForecast, TimeGPT (mention only in report) |

### §12 enhancements — in scope for v1

| Item | Action |
|------|--------|
| Rolling-origin backtest `n_windows=4–6` | Required — report stability for every headline model |
| Perfect-foresight visits diagnostic | Required — upper-bound only; **not** in headline metrics; clearly labeled leakage-for-diagnosis |
| Conformal coverage / miscoverage | Required — report % of test points inside 80/95% bands for chosen MLForecast model |
| Pattern-recovery assertion test | Required — seasonal factors lowest Jul–Aug, highest Oct–Dec |
| Drift-monitor PSI stub | Required — function recomputing PSI on a new month batch (callable from metrics module) |
| Log/Box-Cox comparison | Optional diagnostic only (not default) |
| Feature importance / SHAP | **Defer** — if cheap, tree `feature_importances_` for lag_12 / month story; no SHAP dependency |

---

## Repository layout (create)

```
data/forecast/
  __init__.py
  clean.py
  features.py              # FEATURE_COLUMNS source of truth
  models_mlforecast.py
  models_statsforecast.py
  metrics.py
  plotting.py
scripts/
  train_revenue_forecast.py
tests/pipelines/
  test_revenue_split.py
  test_revenue_no_leakage.py
  test_revenue_data_validation.py
  test_revenue_pattern_recovery.py   # §12 pattern-recovery
```

**Writes into existing dirs:**

```
data/raw/healthcore_sales.csv                 # local, gitignored
data/process/healthcore_sales_clean.parquet   # regenerated
data/process/models/*.pkl                     # COMMIT
data/eval/revenue_forecast/
  metrics.json                                # COMMIT
  report.md                                   # COMMIT
  figures/*.png                               # COMMIT
```

---

## Eval criteria crosswalk

| # | Criterion | Plan coverage |
|---|-----------|---------------|
| 1 | Two-stage exogenous / no leakage | Phase 4a–4c; `X_df` = Stage-1 forecast; no `avg_revenue_per_visit`; ablation |
| 1b | Explicit feature catalog | `features.FEATURE_COLUMNS`; asserted in no-leakage tests |
| 2 | Chronological 8/2 split | Phase 2; `test_revenue_split.py` |
| 3 | Transforms fit on train only | MLForecast `Differences([12])` + `LocalStandardScaler` inside `.fit()` |
| 4 | Tests pass | Phase 10 |
| 5 | RF vs XGB by CV | Phase 4b (+ ElasticNet as third CV candidate); test set scored once |
| 5b | Stage-1 visits + ablation | Phases 4a, 4c; metrics + report |
| 6 | Beats SeasonalNaive | Phase 3 baseline; report explains if not |
| 7 | SARIMA + AutoARIMA + AutoETS | Phase 5 (+ AutoTheta/AutoCES extras) |
| 8 | MSE/PSI/Gini/K2 + interpretations | Phase 6–8 |
| 8b | MASE vs SeasonalNaive (plan add-on) | Phase 6 — store in `metrics.json`; interpret in report |
| 9 | Combined prediction plot | Phase 7 |
| 10 | Deterministic rerun | seed 42; verify script twice |
| 11 | Readable report | Phase 8 |

---

## Implementation phases

### Phase 0 — Branch, deps, scaffold

1. Create/checkout `feature/sales_forecast`.
2. Append to root `pyproject.toml` under `[dependency-groups]`:

```toml
forecast = [
  "numpy>=1.26",
  "scikit-learn>=1.4",
  "xgboost>=2.0",
  "mlforecast>=0.13",
  "statsforecast>=1.7",
  "utilsforecast>=0.2",
  "matplotlib>=3.8",
  "pyarrow>=15",
  "scipy>=1.11",
]
```

3. Run `uv sync --group forecast` (root lockfile only). If lock conflict: `uv pip install …` into workspace `.venv` and note in report.
4. Create empty package modules + script stub + test file shells listed above.
5. Confirm `data/raw/healthcore_sales.csv` exists (do not commit).

### Phase 1 — Clean & validate (`clean.py`)

Follow specs §5.1:

1. Load CSV; parse `month` → datetime.  
2. Filter `region == "consolidated"`.  
3. Drop null/empty `month` or `revenue_usd`; log drop count.  
4. Sort ascending; validate exactly 120 rows, no month gaps `2016-01…2025-12`, all `revenue_usd > 0`.  
5. Nixtla long format: `unique_id="consolidated"`, `ds`, `y=revenue_usd`, keep `visits_count`. Drop `avg_revenue_per_visit_usd` and `region`.  
6. Write `data/process/healthcore_sales_clean.parquet`.  
7. Print short profile (rows, date range, revenue min/max/mean).

### Phase 2 — Split & features

**Split [DECIDED]:** train `2016-01…2023-12` (96), test `2024-01…2025-12` (24). Assert `train.ds.max() < test.ds.min()`.

**`features.py`:** build Groups A–C per specs §5.2. Keep single `FEATURE_COLUMNS` list. Causality:

- Revenue lags/rolling via `.shift(1+)` or MLForecast lags only.  
- Never include `avg_revenue_per_visit_usd`.  
- Contemporaneous `visits_count` at predict time from Stage-1 forecast only.  
- Prefer precomputing `trend`, `rev_yoy`, and any visits lags/rolls that tests must inspect via explicit `.shift()`.

MLForecast config (spec §5.2 snippet) as starting point — add `ElasticNet` to `models={...}` with `random_state=42` where applicable.

### Phase 3 — SeasonalNaive baseline

Fit `StatsForecast(models=[SeasonalNaive(season_length=12)], freq="MS")` on train; `predict(h=24)`; store test RMSE/MAE. All later models reported **relative to** this baseline.

### Phase 4a — Stage 1: visits forecast

```text
visits_train = train with y := visits_count
sf_v = AutoARIMA + AutoETS (season_length=12)
pick winner by visits rolling-origin CV RMSE
visits_fcst → X_df for revenue predict (unique_id, ds, visits_count)
```

- Report visits RMSE/MAPE vs actual test visits.  
- Leakage rule: `X_df` ≠ `test_df.visits_count`; perturbing test visits must not change revenue preds.

### Phase 4b — Stage 2: MLForecast revenue

1. Fit RF + XGB + ElasticNet on train with actual historical visits + Group A/B/C.  
2. Select via `mlf.cross_validation(train_df, n_windows=3, h=12, step_size=12)` — mean CV RMSE (tie-break MAE, then simplicity). **Test untouched.**  
3. Light param sweep on winner only (RF: `n_estimators`, `max_depth`, `max_features`; XGB: `max_depth` 2–3, `n_estimators`, `learning_rate`, `subsample`/`colsample`; ElasticNet: `alpha`, `l1_ratio`).  
4. Refit with `PredictionIntervals(n_windows=3, h=12)`; `predict(h=24, X_df=visits_fcst, level=[80,95])`.  
5. Persist fitted model(s) to `data/process/models/` (e.g. `mlforecast_exogenous.pkl`, `mlforecast_univariate.pkl`).

### Phase 4c — Univariate ablation

Same MLForecast path **without** Group C visits features. Forecast test horizon. Side-by-side metrics → ablation verdict in report. Recommendation must name **at least one** regression model for the dashboard.

### Phase 5 — Classical StatsForecast

Models list:

```text
ARIMA → alias "SARIMA" (explicit seasonal order)
AutoARIMA(season_length=12)
AutoETS(season_length=12)
AutoTheta(season_length=12)      # §13 include
AutoCES(season_length=12)        # §13 include
SeasonalNaive(season_length=12)  # already Phase 3; may reuse
```

- `fit(train)` → `predict(h=24, level=[80,95])`.  
- Record final `SARIMA(p,d,q)(P,D,Q)₁₂`, AutoARIMA order agreement, ETS components.  
- Persist fitted StatsForecast object(s) under `data/process/models/`.

### Phase 6 — Metrics (`metrics.py` → `metrics.json`)

On **test** set for: chosen MLForecast exogenous, univariate ablation, SARIMA, AutoARIMA, AutoETS (plus AutoTheta/AutoCES if reporting them).

**Required:** MSE, RMSE, RMSE/MSE as % of mean monthly test revenue, MAE, MAPE, **MASE**, PSI (score distribution + caveat), Gini, K2 (`scipy.stats.normaltest` + p).

**MASE (added):** Mean Absolute Scaled Error vs the **SeasonalNaive** (season_length=12) in-sample / seasonal-naive scale — typically  
`MASE = mean(|ŷ − y| on test) / mean(|y_t − y_{t−12}| on train)`.  
Report for every headline model so Sandra can read skill relative to “same month last year.” MASE &lt; 1 beats SeasonalNaive on absolute error scale.

**Extras (§8.5):** R², sMAPE, directional accuracy, PI coverage 80/95, Ljung–Box on residuals.

**Also:** Stage-1 visits RMSE/MAPE; conformal miscoverage; perfect-foresight diagnostic metrics (separate key, labeled); rolling-origin CV summary tables.

Expose `compute_psi(...)` / thin `drift_monitor_psi(new_scores, reference_scores)` stub for dashboard reuse.

### Phase 7 — Plots (`plotting.py`)

`matplotlib.use("Agg")`, ≥150 dpi → `data/eval/revenue_forecast/figures/`:

1. **`predictions_combined.png`** — full 10y axis; train actual solid; test actual markers; overlays for exogenous MLF, univariate, SARIMA, AutoARIMA, AutoETS (Theta/CES optional if legend stays readable); shade intervals; optional visits inset.  
2. **`prediction_interval.png`** — chosen MLForecast 80/95% bands vs 2024–25 actuals, zoomed.  
3. **`residual_diagnostics.png`** — residuals over time, histogram + normal overlay, residual ACF.

### Phase 8 — Report (`report.md`)

Sections per specs §10:

1. Executive summary (numbers-first for Sandra)  
2. Data & cleaning / 8–2 split / leakage decisions  
3. MLForecast two-stage + CV evidence + Stage-1 visits accuracy + ablation verdict  
4. Classical models + SARIMA order + vs SeasonalNaive  
5. Embedded plots  
6. Metrics table + plain-English interpretations (MSE/RMSE/%, **MASE**, PSI caveat, K2 → interval trust)  
7. Recommendation + limitations (120 points, trend extrapolation, no regional data)  
8. Brief note on deferred items (SHAP, TimeGPT, log as default)

### Phase 9 — In-scope extras (wire into script + report)

- Rolling-origin backtest `n_windows=4–6` for headline models  
- Perfect-foresight visits run (diagnostic only)  
- Conformal coverage numbers  
- `test_revenue_pattern_recovery.py`  
- PSI drift stub in `metrics.py`

### Phase 10 — Unit tests

Match repo style (`from __future__ import annotations`, type hints, import real `data.forecast.*`).

| File | Asserts |
|------|---------|
| `test_revenue_split.py` | 96/24; `2023-12` / `2024-01` boundaries; no overlap; full coverage |
| `test_revenue_no_leakage.py` | fit train-only; transforms ignore test `y`; `FEATURE_COLUMNS` match; no avg_rev_per_visit; `X_df` = forecast ≠ test visits; perturb test visits → preds unchanged; CV cutoffs causal |
| `test_revenue_data_validation.py` | 120 rows, `y>0`, no gaps; null row dropped |
| `test_revenue_pattern_recovery.py` | AutoARIMA/AutoETS seasonal factors: Jul–Aug low, Oct–Dec high |

### Phase 11 — Verify & handoff

```bash
uv sync --group forecast
uv run python scripts/train_revenue_forecast.py   # run twice; diff metrics.json
uv run pytest tests/pipelines/ -v
```

Before commit (per AGENTS.md): re-read progress/decisions; update them; summarize change/risk; **wait for explicit developer acknowledgement** before `git commit`.

**Suggested commit contents:** `data/forecast/**`, `scripts/train_revenue_forecast.py`, `tests/pipelines/test_revenue_*.py`, root `pyproject.toml` + `uv.lock`, `data/process/models/*.pkl`, `data/eval/revenue_forecast/**`. Not raw CSV.

---

## Entrypoint contract

`scripts/train_revenue_forecast.py` must:

1. Be runnable from repo root with no env secrets.  
2. Regenerate clean parquet, models, metrics, figures, report.  
3. Be deterministic given fixed CSV + seed 42.  
4. Print which regression learner and classical model win, plus ablation one-liner.

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Near-perfect metrics (leakage red flag) | No-leakage tests + review `X_df` source |
| Trees ignore scaling | Report honestly: `Differences` helps; scaler satisfies assignment |
| Strong 2024–25 trend → high PSI | Document as score-range drift, not clinic-mix |
| CV on ~84 effective rows unstable | Light sweep; prefer simpler model on MAE tie; backtest windows |
| `uv.lock` / numba install friction | Fall back to `uv pip install`; document in report |
| Legend overcrowding on combined plot | Prefer required models in main legend; Theta/CES in metrics table / secondary panel if needed |
| Pickling StatsForecast/MLForecast | Prefer joblib/pickle of fitted objects; document reload path in report |

---

## Non-goals (explicit)

- Dashboard UI / FastAPI endpoints for forecasts  
- Regional US/UK series (data unavailable)  
- Hosted Nixtla TimeGPT  
- Changing `services/api` or Docker images  
- Committing `data/raw/*.csv`

---

## Memory-bank updates (at delivery)

- [`progress.md`](../../progress.md) — add Sales Forecast milestone / status on `feature/sales_forecast`  
- [`decisions.md`](../../decisions.md) — record two-stage exogenous design, local Nixtla stack, committed models path, extras included/deferred  

---

## Ready-to-build checklist

- [ ] Branch `feature/sales_forecast` created  
- [ ] CSV at `data/raw/healthcore_sales.csv`  
- [ ] This plan + specs + eval criteria acknowledged  
- [ ] Proceed with Phase 0 when developer says start implementation  
