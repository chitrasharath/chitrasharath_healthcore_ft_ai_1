"""Load, validate, reshape, and split HealthCore monthly sales data."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_CSV = Path("data/raw/healthcore_sales.csv")
CLEAN_PARQUET = Path("data/process/healthcore_sales_clean.parquet")
TRAIN_END = pd.Timestamp("2023-12-01")
TEST_START = pd.Timestamp("2024-01-01")
EXPECTED_START = pd.Timestamp("2016-01-01")
EXPECTED_END = pd.Timestamp("2025-12-01")
EXPECTED_ROWS = 120


def load_raw(path: Path | str = RAW_CSV) -> pd.DataFrame:
    """Load the raw CSV and parse month to datetime."""
    frame = pd.read_csv(path)
    frame["month"] = pd.to_datetime(frame["month"])
    return frame


def clean_sales(frame: pd.DataFrame) -> pd.DataFrame:
    """Filter consolidated rows, drop nulls, validate, reshape to Nixtla long format."""
    work = frame.copy()
    work = work.loc[work["region"].astype(str).str.lower() == "consolidated"].copy()

    before = len(work)
    null_mask = work["month"].isna() | work["revenue_usd"].isna()
    empty_rev = work["revenue_usd"].astype(str).str.strip().eq("")
    dropped = int((null_mask | empty_rev).sum())
    work = work.loc[~null_mask & ~empty_rev].copy()
    if dropped:
        logger.info("Dropped %s null/empty rows (of %s)", dropped, before)

    work = work.sort_values("month").reset_index(drop=True)
    _validate_clean(work)

    long_df = pd.DataFrame(
        {
            "unique_id": "consolidated",
            "ds": work["month"].values,
            "y": work["revenue_usd"].astype(float).values,
            "visits_count": work["visits_count"].astype(float).values,
        }
    )
    return long_df


def _validate_clean(work: pd.DataFrame) -> None:
    if len(work) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} rows, got {len(work)}")
    expected = pd.date_range(EXPECTED_START, EXPECTED_END, freq="MS")
    actual = pd.DatetimeIndex(work["month"].unique()).sort_values()
    if not actual.equals(expected):
        missing = expected.difference(actual)
        raise ValueError(f"Missing months in series: {list(missing)}")
    if (work["revenue_usd"].astype(float) <= 0).any():
        raise ValueError("All revenue_usd values must be > 0")


def write_clean(frame: pd.DataFrame, path: Path | str = CLEAN_PARQUET) -> Path:
    """Persist cleaned long-format frame to parquet."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    return out


def load_clean(path: Path | str = CLEAN_PARQUET) -> pd.DataFrame:
    """Load cleaned parquet (or rebuild from CSV if missing)."""
    out = Path(path)
    if out.exists():
        frame = pd.read_parquet(out)
        frame["ds"] = pd.to_datetime(frame["ds"])
        return frame
    cleaned = clean_sales(load_raw())
    write_clean(cleaned, out)
    return cleaned


def split_train_test(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronological 8/2-year split: train through 2023-12, test 2024-01..2025-12."""
    work = frame.copy()
    work["ds"] = pd.to_datetime(work["ds"])
    train = work.loc[work["ds"] <= TRAIN_END].copy().reset_index(drop=True)
    test = work.loc[work["ds"] >= TEST_START].copy().reset_index(drop=True)
    if len(train) != 96 or len(test) != 24:
        raise ValueError(f"Expected 96/24 split, got {len(train)}/{len(test)}")
    if train["ds"].max() >= test["ds"].min():
        raise ValueError("Train/test overlap: train.ds.max must be < test.ds.min")
    return train, test


def profile(frame: pd.DataFrame) -> dict[str, float | int | str]:
    """Short summary for CLI logging."""
    return {
        "rows": int(len(frame)),
        "ds_min": str(pd.to_datetime(frame["ds"]).min().date()),
        "ds_max": str(pd.to_datetime(frame["ds"]).max().date()),
        "y_min": float(frame["y"].min()),
        "y_max": float(frame["y"].max()),
        "y_mean": float(frame["y"].mean()),
    }
