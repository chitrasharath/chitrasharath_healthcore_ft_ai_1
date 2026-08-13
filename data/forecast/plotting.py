"""Matplotlib plots for revenue forecast evaluation."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf

FIGURES_DIR = Path("data/eval/revenue_forecast/figures")

# Near-black actuals vs saturated forecast hues (high contrast on white).
ACTUAL_TRAIN = "#111827"
ACTUAL_TEST = "#374151"
FORECAST_DEFAULT = "#E11D48"

MODEL_COLORS = {
    "MLForecast_exog": "#2563EB",  # blue
    "MLForecast_uni": "#EA580C",  # orange
    "SARIMA": "#DB2777",  # pink
    "AutoARIMA": "#16A34A",  # green
    "AutoETS": "#DC2626",  # red
    "AutoTheta": "#CA8A04",  # gold
    "AutoCES": "#0891B2",  # cyan
    "SeasonalNaive": "#7C3AED",  # violet
}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _plot_actuals(ax: plt.Axes, train: pd.DataFrame, test: pd.DataFrame, *, y_col: str = "y", scale: float = 1e6) -> None:
    ax.plot(
        train["ds"],
        train[y_col] / scale,
        color=ACTUAL_TRAIN,
        lw=2.2,
        label="Actual (train)",
        zorder=3,
    )
    ax.plot(
        test["ds"],
        test[y_col] / scale,
        color=ACTUAL_TEST,
        lw=2.2,
        ls="--",
        marker="o",
        ms=4,
        label="Actual (test)",
        zorder=3,
    )

def _forecast_value_col(frame: pd.DataFrame, model_name: str) -> str:
    if model_name in frame.columns:
        return model_name
    candidates = [c for c in frame.columns if c not in {"unique_id", "ds"} and "-lo-" not in c and "-hi-" not in c]
    if not candidates:
        raise ValueError(f"No forecast column found for {model_name}")
    return candidates[0]


def plot_model_vs_actual(
    history: pd.DataFrame,
    test: pd.DataFrame,
    forecast: pd.DataFrame,
    model_name: str,
    *,
    out_path: Path | str | None = None,
) -> Path:
    """One page: actual train/test revenue vs a single model forecast."""
    safe = model_name.replace("/", "_").replace(" ", "_")
    out = Path(out_path) if out_path is not None else FIGURES_DIR / f"actual_vs_{safe}.png"
    _ensure_dir(out.parent)
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)

    hist = history.copy()
    hist["ds"] = pd.to_datetime(hist["ds"])
    tst = test.copy()
    tst["ds"] = pd.to_datetime(tst["ds"])
    f = forecast.copy()
    f["ds"] = pd.to_datetime(f["ds"])
    col = _forecast_value_col(f, model_name)
    color = MODEL_COLORS.get(model_name, FORECAST_DEFAULT)

    train = hist.loc[hist["ds"] <= pd.Timestamp("2023-12-01")]
    _plot_actuals(ax, train, tst)
    ax.plot(
        f["ds"],
        f[col] / 1e6,
        color=color,
        lw=2.4,
        marker="s",
        ms=4,
        label=f"{model_name} forecast",
        zorder=4,
    )

    # Optional interval shading when present
    lo95, hi95 = f"{col}-lo-95", f"{col}-hi-95"
    lo80, hi80 = f"{col}-lo-80", f"{col}-hi-80"
    if lo95 in f.columns and hi95 in f.columns:
        ax.fill_between(f["ds"], f[lo95] / 1e6, f[hi95] / 1e6, color=color, alpha=0.15, label="95% PI", zorder=1)
    if lo80 in f.columns and hi80 in f.columns:
        ax.fill_between(f["ds"], f[lo80] / 1e6, f[hi80] / 1e6, color=color, alpha=0.28, label="80% PI", zorder=1)

    ax.set_title(f"Actual vs {model_name}")
    ax.set_ylabel("Revenue (USD millions)")
    ax.set_xlabel("Month")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_each_model_vs_actual(
    history: pd.DataFrame,
    test: pd.DataFrame,
    forecasts: dict[str, pd.DataFrame],
    *,
    figures_dir: Path | str = FIGURES_DIR,
) -> list[Path]:
    """Write one actual-vs-model PNG per entry in ``forecasts``."""
    paths: list[Path] = []
    out_dir = Path(figures_dir)
    for name, fcst in forecasts.items():
        paths.append(
            plot_model_vs_actual(
                history,
                test,
                fcst,
                name,
                out_path=out_dir / f"actual_vs_{name}.png",
            )
        )
    return paths


def plot_visits_forecast(
    history: pd.DataFrame,
    visits_compare: pd.DataFrame,
    *,
    out_path: Path | str = FIGURES_DIR / "visits_forecast.png",
) -> Path:
    """Standalone Stage-1 visits page: train history + test actual vs forecast."""
    out = Path(out_path)
    _ensure_dir(out.parent)
    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)

    hist = history.copy()
    hist["ds"] = pd.to_datetime(hist["ds"])
    train = hist.loc[hist["ds"] <= pd.Timestamp("2023-12-01")]
    ax.plot(
        train["ds"],
        train["visits_count"],
        color=ACTUAL_TRAIN,
        lw=2.0,
        label="Visits actual (train)",
        zorder=3,
    )

    v = visits_compare.copy()
    v["ds"] = pd.to_datetime(v["ds"])
    ax.plot(
        v["ds"],
        v["actual"],
        color=ACTUAL_TEST,
        lw=2.2,
        ls="--",
        marker="o",
        ms=4,
        label="Visits actual (test)",
        zorder=3,
    )
    ax.plot(
        v["ds"],
        v["forecast"],
        color="#EA580C",
        lw=2.4,
        marker="s",
        ms=4,
        label="Stage-1 visits forecast",
        zorder=4,
    )

    ax.set_title("Stage-1 visits forecast vs actual (test window)")
    ax.set_ylabel("Visits count")
    ax.set_xlabel("Month")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out

def plot_prediction_interval(
    test: pd.DataFrame,
    preds: pd.DataFrame,
    model_col: str,
    *,
    out_path: Path | str = FIGURES_DIR / "prediction_interval.png",
) -> Path:
    """Zoomed test window with conformal 80/95% bands for the chosen MLForecast model."""
    out = Path(out_path)
    _ensure_dir(out.parent)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)

    t = test.copy()
    t["ds"] = pd.to_datetime(t["ds"])
    p = preds.copy()
    p["ds"] = pd.to_datetime(p["ds"])

    lo95 = f"{model_col}-lo-95"
    hi95 = f"{model_col}-hi-95"
    lo80 = f"{model_col}-lo-80"
    hi80 = f"{model_col}-hi-80"

    if lo95 in p.columns and hi95 in p.columns:
        ax.fill_between(p["ds"], p[lo95] / 1e6, p[hi95] / 1e6, color="#2563EB", alpha=0.15, label="95% PI")
    if lo80 in p.columns and hi80 in p.columns:
        ax.fill_between(p["ds"], p[lo80] / 1e6, p[hi80] / 1e6, color="#2563EB", alpha=0.28, label="80% PI")

    ax.plot(t["ds"], t["y"] / 1e6, "o-", color=ACTUAL_TRAIN, lw=2.2, ms=4, label="Actual", zorder=3)
    ax.plot(
        p["ds"],
        p[model_col] / 1e6,
        "-",
        color=FORECAST_DEFAULT,
        lw=2.4,
        label=f"Forecast ({model_col})",
        zorder=4,
    )
    ax.set_title("Chosen MLForecast — test window with prediction intervals")
    ax.set_ylabel("Revenue (USD millions)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def plot_residual_diagnostics(
    actual: pd.Series | np.ndarray,
    predicted: pd.Series | np.ndarray,
    *,
    out_path: Path | str = FIGURES_DIR / "residual_diagnostics.png",
) -> Path:
    """Residuals over time, histogram + normal overlay, and residual ACF."""
    out = Path(out_path)
    _ensure_dir(out.parent)
    y = np.asarray(actual, dtype=float).ravel()
    yhat = np.asarray(predicted, dtype=float).ravel()
    resid = y - yhat

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), dpi=150)
    axes[0].plot(resid, color="#0f766e")
    axes[0].axhline(0, color="#64748b", lw=1)
    axes[0].set_title("Residuals over time")

    axes[1].hist(resid, bins=10, density=True, color="#99f6e4", edgecolor="#0f766e")
    xs = np.linspace(resid.min(), resid.max(), 200)
    axes[1].plot(xs, _normal_pdf(xs, resid.mean(), resid.std(ddof=1)), color="#0369a1", lw=1.5)
    axes[1].set_title("Residual histogram")

    plot_acf(resid, ax=axes[2], lags=min(12, len(resid) - 1))
    axes[2].set_title("Residual ACF")

    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def _normal_pdf(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return np.zeros_like(x)
    return (1.0 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
