"""LLM self-evaluation → MemoryProposal (classifier-style JSON)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable

import httpx

from app.domains.agent.memory.schemas import MemoryProposal, new_proposal_id

logger = logging.getLogger(__name__)

_PROPOSAL_SYSTEM = """You evaluate whether a HealthCore front-desk support turn \
produced durable operational knowledge worth remembering.
Return ONLY JSON:
{"worth_remembering":true|false,"type":"semantic"|"procedural",\
"memory_text":"…","scope_hint":"clinic"|"staff","reasoning":"…"}

Worth remembering:
- Recurring clinic operational corrections / local protocols (no patient data)
- Staff-stated local facts NOT in the published knowledge base
  (clinic hours/schedules, local workarounds, "for this clinic" notes)
- Known incident patterns WITHOUT patient identifiers
- Staff presentation preferences (procedural)

Dismiss (worth_remembering=false):
- One-off factual *questions* answerable from the knowledge base every time
  (published referral SLAs, escalation contacts already in policy docs, fees, coverage)
- Temporary / same-day status (delays *today*, running late *right now*, current outage
  with no recurring pattern) — do not store ephemeral front-desk chatter
- Conversation closing / chit-chat / thanks / greetings
- Anything with patient names, MRNs, or patient-specific clinical details

IMPORTANT: When the staff *states* local hours, schedules, or clinic-specific
ops facts (e.g. "clinic hours are 8am-5pm weekdays"), that IS worth remembering —
even if the assistant reply only confirmed it. Do not dismiss as a knowledge-base lookup.
Recurring patterns ("every Monday morning", "always show units not cases") ARE worth
remembering; "appointments are delayed today" is NOT.

memory_text must be a short PHI-free operational statement when worth_remembering.
Do NOT propose content that merely restates the knowledge-base answer.
"""

# Deterministic rescue when the LLM dismisses clear staff-stated local hours.
_HOURS_STATEMENT = re.compile(
    r"\b("
    r"(?:clinic\s+)?hours?\b.{"
    r"0,40}\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|open|close)|"
    r"(?:open|close[sd]?|we\s+(?:open|close))\b.{"
    r"0,40}\b\d{1,2}(?::\d{2})?\s*(?:am|pm)"
    r")",
    re.I | re.S,
)


def _hours_fallback_text(question: str) -> str | None:
    q = (question or "").strip()
    if not q or not _HOURS_STATEMENT.search(q):
        return None
    # Prefer a short cleaned statement from the staff message.
    text = re.sub(r"\s+", " ", q).strip(" .")
    if len(text) > 180:
        text = text[:177].rstrip() + "…"
    return text


def _hours_fallback_proposal(
    question: str,
    *,
    clinic_id: str,
    staff_id: str,
    trace_id: str | None,
) -> MemoryProposal | None:
    fallback = _hours_fallback_text(question)
    if not fallback:
        return None
    return MemoryProposal(
        proposal_id=new_proposal_id(),
        clinic_id=clinic_id,
        staff_id=staff_id,
        type="semantic",
        text=fallback,
        source_trace_id=trace_id,
        created_at=int(time.time()),
        worth_remembering=True,
        scope_hint="clinic",
        reasoning="hours_statement_fallback",
    )


def _parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _default_propose(
    question: str,
    answer: str,
    *,
    clinic_id: str,
    staff_id: str,
    trace_id: str | None = None,
) -> MemoryProposal:
    from app.core.config import settings

    empty = MemoryProposal(
        proposal_id=new_proposal_id(),
        clinic_id=clinic_id,
        staff_id=staff_id,
        type="semantic",
        text="",
        source_trace_id=trace_id,
        created_at=int(time.time()),
        worth_remembering=False,
        reasoning="no proposal",
    )

    def _or_hours() -> MemoryProposal:
        return (
            _hours_fallback_proposal(
                question,
                clinic_id=clinic_id,
                staff_id=staff_id,
                trace_id=trace_id,
            )
            or empty
        )

    if not settings.llm_api_key:
        return _or_hours()

    url = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    user_msg = f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n"
    payload = {
        "model": settings.generation_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _PROPOSAL_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
            response = client.post(url, headers=headers, json=payload)
        if response.status_code < 200 or response.status_code >= 300:
            return _or_hours()
        content = (
            (response.json().get("choices") or [{}])[0]
            .get("message", {})
            .get("content")
        )
        if not isinstance(content, str):
            return _or_hours()
        raw = _parse_json_content(content)
    except Exception:
        logger.warning("Memory proposal LLM failed", exc_info=True)
        return _or_hours()

    worth = bool(raw.get("worth_remembering"))
    mem_type = str(raw.get("type") or "semantic").strip().lower()
    if mem_type not in {"semantic", "procedural"}:
        mem_type = "semantic"
    text = str(raw.get("memory_text") or "").strip()
    reasoning = str(raw.get("reasoning") or "") or None

    if not (worth and text):
        return _or_hours()

    return MemoryProposal(
        proposal_id=new_proposal_id(),
        clinic_id=clinic_id,
        staff_id=staff_id,
        type=mem_type,  # type: ignore[arg-type]
        text=text,
        source_trace_id=trace_id,
        created_at=int(time.time()),
        worth_remembering=True,
        scope_hint=str(raw.get("scope_hint") or "") or None,
        reasoning=reasoning,
    )


ProposeFn = Callable[..., MemoryProposal]
propose_fn: ProposeFn = _default_propose
