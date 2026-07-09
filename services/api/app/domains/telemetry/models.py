from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

_TAGS_COLUMN = Column(
    sa.JSON().with_variant(JSONB, "postgresql"),
    nullable=False,
)


class TelemetryEventRow(SQLModel, table=True):
    __tablename__ = "telemetry_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    timestamp: datetime = Field(sa_column=Column(sa.DateTime(timezone=True), nullable=False, index=True))
    service: str
    event_type: str = Field(index=True)
    level: str = Field(default="info")
    value: Optional[float] = None
    message: Optional[str] = None
    tags: dict[str, Any] = Field(default_factory=dict, sa_column=_TAGS_COLUMN)
