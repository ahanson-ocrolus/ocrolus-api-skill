# Ocrolus API Skill — Live Testing Findings

**Tested by:** Adam Hanson (ahanson@ocrolus.com)
**Date:** March 20, 2026
**Tenant:** ahanson_personalOrg

---

## Summary

We ran the full Ocrolus API skill toolkit against a live personal org tenant, including endpoint validation, webhook listener setup, document upload processing, and auto-fetched analytics. This document captures all discrepancies between the documented API and observed behavior, plus recommendations for improving the toolkit.

---

## Critical Findings

### 1. Book Create Endpoint is `/v1/book/add`, NOT `/v1/book/create`

The documented endpoint `/v1/book/create` returns HTTP 200 with an embedded `404 Not Found` on this tenant. The actual working endpoint is **`/v1/book/add`**, discovered by examining the `ocrolus_automations` client.

| Documented | Actual | Status |
|-----------|--------|--------|
| `POST /v1/book/create` | Returns 200 with body `{"status":400,"code":404}` | **Broken** |
| `POST /v1/books` | Returns book list regardless of method | List-only, not create |
| `POST /v1/book/add` | Creates book, returns pk + uuid | **Working** |

**Impact:** Anyone following the SKILL.md or SDK will fail to create books.

### 2. Upload Endpoint Uses `pk` Not `book_pk`

The upload endpoint `/v1/book/upload` expects `pk` in form data, not `book_pk` as documented in the SDK.

```
# Documented (FAILS with "Required pk or book uuid"):
data={'book_pk': 71250194}

# Actual (WORKS):
data={'pk': 71250194}
```

### 3. Auth Uses Form-Encoded Data, Not JSON

The working auth call uses `data=` (form-encoded), not `json=`. Adding an `audience` parameter causes a 403 error.

```python
# Works:
requests.post(AUTH_URL, data={"grant_type": "client_credentials", ...})

# Fails (403 unauthorized_client):
requests.post(AUTH_URL, json={..., "audience": "https://api.ocrolus.com"})
```

### 4. Webhook Event Names Differ from Documentation

The documented webhook event names are placeholders. Real event names observed:

| Documented (Placeholder) | Actual (Observed) |
|--------------------------|-------------------|
| Not documented | `document.upload_succeeded` |
| `document.classification_succeeded` | Not observed (may not fire separately) |
| Not documented | `document.verification_succeeded` |
| `document.detect_succeeded` | `document.detect.signal_found` |
| `book.processing_complete` | `book.completed` |
| Not documented | `book.verified` |
| Not documented | `book.analytics_v2.generated` |
| Not documented | `book.analytics_v2.completed` |
| Not documented | `book.detect.signal_found` |

**The event field name is `event_name`**, not `event_type`.

### 5. Webhook Secret Configuration Endpoint Returns 404

`POST /v1/account/settings/webhooks/secret` returns 404 on this tenant. HMAC signature verification cannot be configured via API — the secret may need to be set through the Ocrolus dashboard, or this feature may not be available on all tenants.

### 6. Webhook Event Subscription Requires Manual Dashboard Step

After registering a webhook URL via API, you must manually edit the webhook in the Ocrolus dashboard to subscribe to specific event types. The API registration alone does not subscribe to any events by default.

### 7. `/v1/book/{pk}/upload/pdf` Path Does Not Exist

The path-style upload endpoint returns 404. Only the flat endpoint with `pk` in form data works:

```
# 404:
POST /v1/book/71250194/upload/pdf

# Works:
POST /v1/book/upload with data={'pk': 71250194}
```

---

## Webhook Processing Flow (Observed)

When uploading bank statements to a book, events arrive in this order:

```
1. document.upload_succeeded        (immediate, per document)
   ↓
2. document.verification_succeeded  (per document, after OCR/processing)
   ↓
3. book.verified                    (all docs verified, book-level)
   ↓
4. book.analytics_v2.generated      (cash flow analytics computed)
   ↓
5. document.detect.signal_found     (per document, fraud signals)
   ↓
6. book.detect.signal_found         (book-level fraud summary)
   ↓
7. book.completed                   (all tasks done: ANALYTICS, CAPTURE, DETECT)
```

Each event includes:
- `event_name` — the event type
- `severity` — LOW, MODERATE, or HIGH
- `notification_type` — STATUS
- `notification_reason` — human-readable description
- `book_pk`, `book_uuid` — book identifiers
- `uploaded_docs` — array of document statuses (on book events)

### Book Completion Payload Example

```json
{
  "status": "BOOK_COMPLETE",
  "book_pk": 71400892,
  "book_uuid": "09c52985-2f05-4022-a738-9277cc335c7e",
  "severity": "MODERATE",
  "event_name": "book.completed",
  "notification_type": "STATUS",
  "notification_reason": "Completed tasks: ANALYTICS, CAPTURE, DETECT",
  "tasks": ["ANALYTICS", "CAPTURE", "DETECT"],
  "uploaded_docs": [
    {"uuid": "...", "status": "VERIFICATION_COMPLETE"},
    ...
  ]
}
```

---

## Endpoint Alias Discovery

Many endpoints have undocumented aliases that both work:

| Feature | Path A (Documented) | Path B (Also Works) |
|---------|--------------------|--------------------|
| Book Status | `/v1/book/status?book_pk=X` | `/v1/book/{pk}/status` |
| Transactions | `/v1/book/{pk}/transactions` | `/v1/book/transactions?book_pk=X` |
| Cash Flow | `/v2/book/{uuid}/cash_flow_features` | `/v2/book/{uuid}/cashflow-features` |
| Enriched Txns | `/v2/book/{uuid}/enriched_txns` | `/v2/book/{uuid}/enriched-transactions` |
| Risk Score | `/v2/book/{uuid}/cash_flow_risk_score` | `/v2/book/{uuid}/risk-score` |
| Webhook List | `/v1/account/settings/webhooks` | `/v1/org/webhooks` |

### Known Issues

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /v2/analytics/revenue-deduction-tags` | 500 | Server error on this tenant |
| `POST /v1/account/settings/webhooks/secret` | 404 | Not available on this tenant |
| `GET /v1/webhook/configuration` | 404 | Account-level webhook config not available |
| `GET /v1/org/webhooks` | 404 | Org webhook listing not available |

---

## Health Check Results

**78 endpoints tested — 100% reachable — 93.6% success (2xx)**

The 5 non-2xx responses are expected:
- 3 endpoints return 400 (rejected empty probe payload — route exists)
- 1 endpoint returns 500 (revenue-deduction-tags bug)
- 1 endpoint returns 400 on Import Plaid Asset (empty payload rejection)

Average response time: ~680ms per endpoint.

---

## Recommendations for the Skill Toolkit

1. **Fix `/v1/book/create` → `/v1/book/add`** in endpoints.md, ocrolus_client.py, and SKILL.md
2. **Fix upload `book_pk` → `pk`** in the SDK and documentation
3. **Replace placeholder webhook events** with the real event names from this testing
4. **Document the manual webhook subscription step** — users must edit webhooks in the Ocrolus dashboard to subscribe to events after API registration
5. **Add `event_name` field** to webhook documentation (not `event_type`)
6. **Document the auth format** — form-encoded, no audience parameter
7. **Add the webhook processing flow diagram** showing event order
8. **Mark `/v2/analytics/revenue-deduction-tags` as broken** in coverage matrix
9. **Add `/v1/book/add` to the endpoint inventory** as the confirmed create path
10. **Update the coverage matrix** with live validation results
