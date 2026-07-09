from __future__ import annotations

from sqlalchemy import Engine, text


def ensure_telemetry_indexes(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp "
                "ON telemetry_events (timestamp)",
            ),
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_events_event_type "
                "ON telemetry_events (event_type)",
            ),
        )
        if engine.dialect.name == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE telemetry_events "
                    "ALTER COLUMN tags TYPE jsonb USING tags::jsonb",
                ),
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_telemetry_events_tags "
                    "ON telemetry_events USING GIN (tags)",
                ),
            )
