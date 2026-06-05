# Ocrolus API — Endpoint Inventory

A capability-organized inventory of Ocrolus API endpoints, mirroring the public reference at <https://docs.ocrolus.com/reference>. Sections, names, and paths match the docs site (which is what customers integrate against).

For interactive exploration, see the Ocrolus Postman collection linked from <https://docs.ocrolus.com/reference>.

> **About this inventory.** Paths and parameter names below are aligned to the public docs page. Where the live API also accepts an undocumented alias (e.g. legacy path-style routes), the alias is called out so you don't get surprised in older code, but new code should always use the documented path.

---

## Authentication

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Grant authentication token | POST | `https://auth.ocrolus.com/oauth/token` | **Body (form-encoded):** `grant_type=client_credentials`, `client_id`, `client_secret` |

The body **must** be form-encoded (`application/x-www-form-urlencoded`). JSON bodies and the `audience` parameter return `403 unauthorized_client`.

**Response:** `{ "access_token": "...", "token_type": "Bearer", "expires_in": 86400 }`
**All subsequent requests:** `Authorization: Bearer <access_token>`

---

## Books

### Book Commands

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Create Book | POST | `/v1/book/add` | **Body (JSON):** `name` (required); `book_class` = `INSTANT` \| `COMPLETE` \| `INSTANT_CLASSIFY_ONLY` \| `INSTANT_CLASSIFY_ISO_CAPTURE` (see below); `book_type` = `DEFAULT` \| `INSTANT_ML` (optional); `is_public`, `xid` (optional) |
| Update Book | POST | `/v1/book/update` | **Body (JSON):** `pk` OR `book_uuid`, optional `name`, `book_type`, `book_class`, `is_public`, `xid` |
| Delete Book | POST | `/v1/book/remove` | **Body (JSON):** `book_id` (integer) OR `book_uuid` (UUID) |

#### `book_class` values

`book_class` is set at book creation and cannot be changed later. Map the user's natural-language request to one of:

- **`INSTANT`** — machine-only processing through the full pipeline (classify → capture → analyze). Synonyms: "instant", "instantly", "machine only", "automated", "no human review", "fast".
- **`COMPLETE`** — full pipeline with human verification of low-confidence fields. Default when `book_class` is omitted. Synonyms: "complete", "HITL", "human in the loop", "human verification", "human-verified", "highest accuracy".
- **`INSTANT_CLASSIFY_ONLY`** *(rare)* — stops processing after classification; nothing is captured or analyzed. The integrator listens for `book.classified` and decides per-document what to do next (based on `form_type`). Synonyms: "classify only", "stop after classification", "just classify", "classification only", "no capture".
- **`INSTANT_CLASSIFY_ISO_CAPTURE`** *(rare)* — same as `INSTANT_CLASSIFY_ONLY` for every document **except ISO applications**, which continue through capture. The integrator uses `book.classified` for the stopped-at-classify docs and `book.verified` to know the ISO app finished capture. Synonyms: "ISO app capture only", "classify everything, capture ISO".

Default to `INSTANT` or `COMPLETE` for ordinary use. The two `INSTANT_CLASSIFY_*` variants exist for orchestrators that need to inspect documents and decide what to do next — don't use them unless the user explicitly describes that workflow.

Any other value (`CLASSIFY`, `INSTANT_CLASSIFY`, free-text descriptors like `individual` / `business`) returns `400 Invalid dictionary value @ data["book_class"]`. `book_type` is a separate field and only accepts `DEFAULT` or `INSTANT_ML`.

### Book Queries

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Book information | GET | `/v1/book/info` | **Query:** `pk` OR `book_uuid` |
| Book status | GET | `/v1/book/status` | **Query:** `pk` OR `book_uuid` |
| Book list | GET | `/v1/books` | **Query (optional):** `limit`, `offset`, `order`, `order_by`, `name`, `search`, `xid` |
| Loan details from Book | GET | `/v2/los-connect/book/{book_uuid}/loans` | **Path:** `book_uuid` |
| Book from loan | GET | `/v2/los-connect/encompass/book` | **Query:** `loan_id` and/or `loan_number` |

`/v1/book/add` returns both `pk` (integer) and `uuid` (UUID). Persist both — v1 endpoints typically take `pk`, v2 endpoints take `book_uuid`.

**Undocumented aliases the live API still answers (don't rely on these in new code):**
- `GET /v1/book/{pk}` (use `/v1/book/info?pk=` instead)
- `GET /v1/book/{pk}/status` (use `/v1/book/status?pk=` instead)
- `GET /v1/book/{pk}/loan` (use `/v2/los-connect/book/{book_uuid}/loans` instead)
- `GET /v1/book/loan/{loan_id}` (use `/v2/los-connect/encompass/book?loan_id=` instead)

---

## File Uploads

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Upload PDF to Book | POST | `/v1/book/upload` | **Form (multipart):** `pk` OR `book_uuid`, `upload` (file), `form_type` (optional), `doc_name` (optional) |
| Upload Mixed Document PDF to Book | POST | `/v1/book/upload/mixed` | **Form (multipart):** `pk` OR `book_uuid`, `upload` (file), `doc_name` (optional) |
| Upload Image to Book | POST | `/v1/book/upload/image` | **Form (multipart):** `pk` OR `book_uuid`, `upload` (file), `return_image_pk` (optional) |
| Finalize Image Group | POST | `/v1/book/upload/image/done` | **Body (JSON):** `pk` OR `book_uuid`, `form_type` |
| Upload aggregator JSON to Book | POST | `/v1/book/upload/json` | **Form (multipart):** `pk` OR `uuid`, `upload` (file), `accounts`, `transactions`, `customers`, `institutions`, `doc_name`; **Query (optional):** `upload_intent`, `aggregate_source` |
| Upload Pay stub PDF to Book | POST | `/v2/book/{book_uuid}/document/paystub` | **Path:** `book_uuid`; **Form (multipart):** `upload` (file) |
| Import Plaid Asset Report | POST | `/v1/book/import/plaid/asset` | **Body (JSON):** `pk` OR `book_uuid`, `audit_copy_token`, `form_type`, `doc_name`. Production only. |

The multipart file field is `upload` (the live API also accepts `file`). The book selector field is **`pk`** (integer) or **`book_uuid`** (UUID) — `book_pk` returns `Required pk or book uuid` (status 1103). Maximum file size: **200 MB**.

---

## File Commands

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Cancel document verification | POST | `/v1/document/cancel` | **Body (JSON):** `doc_pk` OR `doc_uuid`, `accept_charges` (boolean) |
| Delete document | POST | `/v1/document/remove` | **Body (JSON):** `doc_id` OR `doc_uuid` |
| Download document | GET | `/v2/document/download` | **Query:** `doc_uuid` |
| Upgrade a document | POST | `/v1/document/upgrade` | **Body (JSON):** `doc_pk` OR `doc_uuid`, `upgrade_type` |
| Upgrade a mixed document | POST | `/v1/document/mixed/upgrade` | **Body (JSON):** `mixed_doc_pk` OR `mixed_doc_uuid`, `upgrade_type` |

## File Queries

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Retrieve Mixed Document status | GET | `/v1/document/mixed/status` | **Query:** one of `pk`, `doc_uuid`, or `mixed_doc_uuid` |

---

## Classify

Identify document types with confidence scores. Uses `book_uuid`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Book classification summary | GET | `/v2/book/{book_uuid}/classification-summary` | **Path:** `book_uuid`; **Query (optional):** `process_unknowns` |
| Mixed Doc classification summary | GET | `/v2/mixed-document/{mixed_doc_uuid}/classification-summary` | **Path:** `mixed_doc_uuid`; **Query (optional):** `process_unknowns` |
| Grouped mixed doc classification summary | GET | `/v2/index/mixed-doc/{mixed_doc_uuid}/summary` | **Path:** `mixed_doc_uuid`; **Query (optional):** `split_unknowns` |

- Identifies 300+ document types with confidence scores (0–1).
- Uniqueness Values (UV): extracts key fields during classification (e.g., employer + employee name from pay stubs).
- Webhook events: `document.classification_succeeded`, `document.classification_failed`.

---

## Capture

Extract structured data from documents (forms, pay stubs, transactions). Uses query parameters that accept either `pk`/`book_pk` (integer) **or** `book_uuid` (UUID).

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Book form data | GET | `/v1/book/forms` | **Query:** `pk` OR `book_uuid` |
| Book form raw fields (v2) | GET | `/v2/book/{book_uuid}/forms` | **Path:** `book_uuid` |
| Doc form data | GET | `/v1/document/forms/fields` | **Query:** `pk` OR `doc_uuid`; optional `include_all`, `include_bboxes` |
| Form data | GET | `/v1/form` | **Query:** `uuid` OR `pk` |
| Book pay stub data | GET | `/v2/book/{book_uuid}/paystub` | **Path:** `book_uuid` |
| Doc pay stub data | GET | `/v2/document/{doc_uuid}/paystub` | **Path:** `doc_uuid`; **Query (optional):** `include_page_doc_info` |
| Pay stub data | GET | `/v2/paystub/{paystub_uuid}` | **Path:** `paystub_uuid` |
| Transactions | GET | `/v1/transaction` | **Query:** `book_pk` OR `book_uuid`; optional `uploaded_doc_pk`, `uploaded_doc_uuid`, `only_tagged`, `distinct_fields`, `include_page_info` |

- Per-field confidence scores (0 = no confidence, 1 = very high).
- Pay stub endpoints moved to v2; the v1 forms remain document-agnostic.
- `GET /v2/book/{book_uuid}/forms` returns raw fields keyed by **v2** `form_uuid`. Use it (not `/v1/form`) to fetch per-form raw fields when you started from `/v2/book/{book_uuid}/classification-summary` — that endpoint's `form_uuid` is a v2 id and is rejected by `/v1/form`.

**Undocumented aliases the live API still answers (don't rely on these in new code):**
- `GET /v1/book/{pk}/forms` (use `/v1/book/forms?pk=` instead)
- `GET /v1/book/{pk}/paystubs` (use `/v2/book/{book_uuid}/paystub` instead)
- `GET /v1/document/{doc_uuid}/forms` (use `/v1/document/forms/fields?doc_uuid=` instead)
- `GET /v1/document/{doc_uuid}/paystubs` (use `/v2/document/{doc_uuid}/paystub` instead)
- `GET /v1/form/{form_uuid}/fields` (use `/v1/form?uuid=` instead)
- `GET /v1/paystub/{paystub_uuid}` (use `/v2/paystub/{paystub_uuid}` instead)
- `GET /v1/book/{pk}/transactions` (use `/v1/transaction?book_pk=` instead)

---

## Detect

Fraud detection signals, authenticity scores, and reason codes. Uses `book_uuid` / `uploaded_doc_uuid`.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Book-level Fraud Signals | GET | `/v2/detect/book/{book_uuid}/signals` | **Path:** `book_uuid`; **Query (optional):** `exclude_dashboard_url` |
| Document-Level Fraud Signals | GET | `/v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals` | **Path:** `uploaded_doc_uuid`; **Query (optional):** `exclude_dashboard_url` |
| Signal visualization | GET | `/v2/detect/visualization/{visualization_uuid}` | **Path:** `visualization_uuid`; **Query (optional):** `size`. Returns a binary image. |
| Suspicious Activity Flags (Legacy) | GET | `/v1/book/{book_uuid}/suspicious-activity-flags` | **Path:** `book_uuid` |

The document-level endpoint is `/v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals` — note `uploaded_doc`, not `document`. See `references/detect.md` for the authenticity score scale, reason code taxonomy, and signal interpretation.

---

## Cash Flow Analytics

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Book summary | GET | `/v2/book/{book_uuid}/summary` | **Path:** `book_uuid`; **Query (optional):** `scope`, `exclude_months`, `exclude_bank_account_pks` |
| Cash flow features | GET | `/v2/book/{book_uuid}/cash_flow_features` | **Path:** `book_uuid` |
| Enriched transactions | GET | `/v2/book/{book_uuid}/enriched_txns` | **Path:** `book_uuid`; **Query (optional):** `offset`, `limit`, `include_pending_plaid_transactions` |
| Risk score | GET | `/v2/book/{book_uuid}/cash_flow_risk_score` | **Path:** `book_uuid` |
| SMB analytics (Excel) | GET | `/v2/book/{book_uuid}/lender_analytics/xlsx` | **Path:** `book_uuid`. Returns `.xlsx` binary. |
| Bank statement income calculator | GET | `/v2/book/{book_uuid}/income/bank-statement-v2` | **Path:** `book_uuid` |
| Bank statement income calculator (Excel) | GET | `/v2/book/{book_uuid}/income/bank-statement-v2/xlsx` | **Path:** `book_uuid`. Returns `.xlsx` binary. |

> The Excel export for BSIC is its own endpoint (`.../xlsx`) — not an `Accept` header on the JSON endpoint.

---

## Income

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Income calculations | GET | `/v2/book/{book_uuid}/income-calculations` | **Path:** `book_uuid`; **Query (optional):** `guideline` (`FANNIE_MAE`, `FREDDIE_MAC`, `FHA`, `VA`, `USDA`) |
| Income summary | GET | `/v2/book/{book_uuid}/income/summary` | **Path:** `book_uuid`; **Query (optional):** `guideline` |
| Configure income entity | POST | `/v2/book/{book_uuid}/income/entity_config` | **Path:** `book_uuid`; **Body (JSON):** `entity_details`, `borrower_details`, `xid`, `employment_start_date`, `income_type` |
| Save income guideline | PUT | `/v2/book/{book_uuid}/income-guideline` | **Path:** `book_uuid`; **Query (optional):** `guideline` |
| Calculate Fannie Mae self-employed income | POST | `/v2/book/{book_uuid}/income/self-employed/calculate` | **Path:** `book_uuid`; **Body (JSON):** `borrower_uuid`, `business_uuid`, `income_guideline`, `meta_info` |

> Path naming is inconsistent on the public docs: most income endpoints sit under `/income/...` (slash) but `income-calculations` and `income-guideline` use a hyphen. Match the docs exactly — the live API doesn't accept the wrong shape.

---

## Business History

Business-level views aggregated across books for a known business identifier.

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Business identifier | GET | `/v2/book/{book_uuid}/business` | **Path:** `book_uuid` |
| Business overview | GET | `/v1/businesses/{business_id}` | **Path:** `business_id` |
| Business summary | GET | `/v1/businesses/{business_id}/summary` | **Path:** `business_id`; **Query (optional):** `begin_date`, `end_date`, `updated_since` |
| Business transactions | GET | `/v1/businesses/{business_id}/transactions` | **Path:** `business_id`; **Query (optional):** `offset`, `limit`, `start_date`, `end_date`, `updated_since` |

---

## Tag Management

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Create tag | POST | `/v2/analytics/tags` | **Body (JSON):** `name`, `description`, `color`, `customization` |
| Retrieve all tags | GET | `/v2/analytics/tags` | **Query (optional):** `tag_type` |
| Retrieve a tag | GET | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` |
| Modify tag | PUT | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid`; **Body (JSON):** `name`, `description`, `color`, `customization` |
| Delete tag | DELETE | `/v2/analytics/tags/{tag_uuid}` | **Path:** `tag_uuid` |
| Retrieve revenue deduction tags | GET | `/v2/analytics/revenue-deduction-tags` | None |
| Update revenue deduction tag | PUT | `/v2/analytics/revenue-deduction-tags` | **Body (JSON):** `revenue_deduction_tags` (array of strings) |
| Override transaction tag | PUT | `/v2/analytics/book/{book_uuid}/transactions` | **Path:** `book_uuid`; **Body (JSON):** `txns` (array) |

---

## Encore (Book Copy)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Create Book copy jobs | POST | `/v1/book/copy-jobs` | **Body (JSON):** array of copy requests (max 50) |
| List Book copy jobs | GET | `/v1/book/copy-jobs` | **Query (optional):** `job_type`, `org_uuid`, `offset`, `limit` |
| Accept Book copy jobs | POST | `/v1/book/copy-jobs/{job_id}/accept` | **Path:** `job_id`; **Body (JSON):** `book_name` |
| Reject Book copy jobs | POST | `/v1/book/copy-jobs/{job_id}/reject` | **Path:** `job_id` |
| Run automated cash flow kick-outs | POST | `/v1/book/copy-jobs/run-kickouts` | None |
| Retrieve Book copy settings | GET | `/v1/settings/book-copy` | None |

---

## Webhooks

Webhook subscriptions and event delivery. Use **Org-level** webhooks for new integrations; the legacy account-level set still works but is superseded.

### Org Level Webhooks

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Add webhook | POST | `/v1/account/settings/webhook` | **Body (JSON):** `url`, `events` (array of event names) |
| List webhooks | GET | `/v1/account/settings/webhooks` | None |
| Retrieve webhook | GET | `/v1/account/settings/webhook/{webhook_uuid}` | **Path:** `webhook_uuid` |
| Update webhook | POST | `/v1/account/settings/webhook/{webhook_uuid}/update` | **Path:** `webhook_uuid`; **Body (JSON):** `url`, `events` |
| Delete webhook | DELETE | `/v1/account/settings/webhook/{webhook_uuid}/delete` | **Path:** `webhook_uuid` |
| List webhook events | GET | `/v1/account/settings/webhook/{webhook_uuid}/events` | **Path:** `webhook_uuid` |
| Test webhook | POST | `/v1/account/settings/webhook/{webhook_uuid}/test` | **Path:** `webhook_uuid`; **Body (JSON):** `event_uuid` |
| Configure webhook secret | POST | `/v1/account/settings/webhook/{webhook_uuid}/rotate-secret` | **Path:** `webhook_uuid`; **Body (JSON):** `secret_key` |

> Update is **POST** to `.../update` and delete is **DELETE** to `.../delete` — both use the action-suffix style, not a method on the resource URL. Path segment is `webhook` (singular) for the per-webhook routes; `webhooks` (plural) only for the list endpoint.

### Account-level Webhooks (legacy)

| Endpoint | Method | Path | Input |
|----------|--------|------|-------|
| Configure webhook | POST | `/v1/account/settings/update/webhook_endpoint` | **Body (JSON):** `webhook_endpoint`, `event` (array of `WebhookEventType`) |
| Get webhook configuration | GET | `/v1/account/settings/webhook_details` | None |
| Test webhook | GET | `/v1/account/settings/test_webhook_endpoint` | None |
| Configure webhook secret | POST | `/v1/account/settings/webhook/rotate-secret` | **Body (JSON):** `secret_key` |

Only one model can be active per tenant — Org-level or account-level, not both. See `references/webhooks.md` for event names, payloads, and signature verification.

---

## Input Type Legend

| Label | Meaning |
|-------|---------|
| **Path:** | URL path parameter — value is embedded in the URL (e.g., `/v1/book/{pk}`) |
| **Query:** | URL query parameter — appended as `?key=value` |
| **Query (optional):** | Optional URL query parameter |
| **Body (JSON):** | Request body sent as `application/json` |
| **Body (form-encoded):** | Request body sent as `application/x-www-form-urlencoded` |
| **Form (multipart):** | Request body sent as `multipart/form-data` (file uploads) |
| **Header:** | Custom request header |
| None | No parameters required |
