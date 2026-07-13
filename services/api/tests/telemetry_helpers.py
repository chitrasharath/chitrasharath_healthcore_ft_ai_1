from __future__ import annotations

from sqlmodel import Session, select

from app.domains.telemetry.models import TelemetryEventRow


def sample_event(event_type: str, event_id: str = "evt-001", **properties: object) -> dict:
    return {
        "eventId": event_id,
        "timestamp": "2026-07-08T12:00:00Z",
        "sessionId": "sess-001",
        "userId": "42",
        "event_type": event_type,
        "schemaVersion": "1.1.0",
        "requestId": "req-001",
        "service": "backoffice",
        "properties": properties,
    }


def latest_row(session_engine, event_type: str | None = None) -> TelemetryEventRow:
    with Session(session_engine) as session:
        statement = select(TelemetryEventRow).order_by(TelemetryEventRow.timestamp.desc())
        if event_type:
            statement = statement.where(TelemetryEventRow.event_type == event_type)
        row = session.exec(statement).first()
        assert row is not None
        return row
