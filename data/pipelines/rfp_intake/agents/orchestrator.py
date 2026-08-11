"""Orchestrator — departments_needed (compliance always on)."""

from __future__ import annotations

from typing import Any

VALID_DEPARTMENTS = ("revenue", "clinical", "compliance")


def determine_departments(
    metadata: dict[str, Any],
    markdown: str,
) -> tuple[list[str], list[str]]:
    """Return (departments_needed, open_questions). Never empty."""
    open_questions: list[str] = []
    text = (markdown or "").lower()
    program = str(metadata.get("program_type") or "").lower()

    # Defaults for institutional RFPs
    needed = {"compliance", "revenue", "clinical"}

    # Soft signals — still keep all three for canonical types; record inference
    mentions_any = any(
        token in text or token in program
        for token in (
            "occupational",
            "wellness",
            "referral",
            "budget",
            "clinic",
            "hipaa",
            "gdpr",
            "baa",
            "dpa",
            "contract",
            "employees",
            "students",
        )
    )
    if not mentions_any and not metadata.get("program_type"):
        open_questions.append(
            "departments inferred as revenue+clinical+compliance — document did not name departmental needs"
        )

    # compliance is mandatory even if somehow stripped
    needed.add("compliance")
    ordered = [d for d in VALID_DEPARTMENTS if d in needed]
    if not ordered:
        ordered = list(VALID_DEPARTMENTS)
        open_questions.append("fallback to all departments — empty departments_needed prevented")
    return ordered, open_questions
