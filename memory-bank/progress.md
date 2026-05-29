# Project Progress

## Current Status Summary

The project is organized into milestone-based delivery.
Milestone 1, milestone 2, and milestone 3 establish the current implementation baseline.
Milestone 4 public portal migration is **delivered** at `uis/website` (`/` landing, `/enquiry-form` enquiry). Legacy `apps/healthcore_web_portal/` remains unchanged. Milestone 2 internal manual test UI is **delivered** at `uis/backoffice` (Next.js 16, imports from `apps/src` utils/types). Legacy `apps/src/index.html` + CLI + tests remain unchanged.

## Major Milestones

### Milestone 1: Public Website and Structured Enquiry Intake

- Goal: establish a credible bilingual public presence and reduce unstructured intake.
- Delivered focus: landing page content, service and location presentation, and patient enquiry workflow.
- Technical approach: static HTML, JavaScript, and Tailwind CSS.
- Business outcome target: improve trust, accessibility, and front-desk intake quality.

### Milestone 2: Operational Programming Foundation

- Goal: deliver reliable operational business logic for key healthcare workflows.
- Delivered focus: typed data modeling, filtering/search utilities, denial and no-show calculations, CME compliance logic, and validations.
- Technical approach: modular TypeScript utilities executed and verified in Node.js context.
- Business outcome target: trusted weekly KPI generation for billing, clinical, and compliance teams.

### Milestone 3: Talent Pipeline Tracker

- Goal: deliver a mobile-first internal recruiting application.
- Delivered focus: candidate list/detail/edit/new flows, filtering/search/pagination, notes workflows, and API integration.
- Technical approach: Next.js 16 with App Router, TypeScript, and Tailwind CSS.
- Business outcome target: faster and clearer candidate lifecycle management.

### Milestone 4: Public Portal Migration (In Progress)

- Goal: migrate milestone 1 public web portal to the same stack as milestone 3 without retiring the legacy static app yet.
- **Delivered (initial):**
	- `uis/website` — Next.js 16, App Router, TypeScript, Tailwind v4 (PostCSS build, no CDN).
	- Routes: `/` (from `index.html`), `/enquiry-form` (from `application.html`).
	- Shared layout: header, footer, EN/ES via `?lang=` and `localStorage` (`healthcore_lang`).
	- Form validation ported to `lib/enquiry-validation.ts` + `hooks/use-enquiry-form.ts` (no `apps/src` imports yet).
	- Schema.org JSON-LD on landing and enquiry routes.
	- `npm run verify` (lint + build) passes in `uis/website`.
- **Retained:** `apps/healthcore_web_portal/` (static HTML/JS) — not modified.
- **Deferred:** Import `apps/src` utilities into the enquiry form (future phase).
- **Next:** Stakeholder sign-off per UAT checklists in `memory-bank/references/milestone4_ai_plan/m4_portal_migration_plan.md`; optional legacy retirement after cutover.

### Milestone 2 Backoffice Manual Test UI (Delivered)

- Goal: replace the browser workflow of the M2 manual test page with a Next.js internal app.
- **Delivered:**
  - `uis/backoffice` — Next.js 16, App Router, TypeScript, Tailwind v4.
  - Single route `/` — function selector, dynamic params, run selected/all, results + history (parity with `apps/src/index.html`).
  - Imports business logic from `apps/src/utils/*` and types from `apps/src/types/models` via `@healthcore/src/*` path alias.
  - Registry and sample fixtures copied into `uis/backoffice/lib/` (copy-only; `apps/src/main.ts` unchanged).
  - `npm run verify` (lint + webpack build) passes.
- **Retained:** `apps/src/main.ts` (CLI), `apps/src/index.html` (legacy browser), `apps/src/tests/run-tests.ts`.

## Future Feature Additions

- Expand reusable shared logic and typing between migrated milestone 1 and existing milestone 3 apps.
- Extend milestone 2 function usage in UI workflows where validated logic improves data quality.
- Improve cross-app bilingual consistency and content governance.
- Integrate `apps/src` validators into `/enquiry-form` when milestone 2 wiring is scheduled.
- Legacy portal retirement and redirect strategy after stakeholder cutover approval.
- Optional: extract shared operations registry from `apps/src/main.ts` and `uis/backoffice/lib/operations-registry.ts` to reduce drift.
