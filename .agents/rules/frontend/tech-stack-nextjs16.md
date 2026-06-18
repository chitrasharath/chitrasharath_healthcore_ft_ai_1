---
title: Frontend Tech Stack
description: Require Next.js 16 App Router with TypeScript and Tailwind CSS for Next.js frontend applications.
scope: Next.js applications under apps/
globs:
  - apps/talent-pipeline-tracker/**
  - apps/**/app/**
  - apps/**/components/**
  - apps/**/lib/**
alwaysApply: false
content: |
  Use Next.js 16 App Router with TypeScript and Tailwind CSS for Next.js frontend applications.
  Handle data fetching and mutations with async/await and explicit loading, success, and error states.
examples:
  - "Good: Route pages live under app/ and reusable UI under components/ with TypeScript."
  - "Avoid: Introducing a separate non-Next framework for apps that should follow this stack."
---
