---
title: Utility Reuse
description: Import shared TypeScript utilities instead of duplicating business logic in UI code.
scope: Frontend apps that need validation or calculations
globs:
  - apps/talent-pipeline-tracker/**
  - apps/healthcore_web_portal/**
  - apps/**/app/**
  - apps/**/components/**
alwaysApply: false
content: |
  When frontend workflows need validation, calculations, or other business logic, import and reuse
  existing TypeScript utilities from shared modules (for example, under apps/src/).
  Do not duplicate equivalent business logic inside page or component files.
examples:
  - "Good: Import validateClaim from apps/src/utils/validations.ts in a form workflow."
  - "Avoid: Re-implementing denial-rate math inline in a React component."
---
