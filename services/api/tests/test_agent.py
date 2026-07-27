"""HTTP contract tests for POST /api/v1/agent/query."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.domains.agent.nodes import AGENT_NO_CONTEXT_ANSWER, EMPTY_QUESTION_ANSWER
from app.main import app
from data.pipelines.rag import RagConfigError
from data.process.rag import EmbeddingError

_RAG_ONLY_INTENT = {
    "use_rag": True,
    "use_incident": False,
    "use_inventory": False,
    "incident_id": None,
    "product_hint": None,
    "reasoning": "test stub",
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    from app.core import config

    config.settings = config.Settings()
    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client: TestClient) -> str:
    email = "agent-tester@healthcore.example"
    password = "SecurePass1!"
    body = {"email": email, "password": password, "name": "Agent Tester"}
    client.post("/api/v1/auth/register", json=body)
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_agent_query_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/agent/query", json={"question": "hello"})
    assert response.status_code in (401, 403)


def test_empty_question_returns_200(client: TestClient) -> None:
    token = _register_and_login(client)
    response = client.post(
        "/api/v1/agent/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "  "},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == EMPTY_QUESTION_ANSWER
    assert body["trace_id"].startswith("run-")
    assert body["sources"] == []


def test_no_context_path(client: TestClient) -> None:
    token = _register_and_login(client)
    with (
        patch(
            "app.domains.agent.nodes.classifier_fn",
            side_effect=lambda q: dict(_RAG_ONLY_INTENT),
        ),
        patch("app.domains.agent.nodes.retrieve", return_value=[]),
    ):
        response = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "What is the capital of Mars?"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == AGENT_NO_CONTEXT_ANSWER
    assert body["sources"] == []
    assert body["trace_id"].startswith("run-")


def test_happy_path_shape(client: TestClient) -> None:
    token = _register_and_login(client)
    hits = [
        {
            "source_document": "appointment-policy",
            "section": "Fees",
            "text": "Fee is 50 USD.",
            "score": 0.91,
        }
    ]
    with (
        patch(
            "app.domains.agent.nodes.classifier_fn",
            side_effect=lambda q: dict(_RAG_ONLY_INTENT),
        ),
        patch("app.domains.agent.nodes.retrieve", return_value=hits),
        patch(
            "app.domains.agent.nodes.generate_answer",
            return_value="The late cancellation fee is 50 USD.",
        ),
    ):
        response = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "cancellation fee?"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "50 USD" in body["answer"]
    assert body["sources"]
    assert body["sources"][0]["source_document"] == "appointment-policy"
    assert body["trace_id"].startswith("run-")
    assert body["sources_used"] == ["rag"]


def test_embedding_error_maps_to_502(client: TestClient) -> None:
    token = _register_and_login(client)
    with (
        patch(
            "app.domains.agent.nodes.classifier_fn",
            side_effect=lambda q: dict(_RAG_ONLY_INTENT),
        ),
        patch(
            "app.domains.agent.nodes.retrieve",
            side_effect=EmbeddingError("embed failed"),
        ),
    ):
        response = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Do you take Medicaid?"},
        )
    assert response.status_code == 502
    assert "stack" not in response.text.lower()
    assert "traceback" not in response.text.lower()
    assert "unavailable" in response.json()["detail"].lower()


def test_rag_config_error_maps_to_503(client: TestClient) -> None:
    token = _register_and_login(client)
    with (
        patch(
            "app.domains.agent.nodes.classifier_fn",
            side_effect=lambda q: dict(_RAG_ONLY_INTENT),
        ),
        patch(
            "app.domains.agent.nodes.retrieve",
            side_effect=RagConfigError("bad config"),
        ),
    ):
        response = client.post(
            "/api/v1/agent/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Do you take Medicaid?"},
        )
    assert response.status_code == 503
    assert "traceback" not in response.text.lower()
