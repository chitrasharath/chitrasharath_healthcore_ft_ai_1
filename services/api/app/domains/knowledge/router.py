from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.domains.knowledge import service
from app.domains.knowledge.schemas import (
    KnowledgeFeedbackRequest,
    KnowledgeFeedbackResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/query", response_model=KnowledgeQueryResponse)
def query_knowledge(
    body: KnowledgeQueryRequest,
    current_user: dict = Depends(get_current_user),
) -> KnowledgeQueryResponse:
    return service.answer_question(body, user_id=str(current_user["id"]))


@router.post("/feedback", response_model=KnowledgeFeedbackResponse)
def submit_feedback(
    body: KnowledgeFeedbackRequest,
    current_user: dict = Depends(get_current_user),
) -> KnowledgeFeedbackResponse:
    return service.record_feedback(body, user_id=str(current_user["id"]))
