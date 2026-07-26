# RAG Knowledge Base — Design

## Problem & goals

Patient coordinators need consistent, faithful answers to recurring desk questions (insurance, cancellations, referrals, new-patient intake). This milestone delivers a Retrieval-Augmented Generation assistant that:

- Answers in a clear, warm, salesperson tone suitable to read aloud to patients
- Never invents coverage, fees, or policies
- Always traces answers to source documents (or abstains)
- Never introduces PHI

## Architecture

```text
docs/company-knowledge-base/*.en.md
        │
        ▼
 data/process/rag.setup ──embed──► local Qdrant (COSINE)
        │
        ▼
POST /api/v1/knowledge/query (JWT)
        │
        ▼
 data/pipelines/rag.query
   ├─ retrieve (top_k, min_score)
   ├─ empty → fallback, no LLM
   └─ hits → labeled prompt → generation model → answer + sources
        │
        ▼
uis/backoffice/knowledge (landing :3001)
   + thumbs feedback → JSONL (data/eval/feedback.jsonl)
```

Seeding: `scripts/seed_knowledge_base.py` runs `setup()` (prefer API stopped — local Qdrant file lock). API startup no-ops if the collection is already populated; seeds once if empty and `LLM_API_KEY` is set.

## Chunking

Semantic Markdown chunking in `chunk_markdown()`:

- Document `#` title + blank-line / subtitle blocks (`Cancellation policy:`, country sections, numbered process groups)
- Never split mid-sentence or mid-bullet; soft max ~1,200 chars
- KPI: ≥3 chunks per document (verified in unit tests)
- `assert_chunk_integrity()` fails loud on orphaned mid-bullet starts

**Contextual embedding:** payload `text` stays verbatim; the string sent to `embed()` at index time is `{doc_title} — {section}\n{chunk_text}`. Queries are embedded raw.

## Models & dimension

| Role | Proxy | Model (config) |
|------|-------|----------------|
| Embeddings | `LLM_BASE_URL` `/v1/embeddings` | `EMBEDDING_MODEL` (default Perplexity pplx-embed-v1-0.6b via LiteLLM) |
| Generation | `/v1/chat/completions` | `GENERATION_MODEL` (default DeepSeek v4 flash) |

Vector dimension is **probed** at setup (never hardcoded). Temperature ~0.15.

## Qdrant

- Local on-disk (`QDRANT_PATH`, default `./data/qdrant`)
- Collection `company_knowledge_base`, COSINE
- Deterministic point IDs: `uuid5(NAMESPACE, "{source_document}:{chunk_index}")`
- Per-document delete-before-upsert for stale-chunk cleanup
- Full-text payload index on `text` created at collection setup (no effect in local mode; seam for future hybrid retrieval)

**File lock:** only one process may open the local store. Seed with API stopped, or let API own the store at runtime.

## Payload schema

`company`, `source_document`, `section`, `language` (`en`), `chunk_index`, `text`

## Retrieval

- Dense-only `query_points`, `RAG_TOP_K=3`
- Filter hits strictly below `RAG_MIN_SCORE` (default start `0.30`; **tune with `data/eval/run_eval.py` and record the final value here**)
- Hybrid (keyword/full-text fusion) deferred until named-entity misses appear in eval

### Tuned params (fill after live eval)

| Param | Value | Notes |
|-------|-------|-------|
| `RAG_TOP_K` | 3 | Spec default |
| `RAG_MIN_SCORE` | _TBD — run eval_ | Calibrate from correct vs incorrect top-score distribution |

## Prompt & answer language

Labeled context blocks:

```text
[Source: appointment-policy — Cancellation policy]
…
```

System rules: salesperson tone; facts only from context; unlisted insurer → Tom Callahan; US/UK distinction; Medicare/Medicaid never charged no-show fees; no PHI; answer in the question’s language with policy values verbatim.

## Guardrails & KPIs

| Gate | Target |
|------|--------|
| Recall@3 | ≥ 80% |
| False-answer rate (abstain set) | = 0 |
| Key-fact coverage | ≥ 90% |
| Guardrail scenarios | all pass |
| Faithfulness (opt-in judge) | ≥ 95% |

Eval: `uv run python data/eval/run_eval.py` (skipped without `LLM_API_KEY`). Optional `--judge`.

### Eval results (fill after hand-off run)

| Metric | Value |
|--------|-------|
| Recall@3 | _TBD_ |
| Recall@1 | _TBD_ |
| MRR | _TBD_ |
| Key-fact coverage | _TBD_ |
| False-answer rate | _TBD_ |
| Faithfulness | _TBD_ |

## PHI / HIPAA / UK GDPR

- KB docs contain no patient records
- UI warns against PHI in feedback comments
- Server regex-redacts emails, phones, MRN-like tokens before JSONL persist
- Feedback store git-ignored; no INFO logging of raw comments
- **Reuse gate:** scrub + human review required before any training/eval reuse; retention via delete-by-`query_id`

## Feedback loop

Append-only JSONL (`FEEDBACK_PATH`):

1. Interaction line on every `/query` (`schema_version`, `query_id`, question/answer, `sources`, `context_texts`, generation prompt/params, nullable `session_id` / `parent_query_id`)
2. Feedback line on `/feedback` referencing `query_id`

Offline uses: expand golden set from down-votes; retune `min_score`; promote up-voted exemplars; cluster KB gaps. No live model updates. UI pairing for preference pairs is deferred (schema ready).

## UI

- Landing-aliased module `uis/backoffice/knowledge` at `/knowledge`
- Hub card “Knowledge Assistant” (New)
- Shared light/dark theme toggle (`@backoffice/shared`) on tool toolbar + root `dark` class

## Trade-offs & future work

- Dense-only on a tiny corpus should clear Recall@3; hybrid seam reserved for entity misses
- Local Qdrant blocks multi-process access — acceptable for milestone; hosted client factory later
- Embedding cache, bilingual `.es.md`, telemetry hit/no-answer rates deferred
- Swap embed/gen models via env if KPIs fail after prompt/`min_score` tuning
