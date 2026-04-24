# Ocrolus API -- Endpoint Inventory

> **Validation status:** VALIDATED against a live Ocrolus tenant (ahanson_personalOrg) on 2026-03-20.
> All 78 endpoints tested — 100% reachable. See FINDINGS.md for full details.
> Paths marked with `CONFIRMED` have been verified with live API calls.
> Paths marked with `CORRECTED` had documentation errors that have been fixed below.
>
> **Naming convention:** Endpoint names in this document match the actual URL path segments
> (e.g., `book/add` not "Create Book"). This avoids confusion when the human-readable name
> on docs.ocrolus.com doesn't match the actual endpoint.
>
> Last validation: 2026-03-20 | Original doc scrape: 2026-03-18

---

## Authentication

| Endpoint | Method | Path | Input | Notes |
|----------|--------|------|-------|-------|
| `oauth/token` | POST | `https://auth.ocrolus.com/oauth/token` | **Body (form-encoded):** `grant_type`, `client_id`, `client_secret` | OAuth 2.0 client_credentials grant; returns JWT; 24h expiry |

**IMPORTANT:** Auth body must be form-encoded (`application/x-www-form-urlencoded`), NOT JSON. Do NOT include `audience` param — causes 403.

**Response:** `{ "access_token": "...", "token_type": "Bearer", "expires_in": 86400 }`
**All subsequent requests:** `Authorization: Bearer <access_token>`

---

## Book Operations (v1, uses `pk` integer)

| Endpoint | Method | Path | Input | Status |
|----------|--------|------|-------|--------|
| `book/add` | POST | `/v1/book/add` | **Body (JSON):** `name`, `book_type` | CORRECTED — `/v1/book/create` returns 404 |
| `book/delete` | POST | `/v1/book/delete` | **Body (JSON):** `book_id` (integer) OR `book_uuid` (UUID) | CONFIRMED |
| `book/update` | POST | `/v1/book/update` | **Body (JSON):** `pk` (integer) OR `book_uuid` (UUID), + `name` | CONFIRMED |
| `book/{pk}` | GET | `/v1/book/{pk}` | **Path:** `pk` (integer) | CONFIRMED |
| `books` | GET | `/v1/books` | **Query (optional):** `page`, `per_page` | CONFIRMED |
| `book/status` | GET | `/v1/book/status?book_pk={pk}` | **Query:** `book_pk` (integer) | CONFIRMED — path-param `/v1/book/{pk}/status` also works |
| `book/loan/{loan_id}` | GET | `/v1/book/loan/{loan_id}` | **Path:** `loan_id` (string) | CONFIRMED |
| `book/{pk}/loan` | GET | `/v1/book/{pk}/loan` | **Path:** `pk` (integer) | CONFIRMED |

**Important corrections:**
- The add endpoint is `/v1/book/add` (NOT `/v1/book/create`). Returns `pk`, `uuid`, `book_type`.
- **Field names vary by endpoint** — delete uses `book_id`, update uses `pk`, uploads use `pk`. Always check the specific endpoint.
- Both Book Status styles work: query param (`?book_pk=X`) and path param (`/{pk}/status`).

---

## Document Upload & Management (v1)

| Endpoint | Method | Path | Input | Notes |
|----------|--------|------|-------|-------|
| `book/upload` | POST | `/v1/book/upload` | **Form (multipart):** `pk` (integer) OR `book_uuid` (UUID), `upload` (file), `form_type` (optional), `doc_name` (optional) | Max 200MB |
| `book/upload/mixed` | POST | `/v1/book/upload/mixed` | **Form (multipart):** `pk` (integer) OR `book_uuid` (UUID), `upload` (file) | Multiple doc types in single PDF |
| `book/upload/paystub` | POST | `/v1/book/upload/paystub` | **Form (multipart):** `pk` (integer) OR `book_uuid` (UUID), `upload` (file) | |
| `book/upload/image` | POST | `/v1/book/upload/image` | **Form (multipart):** `pk` (integer) OR `book_uuid` (UUID), `upload` (file), `image_group` (string) | |
| `book/finalize-image-group` | POST | `/v1/book/finalize-image-group` | **Body (JSON):** `pk` (integer) OR `book_uuid` (UUID), `image_group` (string) | |
| `book/upload/plaid` | POST | `/v1/book/upload/plaid` | **Body (JSON):** `pk` (integer) OR `book_uuid` (UUID) | |
| `book/import/plaid/asset` | POST | `/v1/book/import/plaid/asset` | **Body (JSON):** `audit_copy_token` (string) | Production only; `auditor_id: "ocrolus"` |
| `document/cancel` | POST | `/v1/document/{doc_uuid}/cancel` | **Path:** `doc_uuid` (UUID); **Body (JSON, optional):** `doc_pk` (integer) OR `doc_uuid` (UUID), `accept_charges` (boolean) | Also: `/v1/document/cancel?doc_uuid=X` |
| `document/remove` | POST | `/v1/document/{doc_uuid}/delete` | **Path:** `doc_uuid` (UUID); **Body (JSON):** `doc_id` (integer) OR `doc_uuid` (UUID) | Also: `/v1/document/remove?doc_uuid=X` |
| `document/{doc_uuid}/download` | GET | `/v1/document/{doc_uuid}/download` | **Path:** `doc_uuid` (UUID) | Returns binary |
| `document/upgrade` | POST | `/v1/document/{doc_uuid}/upgrade` | **Path:** `doc_uuid` (UUID); **Body (JSON):** `doc_pk` (integer) OR `doc_uuid` (UUID), `upgrade_type` (string) | Also: `/v1/document/upgrade?doc_uuid=X` |
| `document/mixed/upgrade` | POST | `/v1/document/mixed/upgrade` | **Body (JSON):** `mixed_doc_pk` (integer) OR `mixed_doc_uuid` (UUID), `upgrade_type` (string) | |
| `document/mixed/status` | GET | `/v1/document/mixed/status` | **Query:** one of `pk` (integer), `doc_uuid` (UUID), or `mixed_doc_uuid` (UUID) | |

**Upload notes:**
- PDF upload path is `/v1/book/upload` (with `pk` or `book_uuid` in form data), NOT `/v1/book/{pk}/upload/pdf`
- The form field is `pk` (integer) or `book_uuid` (UUID) — NOT `book_pk`
- Max file size: **200 MB**
- `form_type` is optional; cannot be used for bank statements
- Plaid Asset Import uses audit copy token (production only; `auditor_id: "ocrolus"`)

**Field name inconsistencies (per official spec):**
- Delete uses `book_id` (not `book_pk` or `pk`)
- Document cancel/upgrade use `doc_pk` (not `doc_id`)
- Document remove (delete) uses `doc_id` (not `doc_pk`)
- Mixed document upgrade uses `mixed_doc_pk` (not `mixed_doc_id`)
- Transactions use `book_pk` and `uploaded_doc_pk` in query params

---

## Document Classification -- Classify (v2, uses `book_uuid`)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{book_uuid}/classification-summary` | GET | `/v2/book/{book_uuid}/classification-summary` | **Path:** `book_uuid` (UUID) |
| `mixed-document/{mixed_doc_uuid}/classification-summary` | GET | `/v2/mixed-document/{mixed_doc_uuid}/classification-summary` | **Path:** `mixed_doc_uuid` (UUID) |
| `index/mixed-doc/{mixed_doc_uuid}/summary` | GET | `/v2/index/mixed-doc/{mixed_doc_uuid}/summary` | **Path:** `mixed_doc_uuid` (UUID) |

**Features:**
- Identifies 300+ document types with confidence scores (0-1)
- Uniqueness Values (UV): extracts key fields during classification (employer+employee name from paystubs, etc.)
- Grouped summary organizes forms into logical groups
- Webhook events: `document.classification_succeeded`, `document.classification_failed`

---

## Data Extraction -- Capture (v1, uses `pk`)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{pk}/forms` | GET | `/v1/book/{pk}/forms` | **Path:** `pk` (integer) |
| `book/{pk}/paystubs` | GET | `/v1/book/{pk}/paystubs` | **Path:** `pk` (integer) |
| `document/{doc_uuid}/forms` | GET | `/v1/document/{doc_uuid}/forms` | **Path:** `doc_uuid` (UUID) |
| `document/{doc_uuid}/paystubs` | GET | `/v1/document/{doc_uuid}/paystubs` | **Path:** `doc_uuid` (UUID) |
| `form/{form_uuid}/fields` | GET | `/v1/form/{form_uuid}/fields` | **Path:** `form_uuid` (UUID) |
| `paystub/{paystub_uuid}` | GET | `/v1/paystub/{paystub_uuid}` | **Path:** `paystub_uuid` (UUID) |
| `book/{pk}/transactions` | GET | `/v1/book/{pk}/transactions` | **Path:** `pk` (integer); **Query (optional):** `uploaded_doc_pk` (integer), `uploaded_doc_uuid` (UUID), `only_tagged` (boolean), `distinct_fields` (boolean) |
| `document/periods` | GET | `/v1/document/periods?pk={pk}` | **Query:** `pk` (integer) | UNDOCUMENTED — not in official docs; likely legacy |

**Features:**
- Confidence scores per field (0 = no confidence, 1 = very high)
- Supports 300+ document types
- Transactions also available via query-param style: `/v1/transaction?book_pk=X`
- Transaction filtering: use `uploaded_doc_pk` or `uploaded_doc_uuid` to scope to a specific document

---

## Fraud Detection -- Detect (v2, uses `book_uuid`)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `detect/book/{book_uuid}/signals` | GET | `/v2/detect/book/{book_uuid}/signals` | **Path:** `book_uuid` (UUID) |
| `detect/document/{doc_uuid}/signals` | GET | `/v2/detect/document/{doc_uuid}/signals` | **Path:** `doc_uuid` (UUID) |
| `detect/visualization/{visualization_uuid}` | GET | `/v2/detect/visualization/{visualization_uuid}` | **Path:** `visualization_uuid` (UUID) |
| `book/{book_uuid}/suspicious-activity-flags` | GET | `/v1/book/{book_uuid}/suspicious-activity-flags` | **Path:** `book_uuid` (UUID) | LEGACY/DEPRECATED |

**CRITICAL:** The current Detect endpoints are under `/v2/detect/`, NOT `/v1/.../fraud-signals`. The v1 fraud-signals paths are outdated.

See `references/detect.md` for full Detect coverage including authenticity scores, reason codes, and signal interpretation.

---

## Financial Analysis -- Analyze (v2, uses `book_uuid`)

### Cash Flow Analytics

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{book_uuid}/summary` | GET | `/v2/book/{book_uuid}/summary` | **Path:** `book_uuid` (UUID) |
| `book/{book_uuid}/cash_flow_features` | GET | `/v2/book/{book_uuid}/cash_flow_features` | **Path:** `book_uuid` (UUID); **Query (optional):** `min_days_to_include` (integer, default 0) |
| `book/{book_uuid}/enriched_txns` | GET | `/v2/book/{book_uuid}/enriched_txns` | **Path:** `book_uuid` (UUID) |
| `book/{book_uuid}/cash_flow_risk_score` | GET | `/v2/book/{book_uuid}/cash_flow_risk_score` | **Path:** `book_uuid` (UUID) |
| `book/{book_uuid}/benchmarking` | GET | `/v2/book/{book_uuid}/benchmarking` | **Path:** `book_uuid` (UUID) | Beta |
| `book/{book_uuid}/lender_analytics/xlsx` | GET | `/v2/book/{book_uuid}/lender_analytics/xlsx` | **Path:** `book_uuid` (UUID) | Returns .xlsx binary |

**Path corrections from live testing:**
- Cash Flow Features: `/v2/book/{book_uuid}/cash_flow_features` (NOT `cashflow-features`)
- Enriched Transactions: `/v2/book/{book_uuid}/enriched_txns` (NOT `enriched-transactions`)
- Risk Score: `/v2/book/{book_uuid}/cash_flow_risk_score` (NOT `risk-score`)

**`cash_flow_features` query params:**
- `min_days_to_include` (optional, default 0): minimum days for most recent month; set to 32 for full months only

### Income Calculations

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/{book_uuid}/income-calculations` | GET | `/v2/book/{book_uuid}/income-calculations` | **Path:** `book_uuid` (UUID); **Query (optional):** `guideline` (FANNIE_MAE, FREDDIE_MAC, FHA, VA, USDA) |
| `book/{book_uuid}/income-summary` | GET | `/v2/book/{book_uuid}/income-summary` | **Path:** `book_uuid` (UUID) |
| `book/{book_uuid}/income-entity` | POST | `/v2/book/{book_uuid}/income-entity` | **Path:** `book_uuid` (UUID); **Body (JSON):** config object |
| `book/{book_uuid}/income-guideline` | PUT | `/v2/book/{book_uuid}/income-guideline` | **Path:** `book_uuid` (UUID); **Body (JSON):** guideline object |
| `book/{book_uuid}/self-employed-income` | POST | `/v2/book/{book_uuid}/self-employed-income` | **Path:** `book_uuid` (UUID); **Body (JSON):** params object |
| `book/{book_uuid}/bsic` | GET | `/v2/book/{book_uuid}/bsic` | **Path:** `book_uuid` (UUID) |
| `book/{book_uuid}/bsic` (Excel) | GET | `/v2/book/{book_uuid}/bsic` | **Path:** `book_uuid` (UUID); **Header:** `Accept: application/xlsx` |

---

## Tag Management (v2, Beta)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `analytics/tags` (create) | POST | `/v2/analytics/tags` | **Body (JSON):** `name` (string) |
| `analytics/tags/{tag_uuid}` | GET | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` (UUID) |
| `analytics/tags/{tag_uuid}` (modify) | PUT | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` (UUID); **Body (JSON):** `name` (string) |
| `analytics/tags/{tag_uuid}` (delete) | DELETE | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` (UUID) |
| `analytics/tags` (list) | GET | `/v2/analytics/tags` | **Query (optional):** `is_system_tag` (boolean) |
| `analytics/revenue-deduction-tags` | GET | `/v2/analytics/revenue-deduction-tags` | None |
| `analytics/revenue-deduction-tags` (update) | PUT | `/v2/analytics/revenue-deduction-tags` | **Body (JSON):** `tag_names` (array) |
| `analytics/book/{book_uuid}/transactions` | PUT | `/v2/analytics/book/{book_uuid}/transactions` | **Path:** `book_uuid` (UUID); **Body (JSON):** `txn_pk`, `tag_uuids` |

---

## Encore / Book Copy (v1)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `book/copy-jobs` (create) | POST | `/v1/book/copy-jobs` | **Body (JSON):** `jobs` (array, max 50) |
| `book/copy-jobs` (list) | GET | `/v1/book/copy-jobs` | **Query (optional):** `direction` ('outbound' or 'inbound') |
| `book/copy-jobs/{job_id}/accept` | POST | `/v1/book/copy-jobs/{job_id}/accept` | **Path:** `job_id` (string); **Body (JSON):** `name` |
| `book/copy-jobs/{job_id}/reject` | POST | `/v1/book/copy-jobs/{job_id}/reject` | **Path:** `job_id` (string) |
| `book/copy-jobs/run-kickouts` | POST | `/v1/book/copy-jobs/run-kickouts` | None |
| `settings/book-copy` | GET | `/v1/settings/book-copy` | None |

---

## Webhooks

### Organization-Level

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `account/settings/webhook` | POST | `/v1/account/settings/webhook` | **Body (JSON):** `url`, `events` (array) |
| `account/settings/webhooks` | GET | `/v1/account/settings/webhooks` | None |
| `account/settings/webhooks/{webhook_id}` | GET | `/v1/account/settings/webhooks/{webhook_id}` | **Path:** `webhook_id` (string) |
| `account/settings/webhooks/{webhook_id}` (update) | PUT | `/v1/account/settings/webhooks/{webhook_id}` | **Path:** `webhook_id` (string); **Body (JSON):** `url`, `events` |
| `account/settings/webhooks/{webhook_id}` (delete) | DELETE | `/v1/account/settings/webhooks/{webhook_id}` | **Path:** `webhook_id` (string) |
| `account/settings/webhooks/events` | GET | `/v1/account/settings/webhooks/events` | None |
| `account/settings/webhooks/{webhook_id}/test` | POST | `/v1/account/settings/webhooks/{webhook_id}/test` | **Path:** `webhook_id` (string) |
| `account/settings/webhooks/secret` | POST | `/v1/account/settings/webhooks/secret` | **Body (JSON):** `secret` (string, 16-128 chars) |

**Path correction:** Webhook endpoints are under `/v1/account/settings/webhook(s)`, NOT `/v1/org/webhooks`.

### Account-Level

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `webhook/configure` | POST | `/v1/webhook/configure` | **Body (JSON):** `url`, `events` (array) |
| `webhook/configuration` | GET | `/v1/webhook/configuration` | None |
| `webhook/test` | POST | `/v1/webhook/test` | None |
| `webhook/secret` | POST | `/v1/webhook/secret` | **Body (JSON):** `secret` (string) |

See `references/webhooks.md` for complete webhook documentation.

---

## Optima -- Real-Time Extraction (separate host)

> **Note:** These endpoints use a different base URL (`apika.ocrolus.com`) and are not linked
> from the main Ocrolus docs navigation.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| `ml/v2/instant` | POST | `https://apika.ocrolus.com/ml/v2/instant` | **Body (raw):** PDF binary (`Content-Type: application/pdf`) |
| `ml/v2/instant/images` | POST | `https://apika.ocrolus.com/ml/v2/instant/images` | **Form (multipart):** image files |

**How Optima differs from the standard pipeline:**
- **No book required** — documents are not stored; results returned immediately
- **No human verification** — pure ML extraction
- **Same auth** — uses the same OAuth Bearer token from `auth.ocrolus.com`
- **Use case:** Quick validation (confirm doc type, check if a field is present) rather than full processing

**Validated:** 2026-03-31 — both endpoints return `415` (correct content-type required), confirming routes are live and authenticated.

---

## Endpoint Count Summary

| Category | Count |
|----------|-------|
| Authentication | 1 |
| Book Operations | 8 |
| Document Upload & Management | 13 |
| Classification (Classify) | 3 |
| Data Extraction (Capture) | 8 |
| Fraud Detection (Detect) | 4 |
| Cash Flow Analytics | 6 |
| Income Calculations | 7 |
| Tag Management | 8 |
| Encore / Book Copy | 6 |
| Webhooks (Org-Level) | 8 |
| Webhooks (Account-Level) | 4 |
| Optima (Real-Time) | 2 |
| **TOTAL** | **78** |

---

## Input Type Legend

| Label | Meaning |
|-------|---------|
| **Path:** | URL path parameter — value is embedded in the URL (e.g., `/v1/book/{pk}`) |
| **Query:** | URL query parameter — appended as `?key=value` |
| **Query (optional):** | Optional URL query parameter |
| **Body (JSON):** | Request body sent as `application/json` |
| **Body (form-encoded):** | Request body sent as `application/x-www-form-urlencoded` |
| **Body (raw):** | Request body sent as raw binary with appropriate Content-Type |
| **Form (multipart):** | Request body sent as `multipart/form-data` (file uploads) |
| **Header:** | Custom request header |
| None | No parameters required |
