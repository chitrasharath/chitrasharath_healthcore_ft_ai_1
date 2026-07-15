from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.domains.jobs import models as job_models  # noqa: F401
from app.domains.jobs.job_runner import (
    create_pending,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
    reclaim_stale_locks,
)
from app.domains.jobs.models import JobRun

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


def test_pending_to_processing_to_completed_sets_timestamps(session: Session) -> None:
    target = date(2026, 7, 14)
    run = create_pending(session, "nightly_export", target)
    session.commit()
    assert run.status == "pending"
    assert run.created_at is not None
    assert run.started_at is None
    assert run.finished_at is None

    mark_processing(session, run)
    session.commit()
    assert run.status == "processing"
    assert run.started_at is not None

    mark_completed(session, run)
    session.commit()
    assert run.status == "completed"
    assert run.finished_at is not None


def test_pending_to_processing_to_failed_records_error(session: Session) -> None:
    run = create_pending(session, "nightly_export", date(2026, 7, 14))
    mark_processing(session, run)
    mark_failed(session, run, "boom " + ("x" * 600))
    session.commit()

    assert run.status == "failed"
    assert run.finished_at is not None
    assert run.error_message is not None
    assert len(run.error_message) == 500
    assert run.status != "processing"


def test_has_completed_for_date_is_per_target_date(session: Session) -> None:
    run = create_pending(session, "nightly_export", date(2026, 7, 14))
    mark_processing(session, run)
    mark_completed(session, run)
    session.commit()

    assert has_completed_for_date(session, "nightly_export", date(2026, 7, 14)) is True
    assert has_completed_for_date(session, "nightly_export", date(2026, 7, 15)) is False


def test_has_processing_lock_sees_active_ignores_completed(session: Session) -> None:
    done = create_pending(session, "nightly_export", date(2026, 7, 10))
    mark_processing(session, done)
    mark_completed(session, done)
    session.commit()
    assert has_processing_lock(session, "nightly_export") is False

    active = create_pending(session, "nightly_export", date(2026, 7, 14))
    mark_processing(session, active)
    session.commit()
    assert has_processing_lock(session, "nightly_export") is True


def test_reclaim_stale_locks_flips_stale_leaves_fresh(session: Session) -> None:
    stale = create_pending(session, "nightly_export", date(2026, 7, 1))
    mark_processing(session, stale)
    stale.started_at = datetime.now(timezone.utc) - timedelta(hours=12)
    session.add(stale)

    fresh = create_pending(session, "nightly_export", date(2026, 7, 14))
    mark_processing(session, fresh)
    session.commit()

    count = reclaim_stale_locks(session, "nightly_export")
    session.commit()

    session.refresh(stale)
    session.refresh(fresh)
    assert count == 1
    assert stale.status == "failed"
    assert stale.error_message is not None
    assert "reclaimed" in stale.error_message
    assert fresh.status == "processing"
