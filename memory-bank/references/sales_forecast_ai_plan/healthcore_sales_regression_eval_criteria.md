# HealthCore — Revenue Prediction Evaluation Criteria

Checklist used to evaluate the deliverable produced from [`healthcore_sales_regression_specs.md`](healthcore_sales_regression_specs.md). The stack is **Nixtla** — MLForecast (regression) + StatsForecast (classical), running fully locally (no hosted APIs).

## ✅ What We Will Evaluate

- [ ] **Two-stage exogenous, no leakage** — Visits are forecast first (Stage 1) and fed to the revenue model as exogenous; the test horizon uses **forecasted** visits, never actual test visits. `avg_revenue_per_visit_usd` is never a feature. A univariate ablation is run for comparison.
- [ ] **Explicit feature catalog built** — The §5.2 features exist (calendar/seasonality incl. `is_high_season`/`is_low_season`, autoregressive revenue lags/rolling, exogenous visits) and match a single `FEATURE_COLUMNS` source of truth.
- [ ] **Chronological 8/2 split** — Train 2016–2023 (96 mo), test 2024–2025 (24 mo), by date, never random. `train.ds.max() < test.ds.min()`.
- [ ] **Transforms fit on train only** — MLForecast `target_transforms` (`Differences` + `LocalStandardScaler`) are learned inside `.fit()` on the training window; nothing sees test rows.
- [ ] **Split + leakage unit tests pass** — `tests/pipelines/` contains and passes the split, no-leakage, and data-validation tests.
- [ ] **RF vs XGBoost chosen by CV** — Both learners run inside one MLForecast; the winner is picked by `cross_validation` (rolling-origin) on the training set, with evidence shown. The test set is scored once.
- [ ] **Stage-1 visits forecast reported** — `visits_count` is forecast with StatsForecast and its own accuracy (RMSE/MAPE) is reported, since the revenue model inherits that error.
- [ ] **Ablation verdict stated** — The report compares exogenous vs univariate and says whether visits earned their keep (and which model it recommends for the dashboard).
- [ ] **Beats SeasonalNaive** — The chosen MLForecast model outperforms StatsForecast `SeasonalNaive` on test RMSE, or the report explains why not.
- [ ] **SARIMA + AutoARIMA + AutoETS implemented** — An explicit `SARIMA(p,d,q)(P,D,Q)₁₂` (StatsForecast `ARIMA`) plus AutoARIMA and AutoETS, all fit on train and forecasting 24 months with `level=[80,95]` intervals. (Prophet/`statsmodels`/TimeGPT are *not* expected — SARIMA lives in StatsForecast and the pipeline is fully local.)
- [ ] **All four required metrics** — MSE (USD² **and** % of mean revenue), PSI, Gini, K2 — on the **test** set, each interpreted in business language.
- [ ] **Combined prediction plot** — Historical + test actuals + MLForecast (exogenous + univariate ablation), AutoARIMA, AutoETS over the test window, with interval bands.
- [ ] **Deterministic rerun** — `scripts/train_revenue_forecast.py` regenerates identical metrics/figures on a clean run (seed = 42).
- [ ] **Readable report** — Sandra can read the summary and know whether revenue is predictable, which model was chosen, and why.

---

## How Each Criterion Maps to the Spec

| # | Criterion | Where the spec covers it | Evidence to look for |
|---|---|---|---|
| 1 | Two-stage exogenous / no leakage | §1.1, §5.2, §7.4a–c | `X_df` visits = Stage-1 forecast, not `test_df.visits_count`; no `avg_revenue_per_visit`; univariate ablation present |
| 1b | Explicit feature catalog | §5.2 (Groups A–C), `features.py` | `FEATURE_COLUMNS` matches the model's features; seasonality flags + lags/rolling + visits present; tests assert the list |
| 2 | Chronological 8/2 split | §5.3, §11 `test_revenue_split.py` | 96/24 counts; `2023-12` last train `ds`, `2024-01` first test; no random split of the series |
| 3 | Transforms fit on train only | §5.4, §11 `test_revenue_no_leakage.py` | `LocalStandardScaler`/`Differences` applied via `target_transforms`; forecasts unchanged when test `y` is perturbed |
| 4 | Tests pass | §11 | `pytest tests/pipelines/ -v` green; tests call real pipeline functions |
| 5 | RF vs XGB by CV | §7 Phase 4b | `mlf.cross_validation(...)` RMSE table per learner; winner named + small param sweep |
| 5b | Stage-1 visits + ablation | §7 Phase 4a, 4c; §8.1 | Visits forecast RMSE/MAPE reported; exogenous-vs-univariate metrics side by side + recommendation |
| 6 | Beats SeasonalNaive | §7 Phase 3, §1.2 | `SeasonalNaive` test RMSE reported; chosen model compared to it |
| 7 | SARIMA + AutoARIMA + AutoETS | §7 Phase 5 | Explicit `SARIMA(p,d,q)(P,D,Q)₁₂` order recorded; AutoARIMA order + ETS components logged; all forecast 24 mo with `level=[80,95]` |
| 8 | Four metrics + extras | §8 | `metrics.json` has MSE/RMSE (USD & %), PSI (with caveat), Gini, K2 (stat + p); each interpreted |
| 9 | Combined plot | §9, §10 | `data/eval/revenue_forecast/figures/predictions_combined.png` embedded; legend distinguishes every model |
| 10 | Deterministic | §14 | `random_state=42` throughout; second run → identical `metrics.json` |
| 11 | Readable report | §10 | Executive summary answers "can we predict revenue?" numbers-first, before model detail |

---

## Notes for the Reviewer

- **Criterion 1 is the make-or-break one.** Because `visits_count × avg_revenue_per_visit ≈ revenue_usd`, three mistakes must be caught: (a) including `avg_revenue_per_visit` at all — instant leakage; (b) using **actual** test-period `visits_count` in `X_df` instead of the Stage-1 **forecast** — subtle leakage that inflates test scores because in deployment you would not know future visits; (c) any submission showing near-perfect metrics — a **red flag**, not a win. Verify `X_df` visits come from the visits forecast and that perturbing `test_df.visits_count` leaves the revenue forecast unchanged.
- **Criterion 2 — no random splits.** A shuffled split of a time series leaks the future. With Nixtla the correct pattern is `fit(train)` → `predict(h=24)` → score against the held-out 24 months. Any `train_test_split(shuffle=True)` on the series fails.
- **Criterion 3 — scaling is via `target_transforms`, not a separate sklearn `StandardScaler`.** That's correct and expected here; `LocalStandardScaler`/`Differences` are fit inside `.fit()` on train. Tree learners are scale-invariant, so the *point* of the transforms is the `Differences` de-trending and the leakage discipline — the report should say so, not claim scaling boosted the trees.
- **Criterion 5 — CV, not the test set.** RF-vs-XGBoost selection must use `cross_validation` on the *training* window. A submission that picks the model by looking at test-set performance has contaminated the evaluation, even if the code "works."
- **Criterion 7 — SARIMA yes, but inside StatsForecast.** An explicit `SARIMA` (StatsForecast `ARIMA` with a seasonal order) is required alongside AutoARIMA and AutoETS. Prophet and hand-tuned `statsmodels` SARIMAX are *not* — a submission bringing back `statsmodels` for SARIMA has ignored the stack decision (StatsForecast's `AutoARIMA` is itself a seasonal ARIMA, and the explicit `ARIMA` class covers the named SARIMA).
- **Fully local — no external calls.** The pipeline must run offline. A submission that reaches for TimeGPT or any hosted forecasting API has gone outside the spec (TimeGPT was deliberately dropped: it needs an API key and would send the series off-box).
- **Criterion 8 — the PSI caveat is required.** CONTEXT frames PSI as a US/UK visit-mix signal, but there's no regional data. A correct submission computes PSI on the model score distribution and states that a high value most likely reflects the 2024–25 revenue trend exceeding the training range, not a clinic-mix shift.
- **Criterion 8 — K2 is a normality test.** Expect `scipy.stats.normaltest` on residuals (D'Agostino–Pearson K²) as statistic + p-value, interpreted as whether the prediction intervals are trustworthy.
- **Recursive forecast honesty.** MLForecast's `predict(h=24)` is *already* the recursive multi-step (cold-start) forecast — the honest 2-year number. A report that quietly substitutes a one-step-ahead figure and implies it's the deployment accuracy is overselling.
- **Determinism (criterion 10) is quick to spot-check.** Run `scripts/train_revenue_forecast.py` twice and diff `data/eval/revenue_forecast/metrics.json`; any change means an unseeded component.
