# RFP Intake Pipeline (Milestone 9 Parts 1–3)

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
| `drafting_graph.py` / `drafting_runner.py` | Part 2 generate→evaluate loops |
| `arbitration.py` | Part 3 deterministic conflict triggers (no LLM) |
| `approval_graph.py` / `approval_runner.py` | Part 3 interrupts, resume, run-all chain |
| `checkpointer.py` | PostgresSaver (`thread_id = ticket_id`) + MemorySaver for tests |
| `final_document.py` | Markdown + PDF consolidation |
| `transitions.py` / `owners.py` / `node_logging.py` | Status guard, fixed owners, redacted logs |
| `repository.py` | Supabase upserts |

## Part 3 flow

1. **Run all phases** — `POST /api/v1/rfp-intake/run-all` (multipart PDF) → one `rfp_run_all` JobRun: intake → drafting → **approval** (Phase 3 starts automatically when all sections `passed`). Halts only for Part-1 discard/human_review or Phase-2 `needs_human_review`; after Re-draft clears those sections, Phase 3 auto-starts.  
2. **Run Phase 3** — stepwise only (non–run-all tickets) when all sections `passed`, `POST .../send-for-approval`  
3. Mid-pipeline — `POST .../start-drafting?continue_to_approval=true` (P2→P3, no PDF)  
4. Approval graph: arbitration → interrupt gates (dept-matched resume) → final document  
5. Decisions: `POST .../departments/{id}/decision` with owner name-string  
6. On `done`: GET markdown/PDF; UI auto-downloads once + persistent Download button  

### Checkpointer

`langgraph-checkpoint-postgres` + `psycopg` pool over `DATABASE_URL`. Call `.setup()` once on first use. Unit tests use `MemorySaver` (`use_memory=True`). Empty `DATABASE_URL` or a Postgres connect/setup failure **raises** — there is no silent MemorySaver fallback.

Pool connections use `prepare_threshold=None` (disable server prepared statements) so Supabase/PgBouncer and concurrent writers do not raise `DuplicatePreparedStatement` (`_pg3_*`).

### Arbitration (priority)

1. `phi-detected` (incl. `phi_was_redacted`) → Claire Whitfield  
2. `baa-dpa-mismatch` → Claire  
3. `capacity-vs-population` (both sides numeric) → Tom Callahan  

## CLI

```bash
# Part 1 re-run
uv run python -m data.pipelines.rfp_intake.runner --ticket-id <uuid>

# Part 2 drafting
uv run python -m data.pipelines.rfp_intake.drafting_runner --ticket-id <uuid>

# Part 3 approval / resume / run-all
uv run python -m data.pipelines.rfp_intake.approval_runner --ticket-id <uuid>
uv run python -m data.pipelines.rfp_intake.approval_runner --ticket-id <uuid> --run-all
uv run python -m data.pipelines.rfp_intake.approval_runner --ticket-id <uuid> \
  --resume-department compliance --decision approve --approver "Claire Whitfield"
```

## Env

| Variable | Default | Role |
|----------|---------|------|
| `RFP_MAX_DRAFT_ITERATIONS` | 3 | Generate→evaluate cycles |
| `RFP_MAX_APPROVAL_ITERATIONS` | 3 | Approve↔re-approve bound (per section) |
| `RFP_READABILITY_MAX_GRADE` | 12 | Flesch-Kincaid pass threshold |
| `RFP_GENERATOR_MODEL` / `RFP_EVALUATOR_MODEL` | (generation model) | Optional overrides |

## Status vocabulary

**Ticket:** `analyzing` \| `discarded` \| `intake_complete` \| `drafting` \| `under_evaluation` \| `waiting_for_approval` \| `done`

**Section:** `drafting` \| `under_evaluation` \| `passed` \| `needs_human_review`

**Approval:** `pending` \| `approved` \| `request_changes`
