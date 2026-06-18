---
title: Component Size Limit
description: Keep React components small, functional, and within an 80-line limit.
scope: React components in Next.js apps
globs:
  - apps/talent-pipeline-tracker/components/**
  - apps/talent-pipeline-tracker/app/**
  - apps/**/components/**
alwaysApply: false
content: |
  Use const functional components only.
  Keep each component file at 80 lines or less (JSX and logic combined).
  Split into smaller components or hooks when a file grows beyond the limit.
examples:
  - "Good: Extract useCandidateList hook and keep CandidateListPage under 80 lines."
  - "Avoid: A 150-line page component that mixes fetch, filters, table, and pagination."
---
