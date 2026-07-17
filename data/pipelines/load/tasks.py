from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from prefect import task

from app.core.db import supabase_engine
from data.pipelines.config import SNAPSHOT_DIR
from data.pipelines.load import repository as repo


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


@task
def load_reporting_tables(metrics: dict[str, list[dict]], run_id: str) -> int:
    engine = _ensure_engine()
    return repo.load_all_reporting(engine, metrics, UUID(run_id))


@task
def export_snapshot_optional(metrics: dict[str, list[dict]]) -> str | None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"metrics-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(metrics, default=str), encoding="utf-8")
    return str(path)
