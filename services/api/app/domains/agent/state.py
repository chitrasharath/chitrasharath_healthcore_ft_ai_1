from __future__ import annotations

import operator
from typing import Annotated, Any, Sequence, TypedDict


class AgentState(TypedDict):
    question: str
    normalized_question: str | None
    retrieved_context: list[dict[str, Any]] | None
    answer: str | None
    sources: list[dict[str, Any]] | None
    trace_id: str
    trace_steps: Annotated[Sequence[dict[str, Any]], operator.add]
    error: str | None
