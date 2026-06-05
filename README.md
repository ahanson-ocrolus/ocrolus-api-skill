# Ocrolus API Skill

An AI-agent-ready Claude Skill for building [Ocrolus](https://www.ocrolus.com/) integrations. Drop the folder into your project and your AI coding assistant gets the right endpoints, auth patterns, webhook events, and a validated Python SDK — no trial-and-error needed.

This skill is aligned to the public docs at <https://docs.ocrolus.com/reference> and follows the [Anthropic Skills authoring standard](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf).

## What's Here

```
SKILL.md                     ← The skill — entry point read by Claude
scripts/                     ← Executable code
   ocrolus_client.py            SDK + CLI (74 methods, all docs-aligned)
   health_check.py              Probe every endpoint on your tenant
   webhook_setup.py             Local listener + ngrok tunnel + auto-registration
   webhook_verifier.py          HMAC-SHA256 verifier you can drop into production
references/                  ← Detailed docs loaded on demand
   endpoints.md                 Full endpoint inventory (Books, Capture, Detect, ...)
   detect.md                    Authenticity scores, reason codes, signal taxonomy
   webhooks.md                  Event names + signature verification
   openapi/                     Official OpenAPI 3.1 spec
examples/                    ← Runnable example apps
   widget-quickstart/           Python/Flask embed of the Ocrolus widget
requirements.txt
```

## Quick Start

### Use with an AI agent

Point your AI assistant at `SKILL.md`:

- **Claude Code** — place this folder somewhere on your skill search path; the skill activates on Ocrolus-related prompts.
- **Other agents** — include `SKILL.md` as context when asking for Ocrolus integration help.

The skill covers authentication, capability-organized endpoints (Classify, Capture, Detect, Analyze, Income, Encore), webhooks, and the things developers commonly miss.

### Use the SDK directly

```bash
pip install -r requirements.txt
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"
```

```python
from scripts.ocrolus_client import OcrolusClient

client = OcrolusClient()

book = client.create_book("Application #12345")
client.upload_pdf(book["response"]["pk"], "bank_statement.pdf")
client.wait_for_book(book_pk=book["response"]["pk"], timeout=600)

book_uuid = book["response"]["uuid"]
summary = client.get_book_summary(book_uuid)
fraud   = client.get_book_fraud_signals(book_uuid)
income  = client.get_income_calculations(book_uuid)
```

The SDK also runs as a CLI:

```bash
python scripts/ocrolus_client.py list-books
python scripts/ocrolus_client.py create-book "Test Book"
python scripts/ocrolus_client.py book-status 12345
```

## Key Concepts

**Book identifiers** — Ocrolus uses two IDs. v1 endpoints typically take the integer `pk`; v2 endpoints take the `uuid`. They are not interchangeable.

| Identifier | Format | Used by |
|------------|--------|---------|
| `pk` | Integer | v1 endpoints (uploads, status, forms via query) |
| `uuid` | UUID string | v2 endpoints (Classify, Detect, Analyze, Income) |

**Processing modes:** Classify (fastest, classification only) → Instant (fast, good accuracy) → Complete (slowest, human-verified, highest accuracy).

**Response envelopes** — Most Ocrolus responses are wrapped in `{ status, code, response, message, meta }` and return HTTP 200 even on logical errors. Check `envelope.status` (or `code`), not just the HTTP status.

## Scripts & Examples

See [`scripts/README.md`](scripts/README.md) for details on each utility:

- **`scripts/health_check.py`** — probes every documented endpoint on your tenant; generates console + JSON + HTML dashboard.
- **`scripts/webhook_setup.py`** — spins up a local listener, opens an ngrok tunnel, registers the webhook with Ocrolus.
- **`scripts/webhook_verifier.py`** — drop-in HMAC-SHA256 verification for production handlers.
- **`examples/widget-quickstart/`** — Python/Flask implementation of the Ocrolus embeddable upload widget.
- **`references/openapi/`** — official OpenAPI 3.1 YAML. (For an interactive collection, use the official Postman collection linked from <https://docs.ocrolus.com/reference>.)

## Ocrolus Documentation

- [API Reference](https://docs.ocrolus.com/reference) — source of truth this skill is aligned to
- [API Guide](https://docs.ocrolus.com/docs/guide)
- [Authentication](https://docs.ocrolus.com/docs/using-api-credentials)
- [Webhooks](https://docs.ocrolus.com/docs/webhook-overview)
- [Fraud Detection](https://docs.ocrolus.com/docs/detect)
- [Widget](https://docs.ocrolus.com/docs/widget)
