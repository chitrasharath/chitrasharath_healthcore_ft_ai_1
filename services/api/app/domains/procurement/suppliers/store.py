from __future__ import annotations

import os
from pathlib import Path

from tinydb import Query, TinyDB

DEFAULT_DB_PATH = Path(__file__).resolve().parents[4] / "db.json"
DB_PATH = Path(os.environ.get("SUPPLIERS_DB_PATH", DEFAULT_DB_PATH))
TABLE_NAME = "suppliers"

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


def _table():
    return get_db().table(TABLE_NAME)


def _normalize(doc_id: int, doc: dict) -> dict:
    return {key: value for key, value in doc.items() if key != "id"} | {"id": doc_id}


def insert(supplier_doc: dict) -> int:
    return _table().insert(supplier_doc)


def get_by_id(supplier_id: int) -> dict | None:
    doc = _table().get(doc_id=supplier_id)
    if doc is None:
        return None
    return _normalize(supplier_id, doc)


def get_by_name(name: str) -> dict | None:
    matches = _table().search(Query().name == name)
    if not matches:
        return None
    doc_id = matches[0].doc_id
    return _normalize(doc_id, dict(matches[0]))


def list_all() -> list[dict]:
    return [_normalize(doc.doc_id, dict(doc)) for doc in _table().all()]


def list_filtered(country: str | None = None, category: str | None = None) -> list[dict]:
    query = Query()
    condition = None
    if country is not None:
        condition = query.country == country
    if category is not None:
        category_condition = query.categories.test(lambda cats: category in cats)
        condition = category_condition if condition is None else (condition & category_condition)
    if condition is None:
        return list_all()
    return [_normalize(doc.doc_id, dict(doc)) for doc in _table().search(condition)]


def update(supplier_id: int, partial: dict) -> dict | None:
    if _table().get(doc_id=supplier_id) is None:
        return None
    _table().update(partial, doc_ids=[supplier_id])
    return get_by_id(supplier_id)


def clear_all() -> None:
    _table().truncate()
