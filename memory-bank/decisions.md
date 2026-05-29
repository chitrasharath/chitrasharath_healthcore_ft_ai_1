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
