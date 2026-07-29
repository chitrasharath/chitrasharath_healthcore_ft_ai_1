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
    """In-memory guardrail counters.

    ``content`` includes personal/PHI blocks and casual redirects.
    ``redirects`` counts only redirect actions (a subset of ``content``).
    """

    security: int = 0
    content: int = Field(
        default=0,
        description="content-class blocks including casual redirects",
    )
    structural: int = 0
    redirects: int = Field(
        default=0,
        description="casual redirect subset; also counted under content",
    )
