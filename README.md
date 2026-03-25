# Ocrolus API Skill

An AI-agent-ready skill for building [Ocrolus](https://www.ocrolus.com/) integrations. Give your AI coding assistant the `SKILL.md` file and it will know how to work with the Ocrolus API — correct endpoints, auth patterns, gotchas, and a validated Python SDK.

## What's Here

```
SKILL.md                  ← The skill file — feed this to your AI agent
ocrolus_client.py         ← Python SDK (74 methods, CLI included)
requirements.txt          ← SDK dependencies
references/               ← API reference docs (endpoints, webhooks, fraud detection)
tools/                    ← Optional utilities, examples, specs, and test findings
```

## Quick Start

### 1. Use with an AI Agent

Point your AI assistant at `SKILL.md`:

- **Claude Code:** Place this repo in your project, and the skill triggers automatically on Ocrolus-related prompts
- **Other agents:** Include `SKILL.md` as context when asking the agent to build Ocrolus integrations

The skill covers authentication, all endpoint paths (with corrections from live testing), webhook event names, fraud detection scoring, and common pitfalls.

### 2. Use the SDK Directly

```bash
pip install -r requirements.txt
export OCROLUS_CLIENT_ID="your_client_id"
export OCROLUS_CLIENT_SECRET="your_client_secret"
```

```python
from ocrolus_client import OcrolusClient

client = OcrolusClient()

# Create a book and upload a document
book = client.create_book("Loan Application #12345")
client.upload_pdf(book["pk"], "bank_statement.pdf")

# Wait for processing, then get results
client.wait_for_book(book["pk"], timeout=600)
fraud = client.get_book_fraud_signals(book["uuid"])
summary = client.get_book_summary(book["uuid"])
```

The SDK also works as a CLI:

```bash
python ocrolus_client.py list-books
python ocrolus_client.py create-book "Test Book"
python ocrolus_client.py book-status 12345
```

## Key Concepts

**Book identifiers** — Ocrolus uses two IDs. Never mix them:

| Identifier | Format | Used By |
|-----------|--------|---------|
| `book_pk` | Integer | v1 endpoints (upload, forms, transactions, status) |
| `book_uuid` | UUID string | v2 endpoints (analytics, detect, income, classify) |

**Processing modes:** Classify (fastest, classification only) → Instant (fast, good accuracy) → Complete (slowest, human review, highest accuracy)

## Tools & Extras

The `tools/` directory has optional utilities — see [`tools/README.md`](tools/README.md):

- **Health check** — probe all API endpoints on your tenant
- **Webhook setup** — listener + ngrok tunnel + auto-registration
- **Widget quickstart** — Python/Flask implementation of the Ocrolus embeddable widget
- **OpenAPI specs** — generated and official
## Ocrolus Documentation

- [API Guide](https://docs.ocrolus.com/docs/guide)
- [API Reference](https://docs.ocrolus.com/reference)
- [Authentication](https://docs.ocrolus.com/docs/using-api-credentials)
- [Webhooks](https://docs.ocrolus.com/docs/webhook-overview)
- [Fraud Detection](https://docs.ocrolus.com/docs/detect)
- [Widget](https://docs.ocrolus.com/docs/widget)
