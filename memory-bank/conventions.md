# Coding Conventions

This document defines coding standards and implementation patterns for the HealthCore milestone codebases.

## Core Standards

- Use TypeScript for application and business-logic code when available.
- Prefer const declarations and immutable data patterns.
- Keep functions focused, deterministic, and easy to test.
- Use descriptive names for files, variables, and exported functions.
- Write concise comments only when logic is not obvious.

## UI and Component Patterns

- Use mobile-first responsive design.
- Use Tailwind CSS for styling.
- Build custom components only; do not rely on third-party UI component libraries.
- Keep React components as const functional components.
- Keep component files small and composable.
- For milestone 3 and milestone 4 migrated milestone 1 app, every component must be 80 lines or less and functional.

## Milestone-Specific Patterns

### Milestone 1

- Keep public site structure clear and semantic.
- Maintain bilingual content parity across English and Spanish content.
- Keep form validation explicit and user-friendly.

### Milestone 2

- Model all business entities with strict interfaces.
- Keep transformation and calculation functions pure.
- Validate data before calculation paths.
- Separate concerns by utility modules: collections, search, transformations, validations.

### Milestone 3

- Use Next.js App Router route-level organization.
- Keep route state URL-driven where relevant for filtering and search.
- Handle API calls with async/await and explicit loading, success, and error states.

### Milestone 4 Planned Migration

- Migrate milestone 1 app to the same stack and architecture approach as milestone 3.
- Import milestone 2 business logic functions into the migrated milestone 1 app instead of duplicating logic.
- Preserve accessibility, responsiveness, and maintainability during migration.

## Quality and Verification

- Validate business logic with lightweight tests or deterministic execution checks.
- Preserve backwards behavior unless a change is explicitly planned.
- Prefer small, incremental changes over broad rewrites.
