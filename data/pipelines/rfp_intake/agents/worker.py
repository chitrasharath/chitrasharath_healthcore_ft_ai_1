"""Per-department worker — key_aspects from scoped payload only."""

from __future__ import annotations

import json
from typing import Any

from data.pipelines.rfp_intake.llm import LlmCallError, LlmConfigError, chat_json

_SYSTEM = """You are a HealthCore department intake worker.
Given ONLY shared metadata + department-relevant extracts, produce key_aspects.
Return JSON:
{"key_aspects": [string, ...], "open_questions": [string, ...]}

Rules:
- Never invent headcount, budget, PHI, or patient identifiers.
- If covered population / volume is missing, add an open_question.
- Stay within your department_id scope.
- Do not resolve cross-department conflicts.
"""


def run_worker(payload: dict[str, Any]) -> dict[str, Any]:
    department_id = payload.get("department_id")
    user = json.dumps(payload, ensure_ascii=True)[:8000]
    try:
        data = chat_json(
            _SYSTEM + f"\nYour department_id is: {department_id}",
            user,
        )
        aspects = data.get("key_aspects") or []
        questions = data.get("open_questions") or []
        if not isinstance(aspects, list):
            aspects = [str(aspects)]
        if not isinstance(questions, list):
            questions = [str(questions)]
    except (LlmConfigError, LlmCallError):
        aspects = [f"{department_id}: LLM unavailable — review shared metadata manually"]
        questions = ["LLM unavailable — worker deferred to human"]

    shared = payload.get("shared_metadata") or {}
    if department_id in ("revenue", "clinical") and not shared.get("covered_population"):
        q = "covered population / volume not stated"
        if q not in questions:
            questions.append(q)

    if department_id == "compliance":
        country = shared.get("client_country")
        if country == "US":
            aspects.append("US client — BAA (HIPAA) clause required")
        elif country == "UK":
            aspects.append("UK client — DPA / UK GDPR clause required")
        elif not country:
            questions.append("client_country unknown — cannot select BAA vs DPA yet")
        if payload.get("contains_phi"):
            aspects.append("PHI flagged during intake — Compliance human review required")

    return {"key_aspects": aspects, "open_questions": questions}
