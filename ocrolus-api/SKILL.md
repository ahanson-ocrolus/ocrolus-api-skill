---
name: ocrolus-api
description: Use this skill when the user wants to integrate with the Ocrolus API for document processing, financial analysis, or fraud detection. Trigger on mentions of "Ocrolus", "ocrolus api", "document classification", "bank statement analysis", "income calculations", "fraud detection signals", "cash flow analytics", "book upload", "ocrolus webhook", "ocrolus widget", "transaction tags", "book copy", "encore", or any reference to Ocrolus document automation, capture, classify, detect, or analyze features. Also trigger when building applications that process financial documents (tax forms, pay stubs, bank statements, W-2s) via Ocrolus.
version: 3.0.0
---

# Ocrolus API Integration Skill

Ocrolus is a document automation platform with four core capabilities: **Classify** (document identification), **Capture** (data extraction), **Detect** (fraud detection), and **Analyze** (financial metrics).

## Quick Reference

- **Base URL:** `https://api.ocrolus.com`
- **Auth URL:** `https://auth.ocrolus.com/oauth/token`
- **Auth type:** OAuth 2.0 Client Credentials -> Bearer JWT (24h expiry, refresh at 12h)
- **Widget Auth URL:** `https://jwe-issuer.ocrolus.net/token` (separate from API auth)

## Skill File Layout

> **Live-validated** against Ocrolus tenant (ahanson_personalOrg) on 2026-03-20.
> 78 endpoints tested, 100% reachable. See `FINDINGS.md` for full details.
> Re-validate on your own tenant with `scripts/validate_endpoints.py` before production use.

| File | Purpose |
|------|---------|
| `SKILL.md` | This file -- concise overview and routing guide |
| `README.md` | Client-facing setup guide with health check and webhook instructions |
| `FINDINGS.md` | Live testing findings and API corrections |
| `references/endpoints.md` | Endpoint inventory (VALIDATED -- corrected paths confirmed) |
| `references/detect.md` | Detect fraud signals, authenticity scores, reason codes |
| `references/webhooks.md` | Webhook setup, real event names, payloads, processing flow (VALIDATED) |
| `references/coverage-matrix.md` | Endpoint coverage tracking (VALIDATED) |
| `scripts/ocrolus_client.py` | Python SDK -- importable module, 74 methods |
| `scripts/health_check.py` | Comprehensive API health check (console/JSON/HTML reports) |
| `scripts/webhook_setup.py` | Webhook listener, ngrok tunnel, registration, activity dashboard |
| `scripts/validate_endpoints.py` | Validation script to confirm paths and webhook events against your tenant |
| `scripts/webhook_verifier.py` | Production webhook receiver with HMAC-SHA256 verification |
| `scripts/generate_openapi.py` | OpenAPI 3.0 / Swagger 2.0 spec generator |
| `scripts/test_fixtures.py` | pytest suite for integration testing |
| `examples/widget_app.py` | Widget embedding sample (requires manual script tag insertion -- see README) |

## When Building Ocrolus Integrations

1. **Start with `README.md`** -- run the health check and endpoint validation against your tenant before writing integration code
2. **Use `references/endpoints.md`** for the endpoint list -- all paths have been live-validated and corrected (e.g., `/v1/book/add` not `/v1/book/create`)
3. **Use `scripts/ocrolus_client.py`** as a runnable SDK -- it is a real importable Python module, not just illustrative markdown
4. **For Detect/fraud**, read `references/detect.md` for authenticity scores (0-100), reason codes (e.g. `110-H`), signal types (file origin vs file tampering), and confidence levels
5. **For webhooks**, read `references/webhooks.md` -- event names (`event_name` field) and processing flow have been validated with real webhook deliveries
6. **For widget embedding**, see `examples/widget_app.py` -- handles auth and page structure, but requires manual insertion of your widget script tag from the Ocrolus Dashboard

## Key Identifier Conventions

Ocrolus uses two identifiers for Books -- know which endpoints expect which:

| Identifier | Format | Used By |
|-----------|--------|---------|
| `book_pk` | Integer (e.g. `12345`) | v1 endpoints: upload, forms, transactions, status |
| `book_uuid` | UUID string (e.g. `"a1b2c3d4-..."`) | v2 endpoints: analytics, detect, income, classify |

Both are returned in the Create Book response. **Never mix them** -- v1 endpoints reject UUIDs and v2 endpoints reject PKs.

## Processing Modes

| Mode | What It Does | Upgrade Path |
|------|-------------|--------------|
| **Classify** | Document type ID only | -> Instant -> Complete |
| **Instant** | Automated classification + extraction (fastest) | -> Complete |
| **Instant Classify with UV** | Classification + Uniqueness Values (no full capture) | -> Instant -> Complete |
| **Complete** | Full extraction with human review (most accurate) | None (maximum) |

## Core Workflow

```
Create Book -> Upload Docs -> Poll Status / Wait for Webhook -> Retrieve Results
```

See `scripts/ocrolus_client.py` for the full runnable implementation of this flow.

## Breaking Change Policy

- **Non-breaking** (any time): new response fields, new array members, optional->mandatory relaxation
- **Breaking** (60-day notice): field removal/rename, type changes, optional->mandatory tightening
- **Key principle:** Clients must tolerate unknown fields gracefully

## Environment Variables

```bash
OCROLUS_CLIENT_ID=your_client_id
OCROLUS_CLIENT_SECRET=your_client_secret
OCROLUS_WEBHOOK_SECRET=your_webhook_secret     # for signature verification
OCROLUS_WIDGET_CLIENT_ID=widget_client_id      # if using widget
OCROLUS_WIDGET_CLIENT_SECRET=widget_client_secret
```

## API Documentation Links

- Guide: https://docs.ocrolus.com/docs/guide
- API Reference: https://docs.ocrolus.com/reference
- Authentication: https://docs.ocrolus.com/docs/using-api-credentials
- Webhooks: https://docs.ocrolus.com/docs/webhook-overview
- Detect: https://docs.ocrolus.com/docs/detect
- Widget: https://docs.ocrolus.com/docs/widget
