"""Phase 2 drafting pipeline unit tests — mock LLM; no live network; no real PHI."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from data.pipelines.rfp_intake.agents.evaluators import (
    aggregate_results,
    compose_feedback,
    evaluate_compliance,
    evaluate_readability,
    evaluate_relevance,
)
from data.pipelines.rfp_intake.agents.generator import generate_section
from data.pipelines.rfp_intake.rules import evaluate_rules
from tests.fixtures.rfp_intake.golden_drafts import (
    UK_COMPLIANCE_DRAFT,
    US_MISSING_BAA,
    US_REVENUE_DRAFT,
)

# Synthetic PHI for detectors only — never logged/asserted as raw success path content
_SYNTH_PHI = "Patient Jane Doe diagnosed with diabetes at Austin clinic."


def test_generator_us_includes_baa_usd():
    with patch(
        "data.pipelines.rfp_intake.agents.generator.chat_json",
        side_effect=Exception("force fallback"),
    ):
        draft = generate_section(
            {
                "department_id": "revenue",
                "key_aspects": ["monthly retainer"],
                "open_questions": ["Confirm covered population"],
                "shared_metadata": {
                    "client_name": "Meridian",
                    "client_country": "US",
                    "program_type": "occupational health",
                },
            }
        )
    assert "Business Associate Agreement" in draft or "BAA" in draft
    assert "USD" in draft
    assert "Open items" in draft
    assert "Confirm covered population" in draft
    # never invent a population number
    assert "800 employees" not in draft


def test_generator_uk_includes_dpa_gbp():
    with patch(
        "data.pipelines.rfp_intake.agents.generator.chat_json",
        side_effect=Exception("force fallback"),
    ):
        draft = generate_section(
            {
                "department_id": "compliance",
                "key_aspects": ["DPA required"],
                "open_questions": [],
                "shared_metadata": {
                    "client_name": "Thames",
                    "client_country": "UK",
                    "program_type": "referral",
                },
            }
        )
    assert "Data Processing Agreement" in draft or "DPA" in draft
    assert "GBP" in draft


def test_readability_pass_fail_and_unavailable():
    with patch(
        "data.pipelines.rfp_intake.agents.evaluators.compute_readability",
        return_value={
            "status": "ok",
            "flesch_kincaid_grade": 10.0,
            "flesch_reading_ease": 55.0,
        },
    ):
        ok = evaluate_readability("short draft")
    assert ok["pass"] is True

    with patch(
        "data.pipelines.rfp_intake.agents.evaluators.compute_readability",
        return_value={
            "status": "ok",
            "flesch_kincaid_grade": 16.0,
            "flesch_reading_ease": 20.0,
        },
    ):
        bad = evaluate_readability("dense draft")
    assert bad["pass"] is False

    with patch(
        "data.pipelines.rfp_intake.agents.evaluators.compute_readability",
        return_value={"status": "unavailable", "reason": "punkt"},
    ):
        soft = evaluate_readability("x")
    assert soft["pass"] is True
    assert soft["details"]["status"] == "unavailable"


@patch("data.pipelines.rfp_intake.agents.evaluators.chat_json")
def test_relevance_missing_and_open_questions(mock_chat: MagicMock):
    mock_chat.return_value = {"missing_aspects": ["clinic staffing capacity"]}
    result = evaluate_relevance(
        {
            "draft_content": "generic text",
            "key_aspects": ["clinic staffing capacity", "payment terms"],
            "open_questions": [],
        }
    )
    assert result["pass"] is False
    assert "clinic staffing capacity" in result["missing_aspects"]

    mock_chat.return_value = {"missing_aspects": ["Confirm headcount"]}
    result2 = evaluate_relevance(
        {
            "draft_content": "covers payment",
            "key_aspects": ["payment terms"],
            "open_questions": ["Confirm headcount"],
        }
    )
    assert result2["pass"] is True
    assert result2["missing_aspects"] == []


def test_compliance_us_uk_currency_and_clean():
    us_bad = evaluate_compliance(
        {
            "draft_content": US_MISSING_BAA,
            "shared_metadata": {"client_country": "US"},
        }
    )
    assert us_bad["pass"] is False
    ids = {v["rule_id"] for v in us_bad["violations"]}
    assert "baa-required-us" in ids

    uk_ok = evaluate_compliance(
        {
            "draft_content": UK_COMPLIANCE_DRAFT,
            "shared_metadata": {"client_country": "UK"},
        }
    )
    assert uk_ok["pass"] is True
    assert "dpa-required-uk" in uk_ok["rule_ids"]

    us_ok = evaluate_compliance(
        {
            "draft_content": US_REVENUE_DRAFT,
            "shared_metadata": {"client_country": "US"},
        }
    )
    assert us_ok["pass"] is True


@patch("data.pipelines.rfp_intake.agents.evaluators.chat_json", side_effect=Exception("no llm"))
def test_phi_redact_clears_for_phase3(_mock_chat: MagicMock):
    result = evaluate_compliance(
        {
            "draft_content": (
                f"Proposal for Meridian with Business Associate Agreement (BAA). "
                f"Pricing in USD. Attachment note: {_SYNTH_PHI}"
            ),
            "shared_metadata": {"client_country": "US"},
        }
    )
    assert result["phi_was_redacted"] is True
    assert result["contains_phi"] is False
    assert result["pass"] is True
    assert result.get("redacted_draft")
    assert "Jane Doe" not in (result.get("redacted_draft") or "")
    assert "BAA" in (result.get("redacted_draft") or "") or "Business Associate" in (
        result.get("redacted_draft") or ""
    )

    agg = aggregate_results(
        readability={"pass": True, "score": 8, "details": {}},
        relevance={"pass": True, "missing_aspects": []},
        compliance=result,
    )
    assert agg["hard_stop_phi"] is False
    assert agg["overall_pass"] is True
    assert agg["phi_was_redacted"] is True


def test_compliance_boilerplate_not_phi():
    """Institutional drafts mentioning PHI/clinic/headcount must not false-positive."""
    draft = (
        "HIPAA applies because the vendor may access protected health information (PHI). "
        "Covering 800 employees at clinic sites. No patient names are used in this proposal. "
        "Business Associate Agreement (BAA). Pricing in USD."
    )
    from data.pipelines.rfp_intake.phi import contains_rfp_phi

    flagged, reasons = contains_rfp_phi(draft)
    assert flagged is False, reasons
    result = evaluate_compliance(
        {"draft_content": draft, "shared_metadata": {"client_country": "US"}}
    )
    assert result["contains_phi"] is False
    assert result["pass"] is True


def test_phi_residual_still_blocks():
    compliance = {
        "pass": False,
        "rule_ids": ["phi-free"],
        "violations": [{"rule_id": "phi-free", "message": "residual"}],
        "contains_phi": True,
        "phi_was_redacted": True,
    }
    agg = aggregate_results(
        readability={"pass": True, "score": 8, "details": {}},
        relevance={"pass": True, "missing_aspects": []},
        compliance=compliance,
    )
    assert agg["hard_stop_phi"] is True
    assert agg["overall_pass"] is False
    assert agg["feedback_for_generator"] == ""


def test_aggregate_and_concurrency_single_writer_shape():
    def _one(name: str) -> dict:
        return {"pass": True, "score": 1, "details": {"evaluator": name}}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(_one, n) for n in ("r", "rel", "c")]
        results = [f.result() for f in futs]

    agg = aggregate_results(
        readability={"pass": True, "score": 9, "details": results[0]},
        relevance={"pass": True, "missing_aspects": []},
        compliance={
            "pass": True,
            "rule_ids": ["phi-free"],
            "violations": [],
            "contains_phi": False,
        },
    )
    assert agg["overall_pass"] is True
    assert "readability" in agg and "relevance" in agg and "compliance" in agg


def test_feedback_is_specific():
    fb = compose_feedback(
        {"pass": False, "score": 16, "details": {"flesch_kincaid_grade": 16, "threshold_grade": 12}},
        {"pass": False, "missing_aspects": ["clinic staffing capacity for 450 employees"]},
        {
            "pass": False,
            "violations": [
                {"rule_id": "baa-required-us", "message": "Add a BAA clause"},
            ],
            "contains_phi": False,
        },
        contains_phi=False,
    )
    assert "clinic staffing capacity" in fb
    assert "baa-required-us" in fb
    assert "16" in fb
    assert "improve the section" not in fb.lower()


def test_rules_deterministic_currency():
    bad = evaluate_rules(
        "Quote is €5000/month",
        {"client_country": "US"},
        rule_ids=["currency-usd-us", "baa-required-us", "phi-free"],
    )
    assert bad["pass"] is False
    assert {v["rule_id"] for v in bad["violations"]} >= {"currency-usd-us", "baa-required-us"}


def test_rollup_non_blocking_logic():
    from app.domains.rfp_intake.store import phase2_rollup
    from app.domains.rfp_intake.models import DepartmentSection

    sections = [
        DepartmentSection(ticket_id="t", department_id="revenue", status="passed"),
        DepartmentSection(
            ticket_id="t", department_id="clinical", status="needs_human_review"
        ),
        DepartmentSection(ticket_id="t", department_id="compliance", status="passed"),
    ]
    needing, complete = phase2_rollup(sections)
    assert needing == 1
    assert complete is True
