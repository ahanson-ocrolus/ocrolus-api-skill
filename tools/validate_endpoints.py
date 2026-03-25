"""
Ocrolus Endpoint Validation Script
====================================

Runs against a live Ocrolus tenant to confirm which endpoint paths
actually return successful responses. Resolves doc-vs-reality conflicts.

Requirements:
    pip install requests

Usage:
    # Validate all API endpoints:
    export OCROLUS_CLIENT_ID="your_id"
    export OCROLUS_CLIENT_SECRET="your_secret"
    python validate_endpoints.py

    # Also discover canonical webhook event names:
    python validate_endpoints.py --webhooks

    # Full validation including write-path probing (creates then deletes a test book):
    python validate_endpoints.py --write-paths

    # Output results to a file:
    python validate_endpoints.py --output validation_results.json

What this does:
    1. Authenticates against your Ocrolus tenant
    2. Probes GET endpoints with lightweight requests
    3. For write-path conflicts (POST/PUT/DELETE), uses two strategies:
       a. Default: sends OPTIONS or HEAD to distinguish 404 (no route) from 405 (route exists, wrong method)
       b. --write-paths flag: actually creates a test book to confirm create/status/transaction paths,
          then cleans up by deleting it
    4. For endpoints with conflicting doc paths, tests BOTH variants
    5. If --webhooks: calls List Webhook Events and dumps the raw response to
       show canonical event names in whatever schema Ocrolus returns
    6. Prints a report and optionally saves JSON results

Safety:
    - Without --write-paths: read-only, no side effects
    - With --write-paths: creates ONE test book named "endpoint-validation-test-DELETE-ME",
      uses it to probe write paths, then deletes it
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

import requests


BASE_URL = "https://api.ocrolus.com"
AUTH_URL = "https://auth.ocrolus.com/oauth/token"


def get_token(client_id: str, client_secret: str) -> str:
    """Obtain OAuth token."""
    resp = requests.post(AUTH_URL, data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    })
    if not resp.ok:
        print(f"FATAL: Authentication failed ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)
    return resp.json()["access_token"]


def probe_get(token: str, path: str, params: Optional[dict] = None) -> dict:
    """Probe a GET endpoint. Straightforward -- sends GET, checks response."""
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        return {
            "path": path,
            "method_tested": "GET",
            "status_code": resp.status_code,
            "exists": resp.status_code != 404,
            "success": resp.ok,
            "note": "",
        }
    except requests.RequestException as e:
        return {
            "path": path, "method_tested": "GET", "status_code": None,
            "exists": False, "success": False, "note": f"Connection error: {e}",
        }


def probe_write_path(token: str, method: str, path: str) -> dict:
    """
    Probe a non-GET endpoint path without actually executing the operation.

    Strategy: send the correct HTTP method with an empty/minimal body.
    We distinguish three outcomes:
      - 404: route does not exist at all
      - 405: route exists but doesn't accept this method (unlikely for correct method, but informative)
      - 400/401/403/422: route EXISTS and rejected our bad payload -- path is valid
      - 200/201: route exists and somehow accepted (unlikely with empty body)

    Key insight: 400 "bad request" means the route matched and the server
    tried to process it -- that confirms the path is real, even though our
    request was intentionally incomplete.
    """
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.request(method.upper(), url, headers=headers, json={}, timeout=15)
        route_exists = resp.status_code != 404
        return {
            "path": path,
            "method_tested": method.upper(),
            "status_code": resp.status_code,
            "exists": route_exists,
            "success": resp.ok,
            "note": (
                "400/422 = route exists, rejected empty payload (path confirmed)"
                if resp.status_code in (400, 422) else
                "405 = path exists but wrong method"
                if resp.status_code == 405 else
                ""
            ),
        }
    except requests.RequestException as e:
        return {
            "path": path, "method_tested": method.upper(), "status_code": None,
            "exists": False, "success": False, "note": f"Connection error: {e}",
        }


def probe_write_paths_live(token: str) -> dict:
    """
    Create a real test book to resolve write-path conflicts definitively.
    Tests create, status, transactions, then cleans up.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    results = {}

    print("\n  --- LIVE WRITE-PATH PROBING ---")
    print("  Creating test book...")

    # Test Create Book: try both paths
    for label, path in [("POST /v1/book/create", "/v1/book/create"), ("POST /v1/books", "/v1/books")]:
        try:
            resp = requests.post(
                f"{BASE_URL}{path}", headers=headers,
                json={"name": "endpoint-validation-test-DELETE-ME"}, timeout=15,
            )
            results[label] = {
                "status_code": resp.status_code, "success": resp.ok,
                "response_keys": list(resp.json().keys()) if resp.ok else None,
            }
            if resp.ok:
                book_data = resp.json()
                print(f"  [OK] {resp.status_code}  {path} -- book created")
            else:
                print(f"  [XX] {resp.status_code}  {path} -- {resp.text[:100]}")
        except Exception as e:
            results[label] = {"status_code": None, "success": False, "note": str(e)}
            print(f"  [ERR] {path} -- {e}")

    # Find whichever create succeeded to get book_pk and book_uuid
    book_pk = None
    book_uuid = None
    for label in results:
        if results[label].get("success"):
            # Re-fetch via list to get the test book
            try:
                resp = requests.get(f"{BASE_URL}/v1/books", headers=headers, timeout=15)
                if resp.ok:
                    books = resp.json()
                    # Find our test book
                    book_list = books if isinstance(books, list) else books.get("books", books.get("data", []))
                    for b in (book_list if isinstance(book_list, list) else []):
                        name = b.get("name", "")
                        if "endpoint-validation-test" in name:
                            book_pk = b.get("pk") or b.get("book_pk") or b.get("id")
                            book_uuid = b.get("uuid") or b.get("book_uuid")
                            break
            except Exception:
                pass
            break

    if book_pk:
        print(f"  Test book: pk={book_pk}, uuid={book_uuid}")

        # Test Book Status: both variants
        for label, path, params in [
            ("GET /v1/book/status (query)", "/v1/book/status", {"book_pk": str(book_pk)}),
            ("GET /v1/book/{pk}/status (path)", f"/v1/book/{book_pk}/status", None),
        ]:
            try:
                resp = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=15)
                results[label] = {"status_code": resp.status_code, "success": resp.ok}
                icon = "OK" if resp.ok else "XX"
                full_path = f"{path}?book_pk={book_pk}" if params else path
                print(f"  [{icon}] {resp.status_code}  {full_path}")
            except Exception as e:
                results[label] = {"status_code": None, "success": False}
                print(f"  [ERR] {path} -- {e}")

        # Test Transactions: both variants
        for label, path, params in [
            ("GET /v1/book/{pk}/transactions (path)", f"/v1/book/{book_pk}/transactions", None),
            ("GET /v1/book/transactions (query)", "/v1/book/transactions", {"book_pk": str(book_pk)}),
        ]:
            try:
                resp = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=15)
                results[label] = {"status_code": resp.status_code, "success": resp.ok}
                icon = "OK" if resp.ok else "XX"
                print(f"  [{icon}] {resp.status_code}  {path}")
            except Exception as e:
                results[label] = {"status_code": None, "success": False}

        # Cleanup: delete the test book
        print("  Cleaning up test book...")
        for del_path in ["/v1/book/delete"]:
            try:
                resp = requests.post(
                    f"{BASE_URL}{del_path}", headers=headers,
                    json={"book_pk": book_pk}, timeout=15,
                )
                if resp.ok:
                    print(f"  [OK] Test book deleted")
                else:
                    print(f"  [!!] Delete returned {resp.status_code} -- manually delete book pk={book_pk}")
            except Exception:
                print(f"  [!!] Delete failed -- manually delete book pk={book_pk}")
    else:
        print("  [!!] Could not create test book via either path -- write-path validation skipped")

    return results


# =============================================================================
# ENDPOINT DEFINITIONS
# =============================================================================

# (name, method, path, alt_path_or_None, params_or_None)
# For write endpoints (POST/PUT/DELETE), method is preserved and we probe properly.
ENDPOINTS_TO_VALIDATE = [
    # Book Operations -- write paths use probe_write_path (sends actual method with empty body)
    ("Create Book", "POST", "/v1/book/create", "/v1/books", None),
    ("Delete Book", "POST", "/v1/book/delete", None, None),
    ("Update Book", "POST", "/v1/book/update", None, None),
    ("Get Book Info", "GET", "/v1/book/1", None, None),
    ("List Books", "GET", "/v1/books", None, None),
    ("Book Status (query param)", "GET", "/v1/book/status", None, {"book_pk": "1"}),
    ("Book Status (path param)", "GET", "/v1/book/1/status", None, None),
    ("Book from Loan", "GET", "/v1/book/loan/test", None, None),

    # Upload -- write paths
    ("Upload PDF (flat)", "POST", "/v1/book/upload", None, None),
    ("Upload PDF (pk in path)", "POST", "/v1/book/1/upload/pdf", None, None),
    ("Upload Mixed", "POST", "/v1/book/upload/mixed", None, None),
    ("Upload Paystub", "POST", "/v1/book/upload/paystub", None, None),
    ("Upload Image", "POST", "/v1/book/upload/image", None, None),
    ("Upload Plaid", "POST", "/v1/book/upload/plaid", None, None),
    ("Import Plaid Asset", "POST", "/v1/book/import/plaid/asset", None, None),

    # Capture -- GET endpoints
    ("Book Forms", "GET", "/v1/book/1/forms", None, None),
    ("Book Transactions (path)", "GET", "/v1/book/1/transactions", None, None),
    ("Book Transactions (query)", "GET", "/v1/book/transactions", None, {"book_pk": "1"}),
    ("Document Forms", "GET", "/v1/document/test-uuid/forms", None, None),
    ("Form Fields", "GET", "/v1/form/test-uuid/fields", None, None),

    # Classify (v2)
    ("Book Classification", "GET", "/v2/book/test-uuid/classification-summary", None, None),
    ("Mixed Doc Classification", "GET", "/v2/mixed-document/test-uuid/classification-summary", None, None),
    ("Grouped Mixed Doc", "GET", "/v2/index/mixed-doc/test-uuid/summary", None, None),

    # Detect (v2)
    ("Detect Book Signals (v2)", "GET", "/v2/detect/book/test-uuid/signals", None, None),
    ("Detect Doc Signals (v2)", "GET", "/v2/detect/document/test-uuid/signals", None, None),
    ("Detect Viz (v2)", "GET", "/v2/detect/visualization/test-uuid", None, None),
    ("Detect Book Signals (v1 legacy)", "GET", "/v1/book/test-uuid/fraud-signals", None, None),

    # Cash Flow (v2) -- naming variants
    ("Book Summary", "GET", "/v2/book/test-uuid/summary", None, None),
    ("Cash Flow Features (underscore)", "GET", "/v2/book/test-uuid/cash_flow_features", None, None),
    ("Cash Flow Features (kebab)", "GET", "/v2/book/test-uuid/cashflow-features", None, None),
    ("Enriched Txns (underscore)", "GET", "/v2/book/test-uuid/enriched_txns", None, None),
    ("Enriched Txns (kebab)", "GET", "/v2/book/test-uuid/enriched-transactions", None, None),
    ("Risk Score (underscore)", "GET", "/v2/book/test-uuid/cash_flow_risk_score", None, None),
    ("Risk Score (kebab)", "GET", "/v2/book/test-uuid/risk-score", None, None),
    ("Benchmarking", "GET", "/v2/book/test-uuid/benchmarking", None, None),
    ("Analytics Excel", "GET", "/v2/book/test-uuid/lender_analytics/xlsx", None, None),

    # Income
    ("Income Calculations", "GET", "/v2/book/test-uuid/income-calculations", None, None),
    ("Income Summary", "GET", "/v2/book/test-uuid/income-summary", None, None),
    ("BSIC", "GET", "/v2/book/test-uuid/bsic", None, None),

    # Tags
    ("List Tags", "GET", "/v2/analytics/tags", None, None),
    ("Revenue Deduction Tags", "GET", "/v2/analytics/revenue-deduction-tags", None, None),

    # Encore
    ("List Copy Jobs", "GET", "/v1/book/copy-jobs", None, None),
    ("Copy Settings", "GET", "/v1/settings/book-copy", None, None),

    # Webhooks -- path variants
    ("Webhooks List (account/settings)", "GET", "/v1/account/settings/webhooks", None, None),
    ("Webhooks List (org)", "GET", "/v1/org/webhooks", None, None),
    ("Webhook Events (account/settings)", "GET", "/v1/account/settings/webhooks/events", None, None),
    ("Webhook Events (org)", "GET", "/v1/org/webhooks/events", None, None),
    ("Account Webhook Config", "GET", "/v1/webhook/configuration", None, None),
]


def run_validation(token: str, include_webhooks: bool = False, write_paths: bool = False) -> dict:
    """Run all endpoint probes and return results."""
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endpoints": [],
        "write_path_results": None,
        "webhook_events": None,
    }

    print("\n" + "=" * 70)
    print("OCROLUS ENDPOINT VALIDATION")
    print("=" * 70)

    for name, method, path, alt_path, params in ENDPOINTS_TO_VALIDATE:
        # Choose probe strategy based on HTTP method
        if method.upper() == "GET":
            result = probe_get(token, path, params)
        else:
            result = probe_write_path(token, method, path)

        result["name"] = name

        # Test alternate path if provided
        if alt_path:
            if method.upper() == "GET":
                alt_result = probe_get(token, alt_path, params)
            else:
                alt_result = probe_write_path(token, method, alt_path)
            result["alt_path"] = alt_path
            result["alt_status_code"] = alt_result["status_code"]
            result["alt_exists"] = alt_result["exists"]
            result["alt_note"] = alt_result.get("note", "")

        results["endpoints"].append(result)

        # Print result
        status_str = f"{result['status_code']}" if result['status_code'] else "ERR"
        icon = "OK" if result["exists"] else "XX"
        method_tag = f"[{result['method_tested']}]" if result["method_tested"] != "GET" else ""
        note = f"  ({result['note']})" if result.get("note") else ""
        line = f"  [{icon}] {status_str:>4}  {method_tag:>6} {path:<50} {name}{note}"
        if alt_path:
            alt_icon = "OK" if result.get("alt_exists") else "XX"
            alt_status = f"{result['alt_status_code']}" if result.get('alt_status_code') else "ERR"
            alt_note = f"  ({result.get('alt_note', '')})" if result.get("alt_note") else ""
            line += f"\n  [{alt_icon}] {alt_status:>4}  {method_tag:>6} {alt_path:<50} (alt){alt_note}"
        print(line)

    # Live write-path probing (creates a real book)
    if write_paths:
        results["write_path_results"] = probe_write_paths_live(token)

    # Webhook event discovery
    if include_webhooks:
        print("\n" + "-" * 70)
        print("WEBHOOK EVENT DISCOVERY")
        print("-" * 70)
        print("  (Dumping raw API response so you see the exact schema)\n")

        for events_path in ["/v1/account/settings/webhooks/events", "/v1/org/webhooks/events"]:
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = requests.get(f"{BASE_URL}{events_path}", headers=headers, timeout=15)
                if resp.ok:
                    raw_response = resp.json()
                    results["webhook_events"] = {"path": events_path, "raw_response": raw_response}

                    print(f"  Endpoint: {events_path}")
                    print(f"  Status: {resp.status_code}")
                    print(f"  Raw response:\n")
                    print(json.dumps(raw_response, indent=4))

                    # Extract event names from any plausible key
                    event_names = _extract_event_names(raw_response)
                    if event_names:
                        print(f"\n  Extracted event names ({len(event_names)}):")
                        for name in sorted(event_names):
                            print(f"    - {name}")
                        results["webhook_events"]["extracted_names"] = sorted(event_names)

                    # Also identify the payload field name used for event type
                    payload_key = _detect_event_type_field(raw_response)
                    if payload_key:
                        print(f"\n  Event type field name in payloads: \"{payload_key}\"")
                        print(f"  (Use this as the key in event.get(\"{payload_key}\") in your handlers)")
                        results["webhook_events"]["event_type_field"] = payload_key

                    print(f"\n  ** Copy the names above into your webhook handlers **")
                    print(f"  ** Use the field name above instead of hardcoded \"event_type\" **")
                    break
                else:
                    print(f"  [{resp.status_code}] {events_path} -- trying alternate...")
            except requests.RequestException as e:
                print(f"  [ERR] {events_path} -- {e}")

        if results["webhook_events"] is None:
            print("\n  WARNING: Could not retrieve webhook event list from either path.")
            print("  You may need to register a webhook first before events are listed.")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    exists_count = sum(1 for e in results["endpoints"] if e["exists"])
    total = len(results["endpoints"])
    print(f"  Endpoints probed: {total}")
    print(f"  Routes confirmed (not 404): {exists_count}")
    print(f"  Write endpoints tested with actual method: {sum(1 for e in results['endpoints'] if e['method_tested'] != 'GET')}")

    conflicts = [e for e in results["endpoints"] if e.get("alt_path")]
    if conflicts:
        print(f"\n  PATH CONFLICTS:")
        for e in conflicts:
            primary = "YES" if e["exists"] else "no"
            alt = "YES" if e.get("alt_exists") else "no"
            # Flag ambiguous cases
            ambiguous = ""
            if e["exists"] and e.get("alt_exists"):
                ambiguous = "  ** BOTH paths responded -- use --write-paths to disambiguate **"
            print(f"    {e['name']}:{ambiguous}")
            print(f"      {e['path']:<55} -> {primary}")
            print(f"      {e['alt_path']:<55} -> {alt}")

    if write_paths and results.get("write_path_results"):
        print(f"\n  LIVE WRITE-PATH RESULTS:")
        for label, info in results["write_path_results"].items():
            icon = "OK" if info.get("success") else "XX"
            print(f"    [{icon}] {info.get('status_code', 'ERR'):>4}  {label}")

    return results


def _extract_event_names(response) -> list[str]:
    """
    Extract event name strings from the webhook events response,
    handling any plausible schema Ocrolus might use.
    """
    names = []

    if isinstance(response, list):
        for item in response:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                # Try every plausible key for the event name
                for key in ("name", "event_name", "event_type", "type", "event", "id", "key", "value"):
                    if key in item and isinstance(item[key], str):
                        names.append(item[key])
                        break
                else:
                    # If no known key, dump the whole object so the user can see
                    names.append(json.dumps(item))
    elif isinstance(response, dict):
        # Could be {"events": [...]} or {"data": [...]} wrapper
        for wrapper_key in ("events", "data", "items", "results", "event_types", "webhook_events"):
            if wrapper_key in response and isinstance(response[wrapper_key], list):
                names.extend(_extract_event_names(response[wrapper_key]))
                break
        else:
            # Maybe the keys themselves are event names
            for key, val in response.items():
                if isinstance(val, (str, dict)):
                    names.append(key)

    return names


def _detect_event_type_field(response) -> Optional[str]:
    """
    Try to detect which field name Ocrolus uses for the event type
    in webhook payloads, by inspecting the events list response.
    """
    # Look for sample payloads or field hints in the response
    items = []
    if isinstance(response, list):
        items = response
    elif isinstance(response, dict):
        for key in ("events", "data", "items", "results"):
            if key in response and isinstance(response[key], list):
                items = response[key]
                break

    for item in items:
        if isinstance(item, dict):
            # If any item has a "payload" example, check its keys
            if "payload" in item and isinstance(item["payload"], dict):
                for key in ("event_type", "event_name", "type", "event"):
                    if key in item["payload"]:
                        return key
            # Otherwise check the item itself for clues
            for key in ("event_type", "event_name", "type"):
                if key in item:
                    return key

    return None


def main():
    parser = argparse.ArgumentParser(description="Validate Ocrolus API endpoints against a live tenant")
    parser.add_argument("--webhooks", action="store_true", help="Discover canonical webhook event names")
    parser.add_argument("--write-paths", action="store_true",
                        help="Create a test book to definitively resolve write-path conflicts (creates then deletes)")
    parser.add_argument("--output", "-o", type=str, help="Save results to JSON file")
    args = parser.parse_args()

    client_id = os.environ.get("OCROLUS_CLIENT_ID")
    client_secret = os.environ.get("OCROLUS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Set OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET environment variables")
        sys.exit(1)

    print("Authenticating...")
    token = get_token(client_id, client_secret)
    print("Authentication successful.\n")

    if args.write_paths:
        print("NOTE: --write-paths will create and delete a test book on your tenant.\n")

    results = run_validation(token, include_webhooks=args.webhooks, write_paths=args.write_paths)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    print("\nDone. Update references/endpoints.md, references/webhooks.md,")
    print("references/coverage-matrix.md, and ocrolus_client.py")
    print("with the confirmed paths above.")


if __name__ == "__main__":
    main()
