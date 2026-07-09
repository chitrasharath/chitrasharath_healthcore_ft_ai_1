from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlmodel import Session, select

from app.domains.telemetry.models import TelemetryEventRow


def load_events(
    session: Session,
    event_types: list[str],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    if not event_types:
        return pd.DataFrame(columns=["id", "timestamp", "event_type", "tags"])

    statement = (
        select(
            TelemetryEventRow.id,
            TelemetryEventRow.timestamp,
            TelemetryEventRow.event_type,
            TelemetryEventRow.tags,
        )
        .where(TelemetryEventRow.event_type.in_(event_types))
        .where(TelemetryEventRow.timestamp >= start_date)
        .where(TelemetryEventRow.timestamp < end_date)
    )
    rows = session.exec(statement).all()
    if not rows:
        return pd.DataFrame(columns=["id", "timestamp", "event_type", "tags"])

    return pd.DataFrame(
        [
            {
                "id": str(row.id),
                "timestamp": row.timestamp,
                "event_type": row.event_type,
                "tags": row.tags or {},
            }
            for row in rows
        ],
    )
