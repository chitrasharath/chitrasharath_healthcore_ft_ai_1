# Technical Context

## Tech Stack

### Milestone 1 (Legacy — retained)
- HTML, JavaScript, and Tailwind CSS (via CDN)
- Static pages: `apps/healthcore_web_portal/index.html`, `application.html`, `validation.js`
- No framework; client-side validation only

### Milestone 1 (Migrated — `uis/website`)
- Next.js 16.2.6 (App Router) with TypeScript and Tailwind CSS v4 via PostCSS
- React 19 functional components (target ≤80 lines per component file)
- Routes: `/` (landing), `/enquiry-form` (patient enquiry)
- Bilingual EN/ES: `lib/i18n/translations.ts`, `LanguageProvider`, `?lang=` + `localStorage`
- No backend; form submit shows success modal only (parity with legacy)
- Verification: `cd uis/website && npm run verify`

### Milestone 2
- TypeScript for all business logic utilities
- Node.js for CLI/test execution
- Modular code structure: models, collections, search, transformations, validations
- Location: `apps/src/` — **not yet imported by `uis/website`** (deferred)

### Milestone 3
- Next.js 16 (App Router) with TypeScript and Tailwind CSS
- React functional components
- API integration with Talent Tracker API
- Mobile-first responsive design
- Location: `apps/talent-pipeline-tracker/`

### Milestone 4
- Migration target: `uis/website/` (new top-level `uis/` folder)
- Legacy reference: `apps/healthcore_web_portal/` (do not delete until explicit cutover)
- Patterns aligned with `apps/talent-pipeline-tracker/`
- M2 utility integration planned as a follow-up phase

## Architectural Decisions Made

### Milestone 1 (Legacy)
- Two-page static site: landing page and application form
- Shared header, footer, and navigation
- All validation and interactivity handled client-side
- Schema.org markup for SEO and compliance

### Milestone 1 (Migrated — `uis/website`)
- App Router with `app/page.tsx` and `app/enquiry-form/page.tsx`
- Shared chrome in `components/layout/`; landing sections in `components/landing/`
- Enquiry UI in `components/enquiry/`; validation in `lib/enquiry-validation.ts`
- JSON-LD in `components/schema-org/`
- Footer in root `app/layout.tsx`; header per page

### Milestone 2
- Strong typing and validation for all business entities
- Pure functions for all calculations and data transformations
- Test harness and CLI for validation and verification

### Milestone 3
- SPA architecture with route-level pages for candidate management
- State management via React hooks and URL query params
- All API calls handled with async/await
- No third-party UI libraries (custom components only)

### Milestone 4
- New app at `uis/website` rather than in-place edit of `apps/healthcore_web_portal`
- Legacy portal retained side-by-side for regression comparison
- Enquiry route named `/enquiry-form` (not `/application`)
- M2 `apps/src` import deferred; form rules ported from `validation.js` into `uis/website`

## Technical Constraints

- Accessibility and responsive design required throughout
- All styling via Tailwind CSS (no custom CSS unless necessary)
- No backend or database for public portal; all data is client-side
- For milestone 2, logic must be deterministic and testable
- For milestone 3 and `uis/website`, components should be ≤80 lines and functional
- No third-party UI component libraries on Next.js apps
- No Tailwind CDN in `uis/website` (build pipeline only)
