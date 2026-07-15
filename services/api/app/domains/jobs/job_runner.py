"""Job run status service — no FastAPI imports (standalone script safe)."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from app.domains.jobs.models import JobRun

logger = logging.getLogger(__name__)

STALE_LOCK_HOURS = 6


def _stale_lock_hours() -> int:
    raw = os.environ.get("STALE_LOCK_HOURS")
    if raw is None:
        return STALE_LOCK_HOURS
    return int(raw)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_pending(session: Session, job_name: str, target_date: date) -> JobRun:
    run = JobRun(
        job_name=job_name,
        target_date=target_date,
        status="pending",
        created_at=_utcnow(),
    )
    session.add(run)
    session.flush()
    return run


def mark_processing(session: Session, run: JobRun) -> None:
    run.status = "processing"
    run.started_at = _utcnow()
    session.add(run)
    session.flush()


def mark_completed(session: Session, run: JobRun) -> None:
    run.status = "completed"
    run.finished_at = _utcnow()
    session.add(run)
    session.flush()


def mark_failed(session: Session, run: JobRun, error: str) -> None:
    run.status = "failed"
    run.finished_at = _utcnow()
    run.error_message = str(error)[:500]
    session.add(run)
    session.flush()


def _stale_cutoff() -> datetime:
    return _utcnow() - timedelta(hours=_stale_lock_hours())


def reclaim_stale_locks(session: Session, job_name: str) -> int:
    hours = _stale_lock_hours()
    cutoff = _utcnow() - timedelta(hours=hours)
    statement = select(JobRun).where(
        JobRun.job_name == job_name,
        JobRun.status == "processing",
        JobRun.started_at != None,  # noqa: E711
        JobRun.started_at < cutoff,  # type: ignore[operator]
    )
    rows = list(session.exec(statement).all())
    message = f"reclaimed: stale processing lock (no heartbeat for >{hours}h)"
    for run in rows:
        mark_failed(session, run, message)
        logger.warning(
            "status=failed reclaimed stale processing lock id=%s job_name=%s",
            run.id,
            job_name,
        )
    return len(rows)


def has_processing_lock(session: Session, job_name: str) -> bool:
    cutoff = _stale_cutoff()
    statement = select(JobRun).where(
        JobRun.job_name == job_name,
        JobRun.status == "processing",
    )
    for run in session.exec(statement).all():
        if run.started_at is None:
            return True
        started = run.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started >= cutoff:
            return True
    return False


def has_completed_for_date(
    session: Session,
    job_name: str,
    target_date: date,
) -> bool:
    statement = select(JobRun).where(
        JobRun.job_name == job_name,
        JobRun.target_date == target_date,
        JobRun.status == "completed",
    )
    return session.exec(statement).first() is not None
