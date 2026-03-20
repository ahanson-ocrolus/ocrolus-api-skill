"""
Ocrolus API Python SDK
======================

Runnable client covering all Ocrolus API endpoints.
Import and use directly in your application.

Requirements:
    pip install requests

Usage:
    from ocrolus_client import OcrolusClient

    client = OcrolusClient(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
    )
    book = client.create_book("My Application")
"""

import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

import requests


class OcrolusError(Exception):
    """Raised when the Ocrolus API returns an error."""

    def __init__(self, status_code: int, message: str, response: Optional[dict] = None):
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"[{status_code}] {message}")


class OcrolusClient:
    """
    Full-coverage Ocrolus API client.

    Endpoints are grouped by capability:
      - Authentication (automatic token management)
      - Book Operations (v1, book_pk)
      - Document Upload & Management (v1, book_pk / doc_uuid)
      - Classification -- Classify (v2, book_uuid)
      - Data Extraction -- Capture (v1, book_pk)
      - Fraud Detection -- Detect (v2, book_uuid)
      - Cash Flow Analytics (v2, book_uuid)
      - Income Calculations (v2, book_uuid)
      - Tag Management (v2, beta)
      - Encore / Book Copy (v1)
      - Webhooks (org-level and account-level)
    """

    BASE_URL = "https://api.ocrolus.com"
    AUTH_URL = "https://auth.ocrolus.com/oauth/token"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.client_id = client_id or os.environ.get("OCROLUS_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("OCROLUS_CLIENT_SECRET", "")
        if base_url:
            self.BASE_URL = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._session = requests.Session()

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def _get_token(self) -> str:
        """Obtain or refresh OAuth 2.0 Bearer token."""
        if self._token and time.time() < self._token_expiry:
            return self._token
        resp = self._session.post(
            self.AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        self._raise_for_status(resp)
        data = resp.json()
        self._token = data["access_token"]
        # Refresh at 12h (43200s) instead of waiting for 24h expiry
        self._token_expiry = time.time() + 43200
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.ok:
            return
        try:
            body = resp.json()
        except Exception:
            body = None
        raise OcrolusError(resp.status_code, resp.text[:500], body)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get(self, path: str, **kwargs) -> dict:
        resp = self._session.get(f"{self.BASE_URL}{path}", headers=self._headers(), **kwargs)
        self._raise_for_status(resp)
        return resp.json()

    def _get_binary(self, path: str, **kwargs) -> bytes:
        resp = self._session.get(f"{self.BASE_URL}{path}", headers=self._headers(), **kwargs)
        self._raise_for_status(resp)
        return resp.content

    def _post(self, path: str, **kwargs) -> dict:
        resp = self._session.post(f"{self.BASE_URL}{path}", headers=self._headers(), **kwargs)
        self._raise_for_status(resp)
        return resp.json()

    def _put(self, path: str, **kwargs) -> dict:
        resp = self._session.put(f"{self.BASE_URL}{path}", headers=self._headers(), **kwargs)
        self._raise_for_status(resp)
        return resp.json()

    def _delete(self, path: str, **kwargs) -> dict:
        resp = self._session.delete(f"{self.BASE_URL}{path}", headers=self._headers(), **kwargs)
        self._raise_for_status(resp)
        return resp.json()

    def _upload(self, path: str, file: Union[str, Path, BinaryIO], field: str = "upload", data: Optional[dict] = None) -> dict:
        """Upload a file via multipart/form-data."""
        if isinstance(file, (str, Path)):
            with open(file, "rb") as f:
                return self._upload(path, f, field, data)
        resp = self._session.post(
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            files={field: file},
            data=data or {},
        )
        self._raise_for_status(resp)
        return resp.json()

    # =========================================================================
    # BOOK OPERATIONS (v1, uses book_pk integer)
    # =========================================================================

    def create_book(self, name: str, **kwargs) -> dict:
        """Create a new Book. Returns dict with 'pk' (int) and 'uuid' (str).

        Note: The endpoint is /v1/book/add (NOT /v1/book/create which returns 404).
        The 'book_type' parameter is not accepted; books default to 'DEFAULT' type.
        """
        return self._post("/v1/book/add", json={"name": name, **kwargs})

    def get_book(self, book_pk: int) -> dict:
        """Get Book information by pk."""
        return self._get(f"/v1/book/{book_pk}")

    def list_books(self) -> dict:
        """List all Books."""
        return self._get("/v1/books")

    def get_book_status(self, book_pk: int) -> dict:
        """Get Book and Document processing status."""
        return self._get("/v1/book/status", params={"book_pk": book_pk})

    def update_book(self, book_pk: int, **kwargs) -> dict:
        """Update Book properties."""
        return self._post("/v1/book/update", json={"book_pk": book_pk, **kwargs})

    def delete_book(self, book_pk: int) -> dict:
        """Delete a Book."""
        return self._post("/v1/book/delete", json={"book_pk": book_pk})

    def get_book_from_loan(self, loan_id: str) -> dict:
        """Get Book associated with a loan ID."""
        return self._get(f"/v1/book/loan/{loan_id}")

    def get_loan_from_book(self, book_pk: int) -> dict:
        """Get loan details from a Book."""
        return self._get(f"/v1/book/{book_pk}/loan")

    # =========================================================================
    # DOCUMENT UPLOAD & MANAGEMENT (v1)
    # =========================================================================

    def upload_pdf(self, book_pk: int, file: Union[str, Path, BinaryIO], form_type: Optional[str] = None) -> dict:
        """Upload a PDF to a Book. Max 200MB.
        Note: The form data field is 'pk' (not 'book_pk') per live testing."""
        data = {"pk": str(book_pk)}
        if form_type:
            data["form_type"] = form_type
        return self._upload("/v1/book/upload", file, data=data)

    def upload_mixed_pdf(self, book_pk: int, file: Union[str, Path, BinaryIO]) -> dict:
        """Upload a mixed document PDF containing multiple document types."""
        return self._upload("/v1/book/upload/mixed", file, data={"pk": str(book_pk)})

    def upload_paystub_pdf(self, book_pk: int, file: Union[str, Path, BinaryIO]) -> dict:
        """Upload a pay stub PDF."""
        return self._upload("/v1/book/upload/paystub", file, data={"pk": str(book_pk)})

    def upload_image(self, book_pk: int, file: Union[str, Path, BinaryIO], image_group: Optional[str] = None) -> dict:
        """Upload an image to a Book."""
        data = {"pk": str(book_pk)}
        if image_group:
            data["image_group"] = image_group
        return self._upload("/v1/book/upload/image", file, data=data)

    def finalize_image_group(self, book_pk: int, image_group: str) -> dict:
        """Finalize an image group after uploading all images."""
        return self._post("/v1/book/finalize-image-group", json={"book_pk": book_pk, "image_group": image_group})

    def upload_plaid_json(self, book_pk: int, plaid_data: dict) -> dict:
        """Upload Plaid aggregator JSON to a Book."""
        return self._post(f"/v1/book/upload/plaid", json={"book_pk": book_pk, **plaid_data})

    def import_plaid_asset_report(self, audit_copy_token: str) -> dict:
        """Import Plaid Asset Report via audit copy token (production only)."""
        return self._post("/v1/book/import/plaid/asset", json={"audit_copy_token": audit_copy_token})

    def cancel_document(self, doc_uuid: str) -> dict:
        """Cancel document verification."""
        return self._post(f"/v1/document/{doc_uuid}/cancel")

    def delete_document(self, doc_uuid: str) -> dict:
        """Delete a document."""
        return self._post(f"/v1/document/{doc_uuid}/delete")

    def download_document(self, doc_uuid: str) -> bytes:
        """Download a document file."""
        return self._get_binary(f"/v1/document/{doc_uuid}/download")

    def upgrade_document(self, doc_uuid: str, target_type: Optional[str] = None) -> dict:
        """Upgrade a document's processing type."""
        body = {}
        if target_type:
            body["target_type"] = target_type
        return self._post(f"/v1/document/{doc_uuid}/upgrade", json=body)

    def upgrade_mixed_document(self, mixed_doc_id: str, target_type: Optional[str] = None) -> dict:
        """Upgrade a mixed document's processing type."""
        body = {"mixed_doc_id": mixed_doc_id}
        if target_type:
            body["target_type"] = target_type
        return self._post("/v1/document/mixed/upgrade", json=body)

    def get_mixed_document_status(self, mixed_doc_id: str) -> dict:
        """Get processing status of a mixed document."""
        return self._get("/v1/document/mixed/status", params={"mixed_doc_id": mixed_doc_id})

    # =========================================================================
    # CLASSIFICATION -- CLASSIFY (v2, uses book_uuid)
    # =========================================================================

    def get_book_classification_summary(self, book_uuid: str) -> dict:
        """Get classification summary for all documents in a Book."""
        return self._get(f"/v2/book/{book_uuid}/classification-summary")

    def get_mixed_doc_classification_summary(self, mixed_doc_uuid: str) -> dict:
        """Get classification summary for a mixed document."""
        return self._get(f"/v2/mixed-document/{mixed_doc_uuid}/classification-summary")

    def get_grouped_mixed_doc_summary(self, mixed_doc_uuid: str) -> dict:
        """Get grouped classification summary with uniqueness values."""
        return self._get(f"/v2/index/mixed-doc/{mixed_doc_uuid}/summary")

    # =========================================================================
    # DATA EXTRACTION -- CAPTURE (v1, uses book_pk)
    # =========================================================================

    def get_book_forms(self, book_pk: int) -> dict:
        """Get all extracted form data for a Book."""
        return self._get(f"/v1/book/{book_pk}/forms")

    def get_book_paystubs(self, book_pk: int) -> dict:
        """Get all extracted pay stub data for a Book."""
        return self._get(f"/v1/book/{book_pk}/paystubs")

    def get_document_forms(self, doc_uuid: str) -> dict:
        """Get extracted form data for a specific document."""
        return self._get(f"/v1/document/{doc_uuid}/forms")

    def get_document_paystubs(self, doc_uuid: str) -> dict:
        """Get extracted pay stub data for a specific document."""
        return self._get(f"/v1/document/{doc_uuid}/paystubs")

    def get_form_fields(self, form_uuid: str) -> dict:
        """Get individual field data for a form."""
        return self._get(f"/v1/form/{form_uuid}/fields")

    def get_paystub(self, paystub_uuid: str) -> dict:
        """Get data for a specific pay stub."""
        return self._get(f"/v1/paystub/{paystub_uuid}")

    def get_book_transactions(self, book_pk: int) -> dict:
        """Get all transactions for a Book."""
        return self._get(f"/v1/book/{book_pk}/transactions")

    # =========================================================================
    # FRAUD DETECTION -- DETECT (v2, uses book_uuid)
    # =========================================================================

    def get_book_fraud_signals(self, book_uuid: str) -> dict:
        """
        Get book-level fraud signals including authenticity scores and reason codes.
        Returns signals for all documents in the book.
        """
        return self._get(f"/v2/detect/book/{book_uuid}/signals")

    def get_document_fraud_signals(self, doc_uuid: str) -> dict:
        """
        Get document-level fraud signals including authenticity score and reason codes.
        """
        return self._get(f"/v2/detect/document/{doc_uuid}/signals")

    def get_fraud_visualization(self, visualization_uuid: str) -> bytes:
        """
        Get fraud signal visualization image.
        Returns binary image data (not JSON).
        Cannot be hotlinked -- must be fetched and served by your application.
        """
        return self._get_binary(f"/v2/detect/visualization/{visualization_uuid}")

    # =========================================================================
    # CASH FLOW ANALYTICS (v2, uses book_uuid)
    # =========================================================================

    def get_book_summary(self, book_uuid: str) -> dict:
        """Get cash flow analytics summary (daily balances, PII, time series)."""
        return self._get(f"/v2/book/{book_uuid}/summary")

    def get_cashflow_features(self, book_uuid: str, min_days_to_include: int = 0) -> dict:
        """
        Get pre-engineered cash flow analytics features.
        Set min_days_to_include=32 to include only fully completed months.
        """
        params = {}
        if min_days_to_include:
            params["min_days_to_include"] = min_days_to_include
        return self._get(f"/v2/book/{book_uuid}/cash_flow_features", params=params)

    def get_enriched_transactions(self, book_uuid: str) -> dict:
        """Get enriched transactions with categories and tags."""
        return self._get(f"/v2/book/{book_uuid}/enriched_txns")

    def get_risk_score(self, book_uuid: str) -> dict:
        """Get cash flow risk score (probability of default)."""
        return self._get(f"/v2/book/{book_uuid}/cash_flow_risk_score")

    def get_benchmarking(self, book_uuid: str) -> dict:
        """Get cash flow benchmarking data (Beta, NAICS4-based)."""
        return self._get(f"/v2/book/{book_uuid}/benchmarking")

    def get_analytics_excel(self, book_uuid: str) -> bytes:
        """
        Download SMB analytics as Excel file.
        Returns binary .xlsx content.
        """
        return self._get_binary(f"/v2/book/{book_uuid}/lender_analytics/xlsx")

    # =========================================================================
    # INCOME CALCULATIONS (v2, uses book_uuid)
    # =========================================================================

    def get_income_calculations(self, book_uuid: str) -> dict:
        """Get income calculations based on configured guidelines."""
        return self._get(f"/v2/book/{book_uuid}/income-calculations")

    def get_income_summary(self, book_uuid: str) -> dict:
        """Get income summary."""
        return self._get(f"/v2/book/{book_uuid}/income-summary")

    def configure_income_entity(self, book_uuid: str, config: dict) -> dict:
        """Configure income entity settings."""
        return self._post(f"/v2/book/{book_uuid}/income-entity", json=config)

    def save_income_guideline(self, book_uuid: str, guideline: dict) -> dict:
        """Save income calculation guideline."""
        return self._put(f"/v2/book/{book_uuid}/income-guideline", json=guideline)

    def calculate_self_employed_income(self, book_uuid: str, params: dict) -> dict:
        """Calculate Fannie Mae self-employed income. Call BEFORE get_income_calculations."""
        return self._post(f"/v2/book/{book_uuid}/self-employed-income", json=params)

    def get_bsic(self, book_uuid: str) -> dict:
        """Get Bank Statement Income Calculator results."""
        return self._get(f"/v2/book/{book_uuid}/bsic")

    def get_bsic_excel(self, book_uuid: str) -> bytes:
        """Get BSIC results as Excel."""
        return self._get_binary(
            f"/v2/book/{book_uuid}/bsic",
            headers={**self._headers(), "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )

    # =========================================================================
    # TAG MANAGEMENT (v2, Beta)
    # =========================================================================

    def create_tag(self, name: str, **kwargs) -> dict:
        """Create a custom transaction tag."""
        return self._post("/v2/analytics/tags", json={"name": name, **kwargs})

    def get_tag(self, tag_uuid: str) -> dict:
        """Retrieve a tag by UUID."""
        return self._get(f"/v2/analytics/tags/{tag_uuid}")

    def modify_tag(self, tag_uuid: str, updates: dict) -> dict:
        """Modify a tag."""
        return self._put(f"/v2/analytics/tags/{tag_uuid}", json=updates)

    def delete_tag(self, tag_uuid: str) -> dict:
        """Delete a custom tag (system tags cannot be deleted)."""
        return self._delete(f"/v2/analytics/tags/{tag_uuid}")

    def list_tags(self, is_system_tag: Optional[bool] = None) -> dict:
        """List all tags. Filter with is_system_tag=True/False."""
        params = {}
        if is_system_tag is not None:
            params["is_system_tag"] = str(is_system_tag).lower()
        return self._get("/v2/analytics/tags", params=params)

    def get_revenue_deduction_tags(self) -> dict:
        """Get tags excluded from Net Revenue calculation."""
        return self._get("/v2/analytics/revenue-deduction-tags")

    def update_revenue_deduction_tags(self, tag_names: list) -> dict:
        """Set revenue deduction tags (replaces full collection)."""
        return self._put("/v2/analytics/revenue-deduction-tags", json={"tag_names": tag_names})

    def override_transaction_tag(self, book_uuid: str, txn_pk: int, tag_uuids: list) -> dict:
        """Override tag assignment for a specific transaction."""
        return self._put(
            f"/v2/analytics/book/{book_uuid}/transactions",
            json={"txn_pk": txn_pk, "tag_uuids": tag_uuids},
        )

    # =========================================================================
    # ENCORE / BOOK COPY (v1)
    # =========================================================================

    def create_book_copy_jobs(self, jobs: list) -> dict:
        """Create book copy jobs (max 50 per call)."""
        return self._post("/v1/book/copy-jobs", json={"jobs": jobs})

    def list_book_copy_jobs(self, direction: str = "outbound") -> dict:
        """List book copy jobs. direction: 'outbound' or 'inbound'."""
        return self._get("/v1/book/copy-jobs", params={"direction": direction})

    def accept_book_copy_job(self, job_id: str, name: Optional[str] = None) -> dict:
        """Accept a book copy job."""
        body = {"name": name} if name else {}
        return self._post(f"/v1/book/copy-jobs/{job_id}/accept", json=body)

    def reject_book_copy_job(self, job_id: str) -> dict:
        """Reject a book copy job."""
        return self._post(f"/v1/book/copy-jobs/{job_id}/reject")

    def run_book_copy_kickouts(self) -> dict:
        """Run automated kick-outs on all AWAITING_RECIPIENT jobs."""
        return self._post("/v1/book/copy-jobs/run-kickouts")

    def get_book_copy_settings(self) -> dict:
        """Get allowed sender/recipient organizations for book copy."""
        return self._get("/v1/settings/book-copy")

    # =========================================================================
    # WEBHOOKS -- ORG-LEVEL (recommended)
    # =========================================================================

    def add_org_webhook(self, url: str, events: list, **kwargs) -> dict:
        """Add an org-level webhook."""
        return self._post("/v1/account/settings/webhook", json={"url": url, "events": events, **kwargs})

    def list_org_webhooks(self) -> dict:
        """List all org-level webhooks."""
        return self._get("/v1/account/settings/webhooks")

    def get_org_webhook(self, webhook_id: str) -> dict:
        """Retrieve a specific org-level webhook."""
        return self._get(f"/v1/account/settings/webhooks/{webhook_id}")

    def update_org_webhook(self, webhook_id: str, **kwargs) -> dict:
        """Update an org-level webhook."""
        return self._put(f"/v1/account/settings/webhooks/{webhook_id}", json=kwargs)

    def delete_org_webhook(self, webhook_id: str) -> dict:
        """Delete an org-level webhook."""
        return self._delete(f"/v1/account/settings/webhooks/{webhook_id}")

    def list_org_webhook_events(self) -> dict:
        """List available webhook event types."""
        return self._get("/v1/account/settings/webhooks/events")

    def test_org_webhook(self, webhook_id: str) -> dict:
        """Send a test event to an org-level webhook."""
        return self._post(f"/v1/account/settings/webhooks/{webhook_id}/test")

    def configure_org_webhook_secret(self, secret: str) -> dict:
        """Configure the HMAC-SHA256 signing secret for org-level webhooks."""
        return self._post("/v1/account/settings/webhooks/secret", json={"secret": secret})

    # =========================================================================
    # WEBHOOKS -- ACCOUNT-LEVEL
    # =========================================================================

    def configure_account_webhook(self, url: str, events: list, **kwargs) -> dict:
        """Configure account-level webhook."""
        return self._post("/v1/webhook/configure", json={"url": url, "events": events, **kwargs})

    def get_account_webhook_config(self) -> dict:
        """Get account-level webhook configuration."""
        return self._get("/v1/webhook/configuration")

    def test_account_webhook(self) -> dict:
        """Test account-level webhook."""
        return self._post("/v1/webhook/test")

    def configure_account_webhook_secret(self, secret: str) -> dict:
        """Configure signing secret for account-level webhooks."""
        return self._post("/v1/webhook/secret", json={"secret": secret})

    # =========================================================================
    # HELPERS
    # =========================================================================

    def wait_for_book(self, book_pk: int, timeout: int = 600, interval: int = 10) -> dict:
        """
        Poll book status until processing completes or timeout.
        Prefer webhooks for production use.
        """
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_book_status(book_pk)
            book_status = status.get("status", "")
            if book_status in ("VERIFIED", "VERIFICATION_COMPLETE", "COMPLETED", "DONE"):
                return status
            time.sleep(interval)
        raise TimeoutError(f"Book {book_pk} did not complete within {timeout}s")


# =============================================================================
# WEBHOOK SIGNATURE VERIFICATION (standalone function)
# =============================================================================

def verify_webhook_signature(
    headers: dict,
    body: bytes,
    secret: str,
) -> bool:
    """
    Verify Ocrolus webhook HMAC-SHA256 signature.

    Args:
        headers: Request headers (must contain Webhook-Signature,
                 Webhook-Timestamp, Webhook-Request-Id)
        body: Raw request body as bytes (NOT parsed JSON)
        secret: Your webhook secret (16-128 chars)

    Returns:
        True if signature is valid, False otherwise.
    """
    timestamp = headers.get("Webhook-Timestamp", "")
    request_id = headers.get("Webhook-Request-Id", "")
    received_sig = headers.get("Webhook-Signature", "")

    if not all([timestamp, request_id, received_sig]):
        return False

    signed_message = f"{timestamp}.{request_id}.".encode() + body
    expected_sig = hmac.new(
        secret.encode(),
        signed_message,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, received_sig)


# =============================================================================
# CLI ENTRYPOINT (for quick testing)
# =============================================================================

if __name__ == "__main__":
    import json
    import sys

    client = OcrolusClient()

    if len(sys.argv) < 2:
        print("Usage: python ocrolus_client.py <command> [args...]")
        print("Commands: list-books, create-book <name>, book-status <pk>, book-forms <pk>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list-books":
        print(json.dumps(client.list_books(), indent=2))
    elif cmd == "create-book" and len(sys.argv) >= 3:
        print(json.dumps(client.create_book(sys.argv[2]), indent=2))
    elif cmd == "book-status" and len(sys.argv) >= 3:
        print(json.dumps(client.get_book_status(int(sys.argv[2])), indent=2))
    elif cmd == "book-forms" and len(sys.argv) >= 3:
        print(json.dumps(client.get_book_forms(int(sys.argv[2])), indent=2))
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)
