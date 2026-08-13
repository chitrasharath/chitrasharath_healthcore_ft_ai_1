"""LLM structured metadata extraction with heuristic fallback."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.llm import LlmCallError, LlmConfigError, chat_json

_SYSTEM = """You extract structured metadata from HealthCore institutional RFP documents.
Return ONLY a JSON object with keys:
client_name, client_country (US or UK or null), program_type,
covered_population (verbatim string or null), covered_population_n (integer or null),
deadline (string or null), budget_range (string or null),
open_questions (array of strings for missing/unclear fields).

Rules:
- Never invent headcount, budget, names, or patient data.
- If a field is missing or ambiguous, set it null and add an open_question.
- client_country must be US, UK, or null.
- covered_population_n only when a clear integer is present; otherwise null.

Examples:
Formal RFP: Meridian Manufacturing, Austin, 800 employees, occupational health →
{"client_name":"Meridian Manufacturing","client_country":"US","program_type":"occupational health",
"covered_population":"800 employees","covered_population_n":800,"deadline":null,"budget_range":null,"open_questions":[]}

Informal email: Thames Valley University referral partnership (UK) →
{"client_name":"Thames Valley University","client_country":"UK","program_type":"referral network",
"covered_population":null,"covered_population_n":null,"deadline":null,"budget_range":null,
"open_questions":["covered population / student volume not stated"]}
"""


def _parse_population_n(raw: str | None) -> int | None:
    if not raw:
        return None
    match = re.search(r"\b(\d{1,7})\b", raw.replace(",", ""))
    if not match:
        return None
    return int(match.group(1))


def _heuristic_metadata(markdown: str) -> dict[str, Any]:
    text = markdown or ""
    lower = text.lower()
    open_questions: list[str] = [
        "LLM unavailable — metadata extracted with heuristics; please verify"
    ]

    client_name = None
    for pattern in (
        r"Issuing Organization:\s*(.+)",
        r"Client:\s*(.+)",
        r"\*\*Client:\*\*\s*(.+)",
        r"from\s+([A-Z][^\n,]{2,80})\s+\(UK\)",
    ):
        match = re.search(pattern, text, re.I)
        if match:
            client_name = match.group(1).strip().split("\n")[0][:120]
            break

    country = None
    if re.search(r"\b(united kingdom|uk gdpr|\(uk\)|\bUK\b)", text, re.I):
        country = "UK"
    elif re.search(r"\b(united states|\bUSA\b|\bUS\b|HIPAA|Austin,\s*Texas)", text, re.I):
        country = "US"

    program_type = None
    if "occupational" in lower:
        program_type = "occupational health"
    elif "wellness" in lower:
        program_type = "corporate wellness"
    elif "referral" in lower:
        program_type = "referral network"

    covered = None
    pop = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)\s+employees", text, re.I)
    if pop:
        covered = f"{pop.group(1).replace(',', '')} employees"
    students = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)\s+students", text, re.I)
    if students and not covered:
        covered = f"{students.group(1).replace(',', '')} students"

    deadline = None
    due = re.search(r"(?:Proposal Due Date|deadline):\s*(.+)", text, re.I)
    if due:
        deadline = due.group(1).strip().split("\n")[0][:80]

    budget_range = None
    if "budget" in lower:
        bud = re.search(r"budget[^\n]{0,80}", text, re.I)
        if bud:
            budget_range = bud.group(0).strip()[:120]

    covered_n = _parse_population_n(covered)
    for field, value in (
        ("client_name", client_name),
        ("program_type", program_type),
        ("covered_population", covered),
        ("deadline", deadline),
        ("budget_range", budget_range),
    ):
        if not value:
            open_questions.append(f"{field} not found in document")

    return {
        "client_name": client_name,
        "client_country": country,
        "program_type": program_type,
        "covered_population": covered,
        "covered_population_n": covered_n,
        "deadline": deadline,
        "budget_range": budget_range,
        "open_questions": open_questions,
    }


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    open_questions = data.get("open_questions") or []
    if not isinstance(open_questions, list):
        open_questions = [str(open_questions)]

    country = data.get("client_country")
    if country not in ("US", "UK", None):
        open_questions.append(f"unrecognized client_country: {country!r}")
        country = None

    covered = data.get("covered_population")
    if covered is not None:
        covered = str(covered).strip() or None
    covered_n = data.get("covered_population_n")
    if covered is None:
        covered_n = None
    elif covered_n is not None:
        try:
            covered_n = int(covered_n)
        except (TypeError, ValueError):
            covered_n = None
            open_questions.append("covered_population_n was not a clear integer")
    if covered_n is None and covered:
        covered_n = _parse_population_n(covered)

    for field in (
        "client_name",
        "program_type",
        "deadline",
        "budget_range",
        "covered_population",
    ):
        if not data.get(field):
            q = f"{field} not found in document"
            if q not in open_questions:
                open_questions.append(q)

    return {
        "client_name": data.get("client_name") or None,
        "client_country": country,
        "program_type": data.get("program_type") or None,
        "covered_population": covered,
        "covered_population_n": covered_n,
        "deadline": data.get("deadline") or None,
        "budget_range": data.get("budget_range") or None,
        "open_questions": open_questions,
    }


def extract_metadata(markdown: str) -> dict[str, Any]:
    try:
        data = chat_json(_SYSTEM, markdown[:12000])
        return _normalize(data)
    except (LlmConfigError, LlmCallError):
        return _heuristic_metadata(markdown)
