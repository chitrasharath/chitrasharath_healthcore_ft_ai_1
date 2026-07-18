from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.domains.async_tasks.schemas import (
    DeadLetterItem,
    DeadLetterListResponse,
    TaskStatusResponse,
)
from app.domains.async_tasks.service import get_task_status, list_dlq

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/dlq", response_model=DeadLetterListResponse)
def get_dead_letter_queue(
    limit: int = Query(default=50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
) -> DeadLetterListResponse:
    rows = list_dlq(limit=limit)
    return DeadLetterListResponse(
        items=[
            DeadLetterItem(
                id=row.id,
                task_id=row.task_id,
                task_name=row.task_name,
                attempt=row.attempt,
                error=row.error,
                created_at=row.created_at,
            )
            for row in rows
        ],
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task(
    task_id: str,
    _user: dict = Depends(get_current_user),
) -> TaskStatusResponse:
    """Return lowercase pending/started/success/failure for a Celery task id."""
    payload = get_task_status(task_id)
    return TaskStatusResponse(**payload)
