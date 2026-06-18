from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2].parent
    / "uis"
    / "incident_analyzer"
    / "incidents-healthcore.csv"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_analyze_incidents_healthcore_csv(client: TestClient) -> None:
    with FIXTURE_PATH.open("rb") as handle:
        response = client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["totals"]["total"] == 100
    assert data["totals"]["valid"] == 94
    assert data["totals"]["invalid"] == 6
    assert data["satisfaction"]["average"] == 3.58
    assert "PAT-" not in response.text


def test_export_requires_prior_analysis(client: TestClient) -> None:
    from app.domains.reporting.incidents.store import last_analysis_store

    last_analysis_store._current = None
    response = client.get("/api/v1/incidents/results/export")
    assert response.status_code == 404


def test_export_after_analyze(client: TestClient) -> None:
    with FIXTURE_PATH.open("rb") as handle:
        client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
        )

    response = client.get("/api/v1/incidents/results/export")
    assert response.status_code == 200
    assert "total_records" in response.text
    assert "PAT-" not in response.text
