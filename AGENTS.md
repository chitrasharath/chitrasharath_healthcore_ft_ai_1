# AGENTS.md

Repository-wide operating policy for coding agents.

## 1) Mandatory Session Bootstrap

At the start of each session, the agent must read these files in order:

1. memory-bank/projectbrief.md
2. memory-bank/techContext.md
3. memory-bank/progress.md
4. memory-bank/conventions.md
5. memory-bank/decisions.md

Reference policy:
- Use memory-bank/references only when required information is not available in the files above.
- For milestone work, treat **SPECS** and **IMPLEMENTATION_PLAN** files in references as the authoritative requirements source.
- Do **not** use `*_screenshot.md` or `screenshot_content.md` files for build decisions — that content is captured in the corresponding SPECS files.

## 2) Mandatory Pre-Build Context (`.agents/`)

Before starting implementation or build work for a milestone, the agent must load applicable rules and skills from `.agents/`:

1. Read `.agents/rules/frontend/README.md` and `.agents/rules/utilities/README.md` to identify which rule files apply to the touched paths.
2. Read every applicable rule under `.agents/rules/` for the scope being modified (for example, Next.js UI work under `uis/` or `apps/` → `.agents/rules/frontend/*`).
3. Read applicable skills under `.agents/skills/` when the task matches a skill description (see each folder's README). Follow skill steps when a skill applies.
4. Re-read the milestone **SPECS** and **IMPLEMENTATION_PLAN** in `memory-bank/references/` for the work in progress.

Apply `.agents` rules and skills throughout the build alongside memory-bank root files (`conventions.md`, `decisions.md`, `techContext.md`).

## 3) Mandatory Pre-Commit Workflow

Before any commit, the agent must complete these steps in order:

1. Re-sync context:
- Re-read memory-bank/progress.md and memory-bank/decisions.md for any updates relevant to the current changes.

2. Run targeted verification:
- Execute relevant verification for the touched scope (for example: tests, type-check, lint, or build).
- If no relevant verification target exists, document the reason explicitly.

3. Update memory-bank records when applicable:
- Update memory-bank/progress.md when milestone status, scope, or future work has changed.
- Update memory-bank/decisions.md when architectural or feature decisions were made or revised.

4. Produce a concise change and risk summary:
- List what changed.
- List what was validated.
- List residual risks or known gaps.

5. Request explicit developer acknowledgement:
- Do not execute commit commands until the developer confirms.

## 4) Modification Boundaries

No protected paths are enforced by this policy.
- All repository paths may be modified when task-relevant and explicitly requested.

## 5) Maintenance Rule

When process rules change, update both:
- AGENTS.md
- memory-bank/conventions.md

This prevents policy drift between agent workflow and coding standards.
