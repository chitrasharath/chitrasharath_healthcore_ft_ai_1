"""Tests for scripts/nightly_export.py — pipeline subprocess is always mocked."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
os.environ.setdefault("DATABASE_URL", "")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
API_ROOT = REPO_ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.domains.jobs import models as job_models  # noqa: E402, F401
from app.domains.jobs.job_runner import (  # noqa: E402
    create_pending,
    mark_completed,
    mark_processing,
)
from app.domains.jobs.models import JobRun  # noqa: E402
from app.domains.telemetry import models as telemetry_models  # noqa: E402, F401
from scripts import nightly_export as nightly  # noqa: E402

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr("app.core.db.supabase_engine", test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def raw_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    def _csv_path(target: date) -> Path:
        return tmp_path / f"telemetry_{target.isoformat()}.csv"

    monkeypatch.setattr(nightly, "_csv_path", _csv_path)
    return tmp_path


def _count_jobs(status: str | None = None) -> int:
    with Session(test_engine) as session:
        statement = select(JobRun)
        if status is not None:
            statement = statement.where(JobRun.status == status)
        return len(list(session.exec(statement).all()))


def test_completed_row_skips_csv_and_subprocess(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = date(2026, 7, 14)
    monkeypatch.setenv("TARGET_DATE", target.isoformat())
    with Session(test_engine) as session:
        run = create_pending(session, "nightly_export", target)
        mark_processing(session, run)
        mark_completed(session, run)
        session.commit()

    sub = MagicMock()
    monkeypatch.setattr(subprocess, "run", sub)

    assert nightly.main() == 0
    sub.assert_not_called()
    assert not (raw_dir / f"telemetry_{target.isoformat()}.csv").exists()
    assert _count_jobs() == 1


def test_active_processing_exits_zero_no_new_row(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = date(2026, 7, 14)
    monkeypatch.setenv("TARGET_DATE", target.isoformat())
    with Session(test_engine) as session:
        run = create_pending(session, "nightly_export", date(2026, 7, 10))
        mark_processing(session, run)
        session.commit()

    sub = MagicMock()
    monkeypatch.setattr(subprocess, "run", sub)

    assert nightly.main() == 0
    sub.assert_not_called()
    assert _count_jobs() == 1
    assert _count_jobs("processing") == 1


def test_existing_csv_skips_export_but_triggers_pipeline(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = date(2026, 7, 14)
    monkeypatch.setenv("TARGET_DATE", target.isoformat())
    csv_path = raw_dir / f"telemetry_{target.isoformat()}.csv"
    csv_path.write_text("id\n", encoding="utf-8")

    sub = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(subprocess, "run", sub)

    assert nightly.main() == 0
    sub.assert_called_once()
    argv = sub.call_args.args[0]
    assert "--start" in argv and "--end" in argv
    assert csv_path.read_text(encoding="utf-8") == "id\n"
    assert _count_jobs("completed") == 1


def test_pipeline_failure_marks_failed_no_processing_left(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = date(2026, 7, 14)
    monkeypatch.setenv("TARGET_DATE", target.isoformat())

    err = subprocess.CalledProcessError(
        returncode=2,
        cmd=["uv", "run", "python", "data/pipelines/pipeline.py"],
        stderr="pipeline boom stderr tail",
    )
    monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=err))

    assert nightly.main() == 1
    assert _count_jobs("processing") == 0
    with Session(test_engine) as session:
        run = session.exec(select(JobRun)).one()
        assert run.status == "failed"
        assert run.error_message is not None
        assert "pipeline boom stderr tail" in run.error_message


def test_target_date_drives_csv_name_and_pipeline_argv(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = date(2026, 3, 15)
    monkeypatch.setenv("TARGET_DATE", target.isoformat())
    sub = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(subprocess, "run", sub)

    assert nightly.main() == 0

    expected_csv = raw_dir / "telemetry_2026-03-15.csv"
    assert expected_csv.is_file()

    argv = sub.call_args.args[0]
    start_idx = argv.index("--start") + 1
    end_idx = argv.index("--end") + 1
    assert argv[start_idx] == "2026-03-15T00:00:00+00:00"
    assert argv[end_idx] == "2026-03-16T00:00:00+00:00"


def test_stale_lock_reclaim_allows_new_run(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = date(2026, 7, 14)
    monkeypatch.setenv("TARGET_DATE", target.isoformat())
    with Session(test_engine) as session:
        stale = create_pending(session, "nightly_export", date(2026, 7, 1))
        mark_processing(session, stale)
        stale.started_at = datetime.now(timezone.utc) - timedelta(hours=12)
        session.add(stale)
        session.commit()

    monkeypatch.setattr(
        subprocess,
        "run",
        MagicMock(return_value=MagicMock(returncode=0)),
    )
    assert nightly.main() == 0
    assert _count_jobs("failed") == 1
    assert _count_jobs("completed") == 1
