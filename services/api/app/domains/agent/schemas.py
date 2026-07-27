from __future__ import annotations

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
