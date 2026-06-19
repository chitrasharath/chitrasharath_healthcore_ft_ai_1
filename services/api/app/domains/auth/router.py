from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.domains.auth import service
from app.domains.auth.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from app.domains.auth.service import DuplicateEmailError, InvalidCredentialsError
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
