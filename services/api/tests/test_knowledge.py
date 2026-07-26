"""API tests for knowledge query + feedback."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.domains.knowledge.pii import redact_pii
from app.main import app
from data.pipelines.rag import FALLBACK_ANSWER, QueryResult


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    feedback = tmp_path / "feedback.jsonl"
    monkeypatch.setenv("FEEDBACK_PATH", str(feedback))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    from app.core import config

    config.settings = config.Settings()
    with TestClient(app) as test_client:
        yield test_client, feedback


def _register_and_login(client: TestClient) -> str:
    email = "rag-tester@healthcore.example"
    password = "SecurePass1!"
    body = {"email": email, "password": password, "name": "Rag Tester"}
    client.post("/api/v1/auth/register", json=body)
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_query_writes_interaction_and_feedback_roundtrip(client) -> None:
    test_client, feedback_path = client
    token = _register_and_login(test_client)
    headers = {"Authorization": f"Bearer {token}"}

    fake = QueryResult(
        answer="Per our appointment policy, the fee is 50 USD.",
        sources=[
            {
                "source_document": "appointment-policy",
                "section": "Cancellation policy",
                "score": 0.9,
            }
        ],
        context_texts=["Cancelling less than 24 hours: 50 USD"],
        assembled_prompt="SYSTEM+CONTEXT",
        model="test-model",
        temperature=0.15,
    )

    with patch("app.domains.knowledge.service.rag_query", return_value=fake):
        response = test_client.post(
            "/api/v1/knowledge/query",
            headers=headers,
            json={"question": "cancellation fee?"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"]
    assert body["sources"]
    query_id = body["query_id"]

    lines = feedback_path.read_text(encoding="utf-8").strip().splitlines()
    interaction = json.loads(lines[0])
    assert interaction["record_type"] == "interaction"
    assert interaction["schema_version"] == 1
    assert interaction["context_texts"]
    assert interaction["generation"]["model"] == "test-model"
    assert interaction["session_id"] is None
    assert interaction["parent_query_id"] is None

    fb = test_client.post(
        "/api/v1/knowledge/feedback",
        headers=headers,
        json={"query_id": query_id, "rating": "up"},
    )
    assert fb.status_code == 200
    assert fb.json()["status"] == "recorded"

    missing = test_client.post(
        "/api/v1/knowledge/feedback",
        headers=headers,
        json={"query_id": "00000000-0000-0000-0000-000000000000", "rating": "down"},
    )
    assert missing.status_code == 404


def test_query_requires_auth(client) -> None:
    test_client, _ = client
    response = test_client.post(
        "/api/v1/knowledge/query",
        json={"question": "hello"},
    )
    assert response.status_code in (401, 403)


def test_redact_pii() -> None:
    text = "Patient MRN: MRN-123456 emailed a@b.co"
    redacted = redact_pii(text) or ""
    assert "MRN-123456" not in redacted
    assert "a@b.co" not in redacted
    assert "[REDACTED" in redacted


def test_fallback_response_shape(client) -> None:
    test_client, _ = client
    token = _register_and_login(test_client)
    fake = QueryResult(answer=FALLBACK_ANSWER, sources=[])
    with patch("app.domains.knowledge.service.rag_query", return_value=fake):
        response = test_client.post(
            "/api/v1/knowledge/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Do you offer dental cleanings?"},
        )
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert response.json()["answer"] == FALLBACK_ANSWER
