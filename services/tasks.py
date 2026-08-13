"""Celery tasks — telemetry ETL with retries, backoff, and DLQ."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from services.celery_app import celery_app

# Ensure DLQ table is registered for worker-side create_all
import app.domains.async_tasks.models  # noqa: F401, E402
from app.domains.async_tasks.service import record_dead_letter  # noqa: E402

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
MAX_RETRIES = MAX_ATTEMPTS - 1  # 2 Celery retries → 3 total executions
BASE_BACKOFF_SECONDS = 2


def log_task(
    *,
    task_id: str,
    attempt: int,
    status: str,
    duration: float,
    error: str | None = None,
) -> None:
    rounded = round(duration, 3)
    if error:
        logger.error(
            "task_id=%s attempt=%s status=%s duration=%ss error=%s",
            task_id,
            attempt,
            status,
            rounded,
            error,
        )
    else:
        logger.info(
            "task_id=%s attempt=%s status=%s duration=%ss",
            task_id,
            attempt,
            status,
            rounded,
        )


class DLQTask(celery_app.Task):
    """Persist a dead-letter row when retries are exhausted."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        attempt = self.request.retries + 1
        record_dead_letter(
            task_id=task_id,
            task_name=self.name or "pipeline.run_telemetry_etl",
            attempt=attempt,
            error=repr(exc),
            traceback=str(einfo) if einfo is not None else None,
        )


@celery_app.task(
    bind=True,
    base=DLQTask,
    name="pipeline.run_telemetry_etl",
    max_retries=MAX_RETRIES,
)
def run_telemetry_etl(self, run_id: str, *, _force_fail: bool = False):
    """Run telemetry ETL for ``run_id``. Retries share the same run_id (idempotent upsert)."""
    attempt = self.request.retries + 1
    started = time.monotonic()
    try:
        if _force_fail:
            raise RuntimeError("forced failure for DLQ demonstration")

        from data.pipelines.pipeline import telemetry_etl_flow

        result = telemetry_etl_flow(run_id=UUID(run_id))
        duration = time.monotonic() - started
        log_task(
            task_id=self.request.id,
            attempt=attempt,
            status="success",
            duration=duration,
        )
        return {"run_id": run_id, "rows_loaded": result}
    except Exception as exc:
        duration = time.monotonic() - started
        log_task(
            task_id=self.request.id,
            attempt=attempt,
            status="failure",
            duration=duration,
            error=str(exc),
        )
        if self.request.retries >= MAX_RETRIES:
            raise
        countdown = BASE_BACKOFF_SECONDS * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
