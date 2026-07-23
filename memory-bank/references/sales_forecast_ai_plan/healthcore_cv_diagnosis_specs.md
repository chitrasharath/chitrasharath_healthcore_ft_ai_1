# HealthCore — Temporal Cross-Validation & Fit Diagnosis

> **Spec for a coding agent.** Read end to end before coding. This extends the existing
> revenue forecaster on branch **`feature/sales_forecast`** of the HealthCore monorepo
> (`chitrasharath_healthcore_ft_ai_1/`). It does **not** re-implement the models — it
> validates the cross-validation strategy, diagnoses model fit, and produces a report +
> tests. Decisions already made by the human are marked **[DECIDED]**; empirical calls
> you must make and document are **[YOU DECIDE — document it]**.
>
> **[DECIDED] Work on a new branch `feature/eval_metrics`, cut from `feature/sales_forecast`
> (not `main`).** All changes land there; the PR base is `feature/sales_forecast`. See §15.

---

## 1. Project Overview

The revenue forecaster is already built (see `data/forecast/` on `feature/sales_forecast`):
a two-stage MLForecast regression (visits → revenue) plus StatsForecast classical models
(SARIMA/AutoARIMA/AutoETS/AutoTheta/SeasonalNaive), trained on 2016–2023 and tested on
2024–2025. This task is a **validation and diagnosis pass** on that work.

The current pipeline selects learners with **rolling-origin CV of only `n_windows=3`**
(`cross_validation_select` in `data/forecast/models_mlforecast.py`). The assignment
requires **≥5 folds**, a per-fold spread (mean ± std), a learning-curve-based over/under-fit
diagnosis, and a test that proves the folds never break chronological order.

**Two models are in scope [DECIDED]:** the univariate regression **`MLForecast_uni` (rf)**
and the best classical model **`AutoETS`**. (The `MLForecast_exog` model is *not* diagnosed
here — prior analysis showed its "visits help" edge is within noise; see §13.)

**CV engine per model [DECIDED]:** the Random Forest is validated with **sklearn
`TimeSeriesSplit`** (on a causal feature matrix), and AutoETS with **Nixtla
`StatsForecast.cross_validation`**. Each uses the splitter native to its ecosystem; both
use **5 folds × 6-month blocks** so the per-fold metric is comparable across the two.

### 1.1 What must be true when this is done

- Cross-validation runs on **≥5 folds** and the code/report **confirm** it.
- **No fold shuffles or mixes time**: within and across folds, training months strictly
  precede validation months; validation blocks are contiguous and move forward in time.
- The **chosen metric (RMSE)** is reported as **mean ± std across the 5 folds**, for both
  in-scope models.
- A **learning curve** (train vs validation error over growing training size) exists for
  both models, saved as PNG.
- **MAE and RMSE** are computed for **training and validation**, both models.
- The report **justifies MAE vs RMSE** as the business-cost metric, grounded in
  `rag_assignments/CONTEXT-healthcore.en.md` §3 (the sales-prediction context — **not** the
  repo's website-milestone `CONTEXT.md`).
- The report **classifies each model** as **well-fitted / underfitting / overfitting**,
  backed by the learning curve *and* the CV spread, and proposes **corrective action
  consistent with the diagnosis**.
- A unit test in `tests/pipelines/` proves the temporal CV preserves chronological order
  within each fold.

---

## 2. Tech Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python **3.12+** | Repo `requires-python`. |
| Env / deps | `uv` workspace | Reuse the root `forecast` dependency-group; no new deps expected (§6). |
| Data / models | `pandas`, `numpy`, `mlforecast`, `statsforecast`, `utilsforecast` | Already installed on the branch. |
| CV — Random Forest | **`sklearn.model_selection.TimeSeriesSplit`** on a causal feature matrix | §5.1a. Explicit `train_idx`/`test_idx`; you own the per-fold feature build. |
| CV — AutoETS | reuse existing **`classical_backtest`** (`StatsForecast.cross_validation`) | §5.1b. Already 5-fold; call with `h=6`. AutoETS is not an sklearn estimator. |
| Learning curve | small custom expanding-window splitter (fixed validation block) | §7.3. |
| Metrics | `utilsforecast.losses` (`rmse`, `mae`) | Same as the existing pipeline. |
| Plotting | `matplotlib` (`Agg`) | Learning-curve PNGs. |
| Tests | `pytest` | `tests/pipelines/`. |
| Report | Markdown + embedded PNGs | §10. |

Seed everything with `random_state=42` (as the existing code does) so folds and curves
are reproducible.

---

## 3. Repository Structure

Work inside the existing monorepo (branch `feature/sales_forecast`). Reuse existing
modules; add the marked new files.

```
data/forecast/
  models_mlforecast.py        # EDIT: bump default n_windows 3 → 5, expose h; keep signatures back-compatible
  models_statsforecast.py     # reuse (AutoETS fit/forecast)
  diagnostics.py              # NEW: per-model temporal CV (RF→TimeSeriesSplit, ETS→StatsForecast CV), causal feature-matrix builder for RF, learning curve, train/val MAE+RMSE, fit classification
scripts/
  train_revenue_forecast.py   # EDIT: after training, call diagnostics; write artifacts (or add run_diagnostics.py — §7.6)
tests/pipelines/
  test_temporal_cv_order.py   # NEW: folds preserve chronological order (required deliverable)
data/eval/revenue_forecast/
  diagnostics/
    cv_folds.json             # NEW: per-fold RMSE/MAE, mean±std, fold cutoffs, n_windows, h
    learning_curve_mlforecast_uni.png   # NEW
    learning_curve_autoets.png          # NEW
    learning_curve.json       # NEW: raw train/val MAE+RMSE per training size
  cv_fit_diagnosis_report.md  # NEW: the report (§10)
```

Do not create a `src/` dir or a second `pyproject.toml` — this repo resolves root
packages via `pythonpath = ["."]` and manages deps in the root `pyproject.toml`.

---

## 4. Baseline: what the code does today (verify, then change)

From `data/forecast/models_mlforecast.py` on the branch:
- `cross_validation_select(train_df, *, include_visits=True, n_windows=3, h=12)` runs
  `mlf.cross_validation(prepared, n_windows=3, h=12, step_size=12, static_features=[])`
  and picks the learner by **mean RMSE** (tie-break MAE, then simplicity).
- `light_param_sweep(...)` and `_attach_residual_intervals(...)` also use `n_windows=3`.
- The CV metric captured is **RMSE (primary) and MAE**.
- The winning RF params live in `data/eval/revenue_forecast/metrics.json` under
  `mlforecast_cv_exog.sweep.best_params` (`n_estimators=200, max_depth=null,
  max_features=1.0`) — read these for the RF diagnostic (§5.1a).

From `data/forecast/models_statsforecast.py`:
- `classical_backtest(train_df, *, n_windows=5, h=12)` **already runs 5-fold** rolling-origin
  CV for the classical models — reuse it for the AutoETS diagnostic (§5.1b) with `h=6`.

**Finding to state explicitly in the report:** the **MLForecast learner-selection** CV used
**3 folds, not 5** (the classical backtest was already 5). This task raises the MLForecast
selection CV to **≥5** and re-runs selection so the diagnosis reflects the ≥5-fold result.

---

## 5. Cross-Validation Requirements

### 5.1 Fold configuration — **[DECIDED] 5 folds, 6-month blocks, non-overlapping**

Both models use **5 folds** with a **6-month validation block** each, non-overlapping, over
the **training window only** (2016–2023). Rationale to record: 5 × 12-month non-overlapping
folds don't fit the 96-month window after `Differences([12])` + `lag_12` consume ~24 months;
overlapping folds understate the std. `n_windows=6, h=6` is the sanctioned alternative if a
tighter std is wanted. **Assert ≥5 folds** in code and report the actual count + each fold's
boundary.

**Define the five validation windows by date first** (gotcha #4). Compute the five
6-month `ds` blocks (the last 30 usable months of the training window) as the single source
of truth, then configure *both* engines to those exact blocks and **assert the per-fold date
boundaries match** across engines before scoring. Do not rely on `TimeSeriesSplit`'s integer
positions (~72–84 rows after dropping `lag_12` NaNs) and `StatsForecast`'s 96-row series
landing on the same months by coincidence — they won't unless you pin the dates.

#### 5.1a Random Forest → `sklearn.model_selection.TimeSeriesSplit`

The RF is pulled out of the MLForecast wrapper and validated directly, because sklearn's
splitter gives explicit `train_idx`/`test_idx` (a clean, inspectable temporal-order test).
**You now own the feature causality that MLForecast handled internally** — do it correctly:

- **Build a causal feature matrix** from `data/forecast/features.py` (`add_engineered_features`
  / `FEATURE_COLUMNS`). Those features already use `.shift()`, so each row `t` depends only
  on data `≤ t-1` — a globally-computed matrix is therefore causal per row. Sort by `ds`,
  drop the initial rows lacking `lag_12`.
- **Target transform per fold, not globally.** The shipped `MLForecast_uni` uses
  `Differences([12])` + `LocalStandardScaler`. To diagnose the *same* model, apply seasonal
  differencing/scaling **fit on the training fold only** and invert for scoring. (Scaling is
  a no-op for trees — say so; `Differences([12])` is what matters and must be fold-local.)
- **Split:** `TimeSeriesSplit(n_splits=5, test_size=6, gap=0)` over the ordered matrix →
  five expanding-train / 6-month-test folds ending at the training window's tail.
  `random_state=42`. Verify the resulting test blocks equal the date-defined windows (§5.1).
- **Use the *actual* shipped RF hyperparameters — read them, don't hardcode.** The base
  learner in `models_mlforecast.py` is `RandomForestRegressor(n_estimators=300, …)`, but the
  CV sweep overrode it (the `mlforecast_cv_exog.sweep.best_params` in
  `data/eval/revenue_forecast/metrics.json` was `{n_estimators: 200, max_depth: null,
  max_features: 1.0}`). Load the winning params from `metrics.json` (or re-derive them via
  the pipeline) so the diagnosed RF is the one that actually shipped — and state which
  params were used in the report.
- **Predict the 6-month block recursively, not in one shot (gotcha #3).** Do **not** call
  `rf.predict(X[test_idx])` on the whole block — its lag features hold the *actual* revenue
  of earlier validation months, which real forecasting wouldn't know, making the score
  optimistic. Instead **roll month-by-month within the fold**: predict month 1, substitute
  that prediction into the lag/rolling features for month 2, re-predict, and so on for all 6
  months. This mirrors `MLForecast.predict(h=6)` and keeps the RF comparable to AutoETS's
  genuine 6-month forecast. (Feature rows for the recursion are rebuilt from the training
  tail + the model's own predictions — never from validation actuals.)
- **Embargo:** with recursive prediction and `.shift()` features no `gap` is strictly
  required, but `gap=1` is a defensible belt-and-suspenders — note if used.

#### 5.1b AutoETS → `StatsForecast.cross_validation` (reuse `classical_backtest`)

- **Reuse the existing helper**, don't write a fresh call: `models_statsforecast.py` already
  has `classical_backtest(train_df, *, n_windows=5, h=12)` doing rolling-origin
  `sf.cross_validation(h=h, step_size=h, n_windows=n_windows)`. Call it with **`h=6,
  n_windows=5`** (add/override the `step_size=6` and, if needed, narrow the model list to
  `AutoETS`) so the AutoETS fold structure matches the RF's 6-month blocks. Note: the
  classical side is **already at 5 folds** — only the MLForecast *selection* CV (§7 Phase 1)
  is stuck at 3.
- AutoETS runs on the raw revenue series (handles trend/seasonality internally — no
  differencing/scaling of its input). The output carries a `cutoff` column per fold.

### 5.2 Chronological integrity (the core requirement)

Both engines must be **proven and reported** to preserve time order:
- **RF / TimeSeriesSplit:** for every fold, `max(ds[train_idx]) < min(ds[test_idx])`; test
  indices are strictly increasing, contiguous, and later than all train indices; the five
  test blocks don't overlap; folds roll forward. `TimeSeriesSplit` never shuffles — state it.
- **AutoETS / StatsForecast CV:** fold `cutoff`s are strictly increasing and spaced by
  `step_size`; every validation `ds` > its `cutoff`; each fold's validation `ds` are
  contiguous months immediately after the cutoff. No `shuffle` anywhere.
- **Both:** the five validation blocks map to the **same calendar months** across the two
  engines (alignment check), so their per-fold RMSEs are comparable.

### 5.3 Report the chosen metric as mean ± std

- **Chosen metric = RMSE** (justified in §9 as the business-cost metric). Compute per-fold
  RMSE for each in-scope model, then report **mean ± std across the 5 folds** (e.g.
  `RMSE = $X ± $Y`). Report MAE mean ± std alongside.
- Because folds are few (5), also report the **min/max** per fold and note that the std is
  a small-sample estimate.

### 5.4 Correctness rules (the RF-via-`TimeSeriesSplit` gotchas) — do all of these

These are the traps introduced by validating the RF outside MLForecast. The chosen approach
for each is mandatory, not optional:

| # | Gotcha | Chosen approach |
|---|---|---|
| 1 | Self-built feature matrix can leak the future | Use `features.py` `.shift()`-based builder; each row uses only data `≤ t-1`; assert no feature equals the same-month target |
| 2 | Global target transform sees validation | Fit `Differences([12])` (+ scaler, a tree no-op) **per fold on train rows only**; invert for scoring |
| 3 | One-shot block prediction peeks at within-block actuals | **Recursive** month-by-month prediction inside each fold (feed predictions back into lags); mirrors `predict(h=6)` |
| 4 | Index-based vs date-based folds misalign the two engines | **Define the 5 windows by date first**; configure both engines to them; assert boundaries match |
| 5 | RF train error ≈ 0 misread as "good fit" | Interpret the **val − train gap**, not the absolute; state that near-zero RF train error *is* the overfit signature; don't compare RF vs AutoETS train error directly |
| 6 | Trees can't extrapolate the upward trend | Keep `Differences([12])` so the RF models a detrended series (matches the shipped model); if diagnosing raw-revenue RF instead, label the bias as trend-extrapolation, not underfitting |

Rules 1–4 are correctness (a violation makes the numbers wrong); rules 5–6 are
interpretation (a violation makes the *diagnosis* wrong). The report must show it honored 5–6.

---

## 6. Dependencies

No new dependencies expected — `mlforecast`, `statsforecast`, `utilsforecast`,
`matplotlib`, `scikit-learn`, `numpy`, `pandas` are already in the root `forecast`
dependency-group. Setup, from the repo root:

```bash
uv sync --group forecast
```

If any helper (e.g. `scipy.stats.t` for a CI on the fold mean) is needed and missing, add
it to the root `forecast` group — do not touch `services/api`.

---

## 7. Implementation

### Phase 0 — Confirm the baseline
Load `feature/sales_forecast`, run the existing pipeline once, and record that CV was
`n_windows=3`. This is the "before" the report contrasts against.

### Phase 1 — Raise the pipeline's selection CV to ≥5 folds
Separate from the diagnostic below, the shipped **model-selection** CV must also satisfy
"≥5 folds." In `models_mlforecast.py`, change the **defaults** of `cross_validation_select`,
`light_param_sweep` (and the interval helper where sensible) to `n_windows=5, h=6,
step_size=6`, keeping parameters overridable and signatures back-compatible. This selection
CV stays **MLForecast-native** (it must regenerate features per fold to compare rf/xgb/
elasticnet safely — sklearn's splitter is not used here). Re-run
`scripts/train_revenue_forecast.py` so `metrics.json` reflects 5-fold selection; note in the
report whether the winner changed vs the 3-fold run.

### Phase 2 — `diagnostics.py`: temporal 5-fold CV, per-model engine
Run the diagnostic CV on the **training window only** (2016–2023), 5 folds × 6-month blocks,
using the engine chosen per model (§5.1):

- **`MLForecast_uni` (rf) → `TimeSeriesSplit` (§5.1a).** Build the causal feature matrix,
  apply the fold-local target transform, split with `TimeSeriesSplit(n_splits=5,
  test_size=6)`, fit the shipped RF on `train_idx`, and **predict the 6-month block
  recursively** (§5.1a gotcha #3). Honor all of §5.4.
- **`AutoETS` → reuse `classical_backtest` (§5.1b).** Call with `n_windows=5, h=6`
  (override `step_size=6`); the classical helper is already 5-fold.
- Collect **per-fold train and validation** MAE and RMSE for both:
  - **Validation error** = error on that fold's held-out 6 months.
  - **Training error** = the fitted model's error on its own training rows (in-sample) —
    for RF, predict on `X[train_idx]`; for AutoETS, in-sample fitted values for the fold.
- **Align the five blocks by calendar month** across the two engines and assert they match.
- Emit `cv_folds.json`: per model — `engine`, `n_splits/n_windows`, `test_size/h`, each
  fold's date range, per-fold train/val MAE+RMSE, and **mean ± std** (plus min/max).

### Phase 3 — Learning curve — **[DECIDED] expanding window, vary training size**
Construct a proper learning curve to expose bias vs variance:
- **Fixed validation block:** hold out the **last 12 months of the training window**
  (2023-01…2023-12) as a fixed validation set. (It stays out of every training prefix, and
  every prefix precedes it in time — chronology preserved.)
- **Growing training prefixes:** train on the first `s` months for
  `s ∈ {36, 48, 60, 72}` (all ending before 2023-01). For each `s`:
  - fit the model on the prefix,
  - **training error** = MAE/RMSE on the prefix (in-sample),
  - **validation error** = MAE/RMSE forecasting the fixed 12-month block.
- Plot **train vs validation MAE and RMSE against training size** for each model →
  `learning_curve_mlforecast_uni.png`, `learning_curve_autoets.png`. Save the raw numbers
  to `learning_curve.json`.
- Note that the smallest prefixes (~36 months, ~12 usable after transforms) are noisy —
  say so rather than over-reading them.

### Phase 4 — Fit classification **[YOU DECIDE — document from the numbers]**
Classify each model from the learning curve **and** the CV spread:
- **Underfitting (high bias):** train and validation errors both high and close together;
  curve plateaus high; adding data doesn't help.
- **Overfitting (high variance):** low/near-zero training error, much higher validation
  error, a persistent gap; high fold-to-fold std.
- **Well-fitted:** train and validation errors both low and converging; small gap; low std.

Likely (confirm empirically): a `max_depth=None` Random Forest on ~84 rows tends to
memorize training (train RMSE ≈ 0) while validation RMSE ≈ $100k — i.e. **overfitting /
high variance**; **AutoETS** (few parameters, R² ≈ 0.92, good interval coverage) tends to
sit **well-fitted**. Do not assume — read it off the actual curves and folds, and quote
the numbers.

**Interpretation guardrails (gotchas #5, #6):** RF's near-zero training error is the
*overfitting signature*, not a data bug — diagnose on the **val − train gap**, and don't
compare RF's ~0 training error against AutoETS's genuine in-sample residuals as if they were
the same quantity. If (per open question 1b) the RF is diagnosed on raw revenue without
`Differences([12])`, any large flat bias is **trend-extrapolation** (trees can't predict
above their training range), not signal underfitting — label it as such.

### Phase 5 — Corrective actions (must match the diagnosis) — §11.

### Phase 6 — Wire-up & artifacts
Either extend `scripts/train_revenue_forecast.py` to call `diagnostics.run_all()` at the
end, or add `scripts/run_diagnostics.py` that imports the trained artifacts. Deterministic
reruns (seed 42) → identical `cv_folds.json`, `learning_curve.json`, and PNGs.

---

## 8. Metrics: MAE & RMSE, train & validation

For both models, both stages (train, validation), report **MAE** and **RMSE**:
- **MAE** — mean absolute error, in plain USD; the average miss.
- **RMSE** — root mean squared error, in USD; penalizes large misses more than small ones.
- **RMSE as % of average monthly revenue** — the interpretability framing CONTEXT §3 asks
  for (it requests MSE "as a percentage of average monthly revenue"); include it so the
  business-cost number reads without translation.
Report validation numbers as the 5-fold **mean ± std** (§5.3); report training numbers the
same way (per-fold in-sample). Keep everything in USD so Tom/Sandra can read it.

---

## 9. Which metric reflects business cost? (must be justified from CONTEXT)

The report must pick one and argue it from the context file, not in the abstract. The
authoritative context is **`rag_assignments/CONTEXT-healthcore.en.md`** (the sales-prediction
context) — **not** the repo's `CONTEXT.md`, which covers the website/patient-form milestone
and says nothing about forecasting metrics. Ground each point in it:
- **CONTEXT §3** names the metrics that matter: it asks to *"report MSE in USD², and also as
  a percentage of average monthly revenue"*, and prizes a high **Gini** to *"distinguish a
  normal low-season month … from an atypical drop."* Both signals say the business cares
  about **large, unusual deviations**, not just average error. (CONTEXT §6 lists MSE among
  the four required metrics; MAE and RMSE are not named there — they enter via this task.)
- **RMSE is the business-cost metric.** It is the square root of the MSE the context already
  asks for, in interpretable dollars, and it **penalizes large errors disproportionately** —
  matching the cost of a big, planning-breaking revenue miss (over/under-staffing,
  misinformed executive decisions). A single $500k miss is *worse than* ten $50k misses to
  the business; RMSE reflects that, MAE treats them as equal.
- **Also report RMSE as a % of average monthly revenue** — the exact interpretability framing
  CONTEXT §3 requests for the MSE family, so Tom and Sandra read it without translation.
- **MAE** is the intuitive "average dollars off" and should be **reported alongside** for
  interpretability — but the **business-cost metric is RMSE**.
State this conclusion explicitly and quote the specific CONTEXT §3 lines.

---

## 10. Report (`data/eval/revenue_forecast/cv_fit_diagnosis_report.md`)

Markdown + embedded PNGs. Structure:
1. **Summary** — for each model: fit verdict (well-fit / under / over), the CV
   `RMSE = mean ± std`, and the one-line corrective action.
2. **CV setup & integrity** — confirm ≥5 folds (state the count), the 5×6 non-overlapping
   design and why, and the chronological-integrity evidence (fold cutoffs, "no shuffle").
   Note the change from the shipped 3-fold CV and whether the winner changed.
3. **Metrics table** — train & validation MAE and RMSE (mean ± std) for both models.
4. **Learning curves** — embed both PNGs; read each one (gap, plateau, convergence).
5. **Business-cost metric** — the MAE-vs-RMSE justification (§9), tied to CONTEXT.
6. **Fit diagnosis** — the explicit classification per model, backed by *both* the learning
   curve and the CV spread (not one or the other). Include the §5.4 interpretation
   guardrails: state that RF's ~0 training error is the overfit signature (read the gap),
   and that RF and AutoETS training errors aren't directly comparable.
7. **Method note** — one short paragraph confirming the §5.4 correctness rules were honored:
   causal features, per-fold transforms, **recursive** within-fold RF prediction, date-aligned
   folds. This is what makes the RF-vs-AutoETS comparison fair.
8. **Corrective actions** — §11, matched to each diagnosis.
9. **Limitations** — 120 monthly points, ~84 effective training rows, 6-month CV horizon,
   small-sample std.

---

## 11. Corrective actions (must be consistent with the diagnosis)

Propose only actions that match what the numbers show. Reference set:
- **If overfitting (expected for RF):** constrain the trees — set `max_depth`
  (e.g. 3–5), raise `min_samples_leaf`, `max_features < 1.0`, fewer estimators; **prune
  the feature set** (20 features on ~84 rows — drop redundant lags/rollings); prefer a
  **more regularized learner** (the `elasticnet` already in the learner set) or lean on the
  **classical AutoETS**, which has far fewer parameters; add drift monitoring (PSI) since
  variance is the issue. "Get more data" is not available (fixed 120 months) — say so.
- **If underfitting:** add capacity/features (richer lags, interactions), reduce
  over-aggressive regularization, extend training history.
- **If well-fitted (expected for AutoETS):** ship it; keep the CV/learning-curve as a
  regression guard; monitor PSI for drift; revisit only if new data shifts the regime.

---

## 12. Unit Test (`tests/pipelines/test_temporal_cv_order.py`) — required deliverable

Match the repo's test style (`from __future__ import annotations`, typed, docstrings,
import from `data.forecast.*`). Load through real pipeline functions
(`clean_sales`, `load_raw`, `split_train_test`, `prepare_frame`, the diagnostics splitter).

Assert **both** CV engines preserve chronological order within each fold. Cover them in the
same file so the "temporal CV strategy" is validated as a whole.

**Random Forest / `TimeSeriesSplit`:**
- **≥5 folds:** the splitter yields `n_splits >= 5` folds over the causal feature matrix.
- **Train precedes validation, every fold:** for each `(train_idx, test_idx)`,
  `ds[train_idx].max() < ds[test_idx].min()` and every train index < every test index.
- **No shuffle / contiguous validation:** each fold's `test_idx` maps to strictly
  increasing, monthly-contiguous `ds` (no gaps, no reordering).
- **Folds roll forward, no overlap:** successive folds' test blocks advance in time and
  don't share a `ds`.

**AutoETS / `StatsForecast.cross_validation`:**
- **≥5 folds:** produces `n_windows >= 5` distinct `cutoff`s, strictly increasing, spaced by
  `step_size`.
- **Train precedes validation:** every validation `ds` > its `cutoff`; each fold's
  validation `ds` are contiguous months immediately after the cutoff.

**Both:**
- **Aligned blocks:** the five validation windows cover the **same calendar months** across
  the two engines.
- **Determinism:** running each splitter twice yields identical fold boundaries (no random
  sampling anywhere).
- **Negative control:** shuffle a copy of the frame and assert the RF path either sorts by
  `ds` first (so folds stay ordered) or the order assertions would fail — guards against a
  future regression that forgets to sort. (Confirm `TimeSeriesSplit` is never constructed
  with, and the pipeline never calls, a shuffling splitter such as `KFold(shuffle=True)`.)

---

## 13. Suggested Additional Work (do these — they strengthen the diagnosis)

1. **Purged CV gap:** insert a 1-period embargo between each fold's train and validation so
   `lag_12`/rolling features straddling the boundary can't leak. Report whether it moves
   the numbers.
2. **Nested CV for the sweep:** the current `light_param_sweep` tunes on the same CV it
   scores on (optimistic). Wrap tuning in an inner CV so the reported validation error is
   honest.
3. **Fold distribution, not just mean ± std:** add a per-fold RMSE boxplot/strip plot; with
   5 folds the shape matters.
4. **t-based CI on the fold mean:** report a 95% CI using `t(df=4)` given only 5 folds.
5. **SeasonalNaive-in-CV:** compute the baseline per fold too, so the CV RMSE is
   contextualized (skill vs naive within each fold).
6. **Seed stability:** re-run RF CV over a few seeds; report the spread — part of the
   variance story for the overfitting diagnosis.
7. **Learning curve for the exog model** as a side check on whether visits change the
   bias/variance picture (ties to the earlier "visits barely help" finding).

---

## 14. Alternative Models (evaluate/mention; implement where cheap)

Given the likely **overfitting** verdict on the RF, the useful alternatives all reduce
variance:
- **Regularized linear (ElasticNet)** on the same features — already a learner in the set;
  promote it and compare its learning curve (should show a smaller train/val gap).
- **HistGradientBoosting / LightGBM with early stopping and shallow depth** — lower
  variance than an unconstrained RF; cheap to add inside MLForecast's `models={}`.
- **AutoETS / AutoTheta (classical)** — few parameters, naturally well-regularized on short
  series; AutoETS is already in scope.
- **Simple seasonal linear model** (month dummies + trend) — a high-bias/low-variance
  anchor that makes the over/under-fit contrast legible.
- **Mention, don't implement:** NeuralForecast (NHITS/NBEATS) — 120 points is far too few;
  it would overfit harder, not less.

---

## 15. Development Workflow

**[DECIDED] Branch:** do **all** of this work on a new branch **`feature/eval_metrics`**,
cut from **`feature/sales_forecast`** (not from `main`). Every change — the diagnostics
module, the CV bump, the test, the report, the artifacts — lands on that branch. Open the
PR against `feature/sales_forecast` as the base.

```bash
# from the repo root (chitrasharath_healthcore_ft_ai_1/)
git checkout feature/sales_forecast
git pull                                              # ensure up to date
git checkout -b feature/eval_metrics                  # branch off sales_forecast
uv sync --group forecast

# re-run training with ≥5-fold CV, then diagnostics
uv run python scripts/train_revenue_forecast.py       # now n_windows=5
uv run python scripts/run_diagnostics.py              # or diagnostics called at end of training

# required gate
uv run pytest tests/pipelines/test_temporal_cv_order.py -v
uv run pytest tests/pipelines/ -v                     # full suite still green

# commit on feature/eval_metrics; open PR with base = feature/sales_forecast
```

Deterministic reruns (seed 42) must reproduce `cv_folds.json`, `learning_curve.json`, and
the PNGs byte-for-byte where matplotlib allows. Commit the report and PNGs under
`data/eval/revenue_forecast/`; regenerated model `.pkl`s need not be committed.

---

## 16. Constraints

- **Branch:** all work on **`feature/eval_metrics`**, cut from **`feature/sales_forecast`**;
  PR base is `feature/sales_forecast` (§15). Do not commit to `feature/sales_forecast` or
  `main` directly.
- **Fixed data:** 120 monthly rows; ~84 effective training rows after `Differences([12])`
  + `lag_12`. "More data" is not a lever — corrective actions must respect this.
- **Chronology is sacred:** no shuffling, no random K-fold, no future-into-past anywhere in
  CV or the learning curve. This is the whole point of the task. For the RF `TimeSeriesSplit`
  path specifically, **you own feature causality** — build lags/rolling with `.shift()` and
  fit the seasonal-difference/scaler transform **per fold on train only**, or the diagnosis
  is on a leaky model.
- **Don't regress the shipped pipeline:** changing `n_windows` must keep function
  signatures back-compatible and the existing `tests/pipelines/` suite green.
- **Local & offline:** no external services or API keys (consistent with the branch).
- **Aggregate revenue only:** no PHI; nothing new touches patient-level data.

---

## 17. Open Questions for the Implementer

Proceed with the defaults unless told otherwise; surface these in the report if they bite:
1. **Fold config.** Default 5 × 6mo non-overlapping (§5.1). Switch to 6 × 6mo if a tighter
   std is preferred — confirm.
1b. **RF diagnostic faithfulness [RESOLVED — default].** The RF is diagnosed faithfully to
   the shipped model: causal feature matrix, `Differences([12])` applied **per fold**, and
   **recursive** within-fold prediction (§5.4). Only override to the simpler "raw-revenue RF"
   if you explicitly want that — it changes the bias/variance reading (trend-extrapolation
   bias appears) and must be labeled as such.
2. **Where diagnostics run.** Default: extend `train_revenue_forecast.py` and add
   `run_diagnostics.py`. Confirm you don't want a fully separate entrypoint only.
3. **Learning-curve validation block.** Default: fixed last 12 months of the training
   window. Confirm that (vs a moving block) is acceptable.
4. **Winner change.** If raising CV to 5 folds changes the selected learner, the report
   should adopt the new winner — confirm that's desired rather than pinning the old one.
