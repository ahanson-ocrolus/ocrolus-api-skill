# Ocrolus Webhooks -- Production Reference

> Source: https://docs.ocrolus.com/docs/webhook-overview, secure-webhook-urls
> **VALIDATED** against live tenant (ahanson_personalOrg) on 2026-03-20.
> Event names and payload structures below are from real production webhooks.

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

| Operation | Method | Path | Status |
|-----------|--------|------|--------|
| Add Webhook | POST | `/v1/account/settings/webhook` | CONFIRMED |
| List Webhooks | GET | `/v1/account/settings/webhooks` | CONFIRMED |
| Retrieve Webhook | GET | `/v1/account/settings/webhooks/{webhook_id}` | CONFIRMED |
| Update Webhook | PUT | `/v1/account/settings/webhooks/{webhook_id}` | CONFIRMED |
| Delete Webhook | DELETE | `/v1/account/settings/webhooks/{webhook_id}` | CONFIRMED |
| List Events | GET | `/v1/account/settings/webhooks/events` | CONFIRMED (returns 404-in-body if no events configured) |
| Test Webhook | POST | `/v1/account/settings/webhooks/{webhook_id}/test` | CONFIRMED |
| Configure Secret | POST | `/v1/account/settings/webhooks/secret` | NOT AVAILABLE (404 on tested tenant) |

### Account-Level

| Operation | Method | Path | Status |
|-----------|--------|------|--------|
| Configure | POST | `/v1/webhook/configure` | CONFIRMED (route exists) |
| Get Config | GET | `/v1/webhook/configuration` | NOT AVAILABLE (404 on tested tenant) |
| Test | GET/POST | `/v1/webhook/test` | CONFIRMED |
| Configure Secret | POST | `/v1/webhook/secret` | CONFIRMED (route exists) |

## Event Types (VALIDATED)

The following event names were observed from **real production webhook deliveries** on 2026-03-20. The event type field is **`event_name`** (not `event_type`).

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

### Encore / Book Copy Events (not yet validated)
- `book.copy.request_accepted` -- recipient accepted book copy
- `book.copy.request_rejected` -- recipient rejected book copy
- `book.copy.kickout_evaluated` -- automated kick-out evaluation complete

## Webhook Payload Structure (Observed)

Every webhook payload includes these common fields:

```json
{
  "event_name": "book.completed",
  "status": "BOOK_COMPLETE",
  "severity": "MODERATE",
  "notification_type": "STATUS",
  "notification_reason": "Completed tasks: ANALYTICS, CAPTURE, DETECT",
  "book_pk": 71400892,
  "book_uuid": "09c52985-2f05-4022-a738-9277cc335c7e"
}
```

### Document-Level Event Payload

```json
{
  "event_name": "document.verification_succeeded",
  "severity": "LOW",
  "notification_type": "STATUS",
  "notification_reason": "Document verification succeeded",
  "book_pk": 71400892,
  "book_uuid": "09c52985-...",
  "doc_uuid": "5c12b7b2-...",
  "uploaded_doc_pk": 133257741,
  "uploaded_doc_uuid": "5c12b7b2-..."
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
  "book_pk": 71400892,
  "book_uuid": "09c52985-...",
  "book_name": "Jills Coffee - Webhook Test 2",
  "tasks": ["ANALYTICS", "CAPTURE", "DETECT"],
  "uploaded_docs": [
    {"uuid": "5c12b7b2-...", "status": "VERIFICATION_COMPLETE"},
    {"uuid": "b79fb14b-...", "status": "VERIFICATION_COMPLETE"}
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
  "book_pk": 71400892,
  "book_uuid": "09c52985-...",
  "doc_uuid": "5c12b7b2-...",
  "is_cloud_compliant": false,
  "uploaded_doc_name": "Jills Coffee_Business_Bank Statement_01-2024.pdf"
}
```

**Note:** The fraud webhook only signals that fraud was detected. To get specific reason codes and authenticity scores, call `GET /v2/detect/document/{doc_uuid}/signals`.

## Webhook Headers (Observed)

| Header | Content | Example |
|--------|---------|---------|
| `Webhook-Signature` | HMAC-SHA256 hex digest | (present but verification requires matching secret) |
| `Webhook-Timestamp` | Timestamp string | `1710960000` |
| `Webhook-Request-Id` | UUID for this delivery | `019d0c76-a902-7b75-8f9e-8694eae8a374` |
| `Content-Type` | Always JSON | `application/json` |

## Signature Verification (HMAC-SHA256)

### Important Note on Secret Configuration

The API endpoint for configuring webhook secrets (`/v1/account/settings/webhooks/secret`) returned 404 on the tested tenant. The secret may need to be configured through the Ocrolus dashboard rather than via API. Until the secret is confirmed, signature verification should log warnings but not reject events.

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
