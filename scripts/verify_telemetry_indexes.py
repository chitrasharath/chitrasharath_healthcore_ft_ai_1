#!/usr/bin/env python3
"""Verify telemetry_events indexes (including GIN on tags) against Supabase Postgres."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PATH = REPO_ROOT / "services" / "api"

if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))

from app.core.config import settings  # noqa: E402
from app.core.db import supabase_engine  # noqa: E402
from app.domains.telemetry.indexes import ensure_telemetry_indexes  # noqa: E402

EXPECTED_INDEXES = frozenset(
    {
        "idx_telemetry_events_timestamp",
        "idx_telemetry_events_event_type",
        "idx_telemetry_events_tags",
    },
)


def _fail(message: str) -> None:
    print(f"FAIL: {message}")


def _ok(message: str) -> None:
    print(f"OK:   {message}")


def verify(engine) -> int:
    if engine.dialect.name != "postgresql":
        _fail(f"DATABASE_URL must be PostgreSQL (got {engine.dialect.name})")
        return 1

    failures = 0

    with engine.connect() as conn:
        table_exists = conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_schema = 'public' AND table_name = 'telemetry_events'"
                ")",
            ),
        ).scalar()
        if not table_exists:
            _fail("telemetry_events table does not exist — start the API once with DATABASE_URL set")
            return 1
        _ok("telemetry_events table exists")

    ensure_telemetry_indexes(engine)
    _ok("ensure_telemetry_indexes() completed")

    with engine.connect() as conn:
        tags_type = conn.execute(
            text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'telemetry_events' "
                "  AND column_name = 'tags'",
            ),
        ).scalar()
        if tags_type != "jsonb":
            _fail(f"tags column type is {tags_type!r}, expected jsonb")
            failures += 1
        else:
            _ok("tags column is jsonb")

        rows = conn.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename = 'telemetry_events'",
            ),
        ).all()
        found = {row.indexname for row in rows}
        missing = EXPECTED_INDEXES - found
        if missing:
            for name in sorted(missing):
                _fail(f"missing index {name}")
            failures += 1
        else:
            _ok(f"all expected indexes present ({', '.join(sorted(EXPECTED_INDEXES))})")

        gin_def = next((row.indexdef for row in rows if row.indexname == "idx_telemetry_events_tags"), "")
        if " using gin " not in gin_def.lower():
            _fail(f"idx_telemetry_events_tags is not GIN: {gin_def}")
            failures += 1
        else:
            _ok("idx_telemetry_events_tags uses GIN")

        conn.execute(text("SET enable_seqscan = off"))
        plan_lines = conn.execute(
            text(
                "EXPLAIN SELECT id FROM telemetry_events "
                "WHERE tags @> '{\"schemaVersion\": \"1.1.0\"}'::jsonb",
            ),
        ).scalars().all()
        conn.execute(text("RESET enable_seqscan"))

        plan_text = "\n".join(plan_lines)
        if "idx_telemetry_events_tags" in plan_text:
            _ok(f"GIN index used in plan:\n      {plan_text.replace(chr(10), chr(10) + '      ')}")
        else:
            _fail(f"GIN index not used in plan:\n      {plan_text.replace(chr(10), chr(10) + '      ')}")
            failures += 1

    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1

    print("\nAll telemetry index checks passed.")
    return 0


def main() -> int:
    if not settings.database_url or supabase_engine is None:
        print("DATABASE_URL is not configured. Set it in services/api/.env")
        return 1
    return verify(supabase_engine)


if __name__ == "__main__":
    raise SystemExit(main())
