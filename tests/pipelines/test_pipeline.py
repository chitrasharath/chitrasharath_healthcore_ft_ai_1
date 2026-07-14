"""DB-free unit tests for telemetry transform helpers (analysis.py)."""

from __future__ import annotations

from datetime import date, timezone

import pandas as pd

from app.domains.telemetry.analysis import (
    ensure_columns,
    expand_tags,
    prepare_timestamps,
    records,
)


def test_expand_tags_flattens_jurisdiction_and_clinic() -> None:
    frame = pd.DataFrame(
        [{"id": "1", "tags": {"clinic_id": 3, "jurisdiction": "us"}}],
    )

    result = expand_tags(frame)

    assert "clinic_id" in result.columns
    assert "jurisdiction" in result.columns
    assert "tags" not in result.columns
    assert result.loc[0, "clinic_id"] == 3
    assert result.loc[0, "jurisdiction"] == "us"


def test_prepare_timestamps_derives_utc_date() -> None:
    frame = pd.DataFrame(
        [{"id": "1", "timestamp": "2026-03-15T14:30:00+00:00"}],
    )

    result = prepare_timestamps(frame)

    assert result.loc[0, "date"] == date(2026, 3, 15)
    ts = result.loc[0, "timestamp"]
    assert isinstance(ts, pd.Timestamp)
    assert ts.tzinfo is not None
    assert ts.tz_convert(timezone.utc).date() == date(2026, 3, 15)


def test_ensure_columns_backfills_missing_keys() -> None:
    frame = pd.DataFrame([{"id": "1", "jurisdiction": "uk"}])

    result = ensure_columns(frame, ["consumption_type", "jurisdiction"])

    assert "consumption_type" in result.columns
    assert pd.isna(result.loc[0, "consumption_type"])
    assert result.loc[0, "jurisdiction"] == "uk"


def test_records_serializes_date_to_string() -> None:
    frame = pd.DataFrame(
        [
            {
                "date": date(2026, 1, 2),
                "clinic_id": 1,
                "jurisdiction": "us",
                "count": 4,
            },
        ],
    )

    result = records(frame, ["date", "clinic_id", "jurisdiction", "count"])

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0]["date"], str)
    assert result[0]["date"] == "2026-01-02"


def test_prepare_timestamps_handles_malformed() -> None:
    frame = pd.DataFrame(
        [
            {"id": "1", "timestamp": None},
            {"id": "2", "timestamp": "not-a-date"},
            {"id": "3", "timestamp": "2026-07-01T00:00:00Z"},
        ],
    )

    result = prepare_timestamps(frame)

    assert pd.isna(result.loc[0, "timestamp"])
    assert pd.isna(result.loc[1, "timestamp"])
    assert result.loc[2, "date"] == date(2026, 7, 1)
