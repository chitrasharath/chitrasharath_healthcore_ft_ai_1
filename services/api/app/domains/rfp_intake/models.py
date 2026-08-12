from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel, UniqueConstraint


def _new_ticket_id() -> str:
    return str(uuid4())


def _new_rfp_id() -> str:
    return f"RFP-{uuid4().hex[:8].upper()}"


class Ticket(SQLModel, table=True):
    __tablename__ = "rfp_tickets"

    ticket_id: str = Field(default_factory=_new_ticket_id, primary_key=True)
    rfp_id: str = Field(default_factory=_new_rfp_id, index=True)
    status: str = Field(default="analyzing", index=True)
    raw_pdf_path: str | None = None
    content_sha256: str | None = Field(default=None, index=True)
    needs_human_review: bool = False
    classifier_reason: str | None = None
    created_at: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


class RfpMetadata(SQLModel, table=True):
    __tablename__ = "rfp_metadata"

    ticket_id: str = Field(primary_key=True, foreign_key="rfp_tickets.ticket_id")
    client_name: str | None = None
    client_country: str | None = None
    program_type: str | None = None
    covered_population: str | None = None
    covered_population_n: int | None = None
    deadline: str | None = None
    budget_range: str | None = None
    departments_needed: list[Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    readability_metrics: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    open_questions: list[Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    contains_phi: bool = False
    markdown_text: str | None = Field(
        default=None,
        sa_column=Column(sa.Text, nullable=True),
    )
    sales_summary: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    classifier_result: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )


class DepartmentSection(SQLModel, table=True):
    __tablename__ = "rfp_department_sections"
    __table_args__ = (
        UniqueConstraint("ticket_id", "department_id", name="uq_rfp_section_dept"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True)
    department_id: str = Field(index=True)
    key_aspects: list[Any] | dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    draft_content: str | None = Field(
        default=None,
        sa_column=Column(sa.Text, nullable=True),
    )
    evaluation_results: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    status: str | None = Field(default=None, index=True)
    iteration: int = Field(default=0)
    latest_evaluation_id: int | None = Field(default=None)
    approval_status: str | None = None
    approver: str | None = None
    approved_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )


class EvaluationResult(SQLModel, table=True):
    __tablename__ = "rfp_evaluation_results"

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="rfp_department_sections.id", index=True)
    ticket_id: str = Field(foreign_key="rfp_tickets.ticket_id", index=True)
    department_id: str = Field(index=True)
    iteration: int = Field(default=1)
    readability: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    relevance: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    compliance: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(sa.JSON, nullable=True),
    )
    contains_phi: bool = False
    overall_pass: bool = False
    feedback_for_generator: str | None = Field(
        default=None,
        sa_column=Column(sa.Text, nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
