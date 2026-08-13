from __future__ import annotations

from typing import Any, TypedDict


class RfpIntakeState(TypedDict, total=False):
    ticket_id: str
    job_run_id: str
    pdf_path: str
    markdown: str
    contains_phi: bool
    phi_reasons: list[str]
    metadata: dict[str, Any]
    open_questions: list[str]
    readability_metrics: dict[str, Any]
    classifier: dict[str, Any]
    departments_needed: list[str]
    department_extracts: dict[str, list[str]]
    worker_results: dict[str, Any]
    sales_summary: dict[str, Any]
    stop_reason: str
    error: str
    checkpoint: str
