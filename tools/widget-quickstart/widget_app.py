"""
Ocrolus Widget — Python/Flask Quickstart
=========================================

A Python implementation of the Ocrolus Widget integration, mirroring the
official widget-quickstart (https://github.com/Ocrolus/widget-quickstart)
which provides Node.js and PHP backends. This gives Python developers a
ready-to-use reference.

Endpoints:
    GET  /           — Serves the widget page
    POST /token      — Server-side token exchange (called by the widget)
    POST /webhook    — Receives document event callbacks from Ocrolus
    GET  /health     — Health check

Requirements:
    pip install flask requests python-dotenv

Setup:
    1. Copy .env.example to .env and fill in your credentials
    2. Get your Widget UUID from Ocrolus Dashboard > Account & Settings > Embedded Widget
    3. Run: python widget_app.py
    4. Open: http://localhost:5000

Environment variables:
    OCROLUS_CLIENT_ID        — Your Ocrolus API client ID
    OCROLUS_CLIENT_SECRET    — Your Ocrolus API client secret
    OCROLUS_WIDGET_UUID      — Your widget UUID from the Ocrolus Dashboard
    OCROLUS_WIDGET_ENVIRONMENT — "production" or "sandbox" (default: production)

References:
    - Widget docs:      https://docs.ocrolus.com/docs/widget
    - Official starter: https://github.com/Ocrolus/widget-quickstart
"""

import os
import sys

try:
    from flask import Flask, request, jsonify, render_template_string
    import requests as http_requests
except ImportError:
    print("Required: pip install flask requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


# =============================================================================
# CONFIGURATION
# =============================================================================

WIDGET_BASE_URL = "https://widget.ocrolus.com"
AUTH_BASE_URL = "https://auth.ocrolus.com"
API_BASE_URL = "https://api.ocrolus.com"

OCROLUS_CLIENT_ID = os.environ.get("OCROLUS_CLIENT_ID", "")
OCROLUS_CLIENT_SECRET = os.environ.get("OCROLUS_CLIENT_SECRET", "")
OCROLUS_WIDGET_UUID = os.environ.get("OCROLUS_WIDGET_UUID", "")
OCROLUS_WIDGET_ENVIRONMENT = os.environ.get("OCROLUS_WIDGET_ENVIRONMENT", "production")

if not OCROLUS_CLIENT_ID or not OCROLUS_CLIENT_SECRET:
    print("WARNING: Set OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET in your .env file")

if not OCROLUS_WIDGET_UUID:
    print("WARNING: Set OCROLUS_WIDGET_UUID in your .env file")


# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)

# HTML template — mirrors the official quickstart's frontend structure
WIDGET_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Upload — Ocrolus Widget</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        .header {
            background: #fff;
            padding: 20px 40px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 { font-size: 20px; font-weight: 600; }
        .header .status {
            font-size: 13px;
            padding: 4px 12px;
            border-radius: 12px;
            background: #e8f5e9;
            color: #2e7d32;
        }
        .header .status.error {
            background: #ffebee;
            color: #c62828;
        }
        .container {
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
        }
        .instructions {
            background: #fff;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #e0e0e0;
        }
        .instructions h2 { font-size: 16px; margin-bottom: 12px; }
        .instructions p { font-size: 14px; color: #666; line-height: 1.6; }
        #ocrolus-widget-frame {
            background: #fff;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            min-height: 600px;
            overflow: hidden;
        }
        .event-log {
            background: #fff;
            border-radius: 8px;
            padding: 24px;
            margin-top: 24px;
            border: 1px solid #e0e0e0;
        }
        .event-log h3 { font-size: 14px; margin-bottom: 12px; }
        .event-log ul {
            list-style: none;
            font-size: 13px;
            font-family: 'SF Mono', Menlo, monospace;
            color: #555;
            max-height: 200px;
            overflow-y: auto;
        }
        .event-log li { padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
        .footer {
            text-align: center;
            padding: 24px;
            font-size: 12px;
            color: #999;
        }
    </style>

    <script>
        // =================================================================
        // Token provider — called by the Ocrolus widget to get auth tokens
        // Mirrors the official quickstart's getAuthToken pattern
        // =================================================================
        async function getAuthToken() {
            try {
                const response = await fetch('/token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        custom_id: '{{ custom_id }}',
                        book_name: 'Widget Upload - {{ custom_id }}'
                    })
                });

                if (!response.ok) {
                    updateStatus('Token request failed', true);
                    throw new Error('Token request failed');
                }

                const data = await response.json();
                updateStatus('Connected');
                return data.accessToken;
            } catch (error) {
                updateStatus('Connection error', true);
                console.error('Token error:', error);
                throw error;
            }
        }

        function updateStatus(text, isError) {
            const el = document.getElementById('connection-status');
            if (el) {
                el.textContent = text;
                el.className = isError ? 'status error' : 'status';
            }
        }

        // =================================================================
        // Widget event listeners — mirrors the official quickstart's
        // postMessage handling for upload lifecycle events
        // =================================================================
        function logEvent(type, detail) {
            const ul = document.getElementById('event-list');
            if (!ul) return;
            const li = document.createElement('li');
            const time = new Date().toLocaleTimeString();
            li.textContent = `[${time}] ${type}` + (detail ? `: ${detail}` : '');
            ul.prepend(li);
        }

        window.addEventListener('message', function(event) {
            const { type, payload } = event.data || {};

            switch (type) {
                case 'USER_UPLOAD_RECEIVED':
                    logEvent('Upload received', payload?.fileName);
                    break;
                case 'USER_UPLOAD_COMPLETE':
                    logEvent('Upload complete', payload?.fileName);
                    updateStatus('Upload complete');
                    break;
                case 'USER_UPLOAD_FAILED':
                    logEvent('Upload failed', payload?.error);
                    updateStatus('Upload failed', true);
                    break;
                case 'LINK_SUCCESS':
                    logEvent('Bank linked successfully');
                    updateStatus('Bank linked');
                    break;
                case 'PLAID_ERROR':
                    logEvent('Plaid error', payload?.error);
                    break;
            }
        });
    </script>

    <!-- Ocrolus Widget Initializer SDK -->
    <script src="https://widget.ocrolus.com/static/initializer-sdk.bundle.js"></script>
    <script>
        // Initialize the widget with your UUID
        // See: https://docs.ocrolus.com/docs/widget
        if (typeof ocrolus_script === 'function') {
            ocrolus_script('init', '{{ widget_uuid }}');
        }
    </script>
</head>
<body>
    <div class="header">
        <h1>Upload Financial Documents</h1>
        <span id="connection-status" class="status">Connecting...</span>
    </div>

    <div class="container">
        <div class="instructions">
            <h2>Upload Your Documents</h2>
            <p>
                Use the widget below to upload your financial documents (bank statements,
                pay stubs, tax forms, etc.) or connect your bank account directly.
                Documents are securely processed by Ocrolus.
            </p>
        </div>

        <!-- Widget renders inside this div — ID must be "ocrolus-widget-frame" -->
        <div id="ocrolus-widget-frame"></div>

        <div class="event-log">
            <h3>Event Log</h3>
            <ul id="event-list"></ul>
        </div>
    </div>

    <div class="footer">
        Powered by Ocrolus Document Automation
    </div>
</body>
</html>
"""


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def index():
    """Serve the widget page."""
    custom_id = request.args.get("custom_id", "demo-user-001")
    return render_template_string(
        WIDGET_PAGE,
        custom_id=custom_id,
        widget_uuid=OCROLUS_WIDGET_UUID,
    )


@app.route("/token", methods=["POST"])
def get_token():
    """
    Server-side token exchange — mirrors the official quickstart's /token endpoint.

    The widget calls getAuthToken() on the client, which POSTs here.
    This endpoint calls the Ocrolus Widget API to get a JWT token.

    IMPORTANT: Never expose credentials to the client side.
    """
    data = request.get_json(silent=True) or {}
    custom_id = data.get("custom_id", "unknown")
    book_name = data.get("book_name", f"Widget Upload - {custom_id}")

    if not OCROLUS_CLIENT_ID or not OCROLUS_CLIENT_SECRET or not OCROLUS_WIDGET_UUID:
        return jsonify({"error": "Widget credentials not configured"}), 500

    try:
        resp = http_requests.post(
            f"{WIDGET_BASE_URL}/v1/widget/{OCROLUS_WIDGET_UUID}/token",
            json={
                "grant_type": "client_credentials",
                "client_id": OCROLUS_CLIENT_ID,
                "client_secret": OCROLUS_CLIENT_SECRET,
                "custom_id": custom_id,
                "book_name": book_name,
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()

        # Return accessToken to match the field name the widget SDK expects
        return jsonify({"accessToken": token_data["access_token"]})

    except http_requests.RequestException as e:
        app.logger.error(f"Token exchange failed: {e}")
        return jsonify({"error": "Failed to obtain token"}), 502


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Webhook endpoint — receives document event callbacks from Ocrolus.

    Configure this URL in the Ocrolus Dashboard to receive notifications
    when documents are uploaded, processed, or verified through the widget.

    In production, validate the webhook source (e.g., IP allowlist or signature).
    See: https://docs.ocrolus.com/docs/webhooks
    """
    event = request.get_json(silent=True) or {}
    event_type = event.get("type", "unknown")

    app.logger.info(f"Webhook received: {event_type}")
    app.logger.debug(f"Webhook payload: {event}")

    # Handle document verification events
    if event_type == "document.verification_succeeded":
        doc_id = event.get("data", {}).get("document_id")
        app.logger.info(f"Document verified: {doc_id}")
        # Add your business logic here (e.g., notify user, trigger processing)

    return jsonify({"received": True}), 200


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "widget_configured": bool(
            OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET and OCROLUS_WIDGET_UUID
        ),
        "environment": OCROLUS_WIDGET_ENVIRONMENT,
    })


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    print(f"Ocrolus Widget App — http://localhost:{port}")
    print(f"Environment: {OCROLUS_WIDGET_ENVIRONMENT}")
    print(f"Widget UUID configured: {bool(OCROLUS_WIDGET_UUID)}")
    print(f"Credentials configured: {bool(OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET)}")

    app.run(host="0.0.0.0", port=port, debug=debug)
