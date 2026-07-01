from __future__ import annotations

VALID_CLINICS: dict[str, str] = {
    "US-TX-01": "US",
    "US-TX-02": "US",
    "US-TX-03": "US",
    "US-FL-01": "US",
    "US-FL-02": "US",
    "US-FL-03": "US",
    "US-GA-01": "US",
    "US-GA-02": "US",
    "US-GA-03": "US",
    "UK-LON-01": "UK",
    "UK-LON-02": "UK",
    "UK-MAN-01": "UK",
}

VALID_CATEGORIES = frozenset(
    {"APPOINTMENT", "BILLING", "CLINICAL_CARE", "ACCESSIBILITY", "ADMINISTRATIVE"}
)

VALID_CSV_STATUSES = frozenset({"OPEN", "CLOSED", "DISCARDED"})

VALID_STATUSES = frozenset({"open", "in_progress", "resolved", "discarded"})

VALID_ORIGINS = frozenset({"customer", "branch", "internal"})

VALID_CLINIC_BRANCHES = frozenset(VALID_CLINICS.keys())

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

RULE_LABELS: dict[str, str] = {
    "invalid_clinic_id": "Invalid or missing clinic_id",
    "country_clinic_mismatch": "Country/clinic mismatch",
    "invalid_category": "Invalid or missing category",
    "empty_description": "Empty description",
    "missing_patient_id": "Missing patient_id",
    "closed_no_score": "Closed case, no score",
    "score_out_of_range": "Satisfaction score out of range",
}
