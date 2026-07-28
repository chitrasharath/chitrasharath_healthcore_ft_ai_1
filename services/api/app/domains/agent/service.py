from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core import config
from app.domains.agent.graph import compiled_graph
from app.domains.agent.harness.observability import get_metrics
from app.domains.agent.nodes import EMPTY_QUESTION_ANSWER
from app.domains.agent.schemas import (
    AgentFeedbackRequest,
    AgentFeedbackResponse,
    AgentQueryResponse,
    AgentSource,
    GuardrailMetricsResponse,
)
from app.domains.knowledge import feedback_store
from app.domains.knowledge.pii import redact_pii
from data.process.rag import _REPO_ROOT

logger = logging.getLogger(__name__)

_HARD_ERRORS = {
    "RagConfigError": 503,
    "EmbeddingError": 502,
    "GenerationError": 502,
}


def _feedback_path() -> Path:
    path = Path(config.settings.feedback_path)
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


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


def invoke_graph(
    question: str,
    *,
    auth_token: str | None = None,
    user_id: str | None = None,
) -> AgentQueryResponse:
    trace_id = "run-" + uuid.uuid4().hex[:12]
    initial_state: dict[str, Any] = {
        "question": question,
        "normalized_question": None,
        "auth_token": auth_token,
        "intent": None,
        "retrieved_context": None,
        "incident_result": None,
        "inventory_result": None,
        "compose_context_blocks": None,
        "answer": None,
        "sources": None,
        "sources_used": [],
        "trace_id": trace_id,
        "trace_steps": [],
        "error": None,
        "guardrail_action": None,
        "guardrail_type": None,
        "guardrail_events": [],
        "final_answer_overridden": None,
    }
    config_run = {"configurable": {"thread_id": trace_id}}
    try:
        final_state = compiled_graph.invoke(initial_state, config=config_run)
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
    response = AgentQueryResponse(
        answer=answer,
        trace_id=trace_id,
        sources=_map_sources(final_state.get("sources")),
        sources_used=list(final_state.get("sources_used") or []),
    )

    if user_id is not None:
        interaction = {
            "record_type": "interaction",
            "schema_version": feedback_store.SCHEMA_VERSION,
            "surface": "agent",
            "query_id": response.trace_id,
            "timestamp": feedback_store.utc_now_iso(),
            "user_id": user_id,
            "question": redact_pii(question),
            "answer": response.answer,
            "sources": [s.model_dump() for s in response.sources],
            "sources_used": response.sources_used,
            "guardrail": final_state.get("guardrail_type"),
        }
        try:
            feedback_store.append_record(_feedback_path(), interaction)
        except OSError:
            logger.exception("Failed to append agent interaction record")

    return response


def record_feedback(
    body: AgentFeedbackRequest, *, user_id: str
) -> AgentFeedbackResponse:
    path = _feedback_path()
    if not feedback_store.query_id_exists(path, body.trace_id):
        raise HTTPException(status_code=404, detail="Unknown trace_id")
    record = {
        "record_type": "feedback",
        "schema_version": feedback_store.SCHEMA_VERSION,
        "surface": "agent",
        "query_id": body.trace_id,
        "timestamp": feedback_store.utc_now_iso(),
        "user_id": user_id,
        "rating": body.rating,
        "comment": redact_pii(body.comment),
    }
    logger.debug("Recording agent feedback for trace_id=%s", body.trace_id)
    try:
        feedback_store.append_record(path, record)
    except OSError as exc:
        logger.exception("Failed to append agent feedback")
        raise HTTPException(status_code=503, detail="Could not record feedback") from exc
    return AgentFeedbackResponse(status="recorded")


def guardrail_metrics(session: str | None = None) -> GuardrailMetricsResponse:
    counts = get_metrics(session)
    return GuardrailMetricsResponse(
        security=int(counts.get("security", 0)),
        content=int(counts.get("content", 0)),
        structural=int(counts.get("structural", 0)),
        redirects=int(counts.get("redirects", 0)),
    )
