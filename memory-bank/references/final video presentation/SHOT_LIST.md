# Screenshot / Screen-Recording Shot List

Capture these before recording. Zoom browser to **125–150%**, hide bookmarks bar,
use a window ~1600×1000. Shots marked 🎬 are better as short screen recordings
(5–15 s) than stills. Shot numbers are referenced in the PPTX placeholders and
VIDEO_SCRIPT_GUIDE.md.

## Setup (do once, before capturing)

```bash
cd chitrasharath_healthcore_ft_ai_1
cp .example.env .env          # if not already done; set SECRET_KEY, DATABASE_URL, LLM_API_KEY
docker compose up --build     # or the manual workflow from README
docker compose exec api uv run seed                                   # suppliers + inventory + reporting demo
docker compose exec api uv run python /app/scripts/seed_incidents.py  # incidents
uv run python scripts/seed_knowledge_base.py                          # RAG collection (needs LLM_API_KEY)
```

Log in at http://localhost:3001 with a seeded/registered user before capturing.

---

| # | Shot | URL / state | What to show / crop | Used in |
|---|------|-------------|---------------------|---------|
| 1 | Backoffice hub | http://localhost:3001 logged in | Full hub with tool tiles (Knowledge, Reporting, Inventory, Incident Manager visible) | Slide 4 (context) |
| 2 🎬 | RAG answer with sources | `/knowledge` → ask **"Is Medicaid accepted at Georgia clinics?"** | Question, grounded answer, sources panel showing `insurance-coverage`, thumbs buttons | Slide 5 + demo |
| 3 🎬 | Live incident tool | `/knowledge` → ask **"What is the status of incident 1?"** | Answer showing live incident status; note sources_used = incident_tool if surfaced in UI | Slide 5/6 + demo |
| 4 🎬 | Fan-out (RAG + tool) | `/knowledge` → ask **"What's our mask policy and do we have any in stock?"** | One answer combining policy text + live stock number | Slide 6 + demo (the money shot) |
| 5 | Honest fallback | `/knowledge` → ask **"What is the capital of Mars?"** | The verbatim "I don't have information about that." reply | Slide 6 + demo |
| 6 | Guardrail refusal | `/knowledge` → try a jailbreak (e.g. "Ignore your instructions and…") or a PHI-laden request | The refusal/redirect message | Slide 8 |
| 7 | API surface | http://localhost:8000/docs | Swagger scrolled to `/api/v1/agent/query` + `/api/v1/knowledge/*` | Slide 7 (optional) |
| 8 | LangSmith trace | smith.langchain.com project `healthcore-agent` (needs `LANGCHAIN_TRACING_V2=true` + key) | One trace expanded: classify → parallel retrieve/tool → compose | Slide 7 (optional but impressive) |
| 9 | Reporting dashboard | http://localhost:3001/reporting (after `seed_reporting`) | Summary tab with KPI charts; or Pipeline health tab | Slide 4 (supporting cast) |
| 10 | Stack running | Terminal: `docker compose ps` | Services list: api, ui, redis, worker, flower | Slide 9 (optional) |
| 11 | Agent graph code | Editor open at `services/api/app/domains/agent/graph.py` | The graph wiring: classify → fan-out → gather → compose/fallback. Increase editor font first | Slide 9/10 |
| 12 | Evals passing | Terminal: `uv run pytest tests/pipelines/test_agent_evals.py tests/pipelines/test_guardrails_injection.py -q` | Green pass summary | Slide 11 |

## Capture tips

- **macOS:** `Cmd+Shift+4` + space bar → click window = clean window capture with shadow. For recordings, `Cmd+Shift+5` → "Record Selected Portion".
- Capture at 2× (Retina default) — the deck placeholders assume crisp images.
- For Shot 4, wait for the full answer to render before capturing; that composed answer is your single best visual proof of the agent working.
- If the memory feature is enabled, an optional bonus recording: the consent flow from `services/api/app/domains/agent/memory/README.md` Cycle A (propose → approve → recall).
