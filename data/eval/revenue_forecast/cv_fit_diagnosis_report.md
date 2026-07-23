# HealthCore — Temporal CV & Fit Diagnosis Report

## 1. Summary

| Model | Fit verdict | CV RMSE (mean ± std) | Corrective action |
|---|---|---|---|
| MLForecast_uni(rf) | **overfitting** | $97,608 ± $26,157 | Constrain MLForecast_uni(rf): set max_depth (e.g. 3–5), raise min_samples_leaf, max_features < 1.0, and/or fewer estimators. |
| AutoETS | **well-fitted** | $88,096 ± $21,104 | Ship AutoETS; keep this CV/learning-curve suite as a regression guard. |

- Diagnostic ML target: `MLForecast_uni(rf)` with params `{'max_depth': None, 'max_features': 1.0, 'n_estimators': 200}`.
- 5-fold selection winner is `rf` (params `{'max_depth': None, 'max_features': 1.0, 'n_estimators': 200}`). Prior 3-fold shipped selection pinned as `rf` with params `{'n_estimators': 200, 'max_depth': None, 'max_features': 1.0}`. Winner unchanged vs the pinned 3-fold selection.

## 2. CV setup & integrity

- **Folds:** 5 (≥5 required) × 6-month non-overlapping validation blocks on the **training window only** (2016–2023).
- **Why 5×6:** five non-overlapping 12-month folds do not fit after `Differences([12])` + `lag_12` consume ~24 months; overlapping folds understate fold std.
- **Engines:** ML winner → `sklearn.model_selection.TimeSeriesSplit` (gap=0); AutoETS → existing `classical_backtest` / `StatsForecast.cross_validation` (`n_windows=5`, `h=6`, `step_size=6`).
- **Chronology:** no shuffle; every fold has `max(train ds) < min(val ds)`; validation blocks are contiguous and roll forward; `TimeSeriesSplit` never shuffles.
- **Date alignment:** both engines score the same calendar windows `[('2021-07-01', '2021-12-01'), ('2022-01-01', '2022-06-01'), ('2022-07-01', '2022-12-01'), ('2023-01-01', '2023-06-01'), ('2023-07-01', '2023-12-01')]`.
- **Selection CV change:** MLForecast learner-selection defaults raised from **n_windows=3, h=12** (shipped) to **n_windows=5, h=6**. Classical `classical_backtest` was already 5-fold.

- **Pipeline recommendation after 5-fold retrain:** primary classical `AutoETS`; regression path `MLForecast_exog` (visits help=True). Prior 3-fold narrative preferred univariate when visits lift was weak — note any flip; learner identity for uni/exog remains pinned above when unchanged.

### Per-fold validation RMSE

| Fold | Window | ML val RMSE | AutoETS val RMSE |
|---:|---|---:|---:|
| 0 | 2021-07-01…2021-12-01 | $94,978 | $91,767 |
| 1 | 2022-01-01…2022-06-01 | $103,365 | $90,130 |
| 2 | 2022-07-01…2022-12-01 | $58,379 | $60,529 |
| 3 | 2023-01-01…2023-06-01 | $131,567 | $118,584 |
| 4 | 2023-07-01…2023-12-01 | $99,750 | $79,469 |

- ML val RMSE min/max: $58,379 / $131,567 (small-sample std caveat: only 5 folds).
- AutoETS val RMSE min/max: $60,529 / $118,584.

## 3. Metrics table (train & validation)

| Model | Stage | MAE (mean ± std) | RMSE (mean ± std) | RMSE % mean train revenue |
|---|---|---|---|---|
| MLForecast_uni(rf) | Train | $28,126 ± $1,865 | $36,254 ± $1,494 | — |
| MLForecast_uni(rf) | Validation | $82,671 ± $26,183 | $97,608 ± $26,157 | 3.5% |
| AutoETS | Train | $57,173 ± $2,107 | $68,676 ± $1,854 | — |
| AutoETS | Validation | $77,164 ± $21,721 | $88,096 ± $21,104 | 3.2% |

Mean monthly train revenue ≈ **$2,754,918**.

## 4. Learning curves

Fixed validation block: **2023-01…2023-12**. Training prefixes `[36, 48, 60, 72]` all end before 2023-01. Smallest prefixes (~36 months) are noisy.

### MLForecast_uni(rf)

![ML learning curve](diagnostics/learning_curve_mlforecast_uni.png)

- s=36: train RMSE $0, val RMSE $146,226 (gap $146,226)
- s=48: train RMSE $44,603, val RMSE $104,688 (gap $60,085)
- s=60: train RMSE $37,100, val RMSE $121,277 (gap $84,177)
- s=72: train RMSE $35,913, val RMSE $119,851 (gap $83,938)

### AutoETS

![AutoETS learning curve](diagnostics/learning_curve_autoets.png)

- s=36: train RMSE $51,223, val RMSE $595,843 (gap $544,620)
- s=48: train RMSE $56,533, val RMSE $382,106 (gap $325,573)
- s=60: train RMSE $61,279, val RMSE $294,749 (gap $233,470)
- s=72: train RMSE $67,704, val RMSE $178,649 (gap $110,945)

### ElasticNet side check (ML overfit contrast)

![ElasticNet learning curve](diagnostics/learning_curve_elasticnet.png)

- s=36: train RMSE $0, val RMSE $146,226
- s=48: train RMSE $93,901, val RMSE $103,298
- s=60: train RMSE $104,674, val RMSE $283,236
- s=72: train RMSE $104,956, val RMSE $109,876

## 5. Business-cost metric (MAE vs RMSE)

Authoritative context: **`rag_assignments/CONTEXT-healthcore.en.md` §3** (sales-prediction context — **not** the repo website `CONTEXT.md`).

CONTEXT §3 asks to *"report MSE in USD², and also as a percentage of average monthly revenue"*, and prizes a high **Gini** to *"distinguish a normal low-season month … from an atypical drop."* Both signals say the business cares about **large, unusual deviations**, not just average error.

**RMSE is the business-cost metric.** It is √MSE in interpretable dollars and penalizes large errors disproportionately — matching the cost of a planning-breaking revenue miss (over/under-staffing, misinformed executive decisions). A single $500k miss is worse than ten $50k misses; RMSE reflects that, MAE treats them as equal.

- ML CV RMSE as % of mean monthly train revenue: **3.5%**.
- AutoETS CV RMSE as % of mean monthly train revenue: **3.2%**.
- MAE is reported alongside for “average dollars off” interpretability.

## 6. Fit diagnosis

### MLForecast_uni(rf) → **overfitting**

- Learning-curve (largest prefix): train RMSE $35,913, val RMSE $119,851, gap $83,938 (relative 70%).
- CV: train RMSE $36,254, val RMSE $97,608 ± $26,157, CV gap $61,354 (relative 63%), fold CV 0.27.
- Guardrail: For tree models, near-zero train RMSE is the overfitting signature; diagnose on the val−train gap, not absolute train error. Do not compare tree train error to AutoETS in-sample residuals as like-for-like.

### AutoETS → **well-fitted**

- Learning-curve (largest prefix): train RMSE $67,704, val RMSE $178,649, gap $110,945 (relative 62%).
- CV: train RMSE $68,676, val RMSE $88,096 ± $21,104, CV gap $19,420 (relative 22%), fold CV 0.24.
- Guardrail: Classical AutoETS train error is genuine in-sample residual, not memorization. Learning-curve val error from early prefixes includes a long multi-step horizon into 2023 (trend), so CV train/val gap is the primary fit signal.

## 7. Method note

§5.4 correctness rules honored for the ML path: causal `.shift()` features (no same-month target leakage); `Differences([12])` + local scaler **fit per fold on train rows only** and inverted for scoring (scaler is a tree no-op but kept for faithfulness); **recursive** month-by-month prediction inside each 6-month block (predictions feed lag features — never one-shot `predict(X[test])`); validation windows defined **by date first** and asserted identical across `TimeSeriesSplit` and `StatsForecast.cross_validation`.

## 8. Corrective actions

### MLForecast_uni(rf) (overfitting)

- Constrain MLForecast_uni(rf): set max_depth (e.g. 3–5), raise min_samples_leaf, max_features < 1.0, and/or fewer estimators.
- Prune the feature set (many lags/rollings on ~84 effective rows).
- Prefer a more regularized learner (ElasticNet) or lean on classical AutoETS.
- Add drift monitoring (PSI); more historical data is not available (fixed 120 months).

### AutoETS (well-fitted)

- Ship AutoETS; keep this CV/learning-curve suite as a regression guard.
- Monitor PSI for regime shift; revisit only if new data changes the pattern.
- More data is not available as a lever (fixed 120 months).

## Stretch notes

- **Purged gap=1 A/B:** gap=0 val RMSE $97,608 ± $26,157; gap=1 val RMSE $99,223 ± $25,494.
- Per-fold RMSE strip: `diagnostics/fold_rmse_strip.png`.
- **SeasonalNaive-in-CV** val RMSE $163,407 ± $49,039 (skill context vs ML / AutoETS fold RMSE).

## 9. Limitations

- Only 120 monthly points; ~84 effective training rows after differencing + `lag_12`.
- 6-month CV horizon; std across 5 folds is a small-sample estimate (report min/max).
- “Collect more data” is not a lever for corrective action.
- Learning-curve prefixes at s=36 are noisy after transforms.
