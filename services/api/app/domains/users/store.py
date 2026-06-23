from __future__ import annotations

from pathlib import Path

from tinydb import Query

from app.core.db import get_db, reset_db

TABLE_NAME = "users"

__all__ = ["reset_db"]


def _table():
    return get_db().table(TABLE_NAME)


def _normalize(doc_id: int, doc: dict) -> dict:
    return {key: value for key, value in doc.items() if key != "id"} | {"id": doc_id}


def _normalize_email(email: str) -> str:
    return email.lower()


def insert_user(doc: dict) -> int:
    payload = dict(doc)
    payload["email"] = _normalize_email(payload["email"])
    return _table().insert(payload)


def get_by_id(user_id: int) -> dict | None:
    doc = _table().get(doc_id=user_id)
    if doc is None:
        return None
    return _normalize(user_id, doc)


def get_by_email(email: str) -> dict | None:
    matches = _table().search(Query().email == _normalize_email(email))
    if not matches:
        return None
    doc_id = matches[0].doc_id
    return _normalize(doc_id, dict(matches[0]))


def get_all() -> list[dict]:
    return [_normalize(doc.doc_id, dict(doc)) for doc in _table().all()]


def update_user(user_id: int, partial: dict) -> dict | None:
    if _table().get(doc_id=user_id) is None:
        return None
    payload = dict(partial)
    if "email" in payload:
        payload["email"] = _normalize_email(payload["email"])
    _table().update(payload, doc_ids=[user_id])
    return get_by_id(user_id)


def delete_user(user_id: int) -> bool:
    if _table().get(doc_id=user_id) is None:
        return False
    removed = _table().remove(doc_ids=[user_id])
    return len(removed) > 0


def email_exists(email: str) -> bool:
    return get_by_email(email) is not None


def clear_all() -> None:
    _table().truncate()
