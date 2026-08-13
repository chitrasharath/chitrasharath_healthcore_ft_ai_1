"""Synthesizer — sales-facing 'what to ask whom' summary."""

from __future__ import annotations

import json
import re
from typing import Any

from data.pipelines.rfp_intake.llm import LlmCallError, LlmConfigError, chat_json

_SYSTEM = """You consolidate department key_aspects for Tom Callahan (Revenue Cycle / Sales).
Return JSON:
{
  "summary": "short overview",
  "what_to_ask_whom": [{"department_id": "...", "owner": "...", "asks": [string, ...]}],
  "conflict_flags": [string, ...],
  "open_items": [string, ...]
}

Owners: revenue=Tom Callahan, clinical=Dr. Marcus Reid, compliance=Claire Whitfield.
Surface cross-department contradictions as conflict_flags — do NOT resolve by consensus.
PHI/compliance issues always defer to compliance.
Frame as what Sales should ask whom next.
"""

_OWNERS = {
    "revenue": "Tom Callahan",
    "clinical": "Dr. Marcus Reid",
    "compliance": "Claire Whitfield",
}

_CAPACITY_RE = re.compile(r"capacit|staff|clinic|site|cover", re.I)
_POP_RE = re.compile(r"population|employee|student|headcount|volume", re.I)


def _detect_conflicts(worker_results: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    clinical = worker_results.get("clinical") or {}
    revenue = worker_results.get("revenue") or {}
    clinical_text = " ".join(str(x) for x in (clinical.get("key_aspects") or []))
    revenue_text = " ".join(str(x) for x in (revenue.get("key_aspects") or []))
    if _CAPACITY_RE.search(clinical_text) and _POP_RE.search(revenue_text):
        # Soft signal — always surface for Tom when both mention capacity/volume themes
        if "cannot" in clinical_text.lower() or "insufficient" in clinical_text.lower():
            flags.append(
                "conflict: capacity vs. population — Tom to reconcile with Clinical"
            )
    compliance = worker_results.get("compliance") or {}
    for aspect in compliance.get("key_aspects") or []:
        if "PHI" in str(aspect):
            flags.append("compliance: PHI flagged — Claire Whitfield review required")
            break
    return flags


def synthesize(
    metadata: dict[str, Any],
    worker_results: dict[str, Any],
    open_questions: list[str],
) -> dict[str, Any]:
    conflict_flags = _detect_conflicts(worker_results)
    payload = {
        "metadata": metadata,
        "worker_results": worker_results,
        "open_questions": open_questions,
        "precomputed_conflict_flags": conflict_flags,
    }
    try:
        data = chat_json(_SYSTEM, json.dumps(payload, ensure_ascii=True)[:10000])
    except (LlmConfigError, LlmCallError, ValueError, TypeError, json.JSONDecodeError):
        data = _fallback_summary(metadata, worker_results, open_questions, conflict_flags)

    flags = data.get("conflict_flags") or []
    if not isinstance(flags, list):
        flags = [str(flags)]
    for f in conflict_flags:
        if f not in flags:
            flags.append(f)

    asks = data.get("what_to_ask_whom") or []
    if not isinstance(asks, list):
        asks = []

    return {
        "summary": str(data.get("summary") or ""),
        "what_to_ask_whom": asks,
        "conflict_flags": flags,
        "open_items": data.get("open_items") or open_questions,
    }


def _fallback_summary(
    metadata: dict[str, Any],
    worker_results: dict[str, Any],
    open_questions: list[str],
    conflict_flags: list[str],
) -> dict[str, Any]:
    asks = []
    for dept, owner in _OWNERS.items():
        result = worker_results.get(dept) or {}
        dept_asks = list(result.get("open_questions") or [])
        if result.get("key_aspects"):
            dept_asks = dept_asks or [f"Review {dept} key aspects"]
        asks.append({"department_id": dept, "owner": owner, "asks": dept_asks})
    client = metadata.get("client_name") or "unknown client"
    return {
        "summary": f"Intake complete for {client}. Review department key aspects and open questions.",
        "what_to_ask_whom": asks,
        "conflict_flags": conflict_flags,
        "open_items": open_questions,
    }
