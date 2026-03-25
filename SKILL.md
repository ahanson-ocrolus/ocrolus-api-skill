---
name: ocrolus-api
description: Use this skill when the user wants to integrate with the Ocrolus API for document processing, financial analysis, or fraud detection. Trigger on mentions of "Ocrolus", "ocrolus api", "document classification", "bank statement analysis", "income calculations", "fraud detection signals", "cash flow analytics", "book upload", "ocrolus webhook", "ocrolus widget", "transaction tags", "book copy", "encore", or any reference to Ocrolus document automation, capture, classify, detect, or analyze features. Also trigger when building applications that process financial documents (tax forms, pay stubs, bank statements, W-2s) via Ocrolus.
version: 4.0.0
---

# Ocrolus API Integration Skill

Ocrolus is a document automation platform: **Classify** (document identification), **Capture** (data extraction), **Detect** (fraud detection), **Analyze** (financial metrics).

## Quick Reference

- **Base URL:** `https://api.ocrolus.com`
- **Auth URL:** `https://auth.ocrolus.com/oauth/token` (form-encoded, no audience param)
- **Auth type:** OAuth 2.0 Client Credentials -> Bearer JWT (24h expiry)
- **Widget Auth URL:** `https://widget.ocrolus.com/v1/widget/{uuid}/token` (separate credentials)

## Where to Find Things

| Need | File |
|------|------|
| Setup and quick start | `README.md` |
| Python SDK (74 methods) | `ocrolus_client.py` |
| Endpoint paths and methods | `references/endpoints.md` |
| Fraud detection (scores, reason codes) | `references/detect.md` |
| Webhook events and payloads | `references/webhooks.md` |
| Coverage and validation status | `references/coverage-matrix.md` |
| Health check, webhook, widget tools | `tools/` (optional — see `tools/README.md`) |

## Key Identifiers

| Identifier | Format | Used By |
|-----------|--------|---------|
| `book_pk` | Integer | v1 endpoints: upload, forms, transactions, status |
| `book_uuid` | UUID string | v2 endpoints: analytics, detect, income, classify |

Never mix them -- v1 rejects UUIDs, v2 rejects PKs.

## Core Workflow

```
Create Book -> Upload Docs -> Poll Status / Wait for Webhook -> Retrieve Results
```

## Critical API Corrections

- Book create: `/v1/book/add` (NOT `/v1/book/create`)
- Upload form field: `pk` (NOT `book_pk`)
- Auth: form-encoded POST, no `audience` parameter
- Webhook event field: `event_name` (NOT `event_type`)
- After webhook registration, must subscribe to events in Ocrolus dashboard manually

## Environment Variables

```bash
OCROLUS_CLIENT_ID=your_client_id
OCROLUS_CLIENT_SECRET=your_client_secret
OCROLUS_WEBHOOK_SECRET=your_webhook_secret          # if using webhooks
OCROLUS_WIDGET_CLIENT_ID=widget_client_id            # if using widget
OCROLUS_WIDGET_CLIENT_SECRET=widget_client_secret
```
