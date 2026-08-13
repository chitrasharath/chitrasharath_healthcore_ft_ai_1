"""Heuristic department-relevant extracts (least privilege)."""

from __future__ import annotations

import re

DEPARTMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "budget",
        "price",
        "pricing",
        "payment",
        "usd",
        "gbp",
        "cost",
        "fee",
        "financial",
        "invoice",
        "contract term",
        "12-month",
        "volume",
        "employees",
        "students",
    ),
    "clinical": (
        "clinic",
        "clinical",
        "occupational",
        "wellness",
        "referral",
        "capacity",
        "staff",
        "on-site",
        "onsite",
        "satellite",
        "program",
        "appointment",
        "coverage",
    ),
    "compliance": (
        "hipaa",
        "gdpr",
        "baa",
        "dpa",
        "data processing",
        "business associate",
        "privacy",
        "compliance",
        "phi",
        "patient data",
        "uk gdpr",
        "regulatory",
    ),
}


def extract_department_snippets(
    markdown: str,
    departments: list[str],
    *,
    max_snippets: int = 8,
    window: int = 220,
) -> dict[str, list[str]]:
    text = markdown or ""
    lower = text.lower()
    out: dict[str, list[str]] = {}
    for dept in departments:
        keywords = DEPARTMENT_KEYWORDS.get(dept, ())
        snippets: list[str] = []
        seen: set[str] = set()
        for kw in keywords:
            start = 0
            while True:
                idx = lower.find(kw, start)
                if idx < 0:
                    break
                lo = max(0, idx - window // 2)
                hi = min(len(text), idx + len(kw) + window // 2)
                snippet = re.sub(r"\s+", " ", text[lo:hi]).strip()
                key = snippet[:80].lower()
                if snippet and key not in seen:
                    seen.add(key)
                    snippets.append(snippet)
                start = idx + len(kw)
                if len(snippets) >= max_snippets:
                    break
            if len(snippets) >= max_snippets:
                break
        if not snippets and text:
            # Thin fallback: first paragraph only (still not full doc dump to workers
            # beyond a short head — synthesizer has metadata separately).
            head = re.sub(r"\s+", " ", text[:400]).strip()
            if head:
                snippets = [head]
        out[dept] = snippets
    return out
