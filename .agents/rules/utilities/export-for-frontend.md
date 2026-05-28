---
title: Export for Frontend Import
description: Export utility modules so frontend apps can import them directly.
scope: Public exports from apps/src utility modules
globs:
  - apps/src/utils/**
  - apps/src/types/**
alwaysApply: false
content: |
  All utility modules and functions must be exported and accessible for import in frontend
  application files (for example, Next.js pages and components).
examples:
  - "Good: Named exports from apps/src/utils/validations.ts consumed by a form component."
  - "Avoid: Private unexported helpers that duplicate logic already needed in the UI layer."
---
