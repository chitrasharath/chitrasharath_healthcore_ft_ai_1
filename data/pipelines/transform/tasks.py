from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from prefect import task
from sqlmodel import Session

from app.core.db import supabase_engine
from app.domains.telemetry.analysis import build_metrics


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


def window_cache_key(context, parameters: dict[str, Any]) -> str:  # noqa: ANN001, ARG001
    return f"kpi-{parameters['start']!s}-{parameters['end']!s}"


@task(
    cache_key_fn=window_cache_key,
    cache_expiration=timedelta(hours=1),
)
def transform_kpi_aggregates(start: datetime, end: datetime) -> dict[str, list[dict]]:
    engine = _ensure_engine()
    with Session(engine) as session:
        return build_metrics(session, start, end)
