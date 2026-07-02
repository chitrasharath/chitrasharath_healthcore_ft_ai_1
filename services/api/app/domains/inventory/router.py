from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.core.db import get_supabase_db
from app.core.dependencies import get_current_user
from app.domains.inventory.models import MedicalSupply, SupplyConsumption, SupplyDelivery
from app.domains.inventory.schemas import (
    MedicalSupplyCreate,
    MedicalSupplyRead,
    OrderRead,
    SupplyConsumptionCreate,
    SupplyConsumptionRead,
    SupplyDeliveryCreate,
    SupplyDeliveryRead,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def compute_stock(session: Session, supply_id: int) -> int:
    inbound = session.exec(
        select(func.coalesce(func.sum(SupplyDelivery.quantity), 0)).where(
            SupplyDelivery.supply_id == supply_id
        )
    ).one()
    outbound = session.exec(
        select(func.coalesce(func.sum(SupplyConsumption.quantity), 0)).where(
            SupplyConsumption.supply_id == supply_id
        )
    ).one()
    return int(inbound) - int(outbound)


def _to_supply_read(supply: MedicalSupply, stock: int) -> MedicalSupplyRead:
    return MedicalSupplyRead(
        id=supply.id,
        name=supply.name,
        sku=supply.sku,
        category=supply.category,
        unit=supply.unit,
        country=supply.country,
        current_stock=stock,
    )


def _get_supply_or_404(session: Session, supply_id: int) -> MedicalSupply:
    supply = session.get(MedicalSupply, supply_id)
    if supply is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return supply


@router.get("/products", response_model=list[MedicalSupplyRead])
def list_products(session: Session = Depends(get_supabase_db)) -> list[MedicalSupplyRead]:
    supplies = session.exec(select(MedicalSupply)).all()
    return [_to_supply_read(s, compute_stock(session, s.id)) for s in supplies]


@router.post("/products", response_model=MedicalSupplyRead, status_code=201)
def create_product(
    body: MedicalSupplyCreate,
    session: Session = Depends(get_supabase_db),
    _: dict = Depends(get_current_user),
) -> MedicalSupplyRead:
    supply = MedicalSupply.model_validate(body)
    session.add(supply)
    session.commit()
    session.refresh(supply)
    return _to_supply_read(supply, 0)


@router.get("/products/{product_id}", response_model=MedicalSupplyRead)
def get_product(
    product_id: int,
    session: Session = Depends(get_supabase_db),
) -> MedicalSupplyRead:
    supply = _get_supply_or_404(session, product_id)
    return _to_supply_read(supply, compute_stock(session, product_id))


@router.post("/orders/inbound", response_model=SupplyDeliveryRead, status_code=201)
def create_inbound_order(
    body: SupplyDeliveryCreate,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> SupplyDeliveryRead:
    _get_supply_or_404(session, body.supply_id)
    delivery = SupplyDelivery(
        **body.model_dump(),
        user_uuid=str(current_user["id"]),
    )
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return SupplyDeliveryRead.model_validate(delivery)


@router.post("/orders/outbound", response_model=SupplyConsumptionRead, status_code=201)
def create_outbound_order(
    body: SupplyConsumptionCreate,
    session: Session = Depends(get_supabase_db),
    current_user: dict = Depends(get_current_user),
) -> SupplyConsumptionRead:
    supply = _get_supply_or_404(session, body.supply_id)
    available = compute_stock(session, body.supply_id)
    if body.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient stock for supply '{supply.name}'. "
                f"Available: {available}, requested: {body.quantity}."
            ),
        )
    consumption = SupplyConsumption(
        **body.model_dump(),
        user_uuid=str(current_user["id"]),
    )
    session.add(consumption)
    session.commit()
    session.refresh(consumption)
    return SupplyConsumptionRead.model_validate(consumption)


@router.get("/orders", response_model=list[OrderRead])
def list_orders(session: Session = Depends(get_supabase_db)) -> list[OrderRead]:
    deliveries = session.exec(select(SupplyDelivery)).all()
    consumptions = session.exec(select(SupplyConsumption)).all()

    supply_ids = {d.supply_id for d in deliveries} | {c.supply_id for c in consumptions}
    supplies: dict[int, MedicalSupply] = {}
    if supply_ids:
        rows = session.exec(select(MedicalSupply).where(MedicalSupply.id.in_(supply_ids))).all()
        supplies = {row.id: row for row in rows}

    orders: list[OrderRead] = []
    for delivery in deliveries:
        supply = supplies.get(delivery.supply_id)
        orders.append(
            OrderRead(
                id=delivery.id,
                order_type="inbound",
                supply_id=delivery.supply_id,
                supply_name=supply.name if supply else "",
                quantity=delivery.quantity,
                user_uuid=delivery.user_uuid,
                created_at=delivery.created_at,
                vendor_name=delivery.vendor_name,
                consumption_type=None,
                clinic_id=delivery.clinic_id,
            )
        )
    for consumption in consumptions:
        supply = supplies.get(consumption.supply_id)
        orders.append(
            OrderRead(
                id=consumption.id,
                order_type="outbound",
                supply_id=consumption.supply_id,
                supply_name=supply.name if supply else "",
                quantity=consumption.quantity,
                user_uuid=consumption.user_uuid,
                created_at=consumption.created_at,
                vendor_name=None,
                consumption_type=consumption.consumption_type,
                clinic_id=consumption.clinic_id,
            )
        )

    orders.sort(key=lambda o: o.created_at, reverse=True)
    return orders
