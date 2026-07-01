from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentCreate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    origin: str | None = None
    branch: str | None = None


class IncidentUpdate(IncidentCreate):
    pass


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    status: str
    origin: str
    branch: str
    created_at: datetime
    updated_at: datetime


class StatusUpdate(BaseModel):
    status: str


class IncidentSummary(BaseModel):
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_origin: dict[str, int]
    by_branch: dict[str, int]
