"""LangGraph state for per-section drafting loops."""

from __future__ import annotations

from typing import Any, TypedDict


class DraftingState(TypedDict, total=False):
    ticket_id: str
    job_run_id: str | None
    section_id: int
    department_id: str
    key_aspects: list[Any]
    open_questions: list[Any]
    shared_metadata: dict[str, Any]
    subtask: str
    draft_content: str
    feedback_for_generator: str
    iteration: int
    max_iterations: int
    readability_result: dict[str, Any]
    relevance_result: dict[str, Any]
    compliance_result: dict[str, Any]
    evaluation: dict[str, Any]
    section_status: str
    hard_stop_phi: bool
    route: str
