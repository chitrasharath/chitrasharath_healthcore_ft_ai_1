from __future__ import annotations

from app.domains.agent.state import AgentState

_HARD_RETRIEVE_ERRORS = frozenset({"RagConfigError", "EmbeddingError"})


def after_receive(state: AgentState) -> str:
    if state.get("error") == "empty_question" or not state.get("normalized_question"):
        return "end"
    return "memory_consent_check"


def after_memory_consent(state: AgentState) -> str:
    if state.get("memory_consent_resolved"):
        return "observability"
    return "input_guards"


def after_input_guards(state: AgentState) -> str:
    action = state.get("guardrail_action")
    if action in {"block", "redirect"} and state.get("answer"):
        return "observability"
    return "memory_read"


def route_intent(state: AgentState) -> list[str]:
    """Fan-out conditional edge — real condition on classifier intent."""
    intent = state.get("intent") or {}
    targets: list[str] = []
    if intent.get("use_incident"):
        targets.append("incident_tool")
    if intent.get("use_inventory"):
        targets.append("inventory_tool")
    if intent.get("use_rag") or not targets:
        targets.append("retrieve")
    return targets


def after_gather(state: AgentState) -> str:
    """Explicit recovery decision after parallel source branches join."""
    error = state.get("error")
    rag_hits = state.get("retrieved_context") or []
    rag_ok = bool(rag_hits)
    mem_ok = bool(state.get("memory_block"))
    inc = state.get("incident_result")
    inv = state.get("inventory_result")
    inc_ok = bool(inc) and bool(inc.get("ok")) and not bool(inc.get("empty"))
    inv_ok = bool(inv) and bool(inv.get("ok")) and not bool(inv.get("empty"))

    # Preserve Part 1 hard retrieve errors when no tool/memory succeeded.
    if error in _HARD_RETRIEVE_ERRORS and not inc_ok and not inv_ok and not mem_ok:
        return "end"

    if not rag_ok and not inc_ok and not inv_ok and not mem_ok:
        return "honest_fallback"
    return "compose"


def after_external_content(state: AgentState) -> str:
    """Route to compose or honest_fallback using the same rules as after_gather."""
    return after_gather(state)
