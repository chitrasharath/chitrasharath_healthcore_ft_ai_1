# Milestone 2 Execution Checklist

## Objective
Implement and validate TypeScript business-logic utilities for HealthCore Milestone 2, including models, collections/search/transformations/validations, CLI verification, lightweight tests, and browser-based manual testing.

## 1. Requirements Intake
- Reviewed milestone requirements from `milestone2_ai_plan/milestone2_CONTEXT.md`.
- Used directory blueprint from `milestone2_ai_plan/directory_structure.png`.
- Confirmed no edits to existing `apps/healthcore_web_portal` implementation.

## 2. Core Implementation
- Implemented business entity models and types in `apps/src/types/models.ts`.
- Implemented collections utilities in `apps/src/utils/collections.ts`.
- Implemented search utilities in `apps/src/utils/search.ts`.
- Implemented transformations and KPI calculators in `apps/src/utils/transformations.ts`.
- Implemented validation rules and threshold checks in `apps/src/utils/validations.ts`.

## 3. Sample-Data Runner
- Added sample data from the context and executable flows in `apps/src/main.ts`.
- Added CLI output formatting with section headings per function execution.
- Added browser-mode UI bootstrap and parameter-driven function execution.

## 4. Manual Testing UI
- Built manual test interface in `apps/src/index.html`.
- Added function selector, dynamic parameter controls, run-selected/run-all actions, latest output panel, and execution history.
- Ensured browser module compatibility for compiled JS imports.

## 5. Lightweight Automated Tests
- Added test harness in `apps/src/tests/run-tests.ts`.
- Covered positive/negative validation paths, threshold boundaries, and edge cases.

## 6. Build and Command Documentation
- Consolidated active development commands in `apps/src/DEVELOPMENT.md`.
- Updated commands to use `apps/src/tsconfig.json` and HTTP serving path `/src/`.

## 7. File Structure Cleanup
- Moved canonical files into `apps/src`:
  - `index.html`
  - `tsconfig.json`
  - `DEVELOPMENT.md`
- Removed obsolete root duplicates:
  - `apps/index.html`
  - `apps/tsconfig.json`
  - `apps/DEVELOPMENT.md`

## 8. Validation Runs Performed
- Type-check:
  - `npx -y -p typescript tsc --project apps/src/tsconfig.json --noEmit`
- Compile:
  - `npx -y -p typescript tsc --project apps/src/tsconfig.json`
- Unit tests:
  - `npx -y tsx apps/src/tests/run-tests.ts`
- CLI function execution:
  - `npx -y tsx apps/src/main.ts`

## 9. Runtime Notes
- If browser page is opened through `file://`, module loading may fail in some environments.
- Recommended local serve command:
  - `cd /workspaces/chitrasharath_healthcore_ft_ai_1/apps`
  - `npx -y http-server . -p 3001 -a 0.0.0.0`
- Open:
  - `http://localhost:3001/src/`
- If `EADDRINUSE` appears, the selected port is already occupied; use another port or stop the existing process.

## 10. Current Canonical Paths
- `apps/src/types/models.ts`
- `apps/src/utils/collections.ts`
- `apps/src/utils/search.ts`
- `apps/src/utils/transformations.ts`
- `apps/src/utils/validations.ts`
- `apps/src/tests/run-tests.ts`
- `apps/src/main.ts`
- `apps/src/index.html`
- `apps/src/tsconfig.json`
- `apps/src/DEVELOPMENT.md`
