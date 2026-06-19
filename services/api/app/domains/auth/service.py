from __future__ import annotations

from datetime import datetime, timezone

from app.domains.auth import token
from app.domains.auth.password import hash_password, verify_password
from app.domains.auth.schemas import TokenResponse, UserCreate, UserLogin
from app.domains.users import store


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def register(body: UserCreate) -> TokenResponse:
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
    access_token = token.create_access_token(user_id)
    return TokenResponse(access_token=access_token)


def login(body: UserLogin) -> TokenResponse:
    user = store.get_by_email(body.email)
    if user is None or not verify_password(body.password, user["hashed_password"]):
        raise InvalidCredentialsError
    if not user["is_active"]:
        raise InvalidCredentialsError
    access_token = token.create_access_token(user["id"])
    return TokenResponse(access_token=access_token)
