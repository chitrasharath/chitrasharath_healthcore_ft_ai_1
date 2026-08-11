"""Classifier agent — genuine institutional RFP vs not."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.llm import LlmCallError, LlmConfigError, chat_json

CONFIDENCE_THRESHOLD = 0.5

_SYSTEM = """You classify whether a document is a genuine HealthCore institutional RFP.
HealthCore RFPs ask HealthCore to provide occupational health, corporate wellness,
or referral-network services to an institutional client (employer, university, partner).

Valid: formal RFP PDFs AND informal email-style requests.
Invalid: vendor pitches selling TO HealthCore (e.g. EHR systems), marketing collateral,
internal memos, unrelated forms, or no recognizable proposal request.

Return ONLY JSON:
{"is_rfp": bool, "confidence": float 0-1, "reason": string}

Examples:
1) Meridian Manufacturing occupational health for 800 employees → is_rfp true, high confidence
2) Thames Valley University email asking for referral partnership → is_rfp true
3) Vendor EHR sales deck pitched to HealthCore → is_rfp false
"""

_VENDOR_RE = re.compile(
    r"\b(buy our|sales deck|vendor pitch|electronic health record|EHR system|"
    r"please buy|license(?:s)? for your)\b",
    re.I,
)
_RFP_RE = re.compile(
    r"\b(request for proposal|\bRFP\b|occupational health|corporate wellness|"
    r"referral network|proposal due|issuing organization)\b",
    re.I,
)


def _heuristic_classify(markdown: str) -> dict[str, Any]:
    text = markdown or ""
    if _VENDOR_RE.search(text) and not _RFP_RE.search(text):
        return {
            "is_rfp": False,
            "confidence": 0.7,
            "reason": "Heuristic: vendor/product pitch (LLM unavailable)",
            "needs_human_review": False,
        }
    if _RFP_RE.search(text):
        return {
            "is_rfp": True,
            "confidence": 0.7,
            "reason": "Heuristic: institutional RFP signals (LLM unavailable)",
            "needs_human_review": False,
        }
    return {
        "is_rfp": False,
        "confidence": 0.0,
        "reason": "LLM unavailable and no clear RFP signals — human review required",
        "needs_human_review": True,
    }


def classify_document(markdown: str) -> dict[str, Any]:
    try:
        data = chat_json(_SYSTEM, markdown[:10000])
    except (LlmConfigError, LlmCallError):
        return _heuristic_classify(markdown)

    confidence = data.get("confidence")
    try:
        confidence_f = float(confidence)
    except (TypeError, ValueError):
        confidence_f = 0.0

    is_rfp = bool(data.get("is_rfp"))
    reason = str(data.get("reason") or "")
    needs_human_review = confidence_f < CONFIDENCE_THRESHOLD
    return {
        "is_rfp": is_rfp,
        "confidence": confidence_f,
        "reason": reason,
        "needs_human_review": needs_human_review,
    }
