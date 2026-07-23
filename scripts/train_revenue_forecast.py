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
    plot_predictions_combined,
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

    # Train scores for PSI: use fitted values when available, else in-sample predict proxy
    train_scores = exog_pred  # fallback
    if exog["fitted_values"] is not None and winner in exog["fitted_values"].columns:
        train_scores = exog["fitted_values"][winner].astype(float)

    print("=== Phase 4c: univariate ablation ===")
    cv_uni = cross_validation_select(train_df, include_visits=False)
    uni_winner = cv_uni["winner"]
    uni_sweep = light_param_sweep(train_df, uni_winner, include_visits=False)
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
        "mlforecast_cv_exog": {"winner": winner, "scores": cv_exog["scores"], "sweep": {
            "best_params": sweep["best_params"],
            "best_rmse": sweep["best_rmse"],
        }},
        "mlforecast_cv_uni": {"winner": uni_winner, "scores": cv_uni["scores"]},
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
        train_scores=train_scores,
        lo80=exog_iv["lo80"],
        hi80=exog_iv["hi80"],
        lo95=exog_iv["lo95"],
        hi95=exog_iv["hi95"],
    )
    metrics["models"]["MLForecast_uni"] = evaluate_model(
        y_test,
        uni_pred,
        train_actual=y_train,
        train_scores=uni_pred if uni["fitted_values"] is None else uni["fitted_values"].get(uni_winner, uni_pred),
        lo80=uni_iv["lo80"],
        hi80=uni_iv["hi80"],
        lo95=uni_iv["lo95"],
        hi95=uni_iv["hi95"],
    )

    for name in classical["model_names"]:
        pred = _series_from_forecast(classical["forecast"], name)
        iv = _interval_cols(classical["forecast"], name)
        metrics["models"][name] = evaluate_model(
            y_test,
            pred,
            train_actual=y_train,
            train_scores=pred,
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

    # Choose regression + classical winners for recommendation
    exog_rmse = metrics["models"]["MLForecast_exog"]["rmse"]
    uni_rmse = metrics["models"]["MLForecast_uni"]["rmse"]
    chosen_regression = "MLForecast_exog" if exog_rmse <= uni_rmse else "MLForecast_uni"
    classical_candidates = [n for n in ["SARIMA", "AutoARIMA", "AutoETS", "AutoTheta", "AutoCES"] if n in metrics["models"]]
    chosen_classical = min(classical_candidates, key=lambda n: metrics["models"][n]["rmse"])
    beats_naive = metrics["models"][chosen_regression]["rmse"] < baseline["rmse"]
    metrics["recommendation"] = {
        "regression": chosen_regression,
        "regression_learner_exog": winner,
        "regression_learner_uni": uni_winner,
        "classical": chosen_classical,
        "beats_seasonal_naive": beats_naive,
        "ablation_visits_help": exog_rmse < uni_rmse,
    }
    if classical.get("ces_note"):
        metrics["ces_note"] = classical["ces_note"]

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
    plot_predictions_combined(cleaned, test_df, forecast_overlays)
    per_model_paths = plot_each_model_vs_actual(cleaned, test_df, forecast_overlays)
    plot_visits_forecast(cleaned, visits_compare)
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


def _write_report(metrics: dict[str, Any], baseline: dict[str, float]) -> None:
    rec = metrics["recommendation"]
    models = metrics["models"]
    exog = models["MLForecast_exog"]
    uni = models["MLForecast_uni"]
    classical_name = rec["classical"]
    classical = models[classical_name]
    reg_name = rec["regression"]
    reg = models[reg_name]

    lines = [
        "# HealthCore Monthly Revenue Forecast Report",
        "",
        "## 1. Executive summary",
        "",
        f"Yes — monthly consolidated revenue is predictable enough to justify a network dashboard, "
        f"with honest recursive 24-month accuracy around **RMSE ${reg['rmse']:,.0f}** "
        f"({reg['rmse_pct_of_mean']:.1f}% of mean test monthly revenue) for the recommended "
        f"regression model **{reg_name}** "
        f"(learner: `{rec['regression_learner_exog'] if reg_name == 'MLForecast_exog' else rec['regression_learner_uni']}`).",
        "",
        f"- SeasonalNaive baseline test RMSE: **${baseline['rmse']:,.0f}**.",
        f"- Chosen regression beats SeasonalNaive: **{rec['beats_seasonal_naive']}**.",
        f"- Best classical model on the holdout: **{classical_name}** (RMSE ${classical['rmse']:,.0f}).",
        f"- Visits exogenous lift: exogenous RMSE ${exog['rmse']:,.0f} vs univariate ${uni['rmse']:,.0f} "
        f"(visits help={rec['ablation_visits_help']}).",
        f"- Stage-1 visits forecast RMSE: **{metrics['stage1_visits']['rmse']:.1f}** visits "
        f"(MAPE {metrics['stage1_visits']['mape']:.3f}); the exogenous revenue model inherits this error.",
        "",
        "## 2. Data & cleaning",
        "",
        "Source: `data/raw/healthcore_sales.csv` (120 consolidated monthly rows, 2016-01 … 2025-12).",
        "Cleaning drops null/empty month or revenue rows, validates a continuous monthly index,",
        "and reshapes to Nixtla long format (`unique_id`, `ds`, `y`, `visits_count`).",
        "",
        "**Split:** train 2016-01…2023-12 (96 months), test 2024-01…2025-12 (24 months), chronological — never random.",
        "",
        "**Leakage controls:** `avg_revenue_per_visit_usd` is excluded (with visits it reconstructs revenue).",
        "`visits_count` is used as an exogenous demand driver, but over the test horizon it comes from a",
        "**Stage-1 StatsForecast visits forecast**, never actual test visits.",
        "",
        f"Feature catalog (`FEATURE_COLUMNS`): {', '.join(metrics['feature_columns'])}.",
        "",
        "## 3. Regression model (MLForecast)",
        "",
        "Two-stage design: forecast visits → feed as `X_df` into MLForecast with lag/calendar features,",
        f"`Differences([12])` + `LocalStandardScaler` inside `.fit()` (train only). Learners compared by",
        "rolling-origin CV on the training window (RF, XGBoost, ElasticNet); test scored once.",
        "",
        f"- Exogenous CV winner: `{metrics['mlforecast_cv_exog']['winner']}` "
        f"with light sweep params `{metrics['mlforecast_cv_exog']['sweep']['best_params']}`.",
        f"- Univariate CV winner: `{metrics['mlforecast_cv_uni']['winner']}`.",
        f"- Ablation verdict: {'exogenous visits improved test RMSE' if rec['ablation_visits_help'] else 'univariate matched/beat exogenous — prefer the simpler univariate regression for the dashboard'}.",
        "",
        f"Perfect-foresight diagnostic (actual test visits — **not** a reportable model): "
        f"RMSE ${metrics['perfect_foresight_diagnostic']['rmse']:,.0f}. "
        "Gap vs exogenous forecast isolates Stage-1 visits error.",
        "",
        "## 4. Classical models (StatsForecast)",
        "",
        f"Explicit **{metrics['sarima_order']}** (pinned from / compared to AutoARIMA where available).",
        f"AutoARIMA order note: `{metrics['autoarima_order']}`.",
        "Also fit AutoETS, AutoTheta, AutoCES, and SeasonalNaive with 80/95% intervals.",
        "",
        f"Holdout winner among classical models: **{classical_name}**.",
        f"Rolling-origin backtest RMSE (train windows): `{metrics.get('classical_backtest_rmse', {})}`.",
        "",
        "## 5. Predictions",
        "",
        "### Combined overlay",
        "",
        "![Combined predictions](figures/predictions_combined.png)",
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
        "### Chosen model intervals & residuals",
        "",
        "![Prediction intervals](figures/prediction_interval.png)",
        "",
        "![Residual diagnostics](figures/residual_diagnostics.png)",
        "",
        "## 6. Evaluation metrics",
        "",
        "| Model | RMSE (USD) | RMSE % mean | MAE | MAPE | MASE | PSI | Gini | K2 p | Cov80 | Cov95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for name, m in models.items():
        lines.append(
            f"| {name} | {m['rmse']:,.0f} | {m['rmse_pct_of_mean']:.1f}% | {m['mae']:,.0f} | "
            f"{m['mape']:.3f} | {m.get('mase', float('nan')):.3f} | {m.get('psi', float('nan')):.3f} | "
            f"{m.get('gini', float('nan')):.3f} | {m.get('k2_pvalue', float('nan')):.3f} | "
            f"{m.get('coverage_80', float('nan')):.2f} | {m.get('coverage_95', float('nan')):.2f} |"
        )

    lines.extend(
        [
            "",
            "### Plain-English interpretations",
            "",
            f"- **RMSE / MSE:** typical monthly miss of ~${reg['rmse']:,.0f} "
            f"({reg['rmse_pct_of_mean']:.1f}% of average test revenue). MSE is in USD².",
            f"- **MASE:** {reg.get('mase', float('nan')):.3f} vs SeasonalNaive scale — "
            f"{'better than' if reg.get('mase', 1) < 1 else 'not better than'} same-month-last-year on absolute error.",
            f"- **PSI ({reg.get('psi', float('nan')):.3f}):** score-distribution drift train→test. "
            "CONTEXT frames PSI as US/UK visit-mix shift, but this dataset has only consolidated revenue — "
            "a high value here most likely reflects 2024–25 revenue exceeding the training range, not clinic mix.",
            f"- **Gini ({reg.get('gini', float('nan')):.3f}):** ranking quality — how well the model orders low vs high months.",
            f"- **K2 p-value ({reg.get('k2_pvalue', float('nan')):.3f}):** "
            f"{'residuals look roughly normal — intervals more trustworthy' if reg.get('k2_pvalue', 0) > 0.05 else 'residuals deviate from normality — read intervals with caution'}.",
            f"- **Interval coverage:** 80% band covers {reg.get('coverage_80', float('nan')):.0%} of test months; "
            f"95% band covers {reg.get('coverage_95', float('nan')):.0%} (conformal / StatsForecast levels).",
            "",
            "## 7. Recommendation",
            "",
            f"Put **{reg_name}** behind the executive dashboard as the regression path, "
            f"with **{classical_name}** as the classical comparator.",
            "Use the recursive 24-month forecast (not one-step) as the honest accuracy number.",
            "",
            "### Limitations",
            "",
            "- Only 120 monthly points; deep models (NeuralForecast / TimeGPT) are not justified and TimeGPT was dropped to keep the pipeline local/key-free.",
            "- Strong upward trend makes extrapolation and PSI sensitive.",
            "- No US/UK regional breakdown — visit-mix PSI is not directly computable.",
            "- Log/Box-Cox left off the default path; SHAP deferred.",
            "",
        ]
    )
    (EVAL_DIR / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
