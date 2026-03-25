# Ocrolus Widget Integration (`widget_app.py`)

A Python/Flask implementation of the [Ocrolus embeddable widget](https://docs.ocrolus.com/docs/widget). This is a Python equivalent of the official [widget-quickstart](https://github.com/Ocrolus/widget-quickstart), which provides Node.js and PHP backends but no Python option.

### What it does

- Serves a page with the Ocrolus widget embedded for document upload and bank linking
- Handles server-side token exchange so credentials are never exposed to the browser
- Listens for widget events (upload received, complete, failed, bank linked)
- Provides a webhook endpoint for Ocrolus document event callbacks

### Prerequisites

- Python 3.8+
- An Ocrolus account with widget access enabled
- Widget credentials from the [Ocrolus Dashboard](https://app.ocrolus.com) > Account & Settings > Embedded Widget

### Quick start

1. **Install dependencies:**

   ```bash
   pip install flask requests python-dotenv
   ```

2. **Configure credentials:**

   ```bash
   cd tools/widget-quickstart
   cp .env.example .env
   ```

   Edit `.env` and fill in your values:

   | Variable | Where to find it |
   |----------|-----------------|
   | `OCROLUS_CLIENT_ID` | Ocrolus Dashboard > API credentials |
   | `OCROLUS_CLIENT_SECRET` | Ocrolus Dashboard > API credentials |
   | `OCROLUS_WIDGET_UUID` | Ocrolus Dashboard > Account & Settings > Embedded Widget |

3. **Run the app:**

   ```bash
   python widget_app.py
   ```

4. **Open** [http://localhost:5000](http://localhost:5000) in your browser.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Widget page (pass `?custom_id=your-user-id` to set the user identifier) |
| `POST` | `/token` | Token exchange — called by the widget SDK, not directly |
| `POST` | `/webhook` | Receives document event callbacks from Ocrolus |
| `GET` | `/health` | Health check — shows whether credentials are configured |

### How the auth flow works

```
Browser                    Your Flask App               Ocrolus
  │                            │                           │
  │  1. Load page              │                           │
  │ ──────────────────────────>│                           │
  │  2. Widget SDK loads       │                           │
  │  3. Widget calls           │                           │
  │     getAuthToken()         │                           │
  │ ──────POST /token─────────>│                           │
  │                            │  4. Exchange credentials   │
  │                            │ ──POST /v1/widget/{uuid}──>│
  │                            │          /token            │
  │                            │<──── access_token ─────────│
  │<──── accessToken ──────────│                           │
  │  5. Widget renders with    │                           │
  │     auth token             │                           │
```

### Webhooks (optional)

To receive document event callbacks:

1. Expose your app to the internet (e.g., using [ngrok](https://ngrok.com/))
2. Configure the webhook URL in the Ocrolus Dashboard pointing to `/webhook`
3. Events like `document.verification_succeeded` will be logged

See the [Ocrolus webhook docs](https://docs.ocrolus.com/docs/webhooks) for the full list of event types.

### Key differences from the official quickstart

| | Official quickstart | This example |
|---|---|---|
| **Backend** | Node.js (Express) or PHP (Lumen) | Python (Flask) |
| **Frontend** | React + TypeScript + Material UI | Vanilla HTML/JS (no build step) |
| **Infrastructure** | Docker Compose + Caddy reverse proxy | Single file, run directly |
| **Scope** | Full production-ready scaffold | Minimal working reference |

### References

- [Widget documentation](https://docs.ocrolus.com/docs/widget)
- [Official widget-quickstart repo](https://github.com/Ocrolus/widget-quickstart)
- [Webhook documentation](https://docs.ocrolus.com/docs/webhooks)
- [Ocrolus API docs](https://docs.ocrolus.com/reference)
