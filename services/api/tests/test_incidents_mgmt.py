from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.db import get_supabase_db
from app.domains.incidents import models as incident_models  # noqa: F401
from app.domains.inventory import models as inventory_models  # noqa: F401
from app.main import app
from tests.auth_helpers import auth_headers

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="incidents_session")
def incidents_session_fixture():
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(incidents_session):
    def override():
        with Session(incidents_session) as session:
            yield session

    app.dependency_overrides[get_supabase_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def bearer(client: TestClient) -> dict[str, str]:
    return auth_headers(client)


VALID_INCIDENT = {
    "title": "Patient registration error at Austin North",
    "description": "Patient registration data contains error from onboarding process.",
    "category": "ADMINISTRATIVE",
    "origin": "branch",
    "branch": "US-TX-02",
}


def test_post_incident_creates_open_status(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.post("/api/v1/incidents", json=VALID_INCIDENT, headers=bearer)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "open"
    assert data["title"] == VALID_INCIDENT["title"]
    assert "id" in data
    assert "incident_id" not in data


def test_post_missing_title(client: TestClient, bearer: dict[str, str]) -> None:
    body = {**VALID_INCIDENT}
    del body["title"]
    response = client.post("/api/v1/incidents", json=body, headers=bearer)
    assert response.status_code == 400
    assert response.json()["detail"] == "Title is required."


def test_post_empty_title(client: TestClient, bearer: dict[str, str]) -> None:
    body = {**VALID_INCIDENT, "title": "   "}
    response = client.post("/api/v1/incidents", json=body, headers=bearer)
    assert response.status_code == 400
    assert response.json()["detail"] == "Title cannot be empty."


def test_post_empty_description(client: TestClient, bearer: dict[str, str]) -> None:
    body = {**VALID_INCIDENT, "description": ""}
    response = client.post("/api/v1/incidents", json=body, headers=bearer)
    assert response.status_code == 400
    assert response.json()["detail"] == "Description cannot be empty."


def test_post_invalid_category(client: TestClient, bearer: dict[str, str]) -> None:
    body = {**VALID_INCIDENT, "category": "UNKNOWN"}
    response = client.post("/api/v1/incidents", json=body, headers=bearer)
    assert response.status_code == 400
    assert "Invalid category 'UNKNOWN'" in response.json()["detail"]


def test_post_invalid_branch(client: TestClient, bearer: dict[str, str]) -> None:
    body = {**VALID_INCIDENT, "branch": "XX-BAD"}
    response = client.post("/api/v1/incidents", json=body, headers=bearer)
    assert response.status_code == 400
    assert "Invalid branch" in response.json()["detail"]


def test_get_list_empty(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.get("/api/v1/incidents", headers=bearer)
    assert response.status_code == 200
    assert response.json() == []


def test_get_summary_empty(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.get("/api/v1/incidents/summary", headers=bearer)
    assert response.status_code == 200
    data = response.json()
    assert data["by_status"]["open"] == 0
    assert data["by_category"]["BILLING"] == 0
    assert data["by_origin"]["customer"] == 0
    assert data["by_branch"] == {}


def test_get_unknown_id_returns_404(client: TestClient, bearer: dict[str, str]) -> None:
    response = client.get("/api/v1/incidents/999", headers=bearer)
    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found."


def test_patch_valid_transition(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/incidents", json=VALID_INCIDENT, headers=bearer).json()
    response = client.patch(
        f"/api/v1/incidents/{created['id']}/status",
        json={"status": "in_progress"},
        headers=bearer,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_patch_final_state_rejected(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/incidents", json=VALID_INCIDENT, headers=bearer).json()
    client.patch(
        f"/api/v1/incidents/{created['id']}/status",
        json={"status": "in_progress"},
        headers=bearer,
    )
    client.patch(
        f"/api/v1/incidents/{created['id']}/status",
        json={"status": "resolved"},
        headers=bearer,
    )
    response = client.patch(
        f"/api/v1/incidents/{created['id']}/status",
        json={"status": "open"},
        headers=bearer,
    )
    assert response.status_code == 400
    assert "final state" in response.json()["detail"]


def test_patch_invalid_path(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/incidents", json=VALID_INCIDENT, headers=bearer).json()
    response = client.patch(
        f"/api/v1/incidents/{created['id']}/status",
        json={"status": "resolved"},
        headers=bearer,
    )
    assert response.status_code == 400
    assert "Valid transitions: in_progress, discarded" in response.json()["detail"]


def test_list_filter_by_status(client: TestClient, bearer: dict[str, str]) -> None:
    client.post("/api/v1/incidents", json=VALID_INCIDENT, headers=bearer)
    response = client.get("/api/v1/incidents?status=open", headers=bearer)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_unauthenticated_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/incidents")
    assert response.status_code == 401


def test_patch_incident_updates_fields(client: TestClient, bearer: dict[str, str]) -> None:
    created = client.post("/api/v1/incidents", json=VALID_INCIDENT, headers=bearer).json()
    updated_body = {**VALID_INCIDENT, "title": "Updated incident title"}
    response = client.patch(
        f"/api/v1/incidents/{created['id']}",
        json=updated_body,
        headers=bearer,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated incident title"
    assert data["updated_at"] != data["created_at"] or data["title"] != created["title"]
