"""Idempotent DDL for Phase 2/3 DepartmentSection columns."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)

_SECTION_COLS: tuple[tuple[str, str], ...] = (
    ("status", "VARCHAR"),
    ("iteration", "INTEGER DEFAULT 0"),
    ("latest_evaluation_id", "INTEGER"),
    ("approval_iteration", "INTEGER DEFAULT 0"),
)


def ensure_rfp_phase2_columns(engine: Engine) -> None:
    """Add Phase 2/3 section columns if missing (create_all does not ALTER)."""
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            cols = {
                row[1]
                for row in conn.execute(
                    text("PRAGMA table_info(rfp_department_sections)")
                ).fetchall()
            }
            for name, col_type in _SECTION_COLS:
                if name not in cols:
                    conn.execute(
                        text(
                            f"ALTER TABLE rfp_department_sections "
                            f"ADD COLUMN {name} {col_type}"
                        )
                    )
            return

        for name, col_type in _SECTION_COLS:
            conn.execute(
                text(
                    f"ALTER TABLE rfp_department_sections "
                    f"ADD COLUMN IF NOT EXISTS {name} {col_type}"
                )
            )
            if name == "status":
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS "
                        "ix_rfp_department_sections_status "
                        "ON rfp_department_sections (status)"
                    )
                )
    logger.info("Ensured rfp_department_sections Phase 2/3 columns")
