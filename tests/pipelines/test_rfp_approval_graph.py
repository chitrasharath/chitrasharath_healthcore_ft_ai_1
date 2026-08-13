"""Approval graph interrupt / resume with MemorySaver."""

from __future__ import annotations

from unittest.mock import patch

from langgraph.types import Command

from data.pipelines.rfp_intake.approval_graph import build_approval_graph
from data.pipelines.rfp_intake.checkpointer import thread_config
from data.pipelines.rfp_intake.owners import DEPARTMENT_OWNERS


def _clean_sections():
    return [
        {
            "department_id": "revenue",
            "draft_content": "Revenue section with USD pricing.",
            "key_aspects": ["pricing"],
            "evaluation_results": {
                "contains_phi": False,
                "phi_was_redacted": False,
                "overall_pass": True,
            },
            "status": "passed",
            "approval_status": "pending",
            "approval_iteration": 0,
        },
        {
            "department_id": "clinical",
            "draft_content": "Clinical capacity is sufficient.",
            "key_aspects": {"committed_capacity": 1000, "sites": ["Austin"]},
            "evaluation_results": {
                "contains_phi": False,
                "phi_was_redacted": False,
                "overall_pass": True,
            },
            "status": "passed",
            "approval_status": "pending",
            "approval_iteration": 0,
        },
        {
            "department_id": "compliance",
            "draft_content": "Business Associate Agreement (BAA) included.",
            "key_aspects": {"instrument": "BAA"},
            "evaluation_results": {
                "contains_phi": False,
                "phi_was_redacted": False,
                "overall_pass": True,
            },
            "status": "passed",
            "approval_status": "pending",
            "approval_iteration": 0,
        },
    ]


def test_b_approves_while_a_still_pending():
    graph = build_approval_graph(use_memory=True)
    ticket_id = "ticket-interrupt-1"
    config = thread_config(ticket_id)
    sections = _clean_sections()

    with (
        patch(
            "data.pipelines.rfp_intake.approval_graph._load_sections",
            return_value=sections,
        ),
        patch("data.pipelines.rfp_intake.approval_graph._persist_log"),
        patch("data.pipelines.rfp_intake.approval_graph._persist_arbitration"),
        patch("data.pipelines.rfp_intake.approval_graph._write_section_approval"),
        patch("data.pipelines.rfp_intake.approval_graph.supabase_engine", None),
    ):
        graph.invoke(
            {
                "ticket_id": ticket_id,
                "job_run_id": "job-1",
                "required_departments": ["revenue", "clinical", "compliance"],
                "metadata": {
                    "client_country": "US",
                    "covered_population_n": 800,
                },
                "approvals": {},
                "sections": sections,
                "execution_log": [],
            },
            config=config,
        )

        # Approve clinical while revenue still pending
        state = graph.invoke(
            Command(
                resume={
                    "department_id": "clinical",
                    "decision": "approve",
                    "approver": DEPARTMENT_OWNERS["clinical"],
                    "reason": "",
                }
            ),
            config=config,
        )
        approvals = state.get("approvals") or {}
        assert approvals.get("clinical", {}).get("decision") == "approve"
        assert approvals.get("revenue", {}).get("decision") != "approve"

        # Finish remaining approvals
        for dept in ("revenue", "compliance"):
            with patch(
                "data.pipelines.rfp_intake.approval_graph.node_final_document",
                return_value={"phase3_complete": True, "execution_log": []},
            ):
                state = graph.invoke(
                    Command(
                        resume={
                            "department_id": dept,
                            "decision": "approve",
                            "approver": DEPARTMENT_OWNERS[dept],
                            "reason": "",
                        }
                    ),
                    config=config,
                )
        approvals = state.get("approvals") or {}
        assert approvals.get("revenue", {}).get("decision") == "approve"
        assert approvals.get("compliance", {}).get("decision") == "approve"
