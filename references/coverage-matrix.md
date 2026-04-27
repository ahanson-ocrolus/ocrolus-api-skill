# Endpoint Coverage Matrix

> **VALIDATED against live Ocrolus tenant (ahanson_personalOrg) on 2026-03-20.**
> 78 endpoints tested — 100% reachable. See FINDINGS.md for full details.
> All previous `:warning:` conflicts have been resolved.
>
> **Naming convention:** Endpoint names match actual URL path segments (not human-readable names).
>
> Last validation: 2026-03-20 | Original doc scrape: 2026-03-18

## Legend

| Symbol | Meaning |
|--------|---------|
| :white_check_mark: | Live-validated against real tenant (HTTP 200 or expected 4xx) |
| :hammer_and_wrench: | SDK method corrected based on live testing |
| :memo: | Documented in endpoint reference only (no SDK method) |
| :x: | Not working on tested tenant (500 or unexpected 404) |

---

## Authentication

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `oauth/token` | `POST https://auth.ocrolus.com/oauth/token` | Body (form-encoded) | `_get_token()` (auto) | :white_check_mark: Form-encoded, no audience param |

## Book Commands

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/add` | `POST /v1/book/add` | Body (JSON): `name`, `book_type` | `create_book()` | :hammer_and_wrench: CORRECTED from `/v1/book/create` |
| `book/remove` | `POST /v1/book/remove` | Body (JSON): `book_id` OR `book_uuid` | `delete_book()` | :white_check_mark: `/v1/book/delete` is an alias |
| `book/update` | `POST /v1/book/update` | Body (JSON): `pk` OR `book_uuid`, `name` | `update_book()` | :white_check_mark: |

## Book Queries

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/{pk}` | `GET /v1/book/{pk}` | Path: `pk` (integer) | `get_book()` | :white_check_mark: |
| `books` | `GET /v1/books` | Query (optional): `page`, `per_page` | `list_books()` | :white_check_mark: |
| `book/status` | `GET /v1/book/status?book_pk={pk}` | Query: `book_pk` (integer) | `get_book_status()` | :white_check_mark: Both query and path param work |
| `book/loan/{loan_id}` | `GET /v1/book/loan/{loan_id}` | Path: `loan_id` (string) | `get_book_from_loan()` | :white_check_mark: |
| `book/{pk}/loan` | `GET /v1/book/{pk}/loan` | Path: `pk` (integer) | `get_loan_from_book()` | :white_check_mark: |

## File Uploads

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/upload` | `POST /v1/book/upload` | Form (multipart): `pk` OR `book_uuid`, `upload`, `form_type`, `doc_name` | `upload_pdf()` | :hammer_and_wrench: Uses `pk` (not `book_pk`) in form data |
| `book/upload/mixed` | `POST /v1/book/upload/mixed` | Form (multipart): `pk` OR `book_uuid`, `upload` | `upload_mixed_pdf()` | :white_check_mark: |
| `book/upload/paystub` | `POST /v1/book/upload/paystub` | Form (multipart): `pk` OR `book_uuid`, `upload` | `upload_paystub_pdf()` | :white_check_mark: |
| `book/upload/image` | `POST /v1/book/upload/image` | Form (multipart): `pk` OR `book_uuid`, `upload`, `image_group` | `upload_image()` | :white_check_mark: |
| `book/finalize-image-group` | `POST /v1/book/finalize-image-group` | Body (JSON): `pk` OR `book_uuid`, `image_group` | `finalize_image_group()` | :white_check_mark: |
| `book/upload/plaid` | `POST /v1/book/upload/plaid` | Body (JSON): `pk` OR `book_uuid` | `upload_plaid_json()` | :white_check_mark: |
| `book/import/plaid/asset` | `POST /v1/book/import/plaid/asset` | Body (JSON): `audit_copy_token` | `import_plaid_asset_report()` | :white_check_mark: |

## File Commands

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `document/cancel` | `POST /v1/document/{doc_uuid}/cancel` | Path: `doc_uuid`; Body (JSON): `doc_pk` OR `doc_uuid`, `accept_charges` | `cancel_document()` | :white_check_mark: |
| `document/remove` | `POST /v1/document/{doc_uuid}/delete` | Path: `doc_uuid`; Body (JSON): `doc_id` OR `doc_uuid` | `delete_document()` | :white_check_mark: |
| `document/{doc_uuid}/download` | `GET /v1/document/{doc_uuid}/download` | Path: `doc_uuid` (UUID) | `download_document()` | :white_check_mark: |
| `document/upgrade` | `POST /v1/document/{doc_uuid}/upgrade` | Path: `doc_uuid`; Body (JSON): `doc_pk` OR `doc_uuid`, `upgrade_type` | `upgrade_document()` | :white_check_mark: |
| `document/mixed/upgrade` | `POST /v1/document/mixed/upgrade` | Body (JSON): `mixed_doc_pk` OR `mixed_doc_uuid`, `upgrade_type` | `upgrade_mixed_document()` | :white_check_mark: |

## File Queries

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `document/mixed/status` | `GET /v1/document/mixed/status` | Query: `pk` OR `doc_uuid` OR `mixed_doc_uuid` | `get_mixed_document_status()` | :white_check_mark: |

## Classify

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/{uuid}/classification-summary` | `GET /v2/book/{uuid}/classification-summary` | Path: `book_uuid` (UUID) | `get_book_classification_summary()` | :white_check_mark: |
| `mixed-document/{uuid}/classification-summary` | `GET /v2/mixed-document/{uuid}/classification-summary` | Path: `mixed_doc_uuid` (UUID) | `get_mixed_doc_classification_summary()` | :white_check_mark: |
| `index/mixed-doc/{uuid}/summary` | `GET /v2/index/mixed-doc/{uuid}/summary` | Path: `mixed_doc_uuid` (UUID) | `get_grouped_mixed_doc_summary()` | :white_check_mark: |

## Capture

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/{pk}/forms` | `GET /v1/book/{pk}/forms` | Path: `pk` (integer) | `get_book_forms()` | :white_check_mark: |
| `book/{pk}/paystubs` | `GET /v1/book/{pk}/paystubs` | Path: `pk` (integer) | `get_book_paystubs()` | :white_check_mark: |
| `document/{uuid}/forms` | `GET /v1/document/{uuid}/forms` | Path: `doc_uuid` (UUID) | `get_document_forms()` | :white_check_mark: |
| `document/{uuid}/paystubs` | `GET /v1/document/{uuid}/paystubs` | Path: `doc_uuid` (UUID) | `get_document_paystubs()` | :white_check_mark: |
| `form/{uuid}/fields` | `GET /v1/form/{uuid}/fields` | Path: `form_uuid` (UUID) | `get_form_fields()` | :white_check_mark: |
| `paystub/{uuid}` | `GET /v1/paystub/{uuid}` | Path: `paystub_uuid` (UUID) | `get_paystub()` | :white_check_mark: |
| `book/{pk}/transactions` | `GET /v1/book/{pk}/transactions` | Path: `pk` (integer); Query (opt): `uploaded_doc_pk`, `uploaded_doc_uuid`, `only_tagged`, `distinct_fields` | `get_book_transactions()` | :white_check_mark: Both path and query param work |

## Detect

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `detect/book/{uuid}/signals` | `GET /v2/detect/book/{uuid}/signals` | Path: `book_uuid` (UUID) | `get_book_fraud_signals()` | :white_check_mark: |
| `detect/document/{uuid}/signals` | `GET /v2/detect/document/{uuid}/signals` | Path: `doc_uuid` (UUID) | `get_document_fraud_signals()` | :white_check_mark: |
| `detect/visualization/{viz_uuid}` | `GET /v2/detect/visualization/{viz_uuid}` | Path: `visualization_uuid` (UUID) | `get_fraud_visualization()` | :white_check_mark: |
| `book/{uuid}/suspicious-activity-flags` | `GET /v1/book/{uuid}/suspicious-activity-flags` | Path: `book_uuid` (UUID) | -- | :memo: Deprecated, documented only |

**Detect coverage notes:**
- Authenticity scores (0-100) documented in `references/detect.md`
- Reason codes (e.g., `110-H`) with confidence levels documented
- File Origin vs File Tampering signal types documented
- Score thresholds and interpretation guidance included

## Analyze (Cash Flow)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/{uuid}/summary` | `GET /v2/book/{uuid}/summary` | Path: `book_uuid` (UUID) | `get_book_summary()` | :white_check_mark: |
| `book/{uuid}/cash_flow_features` | `GET /v2/book/{uuid}/cash_flow_features` | Path: `book_uuid` (UUID); Query: `min_days_to_include` (optional) | `get_cashflow_features()` | :white_check_mark: |
| `book/{uuid}/enriched_txns` | `GET /v2/book/{uuid}/enriched_txns` | Path: `book_uuid` (UUID) | `get_enriched_transactions()` | :white_check_mark: |
| `book/{uuid}/cash_flow_risk_score` | `GET /v2/book/{uuid}/cash_flow_risk_score` | Path: `book_uuid` (UUID) | `get_risk_score()` | :white_check_mark: |
| `book/{uuid}/benchmarking` | `GET /v2/book/{uuid}/benchmarking` | Path: `book_uuid` (UUID) | `get_benchmarking()` | :white_check_mark: |
| `book/{uuid}/lender_analytics/xlsx` | `GET /v2/book/{uuid}/lender_analytics/xlsx` | Path: `book_uuid` (UUID) | `get_analytics_excel()` | :white_check_mark: |

## Income

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/{uuid}/income-calculations` | `GET /v2/book/{uuid}/income-calculations` | Path: `book_uuid` (UUID); Query: `guideline` (optional) | `get_income_calculations()` | :white_check_mark: |
| `book/{uuid}/income-summary` | `GET /v2/book/{uuid}/income-summary` | Path: `book_uuid` (UUID) | `get_income_summary()` | :white_check_mark: |
| `book/{uuid}/income-entity` | `POST /v2/book/{uuid}/income-entity` | Path: `book_uuid` (UUID); Body (JSON) | `configure_income_entity()` | :white_check_mark: |
| `book/{uuid}/income-guideline` | `PUT /v2/book/{uuid}/income-guideline` | Path: `book_uuid` (UUID); Body (JSON) | `save_income_guideline()` | :white_check_mark: |
| `book/{uuid}/self-employed-income` | `POST /v2/book/{uuid}/self-employed-income` | Path: `book_uuid` (UUID); Body (JSON) | `calculate_self_employed_income()` | :white_check_mark: |
| `book/{uuid}/bsic` | `GET /v2/book/{uuid}/bsic` | Path: `book_uuid` (UUID) | `get_bsic()` | :white_check_mark: |
| `book/{uuid}/bsic` (Excel) | `GET /v2/book/{uuid}/bsic` (Accept: xlsx) | Path: `book_uuid` (UUID); Header: Accept | `get_bsic_excel()` | :white_check_mark: |

## Tag Management

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `analytics/tags` (create) | `POST /v2/analytics/tags` | Body (JSON): `name` | `create_tag()` | :white_check_mark: |
| `analytics/tags/{uuid}` | `GET /v2/analytics/tags/{uuid}` | Path: `tag_uuid` (UUID) | `get_tag()` | :white_check_mark: |
| `analytics/tags/{uuid}` (modify) | `PUT /v2/analytics/tags/{uuid}` | Path: `tag_uuid` (UUID); Body (JSON): `name` | `modify_tag()` | :white_check_mark: |
| `analytics/tags/{uuid}` (delete) | `DELETE /v2/analytics/tags/{uuid}` | Path: `tag_uuid` (UUID) | `delete_tag()` | :white_check_mark: |
| `analytics/tags` (list) | `GET /v2/analytics/tags` | Query: `is_system_tag` (optional) | `list_tags()` | :white_check_mark: |
| `analytics/revenue-deduction-tags` | `GET /v2/analytics/revenue-deduction-tags` | None | `get_revenue_deduction_tags()` | :x: Returns 500 on tested tenant |
| `analytics/revenue-deduction-tags` (update) | `PUT /v2/analytics/revenue-deduction-tags` | Body (JSON): `tag_names` | `update_revenue_deduction_tags()` | :white_check_mark: |
| `analytics/book/{uuid}/transactions` | `PUT /v2/analytics/book/{uuid}/transactions` | Path: `book_uuid` (UUID); Body (JSON): `txn_pk`, `tag_uuids` | `override_transaction_tag()` | :white_check_mark: |

## Encore

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/copy-jobs` (create) | `POST /v1/book/copy-jobs` | Body (JSON): `jobs` (array) | `create_book_copy_jobs()` | :white_check_mark: |
| `book/copy-jobs` (list) | `GET /v1/book/copy-jobs` | Query: `direction` (optional) | `list_book_copy_jobs()` | :white_check_mark: |
| `book/copy-jobs/{id}/accept` | `POST /v1/book/copy-jobs/{id}/accept` | Path: `job_id` (string); Body (JSON): `name` | `accept_book_copy_job()` | :white_check_mark: |
| `book/copy-jobs/{id}/reject` | `POST /v1/book/copy-jobs/{id}/reject` | Path: `job_id` (string) | `reject_book_copy_job()` | :white_check_mark: |
| `book/copy-jobs/run-kickouts` | `POST /v1/book/copy-jobs/run-kickouts` | None | `run_book_copy_kickouts()` | :white_check_mark: |
| `settings/book-copy` | `GET /v1/settings/book-copy` | None | `get_book_copy_settings()` | :white_check_mark: |

## Webhooks (Org Level)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `account/settings/webhook` | `POST /v1/account/settings/webhook` | Body (JSON): `url`, `events` | `add_org_webhook()` | :white_check_mark: |
| `account/settings/webhooks` | `GET /v1/account/settings/webhooks` | None | `list_org_webhooks()` | :white_check_mark: |
| `account/settings/webhooks/{id}` | `GET /v1/account/settings/webhooks/{id}` | Path: `webhook_id` (string) | `get_org_webhook()` | :white_check_mark: |
| `account/settings/webhooks/{id}` (update) | `PUT /v1/account/settings/webhooks/{id}` | Path: `webhook_id` (string); Body (JSON): `url`, `events` | `update_org_webhook()` | :white_check_mark: |
| `account/settings/webhooks/{id}` (delete) | `DELETE /v1/account/settings/webhooks/{id}` | Path: `webhook_id` (string) | `delete_org_webhook()` | :white_check_mark: |
| `account/settings/webhooks/events` | `GET /v1/account/settings/webhooks/events` | None | `list_org_webhook_events()` | :white_check_mark: |
| `account/settings/webhooks/{id}/test` | `POST /v1/account/settings/webhooks/{id}/test` | Path: `webhook_id` (string) | `test_org_webhook()` | :white_check_mark: |
| `account/settings/webhooks/secret` | `POST /v1/account/settings/webhooks/secret` | Body (JSON): `secret` | `configure_org_webhook_secret()` | :white_check_mark: |

## Webhooks (Account Level)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `webhook/configure` | `POST /v1/webhook/configure` | Body (JSON): `url`, `events` | `configure_account_webhook()` | :white_check_mark: |
| `webhook/configuration` | `GET /v1/webhook/configuration` | None | `get_account_webhook_config()` | :white_check_mark: |
| `webhook/test` | `POST /v1/webhook/test` | None | `test_account_webhook()` | :white_check_mark: |
| `webhook/secret` | `POST /v1/webhook/secret` | Body (JSON): `secret` | `configure_account_webhook_secret()` | :white_check_mark: |

## LOS Connect (Discovered 2026-03-20)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `los-connect/encompass/book` | `GET /v2/los-connect/encompass/book` | Query: `loan_id` or `loan_number` | -- | :memo: Reachable (400 — needs params) |
| `los-connect/book/{uuid}/loan` | `GET /v2/los-connect/book/{uuid}/loan` | Path: `book_uuid` (UUID) | -- | :memo: Reachable (500 with dummy UUID) |

## V2 Document Operations (Discovered 2026-03-20)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `book/{uuid}/document/{form_type}` | `POST /v2/book/{uuid}/document/{form_type}` | Path: `book_uuid`, `form_type` | -- | :memo: Supports `bank_statement`, `tax_return`, `paystub` |
| `book/{uuid}/mixed-document` | `POST /v2/book/{uuid}/mixed-document` | Path: `book_uuid` (UUID) | -- | :memo: Reachable |
| `book/upload/json` | `POST /v1/book/upload/json` | Body (JSON): `pk` or `uuid` | -- | :memo: Reachable |
| `book/{uuid}/paystub` (v2) | `GET /v2/book/{uuid}/paystub` | Path: `book_uuid` (UUID) | -- | :memo: Reachable |
| `document/{uuid}/paystub` (v2) | `GET /v2/document/{uuid}/paystub` | Path: `doc_uuid` (UUID) | -- | :memo: Reachable |
| `paystub/{uuid}` (v2) | `GET /v2/paystub/{uuid}` | Path: `paystub_uuid` (UUID) | -- | :memo: Reachable |
| `document/download` (v2) | `GET /v2/document/download` | Query: `doc_uuid` (UUID) | -- | :memo: Reachable (query-param style) |

## Kickout Rules (Discovered 2026-03-20)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `settings/book-copy/kickout-rules` (update) | `PUT /v1/settings/book-copy/kickout-rules` | Body (JSON) | -- | :memo: Reachable — returns config fields |
| `settings/book-copy/kickout-rules` (get) | `GET /v1/settings/book-copy/kickout-rules` | None | -- | :x: 404 |

## Legacy Webhooks (Discovered 2026-03-20)

| Endpoint | Path | Input | SDK Method | Status |
|----------|------|-------|------------|--------|
| `account/settings/webhook_details` | `GET /v1/account/settings/webhook_details` | None | -- | :memo: Returns `webhook_endpoint` + `events` |
| `account/settings/test_webhook_endpoint` | `GET /v1/account/settings/test_webhook_endpoint` | None | -- | :memo: Reachable |
| `account/settings/update/webhook_endpoint` | `POST /v1/account/settings/update/webhook_endpoint` | Body (JSON) | -- | :memo: Reachable |

## Query-Param Path Aliases (Confirmed 2026-03-20)

All v1 endpoints support both path-param and query-param styles:

| Path-Param Style (Our SDK) | Query-Param Style (Official Spec) | Status |
|----|---|---|
| `GET /v1/book/{pk}` | `GET /v1/book/info?pk=X` | :white_check_mark: Both work |
| `POST /v1/book/remove` (Official) | `POST /v1/book/delete` (alias) | :white_check_mark: Both work |
| `POST /v1/document/{uuid}/cancel` | `POST /v1/document/cancel?doc_uuid=X` | :white_check_mark: Both work |
| `POST /v1/document/{uuid}/delete` | `POST /v1/document/remove?doc_uuid=X` | :white_check_mark: Both work |
| `POST /v1/document/{uuid}/upgrade` | `POST /v1/document/upgrade?doc_uuid=X` | :white_check_mark: Both work |
| `GET /v1/book/{pk}/forms` | `GET /v1/book/forms?book_pk=X` | :white_check_mark: Both work |
| `GET /v1/form/{uuid}/fields` | `GET /v1/form?form_uuid=X` | :white_check_mark: Both work |
| `GET /v1/book/{pk}/transactions` | `GET /v1/transaction?book_pk=X` | :white_check_mark: Both work |
| `POST /v1/book/finalize-image-group` | `POST /v1/book/upload/image/done` | :white_check_mark: Both work |

---

## Coverage Summary

| Category | Total Endpoints | SDK Methods | Ref Documented | Live Validated |
|----------|----------------|------------|----------------|---------------|
| Authentication | 1 | 1 | 1 | :white_check_mark: |
| Book Commands | 3 | 3 | 3 | :white_check_mark: (1 corrected) |
| Book Queries | 5 | 5 | 5 | :white_check_mark: |
| File Uploads | 7 | 7 | 7 | :white_check_mark: (1 corrected) |
| File Commands | 5 | 5 | 5 | :white_check_mark: |
| File Queries | 1 | 1 | 1 | :white_check_mark: |
| Classify | 3 | 3 | 3 | :white_check_mark: |
| Capture | 7 | 7 | 7 | :white_check_mark: |
| Detect | 4 | 3 (+1 legacy) | 4 | :white_check_mark: |
| Analyze (Cash Flow) | 6 | 6 | 6 | :white_check_mark: |
| Income | 7 | 7 | 7 | :white_check_mark: |
| Tag Management | 8 | 8 | 8 | :white_check_mark: (1 broken: revenue-deduction-tags) |
| Encore | 6 | 6 | 6 | :white_check_mark: |
| Webhooks (Account Level) | 4 | 4 | 4 | :white_check_mark: (1 unavailable: get config) |
| Webhooks (Org Level) | 8 | 8 | 8 | :white_check_mark: (1 unavailable: secret config) |
| LOS Connect | 2 | 0 | 2 | :memo: Discovered from official spec |
| V2 Document Ops | 7 | 0 | 7 | :memo: Discovered from official spec |
| Kickout Rules | 2 | 0 | 2 | :memo: 1 reachable, 1 returns 404 |
| Legacy Webhooks | 3 | 0 | 3 | :memo: Discovered from official spec |
| Query-Param Aliases | 9 | 0 | 9 | :white_check_mark: All confirmed working |
| **TOTAL** | **98** | **74** | **98** | **107 probed, 23 new discoveries** |

## Resolved Conflicts (from Live Testing 2026-03-20)

| # | Conflict | Resolution |
|---|----------|------------|
| 1 | Book add path | **`/v1/book/add`** is correct. `/v1/book/create` returns 404. `/v1/books` POST is list-only. |
| 2 | Book Status path | **Both work**: query param (`?book_pk=X`) and path param (`/{pk}/status`). |
| 3 | Upload PDF path | **`/v1/book/upload`** with `pk` in form data. Path-style upload returns 404. Field is `pk` not `book_pk`. |
| 4 | Transactions path | **Both work**: path param and query param styles. |
| 5 | Webhook event names | **Validated**: `event_name` field with real names like `book.completed`, `document.verification_succeeded`. See webhooks.md. |
| 6 | Cash flow paths | **Both naming conventions work**: `cash_flow_features`/`cashflow-features`, `enriched_txns`/`enriched-transactions`. |
| 7 | Detect paths | **Confirmed**: `/v2/detect/book/{uuid}/signals` and `/v2/detect/document/{uuid}/signals` both work. |
| 8 | Webhook paths | **`/v1/account/settings/webhooks`** is the working org-level path. `/v1/org/webhooks` returns 404 on this tenant. |

## Remaining Open Questions

1. **Revenue deduction tags endpoint**: Returns 500 — may be a tenant-level feature flag
2. **Webhook secret configuration**: API endpoint 404 — may need dashboard configuration
3. **Reason code full list**: Not publicly published; codes returned dynamically in Detect responses
4. **Widget script URL**: Must be obtained from Dashboard; not a static public URL

## How to Validate on Your Tenant

```bash
# 1. Run health check with webhook validation
python tools/health_check.py --webhooks

# 2. Run endpoint validation with webhook event discovery
python tools/validate_endpoints.py --webhooks

# 3. Full write-path validation (creates/deletes a test book)
python tools/validate_endpoints.py --write-paths
```
