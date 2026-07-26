from __future__ import annotations

from app.domains.agent.state import AgentState


def after_receive(state: AgentState) -> str:
    if state.get("error") == "empty_question" or not state.get("normalized_question"):
        return "end"
    return "retrieve"


def after_retrieve(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("retrieved_context"):
        return "no_context"
    return "query"
