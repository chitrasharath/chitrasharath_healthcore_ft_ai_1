# HealthCore — Monthly Revenue Prediction (Nixtla: MLForecast + StatsForecast)

> **Spec for a coding agent.** Read this end to end before writing code. It tells you
> what to build, where to put it, and how each piece is judged. Where a decision has
> already been made by the human, it is marked **[DECIDED]**. Where you must decide
> empirically, it is marked **[YOU DECIDE — document it]**.
>
> **Stack decision:** this project is built on the **Nixtla** ecosystem —
> **MLForecast** for the tree-based regression forecast and **StatsForecast** for the
> classical time-series models. Everything runs **locally**; no API keys, no external
> services, no data leaving the environment. Prophet and hand-rolled `statsmodels` SARIMA
> are **not** used. (TimeGPT was considered and **dropped** — it requires a Nixtla API
> key and would send the series to Nixtla's servers; noted as possible future work only.)
>
> **Feature decision:** the regression is a **two-stage exogenous** design — first
> forecast `visits_count`, then feed that forecast into MLForecast as an exogenous
> demand driver alongside revenue's own lag/calendar features. A pure-univariate model
> (revenue only) is kept as an **ablation baseline** to prove whether visits actually
> help. `avg_revenue_per_visit_usd` stays excluded (it would reconstruct the target).

---

## 1. Project Overview

HealthCore is a network of 12 clinics (9 US, 3 UK). Sandra (CEO) wants to know whether
monthly consolidated revenue can be **predicted well enough** to justify building a
network-wide executive dashboard. Revenue tracks visit demand, which is strongly
seasonal (year-end flu-season lift, summer-vacation dip) on top of a modest upward
growth trend. Marcus (Clinical Operations) and Tom (Revenue Cycle) have observed this
for years but never quantified it.

You are given **10 years of monthly aggregated revenue** (`2016-01` … `2025-12`, 120
rows). Build two families of models on the Nixtla stack and compare them honestly:

1. A **regression forecast** via **MLForecast** (Random Forest *or* XGBoost as the
   underlying learner — you choose and justify), using automatically-generated lag,
   rolling, and calendar features **plus `visits_count` as an exogenous demand driver**
   (forecast in a first stage — §7.4a), with native recursive multi-step forecasting.
   A univariate variant (no visits) is trained alongside as an ablation.
2. **Classical time-series** via **StatsForecast** — **[DECIDED]** an explicit
   **SARIMA** (`ARIMA` with a seasonal order), plus **`AutoARIMA`** (auto-selected
   seasonal ARIMA) and **`AutoETS`**, with `SeasonalNaive` as the built-in baseline.
   Prophet is dropped; SARIMA is implemented inside StatsForecast (no `statsmodels`).

Then write a markdown **report** explaining which models were chosen and why, with the
prediction plots embedded and every evaluation metric interpreted in plain business
language.

### 1.1 Framing points the report MUST make explicitly

- **Why `avg_revenue_per_visit` is excluded but `visits_count` is used carefully.** The
  raw dataset contains a near-identity: `visits_count × avg_revenue_per_visit ≈
  revenue_usd` (verify: `2016-01` → `13938 × 169.74 = 2,365,635` vs actual `2,365,866`).
  Feeding **both** columns to predict `revenue_usd` is **target leakage** — the model
  just relearns multiplication. `avg_revenue_per_visit_usd` is therefore **never** a
  feature. `visits_count` alone, however, does **not** determine revenue (the per-visit
  price varies ~$170–190 month to month), so it is a legitimate *partial* demand signal.
  **[DECIDED]** The primary regression uses **`visits_count` as an exogenous regressor**,
  but — critically — for the test/forecast horizon it must use a **forecast of visits**,
  not the actual test-period visits (you would not know future visits at prediction
  time; using them is leakage). This makes it a **two-stage** model: forecast visits
  (§7.4a), then forecast revenue conditioned on predicted visits (§7.4b). A univariate
  model (revenue's own history only) is trained as an ablation to quantify how much
  visits actually add.
- **The test set is the last 2 years, held out chronologically** — never random. In
  Nixtla terms: `fit` on the training window, `predict(h=24)`, and score against the
  held-out 24 months. Random splitting a time series leaks the future.
- **This is aggregate revenue only.** No patient-level data, no PHI. Never introduce a
  patient identifier, diagnosis, or clinical field. This keeps the work outside HIPAA /
  UK GDPR scope (CONTEXT §1). Because the whole pipeline runs locally (no external
  forecasting service), no data ever leaves the environment.

### 1.2 Success criteria

- `scripts/train_revenue_forecast.py` runs end to end from a clean checkout and regenerates every
  artifact (models, metrics JSON, plots, report figures) deterministically.
- `pytest tests/pipelines/` passes, including the **split** and **no-leakage** tests.
- The chosen MLForecast model beats the `SeasonalNaive` baseline on test RMSE, or the
  report explains why not.
- The report names the chosen regression learner, the chosen StatsForecast model, shows
  the combined prediction plot, and interprets MSE, PSI, Gini, and K2 in business terms.

---

## 2. Tech Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python **3.12+** | Matches the repo's `requires-python` (§6). |
| Env / deps | `uv` **workspace** | Add a `forecast` dependency-group to the **root** `pyproject.toml`; do not touch `services/api` (§6). |
| Data | `pandas`, `numpy` | Long format: `unique_id`, `ds`, `y` (§5). |
| Regression forecast | **`mlforecast`** wrapping `scikit-learn` RandomForest + `xgboost` | Train both learners, pick one via rolling-origin CV (§7.4). |
| Classical TS | **`statsforecast`** — `ARIMA` (explicit SARIMA), `AutoARIMA`, `AutoETS`, `SeasonalNaive` | **[DECIDED]**. SARIMA lives in StatsForecast; no `statsmodels`. |
| Scaling / transforms | `mlforecast.target_transforms` (`Differences`, `LocalStandardScaler`) | Fit inside `.fit()` on train only → leakage-safe (§5.4). |
| Loss helpers | `utilsforecast.losses` | For MSE/RMSE/MAPE; PSI/Gini/K2 are custom (§8). |
| Plotting | `utilsforecast.plotting` / `matplotlib` | Save PNGs; `Agg` backend. |
| Tests | `pytest` | In `tests/pipelines/`. |
| Report | Markdown + embedded PNGs | **[DECIDED]**. |

Pin `random_state=42` on every learner and seed. StatsForecast/MLForecast are
deterministic given fixed learners and data.

---

## 3. Repository Structure

**[DECIDED]** This lands inside the **existing HealthCore monorepo**
(`chitrasharath_healthcore_ft_ai_1/`), which is a `uv` workspace where root packages
resolve via `pythonpath = ["."]` (there is **no `src/`** — code lives in top-level
packages like `data.pipelines` and `app.*`). The revenue forecaster is a new pipeline in
the `data.*` namespace, siblings to the existing `data/pipelines/` ETL flow. Working dir
is the repo root.

**New files (create these):**

```
data/
  forecast/                         # NEW package — the revenue-forecasting pipeline
    __init__.py
    clean.py                        # load, remove nulls, validate, to long format (+ visits exog), split
    features.py                     # explicit feature catalog (Groups A–C) + FEATURE_COLUMNS source of truth (§5.2)
    models_mlforecast.py            # MLForecast: RF + XGB, CV selection, intervals, exog + univariate ablation
    models_statsforecast.py         # StatsForecast: SARIMA (explicit ARIMA) + AutoARIMA + AutoETS for revenue AND the Stage-1 visits forecast; SeasonalNaive baseline
    metrics.py                      # MSE, PSI, Gini, K2, extras
    plotting.py                     # prediction + diagnostic plots
scripts/
  train_revenue_forecast.py         # entrypoint: load → clean → split → features → fit → forecast → eval → plot
tests/
  pipelines/                        # ALREADY EXISTS (holds test_pipeline.py)
    test_revenue_split.py           # 8/2-year split correctness
    test_revenue_no_leakage.py      # fit-on-train-only, transforms causal, feature catalog, no target identity
    test_revenue_data_validation.py # 120 rows, no gaps, positive revenue
```

**Existing folders this pipeline writes into (do not invent new top-level dirs):**

```
data/
  raw/healthcore_sales.csv          # PLACE the provided file here (§4). NOTE: data/raw/*.csv is .gitignored.
  process/
    healthcore_sales_clean.parquet  # cleaned dataset (data/process = processed artifacts, per its README)
    models/*.pkl                     # persisted fitted models
  eval/
    revenue_forecast/               # data/eval = evaluation outputs, per its README
      metrics.json                  # all metrics
      report.md                     # the markdown report
      figures/predictions_combined.png
      figures/prediction_interval.png
      figures/residual_diagnostics.png
```

- **Phase 0** places the provided CSV at `data/raw/healthcore_sales.csv`. Because
  `.gitignore` excludes `data/raw/*.csv`, the file lives locally and is **not** committed
  — consistent with how the repo already treats raw data. The agent must ensure the file
  is present before running; don't assume it comes from git.
- The report figures under `data/eval/revenue_forecast/figures/` **are** committed (they
  are not covered by any gitignore rule) so `report.md` renders on GitHub.
- Add `__init__.py` to `data/forecast/` (the repo uses package markers, e.g.
  `data/__init__.py`, `data/pipelines/__init__.py`). `tests/pipelines/` already has one.

---

## 4. The Data

`data/raw/healthcore_sales.csv` — 120 monthly `consolidated` rows, `2016-01-01` …
`2025-12-01`.

| Column | Type | Notes |
|---|---|---|
| `month` | date `YYYY-MM-01` | → Nixtla `ds` (datetime, freq `MS`). |
| `revenue_usd` | float | → Nixtla `y` (target). Must be > 0. |
| `visits_count` | int | **Exogenous regressor** — actual values in training, **forecasted** values over the test horizon (§7.4a, §1.1). |
| `avg_revenue_per_visit_usd` | float | **Excluded** — with visits it reconstructs the target. |
| `region` | string | Filter to `"consolidated"`; becomes the single `unique_id`. |

### 4.1 Patterns baked into the data (understand, don't regenerate)

- Base annual growth `X = 4%`, variation `Y = 2%`; each year alternates 6% / 2% growth.
- **Oct–Dec:** +15–20% vs average (flu + year-end). **Jul–Aug:** −12–18% (summer).
- Other months ±5%. Generated with `random_state=42` → deterministic.

The report should confirm the models *recover* these patterns (AutoARIMA/AutoETS seasonal
components dip Jul–Aug and peak Oct–Dec; MLForecast lag-12 / month features dominate).

### 4.2 Data quirks to surface

- Revenue grows ~$2.3M/mo (2016) → ~$4.0M/mo (2025): a strong trend the models must not
  read as noise. `Differences([12])` in MLForecast and the trend/drift terms in
  AutoARIMA/AutoETS handle this — confirm in the report.
- Only `consolidated` exists — **no US/UK breakdown**, so CONTEXT §3's US/UK visit-mix
  PSI is **not directly computable**. Compute PSI on the model score distribution instead
  and state the caveat (§8.2).

---

## 5. Cleaning, Long Format, Splitting, Transforms

### 5.1 Cleaning (`data/forecast/clean.py`)

1. Load CSV, parse `month` → datetime.
2. Filter `region == "consolidated"`.
3. **Remove nulls / empty values**: drop rows with null/empty `month` or `revenue_usd`;
   log the count dropped (expected 0, but handle it).
4. Sort by `month` ascending.
5. **Validate** (raise on failure): exactly 120 rows; no missing months in
   `2016-01…2025-12` (reindex a monthly `date_range`, assert no gaps); all
   `revenue_usd > 0`.
6. **Reshape to Nixtla long format**: columns `unique_id="consolidated"`,
   `ds=month`, `y=revenue_usd`, **and keep `visits_count` as an exogenous column**.
   Write to `data/process/healthcore_sales_clean.parquet`. (`avg_revenue_per_visit_usd`
   and `region` are dropped from the modeling frame.)

### 5.2 Features — MLForecast lag/calendar features + exogenous visits

**[DECIDED]** The regression predictors fall in four groups: **(A) calendar/seasonality**,
**(B) autoregressive** (from revenue's own past), **(C) exogenous visits**, and the
**(D) target transforms** applied before the learner. The full catalog — build exactly
these:

#### Group A — Calendar & seasonality (deterministic, always known)

| Feature | Definition | Why |
|---|---|---|
| `month` | month number 1–12 | lets trees split on specific months |
| `month_sin`, `month_cos` | `sin/cos(2π·month/12)` | smooth cyclical seasonality (better than raw month for boundaries Dec→Jan) |
| `quarter` | 1–4 | coarse seasonal block |
| `year` | calendar year (e.g. 2016…2025) | trend level |
| `trend` | integer 0,1,2,… over the ordered series | monotonic trend index |
| `is_high_season` | 1 if month ∈ {10,11,12} else 0 | encodes CONTEXT §4's Oct–Dec +15–20% lift directly |
| `is_low_season` | 1 if month ∈ {7,8} else 0 | encodes CONTEXT §4's Jul–Aug −12–18% dip directly |

#### Group B — Autoregressive revenue features (strictly past values)

| Feature | Definition | Why |
|---|---|---|
| `rev_lag_1` | revenue at t−1 | short-term level / momentum |
| `rev_lag_2`, `rev_lag_3` | revenue at t−2, t−3 | recent trajectory |
| `rev_lag_12` | revenue at t−12 (same month last year) | carries seasonality directly |
| `rev_roll_mean_3` | mean of t−1..t−3 | smoothed recent level |
| `rev_roll_mean_12` | mean of t−1..t−12 | trailing annual level (trend anchor) |
| `rev_roll_std_3` | std of t−1..t−3 | recent volatility |
| `rev_yoy` | `rev_lag_1 / rev_lag_13 − 1` | year-over-year growth signal |

#### Group C — Exogenous visits (demand driver)

| Feature | Definition | Known at predict time via |
|---|---|---|
| `visits_count` | visits in month t | **Stage-1 visits forecast** (`X_df`) — never actual test visits |
| `visits_lag_1` | visits at t−1 | past actual visits |
| `visits_lag_12` | visits at t−12 | past actual visits |
| `visits_roll_mean_3` | mean visits t−1..t−3 | past actual visits |

#### Group D — Target transforms (not features; applied to `y` before fitting)

`Differences([12])` (remove annual seasonal level) then `LocalStandardScaler` (the
**scaling** step, §5.4). Both are fit **inside** `.fit()` on the training window only.

#### MLForecast configuration that produces the catalog

```python
import numpy as np
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, RollingStd
from mlforecast.target_transforms import Differences, LocalStandardScaler
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

# Group A extras that MLForecast's built-in date_features don't cover, as callables:
def quarter(dates):        return dates.quarter
def is_high_season(dates): return dates.month.isin([10, 11, 12]).astype(int)
def is_low_season(dates):  return dates.month.isin([7, 8]).astype(int)
def month_sin(dates):      return np.sin(2 * np.pi * dates.month / 12)
def month_cos(dates):      return np.cos(2 * np.pi * dates.month / 12)

mlf = MLForecast(
    models={
        "rf":  RandomForestRegressor(n_estimators=300, random_state=42),
        "xgb": XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05,
                            subsample=0.9, colsample_bytree=0.9, random_state=42),
    },
    freq="MS",
    lags=[1, 2, 3, 12],                                    # Group B lags → rev_lag_1/2/3/12
    lag_transforms={
        1:  [RollingMean(window_size=3), RollingStd(window_size=3)],  # rev_roll_mean_3, rev_roll_std_3
        12: [RollingMean(window_size=12)],                 # rev_roll_mean_12
    },
    date_features=["month", "year", quarter, month_sin, month_cos,
                   is_high_season, is_low_season],          # Group A
    target_transforms=[Differences([12]), LocalStandardScaler()],  # Group D
)
# `trend`, `rev_yoy`, and the visits_* features (Group C) are added to the input frame as
# columns before fit; visits_count is supplied for the horizon via X_df at predict time.
# MLForecast lags any exogenous column you pass, so visits_lag_1/12 come for free once
# visits_count is in the frame.
```

> **Implementation note.** MLForecast's automatic lag machinery covers the `rev_lag_*`
> and rolling features and will lag exogenous `visits_count`. A few features
> (`trend`, `rev_yoy`, and the explicit `visits_lag_*`/`visits_roll_mean_3` if you prefer
> them precomputed) are simplest to compute in `features.py` and attach to the frame
> before `fit`. Whichever route, **every feature must obey the causality rule below** —
> if in doubt, precompute in `features.py` with explicit `.shift()` so the leakage test
> can inspect it. Keep a single `FEATURE_COLUMNS` list in `features.py` as the source of
> truth, asserted by the tests.

**Causality rule (enforced by `test_revenue_no_leakage.py`):** every feature for the row
at time `t` must be computable strictly *before* `revenue_usd[t]` is known.
- Revenue lags/rolling use only `t−1` and earlier → `.shift(1)` or more.
- **`avg_revenue_per_visit_usd` is never a feature** (with visits it reconstructs the target).
- Contemporaneous `visits_count[t]` is exogenous but *unknown* for the future, so at
  predict time it comes from the **Stage-1 visits forecast** (§7.4a), **never** the actual
  test-period visits.

### 5.3 Split — **[DECIDED] first 8 years train, last 2 years test**

- **Train:** `2016-01…2023-12` (96 months). **Test:** `2024-01…2025-12` (24 months).
- Split **chronologically by `ds`**, never randomly. Assert `train.ds.max() < test.ds.min()`.
- Fit models on the 96-month train frame; `predict(h=24)`; score against the 24-month
  test frame. (MLForecast internally drops the earliest rows lacking a `lag_12` — that
  is expected and stays inside `.fit()`; the raw split boundary is still 96/24, which is
  what `test_revenue_split.py` checks.)

### 5.4 Scaling / transforms

- **Scaling requirement is satisfied by MLForecast `target_transforms`**:
  `Differences([12])` + `LocalStandardScaler()`. `LocalStandardScaler` standardizes the
  (differenced) series using **training statistics only**, learned inside `.fit()`, and
  inverts automatically at `.predict()`. This is the leakage-safe equivalent of an
  sklearn `StandardScaler.fit(train)`.
- Tree learners are scale-invariant, so scaling doesn't change RF/XGB point predictions —
  the transforms matter because `Differences` **stabilizes the trend+seasonality** (which
  does help) and because the assignment requires scaling. State this honestly in the
  report rather than claiming scaling boosted the trees.
- **StatsForecast models** (`AutoARIMA`, `AutoETS`) take the **raw `y`** and handle
  trend/seasonality internally — do not pre-difference or pre-scale their input.

---

## 6. Dependencies

**Do not create a new `pyproject.toml`.** The repo is a `uv` workspace with a root
`pyproject.toml` (name `healthcore-workspace`, `requires-python = ">=3.12"`) and a
member at `services/api`. The forecasting deps do not belong to the API service, so add
them as a **dependency-group in the root `pyproject.toml`**, leaving `services/api`
untouched.

### 6.1 Root `pyproject.toml` — add a `forecast` group

```toml
# append under the existing [dependency-groups] table in the ROOT pyproject.toml
[dependency-groups]
# ... existing dev = [...] stays ...
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
`pandas>=2.0` is already a workspace dependency (via `services/api`), so it is not
repeated. Python is **3.12+** (repo requirement) — do not pin 3.11.

### 6.2 Setup

```bash
# from the repo root
uv sync --group forecast          # resolves into the existing uv.lock / .venv
```

`statsforecast` and `mlforecast` are pure-Python + `numba`; they install cleanly (no
Stan/cmdstan, unlike the dropped Prophet). No API keys or network access are required —
the whole pipeline runs offline. If `uv sync --group forecast` conflicts with the pinned
`uv.lock`, fall back to `uv pip install <the forecast deps>` inside the workspace `.venv`
and note it in the report.

---

## 7. Implementation

### Phase 0 — Scaffold
Create the `data/forecast/` package (with `__init__.py`) and the `scripts/` +
`tests/pipelines/` files from §3, place the CSV at `data/raw/healthcore_sales.csv`, and
add the `forecast` dependency-group to the **root** `pyproject.toml` (§6). Do not create a
new `pyproject.toml` or a `src/` dir.

### Phase 1 — Load, clean, validate, reshape
Implement §5.1. Print a short profile (row count, date range, revenue min/max/mean).

### Phase 2 — Split & features
Implement §5.3 (split) and build the §5.2 feature catalog in `features.py`, exposing
`FEATURE_COLUMNS`. Produce `train_df`/`test_df` in Nixtla long format with the exogenous
`visits_count` column attached.

### Phase 3 — Baseline
Fit `StatsForecast(models=[SeasonalNaive(season_length=12)], freq="MS")` and record its
test RMSE/MAE. Every model is reported **relative to SeasonalNaive**.

### Phase 4a — Stage 1: forecast `visits_count` (StatsForecast)
The revenue model needs future visits it does not know. Forecast them first:
```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS

visits_train = train_df.rename(columns={"visits_count": "y"})[["unique_id", "ds", "y"]]
sf_v = StatsForecast(models=[AutoARIMA(season_length=12), AutoETS(season_length=12)],
                     freq="MS")
sf_v.fit(visits_train)
visits_fcst = sf_v.predict(h=24)          # predicted visits for 2024-01 … 2025-12
```
- Report the visits forecast's own accuracy against actual test visits (RMSE/MAPE) — the
  revenue model inherits this error, so it matters.
- Build `X_df` for the horizon: `unique_id`, `ds`, and `visits_count` = the chosen
  visits forecast (pick AutoARIMA or AutoETS by the visits-CV RMSE).
- **Leakage rule:** `X_df` uses the *forecast*, never `test_df.visits_count`. The
  no-leakage test checks this.

### Phase 4b — Stage 2: MLForecast revenue regression, RF vs XGBoost **[YOU DECIDE — document it]**
- Fit the `mlf` from §5.2 on `train_df` (revenue `y` + actual historical `visits_count`),
  both learners at once.
- **Select** RF vs XGBoost by **rolling-origin cross-validation on the training window**:
  `mlf.cross_validation(train_df, n_windows=3, h=12, step_size=12)`. Within CV, MLForecast
  supplies the exogenous automatically from the held-out fold's known history — fine for
  selection. Selection metric: mean CV RMSE (tie-break CV MAE, then simplicity). **The
  test set is touched once, at the very end.**
- Guidance (report your actual finding): with ~84 effective training rows a
  well-regularized XGBoost or a Random Forest can win — let CV decide, then do a small
  `RandomizedSearchCV`-style sweep of the winner's key params (RF: `n_estimators`,
  `max_depth`, `max_features`; XGB: `max_depth` 2–3, `n_estimators`, `learning_rate`,
  `subsample`/`colsample`).
- **Predict the test horizon with the Stage-1 visits forecast:**
  ```python
  mlf.fit(train_df, prediction_intervals=PredictionIntervals(n_windows=3, h=12))
  preds = mlf.predict(h=24, X_df=visits_fcst_as_X, level=[80, 95])
  ```
  Conformal intervals give the regression a variability band comparable to StatsForecast.
- MLForecast's `predict(h=24)` **is** the recursive multi-step forecast natively (it feeds
  its own revenue predictions back into the revenue lags; visits come from `X_df`) — the
  realistic cold-start 2-year forecast Sandra cares about.

### Phase 4c — Ablation: univariate revenue model
Train the same `mlf` with **Group A + Group B features only** — drop the Group C visits
features (`visits_count`, `visits_lag_*`, `visits_roll_mean_3`) — and forecast the test
horizon. Report its metrics next to the exogenous model so the report
can state **whether visits actually improved the forecast** — if the lift is small,
recommend the simpler univariate model for the dashboard (fewer moving parts, no Stage-1
dependency).

### Phase 5 — StatsForecast classical models **[DECIDED SARIMA + AutoARIMA + AutoETS]**
```python
from statsforecast import StatsForecast
from statsforecast.models import ARIMA, AutoARIMA, AutoETS, SeasonalNaive

sf = StatsForecast(
    models=[
        # Explicit SARIMA(p,d,q)(P,D,Q)_12 — start here, tune orders (see below):
        ARIMA(order=(1, 1, 1), season_length=12, seasonal_order=(1, 1, 1),
              alias="SARIMA"),
        AutoARIMA(season_length=12),          # auto-selected seasonal ARIMA (also SARIMA)
        AutoETS(season_length=12),
        SeasonalNaive(season_length=12),      # baseline
    ],
    freq="MS",
)
sf.fit(train_df)
fcst = sf.predict(h=24, level=[80, 95])       # point + 80/95% intervals for every model
```
- **SARIMA orders:** the data has strong yearly seasonality on an upward trend
  (CONTEXT §4), so a seasonal difference (`D=1`, `season_length=12`) and a first
  difference (`d=1`) are the natural starting point. Confirm `d`/`D` with ADF +
  seasonal-strength checks; pick `p,q,P,Q` by AIC over a small grid (or read them off
  `AutoARIMA`'s chosen order and pin them). **Record the final
  `SARIMA(p,d,q)(P,D,Q)₁₂` in the report** — it is the interpretable classical model.
- **AutoARIMA** is the auto-tuned counterpart; report whether it lands on the same order
  as the hand-specified SARIMA (a good sanity check) and whether it beats it on test.
- Compute the same test metrics (§8) for SARIMA, AutoARIMA, and AutoETS. Record the ETS
  components (error/trend/seasonality) too.

### Phase 6 — Metrics (§8) on the test set → `data/eval/revenue_forecast/metrics.json`.
### Phase 7 — Plots (§9).
### Phase 8 — Report (§10).

---

## 8. Metrics (`data/forecast/metrics.py`)

Compute all on the **test set** for the chosen MLForecast model (exogenous), the
univariate ablation, SARIMA, AutoARIMA, and AutoETS. Store in `metrics.json`. Each gets a one-line business
interpretation in the report. Use `utilsforecast.losses` for the standard errors;
PSI/Gini/K2 are custom.

### 8.1 MSE (required)
**MSE (USD²)**, **RMSE (USD)**, and **RMSE/MSE as % of mean monthly test revenue**
(CONTEXT §3 — readable without translation). Also **MAE** and **MAPE**. Compute these for
the exogenous model, the univariate ablation (§7.4c), SARIMA, AutoARIMA, and AutoETS.

Additionally report the **Stage-1 visits forecast accuracy** (visits RMSE/MAPE vs actual
test visits). The revenue model inherits this error, so the report must acknowledge it
when interpreting the exogenous model's performance.

### 8.2 PSI — Population Stability Index (required)
PSI between the **training score distribution** and **test score distribution**
(predicted revenues), 10 quantile bins defined on training predictions:
`PSI = Σ (actual% − expected%) · ln(actual% / expected%)`. `<0.1` stable, `0.1–0.25`
moderate, `>0.25` significant. **Caveat:** CONTEXT §3 frames PSI as US/UK visit-mix
shift, but the data has no regional breakdown, so we measure model-score drift; a high
value here most likely reflects the 2024–25 revenue trend exceeding the training range,
not a clinic-mix change — say so.

### 8.3 Gini (required)
Normalized Gini for a continuous target (Kaggle-style): sort actuals by predicted value,
build the cumulative-actual curve, Gini = area vs the diagonal, normalized by a perfect
ordering (≡ `2·AUC − 1` in the ranking sense). Business meaning: a high Gini means the
model reliably **ranks** months low→high revenue — distinguishing a normal low-season
August from an atypical drop worth investigating (CONTEXT §3).

### 8.4 K2 Score — D'Agostino–Pearson normality test (required)
`scipy.stats.normaltest(residuals)` → **K² statistic** + p-value on test residuals
`(actual − predicted)`. High p (>0.05) → residuals plausibly normal → the prediction
intervals are trustworthy; low p → skewed/heavy-tailed errors, read intervals with
caution. Report both.

### 8.5 Additional suitable metrics (add these)
- **R²**, **sMAPE**, **directional accuracy** (correct up/down vs prior month),
  **prediction-interval coverage** (% of test actuals inside 80/95% bands — available for
  every model since MLForecast conformal intervals and StatsForecast both emit `level`),
  **Ljung–Box** on residuals (leftover autocorrelation the model missed).

---

## 9. Plots (`data/forecast/plotting.py` → `data/eval/revenue_forecast/figures/`)

Use `matplotlib.use("Agg")`, ≥150 dpi. `utilsforecast.plotting.plot_series` can jump-start
these but the combined overlay likely needs custom matplotlib.

1. **`predictions_combined.png`** — headline. Full 10-year x-axis: historical actual
   (2016–2023 solid), test actual (2024–2025 marker), and overlaid **test-window
   forecasts** from the chosen MLForecast model (exogenous), the univariate ablation,
   SARIMA, AutoARIMA, and AutoETS. Shade the intervals. Legend, USD (millions) axis,
   title. Optionally a small inset showing the Stage-1 visits forecast vs actual.
2. **`prediction_interval.png`** — CONTEXT deliverable: the chosen MLForecast model's
   test forecast with its **conformal 80/95% band** against the real 2024–2025 data,
   zoomed.
3. **`residual_diagnostics.png`** — residuals over time, residual histogram + normal
   overlay (visualizes K2), residual ACF.

---

## 10. Report (`data/eval/revenue_forecast/report.md`) — **[DECIDED] markdown + embedded PNGs**

1. **Executive summary** — can we predict monthly revenue? Numbers-first, for Sandra.
2. **Data & cleaning** — cleaning, the 8/2 split, the exogenous-visits / leakage decision
   (§1.1: why `avg_revenue_per_visit` is out and why visits must be forecast), row counts.
3. **Regression model (MLForecast)** — the two-stage design (visits forecast → revenue),
   RF vs XGBoost and the rolling-origin CV evidence, which features dominate (does
   `visits_count` / `lag_12` / `month` recover Oct–Dec up / Jul–Aug down?), the recursive
   2-year forecast, the **Stage-1 visits accuracy** it inherits, and the **ablation
   verdict**: did exogenous visits beat the univariate model, and by enough to justify the
   extra pipeline stage?
4. **Classical models (StatsForecast)** — the chosen `SARIMA(p,d,q)(P,D,Q)₁₂` order and
   why, whether AutoARIMA agreed, AutoETS components, which forecasts the test years
   better, all vs SeasonalNaive.
5. **Predictions plot** — embed `predictions_combined.png` + `prediction_interval.png`.
6. **Evaluation metrics** — table of MSE/RMSE (USD & %), PSI, Gini, K2 + §8.5 extras,
   each with a plain-English interpretation; state the PSI caveat and the K2 implication
   for intervals.
7. **Recommendation** — which model HealthCore should put behind the dashboard, the
   honest recursive 2-year accuracy, and limitations (120 points, trend extrapolation,
   no regional data).

---

## 11. Unit Tests (`tests/pipelines/`) — required deliverable

These live in the **existing** `tests/pipelines/` dir (alongside `test_pipeline.py`) and
are collected by the repo's pytest config (`testpaths` includes `tests`, `pythonpath`
includes `.`). Match the repo's test style: `from __future__ import annotations`, type
hints, docstrings, plain `pytest`, pandas frames. Import through the real pipeline
functions (`from data.forecast.clean import ...`, `from data.forecast.features import
FEATURE_COLUMNS`); don't duplicate logic.

### `test_revenue_split.py` — validates the 8/2-year split
- Train 96 rows, test 24 rows.
- `train.ds.max() == 2023-12-01`, `test.ds.min() == 2024-01-01`,
  `train.ds.max() < test.ds.min()`.
- No `ds` in both sets; union covers `2016-01…2025-12` with no gap.

### `test_revenue_no_leakage.py` — verifies no data leakage
- **Fit on train only:** the MLForecast/StatsForecast `.fit()` receives only rows with
  `ds <= 2023-12-01`; assert no `ds >= 2024-01-01` reaches `fit`.
- **Transforms learned from train only:** the `LocalStandardScaler`/`Differences` stats
  come from the training window — assert forecasts for the test horizon don't change when
  test-period `y` values are altered (they're never passed to `fit`).
- **Feature catalog matches spec:** assert the model's feature columns equal
  `features.FEATURE_COLUMNS` (Groups A–C of §5.2) — no missing or unexpected features.
- **`avg_revenue_per_visit` never used:** assert it is absent from `FEATURE_COLUMNS`,
  every modeling frame, and every `X_df` (it would reconstruct the target with visits).
- **Exogenous visits are forecasted, not actual:** assert the `X_df` passed to
  `mlf.predict` for the test horizon equals the Stage-1 visits *forecast* and is **not**
  equal to `test_df.visits_count`; assert the revenue forecast is unchanged when
  `test_df.visits_count` is perturbed (the actual test visits never touch prediction).
- **CV windows are causal:** `cross_validation` cutoffs are strictly increasing and each
  fold's training portion ends before its horizon starts (no future in a fold).

### `test_revenue_data_validation.py`
- Exactly 120 consolidated rows after cleaning; all `y > 0`; no missing months.
- Inject a synthetic null/empty row and assert cleaning drops it.

---

## 12. Suggested Additional Work (do these — they materially improve the outcome)

1. **Rolling-origin backtest across several origins** (`n_windows=4–6`) reported for
   every model — stability, not a single split. Nixtla's `cross_validation` makes this
   one call.
2. **`AutoTheta` and `AutoCES`** added to the StatsForecast model list — near-free extra
   baselines that often beat ARIMA on seasonal monthly data.
3. **Perfect-foresight visits check (diagnostic only):** as an upper-bound diagnostic —
   **not** a reportable model — run the revenue model once with *actual* test visits in
   `X_df` to see the ceiling if visits were known perfectly. This isolates how much of the
   exogenous model's error comes from the Stage-1 visits forecast vs the revenue mapping.
   Clearly label it as leakage-for-diagnosis; it must not appear in the headline metrics.
4. **Log target transform:** add a log/`boxcox` step to `target_transforms` to tame the
   multiplicative growth; compare MAPE.
5. **Conformal coverage tuning** — check the 80/95% MLForecast intervals actually cover
   ~80/95% of test points; report the miscoverage.
6. **Feature importance / SHAP** on the winning MLForecast learner to confirm it leans on
   `lag_12` + `month` (ties back to CONTEXT §4).
7. **Drift-monitor stub** — a function that recomputes PSI on any new month batch so the
   eventual dashboard can alarm on shift.
8. **Pattern-recovery assertion test** — AutoARIMA/AutoETS seasonal factors lowest in
   Jul–Aug, highest in Oct–Dec.

---

## 13. Alternative Models (evaluate and document; implement only where noted)

- **Within StatsForecast (cheap, worth implementing):** `AutoTheta`, `AutoCES`, `MSTL`
  (if multiple seasonalities emerge). All share the same `.fit/.predict` API.
- **Within MLForecast:** swap in `LightGBM`, `ElasticNet`, or `HistGradientBoosting` as
  additional learners in the same `models={...}` dict — a linear learner on lag/date
  features is a strong, humbling baseline on 84 rows and is *worth implementing*.
- **NeuralForecast (mention, do not implement):** `NHITS`, `NBEATS`, TFT — 120 monthly
  points is far too little data; note this and move on.
- **TimeGPT (out of scope):** Nixtla's hosted foundation model would be a useful zero-shot
  comparison, but it needs an API key and sends the series to Nixtla's servers. Dropped to
  keep the pipeline local and key-free; mention as possible future work only.

Recommendation to encode: for a 120-point monthly series with clean seasonality, the
right altitude is **StatsForecast classical models + an MLForecast tree on lag/calendar
features**; deep models are not justified.

---

## 14. Development Workflow

```bash
# from the repo root (chitrasharath_healthcore_ft_ai_1/)
# one-time
uv sync --group forecast

# full pipeline (regenerates processed data, models, metrics, figures) — runs fully offline
uv run python scripts/train_revenue_forecast.py

# quality gate before committing (repo pytest collects tests/ from root)
uv run pytest tests/pipelines/ -v
```

`scripts/train_revenue_forecast.py` must be **idempotent and deterministic** (seed
everything with 42) — same inputs → identical `metrics.json` and figures. The intermediate
artifacts (`data/process/healthcore_sales_clean.parquet`, `data/process/models/*.pkl`) are
regenerated and need not be committed; the report and its figures under
`data/eval/revenue_forecast/` **are** committed so `report.md` renders on GitHub.

---

## 15. Open Questions for the Implementer

Proceed with the stated defaults unless the human says otherwise; surface these in the
report if an assumption bites:

1. **PSI target.** Defaulting to PSI on the model score distribution (no regional data
   for the CONTEXT's visit-mix framing). Confirm acceptable.
2. **Exogenous visits.** Default: **included** via the two-stage design (forecast visits →
   feed to revenue model), with a univariate ablation for comparison. If the ablation shows
   visits add little, the report may recommend the simpler univariate model — confirm that
   trade-off is acceptable, or state a hard preference for one.
3. **Log transform.** Default off for the required deliverable, on as the §12.4
   enhancement. Confirm if it should be the default given multiplicative growth.
