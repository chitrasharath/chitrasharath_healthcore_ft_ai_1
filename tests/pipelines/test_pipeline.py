"""DB-free unit tests for telemetry transform helpers and KPI math."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pandas as pd

from app.domains.telemetry.analysis import (
    _ensure_columns,
    _expand_tags,
    _prepare_timestamps,
    _records,
    waste_rate_per_day,
)


def test_expand_tags_flattens_jurisdiction_and_clinic() -> None:
    frame = pd.DataFrame(
        [{"id": "1", "tags": {"clinic_id": 3, "jurisdiction": "us"}}],
    )

    result = _expand_tags(frame)

    assert "clinic_id" in result.columns
    assert "jurisdiction" in result.columns
    assert "tags" not in result.columns
    assert result.loc[0, "clinic_id"] == 3
    assert result.loc[0, "jurisdiction"] == "us"


def test_prepare_timestamps_derives_utc_date() -> None:
    frame = pd.DataFrame(
        [{"id": "1", "timestamp": "2026-03-15T14:30:00+00:00"}],
    )

    result = _prepare_timestamps(frame)

    assert result.loc[0, "date"] == date(2026, 3, 15)
    ts = result.loc[0, "timestamp"]
    assert isinstance(ts, pd.Timestamp)
    assert ts.tzinfo is not None
    assert ts.tz_convert(timezone.utc).date() == date(2026, 3, 15)


def test_ensure_columns_backfills_missing_keys() -> None:
    frame = pd.DataFrame([{"id": "1", "jurisdiction": "uk"}])

    result = _ensure_columns(frame, ["consumption_type", "jurisdiction"])

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

    result = _records(frame, ["date", "clinic_id", "jurisdiction", "count"])

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

    result = _prepare_timestamps(frame)

    assert pd.isna(result.loc[0, "timestamp"])
    assert pd.isna(result.loc[1, "timestamp"])
    assert result.loc[2, "date"] == date(2026, 7, 1)


def test_waste_rate_matches_kpi_definition(monkeypatch) -> None:
    """Supply waste rate = expiry_waste / all outbound consumptions per day/jurisdiction.

    Definition: telemetry-plan.md §2 KPI 2 (share of outbound where
    consumption_type = expiry_waste vs clinical_use + expiry_waste).
    Fixture: 1 waste + 3 clinical on 2026-07-01 us → waste_rate = 0.25, total = 4.
    """
    events = pd.DataFrame(
        [
            {
                "id": "a",
                "event_type": "supply_consumption_created",
                "timestamp": "2026-07-01T10:00:00Z",
                "tags": {"jurisdiction": "us", "consumption_type": "expiry_waste"},
            },
            {
                "id": "b",
                "event_type": "supply_consumption_created",
                "timestamp": "2026-07-01T11:00:00Z",
                "tags": {"jurisdiction": "us", "consumption_type": "clinical_use"},
            },
            {
                "id": "c",
                "event_type": "supply_consumption_created",
                "timestamp": "2026-07-01T12:00:00Z",
                "tags": {"jurisdiction": "us", "consumption_type": "clinical_use"},
            },
            {
                "id": "d",
                "event_type": "supply_consumption_created",
                "timestamp": "2026-07-01T13:00:00Z",
                "tags": {"jurisdiction": "us", "consumption_type": "clinical_use"},
            },
        ],
    )
    monkeypatch.setattr(
        "app.domains.telemetry.analysis.load_events",
        lambda *_args, **_kwargs: events,
    )

    result = waste_rate_per_day(
        MagicMock(),
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert len(result) == 1
    row = result[0]
    assert row["date"] == "2026-07-01"
    assert row["jurisdiction"] == "us"
    assert row["total"] == 4
    assert row["waste_rate"] == 0.25
