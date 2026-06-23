from __future__ import annotations

from datetime import datetime, timezone

from app.domains.auth.password import hash_password
from app.domains.auth.schemas import UserCreate, UserResponse, UserUpdate
from app.domains.users import store


class DuplicateEmailError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_user_response(doc: dict) -> UserResponse:
    payload = dict(doc)
    payload.setdefault("name", "")
    created_at = payload["created_at"]
    if isinstance(created_at, str):
        payload["created_at"] = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return UserResponse(**payload)


def create_user(body: UserCreate) -> UserResponse:
    if store.email_exists(body.email):
        raise DuplicateEmailError
    doc = {
        "email": body.email,
        "name": body.name,
        "hashed_password": hash_password(body.password),
        "is_active": True,
        "created_at": _utc_now().isoformat(),
    }
    user_id = store.insert_user(doc)
    created = store.get_by_id(user_id)
    assert created is not None
    return to_user_response(created)


def list_users() -> list[UserResponse]:
    return [to_user_response(doc) for doc in store.get_all()]


def get_user(user_id: int) -> UserResponse:
    doc = store.get_by_id(user_id)
    if doc is None:
        raise UserNotFoundError
    return to_user_response(doc)


def update_user(user_id: int, body: UserUpdate) -> UserResponse:
    existing = store.get_by_id(user_id)
    if existing is None:
        raise UserNotFoundError
    partial = body.model_dump(exclude_none=True)
    if "password" in partial:
        partial["hashed_password"] = hash_password(partial.pop("password"))
    if "email" in partial:
        other = store.get_by_email(partial["email"])
        if other is not None and other["id"] != user_id:
            raise DuplicateEmailError
    updated = store.update_user(user_id, partial)
    assert updated is not None
    return to_user_response(updated)


def delete_user(user_id: int) -> None:
    if not store.delete_user(user_id):
        raise UserNotFoundError
