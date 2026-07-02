from __future__ import annotations

from sqlmodel import Session, select

from app.core.db import supabase_engine
from app.domains.inventory.models import MedicalSupply, SupplyConsumption, SupplyDelivery

SUPPLIES_SEED = [
    {
        "name": "Nitrile gloves (box of 100)",
        "sku": "HCR-PPE-001",
        "category": "ppe",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Surgical mask (pack of 50)",
        "sku": "HCR-PPE-002",
        "category": "ppe",
        "unit": "pack",
        "country": "UK",
    },
    {
        "name": "Adhesive wound dressing",
        "sku": "HCR-WND-001",
        "category": "wound_care",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Rapid strep test kit",
        "sku": "HCR-DIAG-001",
        "category": "diagnostics",
        "unit": "unit",
        "country": "US",
    },
    {
        "name": "Blood glucose test strips (50)",
        "sku": "HCR-DIAG-002",
        "category": "diagnostics",
        "unit": "box",
        "country": "UK",
    },
    {
        "name": "0.9% Saline solution 500ml",
        "sku": "HCR-MED-001",
        "category": "medications",
        "unit": "vial",
        "country": "US",
    },
]

DELIVERIES_SEED = [
    {"sku": "HCR-PPE-001", "quantity": 100, "vendor_name": "MedLine Industries", "clinic_id": 1},
    {"sku": "HCR-PPE-001", "quantity": 50, "vendor_name": "Bound Tree Medical", "clinic_id": 3},
    {"sku": "HCR-PPE-002", "quantity": 200, "vendor_name": "Cardinal Health UK", "clinic_id": 10},
    {"sku": "HCR-DIAG-001", "quantity": 30, "vendor_name": "MedLine Industries", "clinic_id": 5},
]

CONSUMPTIONS_SEED = [
    {"sku": "HCR-PPE-001", "quantity": 20, "consumption_type": "clinical_use", "clinic_id": 1},
    {"sku": "HCR-PPE-001", "quantity": 5, "consumption_type": "expiry_waste", "clinic_id": 3},
    {"sku": "HCR-PPE-002", "quantity": 10, "consumption_type": "clinical_use", "clinic_id": 10},
]


def _get_by_sku(session: Session, sku: str) -> MedicalSupply | None:
    return session.exec(select(MedicalSupply).where(MedicalSupply.sku == sku)).first()


def seed_inventory() -> None:
    if supabase_engine is None:
        print("Skipping inventory seed: DATABASE_URL not configured.")
        return

    with Session(supabase_engine) as session:
        sku_to_id: dict[str, int] = {}
        any_inserted = False

        for record in SUPPLIES_SEED:
            existing = _get_by_sku(session, record["sku"])
            if existing is not None:
                sku_to_id[record["sku"]] = existing.id
                continue
            supply = MedicalSupply.model_validate(record)
            session.add(supply)
            session.commit()
            session.refresh(supply)
            sku_to_id[record["sku"]] = supply.id
            any_inserted = True

        if not any_inserted:
            print("Inventory supplies the same: supplies already exist; skipping order seed.")
            return

        for record in DELIVERIES_SEED:
            session.add(
                SupplyDelivery(
                    supply_id=sku_to_id[record["sku"]],
                    quantity=record["quantity"],
                    vendor_name=record["vendor_name"],
                    clinic_id=record["clinic_id"],
                    user_uuid="1",
                )
            )

        for record in CONSUMPTIONS_SEED:
            session.add(
                SupplyConsumption(
                    supply_id=sku_to_id[record["sku"]],
                    quantity=record["quantity"],
                    consumption_type=record["consumption_type"],
                    clinic_id=record["clinic_id"],
                    user_uuid="1",
                )
            )

        session.commit()
        print(
            f"Inventory seed complete: {len(SUPPLIES_SEED)} supplies, "
            f"{len(DELIVERIES_SEED)} deliveries, {len(CONSUMPTIONS_SEED)} consumptions."
        )
