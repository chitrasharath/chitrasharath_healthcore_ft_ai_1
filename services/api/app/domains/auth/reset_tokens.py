from __future__ import annotations

from tinydb import Query

from app.core.db import get_db

TABLE_NAME = "used_reset_tokens"


def _table():
    return get_db().table(TABLE_NAME)


def is_token_used(token: str) -> bool:
    return len(_table().search(Query().token == token)) > 0


def mark_token_used(token: str) -> None:
    if not is_token_used(token):
        _table().insert({"token": token})


def clear_all() -> None:
    _table().truncate()
