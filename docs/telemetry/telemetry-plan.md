# HealthCore — Telemetry Plan

**Document:** `docs/telemetry/telemetry-plan.md`
**Author:** HealthCore Digital (Technology Team)
**Status:** Design — ready for implementation
**Schema version:** `1.0.0`
**Companion file:** `docs/telemetry/event-schemas.json`
**Context source:** `docs/telemetry/CONTEXT-healthcore.md`

---

## 1. Executive Summary

HealthCore's inventory management system — tracking `MedicalSupply`, `SupplyDelivery`, and `DispensingOrder` entities across 12 clinics in the US (Texas, Florida, Georgia) and UK (London, Manchester) — is operational but opaque. Dr. Marcus Reid (Director of Clinical Operations) and Claire Whitfield (Chief Compliance Officer) have raised questions the system cannot answer today:

- How often do clinics hit zero stock on critical supplies?
- Which clinics generate the most emergency dispensing orders, and is that trending up?
- Are operators attempting to bypass the order-based stock modification rule?
- How many dispensing attempts fail due to insufficient stock or invalid clinical context?
- When do stock threshold alerts fire most — and are they actionable?

This plan defines 12 telemetry events (6 inventory, 6 backoffice) that answer these questions, structured against HealthCore's three primary KPIs. Each event includes a standard envelope, a property allowlist, PII handling notes, and a stream-vs-batch justification grounded in clinical urgency. The companion `event-schemas.json` provides JSON Schema draft-07 definitions with a root `oneOf` for validation by `event_type`. KPI and domain grounding is documented in §2 against `CONTEXT-healthcore.md`.

**Non-negotiable business rule:** Stock cannot be modified directly. All stock changes flow through `SupplyDelivery` (inbound) or `DispensingOrder` (outbound), traceable to an authenticated user via opaque TinyDB UUID.

---

## 2. Context & Data Basis

This plan is grounded in `docs/telemetry/CONTEXT-healthcore.md` — the assigned company context for HealthCore Digital's telemetry phase. The following facts from that document directly justify the KPIs, events, and compliance constraints below.

| Context fact | Source | How the plan uses it |
| ------------ | ------ | -------------------- |
| **12 clinics** across US (Texas, Florida, Georgia) and UK (London, Manchester) | CONTEXT §Your Company | Segmentation dimensions for all clinic-origin events (`clinicId`, `jurisdiction`) |
| **Canonical entities:** `MedicalSupply`, `SupplyDelivery`, `DispensingOrder` | CONTEXT §Your Inventory System Entities | Event names, property fields, and flow diagram entity references |
| **`MedicalSupply.category`** includes `ppe`, `consumable`, etc. | CONTEXT entity fields | KPI 1 filters on PPE and high-priority consumables |
| **`DispensingOrder.clinical_context`** enum includes `emergency` | CONTEXT entity fields | KPI 2 and stream event `emergency_dispensing_flagged` |
| **Dr. Reid and Claire Whitfield** cannot answer stock, emergency, and compliance questions today | CONTEXT §Your Company | Executive summary problem statements and backoffice auth events |
| **Three assigned KPIs** with definitions and business decisions | CONTEXT §Your 3 KPIs | Section 3 maps each KPI to telemetry events (see KPI table below) |
| **Jurisdiction field mandatory** on clinic operations (`us` / `uk`) | CONTEXT §Business Constraints | Required on every clinic-origin event property allowlist |
| **No PII; emergency + PPE threshold events are stream** | CONTEXT §Business Constraints | Envelope PII policy, stream/batch justifications, §9 exclusions |
| **Audit immutability + `schemaVersion`** | CONTEXT §Business Constraints | Envelope design (§6) and 7-year retention in §9 |

### KPI targets and operational thresholds

| KPI | Target in this plan | Basis |
| --- | ------------------- | ----- |
| KPI 1 — Critical supply availability | ≥ 95%; below triggers emergency procurement | **From CONTEXT:** "trigger emergency procurement when availability drops below 95%" |
| KPI 2 — Emergency dispensing frequency | Sustained >20% increase over 4-week rolling average triggers stock review | **Operational default** — CONTEXT defines weekly per-clinic measurement but not a numeric alert threshold; 20% is a reasonable ops-team starting point pending baseline data |
| KPI 3 — Stock-out incident rate | Zero stock-outs on PPE/critical consumables; any stock-out is stream-alert severity | **Derived from CONTEXT:** KPI 3 definition + constraint that PPE stock-outs "are not a batch-reporting problem" |

---

## 3. KPI Analysis

### KPI 1: Critical Supply Availability Rate

- **Definition:** Percentage of time that PPE and high-priority consumables remain above `min_stock_threshold` across all clinics.
- **Data components:** `MedicalSupply.current_stock`, `MedicalSupply.min_stock_threshold`, `MedicalSupply.category` (filtered to `ppe` and `consumable`), time-series of stock level changes.
- **System touchpoints:** `POST /inventory/dispensing-orders` (each dispensing reduces stock), `POST /inventory/supply-deliveries` (each delivery increases stock), the threshold comparison logic that fires after each dispensing.
- **Context link:** Per CONTEXT §Your 3 KPIs — "Prevent clinical care disruption; trigger emergency procurement when availability drops below 95%."
- **Telemetry need:** The system currently enforces thresholds but does not record *when* a threshold was breached, *how long* stock stayed below threshold, or *which clinic/jurisdiction* is most affected. Events `stock_threshold_triggered` and `dispensing_order_created` feed this KPI directly.
- **Target:** ≥ 95% availability (CONTEXT-assigned threshold). Below 95% triggers emergency procurement.

### KPI 2: Emergency Dispensing Frequency

- **Definition:** Number of `DispensingOrder` records with `clinical_context = emergency` per clinic per week.
- **Data components:** `DispensingOrder.clinical_context`, `DispensingOrder.clinic_id`, `DispensingOrder.created_at`, weekly aggregation.
- **System touchpoints:** `POST /inventory/dispensing-orders` where `clinical_context = emergency`.
- **Context link:** Per CONTEXT §Your 3 KPIs — "Identify clinics with recurring emergency supply needs; adjust standard stock levels proactively."
- **Telemetry need:** The database stores emergency orders but has no alerting or trending layer. A spike in emergency dispensing at a specific clinic signals that standard stock levels are inadequate for that clinic's patient volume. Event `emergency_dispensing_flagged` feeds this KPI as a stream event; `dispensing_order_created` provides the batch denominator for rate calculation.
- **Target:** Clinic-specific baseline (CONTEXT). Sustained increase of >20% over 4-week rolling average triggers stock level review *(operational default — see §2)*.

### KPI 3: Stock-Out Incident Rate

- **Definition:** Number of times any supply's `current_stock` reaches zero, segmented by `clinic_id` and `jurisdiction`.
- **Data components:** `MedicalSupply.current_stock` (= 0), `MedicalSupply.clinic_id`, `MedicalSupply.jurisdiction`, timestamp of zero-crossing.
- **System touchpoints:** `POST /inventory/dispensing-orders` (the action that can reduce stock to zero), threshold comparison logic.
- **Context link:** Per CONTEXT §Your 3 KPIs — "Compare US vs. UK supply chain reliability; inform vendor performance reviews." Per CONTEXT §Business Constraints — PPE/critical threshold events require stream processing.
- **Telemetry need:** A stock-out is more severe than a threshold breach — it means clinical care may be disrupted *now*. The system currently blocks orders when stock is insufficient (`dispensing_order_failed`) but does not record the zero-stock event distinctly from a generic threshold. Event `stock_threshold_triggered` with `current_stock = 0` captures this; filtering by `jurisdiction` enables the US-vs-UK supply chain reliability comparison Dr. Okonkwo requested.
- **Target:** Zero stock-outs on PPE/critical consumables. Any stock-out triggers immediate stream alert.

---

## 4. Inventory Flow Mapping and Instrumentation Points

The diagram below traces the inventory management flow from authenticated access through order completion, with numbered instrumentation points.

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUTHENTICATED USER (clinic manager / administrator)                │
│  Session established → sessionId, userId (TinyDB UUID)             │
└────────────────┬────────────────────────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │ User navigates  │
        │ to inventory    │──────────────────────────────────────────┐
        │ section         │                                         │
        └────────┬────────┘                                         │
                 │                                                  │
    ┌────────────▼────────────────┐                                 │
    │ Views supply list for       │ ◀── ④ supply_list_viewed        │
    │ a clinic (filtered by       │                                 │
    │ clinic_id / jurisdiction)   │                                 │
    └────────────┬────────────────┘                                 │
                 │                                                  │
     ┌───────────┴───────────────┐                                  │
     ▼                           ▼                                  │
┌─────────────┐          ┌──────────────┐       ┌──────────────────┐│
│ INBOUND     │          │ OUTBOUND     │       │ DIRECT EDIT      ││
│ (Delivery)  │          │ (Dispensing)  │       │ (Rejected)       ││
└──────┬──────┘          └──────┬───────┘       └──────┬───────────┘│
       │                        │                      │            │
       ▼                        ▼                      ▼            │
 Validate delivery       Validate order         API intercepts  ③  │
 fields                  fields                 direct PUT/PATCH    │
       │                        │               on stock field      │
       │                   ┌────┴────┐          → direct_stock_     │
       │                   │ Valid?  │            edit_rejected      │
       │                   └────┬────┘                              │
       │                 yes/   \no                                 │
       ▼                 ▼       ▼                                  │
 ① supply_delivery   ② dispensing_order   ⑤ dispensing_order        │
   _created             _created             _failed                │
       │                    │                                       │
       │                    ▼                                       │
       │         ┌──────────────────┐                               │
       │         │ Post-dispensing   │                               │
       │         │ stock check       │                               │
       │         └────────┬─────────┘                               │
       │           ┌──────┴───────┐                                 │
       │           ▼              ▼                                 │
       │    stock > threshold  stock ≤ threshold                    │
       │    (no event)         ⑥ stock_threshold_triggered          │
       │                          │                                 │
       │                    ┌─────┴──────────┐                      │
       │                    ▼                ▼                      │
       │              stock = 0        stock > 0                    │
       │           (stock-out alert) (low-stock alert)              │
       │                                                            │
       │         ┌──────────────────┐                               │
       │         │ clinical_context  │                               │
       │         │ = emergency?      │                               │
       │         └────────┬─────────┘                               │
       │              yes/   \no                                    │
       │              ▼       (no extra event)                      │
       │    ⑦ emergency_dispensing_flagged                           │
       │                                                            │
       └────────────────────────────────────────────────────────────┘
```

### Instrumentation Points (Inventory Module — minimum 5 required)

| #   | Event                          | Trigger                                                                                      | KPI fed       |
| --- | ------------------------------ | -------------------------------------------------------------------------------------------- | ------------- |
| ①   | `supply_delivery_created`      | A `SupplyDelivery` is successfully registered, increasing stock                              | KPI 1, KPI 3  |
| ②   | `dispensing_order_created`     | A `DispensingOrder` is successfully registered, reducing stock                               | KPI 1, KPI 2  |
| ③   | `direct_stock_edit_rejected`   | A request to modify `MedicalSupply.current_stock` directly (outside an order) is blocked     | Policy signal |
| ④   | `supply_list_viewed`           | User opens the medical supply stock list for a clinic (moved here from backoffice — it's part of the inventory flow) | Navigation    |
| ⑤   | `dispensing_order_failed`      | A `DispensingOrder` is rejected due to insufficient stock, invalid `clinical_context`, or validation error | KPI 1, KPI 3  |
| ⑥   | `stock_threshold_triggered`    | A supply's `current_stock` falls to or below `min_stock_threshold` after a dispensing        | KPI 1, KPI 3  |
| ⑦   | `emergency_dispensing_flagged` | A `DispensingOrder` with `clinical_context = emergency` is created                           | KPI 2         |

> **Note:** `supply_list_viewed` (④) lives at the boundary of inventory and navigation. It is counted here as an inventory instrumentation point because it occurs within the inventory management flow, but it also appears in the backoffice section for completeness.

**Golden rule test:**
- "We capture `supply_delivery_created` because we need to know **the volume, frequency, and vendor distribution of inbound supply deliveries per clinic**, which allows us to make the decision **whether current vendor contracts meet restocking needs and whether delivery frequency should be adjusted for specific clinics or supply categories**."
- "We capture `dispensing_order_created` because we need to know **the consumption rate of medical supplies per clinic, per category, and per clinical context**, which allows us to make the decision **whether to adjust standard stock levels, modify reorder points, or flag clinics with unusually high consumption**."
- "We capture `stock_threshold_triggered` because we need to know **when a supply's stock falls to or below its minimum threshold, especially for PPE and critical consumables**, which allows us to make the decision **whether to trigger emergency procurement, redistribute stock between clinics, or escalate to Dr. Reid's operations team for immediate action**."
- "We capture `direct_stock_edit_rejected` because we need to know **how often operators attempt to bypass the order-based stock modification rule by directly editing supply quantities**, which allows us to make the decision **whether to add UX guardrails that better guide operators toward the SupplyDelivery/DispensingOrder workflow, or whether targeted training is needed at specific clinics**."
- "We capture `dispensing_order_failed` because we need to know **the frequency and types of dispensing failures — insufficient stock, invalid clinical context, validation errors — and whether they cluster at specific clinics**, which allows us to make the decision **whether to adjust stock levels, fix UI validation to prevent invalid submissions, or investigate systemic data quality issues**."
- "We capture `emergency_dispensing_flagged` because we need to know **which clinics are experiencing spikes in emergency supply usage and whether those spikes are sustained or episodic**, which allows us to make the decision **whether to increase standard stock levels at those clinics, negotiate faster delivery schedules with vendors, or investigate whether clinical workflows are routing too many orders through the emergency path unnecessarily**."

---

## 5. Backoffice Opportunities (Beyond Inventory)

### Opportunity 1: Authentication Events

| Event                    | Trigger                                                       |
| ------------------------ | ------------------------------------------------------------- |
| `user_login_succeeded`   | Successful login by a clinic manager or administrator         |
| `user_login_failed`      | Failed login attempt (wrong credentials or expired session)   |
| `session_expired`        | User session timed out and was invalidated                    |

**Why it matters:** Dr. Reid needs to know whether clinic staff are experiencing access friction — repeated login failures could indicate password fatigue, credential management issues, or (worst case) unauthorized access attempts. Claire Whitfield requires login audit trails for HIPAA/UK GDPR compliance. A burst of `user_login_failed` events for the same `userId` or clinic within a short window is a security signal. **IP-based brute-force detection is handled by the authentication layer's security logs, not telemetry** — telemetry records failure patterns via `attemptNumber` and escalates to stream at 5+ failures in 10 minutes.

**Golden rule test:**
- "We capture `user_login_succeeded` because we need to know **the volume and timing of successful logins per clinic and jurisdiction**, which allows us to make the decision **whether system usage aligns with staffing schedules and whether to adjust infrastructure capacity for peak usage periods**."
- "We capture `user_login_failed` because we need to know **how often operators fail to authenticate and whether failures cluster around specific clinics or times**, which allows us to make the decision **whether to implement SSO, adjust session timeouts, or flag potential unauthorized access for investigation**."
- "We capture `session_expired` because we need to know **how frequently sessions time out during active use**, which allows us to make the decision **whether current timeout settings are appropriate for clinical workflows or are causing operators to lose work in progress**."

### Opportunity 2: Navigation and Abandoned Flows

| Event                      | Trigger                                                           |
| -------------------------- | ----------------------------------------------------------------- |
| `supply_list_viewed`       | User opens the medical supply stock list for a clinic             |
| `dispensing_form_abandoned` | User starts but does not complete a `DispensingOrder` form        |
| `clinic_filter_applied`    | User filters the supply view by a specific clinic or jurisdiction |

**Why it matters:** If operators frequently start a dispensing form and abandon it, the UI may have usability issues — confusing field labels, unclear `clinical_context` options, or missing information that forces the operator to leave and come back. `clinic_filter_applied` reveals which clinics and jurisdictions operators monitor most frequently, informing dashboard prioritization and default view configuration.

**Golden rule test:**
- "We capture `supply_list_viewed` because we need to know **which clinic supply lists operators access most frequently and how often**, which allows us to make the decision **whether to set personalized default views, pre-load frequently accessed clinic data, or build a priority dashboard for high-traffic locations**."
- "We capture `dispensing_form_abandoned` because we need to know **how often operators start but fail to complete dispensing orders and at what step they drop off**, which allows us to make the decision **whether to simplify the dispensing form, add field-level help text, or pre-fill default values based on clinic context**."
- "We capture `clinic_filter_applied` because we need to know **which clinics and jurisdictions operators monitor most frequently**, which allows us to make the decision **whether to set personalized default views or build a clinic-specific dashboard for high-traffic locations**."

### Backoffice Instrumentation Points

| Event                       | Layer    | Emit when                                                                 | `sessionId` / `requestId` source                                      |
| --------------------------- | -------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `user_login_succeeded`      | Backend  | After `POST /api/v1/auth/login` returns a successful authentication     | `requestId` from API middleware; `sessionId` from new session token     |
| `user_login_failed`         | Backend  | After `POST /api/v1/auth/login` rejects credentials or session            | `requestId` from failed login request; `sessionId` from client if any |
| `session_expired`           | Backend  | When session middleware invalidates a timed-out session                   | `requestId` from the request that detected expiry; `sessionId` of expired session |
| `supply_list_viewed`        | Frontend | On supply-list route enter / component mount (see also §4 point ④)        | `sessionId` from auth context; `requestId` generated per page view      |
| `dispensing_form_abandoned` | Frontend | On form unmount or route change when the dispensing form is dirty and not submitted | `sessionId` from auth context; `requestId` per form session     |
| `clinic_filter_applied`     | Frontend | On clinic/jurisdiction filter change, after §8 debounce (5 seconds)       | `sessionId` from auth context; `requestId` per debounced selection    |

> **Inventory events (§4):** Backend inventory events (`supply_delivery_created`, `dispensing_order_created`, etc.) emit from FastAPI business logic after the corresponding `SupplyDelivery` or `DispensingOrder` operation completes. `sessionId` and `requestId` propagate from the authenticated API request. `stock_threshold_triggered` requires a post-dispensing hook comparing `current_stock` to `min_stock_threshold` — this comparison logic is a prerequisite not yet present in all deployments.

---

## 6. Standard Event Envelope

Every telemetry event emitted by HealthCore's system MUST include these mandatory fields. The `properties` object contains event-specific payload restricted to an explicit allowlist — no additional keys are permitted.

| Field           | Type              | Required | Description                                                                                            |
| --------------- | ----------------- | -------- | ------------------------------------------------------------------------------------------------------ |
| `eventId`       | string (UUID v4)  | yes      | Unique identifier for this event instance. Used for idempotency and deduplication.                     |
| `timestamp`     | string (ISO 8601) | yes      | UTC timestamp of when the event occurred. Format: `YYYY-MM-DDTHH:mm:ss.sssZ`.                         |
| `sessionId`     | string            | yes      | Browser or API session identifier. Ties events to a user's session for flow reconstruction.            |
| `userId`        | string            | yes      | Authenticated operator's TinyDB UUID. **Never** a name or email — opaque identifier only.              |
| `event_type`    | string            | yes      | Event name in `entity_action` format (e.g. `dispensing_order_created`). Must match a defined schema.   |
| `schemaVersion` | string            | yes      | Semantic version of this event's schema (e.g. `1.0.0`). Immutable once written — never overwritten.   |
| `requestId`     | string            | yes      | Correlation ID that joins frontend action → API request → backend log for end-to-end tracing.          |
| `properties`    | object            | yes      | Event-specific payload. Only keys declared in the event's allowlist are permitted.                     |

**Envelope correlation fields:**

| Field         | Source                                                                 |
| ------------- | ---------------------------------------------------------------------- |
| `eventId`     | Generate a new UUID v4 per event at emission time                      |
| `timestamp`   | UTC `datetime.now(timezone.utc).isoformat()` at emission time          |
| `userId`      | TinyDB UUID from authenticated user (`created_by` / JWT subject)       |
| `sessionId`   | Browser session token ID or API session identifier from auth middleware |
| `requestId`   | Correlation ID from API middleware (`X-Request-ID` header or equivalent); frontend generates one per user action when no API round-trip occurs |
| `schemaVersion` | Fixed string `"1.0.0"` for this schema release                     |

**Immutability rule:** Once an event is persisted, it MUST NOT be modified or deleted. HealthCore's supply movement events may be subpoenaed as part of a clinical audit. `schemaVersion` enables backward-compatible evolution without breaking audit integrity.

**PII policy:** `userId` is always a TinyDB UUID — never a staff name, email, or badge number. No patient identifiers appear anywhere in telemetry. `DispensingOrder` events tied to clinical procedures use `clinical_context` and `clinic_id` only — never patient names, MRNs, or encounter IDs.

---

## 7. Event Catalog

### 7.1 Inventory Events

---

#### `supply_delivery_created` — BATCH

> "We capture `supply_delivery_created` because we need to know **the volume, frequency, and vendor distribution of inbound supply deliveries per clinic**, which allows us to make the decision **whether current vendor contracts meet restocking needs and whether delivery frequency should be adjusted for specific clinics or supply categories**."

| Property    | Type    | Required | Allowlist | PII | Description                                                         |
| ----------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------- |
| `deliveryId`| string  | yes      | yes       | no  | `SupplyDelivery.id` — the delivery record identifier                |
| `supplyId`  | string  | yes      | yes       | no  | `MedicalSupply.id` — which supply was restocked                     |
| `quantity`  | integer | yes      | yes       | no  | Number of units delivered                                           |
| `vendor`    | string  | yes      | yes       | no  | Vendor name (not PII — corporate entity)                            |
| `clinicId`  | string  | yes      | yes       | no  | Clinic receiving the delivery                                       |
| `jurisdiction` | string | yes   | yes       | no  | `us` or `uk` — mandatory per compliance                            |
| `category`  | string  | yes      | yes       | no  | `MedicalSupply.category` — enables KPI 1 filtering on PPE/critical  |

- **Stream vs batch:** Batch — feeds daily/weekly restocking reports. Supply deliveries are planned events; sub-minute latency adds no clinical value.
- **Sanitization:** None required. No user-identifying fields beyond envelope `userId` (TinyDB UUID). Vendor is a corporate name, not PII.

---

#### `dispensing_order_created` — BATCH

> "We capture `dispensing_order_created` because we need to know **the consumption rate of medical supplies per clinic, per category, and per clinical context**, which allows us to make the decision **whether to adjust standard stock levels, modify reorder points, or flag clinics with unusually high consumption**."

| Property          | Type    | Required | Allowlist | PII | Description                                                         |
| ----------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------- |
| `orderId`         | string  | yes      | yes       | no  | `DispensingOrder.id` — the dispensing record identifier             |
| `supplyId`        | string  | yes      | yes       | no  | `MedicalSupply.id` — which supply was dispensed                     |
| `quantity`        | integer | yes      | yes       | no  | Number of units dispensed                                           |
| `clinicalContext` | string  | yes      | yes       | no  | One of: `procedure`, `routine_care`, `emergency`, `waste_disposal`  |
| `clinicId`        | string  | yes      | yes       | no  | Clinic where dispensing occurred                                    |
| `jurisdiction`    | string  | yes      | yes       | no  | `us` or `uk` — mandatory per compliance                            |
| `category`        | string  | yes      | yes       | no  | `MedicalSupply.category` — supply type for aggregation              |
| `remainingStock`  | integer | yes      | yes       | no  | Stock level after this dispensing — enables trend analysis           |

- **Stream vs batch:** Batch — feeds daily consumption dashboards and weekly KPI reports. Routine dispensing does not require real-time alerting.
- **Sanitization:** None required. `clinicalContext` describes the type of use, not the patient. No patient identifiers.

---

#### `stock_threshold_triggered` — STREAM

> "We capture `stock_threshold_triggered` because we need to know **when a supply's stock falls to or below its minimum threshold, especially for PPE and critical consumables**, which allows us to make the decision **whether to trigger emergency procurement, redistribute stock between clinics, or escalate to Dr. Reid's operations team for immediate action**."

| Property        | Type    | Required | Allowlist | PII | Description                                                        |
| --------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `supplyId`      | string  | yes      | yes       | no  | `MedicalSupply.id` — which supply breached its threshold           |
| `supplyName`    | string  | yes      | yes       | no  | `MedicalSupply.name` — human-readable for alert messages            |
| `currentStock`  | integer | yes      | yes       | no  | Stock level at the moment of the trigger                           |
| `threshold`     | integer | yes      | yes       | no  | The `min_stock_threshold` value that was breached                  |
| `clinicId`      | string  | yes      | yes       | no  | Clinic where the threshold was breached                            |
| `jurisdiction`  | string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `category`      | string  | yes      | yes       | no  | `MedicalSupply.category` — PPE triggers are highest priority        |
| `isStockOut`    | boolean | yes      | yes       | no  | `true` when `currentStock = 0` — distinguishes threshold from stockout for KPI 3 |
| `triggeringOrderId` | string | yes  | yes       | no  | `DispensingOrder.id` that caused this trigger — for audit trail     |

- **Stream vs batch:** **Stream — non-negotiable.** A PPE stock-out directly threatens clinical care. Threshold alerts must reach the operations team within seconds, not in a next-day batch report. `isStockOut = true` events are highest severity.
- **Throttle:** Debounce repeated triggers for the same `supplyId` + `clinicId` within **15 minutes**. A single dispensing may reduce stock through the threshold; subsequent dispensings of the same supply within the debounce window should not re-trigger. The debounce resets if stock is replenished above the threshold and then falls again.
- **Sanitization:** None required. Supply names are product catalog data, not PII.

---

#### `direct_stock_edit_rejected` — BATCH

> "We capture `direct_stock_edit_rejected` because we need to know **how often operators attempt to bypass the order-based stock modification rule by directly editing supply quantities**, which allows us to make the decision **whether to add UX guardrails that better guide operators toward the SupplyDelivery/DispensingOrder workflow, or whether targeted training is needed at specific clinics**."

| Property        | Type    | Required | Allowlist | PII | Description                                                        |
| --------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `supplyId`      | string  | yes      | yes       | no  | `MedicalSupply.id` — which supply they tried to edit               |
| `attemptedField`| string  | yes      | yes       | no  | The field the user attempted to modify (e.g. `current_stock`)      |
| `clinicId`      | string  | yes      | yes       | no  | Clinic where the attempt originated                                |
| `jurisdiction`  | string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `httpMethod`    | string  | yes      | yes       | no  | The HTTP method used (`PUT`, `PATCH`, `DELETE`)                    |
| `endpoint`      | string  | yes      | yes       | no  | The API endpoint that rejected the request                         |

- **Stream vs batch:** Batch — this is a policy enforcement signal, not a clinical emergency. Weekly reports on rejection frequency and distribution across clinics are sufficient.
- **Sanitization:** None required. `userId` in envelope identifies the operator. No additional user-identifying data in properties.

---

#### `dispensing_order_failed` — BATCH (with stream exception)

> "We capture `dispensing_order_failed` because we need to know **the frequency and types of dispensing failures — insufficient stock, invalid clinical context, validation errors — and whether they cluster at specific clinics**, which allows us to make the decision **whether to adjust stock levels, fix UI validation to prevent invalid submissions, or investigate systemic data quality issues**."

| Property          | Type    | Required | Allowlist | PII | Description                                                        |
| ----------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `supplyId`        | string  | yes      | yes       | no  | `MedicalSupply.id` — which supply the failed order targeted        |
| `quantity`        | integer | yes      | yes       | no  | Requested quantity that failed                                     |
| `clinicalContext` | string  | no       | yes       | no  | Raw submitted value if present; omit when missing. When invalid, emit the raw string and set `failureReason = invalid_clinical_context` (do not coerce to a valid enum) |
| `failureReason`   | string  | yes      | yes       | no  | One of: `insufficient_stock`, `invalid_clinical_context`, `validation_error`, `quantity_exceeds_available` |
| `clinicId`        | string  | yes      | yes       | no  | Clinic where the failure occurred                                  |
| `jurisdiction`    | string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `availableStock`  | integer | no       | yes       | no  | Current stock at time of failure (for `insufficient_stock` cases)  |
| `category`        | string  | yes      | yes       | no  | `MedicalSupply.category`                                           |

- **Stream vs batch:** Batch for most failures — daily error pattern reports are sufficient. **Exception:** If `failureReason = insufficient_stock` AND `availableStock = 0`, this is effectively a stock-out encounter and should be treated as stream (same urgency as `stock_threshold_triggered` with `isStockOut = true`).
- **Sanitization:** None required. Error reasons are system-defined constants.

---

#### `emergency_dispensing_flagged` — STREAM

> "We capture `emergency_dispensing_flagged` because we need to know **which clinics are experiencing spikes in emergency supply usage and whether those spikes are sustained or episodic**, which allows us to make the decision **whether to increase standard stock levels at those clinics, negotiate faster delivery schedules with vendors, or investigate whether clinical workflows are routing too many orders through the emergency path unnecessarily**."

| Property          | Type    | Required | Allowlist | PII | Description                                                        |
| ----------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `orderId`         | string  | yes      | yes       | no  | `DispensingOrder.id`                                               |
| `supplyId`        | string  | yes      | yes       | no  | `MedicalSupply.id`                                                 |
| `quantity`        | integer | yes      | yes       | no  | Units dispensed under emergency context                            |
| `clinicId`        | string  | yes      | yes       | no  | Clinic where the emergency dispensing occurred                     |
| `jurisdiction`    | string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `category`        | string  | yes      | yes       | no  | `MedicalSupply.category`                                           |
| `remainingStock`  | integer | yes      | yes       | no  | Stock level after this emergency dispensing                        |

- **Stream vs batch:** **Stream — non-negotiable.** Per HealthCore business constraints, any event with `clinical_context = emergency` must be processed in real time. An emergency dispensing may signal an unfolding clinical situation that requires operations team awareness.
- **Sanitization:** None required. `clinical_context = emergency` is a system-defined enum value, not patient-identifying.

---

### 7.2 Backoffice Events

---

#### `user_login_succeeded` — BATCH

> "We capture `user_login_succeeded` because we need to know **the volume and timing of successful logins per clinic and jurisdiction**, which allows us to make the decision **whether system usage aligns with staffing schedules and whether to adjust infrastructure capacity for peak usage periods**."

| Property      | Type    | Required | Allowlist | PII | Description                                                        |
| ------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `clinicId`    | string  | no       | yes       | no  | Clinic the user is associated with (if determinable at login)      |
| `jurisdiction`| string  | no       | yes       | no  | `us` or `uk` (if determinable at login)                            |
| `loginMethod` | string  | yes      | yes       | no  | Authentication method used: `password`, `sso`, `token_refresh`     |

- **Stream vs batch:** Batch — login volume is an operational planning metric, not a real-time need.
- **Sanitization:** `userId` in the envelope is the TinyDB UUID. No username, email, or IP address in properties.

---

#### `user_login_failed` — BATCH (with stream exception)

> "We capture `user_login_failed` because we need to know **the frequency and pattern of failed login attempts — whether they indicate password fatigue, credential management issues, or potential unauthorized access**, which allows us to make the decision **whether to implement SSO, adjust password policies, or escalate to the security team for investigation**."

| Property        | Type    | Required | Allowlist | PII | Description                                                        |
| --------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `failureReason` | string  | yes      | yes       | no  | One of: `invalid_credentials`, `account_locked`, `expired_session`, `mfa_failed` |
| `attemptNumber` | integer | yes      | yes       | no  | Sequential failure count within the current window (1, 2, 3...)    |
| `clinicId`      | string  | no       | yes       | no  | Clinic association, if determinable                                |
| `jurisdiction`  | string  | no       | yes       | no  | `us` or `uk`, if determinable                                     |

- **Stream vs batch:** Batch for routine daily security reports. **Exception:** If `attemptNumber >= 5` within a 10-minute window for the same `userId`, treat as a stream event and trigger a security alert. This threshold aligns with typical brute-force detection.
- **Sanitization:** **Critical.** The `userId` in the envelope for failed logins is the *attempted* userId, which may not correspond to a real user (e.g., typos). No attempted passwords, IP addresses, or user-agent strings in properties — these are security-sensitive and handled by the authentication layer's own logging.

---

#### `session_expired` — BATCH

> "We capture `session_expired` because we need to know **how frequently user sessions time out during active use and whether expirations correlate with specific workflows or clinics**, which allows us to make the decision **whether current session timeout settings are appropriate for clinical workflows or whether they cause operators to lose work in progress, particularly during complex dispensing orders**."

| Property          | Type    | Required | Allowlist | PII | Description                                                        |
| ----------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `sessionDuration` | integer | yes      | yes       | no  | Session length in seconds before expiration                        |
| `lastActiveSection`| string | no       | yes       | no  | Last backoffice section the user was in when the session expired   |
| `clinicId`        | string  | no       | yes       | no  | Associated clinic                                                  |
| `jurisdiction`    | string  | no       | yes       | no  | `us` or `uk`                                                       |

- **Stream vs batch:** Batch — session timeout analysis is an operational improvement metric, not time-sensitive.
- **Sanitization:** None beyond standard envelope. `lastActiveSection` is a UI route name (e.g. `supply-list`, `dispensing-form`), not PII.

---

#### `supply_list_viewed` — BATCH

> "We capture `supply_list_viewed` because we need to know **which clinic supply lists operators access most frequently and how often**, which allows us to make the decision **whether to set personalized default views, pre-load frequently accessed clinic data, or build a priority dashboard for high-traffic locations**."

| Property      | Type    | Required | Allowlist | PII | Description                                                        |
| ------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `clinicId`    | string  | yes      | yes       | no  | Clinic whose supply list was viewed                                |
| `jurisdiction`| string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `supplyCount` | integer | no       | yes       | no  | Number of supplies rendered in the list (page size indicator)      |

- **Stream vs batch:** Batch — navigation analytics are for weekly usage reports, not real-time.
- **Sanitization:** None required.

---

#### `dispensing_form_abandoned` — BATCH

> "We capture `dispensing_form_abandoned` because we need to know **how often operators start but fail to complete dispensing orders and at what step they drop off**, which allows us to make the decision **whether to simplify the dispensing form, add contextual help, pre-fill default values, or investigate whether the form is surfacing confusing options (e.g., unclear clinical_context choices)**."

| Property          | Type    | Required | Allowlist | PII | Description                                                        |
| ----------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `clinicId`        | string  | yes      | yes       | no  | Clinic where the abandonment occurred                              |
| `jurisdiction`    | string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `lastFieldFilled` | string  | no       | yes       | no  | Last form field the user interacted with before abandoning         |
| `timeSpentSeconds`| integer | no       | yes       | no  | Time in seconds from form open to abandonment                      |
| `fieldsCompleted` | integer | no       | yes       | no  | Count of form fields completed before abandonment                  |

- **Stream vs batch:** Batch — form usability analysis is a product improvement metric reviewed weekly.
- **Throttle:** Debounce within **60 seconds** per `userId` + `sessionId`. If a user opens and closes the form multiple times rapidly (e.g., accidental clicks), only the last abandonment is captured.
- **Sanitization:** `lastFieldFilled` is a field name from the form schema (e.g. `supply_id`, `quantity`, `clinical_context`), not the value the user entered.

---

#### `clinic_filter_applied` — BATCH

> "We capture `clinic_filter_applied` because we need to know **which clinics and jurisdictions operators monitor most frequently and whether usage patterns suggest the default view should be personalized**, which allows us to make the decision **whether to implement user-specific default filters, optimize the clinic selector UX, or build a cross-clinic comparison view for managers who oversee multiple locations**."

| Property        | Type    | Required | Allowlist | PII | Description                                                        |
| --------------- | ------- | -------- | --------- | --- | ------------------------------------------------------------------ |
| `clinicId`      | string  | yes      | yes       | no  | The clinic selected in the filter                                  |
| `jurisdiction`  | string  | yes      | yes       | no  | `us` or `uk`                                                       |
| `previousFilter`| string  | no       | yes       | no  | The previous filter value (to track filter switching patterns)     |
| `section`       | string  | yes      | yes       | no  | UI section where the filter was applied (e.g. `supply-list`, `orders`) |

- **Stream vs batch:** Batch — navigation pattern analytics for weekly product reviews.
- **Throttle:** Debounce within **5 seconds** per `userId` + `sessionId` + `section`. Rapid filter cycling (user clicking through multiple clinics) should emit only the final selection.
- **Sanitization:** None required.

---

## 8. High-Frequency Event Strategy

| Event                       | Expected Frequency            | Strategy                                                                 |
| --------------------------- | ----------------------------- | ------------------------------------------------------------------------ |
| `stock_threshold_triggered` | Burst after large dispensing  | Debounce: same `supplyId` + `clinicId` within 15 minutes                 |
| `dispensing_form_abandoned`  | Multiple per session possible | Debounce: same `userId` + `sessionId` within 60 seconds                  |
| `clinic_filter_applied`     | Rapid cycling possible        | Debounce: same `userId` + `sessionId` + `section` within 5 seconds       |
| `supply_list_viewed`        | Every navigation              | No throttle needed — frequency is bounded by user navigation speed       |
| `user_login_failed`         | Burst on brute-force          | No throttle on event emission, but escalation to stream at 5+ failures in 10 minutes |

All other events fire once per business action (order creation, delivery registration) and do not require throttling.

---

## 9. Risks and Exclusions

### 9.1 Events Discarded

| Candidate considered          | Reason for exclusion                                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------- |
| `supply_updated`              | Generic update events fail the golden-rule test — what hypothesis does "something changed" answer? Updates that matter (stock changes) are already captured through `SupplyDelivery` and `DispensingOrder` events. |
| `report_generated`            | Considered for tracking report usage, but report generation is a read-only action that doesn't feed any of the 3 KPIs. May be added in a future schema version if dashboard usage analytics become a priority. |
| `user_role_changed`           | Access control changes are important but belong in the audit log, not telemetry. The frequency is too low (monthly at most) and the security sensitivity too high for the telemetry pipeline. |

### 9.2 Data Not Captured — Privacy and Compliance

| Data element             | Reason not captured                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| **Patient identifiers**  | HIPAA (US) and UK GDPR prohibit linking telemetry to specific patients. `DispensingOrder` events use `clinical_context` and `clinic_id` only — never patient names, MRNs, encounter IDs, or dates of birth. |
| **Staff names/emails**   | `userId` is always a TinyDB UUID. Staff directory information is managed in the HR system, not telemetry. Join-on-demand from a separate, access-controlled staff directory if name resolution is needed for reports. |
| **IP addresses**         | Captured by the authentication layer's security logs, not telemetry. Including IP in telemetry would create a PII data store with no clear KPI benefit and additional GDPR exposure. |
| **User-agent strings**   | Low signal-to-noise ratio for clinical operations KPIs. Browser/device analytics may be added in a future version if UX optimization becomes a priority. |
| **Attempted passwords**  | Never captured anywhere in the telemetry pipeline. `user_login_failed` records the failure reason, never the credential. |
| **Full request bodies**  | API request/response payloads are logged by the API layer, not telemetry. Properties contain only the allowlisted fields relevant to the business hypothesis. |

### 9.3 Cost and Signal Considerations

- **Event volume estimate:** With 12 clinics, ~50 operators, and average 200 dispensing orders/day across all clinics, the expected daily event volume is approximately 500–1,000 events/day. This is well within batch processing capacity and does not require sampling or data retention limits in the initial deployment.
- **Stream cost:** Only 3 event types are designated stream (`stock_threshold_triggered`, `emergency_dispensing_flagged`, and escalated `dispensing_order_failed` / `user_login_failed`). Stream infrastructure costs are contained by the debounce strategy and the low frequency of genuine threshold/emergency events.
- **Retention policy:** All events are retained for **7 years** minimum to comply with HealthCore's clinical audit requirements. Events are immutable once created — no deletion, no modification. Storage cost for ~365K events/year at ~1KB/event is ~365MB/year — negligible.

---

## Summary Table

| Event                          | Domain     | Processing | KPI    | Throttle                |
| ------------------------------ | ---------- | ---------- | ------ | ----------------------- |
| `supply_delivery_created`      | Inventory  | Batch      | 1, 3   | —                       |
| `dispensing_order_created`     | Inventory  | Batch      | 1, 2   | —                       |
| `stock_threshold_triggered`    | Inventory  | **Stream** | 1, 3   | 15 min / supply+clinic  |
| `direct_stock_edit_rejected`   | Inventory  | Batch      | Policy | —                       |
| `dispensing_order_failed`      | Inventory  | Batch*     | 1, 3   | —                       |
| `emergency_dispensing_flagged` | Inventory  | **Stream** | 2      | —                       |
| `user_login_succeeded`         | Auth       | Batch      | Ops    | —                       |
| `user_login_failed`            | Auth       | Batch*     | Ops    | —                       |
| `session_expired`              | Auth       | Batch      | Ops    | —                       |
| `supply_list_viewed`           | Navigation | Batch      | Ops    | —                       |
| `dispensing_form_abandoned`    | Navigation | Batch      | Ops    | 60 sec / user+session   |
| `clinic_filter_applied`        | Navigation | Batch      | Ops    | 5 sec / user+session    |

*Batch with stream exception for specific conditions (see event definitions above).

---

*HealthCore Digital — Internal document for 4Geeks Academy AI Engineering Track*
*Schema version 1.0.0 — Review deadline: Friday*
