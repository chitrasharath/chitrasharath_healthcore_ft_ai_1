"""RFP drafting runner — BackgroundTasks entry + CLI."""

from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlmodel import Session

_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.core.db import supabase_engine  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.domains.jobs import job_runner  # noqa: E402
from app.domains.jobs.models import JobRun  # noqa: E402
from app.domains.rfp_intake import store  # noqa: E402
from data.pipelines.rfp_intake.drafting_graph import get_drafting_graph  # noqa: E402

logger = logging.getLogger(__name__)

JOB_NAME = "rfp_drafting"


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


def _shared_metadata(session: Session, ticket_id: str) -> dict[str, Any]:
    meta = store.get_metadata(session, ticket_id)
    if meta is None:
        return {}
    country = (meta.client_country or "").upper()
    currency = "GBP" if country == "UK" else "USD"
    return {
        "client_name": meta.client_name,
        "client_country": meta.client_country,
        "program_type": meta.program_type,
        "covered_population": meta.covered_population,
        "covered_population_n": meta.covered_population_n,
        "deadline": meta.deadline,
        "budget_range": meta.budget_range,
        "currency": currency,
        "open_questions": meta.open_questions or [],
    }


def _run_one_section(
    *,
    ticket_id: str,
    job_run_id: str,
    section_id: int,
    department_id: str,
    key_aspects: Any,
    open_questions: list[Any],
    shared_metadata: dict[str, Any],
    draft_content: str = "",
    feedback_for_generator: str = "",
) -> None:
    initial = {
        "ticket_id": ticket_id,
        "job_run_id": job_run_id,
        "section_id": section_id,
        "department_id": department_id,
        "key_aspects": key_aspects or [],
        "open_questions": open_questions,
        "shared_metadata": shared_metadata,
        "subtask": f"Draft the {department_id} proposal section answering key_aspects.",
        "iteration": 0,
        "max_iterations": int(settings.rfp_max_draft_iterations),
        "feedback_for_generator": feedback_for_generator or "",
        "draft_content": draft_content or "",
    }
    get_drafting_graph().invoke(initial)


def run_drafting(
    ticket_id: str,
    job_run_id: str | None = None,
    *,
    department_id: str | None = None,
) -> None:
    """Run drafting loops for all (or one) department sections concurrently."""
    engine = _ensure_engine()
    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        if ticket is None:
            raise ValueError(f"ticket not found: {ticket_id}")
        if ticket.status in ("discarded", "analyzing"):
            raise RuntimeError(
                f"Cannot draft ticket in status={ticket.status} "
                "(must be intake_complete or later)"
            )

        run: JobRun | None = None
        if job_run_id:
            run = session.get(JobRun, UUID(job_run_id))
        if run is None:
            from datetime import date

            lock_key = f"{ticket_id}:{department_id}" if department_id else ticket_id
            job_runner.reclaim_stale_locks(session, JOB_NAME)
            if job_runner.has_processing_lock_for_key(session, JOB_NAME, lock_key):
                raise RuntimeError(f"processing lock held for {lock_key}")
            if department_id and job_runner.has_processing_lock_for_key(
                session, JOB_NAME, ticket_id
            ):
                raise RuntimeError(f"processing lock held for ticket {ticket_id}")
            run = job_runner.create_pending_for_key(
                session,
                JOB_NAME,
                lock_key,
                date.today(),
            )
            session.commit()
            session.refresh(run)

        job_runner.mark_processing(session, run)
        if ticket.status == "intake_complete":
            store.set_ticket_status(session, ticket, "drafting")
        session.commit()
        job_run_uuid = str(run.id)

        sections = store.list_sections(session, ticket_id)
        if department_id:
            sections = [s for s in sections if s.department_id == department_id]
        if not sections:
            job_runner.mark_failed(session, run, "No department sections to draft")
            session.commit()
            raise ValueError("No department sections to draft")

        meta = _shared_metadata(session, ticket_id)
        open_questions = list(meta.get("open_questions") or [])
        work = [
            {
                "section_id": int(s.id),
                "department_id": s.department_id,
                "key_aspects": s.key_aspects,
                "open_questions": open_questions,
                "shared_metadata": meta,
                "draft_content": s.draft_content or "",
                "feedback_for_generator": str(
                    (s.evaluation_results or {}).get("feedback_for_generator") or ""
                ),
            }
            for s in sections
            if s.id is not None
        ]

    try:
        with ThreadPoolExecutor(max_workers=max(1, len(work))) as pool:
            futures = [
                pool.submit(
                    _run_one_section,
                    ticket_id=ticket_id,
                    job_run_id=job_run_uuid,
                    section_id=item["section_id"],
                    department_id=item["department_id"],
                    key_aspects=item["key_aspects"],
                    open_questions=item["open_questions"],
                    shared_metadata=item["shared_metadata"],
                    draft_content=item.get("draft_content") or "",
                    feedback_for_generator=item.get("feedback_for_generator") or "",
                )
                for item in work
            ]
            errors: list[str] = []
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("section drafting failed ticket=%s", ticket_id)
                    errors.append(str(exc)[:200])
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_run_uuid))
            if run is not None:
                if errors:
                    job_runner.mark_failed(session, run, "; ".join(errors)[:500])
                else:
                    job_runner.mark_completed(session, run)
                session.commit()
        if errors:
            raise RuntimeError("; ".join(errors))
    except Exception as exc:
        logger.exception("rfp_drafting failed ticket_id=%s", ticket_id)
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_run_uuid))
            if run is not None and run.status == "processing":
                job_runner.mark_failed(session, run, str(exc))
                session.commit()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RFP drafting for a ticket")
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument("--department-id", default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    _ensure_engine()
    run_drafting(args.ticket_id, department_id=args.department_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
