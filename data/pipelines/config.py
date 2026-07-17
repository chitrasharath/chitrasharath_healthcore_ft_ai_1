from __future__ import annotations

from pathlib import Path

# Prefect Block field equivalents (Build 1: constants, not registered Blocks).

KPI_EVENT_TYPES: list[str] = [
    "supply_consumption_created",
    "supply_consumption_failed",
    "user_login_succeeded",
    "user_login_failed",
]

REPROCESS_WINDOW_DAYS = 2
LOOKBACK_DAYS = 7
BATCH_SIZE = 5000
PIPELINE_VERSION = "1.0.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = REPO_ROOT / "data" / "pipelines" / "load" / "snapshots"

ENVELOPE_TAG_KEYS = frozenset(
    {"eventId", "sessionId", "userId", "schemaVersion", "requestId"},
)
