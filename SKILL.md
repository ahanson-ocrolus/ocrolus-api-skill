---
name: ocrolus-api
description: "Build integrations against the Ocrolus document automation API. Use when an application uploads documents (bank statements, pay stubs, tax forms, W-2s) to Ocrolus and reads back classification, captured fields, fraud signals, cash flow analytics, or income calculations. Triggers: \"Ocrolus\", \"ocrolus api\", \"ocrolus webhook\", \"ocrolus widget\", and any reference to the Ocrolus capabilities Classify, Capture, Detect, Analyze, Income, Encore, or transaction tags. Do NOT trigger for generic document/OCR work that does not specifically target Ocrolus."
license: MIT
metadata:
  version: 1.0.0
  source_of_truth: https://docs.ocrolus.com/reference/ocrolus-api-intro
---

# Ocrolus API

Ocrolus turns financial documents into structured, decision-ready data. Integrations are built around five capabilities:

| Capability | What it gives you |
|------------|-------------------|
| **Classify** | Identify 300+ document types with confidence scores |
| **Capture** | Extract structured fields and transactions |
| **Detect** | Fraud signals, authenticity scores, and reason codes |
| **Analyze** | Cash flow features, enriched transactions, risk scoring |
| **Income** | Income calculations, BSIC, self-employed income |

Most workflows: create a **Book**, upload documents, wait for processing (webhooks recommended), then read results.

Reference: <https://docs.ocrolus.com/reference> · API Guide: <https://docs.ocrolus.com/docs/guide>

## Hosts and Authentication

| Purpose | Base URL |
|---------|----------|
| API | `https://api.ocrolus.com` |
| OAuth token | `https://auth.ocrolus.com/oauth/token` |
| Widget token | `https://widget.ocrolus.com/v1/widget/{uuid}/token` |

OAuth 2.0 client credentials → JWT bearer (24-hour expiry). The token request is **form-encoded** and does **not** take an `audience` parameter:

```bash
curl -X POST https://auth.ocrolus.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$OCROLUS_CLIENT_ID" \
  -d "client_secret=$OCROLUS_CLIENT_SECRET"
```

```python
import requests
token = requests.post(
    "https://auth.ocrolus.com/oauth/token",
    data={
        "grant_type": "client_credentials",
        "client_id": OCROLUS_CLIENT_ID,
        "client_secret": OCROLUS_CLIENT_SECRET,
    },
).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

Every other request sends `Authorization: Bearer <token>`.

## Book Identifiers

A Book is the container for documents in a single application/case. When you create one, Ocrolus returns two identifiers:

| Identifier | Type | Used by |
|------------|------|---------|
| `pk` | Integer | v1 endpoints (uploads, forms, transactions, status) |
| `uuid` | UUID string | v2 endpoints (Classify, Detect, Analyze, Income) |

Persist both. v1 endpoints reject UUIDs; v2 endpoints reject integer pks. Where v1 endpoints accept either, the form/JSON field is named `pk` (integer) or `book_uuid` (UUID).

## Processing Mode — `book_class`

Set `book_class` **when creating the book** (`POST /v1/book/add`). It cannot be changed after creation. Map the user's natural-language request to one of these four values:

| User says… | `book_class` value | What it means |
|------------|--------------------|---------------|
| "instant", "instantly", "machine only", "automated", "no human review", "fast", "Instant" | **`INSTANT`** | Machine-only processing through the full pipeline (classify → capture → analyze). Fastest result, no human verification step. |
| "complete", "HITL", "human in the loop", "human verification", "human-verified", "highest accuracy", "Complete" | **`COMPLETE`** | Full pipeline with human review of low-confidence fields. Slower but higher accuracy. **Default when `book_class` is omitted.** |
| "classify only", "stop after classification", "just classify", "classification only", "no capture" | **`INSTANT_CLASSIFY_ONLY`** *(rare)* | Stops processing after classification. Listen for the `book.classified` webhook and route each document yourself based on its `form_type`. |
| "ISO app capture only", "classify everything, capture ISO" | **`INSTANT_CLASSIFY_ISO_CAPTURE`** *(rare)* | Same as `INSTANT_CLASSIFY_ONLY` for every document **except ISO applications**, which continue through capture. Listen for `book.classified` for the stops-at-classify docs, and `book.verified` to know the ISO app finished capture. |

Other values (`CLASSIFY`, `INSTANT_CLASSIFY`, free-text descriptors like `individual` / `business`) return `400 Invalid dictionary value @ data["book_class"]`.

**Don't use `INSTANT_CLASSIFY_ONLY` or `INSTANT_CLASSIFY_ISO_CAPTURE` unless the user explicitly asks for that "stop-after-classify" workflow** — they're for orchestrators that need to inspect documents and decide what to do next based on form type. For ordinary processing, default to `INSTANT` or `COMPLETE`.

`book_type` is a separate field and only accepts `DEFAULT` or `INSTANT_ML`. If you only need a normal processing book, omit it (the API defaults to `DEFAULT`).

## 5-Minute Quick Start

```bash
# 1. Create a book — set book_class to INSTANT for machine-only processing,
#    or omit it (defaults to COMPLETE) for human-in-the-loop verification.
curl -X POST https://api.ocrolus.com/v1/book/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Application #12345", "book_class": "INSTANT"}'
# → 200 OK with envelope:
#   {"status":200,"response":{"pk":71250194,"uuid":"09c52985-...","book_class":"INSTANT",...},"message":"OK"}

# 2. Upload a PDF (multipart; field is `pk`, not `book_pk`)
curl -X POST https://api.ocrolus.com/v1/book/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "pk=71250194" \
  -F "upload=@bank_statement.pdf"

# 3. Poll status (or, preferred: use webhooks — see below)
curl "https://api.ocrolus.com/v1/book/status?pk=71250194" \
  -H "Authorization: Bearer $TOKEN"

# 4. Read results (use the UUID for v2 capabilities)
curl "https://api.ocrolus.com/v2/book/$BOOK_UUID/summary" \
  -H "Authorization: Bearer $TOKEN"
curl "https://api.ocrolus.com/v2/detect/book/$BOOK_UUID/signals" \
  -H "Authorization: Bearer $TOKEN"
```

The same flow using the included Python SDK:

```python
from scripts.ocrolus_client import OcrolusClient  # or copy scripts/ocrolus_client.py into your project

client = OcrolusClient()  # reads OCROLUS_CLIENT_ID / OCROLUS_CLIENT_SECRET

# book_class="INSTANT" → machine-only. Omit (or "COMPLETE") for HITL.
env  = client.create_book("Application #12345", book_class="INSTANT")
book = env["response"]
pk, uuid = book["pk"], book["uuid"]

client.upload_pdf(pk, "bank_statement.pdf")
client.wait_for_book(book_pk=pk, timeout=600)

summary  = client.get_book_summary(uuid)
fraud    = client.get_book_fraud_signals(uuid)
income   = client.get_income_calculations(uuid)
```

## Capability Reference

Endpoints below mirror the structure at <https://docs.ocrolus.com/reference>. Prefer v2/UUID endpoints when both exist.

### Books

| Operation | Method & Path | Notes |
|-----------|---------------|-------|
| Create Book | `POST /v1/book/add` | Body: `name` (required), `book_class` (`INSTANT` or `COMPLETE` — see "Processing Mode" section), optional `book_type` (`DEFAULT` \| `INSTANT_ML`), `is_public`, `xid`. Returns `pk` and `uuid`. |
| Book information | `GET /v1/book/info?pk={pk}` | Or `?book_uuid={uuid}`. |
| Book list | `GET /v1/books` | Optional `limit`, `offset`, `order`, `order_by`, `name`, `search`, `xid`. |
| Update Book | `POST /v1/book/update` | Body: `pk` or `book_uuid`, plus fields to update. |
| Delete Book | `POST /v1/book/remove` | Body: `book_id` or `book_uuid`. |
| Book Status | `GET /v1/book/status?pk={pk}` | Or `?book_uuid={uuid}`. |
| Loan from Book | `GET /v2/los-connect/book/{book_uuid}/loans` | LOS-Connect (Encompass). |
| Book from loan | `GET /v2/los-connect/encompass/book?loan_id={id}` | LOS-Connect (Encompass). |

### Document Upload

| Operation | Method & Path | Notes |
|-----------|---------------|-------|
| Upload PDF | `POST /v1/book/upload` | Multipart: `pk` or `book_uuid`, `upload` (file), optional `form_type`, `doc_name`. 200 MB max. |
| Upload Mixed PDF | `POST /v1/book/upload/mixed` | Multiple doc types in a single PDF. |
| Upload Pay Stub | `POST /v2/book/{book_uuid}/document/paystub` | Multipart: `upload` (file). |
| Upload Image | `POST /v1/book/upload/image` | Multipart: `pk` or `book_uuid`, `upload`, optional `return_image_pk`. |
| Finalize Image Group | `POST /v1/book/upload/image/done` | Body: `pk` or `book_uuid`, `form_type`. |
| Upload Aggregator JSON | `POST /v1/book/upload/json` | Plaid, MX, Yodlee, Flinks payloads. |
| Import Plaid Asset Report | `POST /v1/book/import/plaid/asset` | Production only. |
| Cancel document | `POST /v1/document/cancel` | Body: `doc_pk` or `doc_uuid`, optional `accept_charges`. |
| Delete document | `POST /v1/document/remove` | Body: `doc_id` or `doc_uuid`. |
| Download document | `GET /v2/document/download?doc_uuid={uuid}` | Returns binary. |
| Upgrade Document | `POST /v1/document/upgrade` | Body: `doc_pk` or `doc_uuid`, `upgrade_type`. |
| Upgrade Mixed Document | `POST /v1/document/mixed/upgrade` | Body: `mixed_doc_pk` or `mixed_doc_uuid`, `upgrade_type`. |
| Mixed Document status | `GET /v1/document/mixed/status` | Query: one of `pk`, `doc_uuid`, `mixed_doc_uuid`. |

`form_type` is optional and cannot be used for bank statements.

### Classify

| Operation | Method & Path |
|-----------|---------------|
| Book classification summary | `GET /v2/book/{book_uuid}/classification-summary` |
| Mixed-document classification | `GET /v2/mixed-document/{mixed_doc_uuid}/classification-summary` |
| Grouped mixed-doc summary | `GET /v2/index/mixed-doc/{mixed_doc_uuid}/summary` |

Each classification carries a confidence score (0–1). Uniqueness Values (UV) extract key fields during classification (e.g., employer + employee name from a pay stub).

### Capture

| Operation | Method & Path |
|-----------|---------------|
| Book forms | `GET /v1/book/forms?pk={pk}` (or `?book_uuid={uuid}`) |
| Book pay stubs | `GET /v2/book/{book_uuid}/paystub` |
| Document form fields | `GET /v1/document/forms/fields?doc_uuid={uuid}` |
| Document pay stubs | `GET /v2/document/{doc_uuid}/paystub` |
| Form data | `GET /v1/form?uuid={form_uuid}` |
| Pay stub data | `GET /v2/paystub/{paystub_uuid}` |
| Transactions | `GET /v1/transaction?book_pk={pk}` (or `?book_uuid={uuid}`) |

Per-field confidence scores (0 = no confidence, 1 = very high). Scope transactions to a single document with `uploaded_doc_pk` or `uploaded_doc_uuid`.

### Detect (Fraud)

| Operation | Method & Path |
|-----------|---------------|
| Book signals | `GET /v2/detect/book/{book_uuid}/signals` |
| Document signals | `GET /v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals` |
| Signal visualization (image) | `GET /v2/detect/visualization/{visualization_uuid}` |
| Suspicious Activity Flags (legacy) | `GET /v1/book/{book_uuid}/suspicious-activity-flags` |

Each processed document carries an **Authenticity Score** (0–100; <61 is "low authenticity") and **Reason Codes** (e.g., `110-H` "bank statement account info tampered", with HIGH/MEDIUM/LOW confidence). Supported document types: bank statements, pay stubs, W-2s. See `references/detect.md` for the full signal taxonomy.

### Analyze (Cash Flow)

| Operation | Method & Path |
|-----------|---------------|
| Book summary | `GET /v2/book/{book_uuid}/summary` |
| Cash flow features | `GET /v2/book/{book_uuid}/cash_flow_features` |
| Enriched transactions | `GET /v2/book/{book_uuid}/enriched_txns` |
| Cash flow risk score | `GET /v2/book/{book_uuid}/cash_flow_risk_score` |
| Lender analytics (XLSX) | `GET /v2/book/{book_uuid}/lender_analytics/xlsx` |
| BSIC | `GET /v2/book/{book_uuid}/income/bank-statement-v2` |
| BSIC (Excel) | `GET /v2/book/{book_uuid}/income/bank-statement-v2/xlsx` |

### Income

| Operation | Method & Path |
|-----------|---------------|
| Income calculations | `GET /v2/book/{book_uuid}/income-calculations` |
| Income summary | `GET /v2/book/{book_uuid}/income/summary` |
| Configure income entity | `POST /v2/book/{book_uuid}/income/entity_config` |
| Set income guideline | `PUT /v2/book/{book_uuid}/income-guideline` |
| Self-employed income (Fannie Mae) | `POST /v2/book/{book_uuid}/income/self-employed/calculate` |

`income-calculations` accepts `guideline=FANNIE_MAE | FREDDIE_MAC | FHA | VA | USDA`. Note path naming: most income endpoints sit under `/income/...` (slash), but `income-calculations` and `income-guideline` use a hyphen. Match the docs path exactly.

### Business History

| Operation | Method & Path |
|-----------|---------------|
| Business identifier | `GET /v2/book/{book_uuid}/business` |
| Business overview | `GET /v1/businesses/{business_id}` |
| Business summary | `GET /v1/businesses/{business_id}/summary` |
| Business transactions | `GET /v1/businesses/{business_id}/transactions` |

### Transaction Tags

| Operation | Method & Path |
|-----------|---------------|
| Create / Get / Update / Delete tag | `POST /v2/analytics/tags` · `GET|PUT|DELETE /v2/analytics/tags/{tag_uuid}` |
| List tags | `GET /v2/analytics/tags` (optional `tag_type`) |
| Revenue / deduction tag config | `GET|PUT /v2/analytics/revenue-deduction-tags` |
| Tag transactions on a book | `PUT /v2/analytics/book/{book_uuid}/transactions` |

### Encore (Book Copy)

For organization-to-organization sharing of a completed book.

| Operation | Method & Path |
|-----------|---------------|
| Create copy jobs | `POST /v1/book/copy-jobs` (up to 50 per request) |
| List copy jobs | `GET /v1/book/copy-jobs` (optional `job_type`, `org_uuid`, `offset`, `limit`) |
| Accept / Reject | `POST /v1/book/copy-jobs/{job_id}/accept` · `POST /v1/book/copy-jobs/{job_id}/reject` |
| Run kick-outs | `POST /v1/book/copy-jobs/run-kickouts` |
| Org settings | `GET /v1/settings/book-copy` |

### Webhooks (Org-level — preferred)

Use webhooks instead of polling status endpoints.

| Operation | Method & Path |
|-----------|---------------|
| Add webhook | `POST /v1/account/settings/webhook` (Body: `url`, `events[]`) |
| List webhooks | `GET /v1/account/settings/webhooks` |
| Retrieve webhook | `GET /v1/account/settings/webhook/{webhook_uuid}` |
| Update webhook | `POST /v1/account/settings/webhook/{webhook_uuid}/update` |
| Delete webhook | `DELETE /v1/account/settings/webhook/{webhook_uuid}/delete` |
| List webhook events | `GET /v1/account/settings/webhook/{webhook_uuid}/events` |
| Test webhook | `POST /v1/account/settings/webhook/{webhook_uuid}/test` |
| Rotate signing secret | `POST /v1/account/settings/webhook/{webhook_uuid}/rotate-secret` |

> Update is **POST** to `.../update` and delete is **DELETE** to `.../delete` — both use the action-suffix style, not a method on the resource URL. Per-webhook routes use the singular `webhook`; only the list endpoint uses `webhooks`.

### Webhooks (Account-level — legacy)

| Operation | Method & Path |
|-----------|---------------|
| Configure webhook | `POST /v1/account/settings/update/webhook_endpoint` |
| Get configuration | `GET /v1/account/settings/webhook_details` |
| Test webhook | `GET /v1/account/settings/test_webhook_endpoint` |
| Rotate signing secret | `POST /v1/account/settings/webhook/rotate-secret` |

After registering the URL, **subscribe to event types** in the Ocrolus dashboard (Settings → Webhooks → Edit). API registration alone delivers zero events until events are selected.

Event payloads use `event_name` (not `event_type`). Common events:

- `document.upload_succeeded` — accepted into the pipeline
- `document.verification_succeeded` — OCR/processing complete
- `book.verified` — all docs verified
- `book.analytics_v2.generated` — cash flow analytics ready
- `document.detect.signal_found` / `book.detect.signal_found` — fraud signals
- `book.completed` — final event; all tasks done

Signatures are HMAC-SHA256 over `{Webhook-Timestamp}.{Webhook-Request-Id}.{raw_body}` with your configured secret, delivered in `Webhook-Signature`. Verify against raw bytes before parsing JSON. Handlers must respond within **5 seconds** — queue heavy work asynchronously.

See `references/webhooks.md` for full event reference and a verification snippet.

### Widget (embeddable upload UI)

Generate a short-lived widget token server-side, then mount the widget in your frontend:

```
POST https://widget.ocrolus.com/v1/widget/{widget_uuid}/token
```

Widget auth uses separate credentials (`OCROLUS_WIDGET_CLIENT_ID` / `OCROLUS_WIDGET_CLIENT_SECRET`). See `examples/widget-quickstart/` for a working Python/Flask example.

## What to Read Next

| If you are… | Read |
|-------------|------|
| Trying endpoints interactively | The Ocrolus Postman collection (linked from <https://docs.ocrolus.com/reference>) |
| Looking up a single endpoint signature | `references/endpoints.md` |
| Building fraud workflows | `references/detect.md` |
| Building a webhook handler | `references/webhooks.md` |
| Working in Python | `scripts/ocrolus_client.py` — SDK + CLI |
| Embedding the widget | `examples/widget-quickstart/README.md` |
| Validating against your tenant | `scripts/health_check.py` |

## Environment Variables

```bash
OCROLUS_CLIENT_ID=...
OCROLUS_CLIENT_SECRET=...
OCROLUS_WEBHOOK_SECRET=...          # if using webhooks
OCROLUS_WIDGET_CLIENT_ID=...        # if using the widget
OCROLUS_WIDGET_CLIENT_SECRET=...
```

## Things People Miss

- **The endpoint is `POST /v1/book/add`** — not `/v1/book/create`, `/v1/books`, or `/v1/book`. Other paths return 404 or the wrong action.
- **`book_class` is set at book creation and cannot be changed later.** Four accepted values: `INSTANT` (machine-only, full pipeline), `COMPLETE` (HITL, full pipeline; default), and the rare `INSTANT_CLASSIFY_ONLY` / `INSTANT_CLASSIFY_ISO_CAPTURE` for orchestrators that stop processing at classification and use webhooks (`book.classified`, `book.verified`) to route each document themselves. See the "Processing Mode" section above for the full synonym map. The API rejects everything else (`CLASSIFY`, `INSTANT_CLASSIFY`, `individual`, `business`).
- **`book_type` is a different field** that only accepts `DEFAULT` or `INSTANT_ML`. Don't confuse it with `book_class`. If unsure, omit it.
- **Auth body must be form-encoded.** JSON-encoded bodies — or adding an `audience` parameter — return `403 unauthorized_client`.
- **Upload form field is `pk` (or `book_uuid`)** — not `book_pk`. Using `book_pk` returns "Required pk or book uuid".
- **`pk` and `uuid` are not interchangeable.** v1 endpoints typically take the integer `pk`; v2 endpoints take the UUID. Mismatches return 404 or empty results.
- **Book status / book info / book forms / transactions are query-based on the public docs** (`/v1/book/info?pk=`, `/v1/book/status?pk=`, `/v1/book/forms?pk=`, `/v1/transaction?book_pk=`). Path-style `/v1/book/{pk}/...` aliases still respond on the live API but are not documented.
- **Document-level endpoints moved to v2:** `/v2/detect/uploaded_doc/{uuid}/signals`, `/v2/document/download`, `/v2/document/{uuid}/paystub`, `/v2/paystub/{uuid}`, `/v2/book/{uuid}/document/paystub`.
- **Income endpoints mix `/income/...` and `income-...`:** `income-calculations` and `income-guideline` are hyphenated, but `income/summary`, `income/entity_config`, `income/self-employed/calculate`, `income/bank-statement-v2` are slash-segmented. Use the docs path verbatim.
- **Cancel / delete / upgrade documents use a body, not a path UUID** (`POST /v1/document/cancel`, `POST /v1/document/remove`, `POST /v1/document/upgrade`).
- **Org-level webhook routes use `webhook` (singular) per-resource and `webhooks` (plural) only for list** — and update/delete are action-suffix routes (`.../update`, `.../delete`) rather than PUT/DELETE on the bare resource.
- **Most Ocrolus responses are envelopes** (`{ status, code, response, message, meta }`) and return HTTP 200 even on logical errors. Check the envelope `status` (or `code`), not just the HTTP status.
- **Webhook events must be selected in the dashboard** after API registration, or no events deliver.
- **Webhook field is `event_name`**, not `event_type`. Parsing the wrong field returns `None`.
- **Verify webhook signatures against the raw request body**, before JSON parsing, or the HMAC will not match.
- **Authenticity Scores are only available for documents processed after Nov 15, 2023**; older books lack them.
