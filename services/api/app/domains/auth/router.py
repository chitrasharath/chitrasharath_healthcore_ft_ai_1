from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.domains.auth import service
from app.domains.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.domains.auth.service import DuplicateEmailError, InvalidCredentialsError
from app.domains.auth import reset_service
from app.domains.auth.reset_service import INVALID_RESET_TOKEN_MESSAGE
from app.domains.auth.token import InvalidResetTokenError
from app.domains.users import service as users_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: UserCreate) -> TokenResponse:
    try:
        return service.register(body)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=422, detail="Email already registered") from exc


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin) -> TokenResponse:
    try:
        return service.login(body)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return users_service.to_user_response(current_user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    return reset_service.forgot_password(body)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(body: ResetPasswordRequest) -> ResetPasswordResponse:
    try:
        return reset_service.reset_password(body)
    except InvalidResetTokenError as exc:
        raise HTTPException(status_code=400, detail=INVALID_RESET_TOKEN_MESSAGE) from exc
