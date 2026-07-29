"""Pydantic models for agent long-term memory."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_mem_id() -> str:
    return "m-" + uuid4().hex[:12]


def new_proposal_id() -> str:
    return "mp-" + uuid4().hex[:12]


class MemoryScope(BaseModel):
    clinic_id: str
    staff_id: str

    def normalized(self) -> MemoryScope:
        return MemoryScope(
            clinic_id=self.clinic_id.strip().lower() or "unassigned",
            staff_id=self.staff_id.strip().lower(),
        )


class MemoryEntry(BaseModel):
    id: str
    scope: MemoryScope
    type: Literal["semantic", "procedural"]
    text: str
    created_at: int
    last_recalled_at: int
    recall_count: int = 0
    source_trace_id: str | None = None


class MemoryProposal(BaseModel):
    proposal_id: str = Field(default_factory=new_proposal_id)
    clinic_id: str
    staff_id: str
    type: Literal["semantic", "procedural"] = "semantic"
    text: str
    source_trace_id: str | None = None
    created_at: int | None = None
    worth_remembering: bool = True
    scope_hint: str | None = None
    reasoning: str | None = None


class MemoryDecision(BaseModel):
    decision: Literal["approve", "edit", "reject", "new_question"]
    edited_text: str | None = None


class MemoryProposalPublic(BaseModel):
    """API response shape for pending consent."""

    id: str
    text: str
    options: list[str] = Field(default_factory=lambda: ["approve", "edit", "reject"])
