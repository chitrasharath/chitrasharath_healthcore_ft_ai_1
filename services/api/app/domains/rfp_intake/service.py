from __future__ import annotations

import hashlib
import logging
import threading
from datetime import date, datetime
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlmodel import Session, select

from app.domains.jobs import job_runner
from app.domains.jobs.models import JobRun
from app.domains.rfp_intake import store
from app.domains.rfp_intake.schemas import (
    ApprovalAccepted,
    DecisionAccepted,
    DepartmentDecisionBody,
    DraftingAccepted,
    FinalDocumentOut,
    RedraftAccepted,
    ReleaseRedactedAccepted,
    RerunAccepted,
    RunAllAccepted,
    TicketDetail,
    TicketSummary,
    UploadAccepted,
)

logger = logging.getLogger(__name__)

JOB_NAME = "rfp_intake"
DRAFT_JOB_NAME = "rfp_drafting"
APPROVAL_JOB_NAME = "rfp_approval"
RUN_ALL_JOB_NAME = "rfp_run_all"
MAX_PDF_BYTES = 20 * 1024 * 1024
REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_DIR = REPO_ROOT / "data" / "raw"


def _latest_job(session: Session, ticket_id: str, job_name: str = JOB_NAME) -> JobRun | None:
    """Latest job for ticket_id, including department-scoped keys (`ticket_id:dept`)."""
    from sqlalchemy import or_

    statement = (
        select(JobRun)
        .where(
            JobRun.job_name == job_name,
            or_(
                JobRun.target_key == ticket_id,
                JobRun.target_key.like(f"{ticket_id}:%"),  # type: ignore[arg-type]
            ),
        )
        .order_by(JobRun.created_at.desc())  # type: ignore[arg-type]
    )
    return session.exec(statement).first()


def _latest_any_job(session: Session, ticket_id: str) -> JobRun | None:
    candidates = [
        _latest_job(session, ticket_id, name)
        for name in (RUN_ALL_JOB_NAME, APPROVAL_JOB_NAME, DRAFT_JOB_NAME, JOB_NAME)
    ]
    present = [j for j in candidates if j is not None]
    if not present:
        return None
    present.sort(
        key=lambda j: j.created_at or datetime.min.replace(tzinfo=None),
        reverse=True,
    )
    return present[0]


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
        # Run-all / continue-to-approval: when Phase 2 is fully passed, start Phase 3
        _auto_start_phase3_if_run_all(ticket_id)
    except Exception:
        logger.exception("background rfp_drafting failed ticket_id=%s", ticket_id)


def _ticket_has_run_all(session: Session, ticket_id: str) -> bool:
    run_all = _latest_job(session, ticket_id, RUN_ALL_JOB_NAME)
    if run_all is None:
        return False
    if (run_all.error_message or "").startswith("superseded by intake re-run"):
        return False
    if run_all.status in ("pending", "processing"):
        return True
    # A newer intake after run-all finished is a step-by-step re-run
    intake = _latest_job(session, ticket_id, JOB_NAME)
    if intake is None or intake.created_at is None:
        return True
    run_all_end = run_all.finished_at or run_all.created_at
    if run_all_end is None:
        return True
    try:
        if intake.created_at > run_all_end:
            return False
    except TypeError:
        return True
    return True


def _sections_all_passed(session: Session, ticket_id: str) -> bool:
    sections = store.list_sections(session, ticket_id)
    return bool(sections) and all(s.status == "passed" for s in sections)


def _auto_start_phase3_if_run_all(ticket_id: str) -> None:
    """If this ticket was started via run-all and Phase 2 is complete, start approvals."""
    from app.core.db import supabase_engine

    if supabase_engine is None:
        return
    with Session(supabase_engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        if ticket is None:
            return
        if ticket.status in ("waiting_for_approval", "done"):
            return
        if not _ticket_has_run_all(session, ticket_id):
            return
        if not _sections_all_passed(session, ticket_id):
            return
        if job_runner.has_processing_lock_for_key(session, APPROVAL_JOB_NAME, ticket_id):
            return

    try:
        from data.pipelines.rfp_intake.approval_runner import start_approval

        logger.info("run-all auto-starting Phase 3 for ticket=%s", ticket_id)
        start_approval(ticket_id)
    except Exception:
        logger.exception("auto Phase 3 start failed ticket_id=%s", ticket_id)


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
                from_run_all=_ticket_has_run_all(session, ticket.ticket_id),
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
    detail = store.to_detail(
        ticket,
        meta,
        sections,
        job_status=job.status if job else None,
        job_checkpoint=job.checkpoint if job else None,
        job_error=job.error_message if job else None,
        evaluations=evaluations,
    )
    from app.domains.rfp_intake.models import FinalDocument, RfpArbitrationRecord

    final = session.get(FinalDocument, ticket_id)
    detail.final_document_available = bool(
        final and final.rendered_markdown and final.pdf_path
    )
    detail.from_run_all = _ticket_has_run_all(session, ticket_id)
    from sqlmodel import select

    arb_rows = list(
        session.exec(
            select(RfpArbitrationRecord)
            .where(RfpArbitrationRecord.ticket_id == ticket_id)
            .order_by(RfpArbitrationRecord.created_at.desc())  # type: ignore[arg-type]
        ).all()
    )
    detail.arbitration_records = [
        {
            "trigger_id": r.trigger_id,
            "arbiter": r.arbiter,
            "forced_action": r.forced_action,
            "resolved": r.resolved,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in arb_rows[:20]
    ]
    return detail


def delete_ticket(session: Session, ticket_id: str) -> None:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    paths: list[Path] = []
    if ticket.raw_pdf_path:
        paths.append(Path(ticket.raw_pdf_path))
    from app.domains.rfp_intake.models import FinalDocument

    final_doc = session.get(FinalDocument, ticket_id)
    if final_doc and final_doc.pdf_path:
        paths.append(Path(final_doc.pdf_path))
    # Also remove regenerated final naming convention
    paths.append(RAW_DIR / f"{ticket_id}_final.pdf")

    removed = store.delete_ticket(session, ticket_id)
    if removed is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    session.commit()

    for path in paths:
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            logger.warning("could not remove artifact %s", path)


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
    store.clear_phase2_and_phase3_state(session, ticket_id)
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
    *,
    continue_to_approval: bool = False,
) -> DraftingAccepted:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if continue_to_approval:
        if ticket.status != "intake_complete":
            if ticket.status in (
                "drafting",
                "under_evaluation",
                "waiting_for_approval",
                "done",
            ):
                return DraftingAccepted(
                    ticket_id=ticket_id,
                    status=ticket.status,
                    message="continue-to-approval already in progress or complete",
                )
            raise HTTPException(
                status_code=409,
                detail=f"Ticket must be intake_complete (got {ticket.status})",
            )
        job_runner.reclaim_stale_locks(session, RUN_ALL_JOB_NAME)
        run = job_runner.create_pending_for_key(
            session, RUN_ALL_JOB_NAME, ticket_id, date.today()
        )
        session.commit()
        background_tasks.add_task(
            _run_all_background, ticket_id, str(run.id), True
        )
        return DraftingAccepted(
            ticket_id=ticket_id,
            status="drafting",
            message="drafting→approval chain enqueued",
        )

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
    dept_lock = f"{ticket_id}:{department_id}"
    if job_runner.has_processing_lock_for_key(session, DRAFT_JOB_NAME, dept_lock):
        raise HTTPException(
            status_code=409,
            detail=f"Re-draft already processing for {department_id}",
        )
    if job_runner.has_processing_lock_for_key(session, DRAFT_JOB_NAME, ticket_id):
        raise HTTPException(
            status_code=409,
            detail="Full-ticket drafting is still running — try again shortly",
        )

    store.reset_section_for_redraft(session, ticket_id, department_id)
    if ticket.status not in ("drafting", "under_evaluation"):
        store.set_ticket_status(session, ticket, "drafting")

    run = job_runner.create_pending_for_key(
        session,
        DRAFT_JOB_NAME,
        dept_lock,
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
        message=f"re-draft enqueued for {department_id}",
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
    needing, _, _ = store.phase2_rollup(refreshed)
    if needing == 0 and ticket.needs_human_review:
        store.set_ticket_status(session, ticket, ticket.status, needs_human_review=False)
    session.commit()

    # Run-all tickets: Phase 2 complete → auto Phase 3
    if new_status == "passed" and _sections_all_passed(session, ticket_id):
        threading.Thread(
            target=_auto_start_phase3_if_run_all,
            args=(ticket_id,),
            daemon=True,
            name=f"rfp-auto-p3-{ticket_id[:8]}",
        ).start()

    return ReleaseRedactedAccepted(
        ticket_id=ticket_id,
        department_id=department_id,
        status=new_status,
        phi_cleared=True,
        message="PHI redacted; section released" if new_status == "passed" else "PHI cleared; other checks still failing",
    )


def _run_approval_background(ticket_id: str, job_run_id: str | None = None) -> None:
    try:
        from data.pipelines.rfp_intake.approval_runner import start_approval

        start_approval(ticket_id, job_run_id=job_run_id)
    except Exception:
        logger.exception("background rfp_approval failed ticket_id=%s", ticket_id)


def _run_all_background(ticket_id: str, job_run_id: str, skip_intake: bool = False) -> None:
    try:
        from data.pipelines.rfp_intake.approval_runner import run_all_phases

        run_all_phases(ticket_id, job_run_id=job_run_id, skip_intake=skip_intake)
    except Exception:
        logger.exception("background rfp_run_all failed ticket_id=%s", ticket_id)


def send_for_approval(
    session: Session,
    ticket_id: str,
    background_tasks: BackgroundTasks,
) -> ApprovalAccepted:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status == "done":
        return ApprovalAccepted(
            ticket_id=ticket_id,
            status=ticket.status,
            message="already done",
        )
    if ticket.status == "waiting_for_approval":
        return ApprovalAccepted(
            ticket_id=ticket_id,
            status=ticket.status,
            message="already in approval",
        )

    sections = store.list_sections(session, ticket_id)
    if not sections or not all(s.status == "passed" for s in sections):
        raise HTTPException(
            status_code=409,
            detail="All required sections must be passed before Run Phase 3",
        )

    job_runner.reclaim_stale_locks(session, APPROVAL_JOB_NAME)
    # Stuck lock after re-run / failed start: ticket still under_evaluation but
    # an old rfp_approval row is processing — clear it and start fresh.
    if job_runner.has_processing_lock_for_key(session, APPROVAL_JOB_NAME, ticket_id):
        from datetime import datetime, timezone

        stuck = list(
            session.exec(
                select(JobRun).where(
                    JobRun.job_name == APPROVAL_JOB_NAME,
                    JobRun.target_key == ticket_id,
                    JobRun.status == "processing",
                )
            ).all()
        )
        now = datetime.now(timezone.utc)
        for run in stuck:
            run.status = "failed"
            run.finished_at = now
            run.error_message = "cleared stale approval lock before restart"
            session.add(run)
        session.commit()

    run = job_runner.create_pending_for_key(
        session,
        APPROVAL_JOB_NAME,
        ticket_id,
        date.today(),
    )
    session.commit()
    background_tasks.add_task(_run_approval_background, ticket_id, str(run.id))
    return ApprovalAccepted(
        ticket_id=ticket_id,
        status="waiting_for_approval",
        message="approval enqueued",
    )


async def run_all_from_pdf(
    session: Session,
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> RunAllAccepted:
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
    if existing is not None and job_runner.has_processing_lock_for_key(
        session, RUN_ALL_JOB_NAME, existing.ticket_id
    ):
        return RunAllAccepted(
            ticket_id=existing.ticket_id,
            rfp_id=existing.rfp_id,
            status=existing.status,
            message="run-all already processing",
        )

    ticket = store.create_ticket(session, raw_pdf_path="", content_sha256=digest)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RAW_DIR / f"{ticket.ticket_id}.pdf"
    pdf_path.write_bytes(data)
    ticket.raw_pdf_path = str(pdf_path)
    store.touch_ticket(session, ticket)

    job_runner.reclaim_stale_locks(session, RUN_ALL_JOB_NAME)
    run = job_runner.create_pending_for_key(
        session, RUN_ALL_JOB_NAME, ticket.ticket_id, date.today()
    )
    session.commit()
    background_tasks.add_task(_run_all_background, ticket.ticket_id, str(run.id), False)
    return RunAllAccepted(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
        message="run-all enqueued from PDF",
    )


def apply_department_decision(
    session: Session,
    ticket_id: str,
    department_id: str,
    body: DepartmentDecisionBody,
    background_tasks: BackgroundTasks | None = None,
) -> DecisionAccepted:
    """Apply approve/reject immediately in DB; sync LangGraph in the background."""
    from datetime import timezone

    from data.pipelines.rfp_intake.final_document import generate_final_document
    from data.pipelines.rfp_intake.owners import REQUIRED_DEPARTMENTS, is_valid_approver
    from data.pipelines.rfp_intake.transitions import assert_can_transition

    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status != "waiting_for_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Ticket must be waiting_for_approval (got {ticket.status})",
        )

    sections = store.list_sections(session, ticket_id)
    section = next((s for s in sections if s.department_id == department_id), None)
    if section is None:
        raise HTTPException(status_code=404, detail="Department not on ticket")

    decision = (body.decision or "").strip().lower()
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be approve or reject")
    if decision == "reject" and not (body.reason or "").strip():
        raise HTTPException(status_code=400, detail="reason required when rejecting")
    if not is_valid_approver(department_id, body.approver):
        raise HTTPException(status_code=400, detail="approver does not match department owner")

    already = decision == "approve" and section.approval_status == "approved"
    if section.approval_status == "approved" and decision == "reject":
        raise HTTPException(status_code=409, detail="Section already approved")

    approver = body.approver.strip()
    reason = (body.reason or "").strip()

    # Persist immediately so the UI refreshes even if the graph hangs
    if not already:
        if decision == "approve":
            section.approval_status = "approved"
            section.approver = approver
            section.approved_at = datetime.now(timezone.utc)
        else:
            section.approval_status = "request_changes"
            section.approver = approver
            section.approved_at = None
            ev = dict(section.evaluation_results or {})
            ev["approval_reason"] = reason
            section.evaluation_results = ev
        session.add(section)
        session.commit()

    # Best-effort graph resume in a daemon thread (must not block the event loop)
    def _sync_graph() -> None:
        try:
            from data.pipelines.rfp_intake.approval_runner import resume_approval

            resume_approval(
                ticket_id,
                {
                    "department_id": department_id,
                    "decision": decision,
                    "approver": approver,
                    "reason": reason,
                },
            )
        except Exception:
            logger.exception(
                "graph resume failed ticket=%s dept=%s (DB decision already saved)",
                ticket_id,
                department_id,
            )

    def _spawn(target) -> None:
        threading.Thread(target=target, daemon=True, name=f"rfp-decision-{ticket_id[:8]}").start()

    def _try_finalize() -> None:
        session.expire_all()
        sections_now = store.list_sections(session, ticket_id)
        by_dept = {s.department_id: s for s in sections_now}
        all_ok = all(
            by_dept.get(d) is not None and by_dept[d].approval_status == "approved"
            for d in REQUIRED_DEPARTMENTS
        )
        ticket_now = store.get_ticket(session, ticket_id)
        if not all_ok or ticket_now is None or ticket_now.status == "done":
            return
        try:
            assert_can_transition(ticket_now.status, "done")
            generate_final_document(session, ticket_id)
            store.set_ticket_status(session, ticket_now, "done")
            session.commit()
        except Exception:
            logger.exception("final document after approvals failed ticket=%s", ticket_id)
            session.rollback()

    if decision == "reject":
        def _reject_path() -> None:
            try:
                from data.pipelines.rfp_intake.drafting_runner import run_drafting

                run_drafting(ticket_id, department_id=department_id)
            except Exception:
                logger.exception("reject revision failed ticket=%s dept=%s", ticket_id, department_id)
            _sync_graph()

        _spawn(_reject_path)
    else:
        _try_finalize()
        if not already:
            _spawn(_sync_graph)

    session.expire_all()
    refreshed = store.get_ticket(session, ticket_id)
    msg = "approved"
    if already:
        msg = "already approved"
        if refreshed and refreshed.status == "done":
            msg = "already approved — finalized"
    elif decision == "reject":
        msg = "rejected — revision queued"
    return DecisionAccepted(
        ticket_id=ticket_id,
        department_id=department_id,
        decision=decision,
        status=refreshed.status if refreshed else ticket.status,
        message=msg,
    )


def get_final_document(session: Session, ticket_id: str) -> FinalDocumentOut:
    from app.domains.rfp_intake.models import FinalDocument

    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    row = session.get(FinalDocument, ticket_id)
    if row is None or not row.rendered_markdown:
        raise HTTPException(status_code=404, detail="Final document not available")
    return FinalDocumentOut(
        ticket_id=ticket_id,
        currency=row.currency,
        generated_at=row.generated_at,
        rendered_markdown=row.rendered_markdown,
        pdf_available=bool(row.pdf_path and Path(row.pdf_path).is_file()),
        sections=row.sections,
    )


def get_final_document_pdf_path(session: Session, ticket_id: str) -> Path:
    from app.domains.rfp_intake.models import FinalDocument

    row = session.get(FinalDocument, ticket_id)
    if row is None or not row.pdf_path:
        raise HTTPException(status_code=404, detail="Final PDF not available")
    path = Path(row.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Final PDF file missing")
    return path

