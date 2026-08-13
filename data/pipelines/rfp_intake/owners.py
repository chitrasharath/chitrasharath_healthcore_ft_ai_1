"""Fixed department owners (CONTEXT §2.1) — name-string validation for Phase 3."""

from __future__ import annotations

DEPARTMENT_OWNERS: dict[str, str] = {
    "revenue": "Tom Callahan",
    "clinical": "Dr. Marcus Reid",
    "compliance": "Claire Whitfield",
}

REQUIRED_DEPARTMENTS: tuple[str, ...] = ("revenue", "clinical", "compliance")


def owner_for(department_id: str) -> str | None:
    return DEPARTMENT_OWNERS.get(department_id)


def is_valid_approver(department_id: str, approver: str) -> bool:
    expected = owner_for(department_id)
    if expected is None:
        return False
    return (approver or "").strip() == expected
