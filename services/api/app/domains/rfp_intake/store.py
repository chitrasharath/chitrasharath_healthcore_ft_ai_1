from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.domains.rfp_intake.models import DepartmentSection, RfpMetadata, Ticket
from app.domains.rfp_intake.schemas import (
    DepartmentSectionOut,
    RfpMetadataOut,
    TicketDetail,
    TicketSummary,
)

PREVIEW_CHARS = 800


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
    session.add(section)
    session.flush()
    return section


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
) -> TicketSummary:
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
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def to_detail(
    ticket: Ticket,
    meta: RfpMetadata | None,
    sections: list[DepartmentSection],
    *,
    job_status: str | None = None,
    job_checkpoint: str | None = None,
    job_error: str | None = None,
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
    return TicketDetail(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
        needs_human_review=ticket.needs_human_review,
        classifier_reason=ticket.classifier_reason,
        job_status=job_status,
        job_checkpoint=job_checkpoint,
        job_error=job_error,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        metadata=metadata_out,
        sections=[
            DepartmentSectionOut(
                department_id=s.department_id,
                key_aspects=s.key_aspects,
                evaluation_results=s.evaluation_results,
            )
            for s in sections
        ],
    )
