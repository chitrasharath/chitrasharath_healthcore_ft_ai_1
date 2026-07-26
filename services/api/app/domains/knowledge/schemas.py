from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def trim_question(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Question must not be blank")
        return cleaned


class KnowledgeSource(BaseModel):
    source_document: str
    section: str
    score: float


class KnowledgeQueryResponse(BaseModel):
    query_id: str
    answer: str
    sources: list[KnowledgeSource]


class KnowledgeFeedbackRequest(BaseModel):
    query_id: str = Field(..., min_length=1)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def trim_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class KnowledgeFeedbackResponse(BaseModel):
    status: str
