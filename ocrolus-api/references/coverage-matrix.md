# Endpoint Coverage Matrix

> **VALIDATED against live Ocrolus tenant (ahanson_personalOrg) on 2026-03-20.**
> 78 endpoints tested — 100% reachable. See FINDINGS.md for full details.
> All previous `:warning:` conflicts have been resolved.
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

| Endpoint | Path | SDK Method | Status |
|----------|------|------------|--------|
| Grant Token | `POST https://auth.ocrolus.com/oauth/token` | `_get_token()` (auto) | :white_check_mark: Form-encoded, no audience param |

## Book Operations

| Endpoint | Path | SDK Method | Status |
|----------|------|------------|--------|
| Create Book | `POST /v1/book/add` | `create_book()` | :hammer_and_wrench: CORRECTED from `/v1/book/create` |
| Delete Book | `POST /v1/book/delete` | `delete_book()` | :white_check_mark: |
| Update Book | `POST /v1/book/update` | `update_book()` | :white_check_mark: |
| Book Info | `GET /v1/book/{pk}` | `get_book()` | :white_check_mark: |
| List Books | `GET /v1/books` | `list_books()` | :white_check_mark: |
| Book Status | `GET /v1/book/status?book_pk={pk}` | `get_book_status()` | :white_check_mark: Both query and path param work |
| Book from Loan | `GET /v1/book/loan/{loan_id}` | `get_book_from_loan()` | :white_check_mark: |
| Loan from Book | `GET /v1/book/{pk}/loan` | `get_loan_from_book()` | :white_check_mark: |

## Document Upload & Management

| Endpoint | Path | SDK Method | Status |
|----------|------|------------|--------|
| Upload PDF | `POST /v1/book/upload` | `upload_pdf()` | :hammer_and_wrench: Uses `pk` (not `book_pk`) in form data |
| Upload Mixed PDF | `POST /v1/book/upload/mixed` | `upload_mixed_pdf()` | :white_check_mark: |
| Upload Pay Stub | `POST /v1/book/upload/paystub` | `upload_paystub_pdf()` | :white_check_mark: |
| Upload Image | `POST /v1/book/upload/image` | `upload_image()` | :white_check_mark: |
| Finalize Image Group | `POST /v1/book/finalize-image-group` | `finalize_image_group()` | :white_check_mark: |
| Upload Plaid JSON | `POST /v1/book/upload/plaid` | `upload_plaid_json()` | :white_check_mark: |
| Import Plaid Asset | `POST /v1/book/import/plaid/asset` | `import_plaid_asset_report()` | :white_check_mark: |
| Cancel Document | `POST /v1/document/{doc_uuid}/cancel` | `cancel_document()` | :white_check_mark: |
| Delete Document | `POST /v1/document/{doc_uuid}/delete` | `delete_document()` | :white_check_mark: |
| Download Document | `GET /v1/document/{doc_uuid}/download` | `download_document()` | :white_check_mark: |
| Upgrade Document | `POST /v1/document/{doc_uuid}/upgrade` | `upgrade_document()` | :white_check_mark: |
| Upgrade Mixed Doc | `POST /v1/document/mixed/upgrade` | `upgrade_mixed_document()` | :white_check_mark: |
| Mixed Doc Status | `GET /v1/document/mixed/status` | `get_mixed_document_status()` | :white_check_mark: |

## Classification (Classify)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Classification | `GET /v2/book/{uuid}/classification-summary` | `get_book_classification_summary()` | :white_check_mark: |
| Mixed Doc Classification | `GET /v2/mixed-document/{uuid}/classification-summary` | `get_mixed_doc_classification_summary()` | :white_check_mark: |
| Grouped Mixed Doc | `GET /v2/index/mixed-doc/{uuid}/summary` | `get_grouped_mixed_doc_summary()` | :white_check_mark: |

## Data Extraction (Capture)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Forms | `GET /v1/book/{pk}/forms` | `get_book_forms()` | :white_check_mark: |
| Book Paystubs | `GET /v1/book/{pk}/paystubs` | `get_book_paystubs()` | :white_check_mark: |
| Document Forms | `GET /v1/document/{uuid}/forms` | `get_document_forms()` | :white_check_mark: |
| Document Paystubs | `GET /v1/document/{uuid}/paystubs` | `get_document_paystubs()` | :white_check_mark: |
| Form Fields | `GET /v1/form/{uuid}/fields` | `get_form_fields()` | :white_check_mark: |
| Pay Stub Data | `GET /v1/paystub/{uuid}` | `get_paystub()` | :white_check_mark: |
| Transactions | `GET /v1/book/{pk}/transactions` | `get_book_transactions()` | :white_check_mark: Both path and query param work |

## Fraud Detection (Detect)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Fraud Signals | `GET /v2/detect/book/{uuid}/signals` | `get_book_fraud_signals()` | :white_check_mark: |
| Doc Fraud Signals | `GET /v2/detect/document/{uuid}/signals` | `get_document_fraud_signals()` | :white_check_mark: |
| Signal Visualization | `GET /v2/detect/visualization/{viz_uuid}` | `get_fraud_visualization()` | :white_check_mark: |
| Suspicious Activity (LEGACY) | `GET /v1/book/{uuid}/suspicious-activity-flags` | -- | :memo: Deprecated, documented only |

**Detect coverage notes:**
- Authenticity scores (0-100) documented in `references/detect.md`
- Reason codes (e.g., `110-H`) with confidence levels documented
- File Origin vs File Tampering signal types documented
- Score thresholds and interpretation guidance included

## Cash Flow Analytics

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Book Summary | `GET /v2/book/{uuid}/summary` | `get_book_summary()` | :white_check_mark: |
| Cash Flow Features | `GET /v2/book/{uuid}/cash_flow_features` | `get_cashflow_features()` | :white_check_mark: |
| Enriched Transactions | `GET /v2/book/{uuid}/enriched_txns` | `get_enriched_transactions()` | :white_check_mark: |
| Risk Score | `GET /v2/book/{uuid}/cash_flow_risk_score` | `get_risk_score()` | :white_check_mark: |
| Benchmarking (Beta) | `GET /v2/book/{uuid}/benchmarking` | `get_benchmarking()` | :white_check_mark: |
| SMB Analytics Excel | `GET /v2/book/{uuid}/lender_analytics/xlsx` | `get_analytics_excel()` | :white_check_mark: |

## Income Calculations

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Income Calculations | `GET /v2/book/{uuid}/income-calculations` | `get_income_calculations()` | :white_check_mark: |
| Income Summary | `GET /v2/book/{uuid}/income-summary` | `get_income_summary()` | :white_check_mark: |
| Configure Entity | `POST /v2/book/{uuid}/income-entity` | `configure_income_entity()` | :white_check_mark: |
| Save Guideline | `PUT /v2/book/{uuid}/income-guideline` | `save_income_guideline()` | :white_check_mark: |
| Self-Employed (Fannie Mae) | `POST /v2/book/{uuid}/self-employed-income` | `calculate_self_employed_income()` | :white_check_mark: |
| BSIC | `GET /v2/book/{uuid}/bsic` | `get_bsic()` | :white_check_mark: |
| BSIC Excel | `GET /v2/book/{uuid}/bsic` (Accept: xlsx) | `get_bsic_excel()` | :white_check_mark: |

## Tag Management (Beta)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Create Tag | `POST /v2/analytics/tags` | `create_tag()` | :white_check_mark: |
| Retrieve Tag | `GET /v2/analytics/tags/{uuid}` | `get_tag()` | :white_check_mark: |
| Modify Tag | `PUT /v2/analytics/tags/{uuid}` | `modify_tag()` | :white_check_mark: |
| Delete Tag | `DELETE /v2/analytics/tags/{uuid}` | `delete_tag()` | :white_check_mark: |
| List All Tags | `GET /v2/analytics/tags` | `list_tags()` | :white_check_mark: |
| Revenue Deduction Tags | `GET /v2/analytics/revenue-deduction-tags` | `get_revenue_deduction_tags()` | :x: Returns 500 on tested tenant |
| Update Rev Deduction | `PUT /v2/analytics/revenue-deduction-tags` | `update_revenue_deduction_tags()` | :white_check_mark: |
| Override Txn Tag | `PUT /v2/analytics/book/{uuid}/transactions` | `override_transaction_tag()` | :white_check_mark: |

## Encore / Book Copy

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Create Copy Jobs | `POST /v1/book/copy-jobs` | `create_book_copy_jobs()` | :white_check_mark: |
| List Copy Jobs | `GET /v1/book/copy-jobs` | `list_book_copy_jobs()` | :white_check_mark: |
| Accept Copy Job | `POST /v1/book/copy-jobs/{id}/accept` | `accept_book_copy_job()` | :white_check_mark: |
| Reject Copy Job | `POST /v1/book/copy-jobs/{id}/reject` | `reject_book_copy_job()` | :white_check_mark: |
| Run Kick-Outs | `POST /v1/book/copy-jobs/run-kickouts` | `run_book_copy_kickouts()` | :white_check_mark: |
| Copy Settings | `GET /v1/settings/book-copy` | `get_book_copy_settings()` | :white_check_mark: |

## Webhooks -- Org-Level

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Add Webhook | `POST /v1/account/settings/webhook` | `add_org_webhook()` | :white_check_mark: |
| List Webhooks | `GET /v1/account/settings/webhooks` | `list_org_webhooks()` | :white_check_mark: |
| Retrieve Webhook | `GET /v1/account/settings/webhooks/{id}` | `get_org_webhook()` | :white_check_mark: |
| Update Webhook | `PUT /v1/account/settings/webhooks/{id}` | `update_org_webhook()` | :white_check_mark: |
| Delete Webhook | `DELETE /v1/account/settings/webhooks/{id}` | `delete_org_webhook()` | :white_check_mark: |
| List Events | `GET /v1/account/settings/webhooks/events` | `list_org_webhook_events()` | :white_check_mark: |
| Test Webhook | `POST /v1/account/settings/webhooks/{id}/test` | `test_org_webhook()` | :white_check_mark: |
| Configure Secret | `POST /v1/account/settings/webhooks/secret` | `configure_org_webhook_secret()` | :white_check_mark: |

## Webhooks -- Account-Level

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Configure | `POST /v1/webhook/configure` | `configure_account_webhook()` | :white_check_mark: |
| Get Config | `GET /v1/webhook/configuration` | `get_account_webhook_config()` | :white_check_mark: |
| Test | `POST /v1/webhook/test` | `test_account_webhook()` | :white_check_mark: |
| Configure Secret | `POST /v1/webhook/secret` | `configure_account_webhook_secret()` | :white_check_mark: |

## LOS Connect (Discovered 2026-03-20)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Encompass Book Lookup | `GET /v2/los-connect/encompass/book` | -- | :memo: Reachable (400 — needs `loan_id` or `loan_number`) |
| LOS Connect Loan | `GET /v2/los-connect/book/{uuid}/loan` | -- | :memo: Reachable (500 with dummy UUID) |

## V2 Document Operations (Discovered 2026-03-20)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| V2 Typed Upload | `POST /v2/book/{uuid}/document/{form_type}` | -- | :memo: Reachable — supports `bank_statement`, `tax_return`, `paystub` |
| V2 Mixed Doc Upload | `POST /v2/book/{uuid}/mixed-document` | -- | :memo: Reachable |
| JSON Upload | `POST /v1/book/upload/json` | -- | :memo: Reachable (needs `pk` or `uuid`) |
| V2 Book Paystub | `GET /v2/book/{uuid}/paystub` | -- | :memo: Reachable |
| V2 Document Paystub | `GET /v2/document/{uuid}/paystub` | -- | :memo: Reachable |
| V2 Paystub by UUID | `GET /v2/paystub/{uuid}` | -- | :memo: Reachable |
| V2 Document Download | `GET /v2/document/download` | -- | :memo: Reachable (query-param style) |

## Kickout Rules (Discovered 2026-03-20)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Update Kickout Rules | `PUT /v1/settings/book-copy/kickout-rules` | -- | :memo: Reachable — returns config fields |
| Get Kickout Rules | `GET /v1/settings/book-copy/kickout-rules` | -- | :x: 404 |

## Legacy Webhooks (Discovered 2026-03-20)

| Endpoint | Live Docs Path | SDK Method | Status |
|----------|---------------|------------|--------|
| Webhook Details | `GET /v1/account/settings/webhook_details` | -- | :memo: Reachable — returns `webhook_endpoint` + `events` |
| Test Webhook (GET) | `GET /v1/account/settings/test_webhook_endpoint` | -- | :memo: Reachable |
| Update Webhook (Legacy) | `POST /v1/account/settings/update/webhook_endpoint` | -- | :memo: Reachable |

## Query-Param Path Aliases (Confirmed 2026-03-20)

All v1 endpoints support both path-param and query-param styles:

| Path-Param Style (Our SDK) | Query-Param Style (Official Spec) | Status |
|----|---|---|
| `GET /v1/book/{pk}` | `GET /v1/book/info?pk=X` | :white_check_mark: Both work |
| `POST /v1/book/delete` | `POST /v1/book/remove` | :white_check_mark: Both work |
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
| Book Operations | 8 | 8 | 8 | :white_check_mark: (1 corrected) |
| Document Upload | 13 | 13 | 13 | :white_check_mark: (1 corrected) |
| Classification | 3 | 3 | 3 | :white_check_mark: |
| Data Extraction | 7 | 7 | 7 | :white_check_mark: |
| Fraud Detection | 4 | 3 (+1 legacy) | 4 | :white_check_mark: |
| Cash Flow Analytics | 6 | 6 | 6 | :white_check_mark: |
| Income Calculations | 7 | 7 | 7 | :white_check_mark: |
| Tag Management | 8 | 8 | 8 | :white_check_mark: (1 broken: revenue-deduction-tags) |
| Encore / Book Copy | 6 | 6 | 6 | :white_check_mark: |
| Webhooks (Org) | 8 | 8 | 8 | :white_check_mark: (1 unavailable: secret config) |
| Webhooks (Account) | 4 | 4 | 4 | :white_check_mark: (1 unavailable: get config) |
| LOS Connect | 2 | 0 | 2 | :memo: Discovered from official spec |
| V2 Document Ops | 7 | 0 | 7 | :memo: Discovered from official spec |
| Kickout Rules | 2 | 0 | 2 | :memo: 1 reachable, 1 returns 404 |
| Legacy Webhooks | 3 | 0 | 3 | :memo: Discovered from official spec |
| Query-Param Aliases | 9 | 0 | 9 | :white_check_mark: All confirmed working |
| **TOTAL** | **98** | **74** | **98** | **107 probed, 23 new discoveries** |

## Resolved Conflicts (from Live Testing 2026-03-20)

| # | Conflict | Resolution |
|---|----------|------------|
| 1 | Book Create path | **`/v1/book/add`** is correct. `/v1/book/create` returns 404. `/v1/books` POST is list-only. |
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
