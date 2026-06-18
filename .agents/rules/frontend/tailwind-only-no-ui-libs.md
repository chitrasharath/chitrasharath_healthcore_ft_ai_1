---
title: Tailwind Styling
description: Use Tailwind for styling, avoid third-party UI libraries, and choose the correct Tailwind delivery per app type.
scope: All frontend styling under apps/
globs:
  - apps/talent-pipeline-tracker/**
  - apps/healthcore_web_portal/**
  - apps/**/app/**
  - apps/**/components/**
alwaysApply: false
content: |
  Use Tailwind CSS for all styling; avoid third-party UI component libraries.
  For Next.js applications, use the project's Tailwind CSS build pipeline. Do not load Tailwind via CDN.
  For standalone static HTML pages without a build step, Tailwind via CDN is acceptable when that is the established stack.
  Avoid custom CSS unless strictly necessary.
examples:
  - "Good: className utilities in a Next.js component; postcss/tailwind config in the app root."
  - "Good: Tailwind CDN script in apps/healthcore_web_portal static HTML only."
  - "Avoid: Adding MUI or Chakra to a Next.js app; loading Tailwind CDN in talent-pipeline-tracker."
---
