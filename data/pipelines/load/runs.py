from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Session

from app.domains.telemetry.reporting_models import PipelineRun
from data.pipelines.config import PIPELINE_VERSION
from data.pipelines.load import repository as repo


def start_run(session: Session) -> UUID:
    run_id = uuid4()
    run = PipelineRun(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        status="running",
        pipeline_version=PIPELINE_VERSION,
        rows_extracted=0,
        rows_loaded=0,
        rows_quarantined=0,
    )
    repo.insert_pipeline_run(session, run)
    return run_id


def load_run(session: Session, run_id: UUID) -> PipelineRun:
    run = repo.get_pipeline_run(session, run_id)
    if run is None:
        raise RuntimeError(f"pipeline_runs row missing for {run_id}")
    return run


def finish_run(
    session: Session,
    run_id: UUID,
    *,
    status: str,
    watermark_from: datetime | None = None,
    watermark_to: datetime | None = None,
    rows_extracted: int = 0,
    rows_loaded: int = 0,
    rows_quarantined: int = 0,
    error_summary: str | None = None,
    checkpoint: str | None = None,
) -> None:
    run = load_run(session, run_id)
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.rows_extracted = rows_extracted
    run.rows_loaded = rows_loaded
    run.rows_quarantined = rows_quarantined
    run.error_summary = error_summary
    run.checkpoint = checkpoint
    if watermark_from is not None:
        run.watermark_from = watermark_from
    if watermark_to is not None and status in {"success", "partial"}:
        run.watermark_to = watermark_to
    elif watermark_to is not None and status not in {"success", "partial"}:
        run.watermark_to = watermark_to if status == "quarantined" else run.watermark_to
        run.watermark_from = watermark_from
    repo.update_pipeline_run(session, run)
