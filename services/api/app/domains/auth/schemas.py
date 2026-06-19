from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


def _validate_password_min_length(value: str) -> str:
    if len(value) < 8:
        raise ValueError("password must be at least 8 characters")
    return value


class User(BaseModel):
    id: int
    email: EmailStr
    hashed_password: str
    name: str = ""
    is_active: bool = True
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str = ""

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        return _validate_password_min_length(v)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    name: str | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_password_min_length(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    created_at: datetime
