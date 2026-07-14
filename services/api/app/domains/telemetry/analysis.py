from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from sqlmodel import Session

from app.domains.telemetry.repository import load_events


def prepare_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    prepared = df.copy()
    prepared["timestamp"] = pd.to_datetime(
        prepared["timestamp"],
        utc=True,
        errors="coerce",
    )
    prepared["date"] = prepared["timestamp"].dt.date
    return prepared


def expand_tags(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    tags = pd.json_normalize(df["tags"])
    return pd.concat([df.drop(columns=["tags"]), tags], axis=1)


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    prepared = df.copy()
    for column in columns:
        if column not in prepared.columns:
            prepared[column] = pd.NA
    return prepared


def records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    output = frame[columns].copy()
    if "date" in output.columns:
        output["date"] = output["date"].astype(str)
    return output.to_dict(orient="records")


# Stable public names; underscore aliases kept for any residual private imports.
_prepare_timestamps = prepare_timestamps
_expand_tags = expand_tags
_ensure_columns = ensure_columns
_records = records

__all__ = [
    "prepare_timestamps",
    "expand_tags",
    "ensure_columns",
    "records",
    "consumption_volume_per_day",
    "waste_rate_per_day",
    "insufficient_stock_failures_per_day",
    "auth_failure_rate",
    "build_metrics",
]


def consumption_volume_per_day(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """KPI 1 (telemetry-plan.md §2): supply consumption rate per clinic/day/jurisdiction.

    Replaces CONTEXT metric ``dispensing_volume_per_day``.
    """
    df = load_events(session, ["supply_consumption_created"], start_date, end_date)
    if df.empty:
        return []

    df = ensure_columns(expand_tags(prepare_timestamps(df)), ["clinic_id", "jurisdiction"])
    df = df.dropna(subset=["clinic_id", "jurisdiction"])
    if df.empty:
        return []

    grouped = (
        df.groupby(["date", "clinic_id", "jurisdiction"], as_index=False)
        .agg(count=("id", "count"))
    )
    return records(grouped, ["date", "clinic_id", "jurisdiction", "count"])


def waste_rate_per_day(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """KPI 2 (telemetry-plan.md §2): expiry waste share of outbound consumptions.

    Replaces CONTEXT metric ``emergency_dispensing_per_day`` (no emergency/clinical_context in code).
    """
    df = load_events(session, ["supply_consumption_created"], start_date, end_date)
    if df.empty:
        return []

    df = ensure_columns(expand_tags(prepare_timestamps(df)), ["jurisdiction", "consumption_type"])
    df = df.dropna(subset=["jurisdiction", "consumption_type"])
    if df.empty:
        return []

    df["is_waste"] = df["consumption_type"] == "expiry_waste"
    grouped = df.groupby(["date", "jurisdiction"], as_index=False).agg(
        total=("id", "count"),
        waste=("is_waste", "sum"),
    )
    grouped["waste_rate"] = grouped["waste"] / grouped["total"]
    return records(grouped, ["date", "jurisdiction", "waste_rate", "total"])


def insufficient_stock_failures_per_day(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """KPI 3 (telemetry-plan.md §2): insufficient-stock rejections and rejection rate.

    ``count`` = failed outbound attempts; ``attempts`` = created + failed;
    ``rejection_rate`` = count / attempts per supply/clinic/jurisdiction/day.

    Replaces CONTEXT stock-out observability via the HTTP 400 rejection signal.
    """
    df = load_events(
        session,
        ["supply_consumption_created", "supply_consumption_failed"],
        start_date,
        end_date,
    )
    if df.empty:
        return []

    group_cols = ["date", "clinic_id", "jurisdiction", "supply_id"]
    df = ensure_columns(
        expand_tags(prepare_timestamps(df)),
        ["clinic_id", "jurisdiction", "supply_id"],
    )
    df = df.dropna(subset=["clinic_id", "jurisdiction", "supply_id"])
    if df.empty:
        return []

    df["is_failure"] = df["event_type"] == "supply_consumption_failed"
    grouped = df.groupby(group_cols, as_index=False).agg(
        attempts=("id", "count"),
        count=("is_failure", "sum"),
    )
    grouped["count"] = grouped["count"].astype(int)
    grouped["rejection_rate"] = grouped["count"] / grouped["attempts"]
    return records(
        grouped,
        ["date", "clinic_id", "jurisdiction", "supply_id", "count", "attempts", "rejection_rate"],
    )


def auth_failure_rate(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """Auth instrumentation: daily login failure rate (login success vs failure events).

    Does not use ``jurisdiction`` — login capture does not reliably include it.
    """
    df = load_events(
        session,
        ["user_login_succeeded", "user_login_failed"],
        start_date,
        end_date,
    )
    if df.empty:
        return []

    df = prepare_timestamps(df)
    df["failed"] = df["event_type"] == "user_login_failed"
    df["succeeded"] = df["event_type"] == "user_login_succeeded"
    grouped = df.groupby(["date"], as_index=False).agg(
        failed=("failed", "sum"),
        succeeded=("succeeded", "sum"),
    )
    grouped["failure_rate"] = grouped["failed"] / (grouped["failed"] + grouped["succeeded"])
    grouped["failed"] = grouped["failed"].astype(int)
    grouped["succeeded"] = grouped["succeeded"].astype(int)
    return records(grouped, ["date", "failed", "succeeded", "failure_rate"])


def build_metrics(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "consumption_volume_per_day": consumption_volume_per_day(session, start_date, end_date),
        "waste_rate_per_day": waste_rate_per_day(session, start_date, end_date),
        "insufficient_stock_failures_per_day": insufficient_stock_failures_per_day(
            session,
            start_date,
            end_date,
        ),
        "auth_failure_rate": auth_failure_rate(session, start_date, end_date),
    }
