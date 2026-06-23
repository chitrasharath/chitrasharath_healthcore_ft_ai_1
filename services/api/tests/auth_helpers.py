from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def auth_headers(client: TestClient) -> dict[str, str]:
    email = f"auth-test-{uuid.uuid4().hex}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "API Test"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
