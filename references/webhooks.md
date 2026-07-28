# Ocrolus Webhooks — Reference

> Sources: <https://docs.ocrolus.com/docs/webhook-overview>, <https://docs.ocrolus.com/docs/secure-webhook-urls>.
> Event names and payload shapes below reflect observed production deliveries.

## Overview

Ocrolus delivers event notifications via HTTP POST to your configured endpoint(s). Use webhooks instead of polling for efficient, real-time processing updates.

**Key constraints:**
- Webhook requests have a **5-second timeout** -- handlers must respond quickly
- Only ONE webhook type can be active: **org-level OR account-level**, not both
- Return HTTP `200 OK` to acknowledge receipt
- **After API registration, you must manually subscribe to events in the Ocrolus dashboard** (Settings > Webhooks > Edit > select event types)

## Webhook Types

| Feature | Organization-Level | Account-Level |
|---------|-------------------|---------------|
| Configuration | Dashboard + API | API only |
| Multiple webhooks | Yes (per org) | No (one per account) |
| Testing via API | Yes | Yes |
| Dashboard visibility | Yes | No |
| Recommended | **Yes** | Legacy |

## API Endpoints

> Canonical paths live in `references/endpoints.md`; the tables below mirror them. Per-webhook org-level routes use the **singular** `webhook/{webhook_uuid}` with action suffixes (`/update`, `/delete`, `/test`, `/rotate-secret`); only the list route uses the **plural** `webhooks`. (Validated against the live API.)

### Organization-Level (recommended)

| Operation | Method | Path |
|-----------|--------|------|
| Add Webhook | POST | `/v1/account/settings/webhook` |
| List Webhooks | GET | `/v1/account/settings/webhooks` |
| Retrieve Webhook | GET | `/v1/account/settings/webhook/{webhook_uuid}` |
| Update Webhook | POST | `/v1/account/settings/webhook/{webhook_uuid}/update` |
| Delete Webhook | DELETE | `/v1/account/settings/webhook/{webhook_uuid}/delete` |
| List Events | GET | `/v1/account/settings/webhook/{webhook_uuid}/events` |
| Test Webhook | POST | `/v1/account/settings/webhook/{webhook_uuid}/test` |
| Rotate Signing Secret | POST | `/v1/account/settings/webhook/{webhook_uuid}/rotate-secret` |

### Account-Level (legacy)

| Operation | Method | Path |
|-----------|--------|------|
| Configure | POST | `/v1/account/settings/update/webhook_endpoint` |
| Get Config | GET | `/v1/account/settings/webhook_details` |
| Test | GET | `/v1/account/settings/test_webhook_endpoint` |
| Rotate Signing Secret | POST | `/v1/account/settings/webhook/rotate-secret` |

## Event Types

The event type field is **`event_name`** (not `event_type`). The authoritative list
of available events is at
<https://docs.ocrolus.com/docs/organization-level-webhook#available-events>; the
full set is reproduced below.

### Book Events

| Event Name | Description |
|-----------|-------------|
| `book.classified` | Book has been classified/categorized — **fetch `classification-summary` here** |
| `book.verified` | Capture complete; documents verified or rejected — **fetch `/v2/book/{uuid}/forms` and analysis here** |
| `book.analytics_v2.generated` | Analytics produced by the v2 analytics engine |
| `book.analytics_completed` | Asynchronous analytics request completed |
| `book.detect.signal_found` | Book contains documents with suspicious-activity signals |
| `book.detect.signal_not_found` | Book contains no suspicious-activity signals |
| `book.income.generated` | Book income calculation freshly generated |
| `book.income.updated` | Book income manually edited or overridden |
| `book.pacing.discrepancies_found` | Discrepancies found in Plaid-to-statement mapping |
| `book.pacing.discrepancies_not_found` | No discrepancies in Plaid-to-statement mapping |
| `book.completed` | Capture, Detect, Income, and Analytics all finished — **final event** |

### Document Events

| Event Name | Description |
|-----------|-------------|
| `document.upload_succeeded` / `document.upload_failed` | Single-document upload outcome |
| `document.classification_succeeded` / `document.classification_failed` | Per-document classification outcome |
| `document.verification_succeeded` / `document.verification_failed` | Per-document capture/verification outcome |
| `document.detect.signal_found` / `document.detect.signal_not_found` | Per-document fraud outcome |
| `document.detect.unable_to_process` | Document could not be processed through Detect |
| `mixed_document.rejected` | A mixed document was rejected |

### Image Group / Plaid Events

| Event Name | Description |
|-----------|-------------|
| `image_group.upload_succeeded` / `image_group.upload_failed` | Image-group upload outcome |
| `image_group.verification_succeeded` / `image_group.verification_failed` | Image-group verification outcome |
| `plaid.upload_succeeded` / `plaid.upload_failed` | Plaid aggregator data upload outcome |

### Book Copy (Encore) / Network / Org Events

| Event Name | Description |
|-----------|-------------|
| `book.copy.request_received` | New book shared with your organization |
| `book.copy.request_accepted` / `book.copy.request_rejected` | Recipient accepted/rejected a copy |
| `book.copy.docs_added` | Additional documents shared under an existing copy |
| `book.copy.kickout_evaluated` | Automated cash-flow kick-outs evaluated |
| `network.book.created` | New application submitted for a monitored borrower |
| `network.book.funded` | Monitored borrower has been funded |
| `analytics.config_updated` | Analytics configuration updated for the org |

> **Core-workflow events:** `book.classified` → fetch classification; `book.verified`
> → fetch `/v2/book/{uuid}/forms` + analysis (cash-flow or income); `book.detect.signal_found`
> → fetch book signals; `book.completed` is the final all-done marker.

### Processing Flow (Observed Order)

```
Upload documents to book
    │
    ├── document.upload_succeeded          (per document, immediate)
    │
    ├── document.classification_succeeded  (per document, after classify)
    │
    ├── book.classified                    (book-level, all docs classified)  → classification-summary
    │
    ├── document.verification_succeeded    (per document, after capture)
    │
    ├── book.verified                      (book-level, all docs verified)     → /v2/book/{uuid}/forms + analysis
    │
    ├── book.analytics_v2.generated        (cash flow analytics ready)
    │
    ├── document.detect.signal_found       (per document, fraud signals)
    │
    ├── book.detect.signal_found           (book-level fraud summary)          → /v2/detect/book/{uuid}/signals
    │
    └── book.completed                     (all tasks: CAPTURE, DETECT, INCOME, ANALYTICS)
```

> Analytics/income endpoints (`summary`, `enriched_txns`, `cash_flow_features`,
> `income-calculations`) return **HTTP 425 "Too Early"** until generated — wait for
> `book.analytics_v2.generated` (or `book.completed`) rather than calling them at `book.verified`.

### Encore / Book Copy Events
- `book.copy.request_accepted` — recipient accepted book copy
- `book.copy.request_rejected` — recipient rejected book copy
- `book.copy.kickout_evaluated` — automated kick-out evaluation complete

## Webhook Payload Structure

Every webhook payload includes these common fields:

```json
{
  "event_name": "book.completed",
  "status": "BOOK_COMPLETE",
  "severity": "MODERATE",
  "notification_type": "STATUS",
  "notification_reason": "Completed tasks: ANALYTICS, CAPTURE, DETECT",
  "book_pk": 12345678,
  "book_uuid": "00000000-0000-0000-0000-000000000000"
}
```

### Document-Level Event Payload

```json
{
  "event_name": "document.verification_succeeded",
  "severity": "LOW",
  "notification_type": "STATUS",
  "notification_reason": "Document verification succeeded",
  "book_pk": 12345678,
  "book_uuid": "00000000-...",
  "doc_uuid": "11111111-...",
  "uploaded_doc_pk": 87654321,
  "uploaded_doc_uuid": "11111111-..."
}
```

### Book Completion Payload (with document statuses)

```json
{
  "event_name": "book.completed",
  "status": "BOOK_COMPLETE",
  "severity": "MODERATE",
  "notification_type": "STATUS",
  "notification_reason": "Completed tasks: ANALYTICS, CAPTURE, DETECT",
  "book_pk": 12345678,
  "book_uuid": "00000000-...",
  "book_name": "Application #12345",
  "tasks": ["ANALYTICS", "CAPTURE", "DETECT"],
  "uploaded_docs": [
    {"uuid": "11111111-...", "status": "VERIFICATION_COMPLETE"},
    {"uuid": "22222222-...", "status": "VERIFICATION_COMPLETE"}
  ]
}
```

### Fraud Signal Payload

```json
{
  "event_name": "document.detect.signal_found",
  "severity": "MODERATE",
  "notification_type": "STATUS",
  "notification_reason": "Signals found for document",
  "book_pk": 12345678,
  "book_uuid": "00000000-...",
  "doc_uuid": "11111111-...",
  "is_cloud_compliant": false,
  "uploaded_doc_name": "Bank_Statement_01-2024.pdf"
}
```

**Note:** The fraud webhook only signals that fraud was detected. To get specific reason codes and authenticity scores, call `GET /v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals`.

## Webhook Headers

| Header | Content | Example |
|--------|---------|---------|
| `Webhook-Signature` | HMAC-SHA256 hex digest | (present when a signing secret is configured) |
| `Webhook-Timestamp` | Timestamp string | `1710960000` |
| `Webhook-Request-Id` | UUID for this delivery | `019d0c76-a902-7b75-8f9e-8694eae8a374` |
| `Content-Type` | Always JSON | `application/json` |

## Signature Verification (HMAC-SHA256)

Configure a signing secret first (via the dashboard, or via `POST /v1/account/settings/webhook/{webhook_uuid}/rotate-secret` if your tenant has the API enabled). Until a secret is configured, deliveries arrive without a `Webhook-Signature` header.

> ⚠️ **Security:** once a secret IS configured, an unsigned delivery must be **rejected**, not accepted. Accepting a request with no signature header when you hold a secret is a trivial bypass — an attacker just omits the header. The `secret` you pass in is the signal that a secret is configured, so treat a missing signature as a failure. Only accept-and-warn on unsigned deliveries while you have **no** secret set (e.g. during initial bring-up).

### Verification Algorithm

```python
import hmac
import hashlib

def verify_webhook(headers: dict, body: bytes, secret: str) -> bool:
    timestamp = headers.get("Webhook-Timestamp", "")
    request_id = headers.get("Webhook-Request-Id", "")
    received_signature = headers.get("Webhook-Signature", "")

    # A secret is configured (it was passed in), so an unsigned delivery
    # is not trustworthy — reject it. Only skip verification when you have
    # deliberately not configured a secret yet.
    if not received_signature:
        return False

    signed_message = f"{timestamp}.{request_id}.".encode() + body

    expected_signature = hmac.new(
        secret.encode(),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)
```

## Setup Instructions

### Quick Start

```bash
# 1. Set credentials
export OCROLUS_CLIENT_ID="your_id"
export OCROLUS_CLIENT_SECRET="your_secret"

# 2. Start webhook listener + ngrok tunnel + register
python scripts/webhook_setup.py auto

# 3. IMPORTANT: Go to Ocrolus Dashboard > Settings > Webhooks
#    Edit the webhook and subscribe to the events you want to receive.
#    The API registration alone does NOT subscribe to any events.

# 4. Upload documents to trigger webhook events
# 5. View activity dashboard at http://localhost:8080/activity
```

### Manual Setup

```bash
# Start listener
python scripts/webhook_setup.py listen --port 8080

# In another terminal, start ngrok
ngrok http 8080

# Register the ngrok URL
python scripts/webhook_setup.py register --url https://YOUR-URL.ngrok-free.dev/webhooks/ocrolus

# Then subscribe to events in the Ocrolus dashboard
```

### Monitoring

- **Activity Dashboard:** http://localhost:8080/activity (live-refreshing)
- **Health Endpoint:** http://localhost:8080/health (JSON stats)
- **Export Events:** http://localhost:8080/export/json or /export/csv
- **Event Log:** `reports/webhook-events/events.jsonl` (persists across restarts)

## Production Handler Pattern

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhooks/ocrolus", methods=["POST"])
def handle_ocrolus_webhook():
    event = request.get_json()
    event_name = event.get("event_name", "")

    # Respond immediately (5s timeout)
    if event_name == "document.upload_succeeded":
        # Document accepted, processing will begin
        pass
    elif event_name == "document.verification_succeeded":
        queue_document_processing(event)
    elif event_name == "book.verified":
        # All docs verified — can fetch classification results
        pass
    elif event_name == "book.analytics_v2.generated":
        # Cash flow analytics ready — fetch summary + transactions
        fetch_book_analytics(event["book_uuid"])
    elif event_name == "document.detect.signal_found":
        # Fraud detected — fetch detailed signals
        fetch_fraud_details(event["doc_uuid"])
    elif event_name == "book.completed":
        # All processing done — safe to generate final report
        finalize_book_report(event)

    return jsonify({"status": "ok"}), 200
```

## Common Pitfalls

1. **Not subscribing to events** -- API registration alone doesn't subscribe. Edit the webhook in the Ocrolus dashboard to select event types.
2. **Wrong event field name** -- The field is `event_name`, not `event_type`.
3. **Long-running handlers** -- Ocrolus times out at 5 seconds. Queue work and respond immediately.
4. **Not verifying signatures** -- Always verify before processing (once secret is configured).
5. **Mixing webhook types** -- Only org-level OR account-level can be active, not both.
6. **Parsing body before verification** -- Verify against raw bytes, then parse JSON.
7. **Hardcoded secrets** -- Use environment variables or a secrets manager.
8. **Expecting fraud details in webhook** -- The webhook only signals detection. Call `/v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals` for reason codes.
