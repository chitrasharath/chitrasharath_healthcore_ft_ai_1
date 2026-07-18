"""Async task status helpers and dead-letter persistence (worker-safe)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from celery.result import AsyncResult
from sqlmodel import Session, SQLModel, select

from app.core.db import supabase_engine
from app.domains.async_tasks.models import DeadLetterTask

logger = logging.getLogger(__name__)

_CELERY_STATUS_MAP = {
    "PENDING": "pending",
    "STARTED": "started",
    "RETRY": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
}


def record_dead_letter(
    *,
    task_id: str,
    task_name: str,
    attempt: int,
    error: str,
    traceback: str | None = None,
) -> None:
    if supabase_engine is None:
        logger.error(
            "DATABASE_URL unset — cannot persist dead letter task_id=%s attempt=%s error=%s",
            task_id,
            attempt,
            error,
        )
        return

    SQLModel.metadata.create_all(supabase_engine)
    row = DeadLetterTask(
        task_id=task_id,
        task_name=task_name,
        attempt=attempt,
        error=error[:4000],
        traceback=(traceback[:8000] if traceback else None),
        created_at=datetime.now(timezone.utc),
    )
    try:
        with Session(supabase_engine) as session:
            session.add(row)
            session.commit()
    except Exception:
        logger.exception(
            "failed to persist dead letter task_id=%s attempt=%s",
            task_id,
            attempt,
        )


def get_task_status(task_id: str) -> dict[str, Any]:
    """Map Celery AsyncResult state to ticket vocabulary.

    Celery cannot distinguish an unknown task id from a not-yet-started task —
    both surface as ``pending``.
    """
    from services.celery_app import celery_app

    async_result = AsyncResult(task_id, app=celery_app)
    celery_state = async_result.state or "PENDING"
    status = _CELERY_STATUS_MAP.get(celery_state, "pending")
    result: Any | None = None
    if status == "success":
        result = async_result.result
    elif status == "failure":
        result = str(async_result.result)
    return {"task_id": task_id, "status": status, "result": result}


def list_dlq(*, limit: int = 50) -> list[DeadLetterTask]:
    if supabase_engine is None:
        return []
    capped = max(1, min(limit, 200))
    with Session(supabase_engine) as session:
        statement = (
            select(DeadLetterTask)
            .order_by(DeadLetterTask.created_at.desc())  # type: ignore[attr-defined]
            .limit(capped)
        )
        return list(session.exec(statement).all())
