from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException

from app.domains.agent.graph import compiled_graph
from app.domains.agent.nodes import EMPTY_QUESTION_ANSWER
from app.domains.agent.schemas import AgentQueryResponse, AgentSource
from app.domains.knowledge.pii import redact_pii

logger = logging.getLogger(__name__)

_HARD_ERRORS = {
    "RagConfigError": 503,
    "EmbeddingError": 502,
    "GenerationError": 502,
}


def _map_sources(raw: list[dict[str, Any]] | None) -> list[AgentSource]:
    sources: list[AgentSource] = []
    for item in raw or []:
        sources.append(
            AgentSource(
                source_document=str(item.get("source_document", "")),
                section=str(item.get("section", "")),
                score=float(item.get("score", 0.0)),
            )
        )
    return sources


def invoke_graph(question: str) -> AgentQueryResponse:
    trace_id = "run-" + uuid.uuid4().hex[:12]
    initial_state: dict[str, Any] = {
        "question": question,
        "normalized_question": None,
        "retrieved_context": None,
        "answer": None,
        "sources": None,
        "trace_id": trace_id,
        "trace_steps": [],
        "error": None,
    }
    config = {"configurable": {"thread_id": trace_id}}
    try:
        final_state = compiled_graph.invoke(initial_state, config=config)
    except Exception:
        logger.exception(
            "Support agent graph failed trace_id=%s question=%s",
            trace_id,
            redact_pii(question),
        )
        raise HTTPException(
            status_code=500,
            detail="The support agent is temporarily unavailable. Please try again.",
        ) from None

    error = final_state.get("error")
    if error and error != "empty_question":
        status = _HARD_ERRORS.get(error)
        if status == 503:
            raise HTTPException(
                status_code=503,
                detail="The support agent is temporarily unavailable. Please try again.",
            )
        if status == 502:
            raise HTTPException(
                status_code=502,
                detail="The support agent is temporarily unavailable. Please try again.",
            )
        raise HTTPException(
            status_code=500,
            detail="The support agent is temporarily unavailable. Please try again.",
        )

    answer = final_state.get("answer") or EMPTY_QUESTION_ANSWER
    return AgentQueryResponse(
        answer=answer,
        trace_id=trace_id,
        sources=_map_sources(final_state.get("sources")),
    )
