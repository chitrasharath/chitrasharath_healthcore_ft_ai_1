"""Unit tests for RedisQdrantMemoryStore (fakeredis + FakeQdrant)."""

from __future__ import annotations

import time

import fakeredis
import pytest

from app.domains.agent.memory.fastpath import (
    should_attempt_recall,
    should_consider_proposing,
)
from app.domains.agent.memory.schemas import MemoryEntry, MemoryProposal, MemoryScope
from app.domains.agent.memory.store import RedisQdrantMemoryStore


def test_propose_fastpath_gates():
    assert should_consider_proposing(
        "Heads up — referrals keep failing Monday mornings, retry after 11."
    )
    assert should_consider_proposing("clinic hours are 8am-5pm weekdays")
    assert should_consider_proposing("We close at 5pm on weekdays.")
    assert should_consider_proposing(
        "FYI — for this clinic, always show inventory as units not cases."
    )
    assert not should_consider_proposing("appointments are delayed today")
    assert not should_consider_proposing(
        "Heads up — appointments are delayed today"
    )
    assert not should_consider_proposing("What is the fee for a referral?")
    assert not should_consider_proposing("What are clinic hours?")
    assert not should_consider_proposing("Any known issues with referrals?")
    assert should_attempt_recall("Any known issues with referrals?")
    assert should_attempt_recall("What are clinic hours?")
    assert not should_attempt_recall("Thanks!")


def test_clinic_hours_not_phi_and_hours_fallback():
    from app.domains.agent.harness.input_guards import detect_phi
    from app.domains.agent.memory.proposal import _hours_fallback_text

    assert not detect_phi("Clinic hours are 8:00 AM to 5:00 PM weekdays")
    assert not detect_phi("i think clinic hours for clinic 2 are 8am-5pm weekdays")
    assert _hours_fallback_text("clinic hours are 8am-5pm weekdays")


class FakeQdrant:
    """Minimal Qdrant double used by store tests."""

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


def _now() -> int:
    return int(time.time())


def _proposal() -> MemoryProposal:
    return MemoryProposal(
        proposal_id="mp-test01",
        clinic_id="north",
        staff_id="42",
        type="semantic",
        text="Referrals fail Monday mornings; retry after 11am.",
        created_at=_now(),
    )


@pytest.fixture
def store():
    r = fakeredis.FakeStrictRedis(decode_responses=True)
    s = RedisQdrantMemoryStore(
        redis_client=r,
        qdrant_client=FakeQdrant(),
        embed_fn=lambda text: [0.0, 1.0, 0.0],
    )
    yield s
    r.flushall()


def test_write_read_scoped(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    entry = MemoryEntry(
        id="m-1",
        scope=scope,
        type="semantic",
        text="Referrals fail Monday mornings; retry after 11am.",
        created_at=_now(),
        last_recalled_at=_now(),
        recall_count=0,
    )
    store.write(scope, entry)
    assert store.read(MemoryScope(clinic_id="south", staff_id="99"), "referrals") == []
    got = store.read(scope, "referral problems")
    assert got and got[0].id == "m-1"


def test_ttl_and_touch_refresh(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    store.write(
        scope,
        MemoryEntry(
            id="m-1",
            scope=scope,
            type="semantic",
            text="x",
            created_at=_now(),
            last_recalled_at=_now(),
            recall_count=0,
        ),
    )
    key = "mem:entry:north:42:m-1"
    assert store._redis.ttl(key) > 0
    store.touch(scope, "m-1")
    assert int(store._redis.hget(key, "recall_count")) == 1


def test_pending_getdel_pop(store):
    store.save_pending("42", _proposal())
    assert store.pop_pending("42") is not None
    assert store.pop_pending("42") is None


def test_expiry_reconciles_index(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    store.write(
        scope,
        MemoryEntry(
            id="m-1",
            scope=scope,
            type="semantic",
            text="x",
            created_at=_now(),
            last_recalled_at=_now(),
            recall_count=0,
        ),
    )
    store._redis.delete("mem:entry:north:42:m-1")
    assert store.list(scope) == []


def test_delete_removes_vector(store):
    scope = MemoryScope(clinic_id="north", staff_id="42")
    store.write(
        scope,
        MemoryEntry(
            id="m-1",
            scope=scope,
            type="semantic",
            text="x",
            created_at=_now(),
            last_recalled_at=_now(),
            recall_count=0,
        ),
    )
    assert store._qdrant.points
    store.delete(scope, "m-1")
    assert "m-1" not in store._qdrant.points
    assert store.list(scope) == []
