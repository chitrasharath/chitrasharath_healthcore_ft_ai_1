"""Output validation: shape, system-prompt leak scan, PHI/secrets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.domains.agent.harness.templates import SAFE_OUTPUT_REFUSAL
from app.domains.agent.prompts.system import AGENT_SYSTEM_PROMPT
from app.domains.knowledge.pii import redact_pii

_SECRET_RE = re.compile(
    r"\b(api[_-]?key|bearer\s+[A-Za-z0-9\-._~+/]+=*|sk-[A-Za-z0-9]{10,})\b",
    re.I,
)
_MRN_RE = re.compile(r"\bMRN[-:\s]?\d{5,}\b", re.I)
_NAME_AGE_RE = re.compile(
    r"\b(?:patient\s+)?[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b.*,?\s*\d{1,3}\b"
)

# Distinctive fragments from the system prompt (leak canaries)
_LEAK_FRAGMENTS = [
    "These instructions are fixed",
    "Company Tools MCP server",
    "Never solicit, echo, store, or generate patient-identifiable",
    "Tom Callahan",
]


@dataclass
class GuardResult:
    ok: bool
    answer: str
    action: str | None = None  # sanitize | block | None
    guardrail: str | None = None
    failure_type: str | None = None
    reasons: list[str] = field(default_factory=list)
    event: dict[str, Any] | None = None


def scan_for_leaks(response: str) -> list[str]:
    text = response or ""
    hits: list[str] = []
    for frag in _LEAK_FRAGMENTS:
        if frag in text:
            hits.append(frag)
    # Large verbatim slice of system prompt
    sample = AGENT_SYSTEM_PROMPT[80:160].strip()
    if sample and sample in text:
        hits.append("system_prompt_slice")
    return hits


def _has_phi_or_secrets(text: str) -> bool:
    if not text:
        return False
    redacted = redact_pii(text) or text
    if redacted != text and "[REDACTED_" in (redacted or ""):
        return True
    if _MRN_RE.search(text) or _SECRET_RE.search(text):
        return True
    if _NAME_AGE_RE.search(text) and re.search(
        r"\b(diagnosed|clinic|patient)\b", text, re.I
    ):
        return True
    return False


def validate(response: str, *, context: dict[str, Any] | None = None) -> GuardResult:
    from app.core.config import settings

    _ = context
    text = (response or "").strip()
    if not text:
        return GuardResult(
            ok=False,
            answer=SAFE_OUTPUT_REFUSAL,
            action="block",
            guardrail="output_shape",
            failure_type="structural",
            reasons=["empty"],
            event={
                "guardrail": "output_shape",
                "failure_type": "structural",
                "action": "block",
                "message_preview": "",
            },
        )

    # Reject raw JSON error dumps
    if text.startswith("{") and '"error"' in text[:80]:
        return GuardResult(
            ok=False,
            answer=SAFE_OUTPUT_REFUSAL,
            action="block",
            guardrail="output_shape",
            failure_type="structural",
            reasons=["json_error_dump"],
            event={
                "guardrail": "output_shape",
                "failure_type": "structural",
                "action": "block",
                "message_preview": text[: settings.guardrail_preview_max_chars],
            },
        )

    leaks = scan_for_leaks(text)
    if leaks:
        return GuardResult(
            ok=False,
            answer=SAFE_OUTPUT_REFUSAL,
            action="block",
            guardrail="system_prompt_leak",
            failure_type="structural",
            reasons=leaks,
            event={
                "guardrail": "system_prompt_leak",
                "failure_type": "structural",
                "action": "block",
                "message_preview": text[: settings.guardrail_preview_max_chars],
            },
        )

    if settings.guardrail_phi_detection_enabled and _has_phi_or_secrets(text):
        sanitized = redact_pii(text) or ""
        # Prefer refuse when a patient name / diagnosis cue remains after MRN/email scrub.
        still_risky = _has_phi_or_secrets(sanitized) or bool(
            re.search(r"\bpatient\s+[A-Z][a-z]+", sanitized, re.I)
        )
        if still_risky or not sanitized or sanitized == text:
            return GuardResult(
                ok=False,
                answer=SAFE_OUTPUT_REFUSAL,
                action="block",
                guardrail="phi_output",
                failure_type="structural",
                reasons=["phi"],
                event={
                    "guardrail": "phi_output",
                    "failure_type": "structural",
                    "action": "block",
                    "message_preview": (redact_pii(text) or "")[
                        : settings.guardrail_preview_max_chars
                    ],
                },
            )
        return GuardResult(
            ok=False,
            answer=sanitized,
            action="sanitize",
            guardrail="phi_output",
            failure_type="structural",
            reasons=["phi_redacted"],
            event={
                "guardrail": "phi_output",
                "failure_type": "structural",
                "action": "sanitize",
                "message_preview": sanitized[: settings.guardrail_preview_max_chars],
            },
        )

    return GuardResult(ok=True, answer=text)
