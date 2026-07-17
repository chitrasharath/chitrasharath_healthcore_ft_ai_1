#!/usr/bin/env python3
"""Nightly telemetry CSV export + Milestone 6 pipeline trigger (standalone OS process)."""

from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

JOB_NAME = "nightly_export"
CSV_COLUMNS = (
    "id",
    "timestamp",
    "service",
    "event_type",
    "level",
    "value",
    "message",
    "tags",
)

logging.Formatter.converter = lambda *args: datetime.now(timezone.utc).timetuple()  # type: ignore[assignment]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [nightly_export] %(message)s",
)
logger = logging.getLogger("nightly_export")


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _bootstrap_env() -> None:
    """Load repo-root `.env`, then fill gaps from `services/api/.env`."""
    root_env = _parse_env_file(_REPO_ROOT / ".env")
    api_env = _parse_env_file(_API_ROOT / ".env")
    for key, value in root_env.items():
        os.environ.setdefault(key, value)
    for key, value in api_env.items():
        os.environ.setdefault(key, value)


def _resolve_target_date() -> date:
    raw = os.environ.get("TARGET_DATE")
    if raw is None or raw.strip() == "":
        return datetime.now(timezone.utc).date() - timedelta(days=1)
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        logger.error(
            "status=failed TARGET_DATE must be YYYY-MM-DD, got %r",
            raw,
        )
        sys.exit(1)


def _day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _csv_path(target: date) -> Path:
    return _REPO_ROOT / "data" / "raw" / f"telemetry_{target.isoformat()}.csv"


def _export_csv(session, start: datetime, end: datetime, dest: Path) -> None:
    from sqlmodel import select

    from app.domains.telemetry.models import TelemetryEventRow

    statement = (
        select(TelemetryEventRow)
        .where(TelemetryEventRow.timestamp >= start)
        .where(TelemetryEventRow.timestamp < end)
        .order_by(TelemetryEventRow.timestamp)
    )
    rows = list(session.exec(statement).all())

    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
        writer = csv.DictWriter(tmp, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": str(row.id),
                    "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "service": row.service,
                    "event_type": row.event_type,
                    "level": row.level,
                    "value": "" if row.value is None else row.value,
                    "message": "" if row.message is None else row.message,
                    "tags": json.dumps(row.tags or {}, ensure_ascii=False),
                }
            )
    os.replace(tmp_path, dest)
    logger.info(
        "status=processing exported %d rows to %s",
        len(rows),
        dest,
    )


def _run_pipeline(start: datetime, end: datetime) -> None:
    argv = [
        "uv",
        "run",
        "python",
        "data/pipelines/pipeline.py",
        "--start",
        start.isoformat(),
        "--end",
        end.isoformat(),
    ]
    logger.info("status=processing triggering pipeline: %s", " ".join(argv))
    try:
        subprocess.run(
            argv,
            cwd=str(_REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr_tail = (exc.stderr or "")[-2000:]
        raise RuntimeError(
            f"pipeline subprocess failed (exit {exc.returncode}): {stderr_tail}"
        ) from exc


def _mark_failed_fresh(engine, run_id: UUID, error: str) -> None:
    from sqlmodel import Session

    from app.domains.jobs.job_runner import mark_failed
    from app.domains.jobs.models import JobRun

    with Session(engine) as session:
        run = session.get(JobRun, run_id)
        if run is None:
            return
        if run.status in {"processing", "pending"}:
            mark_failed(session, run, error)
            session.commit()


def main() -> int:
    _bootstrap_env()

    from sqlmodel import Session, SQLModel

    from app.core.db import supabase_engine
    from app.domains.jobs import models as job_models  # noqa: F401
    from app.domains.jobs.job_runner import (
        create_pending,
        has_completed_for_date,
        has_processing_lock,
        mark_completed,
        mark_processing,
        reclaim_stale_locks,
    )
    from app.domains.telemetry import models as telemetry_models  # noqa: F401

    if supabase_engine is None:
        logger.error(
            "status=failed DATABASE_URL is not set — set it in repo-root .env "
            "or services/api/.env (and run with cwd=repo root)."
        )
        return 1

    engine = supabase_engine
    SQLModel.metadata.create_all(engine)

    target = _resolve_target_date()
    start, end = _day_bounds(target)
    dest = _csv_path(target)
    logger.info(
        "status=pending start job_name=%s target_date=%s window=[%s, %s)",
        JOB_NAME,
        target.isoformat(),
        start.isoformat(),
        end.isoformat(),
    )

    with Session(engine) as session:
        reclaim_stale_locks(session, JOB_NAME)
        session.commit()

        if has_processing_lock(session, JOB_NAME):
            logger.info(
                "status=processing lock held — aborting silently (exit 0)"
            )
            return 0

        if has_completed_for_date(session, JOB_NAME, target):
            logger.info(
                "status=completed skipped as duplicate target_date=%s",
                target.isoformat(),
            )
            return 0

        run = create_pending(session, JOB_NAME, target)
        mark_processing(session, run)
        session.commit()
        run_id = run.id

    failed_msg: str | None = None
    try:
        with Session(engine) as session:
            if dest.is_file():
                logger.info(
                    "status=processing CSV already exists — skip export: %s",
                    dest,
                )
            else:
                _export_csv(session, start, end, dest)

        _run_pipeline(start, end)

        with Session(engine) as session:
            from app.domains.jobs.models import JobRun

            run = session.get(JobRun, run_id)
            if run is None:
                raise RuntimeError(f"job_runs row {run_id} missing after work")
            mark_completed(session, run)
            session.commit()
        logger.info(
            "status=completed job_name=%s target_date=%s",
            JOB_NAME,
            target.isoformat(),
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        failed_msg = str(exc)
        logger.exception("status=failed %s", failed_msg)
        _mark_failed_fresh(engine, run_id, failed_msg)
        return 1
    except BaseException as exc:
        # KeyboardInterrupt / SystemExit — do not leave a processing zombie.
        failed_msg = f"{type(exc).__name__}: {exc}"
        logger.exception("status=failed %s", failed_msg)
        _mark_failed_fresh(engine, run_id, failed_msg)
        raise
    finally:
        from sqlmodel import Session as _Session

        from app.domains.jobs.job_runner import mark_failed as _mf
        from app.domains.jobs.models import JobRun as _JobRun

        with _Session(engine) as session:
            run = session.get(_JobRun, run_id)
            if run is not None and run.status in {"processing", "pending"}:
                _mf(session, run, failed_msg or "aborted before completion")
                session.commit()
                logger.error(
                    "status=failed safety-net transitioned stranded row %s",
                    run_id,
                )


if __name__ == "__main__":
    sys.exit(main())
