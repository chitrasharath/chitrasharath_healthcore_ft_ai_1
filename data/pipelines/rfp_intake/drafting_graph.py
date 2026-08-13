"""LangGraph generator ↔ evaluator loop for one DepartmentSection."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from sqlmodel import Session

from data.pipelines.rfp_intake.agents.evaluators import (
    aggregate_results,
    evaluate_compliance,
    evaluate_readability,
    evaluate_relevance,
)
from data.pipelines.rfp_intake.agents.generator import generate_section
from data.pipelines.rfp_intake.drafting_state import DraftingState
from data.pipelines.rfp_intake import repository as repo
from data.pipelines.rfp_intake.phi import scan_and_redact
from data.pipelines.rfp_intake.rules import rules_for_section

logger = logging.getLogger(__name__)


def _session_factory():
    from app.core.db import supabase_engine

    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set")
    return Session(supabase_engine)


def _evaluator_input(state: DraftingState) -> dict[str, Any]:
    meta = dict(state.get("shared_metadata") or {})
    return {
        "department_id": state.get("department_id"),
        "draft_content": state.get("draft_content") or "",
        "key_aspects": state.get("key_aspects") or [],
        "subtask": state.get("subtask")
        or f"Draft the {state.get('department_id')} proposal section.",
        "shared_metadata": meta,
        "open_questions": state.get("open_questions") or [],
        "compliance_rules": rules_for_section(meta),
        "iteration": state.get("iteration") or 1,
    }


def node_generate(state: DraftingState) -> dict[str, Any]:
    iteration = int(state.get("iteration") or 0) + 1
    with _session_factory() as session:
        repo.set_section_drafting(
            session,
            state["ticket_id"],
            state["department_id"],
            iteration=iteration,
        )
        repo.update_checkpoint(
            session,
            state.get("job_run_id"),
            f"generate:{state['department_id']}:{iteration}",
        )
        session.commit()

    draft = generate_section(
        {
            "department_id": state["department_id"],
            "key_aspects": state.get("key_aspects") or [],
            "open_questions": state.get("open_questions") or [],
            "shared_metadata": state.get("shared_metadata") or {},
            "subtask": state.get("subtask"),
            "prior_draft": state.get("draft_content"),
            "feedback_for_generator": state.get("feedback_for_generator"),
        }
    )
    with _session_factory() as session:
        repo.persist_draft(
            session,
            state["ticket_id"],
            state["department_id"],
            draft_content=draft,
            iteration=iteration,
            status="drafting",
        )
        session.commit()
    return {
        "draft_content": draft,
        "iteration": iteration,
        "section_status": "drafting",
        "readability_result": {},
        "relevance_result": {},
        "compliance_result": {},
        "evaluation": {},
        "hard_stop_phi": False,
    }


def node_evaluate(state: DraftingState) -> dict[str, Any]:
    """Fan-out three evaluators in parallel; each writes a disjoint result key."""
    with _session_factory() as session:
        repo.ensure_ticket_under_evaluation(session, state["ticket_id"])
        repo.set_section_status(
            session,
            state["ticket_id"],
            state["department_id"],
            status="under_evaluation",
        )
        session.commit()

    payload = _evaluator_input(state)
    draft = payload["draft_content"]

    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_r = pool.submit(evaluate_readability, draft)
        fut_rel = pool.submit(evaluate_relevance, payload)
        fut_c = pool.submit(evaluate_compliance, payload)
        readability = fut_r.result()
        relevance = fut_rel.result()
        compliance = fut_c.result()

    return {
        "readability_result": readability,
        "relevance_result": relevance,
        "compliance_result": compliance,
        "section_status": "under_evaluation",
    }


def node_aggregate(state: DraftingState) -> dict[str, Any]:
    evaluation = aggregate_results(
        readability=dict(state.get("readability_result") or {}),
        relevance=dict(state.get("relevance_result") or {}),
        compliance=dict(state.get("compliance_result") or {}),
    )
    contains_phi = bool(evaluation.get("contains_phi"))
    draft = state.get("draft_content") or ""
    redacted = evaluation.get("redacted_draft")
    if isinstance(redacted, str) and redacted.strip():
        draft = redacted
    elif contains_phi:
        draft, _, _ = scan_and_redact(draft)

    max_iter = int(state.get("max_iterations") or 3)
    iteration = int(state.get("iteration") or 1)
    overall = bool(evaluation.get("overall_pass"))

    if contains_phi:
        # Residual PHI after scrub — still blocked for Phase 3
        section_status = "needs_human_review"
        route = "phi"
    elif overall:
        section_status = "passed"
        route = "passed"
    elif iteration >= max_iter:
        section_status = "needs_human_review"
        route = "limit"
    else:
        section_status = "under_evaluation"
        route = "retry"

    persist_status = section_status if route != "retry" else "under_evaluation"
    with _session_factory() as session:
        repo.persist_evaluation(
            session,
            ticket_id=state["ticket_id"],
            department_id=state["department_id"],
            section_id=int(state["section_id"]),
            iteration=iteration,
            evaluation=evaluation,
            draft_content=draft,
            section_status=persist_status,
        )
        if section_status == "needs_human_review":
            repo.flag_ticket_section_review(session, state["ticket_id"])
        repo.update_checkpoint(
            session,
            state.get("job_run_id"),
            f"eval:{state['department_id']}:{iteration}:{route}",
        )
        session.commit()

    return {
        "draft_content": draft,
        "evaluation": evaluation,
        "feedback_for_generator": evaluation.get("feedback_for_generator") or "",
        "section_status": persist_status,
        "hard_stop_phi": contains_phi,
        "route": route,
    }


def route_after_aggregate(
    state: DraftingState,
) -> Literal["generate", "__end__"]:
    if state.get("route") == "retry":
        return "generate"
    return "__end__"


def build_drafting_graph():
    graph = StateGraph(DraftingState)
    graph.add_node("generate", node_generate)
    graph.add_node("evaluate", node_evaluate)
    graph.add_node("aggregate", node_aggregate)

    graph.add_edge(START, "generate")
    graph.add_edge("generate", "evaluate")
    graph.add_edge("evaluate", "aggregate")
    graph.add_conditional_edges(
        "aggregate",
        route_after_aggregate,
        {"generate": "generate", "__end__": END},
    )
    return graph.compile()


_GRAPH = None


def get_drafting_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_drafting_graph()
    return _GRAPH
