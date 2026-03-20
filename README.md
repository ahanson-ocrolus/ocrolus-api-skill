# Ocrolus API Integration Toolkit

A complete integration toolkit for the Ocrolus Document Automation Platform API.
Includes a Python SDK, webhook handling, fraud detection support, widget embedding,
and test fixtures.

---

## What's Included

```
ocrolus-api/
  SKILL.md                              # Skill definition (for Claude Code)
  README.md                             # This file
  FINDINGS.md                           # Live testing findings and API corrections
  references/
    endpoints.md                        # Full endpoint inventory (VALIDATED)
    detect.md                           # Fraud detection: signals, scores, reason codes
    webhooks.md                         # Webhook setup, events, payloads (VALIDATED)
    coverage-matrix.md                  # Endpoint coverage tracking (VALIDATED)
  scripts/
    ocrolus_client.py                   # Python SDK -- importable module, 74 methods
    validate_endpoints.py               # Endpoint validation against your live tenant
    health_check.py                     # Comprehensive API health check (console/JSON/HTML)
    webhook_setup.py                    # Webhook listener, ngrok tunnel, registration
    webhook_verifier.py                 # Production webhook receiver with HMAC-SHA256
    generate_openapi.py                 # OpenAPI 3.0 / Swagger 2.0 spec generator
    test_fixtures.py                    # pytest suite for integration testing
  docs/
    ocrolus-api-openapi3.json           # Generated OpenAPI 3.0 spec
    ocrolus-api-openapi3.yaml           # Generated OpenAPI 3.0 spec (YAML)
    ocrolus-api-swagger2.json           # Generated Swagger 2.0 spec
  examples/
    widget_app.py                       # Widget embedding sample (Flask)
  reports/                              # Generated reports (gitignored)
    webhook-events/events.jsonl         # Persistent webhook event log
    webhook-events/book-reports/        # Auto-fetched book analytics
```

## Key Corrections from Live Testing

> See [FINDINGS.md](FINDINGS.md) for the complete report.

| Issue | Documented | Actual (Confirmed) |
|-------|-----------|-------------------|
| Book create endpoint | `/v1/book/create` | **`/v1/book/add`** |
| Upload book identifier field | `book_pk` | **`pk`** |
| Auth request format | JSON with audience | **Form-encoded, no audience** |
| Webhook event field name | `event_type` | **`event_name`** |
| Upload path style | `/v1/book/{pk}/upload/pdf` | **404** — use `/v1/book/upload` with `pk` in form data |

---

## Before You Start: What You Need

| Requirement | Where to Get It |
|------------|----------------|
| Ocrolus API credentials (`client_id`, `client_secret`) | Ocrolus Dashboard > Account & Settings > API Credentials |
| Python 3.9+ | https://python.org |
| `requests` library | `pip install requests` |
| `flask` library (for webhooks and widget) | `pip install flask` |
| `pytest` library (for tests) | `pip install pytest` |

### Install dependencies

```bash
pip install requests flask pytest
```

### Set environment variables

```bash
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"

# Only if using webhooks:
export OCROLUS_WEBHOOK_SECRET="your_webhook_secret"

# Only if using the widget:
export OCROLUS_WIDGET_CLIENT_ID="your_widget_client_id"
export OCROLUS_WIDGET_CLIENT_SECRET="your_widget_client_secret"
```

---

## Setup

### Prerequisites

```bash
pip3 install requests flask
brew install ngrok  # for webhook testing (optional)
```

### 1. Set Credentials

```bash
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"
```

### 2. Run Health Check

The health check probes all 78 API endpoints and generates console, JSON, and HTML reports with export buttons.

```bash
# Basic health check (console + JSON + HTML reports)
python scripts/health_check.py

# Include webhook operational validation
python scripts/health_check.py --webhooks

# Output options
python scripts/health_check.py --output-dir ./reports
python scripts/health_check.py --html-only
python scripts/health_check.py --json-only
python scripts/health_check.py --console-only

# Repeated monitoring
python scripts/health_check.py --repeat 5 --interval 120
```

The HTML report includes **Export JSON**, **Export CSV**, and **Save HTML Snapshot** buttons for archiving results.

### 3. Set Up Webhook Listener

The webhook listener receives real-time event notifications from Ocrolus as documents are processed.

```bash
# Option A: Full auto setup (starts listener + ngrok tunnel + registers with Ocrolus)
python scripts/webhook_setup.py auto

# Option B: Manual setup
# Terminal 1: Start listener
python scripts/webhook_setup.py listen --port 8080

# Terminal 2: Start ngrok
ngrok http 8080

# Terminal 3: Register with Ocrolus
python scripts/webhook_setup.py register --url https://YOUR-URL.ngrok-free.dev/webhooks/ocrolus
```

**IMPORTANT: After registration, you must subscribe to events in the Ocrolus dashboard:**
1. Go to Ocrolus Dashboard > Settings > Webhooks
2. Click Edit on your webhook
3. Select the event types you want to receive (e.g., `book.completed`, `document.verification_succeeded`)
4. Save

Without this manual step, no events will be delivered even though the webhook is registered.

#### Webhook Dashboard & Exports

Once the listener is running:

| URL | Description |
|-----|-------------|
| `http://localhost:8080/activity` | Live activity dashboard (auto-refreshes every 15s) |
| `http://localhost:8080/health` | JSON health/stats endpoint |
| `http://localhost:8080/export/json` | Download all events as JSON |
| `http://localhost:8080/export/csv` | Download all events as CSV |
| `http://localhost:8080/export/html` | Download static HTML snapshot |

Events are persisted to `reports/webhook-events/events.jsonl` and survive listener restarts.

#### Auto-Fetch on Book Completion

When a `book.verified` or `book.completed` webhook arrives, the listener automatically:
1. Fetches the book summary via `/v2/book/{uuid}/summary`
2. Fetches enriched transactions via `/v2/book/{uuid}/enriched_txns`
3. Saves the combined report to `reports/webhook-events/book-reports/`

### 4. Generate API Documentation

Generate OpenAPI 3.0 and Swagger 2.0 specs from the endpoint definitions:

```bash
python scripts/generate_openapi.py
# Output: docs/ocrolus-api-openapi3.json, .yaml, and swagger2.json
```

### 5. Validate Endpoints on Your Tenant

If running on a different tenant, validate that all endpoints match:

```bash
# Read-only validation
python scripts/validate_endpoints.py

# Full validation (creates + deletes a test book)
python scripts/validate_endpoints.py --write-paths

# Discover webhook event names
python scripts/validate_endpoints.py --webhooks
```

---

## Quick Start

### 1. Basic API Usage

```python
from scripts.ocrolus_client import OcrolusClient

client = OcrolusClient()  # reads from OCROLUS_CLIENT_ID/SECRET env vars

# Create a book
book = client.create_book("Loan Application #12345")
book_pk = book["pk"]       # integer -- used by v1 endpoints
book_uuid = book["uuid"]   # UUID string -- used by v2 endpoints

# Upload documents
client.upload_pdf(book_pk, "bank_statement.pdf")
client.upload_mixed_pdf(book_pk, "loan_package.pdf")

# Wait for processing (or use webhooks -- see below)
client.wait_for_book(book_pk, timeout=600)

# Get results
forms = client.get_book_forms(book_pk)                   # Capture
fraud = client.get_book_fraud_signals(book_uuid)         # Detect
summary = client.get_book_summary(book_uuid)             # Analyze
income = client.get_income_calculations(book_uuid)       # Income
```

### 2. Fraud Detection with Authenticity Scores

```python
signals = client.get_book_fraud_signals(book_uuid)

for doc in signals.get("documents", []):
    score = doc.get("authenticity_score")
    if score is not None and score < 61:
        print(f"LOW AUTHENTICITY ({score}/100) -- review required")
        for code in doc.get("reason_codes", []):
            print(f"  {code['code']}: {code['description']} ({code['confidence']})")

        # Get visual overlay for fraud analysts
        for signal in doc.get("signals", []):
            viz_uuid = signal.get("visualization_uuid")
            if viz_uuid:
                image = client.get_fraud_visualization(viz_uuid)
                with open(f"fraud_{viz_uuid}.png", "wb") as f:
                    f.write(image)
```

See `references/detect.md` for the full authenticity score reference (0-100 scale,
reason code format, signal types, threshold guidance).

### 3. Webhook Receiver

```bash
# STEP 1: Discover your tenant's actual event names and payload field
python scripts/validate_endpoints.py --webhooks
# This prints the canonical event names and the JSON field they use.
# Example output:
#   Event type field name in payloads: "event_type"
#   Extracted event names:
#     - document.verification_complete
#     - book.processing_complete
#     - ...

# STEP 2: Update the event names in webhook_verifier.py to match
# (Replace the PLACEHOLDER strings with the exact names from Step 1)

# STEP 3: Start the webhook receiver
export OCROLUS_WEBHOOK_SECRET="your-secret"
export OCROLUS_EVENT_TYPE_FIELD="event_type"  # from Step 1 output
python scripts/webhook_verifier.py

# STEP 4: Register your webhook URL with Ocrolus (one-time):
# Use the EXACT event names from Step 1 in the events list below:
python -c "
from scripts.ocrolus_client import OcrolusClient
client = OcrolusClient()
# List available events first:
print(client.list_org_webhook_events())
# Then register with the actual event names:
client.add_org_webhook(
    url='https://your-domain.com/webhooks/ocrolus',
    events=['...']  # paste actual event names from list above
)
"
```

The webhook verifier includes:
- HMAC-SHA256 signature verification
- Timestamp freshness checking (rejects replays > 5 min old)
- Configurable event type field name (not hardcoded to "event_type")
- Fallback detection if the field name doesn't match (logs a warning with the correct field)
- Event routing with `@handler.on("event_name")` decorators
- Default handler that catches and logs unrecognized events (safety net during initial rollout)
- Secret rotation support (validate against old + new during rotation)

See `references/webhooks.md` for the full webhook reference.

### 4. Widget Embedding

```bash
export OCROLUS_WIDGET_CLIENT_ID="widget_id"
export OCROLUS_WIDGET_CLIENT_SECRET="widget_secret"
python examples/widget_app.py
# Open http://localhost:5000
```

**Important:** The widget app requires one manual step -- you must paste your
widget `<script>` tag from the Ocrolus Dashboard into the HTML template.
The script URL is unique to your account and cannot be retrieved programmatically.
See the `MANUAL STEP REQUIRED` comment in `examples/widget_app.py`.

### 5. Run Tests

```bash
# Run webhook signature tests (no credentials needed):
pytest scripts/test_fixtures.py::TestWebhookVerification -v

# Run API integration tests (requires credentials):
export OCROLUS_CLIENT_ID="your_id"
export OCROLUS_CLIENT_SECRET="your_secret"
pytest scripts/test_fixtures.py -v

# Run specific test categories:
pytest scripts/test_fixtures.py::TestBookOperations -v
pytest scripts/test_fixtures.py::TestDocumentUpload -v
pytest scripts/test_fixtures.py::TestTagManagement -v
```

---

## SDK Reference

The Python SDK (`scripts/ocrolus_client.py`) covers 74 methods across all
Ocrolus API capabilities:

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

The SDK also works as a CLI for quick testing:

```bash
python scripts/ocrolus_client.py list-books
python scripts/ocrolus_client.py create-book "Test Book"
python scripts/ocrolus_client.py book-status 12345
```

---

## Key Concepts

### Book Identifiers

Ocrolus uses two identifiers for Books. **Never mix them.**

| Identifier | Format | Used By |
|-----------|--------|---------|
| `book_pk` | Integer (e.g., `12345`) | v1 endpoints: upload, forms, transactions, status |
| `book_uuid` | UUID string | v2 endpoints: analytics, detect, income, classify |

Both are returned when you create a book:
```python
book = client.create_book("My Book")
book_pk = book["pk"]       # 12345
book_uuid = book["uuid"]   # "a1b2c3d4-..."
```

### Processing Modes

| Mode | Speed | Accuracy | Use Case |
|------|-------|----------|----------|
| Classify | Fastest | Classification only | Document triage |
| Instant | Fast | Good | High-volume automated processing |
| Instant Classify with UV | Fast | Classification + key fields | Dedup and grouping |
| Complete | Slowest | Highest (human review) | Mortgage, high-stakes decisions |

### Document Status Flow

```
UPLOADED -> PROCESSING -> CLASSIFICATION_COMPLETE -> CAPTURE_COMPLETE -> VERIFICATION_COMPLETE
```

Poll with `client.get_book_status(book_pk)` or use webhooks for real-time updates.

---

## File Reference

| File | What It's For |
|------|--------------|
| `references/endpoints.md` | Every API endpoint with path, method, and validation status |
| `references/detect.md` | Authenticity scores (0-100), reason codes, signal types, thresholds |
| `references/webhooks.md` | HMAC-SHA256 verification, event types, handler patterns, secret rotation |
| `references/coverage-matrix.md` | Tracks which endpoints are covered in SDK vs documented vs live-validated |
| `scripts/ocrolus_client.py` | Importable Python SDK with 74 methods and CLI entrypoint |
| `scripts/webhook_verifier.py` | Production-ready Flask webhook receiver with signature verification |
| `scripts/test_fixtures.py` | pytest suite with fixtures for uploads, Plaid, income, Detect, tags |
| `scripts/validate_endpoints.py` | Probes your tenant to confirm paths and discover webhook events |
| `examples/widget_app.py` | Flask app for embedding the Ocrolus widget (requires manual script tag) |

---

## Troubleshooting

**Authentication fails:**
- Verify `OCROLUS_CLIENT_ID` and `OCROLUS_CLIENT_SECRET` are set correctly
- Credentials are created in Dashboard > Account & Settings > API Credentials
- Basic Auth is deprecated -- use OAuth 2.0

**Endpoint returns 404:**
- Run `validate_endpoints.py` to check which path variant your tenant accepts
- Some paths differ between doc versions (query param vs path param)

**Webhook handler receives events but doesn't process them:**
- Event type strings may not match -- run `validate_endpoints.py --webhooks`
  to discover canonical event names
- Check logs for "Unhandled webhook event type" warnings

**Widget doesn't render:**
- You must insert the widget `<script>` tag from your Dashboard (see widget_app.py)
- Widget credentials are separate from API credentials
- Widget auth URL is `https://jwe-issuer.ocrolus.net/token` (not the main API auth URL)

---

## Ocrolus Documentation

- API Guide: https://docs.ocrolus.com/docs/guide
- API Reference: https://docs.ocrolus.com/reference
- Authentication: https://docs.ocrolus.com/docs/using-api-credentials
- Webhooks: https://docs.ocrolus.com/docs/webhook-overview
- Detect: https://docs.ocrolus.com/docs/detect
- Widget: https://docs.ocrolus.com/docs/widget
- Supported Documents: https://docs.ocrolus.com/docs/supported-document-types
