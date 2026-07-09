from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlmodel import Session

from app.core.db import get_supabase_db
from app.domains.telemetry.mapper import map_event_to_row, properties_are_allowlisted
from app.domains.telemetry.schemas import TelemetryBatch, TelemetryEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


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
