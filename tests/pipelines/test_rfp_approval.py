"""Phase 3 RFP approval unit tests."""

from __future__ import annotations

from data.pipelines.rfp_intake.arbitration import (
    detect_baa_dpa_mismatch,
    detect_capacity_vs_population,
    detect_phi_trigger,
    run_arbitration,
)
from data.pipelines.rfp_intake.final_document import currency_for_country, render_markdown
from data.pipelines.rfp_intake.owners import is_valid_approver
from data.pipelines.rfp_intake.transitions import can_transition


def test_owners_validation():
    assert is_valid_approver("compliance", "Claire Whitfield")
    assert not is_valid_approver("compliance", "Tom Callahan")
    assert is_valid_approver("revenue", "Tom Callahan")


def test_can_transition_legal_path():
    assert can_transition("intake_complete", "drafting")
    assert can_transition("under_evaluation", "waiting_for_approval")
    assert can_transition("waiting_for_approval", "done")
    assert not can_transition("intake_complete", "done")
    assert not can_transition("analyzing", "done")


def test_phi_trigger_from_phi_was_redacted():
    sections = [
        {
            "department_id": "revenue",
            "draft_content": "Clean proposal text without identifiers.",
            "evaluation_results": {
                "contains_phi": False,
                "phi_was_redacted": True,
            },
            "approval_status": "pending",
        }
    ]
    hit = detect_phi_trigger(sections)
    assert hit is not None
    assert hit["trigger_id"] == "phi-detected"
    assert "Claire" in hit["arbiter"]


def test_phi_trigger_cleared_after_compliance_approve_on_section():
    sections = [
        {
            "department_id": "revenue",
            "draft_content": "Clean proposal.",
            "evaluation_results": {
                "contains_phi": False,
                "phi_was_redacted": True,
            },
            "approval_status": "approved",
        }
    ]
    assert detect_phi_trigger(sections) is None


def test_baa_dpa_mismatch_us_missing_baa():
    sections = [
        {
            "department_id": "compliance",
            "draft_content": "We will process data carefully.",
            "key_aspects": {"instrument": None},
            "evaluation_results": {},
        }
    ]
    hit = detect_baa_dpa_mismatch(client_country="US", sections=sections)
    assert hit is not None
    assert hit["trigger_id"] == "baa-dpa-mismatch"


def test_baa_ok_when_present():
    sections = [
        {
            "department_id": "compliance",
            "draft_content": "Includes a Business Associate Agreement (BAA).",
            "key_aspects": {"instrument": "BAA"},
            "evaluation_results": {},
        }
    ]
    assert detect_baa_dpa_mismatch(client_country="US", sections=sections) is None


def test_capacity_skips_when_missing_numbers():
    assert (
        detect_capacity_vs_population(
            metadata={"covered_population_n": None},
            sections=[
                {"department_id": "clinical", "key_aspects": {}},
                {"department_id": "revenue", "key_aspects": {}},
            ],
        )
        is None
    )


def test_capacity_fires_when_under_covered():
    hit = detect_capacity_vs_population(
        metadata={"covered_population_n": 800},
        sections=[
            {
                "department_id": "clinical",
                "key_aspects": {"committed_capacity": 100},
            },
            {"department_id": "revenue", "key_aspects": {}},
        ],
    )
    assert hit is not None
    assert hit["trigger_id"] == "capacity-vs-population"
    assert "Tom" in hit["arbiter"]


def test_arbitration_priority_phi_over_baa():
    sections = [
        {
            "department_id": "compliance",
            "draft_content": "No BAA here.",
            "key_aspects": {},
            "evaluation_results": {"contains_phi": True},
            "approval_status": "pending",
        }
    ]
    hit = run_arbitration(metadata={"client_country": "US"}, sections=sections)
    assert hit is not None
    assert hit["trigger_id"] == "phi-detected"


def test_final_document_currency_and_markdown():
    assert currency_for_country("US") == "USD"
    assert currency_for_country("UK") == "GBP"
    md = render_markdown(
        ticket_id="t1",
        rfp_id="RFP-1",
        client_name="Meridian",
        client_country="US",
        currency="USD",
        sections=[
            {"department_id": "revenue", "draft_content": "Price in USD."},
            {"department_id": "clinical", "draft_content": "Capacity ok."},
            {
                "department_id": "compliance",
                "draft_content": "BAA included.",
            },
        ],
    )
    assert "Currency: USD" in md
    assert "## Revenue" in md
    assert "BAA included" in md


def test_write_pdf_strips_markdown_markers(tmp_path):
    from data.pipelines.rfp_intake.final_document import write_pdf

    md = "# Title\n\n## Section\n\n- **Bold** item with `code`\n\nBody *text*.\n"
    path = tmp_path / "out.pdf"
    write_pdf(md, path)
    assert path.is_file() and path.stat().st_size > 200
    # PDF should not embed raw markdown heading markers as plain text lines
    text = path.read_bytes().decode("latin-1", errors="ignore")
    assert "# Title" not in text
    assert "## Section" not in text
    assert "**Bold**" not in text
