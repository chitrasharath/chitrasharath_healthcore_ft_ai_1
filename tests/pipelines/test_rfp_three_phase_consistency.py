"""SPEC Phase 3 §9.11 — Meridian US formal RFP through Phases 1→2→3.

Mock LLM (no live network); simulate Tom / Dr. Marcus Reid / Claire Whitfield
approvals. Assert ticket states, execution-log messages, and data
(key_aspects → draft_content → approval_status → FinalDocument) stay
consistent with no status jump, dropped field, or PHI leak (§5.9).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.domains.jobs.models import JobRun  # noqa: F401
from app.domains.rfp_intake import store
from app.domains.rfp_intake.models import (  # noqa: F401
    DepartmentSection,
    EvaluationResult,
    FinalDocument,
    RfpArbitrationRecord,
    RfpExecutionLog,
    RfpMetadata,
    Ticket,
)
from app.domains.rfp_intake.schema_ddl import ensure_rfp_phase2_columns
from data.pipelines.rfp_intake.approval_graph import get_approval_graph
from data.pipelines.rfp_intake.approval_runner import resume_approval, start_approval
from data.pipelines.rfp_intake.checkpointer import thread_config
from data.pipelines.rfp_intake.drafting_runner import run_drafting
from data.pipelines.rfp_intake.llm import LlmConfigError
from data.pipelines.rfp_intake.owners import DEPARTMENT_OWNERS, REQUIRED_DEPARTMENTS
from data.pipelines.rfp_intake.phi import contains_rfp_phi
from data.pipelines.rfp_intake.runner import run_intake
from data.pipelines.rfp_intake.transitions import can_transition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rfp_intake"
MERIDIAN_MD = (FIXTURES / "meridian_formal.md").read_text(encoding="utf-8")

_LLM_TARGETS = (
    "data.pipelines.rfp_intake.agents.classifier.chat_json",
    "data.pipelines.rfp_intake.metadata.chat_json",
    "data.pipelines.rfp_intake.agents.worker.chat_json",
    "data.pipelines.rfp_intake.agents.synthesizer.chat_json",
    "data.pipelines.rfp_intake.agents.generator.chat_json",
    "data.pipelines.rfp_intake.agents.evaluators.chat_json",
)

_ENGINE_TARGETS = (
    "app.core.db.supabase_engine",
    "data.pipelines.rfp_intake.runner.supabase_engine",
    "data.pipelines.rfp_intake.drafting_runner.supabase_engine",
    "data.pipelines.rfp_intake.approval_runner.supabase_engine",
    "data.pipelines.rfp_intake.approval_graph.supabase_engine",
)

_PHI_FORBIDDEN = ("Jane Doe", "SSN", "social security", "MRN-")


def _deny_llm(*_args: Any, **_kwargs: Any) -> None:
    raise LlmConfigError("mocked — no live LLM in three-phase test")


def _assert_no_phi(*blobs: Any) -> None:
    for blob in blobs:
        if blob is None:
            continue
        text = blob if isinstance(blob, str) else json.dumps(blob, default=str)
        hit, _ = contains_rfp_phi(text)
        assert not hit, "PHI leaked into persisted pipeline artifact"
        lowered = text.lower()
        for token in _PHI_FORBIDDEN:
            assert token.lower() not in lowered


@pytest.fixture
def three_phase_env(tmp_path, monkeypatch):
    db_path = tmp_path / "three_phase.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 60},
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _connection_record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA busy_timeout=60000")

    SQLModel.metadata.create_all(engine)
    ensure_rfp_phase2_columns(engine)

    for target in _ENGINE_TARGETS:
        monkeypatch.setattr(target, engine)

    saver = MemorySaver()

    def _shared_checkpointer(*, use_memory: bool = False):
        return saver

    monkeypatch.setattr(
        "data.pipelines.rfp_intake.checkpointer.get_checkpointer",
        _shared_checkpointer,
    )
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.approval_graph.get_checkpointer",
        _shared_checkpointer,
    )
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.approval_graph._compiled",
        None,
    )
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.graph.pdf_to_markdown",
        lambda _path: MERIDIAN_MD,
    )
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.final_document.RAW_DIR",
        tmp_path,
    )
    for target in _LLM_TARGETS:
        monkeypatch.setattr(target, _deny_llm)

    transitions: list[tuple[str, str]] = []
    original_set_status = store.set_ticket_status

    def _tracked_set_status(session, ticket, status, **kwargs):
        previous = ticket.status
        assert can_transition(previous, status), (
            f"Illegal ticket status jump: {previous} → {status}"
        )
        transitions.append((previous, status))
        return original_set_status(session, ticket, status, **kwargs)

    monkeypatch.setattr(
        "app.domains.rfp_intake.store.set_ticket_status",
        _tracked_set_status,
    )

    yield engine, transitions, saver

    import data.pipelines.rfp_intake.approval_graph as approval_graph

    approval_graph._compiled = None
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@respx.mock
def test_meridian_three_phase_consistency(three_phase_env) -> None:
    """§9.11: real Meridian fixture through intake → drafting → approval → done."""
    respx.route().mock(side_effect=httpx.ConnectError("spec forbids live network"))
    engine, transitions, _saver = three_phase_env

    pdf_path = "/tmp/meridian-formal.pdf"
    with Session(engine) as session:
        ticket = store.create_ticket(
            session,
            raw_pdf_path=pdf_path,
            content_sha256="meridian-formal-three-phase",
        )
        session.commit()
        ticket_id = ticket.ticket_id
        assert ticket.status == "analyzing"

    run_intake(ticket_id)

    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        meta = store.get_metadata(session, ticket_id)
        sections = store.list_sections(session, ticket_id)
        assert ticket is not None
        assert meta is not None
        assert ticket.ticket_id == ticket_id
        assert ticket.status == "intake_complete"
        assert "Meridian" in (meta.client_name or "")
        assert meta.client_country == "US"
        assert meta.covered_population_n == 800
        assert meta.contains_phi is False
        _assert_no_phi(meta.markdown_text)
        assert {s.department_id for s in sections} == set(REQUIRED_DEPARTMENTS)
        phase1_aspects = {
            s.department_id: copy.deepcopy(s.key_aspects) for s in sections
        }
        for dept in REQUIRED_DEPARTMENTS:
            aspects = phase1_aspects[dept]
            assert aspects, f"Phase 1 dropped key_aspects for {dept}"
            _assert_no_phi(aspects)

    run_drafting(ticket_id)

    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        sections = store.list_sections(session, ticket_id)
        evals = list(
            session.exec(
                select(EvaluationResult).where(EvaluationResult.ticket_id == ticket_id)
            ).all()
        )
        assert ticket is not None
        assert ticket.ticket_id == ticket_id
        assert ticket.status == "under_evaluation"
        assert all(s.status == "passed" for s in sections)
        phase2_drafts = {}
        for section in sections:
            assert section.key_aspects == phase1_aspects[section.department_id]
            assert section.draft_content and section.draft_content.strip()
            phase2_drafts[section.department_id] = section.draft_content
            ev = section.evaluation_results or {}
            assert ev.get("overall_pass") is True
            assert ev.get("contains_phi") is False
            _assert_no_phi(section.draft_content, ev)
        assert set(phase2_drafts) == set(REQUIRED_DEPARTMENTS)
        assert evals
        assert all(row.ticket_id == ticket_id for row in evals)
        for row in evals:
            _assert_no_phi(row.feedback_for_generator)

    start_approval(ticket_id)

    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        sections = store.list_sections(session, ticket_id)
        logs = list(
            session.exec(
                select(RfpExecutionLog).where(RfpExecutionLog.ticket_id == ticket_id)
            ).all()
        )
        assert ticket is not None
        assert ticket.status == "waiting_for_approval"
        assert all((s.approval_status or "pending") == "pending" for s in sections)
        assert logs, "execution log must start in Phase 3"
        assert any(row.agent == "arbitration" for row in logs)
        for row in logs:
            assert row.ticket_id == ticket_id
            _assert_no_phi(row.input, row.output, row.agent)

    config = thread_config(ticket_id)
    assert config["configurable"]["thread_id"] == ticket_id
    snap = get_approval_graph().get_state(config)
    snap_cfg = getattr(snap, "config", None) or {}
    snap_thread = (snap_cfg.get("configurable") or {}).get("thread_id")
    assert snap_thread == ticket_id
    assert (snap.values or {}).get("ticket_id") == ticket_id

    # Simulated owners (CONTEXT §2.1) — approve independently, same ticket_id
    for dept in ("clinical", "revenue", "compliance"):
        result = resume_approval(
            ticket_id,
            {
                "department_id": dept,
                "decision": "approve",
                "approver": DEPARTMENT_OWNERS[dept],
                "reason": "",
            },
        )
        assert result["ticket_id"] == ticket_id

    with Session(engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        meta = store.get_metadata(session, ticket_id)
        sections = store.list_sections(session, ticket_id)
        doc = session.get(FinalDocument, ticket_id)
        logs = list(
            session.exec(
                select(RfpExecutionLog).where(RfpExecutionLog.ticket_id == ticket_id)
            ).all()
        )
        assert ticket is not None
        assert meta is not None
        assert ticket.status == "done"
        assert ticket.ticket_id == ticket_id
        assert doc is not None
        assert doc.currency == "USD"
        assert doc.rendered_markdown
        assert doc.pdf_path
        assert Path(doc.pdf_path).is_file()
        _assert_no_phi(doc.rendered_markdown)

        by_dept = {s.department_id: s for s in sections}
        for dept in REQUIRED_DEPARTMENTS:
            section = by_dept[dept]
            assert section.key_aspects == phase1_aspects[dept]
            assert section.draft_content == phase2_drafts[dept]
            assert section.approval_status == "approved"
            assert section.approver == DEPARTMENT_OWNERS[dept]
            assert section.draft_content in (doc.rendered_markdown or "")

        final_sections = {row["department_id"]: row for row in (doc.sections or [])}
        for dept in REQUIRED_DEPARTMENTS:
            assert final_sections[dept]["draft_content"] == phase2_drafts[dept]

        agents = {row.agent for row in logs}
        assert "arbitration" in agents
        assert "approval_gate" in agents
        assert "final_document" in agents
        for row in logs:
            assert row.ticket_id == ticket_id
            _assert_no_phi(row.input, row.output)

        assert meta.client_country == "US"
        assert meta.covered_population_n == 800

    visited = [to_status for _, to_status in transitions]
    for required in (
        "intake_complete",
        "drafting",
        "under_evaluation",
        "waiting_for_approval",
        "done",
    ):
        assert required in visited, f"missing required status {required} on the ticket path"
    assert visited[-1] == "done"
    assert "discarded" not in visited
    # No jump that skips the legal chain (guard already asserted per write)
    assert can_transition("intake_complete", "done") is False
