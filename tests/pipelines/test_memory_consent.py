"""Pipeline tests for memory propose / consent / PHI paths."""

from __future__ import annotations

import time
import uuid
from contextlib import ExitStack
from unittest.mock import patch

import fakeredis
import pytest

from app.domains.agent import nodes as agent_nodes
from app.domains.agent.graph import compiled_graph
from app.domains.agent.memory.audit import AUDIT_STREAM
from app.domains.agent.memory.schemas import (
    MemoryDecision,
    MemoryProposal,
    MemoryScope,
    new_proposal_id,
)
from app.domains.agent.memory.store import RedisQdrantMemoryStore, reset_memory_store_for_tests

_RAG_ONLY = {
    "use_rag": True,
    "use_incident": False,
    "use_inventory": False,
    "incident_id": None,
    "product_hint": None,
    "reasoning": "stub",
}


class FakeQdrant:
    def __init__(self) -> None:
        self.points: dict[str, dict] = {}

    def ensure_collection(self, collection: str, dim: int) -> None:
        return None

    def upsert(self, collection, points=None, **kwargs):
        for p in points or []:
            self.points[str(p.id)] = dict(p.payload)

    def delete(self, collection, points_selector=None, **kwargs):
        ids = points_selector if isinstance(points_selector, list) else []
        for mid in ids:
            self.points.pop(str(mid), None)

    def search(self, collection, query_vector=None, query_filter=None, limit=5, **kwargs):
        clinic = staff = None
        if isinstance(query_filter, dict):
            clinic = query_filter.get("clinic_id")
            staff = query_filter.get("staff_id")
        hits = []
        for pl in self.points.values():
            if clinic and pl.get("clinic_id") != clinic:
                continue
            if staff and pl.get("staff_id") != staff:
                continue
            hits.append(type("H", (), {"payload": pl})())
        return hits[:limit]


@pytest.fixture
def memory_store():
    reset_memory_store_for_tests()
    r = fakeredis.FakeStrictRedis(decode_responses=True)
    s = RedisQdrantMemoryStore(
        redis_client=r,
        qdrant_client=FakeQdrant(),
        embed_fn=lambda text: [0.1, 0.2, 0.3],
    )
    yield s
    r.flushall()
    reset_memory_store_for_tests()


def _initial(question: str, *, staff_id: str = "42", clinic_id: str = "2") -> dict:
    return {
        "question": question,
        "normalized_question": None,
        "auth_token": "test-token",
        "staff_id": staff_id,
        "clinic_id": clinic_id,
        "intent": None,
        "retrieved_context": None,
        "incident_result": None,
        "inventory_result": None,
        "compose_context_blocks": None,
        "memory_block": None,
        "recalled_mem_ids": None,
        "memory_proposal": None,
        "memory_consent_resolved": None,
        "answer": None,
        "sources": None,
        "sources_used": [],
        "trace_id": "run-" + uuid.uuid4().hex[:12],
        "trace_steps": [],
        "error": None,
        "guardrail_action": None,
        "guardrail_type": None,
        "guardrail_events": [],
        "final_answer_overridden": None,
    }


def _run(
    question: str,
    *,
    store: RedisQdrantMemoryStore,
    propose=None,
    classify=None,
    staff_id: str = "42",
    clinic_id: str = "2",
) -> dict:
    from app.core import config as app_config
    from app.domains.agent.memory import nodes as memory_nodes

    initial = _initial(question, staff_id=staff_id, clinic_id=clinic_id)
    config = {"configurable": {"thread_id": initial["trace_id"]}}
    hits = [
        {
            "source_document": "ops",
            "section": "notes",
            "text": "Operational context for tests.",
            "score": 0.9,
        }
    ]
    with ExitStack() as stack:
        stack.enter_context(patch.object(app_config.settings, "guardrails_enabled", False))
        stack.enter_context(patch.object(app_config.settings, "memory_enabled", True))
        stack.enter_context(
            patch(
                "app.domains.agent.memory.nodes.get_memory_store",
                return_value=store,
            )
        )
        stack.enter_context(
            patch.object(agent_nodes, "classifier_fn", lambda q: dict(_RAG_ONLY))
        )
        stack.enter_context(patch.object(agent_nodes, "retrieve", return_value=hits))
        stack.enter_context(
            patch.object(
                agent_nodes,
                "compose_generate_fn",
                lambda assembled: "Here is the operational answer.",
            )
        )
        if propose is not None:
            stack.enter_context(patch.object(memory_nodes, "propose_fn", propose))
        if classify is not None:
            stack.enter_context(patch.object(memory_nodes, "classify_fn", classify))
        return compiled_graph.invoke(initial, config=config)


def _audit_events(store: RedisQdrantMemoryStore) -> list[str]:
    rows = store._redis.xrange(AUDIT_STREAM) or []
    events = []
    for _id, fields in rows:
        ev = fields.get("event") if isinstance(fields, dict) else None
        if ev:
            events.append(ev)
    return events


def test_proposal_worth_remembering_asks_consent(memory_store):
    def propose(question, answer, **kwargs):
        return MemoryProposal(
            proposal_id=new_proposal_id(),
            clinic_id=kwargs["clinic_id"],
            staff_id=kwargs["staff_id"],
            type="semantic",
            text="Referral submissions fail Monday mornings; retry after 11am.",
            worth_remembering=True,
            created_at=int(time.time()),
            source_trace_id=kwargs.get("trace_id"),
        )

    final = _run(
        "Heads up — referrals keep failing Monday mornings.",
        store=memory_store,
        propose=propose,
    )
    assert final.get("memory_proposal")
    assert "May I save it" in (final.get("answer") or "")
    assert memory_store._redis.get("mem:pending:42")
    assert "proposed" in _audit_events(memory_store)


def test_approve_writes_entry(memory_store):
    proposal = MemoryProposal(
        proposal_id="mp-approve1",
        clinic_id="2",
        staff_id="42",
        type="semantic",
        text="Referral submissions fail Monday mornings; retry after 11am.",
        worth_remembering=True,
        created_at=int(time.time()),
    )
    memory_store.save_pending("42", proposal)

    final = _run(
        "approve",
        store=memory_store,
        classify=lambda reply, prop: MemoryDecision(decision="approve"),
        propose=lambda *a, **k: MemoryProposal(
            proposal_id="mp-x",
            clinic_id="2",
            staff_id="42",
            text="",
            worth_remembering=False,
            created_at=int(time.time()),
        ),
    )
    assert final.get("memory_consent_resolved") is True
    assert "Saved" in (final.get("answer") or "")
    scope = MemoryScope(clinic_id="2", staff_id="42")
    assert memory_store.list(scope)
    assert "approved" in _audit_events(memory_store)


def test_reject_writes_nothing(memory_store):
    proposal = MemoryProposal(
        proposal_id="mp-rej1",
        clinic_id="2",
        staff_id="42",
        type="semantic",
        text="Something operational.",
        worth_remembering=True,
        created_at=int(time.time()),
    )
    memory_store.save_pending("42", proposal)
    final = _run(
        "no, don't save that",
        store=memory_store,
        classify=lambda reply, prop: MemoryDecision(decision="reject"),
        propose=lambda *a, **k: MemoryProposal(
            proposal_id="mp-x",
            clinic_id="2",
            staff_id="42",
            text="",
            worth_remembering=False,
            created_at=int(time.time()),
        ),
    )
    assert final.get("memory_consent_resolved") is True
    assert memory_store.list(MemoryScope(clinic_id="2", staff_id="42")) == []
    assert "rejected" in _audit_events(memory_store)


def test_new_question_disregards_and_answers(memory_store):
    proposal = MemoryProposal(
        proposal_id="mp-ign1",
        clinic_id="2",
        staff_id="42",
        type="semantic",
        text="Something operational.",
        worth_remembering=True,
        created_at=int(time.time()),
    )
    memory_store.save_pending("42", proposal)
    final = _run(
        "What's our AXA coverage in the UK?",
        store=memory_store,
        classify=lambda reply, prop: MemoryDecision(decision="new_question"),
        propose=lambda *a, **k: MemoryProposal(
            proposal_id="mp-x",
            clinic_id="2",
            staff_id="42",
            text="",
            worth_remembering=False,
            created_at=int(time.time()),
        ),
    )
    assert final.get("memory_consent_resolved") is not True
    assert "Here is the operational answer" in (final.get("answer") or "")
    assert "dismissed_ignored" in _audit_events(memory_store)
    assert memory_store.list(MemoryScope(clinic_id="2", staff_id="42")) == []


def test_phi_proposal_never_shown(memory_store):
    def propose(question, answer, **kwargs):
        return MemoryProposal(
            proposal_id=new_proposal_id(),
            clinic_id=kwargs["clinic_id"],
            staff_id=kwargs["staff_id"],
            type="semantic",
            text="Patient Johnson cancelled tomorrow's appointment.",
            worth_remembering=True,
            created_at=int(time.time()),
        )

    final = _run(
        "Patient Johnson cancelled tomorrow, note that down.",
        store=memory_store,
        propose=propose,
    )
    assert final.get("memory_proposal") is None
    assert "can't store patient information" in (final.get("answer") or "").lower()
    assert memory_store._redis.get("mem:pending:42") is None
    assert "phi_rejected" in _audit_events(memory_store)
    assert memory_store.list(MemoryScope(clinic_id="2", staff_id="42")) == []


@pytest.mark.parametrize(
    "question",
    [
        "What's the late-cancellation fee for Medicaid in the US?",
        "Thanks, that's all for now.",
        "Good morning!",
    ],
)
def test_dismissible_examples_no_prompt(memory_store, question):
    def propose(q, answer, **kwargs):
        return MemoryProposal(
            proposal_id=new_proposal_id(),
            clinic_id=kwargs["clinic_id"],
            staff_id=kwargs["staff_id"],
            type="semantic",
            text="",
            worth_remembering=False,
            created_at=int(time.time()),
            reasoning="dismiss",
        )

    final = _run(question, store=memory_store, propose=propose)
    assert final.get("memory_proposal") is None
    assert "May I save it" not in (final.get("answer") or "")
