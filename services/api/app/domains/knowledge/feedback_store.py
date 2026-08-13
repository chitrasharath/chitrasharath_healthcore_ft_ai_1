"""Append-only JSONL store for knowledge interactions and feedback."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def _resolve_path(raw: str, repo_root: Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()


def query_id_exists(path: Path, query_id: str) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("query_id") == query_id and obj.get("record_type") == "interaction":
                return True
    return False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
