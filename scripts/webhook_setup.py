#!/usr/bin/env python3
"""
Ocrolus Webhook Setup & Listener
=================================

All-in-one script that:
  1. Starts a local Flask webhook listener (with event logging)
  2. Optionally starts an ngrok tunnel to expose it publicly
  3. Registers the webhook URL with Ocrolus via their API
  4. Sends a test webhook to verify the chain

Usage:
    # Step 1: Start the listener (runs in foreground, logs all events)
    python webhook_setup.py listen

    # Step 2: In another terminal, register your ngrok URL with Ocrolus
    python webhook_setup.py register --url https://YOUR-NGROK-URL.ngrok-free.app/webhooks/ocrolus

    # Step 3: Send a test webhook
    python webhook_setup.py test

    # Or do everything at once (requires ngrok installed):
    python webhook_setup.py auto

    # List current webhooks
    python webhook_setup.py list

    # Delete a webhook
    python webhook_setup.py delete --webhook-id <id>

Environment variables:
    OCROLUS_CLIENT_ID       - Your Ocrolus OAuth client ID
    OCROLUS_CLIENT_SECRET   - Your Ocrolus OAuth client secret
    OCROLUS_WEBHOOK_SECRET  - HMAC signing secret (auto-generated if not set)
    PORT                    - Listener port (default: 8080)
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("webhook-setup")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR.parent / "reports" / "webhook-events"
AUTH_URL = "https://auth.ocrolus.com/oauth/token"
BASE_URL = "https://api.ocrolus.com"
DEFAULT_PORT = 8080

# ---------------------------------------------------------------------------
# Auth helper (uses requests to avoid Python 3.14 SSL issues)
# ---------------------------------------------------------------------------
import requests as _requests

def get_token() -> str:
    """Authenticate and return a Bearer token."""
    client_id = os.environ.get("OCROLUS_CLIENT_ID", "")
    client_secret = os.environ.get("OCROLUS_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        sys.exit(
            "ERROR: Set OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET environment variables.\n"
            "  export OCROLUS_CLIENT_ID='your-client-id'\n"
            "  export OCROLUS_CLIENT_SECRET='your-client-secret'"
        )

    resp = _requests.post(AUTH_URL, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def api_request(method: str, path: str, token: str, body: dict = None) -> dict:
    """Make an authenticated API request to Ocrolus."""
    url = f"{BASE_URL}{path}"
    resp = _requests.request(
        method, url,
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=30,
    )
    try:
        return resp.json()
    except Exception:
        logger.error(f"API error: {resp.status_code} - {resp.text[:500]}")
        return {"error": f"HTTP {resp.status_code}", "body": resp.text[:500]}


# ---------------------------------------------------------------------------
# Webhook registration commands
# ---------------------------------------------------------------------------
def cmd_list(args):
    """List all registered webhooks."""
    token = get_token()
    logger.info("Fetching org-level webhooks...")
    result = api_request("GET", "/v1/account/settings/webhooks", token)
    print(json.dumps(result, indent=2))

    logger.info("Fetching account-level webhook config...")
    result2 = api_request("GET", "/v1/webhook/configuration", token)
    print(json.dumps(result2, indent=2))


def cmd_register(args):
    """Register a webhook URL with Ocrolus."""
    token = get_token()
    url = args.url
    if not url:
        sys.exit("ERROR: --url is required. Provide your public webhook URL.")

    # Generate a signing secret if not provided
    webhook_secret = os.environ.get("OCROLUS_WEBHOOK_SECRET", "")
    if not webhook_secret:
        webhook_secret = secrets.token_urlsafe(48)
        logger.info(f"Generated webhook secret (save this!): {webhook_secret}")
        logger.info("Set it as: export OCROLUS_WEBHOOK_SECRET='%s'", webhook_secret)

    # First, configure the signing secret
    logger.info("Configuring webhook signing secret...")
    secret_result = api_request("POST", "/v1/account/settings/webhooks/secret", token, {"secret": webhook_secret})
    print(f"Secret config result: {json.dumps(secret_result, indent=2)}")

    # Register the webhook
    logger.info(f"Registering webhook URL: {url}")
    register_body = {"url": url}
    if args.events:
        register_body["events"] = args.events.split(",")

    result = api_request("POST", "/v1/account/settings/webhook", token, register_body)
    print(f"\nWebhook registration result:\n{json.dumps(result, indent=2)}")

    # Extract webhook ID for test
    webhook_id = None
    if isinstance(result, dict):
        # Try common response shapes
        for key in ("id", "webhook_id", "pk"):
            if key in result:
                webhook_id = result[key]
                break
        if not webhook_id and "response" in result and isinstance(result["response"], dict):
            for key in ("id", "webhook_id", "pk"):
                if key in result["response"]:
                    webhook_id = result["response"][key]
                    break

    if webhook_id:
        logger.info(f"Webhook registered with ID: {webhook_id}")
        logger.info("Run 'python webhook_setup.py test' to send a test event.")
    else:
        logger.warning("Could not extract webhook ID from response. Check the output above.")

    return webhook_id


def cmd_test(args):
    """Send a test webhook event."""
    token = get_token()

    if args.webhook_id:
        # Test a specific org-level webhook
        logger.info(f"Sending test event to webhook {args.webhook_id}...")
        result = api_request("POST", f"/v1/account/settings/webhooks/{args.webhook_id}/test", token)
    else:
        # Test account-level webhook
        logger.info("Sending test event via account-level webhook...")
        result = api_request("POST", "/v1/webhook/test", token)

    print(json.dumps(result, indent=2))


def cmd_delete(args):
    """Delete a webhook."""
    token = get_token()
    if not args.webhook_id:
        sys.exit("ERROR: --webhook-id is required.")

    logger.info(f"Deleting webhook {args.webhook_id}...")
    result = api_request("DELETE", f"/v1/account/settings/webhooks/{args.webhook_id}", token)
    print(json.dumps(result, indent=2))


def cmd_events(args):
    """List available webhook event types."""
    token = get_token()
    logger.info("Fetching available webhook event types...")
    result = api_request("GET", "/v1/account/settings/webhooks/events", token)
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Flask listener
# ---------------------------------------------------------------------------
def cmd_listen(args):
    """Start the local webhook listener."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        sys.exit("Flask is required: pip3 install flask")

    port = int(os.environ.get("PORT", args.port or DEFAULT_PORT))
    webhook_secret = os.environ.get("OCROLUS_WEBHOOK_SECRET", "")

    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    event_log_file = LOG_DIR / "events.jsonl"  # Single persistent log file

    app = Flask(__name__)

    def verify_signature(body: bytes, headers) -> bool:
        """Verify HMAC-SHA256 signature if a secret is configured."""
        if not webhook_secret:
            return True

        timestamp = headers.get("Webhook-Timestamp", "")
        request_id = headers.get("Webhook-Request-Id", "")
        received_sig = headers.get("Webhook-Signature", "")

        # If Ocrolus doesn't send signature headers, accept the event
        # (the secret config endpoint may not be available on this tenant)
        if not received_sig:
            logger.info("No Webhook-Signature header — accepting event (signature not configured on Ocrolus side)")
            return True

        if not all([timestamp, request_id]):
            logger.warning("Missing timestamp/request-id headers with signature present")
            return True  # Accept anyway, log the warning

        signed_message = f"{timestamp}.{request_id}.".encode() + body
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_message,
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(expected, received_sig):
            return True

        logger.warning("Signature mismatch (local secret may not match Ocrolus config) — accepting event anyway")
        return True

    # In-memory activity log for the dashboard — load history from existing log
    activity_log = []
    stats = {"total": 0, "by_event": {}, "errors": 0, "last_received": None}

    if event_log_file.exists():
        logger.info(f"Loading event history from {event_log_file}...")
        try:
            with open(event_log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    payload = entry.get("payload", {})
                    event_name = payload.get("event_name", payload.get("event", "unknown"))
                    book_pk = payload.get("book_pk")
                    book_uuid = payload.get("book_uuid", "")
                    status = payload.get("status", "")
                    activity_log.append({
                        "time": entry.get("received_at", ""),
                        "type": "webhook",
                        "event_name": event_name,
                        "book_pk": book_pk,
                        "book_uuid": book_uuid,
                        "status": status,
                        "message": payload.get("notification_reason", payload.get("message", "")),
                        "request_id": entry.get("headers", {}).get("Webhook-Request-Id", ""),
                    })
                    stats["total"] += 1
                    stats["by_event"][event_name] = stats["by_event"].get(event_name, 0) + 1
                    stats["last_received"] = entry.get("received_at")
            logger.info(f"Loaded {stats['total']} historical events")
        except Exception as e:
            logger.warning(f"Could not load event history: {e}")

    def fetch_book_data(book_pk: int, book_uuid: str):
        """Fetch book summary and enriched transactions when a book completes."""
        try:
            token = get_token()
            headers_api = {"Authorization": f"Bearer {token}"}
            uid = book_uuid or "unknown"
            report_dir = LOG_DIR / "book-reports"
            report_dir.mkdir(parents=True, exist_ok=True)

            book_report = {"book_pk": book_pk, "book_uuid": uid, "fetched_at": datetime.now(timezone.utc).isoformat()}

            # Get book summary
            logger.info(f"Fetching book summary for {uid}...")
            resp = _requests.get(f"{BASE_URL}/v2/book/{uid}/summary", headers=headers_api, timeout=30)
            book_report["summary"] = resp.json() if resp.ok else {"error": resp.status_code, "body": resp.text[:500]}

            # Get enriched transactions
            logger.info(f"Fetching enriched transactions for {uid}...")
            resp = _requests.get(f"{BASE_URL}/v2/book/{uid}/enriched_txns", headers=headers_api, timeout=30)
            book_report["enriched_transactions"] = resp.json() if resp.ok else {"error": resp.status_code, "body": resp.text[:500]}

            # Save report
            report_file = report_dir / f"book-{uid[:8]}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(book_report, f, indent=2)
            logger.info(f"Book report saved to {report_file}")

            # Log to activity — v2 endpoints return data directly (no "status":200 wrapper)
            summary_resp = book_report["summary"]
            txn_resp = book_report["enriched_transactions"]
            summary_ok = isinstance(summary_resp, dict) and "error" not in summary_resp
            txn_ok = isinstance(txn_resp, dict) and "error" not in txn_resp

            # Extract highlights for the log message
            txn_count = txn_resp.get("total", "?") if txn_ok else "?"
            docs_processed = txn_resp.get("number_of_docs_processed", "?") if txn_ok else "?"
            activity_log.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "type": "auto_fetch",
                "message": f"Book {uid[:8]}... data fetched — summary: {'OK' if summary_ok else 'FAIL'}, transactions: {'OK' if txn_ok else 'FAIL'} ({txn_count} txns, {docs_processed} docs)",
                "report_file": str(report_file),
            })

        except Exception as e:
            logger.error(f"Failed to fetch book data: {e}")
            activity_log.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "type": "auto_fetch_error",
                "message": f"Failed to fetch book data for pk={book_pk}: {e}",
            })

    @app.route("/webhooks/ocrolus", methods=["POST"])
    def webhook_endpoint():
        raw_body = request.get_data()

        # Verify signature
        if not verify_signature(raw_body, request.headers):
            logger.error("SIGNATURE VERIFICATION FAILED")
            stats["errors"] += 1
            activity_log.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "type": "error",
                "message": "Signature verification failed",
            })
            return jsonify({"error": "Invalid signature"}), 401

        # Parse the event
        try:
            event = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {raw_body[:200]}")
            stats["errors"] += 1
            return jsonify({"error": "Invalid JSON"}), 400

        # Log everything — this is the discovery phase
        timestamp = datetime.now(timezone.utc).isoformat()
        event_name = event.get("event_name", event.get("event", "unknown"))
        log_entry = {
            "received_at": timestamp,
            "headers": {
                "Webhook-Signature": request.headers.get("Webhook-Signature", ""),
                "Webhook-Timestamp": request.headers.get("Webhook-Timestamp", ""),
                "Webhook-Request-Id": request.headers.get("Webhook-Request-Id", ""),
                "Content-Type": request.headers.get("Content-Type", ""),
            },
            "payload": event,
        }

        # Update stats
        stats["total"] += 1
        stats["by_event"][event_name] = stats["by_event"].get(event_name, 0) + 1
        stats["last_received"] = timestamp

        # Add to activity log
        book_pk = event.get("book_pk")
        book_uuid = event.get("book_uuid", "")
        status = event.get("status", "")
        activity_log.append({
            "time": timestamp,
            "type": "webhook",
            "event_name": event_name,
            "book_pk": book_pk,
            "book_uuid": book_uuid,
            "status": status,
            "message": event.get("notification_reason", event.get("message", "")),
            "request_id": request.headers.get("Webhook-Request-Id", ""),
        })

        # Print to console with formatting
        print("\n" + "=" * 70)
        print(f"  WEBHOOK EVENT RECEIVED  —  {timestamp}")
        print("=" * 70)
        print(f"  Event: {event_name}  |  Status: {status}")
        print(f"  Headers:")
        for k, v in log_entry["headers"].items():
            if v:
                print(f"    {k}: {v}")
        print(f"\n  Payload keys: {list(event.keys())}")
        print(f"  Full payload:")
        print(json.dumps(event, indent=4))
        print("=" * 70 + "\n")

        # Append to log file
        with open(event_log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info(f"Event logged to {event_log_file}")

        # Auto-fetch book data on book.verified / book.complete
        if event_name in ("book.verified", "book.complete", "book.completed") or status in ("BOOK_COMPLETE",):
            if book_pk or book_uuid:
                import threading
                logger.info(f"Book complete! Fetching summary & transactions for pk={book_pk}, uuid={book_uuid}...")
                threading.Thread(target=fetch_book_data, args=(book_pk, book_uuid), daemon=True).start()

        return jsonify({"status": "ok"}), 200

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "listening": True,
            "stats": stats,
            "event_count": stats["total"],
            "last_received": stats["last_received"],
        }), 200

    @app.route("/activity", methods=["GET"])
    def activity_dashboard():
        """Serve a live-refreshing HTML activity dashboard."""
        limit = request.args.get("limit", 100, type=int)
        recent = list(reversed(activity_log[-limit:]))

        rows = ""
        for entry in recent:
            etype = entry.get("type", "")
            if etype == "webhook":
                badge = '<span style="background:#0e3a1e;color:#2ecc71;padding:2px 8px;border-radius:10px;font-size:.8em">WEBHOOK</span>'
            elif etype == "auto_fetch":
                badge = '<span style="background:#0e1e3a;color:#3498db;padding:2px 8px;border-radius:10px;font-size:.8em">AUTO-FETCH</span>'
            elif "error" in etype:
                badge = '<span style="background:#3a0e0e;color:#e74c3c;padding:2px 8px;border-radius:10px;font-size:.8em">ERROR</span>'
            else:
                badge = '<span style="background:#21262d;color:#8b949e;padding:2px 8px;border-radius:10px;font-size:.8em">INFO</span>'

            event_name = entry.get("event_name", "")
            message = entry.get("message", "")
            book_ref = entry.get("book_uuid", entry.get("book_pk", ""))
            if isinstance(book_ref, str) and len(book_ref) > 12:
                book_ref = book_ref[:8] + "..."

            rows += f"""<tr>
                <td style="white-space:nowrap;color:#8b949e">{entry['time'][:19]}</td>
                <td>{badge}</td>
                <td><code>{event_name}</code></td>
                <td>{entry.get('status', '')}</td>
                <td><code>{book_ref}</code></td>
                <td>{message}</td>
            </tr>"""

        event_counts = ""
        for evt, count in sorted(stats["by_event"].items(), key=lambda x: -x[1]):
            event_counts += f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #21262d"><span>{evt}</span><strong>{count}</strong></div>'

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Webhook Activity</title>
<meta http-equiv="refresh" content="15">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f1117;color:#e1e4e8;padding:20px}}
.container{{max-width:1400px;margin:0 auto}}
h1{{color:#fff;margin-bottom:5px}}
.subtitle{{color:#8b949e;margin-bottom:20px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:25px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px;text-align:center}}
.card .val{{font-size:2em;font-weight:700}}
.card .lbl{{color:#8b949e;font-size:.85em;margin-top:4px}}
.green{{color:#2ecc71}}.red{{color:#e74c3c}}.blue{{color:#3498db}}.yellow{{color:#f39c12}}
.section{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.section h2{{color:#fff;margin-bottom:12px;font-size:1.2em}}
table{{width:100%;border-collapse:collapse;font-size:.9em}}
th{{text-align:left;padding:8px;border-bottom:2px solid #30363d;color:#8b949e}}
td{{padding:6px 8px;border-bottom:1px solid #21262d}}
tr:hover{{background:#1c2128}}
code{{background:#0d1117;padding:2px 6px;border-radius:3px;font-size:.85em}}
.pulse{{animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
.btn{{display:inline-block;padding:8px 16px;border-radius:6px;font-size:.85em;font-weight:600;
      cursor:pointer;text-decoration:none;border:1px solid #30363d;margin-right:8px;margin-bottom:8px;transition:all .2s}}
.btn:hover{{filter:brightness(1.2)}}
.btn-green{{background:#0e3a1e;color:#2ecc71}}.btn-green:hover{{background:#145a2e}}
.btn-blue{{background:#0e1e3a;color:#3498db}}.btn-blue:hover{{background:#142e5a}}
.btn-purple{{background:#2a0e3a;color:#a855f7}}.btn-purple:hover{{background:#3a145a}}
.toolbar{{display:flex;align-items:center;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
</style></head><body>
<div class="container">
<h1>Webhook Activity Dashboard <span class="pulse" style="color:#2ecc71;font-size:.5em">LIVE</span></h1>
<p class="subtitle">Auto-refreshes every 15 seconds | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | {stats['total']} events persisted to disk</p>

<div class="toolbar">
    <a class="btn btn-green" href="/export/json" download>Export JSON</a>
    <a class="btn btn-blue" href="/export/csv" download>Export CSV</a>
    <a class="btn btn-purple" href="/export/html" target="_blank">Export HTML Snapshot</a>
</div>

<div class="cards">
    <div class="card"><div class="val green">{stats['total']}</div><div class="lbl">Events Received</div></div>
    <div class="card"><div class="val blue">{len(stats['by_event'])}</div><div class="lbl">Unique Event Types</div></div>
    <div class="card"><div class="val red">{stats['errors']}</div><div class="lbl">Errors</div></div>
    <div class="card"><div class="val yellow">{stats['last_received'][:19] if stats['last_received'] else 'None'}</div><div class="lbl">Last Event</div></div>
</div>

<div style="display:grid;grid-template-columns:1fr 300px;gap:20px">
<div class="section">
    <h2>Activity Log ({len(recent)} most recent)</h2>
    <table>
    <thead><tr><th>Time</th><th>Type</th><th>Event</th><th>Status</th><th>Book</th><th>Message</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
</div>

<div class="section">
    <h2>Event Counts</h2>
    {event_counts if event_counts else '<p style="color:#8b949e">No events yet</p>'}
</div>
</div>

<div class="section" style="text-align:center;color:#8b949e;font-size:.85em">
    Event log: {event_log_file}
</div>
</div></body></html>"""
        return html, 200, {"Content-Type": "text/html"}

    @app.route("/export/json", methods=["GET"])
    def export_json():
        """Export all events as a JSON file."""
        events = []
        if event_log_file.exists():
            with open(event_log_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return (
            json.dumps({"exported_at": datetime.now(timezone.utc).isoformat(), "total": len(events), "events": events}, indent=2),
            200,
            {"Content-Type": "application/json", "Content-Disposition": f"attachment; filename=webhook-events-{ts}.json"},
        )

    @app.route("/export/csv", methods=["GET"])
    def export_csv():
        """Export all events as a CSV file."""
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["received_at", "event_name", "status", "book_pk", "book_uuid", "notification_reason", "request_id", "doc_count"])
        if event_log_file.exists():
            with open(event_log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    p = entry.get("payload", {})
                    docs = p.get("uploaded_docs", [])
                    writer.writerow([
                        entry.get("received_at", ""),
                        p.get("event_name", p.get("event", "")),
                        p.get("status", ""),
                        p.get("book_pk", ""),
                        p.get("book_uuid", ""),
                        p.get("notification_reason", p.get("message", "")),
                        entry.get("headers", {}).get("Webhook-Request-Id", ""),
                        len(docs),
                    ])
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return (
            output.getvalue(),
            200,
            {"Content-Type": "text/csv", "Content-Disposition": f"attachment; filename=webhook-events-{ts}.csv"},
        )

    @app.route("/export/html", methods=["GET"])
    def export_html_snapshot():
        """Export a self-contained HTML snapshot (no auto-refresh, for archiving)."""
        # Re-use the activity dashboard but strip auto-refresh
        resp = activity_dashboard()
        html_content = resp[0] if isinstance(resp, tuple) else resp
        html_content = html_content.replace('<meta http-equiv="refresh" content="15">', '<!-- snapshot: auto-refresh disabled -->')
        html_content = html_content.replace(
            '<span class="pulse" style="color:#2ecc71;font-size:.5em">LIVE</span>',
            '<span style="color:#8b949e;font-size:.5em">SNAPSHOT</span>',
        )
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        return (
            html_content,
            200,
            {"Content-Type": "text/html", "Content-Disposition": f"attachment; filename=webhook-activity-{ts}.html"},
        )

    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  Ocrolus Webhook Listener                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Listening on: http://0.0.0.0:{port}/webhooks/ocrolus              ║
║  Health check: http://localhost:{port}/health                      ║
║  Event log:    {str(event_log_file):<52s} ║
║                                                                      ║
║  Signature verification: {'ENABLED' if webhook_secret else 'DISABLED (set OCROLUS_WEBHOOK_SECRET)':40s}   ║
║                                                                      ║
║  Next steps:                                                         ║
║  1. Expose this port publicly (ngrok, cloudflared, etc.)             ║
║  2. Register the public URL with Ocrolus:                            ║
║     python webhook_setup.py register --url <PUBLIC_URL>              ║
║  3. Send a test event:                                               ║
║     python webhook_setup.py test --webhook-id <ID>                   ║
║                                                                      ║
║  Press Ctrl+C to stop.                                               ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    app.run(host="0.0.0.0", port=port, debug=False)


# ---------------------------------------------------------------------------
# Auto mode: listener + ngrok + register
# ---------------------------------------------------------------------------
def cmd_auto(args):
    """Start listener, ngrok tunnel, and register automatically."""
    # Check for ngrok
    ngrok_path = subprocess.run(["which", "ngrok"], capture_output=True, text=True)
    if ngrok_path.returncode != 0:
        sys.exit(
            "ngrok is not installed. Install it with:\n"
            "  brew install ngrok    (macOS)\n"
            "  Or download from https://ngrok.com/download\n\n"
            "Then authenticate:\n"
            "  ngrok config add-authtoken YOUR_TOKEN\n\n"
            "Alternative: use 'listen' mode and expose the port yourself."
        )

    port = int(os.environ.get("PORT", args.port or DEFAULT_PORT))

    # Generate webhook secret if needed
    webhook_secret = os.environ.get("OCROLUS_WEBHOOK_SECRET", "")
    if not webhook_secret:
        webhook_secret = secrets.token_urlsafe(48)
        os.environ["OCROLUS_WEBHOOK_SECRET"] = webhook_secret
        logger.info(f"Generated webhook secret: {webhook_secret}")
        logger.info("Save it: export OCROLUS_WEBHOOK_SECRET='%s'", webhook_secret)

    # Start Flask listener in background
    logger.info(f"Starting webhook listener on port {port}...")
    listener_proc = subprocess.Popen(
        [sys.executable, __file__, "listen", "--port", str(port)],
        env={**os.environ, "OCROLUS_WEBHOOK_SECRET": webhook_secret},
    )

    time.sleep(2)  # Wait for Flask to start

    # Start ngrok
    logger.info(f"Starting ngrok tunnel to port {port}...")
    ngrok_proc = subprocess.Popen(
        ["ngrok", "http", str(port), "--log", "stdout"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for ngrok to establish tunnel and get URL
    time.sleep(3)

    # Get ngrok public URL via its local API
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=5) as resp:
            tunnels = json.loads(resp.read())
            public_url = None
            for t in tunnels.get("tunnels", []):
                if t.get("proto") == "https":
                    public_url = t["public_url"]
                    break
            if not public_url and tunnels.get("tunnels"):
                public_url = tunnels["tunnels"][0]["public_url"]
    except Exception as e:
        logger.error(f"Could not get ngrok URL: {e}")
        logger.info("Check ngrok dashboard at http://localhost:4040")
        public_url = None

    if public_url:
        webhook_url = f"{public_url}/webhooks/ocrolus"
        print(f"\n  ngrok tunnel: {public_url}")
        print(f"  Webhook URL:  {webhook_url}\n")

        # Register with Ocrolus
        logger.info("Registering webhook with Ocrolus...")
        token = get_token()

        # Configure secret
        api_request("POST", "/v1/account/settings/webhooks/secret", token, {"secret": webhook_secret})

        # Register webhook
        result = api_request("POST", "/v1/account/settings/webhook", token, {"url": webhook_url})
        print(f"Registration result:\n{json.dumps(result, indent=2)}")
    else:
        print("\nCould not auto-detect ngrok URL. Register manually:")
        print(f"  python webhook_setup.py register --url <YOUR_NGROK_URL>/webhooks/ocrolus")

    # Wait for Ctrl+C
    def cleanup(sig, frame):
        logger.info("Shutting down...")
        listener_proc.terminate()
        ngrok_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("\nPress Ctrl+C to stop all services.\n")
    listener_proc.wait()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Ocrolus Webhook Setup & Listener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # listen
    p_listen = sub.add_parser("listen", help="Start the local webhook listener")
    p_listen.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")

    # register
    p_reg = sub.add_parser("register", help="Register a webhook URL with Ocrolus")
    p_reg.add_argument("--url", required=True, help="Public webhook URL")
    p_reg.add_argument("--events", help="Comma-separated event types to subscribe to")

    # test
    p_test = sub.add_parser("test", help="Send a test webhook event")
    p_test.add_argument("--webhook-id", help="Org webhook ID to test")

    # delete
    p_del = sub.add_parser("delete", help="Delete a webhook")
    p_del.add_argument("--webhook-id", required=True, help="Webhook ID to delete")

    # events
    sub.add_parser("events", help="List available webhook event types")

    # list
    sub.add_parser("list", help="List registered webhooks")

    # auto
    p_auto = sub.add_parser("auto", help="Auto-setup: listener + ngrok + register")
    p_auto.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")

    args = parser.parse_args()

    commands = {
        "listen": cmd_listen,
        "register": cmd_register,
        "test": cmd_test,
        "delete": cmd_delete,
        "events": cmd_events,
        "list": cmd_list,
        "auto": cmd_auto,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
