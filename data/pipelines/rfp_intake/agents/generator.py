"""Per-department proposal section generator."""

from __future__ import annotations

import json
import logging
from typing import Any

from data.pipelines.rfp_intake.llm import chat_json

logger = logging.getLogger(__name__)

DEPT_PROMPTS = {
    "revenue": (
        "You write the Revenue Cycle section: financial terms, payment structure, "
        "and pricing in the client's currency. Never invent headcount or budget."
    ),
    "clinical": (
        "You write the Clinical Operations section: feasibility, clinic/staff capacity, "
        "and sites. Never invent capacity figures; list open items instead."
    ),
    "compliance": (
        "You write the Compliance section: regulatory posture (HIPAA or UK GDPR), "
        "required BAA (US) or DPA/UK GDPR (UK) clause language, and no PHI."
    ),
}


def _currency_for(country: str | None) -> str:
    c = (country or "").upper()
    if c == "UK":
        return "GBP"
    return "USD"


def _system_prompt(department_id: str) -> str:
    base = DEPT_PROMPTS.get(
        department_id,
        "You write one department proposal section for a HealthCore institutional RFP.",
    )
    return (
        f"{base}\n"
        "Output fenced JSON only: {\"draft_content\": \"markdown string\"}.\n"
        "Rules: no patient names/diagnoses/PHI (even illustrative); "
        "US → include a Business Associate Agreement (BAA) clause and USD pricing; "
        "UK → include a Data Processing Agreement / UK GDPR clause and GBP pricing; "
        "unresolved open_questions become an 'Open items / to confirm' bullet list — "
        "never fabricate figures."
    )


def generate_section(payload: dict[str, Any]) -> str:
    """Return markdown draft_content for one department."""
    from app.core.config import settings

    department_id = str(payload.get("department_id") or "")
    meta = dict(payload.get("shared_metadata") or {})
    country = meta.get("client_country")
    currency = meta.get("currency") or _currency_for(str(country) if country else None)
    user_obj = {
        "department_id": department_id,
        "key_aspects": payload.get("key_aspects") or [],
        "open_questions": payload.get("open_questions") or [],
        "shared_metadata": {**meta, "currency": currency},
        "prior_draft": payload.get("prior_draft"),
        "feedback_for_generator": payload.get("feedback_for_generator"),
        "subtask": payload.get("subtask")
        or f"Draft the {department_id} proposal section answering key_aspects.",
    }
    try:
        data = chat_json(
            _system_prompt(department_id),
            json.dumps(user_obj),
            temperature=0.2,
            model=settings.effective_rfp_generator_model,
        )
    except Exception as exc:  # noqa: BLE001 — fall back to deterministic draft
        logger.warning("generator fallback dept=%s: %s", department_id, type(exc).__name__)
        return _fallback_draft(department_id, payload, currency)

    draft = data.get("draft_content")
    if isinstance(draft, str) and draft.strip():
        return draft.strip()
    return _fallback_draft(department_id, payload, currency)


def _fallback_draft(department_id: str, payload: dict[str, Any], currency: str) -> str:
    meta = dict(payload.get("shared_metadata") or {})
    country = str(meta.get("client_country") or "US").upper()
    aspects = payload.get("key_aspects") or []
    if isinstance(aspects, dict):
        aspects = list(aspects.values())
    opens = payload.get("open_questions") or []
    lines = [
        f"## {department_id.capitalize()} proposal section",
        f"Client: {meta.get('client_name') or 'TBD'} ({country})",
        f"Program: {meta.get('program_type') or 'TBD'}",
        "",
        "### Coverage of key aspects",
    ]
    for item in aspects:
        lines.append(f"- {item}")
    if opens:
        lines.append("")
        lines.append("### Open items / to confirm")
        for q in opens:
            lines.append(f"- {q}")
    lines.append("")
    if country == "UK":
        lines.append(
            "### Data Processing Agreement\n"
            "This proposal includes a Data Processing Agreement (DPA) referencing UK GDPR."
        )
        lines.append(f"Pricing will be quoted in {currency} (GBP).")
    else:
        lines.append(
            "### Business Associate Agreement\n"
            "This proposal includes a Business Associate Agreement (BAA) under HIPAA."
        )
        lines.append(f"Pricing will be quoted in {currency} (USD).")
    feedback = payload.get("feedback_for_generator")
    if feedback:
        lines.append("")
        lines.append(f"### Revision notes\n{feedback}")
    return "\n".join(lines)
