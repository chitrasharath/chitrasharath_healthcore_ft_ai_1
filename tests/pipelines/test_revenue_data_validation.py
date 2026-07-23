"""Data validation tests for the revenue cleaning pipeline."""

from __future__ import annotations

import pandas as pd
import pytest

from data.forecast.clean import clean_sales, load_raw


def test_clean_has_120_positive_rows_no_gaps() -> None:
    cleaned = clean_sales(load_raw())
    assert len(cleaned) == 120
    assert (cleaned["y"] > 0).all()
    expected = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
    assert pd.DatetimeIndex(cleaned["ds"]).sort_values().equals(expected)
    assert "visits_count" in cleaned.columns
    assert "avg_revenue_per_visit_usd" not in cleaned.columns


def test_clean_drops_null_revenue_row() -> None:
    raw = load_raw()
    injected = pd.concat(
        [
            raw,
            pd.DataFrame(
                [
                    {
                        "month": "2026-01-01",
                        "revenue_usd": None,
                        "visits_count": 1,
                        "avg_revenue_per_visit_usd": 1.0,
                        "region": "consolidated",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    # Cleaning validates exact 120 rows after drop — inject a null into an existing row instead
    injected = raw.copy()
    injected.loc[0, "revenue_usd"] = None
    with pytest.raises(ValueError, match="Expected 120"):
        clean_sales(injected)


def test_clean_drops_null_then_fails_validation_count() -> None:
    """Null rows are dropped before the 120-row assertion."""
    raw = load_raw().copy()
    raw.loc[5, "revenue_usd"] = None
    with pytest.raises(ValueError):
        clean_sales(raw)
