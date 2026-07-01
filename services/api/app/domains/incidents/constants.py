from __future__ import annotations

VALID_CATEGORIES = frozenset(
    {"APPOINTMENT", "BILLING", "CLINICAL_CARE", "ACCESSIBILITY", "ADMINISTRATIVE"}
)

VALID_STATUSES = frozenset({"open", "in_progress", "resolved", "discarded"})

VALID_ORIGINS = frozenset({"customer", "branch", "internal"})

VALID_CLINIC_BRANCHES = frozenset(
    {
        "US-TX-01",
        "US-TX-02",
        "US-TX-03",
        "US-FL-01",
        "US-FL-02",
        "US-FL-03",
        "US-GA-01",
        "US-GA-02",
        "US-GA-03",
        "UK-LON-01",
        "UK-LON-02",
        "UK-MAN-01",
    }
)

VALID_BRANCHES = VALID_CLINIC_BRANCHES | frozenset({"Central"})

STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "discarded"}),
    "in_progress": frozenset({"resolved", "discarded"}),
    "resolved": frozenset(),
    "discarded": frozenset(),
}

CSV_STATUS_MAP = {
    "OPEN": "open",
    "CLOSED": "resolved",
    "DISCARDED": "discarded",
}

FINAL_STATUSES = frozenset({"resolved", "discarded"})

STATUS_TRANSITION_ORDER = ("in_progress", "discarded", "resolved")

STATUS_DISPLAY = {
    "open": "Open",
    "in_progress": "In progress",
    "resolved": "Resolved",
    "discarded": "Discarded",
}
