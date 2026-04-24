---
name: ocrolus-api
description: Ocrolus API integration skill — provides a validated Python SDK (74 methods), corrected endpoint paths, auth patterns, webhook event names, and fraud detection reference for the Ocrolus document automation platform. Use this skill whenever the user mentions Ocrolus, ocrolus_client, book_pk, book_uuid, or the Ocrolus dashboard. Also trigger on references to Ocrolus-specific features: Classify, Capture, Detect, Analyze, Optima, Encore, book copy, ocrolus webhook, ocrolus widget, transaction tags, authenticity scores, or cash flow analytics via Ocrolus. Trigger when a project already imports ocrolus_client even if the user doesn't mention Ocrolus by name. Do not trigger on generic document processing or financial analysis requests that aren't related to Ocrolus.
---

# Ocrolus API Integration Skill

Ocrolus is a document automation platform with four core capabilities: **Classify** (document identification), **Capture** (data extraction), **Detect** (fraud detection), and **Analyze** (cash flow, income, risk scoring). There is also **Optima** for real-time extraction without creating a book.

## Quick Reference

- **Base URL:** `https://api.ocrolus.com`
- **Optima URL:** `https://apika.ocrolus.com` (real-time classify + capture, no book required)
- **Auth URL:** `https://auth.ocrolus.com/oauth/token` (form-encoded, no audience param)
- **Auth:** OAuth 2.0 Client Credentials → Bearer JWT (24h expiry)
- **Widget Auth URL:** `https://widget.ocrolus.com/v1/widget/{uuid}/token` (separate credentials)

## What to Read Based on the Task

Read only what you need. SKILL.md is always in context; the files below are loaded on demand.

| Task | Read this |
|------|-----------|
| Build an integration (upload docs, get results) | `ocrolus_client.py` (SDK with 74 methods) |
| Look up a specific endpoint path or method | `references/endpoints.md` |
| Work with fraud detection scores or reason codes | `references/detect.md` |
| Set up webhook event processing | `references/webhooks.md` |
| Debug which endpoints work on a tenant | `references/coverage-matrix.md` |
| Embed the Ocrolus upload widget | `tools/widget-quickstart/README.md` |

## Quick Start Example

Use the SDK — it handles auth, token refresh, and all endpoint paths:

```python
from ocrolus_client import OcrolusClient

client = OcrolusClient()  # reads OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET from env

# Create a book and upload a document
book = client.create_book("Loan Application #12345")
book_pk = book["pk"]       # integer — used by v1 endpoints
book_uuid = book["uuid"]   # UUID string — used by v2 endpoints

client.upload_pdf(book_pk, "bank_statement.pdf")

# Wait for processing (or use webhooks — see references/webhooks.md)
client.wait_for_book(book_pk, timeout=600)

# Retrieve results
forms = client.get_book_forms(book_pk)                   # Capture — extracted fields
fraud = client.get_book_fraud_signals(book_uuid)         # Detect — fraud scores
summary = client.get_book_summary(book_uuid)             # Analyze — cash flow
income = client.get_income_calculations(book_uuid)       # Income calculations
```

If not using the SDK, authenticate like this (the format matters — see pitfalls below):

```python
import requests

token = requests.post("https://auth.ocrolus.com/oauth/token", data={
    "grant_type": "client_credentials",
    "client_id": OCROLUS_CLIENT_ID,
    "client_secret": OCROLUS_CLIENT_SECRET,
}).json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}
```

## Key Identifiers

Ocrolus uses two book identifiers. Using the wrong one silently fails or returns empty results.

| Identifier | Format | Used By | Example |
|-----------|--------|---------|---------|
| `book_pk` | Integer | v1 endpoints: upload, forms, transactions, status | `71250194` |
| `book_uuid` | UUID string | v2 endpoints: analytics, detect, income, classify | `09c52985-2f05-4022-a738-9277cc335c7e` |

Both are returned when you create a book. v1 endpoints reject UUIDs; v2 endpoints reject PKs.

## Common Pitfalls

These are corrections from live API testing. The official docs are wrong or misleading on each of these — getting them wrong causes silent failures or confusing errors.

| Pitfall | Wrong | Correct | Why it matters |
|---------|-------|---------|----------------|
| Book create path | `/v1/book/create` | `/v1/book/add` | `/v1/book/create` returns HTTP 200 with an embedded 404 — looks like success but creates nothing |
| Upload form field | `book_pk` in form data | `pk` or `book_uuid` in form data | Using `book_pk` returns "Required pk or book uuid" error |
| Auth format | JSON body with `audience` param | Form-encoded, no `audience` | JSON body or adding `audience` causes 403 `unauthorized_client` |
| Webhook event field | `event_type` | `event_name` | Parsing `event_type` from webhook payloads returns `None` |
| Webhook subscription | API registration is sufficient | Must also subscribe in dashboard | Registering a webhook URL via API delivers zero events until you manually select event types in Dashboard > Settings > Webhooks |

## Environment Variables

```bash
OCROLUS_CLIENT_ID=your_client_id
OCROLUS_CLIENT_SECRET=your_client_secret
OCROLUS_WEBHOOK_SECRET=your_webhook_secret          # if using webhooks
OCROLUS_WIDGET_CLIENT_ID=widget_client_id            # if using widget
OCROLUS_WIDGET_CLIENT_SECRET=widget_client_secret
```

## Capabilities Overview

| Capability | What it does | Key endpoints |
|------------|-------------|---------------|
| **Core** | Book/document CRUD, upload, status polling | `/v1/book/add`, `/v1/book/upload`, `/v1/book/status` |
| **Classify** | Identify 300+ document types with confidence scores | `/v2/book/{uuid}/classification-summary` |
| **Capture** | Extract structured fields from documents | `/v1/book/{pk}/forms`, `/v1/form/{uuid}/fields` |
| **Detect** | Fraud signals, authenticity scores, reason codes | `/v2/detect/book/{uuid}/signals` |
| **Analyze** | Cash flow, enriched transactions, risk scores | `/v2/book/{uuid}/summary`, `/v2/book/{uuid}/enriched_txns` |
| **Income** | Income calculations, BSIC, self-employed income | `/v2/book/{uuid}/income-calculations`, `/v2/book/{uuid}/bsic` |
| **Optima** | Real-time classify + capture without creating a book | `https://apika.ocrolus.com/ml/v2/instant` |
| **Widget** | Embeddable upload UI for end users | See `tools/widget-quickstart/` |
| **Webhooks** | Real-time event notifications | See `references/webhooks.md` |
