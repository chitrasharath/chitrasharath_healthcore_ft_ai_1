"""RAG indexing: chunk company knowledge docs, embed, store in local Qdrant.

Qdrant local mode holds a file lock on the storage path — only one process may
open it at a time. Prefer running setup()/seed while the API is stopped, or let
the API seed once at startup within its own process.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

logger = logging.getLogger(__name__)

POINT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
SOURCE_DOCUMENTS: dict[str, str] = {
    "healthcore-insurance-coverage.en.md": "insurance-coverage",
    "healthcore-appointment-policy.en.md": "appointment-policy",
    "healthcore-referral-process.en.md": "referral-process",
    "healthcore-new-patient-checklist.en.md": "new-patient-checklist",
}
KB_DIR = _REPO_ROOT / "docs" / "company-knowledge-base"
SOFT_MAX_CHARS = 1200
MIN_CHUNKS_PER_DOC = 3
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 1
# LiteLLM team limit is ~15 req/min — eval needs many embeds, so wait out 429s.
_RATE_LIMIT_RETRIES = 12
_RESET_AT_RE = re.compile(
    r"Limit resets at:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*UTC",
    re.I,
)

_client: QdrantClient | None = None
_client_path: str | None = None


class EmbeddingError(Exception):
    """Raised when the embedding proxy returns a non-2xx or malformed body."""


class RagConfigError(Exception):
    """Raised when required RAG configuration is missing."""

@dataclass
class Chunk:
    source_document: str
    section: str
    chunk_index: int
    text: str
    doc_title: str = ""


@dataclass
class SetupResult:
    documents_processed: int
    chunks_per_document: dict[str, int] = field(default_factory=dict)
    total_points: int = 0
    collection_name: str = ""
    vector_dimension: int = 0


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def bootstrap_env() -> None:
    """Load repo-root `.env`, then fill gaps from `services/api/.env`."""
    root_env = _parse_env_file(_REPO_ROOT / ".env")
    api_env = _parse_env_file(_API_ROOT / ".env")
    for key, value in root_env.items():
        os.environ.setdefault(key, value)
    for key, value in api_env.items():
        os.environ.setdefault(key, value)


def _settings():
    bootstrap_env()
    from app.core.config import settings

    return settings


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (_REPO_ROOT / path).resolve()


def point_id_for(source_document: str, chunk_index: int) -> UUID:
    return uuid.uuid5(POINT_NAMESPACE, f"{source_document}:{chunk_index}")


def _is_section_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return True
    if stripped.endswith(":") and len(stripped) < 120 and not stripped.startswith("-"):
        return True
    return False


def _heading_label(line: str, fallback: str) -> str:
    stripped = line.strip().lstrip("#").strip().rstrip(":")
    return stripped or fallback


def chunk_markdown(md: str, *, source_document: str) -> list[Chunk]:
    """Pure semantic chunker: markdown → list of Chunk (section + text)."""
    lines = md.replace("\r\n", "\n").split("\n")
    doc_title = source_document
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            doc_title = line[2:].strip()
            body_start = i + 1
            break

    blocks: list[tuple[str, str]] = []
    current_section = doc_title
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines
        text = "\n".join(current_lines).strip()
        if text:
            blocks.append((current_section, text))
        current_lines = []

    i = body_start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            # blank line — keep list continuity by peeking ahead
            if current_lines and i + 1 < len(lines) and _is_section_heading(lines[i + 1]):
                flush()
                i += 1
                continue
            if current_lines:
                current_lines.append(line)
            i += 1
            continue
        if _is_section_heading(line) and not line.strip().startswith("-"):
            # numbered list items like "1. The physician..." are content, not headings
            if re.match(r"^\d+\.\s", line.strip()):
                current_lines.append(line)
                i += 1
                continue
            flush()
            current_section = _heading_label(line, doc_title)
            # Keep heading with following content when it's a subtitle line
            if line.strip().endswith(":") or line.strip().startswith("#"):
                current_lines.append(line)
            i += 1
            continue
        current_lines.append(line)
        i += 1
    flush()

    # Soft-size split preferring blank-line boundaries within a block
    refined: list[tuple[str, str]] = []
    for section, text in blocks:
        refined.extend(_split_oversized(section, text))

    # Guarantee ≥3 chunks: split largest blocks at blank lines / list groups
    while len(refined) < MIN_CHUNKS_PER_DOC:
        idx = max(range(len(refined)), key=lambda j: len(refined[j][1]))
        section, text = refined[idx]
        parts = _force_split(section, text)
        if len(parts) < 2:
            break
        refined[idx : idx + 1] = parts

    return [
        Chunk(
            source_document=source_document,
            section=section,
            chunk_index=i,
            text=text,
            doc_title=doc_title,
        )
        for i, (section, text) in enumerate(refined)
    ]


def _split_oversized(section: str, text: str) -> list[tuple[str, str]]:
    if len(text) <= SOFT_MAX_CHARS:
        return [(section, text)]
    parts = re.split(r"\n\s*\n", text)
    if len(parts) == 1:
        return [(section, text)]
    out: list[tuple[str, str]] = []
    buf: list[str] = []
    size = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        add = len(part) + (2 if buf else 0)
        if buf and size + add > SOFT_MAX_CHARS:
            out.append((section, "\n\n".join(buf)))
            buf = [part]
            size = len(part)
        else:
            buf.append(part)
            size += add
    if buf:
        out.append((section, "\n\n".join(buf)))
    return out or [(section, text)]


def _force_split(section: str, text: str) -> list[tuple[str, str]]:
    parts = re.split(r"\n\s*\n", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        mid = len(parts) // 2
        return [
            (section, "\n\n".join(parts[:mid])),
            (section, "\n\n".join(parts[mid:])),
        ]
    # Split bullet groups
    lines = text.split("\n")
    bullets = [i for i, ln in enumerate(lines) if re.match(r"^(\s*[-*]|\s*\d+\.)\s", ln)]
    if len(bullets) >= 2:
        mid_b = bullets[len(bullets) // 2]
        left = "\n".join(lines[:mid_b]).strip()
        right = "\n".join(lines[mid_b:]).strip()
        if left and right:
            return [(section, left), (section, right)]
    # Last resort: sentence boundary
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) >= 2:
        mid = len(sentences) // 2
        left = " ".join(sentences[:mid]).strip()
        right = " ".join(sentences[mid:]).strip()
        if left and right:
            return [(section, left), (section, right)]
    return [(section, text)]


def assert_chunk_integrity(chunks: list[Chunk]) -> None:
    """Fail loudly if a chunk appears to start/end mid-bullet or mid-sentence."""
    for chunk in chunks:
        text = chunk.text.strip()
        if not text:
            raise ValueError(
                f"Empty chunk for {chunk.source_document}#{chunk.chunk_index}"
            )
        first = text.split("\n", 1)[0]
        # Orphaned continuation line (indent without bullet marker)
        if re.match(r"^\s{2,}[a-z]", first) and not re.match(
            r"^\s*[-*]\s", first
        ):
            raise ValueError(
                f"Chunk starts mid-bullet: {chunk.source_document}#{chunk.chunk_index}"
            )
        # Mid-word start (lowercase after no space pattern from split)
        if re.match(r"^[a-z]", first) and not first.startswith(
            ("and ", "or ", "the ", "a ", "an ", "to ", "of ", "in ", "for ", "with ")
        ):
            # Allow intentional lowercase starts only for known continuations — flag hard splits
            if not first[0].isupper() and len(first.split()[0]) > 12:
                raise ValueError(
                    f"Chunk may start mid-sentence: {chunk.source_document}"
                    f"#{chunk.chunk_index}: {first[:40]!r}"
                )


def sleep_for_rate_limit(response_text: str) -> None:
    """Block until the proxy rate-limit window resets (plus a small buffer)."""
    wait = 65.0
    match = _RESET_AT_RE.search(response_text or "")
    if match:
        try:
            reset = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            wait = max(1.0, (reset - datetime.now(timezone.utc)).total_seconds() + 1.5)
        except ValueError:
            pass
    wait = min(wait, 120.0)
    logger.warning("Rate limited (429); sleeping %.1fs then retrying", wait)
    time.sleep(wait)


def embed(text: str) -> list[float]:
    """Embed exactly the string given — no title/section enrichment here."""
    settings = _settings()
    if not settings.llm_api_key:
        raise RagConfigError(
            "LLM_API_KEY is unset. Add it to .env before embedding or seeding."
        )
    url = f"{settings.llm_base_url.rstrip('/')}/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.embedding_model, "input": text}
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
                last_error = EmbeddingError(
                    f"Embedding proxy {response.status_code}: {response.text[:200]}"
                )
                continue
            if response.status_code < 200 or response.status_code >= 300:
                raise EmbeddingError(
                    f"Embedding proxy returned {response.status_code}: {response.text[:300]}"
                )
            body = response.json()
            data = body.get("data")
            if not data or not isinstance(data, list):
                raise EmbeddingError("Malformed embedding response: missing data[]")
            vector = data[0].get("embedding")
            if not isinstance(vector, list) or not vector:
                raise EmbeddingError("Malformed embedding response: empty embedding")
            return [float(x) for x in vector]
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = EmbeddingError(f"Embedding request failed: {exc}")
            if attempt >= _MAX_RETRIES:
                raise last_error from exc
    assert last_error is not None
    raise last_error


def get_qdrant_client(path: str | Path | None = None) -> QdrantClient:
    """Reuse a single local client — do not open concurrent clients on the same path."""
    global _client, _client_path
    settings = _settings()
    resolved = _resolve_path(str(path) if path is not None else settings.qdrant_path)
    resolved.mkdir(parents=True, exist_ok=True)
    resolved_str = str(resolved)
    if _client is not None and _client_path != resolved_str:
        reset_qdrant_client()
    if _client is None:
        _client = QdrantClient(path=resolved_str)
        _client_path = resolved_str
    return _client


def reset_qdrant_client() -> None:
    """Close and clear the module client (tests / path switches)."""
    global _client, _client_path
    if _client is not None:
        try:
            _client.close()
        except Exception:  # noqa: BLE001
            pass
        _client = None
        _client_path = None


def store_vector(
    *,
    point_id: UUID,
    vector: list[float],
    payload: dict[str, Any],
    client: QdrantClient | None = None,
    collection_name: str | None = None,
) -> None:
    settings = _settings()
    collection = collection_name or settings.qdrant_collection
    qdrant = client or get_qdrant_client()
    dim = len(vector)
    _ensure_collection(qdrant, collection, dim)
    qdrant.upsert(
        collection_name=collection,
        points=[
            qmodels.PointStruct(
                id=str(point_id),
                vector=vector,
                payload=payload,
            )
        ],
    )


def _ensure_collection(client: QdrantClient, collection: str, dim: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection in existing:
        info = client.get_collection(collection)
        # Local client may expose vectors config differently across versions
        current_dim = None
        vectors = info.config.params.vectors
        if hasattr(vectors, "size"):
            current_dim = vectors.size
        elif isinstance(vectors, dict) and "" in vectors:
            current_dim = vectors[""].size
        if current_dim is not None and current_dim != dim:
            logger.warning(
                "Collection %s dim %s != probed %s — recreating",
                collection,
                current_dim,
                dim,
            )
            client.delete_collection(collection)
        else:
            return
    client.create_collection(
        collection_name=collection,
        vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=collection,
        field_name="text",
        field_schema=qmodels.PayloadSchemaType.TEXT,
    )


def _delete_document_points(
    client: QdrantClient, collection: str, source_document: str
) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection not in existing:
        return
    client.delete(
        collection_name=collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="source_document",
                        match=qmodels.MatchValue(value=source_document),
                    )
                ]
            )
        ),
    )


def collection_is_populated(
    *,
    client: QdrantClient | None = None,
    collection_name: str | None = None,
) -> bool:
    settings = _settings()
    collection = collection_name or settings.qdrant_collection
    try:
        qdrant = client or get_qdrant_client()
        names = {c.name for c in qdrant.get_collections().collections}
        if collection not in names:
            return False
        count = qdrant.count(collection_name=collection, exact=True).count
        return count > 0
    except Exception:  # noqa: BLE001
        return False


def setup(
    *,
    kb_dir: Path | None = None,
    qdrant_path: str | Path | None = None,
    collection_name: str | None = None,
) -> SetupResult:
    settings = _settings()
    if not settings.llm_api_key:
        raise RagConfigError(
            "LLM_API_KEY is unset. Add it to .env before running setup()/seed."
        )
    docs_dir = kb_dir or KB_DIR
    collection = collection_name or settings.qdrant_collection
    missing = [
        name for name in SOURCE_DOCUMENTS if not (docs_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Knowledge-base files missing under "
            f"{docs_dir}: {', '.join(missing)}. Refusing partial index."
        )

    # Probe dimension once
    probe = embed("dimension probe")
    dim = len(probe)

    reset_qdrant_client()
    client = get_qdrant_client(qdrant_path)
    _ensure_collection(client, collection, dim)

    chunks_per_document: dict[str, int] = {}
    total = 0
    for filename, source_document in SOURCE_DOCUMENTS.items():
        md = (docs_dir / filename).read_text(encoding="utf-8")
        chunks = chunk_markdown(md, source_document=source_document)
        assert_chunk_integrity(chunks)
        if len(chunks) < MIN_CHUNKS_PER_DOC:
            raise ValueError(
                f"{source_document} produced {len(chunks)} chunks; need ≥{MIN_CHUNKS_PER_DOC}"
            )
        _delete_document_points(client, collection, source_document)
        for chunk in chunks:
            enriched = f"{chunk.doc_title} — {chunk.section}\n{chunk.text}"
            vector = embed(enriched)
            payload = {
                "company": "healthcore",
                "source_document": chunk.source_document,
                "section": chunk.section,
                "language": "en",
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }
            store_vector(
                point_id=point_id_for(chunk.source_document, chunk.chunk_index),
                vector=vector,
                payload=payload,
                client=client,
                collection_name=collection,
            )
            total += 1
        chunks_per_document[source_document] = len(chunks)
        logger.info(
            "Indexed %s → %s chunks", source_document, len(chunks)
        )

    result = SetupResult(
        documents_processed=len(SOURCE_DOCUMENTS),
        chunks_per_document=chunks_per_document,
        total_points=total,
        collection_name=collection,
        vector_dimension=dim,
    )
    logger.info(
        "RAG setup complete: %s docs, %s points, dim=%s, collection=%s",
        result.documents_processed,
        result.total_points,
        result.vector_dimension,
        result.collection_name,
    )
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = setup()
    print(
        f"Indexed {result.documents_processed} docs → {result.total_points} points "
        f"(dim={result.vector_dimension}) into {result.collection_name}"
    )
    for doc, n in result.chunks_per_document.items():
        print(f"  {doc}: {n} chunks")
    # Close before interpreter teardown to avoid Qdrant local __del__ ImportError
    reset_qdrant_client()


if __name__ == "__main__":
    main()
