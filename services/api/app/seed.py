from __future__ import annotations

from datetime import datetime, timezone

from app.domains.procurement.suppliers import store
from app.domains.procurement.suppliers.seed_data import SUPPLIERS_SEED


def run_seed() -> tuple[int, int]:
    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    for record in SUPPLIERS_SEED:
        if store.get_by_name(record["name"]) is not None:
            skipped += 1
            continue
        payload = {**record}
        payload["rate_updated_at"] = now
        store.insert(payload)
        inserted += 1
    return inserted, skipped


def main() -> None:
    inserted, skipped = run_seed()
    print(f"Inserted {inserted} supplier(s). Skipped {skipped} existing.")


if __name__ == "__main__":
    main()
