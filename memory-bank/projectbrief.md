# HealthCore Project Brief

## Business Description and Objectives

HealthCore is an outpatient healthcare network founded in Austin, Texas, operating 12 clinics across the US and UK. The business model is built on accessible care through same-day appointments, extended hours, and bilingual support in US locations.

### Milestone 1: Public Web Presence and Structured Intake
- Establish a credible public digital presence for HealthCore with a bilingual (English and Spanish) website.
- Present services, US clinic locations, and contact channels clearly for prospective patients.
- Replace unstructured phone-first intake with a structured patient enquiry form to reduce front-desk call overhead and improve follow-up quality.

### Milestone 2: Operational Programming Foundation
- Build reliable TypeScript business-logic utilities for claims, appointments, clinicians, and locations.
- Support denial tracking, no-show cost estimation, and CME compliance reporting for operations stakeholders.
- Standardize validation and calculation logic used for recurring weekly operational reporting.

### Milestone 3: Recruiting Product Delivery
- Deliver Talent Pipeline Tracker as a mobile-first internal recruiting application.
- Enable candidate listing, filtering, detail review, stage/status updates, note workflows, and new candidate creation.
- Integrate with the Talent Tracker API contract while handling documented schema and behavior mismatches.

### Milestone 4: Public Portal Migration
- Migrate the milestone 1 public web portal to Next.js at `uis/website` with bilingual landing and structured enquiry.
- Retain legacy static portal (`apps/healthcore_web_portal/`) for side-by-side comparison until explicit cutover.
- Align public site stack with internal Next.js apps for maintainability.

### Milestone 5: Backend and Internal Operations Platform
- Deliver FastAPI modular monolith at `services/api` with JWT authentication and password reset.
- Provide incident CSV analysis, centralized incident management, supplier registry, and medical supply inventory.
- Consolidate internal tools on a single backoffice landing app (port 3001) with same-origin routing.
- Containerize local development with Docker Compose and documented test workflows.

## Project Vision and Objectives

The project vision is to incrementally modernize HealthCore operations through milestone-driven product delivery, moving from a public-facing trust and access layer to internal operational intelligence and team workflows.

### Milestone 1 Vision
- Build trust with prospective patients and improve access through a professional, bilingual web experience.
- Objective: convert inbound interest into structured, actionable enquiries.

### Milestone 2 Vision
- Build confidence in operational decisions through deterministic, testable, and typed logic.
- Objective: produce reliable KPIs for billing, clinical operations, and compliance teams.

### Milestone 3 Vision
- Improve recruiting execution speed and data quality with a dedicated candidate workflow application.
- Objective: centralize candidate lifecycle actions in a responsive web interface integrated with backend APIs.

### Milestone 4 Vision
- Deliver a modern public web experience on the same framework as internal apps.
- Objective: enable safe migration from the legacy static portal without functional regression.

### Milestone 5 Vision
- Unify internal tooling for Patient Experience, procurement, and clinic operations behind authenticated APIs.
- Objective: replace fragmented spreadsheets and siloed tools with a consolidated backoffice hub and centralized data services.

## Target Users

### Milestone 1 Target Users
- Prospective and returning patients evaluating HealthCore online.
- Spanish-speaking patient population in US markets requiring full-language parity.
- Front-desk and patient experience teams who need structured enquiry data for callbacks.

### Milestone 2 Target Users
- CTO and technology team responsible for operational logic correctness.
- Billing team members tracking payer denial patterns.
- Clinical and people operations teams monitoring no-show impact and CME risk.

### Milestone 3 Target Users
- Internal recruiting and hiring teams managing candidate pipelines.
- Hiring stakeholders who need fast candidate status visibility and note history.
- Operations users who need mobile-first and desktop-capable workflows.

### Milestone 4 Target Users
- Prospective and returning patients using the public website.
- Front-desk and patient experience teams receiving structured enquiry submissions.
- HealthCore Digital engineers maintaining the migrated Next.js portal.

### Milestone 5 Target Users
- Patient Experience teams analyzing and managing incident data.
- Procurement and compliance staff using the supplier directory.
- Clinic operations staff logging inventory deliveries and consumption.
- HealthCore Digital engineering and authenticated backoffice users.

## Problem the Project Solves

### Milestone 1 Problem
- HealthCore lacked a credible, secure, and bilingual public web presence.
- Intake data was captured via long, unstructured phone calls, slowing appointment follow-up and harming conversion.

### Milestone 2 Problem
- Critical operational metrics (denials, no-show cost, CME progress) were manually computed and error-prone.
- Teams lacked reusable and validated logic to generate trustworthy weekly metrics.

### Milestone 3 Problem
- Recruiting workflows were fragmented and inefficient across candidate review, updates, and note management.
- The organization needed a responsive, API-connected application to manage end-to-end candidate progression.

### Milestone 4 Problem
- The legacy static portal was hard to maintain and inconsistent with the internal app stack.
- Migration required framework parity without breaking public-facing behaviour.

### Milestone 5 Problem
- Operational data lived in departmental spreadsheets and disconnected tools.
- Teams needed centralized APIs, audit-friendly supplier and inventory records, and HIPAA-safe incident reporting in a single authenticated backoffice experience.

## Repository Scope

This monorepo delivers HealthCore Digital milestone work across `uis/`, `services/api`, `apps/`, and shared packages. Business narrative and stakeholder context live in [CONTEXT.md](../CONTEXT.md). Delivery status and technical detail are in [progress.md](progress.md) and [techContext.md](techContext.md).
