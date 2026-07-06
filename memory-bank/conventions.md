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

### Milestone 4 (Delivered)

- Public portal migrated to `uis/website` (Next.js 16, App Router, TypeScript, Tailwind v4).
- Import milestone 2 business logic into the enquiry form remains deferred.
- Preserve accessibility, responsiveness, and maintainability; legacy `apps/healthcore_web_portal/` retained.

## Monorepo conventions

- **Dual uv lockfiles (intentional):** `services/api/uv.lock` is canonical for the API package and Docker builds; root `uv.lock` enables `uv run pytest` from the repo root. Re-lock **both** after backend dependency changes.
- **Test dependencies:** Keep `services/api` `[project.optional-dependencies] dev` and root `[dependency-groups] dev` aligned.
- **Legacy talent tracker:** `apps/talent-pipeline-tracker/` is frozen; canonical copy is `uis/backoffice/talent-tracker/`.
- **Environment files:**
  - **Docker:** root `.example.env` → `.env`
  - **Manual API:** `services/api/.example.env` → `.env`
  - **Manual backoffice:** `uis/backoffice/landing/.example.env` → `.env.local` (only standalone Next.js app that needs env for normal dev)
  - **`uis/website`** — no env file required (`npm run dev` only)
  - **Aliased backoffice modules** (inventory, incident-manager, talent-tracker, etc.) — no separate env; they compile through landing and inherit its `NEXT_PUBLIC_*` vars
  - Legacy `.example.env` files under deprecated standalone apps (e.g. `uis/incident_analyzer/`) are not used in the current landing-only workflow
- **npm lockfiles:** Six active UI apps each keep `package-lock.json`; run `python3 scripts/check_ui_dep_versions.py` before committing `package.json` changes.
- **Shared package naming:** `packages/shared/package.json` `name` is `@repo/shared-types`; consumers import via `@repo/shared` alias in `tsconfig.json` / `next.config.ts`.

## Quality and Verification

- Validate business logic with lightweight tests or deterministic execution checks.
- Preserve backwards behavior unless a change is explicitly planned.
- Prefer small, incremental changes over broad rewrites.
- **Docker pytest:** Prefer `docker compose --profile test run --rm test` for one-shot CI-like runs; use `docker compose exec api uv run pytest` when the stack is already up.
- **Local API tests:** `uv run pytest` from repo root or `services/api`.

## Agent Workflow (see also AGENTS.md)

Before starting milestone implementation:

1. Bootstrap from memory-bank root files (`projectbrief.md`, `techContext.md`, `progress.md`, `conventions.md`, `decisions.md`).
2. Read the milestone SPECS and IMPLEMENTATION_PLAN under `memory-bank/references/`. Do not use `*_screenshot.md` files — requirements live in SPECS.
3. Load applicable `.agents/rules/` and `.agents/skills/` for the paths being modified (frontend rules for Next.js apps; utility rules for `apps/src` and shared logic).
4. Update `memory-bank/progress.md` and `memory-bank/decisions.md` when milestones complete or decisions change.
