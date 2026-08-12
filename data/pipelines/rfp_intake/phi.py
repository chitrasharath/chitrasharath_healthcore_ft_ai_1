"""Thin PHI adapter for RFP drafts — stricter than CX-agent chat heuristics."""

from __future__ import annotations

import logging
import re

from app.domains.knowledge.pii import redact_pii

logger = logging.getLogger(__name__)

# Named patient only (capitalized name) — "patient names" (generic) must NOT match
_NAMED_PATIENT_RE = re.compile(
    r"\b(?:[Pp]atient|[Mm]r\.?|[Mm]rs\.?|[Mm]s\.?)\s+"
    r"[A-Z][a-zA-Z'\-]{1,40}"
    r"(?:\s+[A-Z][a-zA-Z'\-]{1,40})?\b"
)
_BOILERPLATE_NAME_TOKENS = frozenset(
    {"names", "name", "data", "information", "records", "identifiers", "privacy"}
)
_DIAGNOSIS_WITH_NAME_RE = re.compile(
    r"(?i)\b(?:diagnosed|diagnosis|condition)\b.{0,60}"
    r"\b(?:[Pp]atient|[Mm]r\.?|[Mm]rs\.?|[Mm]s\.?)\s+[A-Z]"
    r"|"
    r"\b(?:[Pp]atient|[Mm]r\.?|[Mm]rs\.?|[Mm]s\.?)\s+[A-Z][a-zA-Z'\-]*.{0,60}"
    r"\b(?:diagnosed|diagnosis|condition)\b"
)
# Sentence/clause only — never wipe an entire multi-sentence draft
_DIAGNOSIS_SPAN_RE = re.compile(
    r"(?i)[^.!?\n]*\b(diagnos(?:is|ed)\s+with|diagnosed)\b[^.!?\n]*[.!]?",
)


def contains_rfp_phi(text: str) -> tuple[bool, list[str]]:
    """RFP-safe PHI check: real identifiers only, not compliance boilerplate.

    Does **not** use CX-agent ``detect_phi`` (title-case + headcount-as-age +
    "clinic" false-positives on institutional proposals).
    """
    raw = text or ""
    if not raw.strip():
        return False, []

    reasons: list[str] = []
    scrubbed = redact_pii(raw) or raw
    if scrubbed != raw and "[REDACTED_" in scrubbed:
        reasons.append("phi:redact_pii")

    for match in _NAMED_PATIENT_RE.finditer(raw):
        token = match.group(0).split(None, 1)[-1].split()[0]
        if token.lower() in _BOILERPLATE_NAME_TOKENS:
            continue
        reasons.append("phi:named_patient")
        break

    if _DIAGNOSIS_WITH_NAME_RE.search(raw):
        for match in _DIAGNOSIS_WITH_NAME_RE.finditer(raw):
            lowered = match.group(0).lower()
            if "patient names" in lowered or "patient name" in lowered:
                continue
            reasons.append("phi:diagnosis_with_name")
            break

    return (len(reasons) > 0), reasons


def scan_and_redact(markdown: str) -> tuple[str, bool, list[str]]:
    """Return (redacted_text, original_had_phi, reasons). Never log raw PHI.

    The bool is True when the **source** contained PHI (Phase 1 contract), even
    if the returned text is clean after scrubbing.
    """
    text = markdown or ""
    had_phi, reasons = contains_rfp_phi(text)
    redacted = redact_pii(text) or text
    if not had_phi:
        return redacted, False, []

    redacted = _NAMED_PATIENT_RE.sub("[REDACTED_NAME]", redacted)
    redacted = _DIAGNOSIS_SPAN_RE.sub("[REDACTED_CLINICAL_SUMMARY]", redacted)
    still, still_reasons = contains_rfp_phi(redacted)
    logger.info(
        "RFP PHI scan original_had_phi=true residual=%s reasons=%s",
        still,
        still_reasons or reasons,
    )
    return redacted, True, list(reasons)
