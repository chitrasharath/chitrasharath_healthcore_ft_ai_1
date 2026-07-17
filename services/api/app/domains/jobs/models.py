from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


class JobRun(SQLModel, table=True):
    __tablename__ = "job_runs"
    __table_args__ = (
        sa.Index("ix_job_runs_job_name_target_date", "job_name", "target_date"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_name: str
    target_date: date
    status: str = Field(default="pending", index=True)
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )
    error_message: str | None = None
    created_at: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
