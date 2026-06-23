from __future__ import annotations

import os
from pathlib import Path

from tinydb import TinyDB

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "db.json"
DB_PATH = Path(
    os.environ.get("DB_PATH", os.environ.get("SUPPLIERS_DB_PATH", str(DEFAULT_DB_PATH)))
)

_db: TinyDB | None = None


def get_db() -> TinyDB:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = TinyDB(DB_PATH)
    return _db


def reset_db(path: Path | None = None) -> None:
    global _db, DB_PATH
    if _db is not None:
        _db.close()
        _db = None
    if path is not None:
        DB_PATH = path
