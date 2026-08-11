"""LangGraph StateGraph for RFP intake (separate from CX agent graph)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from sqlmodel import Session

from data.pipelines.rfp_intake.agents.classifier import classify_document
from data.pipelines.rfp_intake.agents.orchestrator import determine_departments
from data.pipelines.rfp_intake.agents.synthesizer import synthesize
from data.pipelines.rfp_intake.agents.worker import run_worker
from data.pipelines.rfp_intake.convert import pdf_to_markdown
from data.pipelines.rfp_intake.extracts import extract_department_snippets
from data.pipelines.rfp_intake.metadata import extract_metadata
from data.pipelines.rfp_intake.phi import scan_and_redact
from data.pipelines.rfp_intake.readability import compute_readability
from data.pipelines.rfp_intake import repository as repo
from data.pipelines.rfp_intake.state import RfpIntakeState

logger = logging.getLogger(__name__)


def _session_factory():
    from app.core.db import supabase_engine

    if supabase_engine is None:
        raise RuntimeError("DATABASE_URL is not set")
    return Session(supabase_engine)


def node_convert(state: RfpIntakeState) -> dict[str, Any]:
    markdown = pdf_to_markdown(state["pdf_path"])
    with _session_factory() as session:
        repo.update_checkpoint(session, state.get("job_run_id"), "converted")
        session.commit()
    return {"markdown": markdown, "checkpoint": "converted"}


def node_phi(state: RfpIntakeState) -> dict[str, Any]:
    redacted, flagged, reasons = scan_and_redact(state.get("markdown") or "")
    with _session_factory() as session:
        repo.persist_markdown_and_phi(
            session,
            state["ticket_id"],
            markdown=redacted,
            contains_phi=flagged,
        )
        repo.update_checkpoint(session, state.get("job_run_id"), "phi_scanned")
        session.commit()
    return {
        "markdown": redacted,
        "contains_phi": flagged,
        "phi_reasons": reasons,
        "checkpoint": "phi_scanned",
    }


def node_metadata(state: RfpIntakeState) -> dict[str, Any]:
    metadata = extract_metadata(state.get("markdown") or "")
    open_questions = list(metadata.get("open_questions") or [])
    with _session_factory() as session:
        # readability computed in next node; persist metadata fields here partially
        repo.update_checkpoint(session, state.get("job_run_id"), "metadata")
        session.commit()
    return {
        "metadata": metadata,
        "open_questions": open_questions,
        "checkpoint": "metadata",
    }


def node_readability(state: RfpIntakeState) -> dict[str, Any]:
    metrics = compute_readability(state.get("markdown") or "")
    metadata = dict(state.get("metadata") or {})
    with _session_factory() as session:
        repo.persist_extracted_metadata(
            session,
            state["ticket_id"],
            metadata,
            metrics,
        )
        repo.update_checkpoint(session, state.get("job_run_id"), "readability")
        session.commit()
    return {"readability_metrics": metrics, "checkpoint": "readability"}


def node_classify(state: RfpIntakeState) -> dict[str, Any]:
    result = classify_document(state.get("markdown") or "")
    needs_review = bool(result.get("needs_human_review"))
    is_rfp = bool(result.get("is_rfp"))

    if needs_review:
        status = "analyzing"
        stop = "human_review"
    elif not is_rfp:
        status = "discarded"
        stop = "discarded"
    else:
        status = "analyzing"
        stop = ""

    with _session_factory() as session:
        repo.persist_classifier(
            session,
            state["ticket_id"],
            result,
            status=status,
            needs_human_review=needs_review,
        )
        repo.update_checkpoint(session, state.get("job_run_id"), "classified")
        session.commit()

    out: dict[str, Any] = {
        "classifier": result,
        "checkpoint": "classified",
    }
    if stop:
        out["stop_reason"] = stop
    return out


def route_after_classify(
    state: RfpIntakeState,
) -> Literal["orchestrate", "__end__"]:
    stop = state.get("stop_reason")
    if stop in ("discarded", "human_review"):
        return "__end__"
    return "orchestrate"


def node_orchestrate(state: RfpIntakeState) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    departments, extra_qs = determine_departments(metadata, state.get("markdown") or "")
    open_questions = list(state.get("open_questions") or []) + extra_qs
    extracts = extract_department_snippets(state.get("markdown") or "", departments)
    contains_phi = bool(state.get("contains_phi"))
    with _session_factory() as session:
        repo.persist_departments(
            session,
            state["ticket_id"],
            departments,
            contains_phi=contains_phi,
        )
        repo.update_checkpoint(session, state.get("job_run_id"), "orchestrated")
        session.commit()
    return {
        "departments_needed": departments,
        "department_extracts": extracts,
        "open_questions": open_questions,
        "checkpoint": "orchestrated",
    }


def node_workers(state: RfpIntakeState) -> dict[str, Any]:
    metadata = dict(state.get("metadata") or {})
    shared = {
        "client_name": metadata.get("client_name"),
        "client_country": metadata.get("client_country"),
        "program_type": metadata.get("program_type"),
        "covered_population": metadata.get("covered_population"),
        "deadline": metadata.get("deadline"),
        "budget_range": metadata.get("budget_range"),
    }
    extracts = state.get("department_extracts") or {}
    open_questions = list(state.get("open_questions") or [])
    contains_phi = bool(state.get("contains_phi"))
    results: dict[str, Any] = {}

    for dept in state.get("departments_needed") or []:
        payload = {
            "department_id": dept,
            "shared_metadata": shared,
            "department_extracts": extracts.get(dept) or [],
            "open_questions": open_questions,
            "contains_phi": contains_phi,
        }
        # Least privilege: never include full markdown in payload
        assert "markdown" not in payload
        result = run_worker(payload)
        results[dept] = result
        with _session_factory() as session:
            repo.persist_worker_result(
                session,
                state["ticket_id"],
                dept,
                result,
                contains_phi=contains_phi,
            )
            session.commit()

    with _session_factory() as session:
        repo.update_checkpoint(session, state.get("job_run_id"), "workers_done")
        session.commit()

    merged_qs = list(open_questions)
    for result in results.values():
        for q in result.get("open_questions") or []:
            if q not in merged_qs:
                merged_qs.append(q)

    return {
        "worker_results": results,
        "open_questions": merged_qs,
        "checkpoint": "workers_done",
    }


def node_synthesize(state: RfpIntakeState) -> dict[str, Any]:
    summary = synthesize(
        dict(state.get("metadata") or {}),
        dict(state.get("worker_results") or {}),
        list(state.get("open_questions") or []),
    )
    with _session_factory() as session:
        repo.persist_summary_complete(
            session,
            state["ticket_id"],
            summary,
            list(state.get("open_questions") or []),
        )
        repo.update_checkpoint(session, state.get("job_run_id"), "synthesized")
        session.commit()
    return {
        "sales_summary": summary,
        "checkpoint": "synthesized",
    }


def build_graph():
    graph = StateGraph(RfpIntakeState)
    graph.add_node("convert", node_convert)
    graph.add_node("phi", node_phi)
    graph.add_node("metadata", node_metadata)
    graph.add_node("readability", node_readability)
    graph.add_node("classify", node_classify)
    graph.add_node("orchestrate", node_orchestrate)
    graph.add_node("workers", node_workers)
    graph.add_node("synthesize", node_synthesize)

    graph.add_edge(START, "convert")
    graph.add_edge("convert", "phi")
    graph.add_edge("phi", "metadata")
    graph.add_edge("metadata", "readability")
    graph.add_edge("readability", "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"orchestrate": "orchestrate", "__end__": END},
    )
    graph.add_edge("orchestrate", "workers")
    graph.add_edge("workers", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH
