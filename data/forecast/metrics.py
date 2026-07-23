"""Evaluation metrics for revenue forecasts (MSE/PSI/Gini/K2/MASE + extras)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from utilsforecast.losses import mae, mape, mse, rmse, smape


def _align(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(actual, dtype=float).ravel()
    yhat = np.asarray(predicted, dtype=float).ravel()
    if len(y) != len(yhat):
        raise ValueError(f"Length mismatch: actual={len(y)} predicted={len(yhat)}")
    return y, yhat


def point_metrics(
    actual: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
    *,
    train_actual: pd.Series | np.ndarray | None = None,
    season_length: int = 12,
) -> dict[str, float]:
    """Standard point-forecast metrics including MASE vs seasonal naive scale."""
    y, yhat = _align(actual, predicted)
    frame = pd.DataFrame({"unique_id": "consolidated", "y": y, "model": yhat})
    mse_v = float(mse(frame, models=["model"])["model"].iloc[0])
    rmse_v = float(rmse(frame, models=["model"])["model"].iloc[0])
    mae_v = float(mae(frame, models=["model"])["model"].iloc[0])
    mape_v = float(mape(frame, models=["model"])["model"].iloc[0])
    smape_v = float(smape(frame, models=["model"])["model"].iloc[0])
    mean_y = float(np.mean(y))
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - mean_y) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # Directional accuracy vs prior actual month
    if len(y) >= 2:
        dir_actual = np.sign(np.diff(y))
        dir_pred = np.sign(yhat[1:] - y[:-1])
        directional = float(np.mean(dir_actual == dir_pred))
    else:
        directional = float("nan")

    mase_v = float("nan")
    if train_actual is not None:
        mase_v = mase(y, yhat, train_actual, season_length=season_length)

    return {
        "mse": mse_v,
        "rmse": rmse_v,
        "mae": mae_v,
        "mape": mape_v,
        "smape": smape_v,
        "r2": r2,
        "rmse_pct_of_mean": 100.0 * rmse_v / mean_y if mean_y else float("nan"),
        "mse_pct_of_mean_sq": 100.0 * mse_v / (mean_y**2) if mean_y else float("nan"),
        "mean_test_revenue": mean_y,
        "directional_accuracy": directional,
        "mase": mase_v,
    }


def mase(
    actual: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
    train_actual: pd.Series | np.ndarray,
    *,
    season_length: int = 12,
) -> float:
    """MASE scaled by seasonal naive MAE on the training window."""
    y, yhat = _align(actual, predicted)
    train = np.asarray(train_actual, dtype=float).ravel()
    if len(train) <= season_length:
        raise ValueError("train_actual too short for seasonal MASE scale")
    scale = np.mean(np.abs(train[season_length:] - train[:-season_length]))
    if scale == 0:
        return float("nan")
    return float(np.mean(np.abs(y - yhat)) / scale)


def population_stability_index(
    expected: pd.Series | np.ndarray,
    actual: pd.Series | np.ndarray,
    *,
    n_bins: int = 10,
    eps: float = 1e-6,
) -> float:
    """PSI between expected (train scores) and actual (test scores) distributions."""
    exp = np.asarray(expected, dtype=float).ravel()
    act = np.asarray(actual, dtype=float).ravel()
    quantiles = np.linspace(0, 1, n_bins + 1)
    breaks = np.unique(np.quantile(exp, quantiles))
    if len(breaks) < 3:
        breaks = np.linspace(exp.min(), exp.max(), n_bins + 1)
    exp_counts, _ = np.histogram(exp, bins=breaks)
    act_counts, _ = np.histogram(act, bins=breaks)
    exp_pct = exp_counts / max(exp_counts.sum(), 1) + eps
    act_pct = act_counts / max(act_counts.sum(), 1) + eps
    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def drift_monitor_psi(
    new_scores: pd.Series | np.ndarray,
    reference_scores: pd.Series | np.ndarray,
    *,
    n_bins: int = 10,
) -> float:
    """Stub for dashboard drift alarms: PSI of a new batch vs a reference distribution."""
    return population_stability_index(reference_scores, new_scores, n_bins=n_bins)


def normalized_gini(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    """Kaggle-style normalized Gini for a continuous target (ranking quality)."""
    y, yhat = _align(actual, predicted)
    order = np.argsort(yhat)
    y_sorted = y[order]
    cum = np.cumsum(y_sorted)
    if cum[-1] == 0:
        return float("nan")
    lorenz = cum / cum[-1]
    gini = float(np.trapezoid(lorenz, dx=1.0 / (len(y) - 1)) * 2 - 1) if len(y) > 1 else 0.0

    perfect_order = np.argsort(y)
    y_perf = y[perfect_order]
    cum_p = np.cumsum(y_perf)
    lorenz_p = cum_p / cum_p[-1]
    gini_perfect = float(np.trapezoid(lorenz_p, dx=1.0 / (len(y) - 1)) * 2 - 1) if len(y) > 1 else 1.0
    if gini_perfect == 0:
        return float("nan")
    return float(gini / gini_perfect)


def k2_normality(residuals: pd.Series | np.ndarray) -> dict[str, float]:
    """D'Agostino–Pearson K² normality test on residuals."""
    resid = np.asarray(residuals, dtype=float).ravel()
    stat, pvalue = stats.normaltest(resid)
    return {"k2_statistic": float(stat), "k2_pvalue": float(pvalue)}


def interval_coverage(
    actual: pd.Series | np.ndarray,
    lo: pd.Series | np.ndarray,
    hi: pd.Series | np.ndarray,
) -> float:
    """Fraction of actuals inside [lo, hi]."""
    y = np.asarray(actual, dtype=float).ravel()
    low = np.asarray(lo, dtype=float).ravel()
    high = np.asarray(hi, dtype=float).ravel()
    return float(np.mean((y >= low) & (y <= high)))


def ljung_box_pvalue(residuals: pd.Series | np.ndarray, lags: int = 12) -> float:
    """Ljung–Box p-value for leftover residual autocorrelation."""
    from statsmodels.stats.diagnostic import acorr_ljungbox

    resid = np.asarray(residuals, dtype=float).ravel()
    result = acorr_ljungbox(resid, lags=[lags], return_df=True)
    return float(result["lb_pvalue"].iloc[0])


def evaluate_model(
    actual: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
    *,
    train_actual: pd.Series | np.ndarray | None = None,
    train_scores: pd.Series | np.ndarray | None = None,
    lo80: pd.Series | np.ndarray | None = None,
    hi80: pd.Series | np.ndarray | None = None,
    lo95: pd.Series | np.ndarray | None = None,
    hi95: pd.Series | np.ndarray | None = None,
) -> dict[str, Any]:
    """Full metric bundle for one model on the test set."""
    y, yhat = _align(actual, predicted)
    out: dict[str, Any] = point_metrics(y, yhat, train_actual=train_actual)
    resid = y - yhat
    out.update(k2_normality(resid))
    out["gini"] = normalized_gini(y, yhat)
    out["ljung_box_pvalue"] = ljung_box_pvalue(resid)
    if train_scores is not None:
        out["psi"] = population_stability_index(train_scores, yhat)
    if lo80 is not None and hi80 is not None:
        out["coverage_80"] = interval_coverage(y, lo80, hi80)
        out["miscoverage_80"] = 1.0 - out["coverage_80"]
    if lo95 is not None and hi95 is not None:
        out["coverage_95"] = interval_coverage(y, lo95, hi95)
        out["miscoverage_95"] = 1.0 - out["coverage_95"]
    return out
