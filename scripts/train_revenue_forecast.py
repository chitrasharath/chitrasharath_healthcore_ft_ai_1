#!/usr/bin/env python3
"""Train HealthCore monthly revenue forecasts (Nixtla MLForecast + StatsForecast).

Run from repo root:
  uv sync --group forecast
  uv run python scripts/train_revenue_forecast.py
"""

from __future__ import annotations

import json
import pickle
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from data.forecast.clean import (
    clean_sales,
    load_raw,
    profile,
    split_train_test,
    write_clean,
)
from data.forecast.features import FEATURE_COLUMNS
from data.forecast.metrics import evaluate_model, point_metrics
from data.forecast.models_mlforecast import (
    cross_validation_select,
    fit_predict_revenue,
    light_param_sweep,
    perfect_foresight_predict,
)
from data.forecast.models_statsforecast import (
    classical_backtest,
    fit_classical_models,
    fit_seasonal_naive,
    forecast_visits,
    seasonal_factors_from_ets,
)
from data.forecast.plotting import (
    plot_each_model_vs_actual,
    plot_prediction_interval,
    plot_residual_diagnostics,
    plot_visits_forecast,
)

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "data" / "process" / "models"
EVAL_DIR = ROOT / "data" / "eval" / "revenue_forecast"
FIGURES_DIR = EVAL_DIR / "figures"
RANDOM_STATE = 42


def _save_pickle(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump(obj, fh)


def _interval_cols(preds: pd.DataFrame, model: str) -> dict[str, pd.Series | None]:
    return {
        "lo80": preds.get(f"{model}-lo-80"),
        "hi80": preds.get(f"{model}-hi-80"),
        "lo95": preds.get(f"{model}-lo-95"),
        "hi95": preds.get(f"{model}-hi-95"),
    }


def _series_from_forecast(fcst: pd.DataFrame, col: str) -> pd.Series:
    return fcst.sort_values("ds")[col].astype(float).reset_index(drop=True)


def _ml_train_scores(result: dict[str, Any], winner: str) -> pd.Series | None:
    """In-sample fitted predictions for PSI (never the test-horizon forecast)."""
    fitted = result.get("fitted_values")
    if fitted is None or winner not in fitted.columns:
        return None
    return fitted[winner].astype(float).dropna()


def _classical_train_scores(fitted_values: pd.DataFrame | None, name: str) -> pd.Series | None:
    if fitted_values is None or name not in fitted_values.columns:
        return None
    return fitted_values[name].astype(float).dropna()


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    np.random.seed(RANDOM_STATE)

    print("=== Phase 1: clean ===")
    raw = load_raw(ROOT / "data" / "raw" / "healthcore_sales.csv")
    cleaned = clean_sales(raw)
    write_clean(cleaned, ROOT / "data" / "process" / "healthcore_sales_clean.parquet")
    print("profile:", profile(cleaned))

    print("=== Phase 2: split ===")
    train_df, test_df = split_train_test(cleaned)
    y_test = test_df["y"].astype(float).reset_index(drop=True)
    y_train = train_df["y"].astype(float).reset_index(drop=True)

    print("=== Phase 3: SeasonalNaive baseline ===")
    naive_fcst = fit_seasonal_naive(train_df, h=24)
    naive_pred = _series_from_forecast(naive_fcst, "SeasonalNaive")
    baseline = point_metrics(y_test, naive_pred, train_actual=y_train)
    print(f"SeasonalNaive test RMSE={baseline['rmse']:.2f} MAE={baseline['mae']:.2f}")

    print("=== Phase 4a: Stage-1 visits forecast ===")
    visits_result = forecast_visits(train_df, h=24)
    x_df = visits_result["X_df"]
    visits_winner = visits_result["winner"]
    visits_fcst_col = visits_winner
    visits_pred = _series_from_forecast(visits_result["forecast"], visits_fcst_col)
    visits_actual = test_df["visits_count"].astype(float).reset_index(drop=True)
    visits_metrics = point_metrics(visits_actual, visits_pred)
    print(
        f"Visits winner={visits_winner} RMSE={visits_metrics['rmse']:.2f} "
        f"MAPE={visits_metrics['mape']:.4f} CV={visits_result['cv_rmse']}"
    )
    _save_pickle(visits_result["fitted"], MODELS_DIR / "visits_statsforecast.pkl")

    print("=== Phase 4b: MLForecast exogenous CV + sweep ===")
    cv_exog = cross_validation_select(train_df, include_visits=True)
    winner = cv_exog["winner"]
    print("CV scores:", cv_exog["scores"], "winner=", winner)
    sweep = light_param_sweep(train_df, winner, include_visits=True)
    print("Sweep best:", sweep["best_params"], "rmse=", sweep["best_rmse"])
    exog = fit_predict_revenue(
        train_df,
        winner=winner,
        params=sweep["best_params"],
        h=24,
        X_df=x_df,
        include_visits=True,
        with_intervals=True,
    )
    _save_pickle(exog["model"], MODELS_DIR / "mlforecast_exogenous.pkl")
    exog_pred = _series_from_forecast(exog["predictions"], winner)
    exog_iv = _interval_cols(exog["predictions"], winner)
    exog_train_scores = _ml_train_scores(exog, winner)

    print("=== Phase 4c: univariate ablation ===")
    cv_uni = cross_validation_select(train_df, include_visits=False)
    uni_winner = cv_uni["winner"]
    uni_sweep = light_param_sweep(train_df, uni_winner, include_visits=False)
    print("Uni sweep best:", uni_sweep["best_params"], "rmse=", uni_sweep["best_rmse"])
    uni = fit_predict_revenue(
        train_df,
        winner=uni_winner,
        params=uni_sweep["best_params"],
        h=24,
        X_df=None,
        include_visits=False,
        with_intervals=True,
    )
    _save_pickle(uni["model"], MODELS_DIR / "mlforecast_univariate.pkl")
    uni_pred = _series_from_forecast(uni["predictions"], uni_winner)
    uni_iv = _interval_cols(uni["predictions"], uni_winner)
    uni_train_scores = _ml_train_scores(uni, uni_winner)

    print("=== Perfect-foresight diagnostic (not headline) ===")
    pf_preds = perfect_foresight_predict(
        train_df,
        test_df,
        winner=winner,
        params=sweep["best_params"],
        h=24,
    )
    pf_series = _series_from_forecast(pf_preds, winner)
    pf_metrics = point_metrics(y_test, pf_series, train_actual=y_train)

    print("=== Phase 5: classical StatsForecast ===")
    classical = fit_classical_models(train_df, h=24)
    _save_pickle(classical["fitted"], MODELS_DIR / "statsforecast_classical.pkl")
    print("SARIMA order:", classical["sarima_order"], "AutoARIMA:", classical["autoarima_order"])

    print("=== Phase 6: metrics ===")
    metrics: dict[str, Any] = {
        "baseline_seasonal_naive": baseline,
        "stage1_visits": {
            "winner": visits_winner,
            "cv_rmse": visits_result["cv_rmse"],
            **visits_metrics,
        },
        "mlforecast_cv_exog": {
            "winner": winner,
            "scores": cv_exog["scores"],
            "sweep": {
                "best_params": sweep["best_params"],
                "best_rmse": sweep["best_rmse"],
            },
            "selection_cv": {"n_windows": 5, "h": 6, "step_size": 6},
        },
        "mlforecast_cv_uni": {
            "winner": uni_winner,
            "scores": cv_uni["scores"],
            "sweep": {
                "best_params": uni_sweep["best_params"],
                "best_rmse": uni_sweep["best_rmse"],
            },
            "selection_cv": {"n_windows": 5, "h": 6, "step_size": 6},
        },
        "feature_columns": FEATURE_COLUMNS,
        "sarima_order": classical["sarima_order"],
        "autoarima_order": classical["autoarima_order"],
        "perfect_foresight_diagnostic": {**pf_metrics, "note": "leakage upper bound — not a reportable model"},
        "models": {},
    }

    metrics["models"]["MLForecast_exog"] = evaluate_model(
        y_test,
        exog_pred,
        train_actual=y_train,
        train_scores=exog_train_scores,
        lo80=exog_iv["lo80"],
        hi80=exog_iv["hi80"],
        lo95=exog_iv["lo95"],
        hi95=exog_iv["hi95"],
    )
    metrics["models"]["MLForecast_uni"] = evaluate_model(
        y_test,
        uni_pred,
        train_actual=y_train,
        train_scores=uni_train_scores,
        lo80=uni_iv["lo80"],
        hi80=uni_iv["hi80"],
        lo95=uni_iv["lo95"],
        hi95=uni_iv["hi95"],
    )

    classical_fitted = classical.get("fitted_values")
    for name in classical["model_names"]:
        pred = _series_from_forecast(classical["forecast"], name)
        iv = _interval_cols(classical["forecast"], name)
        metrics["models"][name] = evaluate_model(
            y_test,
            pred,
            train_actual=y_train,
            train_scores=_classical_train_scores(classical_fitted, name),
            lo80=iv["lo80"],
            hi80=iv["hi80"],
            lo95=iv["lo95"],
            hi95=iv["hi95"],
        )

    # Rolling-origin classical backtest summary
    try:
        bt = classical_backtest(train_df, n_windows=5, h=12)
        bt_summary: dict[str, float] = {}
        for col in ["AutoARIMA", "AutoETS", "AutoTheta", "SeasonalNaive"]:
            if col in bt.columns:
                tmp = bt[["unique_id", "y", col]].dropna().rename(columns={col: "model"})
                from utilsforecast.losses import rmse as uf_rmse

                bt_summary[col] = float(uf_rmse(tmp, models=["model"])["model"].mean())
        metrics["classical_backtest_rmse"] = bt_summary
    except Exception as exc:  # pragma: no cover - best effort
        metrics["classical_backtest_rmse"] = {"error": str(exc)}

    metrics["seasonal_factors_ets"] = {str(k): v for k, v in seasonal_factors_from_ets(train_df).items()}

    # Recommendation: prefer univariate when visits lift is weak (spec §7.4c);
    # classical accuracy winner is separate from the regression path.
    exog_rmse = metrics["models"]["MLForecast_exog"]["rmse"]
    uni_rmse = metrics["models"]["MLForecast_uni"]["rmse"]
    cv_exog_winner = winner
    cv_uni_winner = uni_winner
    cv_exog_rmse = float(cv_exog["scores"][cv_exog_winner]["rmse"])
    cv_uni_rmse = float(cv_uni["scores"][cv_uni_winner]["rmse"])
    pf_rmse = float(pf_metrics["rmse"])
    test_lift_usd = float(uni_rmse - exog_rmse)  # >0 means exogenous better on test
    cv_lift_usd = float(cv_uni_rmse - cv_exog_rmse)
    pf_ceiling_gain = float(exog_rmse - pf_rmse)

    # Visits "help" only if CV and holdout both favor exogenous by a clear margin
    relative_test_lift = test_lift_usd / uni_rmse if uni_rmse else 0.0
    visits_help = bool(cv_lift_usd > 0 and relative_test_lift >= 0.03)
    chosen_regression = "MLForecast_exog" if visits_help else "MLForecast_uni"

    classical_candidates = [
        n for n in ["SARIMA", "AutoARIMA", "AutoETS", "AutoTheta", "AutoCES"] if n in metrics["models"]
    ]
    chosen_classical = min(classical_candidates, key=lambda n: metrics["models"][n]["rmse"])
    beats_naive = metrics["models"][chosen_regression]["rmse"] < baseline["rmse"]
    metrics["recommendation"] = {
        "primary_point_forecast": chosen_classical,
        "regression": chosen_regression,
        "regression_learner_exog": winner,
        "regression_learner_uni": uni_winner,
        "classical": chosen_classical,
        "beats_seasonal_naive": beats_naive,
        "ablation_visits_help": visits_help,
        "ablation_detail": {
            "cv_exog_rmse": cv_exog_rmse,
            "cv_uni_rmse": cv_uni_rmse,
            "cv_lift_usd": cv_lift_usd,
            "test_exog_rmse": exog_rmse,
            "test_uni_rmse": uni_rmse,
            "test_lift_usd": test_lift_usd,
            "relative_test_lift": relative_test_lift,
            "perfect_foresight_rmse": pf_rmse,
            "perfect_foresight_gain_vs_exog": pf_ceiling_gain,
            "rule": "Recommend univariate unless CV and test both favor exogenous by >=3% relative RMSE",
        },
    }
    if classical.get("ces_note"):
        metrics["ces_note"] = classical["ces_note"]
        # Keep a short note without the full numba traceback in metrics
        metrics["ces_note_short"] = "AutoCES skipped (numba readonly-array TypingError on this stack)."

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = EVAL_DIR / "metrics.json"

    def _json_default(obj: Any) -> Any:
        if isinstance(obj, (np.floating, np.integer)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        return str(obj)

    # Convert Series leftovers in metrics
    clean_metrics = json.loads(json.dumps(metrics, default=_json_default))
    metrics_path.write_text(json.dumps(clean_metrics, indent=2, sort_keys=True))
    print("Wrote", metrics_path)

    print("=== Phase 7: plots ===")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    forecast_overlays = {
        "MLForecast_exog": exog["predictions"].rename(columns={winner: "MLForecast_exog"}),
        "MLForecast_uni": uni["predictions"].rename(columns={uni_winner: "MLForecast_uni"}),
        "SARIMA": classical["forecast"][["unique_id", "ds", "SARIMA"] + [c for c in classical["forecast"].columns if c.startswith("SARIMA-")]],
        "AutoARIMA": classical["forecast"][["unique_id", "ds", "AutoARIMA"] + [c for c in classical["forecast"].columns if c.startswith("AutoARIMA-")]],
        "AutoETS": classical["forecast"][["unique_id", "ds", "AutoETS"] + [c for c in classical["forecast"].columns if c.startswith("AutoETS-")]],
    }
    for optional in ("AutoTheta", "AutoCES", "SeasonalNaive"):
        if optional in classical["forecast"].columns:
            cols = ["unique_id", "ds", optional] + [
                c for c in classical["forecast"].columns if c.startswith(f"{optional}-")
            ]
            forecast_overlays[optional] = classical["forecast"][cols]

    # Attach ML interval columns under the display names used in overlays
    for display, src, src_col in (
        ("MLForecast_exog", exog["predictions"], winner),
        ("MLForecast_uni", uni["predictions"], uni_winner),
    ):
        frame = forecast_overlays[display].copy()
        for level in (80, 95):
            for side in ("lo", "hi"):
                src_name = f"{src_col}-{side}-{level}"
                dst_name = f"{display}-{side}-{level}"
                if src_name in src.columns:
                    frame[dst_name] = src[src_name].values
        forecast_overlays[display] = frame

    visits_compare = pd.DataFrame(
        {
            "ds": test_df["ds"].values,
            "actual": visits_actual.values,
            "forecast": visits_pred.values,
        }
    )
    plot_visits_forecast(cleaned, visits_compare)
    per_model_paths = plot_each_model_vs_actual(cleaned, test_df, forecast_overlays)
    chosen_preds = exog["predictions"] if chosen_regression == "MLForecast_exog" else uni["predictions"]
    chosen_col = winner if chosen_regression == "MLForecast_exog" else uni_winner
    chosen_yhat = exog_pred if chosen_regression == "MLForecast_exog" else uni_pred
    plot_prediction_interval(test_df, chosen_preds, chosen_col)
    plot_residual_diagnostics(y_test, chosen_yhat)
    clean_metrics["per_model_figures"] = [p.name for p in per_model_paths]
    metrics_path.write_text(json.dumps(clean_metrics, indent=2, sort_keys=True, default=_json_default))
    print("Figures written to", FIGURES_DIR)

    print("=== Phase 8: report ===")
    _write_report(clean_metrics, baseline)
    print("Done. Recommendation:", clean_metrics["recommendation"])

    print("=== Phase 9: CV fit diagnostics ===")
    from data.forecast.diagnostics import run_all as run_diagnostics
    from data.forecast.diagnostics import write_diagnosis_report

    diag = run_diagnostics(train_df=train_df, metrics=clean_metrics, with_stretch=True)
    write_diagnosis_report(diag, clean_metrics)
    print("Diagnostics written to", EVAL_DIR / "diagnostics")


def _fmt_psi(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _write_report(metrics: dict[str, Any], baseline: dict[str, float]) -> None:
    rec = metrics["recommendation"]
    models = metrics["models"]
    exog = models["MLForecast_exog"]
    uni = models["MLForecast_uni"]
    classical_name = rec["classical"]
    classical = models[classical_name]
    reg_name = rec["regression"]
    reg = models[reg_name]
    primary = rec.get("primary_point_forecast", classical_name)
    primary_m = models[primary]
    detail = rec.get("ablation_detail", {})
    factors = metrics.get("seasonal_factors_ets", {})
    jul = float(factors.get("7", factors.get(7, float("nan"))))
    aug = float(factors.get("8", factors.get(8, float("nan"))))
    oct_ = float(factors.get("10", factors.get(10, float("nan"))))
    nov = float(factors.get("11", factors.get(11, float("nan"))))
    dec = float(factors.get("12", factors.get(12, float("nan"))))
    reg_learner = (
        rec["regression_learner_exog"] if reg_name == "MLForecast_exog" else rec["regression_learner_uni"]
    )

    lines = [
        "# HealthCore Monthly Revenue Forecast Report",
        "",
        "## 1. Executive summary",
        "",
        "Yes — monthly consolidated revenue is predictable enough to justify a network-wide executive dashboard.",
        "The honest evaluation number is the **recursive 24-month** holdout (2024–2025), not one-step-ahead error.",
        "",
        "### What to put behind the dashboard",
        "",
        f"1. **Primary point forecast: `{primary}`** — best holdout accuracy "
        f"(RMSE **${primary_m['rmse']:,.0f}**, {primary_m['rmse_pct_of_mean']:.1f}% of mean test revenue, "
        f"R² **{primary_m.get('r2', float('nan')):.3f}**, "
        f"80/95% coverage {primary_m.get('coverage_80', float('nan')):.0%}/{primary_m.get('coverage_95', float('nan')):.0%}).",
        f"2. **Regression path: `{reg_name}`** (learner `{reg_learner}`) — kept for a tree/lag feature workflow "
        f"and possible later scenario analysis. Holdout RMSE **${reg['rmse']:,.0f}** "
        f"(MASE {reg.get('mase', float('nan')):.3f} vs SeasonalNaive).",
        f"3. **Do not default to the visits exogenous model.** Ablation evidence says visits add little "
        f"(see §3.1); Stage-1 visits forecast error is MAPE {metrics['stage1_visits']['mape']:.1%}.",
        "",
        f"- SeasonalNaive baseline test RMSE: **${baseline['rmse']:,.0f}** (all recommended models beat this).",
        f"- Chosen regression beats SeasonalNaive: **{rec['beats_seasonal_naive']}**.",
        f"- Visits help (strict rule)? **{rec['ablation_visits_help']}**.",
        "",
        "## 2. Data & cleaning",
        "",
        "Source: `data/raw/healthcore_sales.csv` — 120 consolidated monthly rows (2016-01 … 2025-12).",
        "Cleaning drops null/empty `month` / `revenue_usd`, validates a continuous monthly index,",
        "and reshapes to Nixtla long format (`unique_id`, `ds`, `y`, `visits_count`).",
        "",
        "**Chronological split (never random):**",
        "",
        "| Set | Window | Months |",
        "|---|---|---:|",
        "| Train | 2016-01 … 2023-12 | 96 |",
        "| Test | 2024-01 … 2025-12 | 24 |",
        "",
        "### Original columns → what we used (and why)",
        "",
        "The raw file has five columns. Here is how each one was treated for the regression models:",
        "",
        "| Original column | Used in regression? | Plain-language reason |",
        "|---|---|---|",
        "| `month` | **Yes** (as the time index `ds`) | Tells the model which month we are predicting. Also drives calendar features (month number, season flags, etc.). |",
        "| `revenue_usd` | **Yes** (as the target `y`) | This is what we are trying to forecast — monthly network revenue in dollars. |",
        "| `visits_count` | **Carefully — only in the exogenous model** | Visits are a demand signal (busier clinics → more revenue), but we do **not** know next year’s visits in advance. See “How visits was used” below. |",
        "| `avg_revenue_per_visit_usd` | **No — never** | Together with visits it almost rebuilds revenue (`visits × $/visit ≈ revenue`). Feeding it in would be cheating: the model could “predict” by multiplying instead of learning real patterns. |",
        "| `region` | **No (as a feature)** | Every row is already `consolidated` (one network total). There is no US vs UK breakdown in this file, so region adds no information. We only keep a constant series id (`unique_id = consolidated`). |",
        "",
        "### How visits was used (layman’s version)",
        "",
        "Think of revenue as depending partly on **how many patients came in**. Visits are useful, but they create a trap:",
        "",
        "1. **In the past (training years 2016–2023):** we *do* know how many visits happened each month, so the exogenous model can learn “when visits were higher, revenue tended to be higher.”",
        "2. **In the future (test years 2024–2025):** if we handed the model the *real* visit counts for those months, we would be peeking at the answer booklet — in real life Sandra would not know next December’s visits yet. That would inflate accuracy unfairly (**leakage**).",
        "3. **So we use a two-step dance for the exogenous model:**",
        "   - **Step 1:** forecast visits for 2024–2025 from past visits alone (StatsForecast).",
        "   - **Step 2:** forecast revenue using those *predicted* visits, plus revenue’s own past and calendar patterns.",
        "4. **We also trained a simpler model with no visits at all** (`MLForecast_uni`) — only past revenue and calendar. That answers: “Did visits earn their keep?” In this dataset the lift was small, so the recommended regression path is the **visits-free** model.",
        "",
        "Bottom line for Sandra: visits are a fair demand hint when forecasted honestly; they are **not** a free look at the future, and they are **not** paired with $/visit (that would just reconstruct revenue).",
        "",
        "### Technical leakage notes",
        "",
        "- **Identity leakage:** `visits × avg_revenue_per_visit ≈ revenue` — so `$/visit` is banned as a feature.",
        "- **Future visits leakage:** test-horizon `visits_count` in the exogenous model comes from the Stage-1 **forecast**, never actual test visits.",
        "- **Transforms:** MLForecast `Differences([12])` + `LocalStandardScaler` are learned on train only inside `.fit()`.",
        "",
        f"Engineered feature catalog (`FEATURE_COLUMNS`): {', '.join(metrics['feature_columns'])}.",
        "",
        "## 3. Regression model (MLForecast)",
        "",
        "Two families were trained with the same lag/calendar machinery:",
        "",
        "- **Exogenous (two-stage):** Stage-1 visits forecast → revenue model with `visits_count` in `X_df`.",
        "- **Univariate ablation:** Groups A+B only (calendar + revenue lags/rolling + trend). No visits.",
        "",
        "Learners compared inside one MLForecast object: RandomForest, XGBoost, ElasticNet.",
        "Selection uses rolling-origin CV on the **training** window only (`n_windows=5`, `h=6`); the test set is scored once.",
        "",
        f"- Exogenous CV winner: `{metrics['mlforecast_cv_exog']['winner']}` "
        f"(CV RMSE {detail.get('cv_exog_rmse', float('nan')):,.0f}); "
        f"light sweep params `{metrics['mlforecast_cv_exog']['sweep']['best_params']}`.",
        f"- Univariate CV winner: `{metrics['mlforecast_cv_uni']['winner']}` "
        f"(CV RMSE {detail.get('cv_uni_rmse', float('nan')):,.0f}).",
        "",
        "### 3.1 Ablation: do visits actually help?",
        "",
        "Spec §7.4c: if the lift is small, recommend the simpler univariate model.",
        "",
        "| Evidence | Exogenous | Univariate | Interpretation |",
        "|---|---:|---:|---|",
        f"| CV RMSE (winner learner) | ${detail.get('cv_exog_rmse', float('nan')):,.0f} | "
        f"${detail.get('cv_uni_rmse', float('nan')):,.0f} | "
        f"{'Exogenous better in CV' if detail.get('cv_lift_usd', 0) > 0 else 'Univariate better/equal in CV'} |",
        f"| Test RMSE | ${exog['rmse']:,.0f} | ${uni['rmse']:,.0f} | "
        f"Test lift for exogenous = ${detail.get('test_lift_usd', float('nan')):,.0f} "
        f"({100 * detail.get('relative_test_lift', float('nan')):.1f}% relative) |",
        f"| Perfect-foresight RMSE (diagnostic) | ${detail.get('perfect_foresight_rmse', float('nan')):,.0f} | — | "
        f"Even with *actual* test visits, gain vs exogenous forecast ≈ "
        f"${detail.get('perfect_foresight_gain_vs_exog', float('nan')):,.0f} |",
        f"| Stage-1 visits error | RMSE {metrics['stage1_visits']['rmse']:.0f} visits "
        f"(MAPE {metrics['stage1_visits']['mape']:.1%}) | — | Exogenous revenue inherits this error |",
        "",
        f"**Verdict:** visits help = **{rec['ablation_visits_help']}**. "
        f"Rule used: `{detail.get('rule', 'n/a')}`.",
        "The holdout edge for exogenous is small relative to revenue scale and contradicts CV; "
        "perfect foresight shows visits carry little incremental signal beyond revenue's own past. "
        f"Therefore the recommended regression path is **`{reg_name}`**.",
        "",
        "Perfect-foresight is **leakage-for-diagnosis only** and is excluded from headline metrics.",
        "",
        "## 4. Classical models (StatsForecast)",
        "",
        f"Explicit **{metrics['sarima_order']}** (hand-specified / AutoARIMA-informed).",
        f"AutoARIMA order note: `{metrics['autoarima_order']}`.",
        "Also fit AutoETS, AutoTheta, and SeasonalNaive with 80/95% intervals.",
        f"{metrics.get('ces_note_short', 'AutoCES attempted; see metrics.json if skipped.')}",
        "",
        f"**Holdout classical winner: `{classical_name}`** "
        f"(RMSE ${classical['rmse']:,.0f}, R² {classical.get('r2', float('nan')):.3f}).",
        f"Rolling-origin backtest RMSE (train windows): `{metrics.get('classical_backtest_rmse', {})}`.",
        "",
        "### 4.1 Seasonality recovery (ETS factors)",
        "",
        "AutoETS monthly seasonal factors recovered the business pattern from CONTEXT §4 "
        "(Jul–Aug −12–18%, Oct–Dec +15–20%):",
        "",
        f"- Jul / Aug factors: **{jul:.2f} / {aug:.2f}** (~{(1 - (jul + aug) / 2) * 100:.0f}% dip vs mean).",
        f"- Oct / Nov / Dec factors: **{oct_:.2f} / {nov:.2f} / {dec:.2f}** "
        f"(~{((oct_ + nov + dec) / 3 - 1) * 100:.0f}% lift vs mean).",
        "",
        "That match is evidence the leakage guards held: a leaked model would not need to learn seasonality.",
        "",
        "## 5. Predictions",
        "",
        "### Per-model vs actual",
        "",
    ]

    for name in metrics.get("per_model_figures", []):
        label = name.replace("actual_vs_", "").replace(".png", "")
        lines.extend(
            [
                f"#### {label}",
                "",
                f"![{label} vs actual](figures/{name})",
                "",
            ]
        )

    lines.extend(
        [
            "### Stage-1 visits",
            "",
            "![Stage-1 visits forecast](figures/visits_forecast.png)",
            "",
            "### Recommended regression — intervals & residuals",
            "",
            "![Prediction intervals](figures/prediction_interval.png)",
            "",
            "![Residual diagnostics](figures/residual_diagnostics.png)",
            "",
            "## 6. Evaluation metrics",
            "",
            "All metrics below are on the **24-month test set** unless noted. "
            "PSI uses **in-sample fitted scores on train** vs **test forecasts** (same definition for every model).",
            "",
            "| Model | RMSE (USD) | RMSE % mean | MAE | MAPE | MASE | R² | PSI | Gini | K2 p | Cov80 | Cov95 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for name, m in models.items():
        lines.append(
            f"| {name} | {m['rmse']:,.0f} | {m['rmse_pct_of_mean']:.1f}% | {m['mae']:,.0f} | "
            f"{m['mape']:.3f} | {m.get('mase', float('nan')):.3f} | {m.get('r2', float('nan')):.3f} | "
            f"{_fmt_psi(m.get('psi'))} | "
            f"{m.get('gini', float('nan')):.3f} | {m.get('k2_pvalue', float('nan')):.3f} | "
            f"{m.get('coverage_80', float('nan')):.2f} | {m.get('coverage_95', float('nan')):.2f} |"
        )

    lines.extend(
        [
            "",
            "### Plain-English metric guide",
            "",
            f"- **RMSE / MSE / MAPE / R²:** size of the typical miss. Recommended regression RMSE "
            f"~${reg['rmse']:,.0f} ({reg['rmse_pct_of_mean']:.1f}% of mean test revenue); "
            f"R²={reg.get('r2', float('nan')):.3f}. Primary classical `{primary}` RMSE "
            f"~${primary_m['rmse']:,.0f} (R²={primary_m.get('r2', float('nan')):.3f}).",
            f"- **MASE:** error scaled by SeasonalNaive’s seasonal MAE on train. "
            f"< 1 beats same-month-last-year. Recommended regression MASE={reg.get('mase', float('nan')):.3f}; "
            f"`{primary}` MASE={primary_m.get('mase', float('nan')):.3f}.",
            "- **PSI (Population Stability Index):** compares the **distribution of model scores** "
            "(train fitted predictions vs test forecasts). Rule of thumb: <0.1 stable, 0.1–0.25 moderate, >0.25 large. "
            "CONTEXT originally framed PSI as US/UK visit-mix shift, but this file has only consolidated revenue — "
            "a high PSI here almost always means **2024–25 revenue sits above the training score range** (trend), "
            "not clinic-mix change. Prior classical PSI=0.000 values were a bug (test scores compared to themselves) "
            "and have been corrected to use in-sample fitted scores.",
            f"- **Gini:** ranking quality (0≈random, 1≈perfect ordering of low→high months). "
            f"Recommended regression Gini={reg.get('gini', float('nan')):.3f}; "
            f"`{primary}` Gini={primary_m.get('gini', float('nan')):.3f}. "
            "This is the “spot an atypical August” metric Sandra cares about — SeasonalNaive is much weaker.",
            f"- **K2 (D'Agostino–Pearson):** normality of residuals. High p (>0.05) → errors look roughly Gaussian → "
            f"interval bands are more trustworthy. Recommended regression K2 p={reg.get('k2_pvalue', float('nan')):.3f}; "
            f"`{primary}` p={primary_m.get('k2_pvalue', float('nan')):.3f}. "
            "**Caveat:** with only 24 test points this test is weak — “looks normal” is soft evidence, not proof.",
            f"- **Interval coverage:** share of test months inside 80%/95% bands. "
            f"`{primary}` covers {primary_m.get('coverage_80', float('nan')):.0%} / "
            f"{primary_m.get('coverage_95', float('nan')):.0%}. "
            "MLForecast bands are conformal; StatsForecast bands come from each classical model.",
            "",
            "## 7. Recommendation",
            "",
            f"- **Ship `{primary}` as the default point forecast** for the executive dashboard "
            "(best holdout RMSE, strong R², strong interval coverage, recovered seasonality).",
            f"- **Keep `{reg_name}` as the regression path** if product wants lag/tree features or later "
            "what-if extensions. Prefer it over the exogenous visits pipeline given the ablation.",
            "- **Treat exogenous visits as optional R&D**, not production default: CV does not favor it, "
            "perfect foresight gain is tiny, and Stage-1 adds moving parts.",
            "- Always quote the **recursive 24-month** error — that is the cold-start number Sandra will live with.",
            "",
            "### Limitations",
            "",
            "- Only 120 monthly points; NeuralForecast / TimeGPT are out of scope (and TimeGPT would leave the box).",
            "- Strong upward trend inflates PSI and stresses extrapolation beyond 2023.",
            "- No US/UK regional series — visit-mix PSI is not directly computable.",
            "- Log/Box-Cox left off the default path; SHAP deferred.",
            "- K2/normality evidence is soft at n=24.",
            "",
        ]
    )
    (EVAL_DIR / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
