from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from tinydb import TinyDB
from tinydb.storages import JSONStorage, Storage, touch

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "db.json"
DB_PATH = Path(
    os.environ.get("DB_PATH", os.environ.get("SUPPLIERS_DB_PATH", str(DEFAULT_DB_PATH)))
)

_db: TinyDB | None = None
_db_lock = threading.RLock()


class LockedJSONStorage(Storage):
    """Thread-safe JSONStorage — TinyDB's shared file handle is not concurrent-safe."""

    def __init__(self, path: str, create_dirs: bool = False, encoding=None, **kwargs):
        self._path = path
        self._lock = _db_lock
        self._inner = JSONStorage(
            path,
            create_dirs=create_dirs,
            encoding=encoding,
            **kwargs,
        )

    def read(self):
        with self._lock:
            try:
                return self._inner.read()
            except json.JSONDecodeError:
                # Transient empty/partial file during a concurrent write — retry once.
                self._inner._handle.seek(0)
                raw = self._inner._handle.read()
                if not raw or not str(raw).strip():
                    return None
                return json.loads(raw)

    def write(self, data) -> None:
        with self._lock:
            self._inner.write(data)

    def close(self) -> None:
        with self._lock:
            self._inner.close()


def get_db() -> TinyDB:
    global _db
    with _db_lock:
        if _db is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not DB_PATH.exists():
                touch(str(DB_PATH), create_dirs=True)
            _db = TinyDB(str(DB_PATH), storage=LockedJSONStorage)
        return _db


def reset_db(path: Path | None = None) -> None:
    global _db, DB_PATH
    with _db_lock:
        if _db is not None:
            _db.close()
            _db = None
        if path is not None:
            DB_PATH = path


from sqlmodel import Session, create_engine

from app.core.config import settings

supabase_engine = None
if settings.database_url:
    supabase_engine = create_engine(settings.database_url, echo=False)


def get_supabase_db():
    with Session(supabase_engine) as session:
        yield session
