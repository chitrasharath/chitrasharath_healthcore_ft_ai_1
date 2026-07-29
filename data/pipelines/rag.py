"""RAG retrieval + generation pipeline."""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from data.process.rag import (  # noqa: E402
    EmbeddingError,
    RagConfigError,
    bootstrap_env,
    embed,
    get_qdrant_client,
    sleep_for_rate_limit,
)

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_MAX_RETRIES = 1
_RATE_LIMIT_RETRIES = 12

FALLBACK_ANSWER = (
    "I don't have that in our knowledge base yet — let me check with the team "
    "and get back to you."
)

SYSTEM_PROMPT = """You are HealthCore's best front-desk service advisor speaking to a patient coordinator.
Answer clearly, warmly, confidently, and concisely — a coordinator should be able to read your reply aloud to a patient.

Rules (mandatory):
- ONLY use facts present in the labeled SOURCE blocks below. Never invent coverage, fees, timeframes, or policies.
- If an insurer is not listed in the sources, do NOT confirm coverage — say it must be verified with the billing team (Tom Callahan).
- When a coverage question does not specify a country, distinguish United States vs United Kingdom explicitly.
- No-show / late-cancellation fees must NEVER be applied to Medicare or Medicaid patients — follow the appointment policy literally.
- Never include or invent PHI (patient names, diagnoses, medical record numbers).
- Cite the source naturally (e.g. "per our appointment policy") so the answer is traceable.
- Answer in the language of the user's question, but keep policy values verbatim: amounts ($50 / £40), insurer names (Bupa, AXA Health, Medicaid, …), and day-counts exactly as written in the sources. Translate prose only.
- If two sources differ by country, present United States and United Kingdom separately.
"""


class GenerationError(Exception):
    """Raised when the chat completion proxy fails."""


@dataclass
class QueryResult:
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    context_texts: list[str] = field(default_factory=list)
    assembled_prompt: str = ""
    model: str = ""
    temperature: float = 0.15


def _settings():
    bootstrap_env()
    from app.core.config import settings

    return settings


def normalize_query(question: str, *, max_length: int | None = None) -> str:
    settings = _settings()
    limit = max_length if max_length is not None else settings.rag_question_max_length
    cleaned = re.sub(r"\s+", " ", (question or "").strip())
    if not cleaned:
        raise ValueError("Question must not be empty")
    if len(cleaned) > limit:
        raise ValueError(f"Question exceeds max length of {limit}")
    return cleaned


# Short desk questions often omit "insurance/coverage", which weakens dense retrieval
# against policy chunks. Expansion is for embedding only — the LLM still sees the
# original user question.
_COVERAGE_TERMS = (
    "kaiser",
    "medicaid",
    "medicare",
    "aetna",
    "cigna",
    "bupa",
    "axa",
    "blue cross",
    "unitedhealthcare",
    "united health",
    "self-pay",
    "self pay",
    "uninsured",
)


def expand_query_for_retrieval(query: str) -> str:
    """Enrich short coverage questions so embeddings align with insurance chunks."""
    lower = query.lower()
    already_grounded = any(
        tip in lower for tip in ("insurance", "coverage", "insurer", "plan", "accept")
    )
    # "do you take/accept X" already has accept — still help bare "kaiser" / "medicaid"
    mentions_coverage_entity = any(term in lower for term in _COVERAGE_TERMS)
    if not mentions_coverage_entity:
        return query
    if "insurance" in lower or "coverage" in lower:
        return query
    # "do you take kaiser" / "do you take medicaid" → add domain signal
    if re.search(r"\b(take|accept|cover|have)\b", lower) or not already_grounded:
        return f"{query} insurance coverage accepted"
    return query


def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    qdrant_path: str | Path | None = None,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    settings = _settings()
    k = top_k if top_k is not None else settings.rag_top_k
    threshold = min_score if min_score is not None else settings.rag_min_score
    collection = collection_name or settings.qdrant_collection
    retrieval_query = expand_query_for_retrieval(query)
    vector = embed(retrieval_query)
    client = get_qdrant_client(qdrant_path)
    response = client.query_points(
        collection_name=collection,
        query=vector,
        limit=k,
        with_payload=True,
    )
    results: list[dict[str, Any]] = []
    for hit in response.points:
        score = float(hit.score or 0.0)
        if score < threshold:
            continue
        payload = dict(hit.payload or {})
        payload["score"] = score
        results.append(payload)
    results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return results


def _dedupe_sources(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for hit in hits:
        key = (str(hit.get("source_document", "")), str(hit.get("section", "")))
        score = float(hit.get("score", 0.0))
        prev = best.get(key)
        if prev is None or score > float(prev.get("score", 0.0)):
            best[key] = {
                "source_document": key[0],
                "section": key[1],
                "score": score,
            }
    return sorted(best.values(), key=lambda s: s["score"], reverse=True)


def _build_context_block(hits: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for hit in hits:
        doc = hit.get("source_document", "unknown")
        section = hit.get("section", "")
        text = hit.get("text", "")
        parts.append(f"[Source: {doc} — {section}]\n{text}")
    return "\n\n".join(parts)


def _generate(assembled_prompt: str) -> str:
    settings = _settings()
    if not settings.llm_api_key:
        raise RagConfigError(
            "LLM_API_KEY is unset. Add it to .env before generating answers."
        )
    url = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.generation_model,
        "temperature": settings.rag_generation_temperature,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": assembled_prompt},
        ],
    }
    last_error: Exception | None = None
    max_attempts = max(_MAX_RETRIES, _RATE_LIMIT_RETRIES) + 1
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                response = client.post(url, headers=headers, json=payload)
            if response.status_code == 429 and attempt < _RATE_LIMIT_RETRIES:
                sleep_for_rate_limit(response.text)
                continue
            if response.status_code >= 500 and attempt < _MAX_RETRIES:
                last_error = GenerationError(
                    f"Generation proxy {response.status_code}: {response.text[:200]}"
                )
                continue
            if response.status_code < 200 or response.status_code >= 300:
                raise GenerationError(
                    f"Generation proxy returned {response.status_code}: {response.text[:300]}"
                )
            body = response.json()
            choices = body.get("choices")
            if not choices:
                raise GenerationError("Malformed generation response: no choices")
            message = choices[0].get("message") or {}
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise GenerationError("Malformed generation response: empty content")
            return content.strip()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = GenerationError(f"Generation request failed: {exc}")
            if attempt >= _MAX_RETRIES:
                raise last_error from exc
    assert last_error is not None
    raise last_error


def build_assembled_prompt(question: str, hits: list[dict[str, Any]]) -> str:
    """Assemble the SOURCE-CONTEXT + QUESTION prompt (moved verbatim from query())."""
    context = _build_context_block(hits)
    return (
        f"SOURCE CONTEXT (every fact you state must come from a labeled block):\n\n"
        f"{context}\n\n"
        f"QUESTION:\n{question}\n"
    )


def generate_answer(
    question: str,
    context: list[dict[str, Any]],
    *,
    generate_fn=_generate,
) -> str:
    """Generate a grounded answer from already-retrieved context.

    `context` is the list of hit dicts returned by `retrieve()`. Callers that
    have no context must NOT call this — routing handles the no-context case.
    """
    assembled = build_assembled_prompt(question, context)
    return generate_fn(assembled)


def query(
    question: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    qdrant_path: str | Path | None = None,
    collection_name: str | None = None,
    generate_fn=_generate,
) -> QueryResult:
    settings = _settings()
    normalized = normalize_query(question)
    hits = retrieve(
        normalized,
        top_k=top_k,
        min_score=min_score,
        qdrant_path=qdrant_path,
        collection_name=collection_name,
    )
    if not hits:
        return QueryResult(
            answer=FALLBACK_ANSWER,
            sources=[],
            context_texts=[],
            assembled_prompt="",
            model=settings.generation_model,
            temperature=settings.rag_generation_temperature,
        )

    assembled = build_assembled_prompt(normalized, hits)
    answer = generate_answer(normalized, hits, generate_fn=generate_fn)
    return QueryResult(
        answer=answer,
        sources=_dedupe_sources(hits),
        context_texts=[str(h.get("text", "")) for h in hits],
        assembled_prompt=assembled,
        model=settings.generation_model,
        temperature=settings.rag_generation_temperature,
    )


__all__ = [
    "FALLBACK_ANSWER",
    "SYSTEM_PROMPT",
    "EmbeddingError",
    "GenerationError",
    "QueryResult",
    "RagConfigError",
    "build_assembled_prompt",
    "expand_query_for_retrieval",
    "generate_answer",
    "normalize_query",
    "query",
    "retrieve",
]
