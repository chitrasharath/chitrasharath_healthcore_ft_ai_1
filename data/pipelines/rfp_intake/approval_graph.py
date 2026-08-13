"""LangGraph approval flow: arbitration → interrupt gates → final document."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlmodel import Session

from app.core.db import supabase_engine
from app.core.config import settings
from app.domains.rfp_intake import store
from app.domains.rfp_intake.models import RfpArbitrationRecord, RfpExecutionLog
from data.pipelines.rfp_intake.arbitration import run_arbitration
from data.pipelines.rfp_intake.approval_state import ApprovalState
from data.pipelines.rfp_intake.checkpointer import get_checkpointer
from data.pipelines.rfp_intake.final_document import generate_final_document
from data.pipelines.rfp_intake.node_logging import make_log_entry
from data.pipelines.rfp_intake.owners import DEPARTMENT_OWNERS, REQUIRED_DEPARTMENTS
from data.pipelines.rfp_intake.transitions import assert_can_transition

logger = logging.getLogger(__name__)

_compiled = None


def _ticket_id_from(state: dict[str, Any] | None, config: RunnableConfig) -> str:
    """Resolve ticket_id from state or thread_id (resume safety net)."""
    if isinstance(state, dict):
        tid = state.get("ticket_id")
        if tid:
            return str(tid)
    if config:
        tid = (config.get("configurable") or {}).get("thread_id")
        if tid:
            return str(tid)
    raise KeyError("ticket_id missing from approval state and thread config")


def _persist_log(ticket_id: str, entry: dict[str, Any]) -> None:
    if supabase_engine is None:
        return
    with Session(supabase_engine) as session:
        row = RfpExecutionLog(
            ticket_id=ticket_id,
            agent=str(entry.get("agent") or ""),
            input=entry.get("input"),
            output=entry.get("output"),
            timestamp=datetime.now(timezone.utc),
            department_id=entry.get("department_id"),
            trigger_id=entry.get("trigger_id"),
        )
        session.add(row)
        session.commit()


def _persist_arbitration(ticket_id: str, arb: dict[str, Any]) -> None:
    if supabase_engine is None:
        return
    with Session(supabase_engine) as session:
        row = RfpArbitrationRecord(
            ticket_id=ticket_id,
            trigger_id=str(arb.get("trigger_id") or ""),
            arbiter=str(arb.get("arbiter") or ""),
            forced_action=arb.get("forced_action"),
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.commit()


def _load_sections(ticket_id: str) -> list[dict[str, Any]]:
    if supabase_engine is None:
        return []
    with Session(supabase_engine) as session:
        sections = store.list_sections(session, ticket_id)
        return [
            {
                "department_id": s.department_id,
                "key_aspects": s.key_aspects,
                "draft_content": s.draft_content,
                "evaluation_results": s.evaluation_results or {},
                "status": s.status,
                "approval_status": s.approval_status or "pending",
                "approver": s.approver,
                "approval_iteration": getattr(s, "approval_iteration", 0) or 0,
            }
            for s in sections
        ]


def node_arbitration(
    state: ApprovalState,
    config: RunnableConfig,
) -> dict[str, Any]:
    ticket_id = _ticket_id_from(state, config)
    sections = _load_sections(ticket_id) or list(state.get("sections") or [])
    metadata = dict(state.get("metadata") or {})
    arb = run_arbitration(metadata=metadata, sections=sections)
    entry = make_log_entry(
        agent="arbitration",
        ticket_id=ticket_id,
        input_snapshot={"section_count": len(sections)},
        output_snapshot=arb,
        trigger_id=(arb or {}).get("trigger_id"),
    )
    _persist_log(ticket_id, entry)
    if arb is not None:
        _persist_arbitration(ticket_id, arb)
    return {
        "ticket_id": ticket_id,
        "sections": sections,
        "arbitration": arb,
        "execution_log": [entry],
    }


def _route_after_arbitration(
    state: ApprovalState,
) -> Literal["await_approvals", "force_revision", "final_document"]:
    arb = state.get("arbitration")
    if arb and arb.get("trigger_id") == "phi-detected":
        # PHI routes to Compliance human review via approval gate (not auto-revision loop)
        return "await_approvals"
    if arb and arb.get("forced_action", {}).get("action") == "request_changes":
        if arb.get("trigger_id") != "phi-detected":
            return "force_revision"
    approvals = state.get("approvals") or {}
    required = state.get("required_departments") or list(REQUIRED_DEPARTMENTS)
    if all(approvals.get(d, {}).get("decision") == "approve" for d in required):
        return "final_document"
    return "await_approvals"


def node_await_approvals(
    state: ApprovalState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Interrupt until a matching department decision arrives; one decision per resume."""
    ticket_id = _ticket_id_from(state, config)
    required = list(state.get("required_departments") or REQUIRED_DEPARTMENTS)
    approvals = dict(state.get("approvals") or {})
    sections = list(state.get("sections") or _load_sections(ticket_id))
    section_by_dept = {s["department_id"]: s for s in sections}

    pending = [d for d in required if approvals.get(d, {}).get("decision") != "approve"]
    if not pending:
        entry = make_log_entry(
            agent="approval_gate",
            ticket_id=ticket_id,
            output_snapshot={"all_approved": True},
        )
        _persist_log(ticket_id, entry)
        return {
            "ticket_id": ticket_id,
            "approvals": approvals,
            "revision_department": None,
            "revision_reason": None,
            "execution_log": [entry],
        }

    while True:
        payload = {
            "ticket_id": ticket_id,
            "pending_departments": pending,
            "sections": [
                {
                    "department_id": d,
                    "owner": DEPARTMENT_OWNERS.get(d),
                    "draft_content": (section_by_dept.get(d) or {}).get("draft_content"),
                    "key_aspects": (section_by_dept.get(d) or {}).get("key_aspects"),
                    "evaluation_summary": {
                        k: (section_by_dept.get(d) or {})
                        .get("evaluation_results", {})
                        .get(k)
                        for k in ("contains_phi", "phi_was_redacted", "overall_pass")
                    },
                    "approval_status": (section_by_dept.get(d) or {}).get(
                        "approval_status", "pending"
                    ),
                }
                for d in pending
            ],
        }
        decision = interrupt(payload)
        if not isinstance(decision, dict):
            continue
        dept = str(decision.get("department_id") or "")
        if dept not in pending:
            continue

        action = str(decision.get("decision") or "")
        approver = str(decision.get("approver") or "")
        reason = str(decision.get("reason") or "")
        expected = DEPARTMENT_OWNERS.get(dept)
        if expected and approver != expected:
            continue

        if action == "reject":
            if not reason.strip():
                continue
            approvals[dept] = {
                "decision": "reject",
                "approver": approver,
                "reason": reason,
            }
            entry = make_log_entry(
                agent="approval_gate",
                ticket_id=ticket_id,
                input_snapshot={"decision": "reject"},
                output_snapshot={"department_id": dept},
                department_id=dept,
            )
            _persist_log(ticket_id, entry)
            _write_section_approval(
                ticket_id, dept, "request_changes", approver, reason=reason
            )
            return {
                "ticket_id": ticket_id,
                "approvals": approvals,
                "revision_department": dept,
                "revision_reason": reason,
                "execution_log": [entry],
            }

        if action == "approve":
            approvals[dept] = {
                "decision": "approve",
                "approver": approver,
                "reason": reason,
            }
            entry = make_log_entry(
                agent="approval_gate",
                ticket_id=ticket_id,
                input_snapshot={"decision": "approve"},
                output_snapshot={"department_id": dept},
                department_id=dept,
            )
            _persist_log(ticket_id, entry)
            _write_section_approval(ticket_id, dept, "approved", approver)
            return {
                "ticket_id": ticket_id,
                "approvals": approvals,
                "revision_department": None,
                "revision_reason": None,
                "execution_log": [entry],
            }

def _write_section_approval(
    ticket_id: str,
    department_id: str,
    approval_status: str,
    approver: str,
    *,
    reason: str | None = None,
) -> None:
    if supabase_engine is None:
        return
    with Session(supabase_engine) as session:
        sections = store.list_sections(session, ticket_id)
        section = next((s for s in sections if s.department_id == department_id), None)
        if section is None:
            return
        section.approval_status = approval_status
        section.approver = approver
        section.approved_at = (
            datetime.now(timezone.utc) if approval_status == "approved" else None
        )
        if reason and section.evaluation_results is not None:
            ev = dict(section.evaluation_results)
            ev["approval_reason"] = reason
            section.evaluation_results = ev
        session.add(section)
        session.commit()


def node_force_revision(
    state: ApprovalState,
    config: RunnableConfig,
) -> dict[str, Any]:
    ticket_id = _ticket_id_from(state, config)
    arb = state.get("arbitration") or {}
    depts = list((arb.get("forced_action") or {}).get("departments") or [])
    reason = str((arb.get("forced_action") or {}).get("message") or arb.get("trigger_id"))
    target = depts[0] if depts else "compliance"
    entry = make_log_entry(
        agent="force_revision",
        ticket_id=ticket_id,
        output_snapshot={"department_id": target, "reason": reason},
        department_id=target,
        trigger_id=arb.get("trigger_id"),
    )
    _persist_log(ticket_id, entry)
    return {
        "ticket_id": ticket_id,
        "revision_department": target,
        "revision_reason": reason,
        "execution_log": [entry],
    }


def node_run_revision(
    state: ApprovalState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Re-enter Phase 2 drafting loop for one department; bound by approval iterations."""
    ticket_id = _ticket_id_from(state, config)
    dept = state.get("revision_department") or "compliance"
    reason = state.get("revision_reason") or "revision required"
    max_iters = int(settings.rfp_max_approval_iterations)

    if supabase_engine is None:
        return {"blocked_reason": "no database", "phase3_complete": False}

    with Session(supabase_engine) as session:
        sections = store.list_sections(session, ticket_id)
        section = next((s for s in sections if s.department_id == dept), None)
        if section is None:
            return {"blocked_reason": f"missing section {dept}"}
        iteration = int(getattr(section, "approval_iteration", 0) or 0) + 1
        section.approval_iteration = iteration
        section.approval_status = "request_changes"
        if iteration > max_iters:
            section.status = "needs_human_review"
            session.add(section)
            session.commit()
            entry = make_log_entry(
                agent="revision_limit",
                ticket_id=ticket_id,
                output_snapshot={"department_id": dept, "iteration": iteration},
                department_id=dept,
            )
            _persist_log(ticket_id, entry)
            return {
                "ticket_id": ticket_id,
                "blocked_reason": "approval iteration limit",
                "execution_log": [entry],
                "approvals": {
                    **(state.get("approvals") or {}),
                    dept: {"decision": "needs_human_review"},
                },
            }
        store.reset_section_for_redraft(session, ticket_id, dept)
        section = store.list_sections(session, ticket_id)
        sec = next(s for s in section if s.department_id == dept)
        sec.approval_iteration = iteration
        sec.evaluation_results = {
            **(sec.evaluation_results or {}),
            "feedback_for_generator": reason,
        }
        session.add(sec)
        session.commit()

    from data.pipelines.rfp_intake.drafting_runner import run_drafting

    try:
        run_drafting(ticket_id, department_id=dept)
    except Exception as exc:  # noqa: BLE001
        logger.exception("revision drafting failed ticket=%s dept=%s", ticket_id, dept)
        return {"blocked_reason": str(exc)[:200]}

    approvals = dict(state.get("approvals") or {})
    approvals.pop(dept, None)
    entry = make_log_entry(
        agent="revision",
        ticket_id=ticket_id,
        output_snapshot={"department_id": dept, "iteration": iteration},
        department_id=dept,
    )
    _persist_log(ticket_id, entry)
    return {
        "ticket_id": ticket_id,
        "approvals": approvals,
        "revision_department": None,
        "revision_reason": None,
        "sections": _load_sections(ticket_id),
        "execution_log": [entry],
    }


def node_final_document(
    state: ApprovalState,
    config: RunnableConfig,
) -> dict[str, Any]:
    ticket_id = _ticket_id_from(state, config)
    if supabase_engine is None:
        return {"blocked_reason": "no database", "phase3_complete": False}
    with Session(supabase_engine) as session:
        ticket = store.get_ticket(session, ticket_id)
        if ticket is None:
            return {"blocked_reason": "ticket missing"}
        try:
            assert_can_transition(ticket.status, "done")
            doc = generate_final_document(session, ticket_id)
            store.set_ticket_status(session, ticket, "done")
            session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("final document failed ticket=%s", ticket_id)
            session.rollback()
            entry = make_log_entry(
                agent="final_document",
                ticket_id=ticket_id,
                output_snapshot={"error": str(exc)[:200]},
            )
            _persist_log(ticket_id, entry)
            return {
                "ticket_id": ticket_id,
                "blocked_reason": str(exc)[:200],
                "phase3_complete": False,
                "execution_log": [entry],
            }
        entry = make_log_entry(
            agent="final_document",
            ticket_id=ticket_id,
            output_snapshot={"currency": doc.currency, "pdf_path": doc.pdf_path},
        )
        _persist_log(ticket_id, entry)
        return {
            "ticket_id": ticket_id,
            "phase3_complete": True,
            "execution_log": [entry],
        }

def _route_after_approvals(
    state: ApprovalState,
) -> Literal["run_revision", "final_document", "await_approvals"]:
    if state.get("revision_department"):
        return "run_revision"
    approvals = state.get("approvals") or {}
    required = state.get("required_departments") or list(REQUIRED_DEPARTMENTS)
    if state.get("blocked_reason"):
        return "await_approvals"
    if all(approvals.get(d, {}).get("decision") == "approve" for d in required):
        return "final_document"
    return "await_approvals"


def _route_after_revision(
    state: ApprovalState,
) -> Literal["arbitration", "await_approvals"]:
    if state.get("blocked_reason") == "approval iteration limit":
        return "await_approvals"
    return "arbitration"


def build_approval_graph(*, use_memory: bool = False):
    checkpointer = get_checkpointer(use_memory=use_memory)
    builder = StateGraph(ApprovalState)
    builder.add_node("arbitration", node_arbitration)
    builder.add_node("await_approvals", node_await_approvals)
    builder.add_node("force_revision", node_force_revision)
    builder.add_node("run_revision", node_run_revision)
    builder.add_node("final_document", node_final_document)

    builder.add_edge(START, "arbitration")
    builder.add_conditional_edges(
        "arbitration",
        _route_after_arbitration,
        {
            "await_approvals": "await_approvals",
            "force_revision": "force_revision",
            "final_document": "final_document",
        },
    )
    builder.add_edge("force_revision", "run_revision")
    builder.add_conditional_edges(
        "await_approvals",
        _route_after_approvals,
        {
            "run_revision": "run_revision",
            "final_document": "final_document",
            "await_approvals": "await_approvals",
        },
    )
    builder.add_conditional_edges(
        "run_revision",
        _route_after_revision,
        {"arbitration": "arbitration", "await_approvals": "await_approvals"},
    )
    builder.add_edge("final_document", END)
    return builder.compile(checkpointer=checkpointer)


def get_approval_graph(*, use_memory: bool = False, refresh: bool = False):
    global _compiled
    if use_memory:
        return build_approval_graph(use_memory=True)
    if _compiled is None or refresh:
        _compiled = build_approval_graph(use_memory=False)
    return _compiled
