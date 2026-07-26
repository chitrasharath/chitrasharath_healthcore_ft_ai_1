# Milestone 7 — RAG Knowledge Base — Build Spec

> **Audience:** the coding agent implementing this milestone.
> **Repo:** build **inside this monorepo** (`chitrasharath_healthcore_ft_ai_1`). All paths below are relative to the repo root unless noted.
> **Source material:** the four English knowledge-base documents will already be placed in `docs/company-knowledge-base/` (the product owner moves them there). Read them from that path — do not read from anywhere outside the repo at runtime.

---

## 1. Project Overview

Priya Nair (Head of Patient Experience) has 8 patient coordinators across 12 clinics who repeatedly answer the same front-desk and phone questions: which insurance is accepted, how cancellations work, how long an internal referral takes, and what a new patient must bring. New coordinators give inconsistent answers.

Build a **Retrieval-Augmented Generation (RAG)** assistant that a coordinator can consult at the desk. It answers **the way the clinic's best service salesperson would** — clear, empathetic, confident about what is documented, and **never inventing** insurance coverage, fees, or policies. Every answer must be traceable to a source document, and when the knowledge base has nothing relevant, the assistant must say so rather than guess.

This is a policy/procedure/service-catalog assistant only. **No real or realistic-looking PHI** (patient names, diagnoses, medical record numbers) may enter the knowledge base or any generated answer — a HIPAA / UK GDPR constraint that applies across the whole feature.

**In scope for this milestone**

1. An indexing/processing layer that chunks and embeds the source documents and stores vectors in Qdrant (`data/process/rag.py`).
2. A retrieval + generation pipeline (`data/pipelines/rag.py`).
3. A JWT-protected FastAPI endpoint `POST /api/v1/knowledge/query`.
4. A Next.js backoffice UI where a coordinator types a question and reads the answer.
5. Unit tests (`tests/pipelines/test_rag.py`) and a design document (`docs/rag-design.md`).

**Explicitly out of scope:** any patient-record data, chat history/memory, multi-turn conversation, streaming responses, and re-ranking models (may be suggested as follow-ups, not built here).

---

## 2. Resolved Decisions (read first)

These were decided with the product owner and override any ambiguity elsewhere:

| # | Decision | Value |
|---|---|---|
| 1 | Target repo | This monorepo (`chitrasharath_healthcore_ft_ai_1`). |
| 2 | Branch | **All work on `feature/rag`** (branched off `main`); PR into `main` when ready. See §17. |
| 3 | Qdrant deployment | **Local on-disk** via `qdrant-client` (no server container, no Qdrant Cloud). |
| 4 | Endpoint auth | **JWT-protected** — reuse `get_current_user`, same as the incidents/suppliers domains. |
| 5 | Language scope | **English only.** Index the four `.en.md` documents. `language` payload field is always `"en"`. |

---

## 3. Tech Stack

Match existing repo conventions — do not introduce parallel tooling.

**Backend (Python)**
- Python **3.12** (`requires-python = ">=3.12"`), managed by **uv** (workspace member `services/api`).
- **FastAPI** + **pydantic-settings** (`app/core/config.py` pattern), domain-oriented layout under `services/api/app/domains/`.
- **qdrant-client** (local mode) for vector storage.
- LLM access over HTTP to the 4Geeks LiteLLM proxy (OpenAI-compatible; see §7). Use `httpx` (already a dev dep; add to the API package deps) or the `openai` SDK pointed at the custom base URL — pick one and be consistent. **Recommendation: `httpx`** to avoid a new heavy dependency and keep the calls explicit.
- **pytest** + **pytest-cov** (already configured; `testpaths` includes `tests/`).

**Frontend (TypeScript)**
- **Next.js 16** (App Router), **React 19**, **Tailwind CSS v4**, **TypeScript 5**, **Jest** + ts-jest — mirror `uis/backoffice/landing/package.json`.
- Reuse `@backoffice/shared/lib/healthcore-api.ts` (`healthcoreFetch`) for authenticated calls — it already attaches the `Bearer` token from `localStorage` and handles `401`.

**Infra**
- No new Docker service required (Qdrant is local on-disk). The vector store persists to a repo path (see §6).

---

## 4. Source Documents & Seed Data

### 4.1 Source documents (already in the repo)
The knowledge-base sources are **saved in `docs/company-knowledge-base/`** (the product owner places them there — do not fetch or copy from elsewhere). Read exactly these four files and map each to its `source_document` value:

| File | `source_document` value |
|---|---|
| `docs/company-knowledge-base/healthcore-insurance-coverage.en.md` | `insurance-coverage` |
| `docs/company-knowledge-base/healthcore-appointment-policy.en.md` | `appointment-policy` |
| `docs/company-knowledge-base/healthcore-referral-process.en.md` | `referral-process` |
| `docs/company-knowledge-base/healthcore-new-patient-checklist.en.md` | `new-patient-checklist` |

Index **only** these four English files. Ignore any `.es.md` files (English-only scope) and never index `CONTEXT-rag-healthcore.en.md` — it is guidance, not knowledge-base content. If a file is missing, fail `setup()` loudly with a clear message rather than indexing a partial KB.

### 4.2 Evaluation queries — the golden set
Create `data/eval/test-queries.json` — the single golden dataset driving **both** retrieval and generation evaluation (§12). **At least 8** answerable questions covering **all four** documents (≥2 per document is ideal), **plus ≥2 should-abstain** questions (genuinely not in the KB), each annotated so the harness can score it automatically:

```json
[
  {
    "question": "Is there a charge for cancelling 12 hours in advance?",
    "expected_source_document": "appointment-policy",
    "expected_key_facts": ["50 USD", "40 GBP"],
    "should_abstain": false
  },
  {
    "question": "What do I need to bring to my first appointment?",
    "expected_source_document": "new-patient-checklist",
    "expected_key_facts": ["valid ID", "Insurance card"],
    "should_abstain": false
  },
  {
    "question": "Do you offer dental cleanings?",
    "expected_source_document": null,
    "expected_key_facts": [],
    "should_abstain": true
  }
]
```

Field meanings: `expected_source_document` = the doc that should appear in top-k (retrieval label); `expected_key_facts` = verbatim golden values the answer must contain (generation label); `should_abstain` = true when the correct behavior is the no-answer fallback.

Cover at least: insurance accepted in Georgia vs Texas (Medicaid nuance), US vs UK coverage, self-pay discount, cancellation windows, Medicare/Medicaid no-show rule, referral target time / 5-day escalation, and new-patient documents. Include **at least one Spanish-language question** against the English index — it exercises the answer-language rule (§8.2) and is the early-warning signal for weak cross-lingual retrieval that would justify prioritizing the bilingual follow-up. Keep every `expected_key_facts` value a real datum from the source docs — **never invent one**, and never add PHI.

**Never** add any datum that simulates a real patient record.

---

## 5. Domain Data Model (Qdrant payload)

Each stored point:

```json
{
  "id": "<deterministic-uuid>",
  "vector": [/* embedding, dimension probed at setup time */],
  "payload": {
    "company": "healthcore",
    "source_document": "insurance-coverage | appointment-policy | referral-process | new-patient-checklist",
    "section": "title or subtitle of the source section",
    "language": "en",
    "chunk_index": 0,
    "text": "the exact chunk text"
  }
}
```

- Payload field names are **fixed** by the context file: `company`, `source_document`, `section`, `language`, `chunk_index`. The assignment additionally requires **`text`** so retrieved chunks can be fed to the LLM and shown as provenance.
- `company` is always `"healthcore"`; `language` always `"en"` this milestone.
- `chunk_index` is the 0-based ordinal **within its `source_document`**.
- Distance metric: **COSINE**.

---

## 6. Backend — Processing Layer (`data/process/rag.py`)

> New file. Add an `__init__.py` if the package doesn't resolve. Follow the sys.path bootstrap pattern used by `data/pipelines/pipeline.py` if the module needs to import `app.*`.

Expose a small, testable module-level API. All configuration (URLs, model names, API key, collection name, storage path, thresholds) comes from **environment/config**, never hardcoded literals in function bodies — see §7 and §11.

> **Standalone key loading:** `data/process/rag.py` runs as a **CLI outside the FastAPI process** (§6.1), so it cannot rely on the API having loaded settings. It must load `LLM_API_KEY` (and the other LLM/Qdrant vars) **itself** from the environment / a repo-root `.env` at startup — e.g. reuse `app.core.config.Settings` (which reads `env_file`) or load the same `.env` directly. **Fail fast with a clear message if `LLM_API_KEY` is unset** rather than making an unauthenticated proxy call. The real key lives only in the git-ignored `.env`; `.example.env` keeps an empty placeholder.

### 6.1 `setup(...) -> SetupResult`
Reads the source documents, produces **semantic chunks**, and indexes them. **Must be idempotent** — running it twice yields the same collection contents (same point IDs, no duplicates, no drift).

Requirements:
- **Read** the four `.en.md` files from `docs/company-knowledge-base/`.
- **Semantic chunking — no sentence, bullet, or numbered step split in half.** Chunk on Markdown structure:
  - Treat the top `#` heading as the document title and each blank-line-separated block / subheading (e.g. `Cancellation policy:`, `United States (...)`, numbered lists) as a candidate section.
  - Keep a heading with the list/paragraph it introduces. A list is a unit — never cut between a bullet and its continuation line, and never mid-sentence.
  - Set `section` to the nearest heading/subtitle the chunk belongs to.
  - Target a soft max chunk size (e.g. ~500–800 tokens or ~1,200 chars) but **prefer semantic boundaries over hitting the size** — these documents are small.
  - Guarantee **≥ 3 chunks per document** (KPI). If a document naturally yields fewer, split at the next-lower heading level, still respecting sentence/bullet integrity.
- **Contextual embedding input (retrieval quality — do not skip):** the stored payload `text` stays the **clean, verbatim chunk body** (for faithful citation/provenance), but the string passed to `embed()` at index time must be **enriched with the document title + `section` heading**, e.g. `f"{doc_title} — {section}\n{chunk_text}"`. Payload fields are *not* part of the vector, so without this the embedding of a fragment like *"Cancelling less than 24 hours... 50 USD"* carries no "cancellation policy" signal. Enrich **passages only**; query embeddings are sent raw (this passage/query asymmetry is intended). The enrichment happens at the call site in `setup`, **not inside `embed()`** — see §6.2.
- **Idempotency mechanism:** derive each point ID deterministically, e.g. `uuid5(NAMESPACE, f"{source_document}:{chunk_index}")`. Re-running upserts the same IDs. Also make collection creation idempotent (create only if absent, or if the stored vector dimension differs from the probed dimension — see `store_vector`).
- **Stale-chunk cleanup (correctness — required):** deterministic IDs overwrite unchanged chunks, but they do **not** remove points that should no longer exist. If an edited document later yields *fewer* chunks, the old higher-index points linger as phantom answers. So, **per document, delete all existing points where `source_document == <that doc>` before upserting its fresh chunks** (Qdrant `delete` with a payload filter on `source_document`). Scope the delete to one document so re-indexing one file never disturbs the others. This makes `setup()` idempotent under content change, not just re-runs of identical content.
- Call `embed` for each chunk and `store_vector` to persist.
- Return a small result object/dict summarizing: documents processed, chunks per document, total points, collection name, vector dimension. Log the summary.
- Provide a CLI entry (`python -m data.process.rag` or `if __name__ == "__main__":`) so indexing can be run as a one-off build/seed step.

> **On-disk local Qdrant caveat (call out in code + design doc):** `qdrant-client` local mode holds a **file lock on the storage path — only one process may open it at a time.** The API process owns the store at runtime. Therefore run `setup()` **while the API is stopped**, or have the API perform an idempotent seed at startup within its own process. Recommended: a `scripts/seed_knowledge_base` (or Makefile/uv script) target that runs `setup()` before the API starts, plus an idempotent startup check that no-ops if the collection is already populated.

### 6.2 `embed(text: str) -> list[float]`
Accepts **either a chunk or a question** and returns its embedding vector.
- POST to the embeddings endpoint (§7) with the configured embedding model.
- Return the raw float vector.
- **`embed()` embeds exactly the string it is given** — it does **not** add titles/headings itself. Contextual enrichment for passages is applied by the caller (`setup`, §6.1); questions are passed through as-is. This keeps `embed()` a pure, symmetric primitive usable for both passages and queries.
- On non-2xx or malformed response, raise a typed error (e.g. `EmbeddingError`) with a clear message; never return a partial/None vector silently.
- Keep it single-item for clarity; a `embed_batch` helper is an acceptable optional addition but the required public signature is single-text.
- **Optional `input_type` seam:** if the chosen embedding model requires distinct query/passage handling (some models do; the Perplexity model's requirement is unconfirmed — verify against the proxy), add an optional `input_type: Literal["query", "passage"] = "query"` parameter that sets the model's prefix/param. If the model needs no such distinction, omit it. Do not silently ignore a required distinction — it degrades retrieval invisibly.

### 6.3 `store_vector(...) -> None` (create collection + upsert)
- **Create the Qdrant collection** if it does not exist, using the probed vector dimension and COSINE distance. If it exists with a mismatched dimension, recreate it (log a warning) — this keeps `setup` safe across embedding-model changes.
- **Upsert** the point(s) with the payload from §5.
- **Create a full-text payload index on `text`** at collection-creation time (Qdrant `create_payload_index`, text schema). Cheap now, and it's the seam that makes the hybrid-retrieval fallback in §8.1 a config change rather than a rewrite.
- Must be idempotent w.r.t. IDs (same ID overwrites, never duplicates).
- The Qdrant client (local on-disk path from config) is created once and reused; do not open multiple concurrent clients on the same path.

---

## 7. LLM & Embedding Access (4Geeks LiteLLM proxy)

Both models are served by an **OpenAI-compatible LiteLLM proxy**. Treat the base URL as OpenAI-style (`/v1/embeddings`, `/v1/chat/completions`).

| Purpose | Base URL | Model name |
|---|---|---|
| Embeddings | `https://llm.4geeks.ai` | `litellm/downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b` |
| Generation | `https://llm.4geeks.ai` | `litellm/downtown-miami/openrouter/deepseek/deepseek-v4-flash` |

Requirements:
- **API key** is required by the proxy → read from env `LLM_API_KEY` (add to `Settings` and `.example.env`). Send as `Authorization: Bearer <key>`.
- **Do not hardcode** URLs, model names, or keys — put them in `app/core/config.py` `Settings` (and mirror the ones the processing layer needs via env, since `data/process` may run outside the API process). Suggested settings: `llm_base_url`, `llm_api_key`, `embedding_model`, `generation_model`, `qdrant_path`, `qdrant_collection` (`"company_knowledge_base"`), `rag_top_k` (default `3`), `rag_min_score` (default a documented value, e.g. `0.30` for cosine — **tune against `test-queries.json` and record the chosen value in the design doc**).
- **Vector dimension is not given** — probe it once at setup time by embedding a short string and reading `len(vector)`. Never hardcode the dimension.
- Set sane timeouts and one bounded retry on transient (5xx/timeout) errors. Surface failures as typed errors so the endpoint can return a clean 502/503.

---

## 8. Backend — Pipeline Layer (`data/pipelines/rag.py`)

> New file alongside the existing `data/pipelines/pipeline.py`. Reuse the same repo-root sys.path bootstrap so `app.*` and `data.*` both import.

### 8.1 `retrieve(query: str, *, top_k: int = <config>, min_score: float = <config>) -> list[dict]`
- Embed the query via `embed` (§6.2).
- Search Qdrant for the **top-k nearest neighbors** (cosine).
- **Filter out any hit strictly below `min_score`.**
- Return the **surviving payloads** (list of payload dicts, each including `text`, `source_document`, `section`, `score`). Preserve descending-score order. Return `[]` when nothing survives.

> **Dense-only now, hybrid-ready (recommendation):** ship **dense vector search** for this milestone — with ~12–15 tiny chunks it should clear Recall@3 comfortably. But this corpus is dense with exact named entities (Bupa, "Medicaid in Georgia", "$50"), where pure dense retrieval can miss literal-term queries. So **enable a Qdrant full-text payload index on `text` at collection-creation time** (cheap, done in `store_vector`) to leave the seam in place. If the eval script (§12) shows named-entity misses, the fix is then a config-level change — add a full-text/keyword pre-filter or sparse vectors and fuse scores with the dense results — not a rewrite. Document this decision and trigger in the design doc.

### 8.2 `query(question: str) -> QueryResult` (orchestration)
Returns a small structured result so answers are **machine-traceable to their sources** (Context §7 requires answers be "traceable back to its source"):

```python
@dataclass
class QueryResult:
    answer: str
    sources: list[dict]  # [{source_document, section, score}], deduped, highest score first; [] when no answer
```

- Call `retrieve`.
- **If nothing survives the threshold**, return `QueryResult(answer=<fallback message>, sources=[])` — the fallback states the **knowledge base has no relevant information** for the question. Do **not** call the generation model and do **not** invent company information. (English, salesperson-polite tone, e.g. *"I don't have that in our knowledge base yet — let me check with the team and get back to you."*)
- Otherwise **assemble the prompt** from the retrieved chunks, call the **generation model** (§7), and return `QueryResult(answer=<generated answer>, sources=<from surviving chunks>)`. Build `sources` from the retrieved payloads — dedupe by `(source_document, section)`, keep the highest score per pair, ordered by score descending.

> The prompt should still cite the source in prose (§8.2 rules) **and** the structured `sources` list provides machine-readable provenance — the two are complementary.

- **Prompt-assembly format (required):** render the retrieved chunks as an explicit, **labeled** context block, one entry per surviving chunk, **ordered by score descending**, each labeled with its `source_document — section` so the model can cite accurately and keep facts attributable. Chunks are tiny — never truncate them. Example layout:

  ```
  [Source: appointment-policy — Cancellation policy]
  Cancelling more than 24 hours in advance: no charge...

  [Source: insurance-coverage — United Kingdom (London and Manchester)]
  HealthCore has a limited NHS contract...
  ```

  Use a clear separator between blocks; put the user's question after the context; instruct the model that **every fact it states must come from a labeled block above**, and if two blocks differ by country it must present United States and United Kingdom separately.

- **System/prompt rules (bake into the prompt):**
  - Answer **from a salesperson's perspective** — clear, warm, confident, concise; a coordinator can read it aloud to a patient.
  - **Only** use facts present in the retrieved chunks. Never state coverage, fees, or timeframes not in the context.
  - For an insurer **not listed** in the context, do not confirm coverage — say it must be verified with the billing team (Tom Callahan).
  - When a coverage question doesn't specify a country, **distinguish United States vs United Kingdom** explicitly.
  - **No-show fees must never be applied to Medicare or Medicaid patients** in the answer — follow the appointment policy literally.
  - **Never** include or invent PHI.
  - Cite the source (e.g. "per our appointment policy") where natural, so the answer is traceable.
  - **Answer language:** reply in the **language of the question**, but draw every fact from the English source chunks. Translate prose, **not** policy values — keep amounts (`$50` / `£40`), insurer names (Bupa, AXA Health, Medicaid…), and day-counts **verbatim**. Retrieval always runs against the English index regardless of query language. (This serves a Spanish-speaking coordinator without a bilingual KB and composes with the later `.es.md` follow-up.)
- Keep generation deterministic-ish (low temperature, e.g. `0.1–0.2`) for faithfulness.

---

## 9. Backend — API Endpoint

New domain: `services/api/app/domains/knowledge/`.

- `schemas.py`:
  - `KnowledgeQueryRequest { question: str }` — non-empty, trimmed; reject blank/oversized (`max_length`, e.g. 1000) with 422.
  - `KnowledgeSource { source_document: str, section: str, score: float }`.
  - `KnowledgeQueryResponse { query_id: str, answer: str, sources: list[KnowledgeSource] }`.
  - `KnowledgeFeedbackRequest { query_id: str, rating: Literal["up", "down"], comment: str | None }` — `comment` optional, trimmed, `max_length` (e.g. 2000).
  - `KnowledgeFeedbackResponse { status: str }`.
- `service.py`: thin wrapper calling `data.pipelines.rag.query(question)`; map the `QueryResult` (§8.2) to the response schema; translate typed pipeline/LLM errors into `HTTPException`s (502/503 with a friendly `detail`).
- `router.py`: `APIRouter(prefix="/knowledge", tags=["knowledge"])`. Register in `app/api/v1/router.py` **with** `dependencies=[Depends(get_current_user)]` (JWT-protected, per decision #4). Routes:
  - `POST /query` → `query()`. Final path: `POST /api/v1/knowledge/query`.
  - `POST /feedback` → persists a feedback record (§13). Final path: `POST /api/v1/knowledge/feedback`.
- **Query request body** `{"question": "..."}`.
- **Query response body** `{"query_id": "...", "answer": "...", "sources": [{"source_document": "...", "section": "...", "score": 0.0}]}`. `answer` is always present; `sources` is a (possibly empty) array — **empty when the knowledge base had no relevant information**, so the UI can distinguish a grounded answer from the no-answer fallback. `query_id` is a fresh UUID minted per query so UI feedback (§13) can be correlated back to this exact answer. This keeps the assignment's `{answer}` field intact while making every answer traceable to its source (Context §7).
- **Feedback request body** `{"query_id": "...", "rating": "up|down", "comment": "..."}`; response `{"status": "recorded"}`. See §13 for storage and the PHI constraint.
- The global exception handler already returns a clean 500; still catch expected failure modes explicitly for better status codes.

---

## 10. Frontend — Backoffice UI (`uis/backoffice/…`)

Create a Next.js app for the knowledge assistant, mirroring `uis/backoffice/landing` conventions. Suggested location: **`uis/backoffice/knowledge/`** (a per-domain app, consistent with `incident-manager`, `reporting`, `inventory`). Port `3001` family; wire it into whatever multi-app runner the backoffice uses.

Requirements:
- A single, focused view: a labeled **question textarea**, a **submit button** (disabled while empty or loading), and an **answer panel**.
- Call the endpoint through **`healthcoreFetch("/knowledge/query", { method: "POST", body: JSON.stringify({ question }) })`** from `@backoffice/shared` so the JWT is attached and `401` redirects to login. Do **not** hand-roll fetch/auth.
- **Loading state** (spinner/skeleton), **empty state**, and **error state**:
  - Network/5xx → friendly "Something went wrong, please try again."
  - `401` handled by the shared client (redirect); surface a message if it returns without redirect.
  - Show the "no relevant information" answer plainly (it's a valid 200 answer, not an error) — identifiable by an **empty `sources` array**.
- **Display the `sources`** returned with a grounded answer (e.g. a small "Sources" list of `source_document · section`) so coordinators can see where the answer came from. Hide the section when `sources` is empty.
- **Feedback widget (§13):** below each answer, show **thumbs up / thumbs down** controls and, on a down-vote (or via a "suggest a correction" link), an optional short comment field. On submit, `POST /knowledge/feedback` via `healthcoreFetch` with `{ query_id, rating, comment }` using the `query_id` from the query response. Reflect a brief "Thanks for the feedback" confirmation; the widget is **fire-and-forget** — a feedback failure must never block or hide the answer, just log/quietly toast. **Show a one-line notice near the comment field: "Do not include patient names or any personal health information."**
- **Light and dark mode** — use Tailwind's dark variant driven by `prefers-color-scheme` and/or a theme toggle consistent with the other backoffice apps. Verify both themes have adequate contrast.
- Accessibility: label the input, associate the button, announce results via an `aria-live` region; the thumbs controls have accessible labels and a pressed/selected state.
- **Frontend tests (Jest + ts-jest):** at minimum — renders the form; submitting calls the API client with the typed question; loading disables the button; a mocked success renders the answer **and its `sources`**; a mocked failure renders the error state; the "no relevant information" response (empty `sources`) renders as an answer with no sources list, not an error; **clicking thumbs-down posts feedback with the returned `query_id` and rating, and a feedback POST failure leaves the answer visible**. Mock `healthcoreFetch`.

---

## 11. Testing — `tests/pipelines/test_rag.py`

Unit tests for **all** functions, runnable from repo root via the existing pytest config. **Mock all network** (embeddings, generation) and use a **temporary on-disk Qdrant path** (pytest `tmp_path`) — no real proxy or persistent store in tests.

Cover:
- **`setup`**: reads all four docs; produces **≥3 chunks per document**; `section`/`chunk_index`/`source_document`/`company`/`language`/`text` payloads correct; **idempotent** (run twice → identical point count and IDs, no duplicates); no sentence/bullet split mid-way (assert chunks don't start/end mid-bullet for a known doc).
- **`embed`**: posts to the configured URL/model with the right auth header (assert on a mocked transport); returns the vector; raises `EmbeddingError` on non-2xx / malformed body.
- **`store_vector`**: creates the collection with the probed dimension + COSINE; upsert is idempotent (same ID overwrites); dimension-mismatch triggers recreate.
- **`retrieve`**: returns top-k; **filters out hits below `min_score`**; returns `[]` when all below threshold; preserves score order; returns payloads including `text`.
- **`query`**:
  - Happy path → assembles prompt from retrieved chunks, returns the mocked LLM answer, and **populates `sources`** (deduped by `(source_document, section)`, highest score per pair, score-descending).
  - **Empty retrieval → returns the "no relevant information" message with `sources == []` and does NOT call the generation model** (assert the generation mock is never called).
  - Prompt contains the guardrail instructions (salesperson tone; US/UK distinction; Medicare/Medicaid no-fee; verify-with-billing for unlisted insurers; no PHI).
- A **harness sanity check** driving `data/eval/test-queries.json` with a stubbed embedder to assert the eval loop wires up (the real metric runs need the proxy — see §12).

Aim for meaningful coverage of `data/process/rag.py` and `data/pipelines/rag.py`.

> **Unit tests (§11) vs. evaluation (§12) are different things.** §11 proves the code behaves (mocked, deterministic, runs in CI). §12 measures answer quality against the golden set (needs the real proxy, run before hand-off). Both are required.

---

## 12. Evaluation — `data/eval/run_eval.py`

A single script scores the pipeline against the golden set (§4.2) and prints a report. It has two tiers: **deterministic checks** (no LLM judge, CI-friendly) and an **opt-in LLM-judged** faithfulness check. Retrieval and the deterministic generation checks require the embedding proxy; keep the whole script **skipped in CI unless `LLM_API_KEY` is set**, and run it manually before hand-off. Emit metrics as both human-readable output and a JSON blob (for later regression tracking).

### 12.1 Retrieval metrics
For every answerable query (`should_abstain == false`), run `retrieve` and compute against `expected_source_document`:
- **Recall@3** — the KPI gate: **≥ 80%** of answerable queries have the expected doc in the top-3. (Primary pass/fail.)
- **Recall@1** and **MRR** — reported alongside, to see how often the right doc is rank-1 and how tuning shifts it.
- **Score distribution** — min/mean of the top hit for correct vs. incorrect retrievals; this is the evidence used to **calibrate `min_score`** (separate signal from noise without filtering out good chunks).

### 12.2 Abstention metrics
For every `should_abstain == true` query, assert `retrieve` returns nothing above `min_score` **and** `query` returns the fallback (empty `sources`). Report **false-answer rate** (abstain-query that got a confident answer — must be 0) and, across the whole set, confirm no answerable query was wrongly abstained. This is what keeps `min_score` honest: too high starves recall, too low invents answers.

### 12.3 Generation — deterministic checks
For every answerable query, run `query` and assert:
- **Key-fact correctness** — every string in `expected_key_facts` appears in the answer (verbatim policy values: `$50`/`£40`, insurer names, day-counts). Report **key-fact coverage %**.
- **Guardrail scenarios (required, promoted from suggested):** dedicated golden queries asserting —
  - unlisted insurer ("Do you accept Kaiser?") → answer says verify with billing, does **not** confirm coverage;
  - Medicare/Medicaid + no-show → answer states **no fee**;
  - country-ambiguous coverage question → answer contains **both** "United States" and "United Kingdom";
  - no-retrieval → fallback, generation model not called.
- **No-invention spot-check** — for a should-abstain query the answer must not contain any fabricated fee/insurer/timeframe.

These are plain string/regex assertions on golden values — fast, deterministic, no judge model.

### 12.4 Generation — faithfulness (opt-in LLM judge)
Because deterministic checks catch missing/known-wrong facts but not subtle unsupported claims, add an **opt-in** faithfulness grader (enabled by a flag / env var): for each answerable query, send the answer + its retrieved chunks to the generation model with a grader prompt — *"Is every claim in the ANSWER supported by the CONTEXT? Reply `SUPPORTED` or `UNSUPPORTED: <claim>`."* Report **faithfulness rate** and list offending claims. Non-deterministic and needs the proxy, so it never gates CI — it's the manual pre-hand-off quality gate for the Context §4 faithfulness constraint.

### 12.5 Pass thresholds (record actuals in the design doc)
- Recall@3 **≥ 80%** (hard gate, Context §4).
- False-answer rate on should-abstain queries **= 0** (hard gate — no invented coverage, Context §4/§6).
- Key-fact coverage **≥ 90%** (target; investigate misses).
- All guardrail scenarios **pass** (hard gate).
- Faithfulness rate (judged) **≥ 95%** (target; any UNSUPPORTED coverage/fee/timeframe is a blocker).

---

## 13. Feedback & Improvement Loop

Capture human preference signals from the UI to improve the system **offline**. This is the signal-collection layer of an RLHF-style loop — **not live/online RL**: the generation model is served by a hosted proxy (§7) whose weights you don't own and cannot fine-tune from the app. Any implication that the model "learns" live from clicks would be wrong; what this provides is a preference dataset for offline iteration.

### 13.1 Capture (UI — §10)
Thumbs up/down on every answer, plus an optional short comment (surfaced on down-vote). The UI submits `{ query_id, rating, comment }` to `POST /knowledge/feedback`, correlating the vote to the exact answer via the `query_id` from the query response. Fire-and-forget — feedback never blocks the answer.

### 13.2 Interaction logging & storage
The store is designed so each record is a **self-contained, reproducible training example** — a `(prompt, response, human preference)` tuple you can turn into DPO/reward data later, without needing this codebase or the original chunks.

- **On every `POST /query`**, the service writes an **interaction record** keyed by the minted `query_id`. Required fields:
  - `schema_version` — integer/semver on **every** record, bumped when the shape changes, so old data never strands (§13 requirement).
  - `query_id`, `timestamp`, `user_id` (from JWT).
  - `question`, `answer`.
  - `sources` (doc/section/score) **and `context_texts`** — the actual chunk `text` fed to the model, so the example is reproducible even after the KB or chunking changes.
  - `generation` reproducibility: `model`, `temperature`, and either the **fully assembled prompt** or enough to reconstruct it (system prompt version + `context_texts`).
  - `session_id` and optional `parent_query_id` — see 13.2a (preference-pair enabler).
  This means feedback need only send `query_id + rating + comment`; the server already holds the answer context, and the client can't spoof it.
- **On `POST /feedback`**, attach `rating` + `comment` (+ feedback `timestamp`) to the matching `query_id` record.
- **Store:** an append-only **JSONL file** at a configurable `FEEDBACK_PATH` (default `data/eval/feedback.jsonl`, git-ignored), or a small SQLModel table if `DATABASE_URL` is set. **Recommendation: JSONL** — zero new infra and it feeds the offline scripts directly. Writes must be append-only and tolerant of concurrent appends (line-buffered, one JSON object per line). If append-only, model feedback as a **second line referencing `query_id`** rather than mutating the original line.
- Unknown `query_id` on feedback → `404` (don't create orphan feedback).

#### 13.2a Preference-pair enabler (optional but recommended)
Thumbs up/down alone is **pointwise**; DPO/reward training wants **pairwise** *chosen vs. rejected for the same intent*. Cheap enabler: give the UI a per-session `session_id`, and when a coordinator re-asks or edits a question after a down-vote, send the previous `query_id` as `parent_query_id`. That lets the offline loop reconstruct `(rejected answer, chosen answer)` pairs for the same question instead of only isolated labels. Optional to wire up now, but the fields should exist in the schema from day one so the signal isn't lost.

### 13.3 Offline improvement loop (documented process — not automated)
Periodically (a human-run review, or a later scheduled job) mine the feedback:
- **Down-voted answers →** add the question (with the corrected expectation) to the golden set `test-queries.json` (§4.2) so the failure is measured going forward.
- **Retrieval tuning →** compare `retrieval_scores` on up- vs. down-voted answers to re-tune `RAG_MIN_SCORE` / `top_k`, and flag named-entity misses that justify the hybrid seam (§8.1).
- **Prompt curation →** promote up-voted exemplars into few-shot examples for the generation prompt (§8.2).
- **KB gaps →** cluster down-votes that map to no/low retrieval into requests for **new source documents**.
- **(Future) preference tuning →** if an open, self-hosted generation model is ever adopted, the records (13.2) become a DPO/reward dataset — pointwise from ratings, and pairwise where `parent_query_id` links a rejected→chosen pair (13.2a). Out of scope to *train* now; the schema is deliberately built so nothing needed for it is lost. **Reuse is gated on the 13.4 scrub/consent step.**

### 13.4 Constraints (feedback-specific)
- **No live model updates from UI interactions** — offline only.
- **PHI — and the reuse gate (important, since this data is meant to be used later):** `question` and `comment` are free text a coordinator could accidentally fill with patient identifiers. The UI warns against it (§10); the server must **never log** raw feedback content at INFO, should keep the store access-controlled and git-ignored. Because the whole point is to *reuse* this data for training, treat PHI as a hard gate on reuse, not just on logging:
  - **Capture-time filter:** run a lightweight PII/PHI screen (regex for MRN-like IDs, emails, phones, obvious name patterns) before persisting; redact or drop flagged fields. It won't be perfect — it's defense in depth, not the guarantee.
  - **Scrub/consent before training:** no record may enter a training/eval-reuse set until it passes an explicit scrub-and-review pass. Document this as a required step in the design doc.
  - **Retention:** note a retention window and a deletion path (a record can be removed by `query_id`).
  This upholds the project-wide HIPAA / UK GDPR constraint — untriaged PHI in the store would make the dataset legally unusable, defeating the purpose.
- Feedback is **JWT-protected** (same dependency as `/query`); `user_id` comes from the token, never the client body.

### 13.5 Tests
- **Backend:** `POST /feedback` with a valid `query_id` records the rating (assert it lands in the store); unknown `query_id` → 404; a `/query` call writes an interaction record carrying the **reproducibility fields** (`schema_version`, `context_texts`, `model`, and prompt/params); feedback content is not emitted to logs.
- **PII filter:** a `question` containing an obvious identifier (e.g. an MRN-like string or email) is redacted/dropped before persistence — assert the raw identifier is not in the stored record.
- **Frontend:** covered in §10 (thumbs-down posts with the returned `query_id`; a feedback failure leaves the answer visible).

---

## 14. Design Document — `docs/rag-design.md`

Author a concise design doc covering:
- **Problem & goals** (front-desk assistant, salesperson tone, no invented policy/PHI).
- **Architecture diagram / flow:** documents → chunk → embed → Qdrant → retrieve (top-k, min_score) → prompt assembly → generation → answer; and the API + UI wrapping it.
- **Chunking strategy** and why it preserves sentence/bullet integrity; chunk counts per document.
- **Embedding & generation models**, URLs, and how dimension is probed.
- **Qdrant local on-disk choice**, the single-process file-lock caveat, and how seeding/serving avoid contention.
- **Payload schema** (§5) and the ID/idempotency scheme.
- **Retrieval params:** chosen `top_k`, chosen `min_score` and how it was tuned against `test-queries.json`.
- **Retrieval strategy:** dense-only for now, the full-text-index seam, and the concrete trigger (named-entity misses in the eval) that would promote it to hybrid.
- **Contextual embedding:** title/section enrichment of the embedding input vs. clean payload `text`, and the passage/query asymmetry.
- **Prompt assembly & answer-language rule:** the labeled-context format and the "answer in the question's language, values verbatim" policy.
- **Guardrails & KPIs:** how the design meets Recall@3 ≥ 80%, faithfulness, unlisted-insurer handling, US/UK distinction, Medicare/Medicaid no-fee, and the no-answer fallback.
- **PHI / HIPAA / UK GDPR** posture.
- **Evaluation results** — the actual Recall@3 / Recall@1 / MRR, key-fact coverage, and (if run) faithfulness numbers from §12, plus the tuned `min_score`.
- **Feedback loop** (§13) — what signals are captured, the PHI/retention posture, and how the offline loop would consume them.
- **Trade-offs and future work** (see §18 suggested tasks and §19 alternative models).

---

## 15. Constraints

- **No PHI, real or realistic** — anywhere in the KB, prompts, logs, or answers. Do not add simulated patient records.
- **Faithfulness:** no coverage, fee, or timeframe in an answer may differ from retrieved chunks.
- **Unlisted insurer** → must say "verify with billing (Tom Callahan)"; never confirm undocumented coverage.
- **US vs UK** coverage must be distinguished when the question omits the country.
- **Medicare/Medicaid** patients are never charged a no-show fee in a generated answer.
- **No LangChain / LlamaIndex** — work directly with the **Qdrant SDK** and **FastAPI**.
- Functions must live exactly where specified: `data/process/rag.py` (setup, embed, store_vector) and `data/pipelines/rag.py` (retrieve, query).
- `setup` must be **idempotent**; chunking must not split sentences/bullets/steps.
- No hardcoded secrets/URLs/model names/dimensions — all via config/env.
- Follow existing repo conventions (domain layout, uv workspace, Next.js/Jest per-app structure).

---

## 16. Dependencies

**New Python deps** (add to `services/api/pyproject.toml`; `uv lock`):
- `qdrant-client`
- `httpx` (promote from dev to runtime dep for the API package, or `openai` if chosen instead)

**New env vars** (add to `Settings` and `.example.env`):
- `LLM_BASE_URL=https://llm.4geeks.ai`
- `LLM_API_KEY=` (required; obtain from the 4Geeks proxy)
- `EMBEDDING_MODEL=litellm/downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b`
- `GENERATION_MODEL=litellm/downtown-miami/openrouter/deepseek/deepseek-v4-flash`
- `QDRANT_PATH=./data/qdrant` (on-disk local store; git-ignore this path)
- `QDRANT_COLLECTION=company_knowledge_base`
- `RAG_TOP_K=3`
- `RAG_MIN_SCORE=0.30` (tune; document final value)
- `FEEDBACK_PATH=./data/eval/feedback.jsonl` (append-only feedback/interaction log; git-ignore this path — §13)

**Frontend deps:** none beyond the `landing` app baseline (Next 16, React 19, Tailwind 4, Jest).

**External services:** the 4Geeks LiteLLM proxy (network access + valid API key) for real runs; fully mocked in tests.

---

## 17. Development Workflow

1. **Create and check out the branch `feature/rag`** off `main`, and do **all** work for this milestone on it — code, tests, the golden set, and the design doc. Do not commit to or push `main`; when the work is ready, open a PR from `feature/rag` into `main`. Do not commit or push unless asked.
2. Confirm the source docs are in `docs/company-knowledge-base/` (§4.1); author the golden set `data/eval/test-queries.json` (§4.2). Git-ignore `QDRANT_PATH`.
3. Add config/env (§16). `uv sync` / `uv lock` after editing `pyproject.toml`.
4. Implement `data/process/rag.py` (`setup`, `embed`, `store_vector`) → run the CLI seed once to build the local store.
5. Implement `data/pipelines/rag.py` (`retrieve`, `query`).
6. Add the `knowledge` domain + register the JWT-protected `/query` and `/feedback` routes (§9, §13); smoke-test with `curl` (with a valid bearer token) and Swagger at `/docs`.
7. Build `uis/backoffice/knowledge/` UI against the endpoint — question flow, sources, and the feedback widget (§13); verify light/dark and error paths.
8. Write unit + frontend tests (`tests/pipelines/test_rag.py` + Jest). Run:
   ```bash
   uv run pytest tests/pipelines/test_rag.py -v
   ```
   and the frontend:
   ```bash
   npm --prefix uis/backoffice/knowledge test
   ```
9. Implement `data/eval/run_eval.py` (§12). Run it against the golden set and **tune `RAG_MIN_SCORE`** using the score distribution:
   ```bash
   LLM_API_KEY=… uv run python data/eval/run_eval.py
   ```
   Confirm the §12.5 gates: Recall@3 ≥ 80%, false-answer rate = 0, all guardrail scenarios pass.
10. Write `docs/rag-design.md`, recording the tuned `min_score` and the actual eval numbers.
11. Ensure `uv run pytest` (whole suite) and each app's `verify` (lint + build) pass before handing off.

**Definition of done:** all five functions in place at the specified paths; endpoint returns `{"answer": …, "sources": […]}` for `{"question": …}` (sources empty on the no-answer fallback); UI renders the answer and its sources in both themes with error handling; **feedback capture works end-to-end (thumbs up/down → `/feedback` → interaction record persisted, PHI notice shown, feedback failure non-blocking)**; unit + frontend tests pass; **`run_eval.py` meets the §12.5 gates (Recall@3 ≥ 80%, false-answer rate = 0, guardrail scenarios pass) with actuals recorded in the design doc**; design doc written; no hardcoded secrets; idempotent setup verified; guardrails demonstrably enforced (including the no-answer fallback and Medicare/Medicaid rule).

---

## 18. Suggested Additional Tasks (to improve model outcomes)

These are **recommendations** beyond the required scope — implement if time allows or flag as follow-ups:

> The automated eval script and the guardrail scenarios are now **required** (§12), not suggestions.

1. **Query pre-processing** — lightweight normalization (trim, collapse whitespace, optional lowercase) and a max-length guard before embedding.
2. **Caching embeddings for chunks** — persist chunk embeddings to avoid re-embedding unchanged docs on re-`setup()` (keying on a content hash), reducing proxy calls and making idempotency cheaper.
3. **Chunk-integrity assertion in setup** — a validation pass that fails loudly if any chunk begins/ends mid-sentence or mid-bullet, encoding the "no half-sentence" rule as a guarantee, not just intent.
4. **Observability** — reuse the repo's telemetry hooks to log query volume, retrieval hit-rate, and no-answer rate (never logging PHI or full questions if they could contain it).
5. **Bilingual follow-up** — the `.es.md` sources exist; a later milestone can index Spanish with `language="es"` and route by detected query language. The payload/`language` field is already designed for it.
6. **Config seam for a hosted Qdrant** — keep the client construction behind a factory so switching from local on-disk to Qdrant server/Cloud is a config change, not a rewrite (removes the single-process lock limitation when scaling).
7. **Semantic-boundary chunker unit** — factor chunking into a pure, separately tested function (input markdown → list of `(section, text)`), independent of embeddings/Qdrant, for fast deterministic tests.

---

## 19. Suggested Alternative Models

The specified models (`pplx-embed-v1-0.6b` for embeddings, `deepseek-v4-flash` for generation) are the required defaults and are a reasonable fit — small, fast, cheap, and adequate for a tiny English policy corpus. Because both are reached through the LiteLLM proxy and all model names live in config, swapping is low-cost. Alternatives that fit this use case, if available on the proxy:

**Embeddings** (short English policy text, needs strong retrieval on paraphrased desk questions):
- **`text-embedding-3-small` (OpenAI, 1536-d)** — excellent retrieval quality per dollar; a strong default if higher Recall@3 is needed.
- **`voyage-3` / `voyage-3-lite` (Voyage AI)** — top-tier retrieval; `-lite` keeps latency/cost low. Good if the perplexity embed under-performs on paraphrase.
- **`bge-small-en-v1.5` / `e5-small-v2`** — open, self-hostable, small; useful if you later want to drop the external dependency for embeddings.
- **`text-embedding-3-large` (3072-d)** — only if retrieval quality is the bottleneck; higher cost/latency and larger vectors, unnecessary for this corpus size.

> Whichever is chosen, **dimension is probed at setup**, so changing the embedding model just needs a re-`setup()` (collection recreates on dimension mismatch by design).

**Generation** (must be faithful, concise, warm; short outputs):
- **`gpt-4o-mini` / `gpt-4.1-mini`** — strong instruction-following and faithfulness at low cost; a safe upgrade if DeepSeek-flash drifts from context.
- **`claude-haiku-4-5`** — fast, low-cost, very good at "answer only from provided context" and tone control; a good fit for the strict no-invention guardrails.
- **`gemini-2.x-flash`** — comparable speed/cost tier; fine alternative if already provisioned.
- Keep **temperature low (~0.1–0.2)** on whichever model to favor faithfulness over creativity.

**Recommendation:** keep the required models as the default; if the KPI evaluation (task #2 above) shows Recall@3 < 80% or faithfulness lapses, switch embeddings to `text-embedding-3-small` and/or generation to `gpt-4o-mini`/`claude-haiku-4-5` via config — no code change.

---

## 20. Open Assumptions (verify if convenient)

- The 4Geeks proxy is **OpenAI-compatible** (`/v1/embeddings`, `/v1/chat/completions`) and needs a bearer API key. If its schema differs, adapt the HTTP calls in `embed` and the generation call accordingly (isolate them so only one function changes).
- The backoffice multi-app runner (`uis/backoffice/start.sh` / Dockerfile) may need a new entry for the `knowledge` app — wire it in following how `landing`/`reporting` are registered.
- `RAG_MIN_SCORE` default `0.30` is a starting point for cosine on this embedder; **the implementer must tune and record the final value**.
