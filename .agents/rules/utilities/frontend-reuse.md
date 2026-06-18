---
title: Frontend Reuse of Utilities
description: Frontend flows must call shared utilities instead of duplicating business logic.
scope: Frontend apps importing apps/src utilities
globs:
  - apps/talent-pipeline-tracker/**
  - apps/healthcore_web_portal/**
  - apps/**/app/**
  - apps/**/components/**
alwaysApply: false
content: |
  Frontend flows must reuse utility functions instead of duplicating business logic in UI components.
  Import validation and calculation helpers from apps/src when the workflow needs them.
examples:
  - "Good: A migrated intake form calls validateClaim before submit."
  - "Avoid: Copy-pasting denial-rate formulas into a React hook."
---
