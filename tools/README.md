# Optional Tools

These tools are **not required** to use the Ocrolus API SDK. They are operational
utilities for validating, monitoring, and debugging your integration.

| Tool | What It Does | When to Use |
|------|-------------|-------------|
| `health_check.py` | Probes all API endpoints, generates HTML/JSON/CSV reports | Before go-live, or for periodic monitoring |
| `validate_endpoints.py` | Confirms endpoint paths and discovers webhook events on your tenant | First-time setup on a new tenant |
| `webhook_setup.py` | Starts a webhook listener + ngrok tunnel + registers with Ocrolus | When setting up real-time event processing |
| `webhook_verifier.py` | Production webhook receiver with HMAC-SHA256 signature verification | Copy into your own project for production use |

## Quick Start

```bash
# Validate your tenant's endpoints
python tools/validate_endpoints.py

# Run a health check
python tools/health_check.py

# Set up webhooks (requires ngrok)
python tools/webhook_setup.py auto
```

All tools read credentials from `OCROLUS_CLIENT_ID` and `OCROLUS_CLIENT_SECRET` environment variables.
