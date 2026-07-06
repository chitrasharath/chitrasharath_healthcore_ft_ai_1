from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class MedicalSupplyCreate(BaseModel):
    name: str
    sku: str
    category: str
    unit: str
    country: str


class MedicalSupplyRead(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int

    model_config = {"from_attributes": True}


class SupplyDeliveryCreate(BaseModel):
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int


class SupplyDeliveryRead(BaseModel):
    id: int
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime
    user_uuid: str

    model_config = {"from_attributes": True}


class SupplyConsumptionCreate(BaseModel):
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int

    @field_validator("consumption_type")
    @classmethod
    def validate_consumption_type(cls, v: str) -> str:
        allowed = ("clinical_use", "expiry_waste")
        if v not in allowed:
            raise ValueError(f"consumption_type must be one of {allowed}")
        return v


class SupplyConsumptionRead(BaseModel):
    id: int
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime
    user_uuid: str

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: int
    order_type: str
    supply_id: int
    supply_name: str
    quantity: int
    user_uuid: str
    created_at: datetime
    vendor_name: str | None = None
    consumption_type: str | None = None
    clinic_id: int
