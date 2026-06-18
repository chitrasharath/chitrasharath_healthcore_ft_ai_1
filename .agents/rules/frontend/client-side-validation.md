---
title: Client-Side Validation
description: Validate forms in the UI with clear errors and explicit API failure handling.
scope: Forms and mutation flows in frontend apps
globs:
  - apps/talent-pipeline-tracker/components/**
  - apps/talent-pipeline-tracker/app/**
  - apps/healthcore_web_portal/validation.js
  - apps/healthcore_web_portal/application.html
alwaysApply: false
content: |
  Implement form validation client-side with clear, user-facing error states.
  Preserve explicit API error handling where applicable (loading, success, and error feedback).
  Place validation messages near the affected field.
examples:
  - "Good: Inline email format error on blur; API 400 mapped to a field-level message."
  - "Avoid: Silent submit failure or a generic alert with no field context."
---
