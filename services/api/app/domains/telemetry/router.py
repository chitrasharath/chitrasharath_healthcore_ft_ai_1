from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlmodel import Session

from app.core.db import get_supabase_db
from app.core.dependencies import get_current_user
from app.domains.telemetry.analysis import build_metrics
from app.domains.telemetry.cache import get_cached_or_compute, report_cache_key
from app.domains.telemetry.mapper import map_event_to_row, properties_are_allowlisted
from app.domains.telemetry.schemas import TelemetryBatch, TelemetryEvent

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
    start, end = _resolve_report_window(start_date, end_date)
    cache_key = report_cache_key(start, end)

    def compute() -> dict:
        return {
            "period": {"from": start.isoformat(), "to": end.isoformat()},
            "metrics": build_metrics(session, start, end),
        }

    return get_cached_or_compute(cache_key, compute)
