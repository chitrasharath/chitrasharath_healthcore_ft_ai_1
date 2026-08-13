"""Evaluator agents + aggregate (single DB writer)."""

from __future__ import annotations

import json
import logging
from typing import Any

from data.pipelines.rfp_intake.llm import LlmCallError, LlmConfigError, chat_json
from data.pipelines.rfp_intake.readability import compute_readability
from data.pipelines.rfp_intake.rules import evaluate_rules, rules_for_section

logger = logging.getLogger(__name__)


def evaluate_readability(draft_content: str, *, max_grade: float | None = None) -> dict[str, Any]:
    from app.core.config import settings

    threshold = (
        max_grade
        if max_grade is not None
        else float(settings.rfp_readability_max_grade)
    )
    metrics = compute_readability(draft_content or "")
    if metrics.get("status") == "unavailable":
        return {
            "pass": True,
            "score": None,
            "details": {
                "status": "unavailable",
                "reason": metrics.get("reason"),
                "threshold_grade": threshold,
            },
        }
    grade = metrics.get("flesch_kincaid_grade")
    ease = metrics.get("flesch_reading_ease")
    if grade is None:
        return {
            "pass": True,
            "score": ease,
            "details": {
                "status": "unavailable",
                "reason": "missing_grade",
                "threshold_grade": threshold,
                "flesch_reading_ease": ease,
            },
        }
    passed = float(grade) <= threshold
    return {
        "pass": passed,
        "score": float(grade),
        "details": {
            "status": "ok",
            "flesch_kincaid_grade": float(grade),
            "flesch_reading_ease": ease,
            "threshold_grade": threshold,
        },
    }


def evaluate_relevance(payload: dict[str, Any]) -> dict[str, Any]:
    """LLM check that draft covers key_aspects; open_questions are not 'missing'."""
    from app.core.config import settings

    aspects = payload.get("key_aspects") or []
    if isinstance(aspects, dict):
        aspects = [str(v) for v in aspects.values()]
    aspects = [str(a) for a in aspects]
    opens = {str(q).lower() for q in (payload.get("open_questions") or [])}
    draft = payload.get("draft_content") or ""

    system = (
        "You are a relevance evaluator for HealthCore RFP proposal sections. "
        "Return fenced JSON: {\"missing_aspects\": [string...]}. "
        "List only key_aspects the draft fails to address. "
        "Do NOT list items that are open_questions (those are legitimately unresolved). "
        "If fully covered, missing_aspects must be []."
    )
    user = json.dumps(
        {
            "key_aspects": aspects,
            "open_questions": list(payload.get("open_questions") or []),
            "subtask": payload.get("subtask"),
            "draft_content": draft,
        }
    )
    try:
        data = chat_json(
            system,
            user,
            temperature=0.0,
            model=settings.effective_rfp_evaluator_model,
        )
        missing = [str(x) for x in (data.get("missing_aspects") or [])]
    except (LlmConfigError, LlmCallError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("relevance fallback: %s", type(exc).__name__)
        missing = _heuristic_missing(aspects, draft, opens)

    # Drop anything that matches an open question
    filtered = [m for m in missing if m.lower() not in opens and m.lower() not in {a.lower() for a in opens}]
    # Also drop if the aspect text itself looks like an open question entry
    filtered = [
        m
        for m in filtered
        if not any(m.lower() in o or o in m.lower() for o in opens)
    ]
    return {"pass": len(filtered) == 0, "missing_aspects": filtered}


def _heuristic_missing(aspects: list[str], draft: str, opens: set[str]) -> list[str]:
    text = (draft or "").lower()
    missing: list[str] = []
    for aspect in aspects:
        a = aspect.lower().strip()
        if not a or a in opens:
            continue
        tokens = [t for t in a.replace("/", " ").split() if len(t) > 3][:4]
        if tokens and not any(t in text for t in tokens):
            missing.append(aspect)
    return missing


def evaluate_compliance(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate compliance; auto-redact PHI so a clean draft can proceed to Phase 3."""
    from app.core.config import settings
    from data.pipelines.rfp_intake.phi import contains_rfp_phi, scan_and_redact

    draft = payload.get("draft_content") or ""
    meta = dict(payload.get("shared_metadata") or {})
    rule_ids = payload.get("compliance_rules") or rules_for_section(meta)

    redacted, had_phi, _ = scan_and_redact(draft)
    working = redacted if had_phi else draft
    residual, _ = contains_rfp_phi(working)
    result = evaluate_rules(working, meta, rule_ids=list(rule_ids))
    result["phi_was_redacted"] = bool(had_phi)
    result["redacted_draft"] = working if had_phi else None
    result["contains_phi"] = residual
    if residual:
        # Could not fully scrub — keep hard block
        if not any(v.get("rule_id") == "phi-free" for v in result["violations"]):
            result["violations"].append(
                {"rule_id": "phi-free", "message": "Draft contains patient identifiers / PHI"}
            )
        result["pass"] = False
        return result

    # Scrubbed clean (or never had PHI)
    result["violations"] = [v for v in result["violations"] if v.get("rule_id") != "phi-free"]
    result["pass"] = len(result["violations"]) == 0

    try:
        data = chat_json(
            (
                "You assist compliance review. Return fenced JSON: "
                '{"extra_violations": [{"rule_id": str, "message": str}]}. '
                "Only flag clear BAA/DPA/currency issues not already covered. "
                "Never invent PHI findings (PHI is handled separately)."
            ),
            json.dumps(
                {
                    "draft_content": working,
                    "client_country": meta.get("client_country"),
                    "rule_ids": rule_ids,
                    "deterministic": {
                        k: result[k]
                        for k in ("pass", "rule_ids", "violations", "contains_phi")
                    },
                }
            ),
            temperature=0.0,
            model=settings.effective_rfp_evaluator_model,
        )
        for v in data.get("extra_violations") or []:
            if not isinstance(v, dict):
                continue
            rid = str(v.get("rule_id") or "")
            if rid == "phi-free":
                continue
            msg = str(v.get("message") or "")
            if rid and msg:
                result["violations"].append({"rule_id": rid, "message": msg})
                if rid not in result["rule_ids"]:
                    result["rule_ids"].append(rid)
        result["pass"] = len(result["violations"]) == 0
    except Exception:  # noqa: BLE001 — LLM optional; deterministic rules already applied
        pass
    return result


def aggregate_results(
    *,
    readability: dict[str, Any],
    relevance: dict[str, Any],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    contains_phi = bool(compliance.get("contains_phi"))
    phi_was_redacted = bool(compliance.get("phi_was_redacted"))
    overall = (
        bool(readability.get("pass"))
        and bool(relevance.get("pass"))
        and bool(compliance.get("pass"))
        and not contains_phi
    )
    feedback = compose_feedback(
        readability,
        relevance,
        compliance,
        contains_phi=contains_phi,
    )
    return {
        "readability": readability,
        "relevance": relevance,
        "compliance": compliance,
        "contains_phi": contains_phi,
        "phi_was_redacted": phi_was_redacted,
        "overall_pass": overall,
        "feedback_for_generator": feedback,
        # Hard stop only when scrub failed; successful redact continues normally
        "hard_stop_phi": contains_phi,
        "redacted_draft": compliance.get("redacted_draft"),
    }


def compose_feedback(
    readability: dict[str, Any],
    relevance: dict[str, Any],
    compliance: dict[str, Any],
    *,
    contains_phi: bool,
) -> str:
    if contains_phi:
        return ""  # PHI hard stop — never feed back to generator
    parts: list[str] = []
    missing = relevance.get("missing_aspects") or []
    if missing:
        parts.append("Add coverage of: " + "; ".join(str(m) for m in missing))
    for v in compliance.get("violations") or []:
        rid = v.get("rule_id")
        msg = v.get("message")
        parts.append(f"{msg} (rule `{rid}`)")
    if not readability.get("pass"):
        details = readability.get("details") or {}
        grade = details.get("flesch_kincaid_grade") or readability.get("score")
        thresh = details.get("threshold_grade", 12)
        parts.append(
            f"Reduce reading grade from {grade} to ≤{thresh}: shorten sentences"
        )
    feedback = ". ".join(parts).strip()
    if not feedback and not (
        readability.get("pass") and relevance.get("pass") and compliance.get("pass")
    ):
        # Guard: never emit empty/generic feedback on failure
        parts = ["Revise section to address failed evaluation criteria"]
        if compliance.get("violations"):
            parts.append(
                "rules: "
                + ", ".join(v.get("rule_id", "?") for v in compliance["violations"])
            )
        feedback = ". ".join(parts)
    return feedback
