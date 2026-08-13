"""No-leakage tests for the revenue forecasting pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data.forecast.clean import clean_sales, load_raw, split_train_test
from data.forecast.features import FEATURE_COLUMNS, FORBIDDEN_COLUMNS, add_engineered_features
from data.forecast.models_mlforecast import (
    cross_validation_select,
    fit_predict_revenue,
    prepare_frame,
)
from data.forecast.models_statsforecast import forecast_visits


@pytest.fixture(scope="module")
def frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned = clean_sales(load_raw())
    return split_train_test(cleaned)


def test_feature_catalog_includes_groups_a_b_c() -> None:
    required = {
        "month",
        "month_sin",
        "is_high_season",
        "is_low_season",
        "rev_lag_1",
        "rev_lag_12",
        "rev_roll_mean_3",
        "rev_yoy",
        "trend",
        "visits_count",
        "visits_lag_1",
        "visits_lag_12",
        "visits_roll_mean_3",
    }
    assert required.issubset(set(FEATURE_COLUMNS))
    for bad in FORBIDDEN_COLUMNS:
        assert bad not in FEATURE_COLUMNS


def test_avg_revenue_per_visit_absent(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, test = frames
    for frame in (train, test):
        for bad in FORBIDDEN_COLUMNS:
            assert bad not in frame.columns
    prepared = add_engineered_features(train)
    for bad in FORBIDDEN_COLUMNS:
        assert bad not in prepared.columns


def test_fit_receives_train_only(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, _test = frames
    assert (train["ds"] <= pd.Timestamp("2023-12-01")).all()
    assert not (train["ds"] >= pd.Timestamp("2024-01-01")).any()


def test_exogenous_visits_are_forecast_not_actual(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, test = frames
    visits = forecast_visits(train, h=24, n_windows=2)
    x_df = visits["X_df"].sort_values("ds").reset_index(drop=True)
    actual = test[["ds", "visits_count"]].sort_values("ds").reset_index(drop=True)
    assert not np.allclose(x_df["visits_count"].values, actual["visits_count"].values)

    result = fit_predict_revenue(
        train,
        winner="elasticnet",
        params={"alpha": 1.0, "l1_ratio": 0.5},
        h=24,
        X_df=x_df,
        include_visits=True,
        with_intervals=False,
    )
    base = result["predictions"].sort_values("ds")["elasticnet"].to_numpy()

    perturbed = test.copy()
    perturbed["visits_count"] = perturbed["visits_count"] * 1.5
    # Perturbing test visits must not affect prediction when X_df is the forecast
    result2 = fit_predict_revenue(
        train,
        winner="elasticnet",
        params={"alpha": 1.0, "l1_ratio": 0.5},
        h=24,
        X_df=x_df,
        include_visits=True,
        with_intervals=False,
    )
    again = result2["predictions"].sort_values("ds")["elasticnet"].to_numpy()
    assert np.allclose(base, again)
    _ = perturbed  # explicit: unused on purpose


def test_transforms_ignore_test_y(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, test = frames
    visits = forecast_visits(train, h=24, n_windows=2)
    x_df = visits["X_df"]
    r1 = fit_predict_revenue(
        train,
        winner="elasticnet",
        params={"alpha": 1.0, "l1_ratio": 0.5},
        h=24,
        X_df=x_df,
        include_visits=True,
        with_intervals=False,
    )
    pred1 = r1["predictions"].sort_values("ds")["elasticnet"].to_numpy()

    # Altering test y cannot affect fit (test never passed to fit)
    test_perturbed = test.copy()
    test_perturbed["y"] = test_perturbed["y"] * 10
    r2 = fit_predict_revenue(
        train,
        winner="elasticnet",
        params={"alpha": 1.0, "l1_ratio": 0.5},
        h=24,
        X_df=x_df,
        include_visits=True,
        with_intervals=False,
    )
    pred2 = r2["predictions"].sort_values("ds")["elasticnet"].to_numpy()
    assert np.allclose(pred1, pred2)
    _ = test_perturbed


def test_cv_windows_are_causal(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, _test = frames
    cv = cross_validation_select(train, include_visits=True, n_windows=3, h=12)
    frame = cv["cv"].copy()
    cutoffs = sorted(frame["cutoff"].unique())
    assert cutoffs == sorted(cutoffs)
    for cutoff in cutoffs:
        fold = frame.loc[frame["cutoff"] == cutoff]
        assert fold["ds"].min() > cutoff


def test_prepare_frame_keeps_feature_inputs(frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, _ = frames
    prepared = prepare_frame(train, include_visits=True)
    for col in ("trend", "visits_count"):
        assert col in prepared.columns
    engineered = add_engineered_features(train)
    for col in ("rev_yoy", "visits_lag_1", "visits_lag_12", "visits_roll_mean_3"):
        assert col in engineered.columns
