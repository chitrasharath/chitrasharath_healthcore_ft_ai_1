from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import db as core_db
from app.core.config import settings
from app.domains.auth import token
from app.domains.users import store as users_store
from app.main import app

VALID_USER = {"email": "alice@example.com", "password": "password123"}


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path) -> None:
    db_path = tmp_path / "auth_test.json"
    core_db.reset_db(db_path)
    users_store.clear_all()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register_user(client: TestClient, payload: dict | None = None) -> dict:
    body = payload or VALID_USER
    response = client.post("/api/v1/auth/register", json=body)
    return response


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_valid_returns_token(client: TestClient) -> None:
    response = register_user(client)
    assert response.status_code == 201
    assert "access_token" in response.json()


def test_register_duplicate_email_returns_422(client: TestClient) -> None:
    register_user(client)
    response = register_user(client)
    assert response.status_code == 422
    assert response.json()["detail"] == "Email already registered"


def test_register_short_password_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_valid_returns_token(client: TestClient) -> None:
    register_user(client)
    response = client.post("/api/v1/auth/login", json=VALID_USER)
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    register_user(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": VALID_USER["email"], "password": "wrongpass1"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_inactive_user_returns_401(client: TestClient) -> None:
    register_user(client)
    users_store.update_user(1, {"is_active": False})
    response = client.post("/api/v1/auth/login", json=VALID_USER)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_me_with_valid_token_returns_profile(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.get("/api/v1/auth/me", headers=auth_header(token_value))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == VALID_USER["email"]
    assert "hashed_password" not in data


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_header("not-a-valid-token"))
    assert response.status_code == 401


def test_me_inactive_user_returns_401(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    users_store.update_user(1, {"is_active": False})
    response = client.get("/api/v1/auth/me", headers=auth_header(token_value))
    assert response.status_code == 401


def test_me_deleted_user_returns_401(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    users_store.delete_user(1)
    response = client.get("/api/v1/auth/me", headers=auth_header(token_value))
    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


def test_create_user_valid_returns_profile(client: TestClient) -> None:
    response = client.post("/api/v1/users", json={"email": "carol@example.com", "password": "password123"})
    assert response.status_code == 201
    data = response.json()
    assert data["id"] >= 1
    assert data["email"] == "carol@example.com"
    assert data["is_active"] is True
    assert "created_at" in data
    assert "hashed_password" not in data


def test_list_users_with_token_returns_list(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.get("/api/v1/users", headers=auth_header(token_value))
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_list_users_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_get_user_without_token_returns_401(client: TestClient) -> None:
    register_user(client)
    response = client.get("/api/v1/users/1")
    assert response.status_code == 401


def test_get_user_by_id_with_token_returns_user(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.get("/api/v1/users/1", headers=auth_header(token_value))
    assert response.status_code == 200
    assert response.json()["email"] == VALID_USER["email"]


def test_get_user_unknown_id_returns_404(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.get("/api/v1/users/999", headers=auth_header(token_value))
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_put_own_user_returns_200(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.put(
        "/api/v1/users/1",
        json={"email": "alice.updated@example.com"},
        headers=auth_header(token_value),
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice.updated@example.com"


def test_put_short_password_returns_422(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.put(
        "/api/v1/users/1",
        json={"password": "short"},
        headers=auth_header(token_value),
    )
    assert response.status_code == 422


def test_put_without_token_returns_401(client: TestClient) -> None:
    register_user(client)
    response = client.put("/api/v1/users/1", json={"email": "alice.updated@example.com"})
    assert response.status_code == 401


def test_put_other_user_returns_403(client: TestClient) -> None:
    register_user(client)
    other = client.post(
        "/api/v1/users",
        json={"email": "other@example.com", "password": "password123"},
    )
    other_token = client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "password123"},
    ).json()["access_token"]
    response = client.put(
        "/api/v1/users/1",
        json={"email": "hacked@example.com"},
        headers=auth_header(other_token),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized"


def test_delete_user_returns_204(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.delete("/api/v1/users/1", headers=auth_header(token_value))
    assert response.status_code == 204


def test_delete_without_token_returns_401(client: TestClient) -> None:
    register_user(client)
    response = client.delete("/api/v1/users/1")
    assert response.status_code == 401


def test_delete_unknown_user_returns_404(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.delete("/api/v1/users/999", headers=auth_header(token_value))
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_register_with_name_returns_name_in_me(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "named@example.com", "password": "password123", "name": "Alice Smith"},
    )
    assert response.status_code == 201
    token_value = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers=auth_header(token_value))
    assert me.status_code == 200
    assert me.json()["name"] == "Alice Smith"


def test_legacy_user_without_name_returns_empty_string(client: TestClient) -> None:
    users_store.insert_user(
        {
            "email": "legacy@example.com",
            "hashed_password": "hashed",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    token_value = token.create_access_token(1)
    response = client.get("/api/v1/auth/me", headers=auth_header(token_value))
    assert response.status_code == 200
    assert response.json()["name"] == ""


def test_put_user_name_returns_updated_name(client: TestClient) -> None:
    token_value = register_user(client).json()["access_token"]
    response = client.put(
        "/api/v1/users/1",
        json={"name": "Updated Name"},
        headers=auth_header(token_value),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_expired_token_returns_401(client: TestClient) -> None:
    register_user(client)
    original = settings.jwt_expire_minutes
    settings.jwt_expire_minutes = -1
    try:
        expired = token.create_access_token(1)
    finally:
        settings.jwt_expire_minutes = original
    response = client.get("/api/v1/auth/me", headers=auth_header(expired))
    assert response.status_code == 401
