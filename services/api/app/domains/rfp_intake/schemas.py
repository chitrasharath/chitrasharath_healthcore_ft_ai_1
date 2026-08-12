from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadAccepted(BaseModel):
    ticket_id: str
    rfp_id: str
    status: str


class EvaluationResultOut(BaseModel):
    id: int
    department_id: str
    iteration: int
    readability: dict[str, Any] | None = None
    relevance: dict[str, Any] | None = None
    compliance: dict[str, Any] | None = None
    contains_phi: bool = False
    overall_pass: bool = False
    feedback_for_generator: str | None = None
    created_at: datetime


class DepartmentSectionOut(BaseModel):
    department_id: str
    key_aspects: list[Any] | dict[str, Any] | None = None
    draft_content: str | None = None
    evaluation_results: dict[str, Any] | None = None
    status: str | None = None
    iteration: int = 0
    latest_evaluation_id: int | None = None
    evaluation_history: list[EvaluationResultOut] = Field(default_factory=list)


class RfpMetadataOut(BaseModel):
    client_name: str | None = None
    client_country: str | None = None
    program_type: str | None = None
    covered_population: str | None = None
    covered_population_n: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    departments_needed: list[Any] | None = None
    readability_metrics: dict[str, Any] | None = None
    open_questions: list[Any] | None = None
    contains_phi: bool = False
    sales_summary: dict[str, Any] | None = None
    classifier_result: dict[str, Any] | None = None
    markdown_preview: str | None = Field(
        default=None,
        description="Redacted preview only; never raw PHI",
    )


class TicketSummary(BaseModel):
    ticket_id: str
    rfp_id: str
    status: str
    client_name: str | None = None
    program_type: str | None = None
    departments_needed: list[Any] | None = None
    contains_phi: bool = False
    needs_human_review: bool = False
    job_status: str | None = None
    sections_needing_review: int = 0
    phase2_complete: bool = False
    created_at: datetime
    updated_at: datetime


class TicketDetail(BaseModel):
    ticket_id: str
    rfp_id: str
    status: str
    needs_human_review: bool = False
    classifier_reason: str | None = None
    job_status: str | None = None
    job_checkpoint: str | None = None
    job_error: str | None = None
    sections_needing_review: int = 0
    phase2_complete: bool = False
    created_at: datetime
    updated_at: datetime
    metadata: RfpMetadataOut | None = None
    sections: list[DepartmentSectionOut] = Field(default_factory=list)


class RerunAccepted(BaseModel):
    ticket_id: str
    status: str
    message: str = "rerun enqueued"


class DraftingAccepted(BaseModel):
    ticket_id: str
    status: str
    message: str = "drafting enqueued"


class RedraftAccepted(BaseModel):
    ticket_id: str
    department_id: str
    status: str
    message: str = "redraft enqueued"


class ReleaseRedactedAccepted(BaseModel):
    ticket_id: str
    department_id: str
    status: str
    phi_cleared: bool
    message: str = "PHI redacted"
