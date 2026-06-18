from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_CATEGORIES = [
    "medical_supplies",
    "laboratory_services",
    "pharmaceutical",
    "clinical_software",
    "it_infrastructure",
    "hr_and_payroll_software",
    "cleaning_and_facilities",
    "patient_communication",
    "billing_and_coding_software",
    "training_platforms",
]

VALID_STATUSES = ["active", "suspended"]
VALID_COUNTRIES = {"USA", "UK"}
COUNTRY_CURRENCY = {"USA": "USD", "UK": "GBP"}
VALID_COMPLIANCE = {"BAA", "DPA", "both", None}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    country: str
    categories: list[str]
    monthly_rate: float
    currency: str
    status: str
    compliance_agreement: str | None = None
    contract_renewal_date: str | None = None
    contact_email: str | None = None
    notes: str | None = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        if value not in VALID_COUNTRIES:
            raise ValueError('country must be "USA" or "UK"')
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError('status must be "active" or "suspended"')
        return value

    @field_validator("monthly_rate")
    @classmethod
    def validate_monthly_rate(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("monthly_rate must be greater than 0")
        return value

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("categories must contain at least one item")
        for category in value:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"invalid category: {category}")
        return value

    @field_validator("compliance_agreement")
    @classmethod
    def validate_compliance(cls, value: str | None) -> str | None:
        if value is not None and value not in {"BAA", "DPA", "both"}:
            raise ValueError('compliance_agreement must be "BAA", "DPA", "both", or null')
        return value

    @field_validator("contract_renewal_date")
    @classmethod
    def validate_renewal_date(cls, value: str | None) -> str | None:
        if value is not None and not DATE_PATTERN.match(value):
            raise ValueError("contract_renewal_date must be YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def validate_currency_matches_country(self) -> SupplierCreate:
        expected = COUNTRY_CURRENCY[self.country]
        if self.currency != expected:
            raise ValueError(f"currency must be {expected} for country {self.country}")
        return self


class SupplierRateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_rate: float

    @field_validator("monthly_rate")
    @classmethod
    def validate_monthly_rate(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("monthly_rate must be greater than 0")
        return value


class SupplierStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError('status must be "active" or "suspended"')
        return value


class SupplierDetailsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compliance_agreement: str | None = None
    contract_renewal_date: str | None = None
    contact_email: str | None = None
    notes: str | None = None

    @field_validator("compliance_agreement")
    @classmethod
    def validate_compliance(cls, value: str | None) -> str | None:
        if value is not None and value not in {"BAA", "DPA", "both"}:
            raise ValueError('compliance_agreement must be "BAA", "DPA", "both", or null')
        return value

    @field_validator("contract_renewal_date")
    @classmethod
    def validate_renewal_date(cls, value: str | None) -> str | None:
        if value is not None and not DATE_PATTERN.match(value):
            raise ValueError("contract_renewal_date must be YYYY-MM-DD")
        return value


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: Literal["USA", "UK"]
    categories: list[str]
    monthly_rate: float
    currency: str
    rate_updated_at: datetime
    status: Literal["active", "suspended"]
    compliance_agreement: str | None = None
    contract_renewal_date: str | None = None
    contact_email: str | None = None
    notes: str | None = None
