from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.domains.telemetry.reporting_models import (
    PipelineRun,
    ReportingAuthFailureDaily,
    ReportingConsumptionVolumeDaily,
    ReportingStockFailuresDaily,
    ReportingWasteRateDaily,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_report_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def upsert_consumption_volume(conn, rows: list[dict[str, Any]], run_id: UUID) -> int:
    if not rows:
        return 0
    updated = now_utc()
    values = [
        {
            "report_date": _parse_report_date(r["date"]),
            "clinic_id": int(r["clinic_id"]),
            "jurisdiction": str(r["jurisdiction"]),
            "count": int(r["count"]),
            "run_id": run_id,
            "updated_at": updated,
        }
        for r in rows
    ]
    stmt = pg_insert(ReportingConsumptionVolumeDaily).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["report_date", "clinic_id", "jurisdiction"],
        set_={
            "count": stmt.excluded.count,
            "run_id": run_id,
            "updated_at": updated,
        },
    )
    conn.execute(stmt)
    return len(values)


def upsert_waste_rate(conn, rows: list[dict[str, Any]], run_id: UUID) -> int:
    if not rows:
        return 0
    updated = now_utc()
    values = [
        {
            "report_date": _parse_report_date(r["date"]),
            "jurisdiction": str(r["jurisdiction"]),
            "waste_rate": float(r["waste_rate"]),
            "total": int(r["total"]),
            "run_id": run_id,
            "updated_at": updated,
        }
        for r in rows
    ]
    stmt = pg_insert(ReportingWasteRateDaily).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["report_date", "jurisdiction"],
        set_={
            "waste_rate": stmt.excluded.waste_rate,
            "total": stmt.excluded.total,
            "run_id": run_id,
            "updated_at": updated,
        },
    )
    conn.execute(stmt)
    return len(values)


def upsert_stock_failures(conn, rows: list[dict[str, Any]], run_id: UUID) -> int:
    if not rows:
        return 0
    updated = now_utc()
    values = [
        {
            "report_date": _parse_report_date(r["date"]),
            "clinic_id": int(r["clinic_id"]),
            "jurisdiction": str(r["jurisdiction"]),
            "supply_id": str(r["supply_id"]),
            "count": int(r["count"]),
            "attempts": int(r["attempts"]),
            "rejection_rate": float(r["rejection_rate"]),
            "run_id": run_id,
            "updated_at": updated,
        }
        for r in rows
    ]
    stmt = pg_insert(ReportingStockFailuresDaily).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["report_date", "clinic_id", "jurisdiction", "supply_id"],
        set_={
            "count": stmt.excluded.count,
            "attempts": stmt.excluded.attempts,
            "rejection_rate": stmt.excluded.rejection_rate,
            "run_id": run_id,
            "updated_at": updated,
        },
    )
    conn.execute(stmt)
    return len(values)


def upsert_auth_failure(conn, rows: list[dict[str, Any]], run_id: UUID) -> int:
    if not rows:
        return 0
    updated = now_utc()
    values = [
        {
            "report_date": _parse_report_date(r["date"]),
            "failed": int(r["failed"]),
            "succeeded": int(r["succeeded"]),
            "failure_rate": float(r["failure_rate"]),
            "run_id": run_id,
            "updated_at": updated,
        }
        for r in rows
    ]
    stmt = pg_insert(ReportingAuthFailureDaily).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["report_date"],
        set_={
            "failed": stmt.excluded.failed,
            "succeeded": stmt.excluded.succeeded,
            "failure_rate": stmt.excluded.failure_rate,
            "run_id": run_id,
            "updated_at": updated,
        },
    )
    conn.execute(stmt)
    return len(values)


def load_all_reporting(
    engine,
    metrics: dict[str, list[dict[str, Any]]],
    run_id: UUID,
) -> int:
    """Upsert all four KPI tables in one transaction. Returns total rows written."""
    with engine.begin() as conn:
        total = 0
        total += upsert_consumption_volume(
            conn,
            metrics.get("consumption_volume_per_day", []),
            run_id,
        )
        total += upsert_waste_rate(
            conn,
            metrics.get("waste_rate_per_day", []),
            run_id,
        )
        total += upsert_stock_failures(
            conn,
            metrics.get("insufficient_stock_failures_per_day", []),
            run_id,
        )
        total += upsert_auth_failure(
            conn,
            metrics.get("auth_failure_rate", []),
            run_id,
        )
    return total


def _date_bounds(start: datetime, end: datetime) -> tuple[date, date]:
    start_d = start.astimezone(timezone.utc).date() if start.tzinfo else start.date()
    end_d = end.astimezone(timezone.utc).date() if end.tzinfo else end.date()
    return start_d, end_d


def read_reporting_metrics(
    session: Session,
    start: datetime,
    end: datetime,
) -> dict[str, list[dict[str, Any]]]:
    start_d, end_d = _date_bounds(start, end)

    consumption = session.exec(
        select(ReportingConsumptionVolumeDaily).where(
            ReportingConsumptionVolumeDaily.report_date >= start_d,
            ReportingConsumptionVolumeDaily.report_date <= end_d,
        ),
    ).all()
    waste = session.exec(
        select(ReportingWasteRateDaily).where(
            ReportingWasteRateDaily.report_date >= start_d,
            ReportingWasteRateDaily.report_date <= end_d,
        ),
    ).all()
    stock = session.exec(
        select(ReportingStockFailuresDaily).where(
            ReportingStockFailuresDaily.report_date >= start_d,
            ReportingStockFailuresDaily.report_date <= end_d,
        ),
    ).all()
    auth = session.exec(
        select(ReportingAuthFailureDaily).where(
            ReportingAuthFailureDaily.report_date >= start_d,
            ReportingAuthFailureDaily.report_date <= end_d,
        ),
    ).all()

    return {
        "consumption_volume_per_day": [
            {
                "date": r.report_date.isoformat(),
                "clinic_id": r.clinic_id,
                "jurisdiction": r.jurisdiction,
                "count": r.count,
            }
            for r in consumption
        ],
        "waste_rate_per_day": [
            {
                "date": r.report_date.isoformat(),
                "jurisdiction": r.jurisdiction,
                "waste_rate": r.waste_rate,
                "total": r.total,
            }
            for r in waste
        ],
        "insufficient_stock_failures_per_day": [
            {
                "date": r.report_date.isoformat(),
                "clinic_id": r.clinic_id,
                "jurisdiction": r.jurisdiction,
                "supply_id": r.supply_id,
                "count": r.count,
                "attempts": r.attempts,
                "rejection_rate": r.rejection_rate,
            }
            for r in stock
        ],
        "auth_failure_rate": [
            {
                "date": r.report_date.isoformat(),
                "failed": r.failed,
                "succeeded": r.succeeded,
                "failure_rate": r.failure_rate,
            }
            for r in auth
        ],
    }


def insert_pipeline_run(session: Session, run: PipelineRun) -> None:
    session.add(run)
    session.commit()


def update_pipeline_run(session: Session, run: PipelineRun) -> None:
    session.add(run)
    session.commit()


def get_latest_pipeline_run(session: Session) -> PipelineRun | None:
    return session.exec(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()),  # type: ignore[arg-type]
    ).first()


def list_recent_pipeline_runs(session: Session, limit: int = 14) -> list[PipelineRun]:
    capped = max(1, min(limit, 50))
    return list(
        session.exec(
            select(PipelineRun)
            .order_by(PipelineRun.started_at.desc())  # type: ignore[arg-type]
            .limit(capped),
        ).all(),
    )


def get_latest_success_watermark_to(session: Session) -> datetime | None:
    row = session.exec(
        select(PipelineRun)
        .where(PipelineRun.status.in_(["success", "partial"]))  # type: ignore[attr-defined]
        .order_by(PipelineRun.started_at.desc()),  # type: ignore[arg-type]
    ).first()
    return row.watermark_to if row else None


def get_pipeline_run(session: Session, run_id: UUID) -> PipelineRun | None:
    return session.get(PipelineRun, run_id)
