"""Temporal CV, learning curves, and fit diagnosis for the revenue forecaster."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from statsforecast import StatsForecast
from statsforecast.models import AutoETS
from utilsforecast.losses import mae as uf_mae
from utilsforecast.losses import rmse as uf_rmse

from data.forecast.clean import load_clean, split_train_test
from data.forecast.features import (
    is_high_season,
    is_low_season,
    month_cos,
    month_sin,
    quarter,
)
from data.forecast.models_mlforecast import make_winner_learner
from data.forecast.models_statsforecast import SEASON_LENGTH, classical_backtest

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval" / "revenue_forecast"
DIAG_DIR = EVAL_DIR / "diagnostics"
METRICS_PATH = EVAL_DIR / "metrics.json"

N_SPLITS = 5
TEST_SIZE = 6
GAP = 0
DIFF_SEASON = 12
LEARNING_PREFIXES = (36, 48, 60, 72, 84)
VAL_BLOCK_START = pd.Timestamp("2023-01-01")
VAL_BLOCK_END = pd.Timestamp("2023-12-01")

# Diagnostic labels (distinct from shipped MLForecast_uni / AutoETS artifact names).
DIAGNOSTIC_ML_NAME = "MLForecast_uni2"
DIAGNOSTIC_ETS_NAME = "AutoETS2"

# Pre-bump shipped selection (3-fold CV) — pin for report continuity.
PINNED_PRIOR = {
    "selection_n_windows": 3,
    "selection_h": 12,
    "uni_winner": "rf",
    "exog_winner": "rf",
    "best_params": {"n_estimators": 200, "max_depth": None, "max_features": 1.0},
}

# Five non-overlapping 6-month blocks shifted later so fold 0 is not starved.
# Span 2022-01…2024-06 (30 months). Fold 5 uses 2024-H1 from the former holdout
# year for diagnostics only — main pipeline selection/holdout metrics stay on 2024–2025.
DATE_VALIDATION_WINDOWS: list[tuple[pd.Timestamp, pd.Timestamp]] = [
    (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-06-01")),
    (pd.Timestamp("2022-07-01"), pd.Timestamp("2022-12-01")),
    (pd.Timestamp("2023-01-01"), pd.Timestamp("2023-06-01")),
    (pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01")),
    (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-01")),
]
DIAG_CV_END = pd.Timestamp("2024-06-01")
PREVIOUS_WINDOWS_NOTE = (
    "Previous design used 2021-07…2023-12 (train-only). Shifted later to thicken fold 0; "
    "last fold scores 2024-01…2024-06 for diagnostics only."
)


@dataclass(frozen=True)
class FoldBounds:
    """One expanding-train / fixed-horizon validation fold."""

    fold: int
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean(err**2)))


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(err)))


def _summary(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def diagnostic_cv_frame(cleaned: pd.DataFrame | None = None) -> pd.DataFrame:
    """Series for diagnostic temporal CV: history through ``DIAG_CV_END`` (2024-06).

    Includes early 2024 so five shifted 6-month folds fit with a thicker fold-0 train.
    """
    if cleaned is None:
        cleaned = load_clean()
    work = cleaned.copy()
    work["ds"] = pd.to_datetime(work["ds"])
    out = work.loc[work["ds"] <= DIAG_CV_END].sort_values("ds").reset_index(drop=True)
    if out["ds"].max() < DIAG_CV_END:
        raise ValueError(f"Diagnostic CV frame must reach {DIAG_CV_END.date()}, got {out['ds'].max().date()}")
    return out


def defined_validation_windows() -> list[FoldBounds]:
    """Date-first source of truth for the five 6-month validation blocks."""
    folds: list[FoldBounds] = []
    for i, (start, end) in enumerate(DATE_VALIDATION_WINDOWS):
        expected = pd.date_range(start, end, freq="MS")
        if len(expected) != TEST_SIZE:
            raise ValueError(f"Window {i} is not {TEST_SIZE} months: {start}..{end}")
        folds.append(
            FoldBounds(
                fold=i,
                train_end=start - pd.offsets.MonthBegin(1),
                val_start=start,
                val_end=end,
            )
        )
    return folds


def build_univariate_feature_frame(train_df: pd.DataFrame) -> pd.DataFrame:
    """Causal feature matrix for univariate ML diagnosis (Groups A+B style).

    Lag/rolling columns use ``.shift()`` so row ``t`` depends only on data ``≤ t-1``.
    Calendar features are deterministic from ``ds``. Initial rows lacking ``lag_12``
    are dropped by the caller after target differencing alignment.
    """
    work = train_df.copy().sort_values("ds").reset_index(drop=True)
    work["ds"] = pd.to_datetime(work["ds"])
    dates = pd.DatetimeIndex(work["ds"])
    y = work["y"].astype(float)

    out = pd.DataFrame({"ds": work["ds"].values, "y": y.values})
    out["trend"] = np.arange(len(out), dtype=int)
    out["month"] = dates.month
    out["year"] = dates.year
    out["quarter"] = quarter(dates).to_numpy()
    out["month_sin"] = month_sin(dates).to_numpy()
    out["month_cos"] = month_cos(dates).to_numpy()
    out["is_high_season"] = is_high_season(dates).to_numpy()
    out["is_low_season"] = is_low_season(dates).to_numpy()

    # Raw-revenue lags for leakage asserts; model features use differenced lags below.
    out["rev_lag_1"] = y.shift(1)
    out["rev_lag_2"] = y.shift(2)
    out["rev_lag_3"] = y.shift(3)
    out["rev_lag_12"] = y.shift(12)
    out["rev_roll_mean_3"] = y.shift(1).rolling(3).mean()
    out["rev_roll_mean_12"] = y.shift(1).rolling(12).mean()
    out["rev_roll_std_3"] = y.shift(1).rolling(3).std()
    out["rev_yoy"] = (y.shift(1) / y.shift(13)) - 1.0
    return out


def assert_features_not_same_month_target(frame: pd.DataFrame) -> None:
    """Gotcha #1: no feature column may equal same-month target."""
    y = frame["y"].to_numpy(dtype=float)
    skip = {"ds", "y"}
    for col in frame.columns:
        if col in skip:
            continue
        vals = frame[col].to_numpy(dtype=float)
        mask = np.isfinite(vals) & np.isfinite(y)
        if mask.sum() < 3:
            continue
        if np.allclose(vals[mask], y[mask], rtol=0, atol=1e-9):
            raise AssertionError(f"Feature {col!r} equals same-month target (leakage)")


def _seasonal_diff(y: np.ndarray, season: int = DIFF_SEASON) -> np.ndarray:
    out = np.full_like(y, np.nan, dtype=float)
    out[season:] = y[season:] - y[:-season]
    return out


def _invert_seasonal_diff(diff_hat: float, y_lag_season: float) -> float:
    return float(diff_hat + y_lag_season)


class _FoldScaler:
    """Local standard scaler fit on train differenced targets only."""

    def __init__(self) -> None:
        self.mean_ = 0.0
        self.std_ = 1.0

    def fit(self, values: np.ndarray) -> _FoldScaler:
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        self.mean_ = float(arr.mean()) if len(arr) else 0.0
        std = float(arr.std(ddof=0)) if len(arr) else 1.0
        self.std_ = std if std > 1e-12 else 1.0
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        return (np.asarray(values, dtype=float) - self.mean_) / self.std_

    def inverse(self, values: np.ndarray | float) -> np.ndarray | float:
        return np.asarray(values, dtype=float) * self.std_ + self.mean_


FEATURE_COLS = [
    "trend",
    "month",
    "year",
    "quarter",
    "month_sin",
    "month_cos",
    "is_high_season",
    "is_low_season",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_12",
    "rolling_mean_lag1_3",
    "rolling_std_lag1_3",
    "rolling_mean_lag12_12",
]


def _features_from_scaled_diff(
    base: pd.DataFrame,
    scaled_diff: np.ndarray,
) -> pd.DataFrame:
    """Build MLForecast-like lag features from a scaled differenced series."""
    s = pd.Series(scaled_diff)
    feat = base[
        [
            "ds",
            "y",
            "trend",
            "month",
            "year",
            "quarter",
            "month_sin",
            "month_cos",
            "is_high_season",
            "is_low_season",
        ]
    ].copy()
    feat["lag_1"] = s.shift(1)
    feat["lag_2"] = s.shift(2)
    feat["lag_3"] = s.shift(3)
    feat["lag_12"] = s.shift(12)
    feat["rolling_mean_lag1_3"] = s.shift(1).rolling(3).mean()
    feat["rolling_std_lag1_3"] = s.shift(1).rolling(3).std()
    feat["rolling_mean_lag12_12"] = s.shift(12).rolling(12).mean()
    feat["target_scaled"] = scaled_diff
    return feat


def usable_feature_matrix(train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Causal matrix with per-row-causal features; drop early rows lacking lag history.

    Target transform is applied later **per fold** — this frame carries raw ``y`` and
    calendar/raw-lag columns for alignment and leakage checks. Modeling features are
    rebuilt per fold from fold-local scaled differences.
    """
    base = build_univariate_feature_frame(train_df)
    assert_features_not_same_month_target(base)
    # Need enough history for seasonal diff + lag_12 on the differenced series (~24 months)
    start = DIFF_SEASON + DIFF_SEASON
    usable = base.iloc[start:].copy().reset_index(drop=True)
    usable["orig_idx"] = np.arange(start, len(base))
    return usable, base


def time_series_split_folds(
    usable: pd.DataFrame,
    *,
    n_splits: int = N_SPLITS,
    test_size: int = TEST_SIZE,
    gap: int = GAP,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return (train_idx, test_idx) pairs from sklearn TimeSeriesSplit."""
    splitter = TimeSeriesSplit(n_splits=n_splits, test_size=test_size, gap=gap)
    return list(splitter.split(usable))


def assert_split_matches_date_windows(
    usable: pd.DataFrame,
    folds: list[tuple[np.ndarray, np.ndarray]],
    windows: list[FoldBounds] | None = None,
) -> None:
    """Gotcha #4: TimeSeriesSplit test blocks must equal the date-defined windows."""
    windows = windows or defined_validation_windows()
    if len(folds) != len(windows):
        raise AssertionError(f"Expected {len(windows)} folds, got {len(folds)}")
    for (train_idx, test_idx), window in zip(folds, windows, strict=True):
        test_ds = pd.to_datetime(usable.iloc[test_idx]["ds"])
        expected = pd.date_range(window.val_start, window.val_end, freq="MS")
        if not test_ds.reset_index(drop=True).equals(pd.Series(expected)):
            raise AssertionError(
                f"Fold {window.fold} test ds {list(test_ds)} != expected {list(expected)}"
            )
        train_ds = pd.to_datetime(usable.iloc[train_idx]["ds"])
        if train_ds.max() >= test_ds.min():
            raise AssertionError(
                f"Fold {window.fold}: train max {train_ds.max()} not < test min {test_ds.min()}"
            )


def _recursive_forecast_block(
    base: pd.DataFrame,
    train_idx_in_base: np.ndarray,
    test_idx_in_base: np.ndarray,
    learner: Any,
    scaler: _FoldScaler,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit on train rows; recursively predict the test block (gotcha #3).

    Returns ``(y_train, yhat_train, y_val, yhat_val)`` in raw revenue space.
    """
    y_raw = base["y"].to_numpy(dtype=float).copy()
    y_diff = _seasonal_diff(y_raw)
    # Fit scaler on train differenced targets only
    train_diff = y_diff[train_idx_in_base]
    scaler.fit(train_diff[np.isfinite(train_diff)])

    scaled = np.full_like(y_diff, np.nan, dtype=float)
    finite = np.isfinite(y_diff)
    scaled[finite] = scaler.transform(y_diff[finite])

    feat = _features_from_scaled_diff(base, scaled)
    # Drop rows without lag_12
    train_mask = np.isin(np.arange(len(feat)), train_idx_in_base)
    train_rows = feat.loc[train_mask].dropna(subset=FEATURE_COLS + ["target_scaled"])
    X_train = train_rows[FEATURE_COLS].to_numpy(dtype=float)
    y_train = train_rows["target_scaled"].to_numpy(dtype=float)
    learner.fit(X_train, y_train)

    # In-sample train predictions (one-shot on train features — actual past lags OK)
    train_pred_scaled = learner.predict(X_train)
    train_pred_diff = np.asarray(scaler.inverse(train_pred_scaled), dtype=float)
    train_actual = train_rows["y"].to_numpy(dtype=float)
    # Invert difference using each row's y_{t-12}
    train_orig_idx = train_rows.index.to_numpy()
    train_pred_raw = np.array(
        [
            _invert_seasonal_diff(train_pred_diff[i], y_raw[idx - DIFF_SEASON])
            for i, idx in enumerate(train_orig_idx)
        ],
        dtype=float,
    )

    # Working raw series: overwrite test positions as we predict
    working_y = y_raw.copy()
    val_preds: list[float] = []
    val_actuals: list[float] = []

    for idx in test_idx_in_base:
        # Recompute diff/scaled from working_y (predictions feed forward)
        w_diff = _seasonal_diff(working_y)
        w_scaled = np.full_like(w_diff, np.nan, dtype=float)
        fin = np.isfinite(w_diff)
        w_scaled[fin] = scaler.transform(w_diff[fin])
        feat_step = _features_from_scaled_diff(base, w_scaled)
        row = feat_step.loc[idx, FEATURE_COLS]
        if row.isna().any():
            raise RuntimeError(f"Missing features at index {idx} ds={base.loc[idx, 'ds']}")
        pred_scaled = float(learner.predict(row.to_numpy(dtype=float).reshape(1, -1))[0])
        pred_diff = float(scaler.inverse(pred_scaled))
        pred_raw = _invert_seasonal_diff(pred_diff, working_y[idx - DIFF_SEASON])
        working_y[idx] = pred_raw
        val_preds.append(pred_raw)
        val_actuals.append(float(y_raw[idx]))

    return train_actual, train_pred_raw, np.asarray(val_actuals), np.asarray(val_preds)


def run_ml_temporal_cv(
    cv_df: pd.DataFrame,
    *,
    winner: str,
    params: dict[str, Any],
    gap: int = GAP,
) -> dict[str, Any]:
    """5-fold TimeSeriesSplit CV with fold-local transforms + recursive forecasts."""
    usable, base = usable_feature_matrix(cv_df)
    folds = time_series_split_folds(usable, gap=gap)
    windows = defined_validation_windows()
    # Date alignment is required for the scored path (gap=0); gap=1 stretch may shift train only.
    if gap == 0:
        assert_split_matches_date_windows(usable, folds, windows)

    fold_rows: list[dict[str, Any]] = []
    for (train_u, test_u), window in zip(folds, windows, strict=True):
        # Map usable indices → base indices
        train_base = usable.iloc[train_u]["orig_idx"].to_numpy(dtype=int)
        test_base = usable.iloc[test_u]["orig_idx"].to_numpy(dtype=int)
        learner = make_winner_learner(winner, params)
        scaler = _FoldScaler()
        y_tr, yhat_tr, y_va, yhat_va = _recursive_forecast_block(
            base, train_base, test_base, learner, scaler
        )
        fold_rows.append(
            {
                "fold": window.fold,
                "val_start": str(window.val_start.date()),
                "val_end": str(window.val_end.date()),
                "train_end": str(window.train_end.date()),
                "n_train": int(len(y_tr)),
                "n_val": int(len(y_va)),
                "train_mae": _mae(y_tr, yhat_tr),
                "train_rmse": _rmse(y_tr, yhat_tr),
                "val_mae": _mae(y_va, yhat_va),
                "val_rmse": _rmse(y_va, yhat_va),
            }
        )

    return {
        "engine": "sklearn.TimeSeriesSplit",
        "model": f"{DIAGNOSTIC_ML_NAME}({winner})",
        "winner": winner,
        "params": params,
        "n_splits": N_SPLITS,
        "test_size": TEST_SIZE,
        "gap": gap,
        "folds": fold_rows,
        "val_rmse": _summary([f["val_rmse"] for f in fold_rows]),
        "val_mae": _summary([f["val_mae"] for f in fold_rows]),
        "train_rmse": _summary([f["train_rmse"] for f in fold_rows]),
        "train_mae": _summary([f["train_mae"] for f in fold_rows]),
        "validation_windows": [
            {"fold": w.fold, "start": str(w.val_start.date()), "end": str(w.val_end.date())}
            for w in windows
        ],
    }


def run_autoets_temporal_cv(cv_df: pd.DataFrame) -> dict[str, Any]:
    """Reuse classical_backtest (StatsForecast CV) for AutoETS with h=6."""
    windows = defined_validation_windows()
    cv = classical_backtest(cv_df, n_windows=N_SPLITS, h=TEST_SIZE)
    if "AutoETS" not in cv.columns:
        raise RuntimeError("classical_backtest did not return AutoETS column")

    fold_rows: list[dict[str, Any]] = []
    cutoffs = sorted(pd.to_datetime(cv["cutoff"].unique()))
    if len(cutoffs) < N_SPLITS:
        raise AssertionError(f"Expected ≥{N_SPLITS} cutoffs, got {len(cutoffs)}")

    train_y = cv_df[["unique_id", "ds", "y"]].copy()
    train_y["ds"] = pd.to_datetime(train_y["ds"])
    train_y["y"] = train_y["y"].astype(float)

    for i, cutoff in enumerate(cutoffs):
        block = cv.loc[pd.to_datetime(cv["cutoff"]) == cutoff].sort_values("ds")
        val_ds = pd.to_datetime(block["ds"])
        expected = pd.date_range(windows[i].val_start, windows[i].val_end, freq="MS")
        if not val_ds.reset_index(drop=True).equals(pd.Series(expected)):
            raise AssertionError(
                f"AutoETS fold {i} ds {list(val_ds)} != expected {list(expected)}"
            )
        y_va = block["y"].to_numpy(dtype=float)
        yhat_va = block["AutoETS"].to_numpy(dtype=float)

        # In-sample train error: fit AutoETS on history through cutoff
        hist = train_y.loc[train_y["ds"] <= cutoff].copy()
        sf = StatsForecast(models=[AutoETS(season_length=SEASON_LENGTH)], freq="MS", n_jobs=1)
        fcst = sf.forecast(df=hist, h=TEST_SIZE, fitted=True)
        fitted = sf.forecast_fitted_values()
        # Align fitted to hist
        merged = hist.merge(fitted[["unique_id", "ds", "AutoETS"]], on=["unique_id", "ds"], how="inner")
        y_tr = merged["y"].to_numpy(dtype=float)
        yhat_tr = merged["AutoETS"].to_numpy(dtype=float)

        # Validation preds from classical_backtest CV frame (already scored)
        _ = fcst  # forecast call required to materialize fitted values

        fold_rows.append(
            {
                "fold": i,
                "cutoff": str(pd.Timestamp(cutoff).date()),
                "val_start": str(windows[i].val_start.date()),
                "val_end": str(windows[i].val_end.date()),
                "n_train": int(len(y_tr)),
                "n_val": int(len(y_va)),
                "train_mae": _mae(y_tr, yhat_tr),
                "train_rmse": _rmse(y_tr, yhat_tr),
                "val_mae": _mae(y_va, yhat_va),
                "val_rmse": _rmse(y_va, yhat_va),
            }
        )

    return {
        "engine": "StatsForecast.cross_validation",
        "model": DIAGNOSTIC_ETS_NAME,
        "engine_model": "AutoETS",
        "n_windows": N_SPLITS,
        "h": TEST_SIZE,
        "step_size": TEST_SIZE,
        "folds": fold_rows,
        "val_rmse": _summary([f["val_rmse"] for f in fold_rows]),
        "val_mae": _summary([f["val_mae"] for f in fold_rows]),
        "train_rmse": _summary([f["train_rmse"] for f in fold_rows]),
        "train_mae": _summary([f["train_mae"] for f in fold_rows]),
        "validation_windows": [
            {"fold": w.fold, "start": str(w.val_start.date()), "end": str(w.val_end.date())}
            for w in windows
        ],
        "cutoffs": [str(pd.Timestamp(c).date()) for c in cutoffs],
    }


def align_validation_windows(ml_result: dict[str, Any], ets_result: dict[str, Any]) -> None:
    """Assert both engines scored the same calendar months."""
    ml_wins = [(f["val_start"], f["val_end"]) for f in ml_result["folds"]]
    ets_wins = [(f["val_start"], f["val_end"]) for f in ets_result["folds"]]
    if ml_wins != ets_wins:
        raise AssertionError(f"Validation windows differ: ML={ml_wins} ETS={ets_wins}")


def _ml_forecast_horizon(
    base: pd.DataFrame,
    train_end_idx: int,
    horizon_idx: np.ndarray,
    winner: str,
    params: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit on prefix ``0..train_end_idx`` inclusive; recursively forecast ``horizon_idx``."""
    train_idx = np.arange(0, train_end_idx + 1)
    # Require enough history inside train for features
    usable_train = train_idx[train_idx >= DIFF_SEASON + DIFF_SEASON]
    if len(usable_train) < 12:
        raise RuntimeError("Prefix too short for differencing + lag_12")
    learner = make_winner_learner(winner, params)
    scaler = _FoldScaler()
    return _recursive_forecast_block(base, usable_train, horizon_idx, learner, scaler)


def run_learning_curve_ml(
    train_df: pd.DataFrame,
    *,
    winner: str,
    params: dict[str, Any],
    prefixes: tuple[int, ...] = LEARNING_PREFIXES,
) -> dict[str, Any]:
    """Expanding-window learning curve with fixed 2023 validation block."""
    base = build_univariate_feature_frame(train_df)
    ds = pd.to_datetime(base["ds"])
    val_mask = (ds >= VAL_BLOCK_START) & (ds <= VAL_BLOCK_END)
    horizon_idx = np.where(val_mask)[0]
    if len(horizon_idx) != 12:
        raise RuntimeError(f"Expected 12-month val block, got {len(horizon_idx)}")

    points: list[dict[str, Any]] = []
    for s in prefixes:
        # First s months must end before 2023-01
        prefix = base.iloc[:s]
        if pd.to_datetime(prefix["ds"].iloc[-1]) >= VAL_BLOCK_START:
            raise AssertionError(f"Prefix s={s} overlaps validation block")
        train_end_idx = s - 1
        y_tr, yhat_tr, y_va, yhat_va = _ml_forecast_horizon(
            base, train_end_idx, horizon_idx, winner, params
        )
        points.append(
            {
                "train_size": s,
                "train_end": str(pd.to_datetime(prefix["ds"].iloc[-1]).date()),
                "train_mae": _mae(y_tr, yhat_tr),
                "train_rmse": _rmse(y_tr, yhat_tr),
                "val_mae": _mae(y_va, yhat_va),
                "val_rmse": _rmse(y_va, yhat_va),
            }
        )
    return {"model": f"{DIAGNOSTIC_ML_NAME}({winner})", "winner": winner, "params": params, "points": points}


def run_learning_curve_autoets(
    train_df: pd.DataFrame,
    *,
    prefixes: tuple[int, ...] = LEARNING_PREFIXES,
) -> dict[str, Any]:
    """Expanding-window AutoETS learning curve vs fixed 2023 block."""
    work = train_df.copy().sort_values("ds").reset_index(drop=True)
    work["ds"] = pd.to_datetime(work["ds"])
    val = work.loc[(work["ds"] >= VAL_BLOCK_START) & (work["ds"] <= VAL_BLOCK_END)]
    if len(val) != 12:
        raise RuntimeError(f"Expected 12-month val block, got {len(val)}")

    points: list[dict[str, Any]] = []
    for s in prefixes:
        prefix = work.iloc[:s][["unique_id", "ds", "y"]].copy()
        if prefix["ds"].iloc[-1] >= VAL_BLOCK_START:
            raise AssertionError(f"Prefix s={s} overlaps validation block")
        sf = StatsForecast(models=[AutoETS(season_length=SEASON_LENGTH)], freq="MS", n_jobs=1)
        fcst = sf.forecast(df=prefix, h=12, fitted=True)
        fitted = sf.forecast_fitted_values()
        merged = prefix.merge(fitted[["unique_id", "ds", "AutoETS"]], on=["unique_id", "ds"])
        y_va = val["y"].to_numpy(dtype=float)
        yhat_va = fcst.sort_values("ds")["AutoETS"].to_numpy(dtype=float)
        points.append(
            {
                "train_size": s,
                "train_end": str(prefix["ds"].iloc[-1].date()),
                "train_mae": _mae(merged["y"].to_numpy(), merged["AutoETS"].to_numpy()),
                "train_rmse": _rmse(merged["y"].to_numpy(), merged["AutoETS"].to_numpy()),
                "val_mae": _mae(y_va, yhat_va),
                "val_rmse": _rmse(y_va, yhat_va),
            }
        )
    return {"model": DIAGNOSTIC_ETS_NAME, "engine_model": "AutoETS", "points": points}


def run_learning_curve_elasticnet(
    train_df: pd.DataFrame,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Side-check learning curve for ElasticNet (variance-reduction alternative)."""
    en_params = params or {"alpha": 1.0, "l1_ratio": 0.5}
    return run_learning_curve_ml(train_df, winner="elasticnet", params=en_params)


def plot_learning_curve(curve: dict[str, Any], path: Path) -> Path:
    """Save train vs validation MAE/RMSE against training size."""
    points = curve["points"]
    sizes = [p["train_size"] for p in points]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, metric in zip(axes, ("mae", "rmse"), strict=True):
        ax.plot(sizes, [p[f"train_{metric}"] for p in points], marker="o", label=f"train {metric}")
        ax.plot(sizes, [p[f"val_{metric}"] for p in points], marker="s", label=f"val {metric}")
        ax.set_xlabel("Training size (months)")
        ax.set_ylabel(metric.upper() + " (USD)")
        ax.set_title(f"{curve['model']} — {metric.upper()}")
        ax.legend()
        ax.grid(True, alpha=0.3)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def classify_fit(
    cv_result: dict[str, Any],
    curve: dict[str, Any],
    *,
    is_tree: bool = False,
) -> dict[str, Any]:
    """Classify well-fitted / underfitting / overfitting from curve + CV spread.

    Primary signal is the **CV** train/val gap and fold std. The learning curve's
    fixed 2023 block is a long multi-step horizon from early prefixes (trend gap),
    so large LC gaps alone do not mean classical overfitting.
    """
    points = curve["points"]
    last = points[-1]
    lc_train = last["train_rmse"]
    lc_val = last["val_rmse"]
    lc_gap = lc_val - lc_train
    lc_rel_gap = lc_gap / lc_val if lc_val > 0 else 0.0

    cv_std = float(cv_result["val_rmse"]["std"])
    cv_mean = float(cv_result["val_rmse"]["mean"])
    cv_train = float(cv_result["train_rmse"]["mean"])
    cv_cv = cv_std / cv_mean if cv_mean > 0 else 0.0
    cv_gap = cv_mean - cv_train
    cv_rel_gap = cv_gap / cv_mean if cv_mean > 0 else 0.0

    # Learning-curve trajectory (skip noisy s=36)
    stable = points[1:] if len(points) > 1 else points
    lc_val_improves = stable[-1]["val_rmse"] < stable[0]["val_rmse"] * 0.85

    if is_tree:
        # Near-zero train error (LC or CV) with large val gap → overfitting signature
        memorizes = lc_train < 0.15 * max(lc_val, 1.0) or cv_train < 0.5 * cv_mean
        if memorizes and (cv_rel_gap > 0.35 or lc_rel_gap > 0.4):
            verdict = "overfitting"
        elif cv_train > 0.85 * cv_mean and cv_mean > 150_000:
            verdict = "underfitting"
        elif cv_rel_gap < 0.3 and cv_cv < 0.35:
            verdict = "well-fitted"
        else:
            verdict = "overfitting" if cv_rel_gap > 0.35 else "well-fitted"
    else:
        # Classical: prefer CV gap; LC long-horizon gap is expected with upward trend
        if cv_train > 0.85 * cv_mean and cv_mean > 150_000 and not lc_val_improves:
            verdict = "underfitting"
        elif cv_rel_gap > 0.45 and cv_cv > 0.4:
            verdict = "overfitting"
        elif cv_rel_gap < 0.4 and cv_cv < 0.45:
            verdict = "well-fitted"
        else:
            verdict = "well-fitted" if cv_rel_gap < 0.4 else "overfitting"

    return {
        "verdict": verdict,
        "train_rmse_last_prefix": lc_train,
        "val_rmse_last_prefix": lc_val,
        "gap": lc_gap,
        "relative_gap": lc_rel_gap,
        "cv_train_rmse_mean": cv_train,
        "cv_rmse_mean": cv_mean,
        "cv_rmse_std": cv_std,
        "cv_gap": cv_gap,
        "cv_relative_gap": cv_rel_gap,
        "cv_coefficient_of_variation": cv_cv,
        "learning_curve_val_improves": lc_val_improves,
        "notes": (
            "For tree models, near-zero train RMSE is the overfitting signature; "
            "diagnose on the val−train gap, not absolute train error. "
            "Do not compare tree train error to AutoETS in-sample residuals as like-for-like."
            if is_tree
            else (
                "Classical AutoETS train error is genuine in-sample residual, not memorization. "
                "Learning-curve val error from early prefixes includes a long multi-step horizon "
                "into 2023 (trend), so CV train/val gap is the primary fit signal."
            )
        ),
    }


def corrective_actions(verdict: str, *, model_name: str) -> list[str]:
    """Report-only actions matched to the diagnosis (specs §11)."""
    if verdict == "overfitting":
        return [
            f"Constrain {model_name}: set max_depth (e.g. 3–5), raise min_samples_leaf, "
            "max_features < 1.0, and/or fewer estimators.",
            "Prune the feature set (many lags/rollings on ~84 effective rows).",
            "Prefer a more regularized learner (ElasticNet) or lean on classical AutoETS.",
            "Add drift monitoring (PSI); more historical data is not available (fixed 120 months).",
        ]
    if verdict == "underfitting":
        return [
            f"Increase capacity/features for {model_name} (richer lags/interactions).",
            "Reduce over-aggressive regularization if present.",
            "More data is not a lever — only 120 monthly points exist.",
        ]
    return [
        f"Ship classical AutoETS (diagnosed here as {model_name}); keep this CV/learning-curve suite as a regression guard."
        if model_name == DIAGNOSTIC_ETS_NAME
        else f"Ship {model_name}; keep this CV/learning-curve suite as a regression guard.",
        "Monitor PSI for regime shift; revisit only if new data changes the pattern.",
        "More data is not available as a lever (fixed 120 months).",
    ]


def seasonal_naive_fold_skill(cv_df: pd.DataFrame) -> dict[str, Any]:
    """Stretch: SeasonalNaive RMSE per date-aligned fold for skill context."""
    cv = classical_backtest(cv_df, n_windows=N_SPLITS, h=TEST_SIZE)
    rows: list[dict[str, Any]] = []
    for i, cutoff in enumerate(sorted(pd.to_datetime(cv["cutoff"].unique()))):
        block = cv.loc[pd.to_datetime(cv["cutoff"]) == cutoff]
        tmp = block[["unique_id", "y", "SeasonalNaive"]].dropna().rename(
            columns={"SeasonalNaive": "model"}
        )
        rows.append(
            {
                "fold": i,
                "cutoff": str(pd.Timestamp(cutoff).date()),
                "val_rmse": float(uf_rmse(tmp, models=["model"])["model"].mean()),
                "val_mae": float(uf_mae(tmp, models=["model"])["model"].mean()),
            }
        )
    return {"model": "SeasonalNaive", "folds": rows, "val_rmse": _summary([r["val_rmse"] for r in rows])}


def plot_fold_rmse_strip(cv_folds: dict[str, Any], path: Path) -> Path:
    """Stretch: per-fold validation RMSE strip plot for diagnosed models."""
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    for label, key in ((DIAGNOSTIC_ML_NAME, "ml"), (DIAGNOSTIC_ETS_NAME, "autoets")):
        folds = cv_folds[key]["folds"]
        xs = [f["fold"] for f in folds]
        ys = [f["val_rmse"] for f in folds]
        ax.scatter(xs, ys, label=label, s=60)
        ax.plot(xs, ys, alpha=0.4)
    ax.set_xlabel("Fold")
    ax.set_ylabel("Validation RMSE (USD)")
    ax.set_title("Per-fold validation RMSE")
    ax.legend()
    ax.grid(True, alpha=0.3)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def load_metrics(path: Path = METRICS_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def resolve_diagnostic_target(metrics: dict[str, Any]) -> dict[str, Any]:
    """Diagnose the 5-fold uni winner; pin and note prior 3-fold selection."""
    uni = metrics.get("mlforecast_cv_uni", {})
    winner = uni.get("winner") or metrics.get("recommendation", {}).get("regression_learner_uni", "rf")
    # Prefer uni sweep params when present; else exog sweep / pinned
    sweep = metrics.get("mlforecast_cv_uni", {}).get("sweep") or metrics.get("mlforecast_cv_exog", {}).get(
        "sweep", {}
    )
    params = dict(sweep.get("best_params") or PINNED_PRIOR["best_params"])
    # JSON null → Python None already; ensure max_depth key OK for RF
    flipped = winner != PINNED_PRIOR["uni_winner"] or params != PINNED_PRIOR["best_params"]
    # Param compare tolerant of null/None
    prior_params = PINNED_PRIOR["best_params"]
    params_flipped = (
        params.get("n_estimators") != prior_params.get("n_estimators")
        or params.get("max_features") != prior_params.get("max_features")
        or params.get("max_depth") != prior_params.get("max_depth")
    )
    winner_flipped = winner != PINNED_PRIOR["uni_winner"]
    return {
        "diagnose_winner": winner,
        "diagnose_params": params,
        "pinned_prior": PINNED_PRIOR,
        "winner_changed": bool(winner_flipped),
        "params_changed": bool(params_flipped),
        "selection_changed": bool(winner_flipped or params_flipped or flipped),
        "include_visits": False,
        "model_label": DIAGNOSTIC_ML_NAME,
        "model_label_with_learner": f"{DIAGNOSTIC_ML_NAME}({winner})",
    }


def run_all(
    *,
    train_df: pd.DataFrame | None = None,
    metrics: dict[str, Any] | None = None,
    with_stretch: bool = True,
) -> dict[str, Any]:
    """Run full diagnostic suite and write artifacts under ``diagnostics/``."""
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    cleaned = load_clean()
    if train_df is None:
        train_df, _ = split_train_test(cleaned)
    cv_df = diagnostic_cv_frame(cleaned)
    if metrics is None:
        metrics = load_metrics()

    target = resolve_diagnostic_target(metrics)
    winner = target["diagnose_winner"]
    params = target["diagnose_params"]

    ml_cv = run_ml_temporal_cv(cv_df, winner=winner, params=params, gap=GAP)
    ets_cv = run_autoets_temporal_cv(cv_df)
    align_validation_windows(ml_cv, ets_cv)

    gap_ab: dict[str, Any] | None = None
    if with_stretch:
        try:
            ml_gap1 = run_ml_temporal_cv(cv_df, winner=winner, params=params, gap=1)
            gap_ab = {
                "gap0_val_rmse": ml_cv["val_rmse"],
                "gap1_val_rmse": ml_gap1["val_rmse"],
                "note": "1-period embargo between train and validation (stretch A/B).",
            }
        except Exception as exc:  # pragma: no cover - best effort stretch
            gap_ab = {"error": str(exc)}

    ml_curve = run_learning_curve_ml(train_df, winner=winner, params=params)
    ets_curve = run_learning_curve_autoets(train_df)

    ml_png = DIAG_DIR / "learning_curve_mlforecast_uni2.png"
    ets_png = DIAG_DIR / "learning_curve_autoets2.png"
    plot_learning_curve(ml_curve, ml_png)
    plot_learning_curve(ets_curve, ets_png)

    ml_fit = classify_fit(ml_cv, ml_curve, is_tree=(winner in {"rf", "xgb"}))
    ets_fit = classify_fit(ets_cv, ets_curve, is_tree=False)

    en_curve = None
    en_png = None
    if ml_fit["verdict"] == "overfitting":
        en_curve = run_learning_curve_elasticnet(train_df)
        en_png = DIAG_DIR / "learning_curve_elasticnet.png"
        plot_learning_curve(en_curve, en_png)

    naive_skill = seasonal_naive_fold_skill(cv_df) if with_stretch else None

    display_label = target["model_label_with_learner"]
    fold0_n_train = int(ml_cv["folds"][0]["n_train"]) if ml_cv["folds"] else None

    cv_payload = {
        "n_splits": N_SPLITS,
        "test_size_months": TEST_SIZE,
        "gap": GAP,
        "cv_frame_end": str(DIAG_CV_END.date()),
        "window_redesign": PREVIOUS_WINDOWS_NOTE,
        "fold0_n_train": fold0_n_train,
        "selection_cv_defaults": {"n_windows": 5, "h": 6, "step_size": 6},
        "pinned_prior_selection": PINNED_PRIOR,
        "diagnostic_target": target,
        "diagnostic_ets_name": DIAGNOSTIC_ETS_NAME,
        "ml": ml_cv,
        "autoets": ets_cv,
        "gap_ablation": gap_ab,
        "seasonal_naive_skill": naive_skill,
        "mean_monthly_revenue_train": float(train_df["y"].mean()),
    }
    (DIAG_DIR / "cv_folds.json").write_text(json.dumps(cv_payload, indent=2, sort_keys=True, default=str))

    curve_payload = {
        "validation_block": {
            "start": str(VAL_BLOCK_START.date()),
            "end": str(VAL_BLOCK_END.date()),
        },
        "prefixes": list(LEARNING_PREFIXES),
        "ml": ml_curve,
        "autoets": ets_curve,
        "elasticnet": en_curve,
    }
    (DIAG_DIR / "learning_curve.json").write_text(
        json.dumps(curve_payload, indent=2, sort_keys=True, default=str)
    )

    if with_stretch:
        plot_fold_rmse_strip(cv_payload, DIAG_DIR / "fold_rmse_strip.png")

    diagnosis = {
        "ml": {
            **ml_fit,
            "model": display_label,
            "corrective_actions": corrective_actions(ml_fit["verdict"], model_name=display_label),
        },
        "autoets": {
            **ets_fit,
            "model": DIAGNOSTIC_ETS_NAME,
            "corrective_actions": corrective_actions(ets_fit["verdict"], model_name=DIAGNOSTIC_ETS_NAME),
        },
    }
    (DIAG_DIR / "fit_classification.json").write_text(
        json.dumps(diagnosis, indent=2, sort_keys=True, default=str)
    )

    return {
        "cv": cv_payload,
        "learning_curve": curve_payload,
        "diagnosis": diagnosis,
        "artifacts": {
            "cv_folds": str(DIAG_DIR / "cv_folds.json"),
            "learning_curve": str(DIAG_DIR / "learning_curve.json"),
            "ml_png": str(ml_png),
            "ets_png": str(ets_png),
            "en_png": str(en_png) if en_png else None,
        },
    }


def write_diagnosis_report(
    diag: dict[str, Any],
    metrics: dict[str, Any] | None = None,
    path: Path | None = None,
) -> Path:
    """Write ``cv_fit_diagnosis_report.md`` per specs §10."""
    path = path or (EVAL_DIR / "cv_fit_diagnosis_report.md")
    metrics = metrics or {}
    cv = diag["cv"]
    lc = diag["learning_curve"]
    fit = diag["diagnosis"]
    target = cv["diagnostic_target"]
    ml = cv["ml"]
    ets = cv["autoets"]
    mean_rev = float(cv.get("mean_monthly_revenue_train") or 0.0)
    ml_label = target.get("model_label_with_learner") or target.get("model_label") or DIAGNOSTIC_ML_NAME
    ets_label = DIAGNOSTIC_ETS_NAME

    def fmt_pm(summary: dict[str, float]) -> str:
        return f"${summary['mean']:,.0f} ± ${summary['std']:,.0f}"

    ml_verdict = fit["ml"]["verdict"]
    ets_verdict = fit["autoets"]["verdict"]
    pinned = cv["pinned_prior_selection"]
    winner_note = (
        f"5-fold selection winner is `{target['diagnose_winner']}` "
        f"(params `{target['diagnose_params']}`). "
        f"Prior 3-fold shipped selection pinned as `{pinned['uni_winner']}` "
        f"with params `{pinned['best_params']}`. "
        + (
            "**Winner/params changed under ≥5-fold CV — prior selection pinned for continuity; "
            "diagnosis below uses the new 5-fold winner.**"
            if target.get("selection_changed")
            else "Winner unchanged vs the pinned 3-fold selection."
        )
    )

    ml_rmse_pct = (ml["val_rmse"]["mean"] / mean_rev * 100) if mean_rev else float("nan")
    ets_rmse_pct = (ets["val_rmse"]["mean"] / mean_rev * 100) if mean_rev else float("nan")

    lines = [
        "# HealthCore — Temporal CV & Fit Diagnosis Report",
        "",
        "## 1. Summary",
        "",
        f"| Model | Fit verdict | CV RMSE (mean ± std) | Corrective action |",
        f"|---|---|---|---|",
        f"| {ml_label} | **{ml_verdict}** | {fmt_pm(ml['val_rmse'])} | "
        f"{fit['ml']['corrective_actions'][0]} |",
        f"| {ets_label} | **{ets_verdict}** | {fmt_pm(ets['val_rmse'])} | "
        f"{fit['autoets']['corrective_actions'][0]} |",
        "",
        f"- Diagnostic ML target: `{ml_label}` with params `{target['diagnose_params']}`.",
        f"- Diagnostic classical label: `{ets_label}` (StatsForecast `AutoETS` under this diagnosis suite).",
        f"- {winner_note}",
        "",
        "## 2. CV setup & integrity",
        "",
        f"- **Folds:** {cv['n_splits']} (≥5 required) × {cv['test_size_months']}-month "
        "non-overlapping validation blocks on the diagnostic CV frame "
        f"(through **{cv.get('cv_frame_end', '2024-06-01')}**).",
        "- **Why 5×6:** comparable per-fold RMSE across engines; non-overlapping so std is not understated.",
        f"- **Window redesign:** {cv.get('window_redesign', PREVIOUS_WINDOWS_NOTE)}",
        f"- **Fold 0 train size:** ML fold 0 has `n_train={cv.get('fold0_n_train', 'n/a')}` "
        "usable rows after differencing/`lag_12` — shifted later so this is no longer the starved "
        "31-row fold from the 2021-07 start. Still interpret mean±std as a small-sample (5-fold) estimate.",
        f"- **Engines:** ML → `sklearn.model_selection.TimeSeriesSplit` "
        f"(gap={cv['gap']}); `{ets_label}` → `classical_backtest` / "
        "`StatsForecast.cross_validation` on model `AutoETS` (`n_windows=5`, `h=6`, `step_size=6`).",
        "- **Chronology:** no shuffle; every fold has `max(train ds) < min(val ds)`; "
        "validation blocks are contiguous and roll forward; `TimeSeriesSplit` never shuffles.",
        "- **Date alignment:** both engines score the same calendar windows "
        f"`{[ (f['val_start'], f['val_end']) for f in ml['folds'] ]}`.",
        "- **Selection CV change:** MLForecast learner-selection defaults raised from "
        f"**n_windows=3, h=12** (shipped) to **n_windows=5, h=6**. "
        "Classical `classical_backtest` was already 5-fold.",
        "",
    ]

    rec = metrics.get("recommendation") or {}
    if rec:
        lines.extend(
            [
                f"- **Pipeline recommendation after 5-fold retrain:** primary classical "
                f"`{rec.get('primary_point_forecast')}`; regression path "
                f"`{rec.get('regression')}` (visits help={rec.get('ablation_visits_help')}). "
                "Prior 3-fold narrative preferred univariate when visits lift was weak — "
                "note any flip; learner identity for uni/exog remains pinned above when unchanged.",
                "",
            ]
        )

    lines.extend(
        [
            "### Per-fold validation RMSE",
            "",
            "| Fold | Window | ML n_train | ML val RMSE | AutoETS2 val RMSE |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for mf, ef in zip(ml["folds"], ets["folds"], strict=True):
        lines.append(
            f"| {mf['fold']} | {mf['val_start']}…{mf['val_end']} | "
            f"{mf.get('n_train', 'n/a')} | ${mf['val_rmse']:,.0f} | ${ef['val_rmse']:,.0f} |"
        )
    lines.extend(
        [
            "",
            f"- ML val RMSE min/max: ${ml['val_rmse']['min']:,.0f} / ${ml['val_rmse']['max']:,.0f} "
            "(small-sample std caveat: only 5 folds).",
            f"- {ets_label} val RMSE min/max: ${ets['val_rmse']['min']:,.0f} / ${ets['val_rmse']['max']:,.0f}.",
            "",
            "## 3. Metrics table (train & validation)",
            "",
            "| Model | Stage | MAE (mean ± std) | RMSE (mean ± std) | RMSE % mean train revenue |",
            "|---|---|---|---|---|",
            f"| {ml_label} | Train | {fmt_pm(ml['train_mae'])} | {fmt_pm(ml['train_rmse'])} | — |",
            f"| {ml_label} | Validation | {fmt_pm(ml['val_mae'])} | {fmt_pm(ml['val_rmse'])} | "
            f"{ml_rmse_pct:.1f}% |",
            f"| {ets_label} | Train | {fmt_pm(ets['train_mae'])} | {fmt_pm(ets['train_rmse'])} | — |",
            f"| {ets_label} | Validation | {fmt_pm(ets['val_mae'])} | {fmt_pm(ets['val_rmse'])} | "
            f"{ets_rmse_pct:.1f}% |",
            "",
            f"Mean monthly train revenue ≈ **${mean_rev:,.0f}**.",
            "",
            "## 4. Learning curves",
            "",
            "Fixed validation block: **2023-01…2023-12**. Training prefixes "
            f"`{lc['prefixes']}` all end before 2023-01. "
            "Prefix **84** ends **2022-12** (contiguous with the val block) so the curve no longer "
            "skips all of 2022 between the largest train set and validation. "
            "Smallest prefixes (~36 months) are noisy.",
            "",
            f"### {ml_label}",
            "",
            "![ML learning curve](diagnostics/learning_curve_mlforecast_uni2.png)",
            "",
        ]
    )
    for p in lc["ml"]["points"]:
        lines.append(
            f"- s={p['train_size']}: train RMSE ${p['train_rmse']:,.0f}, "
            f"val RMSE ${p['val_rmse']:,.0f} (gap ${p['val_rmse'] - p['train_rmse']:,.0f})"
        )
    lines.extend(
        [
            "",
            f"### {ets_label}",
            "",
            "![AutoETS2 learning curve](diagnostics/learning_curve_autoets2.png)",
            "",
        ]
    )
    for p in lc["autoets"]["points"]:
        lines.append(
            f"- s={p['train_size']}: train RMSE ${p['train_rmse']:,.0f}, "
            f"val RMSE ${p['val_rmse']:,.0f} (gap ${p['val_rmse'] - p['train_rmse']:,.0f})"
        )
    if lc.get("elasticnet"):
        lines.extend(
            [
                "",
                "### ElasticNet side check (ML overfit contrast)",
                "",
                "![ElasticNet learning curve](diagnostics/learning_curve_elasticnet.png)",
                "",
            ]
        )
        for p in lc["elasticnet"]["points"]:
            lines.append(
                f"- s={p['train_size']}: train RMSE ${p['train_rmse']:,.0f}, "
                f"val RMSE ${p['val_rmse']:,.0f}"
            )

    lines.extend(
        [
            "",
            "## 5. Business-cost metric (MAE vs RMSE)",
            "",
            "Authoritative context: **`rag_assignments/CONTEXT-healthcore.en.md` §3** "
            "(sales-prediction context — **not** the repo website `CONTEXT.md`).",
            "",
            "CONTEXT §3 asks to *\"report MSE in USD², and also as a percentage of average "
            "monthly revenue\"*, and prizes a high **Gini** to *\"distinguish a normal "
            "low-season month … from an atypical drop.\"* Both signals say the business cares "
            "about **large, unusual deviations**, not just average error.",
            "",
            "**RMSE is the business-cost metric.** It is √MSE in interpretable dollars and "
            "penalizes large errors disproportionately — matching the cost of a planning-breaking "
            "revenue miss (over/under-staffing, misinformed executive decisions). A single $500k "
            "miss is worse than ten $50k misses; RMSE reflects that, MAE treats them as equal.",
            "",
            f"- ML CV RMSE as % of mean monthly train revenue: **{ml_rmse_pct:.1f}%**.",
            f"- {ets_label} CV RMSE as % of mean monthly train revenue: **{ets_rmse_pct:.1f}%**.",
            "- MAE is reported alongside for “average dollars off” interpretability.",
            "",
            "## 6. Fit diagnosis",
            "",
            f"### {ml_label} → **{ml_verdict}**",
            "",
            f"- Learning-curve (largest prefix): train RMSE ${fit['ml']['train_rmse_last_prefix']:,.0f}, "
            f"val RMSE ${fit['ml']['val_rmse_last_prefix']:,.0f}, "
            f"gap ${fit['ml']['gap']:,.0f} (relative {fit['ml']['relative_gap']:.0%}).",
            f"- CV: train RMSE ${fit['ml'].get('cv_train_rmse_mean', float('nan')):,.0f}, "
            f"val RMSE {fmt_pm(ml['val_rmse'])}, "
            f"CV gap ${fit['ml'].get('cv_gap', float('nan')):,.0f} "
            f"(relative {fit['ml'].get('cv_relative_gap', float('nan')):.0%}), "
            f"fold CV {fit['ml']['cv_coefficient_of_variation']:.2f}.",
            f"- Guardrail: {fit['ml']['notes']}",
            "",
            f"### {ets_label} → **{ets_verdict}**",
            "",
            f"- Learning-curve (largest prefix): train RMSE ${fit['autoets']['train_rmse_last_prefix']:,.0f}, "
            f"val RMSE ${fit['autoets']['val_rmse_last_prefix']:,.0f}, "
            f"gap ${fit['autoets']['gap']:,.0f} (relative {fit['autoets']['relative_gap']:.0%}).",
            f"- CV: train RMSE ${fit['autoets'].get('cv_train_rmse_mean', float('nan')):,.0f}, "
            f"val RMSE {fmt_pm(ets['val_rmse'])}, "
            f"CV gap ${fit['autoets'].get('cv_gap', float('nan')):,.0f} "
            f"(relative {fit['autoets'].get('cv_relative_gap', float('nan')):.0%}), "
            f"fold CV {fit['autoets']['cv_coefficient_of_variation']:.2f}.",
            f"- Guardrail: {fit['autoets']['notes']}",
            "",
            "## 7. Method note",
            "",
            "§5.4 correctness rules honored for the ML path: causal `.shift()` features "
            "(no same-month target leakage); `Differences([12])` + local scaler **fit per fold "
            "on train rows only** and inverted for scoring; **recursive** month-by-month "
            "prediction inside each 6-month block (predictions feed lag features — never "
            "one-shot `predict(X[test])`); validation windows defined **by date first** and "
            f"asserted identical across `{DIAGNOSTIC_ML_NAME}` (`TimeSeriesSplit`) and "
            f"`{DIAGNOSTIC_ETS_NAME}` (`StatsForecast.cross_validation` / `classical_backtest`).",
            "",
            "## 8. Corrective actions",
            "",
            f"### {ml_label} ({ml_verdict})",
            "",
        ]
    )
    for a in fit["ml"]["corrective_actions"]:
        lines.append(f"- {a}")
    lines.extend(["", f"### {ets_label} ({ets_verdict})", ""])
    for a in fit["autoets"]["corrective_actions"]:
        lines.append(f"- {a}")

    if cv.get("gap_ablation") and "gap0_val_rmse" in (cv.get("gap_ablation") or {}):
        g0 = cv["gap_ablation"]["gap0_val_rmse"]
        g1 = cv["gap_ablation"]["gap1_val_rmse"]
        lines.extend(
            [
                "",
                "## Stretch notes",
                "",
                f"- **Purged gap=1 A/B:** gap=0 val RMSE {fmt_pm(g0)}; gap=1 val RMSE {fmt_pm(g1)}.",
                "- Per-fold RMSE strip: `diagnostics/fold_rmse_strip.png`.",
            ]
        )
        if cv.get("seasonal_naive_skill"):
            sn = cv["seasonal_naive_skill"]["val_rmse"]
            lines.append(
                f"- **SeasonalNaive-in-CV** val RMSE {fmt_pm(sn)} "
                f"(skill context vs {DIAGNOSTIC_ML_NAME} / {DIAGNOSTIC_ETS_NAME} fold RMSE)."
            )

    lines.extend(
        [
            "",
            "## 9. Limitations",
            "",
            "- Only 120 monthly points; ~84 effective training rows after differencing + `lag_12`.",
            "- 6-month CV horizon; std across 5 folds is a small-sample estimate (report min/max).",
            "- “Collect more data” is not a lever for corrective action.",
            "- Learning-curve prefixes at s=36 are noisy after transforms.",
            "",
        ]
    )
    path.write_text("\n".join(lines))
    return path


def chronological_fold_records(
    cv_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Expose fold index boundaries for unit tests (both engines)."""
    if cv_df is None:
        cv_df = diagnostic_cv_frame()
    usable, _base = usable_feature_matrix(cv_df)
    ml_folds = time_series_split_folds(usable)
    assert_split_matches_date_windows(usable, ml_folds)
    windows = defined_validation_windows()
    ml_records = []
    for (train_idx, test_idx), window in zip(ml_folds, windows, strict=True):
        ml_records.append(
            {
                "fold": window.fold,
                "train_ds": list(pd.to_datetime(usable.iloc[train_idx]["ds"])),
                "test_ds": list(pd.to_datetime(usable.iloc[test_idx]["ds"])),
                "train_idx": train_idx,
                "test_idx": test_idx,
                "n_train_rows": int(len(train_idx)),
            }
        )
    cv = classical_backtest(cv_df, n_windows=N_SPLITS, h=TEST_SIZE)
    ets_records = []
    for i, cutoff in enumerate(sorted(pd.to_datetime(cv["cutoff"].unique()))):
        block = cv.loc[pd.to_datetime(cv["cutoff"]) == cutoff].sort_values("ds")
        ets_records.append(
            {
                "fold": i,
                "cutoff": pd.Timestamp(cutoff),
                "test_ds": list(pd.to_datetime(block["ds"])),
            }
        )
    return {"ml": ml_records, "autoets": ets_records, "usable": usable, "windows": windows, "cv_df": cv_df}
