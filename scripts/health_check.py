#!/usr/bin/env python3
"""
Ocrolus API Health Check
========================

Comprehensive health check for every Ocrolus API endpoint listed on the
public reference at docs.ocrolus.com/reference. Generates console, JSON,
and HTML dashboard reports.

Usage:
    export OCROLUS_CLIENT_ID="your_id"
    export OCROLUS_CLIENT_SECRET="your_secret"

    python scripts/health_check.py
    python scripts/health_check.py --output-dir ./reports
    python scripts/health_check.py --webhooks --write-paths
    python scripts/health_check.py --repeat 5 --interval 120
    python scripts/health_check.py --html-only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import requests

BASE_URL = "https://api.ocrolus.com"
AUTH_URL = "https://auth.ocrolus.com/oauth/token"

# ---------------------------------------------------------------------------
# Endpoint definitions: (name, method, path, category, params_or_None)
# ---------------------------------------------------------------------------
# Reusable placeholders so the route is exercised even without a real book/doc.
_BOOK_UUID = "00000000-0000-0000-0000-000000000000"
_DOC_UUID = "00000000-0000-0000-0000-000000000000"
_MIXED_UUID = "00000000-0000-0000-0000-000000000000"
_TAG_UUID = "00000000-0000-0000-0000-000000000000"
_WEBHOOK_UUID = "00000000-0000-0000-0000-000000000000"
_PAYSTUB_UUID = "00000000-0000-0000-0000-000000000000"
_FORM_UUID = "00000000-0000-0000-0000-000000000000"
_VIS_UUID = "00000000-0000-0000-0000-000000000000"
_JOB_ID = "00000000-0000-0000-0000-000000000000"
_BUSINESS_ID = "1"

# Endpoint inventory aligned to docs.ocrolus.com/reference (see DOCS_ALIGNMENT.md).
ENDPOINTS = [
    # Authentication
    ("Grant Token", "POST", AUTH_URL, "Authentication", None),

    # Book Commands
    ("Create Book", "POST", "/v1/book/add", "Book Commands", None),
    ("Update Book", "POST", "/v1/book/update", "Book Commands", None),
    ("Delete Book", "POST", "/v1/book/remove", "Book Commands", None),

    # Book Queries
    ("Book Information", "GET", "/v1/book/info", "Book Queries", {"pk": "1"}),
    ("Book Status", "GET", "/v1/book/status", "Book Queries", {"pk": "1"}),
    ("Book List", "GET", "/v1/books", "Book Queries", None),
    ("Loan from Book", "GET", f"/v2/los-connect/book/{_BOOK_UUID}/loans", "Book Queries", None),
    ("Book from Loan", "GET", "/v2/los-connect/encompass/book", "Book Queries", {"loan_id": "none"}),

    # File Uploads
    ("Upload PDF", "POST", "/v1/book/upload", "File Uploads", None),
    ("Upload Mixed PDF", "POST", "/v1/book/upload/mixed", "File Uploads", None),
    ("Upload Image", "POST", "/v1/book/upload/image", "File Uploads", None),
    ("Finalize Image Group", "POST", "/v1/book/upload/image/done", "File Uploads", None),
    ("Upload Aggregator JSON", "POST", "/v1/book/upload/json", "File Uploads", None),
    ("Upload Pay Stub", "POST", f"/v2/book/{_BOOK_UUID}/document/paystub", "File Uploads", None),
    ("Import Plaid Asset", "POST", "/v1/book/import/plaid/asset", "File Uploads", None),

    # File Commands
    ("Cancel Document", "POST", "/v1/document/cancel", "File Commands", None),
    ("Delete Document", "POST", "/v1/document/remove", "File Commands", None),
    ("Download Document", "GET", "/v2/document/download", "File Commands", {"doc_uuid": _DOC_UUID}),
    ("Upgrade Document", "POST", "/v1/document/upgrade", "File Commands", None),
    ("Upgrade Mixed Document", "POST", "/v1/document/mixed/upgrade", "File Commands", None),

    # File Queries
    ("Mixed Document Status", "GET", "/v1/document/mixed/status", "File Queries", {"mixed_doc_uuid": _MIXED_UUID}),

    # Classify
    ("Book Classification Summary", "GET", f"/v2/book/{_BOOK_UUID}/classification-summary", "Classify", None),
    ("Mixed Doc Classification Summary", "GET", f"/v2/mixed-document/{_MIXED_UUID}/classification-summary", "Classify", None),
    ("Grouped Mixed Doc Summary", "GET", f"/v2/index/mixed-doc/{_MIXED_UUID}/summary", "Classify", None),

    # Capture
    ("Book Form Data", "GET", "/v1/book/forms", "Capture", {"pk": "1"}),
    ("Doc Form Data", "GET", "/v1/document/forms/fields", "Capture", {"doc_uuid": _DOC_UUID}),
    ("Form Data", "GET", "/v1/form", "Capture", {"uuid": _FORM_UUID}),
    ("Book Pay Stub Data", "GET", f"/v2/book/{_BOOK_UUID}/paystub", "Capture", None),
    ("Doc Pay Stub Data", "GET", f"/v2/document/{_DOC_UUID}/paystub", "Capture", None),
    ("Pay Stub Data", "GET", f"/v2/paystub/{_PAYSTUB_UUID}", "Capture", None),
    ("Transactions", "GET", "/v1/transaction", "Capture", {"book_pk": "1"}),

    # Detect
    ("Book Fraud Signals", "GET", f"/v2/detect/book/{_BOOK_UUID}/signals", "Detect", None),
    ("Doc Fraud Signals", "GET", f"/v2/detect/uploaded_doc/{_DOC_UUID}/signals", "Detect", None),
    ("Signal Visualization", "GET", f"/v2/detect/visualization/{_VIS_UUID}", "Detect", None),
    ("Suspicious Activity (Legacy)", "GET", f"/v1/book/{_BOOK_UUID}/suspicious-activity-flags", "Detect", None),

    # Cash Flow Analytics
    ("Book Summary", "GET", f"/v2/book/{_BOOK_UUID}/summary", "Cash Flow Analytics", None),
    ("Cash Flow Features", "GET", f"/v2/book/{_BOOK_UUID}/cash_flow_features", "Cash Flow Analytics", None),
    ("Enriched Transactions", "GET", f"/v2/book/{_BOOK_UUID}/enriched_txns", "Cash Flow Analytics", None),
    ("Risk Score", "GET", f"/v2/book/{_BOOK_UUID}/cash_flow_risk_score", "Cash Flow Analytics", None),
    ("Analytics Excel", "GET", f"/v2/book/{_BOOK_UUID}/lender_analytics/xlsx", "Cash Flow Analytics", None),
    ("BSIC (JSON)", "GET", f"/v2/book/{_BOOK_UUID}/income/bank-statement-v2", "Cash Flow Analytics", None),
    ("BSIC (Excel)", "GET", f"/v2/book/{_BOOK_UUID}/income/bank-statement-v2/xlsx", "Cash Flow Analytics", None),

    # Income
    ("Income Calculations", "GET", f"/v2/book/{_BOOK_UUID}/income-calculations", "Income", None),
    ("Income Summary", "GET", f"/v2/book/{_BOOK_UUID}/income/summary", "Income", None),
    ("Configure Income Entity", "POST", f"/v2/book/{_BOOK_UUID}/income/entity_config", "Income", None),
    ("Save Income Guideline", "PUT", f"/v2/book/{_BOOK_UUID}/income-guideline", "Income", None),
    ("Self-Employed Income (FM)", "POST", f"/v2/book/{_BOOK_UUID}/income/self-employed/calculate", "Income", None),

    # Business history
    ("Business Identifier", "GET", f"/v2/book/{_BOOK_UUID}/business", "Business History", None),
    ("Business Overview", "GET", f"/v1/businesses/{_BUSINESS_ID}", "Business History", None),
    ("Business Summary", "GET", f"/v1/businesses/{_BUSINESS_ID}/summary", "Business History", None),
    ("Business Transactions", "GET", f"/v1/businesses/{_BUSINESS_ID}/transactions", "Business History", None),

    # Tag Management
    ("Create Tag", "POST", "/v2/analytics/tags", "Tag Management", None),
    ("List Tags", "GET", "/v2/analytics/tags", "Tag Management", None),
    ("Get Tag", "GET", f"/v2/analytics/tags/{_TAG_UUID}", "Tag Management", None),
    ("Modify Tag", "PUT", f"/v2/analytics/tags/{_TAG_UUID}", "Tag Management", None),
    ("Delete Tag", "DELETE", f"/v2/analytics/tags/{_TAG_UUID}", "Tag Management", None),
    ("Revenue Deduction Tags", "GET", "/v2/analytics/revenue-deduction-tags", "Tag Management", None),
    ("Update Revenue Deduction Tags", "PUT", "/v2/analytics/revenue-deduction-tags", "Tag Management", None),
    ("Override Transaction Tag", "PUT", f"/v2/analytics/book/{_BOOK_UUID}/transactions", "Tag Management", None),

    # Encore / Book Copy
    ("Create Copy Jobs", "POST", "/v1/book/copy-jobs", "Encore", None),
    ("List Copy Jobs", "GET", "/v1/book/copy-jobs", "Encore", None),
    ("Accept Copy Job", "POST", f"/v1/book/copy-jobs/{_JOB_ID}/accept", "Encore", None),
    ("Reject Copy Job", "POST", f"/v1/book/copy-jobs/{_JOB_ID}/reject", "Encore", None),
    ("Run Kick-Outs", "POST", "/v1/book/copy-jobs/run-kickouts", "Encore", None),
    ("Book Copy Settings", "GET", "/v1/settings/book-copy", "Encore", None),

    # Webhooks - Org Level
    ("Add Webhook", "POST", "/v1/account/settings/webhook", "Org Level Webhooks", None),
    ("List Webhooks", "GET", "/v1/account/settings/webhooks", "Org Level Webhooks", None),
    ("Retrieve Webhook", "GET", f"/v1/account/settings/webhook/{_WEBHOOK_UUID}", "Org Level Webhooks", None),
    ("Update Webhook", "POST", f"/v1/account/settings/webhook/{_WEBHOOK_UUID}/update", "Org Level Webhooks", None),
    ("Delete Webhook", "DELETE", f"/v1/account/settings/webhook/{_WEBHOOK_UUID}/delete", "Org Level Webhooks", None),
    ("List Webhook Events", "GET", f"/v1/account/settings/webhook/{_WEBHOOK_UUID}/events", "Org Level Webhooks", None),
    ("Test Webhook", "POST", f"/v1/account/settings/webhook/{_WEBHOOK_UUID}/test", "Org Level Webhooks", None),
    ("Rotate Webhook Secret", "POST", f"/v1/account/settings/webhook/{_WEBHOOK_UUID}/rotate-secret", "Org Level Webhooks", None),

    # Webhooks - Account Level (legacy)
    ("Configure Webhook (legacy)", "POST", "/v1/account/settings/update/webhook_endpoint", "Account Level Webhooks", None),
    ("Webhook Configuration (legacy)", "GET", "/v1/account/settings/webhook_details", "Account Level Webhooks", None),
    ("Test Webhook (legacy)", "GET", "/v1/account/settings/test_webhook_endpoint", "Account Level Webhooks", None),
    ("Rotate Secret (legacy)", "POST", "/v1/account/settings/webhook/rotate-secret", "Account Level Webhooks", None),
]


# ---------------------------------------------------------------------------
# Webhook operational validation
# ---------------------------------------------------------------------------

def validate_webhooks(token: str) -> list:
    """Validate that registered webhooks are operational."""
    results = []
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List registered webhooks
    try:
        resp = requests.get(f"{BASE_URL}/v1/account/settings/webhooks", headers=headers, timeout=15)
        data = resp.json()
        webhooks = data.get("response", {}).get("webhooks", []) if isinstance(data.get("response"), dict) else []
    except Exception as e:
        results.append({
            "name": "List Webhooks", "category": "Webhook Validation",
            "status": "ERROR", "message": str(e), "operational": False,
        })
        return results

    if not webhooks:
        results.append({
            "name": "Webhook Registration", "category": "Webhook Validation",
            "status": "NONE", "message": "No webhooks registered", "operational": False,
        })
        return results

    for wh in webhooks:
        wh_uuid = wh.get("uuid", "unknown")
        wh_url = wh.get("url", "")
        wh_active = wh.get("is_active", False)
        short_uuid = wh_uuid[:8] + "..."

        # Check active status
        results.append({
            "name": f"Webhook {short_uuid} Active",
            "category": "Webhook Validation",
            "status": "PASS" if wh_active else "FAIL",
            "message": f"URL: {wh_url}",
            "operational": wh_active,
        })

        # 2. Check if the webhook URL is reachable (health endpoint)
        if wh_url:
            health_url = wh_url.rsplit("/webhooks/ocrolus", 1)[0] + "/health"
            try:
                resp = requests.get(health_url, timeout=10)
                listener_ok = resp.ok
                try:
                    health_data = resp.json()
                    event_count = health_data.get("event_count", 0)
                    last_received = health_data.get("last_received")
                    msg = f"Listener OK — {event_count} events received"
                    if last_received:
                        msg += f", last: {last_received[:19]}"
                except Exception:
                    msg = f"Listener responded {resp.status_code}"
                    event_count = None
                    last_received = None
            except requests.Timeout:
                listener_ok = False
                msg = "Listener timeout (10s)"
            except requests.ConnectionError:
                listener_ok = False
                msg = "Listener unreachable (connection refused)"
            except Exception as e:
                listener_ok = False
                msg = f"Listener error: {str(e)[:100]}"

            results.append({
                "name": f"Webhook {short_uuid} Listener",
                "category": "Webhook Validation",
                "status": "PASS" if listener_ok else "FAIL",
                "message": msg,
                "operational": listener_ok,
            })

        # 3. Send a test webhook via Ocrolus API
        try:
            resp = requests.post(
                f"{BASE_URL}/v1/account/settings/webhook/{wh_uuid}/test",
                headers={**headers, "Content-Type": "application/json"},
                json={}, timeout=15,
            )
            test_ok = resp.ok or resp.status_code in (200, 202)
            test_data = resp.json() if resp.ok else {}
            test_status = test_data.get("status", resp.status_code)
            msg = f"Test event sent (status: {test_status})"
        except Exception as e:
            test_ok = False
            msg = f"Test send failed: {str(e)[:100]}"

        results.append({
            "name": f"Webhook {short_uuid} Test Event",
            "category": "Webhook Validation",
            "status": "PASS" if test_ok else "WARN",
            "message": msg,
            "operational": test_ok,
        })

    return results


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------

def get_token(client_id: str, client_secret: str) -> Optional[str]:
    """Obtain OAuth token. Returns None on failure."""
    try:
        resp = requests.post(AUTH_URL, data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }, timeout=15)
        if resp.ok:
            return resp.json()["access_token"]
        return None
    except Exception:
        return None


def probe_endpoint(token: str, method: str, path: str, params: Optional[dict] = None) -> dict:
    """Probe a single endpoint, return result dict with timing."""
    # Auth endpoint is a special case (full URL)
    if path.startswith("https://"):
        url = path
    else:
        url = f"{BASE_URL}{path}"

    headers = {"Authorization": f"Bearer {token}"}
    if method.upper() != "GET":
        headers["Content-Type"] = "application/json"

    start = time.time()
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=15)
        else:
            resp = requests.request(method.upper(), url, headers=headers, json={}, timeout=15)
        elapsed_ms = round((time.time() - start) * 1000)

        # Ocrolus often returns HTTP 200 with an error envelope. Distinguish a
        # real "route does not exist" (HTTP 404, or 200 envelope with the literal
        # "Resource not found" message) from "route exists but our probe was rejected".
        envelope_msg = ""
        try:
            body = resp.json()
            if isinstance(body, dict):
                envelope_msg = body.get("message") or ""
        except Exception:
            pass

        looks_like_missing_route = (
            resp.status_code == 404
            or "Resource not found" in envelope_msg
        )
        route_exists = not looks_like_missing_route
        # 400/401/403/405/422 on write endpoints means the route exists
        is_reachable = route_exists

        return {
            "status_code": resp.status_code,
            "response_time_ms": elapsed_ms,
            "exists": route_exists,
            "success": resp.ok and "Resource not found" not in envelope_msg,
            "reachable": is_reachable,
            "envelope_message": envelope_msg[:140] if envelope_msg else None,
            "error": None,
        }
    except requests.Timeout:
        elapsed_ms = round((time.time() - start) * 1000)
        return {
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "exists": False,
            "success": False,
            "reachable": False,
            "error": "Timeout (15s)",
        }
    except requests.RequestException as e:
        elapsed_ms = round((time.time() - start) * 1000)
        return {
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "exists": False,
            "success": False,
            "reachable": False,
            "error": str(e)[:200],
        }


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_console_report(results: list, run_info: dict):
    """Print color-coded console report."""
    print(f"\n{'=' * 78}")
    print(f"{BOLD}OCROLUS API HEALTH CHECK{RESET}")
    print(f"{'=' * 78}")
    print(f"  Timestamp: {run_info['timestamp']}")
    if run_info.get("auth_success"):
        print(f"  Auth: {GREEN}Authenticated{RESET}")
    else:
        print(f"  Auth: {RED}Failed{RESET}")
    print()

    current_category = None
    for r in results:
        if r["category"] != current_category:
            current_category = r["category"]
            print(f"\n  {BOLD}{CYAN}{current_category}{RESET}")
            print(f"  {'─' * 72}")

        status = r.get("status_code")
        exists = r.get("exists", False)
        error = r.get("error")
        time_ms = r.get("response_time_ms", 0)

        if error:
            icon = f"{RED}ERR{RESET}"
            status_str = "ERR"
        elif not exists:
            icon = f"{RED}404{RESET}"
            status_str = f"{status}"
        elif status and status < 300:
            icon = f"{GREEN} OK{RESET}"
            status_str = f"{status}"
        elif status in (400, 401, 403, 405, 422):
            # Route exists, rejected our probe - that's expected
            icon = f"{YELLOW}{status}{RESET}"
            status_str = f"{status}"
        else:
            icon = f"{YELLOW}{status or '???'}{RESET}"
            status_str = f"{status or '???'}"

        # Webhook validation entries use a different display format
        wh_status = r.get("webhook_status")
        if wh_status:
            if wh_status == "PASS":
                icon = f"{GREEN}PASS{RESET}"
            elif wh_status == "WARN":
                icon = f"{YELLOW}WARN{RESET}"
            elif wh_status == "NONE":
                icon = f"{YELLOW}NONE{RESET}"
            else:
                icon = f"{RED}FAIL{RESET}"
            print(f"  [{icon}]  {r['name']:<40} {r['path']}")
            continue

        method_tag = f"[{r['method']:>6}]"
        print(f"  [{icon}] {status_str:>4}  {method_tag} {r['path']:<50} {time_ms:>5}ms  {r['name']}")
        if error:
            print(f"         {RED}^ {error}{RESET}")

    # Summary
    total = len(results)
    reachable = sum(1 for r in results if r.get("reachable"))
    success = sum(1 for r in results if r.get("success"))
    failed_404 = sum(1 for r in results if not r.get("exists") and not r.get("error"))
    errors = sum(1 for r in results if r.get("error"))
    times = [r["response_time_ms"] for r in results if r.get("response_time_ms")]
    avg_time = round(sum(times) / len(times)) if times else 0

    print(f"\n{'=' * 78}")
    print(f"{BOLD}SUMMARY{RESET}")
    print(f"{'=' * 78}")
    print(f"  Total: {total} | Reachable: {GREEN}{reachable}{RESET} | "
          f"Success (2xx): {GREEN}{success}{RESET} | "
          f"Not Found: {RED}{failed_404}{RESET} | Errors: {RED}{errors}{RESET}")
    print(f"  Avg Response Time: {avg_time}ms")

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "reachable": 0}
        categories[cat]["total"] += 1
        if r.get("reachable"):
            categories[cat]["reachable"] += 1

    print(f"\n  {BOLD}By Category:{RESET}")
    for cat, counts in categories.items():
        pct = round(100 * counts["reachable"] / counts["total"]) if counts["total"] else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        color = GREEN if pct >= 80 else YELLOW if pct >= 50 else RED
        print(f"    {cat:<25} {color}{bar} {pct:>3}%{RESET} ({counts['reachable']}/{counts['total']})")

    print()


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def save_json_report(results: list, run_info: dict, output_dir: str) -> str:
    """Save JSON report, return filepath."""
    os.makedirs(output_dir, exist_ok=True)
    ts = run_info["timestamp"].replace(":", "-").replace(" ", "T")
    filepath = os.path.join(output_dir, f"health-check-{ts}.json")

    report = {
        "run_info": run_info,
        "summary": _build_summary(results),
        "results": results,
    }
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    return filepath


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def save_html_report(results: list, run_info: dict, output_dir: str) -> str:
    """Save self-contained HTML dashboard report."""
    os.makedirs(output_dir, exist_ok=True)
    ts = run_info["timestamp"].replace(":", "-").replace(" ", "T")
    filepath = os.path.join(output_dir, f"health-check-{ts}.html")

    summary = _build_summary(results)
    categories = _build_category_summary(results)

    # Build endpoint rows
    rows_html = ""
    for r in results:
        status = r.get("status_code", "ERR")
        exists = r.get("exists", False)
        error = r.get("error")

        if error:
            badge_class = "badge-error"
            badge_text = "ERROR"
        elif not exists:
            badge_class = "badge-fail"
            badge_text = f"404"
        elif status and status < 300:
            badge_class = "badge-pass"
            badge_text = f"{status}"
        elif status in (400, 401, 403, 405, 422):
            badge_class = "badge-warn"
            badge_text = f"{status}"
        else:
            badge_class = "badge-warn"
            badge_text = f"{status or '?'}"

        time_ms = r.get("response_time_ms", 0)
        time_bar_width = min(time_ms / 10, 100)  # scale: 1000ms = 100%
        error_note = f'<div class="error-note">{error}</div>' if error else ""

        rows_html += f"""
        <tr>
            <td><span class="badge {badge_class}">{badge_text}</span></td>
            <td><code>{r['method']}</code></td>
            <td><code>{r['path']}</code></td>
            <td>{r['name']}</td>
            <td>{r['category']}</td>
            <td>
                <div class="time-bar-container">
                    <div class="time-bar" style="width: {time_bar_width}%"></div>
                    <span class="time-label">{time_ms}ms</span>
                </div>
            </td>
            <td>{error_note}</td>
        </tr>"""

    # Build category cards
    cat_cards_html = ""
    for cat, info in categories.items():
        pct = info["percent"]
        color = "#2ecc71" if pct >= 80 else "#f39c12" if pct >= 50 else "#e74c3c"
        cat_cards_html += f"""
        <div class="cat-card">
            <h3>{cat}</h3>
            <div class="cat-bar-bg">
                <div class="cat-bar-fill" style="width: {pct}%; background: {color}"></div>
            </div>
            <p>{info['reachable']}/{info['total']} reachable ({pct}%)</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ocrolus API Health Check - {run_info['timestamp']}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #0f1117; color: #e1e4e8; line-height: 1.6; padding: 20px; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    h1 {{ color: #fff; margin-bottom: 5px; font-size: 1.8em; }}
    .subtitle {{ color: #8b949e; margin-bottom: 25px; }}

    .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                      gap: 15px; margin-bottom: 30px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
             padding: 20px; text-align: center; }}
    .card .value {{ font-size: 2.2em; font-weight: 700; }}
    .card .label {{ color: #8b949e; font-size: 0.9em; margin-top: 5px; }}
    .card.pass .value {{ color: #2ecc71; }}
    .card.fail .value {{ color: #e74c3c; }}
    .card.warn .value {{ color: #f39c12; }}
    .card.info .value {{ color: #3498db; }}

    .section {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
                padding: 20px; margin-bottom: 20px; }}
    .section h2 {{ color: #fff; margin-bottom: 15px; font-size: 1.3em; }}

    .cat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; }}
    .cat-card {{ background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 15px; }}
    .cat-card h3 {{ font-size: 0.95em; margin-bottom: 8px; color: #c9d1d9; }}
    .cat-card p {{ font-size: 0.85em; color: #8b949e; margin-top: 5px; }}
    .cat-bar-bg {{ height: 8px; background: #21262d; border-radius: 4px; overflow: hidden; }}
    .cat-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
    th {{ text-align: left; padding: 10px 8px; border-bottom: 2px solid #30363d;
          color: #8b949e; font-weight: 600; }}
    td {{ padding: 8px; border-bottom: 1px solid #21262d; }}
    tr:hover {{ background: #1c2128; }}
    code {{ background: #0d1117; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}

    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
              font-size: 0.8em; font-weight: 600; }}
    .badge-pass {{ background: #0e3a1e; color: #2ecc71; }}
    .badge-fail {{ background: #3a0e0e; color: #e74c3c; }}
    .badge-warn {{ background: #3a2e0e; color: #f39c12; }}
    .badge-error {{ background: #3a0e0e; color: #ff6b6b; }}

    .time-bar-container {{ display: flex; align-items: center; gap: 8px; min-width: 150px; }}
    .time-bar {{ height: 6px; background: #3498db; border-radius: 3px; min-width: 2px; }}
    .time-label {{ font-size: 0.8em; color: #8b949e; white-space: nowrap; }}

    .error-note {{ font-size: 0.8em; color: #e74c3c; max-width: 200px; word-wrap: break-word; }}

    .auth-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px;
                   font-weight: 600; margin-left: 10px; }}
    .auth-ok {{ background: #0e3a1e; color: #2ecc71; }}
    .auth-fail {{ background: #3a0e0e; color: #e74c3c; }}

    .btn {{ display: inline-block; padding: 8px 16px; border-radius: 6px; font-size: 0.85em;
            font-weight: 600; cursor: pointer; text-decoration: none; border: 1px solid #30363d;
            margin-right: 8px; margin-bottom: 8px; transition: all 0.2s; }}
    .btn:hover {{ filter: brightness(1.2); }}
    .btn-green {{ background: #0e3a1e; color: #2ecc71; }}
    .btn-blue {{ background: #0e1e3a; color: #3498db; }}
    .btn-purple {{ background: #2a0e3a; color: #a855f7; }}
    .toolbar {{ display: flex; align-items: center; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}

    @media (max-width: 768px) {{
        .summary-cards {{ grid-template-columns: repeat(2, 1fr); }}
        table {{ font-size: 0.8em; }}
        .time-bar-container {{ min-width: 80px; }}
    }}
</style>
</head>
<body>
<div class="container">
    <h1>Ocrolus API Health Check</h1>
    <p class="subtitle">
        {run_info['timestamp']}
        <span class="auth-badge {'auth-ok' if run_info.get('auth_success') else 'auth-fail'}">
            {'Authenticated' if run_info.get('auth_success') else 'Auth Failed'}
        </span>
    </p>

    <div class="toolbar">
        <a class="btn btn-green" href="#" onclick="exportJSON(); return false;">Export JSON</a>
        <a class="btn btn-blue" href="#" onclick="exportCSV(); return false;">Export CSV</a>
        <a class="btn btn-purple" href="#" onclick="exportHTML(); return false;">Save HTML Snapshot</a>
    </div>

    <div class="summary-cards">
        <div class="card info">
            <div class="value">{summary['total']}</div>
            <div class="label">Total Endpoints</div>
        </div>
        <div class="card pass">
            <div class="value">{summary['reachable']}</div>
            <div class="label">Reachable</div>
        </div>
        <div class="card {'pass' if summary['success'] > 0 else 'warn'}">
            <div class="value">{summary['success']}</div>
            <div class="label">Success (2xx)</div>
        </div>
        <div class="card fail">
            <div class="value">{summary['not_found'] + summary['errors']}</div>
            <div class="label">Failed / Errors</div>
        </div>
        <div class="card info">
            <div class="value">{summary['avg_response_ms']}ms</div>
            <div class="label">Avg Response Time</div>
        </div>
        <div class="card {'pass' if summary['health_pct'] >= 80 else 'warn' if summary['health_pct'] >= 50 else 'fail'}">
            <div class="value">{summary['health_pct']}%</div>
            <div class="label">Health Score</div>
        </div>
    </div>

    <div class="section">
        <h2>Category Breakdown</h2>
        <div class="cat-grid">
            {cat_cards_html}
        </div>
    </div>

    <div class="section">
        <h2>Endpoint Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Status</th>
                    <th>Method</th>
                    <th>Path</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Response Time</th>
                    <th>Notes</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>

    <div class="section" style="text-align:center; color:#8b949e; font-size:0.85em;">
        Generated by Ocrolus API Health Check | {run_info['timestamp']}
    </div>
</div>
<script>
var _reportData = {json.dumps({"run_info": run_info, "summary": summary, "results": [{k: v for k, v in r.items()} for r in results]})};

function _download(filename, content, mime) {{
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([content], {{type: mime}}));
    a.download = filename;
    a.click();
}}

function exportJSON() {{
    _download("health-check-{run_info['timestamp'].replace(' ', 'T').replace(':', '-')}.json",
              JSON.stringify(_reportData, null, 2), "application/json");
}}

function exportCSV() {{
    var rows = [["status_code","method","path","name","category","response_time_ms","reachable","success","error"]];
    _reportData.results.forEach(function(r) {{
        rows.push([r.status_code, r.method, r.path, r.name, r.category, r.response_time_ms, r.reachable, r.success, r.error || ""]);
    }});
    var csv = rows.map(function(r) {{ return r.map(function(c) {{ return '"' + String(c).replace(/"/g, '""') + '"'; }}).join(","); }}).join("\\n");
    _download("health-check-{run_info['timestamp'].replace(' ', 'T').replace(':', '-')}.csv", csv, "text/csv");
}}

function exportHTML() {{
    _download("health-check-{run_info['timestamp'].replace(' ', 'T').replace(':', '-')}.html",
              document.documentElement.outerHTML, "text/html");
}}
</script>
</body>
</html>"""

    with open(filepath, "w") as f:
        f.write(html)
    return filepath


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_summary(results: list) -> dict:
    total = len(results)
    reachable = sum(1 for r in results if r.get("reachable"))
    success = sum(1 for r in results if r.get("success"))
    not_found = sum(1 for r in results if not r.get("exists") and not r.get("error"))
    errors = sum(1 for r in results if r.get("error"))
    times = [r["response_time_ms"] for r in results if r.get("response_time_ms")]
    avg_time = round(sum(times) / len(times)) if times else 0
    health_pct = round(100 * reachable / total) if total else 0

    return {
        "total": total,
        "reachable": reachable,
        "success": success,
        "not_found": not_found,
        "errors": errors,
        "avg_response_ms": avg_time,
        "health_pct": health_pct,
    }


def _build_category_summary(results: list) -> dict:
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "reachable": 0}
        categories[cat]["total"] += 1
        if r.get("reachable"):
            categories[cat]["reachable"] += 1
    for cat in categories:
        t = categories[cat]["total"]
        r = categories[cat]["reachable"]
        categories[cat]["percent"] = round(100 * r / t) if t else 0
    return categories


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_health_check(token: Optional[str], auth_success: bool, include_webhooks: bool = False) -> tuple:
    """Run health check against all endpoints. Returns (results, run_info)."""
    now = datetime.now(timezone.utc)
    run_info = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "auth_success": auth_success,
        "base_url": BASE_URL,
        "endpoint_count": len(ENDPOINTS),
    }

    results = []
    for name, method, path, category, params in ENDPOINTS:
        # Special handling for auth endpoint
        if path == AUTH_URL:
            result = {
                "name": name,
                "method": method,
                "path": path,
                "category": category,
                "status_code": 200 if auth_success else 401,
                "response_time_ms": 0,
                "exists": True,
                "success": auth_success,
                "reachable": True,
                "error": None if auth_success else "Authentication failed",
            }
        elif not token:
            result = {
                "name": name,
                "method": method,
                "path": path,
                "category": category,
                "status_code": None,
                "response_time_ms": 0,
                "exists": False,
                "success": False,
                "reachable": False,
                "error": "No auth token - cannot probe",
            }
        else:
            probe = probe_endpoint(token, method, path, params)
            result = {
                "name": name,
                "method": method,
                "path": path,
                "category": category,
                **probe,
            }
        results.append(result)

    # Webhook operational validation
    if include_webhooks and token:
        webhook_results = validate_webhooks(token)
        for wr in webhook_results:
            operational = wr.get("operational", False)
            wh_status = wr.get("status", "UNKNOWN")
            results.append({
                "name": wr["name"],
                "method": "CHECK",
                "path": wr.get("message", ""),
                "category": wr["category"],
                "status_code": None,
                "response_time_ms": 0,
                "exists": True,
                "success": operational,
                "reachable": operational,
                "error": None if wh_status != "FAIL" else wr.get("message"),
                "webhook_status": wh_status,
            })

    return results, run_info


def main():
    parser = argparse.ArgumentParser(description="Ocrolus API Health Check")
    parser.add_argument("--output-dir", default="./reports", help="Report output directory")
    parser.add_argument("--webhooks", action="store_true", help="Also discover webhook events")
    parser.add_argument("--write-paths", action="store_true", help="Test write endpoints with real book")
    parser.add_argument("--html-only", action="store_true", help="Only generate HTML report")
    parser.add_argument("--json-only", action="store_true", help="Only generate JSON report")
    parser.add_argument("--console-only", action="store_true", help="Only print console report")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to run")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between repeated runs")
    args = parser.parse_args()

    client_id = os.environ.get("OCROLUS_CLIENT_ID")
    client_secret = os.environ.get("OCROLUS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(f"{RED}ERROR: Set OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET environment variables{RESET}")
        print("Example:")
        print('  export OCROLUS_CLIENT_ID="your_id"')
        print('  export OCROLUS_CLIENT_SECRET="your_secret"')
        sys.exit(1)

    # Determine output modes
    gen_console = True
    gen_json = True
    gen_html = True
    if args.html_only:
        gen_console = False
        gen_json = False
    elif args.json_only:
        gen_console = False
        gen_html = False
    elif args.console_only:
        gen_json = False
        gen_html = False

    for run_num in range(1, args.repeat + 1):
        if args.repeat > 1:
            print(f"\n{'=' * 78}")
            print(f"  Run {run_num}/{args.repeat}")
            print(f"{'=' * 78}")

        # Authenticate
        print("Authenticating...")
        token = get_token(client_id, client_secret)
        auth_success = token is not None
        if auth_success:
            print(f"{GREEN}Authentication successful.{RESET}")
        else:
            print(f"{RED}Authentication failed. Will mark all endpoints as unreachable.{RESET}")

        # Run check
        print(f"Probing {len(ENDPOINTS)} endpoints...")
        if args.webhooks:
            print("Including webhook operational validation...")
        results, run_info = run_health_check(token, auth_success, include_webhooks=args.webhooks)

        # Output
        if gen_console:
            print_console_report(results, run_info)

        saved_files = []
        if gen_json:
            path = save_json_report(results, run_info, args.output_dir)
            saved_files.append(path)

        if gen_html:
            path = save_html_report(results, run_info, args.output_dir)
            saved_files.append(path)

        if saved_files:
            print(f"  Reports saved to:")
            for f in saved_files:
                print(f"    {f}")

        # Wait between runs
        if run_num < args.repeat:
            print(f"\n  Waiting {args.interval}s before next run...")
            time.sleep(args.interval)

    summary = _build_summary(results)
    print(f"\n{BOLD}Health Check Complete{RESET}")
    print(f"  Total: {summary['total']} | Reachable: {summary['reachable']} | "
          f"Failed: {summary['not_found']} | Errors: {summary['errors']} | "
          f"Avg: {summary['avg_response_ms']}ms")


if __name__ == "__main__":
    main()
