import asyncio

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app, global_exception_handler
from tests.auth_helpers import auth_headers


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_global_exception_handler_returns_generic_500() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/health", "headers": []})
    response = asyncio.run(
        global_exception_handler(
            request,
            RuntimeError("secret internal traceback /var/app/db.json"),
        )
    )

    assert response.status_code == 500
    assert response.body == b'{"detail":"An unexpected error occurred. Please try again later."}'
    body = response.body.decode()
    assert "traceback" not in body.lower()
    assert "secret" not in body


def test_analyze_non_utf8_csv_returns_400(client: TestClient) -> None:
    bearer = auth_headers(client)
    invalid_utf8 = b"\xff\xfe" + b"col\nval\n"

    response = client.post(
        "/api/v1/incidents/analyze",
        files={"file": ("bad.csv", invalid_utf8, "text/csv")},
        headers=bearer,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File is not valid UTF-8 text."
    assert "Traceback" not in response.text
