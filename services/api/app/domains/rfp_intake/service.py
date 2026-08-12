from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlmodel import Session, select

from app.domains.jobs import job_runner
from app.domains.jobs.models import JobRun
from app.domains.rfp_intake import store
from app.domains.rfp_intake.schemas import (
    DraftingAccepted,
    RedraftAccepted,
    ReleaseRedactedAccepted,
    RerunAccepted,
    TicketDetail,
    TicketSummary,
    UploadAccepted,
)

logger = logging.getLogger(__name__)

JOB_NAME = "rfp_intake"
DRAFT_JOB_NAME = "rfp_drafting"
MAX_PDF_BYTES = 20 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_DIR = REPO_ROOT / "data" / "raw"


def _latest_job(session: Session, ticket_id: str, job_name: str = JOB_NAME) -> JobRun | None:
    statement = (
        select(JobRun)
        .where(JobRun.job_name == job_name, JobRun.target_key == ticket_id)
        .order_by(JobRun.created_at.desc())  # type: ignore[arg-type]
    )
    return session.exec(statement).first()


def _latest_any_job(session: Session, ticket_id: str) -> JobRun | None:
    draft = _latest_job(session, ticket_id, DRAFT_JOB_NAME)
    intake = _latest_job(session, ticket_id, JOB_NAME)
    if draft is None:
        return intake
    if intake is None:
        return draft
    d_at = draft.created_at or datetime.min.replace(tzinfo=None)
    i_at = intake.created_at or datetime.min.replace(tzinfo=None)
    if d_at >= i_at:
        return draft
    return intake


def _run_background(ticket_id: str, job_run_id: str) -> None:
    try:
        from data.pipelines.rfp_intake.runner import run_intake

        run_intake(ticket_id, job_run_id=job_run_id)
    except Exception:
        logger.exception("background rfp_intake failed ticket_id=%s", ticket_id)


def _run_drafting_background(
    ticket_id: str,
    job_run_id: str,
    department_id: str | None = None,
) -> None:
    try:
        from data.pipelines.rfp_intake.drafting_runner import run_drafting

        run_drafting(ticket_id, job_run_id=job_run_id, department_id=department_id)
    except Exception:
        logger.exception("background rfp_drafting failed ticket_id=%s", ticket_id)


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
        sections = store.list_sections(session, ticket.ticket_id)
        job = _latest_any_job(session, ticket.ticket_id)
        out.append(
            store.to_summary(
                ticket,
                meta,
                job_status=job.status if job else None,
                sections=sections,
            )
        )
    return out


def get_ticket_detail(session: Session, ticket_id: str) -> TicketDetail:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    meta = store.get_metadata(session, ticket_id)
    sections = store.list_sections(session, ticket_id)
    evaluations = store.list_evaluations(session, ticket_id)
    job = _latest_any_job(session, ticket_id)
    return store.to_detail(
        ticket,
        meta,
        sections,
        job_status=job.status if job else None,
        job_checkpoint=job.checkpoint if job else None,
        job_error=job.error_message if job else None,
        evaluations=evaluations,
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


def start_drafting(
    session: Session,
    ticket_id: str,
    background_tasks: BackgroundTasks,
) -> DraftingAccepted:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Soft-idempotent: already in Phase 2
    if ticket.status in ("drafting", "under_evaluation"):
        return DraftingAccepted(
            ticket_id=ticket_id,
            status=ticket.status,
            message="drafting already in progress",
        )

    if ticket.status != "intake_complete":
        raise HTTPException(
            status_code=409,
            detail=f"Ticket must be intake_complete to start drafting (got {ticket.status})",
        )

    sections = store.list_sections(session, ticket_id)
    if not sections:
        raise HTTPException(status_code=400, detail="No department sections to draft")

    job_runner.reclaim_stale_locks(session, DRAFT_JOB_NAME)
    if job_runner.has_processing_lock_for_key(session, DRAFT_JOB_NAME, ticket_id):
        return DraftingAccepted(
            ticket_id=ticket_id,
            status=ticket.status,
            message="drafting already processing",
        )

    store.set_ticket_status(session, ticket, "drafting")
    run = job_runner.create_pending_for_key(
        session,
        DRAFT_JOB_NAME,
        ticket_id,
        date.today(),
    )
    session.commit()
    background_tasks.add_task(_run_drafting_background, ticket_id, str(run.id), None)
    return DraftingAccepted(ticket_id=ticket_id, status="drafting")


def redraft_section(
    session: Session,
    ticket_id: str,
    department_id: str,
    background_tasks: BackgroundTasks,
) -> RedraftAccepted:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    sections = store.list_sections(session, ticket_id)
    section = next((s for s in sections if s.department_id == department_id), None)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    if section.status != "needs_human_review":
        raise HTTPException(
            status_code=409,
            detail="Redraft only allowed for sections in needs_human_review",
        )

    job_runner.reclaim_stale_locks(session, DRAFT_JOB_NAME)
    if job_runner.has_processing_lock_for_key(session, DRAFT_JOB_NAME, ticket_id):
        raise HTTPException(status_code=409, detail="Drafting already processing for this ticket")

    store.reset_section_for_redraft(session, ticket_id, department_id)
    if ticket.status not in ("drafting", "under_evaluation"):
        store.set_ticket_status(session, ticket, "drafting")

    run = job_runner.create_pending_for_key(
        session,
        DRAFT_JOB_NAME,
        ticket_id,
        date.today(),
    )
    session.commit()
    background_tasks.add_task(
        _run_drafting_background,
        ticket_id,
        str(run.id),
        department_id,
    )
    return RedraftAccepted(
        ticket_id=ticket_id,
        department_id=department_id,
        status="drafting",
    )


def release_redacted_section(
    session: Session,
    ticket_id: str,
    department_id: str,
) -> ReleaseRedactedAccepted:
    """Redact PHI on an existing draft and release the section if scrub succeeds."""
    from data.pipelines.rfp_intake.agents.evaluators import evaluate_compliance
    from data.pipelines.rfp_intake.phi import contains_rfp_phi, scan_and_redact

    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    sections = store.list_sections(session, ticket_id)
    section = next((s for s in sections if s.department_id == department_id), None)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    if not section.draft_content:
        raise HTTPException(status_code=400, detail="Section has no draft to redact")

    meta = store.get_metadata(session, ticket_id)
    shared = {
        "client_name": meta.client_name if meta else None,
        "client_country": meta.client_country if meta else None,
        "program_type": meta.program_type if meta else None,
        "covered_population": meta.covered_population if meta else None,
        "budget_range": meta.budget_range if meta else None,
        "open_questions": (meta.open_questions if meta else None) or [],
    }
    redacted, flagged_before, _ = scan_and_redact(section.draft_content)
    still_phi, _ = contains_rfp_phi(redacted)
    compliance = evaluate_compliance(
        {
            "draft_content": redacted,
            "shared_metadata": shared,
        }
    )
    # Prefer compliance's view after scrub; fall back to our scan
    working = compliance.get("redacted_draft") or redacted
    still_phi = bool(compliance.get("contains_phi")) or contains_rfp_phi(working)[0]

    eval_sync = dict(section.evaluation_results or {})
    readability = eval_sync.get("readability") or {}
    relevance = eval_sync.get("relevance") or {}
    eval_sync.update(
        {
            "contains_phi": still_phi,
            "phi_was_redacted": bool(flagged_before or compliance.get("phi_was_redacted")),
            "compliance": {
                "pass": (not still_phi) and bool(compliance.get("pass", True)),
                "rule_ids": compliance.get("rule_ids") or [],
                "violations": []
                if not still_phi
                else [
                    v
                    for v in (compliance.get("violations") or [])
                    if v.get("rule_id") == "phi-free"
                ]
                or [{"rule_id": "phi-free", "message": "Draft contains patient identifiers / PHI"}],
                "contains_phi": still_phi,
                "phi_was_redacted": True,
            },
        }
    )

    if still_phi:
        store.upsert_section(
            session,
            ticket_id,
            department_id,
            draft_content=working,
            status="needs_human_review",
            evaluation_results=eval_sync,
        )
        session.commit()
        return ReleaseRedactedAccepted(
            ticket_id=ticket_id,
            department_id=department_id,
            status="needs_human_review",
            phi_cleared=False,
            message="PHI could not be fully scrubbed — still blocked",
        )

    # Clear phi-free; keep other compliance failures if any
    other_violations = [
        v
        for v in (compliance.get("violations") or [])
        if v.get("rule_id") != "phi-free"
    ]
    compliance_ok = len(other_violations) == 0
    eval_sync["compliance"] = {
        "pass": compliance_ok,
        "rule_ids": compliance.get("rule_ids") or [],
        "violations": other_violations,
        "contains_phi": False,
        "phi_was_redacted": True,
    }

    readability_ok = bool(readability.get("pass", True))
    relevance_ok = bool(relevance.get("pass", True))
    new_status = (
        "passed"
        if readability_ok and relevance_ok and compliance_ok
        else "needs_human_review"
    )
    eval_sync["overall_pass"] = new_status == "passed"
    eval_sync["feedback_for_generator"] = (
        ""
        if new_status == "passed"
        else eval_sync.get("feedback_for_generator") or ""
    )
    store.upsert_section(
        session,
        ticket_id,
        department_id,
        draft_content=working,
        status=new_status,
        evaluation_results=eval_sync,
    )
    session.flush()
    refreshed = store.list_sections(session, ticket_id)
    needing, _ = store.phase2_rollup(refreshed)
    if needing == 0 and ticket.needs_human_review:
        store.set_ticket_status(session, ticket, ticket.status, needs_human_review=False)
    session.commit()
    return ReleaseRedactedAccepted(
        ticket_id=ticket_id,
        department_id=department_id,
        status=new_status,
        phi_cleared=True,
        message="PHI redacted; section released" if new_status == "passed" else "PHI cleared; other checks still failing",
    )