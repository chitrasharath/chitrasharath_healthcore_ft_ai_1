from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, oauth2_scheme
from app.domains.agent import service
from app.domains.agent.schemas import (
    AgentFeedbackRequest,
    AgentFeedbackResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    GuardrailMetricsResponse,
    MemoryDecisionRequest,
    MemoryDecisionResponse,
    MemoryDeleteResponse,
    MemoryListResponse,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
def query_agent(
    body: AgentQueryRequest,
    token: str = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user),
) -> AgentQueryResponse:
    # Forward caller JWT into graph state for MCP tools — never log token.
    return service.invoke_graph(
        body.question,
        auth_token=token,
        user_id=str(current_user["id"]),
    )


@router.post("/feedback", response_model=AgentFeedbackResponse)
def agent_feedback(
    body: AgentFeedbackRequest,
    current_user: dict = Depends(get_current_user),
) -> AgentFeedbackResponse:
    return service.record_feedback(body, user_id=str(current_user["id"]))


@router.get("/guardrails/metrics", response_model=GuardrailMetricsResponse)
def agent_guardrail_metrics(
    session: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> GuardrailMetricsResponse:
    _ = current_user
    # In-memory / per-process only — not durable across workers or restarts.
    return service.guardrail_metrics(session)


@router.post("/memory/decision", response_model=MemoryDecisionResponse)
def memory_decision(
    body: MemoryDecisionRequest,
    current_user: dict = Depends(get_current_user),
) -> MemoryDecisionResponse:
    return service.decide_memory(body, user_id=str(current_user["id"]))


@router.get("/memory", response_model=MemoryListResponse)
def memory_list(
    current_user: dict = Depends(get_current_user),
) -> MemoryListResponse:
    return service.list_memories(user_id=str(current_user["id"]))


@router.delete("/memory/{mem_id}", response_model=MemoryDeleteResponse)
def memory_delete(
    mem_id: str,
    current_user: dict = Depends(get_current_user),
) -> MemoryDeleteResponse:
    return service.delete_memory(user_id=str(current_user["id"]), mem_id=mem_id)
