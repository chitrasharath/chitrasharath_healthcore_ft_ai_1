from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.domains.rfp_intake.models import (
    DepartmentSection,
    EvaluationResult,
    RfpMetadata,
    Ticket,
)
from app.domains.rfp_intake.schemas import (
    DepartmentSectionOut,
    EvaluationResultOut,
    RfpMetadataOut,
    TicketDetail,
    TicketSummary,
)

PREVIEW_CHARS = 800
TERMINAL_SECTION_STATUSES = frozenset({"passed", "needs_human_review"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_ticket(session: Session, ticket_id: str) -> Ticket | None:
    return session.get(Ticket, ticket_id)


def get_metadata(session: Session, ticket_id: str) -> RfpMetadata | None:
    return session.get(RfpMetadata, ticket_id)


def find_by_sha256(session: Session, digest: str) -> Ticket | None:
    statement = select(Ticket).where(Ticket.content_sha256 == digest)
    return session.exec(statement).first()


def list_tickets(session: Session) -> list[Ticket]:
    statement = select(Ticket).order_by(Ticket.created_at.desc())  # type: ignore[arg-type]
    return list(session.exec(statement).all())


def list_sections(session: Session, ticket_id: str) -> list[DepartmentSection]:
    statement = select(DepartmentSection).where(DepartmentSection.ticket_id == ticket_id)
    return list(session.exec(statement).all())


def create_ticket(
    session: Session,
    *,
    raw_pdf_path: str,
    content_sha256: str,
) -> Ticket:
    now = _utcnow()
    ticket = Ticket(
        status="analyzing",
        raw_pdf_path=raw_pdf_path,
        content_sha256=content_sha256,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.flush()
    meta = RfpMetadata(ticket_id=ticket.ticket_id)
    session.add(meta)
    session.flush()
    return ticket


def touch_ticket(session: Session, ticket: Ticket) -> None:
    ticket.updated_at = _utcnow()
    session.add(ticket)
    session.flush()


def upsert_metadata(session: Session, ticket_id: str, **fields: Any) -> RfpMetadata:
    meta = session.get(RfpMetadata, ticket_id)
    if meta is None:
        meta = RfpMetadata(ticket_id=ticket_id)
    for key, value in fields.items():
        if hasattr(meta, key):
            setattr(meta, key, value)
    session.add(meta)
    session.flush()
    return meta


def upsert_section(
    session: Session,
    ticket_id: str,
    department_id: str,
    *,
    key_aspects: Any | None = None,
    evaluation_results: dict[str, Any] | None = None,
    draft_content: str | None = None,
    status: str | None = None,
    iteration: int | None = None,
    latest_evaluation_id: int | None = None,
) -> DepartmentSection:
    statement = select(DepartmentSection).where(
        DepartmentSection.ticket_id == ticket_id,
        DepartmentSection.department_id == department_id,
    )
    section = session.exec(statement).first()
    if section is None:
        section = DepartmentSection(ticket_id=ticket_id, department_id=department_id)
    if key_aspects is not None:
        section.key_aspects = key_aspects
    if evaluation_results is not None:
        section.evaluation_results = evaluation_results
    if draft_content is not None:
        section.draft_content = draft_content
    if status is not None:
        section.status = status
    if iteration is not None:
        section.iteration = iteration
    if latest_evaluation_id is not None:
        section.latest_evaluation_id = latest_evaluation_id
    session.add(section)
    session.flush()
    return section


def list_evaluations(
    session: Session,
    ticket_id: str,
    *,
    department_id: str | None = None,
) -> list[EvaluationResult]:
    statement = select(EvaluationResult).where(EvaluationResult.ticket_id == ticket_id)
    if department_id:
        statement = statement.where(EvaluationResult.department_id == department_id)
    statement = statement.order_by(EvaluationResult.iteration.asc())  # type: ignore[arg-type]
    return list(session.exec(statement).all())


def reset_section_for_redraft(
    session: Session,
    ticket_id: str,
    department_id: str,
) -> DepartmentSection:
    """Reset loop counters but keep the last draft + evaluator feedback."""
    sections = list_sections(session, ticket_id)
    section = next((s for s in sections if s.department_id == department_id), None)
    if section is None:
        section = upsert_section(session, ticket_id, department_id)

    ev = dict(section.evaluation_results or {})
    ev["contains_phi"] = False
    section.iteration = 0
    section.status = None
    section.latest_evaluation_id = None
    section.evaluation_results = ev
    session.add(section)
    session.flush()
    return section


def phase2_rollup(sections: list[DepartmentSection]) -> tuple[int, bool]:
    needing = sum(1 for s in sections if s.status == "needs_human_review")
    if not sections:
        return 0, False
    complete = all((s.status or "") in TERMINAL_SECTION_STATUSES for s in sections)
    return needing, complete


def set_ticket_status(
    session: Session,
    ticket: Ticket,
    status: str,
    *,
    classifier_reason: str | None = None,
    needs_human_review: bool | None = None,
) -> None:
    ticket.status = status
    if classifier_reason is not None:
        ticket.classifier_reason = classifier_reason
    if needs_human_review is not None:
        ticket.needs_human_review = needs_human_review
    ticket.updated_at = _utcnow()
    session.add(ticket)
    session.flush()


def to_summary(
    ticket: Ticket,
    meta: RfpMetadata | None,
    *,
    job_status: str | None = None,
    sections: list[DepartmentSection] | None = None,
) -> TicketSummary:
    needing, phase2_done = phase2_rollup(sections or [])
    return TicketSummary(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
        client_name=meta.client_name if meta else None,
        program_type=meta.program_type if meta else None,
        departments_needed=meta.departments_needed if meta else None,
        contains_phi=bool(meta.contains_phi) if meta else False,
        needs_human_review=ticket.needs_human_review,
        job_status=job_status,
        sections_needing_review=needing,
        phase2_complete=phase2_done,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _eval_out(row: EvaluationResult) -> EvaluationResultOut:
    return EvaluationResultOut(
        id=row.id or 0,
        department_id=row.department_id,
        iteration=row.iteration,
        readability=row.readability,
        relevance=row.relevance,
        compliance=row.compliance,
        contains_phi=row.contains_phi,
        overall_pass=row.overall_pass,
        feedback_for_generator=row.feedback_for_generator,
        created_at=row.created_at,
    )


def to_detail(
    ticket: Ticket,
    meta: RfpMetadata | None,
    sections: list[DepartmentSection],
    *,
    job_status: str | None = None,
    job_checkpoint: str | None = None,
    job_error: str | None = None,
    evaluations: list[EvaluationResult] | None = None,
) -> TicketDetail:
    metadata_out: RfpMetadataOut | None = None
    if meta is not None:
        preview = None
        if meta.markdown_text:
            preview = meta.markdown_text[:PREVIEW_CHARS]
        metadata_out = RfpMetadataOut(
            client_name=meta.client_name,
            client_country=meta.client_country,
            program_type=meta.program_type,
            covered_population=meta.covered_population,
            covered_population_n=meta.covered_population_n,
            deadline=meta.deadline,
            budget_range=meta.budget_range,
            departments_needed=meta.departments_needed,
            readability_metrics=meta.readability_metrics,
            open_questions=meta.open_questions,
            contains_phi=meta.contains_phi,
            sales_summary=meta.sales_summary,
            classifier_result=meta.classifier_result,
            markdown_preview=preview,
        )
    needing, phase2_done = phase2_rollup(sections)
    evals_by_dept: dict[str, list[EvaluationResultOut]] = {}
    for row in evaluations or []:
        evals_by_dept.setdefault(row.department_id, []).append(_eval_out(row))

    section_outs: list[DepartmentSectionOut] = []
    for s in sections:
        draft = s.draft_content
        contains_phi = bool((s.evaluation_results or {}).get("contains_phi"))
        if contains_phi and draft:
            # Never return raw PHI — store already redacted; still truncate
            draft = draft[:PREVIEW_CHARS]
        section_outs.append(
            DepartmentSectionOut(
                department_id=s.department_id,
                key_aspects=s.key_aspects,
                draft_content=draft,
                evaluation_results=s.evaluation_results,
                status=s.status,
                iteration=s.iteration or 0,
                latest_evaluation_id=s.latest_evaluation_id,
                evaluation_history=evals_by_dept.get(s.department_id, []),
            )
        )
    return TicketDetail(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
        needs_human_review=ticket.needs_human_review,
        classifier_reason=ticket.classifier_reason,
        job_status=job_status,
        job_checkpoint=job_checkpoint,
        job_error=job_error,
        sections_needing_review=needing,
        phase2_complete=phase2_done,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        metadata=metadata_out,
        sections=section_outs,
    )
