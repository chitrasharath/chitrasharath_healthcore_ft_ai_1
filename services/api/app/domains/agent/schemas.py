from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    question: str = Field(default="", max_length=1000)


class AgentSource(BaseModel):
    source_document: str
    section: str
    score: float


class AgentQueryResponse(BaseModel):
    answer: str
    trace_id: str
    sources: list[AgentSource]
    sources_used: list[str] = Field(default_factory=list)


class AgentFeedbackRequest(BaseModel):
    trace_id: str = Field(..., min_length=1)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)


class AgentFeedbackResponse(BaseModel):
    status: str


class GuardrailMetricsResponse(BaseModel):
    security: int = 0
    content: int = 0
    structural: int = 0
    redirects: int = 0
