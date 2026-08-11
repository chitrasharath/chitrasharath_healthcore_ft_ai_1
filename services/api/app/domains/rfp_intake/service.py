from __future__ import annotations

import hashlib
import logging
from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlmodel import Session, select

from app.domains.jobs import job_runner
from app.domains.jobs.models import JobRun
from app.domains.rfp_intake import store
from app.domains.rfp_intake.schemas import (
    RerunAccepted,
    TicketDetail,
    TicketSummary,
    UploadAccepted,
)

logger = logging.getLogger(__name__)

JOB_NAME = "rfp_intake"
MAX_PDF_BYTES = 20 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_DIR = REPO_ROOT / "data" / "raw"


def _latest_job(session: Session, ticket_id: str) -> JobRun | None:
    statement = (
        select(JobRun)
        .where(JobRun.job_name == JOB_NAME, JobRun.target_key == ticket_id)
        .order_by(JobRun.created_at.desc())  # type: ignore[arg-type]
    )
    return session.exec(statement).first()


def _run_background(ticket_id: str, job_run_id: str) -> None:
    try:
        from data.pipelines.rfp_intake.runner import run_intake

        run_intake(ticket_id, job_run_id=job_run_id)
    except Exception:
        logger.exception("background rfp_intake failed ticket_id=%s", ticket_id)


async def upload_pdf(
    session: Session,
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> UploadAccepted:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    if content_type not in ("application/pdf", "application/x-pdf") and not filename.endswith(
        ".pdf"
    ):
        raise HTTPException(status_code=415, detail="Only PDF uploads are accepted")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF exceeds 20 MB limit")

    digest = hashlib.sha256(data).hexdigest()
    existing = store.find_by_sha256(session, digest)
    if existing is not None and existing.status in ("analyzing", "intake_complete", "discarded"):
        if job_runner.has_processing_lock_for_key(session, JOB_NAME, existing.ticket_id):
            return UploadAccepted(
                ticket_id=existing.ticket_id,
                rfp_id=existing.rfp_id,
                status=existing.status,
            )
        if existing.status != "analyzing" or existing.needs_human_review:
            return UploadAccepted(
                ticket_id=existing.ticket_id,
                rfp_id=existing.rfp_id,
                status=existing.status,
            )

    ticket = store.create_ticket(
        session,
        raw_pdf_path="",  # set after path known
        content_sha256=digest,
    )
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RAW_DIR / f"{ticket.ticket_id}.pdf"
    pdf_path.write_bytes(data)
    ticket.raw_pdf_path = str(pdf_path)
    store.touch_ticket(session, ticket)

    job_runner.reclaim_stale_locks(session, JOB_NAME)
    run = job_runner.create_pending_for_key(
        session,
        JOB_NAME,
        ticket.ticket_id,
        date.today(),
    )
    session.commit()

    background_tasks.add_task(_run_background, ticket.ticket_id, str(run.id))
    return UploadAccepted(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
    )


def list_ticket_summaries(session: Session) -> list[TicketSummary]:
    tickets = store.list_tickets(session)
    out: list[TicketSummary] = []
    for ticket in tickets:
        meta = store.get_metadata(session, ticket.ticket_id)
        job = _latest_job(session, ticket.ticket_id)
        out.append(
            store.to_summary(
                ticket,
                meta,
                job_status=job.status if job else None,
            )
        )
    return out


def get_ticket_detail(session: Session, ticket_id: str) -> TicketDetail:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    meta = store.get_metadata(session, ticket_id)
    sections = store.list_sections(session, ticket_id)
    job = _latest_job(session, ticket_id)
    return store.to_detail(
        ticket,
        meta,
        sections,
        job_status=job.status if job else None,
        job_checkpoint=job.checkpoint if job else None,
        job_error=job.error_message if job else None,
    )


def rerun_ticket(
    session: Session,
    ticket_id: str,
    background_tasks: BackgroundTasks,
) -> RerunAccepted:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not ticket.raw_pdf_path or not Path(ticket.raw_pdf_path).is_file():
        raise HTTPException(status_code=400, detail="PDF artifact missing for re-run")

    job_runner.reclaim_stale_locks(session, JOB_NAME)
    if job_runner.has_processing_lock_for_key(session, JOB_NAME, ticket_id):
        raise HTTPException(status_code=409, detail="Intake already processing for this ticket")

    store.set_ticket_status(session, ticket, "analyzing", needs_human_review=False)
    run = job_runner.create_pending_for_key(
        session,
        JOB_NAME,
        ticket_id,
        date.today(),
    )
    session.commit()
    background_tasks.add_task(_run_background, ticket_id, str(run.id))
    return RerunAccepted(ticket_id=ticket_id, status="analyzing")
