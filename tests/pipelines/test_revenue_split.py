"""Validate the chronological 8/2-year revenue split."""

from __future__ import annotations

import pandas as pd
import pytest

from data.forecast.clean import clean_sales, load_raw, split_train_test


@pytest.fixture(scope="module")
def split_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned = clean_sales(load_raw())
    return split_train_test(cleaned)


def test_split_counts(split_frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, test = split_frames
    assert len(train) == 96
    assert len(test) == 24


def test_split_boundaries(split_frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, test = split_frames
    assert train["ds"].max() == pd.Timestamp("2023-12-01")
    assert test["ds"].min() == pd.Timestamp("2024-01-01")
    assert train["ds"].max() < test["ds"].min()


def test_split_no_overlap_full_coverage(split_frames: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    train, test = split_frames
    train_ds = set(train["ds"])
    test_ds = set(test["ds"])
    assert train_ds.isdisjoint(test_ds)
    expected = set(pd.date_range("2016-01-01", "2025-12-01", freq="MS"))
    assert train_ds | test_ds == expected
