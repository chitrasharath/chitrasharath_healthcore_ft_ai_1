---
name: frontend-consume-shared-utilities
title: Frontend Consume Shared Utilities
description: Guides how a user-specified frontend imports and uses apps/src TypeScript utilities. Use when wiring a named frontend app to validators, transformations, or KPI helpers without duplicating business logic.
scope: Integration between a user-provided frontend path and apps/src (shared utilities)
globs:
  - apps/**
  - uis/**
  - apps/src/**
alwaysApply: false
content: |
  ## When to use

  - Connect a form or UI workflow in a frontend to `apps/src` validators or calculators.
  - User asks to reuse Milestone 2 logic in a specific frontend.
  - Wire shared business rules on submit or display in a UI the user has named.

  ## User-provided target frontend (required)

  Before starting, get the **frontend root path** from the user (e.g. `uis/website`, `apps/talent-pipeline-tracker`, `apps/healthcore_web_portal`).

  - Treat that path as the only frontend you modify for this task unless the user adds more.
  - Do not assume a default frontend if none was given—ask for the path.
  - Inspect that folder to determine stack: Next.js (TypeScript, `app/` or `pages/`), static HTML/JS, or other.

  ## Prerequisites

  - Read `.agents/rules/frontend/utility-reuse.md` and `.agents/rules/utilities/export-for-frontend.md`.
  - Confirm the user-provided frontend path exists in the repo.
  - Identify entry files for forms or workflows (e.g. `validation.js`, form components, hooks) under that path only.

  ## Step 1 — Choose the right utility

  - Modules live under `apps/src/utils/`: `collections`, `search`, `transformations`, `validations`.
  - Entity types are in `apps/src/types/models.ts`.
  - Match workflow to entity and function (see `memory-bank/references/milestone2_ai_plan/milestone2_CONTEXT.md`):
    - Claim validation → `validateClaim` in `validations.ts`
    - Denial KPIs → `transformations.ts` (e.g. `calculateDenialRate`)
    - Appointments / no-show → `transformations.ts` + `Appointment` type
    - CME → `generateCMEReport`, `getCliniciansAtRisk`, etc.
  - If UI fields do not map to a defined entity, keep those checks in the target frontend only. Do not force-fit utilities.

  ## Step 2 — Map UI fields to typed input

  - Build a plain object matching the relevant interface in `models.ts`.
  - Include required fields and correct formats (IDs, ISO dates, enums).
  - Pass extra arguments validators need (e.g. `knownLocationIds` for `validateClaim`).
  - Document any field renamed, omitted, or derived.

  ## Step 3 — Integrate by frontend stack (user path)

  **If the user-provided frontend is Next.js / TypeScript:**

  - Import named exports from `apps/src/utils/*` (add a tsconfig path alias in that frontend if needed).
  - Call utilities from event handlers, hooks, or server actions under the user path—not inside oversized presentational components.
  - Map `{ valid: false, errors: string[] }` to per-field messages near inputs.
  - For KPI display, call transformation functions; do not reimplement formulas in UI code.
  - Follow `.agents/rules/frontend/client-side-validation.md` for API submit errors when a backend exists.

  **If the user-provided frontend is static HTML / plain JavaScript:**

  - **Option A (business rules from utilities):** Compile `apps/src` with `tsc` per `apps/src/DEVELOPMENT.md`, import compiled `.js` as an ES module from a bridge file under the user path.
  - **Option B (UI-only):** Keep presentational validation in existing client scripts; use compiled utilities only where a function explicitly applies.
  - Document which option you used in the change summary.
  - Never copy threshold constants from milestone2 into client-only scripts.

  **If the stack is unclear:** Ask the user to confirm (Next.js vs static vs other) before choosing an integration path.

  ## Step 4 — Error display

  - Show one clear message per entry in `errors[]`.
  - Keep UI rules (email format, required fields) in the target frontend; business rules stay in `apps/src`.
  - Use `aria-describedby` or adjacent text for accessible field errors.

  ## Step 5 — Verify integration

  - If utilities changed: `npx -y -p typescript tsc --project apps/src/tsconfig.json --noEmit`
  - Run lint/build for the user-provided frontend if applicable.
  - Test invalid payload → expected error messages in that frontend.
  - Test valid payload → submit/success path unchanged.
  - Grep files under the user path for duplicated business formulas or threshold literals.

  ## References

  - User-provided frontend path (from task)
  - `apps/src/utils/`, `apps/src/types/models.ts`, `apps/src/DEVELOPMENT.md`
  - `.agents/rules/frontend/utility-reuse.md`
  - `.agents/rules/utilities/export-for-frontend.md`
  - `memory-bank/references/milestone2_ai_plan/milestone2_CONTEXT.md`
examples:
  - "Good: User specifies uis/website; agent imports validateClaim in a hook under that folder only."
  - "Good: User specifies a static app path; agent compiles apps/src and loads validators via a bridge module in that app."
  - "Avoid: Wiring utilities into a frontend path the user did not name."
  - "Avoid: Reimplementing calculateDenialRate logic inline in the target frontend."
---
