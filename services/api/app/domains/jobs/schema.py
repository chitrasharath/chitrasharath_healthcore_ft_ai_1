"""Idempotent DDL for JobRun columns added by RFP intake."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)


def ensure_job_run_columns(engine: Engine) -> None:
    """Add target_key / checkpoint if missing (create_all does not ALTER)."""
    statements = (
        "ALTER TABLE job_runs ADD COLUMN IF NOT EXISTS target_key VARCHAR",
        "ALTER TABLE job_runs ADD COLUMN IF NOT EXISTS checkpoint VARCHAR",
        "CREATE INDEX IF NOT EXISTS ix_job_runs_target_key ON job_runs (target_key)",
    )
    # SQLite (pytest) supports ADD COLUMN IF NOT EXISTS from 3.35+; skip IF NOT EXISTS variants carefully
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            cols = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(job_runs)")).fetchall()
            }
            if "target_key" not in cols:
                conn.execute(text("ALTER TABLE job_runs ADD COLUMN target_key VARCHAR"))
            if "checkpoint" not in cols:
                conn.execute(text("ALTER TABLE job_runs ADD COLUMN checkpoint VARCHAR"))
            return

        for stmt in statements:
            conn.execute(text(stmt))
    logger.info("Ensured job_runs.target_key and job_runs.checkpoint columns")
