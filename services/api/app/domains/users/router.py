from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import get_current_user
from app.domains.auth.schemas import UserCreate, UserResponse, UserUpdate
from app.domains.users import service
from app.domains.users.service import DuplicateEmailError, UserNotFoundError

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate) -> UserResponse:
    try:
        return service.create_user(body)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=422, detail="Email already registered") from exc


@router.get("", response_model=list[UserResponse])
def list_users(current_user: dict = Depends(get_current_user)) -> list[UserResponse]:
    return service.list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: dict = Depends(get_current_user)) -> UserResponse:
    try:
        return service.get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        return service.update_user(user_id, body)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=422, detail="Email already registered") from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    # TODO: restrict to admin when RBAC is implemented
    try:
        service.delete_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
