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

### Organization-Level (recommended)

| Operation | Method | Path |
|-----------|--------|------|
| Add Webhook | POST | `/v1/account/settings/webhook` |
| List Webhooks | GET | `/v1/account/settings/webhooks` |
| Retrieve Webhook | GET | `/v1/account/settings/webhooks/{webhook_id}` |
| Update Webhook | PUT | `/v1/account/settings/webhooks/{webhook_id}` |
| Delete Webhook | DELETE | `/v1/account/settings/webhooks/{webhook_id}` |
| List Events | GET | `/v1/account/settings/webhooks/events` |
| Test Webhook | POST | `/v1/account/settings/webhooks/{webhook_id}/test` |
| Configure Secret | POST | `/v1/account/settings/webhooks/secret` |

### Account-Level

| Operation | Method | Path |
|-----------|--------|------|
| Configure | POST | `/v1/webhook/configure` |
| Get Config | GET | `/v1/webhook/configuration` |
| Test | GET / POST | `/v1/webhook/test` |
| Configure Secret | POST | `/v1/webhook/secret` |

## Event Types

The event type field is **`event_name`** (not `event_type`).

### Document Events

| Event Name | Description | When It Fires |
|-----------|-------------|---------------|
| `document.upload_succeeded` | Document uploaded and accepted | Immediately after upload |
| `document.verification_succeeded` | OCR/processing complete | After document processing finishes |
| `document.detect.signal_found` | Fraud signals detected | After fraud detection runs on the document |

### Book Events

| Event Name | Description | When It Fires |
|-----------|-------------|---------------|
| `book.verified` | All documents in book verified | After all docs reach VERIFICATION_COMPLETE |
| `book.analytics_v2.generated` | Cash flow analytics computed | After analytics processing |
| `book.analytics_v2.completed` | Analytics processing complete | Alternative analytics completion event |
| `book.detect.signal_found` | Book-level fraud summary | After all document fraud detection |
| `book.completed` | All processing tasks done | Final event — ANALYTICS, CAPTURE, DETECT all complete |

### Processing Flow (Observed Order)

```
Upload documents to book
    │
    ├── document.upload_succeeded        (per document, immediate)
    │
    ├── document.verification_succeeded  (per document, after OCR)
    │
    ├── book.verified                    (book-level, all docs done)
    │
    ├── book.analytics_v2.generated      (cash flow analytics ready)
    │
    ├── document.detect.signal_found     (per document, fraud signals)
    │
    ├── book.detect.signal_found         (book-level fraud summary)
    │
    └── book.completed                   (all tasks: ANALYTICS, CAPTURE, DETECT)
```

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

**Note:** The fraud webhook only signals that fraud was detected. To get specific reason codes and authenticity scores, call `GET /v2/detect/document/{doc_uuid}/signals`.

## Webhook Headers

| Header | Content | Example |
|--------|---------|---------|
| `Webhook-Signature` | HMAC-SHA256 hex digest | (present when a signing secret is configured) |
| `Webhook-Timestamp` | Timestamp string | `1710960000` |
| `Webhook-Request-Id` | UUID for this delivery | `019d0c76-a902-7b75-8f9e-8694eae8a374` |
| `Content-Type` | Always JSON | `application/json` |

## Signature Verification (HMAC-SHA256)

Configure a signing secret first (via the dashboard, or via `POST /v1/account/settings/webhooks/secret` if your tenant has the API enabled). Until a secret is configured, deliveries arrive without a `Webhook-Signature` header — handlers should log a warning rather than reject these events.

### Verification Algorithm

```python
import hmac
import hashlib

def verify_webhook(headers: dict, body: bytes, secret: str) -> bool:
    timestamp = headers.get("Webhook-Timestamp", "")
    request_id = headers.get("Webhook-Request-Id", "")
    received_signature = headers.get("Webhook-Signature", "")

    # If no signature header, the secret may not be configured
    if not received_signature:
        return True  # Accept but log warning

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
8. **Expecting fraud details in webhook** -- The webhook only signals detection. Call `/v2/detect/document/{uuid}/signals` for reason codes.
