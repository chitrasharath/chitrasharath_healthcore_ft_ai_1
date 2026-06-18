---
title: Module Separation
description: Split utilities by responsibility into focused modules.
scope: apps/src utility layout
globs:
  - apps/src/utils/**
alwaysApply: false
content: |
  Separate utility concerns into focused modules: collections, search, transformations, validations.
  Do not mix unrelated responsibilities in a single file.
examples:
  - "Good: filterClaims in collections.ts; calculateDenialRate in transformations.ts."
  - "Avoid: Search, validation, and KPI math all in one utils.ts file."
---
