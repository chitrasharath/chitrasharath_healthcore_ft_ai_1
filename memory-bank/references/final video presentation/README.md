# Final Project Video — Deliverables

Everything for the 5–7.5 minute AI Engineering final project video.

| File | What it's for |
|---|---|
| [VIDEO_SCRIPT_GUIDE.md](VIDEO_SCRIPT_GUIDE.md) | Section-by-section script guidance, timing map, hook options, three answer frameworks for Section 5 |
| [SHOT_LIST.md](SHOT_LIST.md) | 12 screenshots / recordings to capture, with exact URLs, setup commands and what to crop |
| `healthcore_final_project.pptx` | 14-slide deck. Condensed script lives in the **speaker notes** of every slide |
| `slide_previews/` | PNG of each slide, for reviewing without opening PowerPoint |

## Before you record — checklist

1. **Fill in the bracketed placeholders.** They are your personal story and cannot be faked:
   - Slide 2 → your background (1–2 lines)
   - Slide 12 → why AI engineering, what almost held you back, the moment it clicked
   - Slide 13 → your starting point, what made the difference, your one piece of advice
2. **Replace the 6 dashed SHOT boxes** with real screenshots (slides 4, 5, 8 and the demo references on 6). See SHOT_LIST.md.
3. **Read the speaker notes** — open PowerPoint in Presenter View, or View → Notes Page.
4. **Rehearse against the timing map** in the guide. Section 3 must include ~45 seconds of live app footage.
5. Optionally add your LinkedIn/GitHub to the final slide.

## Deck structure

| Slide | Section | Content |
|---|---|---|
| 1 | Intro | Title (dark) |
| 2 | 1 · Introduction | Background, business, what was automated, one-line overview |
| 3 | 2 · Problem | Two worlds: policy docs vs live operations |
| 4 | 2 · Opportunity | Time / consistency / compliance + SHOT 1 |
| 5 | 3 · Solution | What it is, what it can do, the endpoint + SHOT 2 |
| 6 | 3 · Demo | Four questions, four paths (SHOTS 2–5) |
| 7 | 3 · How it works | Architecture: RAG indexing + LangGraph query flow |
| 8 | 3 · Safety | Guardrails, PHI, untrusted wrapping, consent memory + SHOT 6 |
| 9 | 3 · Stack | AI / Platform / Quality columns |
| 10 | 4 · Challenge | Hardest problem: honest agent under failure |
| 11 | 4 · Decisions | Read-only trade-off + what you're proud of |
| 12 | 5 · Journey | Questions a & b |
| 13 | 5 · Journey | Question c — advice |
| 14 | Close | Thank you (dark) |

## Regenerating the deck

The generator script and rendered icons are in the session scratchpad. If you want to
change wording, it is faster to edit the `.pptx` directly in PowerPoint — the deck has
no template dependencies and every element is a plain shape or text box.
