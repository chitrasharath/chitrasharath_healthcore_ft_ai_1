from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app.core import db as core_db
from app.core.config import settings
from app.domains.auth import reset_tokens, token
from app.domains.auth.schemas import UserCreate, UserUpdate
from app.domains.auth.token import ALGORITHM, InvalidResetTokenError, RESET_TOKEN_PURPOSE
from app.domains.users import service as users_service
from app.domains.users import store as users_store
from app.main import app

VALID_USER = {"email": "alice@example.com", "password": "password123"}
NEW_PASSWORD = "newpassword123"
FORGOT_PASSWORD_MESSAGE = "If that address is registered, you will receive a reset link shortly."
INVALID_RESET_TOKEN_MESSAGE = "Invalid or expired reset token."


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path) -> None:
    db_path = tmp_path / "auth_test.json"
    core_db.reset_db(db_path)
    users_store.clear_all()
    reset_tokens.clear_all()


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
    # Seed a pre-migration row (no name field) instead of using register.
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
    # Negative TTL mints a token that is already expired when decoded.
    settings.jwt_expire_minutes = -1
    try:
        expired = token.create_access_token(1)
    finally:
        settings.jwt_expire_minutes = original
    response = client.get("/api/v1/auth/me", headers=auth_header(expired))
    assert response.status_code == 401


def _create_expired_reset_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=-1)
    payload = {"sub": str(user_id), "exp": expire, "purpose": RESET_TOKEN_PURPOSE}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def test_forgot_password_unknown_email_returns_generic_message(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == FORGOT_PASSWORD_MESSAGE


def test_forgot_password_known_email_returns_generic_message(client: TestClient, capsys) -> None:
    register_user(client)
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": VALID_USER["email"]},
    )
    assert response.status_code == 200
    assert response.json()["message"] == FORGOT_PASSWORD_MESSAGE
    captured = capsys.readouterr()
    assert "Password reset link for alice@example.com:" in captured.out
    assert "/reset-password?token=" in captured.out


def test_reset_password_valid_token_updates_password(client: TestClient) -> None:
    register_user(client)
    reset_token = token.create_reset_token(1)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password has been reset successfully."

    old_login = client.post("/api/v1/auth/login", json=VALID_USER)
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": VALID_USER["email"], "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200


def test_reset_password_reused_token_returns_400(client: TestClient) -> None:
    register_user(client)
    reset_token = token.create_reset_token(1)
    first = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": NEW_PASSWORD},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "anotherpass1"},
    )
    assert second.status_code == 400
    assert second.json()["detail"] == INVALID_RESET_TOKEN_MESSAGE


def test_reset_password_invalid_token_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-valid-token", "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_RESET_TOKEN_MESSAGE


def test_reset_password_expired_token_returns_400(client: TestClient) -> None:
    register_user(client)
    expired = _create_expired_reset_token(1)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": expired, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_RESET_TOKEN_MESSAGE


def test_reset_password_access_token_wrong_purpose_returns_400(client: TestClient) -> None:
    register_user(client)
    access_token = token.create_access_token(1)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": access_token, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_RESET_TOKEN_MESSAGE


def test_reset_password_short_password_returns_422(client: TestClient) -> None:
    register_user(client)
    reset_token = token.create_reset_token(1)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "short"},
    )
    assert response.status_code == 422


def test_put_user_not_found_returns_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    token_value = register_user(client).json()["access_token"]
    user_doc = users_store.get_by_id(1)
    assert user_doc is not None
    lookup_count = {"n": 0}

    # Router checks ownership (get_by_id #1) before not-found (get_by_id #2); fail only the second lookup.
    def fake_get_by_id(user_id: int) -> dict | None:
        if user_id != 1:
            return None
        lookup_count["n"] += 1
        return user_doc if lookup_count["n"] == 1 else None

    monkeypatch.setattr(users_store, "get_by_id", fake_get_by_id)

    response = client.put(
        "/api/v1/users/1",
        json={"name": "Ghost"},
        headers=auth_header(token_value),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_put_user_duplicate_email_returns_422(client: TestClient) -> None:
    register_user(client)
    client.post(
        "/api/v1/users",
        json={"email": "bob@example.com", "password": "password123"},
    )
    alice_token = client.post("/api/v1/auth/login", json=VALID_USER).json()["access_token"]
    response = client.put(
        "/api/v1/users/1",
        json={"email": "bob@example.com"},
        headers=auth_header(alice_token),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Email already registered"


def test_reset_password_user_deleted_after_token_issued_returns_400(client: TestClient) -> None:
    register_user(client)
    reset_token = token.create_reset_token(1)
    users_store.delete_user(1)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_RESET_TOKEN_MESSAGE


def test_forgot_password_sends_email_when_api_key_set(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_user(client)
    # conftest forces EMAIL_API_KEY="" for stdout fallback; override to exercise Resend path.
    monkeypatch.setattr(settings, "email_api_key", "re_test_key")

    with patch("app.domains.auth.reset_service.resend.Emails.send") as mock_send:
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": VALID_USER["email"]},
        )

    assert response.status_code == 200
    assert response.json()["message"] == FORGOT_PASSWORD_MESSAGE
    mock_send.assert_called_once()
    payload = mock_send.call_args[0][0]
    assert payload["to"] == [VALID_USER["email"]]
    assert "/reset-password?token=" in payload["text"]


def test_decode_reset_token_missing_subject_returns_error() -> None:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    # Valid signature and purpose, but missing sub — must not be accepted as a reset token.
    raw = jwt.encode(
        {"purpose": RESET_TOKEN_PURPOSE, "exp": expire},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(InvalidResetTokenError):
        token.decode_reset_token(raw)


def test_decode_access_token_missing_subject_returns_401() -> None:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    raw = jwt.encode({"exp": expire}, settings.secret_key, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        token.decode_access_token(raw)
    assert exc_info.value.status_code == 401


def test_to_user_response_string_created_at() -> None:
    # TinyDB may persist created_at as an ISO string rather than a datetime object.
    result = users_service.to_user_response(
        {
            "id": 1,
            "email": "test@example.com",
            "name": "Test User",
            "is_active": True,
            "hashed_password": "hashed",
            "created_at": "2025-01-01T00:00:00Z",
        }
    )
    assert result.created_at.year == 2025
    assert result.created_at.month == 1
    assert result.created_at.day == 1


def test_update_user_email_same_as_own_succeeds() -> None:
    created = users_service.create_user(
        UserCreate(email="same@example.com", password="password123")
    )
    # Same address as current row must not trigger DuplicateEmailError.
    updated = users_service.update_user(created.id, UserUpdate(email="same@example.com"))
    assert updated.email == "same@example.com"
