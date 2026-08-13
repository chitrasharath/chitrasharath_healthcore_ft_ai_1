"""Idempotent demo staff users with clinic_id for agent memory Cycles A/B.

Dev-only passwords — create-if-missing; never overwrite existing accounts.
"""

from __future__ import annotations

import logging

from app.domains.auth.password import hash_password
from app.domains.users import store

logger = logging.getLogger(__name__)

# Inventory catalog ids as strings: "2"=Austin North, "7"=London Canary Wharf.
_DEMO_USERS: list[dict[str, str | None]] = [
    {
        "email": "memory-north@example.com",
        "name": "Memory North Demo",
        "password": "memory-demo-1",
        "clinic_id": "2",
    },
    {
        "email": "memory-uk@example.com",
        "name": "Memory UK Demo",
        "password": "memory-demo-1",
        "clinic_id": "7",
    },
    {
        "email": "memory-unassigned@example.com",
        "name": "Memory Unassigned Demo",
        "password": "memory-demo-1",
        "clinic_id": None,
    },
]


def seed_memory_demo_users() -> tuple[int, int]:
    """Create demo memory users if missing. Returns (inserted, skipped)."""
    from datetime import datetime, timezone

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    for record in _DEMO_USERS:
        email = str(record["email"])
        if store.email_exists(email):
            skipped += 1
            continue
        doc: dict = {
            "email": email,
            "name": record["name"],
            "hashed_password": hash_password(str(record["password"])),
            "is_active": True,
            "created_at": now,
        }
        clinic_id = record.get("clinic_id")
        if clinic_id is not None:
            doc["clinic_id"] = str(clinic_id).strip().lower()
        store.insert_user(doc)
        inserted += 1
        logger.info("Seeded memory demo user email=%s clinic_id=%s", email, clinic_id)
    return inserted, skipped
