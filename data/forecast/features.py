"""Feature catalog (Groups A–C) and engineered columns for MLForecast."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Source of truth for Groups A–C (target transforms are Group D, not listed here).
FEATURE_COLUMNS: list[str] = [
    # Group A — calendar / seasonality
    "month",
    "month_sin",
    "month_cos",
    "quarter",
    "year",
    "trend",
    "is_high_season",
    "is_low_season",
    # Group B — autoregressive revenue
    "rev_lag_1",
    "rev_lag_2",
    "rev_lag_3",
    "rev_lag_12",
    "rev_roll_mean_3",
    "rev_roll_mean_12",
    "rev_roll_std_3",
    "rev_yoy",
    # Group C — exogenous visits
    "visits_count",
    "visits_lag_1",
    "visits_lag_12",
    "visits_roll_mean_3",
]

GROUP_C_COLUMNS: list[str] = [
    "visits_count",
    "visits_lag_1",
    "visits_lag_12",
    "visits_roll_mean_3",
]

FORBIDDEN_COLUMNS: list[str] = ["avg_revenue_per_visit_usd", "avg_revenue_per_visit"]


def quarter(dates: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(dates).dt.quarter


def is_high_season(dates: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(dates).dt.month.isin([10, 11, 12]).astype(int)


def is_low_season(dates: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(dates).dt.month.isin([7, 8]).astype(int)


def month_sin(dates: pd.DatetimeIndex) -> pd.Series:
    months = pd.Series(dates).dt.month
    return np.sin(2 * np.pi * months / 12)


def month_cos(dates: pd.DatetimeIndex) -> pd.Series:
    months = pd.Series(dates).dt.month
    return np.cos(2 * np.pi * months / 12)


DATE_FEATURES = [
    "month",
    "year",
    quarter,
    month_sin,
    month_cos,
    is_high_season,
    is_low_season,
]


def add_engineered_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach trend, YoY growth, and explicit visits lags/rolls (causal via shift)."""
    work = frame.copy().sort_values(["unique_id", "ds"]).reset_index(drop=True)
    work["ds"] = pd.to_datetime(work["ds"])
    work["trend"] = np.arange(len(work), dtype=int)

    # rev_yoy = rev_lag_1 / rev_lag_13 - 1  (uses only past revenue)
    lag1 = work["y"].shift(1)
    lag13 = work["y"].shift(13)
    work["rev_yoy"] = (lag1 / lag13) - 1.0

    work["visits_lag_1"] = work["visits_count"].shift(1)
    work["visits_lag_12"] = work["visits_count"].shift(12)
    work["visits_roll_mean_3"] = work["visits_count"].shift(1).rolling(3).mean()
    return work


def assert_no_forbidden_columns(frame: pd.DataFrame) -> None:
    """Raise if leakage columns are present."""
    bad = [c for c in FORBIDDEN_COLUMNS if c in frame.columns]
    if bad:
        raise ValueError(f"Forbidden leakage columns present: {bad}")


def drop_group_c(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy without Group C visits features (univariate ablation)."""
    cols = [c for c in frame.columns if c not in GROUP_C_COLUMNS]
    return frame[cols].copy()
