from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None


class DeadLetterItem(BaseModel):
    id: UUID
    task_id: str
    task_name: str
    attempt: int
    error: str
    created_at: datetime


class DeadLetterListResponse(BaseModel):
    items: list[DeadLetterItem] = Field(default_factory=list)
