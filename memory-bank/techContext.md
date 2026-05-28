# Technical Context

## Tech Stack

### Milestone 1
- HTML, JavaScript, and Tailwind CSS (via CDN)
- No framework; static HTML pages (index.html, application.html)
- JavaScript for form validation and interactivity

### Milestone 2
- TypeScript for all business logic utilities
- Node.js for CLI/test execution
- Modular code structure: models, collections, search, transformations, validations

### Milestone 3
- Next.js 16 (App Router) with TypeScript and Tailwind CSS
- React functional components
- API integration with Talent Tracker API
- Mobile-first responsive design

### Milestone 4 (Planned Migration)
- Migrate milestone 1 (healthcore_web_portal) to the same tech stack as milestone 3:
	- Next.js 16 (App Router)
	- TypeScript
	- Tailwind CSS
- Refactor static HTML/JS into React components and Next.js pages
- Integrate and import business logic functions from milestone 2 into the migrated milestone 1 app for validation and data processing
- This file will be updated after migration to document new architecture and any additional constraints or decisions

## Architectural Decisions Made

### Milestone 1
- Two-page static site: landing page and application form
- Shared header, footer, and navigation
- All validation and interactivity handled client-side
- Schema.org markup for SEO and compliance

### Milestone 2
- Strong typing and validation for all business entities
- Pure functions for all calculations and data transformations
- Test harness and CLI for validation and verification

### Milestone 3
- SPA architecture with route-level pages for candidate management
- State management via React hooks and URL query params
- All API calls handled with async/await
- No third-party UI libraries (custom components only)

### Milestone 4 (Planned)
- Milestone 1 migration will adopt the same architectural decisions as milestone 3:
	- SPA architecture with route-level pages for public site and application form
	- State management via React hooks and URL query params
	- All validation and interactivity handled in React components
	- All API calls and data processing handled with async/await and imported business logic functions from milestone 2
	- No third-party UI libraries (custom components only)
	- All styling via Tailwind CSS
- Will enable direct import of milestone 2 business logic functions into the new milestone 1 app

## Technical Constraints

- Accessibility and responsive design required throughout
- All styling via Tailwind CSS (no custom CSS unless necessary)
- No backend or database for milestone 1; all data is client-side
- For milestone 2, logic must be deterministic and testable
- For milestone 3, all components must be ≤80 lines and functional
- For milestone 4, all components in the migrated milestone 1 app must also be ≤80 lines and functional
