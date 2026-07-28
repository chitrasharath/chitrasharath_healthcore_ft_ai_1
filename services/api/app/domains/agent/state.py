from __future__ import annotations

import operator
from typing import Annotated, Any, Sequence, TypedDict


class AgentState(TypedDict):
    question: str
    normalized_question: str | None
    auth_token: str | None
    intent: dict[str, Any] | None
    retrieved_context: list[dict[str, Any]] | None
    incident_result: dict[str, Any] | None
    inventory_result: dict[str, Any] | None
    compose_context_blocks: list[str] | None
    answer: str | None
    sources: list[dict[str, Any]] | None
    sources_used: Annotated[list[str], operator.add]
    trace_id: str
    trace_steps: Annotated[Sequence[dict[str, Any]], operator.add]
    error: str | None
    guardrail_action: str | None
    guardrail_type: str | None
    guardrail_events: Annotated[list[dict], operator.add]
    final_answer_overridden: bool | None
