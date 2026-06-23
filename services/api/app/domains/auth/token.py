from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
RESET_TOKEN_EXPIRE_MINUTES = 30
RESET_TOKEN_PURPOSE = "reset"


class InvalidResetTokenError(Exception):
    pass


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_reset_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "purpose": RESET_TOKEN_PURPOSE,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_reset_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("purpose") != RESET_TOKEN_PURPOSE:
            raise InvalidResetTokenError("invalid purpose")
        sub = payload.get("sub")
        if sub is None:
            raise InvalidResetTokenError("missing subject")
        return int(sub)
    except (JWTError, ValueError, InvalidResetTokenError) as exc:
        raise InvalidResetTokenError("invalid reset token") from exc


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return int(sub)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
