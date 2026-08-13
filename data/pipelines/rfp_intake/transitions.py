"""Ticket status transition guard (Phase 3 §5.9)."""

from __future__ import annotations

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "analyzing": frozenset({"analyzing", "discarded", "intake_complete"}),
    "discarded": frozenset({"discarded", "analyzing"}),
    "intake_complete": frozenset({"intake_complete", "drafting", "analyzing"}),
    "drafting": frozenset({"drafting", "under_evaluation", "analyzing"}),
    "under_evaluation": frozenset(
        {"under_evaluation", "drafting", "waiting_for_approval", "analyzing"}
    ),
    "waiting_for_approval": frozenset(
        {
            "waiting_for_approval",
            "under_evaluation",
            "done",
            "analyzing",
            "drafting",
        }
    ),
    "done": frozenset({"done", "analyzing"}),
}


def can_transition(from_status: str, to_status: str) -> bool:
    if from_status == to_status:
        return True
    allowed = LEGAL_TRANSITIONS.get(from_status)
    if allowed is None:
        return False
    return to_status in allowed


def assert_can_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise ValueError(f"Illegal ticket status jump: {from_status} → {to_status}")
