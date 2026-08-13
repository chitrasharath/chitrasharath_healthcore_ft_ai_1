"""RFP intake runner — BackgroundTasks entry + CLI re-run."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

# Bootstrap: services/api (app.*) and repo root (data.*)
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
from data.pipelines.rfp_intake.graph import get_graph  # noqa: E402

logger = logging.getLogger(__name__)

JOB_NAME = "rfp_intake"


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


def run_intake(ticket_id: str, job_run_id: str | None = None) -> None:
    """Execute the intake graph for a ticket (from-scratch idempotent upserts)."""
    engine = _ensure_engine()
    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        if ticket is None:
            raise ValueError(f"ticket not found: {ticket_id}")
        pdf_path = ticket.raw_pdf_path
        if not pdf_path:
            raise ValueError(f"ticket {ticket_id} has no raw_pdf_path")

        run: JobRun | None = None
        if job_run_id:
            run = session.get(JobRun, UUID(job_run_id))
        if run is None:
            # CLI / re-run path
            job_runner.reclaim_stale_locks(session, JOB_NAME)
            if job_runner.has_processing_lock_for_key(session, JOB_NAME, ticket_id):
                raise RuntimeError(f"processing lock held for ticket {ticket_id}")
            from datetime import date

            run = job_runner.create_pending_for_key(
                session,
                JOB_NAME,
                ticket_id,
                date.today(),
            )
            session.commit()
            session.refresh(run)

        job_runner.mark_processing(session, run)
        # Reset status for re-run (from scratch)
        store.set_ticket_status(session, ticket, "analyzing", needs_human_review=False)
        session.commit()
        job_run_uuid = str(run.id)

    initial = {
        "ticket_id": ticket_id,
        "job_run_id": job_run_uuid,
        "pdf_path": pdf_path,
    }

    try:
        get_graph().invoke(initial)
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_run_uuid))
            if run is not None:
                job_runner.mark_completed(session, run)
                session.commit()
    except Exception as exc:
        logger.exception("rfp_intake failed ticket_id=%s", ticket_id)
        with Session(engine) as session:
            run = session.get(JobRun, UUID(job_run_uuid))
            if run is not None:
                job_runner.mark_failed(session, run, str(exc))
                session.commit()
            ticket = store.get_ticket(session, ticket_id)
            if ticket is not None and ticket.status not in ("discarded", "intake_complete"):
                # Stay analyzing but flag so UI doesn't look "still running"
                store.set_ticket_status(
                    session,
                    ticket,
                    "analyzing",
                    classifier_reason=f"Job failed: {str(exc)[:240]}",
                    needs_human_review=True,
                )
                session.commit()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-run RFP intake for a ticket")
    parser.add_argument("--ticket-id", required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    _ensure_engine()
    run_intake(args.ticket_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
