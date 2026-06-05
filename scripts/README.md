# Scripts

Executable utilities bundled with this skill. None are required to *use* the Ocrolus API — they're here to help an agent (or a developer) validate, debug, and operate an integration.

| Script | What it does | When to use |
|--------|--------------|-------------|
| `ocrolus_client.py` | Python SDK + CLI covering every public endpoint | Anywhere you want a typed wrapper instead of raw `requests`; also runs as a CLI for quick checks |
| `health_check.py` | Probes every documented endpoint on your tenant, emits HTML/JSON dashboard | Sanity-check before go-live; periodic monitoring; verifying credentials work |
| `webhook_setup.py` | Local webhook listener + ngrok tunnel + auto-registration with Ocrolus | Setting up real-time event processing during development |
| `webhook_verifier.py` | Drop-in HMAC-SHA256 verifier you can copy into your production handler | Production webhook receivers |
| `check_endpoint_drift.py` | Asserts every API path in SKILL.md / references / scripts exists in the canonical `references/endpoints.md` | Pre-commit / CI gate against endpoint drift |

All scripts read credentials from `OCROLUS_CLIENT_ID` / `OCROLUS_CLIENT_SECRET` environment variables.

## SDK + CLI

```python
from scripts.ocrolus_client import OcrolusClient  # or copy the file into your project

client = OcrolusClient()
env = client.create_book("My Book")
book_uuid = env["response"]["uuid"]
print(client.get_book_classification_summary(book_uuid))
```

```bash
python scripts/ocrolus_client.py list-books
python scripts/ocrolus_client.py create-book "Test Book"
python scripts/ocrolus_client.py book-status 12345
```

## Health check

```bash
python scripts/health_check.py --output-dir reports/
# open reports/health-check-<timestamp>.html
```

The probe uses placeholder UUIDs for `{book_uuid}` / `{doc_uuid}` slots, so endpoints that strictly validate a resource ID will return HTTP 404 — that's expected on a brand-new tenant with no real data. Endpoints that route correctly with a placeholder return 200 with an envelope-wrapped error.

## Endpoint drift guard

`references/endpoints.md` is the canonical, live-validated inventory of API paths
(the official OpenAPI spec is incomplete). This guard keeps every other file
consistent with it:

```bash
python scripts/check_endpoint_drift.py    # exit 0 if consistent, 1 + a list on drift
```

Validate `endpoints.md` itself against your tenant with `health_check.py`; the
guard only enforces that SKILL.md, the other references, and the scripts agree
with it. No extra dependencies (standard library only).

## Webhook setup (development)

```bash
python scripts/webhook_setup.py auto
```

Requires `ngrok` on your `$PATH`. Registers the tunnel URL as a webhook in your Ocrolus org and prints the signing secret to copy into `OCROLUS_WEBHOOK_SECRET`.

## Webhook verifier

`webhook_verifier.py` is a self-contained module — copy it into your service. It exposes a single function:

```python
from webhook_verifier import verify_webhook_signature

if not verify_webhook_signature(request.headers, request.get_data(), OCROLUS_WEBHOOK_SECRET):
    abort(401)
```

Verify against the **raw** request body, before JSON parsing — see `references/webhooks.md`.
