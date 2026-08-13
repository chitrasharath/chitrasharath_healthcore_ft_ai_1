# HealthCore — CV & Fit-Diagnosis Evaluation Criteria

Checklist used to evaluate the deliverable produced from [`healthcore_cv_diagnosis_specs.md`](healthcore_cv_diagnosis_specs.md). Target: branch `feature/sales_forecast` of the HealthCore monorepo. Two models in scope: **MLForecast_uni (rf)** via sklearn `TimeSeriesSplit`, **AutoETS** via `StatsForecast.cross_validation`.

## ✅ What We Will Evaluate

- [ ] **On the right branch** — All work is on **`feature/eval_metrics`**, branched from **`feature/sales_forecast`** (not `main`); nothing committed directly to `feature/sales_forecast`. PR base is `feature/sales_forecast`.
- [ ] **≥5 folds, confirmed** — The MLForecast **selection** CV is raised from the shipped `n_windows=3` to **≥5**, and the diagnostic CV runs on ≥5 folds; the report states the actual count and notes the classical backtest was already 5-fold.
- [ ] **Shipped RF params used, not hardcoded** — The RF diagnostic uses the actual sweep winner from `metrics.json` (`n_estimators=200, max_depth=null, max_features=1.0`), not the base-learner `n_estimators=300`.
- [ ] **AutoETS reuses `classical_backtest`** — The AutoETS CV reuses the existing helper (`h=6`), not a fresh hand-written `cross_validation` call.
- [ ] **No shuffle / chronological order per fold** — Every fold has `max(train ds) < min(val ds)`; validation blocks are contiguous, forward-rolling, non-overlapping; no random K-fold anywhere.
- [ ] **Per-model engine used** — RF validated with `TimeSeriesSplit`, AutoETS with `StatsForecast.cross_validation`; both 5 folds × 6-month blocks.
- [ ] **Folds aligned by date across engines** — The five validation windows cover the **same calendar months** for both models, defined by date (not integer position), with an assertion.
- [ ] **Recursive within-fold RF prediction** — The RF's 6-month block is predicted month-by-month feeding its own predictions back into lags — not one-shot `predict(X[test])`.
- [ ] **Per-fold transforms fit on train only** — `Differences([12])`/scaler for the RF path are fit inside each fold's training rows, never globally.
- [ ] **Chosen metric as mean ± std** — RMSE reported as **mean ± std across the 5 folds** for both models (with min/max and small-sample caveat).
- [ ] **MAE and RMSE, train and validation** — All four reported for both models.
- [ ] **Learning curves** — Expanding-window train-vs-validation MAE/RMSE curves saved as PNG for both models, against a fixed validation block.
- [ ] **Business-cost metric justified from CONTEXT** — Report argues which of MAE/RMSE reflects business cost, grounded in specific lines of `CONTEXT-healthcore.en.md` §3 (expected: RMSE, as √MSE in dollars), and reports **RMSE as % of average monthly revenue** per that section. The website `CONTEXT.md` is not the source.
- [ ] **Explicit fit classification** — Each model labeled well-fitted / underfitting / overfitting, backed by **both** the learning curve **and** the CV spread.
- [ ] **Interpretation guardrails honored** — Report reads the val−train gap (not RF's ~0 train error alone) and doesn't compare RF vs AutoETS train error as like-for-like.
- [ ] **Corrective actions match the diagnosis** — Proposed fixes are consistent with each model's verdict (variance-reducers for the overfit RF, "ship + monitor" for a well-fit AutoETS).
- [ ] **Temporal-order unit test** — `tests/pipelines/test_temporal_cv_order.py` validates **both** splitters preserve chronological order per fold; full suite stays green.
- [ ] **Deterministic** — Rerun reproduces `cv_folds.json`, `learning_curve.json`, and PNGs (seed 42).

---

## How Each Criterion Maps to the Spec

| # | Criterion | Where the spec covers it | Evidence to look for |
|---|---|---|---|
| 0 | Correct branch | §15, §16 | Commits on `feature/eval_metrics` off `feature/sales_forecast`; PR base `feature/sales_forecast` |
| 1 | ≥5 folds confirmed | §4, §5.1, §7 Phase 1–2 | MLForecast selection CV `n_windows>=5`; report notes classical backtest was already 5-fold |
| 1a | Shipped RF params from metrics.json | §4, §5.1a | Uses `best_params` (200 trees), not base `n_estimators=300`; params named in report |
| 1b | AutoETS reuses `classical_backtest` | §4, §5.1b | Calls the existing helper with `h=6`; no duplicate CV code |
| 2 | Chronological, no shuffle | §5.2, §12 | Per-fold `max(train ds) < min(val ds)`; no `KFold(shuffle=True)`; non-overlapping blocks |
| 3 | Per-model engine | §5.1a/b, §7 Phase 2 | RF→`TimeSeriesSplit(n_splits=5, test_size=6)`; AutoETS→`cross_validation(n_windows=5, h=6)` |
| 4 | Date-aligned folds | §5.1, §5.4 #4 | Windows defined by `ds` first; assertion the two engines' block boundaries match |
| 5 | Recursive RF prediction | §5.1a, §5.4 #3 | Month-by-month loop feeding predictions into lags; **no** `rf.predict(X[test_idx])` in one shot |
| 6 | Fold-local transforms | §5.1a, §5.4 #2 | `Differences([12])`/scaler `.fit` on train rows of each fold; inverted for scoring |
| 7 | RMSE mean ± std | §5.3 | `RMSE = $X ± $Y` per model; min/max; small-sample note |
| 8 | MAE & RMSE, train & val | §8 | Four numbers per model in USD |
| 9 | Learning curves | §7 Phase 3 | `learning_curve_*.png` + `learning_curve.json`; expanding prefixes, fixed val block |
| 10 | Business-cost metric | §9 | Explicit pick (RMSE) tied to `CONTEXT-healthcore.en.md` §3 (MSE-in-USD²-and-%, Gini/atypical-month); RMSE also given as % of mean revenue; not the website CONTEXT.md |
| 11 | Fit classification | §7 Phase 4, §10.6 | Per-model verdict citing learning curve **and** CV std |
| 12 | Interpretation guardrails | §5.4 #5–6, §10.6 | Diagnosis reads the gap; trend-extrapolation vs underfitting distinguished |
| 13 | Corrective actions | §11, §10.8 | Actions match verdict; "more data" ruled out (fixed 120 rows) |
| 14 | Temporal-order test | §12 | Both engines covered; alignment + determinism + negative control |
| 15 | Deterministic | §15 | Second run diffs clean |

---

## Notes for the Reviewer

- **Criterion 1 — be precise about *which* CV was 3-fold.** The shipped **MLForecast learner-selection** CV was `n_windows=3`; the **classical backtest** (`classical_backtest`) was already 5. A passing submission raises the MLForecast selection CV to ≥5, *says so*, notes the classical side was already 5-fold, and ideally reports whether the selected learner changed. Silently leaving `n_windows=3` fails.
- **Criterion 1a — diagnose the model that shipped.** The base RF learner is `n_estimators=300`, but the sweep winner in `metrics.json` was `n_estimators=200`. A submission that diagnoses the 300-tree base learner is diagnosing a model that never shipped — it must read `best_params`.
- **Criterion 5 is the easy silent failure.** `rf.predict(X[test_idx])` on the whole 6-month block *runs fine and looks correct*, but it lets each validation month peek at the previous month's actual revenue via `lag_1` — inflating the RF's score and understating the overfitting. Check for an explicit month-by-month recursion that feeds predictions back into the lags. If the RF's CV RMSE looks suspiciously close to or better than AutoETS, suspect this.
- **Criterion 6 vs 5 interact.** If the per-fold transform (`Differences([12])`) is fit globally, or the recursion is skipped, the RF numbers are wrong in opposite directions — verify both before trusting any RF fold score.
- **Criterion 4 is a subtle apples-to-oranges trap.** `TimeSeriesSplit` counts rows of the (~72–84-row) feature matrix; `StatsForecast` counts the 96-row series. Without date-first alignment the two "5-fold" CVs can score *different months*, making mean±std incomparable. Look for an explicit date-defined window list and an alignment assertion.
- **Criterion 12 — don't let the report misread RF.** A Random Forest with `max_depth=None` has **train RMSE ≈ 0 by construction**. That is the overfitting signature, not a data bug, and it must not be compared against AutoETS's genuine in-sample residuals as if equal. A report that says "RF fits training perfectly, so it's the best model" has the diagnosis backwards.
- **Criterion 10 must cite the *right* context, not generic ML lore.** The source is `rag_assignments/CONTEXT-healthcore.en.md` §3 — the repo's `CONTEXT.md` is the website/patient-form milestone and is the wrong file. "RMSE penalizes large errors" is true but insufficient — the report must tie it to HealthCore specifics: CONTEXT §3 asks for **MSE in USD² and as % of average monthly revenue** and prizes **Gini** for catching *atypical* months → the business cares about large deviations → **RMSE** (= √MSE in dollars), also expressed as % of mean revenue. MAE reported alongside for interpretability is expected, not a substitute.
- **Criterion 13 must respect the fixed data.** "Collect more data" is not a valid corrective action — there are 120 months, period. For the expected overfit-RF verdict, look for real variance reducers: constrain depth/leaves/features, prune the 20-feature set, prefer ElasticNet or lean on AutoETS.
- **Criterion 14 — test both engines.** The single required test file must validate the RF `TimeSeriesSplit` path **and** the AutoETS `StatsForecast` path, plus the cross-engine date alignment. A test that only checks one engine leaves half the "temporal CV strategy" unverified.
- **Honesty check:** if raising CV to 5 folds flips the selected learner or changes the fit verdict, the report must say so rather than quietly keeping the old conclusion.
