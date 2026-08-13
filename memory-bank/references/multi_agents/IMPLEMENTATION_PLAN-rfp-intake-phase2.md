# RFP Intake Phase 2 — Implementation Plan

**Requirements:** [`SPEC-rfp-intake-phase2.md`](SPEC-rfp-intake-phase2.md) + [`CONTEXT-multi_agent.md`](CONTEXT-multi_agent.md)  
**Prior:** Phase 1 on committed `feature/rfp-intake`  
**Branch:** `feature/rfp-response-generation` ← `feature/rfp-intake`  
**PR target:** `feature/rfp-intake`

## Locked decisions

| # | Decision |
|---|----------|
| 1 | `start-drafting`: soft-idempotent `202` if already `drafting`/`under_evaluation`; `409` otherwise (not `intake_complete`) |
| 2 | Ticket → `under_evaluation` as soon as any section enters evaluation |
| 3 | `redraft`: only `needs_human_review` sections; reset that section’s loop (`iteration=0`, clear draft); keep EvaluationResult history |
| 4 | PHI Compliance flag = `contains_phi` + UI banner naming Claire Whitfield (no assignment table) |
| 5–8 | Max iterations **3**; FK grade **≤12**; relevance **strict**; dedicated **`EvaluationResult` table** |
| 9 | Concurrent independent section loops |
| 10 | In: deterministic BAA/DPA/currency, feedback guard, idempotent redraft, README, golden draft fixtures. Defer: few-shot, structured outputs, loop telemetry |
| 11 | Models via env/`settings.generation_model` (+ optional `rfp_generator_model` / `rfp_evaluator_model` overrides) |
| 12 | Branch from committed Phase 1 |

## Build order

1. Models: `EvaluationResult` table; `DepartmentSection` status/iteration/latest_evaluation_id; Ticket rollup derived in API  
2. `rules.py` + generator + 3 evaluators + aggregate  
3. `drafting_state` / `drafting_graph` / `drafting_runner`  
4. Repository + service endpoints `start-drafting` / `redraft`  
5. Backoffice UI panels + Start drafting button  
6. Tests (§9) + README + memory-bank

## Out of scope

Part 3 approvals/arbitration/final doc; do not touch `approval_*` or CX agent graph.
