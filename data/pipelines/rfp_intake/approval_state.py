"""Approval graph state (Phase 3)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class ApprovalState(TypedDict, total=False):
    ticket_id: str
    job_run_id: str
    required_departments: list[str]
    metadata: dict[str, Any]
    sections: list[dict[str, Any]]
    arbitration: dict[str, Any] | None
    approvals: dict[str, dict[str, Any]]
    revision_department: str | None
    revision_reason: str | None
    phase3_complete: bool
    blocked_reason: str | None
    execution_log: Annotated[list[dict[str, Any]], operator.add]
