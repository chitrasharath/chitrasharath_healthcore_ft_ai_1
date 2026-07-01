# Milestone 5 — Frontend Spec: Inventory Management Interface

> **Branch:** `feature/milestone5` (already contains the backend inventory API)
> **Working directory:** `uis/backoffice/`

---

## 1. Project Overview

**HealthCore** is an outpatient healthcare company operating 6 clinics across Texas, Florida, and Georgia. The backend team shipped a medical supply inventory API (`services/api/app/domains/inventory/`) on this branch. This spec covers the **frontend-only** work: building the inventory section of the backoffice so operations staff can view stock, log deliveries, log clinical consumptions, and review order history — all authenticated and consuming the live API.

The backoffice is a **Next.js multi-app monorepo** at `uis/backoffice/`. The `landing` app is the main host that serves all routes. Feature modules (`backoffice_functions`, `talent-tracker`, etc.) live as sibling directories and are aliased into `landing` via `next.config.ts`. The inventory feature follows this same pattern.

### What this milestone builds

- An **inventory landing page** with hero, navigation cards, header, and footer
- A **products page** showing all medical supplies with color-coded stock levels
- An **inbound order form** to log vendor deliveries (4 fields with dropdowns)
- An **outbound order form** to log clinical consumptions with reactive stock display
- An **order history page** showing all deliveries and consumptions
- An **inventory nav card** on the backoffice hub landing page

### What this milestone does NOT build

- No backend changes — the API is already implemented
- No new auth system — reuse the existing `AuthGuard`
- No new npm dependencies
- No component library — use raw Tailwind matching existing patterns

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router) | 16.2.6 |
| Language | TypeScript | ^5 |
| React | React | 19.2.4 |
| Styling | Tailwind CSS | ^4 |
| Build | Webpack (not Turbopack) | via `next dev --webpack` |
| Port | localhost:3004 | `npm run dev` from `uis/backoffice/landing` |
| API | FastAPI backend | `http://localhost:8000/api/v1` |

### CSS Design Tokens (defined in `landing/app/globals.css`)

```css
--hc-brand: #0369a1;
--hc-brand-strong: #0c4a6e;
--hc-surface: #ffffff;
--hc-surface-muted: #f8fafc;
--hc-border: #cbd5e1;
--hc-text: #0f172a;
--hc-text-muted: #475569;
--hc-success: #166534;
--hc-warning: #a16207;
--hc-danger: #b91c1c;
```

No component library (no shadcn, Radix, MUI). Use raw Tailwind classes matching the existing backoffice patterns.

---

## 3. Business Constraints Enforced by the API

These rules are enforced server-side. The frontend must handle the resulting responses correctly but does NOT re-implement the logic — only provides UX guards where specified.

1. **`current_stock` is computed, never stored.** `current_stock = SUM(deliveries) − SUM(consumptions)`. The API returns it in `GET /inventory/products` and `GET /inventory/products/{id}`.
2. **Outbound orders cannot exceed available stock.** The API returns `HTTP 400` with detail: `"Insufficient stock for supply '{name}'. Available: {available}, requested: {quantity}."` The outbound form must display this message inline near the quantity field.
3. **`consumption_type` must be `"clinical_use"` or `"expiry_waste"`.** The API returns a validation error for anything else.
4. **`user_uuid` is set server-side** from the authenticated user's token. The frontend does NOT send `user_uuid` in POST bodies.
5. **All POST `/inventory` endpoints require `Authorization: Bearer <token>`.** The `healthcoreFetch` helper already handles this.

---

## 4. API Contract

Base URL: `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api/v1`).

### `GET /inventory/products`

Returns all medical supplies with computed stock.

**Response:** `MedicalSupplyRead[]`
```json
[
  {
    "id": 1,
    "name": "Nitrile gloves (box of 100)",
    "sku": "HCR-PPE-001",
    "category": "ppe",
    "unit": "box",
    "country": "US",
    "current_stock": 42
  }
]
```

### `GET /inventory/products/{id}`

Returns a single supply with computed stock. Used by the outbound form for reactive stock display.

**Response:** `MedicalSupplyRead` (same shape as above, single object).

### `POST /inventory/orders/inbound`

Log a vendor delivery. Requires auth.

**Request body:**
```json
{
  "supply_id": 1,
  "quantity": 50,
  "vendor_name": "MedLine Industries",
  "clinic_id": 1
}
```

**Response (201):**
```json
{
  "id": 10,
  "supply_id": 1,
  "quantity": 50,
  "vendor_name": "MedLine Industries",
  "clinic_id": 1,
  "created_at": "2026-06-30T10:00:00Z",
  "user_uuid": "abc-123"
}
```

**Error (400/422):** `{ "detail": "..." }`

### `POST /inventory/orders/outbound`

Log a clinical consumption. Requires auth.

**Request body:**
```json
{
  "supply_id": 1,
  "quantity": 5,
  "consumption_type": "clinical_use",
  "clinic_id": 3
}
```

**Response (201):**
```json
{
  "id": 7,
  "supply_id": 1,
  "quantity": 5,
  "consumption_type": "clinical_use",
  "clinic_id": 3,
  "created_at": "2026-06-30T10:30:00Z",
  "user_uuid": "abc-123"
}
```

**Error (400):** `{ "detail": "Insufficient stock for supply 'Nitrile gloves (box of 100)'. Available: 3, requested: 5." }`

### `GET /inventory/orders`

Returns all orders (deliveries + consumptions) sorted by `created_at` descending.

**Response:** `OrderRead[]`
```json
[
  {
    "id": 7,
    "order_type": "outbound",
    "supply_id": 1,
    "supply_name": "Nitrile gloves (box of 100)",
    "quantity": 5,
    "user_uuid": "abc-123",
    "created_at": "2026-06-30T10:30:00Z",
    "vendor_name": null,
    "consumption_type": "clinical_use",
    "clinic_id": 3
  },
  {
    "id": 10,
    "order_type": "inbound",
    "supply_id": 1,
    "supply_name": "Nitrile gloves (box of 100)",
    "quantity": 50,
    "user_uuid": "abc-123",
    "created_at": "2026-06-30T10:00:00Z",
    "vendor_name": "MedLine Industries",
    "consumption_type": null,
    "clinic_id": 1
  }
]
```

---

## 5. Dependencies & Prerequisites

1. **Backend API must be running** at `http://localhost:8000` with seed data loaded. Start from `services/api/`.
2. **The `feature/milestone5` branch** contains the inventory backend. The frontend work builds on top of this branch.
3. **Existing auth system** — login, token storage in `localStorage`, `AuthGuard` component — is already functional. Do not modify it.
4. **`healthcoreFetch`** from `@backoffice/shared/lib/healthcore-api.ts` handles `Authorization` header injection from `localStorage` and 401 redirect. All inventory API calls must go through it.
5. **No new npm dependencies.** Use only what is already in `landing/package.json`.

### Key existing files (read-only references)

| File | Purpose |
|------|---------|
| `shared/lib/healthcore-api.ts` | `healthcoreFetch` — auth header injection, 401 redirect |
| `landing/lib/api.ts` | `apiFetch`, `getStoredToken`, `fetchCurrentUser` — auth utilities |
| `landing/components/auth/auth-guard.tsx` | `<AuthGuard>` — session verification + redirect |
| `landing/app/(protected)/layout.tsx` | Wraps all protected routes in `<AuthGuard>` |
| `landing/components/layout/tool-toolbar.tsx` | `<ToolToolbar>` — "Back to hub" + logout bar |
| `landing/components/layout/landing-footer.tsx` | `<LandingFooter>` — copyright footer |
| `landing/components/layout/healthcore-logo.tsx` | `<HealthcoreLogo>` — SVG logo |
| `landing/components/landing/nav-card.tsx` | `<NavCard>` — card component for hub |
| `landing/lib/nav-apps.ts` | `NAV_APPS` array — hub navigation entries |
| `landing/app/globals.css` | CSS tokens + Tailwind `@source` directives |
| `landing/next.config.ts` | Feature module alias registration |

---

## 6. Development Workflow

```bash
# 1. Install dependencies
cd uis/backoffice/landing && npm install

# 2. Start backend (separate terminal)
cd services/api && uv run uvicorn app.main:app --reload

# 3. Start frontend
cd uis/backoffice/landing && npm run dev

# 4. Verify build
npm run verify   # runs lint + build
```

- Frontend runs on `http://localhost:3004`
- All new files must pass TypeScript strict mode and ESLint
- All components use `"use client"` since they rely on `useState`, `useEffect`, `useSearchParams`, and `localStorage`

---

## 7. Static Data: Clinics and Dropdowns

### Clinic Map (ID → Display Name)

Define in `inventory/lib/constants.ts`. These match `uis/website/lib/clinics.ts`.

| clinic_id | Display Name |
|-----------|-------------|
| 1 | HealthCore Austin Central |
| 2 | HealthCore Austin North |
| 3 | HealthCore San Antonio |
| 4 | HealthCore Miami |
| 5 | HealthCore Orlando |
| 6 | HealthCore Atlanta |

### Vendor Names (for inbound form dropdown)

| Value |
|-------|
| MedLine Industries |
| Cardinal Health UK |
| Bound Tree Medical |

### Consumption Types (for outbound form dropdown)

| Value | Display Label |
|-------|--------------|
| `clinical_use` | Clinical Use |
| `expiry_waste` | Expiry / Waste |

### Supply Categories (for display labels)

| Value | Display Label |
|-------|--------------|
| `ppe` | PPE |
| `wound_care` | Wound Care |
| `diagnostics` | Diagnostics |
| `medications` | Medications |
| `consumables` | Consumables |

---

## 8. File Structure

### New feature module: `uis/backoffice/inventory/`

```
uis/backoffice/inventory/
├── lib/
│   ├── inventory-api.ts       # Centralized API calls using healthcoreFetch
│   └── constants.ts           # Clinic map, vendor list, consumption types, category labels
├── components/
│   ├── inventory-landing.tsx   # Landing page with hero + nav cards
│   ├── products-table.tsx      # Product list with stock indicators
│   ├── inbound-order-form.tsx  # Inbound delivery form
│   ├── outbound-order-form.tsx # Outbound consumption form with reactive stock
│   └── orders-table.tsx        # Read-only order history table
└── types/
    └── inventory.ts            # TypeScript types matching API schemas
```

### New route pages: `uis/backoffice/landing/app/(protected)/inventory/`

```
landing/app/(protected)/inventory/
├── layout.tsx          # ToolToolbar + footer wrapper
├── page.tsx            # Inventory landing (hero + nav cards)
├── products/
│   └── page.tsx        # Products list page
└── orders/
    ├── page.tsx        # Order history page
    ├── inbound/
    │   └── page.tsx    # Inbound order form page
    └── outbound/
        └── page.tsx    # Outbound order form page
```

---

## 9. Configuration Changes

### 9.1 Register alias in `landing/next.config.ts`

Add to the variable declarations:

```ts
const inventory = path.join(landingDir, "../inventory");
```

Add to the `featureAliases` object:

```ts
"@backoffice/inventory": inventory,
```

### 9.2 Add Tailwind source in `landing/app/globals.css`

Add alongside the other `@source` directives:

```css
@source "../../inventory/**/*";
```

### 9.3 Add nav card in `landing/lib/nav-apps.ts`

Add to the `NAV_APPS` array:

```ts
{
  title: "Inventory Management",
  description: "Track medical supply stock, deliveries, and clinical consumption",
  url: "/inventory",
  protected: true,
},
```

---

## 10. Implementation Details

### 10.1 TypeScript Types — `inventory/types/inventory.ts`

Define types matching the API response schemas exactly:

```ts
export type MedicalSupply = {
  id: number;
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
  current_stock: number;
};

export type SupplyDeliveryCreate = {
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
};

export type SupplyConsumptionCreate = {
  supply_id: number;
  quantity: number;
  consumption_type: string;
  clinic_id: number;
};

export type OrderRead = {
  id: number;
  order_type: "inbound" | "outbound";
  supply_id: number;
  supply_name: string;
  quantity: number;
  user_uuid: string;
  created_at: string;
  vendor_name: string | null;
  consumption_type: string | null;
  clinic_id: number;
};
```

### 10.2 API Layer — `inventory/lib/inventory-api.ts`

- Import `healthcoreFetch` from `@backoffice/shared/lib/healthcore-api`.
- Create a wrapper `inventoryFetch<T>(path, init?)` that:
  - Calls `healthcoreFetch(path, init)`
  - On non-OK response: parses JSON body, extracts `detail` (or `message`, or falls back to `statusText`), throws `Error(detail)`
  - On success: returns parsed JSON as `T`
- Export these functions:
  - `listProducts()` → `GET /inventory/products`
  - `getProduct(id: number)` → `GET /inventory/products/{id}`
  - `createInboundOrder(body: SupplyDeliveryCreate)` → `POST /inventory/orders/inbound`
  - `createOutboundOrder(body: SupplyConsumptionCreate)` → `POST /inventory/orders/outbound`
  - `listOrders()` → `GET /inventory/orders`

**No component may call `fetch` or `healthcoreFetch` directly.** All inventory API access goes through this module.

### 10.3 Constants — `inventory/lib/constants.ts`

```ts
export const CLINICS: { id: number; name: string }[] = [
  { id: 1, name: "HealthCore Austin Central" },
  { id: 2, name: "HealthCore Austin North" },
  { id: 3, name: "HealthCore San Antonio" },
  { id: 4, name: "HealthCore Miami" },
  { id: 5, name: "HealthCore Orlando" },
  { id: 6, name: "HealthCore Atlanta" },
];

export const VENDORS = [
  "MedLine Industries",
  "Cardinal Health UK",
  "Bound Tree Medical",
];

export const CONSUMPTION_TYPES: { value: string; label: string }[] = [
  { value: "clinical_use", label: "Clinical Use" },
  { value: "expiry_waste", label: "Expiry / Waste" },
];

export const CATEGORY_LABELS: Record<string, string> = {
  ppe: "PPE",
  wound_care: "Wound Care",
  diagnostics: "Diagnostics",
  medications: "Medications",
  consumables: "Consumables",
};
```

### 10.4 Inventory Layout — `landing/app/(protected)/inventory/layout.tsx`

Follow the pattern from `supplier-directory/layout.tsx`:

- Render `<ToolToolbar />` at the top (import from `@/components/layout/tool-toolbar`)
- Render `{children}` below
- Render `<LandingFooter />` at the bottom (import from `@/components/layout/landing-footer`)

### 10.5 Inventory Landing Page — `/inventory`

**Route:** `landing/app/(protected)/inventory/page.tsx`
**Component:** `inventory/components/inventory-landing.tsx`

Styled like the main backoffice landing (`components/landing/landing-page.tsx`):

**Hero section** — same gradient style as `landing-hero.tsx`:
- `rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10`
- Include `<HealthcoreLogo />` (import from `@/components/layout/healthcore-logo`)
- Title: **"Medical Supply Inventory"**
- Subtitle: "Track stock levels, log deliveries, and record clinical consumption across all HealthCore clinics."

**Nav cards grid** — 4 cards using the same card style as `nav-card.tsx`:
- Card class: `rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-300 hover:shadow-md`
- Grid: `grid gap-4 sm:grid-cols-2`

| Card Title | Description | Link |
|-----------|-------------|------|
| Supply Stock | View all medical supplies and current stock levels | `/inventory/products` |
| Log Delivery | Register an inbound supply delivery from a vendor | `/inventory/orders/inbound` |
| Log Consumption | Record clinical use or waste of medical supplies | `/inventory/orders/outbound` |
| Order History | View all supply deliveries and consumptions | `/inventory/orders` |

### 10.6 Products Page — `/inventory/products`

**Route:** `landing/app/(protected)/inventory/products/page.tsx`
**Component:** `inventory/components/products-table.tsx`

- Fetch `listProducts()` on mount. Show a loading state while fetching.
- Display a table with columns: **Name**, **SKU**, **Category**, **Unit**, **Country**, **Current Stock**.
- **Stock level indicators** — color-code the `current_stock` cell:
  - `current_stock <= 5` → red background/text (low/critical)
  - `current_stock <= 15` → amber/yellow background/text (warning)
  - `current_stock > 15` → green background/text (healthy)
- **Category display**: Map raw values to labels using `CATEGORY_LABELS` (e.g., `ppe` → `PPE`).
- **Action links per row**: Two clearly labelled links/buttons:
  - "Log Delivery" → navigates to `/inventory/orders/inbound?supplyId={id}`
  - "Log Consumption" → navigates to `/inventory/orders/outbound?supplyId={id}`
- Handle fetch errors by displaying the error message in a visible banner.

### 10.7 Inbound Order Form — `/inventory/orders/inbound`

**Route:** `landing/app/(protected)/inventory/orders/inbound/page.tsx`
**Component:** `inventory/components/inbound-order-form.tsx`

- Fetch `listProducts()` on mount to populate the product dropdown.

**Form fields (all required):**

| Field | Input Type | Options/Behavior |
|-------|-----------|-----------------|
| Medical Supply | `<select>` dropdown | Products listed by `name`. Value = `supply_id`. If `supplyId` query param present, pre-select it. |
| Quantity | `<input type="number" min="1">` | Positive integer |
| Vendor | `<select>` dropdown | "MedLine Industries", "Cardinal Health UK", "Bound Tree Medical" |
| Clinic | `<select>` dropdown | 6 clinics displayed by name, value = `clinic_id` (1–6) |

**On submit:** Call `createInboundOrder(body)`.
- **Success (201):** Clear the form. Show a green confirmation banner (e.g., "Delivery logged successfully").
- **Error (400/422/500):** Display the API error `detail` message in a red banner near the form. Do not clear the form on error.

Disable the submit button while the request is in flight.

### 10.8 Outbound Order Form — `/inventory/orders/outbound`

**Route:** `landing/app/(protected)/inventory/orders/outbound/page.tsx`
**Component:** `inventory/components/outbound-order-form.tsx`

- Fetch `listProducts()` on mount to populate the product dropdown.

**Form fields (all required):**

| Field | Input Type | Options/Behavior |
|-------|-----------|-----------------|
| Medical Supply | `<select>` dropdown | Products listed by `name`. Value = `supply_id`. If `supplyId` query param present, pre-select it. |
| Quantity | `<input type="number" min="1">` | Positive integer |
| Consumption Type | `<select>` dropdown | "Clinical Use" (`clinical_use`), "Expiry / Waste" (`expiry_waste`) |
| Clinic | `<select>` dropdown | 6 clinics displayed by name, value = `clinic_id` (1–6) |

**Reactive stock display:**
- When the user selects a product, call `getProduct(id)` and display `current_stock` prominently near the quantity field (e.g., "Available stock: 42 boxes").
- This must update immediately when the product selection changes.

**Client-side quantity warning:**
- If the entered quantity exceeds the displayed `current_stock`, show an amber/yellow warning near the quantity field (e.g., "Warning: quantity exceeds available stock (42)").
- This is a UX guard only — do not prevent submission.

**On submit:** Call `createOutboundOrder(body)`.
- **Success (201):** Clear the form. Show a green confirmation banner (e.g., "Consumption logged successfully").
- **Error (400):** Display the API `detail` message (e.g., "Insufficient stock for supply 'Nitrile gloves (box of 100)'. Available: 3, requested: 5.") in a red error element **inline near the quantity field**. Do not clear the form.
- **Error (422/500):** Display error in a red banner near the form.

Disable the submit button while the request is in flight.

### 10.9 Orders History Page — `/inventory/orders`

**Route:** `landing/app/(protected)/inventory/orders/page.tsx`
**Component:** `inventory/components/orders-table.tsx`

- Fetch `listOrders()` on mount. Show a loading state while fetching.
- Display a table with columns: **Supply Name**, **Quantity**, **Type**, **Clinic**, **Date**, **User UUID**.
- **Visual distinction for order type:**
  - Inbound → green badge/label (e.g., "Delivery" with green background)
  - Outbound → red/amber badge/label (e.g., "Consumption" with red background)
- **Date formatting:** Display `created_at` in a human-readable format (e.g., `Jun 30, 2026 10:30 AM`).
- **Clinic display:** Map `clinic_id` to clinic name using `CLINICS` constant.
- **Type-specific details:** Show `vendor_name` for inbound orders, `consumption_type` (formatted via `CONSUMPTION_TYPES`) for outbound orders — either in the table or as a secondary line.
- **Read-only.** No edit or delete actions.
- Handle fetch errors by displaying the error message in a visible banner.

### 10.10 Route Protection

All inventory pages live under `landing/app/(protected)/inventory/`, which is inside the `(protected)` route group. The existing `(protected)/layout.tsx` wraps all children in `<AuthGuard>`. **No additional auth code is needed.** Unauthenticated users are automatically redirected to `/login`.

---

## 11. Styling Guide

Match the existing backoffice visual language. Reference these patterns:

| Pattern | Tailwind Classes / Reference |
|---------|------------------------------|
| Page container | `mx-auto w-full max-w-5xl px-4 py-8 sm:px-6` |
| Hero section | `rounded-2xl bg-gradient-to-r from-sky-900 to-teal-700 p-6 text-center text-white shadow-xl md:p-10` |
| Card | `rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-sky-300 hover:shadow-md` |
| Toolbar | `<ToolToolbar />` component |
| Footer | `<LandingFooter />` component |
| Primary button | `rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-800` |
| Secondary button | `rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50` |
| Form label | `text-sm font-medium text-slate-700` |
| Form input/select | `w-full rounded-lg border border-slate-300 px-3 py-2 text-sm` with focus ring |
| Error banner | `rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800` |
| Success banner | `rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-800` |
| Warning banner | `rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800` |
| Table header | `text-left text-xs font-semibold uppercase tracking-wide text-slate-500` |
| Table row | `border-b border-slate-100` with `hover:bg-slate-50` |
| Page heading | `text-xl font-bold text-slate-900` |
| Stock badge (low) | `rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800` |
| Stock badge (warning) | `rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800` |
| Stock badge (healthy) | `rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800` |
| Order type badge (inbound) | `rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800` |
| Order type badge (outbound) | `rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800` |

---

## 12. Acceptance Checklist

### Configuration
- [ ] `@backoffice/inventory` alias registered in `next.config.ts`
- [ ] `@source "../../inventory/**/*"` added to `globals.css`
- [ ] Inventory card added to `NAV_APPS` in `nav-apps.ts`

### API Layer
- [ ] `inventory/lib/inventory-api.ts` exists and uses `healthcoreFetch` — no raw `fetch` in components
- [ ] Error extraction: non-OK responses throw `Error` with the API `detail` message

### Inventory Landing (`/inventory`)
- [ ] Hero section with logo, title, subtitle — same gradient as backoffice landing
- [ ] 4 nav cards linking to products, inbound, outbound, order history
- [ ] Header (ToolToolbar) and footer (LandingFooter) present

### Products Page (`/inventory/products`)
- [ ] Loads live data from `GET /inventory/products`
- [ ] Shows `current_stock` with color-coded indicators (red ≤5, amber ≤15, green >15)
- [ ] Category values displayed as formatted labels
- [ ] Action links per row: "Log Delivery" and "Log Consumption" with `supplyId` query param

### Inbound Form (`/inventory/orders/inbound`)
- [ ] 4 fields: product dropdown (by name), quantity, vendor dropdown, clinic dropdown (by name)
- [ ] Pre-selects product if `supplyId` query param present
- [ ] Clears form + shows green confirmation on success
- [ ] Shows API error message in red banner on failure
- [ ] Submit button disabled during request

### Outbound Form (`/inventory/orders/outbound`)
- [ ] 4 fields: product dropdown (by name), quantity, consumption type dropdown, clinic dropdown (by name)
- [ ] Pre-selects product if `supplyId` query param present
- [ ] Shows reactive `current_stock` when product selection changes (via `GET /inventory/products/{id}`)
- [ ] Shows client-side amber warning when quantity > available stock
- [ ] `400` response shows API `detail` message inline near quantity field
- [ ] Clears form + shows green confirmation on success
- [ ] Submit button disabled during request

### Orders History (`/inventory/orders`)
- [ ] Shows all orders with: supply name, quantity, type badge, clinic name, date, user_uuid
- [ ] Inbound/outbound visually distinguished (green "Delivery" / red "Consumption" badges)
- [ ] Shows vendor_name for inbound, consumption_type for outbound
- [ ] Dates formatted human-readable
- [ ] Read-only — no edit/delete actions

### Auth & Build
- [ ] All pages under `(protected)` route group — unauthenticated users redirected to `/login`
- [ ] `npm run verify` passes (lint + build)
- [ ] UI labels use HealthCore domain language: "Medical Supply", "Delivery", "Consumption"

---

## 13. What NOT to Change

- Do NOT modify `shared/lib/healthcore-api.ts`
- Do NOT modify `landing/lib/api.ts` or `landing/components/auth/auth-guard.tsx`
- Do NOT modify any existing feature module (`talent-tracker`, `backoffice_functions`, `supplier-directory`)
- Do NOT add npm dependencies
- Do NOT create a parallel auth system
- Do NOT call `fetch` directly from components — all API access through `inventory-api.ts`
