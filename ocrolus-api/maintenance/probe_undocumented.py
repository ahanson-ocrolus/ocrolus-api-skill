#!/usr/bin/env python3
"""Probe undocumented/missing Ocrolus API endpoints discovered from the official OpenAPI spec.

Compares official spec paths against our documented endpoints and tests each
undiscovered path against a live tenant.
"""

import json
import os
import sys
import time
import requests

AUTH_URL = "https://auth.ocrolus.com/oauth/token"
BASE_URL = "https://api.ocrolus.com"

CLIENT_ID = os.environ.get("OCROLUS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("OCROLUS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Set OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET environment variables")
    sys.exit(1)


def get_token():
    resp = requests.post(AUTH_URL, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def probe(token, method, path, description="", data=None, json_body=None):
    """Probe an endpoint and return results."""
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            if json_body:
                r = requests.post(url, headers=headers, json=json_body, timeout=30)
            elif data:
                r = requests.post(url, headers=headers, data=data, timeout=30)
            else:
                r = requests.post(url, headers=headers, json={}, timeout=30)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=json_body or {}, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"path": path, "method": method, "error": f"Unknown method {method}"}

        elapsed = round((time.time() - start) * 1000)

        # Try to parse JSON response
        try:
            body = r.json()
        except Exception:
            body = r.text[:500] if r.text else None

        return {
            "method": method,
            "path": path,
            "description": description,
            "status": r.status_code,
            "elapsed_ms": elapsed,
            "body_preview": json.dumps(body)[:300] if isinstance(body, (dict, list)) else str(body)[:300],
            "works": r.status_code < 500 and r.status_code != 404,
        }
    except Exception as e:
        return {
            "method": method,
            "path": path,
            "description": description,
            "status": -1,
            "error": str(e),
            "works": False,
        }


def main():
    print("=" * 80)
    print("UNDOCUMENTED ENDPOINT PROBE")
    print("Probing endpoints from official OpenAPI spec not in our toolkit")
    print("=" * 80)

    token = get_token()
    print(f"\n✓ Authenticated\n")

    # -----------------------------------------------------------------------
    # Category 1: Entirely new endpoints not in our toolkit
    # -----------------------------------------------------------------------
    new_endpoints = [
        # LOS Connect / Encompass
        ("GET", "/v2/los-connect/book/{book_uuid}/loan", "LOS Connect: get loan for book"),
        ("GET", "/v2/los-connect/encompass/book", "Encompass: get book"),

        # V2 document uploads
        ("POST", "/v2/book/{book_uuid}/document/paystub", "V2 paystub upload"),
        ("POST", "/v2/book/{book_uuid}/mixed-document", "V2 mixed document upload"),

        # JSON upload
        ("POST", "/v1/book/upload/json", "JSON document upload"),

        # Kickout rules
        ("GET", "/v1/settings/book-copy/kickout-rules", "Kickout rules list"),
        ("PUT", "/v1/settings/book-copy/kickout-rules", "Kickout rules update"),

        # V2 paystub retrieval
        ("GET", "/v2/book/{book_uuid}/paystub", "V2 book paystub"),
        ("GET", "/v2/document/{doc_uuid}/paystub", "V2 document paystub"),
        ("GET", "/v2/paystub/{paystub_uuid}", "V2 paystub by UUID"),

        # V2 document download
        ("GET", "/v2/document/download", "V2 document download (query param)"),

        # V2 typed document upload (generic)
        ("POST", "/v2/book/{book_uuid}/document/bank_statement", "V2 typed upload: bank_statement"),
        ("POST", "/v2/book/{book_uuid}/document/tax_return", "V2 typed upload: tax_return"),
    ]

    # -----------------------------------------------------------------------
    # Category 2: Alternate path aliases (query-param style from official spec)
    # -----------------------------------------------------------------------
    alias_endpoints = [
        # Book operations
        ("GET", "/v1/book/info", "Book info (query-param style)"),
        ("POST", "/v1/book/remove", "Book remove (alias for delete)"),

        # Document operations (query-param style)
        ("POST", "/v1/document/cancel", "Document cancel (query-param)"),
        ("POST", "/v1/document/remove", "Document remove (query-param)"),
        ("POST", "/v1/document/upgrade", "Document upgrade (query-param)"),

        # Data retrieval (query-param style)
        ("GET", "/v1/book/forms", "Book forms (query-param)"),
        ("GET", "/v1/form", "Form fields (query-param)"),
        ("GET", "/v1/transaction", "Transactions (query-param)"),

        # Image finalize variant
        ("POST", "/v1/book/upload/image/done", "Finalize image (alt path)"),
    ]

    # -----------------------------------------------------------------------
    # Category 3: Webhook path variations from official spec
    # -----------------------------------------------------------------------
    webhook_endpoints = [
        ("GET", "/v1/account/settings/webhook_details", "Webhook details"),
        ("GET", "/v1/account/settings/test_webhook_endpoint", "Test webhook endpoint (GET)"),
        ("POST", "/v1/account/settings/update/webhook_endpoint", "Update webhook endpoint (legacy)"),
    ]

    # -----------------------------------------------------------------------
    # Category 4: Income path variations
    # -----------------------------------------------------------------------
    income_endpoints = [
        ("GET", "/v2/book/{book_uuid}/income/bank-statement-v2", "BSIC v2 (alt path)"),
        ("GET", "/v2/book/{book_uuid}/income/bank-statement-v2/xlsx", "BSIC v2 Excel (alt path)"),
        ("POST", "/v2/book/{book_uuid}/income/entity_config", "Income entity config (alt path)"),
        ("GET", "/v2/book/{book_uuid}/income/summary", "Income summary (alt path)"),
    ]

    # Use a dummy UUID/PK for path params (will get 400/404 but proves route exists)
    dummy_uuid = "00000000-0000-0000-0000-000000000000"
    dummy_pk = "99999999"

    all_categories = [
        ("NEW ENDPOINTS", new_endpoints),
        ("PATH ALIASES (query-param style)", alias_endpoints),
        ("WEBHOOK VARIATIONS", webhook_endpoints),
        ("INCOME PATH VARIATIONS", income_endpoints),
    ]

    all_results = []

    for cat_name, endpoints in all_categories:
        print(f"\n{'─' * 60}")
        print(f"  {cat_name}")
        print(f"{'─' * 60}")

        for method, path, desc in endpoints:
            # Replace path params with dummies
            probe_path = (path
                         .replace("{book_uuid}", dummy_uuid)
                         .replace("{doc_uuid}", dummy_uuid)
                         .replace("{mixed_doc_uuid}", dummy_uuid)
                         .replace("{paystub_uuid}", dummy_uuid)
                         .replace("{visualization_uuid}", dummy_uuid)
                         .replace("{webhook_uuid}", dummy_uuid)
                         .replace("{tag_uuid}", dummy_uuid)
                         .replace("{pk}", dummy_pk)
                         .replace("{id}", "99999")
                         .replace("{book_pk}", dummy_pk))

            result = probe(token, method, probe_path, desc)
            result["original_path"] = path
            result["category"] = cat_name
            all_results.append(result)

            status = result["status"]
            works = result["works"]

            # Color coding
            if status == 200:
                icon = "✅"
            elif status in (400, 401, 403):
                icon = "⚠️ "  # Route exists but rejected our probe
            elif status == 404:
                icon = "❌"
            elif status >= 500:
                icon = "💥"
            else:
                icon = "❓"

            elapsed = result.get("elapsed_ms", "?")
            print(f"  {icon} {method:6} {path:55} → {status} ({elapsed}ms)")

            # Show body preview for interesting responses
            if status not in (404,) and result.get("body_preview"):
                preview = result["body_preview"][:150]
                print(f"       └─ {preview}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")

    working = [r for r in all_results if r["works"]]
    not_found = [r for r in all_results if r["status"] == 404]
    errors = [r for r in all_results if r["status"] >= 500]

    print(f"\n  Total probed:  {len(all_results)}")
    print(f"  Reachable:     {len(working)} (route exists, not 404)")
    print(f"  Not found:     {len(not_found)} (404)")
    print(f"  Server error:  {len(errors)} (5xx)")

    if working:
        print(f"\n  REACHABLE ENDPOINTS (new discoveries):")
        for r in working:
            print(f"    {r['method']:6} {r['original_path']:55} → {r['status']} - {r['description']}")

    if not_found:
        print(f"\n  NOT FOUND (404):")
        for r in not_found:
            print(f"    {r['method']:6} {r['original_path']:55} - {r['description']}")

    # Save results
    os.makedirs("reports", exist_ok=True)
    with open("reports/undocumented-probe-results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to reports/undocumented-probe-results.json")


if __name__ == "__main__":
    main()
