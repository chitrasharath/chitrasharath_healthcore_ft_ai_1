"""PHI validation for memory proposals and consolidations."""

from __future__ import annotations

import re

from app.domains.agent.harness.input_guards import detect_phi
from app.domains.knowledge.pii import redact_pii

# Named patient only — require a capitalized name token so
# "patient has not received…" (generic policy) does not match.
_PATIENT_REF_RE = re.compile(
    r"\b(?:[Pp]atient|[Mm]r\.?|[Mm]rs\.?|[Mm]s\.?)\s+"
    r"[A-Z][a-zA-Z'\-]{1,40}"
    r"(?:\s+[A-Z][a-zA-Z'\-]{1,40})?\b"
)
# Appointment/cancel language tied to a named patient (not staff like Marcus Reid).
_APPOINTMENT_WITH_PATIENT_RE = re.compile(
    r"\b[Pp]atient\s+[A-Z][a-zA-Z'\-]{1,40}(?:\s+[A-Z][a-zA-Z'\-]{1,40})?\b"
    r".{0,80}\b(?:appointment|cancelled|canceled|scheduled|visit)\b"
    r"|\b(?:appointment|cancelled|canceled|scheduled|visit)\b.{0,80}"
    r"\b[Pp]atient\s+[A-Z][a-zA-Z'\-]{1,40}",
)


def validate_no_phi(text: str) -> tuple[bool, list[str]]:
    """Return (ok, reasons). ok=False when patient identifiers / PHI detected."""
    raw = text or ""
    if not raw.strip():
        return True, []

    reasons: list[str] = []
    redacted = redact_pii(raw) or raw
    if redacted != raw and "[REDACTED_" in redacted:
        reasons.append("phi:redact_pii")
    if detect_phi(raw):
        reasons.append("phi:detect_phi")
    if _PATIENT_REF_RE.search(raw):
        reasons.append("phi:patient_ref")
    if _APPOINTMENT_WITH_PATIENT_RE.search(raw):
        reasons.append("phi:named_appointment")
    if reasons:
        return False, reasons
    return True, []
