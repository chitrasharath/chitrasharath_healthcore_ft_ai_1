"""LangGraph nodes for memory consent, read, and propose."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.domains.agent.memory.audit import append_audit
from app.domains.agent.memory.consent import classify_fn
from app.domains.agent.memory.consolidate import maybe_consolidate_after_write
from app.domains.agent.memory.fastpath import (
    should_attempt_recall,
    should_consider_proposing,
)
from app.domains.agent.memory.phi import validate_no_phi
from app.domains.agent.memory.proposal import propose_fn
from app.domains.agent.memory.schemas import (
    MemoryEntry,
    MemoryProposal,
    MemoryProposalPublic,
    MemoryScope,
    new_mem_id,
)
from app.domains.agent.memory.store import get_memory_store
from app.domains.agent.state import AgentState
from app.domains.agent.tracing import trace_step

logger = logging.getLogger(__name__)

CONSENT_PROMPT_TEMPLATE = (
    'I noticed something worth remembering for this clinic: **"{text}"** '
    "May I save it? You can **approve**, **edit** (reply with the corrected text), "
    "or **reject**."
)

PHI_MEMORY_REFUSAL = (
    "I can't store patient information or identifiers in memory. "
    "Nothing was saved."
)

SAVED_CONFIRM = "Saved."
REJECTED_CONFIRM = "Okay — I won't save that."
EDITED_CONFIRM = "Saved your edited version."

_STORE_INTENT_RE = re.compile(
    r"\b(note|remember|save|store|memorize|write\s+down|keep\s+in\s+mind)\b",
    re.I,
)


def _user_tried_to_store_phi(question: str) -> bool:
    """True when the staff message looks like a store-PHI attempt (Cycle B3)."""
    q = question or ""
    if _STORE_INTENT_RE.search(q) and re.search(r"\bpatient\b", q, re.I):
        return True
    ok, _ = validate_no_phi(q)
    return not ok


def _next_order(state: AgentState) -> int:
    return len(state.get("trace_steps") or []) + 1


def _scope_from_state(state: AgentState) -> MemoryScope:
    return MemoryScope(
        clinic_id=str(state.get("clinic_id") or "unassigned"),
        staff_id=str(state.get("staff_id") or "unknown"),
    ).normalized()


def format_memory_block(entries: list[MemoryEntry]) -> str:
    lines = ["[MEMORY]"]
    for entry in entries:
        lines.append(f"- ({entry.type}) {entry.text}")
    return "\n".join(lines)


def apply_consent_decision(
    *,
    proposal: MemoryProposal,
    decision: str,
    edited_text: str | None,
    store: Any,
) -> dict[str, Any]:
    """Shared resolve path for graph + /memory/decision. Returns answer + audit side-effects."""
    scope = MemoryScope(
        clinic_id=proposal.clinic_id, staff_id=proposal.staff_id
    ).normalized()
    redis = store._redis

    if decision == "reject":
        append_audit(
            redis,
            event="rejected",
            staff_id=scope.staff_id,
            clinic_id=scope.clinic_id,
            proposal_id=proposal.proposal_id,
            decision="reject",
            preview_text=proposal.text,
        )
        return {"answer": REJECTED_CONFIRM, "status": "rejected"}

    text = (edited_text or proposal.text).strip() if decision == "edit" else proposal.text.strip()
    if decision == "edit" and not text:
        append_audit(
            redis,
            event="rejected",
            staff_id=scope.staff_id,
            clinic_id=scope.clinic_id,
            proposal_id=proposal.proposal_id,
            decision="edit_empty",
            preview_text=proposal.text,
        )
        return {"answer": REJECTED_CONFIRM, "status": "rejected"}

    ok, reasons = validate_no_phi(text)
    if not ok:
        append_audit(
            redis,
            event="phi_rejected",
            staff_id=scope.staff_id,
            clinic_id=scope.clinic_id,
            proposal_id=proposal.proposal_id,
            reasons=",".join(reasons),
            omit_preview=True,
        )
        return {"answer": PHI_MEMORY_REFUSAL, "status": "phi_rejected"}

    now = int(time.time())
    entry = MemoryEntry(
        id=new_mem_id(),
        scope=scope,
        type=proposal.type,
        text=text,
        created_at=now,
        last_recalled_at=now,
        recall_count=0,
        source_trace_id=proposal.source_trace_id,
    )
    store.write(scope, entry)
    maybe_consolidate_after_write(store, scope)
    event = "edited" if decision == "edit" else "approved"
    append_audit(
        redis,
        event=event,
        staff_id=scope.staff_id,
        clinic_id=scope.clinic_id,
        proposal_id=proposal.proposal_id,
        mem_id=entry.id,
        decision=decision,
        preview_text=text,
    )
    return {
        "answer": EDITED_CONFIRM if decision == "edit" else SAVED_CONFIRM,
        "status": event,
        "mem_id": entry.id,
    }


def memory_consent_check_node(state: AgentState) -> dict[str, Any]:
    """Resolve pending consent or pass through for a normal / new question turn."""
    from app.core.config import settings

    order = _next_order(state)
    if not settings.memory_enabled:
        return {
            "memory_consent_resolved": False,
            "trace_steps": [
                trace_step("memory_consent_check", order, "disabled pass-through")
            ],
        }

    store = get_memory_store()
    staff_id = str(state.get("staff_id") or "")
    if store is None or not staff_id:
        return {
            "memory_consent_resolved": False,
            "trace_steps": [
                trace_step("memory_consent_check", order, "no store/staff")
            ],
        }

    try:
        proposal = store.pop_pending(staff_id)
    except Exception:
        logger.exception("pop_pending failed")
        return {
            "memory_consent_resolved": False,
            "trace_steps": [trace_step("memory_consent_check", order, "pop failed")],
        }

    if proposal is None:
        return {
            "memory_consent_resolved": False,
            "trace_steps": [trace_step("memory_consent_check", order, "no pending")],
        }

    reply = state.get("normalized_question") or state.get("question") or ""
    try:
        decision = classify_fn(reply, proposal)
    except Exception:
        logger.exception("consent classify failed — treating as new_question")
        from app.domains.agent.memory.schemas import MemoryDecision

        decision = MemoryDecision(decision="new_question")

    if decision.decision == "new_question":
        append_audit(
            store._redis,
            event="dismissed_ignored",
            staff_id=proposal.staff_id,
            clinic_id=proposal.clinic_id,
            proposal_id=proposal.proposal_id,
            decision="new_question",
            preview_text=proposal.text,
        )
        return {
            "memory_consent_resolved": False,
            "trace_steps": [
                trace_step("memory_consent_check", order, "dismissed_ignored")
            ],
        }

    result = apply_consent_decision(
        proposal=proposal,
        decision=decision.decision,
        edited_text=decision.edited_text,
        store=store,
    )
    return {
        "answer": result["answer"],
        "sources": [],
        "memory_consent_resolved": True,
        "memory_proposal": None,
        "trace_steps": [
            trace_step(
                "memory_consent_check",
                order,
                f"decision={decision.decision} status={result.get('status')}",
            )
        ],
    }


def memory_read_node(state: AgentState) -> dict[str, Any]:
    """Recall scoped memories; inject [MEMORY] block; never blocks answering."""
    from app.core.config import settings

    order = _next_order(state)
    if not settings.memory_enabled:
        return {
            "memory_block": None,
            "recalled_mem_ids": [],
            "trace_steps": [trace_step("memory_read", order, "disabled")],
        }

    store = get_memory_store()
    if store is None:
        return {
            "memory_block": None,
            "recalled_mem_ids": [],
            "trace_steps": [trace_step("memory_read", order, "store unavailable")],
        }

    scope = _scope_from_state(state)
    question = state.get("normalized_question") or state.get("question") or ""
    if not should_attempt_recall(question):
        return {
            "memory_block": None,
            "recalled_mem_ids": [],
            "trace_steps": [trace_step("memory_read", order, "skipped fastpath")],
        }
    try:
        entries = store.read(scope, question)
    except Exception:
        logger.exception("memory_read failed")
        return {
            "memory_block": None,
            "recalled_mem_ids": [],
            "trace_steps": [trace_step("memory_read", order, "error")],
        }

    if not entries:
        return {
            "memory_block": None,
            "recalled_mem_ids": [],
            "trace_steps": [trace_step("memory_read", order, "0 recalled")],
        }

    block = format_memory_block(entries)
    ids = [e.id for e in entries]
    return {
        "memory_block": block,
        "recalled_mem_ids": ids,
        "trace_steps": [
            trace_step("memory_read", order, f"recalled={','.join(ids)}")
        ],
    }


def memory_propose_node(state: AgentState) -> dict[str, Any]:
    """Self-eval after answer; PHI-gate; maybe ask consent."""
    from app.core.config import settings

    order = _next_order(state)
    if not settings.memory_enabled:
        return {
            "memory_proposal": None,
            "trace_steps": [trace_step("memory_propose", order, "disabled")],
        }

    # Skip when consent already resolved this turn or guardrails blocked without a real answer path
    if state.get("memory_consent_resolved"):
        return {
            "memory_proposal": None,
            "trace_steps": [trace_step("memory_propose", order, "skipped consent turn")],
        }

    store = get_memory_store()
    if store is None:
        return {
            "memory_proposal": None,
            "trace_steps": [trace_step("memory_propose", order, "store unavailable")],
        }

    question = state.get("normalized_question") or state.get("question") or ""
    answer = state.get("answer") or ""
    if not answer or state.get("error") == "empty_question":
        return {
            "memory_proposal": None,
            "trace_steps": [trace_step("memory_propose", order, "no answer")],
        }

    # Already recalled this turn: skip propose unless the user volunteered new ops knowledge.
    if state.get("recalled_mem_ids") and not should_consider_proposing(question, ""):
        return {
            "memory_proposal": None,
            "trace_steps": [
                trace_step("memory_propose", order, "skipped after recall")
            ],
        }

    if not should_consider_proposing(question, answer):
        return {
            "memory_proposal": None,
            "trace_steps": [
                trace_step("memory_propose", order, "skipped fastpath")
            ],
        }

    scope = _scope_from_state(state)
    try:
        proposal = propose_fn(
            question,
            answer,
            clinic_id=scope.clinic_id,
            staff_id=scope.staff_id,
            trace_id=state.get("trace_id"),
        )
    except Exception:
        logger.exception("memory propose failed")
        return {
            "memory_proposal": None,
            "trace_steps": [trace_step("memory_propose", order, "propose error")],
        }

    if not proposal.worth_remembering or not proposal.text.strip():
        return {
            "memory_proposal": None,
            "trace_steps": [
                trace_step("memory_propose", order, "dismissed not worth")
            ],
        }

    ok, reasons = validate_no_phi(proposal.text)
    if not ok:
        append_audit(
            store._redis,
            event="phi_rejected",
            staff_id=scope.staff_id,
            clinic_id=scope.clinic_id,
            proposal_id=proposal.proposal_id,
            reasons=",".join(reasons),
            omit_preview=True,
        )
        # Only surface the refusal when the user tried to store PHI (Cycle B3).
        # Otherwise silently drop a bad proposal so a normal RAG answer stays clean.
        if _user_tried_to_store_phi(question):
            prior = answer.rstrip()
            refusal = (
                f"{prior}\n\n{PHI_MEMORY_REFUSAL}" if prior else PHI_MEMORY_REFUSAL
            )
            return {
                "answer": refusal,
                "memory_proposal": None,
                "trace_steps": [
                    trace_step("memory_propose", order, "phi_rejected")
                ],
            }
        return {
            "memory_proposal": None,
            "trace_steps": [
                trace_step("memory_propose", order, "phi_rejected_silent")
            ],
        }

    try:
        store.save_pending(scope.staff_id, proposal)
    except Exception:
        logger.exception("save_pending failed")
        return {
            "memory_proposal": None,
            "trace_steps": [trace_step("memory_propose", order, "pending failed")],
        }

    append_audit(
        store._redis,
        event="proposed",
        staff_id=scope.staff_id,
        clinic_id=scope.clinic_id,
        proposal_id=proposal.proposal_id,
        preview_text=proposal.text,
    )
    consent_q = CONSENT_PROMPT_TEMPLATE.format(text=proposal.text)
    public = MemoryProposalPublic(id=proposal.proposal_id, text=proposal.text)
    new_answer = f"{answer.rstrip()}\n\n{consent_q}"
    return {
        "answer": new_answer,
        "memory_proposal": public.model_dump(),
        "trace_steps": [
            trace_step(
                "memory_propose",
                order,
                f"proposed {proposal.proposal_id}",
            )
        ],
    }
