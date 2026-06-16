from fastapi import APIRouter, HTTPException, Query

from app.domains.procurement.suppliers import service
from app.domains.procurement.suppliers.schemas import (
    VALID_CATEGORIES,
    VALID_COUNTRIES,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierResponse,
    SupplierStatusUpdate,
)
from app.domains.procurement.suppliers.service import DuplicateSupplierError, SupplierNotFoundError

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierResponse, status_code=201)
def create_supplier(body: SupplierCreate) -> SupplierResponse:
    try:
        return service.create(body)
    except DuplicateSupplierError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> list[SupplierResponse]:
    if country is not None and country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail='country must be "USA" or "UK"')
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"invalid category: {category}")
    return service.list_suppliers(country=country, category=category)


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int) -> SupplierResponse:
    try:
        return service.get_supplier(supplier_id)
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Supplier not found") from exc


@router.patch("/{supplier_id}/rate", response_model=SupplierResponse)
def update_supplier_rate(supplier_id: int, body: SupplierRateUpdate) -> SupplierResponse:
    try:
        return service.update_rate(supplier_id, body)
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Supplier not found") from exc


@router.patch("/{supplier_id}/status", response_model=SupplierResponse)
def update_supplier_status(supplier_id: int, body: SupplierStatusUpdate) -> SupplierResponse:
    try:
        return service.update_status(supplier_id, body)
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Supplier not found") from exc


@router.delete("/{supplier_id}", response_model=SupplierResponse)
def delete_supplier(supplier_id: int) -> SupplierResponse:
    try:
        return service.soft_delete(supplier_id)
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Supplier not found") from exc
