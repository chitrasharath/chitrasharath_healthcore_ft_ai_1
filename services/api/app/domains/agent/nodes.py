from __future__ import annotations

from typing import Any

from app.domains.agent.state import AgentState
from app.domains.agent.tracing import trace_step
from data.pipelines.rag import (
    GenerationError,
    RagConfigError,
    _dedupe_sources,
    generate_answer,
    normalize_query,
    retrieve,
)
from data.process.rag import EmbeddingError

AGENT_NO_CONTEXT_ANSWER = "I don't have information about that."
EMPTY_QUESTION_ANSWER = "Please enter a question."


def _next_order(state: AgentState) -> int:
    return len(state.get("trace_steps") or []) + 1


def receive_question(state: AgentState) -> dict[str, Any]:
    order = _next_order(state)
    try:
        normalized = normalize_query(state["question"])
    except ValueError:
        return {
            "normalized_question": None,
            "answer": EMPTY_QUESTION_ANSWER,
            "sources": [],
            "error": "empty_question",
            "trace_steps": [
                trace_step("receive_question", order, "empty or invalid question")
            ],
        }
    return {
        "normalized_question": normalized,
        "error": None,
        "trace_steps": [trace_step("receive_question", order, "question normalized")],
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    order = _next_order(state)
    question = state.get("normalized_question") or ""
    try:
        from app.core.config import settings

        threshold = settings.rag_min_score
        hits = retrieve(question)
    except RagConfigError:
        return {
            "retrieved_context": None,
            "error": "RagConfigError",
            "trace_steps": [trace_step("retrieve", order, "RagConfigError")],
        }
    except EmbeddingError:
        return {
            "retrieved_context": None,
            "error": "EmbeddingError",
            "trace_steps": [trace_step("retrieve", order, "EmbeddingError")],
        }

    titles: list[str] = []
    for hit in hits:
        doc = str(hit.get("source_document") or "").strip()
        if doc and doc not in titles:
            titles.append(doc)
    title_part = f" [{', '.join(titles)}]" if titles else ""
    summary = f"{len(hits)} hits >= {threshold:.2f}{title_part}"
    return {
        "retrieved_context": hits,
        "error": None,
        "trace_steps": [trace_step("retrieve", order, summary)],
    }


def query_node(state: AgentState) -> dict[str, Any]:
    """Generate via generate_answer — never call pipelines.rag.query().

    Eval seam: monkeypatch data.pipelines.rag.generate_answer (or this module's
    generate_answer import) to stub LLM output.
    """
    order = _next_order(state)
    question = state.get("normalized_question") or ""
    context = list(state.get("retrieved_context") or [])
    try:
        answer = generate_answer(question, context)
    except RagConfigError:
        return {
            "error": "RagConfigError",
            "trace_steps": [trace_step("query", order, "RagConfigError")],
        }
    except GenerationError:
        return {
            "error": "GenerationError",
            "trace_steps": [trace_step("query", order, "GenerationError")],
        }
    sources = _dedupe_sources(context)
    return {
        "answer": answer,
        "sources": sources,
        "error": None,
        "trace_steps": [trace_step("query", order, f"generated ({len(sources)} sources)")],
    }


def no_context_node(state: AgentState) -> dict[str, Any]:
    order = _next_order(state)
    return {
        "answer": AGENT_NO_CONTEXT_ANSWER,
        "sources": [],
        "error": None,
        "trace_steps": [trace_step("no_context", order, "no hits above threshold")],
    }
