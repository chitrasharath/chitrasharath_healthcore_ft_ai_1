# RFP Intake Pipeline (Milestone 9 Parts 1–2)

Dedicated LangGraph graphs — **not** part of the CX support agent.

## Layout

| Module | Role |
|--------|------|
| `convert.py` / `phi.py` / `metadata.py` / `readability.py` | Part 1 intake |
| `agents/` | classifier → orchestrator → workers → synthesizer |
| `graph.py` / `runner.py` | Part 1 LangGraph + BackgroundTasks / CLI |
| `agents/generator.py` | Part 2 per-department section generator |
| `agents/evaluators/` | readability / relevance / compliance + aggregate |
| `rules.py` | Compliance rule catalog (`phi-free`, BAA/DPA, currency) |
| `drafting_graph.py` | generate → parallel evaluate → aggregate → loop/limit |
| `drafting_runner.py` | `job_name=rfp_drafting` entry + concurrent sections |
| `repository.py` | Supabase upserts (intake + drafting) |

## Part 2 flow

1. Ticket at `intake_complete` → sales clicks **Start drafting**
2. `POST /api/v1/rfp-intake/tickets/{id}/start-drafting` → `Ticket.status=drafting` + `JobRun(rfp_drafting)`
3. Independent loops per department (concurrent): generate → evaluators (ThreadPool) → aggregate
4. Ticket flips to `under_evaluation` when any section enters evaluation
5. On pass → section `passed`; on iteration limit / PHI → `needs_human_review`
6. Phase 2 complete when every section ∈ {`passed`, `needs_human_review`}; ticket **stays** `under_evaluation`

### Concurrency

- Evaluators write disjoint state keys then a **single** aggregate DB write per iteration.
- Sections loop independently; one `needs_human_review` does not block others.

### PHI hard stop

Compliance runs detectors first. PHI → redact, `needs_human_review`, Compliance banner — **no** regenerate loop.

## CLI

```bash
# Part 1 re-run
uv run python -m data.pipelines.rfp_intake.runner --ticket-id <uuid>

# Part 2 drafting / single-section redraft
uv run python -m data.pipelines.rfp_intake.drafting_runner --ticket-id <uuid>
uv run python -m data.pipelines.rfp_intake.drafting_runner --ticket-id <uuid> --department-id revenue
```

Requires `DATABASE_URL`. Soft-idempotent start-drafting if already `drafting`/`under_evaluation`.

## Env

| Variable | Default | Role |
|----------|---------|------|
| `RFP_MAX_DRAFT_ITERATIONS` | 3 | Generate→evaluate cycles |
| `RFP_READABILITY_MAX_GRADE` | 12 | Flesch-Kincaid pass threshold |
| `RFP_GENERATOR_MODEL` | (empty → `GENERATION_MODEL`) | Generator override |
| `RFP_EVALUATOR_MODEL` | (empty → `GENERATION_MODEL`) | Relevance/compliance override |

## Readability

`compute_readability` auto-downloads NLTK `punkt` / `punkt_tab` on first use if missing. The API Docker image also pre-downloads them at build time.

If tokenizer data is missing or the text is too short (&lt; ~100 words for Flesch-Kincaid), metrics become `{ "status": "unavailable" }` and Part 2 soft-passes readability so the job continues.

## Status vocabulary

**Ticket:** `analyzing` \| `discarded` \| `intake_complete` \| `drafting` \| `under_evaluation` (Part 3: `waiting_for_approval` \| `done` — not set here)

**Section:** `drafting` \| `under_evaluation` \| `passed` \| `needs_human_review`
