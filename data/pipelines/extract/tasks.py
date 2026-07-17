from __future__ import annotations

from datetime import datetime

import pandas as pd
from prefect import task
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from app.core.db import supabase_engine
from app.domains.telemetry.repository import load_events


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


def is_transient(task, task_run, state) -> bool:  # noqa: A002
    """Retry only transient/connection errors — never validation failures."""
    try:
        state.result(raise_on_failure=True)
    except OperationalError:
        return True
    except Exception as exc:  # noqa: BLE001
        message = str(exc).lower()
        return "connection" in message or "timeout" in message or "operational" in message
    return False


@task(
    retries=3,
    retry_delay_seconds=[10, 30, 60],
    retry_condition_fn=is_transient,
)
def extract_telemetry_events(
    event_types: list[str],
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    # 3 retries w/ backoff: absorbs transient Supabase/connection blips without paging on-call.
    # retry_condition_fn -> retry only OperationalError/connection resets, NOT ValidationError.
    engine = _ensure_engine()
    with Session(engine) as session:
        return load_events(session, event_types, start, end)
