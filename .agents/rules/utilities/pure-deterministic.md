---
title: Pure Deterministic Functions
description: Keep calculations and transformations pure without global state or side effects.
scope: Transformation and calculation utilities
globs:
  - apps/src/utils/transformations.ts
  - apps/src/utils/collections.ts
  - apps/src/utils/search.ts
alwaysApply: false
content: |
  Keep calculations and transformations pure and deterministic.
  Functions should only use their parameters; do not read or mutate global state.
examples:
  - "Good: calculateDenialRate(claims) returns the same result for the same input array."
  - "Avoid: Storing intermediate KPI state in a module-level variable."
---
