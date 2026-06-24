# HealthCore — Testing Guide

## How to run tests

### Backend API (pytest)

```bash
cd services/api
uv sync --extra dev
uv run pip install pytest-cov
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

### Frontend — Website (Jest)

```bash
cd uis/website
npm install
npm test -- --coverage
```

### Frontend — Supplier directory (Jest)

```bash
cd uis/supplier_directory
npm install
npm test -- --coverage
```

---

## Test plan

### Authentication & users (`services/api/tests/test_auth.py`)

| Test | Type | What it covers |
|------|------|----------------|
| Register / login / JWT / me | Happy | Valid credentials, token issuance, profile read |
| Duplicate email, short password, wrong password | Failure | Validation and auth rejection |
| Inactive / deleted user, expired token | Failure | Token and account state guards |
| Users CRUD (list, get, put, delete) | Happy / Failure | Authorized access, 403/404 paths |
| Password reset flow | Happy / Failure | Valid, reused, expired, invalid tokens |
| `test_put_user_not_found_returns_404` | Failure | PUT own user when store row missing → 404 |
| `test_put_user_duplicate_email_returns_422` | Edge | Email collision on update |
| `test_reset_password_user_deleted_after_token_issued_returns_400` | Failure | Reset after user deleted |
| `test_forgot_password_sends_email_when_api_key_set` | Edge | Resend `Emails.send` when API key set |
| `test_decode_reset_token_missing_subject_returns_error` | Failure | JWT without `sub` |
| `test_decode_access_token_missing_subject_returns_401` | Failure | Access JWT without `sub` |
| `test_to_user_response_string_created_at` | Edge | ISO string `created_at` parsing |
| `test_update_user_email_same_as_own_succeeds` | Edge | Same-email update allowed |

### Suppliers (`services/api/tests/test_suppliers.py`)

| Test | Type | What it covers |
|------|------|----------------|
| Seed, CRUD, filters, rate/status PATCH | Happy / Failure | Full supplier domain |
| `test_create_supplier_missing_required_fields_returns_422` | Failure | Empty POST body |
| `test_patch_supplier_details_not_found_returns_404` | Failure | PATCH details for missing ID |
| `test_supplier_schema_validation_edge_cases` | Edge | `monthly_rate: 0`, empty `country`, invalid category |

### Incidents (`services/api/tests/test_incidents.py`)

| Test | Type | What it covers |
|------|------|----------------|
| Analyze / export with auth | Happy | HealthCore CSV fixture, export guard |
| `test_analyze_no_filename_returns_400` | Failure | Upload without filename |
| `test_analyze_invalid_csv_content_returns_400` | Failure | Empty file → ValueError message |
| `test_analyze_unexpected_error_returns_400` | Failure | Generic exception → safe message |
| `test_analyze_valid_csv_returns_analysis` | Happy | Full response schema fields |
| `test_export_csv_content_format` | Edge | CSV headers `metric,value,percentage` |

### Website enquiry validation (`uis/website/__tests__/enquiry-validation.test.ts`)

| Test | Type | What it covers |
|------|------|----------------|
| Name, DOB, email, phone validators | Happy / Failure / Edge | Required formats and bounds |
| Preferred date (business day, 60-day window) | Happy / Edge | Scheduling rules |
| Service, insurance, patient ID, consent | Happy / Failure / Edge | Conditional field rules |
| Evening clinic warning, `calcAge` | Edge | Clinic hours + age calculation |

### Supplier directory (`uis/supplier_directory/__tests__/`)

| Test | Type | What it covers |
|------|------|----------------|
| `format.test.ts` | Happy / Edge | Rate, date, compliance formatting |
| `supplier-filter-params.test.ts` | Happy / Edge | URL filter parse/apply/path helpers |

---

## Coverage results

**Generated:** 2026-06-24

### Backend (`services/api`)

```
88 passed
TOTAL: 811 statements, 27 missed, 97% line coverage
```

| File | Coverage |
|------|----------|
| `app/domains/users/router.py` | 95% |
| `app/domains/reporting/incidents/router.py` | 100% |
| `app/domains/auth/reset_service.py` | 100% |
| `app/domains/auth/token.py` | 100% |

### Website (`uis/website`)

```
22 passed
All files: 87.8% stmts, 93.4% lines (lib/)
enquiry-validation.ts: 93.97% lines
```

### Supplier directory (`uis/supplier_directory`)

```
17 passed
All files: 88.88% stmts, 86.79% lines (lib/)
format.ts: 100%
supplier-filter-params.ts: 86.84% lines
```

---

## Bugs found

### BUG-001: Weekend preferred dates are not rejected — **fixed**

| Field | Detail |
|-------|--------|
| **Discovered by** | `uis/website/__tests__/enquiry-validation.test.ts` — `validatePreferredDate — weekend returns error` |
| **File** | `uis/website/lib/enquiry-validation.ts` |
| **Fix applied** | Reject Saturday/Sunday after min/max bounds: `const day = selected.getDay(); if (day === 0 \|\| day === 6) return err(lang, "preferred_date");` |
| **Verify** | `cd uis/website && npm test` — 22 passed |
| **Status** | `fixed` |

**Note:** Supplier `name` has no max-length validator — extremely long names (300+ chars) are accepted (201). Not logged as a bug; schema has no length constraint today.

No other production bugs identified during test implementation.

---

## AI assistance log

- Gap targets were taken from `memory-bank/references/unit_tests/unit_test_SPECS.md`, cross-checked against `test_coverage_pre.md` (94.1% API baseline, 0% frontend).
- `test_put_user_not_found_returns_404` required a two-call `get_by_id` mock because the router returns 403 when `user_id` ≠ `current_user.id` before the not-found branch runs.
- `test_analyze_no_filename_returns_400` uses a direct `analyze_incidents` call with a mock `UploadFile` because FastAPI's TestClient rejects empty filenames with 422 before the route handler runs.
- BUG-001 (weekend preferred date) was caught when implementing the SPECS §4b Jest case; fixed by rejecting Saturday/Sunday in `validatePreferredDate`.
