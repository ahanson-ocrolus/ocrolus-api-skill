# Ocrolus API Integration Toolkit

A Python SDK and tools for the Ocrolus Document Automation Platform API.

## Quick Setup

```bash
pip install -r requirements.txt
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"
```

Get credentials from: Ocrolus Dashboard > Account & Settings > API Credentials

## Quick Start

```python
from ocrolus_client import OcrolusClient

client = OcrolusClient()  # reads from env vars

# Create a book and upload documents
book = client.create_book("Loan Application #12345")
book_pk = book["pk"]       # integer -- used by v1 endpoints
book_uuid = book["uuid"]   # UUID string -- used by v2 endpoints

client.upload_pdf(book_pk, "bank_statement.pdf")

# Wait for processing (or use webhooks for real-time updates)
client.wait_for_book(book_pk, timeout=600)

# Get results
forms = client.get_book_forms(book_pk)                   # Capture
fraud = client.get_book_fraud_signals(book_uuid)         # Detect
summary = client.get_book_summary(book_uuid)             # Analyze
income = client.get_income_calculations(book_uuid)       # Income
```

The SDK also works as a CLI:

```bash
python ocrolus_client.py list-books
python ocrolus_client.py create-book "Test Book"
python ocrolus_client.py book-status 12345
```

---

## What's in This Repo

```
ocrolus-api/
  ocrolus_client.py               # Python SDK (74 methods) -- start here
  requirements.txt                # Dependencies (core + optional)
  references/
    endpoints.md                  # Full endpoint inventory (validated)
    detect.md                     # Fraud detection: signals, scores, reason codes
    webhooks.md                   # Webhook events, payloads, processing flow
    coverage-matrix.md            # Endpoint coverage and validation status
  tools/                          # Optional operational tools (see tools/README.md)
    health_check.py               # API health check with HTML/JSON/CSV reports
    webhook_setup.py              # Webhook listener + ngrok + registration
    webhook_verifier.py           # Production webhook receiver (HMAC-SHA256)
    validate_endpoints.py         # Endpoint validation for your tenant
  tests/
    test_fixtures.py              # pytest integration tests
  examples/
    widget_app.py                 # Widget embedding sample (requires manual step)
  docs/                           # OpenAPI specs (generated + official)
  maintenance/                    # Internal tools (not for end users)
  FINDINGS.md                     # Live testing report and API corrections
```

---

## Key Concepts

### Book Identifiers

Ocrolus uses two identifiers for Books. **Never mix them.**

| Identifier | Format | Used By |
|-----------|--------|---------|
| `book_pk` | Integer (e.g., `12345`) | v1 endpoints: upload, forms, transactions, status |
| `book_uuid` | UUID string | v2 endpoints: analytics, detect, income, classify |

Both are returned when you create a book. v1 endpoints reject UUIDs and v2 endpoints reject PKs.

### Processing Modes

| Mode | Speed | Accuracy | Use Case |
|------|-------|----------|----------|
| Classify | Fastest | Classification only | Document triage |
| Instant | Fast | Good | High-volume automated processing |
| Complete | Slowest | Highest (human review) | Mortgage, high-stakes decisions |

### Document Status Flow

```
UPLOADED -> PROCESSING -> CLASSIFICATION_COMPLETE -> CAPTURE_COMPLETE -> VERIFICATION_COMPLETE
```

Poll with `client.get_book_status(book_pk)` or use webhooks for real-time updates.

---

## SDK Reference

The SDK (`ocrolus_client.py`) covers 74 methods:

| Category | Methods | ID Type |
|----------|---------|---------|
| Book Operations | 8 | `book_pk` (int) |
| Document Upload & Management | 13 | `book_pk` / `doc_uuid` |
| Classification (Classify) | 3 | `book_uuid` |
| Data Extraction (Capture) | 7 | `book_pk` / `doc_uuid` |
| Fraud Detection (Detect) | 3 | `book_uuid` / `doc_uuid` |
| Cash Flow Analytics | 6 | `book_uuid` |
| Income Calculations | 7 | `book_uuid` |
| Tag Management | 8 | `tag_uuid` / `book_uuid` |
| Encore / Book Copy | 6 | `book_pk` / `job_id` |
| Webhooks (Org-Level) | 8 | `webhook_id` |
| Webhooks (Account-Level) | 4 | -- |
| Helpers | 1 | `book_pk` |

### Fraud Detection Example

```python
signals = client.get_book_fraud_signals(book_uuid)

for doc in signals.get("documents", []):
    score = doc.get("authenticity_score")
    if score is not None and score < 61:
        print(f"LOW AUTHENTICITY ({score}/100) -- review required")
        for code in doc.get("reason_codes", []):
            print(f"  {code['code']}: {code['description']} ({code['confidence']})")
```

See `references/detect.md` for the full authenticity score reference.

---

## Optional: Webhooks

Set up real-time event processing with the webhook tools in `tools/`:

```bash
# Auto setup: starts listener + ngrok tunnel + registers with Ocrolus
python tools/webhook_setup.py auto

# Or manual setup:
python tools/webhook_setup.py listen --port 8080  # Terminal 1
ngrok http 8080                                     # Terminal 2
python tools/webhook_setup.py register --url https://YOUR-URL.ngrok-free.dev/webhooks/ocrolus
```

**After registration, you must subscribe to events in the Ocrolus dashboard:**
1. Go to Dashboard > Settings > Webhooks
2. Click Edit on your webhook
3. Select event types (e.g., `book.completed`, `document.verification_succeeded`)
4. Save

Without this step, no events will be delivered.

The listener provides a live dashboard at `http://localhost:8080/activity` and auto-fetches
book analytics when `book.completed` events arrive.

See `references/webhooks.md` for event names, payloads, and processing flow.

---

## Optional: Health Check

Validate all API endpoints on your tenant:

```bash
python tools/health_check.py              # Console + JSON + HTML reports
python tools/health_check.py --webhooks   # Include webhook validation
```

---

## Optional: Widget Embedding

```bash
export OCROLUS_WIDGET_CLIENT_ID="widget_id"
export OCROLUS_WIDGET_CLIENT_SECRET="widget_secret"
python examples/widget_app.py
```

**Requires manual step:** You must paste your widget `<script>` tag from the Ocrolus
Dashboard into the HTML template. See the comment in `examples/widget_app.py`.

---

## Running Tests

```bash
# Offline tests (no credentials needed):
pytest tests/test_fixtures.py::TestWebhookVerification -v

# Live API tests (requires credentials):
pytest tests/test_fixtures.py -v
```

---

## Troubleshooting

**Authentication fails:**
- Verify `OCROLUS_CLIENT_ID` and `OCROLUS_CLIENT_SECRET` are set
- Auth uses form-encoded POST, not JSON. Do not include an `audience` parameter.

**Endpoint returns 404:**
- Run `python tools/validate_endpoints.py` to check which path variant your tenant accepts

**Webhooks not arriving:**
- You must manually subscribe to events in the Ocrolus dashboard after registration
- Run `python tools/validate_endpoints.py --webhooks` to discover event names

**Widget doesn't render:**
- Widget credentials are separate from API credentials
- You must insert the `<script>` tag from your Dashboard

---

## API Corrections from Live Testing

This toolkit was validated against a live Ocrolus tenant. Key corrections from the
official documentation (see [FINDINGS.md](FINDINGS.md) for full details):

| Issue | Documented | Actual |
|-------|-----------|--------|
| Book create endpoint | `/v1/book/create` | `/v1/book/add` |
| Upload field name | `book_pk` | `pk` |
| Auth format | JSON with audience | Form-encoded, no audience |
| Webhook event field | `event_type` | `event_name` |
| Upload path style | `/v1/book/{pk}/upload/pdf` | `/v1/book/upload` with `pk` in form data |

---

## Ocrolus Documentation

- API Guide: https://docs.ocrolus.com/docs/guide
- API Reference: https://docs.ocrolus.com/reference
- Authentication: https://docs.ocrolus.com/docs/using-api-credentials
- Webhooks: https://docs.ocrolus.com/docs/webhook-overview
- Detect: https://docs.ocrolus.com/docs/detect
- Widget: https://docs.ocrolus.com/docs/widget
