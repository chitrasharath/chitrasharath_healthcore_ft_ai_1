from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import ValidationError

from app.domains.telemetry.schemas import TelemetryBatch, TelemetryEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events")
def ingest_events(body: TelemetryBatch) -> dict[str, int]:
    for raw in body.events:
        try:
            event = TelemetryEvent.model_validate(raw)
            logger.info("telemetry instrumentation: %s", event.event_type)
        except ValidationError:
            logger.warning("telemetry instrumentation validation failed")
    logger.info("telemetry batch received: %s events", len(body.events))
    return {"received": len(body.events)}
