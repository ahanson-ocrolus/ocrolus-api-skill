"""
Ocrolus Widget Sample Application
==================================

Flask app demonstrating the Ocrolus embeddable widget.
Handles server-side token exchange and serves the client-side widget container.

** NOT FULLY TURNKEY **
This app handles auth and page structure, but you MUST manually insert
the widget <script> tag from your Ocrolus Dashboard. The widget script URL
is unique to your account and cannot be programmatically retrieved.
See "MANUAL STEP REQUIRED" in the HTML template below.

Requirements:
    pip install flask requests

Setup:
    1. Create a widget in Ocrolus Dashboard > Account & Settings > Embedded Widget
    2. Save the generated client_id and client_secret
    3. Copy the generated <script> tag from the Dashboard
    4. Paste it into the HTML template below where marked "MANUAL STEP REQUIRED"
    5. Set environment variables:
       export OCROLUS_WIDGET_CLIENT_ID="your_widget_client_id"
       export OCROLUS_WIDGET_CLIENT_SECRET="your_widget_client_secret"
    6. Run: python widget_app.py
    7. Open: http://localhost:5000

Notes:
    - Widget auth uses a SEPARATE endpoint from the main API:
      https://jwe-issuer.ocrolus.net/token (NOT https://auth.ocrolus.com/oauth/token)
    - The widget client_id/secret are DIFFERENT from your API client_id/secret
    - external_id is YOUR user identifier -- use it to track which user uploaded docs
"""

import os
import sys

try:
    from flask import Flask, request, jsonify, render_template_string
    import requests
except ImportError:
    print("Required: pip install flask requests")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

WIDGET_AUTH_URL = "https://jwe-issuer.ocrolus.net/token"
WIDGET_CLIENT_ID = os.environ.get("OCROLUS_WIDGET_CLIENT_ID", "")
WIDGET_CLIENT_SECRET = os.environ.get("OCROLUS_WIDGET_CLIENT_SECRET", "")

if not WIDGET_CLIENT_ID or not WIDGET_CLIENT_SECRET:
    print("WARNING: Set OCROLUS_WIDGET_CLIENT_ID and OCROLUS_WIDGET_CLIENT_SECRET")


# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)

# HTML template with embedded widget
WIDGET_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Upload - Ocrolus Widget</title>
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
        .footer {
            text-align: center;
            padding: 24px;
            font-size: 12px;
            color: #999;
        }
    </style>

    <script>
        // =====================================================================
        // REQUIRED: Global function that the Ocrolus widget calls to get a token
        // This is the CLIENT-SIDE piece -- it calls YOUR server endpoint
        // =====================================================================
        async function getAuthToken() {
            try {
                const response = await fetch('/api/ocrolus-token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        // Pass your application's user ID for tracking
                        user_id: '{{ user_id }}'
                    })
                });

                if (!response.ok) {
                    updateStatus('Token request failed', true);
                    throw new Error('Token request failed');
                }

                const data = await response.json();
                updateStatus('Connected');
                return data.token;
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
    </script>

    <!-- ================================================================== -->
    <!-- MANUAL STEP REQUIRED: Insert your widget script tag here.         -->
    <!-- Get it from Ocrolus Dashboard > Account & Settings > Embedded     -->
    <!-- Widget. It will look something like:                              -->
    <!--                                                                   -->
    <!-- <script src="https://widget.ocrolus.com/v1/widget.js?id=..."></script> -->
    <!--                                                                   -->
    <!-- The widget will NOT render without this script. This URL is       -->
    <!-- unique to your account and cannot be generated programmatically.  -->
    <!-- ================================================================== -->

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

        <!-- Widget renders inside this div -->
        <div id="ocrolus-widget-frame"></div>
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
    # In production, get user_id from your session/auth system
    user_id = request.args.get("user_id", "demo-user-001")
    return render_template_string(WIDGET_PAGE, user_id=user_id)


@app.route("/api/ocrolus-token", methods=["POST"])
def get_ocrolus_token():
    """
    Server-side token exchange endpoint.

    The widget calls getAuthToken() on the client side, which calls this
    endpoint. This endpoint exchanges your widget credentials for a token.

    IMPORTANT: Never expose WIDGET_CLIENT_SECRET to the client side.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "unknown")

    if not WIDGET_CLIENT_ID or not WIDGET_CLIENT_SECRET:
        return jsonify({"error": "Widget credentials not configured"}), 500

    try:
        resp = requests.post(
            WIDGET_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": WIDGET_CLIENT_ID,
                "client_secret": WIDGET_CLIENT_SECRET,
                "external_id": user_id,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()
        return jsonify({"token": token_data["access_token"]})

    except requests.RequestException as e:
        app.logger.error(f"Token exchange failed: {e}")
        return jsonify({"error": "Failed to obtain token"}), 502


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "widget_configured": bool(WIDGET_CLIENT_ID and WIDGET_CLIENT_SECRET),
    })


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    print(f"Starting Ocrolus Widget App on http://localhost:{port}")
    print(f"Widget auth URL: {WIDGET_AUTH_URL}")
    print(f"Widget client configured: {bool(WIDGET_CLIENT_ID)}")

    app.run(host="0.0.0.0", port=port, debug=debug)
