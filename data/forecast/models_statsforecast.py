"""StatsForecast classical models and Stage-1 visits forecast."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import (
    ARIMA,
    AutoARIMA,
    AutoCES,
    AutoETS,
    AutoTheta,
    SeasonalNaive,
)
from utilsforecast.losses import rmse

RANDOM_SEED = 42
FREQ = "MS"
SEASON_LENGTH = 12
LEVELS = [80, 95]


def _sf(models: list[Any]) -> StatsForecast:
    return StatsForecast(models=models, freq=FREQ, n_jobs=1)


def fit_seasonal_naive(train_df: pd.DataFrame, h: int = 24) -> pd.DataFrame:
    """Baseline SeasonalNaive forecast."""
    sf = _sf([SeasonalNaive(season_length=SEASON_LENGTH)])
    sf.fit(train_df[["unique_id", "ds", "y"]])
    return sf.predict(h=h, level=LEVELS)


def forecast_visits(
    train_df: pd.DataFrame,
    *,
    h: int = 24,
    n_windows: int = 3,
) -> dict[str, Any]:
    """Stage-1: forecast visits_count with AutoARIMA vs AutoETS; pick by CV RMSE."""
    visits = (
        train_df[["unique_id", "ds", "visits_count"]]
        .rename(columns={"visits_count": "y"})
        .copy()
    )
    visits["y"] = visits["y"].astype(float)
    models = [
        AutoARIMA(season_length=SEASON_LENGTH),
        AutoETS(season_length=SEASON_LENGTH),
    ]
    sf = _sf(models)
    cv = sf.cross_validation(h=12, df=visits, step_size=12, n_windows=n_windows)
    scores: dict[str, float] = {}
    for col in ["AutoARIMA", "AutoETS"]:
        frame = cv[["unique_id", "ds", "y", col]].dropna().rename(columns={col: "model"})
        scores[col] = float(rmse(frame, models=["model"])["model"].mean())
    winner = min(scores, key=scores.get)

    sf.fit(visits)
    fcst = sf.predict(h=h, level=LEVELS)
    x_df = fcst[["unique_id", "ds", winner]].rename(columns={winner: "visits_count"}).copy()
    x_df["visits_count"] = x_df["visits_count"].astype(float)

    return {
        "winner": winner,
        "cv_rmse": scores,
        "forecast": fcst,
        "X_df": x_df,
        "fitted": sf,
    }


def _sarima_from_auto(train_y: pd.DataFrame) -> ARIMA:
    """Fit AutoARIMA once and pin an explicit SARIMA with the chosen order when available."""
    auto = AutoARIMA(season_length=SEASON_LENGTH)
    sf = _sf([auto])
    sf.fit(train_y)
    # Fallback starter order from the plan
    order = (1, 1, 1)
    seasonal_order = (1, 1, 1)
    try:
        fitted = sf.fitted_[0, 0].model_
        # statsforecast stores order attributes on the underlying model when available
        if hasattr(fitted, "order"):
            order = tuple(fitted.order)  # type: ignore[assignment]
        if hasattr(fitted, "seasonal_order"):
            seasonal_order = tuple(fitted.seasonal_order)  # type: ignore[assignment]
        elif hasattr(fitted, "season_length"):
            # Some backends expose arma orders differently; keep defaults if missing
            pass
    except Exception:
        order, seasonal_order = (1, 1, 1), (1, 1, 1)

    return ARIMA(
        order=order,
        seasonal_order=seasonal_order,
        season_length=SEASON_LENGTH,
        alias="SARIMA",
    )


def fit_classical_models(train_df: pd.DataFrame, h: int = 24) -> dict[str, Any]:
    """Fit SARIMA + AutoARIMA + AutoETS + AutoTheta + AutoCES + SeasonalNaive."""
    train_y = train_df[["unique_id", "ds", "y"]].copy()
    # AutoCES/numba requires a writable float64 buffer
    train_y["y"] = np.array(train_y["y"].to_numpy(dtype=np.float64), copy=True)
    sarima = _sarima_from_auto(train_y)
    models = [
        sarima,
        AutoARIMA(season_length=SEASON_LENGTH),
        AutoETS(season_length=SEASON_LENGTH),
        AutoTheta(season_length=SEASON_LENGTH),
        SeasonalNaive(season_length=SEASON_LENGTH),
    ]
    ces_note = None
    try:
        models.insert(-1, AutoCES(season_length=SEASON_LENGTH))
        sf = _sf(models)
        sf.fit(train_y)
    except Exception as exc:  # pragma: no cover - numba/CES quirks
        ces_note = f"AutoCES skipped due to runtime error: {exc}"
        models = [
            sarima,
            AutoARIMA(season_length=SEASON_LENGTH),
            AutoETS(season_length=SEASON_LENGTH),
            AutoTheta(season_length=SEASON_LENGTH),
            SeasonalNaive(season_length=SEASON_LENGTH),
        ]
        sf = _sf(models)
        sf.fit(train_y)
    fcst = sf.predict(h=h, level=LEVELS)

    auto_order = "unknown"
    sarima_order = f"SARIMA{sarima.order}{sarima.seasonal_order}_{SEASON_LENGTH}"
    try:
        fitted_auto = sf.fitted_[0, 1].model_
        if isinstance(fitted_auto, dict):
            arma = fitted_auto.get("arma")
            auto_order = f"arma={arma}" if arma is not None else "AutoARIMA(fitted)"
        else:
            order = getattr(fitted_auto, "order", None)
            seasonal = getattr(fitted_auto, "seasonal_order", None)
            if order is not None:
                auto_order = f"ARIMA{order}{seasonal if seasonal is not None else ''}"
            else:
                auto_order = type(fitted_auto).__name__
    except Exception:
        pass

    model_names = [c for c in fcst.columns if c not in {"unique_id", "ds"} and "-lo-" not in c and "-hi-" not in c]
    return {
        "fitted": sf,
        "forecast": fcst,
        "sarima_order": sarima_order,
        "sarima_order_tuple": (sarima.order, sarima.seasonal_order),
        "autoarima_order": auto_order,
        "model_names": model_names,
        "ces_note": ces_note,
    }


def classical_backtest(train_df: pd.DataFrame, *, n_windows: int = 5, h: int = 12) -> pd.DataFrame:
    """Rolling-origin CV for classical models (stability, not test selection)."""
    train_y = train_df[["unique_id", "ds", "y"]].copy()
    models = [
        AutoARIMA(season_length=SEASON_LENGTH),
        AutoETS(season_length=SEASON_LENGTH),
        AutoTheta(season_length=SEASON_LENGTH),
        SeasonalNaive(season_length=SEASON_LENGTH),
    ]
    sf = _sf(models)
    return sf.cross_validation(h=h, df=train_y, step_size=h, n_windows=n_windows)


def seasonal_factors_from_ets(train_df: pd.DataFrame) -> dict[int, float]:
    """Extract monthly seasonal factors from AutoETS for pattern-recovery checks."""
    train_y = train_df[["unique_id", "ds", "y"]].copy()
    sf = _sf([AutoETS(season_length=SEASON_LENGTH)])
    sf.fit(train_y)
    factors: dict[int, float] = {m: 0.0 for m in range(1, 13)}
    try:
        model = sf.fitted_[0, 0].model_
        # Prefer explicit seasonal component if present
        season = getattr(model, "seas", None) or getattr(model, "season", None)
        if season is not None:
            arr = np.asarray(season, dtype=float).ravel()
            if len(arr) >= 12:
                for i in range(12):
                    factors[i + 1] = float(arr[i])
                return factors
    except Exception:
        pass

    # Fallback: average month effect from demeaned train series
    work = train_y.copy()
    work["month"] = pd.to_datetime(work["ds"]).dt.month
    overall = work["y"].mean()
    for m, g in work.groupby("month"):
        factors[int(m)] = float(g["y"].mean() / overall)
    return factors
