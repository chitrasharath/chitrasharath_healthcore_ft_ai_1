"""Supabase persistence helpers for RFP intake + drafting pipelines."""

from __future__ import annotations

from datetime import datetime, timezone
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


def set_section_drafting(
    session: Session,
    ticket_id: str,
    department_id: str,
    *,
    iteration: int,
) -> None:
    store.upsert_section(
        session,
        ticket_id,
        department_id,
        status="drafting",
        iteration=iteration,
    )


def set_section_status(
    session: Session,
    ticket_id: str,
    department_id: str,
    *,
    status: str,
) -> None:
    store.upsert_section(session, ticket_id, department_id, status=status)


def persist_draft(
    session: Session,
    ticket_id: str,
    department_id: str,
    *,
    draft_content: str,
    iteration: int,
    status: str,
) -> None:
    store.upsert_section(
        session,
        ticket_id,
        department_id,
        draft_content=draft_content,
        iteration=iteration,
        status=status,
    )
    ticket = load_ticket(session, ticket_id)
    store.touch_ticket(session, ticket)


def ensure_ticket_under_evaluation(session: Session, ticket_id: str) -> None:
    ticket = load_ticket(session, ticket_id)
    if ticket.status in ("drafting", "intake_complete"):
        store.set_ticket_status(session, ticket, "under_evaluation")


def flag_ticket_section_review(session: Session, ticket_id: str) -> None:
    ticket = load_ticket(session, ticket_id)
    store.set_ticket_status(session, ticket, ticket.status, needs_human_review=True)


def persist_evaluation(
    session: Session,
    *,
    ticket_id: str,
    department_id: str,
    section_id: int,
    iteration: int,
    evaluation: dict[str, Any],
    draft_content: str,
    section_status: str,
) -> None:
    from app.domains.rfp_intake.models import EvaluationResult

    now = datetime.now(timezone.utc)
    row = EvaluationResult(
        section_id=section_id,
        ticket_id=ticket_id,
        department_id=department_id,
        iteration=iteration,
        readability=evaluation.get("readability"),
        relevance=evaluation.get("relevance"),
        compliance=evaluation.get("compliance"),
        contains_phi=bool(evaluation.get("contains_phi")),
        overall_pass=bool(evaluation.get("overall_pass")),
        feedback_for_generator=evaluation.get("feedback_for_generator") or "",
        created_at=now,
    )
    session.add(row)
    session.flush()

    eval_sync = {
        "contains_phi": bool(evaluation.get("contains_phi")),
        "phi_was_redacted": bool(evaluation.get("phi_was_redacted")),
        "overall_pass": bool(evaluation.get("overall_pass")),
        "latest_iteration": iteration,
        "feedback_for_generator": evaluation.get("feedback_for_generator") or "",
        "readability": evaluation.get("readability"),
        "relevance": evaluation.get("relevance"),
        "compliance": evaluation.get("compliance"),
    }
    store.upsert_section(
        session,
        ticket_id,
        department_id,
        draft_content=draft_content,
        status=section_status,
        iteration=iteration,
        evaluation_results=eval_sync,
        latest_evaluation_id=row.id,
    )
    ticket = load_ticket(session, ticket_id)
    store.touch_ticket(session, ticket)


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
