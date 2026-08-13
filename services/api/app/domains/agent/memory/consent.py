"""Consent-intent classifier (approve / edit / reject / new_question)."""

from __future__ import annotations

import json
import logging
import re
from typing import Callable

import httpx

from app.domains.agent.memory.schemas import MemoryDecision, MemoryProposal

logger = logging.getLogger(__name__)

_CONSENT_SYSTEM = """Classify the staff reply to a memory-consent question.
A proposal was shown asking to approve, edit, or reject saving a memory.
Return ONLY JSON:
{"decision":"approve"|"edit"|"reject"|"new_question","edited_text":null|"…"}

- approve: yes / approve / save it / ok / sure (no replacement text)
- reject: no / reject / don't save / discard
- edit: user supplies corrected wording to save instead
  (e.g. "edit: …", "save it as: …", "actually, remember: …")
  Put the corrected memory text in edited_text.
- new_question: the user ignored consent and asked something else
"""


def _parse_json_content(content: str) -> dict:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _heuristic_consent(reply: str) -> MemoryDecision | None:
    text = (reply or "").strip()
    lower = text.lower()
    if not text:
        return MemoryDecision(decision="new_question")
    if lower in {"approve", "yes", "y", "ok", "okay", "sure", "save", "save it"}:
        return MemoryDecision(decision="approve")
    if lower in {"reject", "no", "n", "don't save", "dont save", "discard"}:
        return MemoryDecision(decision="reject")
    for prefix in ("edit:", "save it as:", "actually, remember:", "remember:"):
        if lower.startswith(prefix):
            edited = text[len(prefix) :].strip()
            if edited:
                return MemoryDecision(decision="edit", edited_text=edited)
    return None


def _default_classify(reply: str, proposal: MemoryProposal) -> MemoryDecision:
    heur = _heuristic_consent(reply)
    if heur is not None and heur.decision in {"approve", "reject", "edit"}:
        return heur

    from app.core.config import settings

    if not settings.llm_api_key:
        return heur or MemoryDecision(decision="new_question")

    url = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    user_msg = (
        f"PENDING MEMORY:\n{proposal.text}\n\nSTAFF REPLY:\n{reply}\n"
    )
    payload = {
        "model": settings.generation_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _CONSENT_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = client.post(url, headers=headers, json=payload)
        if response.status_code < 200 or response.status_code >= 300:
            return heur or MemoryDecision(decision="new_question")
        content = (
            (response.json().get("choices") or [{}])[0]
            .get("message", {})
            .get("content")
        )
        if not isinstance(content, str):
            return heur or MemoryDecision(decision="new_question")
        raw = _parse_json_content(content)
        decision = str(raw.get("decision") or "").strip().lower()
        if decision not in {"approve", "edit", "reject", "new_question"}:
            return heur or MemoryDecision(decision="new_question")
        edited = raw.get("edited_text")
        edited_text = str(edited).strip() if edited else None
        if decision == "edit" and not edited_text:
            return MemoryDecision(decision="new_question")
        return MemoryDecision(decision=decision, edited_text=edited_text)  # type: ignore[arg-type]
    except Exception:
        logger.warning("Consent classifier failed", exc_info=True)
        return heur or MemoryDecision(decision="new_question")


ClassifyFn = Callable[[str, MemoryProposal], MemoryDecision]
classify_fn: ClassifyFn = _default_classify
