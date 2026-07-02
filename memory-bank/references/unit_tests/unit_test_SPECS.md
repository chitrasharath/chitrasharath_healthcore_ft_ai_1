# Unit Test Specs — Gap Coverage

These specs instruct a coding agent to close the gaps between the project requirements (AUTH-088, API-042, FE-019) and the current test coverage. **Only uncovered or missing test cases are listed here** — do not duplicate tests that already exist.

Current state: `services/api` has 70 pytest tests at 94.1% coverage. Frontend has 0% automated test coverage. `TESTING.md` does not exist.

---

## 1. TESTING.md (Required Deliverable)

Create a `TESTING.md` file at the project root with the following sections:

1. **How to run tests** — commands for pytest (`uv run pytest`, `uv run pytest --cov=app --cov-report=term-missing`) and Jest (`npx jest --coverage`).
2. **Test plan** — for each endpoint group (auth, users, suppliers, incidents) and each frontend module, list the happy-path, edge-case, and failure-mode cases covered.
3. **Coverage results** — paste the latest `pytest --cov` summary table and Jest coverage summary after all tests are written.
4. **Bugs found** — if any generated test reveals a bug in existing code, **document the bug and the proposed fix in TESTING.md but do NOT apply the fix**. Record: the file and line, what the test exposed, and the exact code change needed. The fix will only be applied when explicitly instructed.

Update this file after completing each section below.

---

## 2. AUTH-088 — Backend Auth Endpoint Gap Tests

All tests go in `services/api/tests/`. Use the existing `conftest.py` fixtures. Run with `uv run pytest`.

### 2a. `tests/test_auth.py` — Users Router Gaps

File `app/domains/users/router.py` is at 84.6% coverage. The following branches are untested:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `test_put_user_not_found_returns_404` | Failure | PUT `/users/{id}` with a valid token but a non-existent `user_id` returns 404 with `"User not found"` |
| `test_put_user_duplicate_email_returns_422` | Edge | PUT `/users/{id}` changing email to one already registered by another user returns 422 with `"Email already registered"` |

### 2b. `tests/test_auth.py` — Auth Reset Service Gaps

File `app/domains/auth/reset_service.py` is at 91.2%. Untested paths:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `test_reset_password_user_deleted_after_token_issued_returns_400` | Failure | Issue a valid reset token, delete the user, then call POST `/auth/reset-password` — should return 400 `"Invalid or expired reset token."` |
| `test_forgot_password_sends_email_when_api_key_set` | Edge | Mock `resend.Emails.send` and set `settings.email_api_key` to a non-empty value, call forgot-password for a registered email — assert `resend.Emails.send` was called once with the correct `to` address and a URL containing a valid JWT |

### 2c. `tests/test_auth.py` — Token Module Gaps

File `app/domains/auth/token.py` is at 94.7%. Untested paths:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `test_decode_reset_token_missing_subject_returns_error` | Failure | Craft a JWT with `purpose=reset` but no `sub` claim, call `decode_reset_token` — should raise `InvalidResetTokenError` |
| `test_decode_access_token_missing_subject_returns_401` | Failure | Craft a JWT with no `sub` claim, call `decode_access_token` — should raise HTTPException 401 |

### 2d. `tests/test_auth.py` — Users Service Gaps

File `app/domains/users/service.py` is at 92%. Untested paths:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `test_to_user_response_string_created_at` | Edge | Call `to_user_response` with `created_at` as an ISO string (e.g. `"2025-01-01T00:00:00Z"`) — should parse correctly and return a valid `UserResponse` |
| `test_update_user_email_same_as_own_succeeds` | Edge | Update a user's email to their own current email — should succeed (not raise `DuplicateEmailError`) |

---

## 3. API-042 — Backoffice Endpoint Gap Tests

### 3a. `tests/test_incidents.py` — Incidents Endpoint Gaps

Currently only 4 tests. File `app/domains/reporting/incidents/router.py` is at 84.4%. Add these:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `test_analyze_no_filename_returns_400` | Failure | Upload a file with no filename set — returns 400 `"A CSV file is required."` |
| `test_analyze_invalid_csv_content_returns_400` | Failure | Upload a file with malformed/non-CSV content that triggers a `ValueError` in `analyze_incidents_csv` — returns 400 with the ValueError message |
| `test_analyze_unexpected_error_returns_400` | Failure | Upload content that triggers a generic `Exception` (e.g., mock `analyze_incidents_csv` to raise `RuntimeError`) — returns 400 `"Unable to analyze incidents file."` |
| `test_analyze_valid_csv_returns_analysis` | Happy | Upload a valid HealthCore incidents CSV, assert response contains expected analysis fields (total incidents, breakdown, etc.) — this may overlap with existing test but ensure the response schema is fully validated |
| `test_export_csv_content_format` | Edge | After a successful analysis, GET `/incidents/results/export` and verify the CSV content has correct headers (`metric`, `value`, `percentage`) and rows matching the analysis |

### 3b. `tests/test_suppliers.py` — Suppliers Endpoint Gaps

File `app/domains/procurement/suppliers/router.py` is at 87.5%, `schemas.py` at 93.2%, `service.py` at 94.3%. Check existing tests and add only what's missing:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `test_create_supplier_missing_required_fields_returns_422` | Failure | POST `/suppliers` with empty body — returns 422 validation error |
| `test_update_supplier_not_found_returns_404` | Failure | PUT `/suppliers/{id}` with non-existent ID — returns 404 |
| `test_supplier_schema_validation_edge_cases` | Edge | Test schema validation boundaries: monthly_rate at 0, extremely long supplier name, invalid category value, empty country — assert appropriate validation errors |

---

## 4. FE-019 — Frontend Jest Tests

### 4a. Jest Configuration

No Jest config exists in any `uis/` package. Set up Jest:

1. Install dependencies in the relevant frontend package(s):
   ```bash
   cd uis/website && npm install --save-dev jest @types/jest ts-jest
   cd uis/supplier_directory && npm install --save-dev jest @types/jest ts-jest
   ```
2. Create `jest.config.ts` in each package with TypeScript support and path alias resolution matching each package's `tsconfig.json`.
3. Create a `__tests__/` directory in each package.

### 4b. `uis/website/__tests__/enquiry-validation.test.ts`

File `uis/website/lib/enquiry-validation.ts` exports 14 validation functions with zero test coverage. Test at minimum:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `validateNameField — valid name returns null` | Happy | `validateNameField("en", "Alice", "first_name")` returns `null` |
| `validateNameField — empty string returns error` | Failure | `validateNameField("en", "", "first_name")` returns a non-null error string |
| `validateNameField — name with digits returns error` | Edge | `validateNameField("en", "Alice123", "first_name")` returns error |
| `validateDob — valid adult dob returns null` | Happy | Pass a DOB making the person 25 years old — returns `null` |
| `validateDob — future date returns error` | Failure | Pass tomorrow's date — returns error |
| `validateDob — age over 120 returns error` | Edge | Pass a DOB from 1850 — returns error |
| `validateEmail — valid email returns null` | Happy | `validateEmail("en", "a@b.com")` returns `null` |
| `validateEmail — missing @ returns error` | Failure | `validateEmail("en", "invalid")` returns error |
| `validatePhone — valid intl phone returns null` | Happy | `validatePhone("en", "+1 555-123-4567")` returns `null` |
| `validatePhone — no country code returns error` | Failure | `validatePhone("en", "5551234567")` returns error |
| `validatePreferredDate — next business day returns null` | Happy | Pass the next weekday — returns `null` |
| `validatePreferredDate — weekend returns error` | Edge | Pass a Saturday — returns error |
| `validatePreferredDate — date > 60 days out returns error` | Edge | Pass a date 61 days from now — returns error |
| `validateService — Paediatric Care for adult returns error` | Edge | Service is "Paediatric Care" but DOB indicates age 25 — returns paediatric error |
| `validateInsuranceProvider — has insurance but empty provider returns error` | Failure | `hasInsurance="Yes"`, empty provider — returns error |
| `validateMemberId — invalid format returns error` | Failure | `hasInsurance="Yes"`, memberId `"!!!"` — returns error |
| `validatePatientId — existing patient with invalid format returns error` | Failure | `newPatient="No"`, patientId `"INVALID"` — returns error |
| `validatePatientId — valid HC- format returns null` | Happy | `newPatient="No"`, patientId `"HC-ABC123"` — returns `null` |
| `validateHealthConcern — too short returns error with remaining count` | Failure | Pass 5-char string — error includes remaining character count |
| `validateConsent — false returns error` | Failure | `validateConsent("en", false)` — returns error |
| `shouldShowEveningWarning — evening + early-close clinic returns true` | Edge | Pass `time="Evening (5pm-8pm)"` and a clinic that closes before 8pm — returns `true` |
| `calcAge — birthday today` | Edge | Pass today's date as DOB — returns `0` |

### 4c. `uis/supplier_directory/__tests__/format.test.ts`

File `uis/supplier_directory/lib/format.ts` has 3 pure functions, zero tests:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `formatRate — USD supplier formats with $` | Happy | Supplier with `currency:"USD"`, `monthly_rate:1234.5` → `"$1,234.50"` |
| `formatRate — GBP supplier formats with £` | Happy | Supplier with `currency:"GBP"`, `monthly_rate:999` → `"£999.00"` |
| `formatRateUpdated — formats ISO date string` | Happy | `formatRateUpdated("2025-06-15T10:30:00Z")` → contains `"Jun 15, 2025"` |
| `formatCompliance — null returns em dash` | Edge | `formatCompliance(null)` → `"—"` |
| `formatCompliance — non-null returns value` | Happy | `formatCompliance("HIPAA")` → `"HIPAA"` |

### 4d. `uis/supplier_directory/__tests__/supplier-filter-params.test.ts`

File `uis/supplier_directory/lib/supplier-filter-params.ts` has 6 exported functions, zero tests:

| Test name | Type | What to assert |
|-----------|------|----------------|
| `parseSupplierFilters — no params returns all defaults` | Happy | Empty `URLSearchParams` → `{ countryFilter: "all", categoryFilter: "all" }` |
| `parseSupplierFilters — valid country and category` | Happy | `?country=USA&category=pharmaceutical` → `{ countryFilter: "USA", categoryFilter: "pharmaceutical" }` |
| `parseSupplierFilters — invalid country falls back to all` | Edge | `?country=INVALID` → `countryFilter: "all"` |
| `parseSupplierFilters — invalid category falls back to all` | Edge | `?category=nonexistent` → `categoryFilter: "all"` |
| `applySupplierFilters — sets country param` | Happy | Apply `{ countryFilter: "UK" }` → URLSearchParams contains `country=UK` |
| `applySupplierFilters — removes country when all` | Edge | Apply `{ countryFilter: "all" }` → no `country` param |
| `applySupplierFilters — strips api param` | Edge | Start with `?api=true&country=USA`, apply no changes → `api` param is removed |
| `filterListQuery — builds query string from filters` | Happy | `?country=UK&category=pharmaceutical` → `"country=UK&category=pharmaceutical"` |
| `supplierListPath — no filters returns base path` | Happy | Empty params → `"/supplier-directory"` |
| `supplierDetailPath — with return query` | Happy | `supplierDetailPath(42, "country=USA")` → contains `/suppliers/42?return=` |
| `supplierDetailPath — without return query` | Edge | `supplierDetailPath(42, "")` → `"/supplier-directory/suppliers/42"` |
| `supplierListPathFromReturn — null return query` | Edge | `supplierListPathFromReturn(null)` → `"/supplier-directory"` |

---

## 5. Completion Criteria

- [ ] `TESTING.md` exists at project root with all required sections
- [ ] All tests in sections 2–3 pass with `uv run pytest` from `services/api/`
- [ ] `uv run pytest --cov=app` shows ≥ 70% overall (currently 94.1% — should remain or increase)
- [ ] Target files with gaps improve: `users/router.py` ≥ 95%, `incidents/router.py` ≥ 95%, `reset_service.py` ≥ 95%
- [ ] All tests in section 4 pass with `npx jest --coverage` from the relevant `uis/` package
- [ ] No test asserts on HTTP serialisation — all assertions target business logic (return values, raised exceptions, validation outcomes)
- [ ] `TESTING.md` is updated with final coverage numbers
