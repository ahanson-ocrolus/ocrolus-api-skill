# Tools & Supporting Resources

Additional utilities, examples, specs, and test findings that complement the core SDK and skill. **None of these are required** to use the Ocrolus API — they're here to help with setup, debugging, and integration work.

## Operational Tools

| Tool | What It Does | When to Use |
|------|-------------|-------------|
| `health_check.py` | Probes all API endpoints, generates HTML/JSON/CSV reports | Before go-live, or periodic monitoring |
| `validate_endpoints.py` | Confirms endpoint paths and discovers webhook events on your tenant | First-time setup on a new tenant |
| `webhook_setup.py` | Starts a webhook listener + ngrok tunnel + registers with Ocrolus | Setting up real-time event processing |
| `webhook_verifier.py` | Production webhook receiver with HMAC-SHA256 signature verification | Copy into your project for production use |

```bash
# Validate your tenant's endpoints
python tools/validate_endpoints.py

# Run a health check
python tools/health_check.py

# Set up webhooks (requires ngrok)
python tools/webhook_setup.py auto
```

All tools read credentials from `OCROLUS_CLIENT_ID` and `OCROLUS_CLIENT_SECRET` environment variables.

## Widget Quickstart (`widget-quickstart/`)

A Python/Flask implementation of the [Ocrolus embeddable widget](https://docs.ocrolus.com/docs/widget), mirroring the official [widget-quickstart](https://github.com/Ocrolus/widget-quickstart) (which only has Node.js and PHP backends).

See [`widget-quickstart/README.md`](widget-quickstart/README.md) for full setup instructions.

```bash
cd tools/widget-quickstart
cp .env.example .env  # fill in credentials
pip install flask requests python-dotenv
python widget_app.py
```

## Other Contents

| Path | Description |
|------|-------------|
| `FINDINGS.md` | Live testing report — API corrections, webhook event discovery, endpoint aliases |
| `docs/` | OpenAPI specs (generated + official `ocrolus-api-official-openapi3.yaml`) |
| `tests/` | pytest integration tests (`test_fixtures.py`) |
| `maintenance/` | Internal scripts for spec generation and endpoint probing |
