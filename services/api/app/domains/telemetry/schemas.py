from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TelemetryEvent(BaseModel):
    eventId: str
    timestamp: datetime
    sessionId: str
    userId: str
    event_type: str
    schemaVersion: str
    requestId: str
    service: str
    properties: dict[str, Any] = {}


class TelemetryBatch(BaseModel):
    events: list[dict[str, Any]]
