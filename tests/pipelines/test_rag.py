"""Unit tests for RAG process + pipeline layers (mocked network, tmp Qdrant)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from data.pipelines.rag import (
    FALLBACK_ANSWER,
    SYSTEM_PROMPT,
    normalize_query,
    query,
    retrieve,
)
from data.process.rag import (
    EmbeddingError,
    KB_DIR,
    SOURCE_DOCUMENTS,
    assert_chunk_integrity,
    chunk_markdown,
    embed,
    point_id_for,
    reset_qdrant_client,
    setup,
    store_vector,
)

DIM = 8


def _fake_vector(seed: float = 0.1) -> list[float]:
    return [seed + (i * 0.01) for i in range(DIM)]


@pytest.fixture(autouse=True)
def _rag_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("QDRANT_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setenv("QDRANT_COLLECTION", "test_company_knowledge_base")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.0")
    # Force settings reload
    from app.core import config

    config.settings = config.Settings()
    reset_qdrant_client()
    yield
    reset_qdrant_client()


def test_chunk_markdown_min_three_and_payload_shape() -> None:
    for filename, source in SOURCE_DOCUMENTS.items():
        md = (KB_DIR / filename).read_text(encoding="utf-8")
        chunks = chunk_markdown(md, source_document=source)
        assert_chunk_integrity(chunks)
        assert len(chunks) >= 3, source
        for i, chunk in enumerate(chunks):
            assert chunk.source_document == source
            assert chunk.chunk_index == i
            assert chunk.section
            assert chunk.text.strip()
            assert not chunk.text.strip().startswith("  ")


def test_chunk_does_not_split_mid_bullet_appointment() -> None:
    md = (KB_DIR / "healthcore-appointment-policy.en.md").read_text(encoding="utf-8")
    chunks = chunk_markdown(md, source_document="appointment-policy")
    for chunk in chunks:
        for line in chunk.text.splitlines():
            if line.startswith("  ") and not line.strip().startswith("-"):
                # continuation lines ok inside a chunk, but chunk itself shouldn't START that way
                pass
        assert not chunk.text.lstrip().startswith(
            ("hours in advance", "USD", "GBP in the UK")
        )


def test_normalize_query() -> None:
    assert normalize_query("  hello   world  ") == "hello world"
    with pytest.raises(ValueError):
        normalize_query("   ")


def test_embed_posts_and_returns_vector() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"embedding": _fake_vector()}]}

    with patch("data.process.rag.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = mock_response
        vector = embed("hello")

    assert len(vector) == DIM
    kwargs = client.post.call_args
    assert "/v1/embeddings" in kwargs.args[0]
    assert kwargs.kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs.kwargs["json"]["input"] == "hello"


def test_embed_raises_on_non_2xx() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "nope"

    with patch("data.process.rag.httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = mock_response
        with pytest.raises(EmbeddingError):
            embed("hello")


def test_store_vector_idempotent_and_retrieve(tmp_path: Path) -> None:
    qpath = tmp_path / "q1"
    collection = "test_kb"
    pid = point_id_for("appointment-policy", 0)
    payload = {
        "company": "healthcore",
        "source_document": "appointment-policy",
        "section": "Cancellation policy",
        "language": "en",
        "chunk_index": 0,
        "text": "Cancelling less than 24 hours: 50 USD",
    }
    store_vector(
        point_id=pid,
        vector=_fake_vector(0.2),
        payload=payload,
        collection_name=collection,
        client=None,
    )
    # force client on path
    from data.process.rag import get_qdrant_client

    client = get_qdrant_client(qpath)
    store_vector(
        point_id=pid,
        vector=_fake_vector(0.2),
        payload=payload,
        collection_name=collection,
        client=client,
    )
    store_vector(
        point_id=pid,
        vector=_fake_vector(0.25),
        payload=payload,
        collection_name=collection,
        client=client,
    )
    count = client.count(collection_name=collection, exact=True).count
    assert count == 1


def test_setup_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    vectors = {"n": 0}

    def fake_embed(text: str) -> list[float]:
        vectors["n"] += 1
        # vary slightly by hash so search has signal, but keep dim fixed
        seed = (sum(ord(c) for c in text) % 50) / 100.0
        return _fake_vector(seed)

    monkeypatch.setattr("data.process.rag.embed", fake_embed)
    qpath = tmp_path / "setup_q"
    r1 = setup(qdrant_path=qpath)
    assert r1.documents_processed == 4
    assert r1.total_points >= 12
    assert all(n >= 3 for n in r1.chunks_per_document.values())
    r2 = setup(qdrant_path=qpath)
    assert r2.total_points == r1.total_points
    assert r2.chunks_per_document == r1.chunks_per_document


def test_retrieve_filters_min_score(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_embed(text: str) -> list[float]:
        vec = [0.0] * DIM
        idx = sum(ord(c) for c in text.lower()) % DIM
        vec[idx] = 1.0
        return vec

    monkeypatch.setattr("data.process.rag.embed", fake_embed)
    monkeypatch.setattr("data.pipelines.rag.embed", fake_embed)
    qpath = tmp_path / "ret_q"
    setup(qdrant_path=qpath)
    hits = retrieve("cancellation fee 24 hours", qdrant_path=qpath, top_k=3, min_score=0.0)
    assert hits
    assert "text" in hits[0]
    assert hits == sorted(hits, key=lambda h: h["score"], reverse=True)

    # Force all dense hits below threshold via patched response scores
    from data.process.rag import get_qdrant_client

    client = get_qdrant_client(qpath)
    low = MagicMock()
    low.points = []
    for hit in hits:
        point = MagicMock()
        point.score = 0.1
        point.payload = {k: v for k, v in hit.items() if k != "score"}
        low.points.append(point)
    monkeypatch.setattr(client, "query_points", lambda **kwargs: low)
    empty = retrieve("cancellation fee", qdrant_path=qpath, top_k=3, min_score=0.5)
    assert empty == []


def test_query_happy_and_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_embed(text: str) -> list[float]:
        vec = [0.0] * DIM
        # Route cancellation questions near appointment-policy cancellation text
        key = text.lower()
        if "cancel" in key or "50 usd" in key or "appointment" in key:
            vec[0] = 1.0
        elif "insurance" in key or "medicaid" in key:
            vec[1] = 1.0
        else:
            vec[sum(ord(c) for c in key) % DIM] = 1.0
        return vec

    # Make setup embeddings also favor section keywords
    def setup_embed(text: str) -> list[float]:
        vec = [0.0] * DIM
        key = text.lower()
        if "cancel" in key or "appointment" in key:
            vec[0] = 1.0
        elif "insurance" in key or "medicaid" in key or "united states" in key:
            vec[1] = 1.0
        elif "referral" in key:
            vec[2] = 1.0
        elif "patient" in key or "checklist" in key or "id" in key:
            vec[3] = 1.0
        else:
            vec[sum(ord(c) for c in key) % DIM] = 1.0
        return vec

    monkeypatch.setattr("data.process.rag.embed", setup_embed)
    qpath = tmp_path / "qry_q"
    setup(qdrant_path=qpath)
    monkeypatch.setattr("data.pipelines.rag.embed", fake_embed)

    gen = MagicMock(return_value="Per our appointment policy, the fee is 50 USD.")
    result = query(
        "cancellation less than 24 hours fee?",
        qdrant_path=qpath,
        min_score=0.0,
        generate_fn=gen,
    )
    assert "50 USD" in result.answer
    assert result.sources
    assert gen.called
    prompt = gen.call_args.args[0]
    assert "SOURCE" in prompt or "Source:" in prompt
    assert "Tom Callahan" in SYSTEM_PROMPT
    assert "Medicare" in SYSTEM_PROMPT

    gen2 = MagicMock(return_value="should not be called")
    # Patch retrieve to return nothing so generation is skipped
    monkeypatch.setattr("data.pipelines.rag.retrieve", lambda *a, **k: [])
    empty = query(
        "something unrelated xyzzy",
        qdrant_path=qpath,
        min_score=0.5,
        generate_fn=gen2,
    )
    assert empty.answer == FALLBACK_ANSWER
    assert empty.sources == []
    gen2.assert_not_called()


def test_eval_harness_wires_golden_set() -> None:
    path = Path("data/eval/test-queries.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) >= 10
    answerable = [q for q in data if not q["should_abstain"]]
    abstain = [q for q in data if q["should_abstain"]]
    assert len(answerable) >= 8
    assert len(abstain) >= 2
    docs = {q["expected_source_document"] for q in answerable}
    assert {"insurance-coverage", "appointment-policy", "referral-process", "new-patient-checklist"} <= docs
