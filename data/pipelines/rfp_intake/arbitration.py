"""Deterministic arbitration node — CONTEXT §7 (no LLM)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.owners import DEPARTMENT_OWNERS
from data.pipelines.rfp_intake.phi import contains_rfp_phi
from data.pipelines.rfp_intake.rules import BAA_RE, DPA_RE, _country


def _section_eval(section: dict[str, Any]) -> dict[str, Any]:
    return dict(section.get("evaluation_results") or {})


def _key_aspects_dict(section: dict[str, Any]) -> dict[str, Any]:
    raw = section.get("key_aspects")
    if isinstance(raw, dict):
        return raw
    return {}


def detect_phi_trigger(sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Fire when residual PHI, Phase-2 redaction flag, or Phase-3 re-scan hits."""
    flagged: list[str] = []
    for section in sections:
        dept = section.get("department_id") or ""
        ev = _section_eval(section)
        draft = section.get("draft_content") or ""
        if ev.get("contains_phi"):
            flagged.append(dept)
            continue
        if ev.get("phi_was_redacted") and section.get("approval_status") != "approved":
            # Redaction is deferred to Compliance — not cleared until approved
            flagged.append(dept)
            continue
        hit, _ = contains_rfp_phi(draft)
        if hit:
            flagged.append(dept)
    if not flagged:
        return None
    return {
        "trigger_id": "phi-detected",
        "arbiter": DEPARTMENT_OWNERS["compliance"],
        "departments": sorted(set(flagged)),
        "forced_action": {
            "action": "request_changes",
            "departments": sorted(set(flagged)),
            "message": "PHI detected or Phase-2 redaction awaiting Compliance review",
        },
    }


def detect_baa_dpa_mismatch(
    *,
    client_country: str | None,
    sections: list[dict[str, Any]],
) -> dict[str, Any] | None:
    country = _country({"client_country": client_country})
    compliance = next(
        (s for s in sections if s.get("department_id") == "compliance"),
        None,
    )
    if compliance is None:
        return None
    aspects = _key_aspects_dict(compliance)
    instrument = str(aspects.get("instrument") or "").upper() or None
    draft = compliance.get("draft_content") or ""

    wrong = False
    if country == "US":
        has_baa = instrument == "BAA" or bool(BAA_RE.search(draft))
        has_wrong = bool(DPA_RE.search(draft)) and not has_baa
        wrong = (not has_baa) or has_wrong
    elif country == "UK":
        has_dpa = instrument == "DPA" or bool(DPA_RE.search(draft))
        has_wrong = bool(BAA_RE.search(draft)) and not has_dpa
        wrong = (not has_dpa) or has_wrong
    else:
        return None

    if not wrong:
        return None
    return {
        "trigger_id": "baa-dpa-mismatch",
        "arbiter": DEPARTMENT_OWNERS["compliance"],
        "departments": ["compliance"],
        "forced_action": {
            "action": "request_changes",
            "departments": ["compliance"],
            "message": f"Country {country} requires the correct BAA/DPA instrument",
        },
    }


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def detect_capacity_vs_population(
    *,
    metadata: dict[str, Any],
    sections: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Only fires when both numeric sides exist — never invent."""
    pop = _as_number(metadata.get("covered_population_n"))
    revenue = next((s for s in sections if s.get("department_id") == "revenue"), None)
    clinical = next((s for s in sections if s.get("department_id") == "clinical"), None)
    if revenue is not None:
        vol = _as_number(_key_aspects_dict(revenue).get("contract_volume"))
        if vol is not None:
            pop = vol if pop is None else max(pop, vol)
    if pop is None:
        return None  # missing population → open question, not false conflict

    capacity = None
    sites_n = None
    if clinical is not None:
        aspects = _key_aspects_dict(clinical)
        capacity = _as_number(aspects.get("committed_capacity"))
        sites = aspects.get("sites")
        if isinstance(sites, list):
            sites_n = float(len(sites))
        else:
            sites_n = _as_number(sites)
    if capacity is None and sites_n is None:
        return None  # missing capacity → open question

    cover = capacity if capacity is not None else sites_n
    if cover is None or cover >= pop:
        return None
    return {
        "trigger_id": "capacity-vs-population",
        "arbiter": DEPARTMENT_OWNERS["revenue"],
        "departments": ["revenue", "clinical"],
        "forced_action": {
            "action": "request_changes",
            "departments": ["revenue", "clinical"],
            "message": (
                f"Committed capacity/sites ({cover}) cannot cover population ({pop})"
            ),
        },
    }


def run_arbitration(
    *,
    metadata: dict[str, Any],
    sections: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return highest-priority trigger or None. PHI > BAA/DPA > capacity."""
    phi = detect_phi_trigger(sections)
    if phi is not None:
        return phi
    baa = detect_baa_dpa_mismatch(
        client_country=metadata.get("client_country"),
        sections=sections,
    )
    if baa is not None:
        return baa
    return detect_capacity_vs_population(metadata=metadata, sections=sections)
