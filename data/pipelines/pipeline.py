"""HealthCore telemetry KPI ETL — local Prefect flow orchestrator.

Layout:
  data/pipelines/extract/   — watermark, source read, PHI scan
  data/pipelines/transform/ — KPI aggregates
  data/pipelines/load/      — upserts, run log, snapshot export

Run (requires DATABASE_URL):
  uv run python data/pipelines/pipeline.py
Intended schedule: nightly cron ``0 2 * * *`` (see docs/data_pipelines/pipeline-design.md).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from prefect import flow
from sqlmodel import Session

# Bootstrap: services/api (app.*) and repo root (data.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.core.db import supabase_engine  # noqa: E402
from app.domains.telemetry.reporting_models import PipelineRun  # noqa: E402
from data.pipelines.config import KPI_EVENT_TYPES, PIPELINE_VERSION  # noqa: E402
from data.pipelines.extract.phi import count_null_grain_rows, scan_tags_for_phi  # noqa: E402
from data.pipelines.extract.tasks import extract_telemetry_events  # noqa: E402
from data.pipelines.extract.window import resolve_window  # noqa: E402
from data.pipelines.load import repository as repo  # noqa: E402
from data.pipelines.load.runs import finish_run, load_run, start_run  # noqa: E402
from data.pipelines.load.tasks import (  # noqa: E402
    export_snapshot_optional,
    load_reporting_tables,
)
from data.pipelines.transform.tasks import transform_kpi_aggregates  # noqa: E402

logger = logging.getLogger(__name__)


def _ensure_engine():
    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set — refusing to run against no database.")
    return supabase_engine


@flow(name="telemetry-etl")
def telemetry_etl_flow(
    start: datetime | None = None,
    end: datetime | None = None,
    run_id: UUID | None = None,
) -> int:
    engine = _ensure_engine()
    from sqlmodel import SQLModel
    import app.domains.telemetry.reporting_models  # noqa: F401

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        if run_id is None:
            run_id = start_run(session)
        else:
            existing = repo.get_pipeline_run(session, run_id)
            if existing is None:
                run = PipelineRun(
                    run_id=run_id,
                    started_at=datetime.now(timezone.utc),
                    status="running",
                    pipeline_version=PIPELINE_VERSION,
                )
                repo.insert_pipeline_run(session, run)
        run_id_str = str(run_id)
        w_from, w_to = resolve_window(start, end, session)

    rows_extracted = 0
    rows_loaded = 0
    rows_quarantined = 0
    checkpoint = None

    try:
        df = extract_telemetry_events(KPI_EVENT_TYPES, w_from, w_to)
        rows_extracted = 0 if df is None else len(df)
        checkpoint = "extract"

        with Session(engine) as session:
            run = load_run(session, run_id)
            run.checkpoint = checkpoint
            run.watermark_from = w_from
            run.watermark_to = w_to
            run.rows_extracted = rows_extracted
            repo.update_pipeline_run(session, run)

        phi_tripped, phi_count = scan_tags_for_phi(df)
        null_grains = count_null_grain_rows(df)
        rows_quarantined = phi_count + null_grains
        if phi_tripped:
            logger.warning("possible PHI in tags — load blocked (run_id=%s)", run_id_str)
            with Session(engine) as session:
                finish_run(
                    session,
                    run_id,
                    status="quarantined",
                    watermark_from=w_from,
                    watermark_to=w_to,
                    rows_extracted=rows_extracted,
                    rows_loaded=0,
                    rows_quarantined=rows_quarantined,
                    error_summary="possible PHI in tags",
                    checkpoint=checkpoint,
                )
            return 0

        metrics = transform_kpi_aggregates(w_from, w_to)
        checkpoint = "transform"
        with Session(engine) as session:
            run = load_run(session, run_id)
            run.checkpoint = checkpoint
            repo.update_pipeline_run(session, run)

        rows_loaded = load_reporting_tables(metrics, run_id_str)
        checkpoint = "load"

        snapshot_state = export_snapshot_optional(metrics, return_state=True)
        partial = bool(snapshot_state is not None and snapshot_state.is_failed())
        if partial:
            logger.warning("optional snapshot export failed; continuing (run_id=%s)", run_id_str)

        with Session(engine) as session:
            finish_run(
                session,
                run_id,
                status="partial" if partial else "success",
                watermark_from=w_from,
                watermark_to=w_to,
                rows_extracted=rows_extracted,
                rows_loaded=rows_loaded,
                rows_quarantined=rows_quarantined,
                checkpoint=checkpoint,
            )
        return rows_loaded
    except Exception as exc:  # noqa: BLE001
        logger.exception("telemetry ETL failed (run_id=%s)", run_id_str)
        with Session(engine) as session:
            finish_run(
                session,
                run_id,
                status="failed",
                watermark_from=w_from,
                watermark_to=w_to,
                rows_extracted=rows_extracted,
                rows_loaded=rows_loaded,
                rows_quarantined=rows_quarantined,
                error_summary=str(exc)[:500],
                checkpoint=checkpoint,
            )
        raise


@flow(name="telemetry-backfill")
def backfill_flow(start: datetime, end: datetime) -> int:
    """Thin backfill wrapper — same tasks with an explicit event-time window."""
    return telemetry_etl_flow(start=start, end=end)


if __name__ == "__main__":
    from app.core.config import settings

    if not settings.database_url or supabase_engine is None:
        print(
            "DATABASE_URL is not set — refusing to run against no database.",
            file=sys.stderr,
        )
        sys.exit(1)
    telemetry_etl_flow()
