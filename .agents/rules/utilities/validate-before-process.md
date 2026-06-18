---
title: Validate Before Process
description: Validate entity data before calculations or aggregations run.
scope: Validation utilities and callers
globs:
  - apps/src/utils/validations.ts
  - apps/src/utils/transformations.ts
  - apps/src/main.ts
alwaysApply: false
content: |
  Validate data before processing or aggregation.
  Return structured validation results with explicit error messages per failed rule.
examples:
  - "Good: validateClaim returns { valid: false, errors: [...] } before denial metrics run."
  - "Avoid: Running denialRateByPayer on claims that violate required field rules."
---
