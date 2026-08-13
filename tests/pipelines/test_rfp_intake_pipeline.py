from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data.pipelines.rfp_intake.agents.classifier import CONFIDENCE_THRESHOLD, classify_document
from data.pipelines.rfp_intake.agents.orchestrator import determine_departments
from data.pipelines.rfp_intake.agents.synthesizer import synthesize
from data.pipelines.rfp_intake.agents.worker import run_worker
from data.pipelines.rfp_intake.extracts import extract_department_snippets
from data.pipelines.rfp_intake.metadata import extract_metadata
from data.pipelines.rfp_intake.phi import scan_and_redact
from data.pipelines.rfp_intake.readability import compute_readability

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rfp_intake"


def _md(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_readability_ok_or_unavailable():
    metrics = compute_readability(_md("meridian_formal.md"))
    assert "status" in metrics
    assert metrics["status"] in ("ok", "unavailable")


def test_readability_empty_degrades():
    assert compute_readability("")["status"] == "unavailable"


def test_phi_critical_redacts_patient_strings(caplog):
    raw = (
        "RFP attachment: clinical case summary for Patient Jane Doe, age 42, "
        "diagnosed with diabetes at Austin clinic. Do not share."
    )
    redacted, flagged, reasons = scan_and_redact(raw)
    assert flagged is True
    assert "Jane Doe" not in redacted
    assert "Patient Jane" not in redacted
    assert "[REDACTED_" in redacted or "REDACTED" in redacted
    assert "Jane Doe" not in caplog.text


def test_extracts_are_scoped_not_full_doc():
    text = _md("meridian_formal.md") * 20  # inflate
    extracts = extract_department_snippets(text, ["revenue", "clinical", "compliance"])
    for dept, snippets in extracts.items():
        joined = "\n".join(snippets)
        assert len(joined) < len(text)
        assert snippets


@patch("data.pipelines.rfp_intake.metadata.chat_json")
def test_metadata_missing_fields_become_open_questions(mock_chat: MagicMock):
    mock_chat.return_value = {
        "client_name": "Meridian Manufacturing",
        "client_country": "US",
        "program_type": "occupational health",
        "covered_population": None,
        "covered_population_n": None,
        "deadline": None,
        "budget_range": None,
        "open_questions": [],
    }
    result = extract_metadata(_md("meridian_formal.md"))
    assert result["client_name"] == "Meridian Manufacturing"
    assert result["covered_population"] is None
    assert result["covered_population_n"] is None
    assert any("covered_population" in q for q in result["open_questions"])


@patch("data.pipelines.rfp_intake.metadata.chat_json")
def test_metadata_never_fabricates_population(mock_chat: MagicMock):
    mock_chat.return_value = {
        "client_name": "X",
        "client_country": "UK",
        "program_type": "referral",
        "covered_population": None,
        "covered_population_n": 99999,
        "deadline": None,
        "budget_range": None,
        "open_questions": [],
    }
    result = extract_metadata("no numbers here")
    assert result["covered_population"] is None
    assert result["covered_population_n"] is None


@patch("data.pipelines.rfp_intake.agents.classifier.chat_json")
def test_classifier_formal_valid(mock_chat: MagicMock):
    mock_chat.return_value = {"is_rfp": True, "confidence": 0.92, "reason": "formal RFP"}
    result = classify_document(_md("meridian_formal.md"))
    assert result["is_rfp"] is True
    assert result["needs_human_review"] is False


@patch("data.pipelines.rfp_intake.agents.classifier.chat_json")
def test_classifier_informal_valid(mock_chat: MagicMock):
    mock_chat.return_value = {"is_rfp": True, "confidence": 0.88, "reason": "email RFP"}
    result = classify_document(_md("thames_informal.md"))
    assert result["is_rfp"] is True


@patch("data.pipelines.rfp_intake.agents.classifier.chat_json")
def test_classifier_ehr_invalid(mock_chat: MagicMock):
    mock_chat.return_value = {"is_rfp": False, "confidence": 0.95, "reason": "vendor pitch"}
    result = classify_document(_md("ehr_vendor_pitch.md"))
    assert result["is_rfp"] is False
    assert result["needs_human_review"] is False


@patch("data.pipelines.rfp_intake.agents.classifier.chat_json")
def test_classifier_non_rfp_low_confidence_still_discards(mock_chat: MagicMock):
    """is_rfp=false must discard even when confidence is below threshold."""
    mock_chat.return_value = {
        "is_rfp": False,
        "confidence": CONFIDENCE_THRESHOLD - 0.2,
        "reason": "vendor pitch, uncertain",
    }
    result = classify_document(_md("ehr_vendor_pitch.md"))
    assert result["is_rfp"] is False
    assert result["needs_human_review"] is False


@patch("data.pipelines.rfp_intake.agents.classifier.chat_json")
def test_classifier_low_confidence_human_review(mock_chat: MagicMock):
    mock_chat.return_value = {
        "is_rfp": True,
        "confidence": CONFIDENCE_THRESHOLD - 0.1,
        "reason": "uncertain",
    }
    result = classify_document("ambiguous doc")
    assert result["needs_human_review"] is True


def test_orchestrator_always_includes_compliance():
    deps, qs = determine_departments({}, "generic request for services")
    assert "compliance" in deps
    assert deps
    assert len(deps) == 3


def test_orchestrator_never_empty():
    deps, _ = determine_departments({"program_type": None}, "")
    assert deps == ["revenue", "clinical", "compliance"]


@patch("data.pipelines.rfp_intake.agents.worker.chat_json")
def test_worker_scoped_payload_and_open_question(mock_chat: MagicMock):
    mock_chat.return_value = {"key_aspects": ["USD pricing TBD"], "open_questions": []}
    payload = {
        "department_id": "revenue",
        "shared_metadata": {
            "client_name": "Meridian",
            "client_country": "US",
            "program_type": "occupational health",
            "covered_population": None,
            "deadline": None,
            "budget_range": None,
        },
        "department_extracts": ["budget to be discussed"],
        "open_questions": [],
        "contains_phi": False,
    }
    assert "markdown" not in payload
    result = run_worker(payload)
    assert any("covered population" in q.lower() for q in result["open_questions"])
    called_user = mock_chat.call_args.args[1]
    assert "Patient" not in called_user or "Jane" not in called_user


@patch("data.pipelines.rfp_intake.agents.synthesizer.chat_json")
def test_synthesizer_surfaces_conflict_not_resolve(mock_chat: MagicMock):
    mock_chat.return_value = {
        "summary": "ok",
        "what_to_ask_whom": [],
        "conflict_flags": [],
        "open_items": [],
    }
    workers = {
        "clinical": {
            "key_aspects": ["insufficient clinic capacity to cover volume"],
            "open_questions": [],
        },
        "revenue": {
            "key_aspects": ["covered population 800 employees"],
            "open_questions": [],
        },
        "compliance": {"key_aspects": ["BAA required"], "open_questions": []},
    }
    summary = synthesize({"client_name": "Meridian"}, workers, [])
    assert any("capacity" in f.lower() or "conflict" in f.lower() for f in summary["conflict_flags"])


def test_convert_mocked(tmp_path):
    from data.pipelines.rfp_intake import convert

    class FakeResult:
        text_content = "# Hello RFP"

    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF-1.1\n%%EOF\n")

    with patch("markitdown.MarkItDown") as cls:
        instance = cls.return_value
        instance.convert.return_value = FakeResult()
        text = convert.pdf_to_markdown(str(path))
    assert "Hello RFP" in text


def test_route_after_classify_paths():
    from data.pipelines.rfp_intake.graph import route_after_classify

    assert route_after_classify({"stop_reason": "discarded"}) == "__end__"
    assert route_after_classify({"stop_reason": "human_review"}) == "__end__"
    assert route_after_classify({}) == "orchestrate"
