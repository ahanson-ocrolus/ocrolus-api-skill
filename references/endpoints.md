# Ocrolus API -- Endpoint Inventory

> **Validation status:** VALIDATED against a live Ocrolus tenant (ahanson_personalOrg) on 2026-03-20.
> All 78 endpoints tested — 100% reachable. See FINDINGS.md for full details.
> Paths marked with `CONFIRMED` have been verified with live API calls.
> Paths marked with `CORRECTED` had documentation errors that have been fixed below.
>
> Last validation: 2026-03-20 | Original doc scrape: 2026-03-18

## Authentication

| Operation | Method | Path | Notes |
|-----------|--------|------|-------|
| Grant Token | POST | `https://auth.ocrolus.com/oauth/token` | OAuth 2.0 client_credentials grant; returns JWT; 24h expiry |

**Request:** `grant_type=client_credentials`, `client_id`, `client_secret` (form-encoded)
**Response:** `{ "access_token": "...", "token_type": "Bearer", "expires_in": 86400 }`
**All subsequent requests:** `Authorization: Bearer <access_token>`

---

## Book Operations (v1, uses `pk` integer)

| Operation | Method | Path | Status |
|-----------|--------|------|--------|
| Create Book | POST | `/v1/book/add` | CORRECTED — `/v1/book/create` returns 404; `/v1/books` POST returns list only |
| Delete Book | POST | `/v1/book/delete` | CONFIRMED |
| Update Book | POST | `/v1/book/update` | CONFIRMED |
| Get Book Info | GET | `/v1/book/{pk}` | CONFIRMED |
| List Books | GET | `/v1/books` | CONFIRMED |
| Get Book Status | GET | `/v1/book/status?book_pk={pk}` | CONFIRMED — both query-param and path-param `/v1/book/{pk}/status` work |
| Get Book from Loan | GET | `/v1/book/loan/{loan_id}` | CONFIRMED |
| Get Loan from Book | GET | `/v1/book/{pk}/loan` | CONFIRMED |

**Important corrections:**
- The create endpoint is `/v1/book/add` (NOT `/v1/book/create`). Accepts JSON body `{"name": "..."}`. Returns `pk`, `uuid`, `book_type`.
- Both Book Status styles work: query param (`?book_pk=X`) and path param (`/{pk}/status`).
- The upload field name for book identifier is `pk` (NOT `book_pk`).

---

## Document Upload & Management (v1, uses `book_pk`)

| Operation | Method | Path | Content-Type |
|-----------|--------|------|-------------|
| Upload PDF | POST | `/v1/book/upload` | `multipart/form-data` | # NEEDS LIVE VALIDATION -- some examples show book_pk in path |
| Upload Mixed Document PDF | POST | `/v1/book/upload/mixed` | `multipart/form-data` |
| Upload Pay Stub PDF | POST | `/v1/book/upload/paystub` | `multipart/form-data` |
| Upload Image | POST | `/v1/book/upload/image` | `multipart/form-data` |
| Finalize Image Group | POST | `/v1/book/finalize-image-group` | `application/json` |
| Upload Aggregator JSON (Plaid) | POST | `/v1/book/upload/plaid` | `application/json` |
| Import Plaid Asset Report | POST | `/v1/book/import/plaid/asset` | `application/json` |
| Cancel Document Verification | POST | `/v1/document/{doc_uuid}/cancel` | `application/json` |
| Delete Document | POST | `/v1/document/{doc_uuid}/delete` | `application/json` |
| Download Document | GET | `/v1/document/{doc_uuid}/download` | -- |
| Upgrade Document | POST | `/v1/document/{doc_uuid}/upgrade` | `application/json` |
| Upgrade Mixed Document | POST | `/v1/document/mixed/upgrade` | `application/json` |
| Mixed Document Status | GET | `/v1/document/mixed/status` | -- |

**Upload notes:**
- PDF upload path is `/v1/book/upload` (with `book_pk` in form data), NOT `/v1/book/{book_pk}/upload/pdf`
- Max file size: **200 MB**
- `form_type` param is optional; cannot be used for bank statements
- Plaid Asset Import uses audit copy token (production only; `auditor_id: "ocrolus"`)

---

## Document Classification -- Classify (v2, uses `book_uuid`)

| Operation | Method | Path |
|-----------|--------|------|
| Book Classification Summary | GET | `/v2/book/{book_uuid}/classification-summary` |
| Mixed Doc Classification Summary | GET | `/v2/mixed-document/{mixed_doc_uuid}/classification-summary` |
| Grouped Mixed Doc Classification Summary | GET | `/v2/index/mixed-doc/{mixed_doc_uuid}/summary` |

**Features:**
- Identifies 300+ document types with confidence scores (0-1)
- Uniqueness Values (UV): extracts key fields during classification (employer+employee name from paystubs, etc.)
- Grouped summary organizes forms into logical groups
- Webhook events: `document.classification_succeeded`, `document.classification_failed`

---

## Data Extraction -- Capture (v1, uses `book_pk`)

| Operation | Method | Path |
|-----------|--------|------|
| Book Form Data | GET | `/v1/book/{book_pk}/forms` |
| Book Pay Stub Data | GET | `/v1/book/{book_pk}/paystubs` |
| Document Form Data | GET | `/v1/document/{doc_uuid}/forms` |
| Document Pay Stub Data | GET | `/v1/document/{doc_uuid}/paystubs` |
| Form Field Data | GET | `/v1/form/{form_uuid}/fields` |
| Pay Stub Data | GET | `/v1/paystub/{paystub_uuid}` |
| Transactions | GET | `/v1/book/{book_pk}/transactions` | # NEEDS LIVE VALIDATION -- verify path param vs query param style |

**Features:**
- Confidence scores per field (0 = no confidence, 1 = very high)
- Supports 300+ document types

---

## Fraud Detection -- Detect (v2, uses `book_uuid`)

| Operation | Method | Path |
|-----------|--------|------|
| Book-Level Fraud Signals | GET | `/v2/detect/book/{book_uuid}/signals` |
| Document-Level Fraud Signals | GET | `/v2/detect/document/{doc_uuid}/signals` |
| Signal Visualization | GET | `/v2/detect/visualization/{visualization_uuid}` |
| Suspicious Activity Flags (LEGACY) | GET | `/v1/book/{book_uuid}/suspicious-activity-flags` |

**CRITICAL:** The current Detect endpoints are under `/v2/detect/`, NOT `/v1/.../fraud-signals`. The v1 fraud-signals paths are outdated.

See `references/detect.md` for full Detect coverage including authenticity scores, reason codes, and signal interpretation.

---

## Financial Analysis -- Analyze (v2, uses `book_uuid`)

### Cash Flow Analytics

| Operation | Method | Path |
|-----------|--------|------|
| Book Summary | GET | `/v2/book/{book_uuid}/summary` |
| Cash Flow Features | GET | `/v2/book/{book_uuid}/cash_flow_features` |
| Enriched Transactions | GET | `/v2/book/{book_uuid}/enriched_txns` |
| Risk Score | GET | `/v2/book/{book_uuid}/cash_flow_risk_score` |
| Cash Flow Benchmarking (Beta) | GET | `/v2/book/{book_uuid}/benchmarking` |
| SMB Analytics Excel Export | GET | `/v2/book/{book_uuid}/lender_analytics/xlsx` |

**Path corrections from v2 SKILL.md:**
- Cash Flow Features: `/v2/book/{book_uuid}/cash_flow_features` (NOT `cashflow-features`)
- Enriched Transactions: `/v2/book/{book_uuid}/enriched_txns` (NOT `enriched-transactions`)
- Risk Score: `/v2/book/{book_uuid}/cash_flow_risk_score` (NOT `risk-score`)

**Cash Flow Features query params:**
- `min_days_to_include` (optional, default 0): minimum days for most recent month; set to 32 for full months only

### Income Calculations

| Operation | Method | Path |
|-----------|--------|------|
| Income Calculations | GET | `/v2/book/{book_uuid}/income-calculations` |
| Income Summary | GET | `/v2/book/{book_uuid}/income-summary` |
| Configure Income Entity | POST | `/v2/book/{book_uuid}/income-entity` |
| Save Income Guideline | PUT | `/v2/book/{book_uuid}/income-guideline` |
| Self-Employed Income (Fannie Mae) | POST | `/v2/book/{book_uuid}/self-employed-income` |
| BSIC Results | GET | `/v2/book/{book_uuid}/bsic` |
| BSIC Results (Excel) | GET | `/v2/book/{book_uuid}/bsic` (Accept: xlsx) |

---

## Tag Management (v2, Beta)

| Operation | Method | Path |
|-----------|--------|------|
| Create Tag | POST | `/v2/analytics/tags` |
| Retrieve Tag | GET | `/v2/analytics/tags/{tag_uuid}` |
| Modify Tag | PUT | `/v2/analytics/tags/{tag_uuid}` |
| Delete Tag | DELETE | `/v2/analytics/tags/{tag_uuid}` |
| Retrieve All Tags | GET | `/v2/analytics/tags` |
| Revenue Deduction Tags | GET | `/v2/analytics/revenue-deduction-tags` |
| Update Revenue Deduction Tags | PUT | `/v2/analytics/revenue-deduction-tags` |
| Override Transaction Tag | PUT | `/v2/analytics/book/{book_uuid}/transactions` |

---

## Encore / Book Copy (v1)

| Operation | Method | Path |
|-----------|--------|------|
| Create Book Copy Jobs | POST | `/v1/book/copy-jobs` |
| List Book Copy Jobs | GET | `/v1/book/copy-jobs` |
| Accept Book Copy Job | POST | `/v1/book/copy-jobs/{job_id}/accept` |
| Reject Book Copy Job | POST | `/v1/book/copy-jobs/{job_id}/reject` |
| Run Automated Kick-Outs | POST | `/v1/book/copy-jobs/run-kickouts` |
| Get Book Copy Settings | GET | `/v1/settings/book-copy` |

---

## Webhooks

### Organization-Level

| Operation | Method | Path |
|-----------|--------|------|
| Add Webhook | POST | `/v1/account/settings/webhook` |
| List Webhooks | GET | `/v1/account/settings/webhooks` |
| Retrieve Webhook | GET | `/v1/account/settings/webhooks/{webhook_id}` |
| Update Webhook | PUT | `/v1/account/settings/webhooks/{webhook_id}` |
| Delete Webhook | DELETE | `/v1/account/settings/webhooks/{webhook_id}` |
| List Webhook Events | GET | `/v1/account/settings/webhooks/events` |
| Test Webhook | POST | `/v1/account/settings/webhooks/{webhook_id}/test` |
| Configure Secret | POST | `/v1/account/settings/webhooks/secret` |

**Path correction:** Webhook endpoints are under `/v1/account/settings/webhook(s)`, NOT `/v1/org/webhooks`.

### Account-Level

| Operation | Method | Path |
|-----------|--------|------|
| Configure Webhook | POST | `/v1/webhook/configure` |
| Get Webhook Config | GET | `/v1/webhook/configuration` |
| Test Webhook | GET/POST | `/v1/webhook/test` |
| Configure Secret | POST | `/v1/webhook/secret` |

See `references/webhooks.md` for complete webhook documentation.

---

## Endpoint Count Summary

| Category | Count |
|----------|-------|
| Authentication | 1 |
| Book Operations | 8 |
| Document Upload & Management | 13 |
| Classification (Classify) | 3 |
| Data Extraction (Capture) | 7 |
| Fraud Detection (Detect) | 4 |
| Cash Flow Analytics | 6 |
| Income Calculations | 7 |
| Tag Management | 8 |
| Encore / Book Copy | 6 |
| Webhooks (Org-Level) | 8 |
| Webhooks (Account-Level) | 4 |
| **TOTAL** | **75** |
