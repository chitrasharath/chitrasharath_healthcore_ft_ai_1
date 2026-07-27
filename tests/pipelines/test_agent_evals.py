"""Trace-based evals for the LangGraph support agent (Part 1 + tools).

Refresh the grounding fixture (eval 3a) after a live run by updating
`stub_answer` in tests/pipelines/fixtures/agent_grounding_response.json
with a real generate_answer output for the fixture question.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from app.domains.agent import nodes as agent_nodes
from app.domains.agent.graph import compiled_graph
from app.domains.agent.nodes import (
    AGENT_NO_CONTEXT_ANSWER,
    EMPTY_QUESTION_ANSWER,
    INCIDENT_FALLBACK,
)
from app.domains.agent.tools.incident import IncidentToolResult
from app.domains.agent.tools.inventory import InventoryToolResult
from data.pipelines.rag import FALLBACK_ANSWER

_FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "agent_grounding_response.json"
)
_GOLDEN_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "eval" / "test-queries.json"
)

_RAG_ONLY_INTENT = {
    "use_rag": True,
    "use_incident": False,
    "use_inventory": False,
    "incident_id": None,
    "product_hint": None,
    "reasoning": "stub rag",
}


def _load_fixture() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_faq_question() -> str:
    items = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    for item in items:
        if not item.get("should_abstain", True):
            return str(item["question"])
    raise AssertionError("No should_abstain=false item in test-queries.json")


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """True if needle appears in order (not necessarily contiguous) in haystack."""
    it = iter(haystack)
    return all(node in it for node in needle)


def run_agent(
    question: str,
    *,
    generate_fn=None,
    retrieve_fn=None,
    classifier_fn=None,
    auth_token: str | None = "test-token",
    run_incident_tool_fn=None,
    run_inventory_tool_fn=None,
    compose_generate_fn=None,
) -> dict:
    """Invoke compiled_graph once; optional seams for deterministic evals."""
    initial = {
        "question": question,
        "normalized_question": None,
        "auth_token": auth_token,
        "intent": None,
        "retrieved_context": None,
        "incident_result": None,
        "inventory_result": None,
        "answer": None,
        "sources": None,
        "sources_used": [],
        "trace_id": "run-" + uuid.uuid4().hex[:12],
        "trace_steps": [],
        "error": None,
    }
    config = {"configurable": {"thread_id": initial["trace_id"]}}

    with ExitStack() as stack:
        clf = classifier_fn if classifier_fn is not None else (
            lambda q: dict(_RAG_ONLY_INTENT)
        )
        stack.enter_context(patch.object(agent_nodes, "classifier_fn", clf))
        if generate_fn is not None:
            stack.enter_context(
                patch.object(
                    agent_nodes,
                    "generate_answer",
                    side_effect=lambda q, ctx, **kw: generate_fn(q, ctx),
                )
            )
        if compose_generate_fn is not None:
            stack.enter_context(
                patch.object(agent_nodes, "compose_generate_fn", compose_generate_fn)
            )
        if retrieve_fn is not None:
            stack.enter_context(
                patch.object(agent_nodes, "retrieve", side_effect=retrieve_fn)
            )
        if run_incident_tool_fn is not None:
            stack.enter_context(
                patch.object(
                    agent_nodes, "run_incident_tool", side_effect=run_incident_tool_fn
                )
            )
        if run_inventory_tool_fn is not None:
            stack.enter_context(
                patch.object(
                    agent_nodes, "run_inventory_tool", side_effect=run_inventory_tool_fn
                )
            )
        return compiled_graph.invoke(initial, config=config)


def _node_names(trace_steps) -> list[str]:
    return [step["node"] for step in trace_steps]


def test_compiled_graph_imports() -> None:
    assert compiled_graph is not None


def test_node_order_routing_with_stubbed_generation() -> None:
    question = _load_faq_question()
    hits = [
        {
            "source_document": "appointment-policy",
            "section": "Cancellation",
            "text": "Fee is 50 USD.",
            "score": 0.9,
        }
    ]

    def _fake_retrieve(q: str, **kwargs):
        return hits

    def _fake_generate(q, ctx, **kwargs):
        return "Stubbed grounded answer mentioning 50 USD."

    final = run_agent(question, generate_fn=_fake_generate, retrieve_fn=_fake_retrieve)
    nodes = _node_names(final["trace_steps"])
    assert _is_subsequence(
        ["classify", "retrieve", "gather", "compose"], nodes
    ), nodes
    assert "query" not in nodes
    assert "no_context" not in nodes
    assert final.get("error") in (None, "")
    assert final.get("answer")
    assert final.get("sources_used") == ["rag"]


def test_empty_question_error_path() -> None:
    final = run_agent("   ")
    nodes = _node_names(final["trace_steps"])
    assert "receive_question" in nodes
    assert "classify" not in nodes
    assert "compose" not in nodes
    assert final.get("error") == "empty_question"
    assert final.get("answer") == EMPTY_QUESTION_ANSWER


def test_grounding_via_fixture() -> None:
    """CI acceptance gate — no LLM key required."""
    fixture = _load_fixture()
    hits = fixture["stub_hits"]

    def _fake_retrieve(q: str, **kwargs):
        return hits

    def _fake_generate(q, ctx, **kwargs):
        return fixture["stub_answer"]

    final = run_agent(
        fixture["question"],
        generate_fn=_fake_generate,
        retrieve_fn=_fake_retrieve,
    )
    answer = final.get("answer") or ""
    assert answer.strip()
    assert answer != AGENT_NO_CONTEXT_ANSWER
    assert answer != FALLBACK_ANSWER
    for entity in fixture["expected_entities"]:
        assert entity.lower() in answer.lower(), entity
    source_docs = {s.get("source_document") for s in (final.get("sources") or [])}
    assert fixture["expected_source_document"] in source_docs


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY", "").strip(),
    reason="LLM_API_KEY unset — skip live grounding eval",
)
def test_grounding_live() -> None:
    fixture = _load_fixture()
    from data.process.rag import collection_is_populated, setup

    if not collection_is_populated():
        setup()

    # Live path: do not stub classifier (uses real LLM) — still ok for smoke.
    # Use real classifier_fn by passing through default_classifier_fn.
    from app.domains.agent.nodes import default_classifier_fn

    final = run_agent(fixture["question"], classifier_fn=default_classifier_fn)
    answer = final.get("answer") or ""
    assert answer.strip()
    assert answer != AGENT_NO_CONTEXT_ANSWER
    assert answer != FALLBACK_ANSWER
    assert any(e.lower() in answer.lower() for e in fixture["expected_entities"])
    source_docs = {s.get("source_document") for s in (final.get("sources") or [])}
    assert fixture["expected_source_document"] in source_docs


def test_resolves_with_incident_tool() -> None:
    """Eval 4 — route to incident tool only; answer contains status."""
    incident = {
        "id": 42,
        "title": "Wait time complaint",
        "description": "Patient waited too long",
        "category": "service",
        "status": "in_progress",
        "origin": "phone",
        "branch": "Austin",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-02T00:00:00",
    }

    def _clf(q: str) -> dict:
        return {
            "use_rag": False,
            "use_incident": True,
            "use_inventory": False,
            "incident_id": 42,
            "product_hint": None,
            "reasoning": "incident status",
        }

    def _incident_tool(inp, *, auth_token=None):
        assert inp.incident_id == 42
        assert auth_token == "test-token"
        return IncidentToolResult(ok=True, incident=incident)

    def _inventory_tool(inp, *, auth_token=None):
        raise AssertionError("inventory tool must not be called")

    def _retrieve(q: str, **kwargs):
        raise AssertionError("retrieve must not be called")

    def _compose(prompt: str) -> str:
        assert "in_progress" in prompt or "INCIDENT" in prompt
        return "Incident 42 is currently in_progress."

    final = run_agent(
        "What is the status of incident 42?",
        classifier_fn=_clf,
        run_incident_tool_fn=_incident_tool,
        run_inventory_tool_fn=_inventory_tool,
        retrieve_fn=_retrieve,
        compose_generate_fn=_compose,
    )
    nodes = _node_names(final["trace_steps"])
    assert final.get("sources_used") == ["incident_tool"]
    assert "rag" not in (final.get("sources_used") or [])
    assert _is_subsequence(
        ["classify", "incident_tool", "gather", "compose"], nodes
    ), nodes
    assert "retrieve" not in nodes
    assert "in_progress" in (final.get("answer") or "")


def test_resolves_with_rag_only() -> None:
    """Eval 5 — RAG path; tool HTTP / tool functions not called."""
    hits = [
        {
            "source_document": "insurance-coverage",
            "section": "Medicaid",
            "text": "We accept Medicaid in US clinics.",
            "score": 0.88,
        }
    ]
    incident_calls: list = []
    inventory_calls: list = []

    def _clf(q: str) -> dict:
        return dict(_RAG_ONLY_INTENT)

    def _incident_tool(inp, *, auth_token=None):
        incident_calls.append(inp)
        raise AssertionError("incident tool must not be called")

    def _inventory_tool(inp, *, auth_token=None):
        inventory_calls.append(inp)
        raise AssertionError("inventory tool must not be called")

    def _retrieve(q: str, **kwargs):
        return hits

    def _generate(q, ctx, **kwargs):
        return "Yes, we take Medicaid in the US."

    final = run_agent(
        "Do you take Medicaid in the US?",
        classifier_fn=_clf,
        retrieve_fn=_retrieve,
        generate_fn=_generate,
        run_incident_tool_fn=_incident_tool,
        run_inventory_tool_fn=_inventory_tool,
    )
    nodes = _node_names(final["trace_steps"])
    assert final.get("sources_used") == ["rag"]
    assert "incident_tool" not in nodes
    assert "inventory_tool" not in nodes
    assert incident_calls == []
    assert inventory_calls == []
    assert _is_subsequence(
        ["classify", "retrieve", "gather", "compose"], nodes
    ), nodes
    assert "Medicaid" in (final.get("answer") or "")


def test_resolves_with_both_rag_and_inventory() -> None:
    """Eval 6 — fan-out RAG + inventory; sources_used contains both."""
    hits = [
        {
            "source_document": "infection-control",
            "section": "Masks",
            "text": "Staff must wear surgical masks in clinical areas.",
            "score": 0.9,
        }
    ]
    product = {
        "id": 1,
        "name": "Surgical Masks",
        "sku": "MASK-001",
        "category": "PPE",
        "unit": "box",
        "country": "US",
        "current_stock": 120,
    }

    def _clf(q: str) -> dict:
        return {
            "use_rag": True,
            "use_incident": False,
            "use_inventory": True,
            "incident_id": None,
            "product_hint": "mask",
            "reasoning": "policy + stock",
        }

    def _retrieve(q: str, **kwargs):
        return hits

    def _inventory_tool(inp, *, auth_token=None):
        assert inp.name_hint == "mask"
        return InventoryToolResult(
            ok=True, products=[product], matched=[product], empty=False
        )

    def _incident_tool(inp, *, auth_token=None):
        raise AssertionError("incident tool must not be called")

    def _compose(prompt: str) -> str:
        assert "INVENTORY" in prompt or "Surgical" in prompt
        return "Mask policy requires surgical masks; stock is 120 boxes."

    final = run_agent(
        "What's our mask policy and do we have any in stock?",
        classifier_fn=_clf,
        retrieve_fn=_retrieve,
        run_inventory_tool_fn=_inventory_tool,
        run_incident_tool_fn=_incident_tool,
        compose_generate_fn=_compose,
    )
    used = final.get("sources_used") or []
    assert "rag" in used
    assert "inventory_tool" in used
    nodes = _node_names(final["trace_steps"])
    assert "retrieve" in nodes
    assert "inventory_tool" in nodes
    assert "gather" in nodes
    assert "compose" in nodes
    answer = final.get("answer") or ""
    assert "120" in answer or "mask" in answer.lower()


def test_tool_failure_honest_fallback() -> None:
    """Eval 7 — incident timeout → exact INCIDENT_FALLBACK + honest_fallback."""

    def _clf(q: str) -> dict:
        return {
            "use_rag": False,
            "use_incident": True,
            "use_inventory": False,
            "incident_id": 99,
            "product_hint": None,
            "reasoning": "incident only",
        }

    def _incident_tool(inp, *, auth_token=None):
        return IncidentToolResult(ok=False, error="timeout")

    def _retrieve(q: str, **kwargs):
        raise AssertionError("retrieve must not be called")

    final = run_agent(
        "Status of incident 99?",
        classifier_fn=_clf,
        run_incident_tool_fn=_incident_tool,
        retrieve_fn=_retrieve,
    )
    nodes = _node_names(final["trace_steps"])
    assert final.get("answer") == INCIDENT_FALLBACK
    assert "honest_fallback" in nodes
    assert _is_subsequence(
        ["classify", "incident_tool", "gather", "honest_fallback"], nodes
    ), nodes
    # Trace summary should record timeout
    incident_steps = [
        s for s in final["trace_steps"] if s["node"] == "incident_tool"
    ]
    assert incident_steps
    assert "timeout" in incident_steps[0]["output_summary"]


def test_inventory_match_handles_plural_hint() -> None:
    """Smoke #3 regression: 'surgical masks' must match 'Surgical mask (pack of 50)'."""
    from app.domains.agent.tools.inventory import _match_products

    products = [
        {
            "id": 1,
            "name": "Surgical mask (pack of 50)",
            "sku": "MASK-50",
            "current_stock": 182,
        }
    ]
    matched = _match_products(products, "surgical masks")
    assert len(matched) == 1
    assert matched[0]["sku"] == "MASK-50"
    assert _match_products(products, "mask")
    assert not _match_products(products, "gloves")


def test_tool_http_retry_once_on_500() -> None:
    """Retry-once: first 500, second 200 succeeds."""
    from app.domains.agent.tools import base as tool_base

    calls = {"n": 0}

    class _FakeResp:
        def __init__(self, status_code: int, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, headers=None, params=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return _FakeResp(500, {"detail": "boom"})
            return _FakeResp(
                200,
                {
                    "id": 1,
                    "title": "t",
                    "description": "d",
                    "category": "service",
                    "status": "open",
                    "origin": "web",
                    "branch": "Austin",
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                },
            )

    with patch.object(tool_base.httpx, "Client", _FakeClient):
        from app.domains.agent.tools.incident import (
            IncidentToolInput,
            run_incident_tool,
        )

        result = run_incident_tool(
            IncidentToolInput(incident_id=1), auth_token="tok"
        )
    assert calls["n"] == 2
    assert result.ok is True
    assert result.incident is not None
    assert result.incident["status"] == "open"
