from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Incident(SQLModel, table=True):
    __tablename__ = "incident"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    category: str
    status: str = "open"
    origin: str
    branch: str
    incident_id: Optional[str] = Field(default=None, unique=True, index=True)
    created_at: datetime
    updated_at: datetime
