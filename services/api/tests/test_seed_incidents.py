from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest
from healthcore_incidents import load_incidents, validate_record
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.domains.incidents import models as incident_models  # noqa: F401
from app.domains.incidents.models import Incident

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.seed_incidents import CSV_PATH, seed_incidents  # noqa: E402

CSV_FIXTURE = (
    REPO_ROOT
    / "memory-bank/references/centralized_incident_manager_ai_plan/incidents-healthcore.csv"
)


def test_csv_validation_counts_expected_rows() -> None:
    df = load_incidents(CSV_FIXTURE)
    valid = 0
    invalid = 0
    for _, row in df.iterrows():
        if validate_record(row):
            invalid += 1
        else:
            valid += 1

    assert len(df) == 100
    assert valid == 94
    assert invalid == 6


def test_seed_incidents_is_idempotent() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    first_inserted, first_dupes, first_invalid, _ = seed_incidents(engine=engine)
    second_inserted, second_dupes, second_invalid, _ = seed_incidents(engine=engine)

    assert first_inserted == 94
    assert first_invalid == 6
    assert first_dupes == 0
    assert second_inserted == 0
    assert second_dupes == 94
    assert second_invalid == 6

    with Session(engine) as session:
        incidents = session.exec(select(Incident)).all()
        assert len(incidents) == 94
        assert all(incident.origin == "customer" for incident in incidents)


def test_seed_reports_invalid_rules() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    inserted, dupes, invalid, rules = seed_incidents(engine=engine)

    assert inserted == 94
    assert dupes == 0
    assert invalid == 6
    assert rules["Invalid or missing clinic_id"] == 1
    assert rules["Country/clinic mismatch"] == 1
    assert rules["Invalid or missing category"] == 1
    assert rules["Empty description"] == 1
    assert rules["Missing patient_id"] == 1
    assert rules["Closed case, no score"] == 1


def test_csv_path_matches_fixture() -> None:
    assert CSV_PATH == CSV_FIXTURE
