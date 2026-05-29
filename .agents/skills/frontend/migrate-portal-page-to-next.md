---
name: migrate-portal-page-to-next
title: Migrate Portal Page to Next.js
description: Migrates one HealthCore static portal page (index or application) into the Next.js app at uis/website. Use when migrating healthcore_web_portal content to Next.js. The legacy app is retained, not deleted.
scope: Milestone 4 migration from apps/healthcore_web_portal into uis/website (legacy portal remains in place)
globs:
  - apps/healthcore_web_portal/**
  - uis/website/**
  - uis/website/app/**
  - uis/website/components/**
alwaysApply: false
content: |
  ## When to use

  - Migrate `index.html` or `application.html` content into the Next.js app at `uis/website`.
  - Add a new public route in `uis/website` that mirrors static portal behavior.
  - Milestone 4 refactor of the public web portal.

  ## Target and legacy apps

  - **New app (migration target):** `uis/website` — all migrated Next.js routes, components, and layout live here.
  - **Legacy app (source, retained):** `apps/healthcore_web_portal/` — do **not** delete this folder or its files when migrating. It remains the reference implementation until the team explicitly retires it.

  ## Prerequisites

  - Read `memory-bank/techContext.md` and `memory-bank/decisions.md` (Milestone 4).
  - Scaffold or use the Next.js app under `uis/website` (Next.js 16, App Router, TypeScript, Tailwind).
  - Follow `.agents/rules/frontend/*` for stack, styling, a11y, bilingual parity, Schema.org, and component limits.

  ## Steps

  1. **Inventory source (legacy)**
     - Open the source page under `apps/healthcore_web_portal/` (`index.html` or `application.html`).
     - Read `validation.js` if the page includes the enquiry form.
     - Note EN/ES copy blocks, Schema.org JSON-LD, shared header/nav/footer, and links between pages.
     - Leave `apps/healthcore_web_portal/` unchanged unless fixing a blocking bug in source.

  2. **Plan component boundaries**
     - Map each major HTML section to a React component under `uis/website/components/` (hero, services, locations, form sections, footer).
     - Split before 80 lines per component (see `.agents/rules/frontend/component-size-limit.md`).
     - Extract shared layout once: header, navigation, footer.

  3. **Create the route in uis/website**
     - Add `uis/website/app/<route>/page.tsx` (or `uis/website/app/page.tsx` for landing).
     - Use const functional components; Tailwind build pipeline, not CDN (see `.agents/rules/frontend/tailwind-only-no-ui-libs.md`).
     - Do not move or remove files from `apps/healthcore_web_portal/` as part of this step.

  4. **Port validation**
     - Move form logic into a hook or small components in `uis/website`.
     - Keep UI-only checks (required, format) in the frontend layer.
     - For business rules that map to `apps/src` entities, follow `.agents/skills/utilities/frontend-consume-shared-utilities.md`.
     - Do not duplicate denial/CME/claim validation logic in components.

  5. **Preserve content and SEO**
     - Keep English and Spanish parity (`.agents/rules/frontend/bilingual-parity.md`).
     - Port Schema.org markup to the Next page in `uis/website` (`.agents/rules/frontend/schemaorg-semantic-html.md`).
     - Keep semantic landmarks and accessible labels (`.agents/rules/frontend/accessibility-semantic-html.md`).

  6. **Wire navigation**
     - Replace static links with Next.js `Link` between landing and intake routes inside `uis/website`.
     - Match prior nav labels and footer content from the legacy pages.

  7. **Regression checklist**
     - Mobile, tablet, and desktop layout in `uis/website`.
     - Form validation messages and focus order.
     - Cross-page navigation works in the new app.
     - No Tailwind CDN script tags in `uis/website`.
     - EN/ES sections present where they existed in source.
     - `apps/healthcore_web_portal/` still present and untouched by deletion.

  8. **Verify**
     - Run lint and build from `uis/website`.
     - Smoke-test migrated routes in `uis/website` against legacy static behavior in `apps/healthcore_web_portal/`.

  ## Verification

  - `npm run build` (or project build script) succeeds in `uis/website`.
  - Manual compare: legacy static page vs `uis/website` route for content, form behavior, and nav.
  - Confirm `apps/healthcore_web_portal/` files were not removed.

  ## References

  - Source (retained): `apps/healthcore_web_portal/`
  - Target: `uis/website/`
  - `memory-bank/references/milestone1_ai_plan/`
  - `.agents/rules/frontend/`
  - `.agents/skills/utilities/frontend-consume-shared-utilities.md`
examples:
  - "Good: New landing at uis/website/app/page.tsx; apps/healthcore_web_portal/index.html left in place for reference."
  - "Good: Extract PortalHeader and PortalFooter under uis/website/components, then compose routes from shared layout."
  - "Avoid: Deleting apps/healthcore_web_portal after migrating a single page."
  - "Avoid: Scaffolding the migrated app outside uis/website without an explicit team decision."
---