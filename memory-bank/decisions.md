# Architectural and Feature Decisions

This document records major decisions across project milestones.

## Decision Log

## Milestone 1

- Decision: Build public website as a static implementation using HTML, JavaScript, and Tailwind CSS.
- Why: Fast delivery for digital credibility and structured patient enquiry intake.

- Decision: Use two-page flow for landing and enquiry form with shared navigation.
- Why: Clear separation of presentation content and form workflow.

- Decision: Include client-side validation and Schema.org markup.
- Why: Improve form quality, accessibility, and search visibility.

## Milestone 2

- Decision: Implement core operational logic as typed TypeScript utility modules.
- Why: Reliability, testability, and reuse across future applications.

- Decision: Separate utility responsibilities by module type.
- Why: Improve maintainability and make business logic easier to verify.

- Decision: Prioritize deterministic, validated calculations for reporting.
- Why: Outputs support weekly operational decisions and must be trusted.

## Milestone 3

- Decision: Build recruiting app with Next.js 16, TypeScript, Tailwind CSS, and App Router.
- Why: Scalable routing, consistent component model, and strong typing.

- Decision: Use custom components and URL-driven filtering/search behavior.
- Why: Control UX behavior and align with technical constraints.

- Decision: Integrate with Talent Tracker API using async/await.
- Why: Keep data flows explicit and resilient across loading and error states.

## Milestone 4 Public Portal Migration

- Decision: Build the migrated public portal at `uis/website` (Next.js 16) while retaining `apps/healthcore_web_portal/` unchanged.
- Why: Enable side-by-side regression comparison and safe cutover per migrate-portal-page-to-next skill.

- Decision: Use route `/enquiry-form` for the patient enquiry page (`app/enquiry-form/page.tsx`).
- Why: Clearer public URL than `/application`; maps from legacy `application.html`.

- Decision: Port enquiry validation into `uis/website` (`lib/enquiry-validation.ts`) without `apps/src` imports in the first delivery.
- Why: M2 utility wiring deferred to a later phase; parity with legacy `validation.js` was the priority.

- Decision: Enforce component constraints (const functional components, ≤80 lines per file) in `uis/website`.
- Why: Align with milestone 3 and agent rules.

- Decision (deferred): Import milestone 2 business logic functions into `uis/website` enquiry workflow.
- Why: Scheduled follow-up per frontend-consume-shared-utilities skill.

## Milestone 2 Backoffice Internal App

- Decision: Build internal manual test UI at `uis/backoffice` (Next.js 16) while retaining `apps/src/main.ts`, `apps/src/index.html`, and `apps/src/tests/` unchanged.
- Why: Modern internal UX without disrupting CLI, automated tests, or legacy browser workflow.

- Decision: Copy-only strategy for sample data and operations registry into `uis/backoffice/lib/` rather than extracting shared modules from `main.ts`.
- Why: User chose minimal change to `apps/src`; registry duplication documented with cross-reference comments.

### Operations registry implementation (`uis/backoffice/lib/operations-registry.ts`)

The registry is a **transcription** of the manual-test wiring in `apps/src/main.ts`, not a reimplementation of business logic.

**What was copied from `main.ts` (into backoffice `lib/`):**

| Block | Destination | Role |
|-------|-------------|------|
| Sample fixtures (`sampleLocations`, `sampleClaims`, etc.) | `lib/sample-data.ts` | Demo data passed into utility calls |
| UI types (`OperationDefinition`, `ParameterDefinition`, etc.) | `lib/operation-types.ts` | Shape of dropdown params and `run()` handlers |
| Param helpers + `buildOperations()` (22 operations) | `lib/operations-registry.ts` | Maps UI labels/defaults to utility invocations |

**What was not copied:** DOM code from `main.ts` (rendering, event listeners, history UI). That behavior lives in React (`hooks/use-manual-test-runner.ts` + `components/manual-test/*`).

**How each operation runs:**

1. `buildOperations()` returns an array of `OperationDefinition` objects — one per M2 function.
2. Each entry defines `id`, `label`, `description`, `params` (with defaults), and a `run(params)` handler.
3. Every `run()` handler **imports and calls** the real utility from `apps/src/utils/*` via `@healthcore/src/*` (e.g. `filterClaims`, `validateClaim`). KPI math and validation rules are not duplicated in backoffice.
4. Sample arrays are imported from `@/lib/sample-data.ts` (copied fixtures), matching the legacy manual test page.

**Public API consumed by the UI:**

- `getOperations()` — cached list of all 22 operations (used to populate the function dropdown).
- `defaultParamValues(operation)` — default param map for “Run all with current defaults”.
- `buildOperations()` — rebuilds the registry (same as `getOperations()` on first call).

**CLI / legacy parity:**

- Command-line manual test remains `npx -y tsx apps/src/main.ts` (uses the registry embedded in `main.ts`).
- Legacy browser page remains `apps/src/index.html` + compiled `dist/main.js`.
- Backoffice is a third consumer of the same operation set; all three can drift if `buildOperations()` changes in only one place.

**Sync expectation:** `operations-registry.ts` opens with a comment pointing to `apps/src/main.ts`. Future edits to operation labels, defaults, or wiring should be applied in both files until a shared extract is done.

- Decision: Import M2 business logic via `@healthcore/src/*` path alias; use webpack build with `extensionAlias` for `.js` specifiers in `apps/src`.
- Why: Turbopack cannot resolve `apps/src` internal `.js` imports without webpack; production verify uses `next build --webpack`.
