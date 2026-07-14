"""Demo seed for Reporting dashboard — ~12 months of KPI grains.

Idempotent via the same upsert path as the ETL. Run via ``uv run seed``
(from ``services/api``) or ``python -m app.domains.telemetry.seed_reporting``.
"""

from __future__ import annotations

import hashlib
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlmodel import Session, SQLModel

# Repo root so ``data.pipelines`` is importable when run as ``uv run seed``.
_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.core.db import supabase_engine  # noqa: E402
from app.domains.telemetry.reporting_models import PipelineRun  # noqa: E402
from data.pipelines.load import repository as repo  # noqa: E402

# Match inventory CLINICS catalog (jurisdiction = clinic location).
CLINICS: list[tuple[int, str]] = [
    (1, "us"),
    (2, "us"),
    (3, "us"),
    (4, "us"),
    (5, "us"),
    (6, "us"),
    (7, "uk"),
    (8, "uk"),
    (9, "uk"),
]

SUPPLY_IDS = ["1", "2", "3", "4", "5", "6"]
SEED_RUN_ID = UUID("a1111111-b222-c333-d444-e55555555555")


def _hash01(*parts: object) -> float:
    """Stable 0–1 pseudo-random from grain keys (idempotent regenerations)."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def build_demo_metrics(today: date | None = None) -> dict[str, list[dict[str, Any]]]:
    """Generate ~12 months of daily grains with clinic / jurisdiction variation."""
    end = today or datetime.now(timezone.utc).date()
    start = date(end.year, end.month, 1)
    for _ in range(11):
        start = (start.replace(day=1) - timedelta(days=1)).replace(day=1)

    consumption: list[dict[str, Any]] = []
    stock: list[dict[str, Any]] = []
    auth: list[dict[str, Any]] = []

    for day in _daterange(start, end):
        weekday = day.weekday()
        weekend_scale = 0.35 if weekday >= 5 else 1.0
        month_wave = 1.0 + 0.18 * math.sin((day.month - 1) / 12 * 2 * math.pi)

        for clinic_id, jurisdiction in CLINICS:
            base = 8 if jurisdiction == "us" else 5
            clinic_boost = 1.0 + 0.12 * (clinic_id % 5)
            noise = 0.7 + 0.6 * _hash01(day, clinic_id, "c")
            count = max(
                1,
                int(round(base * clinic_boost * weekend_scale * month_wave * noise)),
            )
            consumption.append(
                {
                    "date": day.isoformat(),
                    "clinic_id": clinic_id,
                    "jurisdiction": jurisdiction,
                    "count": count,
                },
            )

            if _hash01(day, clinic_id, "s") > 0.62:
                supply_id = SUPPLY_IDS[
                    int(_hash01(day, clinic_id, "sid") * len(SUPPLY_IDS)) % len(SUPPLY_IDS)
                ]
                attempts = max(3, int(count * 0.4) + 2)
                failures = max(
                    1,
                    int(attempts * (0.08 + 0.25 * _hash01(day, clinic_id, "f"))),
                )
                failures = min(failures, attempts)
                stock.append(
                    {
                        "date": day.isoformat(),
                        "clinic_id": clinic_id,
                        "jurisdiction": jurisdiction,
                        "supply_id": supply_id,
                        "count": failures,
                        "attempts": attempts,
                        "rejection_rate": failures / attempts,
                    },
                )

        succeeded = int(40 + 30 * _hash01(day, "auth_ok") * weekend_scale)
        failed = max(
            0,
            int(1 + 8 * _hash01(day, "auth_fail") * (1.4 if weekday == 0 else 1.0)),
        )
        denom = failed + succeeded
        auth.append(
            {
                "date": day.isoformat(),
                "failed": failed,
                "succeeded": max(succeeded, 1),
                "failure_rate": failed / denom if denom else 0.0,
            },
        )

    waste: list[dict[str, Any]] = []
    days = sorted({date.fromisoformat(r["date"]) for r in consumption})
    for day in days:
        for jurisdiction in ("us", "uk"):
            day_total = sum(
                r["count"]
                for r in consumption
                if r["date"] == day.isoformat() and r["jurisdiction"] == jurisdiction
            )
            if day_total == 0:
                continue
            waste_share = 0.06 + 0.12 * _hash01(day, jurisdiction, "w")
            if jurisdiction == "uk":
                waste_share *= 0.75
            waste_share = min(0.35, waste_share)
            waste.append(
                {
                    "date": day.isoformat(),
                    "jurisdiction": jurisdiction,
                    "waste_rate": round(waste_share, 4),
                    "total": day_total,
                },
            )

    return {
        "consumption_volume_per_day": consumption,
        "waste_rate_per_day": waste,
        "insufficient_stock_failures_per_day": stock,
        "auth_failure_rate": auth,
    }


def _demo_run_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"healthcore-reporting-demo:{key}")


def build_demo_pipeline_runs(
    metrics: dict[str, list[dict[str, Any]]],
    *,
    now: datetime | None = None,
) -> list[PipelineRun]:
    """~14 nights of ETL history; newest is a full success tied to the KPI seed."""
    now = now or datetime.now(timezone.utc)
    total_rows = sum(len(v) for v in metrics.values())
    # Watermark window matches the first demo report_date through now.
    dates = [
        date.fromisoformat(r["date"])
        for r in metrics.get("consumption_volume_per_day", [])
    ]
    wm_from = datetime.combine(min(dates), datetime.min.time(), tzinfo=timezone.utc) if dates else now - timedelta(days=400)

    scenarios: list[tuple[str, str, str | None, str, int, int, int]] = [
        # days_ago, status, error, checkpoint, extracted, loaded, quarantined
        (13, "success", None, "load", 120, 118, 0),
        (12, "success", None, "load", 140, 140, 0),
        (11, "failed", "connection reset during extract", "extract", 0, 0, 0),
        (10, "success", None, "load", 155, 152, 1),
        (9, "partial", "optional snapshot export failed", "load", 160, 160, 0),
        (8, "success", None, "load", 148, 148, 0),
        (7, "quarantined", "possible PHI in tags", "extract", 42, 0, 42),
        (6, "success", None, "load", 170, 169, 0),
        (5, "success", None, "load", 165, 165, 0),
        (4, "failed", "transform raised: empty grain after dropna", "transform", 90, 0, 0),
        (3, "success", None, "load", 180, 180, 0),
        (2, "partial", "optional snapshot export failed", "load", 175, 175, 0),
        (1, "success", None, "load", 190, 188, 2),
    ]

    runs: list[PipelineRun] = []
    for days_ago, status, error, checkpoint, extracted, loaded, quarantined in scenarios:
        started = now - timedelta(days=days_ago, hours=2, minutes=5)
        finished = started + timedelta(minutes=2, seconds=40)
        runs.append(
            PipelineRun(
                run_id=_demo_run_id(f"nightly-{days_ago}"),
                started_at=started,
                finished_at=finished,
                watermark_from=wm_from if status in {"success", "partial"} else started - timedelta(days=2),
                watermark_to=finished if status in {"success", "partial"} else None,
                rows_extracted=extracted,
                rows_loaded=loaded,
                rows_quarantined=quarantined,
                status=status,
                error_summary=error,
                pipeline_version="1.0.0",
                checkpoint=checkpoint,
            ),
        )

    # Latest = KPI materialization run (newest started_at).
    runs.append(
        PipelineRun(
            run_id=SEED_RUN_ID,
            started_at=now - timedelta(minutes=18),
            finished_at=now - timedelta(minutes=15),
            watermark_from=wm_from,
            watermark_to=now - timedelta(minutes=15),
            rows_extracted=total_rows,
            rows_loaded=total_rows,
            rows_quarantined=0,
            status="success",
            error_summary=None,
            pipeline_version="1.0.0",
            checkpoint="load",
        ),
    )
    return runs


def seed_pipeline_health_demo(
    metrics: dict[str, list[dict[str, Any]]],
) -> int:
    """Replace pipeline_runs with demo history + latest success for health tab."""
    if supabase_engine is None:
        return 0

    from sqlalchemy import text

    runs = build_demo_pipeline_runs(metrics)
    with supabase_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE pipeline_runs"))

    with Session(supabase_engine) as session:
        for run in runs:
            session.add(run)
        session.commit()
    return len(runs)


def seed_reporting_demo(*, force_run_id: UUID | None = None) -> dict[str, int]:
    if supabase_engine is None:
        print("Skipping reporting demo seed: DATABASE_URL not configured.")
        return {"rows_loaded": 0}

    import app.domains.telemetry.reporting_models  # noqa: F401
    from sqlalchemy import text

    SQLModel.metadata.create_all(supabase_engine)
    metrics = build_demo_metrics()
    run_id = force_run_id or SEED_RUN_ID

    # Clear prior demo/ETL KPI grains so the dashboard only shows this catalog.
    with supabase_engine.begin() as conn:
        for table in (
            "reporting_consumption_volume_daily",
            "reporting_waste_rate_daily",
            "reporting_stock_failures_daily",
            "reporting_auth_failure_daily",
        ):
            conn.execute(text(f"TRUNCATE TABLE {table}"))

    health_runs = seed_pipeline_health_demo(metrics)
    rows_loaded = repo.load_all_reporting(supabase_engine, metrics, run_id)

    # Keep latest run row counts in sync with upsert result.
    with Session(supabase_engine) as session:
        run = repo.get_pipeline_run(session, run_id)
        if run is not None:
            run.rows_loaded = rows_loaded
            run.rows_extracted = sum(len(v) for v in metrics.values())
            run.status = "success"
            run.finished_at = datetime.now(timezone.utc)
            repo.update_pipeline_run(session, run)

    counts = {key: len(vals) for key, vals in metrics.items()}
    counts["rows_loaded"] = rows_loaded
    counts["pipeline_runs"] = health_runs
    print(
        "Reporting demo seed complete: "
        f"{counts.get('consumption_volume_per_day', 0)} consumption, "
        f"{counts.get('waste_rate_per_day', 0)} waste, "
        f"{counts.get('insufficient_stock_failures_per_day', 0)} stock, "
        f"{counts.get('auth_failure_rate', 0)} auth rows "
        f"(upserted {rows_loaded}); {health_runs} pipeline_runs.",
    )
    return counts


def main() -> None:
    seed_reporting_demo()


if __name__ == "__main__":
    main()
