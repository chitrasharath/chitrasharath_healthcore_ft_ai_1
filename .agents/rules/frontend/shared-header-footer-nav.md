---
title: Shared Layout Chrome
description: Keep consistent header, navigation, and footer across related public routes.
scope: Public portal and branded app chrome
globs:
  - apps/healthcore_web_portal/**
  - apps/talent-pipeline-tracker/components/page-header.tsx
  - apps/talent-pipeline-tracker/components/sticky-footer.tsx
  - apps/talent-pipeline-tracker/app/layout.tsx
alwaysApply: false
content: |
  Keep shared header, navigation, and footer patterns across public routes (landing and intake flows).
  Reuse HealthCore branding consistently so users recognize the product family.
examples:
  - "Good: index.html and application.html share the same nav links and footer."
  - "Good: talent-pipeline-tracker layout.tsx wraps pages with consistent header/footer components."
  - "Avoid: A one-off intake page with different nav labels or missing footer."
---
