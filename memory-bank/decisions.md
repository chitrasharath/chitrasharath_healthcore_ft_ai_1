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

## Milestone 4 Planned Migration

- Decision: Migrate milestone 1 app to the same tech stack and architectural patterns used in milestone 3.
- Why: Consolidate stack, reduce maintenance overhead, and standardize implementation patterns.

- Decision: Import milestone 2 business logic functions into migrated milestone 1 app.
- Why: Reuse validated logic and avoid duplication in form and data-processing flows.

- Decision: Enforce component constraints in migrated milestone 1 app.
- Why: Keep components functional and maintainable, with each component 80 lines or less.
