from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core import config
from app.domains.agent.graph import compiled_graph
from app.domains.agent.harness.observability import get_metrics
from app.domains.agent.memory.nodes import apply_consent_decision
from app.domains.agent.memory.schemas import MemoryScope
from app.domains.agent.memory.store import get_memory_store
from app.domains.agent.nodes import EMPTY_QUESTION_ANSWER
from app.domains.agent.schemas import (
    AgentFeedbackRequest,
    AgentFeedbackResponse,
    AgentQueryResponse,
    AgentSource,
    GuardrailMetricsResponse,
    MemoryDecisionRequest,
    MemoryDecisionResponse,
    MemoryDeleteResponse,
    MemoryListItem,
    MemoryListResponse,
    MemoryProposalResponse,
)
from app.domains.knowledge import feedback_store
from app.domains.knowledge.pii import redact_pii
from app.domains.users import store as users_store
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


def resolve_clinic_id(user_id: str | None) -> str:
    if not user_id:
        return "unassigned"
    try:
        doc = users_store.get_by_id(int(user_id))
    except (TypeError, ValueError):
        return "unassigned"
    if not doc:
        return "unassigned"
    clinic = doc.get("clinic_id")
    if not clinic or not str(clinic).strip():
        logger.warning("User %s has no clinic_id — using unassigned", user_id)
        return "unassigned"
    return str(clinic).strip().lower()


def invoke_graph(
    question: str,
    *,
    auth_token: str | None = None,
    user_id: str | None = None,
) -> AgentQueryResponse:
    trace_id = "run-" + uuid.uuid4().hex[:12]
    staff_id = str(user_id) if user_id is not None else None
    clinic_id = resolve_clinic_id(user_id)
    initial_state: dict[str, Any] = {
        "question": question,
        "normalized_question": None,
        "auth_token": auth_token,
        "staff_id": staff_id,
        "clinic_id": clinic_id,
        "intent": None,
        "retrieved_context": None,
        "incident_result": None,
        "inventory_result": None,
        "compose_context_blocks": None,
        "memory_block": None,
        "recalled_mem_ids": None,
        "memory_proposal": None,
        "memory_consent_resolved": None,
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
    proposal_raw = final_state.get("memory_proposal")
    memory_proposal = None
    if isinstance(proposal_raw, dict) and proposal_raw.get("id"):
        memory_proposal = MemoryProposalResponse(
            id=str(proposal_raw["id"]),
            text=str(proposal_raw.get("text") or ""),
            options=list(proposal_raw.get("options") or ["approve", "edit", "reject"]),
        )

    response = AgentQueryResponse(
        answer=answer,
        trace_id=trace_id,
        sources=_map_sources(final_state.get("sources")),
        sources_used=list(final_state.get("sources_used") or []),
        memory_proposal=memory_proposal,
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


def decide_memory(
    body: MemoryDecisionRequest, *, user_id: str
) -> MemoryDecisionResponse:
    store = get_memory_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Memory is unavailable")
    proposal = store.pop_pending(str(user_id))
    if proposal is None:
        raise HTTPException(status_code=404, detail="No pending memory proposal")
    if proposal.proposal_id != body.proposal_id:
        # Put it back so classifier path can still resolve
        store.save_pending(str(user_id), proposal)
        raise HTTPException(status_code=409, detail="proposal_id mismatch")
    result = apply_consent_decision(
        proposal=proposal,
        decision=body.decision,
        edited_text=body.edited_text,
        store=store,
    )
    return MemoryDecisionResponse(status=str(result.get("status") or "ok"))


def list_memories(*, user_id: str) -> MemoryListResponse:
    store = get_memory_store()
    clinic_id = resolve_clinic_id(user_id)
    if store is None:
        return MemoryListResponse(memories=[], clinic_id=clinic_id)
    scope = MemoryScope(clinic_id=clinic_id, staff_id=str(user_id)).normalized()
    entries = store.list(scope)
    return MemoryListResponse(
        clinic_id=scope.clinic_id,
        memories=[
            MemoryListItem(
                id=e.id,
                type=e.type,
                text=e.text,
                created_at=e.created_at,
                last_recalled_at=e.last_recalled_at,
                recall_count=e.recall_count,
            )
            for e in entries
        ],
    )


def delete_memory(*, user_id: str, mem_id: str) -> MemoryDeleteResponse:
    store = get_memory_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Memory is unavailable")
    clinic_id = resolve_clinic_id(user_id)
    scope = MemoryScope(clinic_id=clinic_id, staff_id=str(user_id)).normalized()
    existing = {e.id: e for e in store.list(scope)}
    if mem_id not in existing:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.delete(scope, mem_id)
    return MemoryDeleteResponse(status="deleted")
