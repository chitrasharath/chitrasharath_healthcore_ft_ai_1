"""MLForecast regression models: exogenous two-stage + univariate ablation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, RollingStd
from mlforecast.target_transforms import Differences, LocalStandardScaler
from mlforecast.utils import PredictionIntervals
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from utilsforecast.losses import mae, rmse
from xgboost import XGBRegressor

from data.forecast.features import DATE_FEATURES, add_engineered_features, assert_no_forbidden_columns

RANDOM_STATE = 42
FREQ = "MS"
LEVELS = [80, 95]


def _attach_residual_intervals(
    mlf: MLForecast,
    prepared: pd.DataFrame,
    preds: pd.DataFrame,
    winner: str,
    *,
    h: int,
) -> pd.DataFrame:
    """Fallback 80/95% bands from rolling-origin residual quantiles."""
    cv = mlf.cross_validation(prepared, n_windows=3, h=min(12, h), step_size=12, static_features=[])
    resid = (cv["y"] - cv[winner]).dropna().to_numpy()
    out = preds.copy()
    if len(resid) == 0:
        return out
    for level, q in ((80, 0.10), (95, 0.025)):
        lo = float(np.quantile(resid, q))
        hi = float(np.quantile(resid, 1 - q))
        out[f"{winner}-lo-{level}"] = out[winner] + lo
        out[f"{winner}-hi-{level}"] = out[winner] + hi
    return out


def _base_learners() -> dict[str, Any]:
    return {
        "rf": RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE, n_jobs=1),
        "xgb": XGBRegressor(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=RANDOM_STATE,
            n_jobs=1,
            verbosity=0,
        ),
        "elasticnet": ElasticNet(alpha=1.0, l1_ratio=0.5, max_iter=5000, random_state=RANDOM_STATE),
    }


def build_mlforecast(learners: dict[str, Any] | None = None) -> MLForecast:
    """Construct MLForecast with Groups A/B lag machinery + Group D transforms."""
    return MLForecast(
        models=learners or _base_learners(),
        freq=FREQ,
        lags=[1, 2, 3, 12],
        lag_transforms={
            1: [RollingMean(window_size=3), RollingStd(window_size=3)],
            12: [RollingMean(window_size=12)],
        },
        date_features=DATE_FEATURES,
        target_transforms=[Differences([12]), LocalStandardScaler()],
        num_threads=1,
    )


MODEL_ID_COLS = ["unique_id", "ds", "y"]
EXOGENOUS_MODEL_COLS = ["visits_count", "trend"]
UNIVARIATE_EXTRA_COLS = ["trend"]


def prepare_frame(frame: pd.DataFrame, *, include_visits: bool = True) -> pd.DataFrame:
    """Engineer features; return the modeling frame MLForecast can forecast with.

    Precomputed visits lags / rev_yoy remain available via ``add_engineered_features``
    for catalog checks. For fitting we pass ``visits_count`` (MLForecast lags it) and
    deterministic ``trend`` only — those are the columns that must appear in ``X_df``.
    """
    engineered = add_engineered_features(frame)
    assert_no_forbidden_columns(engineered)
    cols = list(MODEL_ID_COLS)
    cols.extend(EXOGENOUS_MODEL_COLS if include_visits else UNIVARIATE_EXTRA_COLS)
    return engineered[cols].copy()


def build_future_X_df(
    train_df: pd.DataFrame,
    visits_x_df: pd.DataFrame | None,
    *,
    include_visits: bool,
    h: int,
) -> pd.DataFrame | None:
    """Build horizon exogenous frame with trend (+ forecasted visits when exogenous)."""
    train_sorted = train_df.sort_values("ds")
    last_trend = int(len(train_sorted) - 1)
    if include_visits:
        if visits_x_df is None:
            raise ValueError("visits_x_df required when include_visits=True")
        out = visits_x_df[["unique_id", "ds", "visits_count"]].copy()
    else:
        # Univariate: still need future dates + trend for the trend feature
        last_ds = pd.to_datetime(train_sorted["ds"].iloc[-1])
        future_ds = pd.date_range(last_ds + pd.offsets.MonthBegin(1), periods=h, freq="MS")
        out = pd.DataFrame(
            {
                "unique_id": train_sorted["unique_id"].iloc[0],
                "ds": future_ds,
            }
        )
    out = out.sort_values("ds").reset_index(drop=True)
    out["trend"] = np.arange(last_trend + 1, last_trend + 1 + len(out), dtype=int)
    return out


def cross_validation_select(
    train_df: pd.DataFrame,
    *,
    include_visits: bool = True,
    n_windows: int = 3,
    h: int = 12,
) -> dict[str, Any]:
    """Rolling-origin CV on the training window; pick learner by mean RMSE."""
    prepared = prepare_frame(train_df, include_visits=include_visits)
    mlf = build_mlforecast()
    cv = mlf.cross_validation(
        prepared,
        n_windows=n_windows,
        h=h,
        step_size=h,
        static_features=[],
    )
    model_cols = [c for c in cv.columns if c not in {"unique_id", "ds", "cutoff", "y"}]
    scores: dict[str, dict[str, float]] = {}
    for col in model_cols:
        tmp = cv[["unique_id", "y", col]].dropna().rename(columns={col: "model"})
        scores[col] = {
            "rmse": float(rmse(tmp.assign(unique_id="consolidated"), models=["model"])["model"].mean()),
            "mae": float(mae(tmp.assign(unique_id="consolidated"), models=["model"])["model"].mean()),
        }

    def sort_key(name: str) -> tuple[float, float, int]:
        # Prefer lower RMSE, then MAE, then simpler models (elasticnet < rf < xgb)
        simplicity = {"elasticnet": 0, "rf": 1, "xgb": 2}.get(name, 9)
        return scores[name]["rmse"], scores[name]["mae"], simplicity

    winner = min(scores, key=sort_key)
    return {"winner": winner, "scores": scores, "cv": cv}


def _param_grid(winner: str) -> list[dict[str, Any]]:
    """Light search grids for the CV winner."""
    if winner == "rf":
        return [
            {"n_estimators": 200, "max_depth": None, "max_features": 1.0},
            {"n_estimators": 300, "max_depth": 8, "max_features": "sqrt"},
            {"n_estimators": 400, "max_depth": 12, "max_features": 0.5},
            {"n_estimators": 300, "max_depth": None, "max_features": "sqrt"},
        ]
    if winner == "xgb":
        return [
            {"n_estimators": 200, "max_depth": 2, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9},
            {"n_estimators": 300, "max_depth": 3, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9},
            {"n_estimators": 400, "max_depth": 3, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 0.8},
            {"n_estimators": 300, "max_depth": 2, "learning_rate": 0.1, "subsample": 1.0, "colsample_bytree": 1.0},
        ]
    return [
        {"alpha": 0.5, "l1_ratio": 0.2},
        {"alpha": 1.0, "l1_ratio": 0.5},
        {"alpha": 2.0, "l1_ratio": 0.8},
        {"alpha": 0.1, "l1_ratio": 0.5},
    ]


def light_param_sweep(
    train_df: pd.DataFrame,
    winner: str,
    *,
    include_visits: bool = True,
    n_windows: int = 3,
    h: int = 12,
) -> dict[str, Any]:
    """Light rolling-origin sweep over a small param grid for the winning learner."""
    prepared = prepare_frame(train_df, include_visits=include_visits)
    best_params: dict[str, Any] | None = None
    best_rmse = float("inf")
    trials: list[dict[str, Any]] = []

    for params in _param_grid(winner):
        learner: Any
        if winner == "rf":
            learner = RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1, **params)
        elif winner == "xgb":
            learner = XGBRegressor(random_state=RANDOM_STATE, n_jobs=1, verbosity=0, **params)
        else:
            learner = ElasticNet(max_iter=5000, random_state=RANDOM_STATE, **params)
        mlf = build_mlforecast({winner: learner})
        cv = mlf.cross_validation(prepared, n_windows=n_windows, h=h, step_size=h, static_features=[])
        tmp = cv[["unique_id", "y", winner]].dropna().rename(columns={winner: "model"})
        score = float(rmse(tmp.assign(unique_id="consolidated"), models=["model"])["model"].mean())
        trials.append({"params": params, "rmse": score})
        if score < best_rmse:
            best_rmse = score
            best_params = params

    return {"best_params": best_params or {}, "best_rmse": best_rmse, "trials": trials}


def _make_winner_learner(winner: str, params: dict[str, Any]) -> Any:
    if winner == "rf":
        return RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=1, **params)
    if winner == "xgb":
        return XGBRegressor(random_state=RANDOM_STATE, n_jobs=1, verbosity=0, **params)
    return ElasticNet(max_iter=5000, random_state=RANDOM_STATE, **params)


def fit_predict_revenue(
    train_df: pd.DataFrame,
    *,
    winner: str,
    params: dict[str, Any],
    h: int = 24,
    X_df: pd.DataFrame | None = None,
    include_visits: bool = True,
    with_intervals: bool = True,
) -> dict[str, Any]:
    """Fit the chosen learner and forecast h steps (visits via X_df when exogenous)."""
    prepared = prepare_frame(train_df, include_visits=include_visits)
    learner = _make_winner_learner(winner, params)
    mlf = build_mlforecast({winner: learner})
    future_x = build_future_X_df(train_df, X_df, include_visits=include_visits, h=h)

    if with_intervals:
        # h must match predict horizon; keep n_windows small so Differences([12])+lag_12 leave samples
        mlf.fit(
            prepared,
            static_features=[],
            prediction_intervals=PredictionIntervals(n_windows=2, h=h),
            fitted=True,
        )
        preds = mlf.predict(h=h, X_df=future_x, level=LEVELS)
    else:
        mlf.fit(prepared, static_features=[], fitted=True)
        preds = mlf.predict(h=h, X_df=future_x)

    # If conformal intervals failed to attach, fall back to CV-residual quantiles
    if with_intervals and f"{winner}-lo-80" not in preds.columns:
        preds = _attach_residual_intervals(mlf, prepared, preds, winner, h=h)

    fitted_values = None
    try:
        fitted_values = mlf.forecast_fitted_values()
    except Exception:
        fitted_values = None

    return {
        "model": mlf,
        "predictions": preds,
        "winner": winner,
        "params": params,
        "include_visits": include_visits,
        "fitted_values": fitted_values,
        "X_df_used": None if future_x is None else future_x.copy(),
    }


def perfect_foresight_predict(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    winner: str,
    params: dict[str, Any],
    h: int = 24,
) -> pd.DataFrame:
    """Diagnostic only: use actual test visits in X_df (leakage upper bound)."""
    x_df = test_df[["unique_id", "ds", "visits_count"]].copy()
    result = fit_predict_revenue(
        train_df,
        winner=winner,
        params=params,
        h=h,
        X_df=x_df,
        include_visits=True,
        with_intervals=False,
    )
    return result["predictions"]


def ml_feature_names(mlf: MLForecast) -> list[str]:
    """Best-effort list of feature names used by the fitted MLForecast."""
    names: list[str] = []
    try:
        ts = mlf.ts
        if hasattr(ts, "features_order_"):
            names = list(ts.features_order_)
        elif hasattr(ts, "features"):
            names = list(ts.features)
    except Exception:
        pass
    return names
