"""Supabase persistence helpers for RFP intake pipeline."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.domains.jobs import job_runner
from app.domains.jobs.models import JobRun
from app.domains.rfp_intake import store
from app.domains.rfp_intake.models import Ticket


def load_ticket(session: Session, ticket_id: str) -> Ticket:
    ticket = store.get_ticket(session, ticket_id)
    if ticket is None:
        raise ValueError(f"ticket not found: {ticket_id}")
    return ticket


def update_checkpoint(session: Session, job_run_id: str | None, checkpoint: str) -> None:
    if not job_run_id:
        return
    run = session.get(JobRun, UUID(job_run_id))
    if run is None:
        return
    job_runner.set_checkpoint(session, run, checkpoint)


def persist_markdown_and_phi(
    session: Session,
    ticket_id: str,
    *,
    markdown: str,
    contains_phi: bool,
) -> None:
    store.upsert_metadata(
        session,
        ticket_id,
        markdown_text=markdown,
        contains_phi=contains_phi,
    )
    ticket = load_ticket(session, ticket_id)
    store.touch_ticket(session, ticket)


def persist_extracted_metadata(
    session: Session,
    ticket_id: str,
    metadata: dict[str, Any],
    readability: dict[str, Any],
) -> None:
    store.upsert_metadata(
        session,
        ticket_id,
        client_name=metadata.get("client_name"),
        client_country=metadata.get("client_country"),
        program_type=metadata.get("program_type"),
        covered_population=metadata.get("covered_population"),
        covered_population_n=metadata.get("covered_population_n"),
        deadline=metadata.get("deadline"),
        budget_range=metadata.get("budget_range"),
        open_questions=metadata.get("open_questions") or [],
        readability_metrics=readability,
    )
    ticket = load_ticket(session, ticket_id)
    store.touch_ticket(session, ticket)


def persist_classifier(
    session: Session,
    ticket_id: str,
    result: dict[str, Any],
    *,
    status: str,
    needs_human_review: bool,
) -> None:
    store.upsert_metadata(session, ticket_id, classifier_result=result)
    ticket = load_ticket(session, ticket_id)
    store.set_ticket_status(
        session,
        ticket,
        status,
        classifier_reason=str(result.get("reason") or ""),
        needs_human_review=needs_human_review,
    )


def persist_departments(
    session: Session,
    ticket_id: str,
    departments: list[str],
    *,
    contains_phi: bool,
) -> None:
    store.upsert_metadata(session, ticket_id, departments_needed=departments)
    for dept in departments:
        eval_results = {"contains_phi": bool(contains_phi)} if contains_phi else {"contains_phi": False}
        store.upsert_section(
            session,
            ticket_id,
            dept,
            evaluation_results=eval_results,
        )
    ticket = load_ticket(session, ticket_id)
    store.touch_ticket(session, ticket)


def persist_worker_result(
    session: Session,
    ticket_id: str,
    department_id: str,
    result: dict[str, Any],
    *,
    contains_phi: bool,
) -> None:
    store.upsert_section(
        session,
        ticket_id,
        department_id,
        key_aspects=result.get("key_aspects") or [],
        evaluation_results={"contains_phi": bool(contains_phi)},
    )


def persist_summary_complete(
    session: Session,
    ticket_id: str,
    summary: dict[str, Any],
    open_questions: list[str],
) -> None:
    store.upsert_metadata(
        session,
        ticket_id,
        sales_summary=summary,
        open_questions=open_questions,
    )
    ticket = load_ticket(session, ticket_id)
    store.set_ticket_status(session, ticket, "intake_complete")
