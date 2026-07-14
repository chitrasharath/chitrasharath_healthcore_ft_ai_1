from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import Session

from app.core.db import get_supabase_db, supabase_engine
from app.core.dependencies import get_current_user
from app.domains.telemetry.analysis import build_metrics
from app.domains.telemetry.cache import get_cached_or_compute, report_cache_key
from app.domains.telemetry.mapper import map_event_to_row, properties_are_allowlisted
from app.domains.telemetry.schemas import TelemetryBatch, TelemetryEvent
from data.pipelines.load.repository import (
    get_latest_pipeline_run,
    list_recent_pipeline_runs,
    read_reporting_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_report_window(
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime, datetime]:
    end = _normalize_utc(end_date or datetime.now(timezone.utc))
    start = _normalize_utc(start_date or (end - timedelta(days=7)))
    return start, end


@router.post("/events")
def ingest_events(
    body: TelemetryBatch,
    session: Session = Depends(get_supabase_db),
) -> dict[str, int]:
    valid_rows = []
    rejected = 0

    for raw in body.events:
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError:
            logger.warning("telemetry instrumentation validation failed")
            rejected += 1
            continue

        if not properties_are_allowlisted(event):
            logger.warning("telemetry instrumentation rejected: %s", event.event_type)
            rejected += 1
            continue

        logger.info("telemetry instrumentation: %s", event.event_type)
        valid_rows.append(map_event_to_row(event))

    stored = 0
    if valid_rows:
        session.add_all(valid_rows)
        session.commit()
        stored = len(valid_rows)

    logger.info(
        "telemetry batch received: %s events (stored=%s, rejected=%s)",
        len(body.events),
        stored,
        rejected,
    )
    return {"received": len(body.events), "stored": stored, "rejected": rejected}


@router.get("/report")
def get_telemetry_report(
    session: Session = Depends(get_supabase_db),
    _user: dict = Depends(get_current_user),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict:
    """Materialized KPIs from reporting_* tables (frontend-facing)."""
    start, end = _resolve_report_window(start_date, end_date)
    cache_key = report_cache_key(start, end)

    def compute() -> dict:
        return {
            "period": {"from": start.isoformat(), "to": end.isoformat()},
            "metrics": read_reporting_metrics(session, start, end),
        }

    return get_cached_or_compute(cache_key, compute)


@router.get("/raw-report")
def get_telemetry_raw_report(
    session: Session = Depends(get_supabase_db),
    _user: dict = Depends(get_current_user),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> dict:
    """Live recompute from telemetry_events (preserved former /report behavior)."""
    start, end = _resolve_report_window(start_date, end_date)
    cache_key = (f"raw|{start.isoformat()}", end.isoformat())

    def compute() -> dict:
        return {
            "period": {"from": start.isoformat(), "to": end.isoformat()},
            "metrics": build_metrics(session, start, end),
        }

    return get_cached_or_compute(cache_key, compute)


def _serialize_pipeline_run(run) -> dict:
    return {
        "run_id": str(run.run_id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "watermark_from": run.watermark_from.isoformat() if run.watermark_from else None,
        "watermark_to": run.watermark_to.isoformat() if run.watermark_to else None,
        "rows_extracted": run.rows_extracted,
        "rows_loaded": run.rows_loaded,
        "rows_quarantined": run.rows_quarantined,
        "error_summary": run.error_summary,
        "checkpoint": run.checkpoint,
        "pipeline_version": run.pipeline_version,
    }


@router.get("/pipelines/runs/latest")
def get_latest_pipeline_run_endpoint(
    session: Session = Depends(get_supabase_db),
    _user: dict = Depends(get_current_user),
) -> dict:
    run = get_latest_pipeline_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return _serialize_pipeline_run(run)


@router.get("/pipelines/runs")
def list_pipeline_runs_endpoint(
    limit: int = 14,
    session: Session = Depends(get_supabase_db),
    _user: dict = Depends(get_current_user),
) -> dict:
    runs = list_recent_pipeline_runs(session, limit=limit)
    return {"runs": [_serialize_pipeline_run(run) for run in runs]}


@router.post("/pipelines/runs/trigger")
def trigger_pipeline_run(
    background_tasks: BackgroundTasks,
    _user: dict = Depends(get_current_user),
) -> dict:
    """Submit ETL asynchronously (FastAPI BackgroundTasks). Poll /pipelines/runs/latest."""
    if supabase_engine is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")

    run_id = uuid4()

    def _task(rid: UUID = run_id) -> None:
        from data.pipelines.pipeline import telemetry_etl_flow

        telemetry_etl_flow(run_id=rid)

    background_tasks.add_task(_task)
    return {
        "message": "Pipeline run submitted",
        "run_id": str(run_id),
    }
