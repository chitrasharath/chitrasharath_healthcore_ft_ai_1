"""RFP approval runner — start / resume + CLI + run-all chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from langgraph.types import Command
from sqlmodel import Session

_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.core.db import supabase_engine  # noqa: E402
from app.domains.jobs import job_runner  # noqa: E402
from app.domains.jobs.models import JobRun  # noqa: E402
from app.domains.rfp_intake import store  # noqa: E402
from data.pipelines.rfp_intake.approval_graph import get_approval_graph  # noqa: E402
from data.pipelines.rfp_intake.checkpointer import thread_config  # noqa: E402
from data.pipelines.rfp_intake.owners import REQUIRED_DEPARTMENTS  # noqa: E402
from data.pipelines.rfp_intake.transitions import assert_can_transition  # noqa: E402

logger = logging.getLogger(__name__)

JOB_NAME = "rfp_approval"
RUN_ALL_JOB = "rfp_run_all"


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


def _sections_all_passed(session: Session, ticket_id: str) -> bool:
    sections = store.list_sections(session, ticket_id)
    if not sections:
        return False
    return all(s.status == "passed" for s in sections)


def _metadata_dict(session: Session, ticket_id: str) -> dict[str, Any]:
    meta = store.get_metadata(session, ticket_id)
    if meta is None:
        return {}
    return {
        "client_name": meta.client_name,
        "client_country": meta.client_country,
        "program_type": meta.program_type,
        "covered_population": meta.covered_population,
        "covered_population_n": meta.covered_population_n,
        "budget_range": meta.budget_range,
        "open_questions": meta.open_questions or [],
    }


def start_approval(
    ticket_id: str,
    job_run_id: str | None = None,
    *,
    use_memory: bool = False,
) -> dict[str, Any]:
    """Start approval graph until first interrupt(s)."""
    engine = _ensure_engine()
    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        if ticket is None:
            raise ValueError(f"ticket not found: {ticket_id}")
        if not _sections_all_passed(session, ticket_id):
            raise ValueError("All required sections must be passed before approval")

        run: JobRun | None = None
        if job_run_id:
            run = session.get(JobRun, UUID(job_run_id))
        if run is None:
            job_runner.reclaim_stale_locks(session, JOB_NAME)
            run = job_runner.create_pending_for_key(
                session, JOB_NAME, ticket_id, date.today()
            )
            session.commit()
            session.refresh(run)

        if ticket.status != "waiting_for_approval":
            assert_can_transition(ticket.status, "waiting_for_approval")
            store.set_ticket_status(session, ticket, "waiting_for_approval")
        # Initialize approval_status pending
        for section in store.list_sections(session, ticket_id):
            if not section.approval_status:
                section.approval_status = "pending"
                session.add(section)
        job_runner.mark_processing(session, run)
        session.commit()
        job_uuid = str(run.id)
        meta = _metadata_dict(session, ticket_id)

    graph = get_approval_graph(use_memory=use_memory)
    config = thread_config(ticket_id)
    initial = {
        "ticket_id": ticket_id,
        "job_run_id": job_uuid,
        "required_departments": list(REQUIRED_DEPARTMENTS),
        "metadata": meta,
        "approvals": {},
        "execution_log": [],
    }
    try:
        result = graph.invoke(initial, config=config)
    except Exception as exc:
        logger.exception("approval start failed ticket=%s", ticket_id)
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_uuid))
            if run is not None and run.status == "processing":
                job_runner.mark_failed(session, run, str(exc)[:500])
                session.commit()
        raise

    if not _pending_interrupts(graph, config):
        # All already approved (edge case) or graph finished early
        logger.info(
            "approval start ticket=%s finished without interrupt (phase3_complete?)",
            ticket_id,
        )

    # If interrupted, LangGraph returns state with __interrupt__
    with Session(engine) as session:
        run = session.get(JobRun, UUID(job_uuid))
        if run is not None:
            run.checkpoint = "awaiting_approvals"
            session.add(run)
            # Keep processing until done — or mark completed if finished
            ticket = store.get_ticket(session, ticket_id)
            if ticket and ticket.status == "done":
                job_runner.mark_completed(session, run)
            session.commit()
    return {"ticket_id": ticket_id, "status": "waiting_for_approval", "result": result}


def _approvals_from_db(session: Session, ticket_id: str) -> dict[str, Any]:
    approvals: dict[str, Any] = {}
    for section in store.list_sections(session, ticket_id):
        if section.approval_status == "approved":
            approvals[section.department_id] = {
                "decision": "approve",
                "approver": section.approver or "",
                "reason": "",
            }
    return approvals


def _pending_interrupts(graph: Any, config: dict[str, Any]) -> bool:
    snap = graph.get_state(config)
    for task in snap.tasks or ():
        if getattr(task, "interrupts", None):
            return True
    return False


def _reseed_graph_to_interrupt(
    ticket_id: str,
    *,
    use_memory: bool = False,
) -> None:
    """Rebuild approval graph state from DB and run until the next interrupt."""
    engine = _ensure_engine()
    with Session(engine) as session:
        meta = _metadata_dict(session, ticket_id)
        approvals = _approvals_from_db(session, ticket_id)
        sections = store.list_sections(session, ticket_id)
        section_payload = [
            {
                "department_id": s.department_id,
                "key_aspects": s.key_aspects,
                "draft_content": s.draft_content,
                "evaluation_results": s.evaluation_results or {},
                "status": s.status,
                "approval_status": s.approval_status or "pending",
                "approver": s.approver,
                "approval_iteration": getattr(s, "approval_iteration", 0) or 0,
            }
            for s in sections
        ]

    graph = get_approval_graph(use_memory=use_memory, refresh=False)
    # Unique thread suffix avoided — overwrite by invoking with full state.
    # If a dead checkpoint exists without interrupts, update_state then step.
    config = thread_config(ticket_id)
    initial = {
        "ticket_id": ticket_id,
        "job_run_id": "reseed",
        "required_departments": list(REQUIRED_DEPARTMENTS),
        "metadata": meta,
        "approvals": approvals,
        "sections": section_payload,
        "revision_department": None,
        "revision_reason": None,
        "arbitration": None,
        "execution_log": [],
    }
    # Force a clean run on this thread by updating values then invoking from START
    try:
        graph.update_state(config, initial, as_node="__start__")
    except Exception:  # noqa: BLE001
        logger.warning("update_state failed for %s; invoking fresh", ticket_id)
    graph.invoke(initial, config=config)


def _apply_decision_without_interrupt(
    ticket_id: str,
    decision: dict[str, Any],
) -> dict[str, Any]:
    """DB-first fallback when the LangGraph interrupt checkpoint is missing."""
    from data.pipelines.rfp_intake.approval_graph import _write_section_approval
    from data.pipelines.rfp_intake.final_document import generate_final_document
    from data.pipelines.rfp_intake.owners import REQUIRED_DEPARTMENTS

    engine = _ensure_engine()
    dept = str(decision.get("department_id") or "")
    action = str(decision.get("decision") or "")
    approver = str(decision.get("approver") or "")
    reason = str(decision.get("reason") or "")

    with Session(engine) as session:
        if action == "approve":
            _write_section_approval(ticket_id, dept, "approved", approver)
        elif action == "reject":
            _write_section_approval(
                ticket_id, dept, "request_changes", approver, reason=reason
            )
            # Kick revision outside lock
            session.commit()
            from data.pipelines.rfp_intake.drafting_runner import run_drafting

            run_drafting(ticket_id, department_id=dept)
            with Session(engine) as session2:
                ticket = store.get_ticket(session2, ticket_id)
                return {
                    "ticket_id": ticket_id,
                    "status": ticket.status if ticket else "waiting_for_approval",
                    "result": {"fallback": "reject_revision"},
                }
        else:
            raise ValueError(f"unknown decision: {action}")

        sections = store.list_sections(session, ticket_id)
        by_dept = {s.department_id: s for s in sections}
        all_approved = all(
            (by_dept.get(d) is not None and by_dept[d].approval_status == "approved")
            for d in REQUIRED_DEPARTMENTS
        )
        if all_approved:
            ticket = store.get_ticket(session, ticket_id)
            if ticket is None:
                raise ValueError("ticket missing")
            generate_final_document(session, ticket_id)
            assert_can_transition(ticket.status, "done")
            store.set_ticket_status(session, ticket, "done")
            session.commit()
            return {"ticket_id": ticket_id, "status": "done", "result": {"fallback": True}}
        session.commit()
        ticket = store.get_ticket(session, ticket_id)
        return {
            "ticket_id": ticket_id,
            "status": ticket.status if ticket else "waiting_for_approval",
            "result": {"fallback": True},
        }


def resume_approval(
    ticket_id: str,
    decision: dict[str, Any],
    *,
    use_memory: bool = False,
) -> dict[str, Any]:
    engine = _ensure_engine()
    graph = get_approval_graph(use_memory=use_memory)
    config = thread_config(ticket_id)

    if not _pending_interrupts(graph, config):
        logger.warning(
            "No approval interrupt for ticket=%s — reseeding graph from DB",
            ticket_id,
        )
        try:
            _reseed_graph_to_interrupt(ticket_id, use_memory=use_memory)
        except Exception:
            logger.exception("reseed failed ticket=%s — DB fallback", ticket_id)
            return _apply_decision_without_interrupt(ticket_id, decision)

    if not _pending_interrupts(graph, config):
        logger.warning(
            "Still no interrupt after reseed ticket=%s — DB fallback",
            ticket_id,
        )
        return _apply_decision_without_interrupt(ticket_id, decision)

    try:
        result = graph.invoke(Command(resume=decision), config=config)
    except KeyError:
        logger.exception(
            "resume KeyError ticket=%s — reseeding then DB fallback if needed",
            ticket_id,
        )
        try:
            _reseed_graph_to_interrupt(ticket_id, use_memory=use_memory)
            if _pending_interrupts(graph, config):
                result = graph.invoke(Command(resume=decision), config=config)
            else:
                return _apply_decision_without_interrupt(ticket_id, decision)
        except Exception:
            logger.exception("resume recovery failed ticket=%s", ticket_id)
            return _apply_decision_without_interrupt(ticket_id, decision)

    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        status = ticket.status if ticket else "unknown"
        if status == "done":
            from sqlmodel import select

            runs = list(
                session.exec(
                    select(JobRun)
                    .where(JobRun.job_name == JOB_NAME, JobRun.target_key == ticket_id)
                    .order_by(JobRun.created_at.desc())  # type: ignore[arg-type]
                ).all()
            )
            if runs and runs[0].status == "processing":
                job_runner.mark_completed(session, runs[0])
                session.commit()
    return {"ticket_id": ticket_id, "status": status, "result": result}


def run_all_phases(
    ticket_id: str,
    job_run_id: str | None = None,
    *,
    skip_intake: bool = False,
) -> dict[str, Any]:
    """Chain intake → drafting → approval until human stop."""
    engine = _ensure_engine()
    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        if ticket is None:
            raise ValueError(f"ticket not found: {ticket_id}")
        run: JobRun | None = None
        if job_run_id:
            run = session.get(JobRun, UUID(job_run_id))
        if run is None:
            job_runner.reclaim_stale_locks(session, RUN_ALL_JOB)
            run = job_runner.create_pending_for_key(
                session, RUN_ALL_JOB, ticket_id, date.today()
            )
            session.commit()
            session.refresh(run)
        job_runner.mark_processing(session, run)
        run.checkpoint = json.dumps({"stage": "intake" if not skip_intake else "drafting"})
        session.add(run)
        session.commit()
        job_uuid = str(run.id)

    try:
        if not skip_intake:
            from data.pipelines.rfp_intake.runner import run_intake

            with Session(engine) as session:
                run = session.get(JobRun, UUID(job_uuid))
                if run:
                    run.checkpoint = json.dumps({"stage": "intake"})
                    session.add(run)
                    session.commit()
            # Intake uses its own JobRun; call pipeline directly via ticket
            from data.pipelines.rfp_intake.runner import run_intake as _intake

            # Create nested intake job
            with Session(engine) as session:
                intake_run = job_runner.create_pending_for_key(
                    session, "rfp_intake", ticket_id, date.today()
                )
                session.commit()
                intake_id = str(intake_run.id)
            _intake(ticket_id, job_run_id=intake_id)

            with Session(engine) as session:
                ticket = store.get_ticket(session, ticket_id)
                if ticket is None:
                    raise ValueError("ticket missing after intake")
                if ticket.status == "discarded" or (
                    ticket.status == "analyzing" and ticket.needs_human_review
                ):
                    run = session.get(JobRun, UUID(job_uuid))
                    if run:
                        run.checkpoint = json.dumps(
                            {"stage": "halted_human_review", "at": "intake"}
                        )
                        job_runner.mark_completed(session, run)
                        session.commit()
                    return {
                        "ticket_id": ticket_id,
                        "halted": True,
                        "stage": "intake",
                        "status": ticket.status,
                    }

        # Drafting
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_uuid))
            if run:
                run.checkpoint = json.dumps({"stage": "drafting"})
                session.add(run)
                session.commit()
            ticket = store.get_ticket(session, ticket_id)
            if ticket and ticket.status == "intake_complete":
                store.set_ticket_status(session, ticket, "drafting")
                session.commit()

        from data.pipelines.rfp_intake.drafting_runner import run_drafting

        run_drafting(ticket_id)

        with Session(engine) as session:
            sections = store.list_sections(session, ticket_id)
            needing = [s for s in sections if s.status == "needs_human_review"]
            if needing:
                run = session.get(JobRun, UUID(job_uuid))
                if run:
                    run.checkpoint = json.dumps(
                        {
                            "stage": "halted_human_review",
                            "at": "drafting",
                            "pending_departments": [s.department_id for s in needing],
                        }
                    )
                    job_runner.mark_completed(session, run)
                    session.commit()
                return {
                    "ticket_id": ticket_id,
                    "halted": True,
                    "stage": "drafting",
                    "status": "under_evaluation",
                    "message": (
                        "Phase 2 needs human review; Phase 3 starts automatically "
                        "once all sections are passed (e.g. after Re-draft)."
                    ),
                }
            if not sections or not all(s.status == "passed" for s in sections):
                raise RuntimeError("Drafting did not complete all sections")

        # Approval — always auto-chain when Phase 2 is fully passed
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_uuid))
            if run:
                run.checkpoint = json.dumps({"stage": "approval"})
                session.add(run)
                session.commit()

        start_approval(ticket_id)
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_uuid))
            if run:
                run.checkpoint = json.dumps({"stage": "awaiting_approvals"})
                job_runner.mark_completed(session, run)
                session.commit()
        return {
            "ticket_id": ticket_id,
            "halted": True,
            "stage": "approval",
            "status": "waiting_for_approval",
        }
    except Exception as exc:
        logger.exception("run_all failed ticket=%s", ticket_id)
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_uuid))
            if run is not None and run.status == "processing":
                job_runner.mark_failed(session, run, str(exc)[:500])
                session.commit()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RFP Phase 3 approval / run-all")
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--skip-intake", action="store_true")
    parser.add_argument("--resume-department", default=None)
    parser.add_argument("--decision", choices=["approve", "reject"], default=None)
    parser.add_argument("--approver", default=None)
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    _ensure_engine()
    if args.run_all:
        run_all_phases(args.ticket_id, skip_intake=args.skip_intake)
        return 0
    if args.resume_department and args.decision and args.approver:
        resume_approval(
            args.ticket_id,
            {
                "department_id": args.resume_department,
                "decision": args.decision,
                "approver": args.approver,
                "reason": args.reason,
            },
        )
        return 0
    start_approval(args.ticket_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
