from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel, UniqueConstraint


class ReportingConsumptionVolumeDaily(SQLModel, table=True):
    __tablename__ = "reporting_consumption_volume_daily"
    __table_args__ = (
        UniqueConstraint(
            "report_date",
            "clinic_id",
            "jurisdiction",
            name="uq_rcv_grain",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    report_date: date = Field(index=True)
    clinic_id: int
    jurisdiction: str
    count: int
    run_id: UUID
    updated_at: datetime = Field(sa_column=Column(sa.DateTime(timezone=True), nullable=False))


class ReportingWasteRateDaily(SQLModel, table=True):
    __tablename__ = "reporting_waste_rate_daily"
    __table_args__ = (
        UniqueConstraint("report_date", "jurisdiction", name="uq_rwr_grain"),
    )

    id: int | None = Field(default=None, primary_key=True)
    report_date: date = Field(index=True)
    jurisdiction: str
    waste_rate: float
    total: int
    run_id: UUID
    updated_at: datetime = Field(sa_column=Column(sa.DateTime(timezone=True), nullable=False))


class ReportingStockFailuresDaily(SQLModel, table=True):
    __tablename__ = "reporting_stock_failures_daily"
    __table_args__ = (
        UniqueConstraint(
            "report_date",
            "clinic_id",
            "jurisdiction",
            "supply_id",
            name="uq_rsf_grain",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    report_date: date = Field(index=True)
    clinic_id: int
    jurisdiction: str
    supply_id: str
    count: int
    attempts: int
    rejection_rate: float
    run_id: UUID
    updated_at: datetime = Field(sa_column=Column(sa.DateTime(timezone=True), nullable=False))


class ReportingAuthFailureDaily(SQLModel, table=True):
    __tablename__ = "reporting_auth_failure_daily"
    __table_args__ = (UniqueConstraint("report_date", name="uq_raf_grain"),)

    id: int | None = Field(default=None, primary_key=True)
    report_date: date = Field(index=True)
    failed: int
    succeeded: int
    failure_rate: float
    run_id: UUID
    updated_at: datetime = Field(sa_column=Column(sa.DateTime(timezone=True), nullable=False))


class PipelineRun(SQLModel, table=True):
    __tablename__ = "pipeline_runs"

    run_id: UUID = Field(primary_key=True)
    started_at: datetime = Field(sa_column=Column(sa.DateTime(timezone=True), nullable=False))
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )
    watermark_from: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )
    watermark_to: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )
    rows_extracted: int = Field(default=0)
    rows_loaded: int = Field(default=0)
    rows_quarantined: int = Field(default=0)
    status: str = Field(default="running", index=True)
    error_summary: str | None = None
    pipeline_version: str = Field(default="1.0.0")
    checkpoint: str | None = None
