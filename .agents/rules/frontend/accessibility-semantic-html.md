---
title: Accessibility and Semantic HTML
description: Enforce accessible, semantic markup on public and internal UI surfaces.
scope: Public-facing and user-facing frontend markup
globs:
  - apps/talent-pipeline-tracker/**
  - apps/healthcore_web_portal/**
  - apps/**/app/**
  - apps/**/components/**
alwaysApply: false
content: |
  Enforce accessibility and semantic HTML across all public UI surfaces.
  Use semantic elements, labels, alt text, visible focus states, and ARIA only when needed.
  Keep touch targets large enough for mobile use.
examples:
  - "Good: <button type=\"button\" aria-label=\"View candidate\"> with a visible focus ring."
  - "Avoid: <div onClick> for primary actions without keyboard support or accessible name."
---
