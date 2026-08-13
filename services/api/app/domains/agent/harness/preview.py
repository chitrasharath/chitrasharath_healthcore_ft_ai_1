"""Shared preview scrubbing so guardrail logs never retain identifiers."""

from __future__ import annotations

import re

from app.domains.knowledge.pii import redact_pii

_PATIENT_NAME_PREVIEW = re.compile(
    r"\b(?:patient|named|name(?:d)?\s+is)\s*[,:]?\s+"
    r"[A-Za-z][A-Za-z'\-]{1,40}"
    r"(?:\s+[A-Za-z][A-Za-z'\-]{1,40})?\b",
    re.I,
)
_TITLECASE_NAME = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b")
_LOC_PREVIEW = re.compile(
    r"\b(Austin|London|clinic|hospital|branch)\b",
    re.I,
)
_AGE_PHRASE = re.compile(
    r"\b\d{1,3}\s*(?:years?\s*old|yo)\b|\baged?\s+\d{1,3}\b",
    re.I,
)


def scrub_message_preview(text: str | None) -> str:
    """redact_pii + name/location/age phrase scrub for any guardrail event preview."""
    preview = redact_pii(text) or ""
    preview = _PATIENT_NAME_PREVIEW.sub("[REDACTED_NAME]", preview)
    preview = _TITLECASE_NAME.sub("[REDACTED_NAME]", preview)
    preview = _LOC_PREVIEW.sub("[REDACTED_LOC]", preview)
    preview = _AGE_PHRASE.sub("[REDACTED_AGE]", preview)
    return preview
