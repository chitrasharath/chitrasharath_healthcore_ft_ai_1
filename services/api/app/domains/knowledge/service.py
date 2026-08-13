from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import HTTPException

from app.core import config
from app.domains.knowledge import feedback_store
from app.domains.knowledge.pii import redact_pii
from app.domains.knowledge.schemas import (
    KnowledgeFeedbackRequest,
    KnowledgeFeedbackResponse,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    KnowledgeSource,
)
from data.pipelines.rag import (
    FALLBACK_ANSWER,
    GenerationError,
    RagConfigError,
    query as rag_query,
)
from data.process.rag import EmbeddingError, _REPO_ROOT

logger = logging.getLogger(__name__)


def _feedback_path() -> Path:
    path = Path(config.settings.feedback_path)
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


def answer_question(body: KnowledgeQueryRequest, *, user_id: str) -> KnowledgeQueryResponse:
    query_id = str(uuid.uuid4())
    try:
        result = rag_query(body.question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RagConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (EmbeddingError, GenerationError) as exc:
        logger.warning("RAG upstream failure: %s", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="The knowledge assistant is temporarily unavailable. Please try again.",
        ) from exc

    sources = [
        KnowledgeSource(
            source_document=s["source_document"],
            section=s["section"],
            score=float(s["score"]),
        )
        for s in result.sources
    ]
    response = KnowledgeQueryResponse(
        query_id=query_id,
        answer=result.answer,
        sources=sources,
    )

    interaction = {
        "record_type": "interaction",
        "schema_version": feedback_store.SCHEMA_VERSION,
        "query_id": query_id,
        "timestamp": feedback_store.utc_now_iso(),
        "user_id": user_id,
        "question": redact_pii(body.question),
        "answer": result.answer,
        "sources": [s.model_dump() for s in sources],
        "context_texts": result.context_texts,
        "generation": {
            "model": result.model,
            "temperature": result.temperature,
            "assembled_prompt": result.assembled_prompt,
        },
        "session_id": None,
        "parent_query_id": None,
        "fallback": result.answer == FALLBACK_ANSWER and not sources,
    }
    try:
        feedback_store.append_record(_feedback_path(), interaction)
    except OSError:
        logger.exception("Failed to append knowledge interaction record")

    return response


def record_feedback(
    body: KnowledgeFeedbackRequest, *, user_id: str
) -> KnowledgeFeedbackResponse:
    path = _feedback_path()
    if not feedback_store.query_id_exists(path, body.query_id):
        raise HTTPException(status_code=404, detail="Unknown query_id")

    record = {
        "record_type": "feedback",
        "schema_version": feedback_store.SCHEMA_VERSION,
        "query_id": body.query_id,
        "timestamp": feedback_store.utc_now_iso(),
        "user_id": user_id,
        "rating": body.rating,
        "comment": redact_pii(body.comment),
    }
    # Never log raw feedback content at INFO
    logger.debug("Recording knowledge feedback for query_id=%s", body.query_id)
    try:
        feedback_store.append_record(path, record)
    except OSError as exc:
        logger.exception("Failed to append knowledge feedback")
        raise HTTPException(status_code=503, detail="Could not record feedback") from exc
    return KnowledgeFeedbackResponse(status="recorded")
