from pathlib import Path
import asyncio
import csv
from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.domains.reporting.incidents.router import analyze_incidents
from app.main import app
from tests.auth_helpers import auth_headers

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2].parent
    / "uis"
    / "incident_analyzer"
    / "incidents-healthcore.csv"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def bearer(client: TestClient) -> dict[str, str]:
    return auth_headers(client)


def test_analyze_without_token_returns_401(client: TestClient) -> None:
    with FIXTURE_PATH.open("rb") as handle:
        response = client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
        )
    assert response.status_code == 401


def test_analyze_incidents_healthcore_csv(client: TestClient, bearer: dict[str, str]) -> None:
    with FIXTURE_PATH.open("rb") as handle:
        response = client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
            headers=bearer,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["totals"]["total"] == 100
    assert data["totals"]["valid"] == 94
    assert data["totals"]["invalid"] == 6
    assert data["satisfaction"]["average"] == 3.58
    assert len(data["by_category"]) > 0
    assert len(data["by_status"]) > 0
    assert len(data["by_country"]) > 0
    assert len(data["invalid_breakdown"]) > 0
    assert data["satisfaction"]["scored_cases"] > 0
    assert "PAT-" not in response.text


def test_export_requires_prior_analysis(client: TestClient, bearer: dict[str, str]) -> None:
    from app.domains.reporting.incidents.store import last_analysis_store

    last_analysis_store._current = None
    response = client.get("/api/v1/incidents/results/export", headers=bearer)
    assert response.status_code == 404


def test_export_after_analyze(client: TestClient, bearer: dict[str, str]) -> None:
    with FIXTURE_PATH.open("rb") as handle:
        client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
            headers=bearer,
        )

    response = client.get("/api/v1/incidents/results/export", headers=bearer)
    assert response.status_code == 200
    assert "total_records" in response.text
    assert "PAT-" not in response.text


def test_analyze_no_filename_returns_400() -> None:
    upload = MagicMock()
    upload.filename = ""
    upload.read = AsyncMock(return_value=b"id,status\n1,open\n")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(analyze_incidents(upload))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "A CSV file is required."


def test_analyze_invalid_csv_content_returns_400(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/incidents/analyze",
        files={"file": ("bad.csv", b"", "text/csv")},
        headers=bearer,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."


def test_analyze_unexpected_error_returns_400(
    client: TestClient,
    bearer: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_content: bytes, _filename: str):
        raise RuntimeError("analysis failed")

    monkeypatch.setattr(
        "app.domains.reporting.incidents.router.analyze_incidents_csv",
        boom,
    )
    response = client.post(
        "/api/v1/incidents/analyze",
        files={"file": ("incidents.csv", b"id,status\n1,open\n", "text/csv")},
        headers=bearer,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to analyze incidents file."


def test_analyze_valid_csv_returns_analysis(client: TestClient, bearer: dict[str, str]) -> None:
    """SPECS §3a — validates full analysis response schema (extends healthcore fixture test)."""
    with FIXTURE_PATH.open("rb") as handle:
        response = client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
            headers=bearer,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["source_filename"] == "incidents-healthcore.csv"
    assert "analyzed_at" in data
    assert isinstance(data["totals"], dict)
    assert isinstance(data["satisfaction"]["distribution"], list)


def test_export_csv_content_format(client: TestClient, bearer: dict[str, str]) -> None:
    with FIXTURE_PATH.open("rb") as handle:
        client.post(
            "/api/v1/incidents/analyze",
            files={"file": ("incidents-healthcore.csv", handle, "text/csv")},
            headers=bearer,
        )

    response = client.get("/api/v1/incidents/results/export", headers=bearer)
    assert response.status_code == 200

    reader = csv.DictReader(StringIO(response.text))
    assert reader.fieldnames == ["metric", "value", "percentage"]
    rows = list(reader)
    assert len(rows) > 0
    metrics = {row["metric"] for row in rows}
    assert "total_records" in metrics
