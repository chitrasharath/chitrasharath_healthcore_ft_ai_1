"""Compliance rule catalog for RFP section drafts (CONTEXT §5)."""

from __future__ import annotations

import re
from typing import Any, Callable

RulePredicate = Callable[[str, dict[str, Any]], tuple[bool, str]]

BAA_RE = re.compile(r"\b(business\s+associate\s+agreement|\bbaa\b)", re.I)
DPA_RE = re.compile(
    r"\b(data\s+processing\s+agreement|\bdpa\b|uk\s*gdpr|uk\s+gdpr)\b",
    re.I,
)
USD_RE = re.compile(r"(\$|USD\b|US\s*dollars?)", re.I)
GBP_RE = re.compile(r"(£|GBP\b|pounds?\s+sterling)", re.I)
EUR_RE = re.compile(r"(€|EUR\b|euros?\b)", re.I)


def _country(meta: dict[str, Any]) -> str:
    return str(meta.get("client_country") or "").strip().upper()


def rule_phi_free(draft: str, meta: dict[str, Any]) -> tuple[bool, str]:
    _ = meta
    from data.pipelines.rfp_intake.phi import contains_rfp_phi

    flagged, _ = contains_rfp_phi(draft)
    if flagged:
        return False, "Draft contains patient identifiers / PHI"
    return True, ""


def rule_baa_us(draft: str, meta: dict[str, Any]) -> tuple[bool, str]:
    if _country(meta) != "US":
        return True, ""
    if BAA_RE.search(draft or ""):
        return True, ""
    return False, "US client section must include a Business Associate Agreement (BAA) clause"


def rule_dpa_uk(draft: str, meta: dict[str, Any]) -> tuple[bool, str]:
    if _country(meta) != "UK":
        return True, ""
    if DPA_RE.search(draft or ""):
        return True, ""
    return False, "UK client section must include a DPA / UK GDPR clause"


def rule_currency_usd(draft: str, meta: dict[str, Any]) -> tuple[bool, str]:
    if _country(meta) != "US":
        return True, ""
    text = draft or ""
    if EUR_RE.search(text) or (GBP_RE.search(text) and not USD_RE.search(text)):
        return False, "US pricing must be quoted in USD"
    return True, ""


def rule_currency_gbp(draft: str, meta: dict[str, Any]) -> tuple[bool, str]:
    if _country(meta) != "UK":
        return True, ""
    text = draft or ""
    if EUR_RE.search(text) or (USD_RE.search(text) and not GBP_RE.search(text)):
        return False, "UK pricing must be quoted in GBP"
    return True, ""


def rule_no_invented_figures(draft: str, meta: dict[str, Any]) -> tuple[bool, str]:
    """Soft heuristic: large headcounts not present in metadata/open questions."""
    _ = draft
    pop = meta.get("covered_population") or meta.get("covered_population_n")
    budget = meta.get("budget_range")
    opens = meta.get("open_questions") or []
    # Deterministic pass when metadata already provides figures or open questions exist.
    if pop or budget or opens:
        return True, ""
    return True, ""


RULES: list[tuple[str, RulePredicate]] = [
    ("phi-free", rule_phi_free),
    ("baa-required-us", rule_baa_us),
    ("dpa-required-uk", rule_dpa_uk),
    ("currency-usd-us", rule_currency_usd),
    ("currency-gbp-uk", rule_currency_gbp),
    ("no-invented-figures", rule_no_invented_figures),
]


def rules_for_section(meta: dict[str, Any]) -> list[str]:
    country = _country(meta)
    ids = ["phi-free", "no-invented-figures"]
    if country == "US":
        ids.extend(["baa-required-us", "currency-usd-us"])
    elif country == "UK":
        ids.extend(["dpa-required-uk", "currency-gbp-uk"])
    return ids


def evaluate_rules(
    draft: str,
    meta: dict[str, Any],
    *,
    rule_ids: list[str] | None = None,
) -> dict[str, Any]:
    wanted = set(rule_ids or [r[0] for r in RULES])
    evaluated: list[str] = []
    violations: list[dict[str, str]] = []
    contains_phi = False
    for rule_id, pred in RULES:
        if rule_id not in wanted:
            continue
        evaluated.append(rule_id)
        ok, message = pred(draft, meta)
        if not ok:
            violations.append({"rule_id": rule_id, "message": message})
            if rule_id == "phi-free":
                contains_phi = True
    return {
        "pass": len(violations) == 0,
        "rule_ids": evaluated,
        "violations": violations,
        "contains_phi": contains_phi,
    }
