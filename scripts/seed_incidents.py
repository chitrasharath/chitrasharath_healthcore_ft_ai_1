#!/usr/bin/env python3
"""Seed incident table from historical CSV (idempotent)."""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from healthcore_incidents import CSV_STATUS_MAP, RULE_LABELS, load_incidents, validate_record
from sqlmodel import Session, SQLModel, select

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = (
    REPO_ROOT
    / "memory-bank/references/centralized_incident_manager_ai_plan/incidents-healthcore.csv"
)
API_PATH = REPO_ROOT / "services" / "api"

if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))

from app.core.config import settings  # noqa: E402
from app.core.db import supabase_engine  # noqa: E402
from app.domains.incidents import models as incident_models  # noqa: F401, E402
from app.domains.incidents.models import Incident  # noqa: E402


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _generate_title(category: str, clinic_id: str) -> str:
    return f"{category} incident at {clinic_id}"


def seed_incidents(engine=None) -> tuple[int, int, int, Counter[str]]:
    if engine is None:
        if not settings.database_url or supabase_engine is None:
            raise SystemExit("DATABASE_URL is not configured. Set it in services/api/.env")
        engine = supabase_engine

    if not CSV_PATH.is_file():
        raise SystemExit(f"CSV not found: {CSV_PATH}")

    SQLModel.metadata.create_all(engine)

    df = load_incidents(CSV_PATH)
    inserted = 0
    skipped_duplicate = 0
    skipped_invalid = 0
    invalid_rules: Counter[str] = Counter()

    with Session(engine) as session:
        for _, row in df.iterrows():
            csv_incident_id = str(row.get("incident_id", "")).strip()
            violations = validate_record(row)
            if violations:
                skipped_invalid += 1
                for rule in violations:
                    invalid_rules[RULE_LABELS[rule.value]] += 1
                continue

            existing = session.exec(
                select(Incident).where(Incident.incident_id == csv_incident_id)
            ).first()
            if existing is not None:
                skipped_duplicate += 1
                continue

            category = str(row.get("category", "")).strip()
            clinic_id = str(row.get("clinic_id", "")).strip()
            csv_status = str(row.get("status", "")).strip()
            status = CSV_STATUS_MAP.get(csv_status, "open")
            created = _parse_date(str(row.get("date", "")))

            incident = Incident(
                title=_generate_title(category, clinic_id),
                description=str(row.get("description", "")).strip(),
                category=category,
                status=status,
                origin="customer",
                branch=clinic_id,
                incident_id=csv_incident_id,
                created_at=created,
                updated_at=created,
            )
            session.add(incident)
            inserted += 1

        session.commit()

    return inserted, skipped_duplicate, skipped_invalid, invalid_rules


def main() -> None:
    inserted, dupes, invalid, rules = seed_incidents()

    if inserted > 0:
        print(f"Inserted {inserted} incident(s).")
        if dupes:
            print(f"Skipped {dupes} duplicate(s).")
        if invalid:
            print(f"Skipped {invalid} invalid CSV row(s).")
            print("Invalid row breakdown:")
            for label, count in sorted(rules.items()):
                print(f"  {label}: {count}")
        return

    if dupes > 0:
        print(f"Incident seed already applied — {dupes} incident(s) in database, 0 new inserts.")
        if invalid:
            print(f"({invalid} CSV rows are excluded by validation and were not stored.)")
        return

    print("Inserted 0 incident(s).")
    if invalid:
        print(f"Skipped {invalid} invalid CSV row(s).")
        print("Invalid row breakdown:")
        for label, count in sorted(rules.items()):
            print(f"  {label}: {count}")


if __name__ == "__main__":
    main()
