# RFP Intake Pipeline (Milestone 9 Part 1)

Dedicated LangGraph intake graph — **not** part of the CX support agent.

## Layout

| Module | Role |
|--------|------|
| `convert.py` | PDF → markdown (`markitdown`) |
| `phi.py` | Detect + redact via existing HealthCore PHI helpers |
| `metadata.py` | Structured LLM extraction (no invented values) |
| `readability.py` | `py-readability-metrics` with graceful degrade |
| `extracts.py` | Heuristic department snippets |
| `agents/` | classifier → orchestrator → workers → synthesizer |
| `graph.py` | LangGraph `StateGraph` |
| `runner.py` | BackgroundTasks / CLI entry |
| `repository.py` | Supabase upserts |

## Checkpoints

`converted` → `phi_scanned` → `metadata` → `readability` → `classified` → `orchestrated` → `workers_done` → `synthesized`

Stored on `JobRun.checkpoint` (`job_name=rfp_intake`, `target_key=ticket_id`).

## Re-run

```bash
# Requires DATABASE_URL
uv run python -m data.pipelines.rfp_intake.runner --ticket-id <uuid>
# or API: POST /api/v1/rfp-intake/tickets/{ticket_id}/rerun
```

Re-runs are **from-scratch idempotent upserts** (not checkpoint resume).

## PHI

- Detectors: `detect_phi`, `redact_pii`, `validate_no_phi`
- On hit: `contains_phi=true`, redact before DB text / worker prompts / UI
- PDF binary under `data/raw/{ticket_id}.pdf` is the only raw artifact
- Never commit PHI fixtures with real patient strings

## Readability

If NLTK `punkt` is missing, metrics become `{ "status": "unavailable" }` and the job continues.

## Status vocabulary

`analyzing` | `discarded` | `intake_complete` (underscores only)

Low classifier confidence (&lt; 0.5) keeps `analyzing` + `needs_human_review`.
