"""Lightweight PII screen for MCP structured logs (local copy — no services/api import)."""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "[REDACTED_EMAIL]"),
    (
        re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
    (re.compile(r"\bMRN[-:\s]?\d{5,}\b", re.I), "[REDACTED_MRN]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_ID]"),
]


def redact_pii(text: str | None) -> str | None:
    if text is None:
        return None
    redacted = text
    for pattern, replacement in _PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
