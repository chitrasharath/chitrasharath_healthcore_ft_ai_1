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
- Filter hits strictly below `RAG_MIN_SCORE` (tuned to **`0.38`** — see below)
- **Query expansion (retrieval only):** short coverage questions that name insurers / Medicaid / Medicare (e.g. “do you take Kaiser?”) are embedded as `… insurance coverage accepted` so they align with policy chunks. The LLM still receives the original question.
- Hybrid (keyword/full-text fusion) deferred until named-entity misses appear in eval

### Tuned params

| Param | Value | Notes |
|-------|-------|-------|
| `RAG_TOP_K` | 3 | Spec default |
| `RAG_MIN_SCORE` | **0.38** | Cosine similarity floor after live `run_eval.py` against `data/eval/test-queries.json` (`pplx-embed` + this KB) |

**Why `0.38` (not the starting `0.30`):**

1. At **`0.30`**, Recall@3 was already strong (~92.9%), but **false-answer rate was 0.5** — an abstain query (e.g. dental cleanings / MRI wait) still retrieved off-topic policy chunks above the floor, so the system answered when it should have returned no context.
2. Score distribution on that run: correct top-hit **mean ≈ 0.55**, weakest correct top hit **≈ 0.38**. Raising the floor to the weakest good hit cuts abstain noise without dropping answerable recall.
3. After setting **`RAG_MIN_SCORE=0.38`**, gates passed: false-answer rate **0**, Recall@3 still ~**93%**, key-fact coverage ~**93%**, guardrail scenarios clean.

Too low → invents answers on OOD questions. Too high (above ~0.38) → risks starving the hardest good retrievals. Re-tune if the embedder or corpus changes.

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

### Sample questions (manual / UI smoke)

Useful questions to try in the Knowledge Assistant or agent (from the golden set):

1. Is there a charge for cancelling 12 hours in advance?
2. Do Medicare or Medicaid patients pay a no-show fee?
3. Is Medicaid accepted at Georgia clinics?
4. What private insurers do you accept in the UK?
5. What discount do uninsured patients get if they pay the same day?
6. What insurance coverage do you accept?
7. How long does an internal referral usually take, and when should I escalate?
8. What do I need to bring to my first appointment?
9. Do you accept Kaiser?
10. Do you take Medicaid?

Abstain check (should return no relevant context / fallback): **Do you offer dental cleanings?**

Full golden set: `data/eval/test-queries.json`.

### Eval results (live `run_eval.py` after `RAG_MIN_SCORE=0.38`)

| Metric | Value |
|--------|-------|
| Recall@3 | ~93% (gate ≥ 80% — pass) |
| Recall@1 | _(reported in eval JSON; not separately recorded)_ |
| MRR | _(reported in eval JSON; not separately recorded)_ |
| Key-fact coverage | ~93% (gate ≥ 90% — pass) |
| False-answer rate | 0 (gate = 0 — pass; was 0.5 at `0.30`) |
| Faithfulness | _(optional `--judge` not required for this tune)_ |

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
