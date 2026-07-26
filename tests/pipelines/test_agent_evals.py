"""Trace-based evals for the LangGraph support agent.

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
from app.domains.agent.nodes import AGENT_NO_CONTEXT_ANSWER, EMPTY_QUESTION_ANSWER
from data.pipelines.rag import FALLBACK_ANSWER

_FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "agent_grounding_response.json"
)
_GOLDEN_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "eval" / "test-queries.json"
)


def _load_fixture() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_faq_question() -> str:
    items = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    for item in items:
        if not item.get("should_abstain", True):
            return str(item["question"])
    raise AssertionError("No should_abstain=false item in test-queries.json")


def run_agent(question: str, *, generate_fn=None, retrieve_fn=None) -> dict:
    """Invoke compiled_graph once; optional seams for deterministic evals."""
    initial = {
        "question": question,
        "normalized_question": None,
        "retrieved_context": None,
        "answer": None,
        "sources": None,
        "trace_id": "run-" + uuid.uuid4().hex[:12],
        "trace_steps": [],
        "error": None,
    }
    config = {"configurable": {"thread_id": initial["trace_id"]}}

    with ExitStack() as stack:
        if generate_fn is not None:
            stack.enter_context(
                patch.object(
                    agent_nodes,
                    "generate_answer",
                    side_effect=lambda q, ctx, **kw: generate_fn(q, ctx),
                )
            )
        if retrieve_fn is not None:
            stack.enter_context(
                patch.object(agent_nodes, "retrieve", side_effect=retrieve_fn)
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
    assert nodes == ["receive_question", "retrieve", "query"]
    assert "no_context" not in nodes
    assert final.get("error") in (None, "")
    assert final.get("answer")


def test_empty_question_error_path() -> None:
    final = run_agent("   ")
    nodes = _node_names(final["trace_steps"])
    assert "receive_question" in nodes
    assert "query" not in nodes
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

    final = run_agent(fixture["question"])
    answer = final.get("answer") or ""
    assert answer.strip()
    assert answer != AGENT_NO_CONTEXT_ANSWER
    assert answer != FALLBACK_ANSWER
    assert any(e.lower() in answer.lower() for e in fixture["expected_entities"])
    source_docs = {s.get("source_document") for s in (final.get("sources") or [])}
    assert fixture["expected_source_document"] in source_docs
