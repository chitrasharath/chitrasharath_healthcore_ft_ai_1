---
title: Testable Logic
description: Keep utility logic verifiable with lightweight automated checks.
scope: Tests and runnable verification for apps/src
globs:
  - apps/src/tests/**
  - apps/src/main.ts
  - apps/src/utils/**
alwaysApply: false
content: |
  Ensure logic is testable and verified with lightweight checks where applicable.
  Add or update tests when changing business rules or thresholds.
examples:
  - "Good: apps/src/tests/run-tests.ts covers boundary cases for threshold helpers."
  - "Avoid: Changing CME compliance rules without updating deterministic test coverage."
---
