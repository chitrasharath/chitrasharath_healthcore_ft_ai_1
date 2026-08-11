"""Thin PHI adapter over existing HealthCore detectors."""

from __future__ import annotations

import logging
import re

from app.domains.agent.harness.input_guards import detect_phi
from app.domains.agent.memory.phi import validate_no_phi
from app.domains.knowledge.pii import redact_pii

logger = logging.getLogger(__name__)

_PATIENT_NAME_RE = re.compile(
    r"\b(?:[Pp]atient|[Mm]r\.?|[Mm]rs\.?|[Mm]s\.?)\s+"
    r"[A-Z][a-zA-Z'\-]{1,40}"
    r"(?:\s+[A-Z][a-zA-Z'\-]{1,40})?\b"
)
_DIAGNOSIS_LINE_RE = re.compile(
    r"(?im)^.*\b(diagnos(?:is|ed)|condition)\b.*$",
)


def scan_and_redact(markdown: str) -> tuple[str, bool, list[str]]:
    """Return (redacted_text, contains_phi, reasons). Never log raw PHI."""
    text = markdown or ""
    ok, reasons = validate_no_phi(text)
    flagged = (not ok) or detect_phi(text)
    redacted = redact_pii(text) or text
    if flagged:
        redacted = _PATIENT_NAME_RE.sub("[REDACTED_NAME]", redacted)
        redacted = _DIAGNOSIS_LINE_RE.sub("[REDACTED_CLINICAL_SUMMARY]", redacted)
        logger.info("RFP PHI scan flagged contains_phi=true reasons=%s", reasons or ["detect_phi"])
    return redacted, flagged, list(reasons)
