from __future__ import annotations

from datetime import datetime, timezone

from app.domains.procurement.suppliers import store
from app.domains.procurement.suppliers.schemas import (
    SupplierCreate,
    SupplierRateUpdate,
    SupplierResponse,
    SupplierStatusUpdate,
)


class DuplicateSupplierError(Exception):
    pass


class SupplierNotFoundError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_response(doc: dict) -> SupplierResponse:
    payload = dict(doc)
    rate_updated = payload["rate_updated_at"]
    if isinstance(rate_updated, str):
        payload["rate_updated_at"] = datetime.fromisoformat(rate_updated.replace("Z", "+00:00"))
    return SupplierResponse(**payload)


def create(data: SupplierCreate) -> SupplierResponse:
    if store.get_by_name(data.name) is not None:
        raise DuplicateSupplierError("A supplier with this name already exists")
    payload = data.model_dump()
    payload["rate_updated_at"] = _utc_now().isoformat()
    supplier_id = store.insert(payload)
    doc = store.get_by_id(supplier_id)
    assert doc is not None
    return _to_response(doc)


def list_suppliers(country: str | None = None, category: str | None = None) -> list[SupplierResponse]:
    docs = store.list_filtered(country=country, category=category)
    return [_to_response(doc) for doc in docs]


def get_supplier(supplier_id: int) -> SupplierResponse:
    doc = store.get_by_id(supplier_id)
    if doc is None:
        raise SupplierNotFoundError
    return _to_response(doc)


def update_rate(supplier_id: int, data: SupplierRateUpdate) -> SupplierResponse:
    doc = store.update(
        supplier_id,
        {"monthly_rate": data.monthly_rate, "rate_updated_at": _utc_now().isoformat()},
    )
    if doc is None:
        raise SupplierNotFoundError
    return _to_response(doc)


def update_status(supplier_id: int, data: SupplierStatusUpdate) -> SupplierResponse:
    doc = store.update(supplier_id, {"status": data.status})
    if doc is None:
        raise SupplierNotFoundError
    return _to_response(doc)


def soft_delete(supplier_id: int) -> SupplierResponse:
    doc = store.update(supplier_id, {"status": "suspended"})
    if doc is None:
        raise SupplierNotFoundError
    return _to_response(doc)
