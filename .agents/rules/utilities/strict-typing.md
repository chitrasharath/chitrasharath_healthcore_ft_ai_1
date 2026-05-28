---
title: Strict TypeScript Entities
description: Model business entities with strict TypeScript interfaces and no any.
scope: Shared business-logic utilities under apps/src
globs:
  - apps/src/types/**
  - apps/src/utils/**
alwaysApply: false
content: |
  Implement business logic in TypeScript with strict typing for all entities.
  Define interfaces for Claim, Appointment, Clinician, Location, and related types in models.
examples:
  - "Good: ClaimStatus union type and Claim interface in apps/src/types/models.ts."
  - "Avoid: Untyped parameters or any for entity payloads."
---
