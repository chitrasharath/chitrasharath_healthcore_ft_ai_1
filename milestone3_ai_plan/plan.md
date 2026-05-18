# Project Overview

Talent Pipeline Tracker is a mobile-first recruiting app backed by the Talent Tracker API. It should let an internal team review all candidates, filter by status and stage, search by name or email without a full page reload, open a full candidate record, update hiring progress, manage internal notes after calls or interviews, create new candidate records, and correct bad source data. Design for a 375px viewport first, then adapt the interface for desktop at 768px and above.

## App Description

Talent Pipeline Tracker should be implemented as a Single Page App with route-level pages for candidate listing, candidate detail, candidate detail editing, and new candidate registration. The app should prioritize fast mobile scanning at `375px`, keep filtering and searching on the client without full page reloads, and expand the layout for desktop at `768px` and above.

### Candidate List Page

- Render a candidate table with `Full Name`, `Position Applied For`, `Current Status`, and `Current Stage`.
- Populate the table with `GET /records`.
- Add pagination controls at the bottom of the page.
- Add a top-right button to create a new candidate and route to the new candidate form page.
- For each candidate row, render three action icons:
  - View candidate detail.
  - Edit candidate detail.
  - Add a note for the candidate.
- Use `useSearchParams` for `status`, `stage`, `page`, and `limit`.
- Add a search input that filters by name or email without reloading the page.
- Show a spinner while records are loading.
- Show an error state if the records fetch fails.
- The add-note icon should route to the edit page with the notes section expanded, since note creation belongs to the edit flow described below.

### Candidate Detail View Page

- Display the candidate `name`, `email`, `phone`, `position`, `linkedin_url`, `cv_url`, `experience_years`, `status`, `stage`, and `applied_at`.
- Populate the page with `GET /records/{id}`.
- Add a button to return to the candidate list page.

### Candidate Detail Edit Page

- Display the same candidate fields as the detail view page.
- Populate the page with `GET /records/{id}`.
- Allow the user to edit `status` and `stage`.
- Save `status` and `stage` changes with `PATCH /records/{id}`.
- Show a non-editable field with the number of notes for the candidate using `GET /records/{id}/notes`.
- Add a notes button with an icon. Clicking it should reveal the notes section at the end of the page.
- Load existing notes with `GET /records/{id}/notes`.
- Add an input for a new note and submit it with `POST /records/{id}/notes`.
- Existing notes should be displayed read-only.
- For each existing note, add a remove button with an icon on the Candidate Detail Edit page.
- Use `DELETE /records/{id}/notes/{note_id}` when the remove action is triggered.
- Add a save button with an icon for candidate updates.

### New Candidate Form Page

- Include fields for `full_name`, `email`, `phone`, `position`, `linkedin_url`, `cv_url`, and `experience_years`.
- Show read-only UI defaults for:
  - `status = received`
  - `stage = pending`
  - `application date = today`
- Add a save action for the new candidate record.
- User requirement note: the requested save action is `PUT /records/{id}`.
- API contract note: the current backend exposes candidate creation as `POST /records`, while `PUT /records/{id}` is a full replacement endpoint for an existing record.
- Planning instruction: flag this mismatch and use `POST /records` for new candidate creation unless the backend contract changes.

## Tech Stack

- Build the project as a `Next.js 16` app with `TypeScript`, `Tailwind CSS`, and the `App Router`.

### Project Setup Instructions

- Create a git branch named `milestone3-talent-pipeline-tracker`.
- Place the project under the `apps` directory in a folder named `talent-pipeline-tracker`.
- Scaffold the app with `npx create-next-app@latest apps/talent-pipeline-tracker --ts --tailwind --app --eslint --use-npm --no-src-dir --import-alias "@/*"`.
- Organize the project with:
  - `/app` for routes.
  - `/components` for reusable UI pieces.
  - `/types` for TypeScript interfaces and shared types.

### Implementation Instructions

- Handle all API calls with `async/await`.
- Model data fetching with three states: `loading`, `success`, and `error`.
- UI updates must reflect mutations and filters without a full page reload.
- Use the Next.js `<Link>` component for all navigation.
- Use `useEffect` to simulate loading the listing data and show a loading indicator while the data is not yet available.
- Use `useState` to track the selected or typed search value and filter the candidate list.

## Testing the API

- Add the API URL to the root `.env` file. Example:
  - `NEXT_PUBLIC_API_URL=https://playground.4geeks.com/tracker/api/v1`
- Use the `openapi.json` schema to test every documented API path before implementation.
- Verify that all documented paths are reachable.
- Identify and document any paths that fail.
- Record any mismatches between the schema and live API behavior discovered during testing.

## Constraints

- Use only `Tailwind CSS` for styling.
- All components must be custom. Do not use third-party UI component libraries.
- No component should exceed `80` lines of JSX and logic combined. If a component grows past that size, split it into smaller components or hooks.
- All components must be defined as `const` functional components.
- Do not use class components.

## Core Product Requirements

- Show all candidates in a list.
- Support filtering by `status` and `stage` without reloading the page.
- Support searching by candidate name or email without reloading the page.
- Open a candidate detail view with the full record information.
- Allow status and stage updates from the candidate detail view.
- Allow internal notes to be added after calls or interviews.
- Allow internal notes to be removed when they are no longer relevant.
- Allow new candidate registration.
- Allow incorrect candidate data to be corrected after submission.
- Include a path for referral-based candidates, but do not invent backend persistence that is not present in the current API contract.

## Backend Contract

- API docs: `https://playground.4geeks.com/tracker/api/v1/docs`
- OpenAPI schema: `https://playground.4geeks.com/tracker/api/v1/openapi.json`
- Base API URL: `https://playground.4geeks.com/tracker/api/v1`

### Records

- `GET /records`
  - Returns a paginated list shaped like `total`, `page`, `limit`, and `data`.
  - Supports query params:
    - `status`
    - `stage`
    - `search`
    - `page`
    - `limit`
- `GET /records/{id}`
  - Returns a single candidate record.
- `POST /records`
  - Creates a new candidate record.
- `PUT /records/{id}`
  - Replaces a full candidate record and should be treated as the correction path for base candidate data.
- `PATCH /records/{id}`
  - Updates `status` and/or `stage`.
- `DELETE /records/{id}`
  - Exists in the API, but it is not a required feature based on the current app scope unless the project plan explicitly adds it later.

### Notes

- `GET /records/{id}/notes`
  - Returns notes for a candidate.
- `POST /records/{id}/notes`
  - Adds a note with `content`.
- `DELETE /records/{id}/notes/{note_id}`
  - Removes a note.

### Supported Record Fields

- `id`
- `full_name`
- `email`
- `phone`
- `position`
- `linkedin_url`
- `cv_url`
- `experience_years`
- `status`
- `stage`
- `notes_count`
- `applied_at`
- `updated_at`

### Supported Workflow Values

- Status values from the schema:
  - `received`
  - `in_progress`
  - `selected`
  - `discarded`
- Stage values from the schema:
  - `pending`
  - `review`
  - `personal_interview`
  - `technical_interview`
  - `offer_presented`

### Planning Constraints From The API

- Treat the backend contract as the source of truth for persisted fields.
- The current schema does not expose a dedicated referral field. The project plan must call this out explicitly instead of assuming unsupported referral persistence.
- The live list response currently includes nested `notes` inside each record, but the schema only clearly guarantees `notes_count` on `RecordOut`. The project plan should treat the record detail endpoint and notes endpoint as the canonical sources for detailed note state.
- `RecordCreate` only supports `full_name`, `email`, `phone`, `position`, `linkedin_url`, `cv_url`, and `experience_years`.
- The current create schema does not accept `status`, `stage`, or `applied_at`, so those values should be treated as UI defaults or server-managed values unless the backend changes.
- The requested new-candidate save flow conflicts with the current API contract:
  - Requested flow: `PUT /records/{id}`
  - Current creation endpoint: `POST /records`
- Use `PATCH /records/{id}` only for `status` and `stage` updates.

## Component Analysis

### Route Components

- `const CandidateListPage = () => {}`
  - Owns list loading, URL-driven filters, search params, pagination state, loading state, and list-level error state.
  - Calls `GET /records`.
- `const CandidateDetailPage = () => {}`
  - Owns candidate detail loading and the back-to-list action.
  - Calls `GET /records/{id}`.
- `const CandidateEditPage = () => {}`
  - Owns candidate detail loading, `status` and `stage` editing, note-count loading, note-panel toggling, note creation, note deletion, and edit-page error handling.
  - Calls `GET /records/{id}`, `PATCH /records/{id}`, `GET /records/{id}/notes`, `POST /records/{id}/notes`, and `DELETE /records/{id}/notes/{note_id}`.
- `const NewCandidatePage = () => {}`
  - Owns candidate creation form state, validation feedback, read-only defaults, and create submission handling.
  - Should plan against `POST /records` unless the backend contract changes.

### List-Page Components

- `const CandidateTable = () => {}`
  - Receives normalized candidate rows and renders the table shell.
- `const CandidateTableRow = () => {}`
  - Renders one candidate row and the three row-level action icons.
- `const CandidateFilters = () => {}`
  - Manages `status` and `stage` filters through `useSearchParams`.
- `const CandidateSearchInput = () => {}`
  - Controls the search term for name and email filtering without a reload.
- `const PaginationControls = () => {}`
  - Renders page navigation from the paginated `GET /records` response.
- `const ListPageToolbar = () => {}`
  - Contains the create button, search input, and filters.

### Detail And Edit Components

- `const CandidateSummaryCard = () => {}`
  - Displays the candidate fields shared by the detail and edit flows.
- `const CandidateStatusStageForm = () => {}`
  - Renders editable `status` and `stage` controls and the save action for `PATCH /records/{id}`.
- `const NotesCountField = () => {}`
  - Displays the read-only note count from `GET /records/{id}/notes`.
- `const NotesPanel = () => {}`
  - Wraps note loading, note list rendering, note deletion, and note creation controls.
- `const NotesList = () => {}`
  - Displays existing notes as read-only items with a remove action.
- `const NoteComposer = () => {}`
  - Renders the new-note input and submit action for `POST /records/{id}/notes`.

### Shared UI Components

- `const LoadingSpinner = () => {}`
  - Reusable loading state for list, detail, edit, and notes fetches.
- `const ErrorState = () => {}`
  - Reusable error message block for fetch and mutation failures.
- `const IconButton = () => {}`
  - Reusable icon-only or icon-plus-label button.
- `const ReadOnlyField = () => {}`
  - Reusable labeled field for immutable data such as note count or defaulted creation values.
- `const PageHeader = () => {}`
  - Reusable title and action area for each route-level page.

### Data Ownership Notes

- Candidate list data should be fetched at the list page level and passed down as props.
- Candidate detail data should be fetched per route using the candidate `id`.
- Notes should be loaded from the notes endpoint when the edit page needs accurate note data.
- Search, filter, and pagination state should stay URL-addressable through `useSearchParams`.
- If a component exceeds `80` lines of JSX and logic combined, split it into smaller pieces before implementation.

## Data Schema

```ts
type CandidateStatus =
  | "received"
  | "in_progress"
  | "selected"
  | "discarded";

type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

type CandidateRecord = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
  status: CandidateStatus;
  stage: CandidateStage;
  notes_count: number;
  applied_at: string;
  updated_at: string;
};

type CandidateNote = {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
};

type CandidateListResponse = {
  total: number;
  page: number;
  limit: number;
  data: CandidateRecord[];
};

type CandidateNotesResponse = {
  data: CandidateNote[];
  meta: {
    total: number;
  };
};

type CandidateCreatePayload = {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  experience_years: number;
};

type CandidatePatchPayload = {
  status?: CandidateStatus;
  stage?: CandidateStage;
};

type CandidateListQuery = {
  status?: CandidateStatus;
  stage?: CandidateStage;
  search?: string;
  page?: number;
  limit?: number;
};

type NewCandidateViewDefaults = {
  status: "received";
  stage: "pending";
  application_date: string;
};
```

## Hardcoded Sample Data

```ts
const sampleCandidateListResponse: CandidateListResponse = {
  total: 3,
  page: 1,
  limit: 20,
  data: [
    {
      id: "c-1001",
      full_name: "Ava Chen",
      email: "ava.chen@example.com",
      phone: "+1 555-0145",
      position: "Product Designer",
      linkedin_url: "https://linkedin.com/in/ava-chen",
      cv_url: "https://storage.example.com/cv/c-1001.pdf",
      experience_years: 4,
      status: "received",
      stage: "pending",
      notes_count: 1,
      applied_at: "2026-05-18T09:00:00.000Z",
      updated_at: "2026-05-18T09:00:00.000Z",
    },
    {
      id: "c-1002",
      full_name: "Mateo Rivera",
      email: "mateo.rivera@example.com",
      phone: "+1 555-0177",
      position: "Frontend Engineer",
      linkedin_url: "https://linkedin.com/in/mateo-rivera",
      cv_url: "https://storage.example.com/cv/c-1002.pdf",
      experience_years: 6,
      status: "in_progress",
      stage: "technical_interview",
      notes_count: 2,
      applied_at: "2026-05-10T14:30:00.000Z",
      updated_at: "2026-05-17T11:45:00.000Z",
    },
    {
      id: "c-1003",
      full_name: "Nina Patel",
      email: "nina.patel@example.com",
      phone: "+1 555-0119",
      position: "Recruiting Coordinator",
      linkedin_url: null,
      cv_url: "https://storage.example.com/cv/c-1003.pdf",
      experience_years: 3,
      status: "selected",
      stage: "offer_presented",
      notes_count: 0,
      applied_at: "2026-05-02T08:15:00.000Z",
      updated_at: "2026-05-16T16:20:00.000Z",
    },
  ],
};

const sampleCandidateDetail: CandidateRecord = {
  id: "c-1002",
  full_name: "Mateo Rivera",
  email: "mateo.rivera@example.com",
  phone: "+1 555-0177",
  position: "Frontend Engineer",
  linkedin_url: "https://linkedin.com/in/mateo-rivera",
  cv_url: "https://storage.example.com/cv/c-1002.pdf",
  experience_years: 6,
  status: "in_progress",
  stage: "technical_interview",
  notes_count: 2,
  applied_at: "2026-05-10T14:30:00.000Z",
  updated_at: "2026-05-17T11:45:00.000Z",
};

const sampleCandidateNotesResponse: CandidateNotesResponse = {
  data: [
    {
      id: "n-7001",
      record_id: "c-1002",
      content: "Strong portfolio review. Move forward to technical interview.",
      created_at: "2026-05-15T10:00:00.000Z",
    },
    {
      id: "n-7002",
      record_id: "c-1002",
      content: "Follow-up call completed. Candidate is available to start in 30 days.",
      created_at: "2026-05-17T15:20:00.000Z",
    },
  ],
  meta: {
    total: 2,
  },
};

const sampleCandidateCreatePayload: CandidateCreatePayload = {
  full_name: "Noah Brooks",
  email: "noah.brooks@example.com",
  phone: "+1 555-0134",
  position: "Sales Operations Analyst",
  linkedin_url: "https://linkedin.com/in/noah-brooks",
  cv_url: "https://storage.example.com/cv/noah-brooks.pdf",
  experience_years: 5,
};

const sampleNewCandidateViewDefaults: NewCandidateViewDefaults = {
  status: "received",
  stage: "pending",
  application_date: "2026-05-18",
};
```

## Interaction Requirements

- Filtering and search must update the candidate list asynchronously without a full page reload.
- Candidate detail updates should keep list and detail state in sync after status or stage changes.
- Note creation and deletion should update the visible note list and note counts immediately after successful API responses.
- Candidate creation and correction flows should reflect backend validation errors clearly in the UI.

## Responsive Requirements

- Design for a `375px` viewport first.
- Adjust layout and spacing for desktop at `768px` and above.
- Mobile should prioritize fast scanning, direct filtering, and a clear path into candidate detail.
- Desktop can expand list density and show more supporting information, but it should preserve the same core flows as mobile.

## Primary User

The primary user is a Healthcore recruiter, hiring coordinator, or operations lead who needs to move quickly through a high volume of candidates without losing context. They are trying to review applicant pipelines, understand each candidate’s current stage, capture notes from calls and interviews, correct intake mistakes, and keep momentum across the hiring process with as few clicks and page transitions as possible.

## Healthcore Brand Reuse

- Use the company name `Healthcore` throughout the product UI.
- Reuse the existing `Healthcore` logo already used in `apps/healthcore_web_portal`. Do not redraw, replace, or restyle the logo.
- Reuse the color scheme from the `apps/healthcore_web_portal` web page. Do not introduce a separate or competing palette for this app.
- Extract the existing portal colors into shared UI tokens before implementation. Recommended token set:
  - `--hc-brand`
  - `--hc-brand-strong`
  - `--hc-surface`
  - `--hc-surface-muted`
  - `--hc-border`
  - `--hc-text`
  - `--hc-text-muted`
  - `--hc-success`
  - `--hc-warning`
  - `--hc-danger`
- Apply the same Healthcore brand palette consistently across:
  - sticky header
  - sticky footer
  - primary buttons
  - filter controls
  - links
  - status badges
  - stage badges
  - loading states
  - empty states
  - error states

## Visual Design Direction

- The interface should feel clinical, efficient, and trustworthy rather than decorative or consumer-social.
- Use a light surface-first layout with strong contrast, clean spacing, and restrained accent color usage.
- Keep the page chrome consistent with the Healthcore portal so users feel they are still inside the same product family.
- On mobile, prioritize vertical rhythm, large touch targets, and clear status chips over dense horizontal data.
- On desktop, increase information density with clearer table headers, wider spacing between columns, and more persistent secondary metadata.
- Prefer rounded cards, thin borders, and layered surfaces over heavy drop shadows.
- Use status and stage chips to make candidate progress scannable at a glance.

## Navigation Experience

- The `Candidate List Page` should be the landing page and primary navigation hub.
- The primary flow should be:
  - open the candidate list
  - filter or search
  - open candidate detail
  - edit candidate pipeline data or notes
  - return to the list without losing context
- Selecting the row or the view icon should open the read-only candidate detail page.
- Selecting the edit icon should open the candidate edit page.
- Selecting the note icon from the list should open the candidate edit page with the notes section already expanded.
- After saving changes or creating a candidate, return the user to the candidate list with visible confirmation feedback and preserved search, filter, and pagination state when possible.
- Use a clear back path from detail and edit routes to the list route.
- Keep all navigation transitions within the SPA and use the Next.js `Link` component.

## Page Design Proposals

### Candidate List Page Design

- Mobile design should use a compact stacked data-card presentation that preserves table meaning while fitting the `375px` viewport.
- Desktop design should switch to a true multi-column table layout at `768px` and above.
- The top area should include:
  - Healthcore logo on the left
  - page title and candidate count
  - primary add-candidate button on the right
- Search should be placed above the list and remain visually prominent.
- Status and stage filters should sit directly below search as pill controls or compact selects.
- Each candidate row or card should visually prioritize:
  - full name
  - applied position
  - current status chip
  - current stage chip
- Row actions should appear as compact icon buttons with accessible labels for:
  - view
  - edit
  - add note
- Pagination should be fixed to the bottom of the content area, visually separate from row actions, and easy to tap on mobile.

### Candidate Detail View Page Design

- Use a clean profile layout with the candidate name, status, and stage as the visual anchor at the top of the page.
- Show contact data and application metadata in grouped information cards rather than one long list.
- Present `linkedin_url` and `cv_url` as clear action links with icons.
- Use a clear secondary button to return to the candidate list.
- Keep the page calm and scan-friendly; this page is for review, not editing.

### Candidate Detail Edit Page Design

- Reuse the same visual structure as the detail page so the user does not feel they have left the candidate context.
- Elevate the editable `status` and `stage` controls in a dedicated form panel near the top.
- Show the note count near the notes toggle so the user immediately understands note volume.
- The notes area should expand below the candidate summary and read as a chronological activity section.
- Each note should be rendered as a compact note card with:
  - timestamp
  - note content
  - remove button with icon
- The add-note input should sit above the note history so new capture feels immediate.
- The save action should remain visually strong and easy to reach on mobile.

### New Candidate Form Page Design

- Use a single-column form on mobile and a two-column layout only from `768px` upward.
- Group fields into:
  - candidate identity
  - contact information
  - professional profile
  - system defaults
- Render `status`, `stage`, and application date as read-only fields with quiet styling so users understand they are system-controlled.
- Keep the save action fixed near the bottom of the viewport on mobile when the form is active.
- Use inline validation and concise helper text to reduce form abandonment.

## Icon And Image Links

### Brand Images

- `Healthcore logo`: reuse the exact existing logo asset already used in `apps/healthcore_web_portal`.
- Resolve the exact logo file path from the existing portal header implementation and reuse that same asset rather than creating a new logo file.
- `Healthcore favicon or mark`: reuse the existing app icon from `apps/healthcore_web_portal` if present.
- Do not introduce unrelated stock photography or decorative illustrations unless Healthcore already uses them in the existing portal.

### Candidate Avatar Placeholder Images For Mock Data

- `https://api.dicebear.com/9.x/initials/svg?seed=Ava%20Chen`
- `https://api.dicebear.com/9.x/initials/svg?seed=Mateo%20Rivera`
- `https://api.dicebear.com/9.x/initials/svg?seed=Nina%20Patel`

### Icon Links

- Search: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/magnifying-glass.svg`
- Filter: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/funnel.svg`
- Add candidate: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/plus.svg`
- View candidate: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/eye.svg`
- Edit candidate: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/pencil-square.svg`
- Add note: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/chat-bubble-left-right.svg`
- Remove note: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/trash.svg`
- Back to list: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/arrow-left.svg`
- External profile or CV link: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/arrow-top-right-on-square.svg`
- Email: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/envelope.svg`
- Phone: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/phone.svg`
- Pagination previous: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/chevron-left.svg`
- Pagination next: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/chevron-right.svg`
- Save success: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/check-circle.svg`
- Error state: `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/exclamation-triangle.svg`

## Sticky Header And Footer

- Add a sticky header across all pages.
- The sticky header should contain:
  - Healthcore logo on the left
  - current page title in the center or center-left
  - the most relevant page action on the right
- The header should stay visible while scrolling and keep key actions available without crowding the content.
- Add a sticky footer across all pages.
- On mobile, the sticky footer should act as a compact persistent action zone for navigation and the most important page action.
- On desktop, the sticky footer can be quieter and show:
  - product context
  - pagination status when relevant
  - save action when relevant
- Add bottom padding to page content so the sticky footer never overlaps form fields, notes, or pagination controls.

## Accessibility And Usability Requirements

- Maintain strong color contrast across text, badges, buttons, and table states.
- Use visible keyboard focus states for all interactive elements.
- Keep touch targets large enough for mobile use.
- Ensure icon-only buttons always include accessible labels.
- Use clear validation messaging near the affected field instead of generic form errors.
- Provide `aria-live` feedback for save success, fetch error, and note deletion.

## Empty, Error, And Success States

- Add a no-results state for search and filter combinations that return zero candidates.
- Add an empty-notes state that encourages the user to capture the first interview or call note.
- Add a fetch-error state with a retry action for candidate list, candidate detail, and notes loading.
- Add lightweight success feedback after:
  - candidate creation
  - status or stage update
  - note creation
  - note removal
