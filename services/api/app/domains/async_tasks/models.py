from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


class DeadLetterTask(SQLModel, table=True):
    __tablename__ = "dead_letter_tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: str = Field(index=True)
    task_name: str
    attempt: int
    error: str
    traceback: str | None = None
    created_at: datetime = Field(
        sa_column=Column(sa.DateTime(timezone=True), nullable=False, index=True),
    )
