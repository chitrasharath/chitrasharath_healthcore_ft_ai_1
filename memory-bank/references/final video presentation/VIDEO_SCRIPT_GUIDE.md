# Final Project Video — Script & Preparation Guide

**Project:** HealthCore Knowledge Assistant — RAG + LangGraph support agent for clinic operations
**Repo:** `chitrasharath_healthcore_ft_ai_1`
**Target length:** 5–7.5 minutes (~1.5 min per section ≈ 200–220 spoken words each)

The centerpiece is the **/knowledge assistant**: a RAG knowledge base plus a LangGraph agent
that answers coordinator questions from policy documents *and* live incident/inventory
systems, wrapped in a guardrail harness with PHI controls. The rest of the platform
(website, backend, telemetry, reporting, forecasting) is the supporting cast that makes
the story credible.

---

## Timing map

| Section | Time | Slides | Screenshots (see SHOT_LIST.md) |
|---|---|---|---|
| 1. Introduction | 0:00–1:30 | 1–2 | — |
| 2. Problem & Opportunity | 1:30–3:00 | 3–4 | Shot 1 (hub) |
| 3. The AI Solution | 3:00–4:30 | 5–8 | Shots 2–6 (demo), 8 (trace) |
| 4. Engineering Decisions | 4:30–6:00 | 9–11 | Shots 11–12 (code, evals) |
| 5. Three Questions | 6:00–7:30 | 12–13 | — |
| Close | last 10 sec | 14 | — |

**Golden rule:** Section 3 is where you should *show the app live or via screen recording*,
not just slides. Talk over the real UI for at least 45 of its 90 seconds.

---

## Section 1 — Introduction (0:00–1:30)

### What the graders want
A hook in the first 10 seconds, then the four facts: name, background, project name, what was automated — in one breath, no throat-clearing.

### Hook options (pick ONE)

1. **The question hook (recommended):** Open cold on the app, type a question, let the answer appear, *then* cut to you:
   > "'Is Medicaid accepted at our Georgia clinics?' A patient coordinator asks a question like that dozens of times a day — and until recently, answering it meant digging through policy PDFs or putting a patient on hold. I built an AI assistant that answers it in seconds, with sources."

2. **The stat hook:**
   > "HealthCore's front desk was spending up to 20 minutes per call just gathering basic information. Multiply that across 12 clinics in two countries, and you have a knowledge problem, not a staffing problem."

3. **The stakes hook:**
   > "In healthcare, a chatbot that makes things up isn't a quirk — it's a liability. So the hardest part of my project wasn't making the AI answer. It was making it honest."

### Fill-in template (~20 seconds after the hook)

> "Hi, I'm **[your name — Chitra Sharath Chandra?]**. My background is in **[your prior field/role — 1 short phrase]**, and over the past months in the 4Geeks AI Engineering program I built **HealthCore Digital** — a full internal platform for a fictional 12-clinic outpatient healthcare network. The piece I'm presenting today is its **AI Knowledge Assistant**: a retrieval-augmented, agentic support tool that automates how patient coordinators get answers about company policy and live operations."

**Do:** say the project name once, clearly. **Don't:** list every milestone here — that's the death of the hook.

---

## Section 2 — Problem & Opportunity (1:30–3:00)

### The three questions, answered from your project's context

**What challenge/inefficiency?**
- HealthCore's operational knowledge lived in scattered policy documents (appointment policy, insurance coverage, referral process, new-patient onboarding).
- Live operational facts — "is incident 12 resolved?", "do we have surgical masks in stock?" — lived in *separate* internal tools (incident manager, inventory).
- Coordinators either interrupted colleagues, dug through docs, or gave inconsistent answers. The front-desk intake process alone was ~20 min/call of unstructured information gathering.

**Who experiences it?**
- Patient coordinators and front-desk staff at 12 clinics (9 US, 3 UK) — ~200 employees.
- Indirectly: patients on hold, and Patient Experience leadership (stakeholder: Priya Nair) who see churn to competitors.

**Why is solving it valuable?** Give 3 concrete value claims:
1. **Time:** seconds instead of minutes per policy question; less phone tag between clinics.
2. **Consistency & trust:** every answer is grounded in the official policy documents and *cites its sources* — no folklore answers that vary by clinic.
3. **Compliance:** healthcare means PHI. A generic chatbot is a HIPAA/UK-GDPR incident waiting to happen; a purpose-built one with guardrails is an asset instead of a risk.

### Script skeleton

> "HealthCore runs 12 clinics across the US and UK. Its policies — insurance, referrals, appointments, new patients — lived in documents; its live operational state — incidents, inventory — lived in separate internal tools. A coordinator with a patient on the phone had to search both, or guess. That's slow, it's inconsistent across clinics, and in healthcare, inconsistent answers are a compliance problem, not just an annoyance. The opportunity: one assistant that answers from official policy *with citations*, checks live systems when the question needs it, and refuses to handle patient data it shouldn't touch."

---

## Section 3 — Your AI Solution (3:00–4:30)

This is the demo section. Structure: **what it does (20s) → show it (45s) → how it works (25s)**.

### What you built (one sentence)
> "A JWT-protected knowledge assistant in the backoffice: coordinators ask a question in plain English; a LangGraph agent classifies it, retrieves from a Qdrant vector knowledge base and/or calls live incident and inventory tools, and composes a grounded, cited answer — or honestly says it doesn't know."

### Demo choreography (screen recording, Shots 2–6)
Run these four queries live — they showcase every path through the agent graph:

| Query | What it demonstrates | Say this |
|---|---|---|
| "Is Medicaid accepted at Georgia clinics?" | RAG path — grounded answer + `insurance-coverage` source | "Answer comes from the official policy doc, with the source cited." |
| "What is the status of incident 1?" | Live incident tool (real API call with my JWT forwarded) | "This isn't in any document — the agent called the live incident API." |
| "What's our mask policy and do we have any in stock?" | **Fan-out**: RAG + inventory tool in parallel, composed into one answer | "One question, two sources — policy retrieval and a live inventory lookup, run in parallel and composed." |
| "What is the capital of Mars?" | Honest fallback | "No hallucination — if retrieval comes back empty, it says so." |

Optionally add a guardrail demo (Shot 6): a jailbreak or PHI-laden prompt getting refused.

### How it works (the technology inventory — pick your depth by pace)

- **RAG pipeline:** four English policy docs → **semantic chunking** → **embeddings** via the 4Geeks LiteLLM proxy → **local Qdrant** vector store → top-k dense retrieval with a minimum-score threshold → grounded generation.
- **Agent:** a **compiled LangGraph** graph — `receive → classify → fan-out {retrieve, incident_tool, inventory_tool} → gather → compose | honest_fallback`. Typed `httpx` tool clients with timeouts and retry-once; the caller's JWT is threaded through the graph into tool calls.
- **Safety harness:** input/output guardrails — jailbreak refusal, PHI controls (HIPAA/UK GDPR framing), and wrapping of RAG chunks and MCP tool JSON as *untrusted content* so retrieved text can't inject instructions.
- **MCP:** a company-tools **MCP server** (incidents + inventory) behind **Keycloak OAuth** — standardized tool access with real auth.
- **Memory:** consent-gated long-term memory (Redis + Qdrant) — the agent *asks permission* before remembering, screens proposals for PHI, and audits every decision.
- **Quality loop:** thumbs feedback to JSONL, an eval suite (`test-queries.json`, agent evals, guardrail injection tests), and **LangSmith** tracing.

**Don't read this list aloud verbatim** — pick 4–5 items and let the architecture slide carry the rest.

### What makes it useful (close the section)
> "It's useful because it's trustworthy: grounded answers with citations, live data when needed, honest 'I don't know' otherwise, and guardrails that make it safe to put in front of healthcare staff."

---

## Section 4 — Engineering Decisions & Challenges (4:30–6:00)

Pick **one** hardest problem, **one** trade-off, **one** pride point. Candidates below are all real in your repo — choose the ones that match your actual experience.

### Hardest technical problem (pick one, tell it as a story: problem → naive approach fails → your solution)

**Option A — Making the agent honest under failure (recommended, easiest to demo):**
> "The hardest problem was failure handling in an agentic system. A live tool call can time out, 500, or return nothing — and an LLM's instinct is to paper over the gap with a plausible guess. I designed the tool clients so they *never raise into the graph*: typed httpx clients with timeouts and a single retry, and any failure becomes an explicit state the compose step must handle with a verbatim fallback — 'I could not confirm the ticket's status.' The agent's honesty isn't a prompt suggestion; it's enforced by the graph's structure."

**Option B — Prompt injection via retrieved content:**
> "The scariest realization was that my own knowledge base is an attack surface: RAG chunks and MCP tool JSON go straight into the prompt, so a malicious document could carry instructions. I built a guardrail harness that wraps all retrieved and tool-returned content as untrusted data — the model is told, structurally, that this text is quoted material, never instructions — plus input guards for jailbreaks and PHI, output guards, and an injection test suite (`test_guardrails_injection.py`) to prove it."

**Option C — Consent-gated memory with PHI screening:**
> "Long-term memory in healthcare is a minefield. My agent proposes a memory, asks the user for consent, screens the proposal for PHI before it's ever shown, stores approved entries in Redis with Qdrant for semantic recall, applies sliding TTLs and pruning, and audits every approve/reject/ignore. 'Patient Johnson cancelled tomorrow' never even reaches the consent step — it's refused outright."

### Trade-off / design decision (pick one)

1. **Read-only agent tools by design:** the MCP server *can* create and update incidents, but the agent deliberately gets lookup-only tools. Trade-off: less capable, but a hallucinated read is an inconvenience while a hallucinated *write* is an incident. In healthcare ops, I chose the blast-radius reduction.
2. **Local on-disk Qdrant instead of a managed vector DB:** zero infra cost, no PHI leaving the machine, perfectly reproducible in Docker — at the cost of horizontal scale I don't need for four policy documents. Right-sized beats impressive.
3. **Reuse over rewrite:** the agent reuses the RAG pipeline's `normalize_query` / `retrieve` / `generate_answer` functions instead of duplicating them, and `POST /knowledge/query` was left untouched when `/agent/query` shipped — one source of truth, non-breaking evolution.

### What you're most proud of (pick one)

- **The discipline, not a feature:** spec-first plans in a memory-bank, evals and injection tests alongside unit tests, seeded demo flows, one-command Docker bring-up. "The agent is the demo; the engineering culture around it is the product."
- **Honest evaluation instincts:** (if you want a second story) in the churn-model work you refused to chase F1 = 0.9, identified it as only achievable via leakage, and reframed the objective to recall/cost — the kind of judgment that separates AI engineering from demo-building.

---

## Section 5 — The Three Questions (6:00–7:30, ~30s each)

These must be *yours*. Below are frameworks with fill-ins — answer honestly; graders can smell a generic answer.

### Q-a: What made you decide to pursue AI Engineering — and what almost held you back?

Framework: **pull** (what drew you) + **fear** (what almost stopped you) + **resolution** (what got you past it).

> "I decided to pursue AI engineering because **[e.g., I kept seeing X problem in my previous work in ___ and realized AI was the lever / I wanted to build, not just use, these tools]**. What almost held me back was **[honest fear: 'I'm not a math person' / career risk of switching from ___ / imposter syndrome about coding / time with family]**. What got me over the line was **[a moment, a person, a realization — e.g., realizing that engineering judgment matters more than research math]**."

*Tip:* the "almost held me back" half is what makes this answer memorable — be specific and a little vulnerable.

### Q-b: Was there a moment, project, or person when things really clicked?

Pick ONE — a real moment from the program. Strong candidates from your own work:

- The first time the **fan-out query** worked — one question hitting RAG *and* the inventory tool in parallel and composing a single answer: "that's when 'agent' stopped being a buzzword for me."
- Watching the agent correctly answer **"I don't have information about that"** — realizing that making AI refuse well is harder, and more valuable, than making it answer.
- A **person**: an instructor or cohort-mate who reframed something for you — name them.
- The **milestone arc** itself: seeing a static HTML form from Milestone 1 evolve into a platform with an agent on top — "the click was realizing I could hold the whole stack in my head."

### Q-c: What would you tell someone on the fence about 4Geeks?

Framework: **acknowledge the fence** + **your evidence** + **one concrete pointer**.

> "If you're on the fence, I'd say: **[your honest pitch]**. I came in **[your starting point]** and left having built **[point at the screen: a bilingual production-style platform with a guarded RAG agent on top]**. The thing that made the difference was **[the structure — milestone-based building on one evolving company / the mentors / building real things instead of toy notebooks]**. If you're going to do it: **[one piece of advice — e.g., 'treat every milestone like production code; the compounding is the point']**."

---

## Recording & delivery tips

1. **Record the demo separately** from your talking-head/slides, then edit together. Live typing + live talking = flubbed takes.
2. **Pre-seed everything** before recording: knowledge base seeded, incidents seeded, inventory stocked, logged in, telemetry warm. Nothing kills a demo like an empty state.
3. **Zoom the browser to 125–150%** and use a clean window (no bookmarks bar, no 47 tabs).
4. **Script ≈ 200 words per 1.5-min section.** Write it out, then rehearse until you can say it *without* reading. Reading is audible.
5. **Timebox with a stopwatch per section.** If Section 3 runs long, cut from Section 3's "how it works" list — never from the demo.
6. Speaker notes in the PPTX contain a condensed script for every slide.
7. End with your name + repo/contact on screen for the final seconds.

## Suggested tools
- **Recording:** Loom, OBS, or QuickTime screen recording + iPhone/webcam for face.
- **Editing:** iMovie / CapCut / Descript (Descript lets you edit by deleting words from the transcript).
