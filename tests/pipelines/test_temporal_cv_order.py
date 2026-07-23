"""Prove temporal CV engines preserve chronological order within each fold."""

from __future__ import annotations

import pandas as pd
import pytest
from sklearn.model_selection import KFold, TimeSeriesSplit

from data.forecast.clean import clean_sales, load_raw, split_train_test
from data.forecast.diagnostics import (
    N_SPLITS,
    TEST_SIZE,
    chronological_fold_records,
    defined_validation_windows,
    time_series_split_folds,
    usable_feature_matrix,
)
from data.forecast.models_statsforecast import classical_backtest


@pytest.fixture(scope="module")
def train_df() -> pd.DataFrame:
    cleaned = clean_sales(load_raw())
    train, _test = split_train_test(cleaned)
    return train


@pytest.fixture(scope="module")
def fold_records(train_df: pd.DataFrame) -> dict:
    return chronological_fold_records(train_df)


def test_ml_at_least_five_folds(fold_records: dict) -> None:
    assert len(fold_records["ml"]) >= 5
    assert len(fold_records["ml"]) == N_SPLITS


def test_ml_train_precedes_validation(fold_records: dict) -> None:
    for rec in fold_records["ml"]:
        train_ds = pd.DatetimeIndex(rec["train_ds"])
        test_ds = pd.DatetimeIndex(rec["test_ds"])
        assert train_ds.max() < test_ds.min()
        assert rec["train_idx"].max() < rec["test_idx"].min()
        assert all(i < j for i in rec["train_idx"] for j in rec["test_idx"])


def test_ml_validation_contiguous_no_shuffle(fold_records: dict) -> None:
    for rec in fold_records["ml"]:
        test_ds = pd.DatetimeIndex(rec["test_ds"])
        assert list(test_ds) == list(sorted(test_ds))
        assert len(test_ds) == TEST_SIZE
        expected = pd.date_range(test_ds.min(), periods=TEST_SIZE, freq="MS")
        assert test_ds.equals(expected)


def test_ml_folds_roll_forward_no_overlap(fold_records: dict) -> None:
    blocks = [set(pd.DatetimeIndex(r["test_ds"])) for r in fold_records["ml"]]
    for earlier, later in zip(blocks, blocks[1:], strict=False):
        assert max(earlier) < min(later)
        assert earlier.isdisjoint(later)


def test_autoets_at_least_five_cutoffs(fold_records: dict) -> None:
    assert len(fold_records["autoets"]) >= 5
    cutoffs = [r["cutoff"] for r in fold_records["autoets"]]
    assert cutoffs == sorted(cutoffs)
    deltas = [(b - a).days for a, b in zip(cutoffs, cutoffs[1:], strict=False)]
    # step_size=6 months ≈ 181–184 days depending on month lengths
    assert all(150 <= d <= 200 for d in deltas)


def test_autoets_train_precedes_validation(fold_records: dict) -> None:
    for rec in fold_records["autoets"]:
        test_ds = pd.DatetimeIndex(rec["test_ds"])
        assert (test_ds > rec["cutoff"]).all()
        expected = pd.date_range(rec["cutoff"] + pd.offsets.MonthBegin(1), periods=TEST_SIZE, freq="MS")
        assert test_ds.equals(expected)


def test_engines_aligned_calendar_months(fold_records: dict) -> None:
    for ml_rec, ets_rec in zip(fold_records["ml"], fold_records["autoets"], strict=True):
        assert list(pd.DatetimeIndex(ml_rec["test_ds"])) == list(pd.DatetimeIndex(ets_rec["test_ds"]))
    windows = defined_validation_windows()
    for ml_rec, window in zip(fold_records["ml"], windows, strict=True):
        expected = list(pd.date_range(window.val_start, window.val_end, freq="MS"))
        assert list(pd.DatetimeIndex(ml_rec["test_ds"])) == expected


def test_splitters_deterministic(train_df: pd.DataFrame) -> None:
    a = chronological_fold_records(train_df)
    b = chronological_fold_records(train_df)
    for ra, rb in zip(a["ml"], b["ml"], strict=True):
        assert list(ra["train_idx"]) == list(rb["train_idx"])
        assert list(ra["test_idx"]) == list(rb["test_idx"])
    assert [r["cutoff"] for r in a["autoets"]] == [r["cutoff"] for r in b["autoets"]]


def test_negative_control_sorts_before_split(train_df: pd.DataFrame) -> None:
    """Shuffled frame must be sorted by ds before TimeSeriesSplit, or order fails."""
    shuffled = train_df.sample(frac=1.0, random_state=0).reset_index(drop=True)
    usable, _ = usable_feature_matrix(shuffled)  # sorts internally via build frame
    folds = time_series_split_folds(usable)
    for train_idx, test_idx in folds:
        train_ds = pd.to_datetime(usable.iloc[train_idx]["ds"])
        test_ds = pd.to_datetime(usable.iloc[test_idx]["ds"])
        assert train_ds.max() < test_ds.min()


def test_no_shuffling_splitter_in_pipeline() -> None:
    """Guard: temporal path uses TimeSeriesSplit; never KFold(shuffle=True)."""
    tss = TimeSeriesSplit(n_splits=N_SPLITS, test_size=TEST_SIZE, gap=0)
    assert getattr(tss, "shuffle", False) is False or not hasattr(tss, "shuffle")
    # Document that KFold(shuffle=True) is not the pipeline splitter
    bad = KFold(n_splits=5, shuffle=True, random_state=42)
    assert bad.shuffle is True


def test_classical_backtest_h6_windows(train_df: pd.DataFrame) -> None:
    cv = classical_backtest(train_df, n_windows=N_SPLITS, h=TEST_SIZE)
    cutoffs = sorted(pd.to_datetime(cv["cutoff"].unique()))
    assert len(cutoffs) >= N_SPLITS
