from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import db as core_db
from app.domains.telemetry import analysis as telemetry_analysis
from app.domains.telemetry import router as telemetry_router
from app.domains.telemetry.cache import clear_report_cache
from app.domains.telemetry.mapper import map_event_to_row
from app.domains.telemetry.models import TelemetryEventRow
from app.domains.telemetry.schemas import TelemetryEvent
from app.domains.users import store as users_store
from tests.telemetry_helpers import sample_event

VALID_USER = {"email": "alice@example.com", "password": "password123"}

WINDOW_START = datetime(2026, 7, 8, 0, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)
EVENT_TS = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated_auth_db(tmp_path: Path) -> None:
    core_db.reset_db(tmp_path / "telemetry_report_auth.json")
    users_store.clear_all()
    clear_report_cache()


@pytest.fixture(name="report_token")
def report_token_fixture(telemetry_client: TestClient) -> str:
    telemetry_client.post("/api/v1/auth/register", json=VALID_USER)
    response = telemetry_client.post("/api/v1/auth/login", json=VALID_USER)
    return response.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _insert_row(
    session_engine,
    event_type: str,
    *,
    timestamp: datetime = EVENT_TS,
    **properties: object,
) -> None:
    event = TelemetryEvent.model_validate(
        sample_event(event_type, event_id=f"evt-{event_type}", **properties),
    )
    row = map_event_to_row(event)
    row.timestamp = timestamp
    with Session(session_engine) as session:
        session.add(row)
        session.commit()


def _seed_report_fixtures(session_engine) -> None:
    _insert_row(
        session_engine,
        "supply_consumption_created",
        supply_id=1,
        quantity=10,
        consumption_type="clinical_use",
        clinic_id=1,
        jurisdiction="us",
    )
    _insert_row(
        session_engine,
        "supply_consumption_created",
        supply_id=2,
        quantity=5,
        consumption_type="expiry_waste",
        clinic_id=1,
        jurisdiction="us",
    )
    _insert_row(
        session_engine,
        "supply_consumption_failed",
        error_code="INSUFFICIENT_STOCK",
        supply_id=1,
        clinic_id=1,
        jurisdiction="us",
    )
    _insert_row(
        session_engine,
        "user_login_succeeded",
    )
    _insert_row(
        session_engine,
        "user_login_failed",
        reason="invalid_credentials",
    )
    _insert_row(
        session_engine,
        "supply_consumption_form_abandoned",
        clinic_id=1,
        had_supply_selected=True,
        had_quantity=False,
        jurisdiction="us",
        abandon_trigger="navigation",
    )
    _insert_row(
        session_engine,
        "supply_consumption_form_abandoned",
        clinic_id=1,
        had_supply_selected=False,
        had_quantity=True,
        abandon_trigger="tab_hidden",
    )
    _insert_row(
        session_engine,
        "incident_list_filter_applied",
        filter_dimension="status",
        filter_value="open",
        active_filter_count=1,
    )


def test_report_requires_auth(telemetry_client: TestClient) -> None:
    response = telemetry_client.get("/api/v1/telemetry/raw-report")
    assert response.status_code == 401


def test_report_returns_four_metric_keys(
    telemetry_client: TestClient,
    telemetry_session,
    report_token: str,
) -> None:
    _seed_report_fixtures(telemetry_session)

    response = telemetry_client.get(
        "/api/v1/telemetry/raw-report",
        params={
            "start_date": WINDOW_START.isoformat(),
            "end_date": WINDOW_END.isoformat(),
        },
        headers=_auth_header(report_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert "period" in body
    assert set(body["metrics"]) == {
        "consumption_volume_per_day",
        "waste_rate_per_day",
        "insufficient_stock_failures_per_day",
        "auth_failure_rate",
    }


def test_kpi_metrics_exclude_v1_1_noise(
    telemetry_client: TestClient,
    telemetry_session,
    report_token: str,
) -> None:
    _seed_report_fixtures(telemetry_session)

    response = telemetry_client.get(
        "/api/v1/telemetry/raw-report",
        params={
            "start_date": WINDOW_START.isoformat(),
            "end_date": WINDOW_END.isoformat(),
        },
        headers=_auth_header(report_token),
    )

    metrics = response.json()["metrics"]
    assert metrics["consumption_volume_per_day"] == [
        {"date": "2026-07-08", "clinic_id": 1, "jurisdiction": "us", "count": 2},
    ]
    assert metrics["waste_rate_per_day"] == [
        {"date": "2026-07-08", "jurisdiction": "us", "waste_rate": 0.5, "total": 2},
    ]
    assert metrics["insufficient_stock_failures_per_day"] == [
        {
            "date": "2026-07-08",
            "clinic_id": 1,
            "jurisdiction": "us",
            "supply_id": 1,
            "count": 1,
            "attempts": 2,
            "rejection_rate": 0.5,
        },
        {
            "date": "2026-07-08",
            "clinic_id": 1,
            "jurisdiction": "us",
            "supply_id": 2,
            "count": 0,
            "attempts": 1,
            "rejection_rate": 0.0,
        },
    ]
    assert metrics["auth_failure_rate"] == [
        {"date": "2026-07-08", "failed": 1, "succeeded": 1, "failure_rate": 0.5},
    ]


def test_report_empty_window_returns_empty_arrays(
    telemetry_client: TestClient,
    report_token: str,
) -> None:
    response = telemetry_client.get(
        "/api/v1/telemetry/raw-report",
        params={
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-01-02T00:00:00Z",
        },
        headers=_auth_header(report_token),
    )

    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["consumption_volume_per_day"] == []
    assert metrics["waste_rate_per_day"] == []
    assert metrics["insufficient_stock_failures_per_day"] == []
    assert metrics["auth_failure_rate"] == []


def test_report_uses_cache_within_ttl(
    telemetry_client: TestClient,
    telemetry_session,
    report_token: str,
) -> None:
    _seed_report_fixtures(telemetry_session)
    params = {
        "start_date": WINDOW_START.isoformat(),
        "end_date": WINDOW_END.isoformat(),
    }
    headers = _auth_header(report_token)

    with patch.object(telemetry_router, "build_metrics", wraps=telemetry_router.build_metrics) as mocked:
        first = telemetry_client.get("/api/v1/telemetry/raw-report", params=params, headers=headers)
        second = telemetry_client.get("/api/v1/telemetry/raw-report", params=params, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert mocked.call_count == 1


def test_auth_failure_rate_ignores_jurisdiction(
    telemetry_session,
) -> None:
    _insert_row(
        telemetry_session,
        "user_login_succeeded",
        jurisdiction="uk",
    )
    _insert_row(
        telemetry_session,
        "user_login_failed",
        reason="invalid_credentials",
        jurisdiction="uk",
    )

    with Session(telemetry_session) as session:
        rows = telemetry_analysis.auth_failure_rate(session, WINDOW_START, WINDOW_END)

    assert rows == [
        {"date": "2026-07-08", "failed": 1, "succeeded": 1, "failure_rate": 0.5},
    ]
