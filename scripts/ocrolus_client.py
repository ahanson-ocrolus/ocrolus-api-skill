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

    def create_book(self, name: str, book_class: Optional[str] = None,
                     book_type: Optional[str] = None,
                     is_public: Optional[bool] = None,
                     xid: Optional[str] = None,
                     **kwargs) -> dict:
        """Create a new Book.

        Public docs path: POST /v1/book/add. Returns the envelope
        ``{ "status": 200, "response": { "pk": int, "uuid": str, ... } }``.

        Set ``book_class`` at creation — it cannot be changed afterwards. Map the
        user's natural-language request:
          - "instant" / "instantly" / "machine only" / "no human review"
            -> ``book_class="INSTANT"``
          - "complete" / "HITL" / "human in the loop" / "human verification"
            -> ``book_class="COMPLETE"`` (also the default when omitted)

        Only ``INSTANT`` and ``COMPLETE`` are valid for ``book_class``. The API
        rejects everything else with ``400 Invalid dictionary value``.

        ``book_type`` is a separate field that only accepts ``DEFAULT`` or
        ``INSTANT_ML``; omit it for normal usage.

        Note: the endpoint is ``/v1/book/add`` — ``/v1/book/create`` returns 404.
        """
        body: dict[str, Any] = {"name": name}
        if book_class is not None:
            body["book_class"] = book_class
        if book_type is not None:
            body["book_type"] = book_type
        if is_public is not None:
            body["is_public"] = is_public
        if xid is not None:
            body["xid"] = xid
        body.update(kwargs)
        return self._post("/v1/book/add", json=body)

    def get_book(self, book_pk: Optional[int] = None, book_uuid: Optional[str] = None) -> dict:
        """Get Book information. Public docs path: GET /v1/book/info?pk= or ?book_uuid=."""
        params: dict[str, Any] = {}
        if book_pk is not None:
            params["pk"] = book_pk
        if book_uuid is not None:
            params["book_uuid"] = book_uuid
        return self._get("/v1/book/info", params=params)

    def list_books(self, **params: Any) -> dict:
        """List all Books. Accepts limit, offset, order, order_by, name, search, xid."""
        return self._get("/v1/books", params=params or None)

    def get_book_status(self, book_pk: Optional[int] = None, book_uuid: Optional[str] = None) -> dict:
        """Get Book and Document processing status. GET /v1/book/status?pk= or ?book_uuid=."""
        params: dict[str, Any] = {}
        if book_pk is not None:
            params["pk"] = book_pk
        if book_uuid is not None:
            params["book_uuid"] = book_uuid
        return self._get("/v1/book/status", params=params)

    def update_book(self, book_pk: Optional[int] = None, book_uuid: Optional[str] = None, **kwargs) -> dict:
        """Update Book properties. Body accepts pk or book_uuid plus any updatable fields."""
        body: dict[str, Any] = dict(kwargs)
        if book_pk is not None:
            body["pk"] = book_pk
        if book_uuid is not None:
            body["book_uuid"] = book_uuid
        return self._post("/v1/book/update", json=body)

    def delete_book(self, book_id: Optional[int] = None, book_uuid: Optional[str] = None) -> dict:
        """Delete a Book. Public docs: POST /v1/book/remove with book_id or book_uuid."""
        body: dict[str, Any] = {}
        if book_id is not None:
            body["book_id"] = book_id
        if book_uuid is not None:
            body["book_uuid"] = book_uuid
        return self._post("/v1/book/remove", json=body)

    def get_book_from_loan(self, loan_id: Optional[str] = None, loan_number: Optional[str] = None) -> dict:
        """Look up a Book from an Encompass loan via LOS-Connect.

        Public docs path: GET /v2/los-connect/encompass/book?loan_id= or ?loan_number=.
        """
        params: dict[str, Any] = {}
        if loan_id is not None:
            params["loan_id"] = loan_id
        if loan_number is not None:
            params["loan_number"] = loan_number
        return self._get("/v2/los-connect/encompass/book", params=params)

    def get_loan_from_book(self, book_uuid: str) -> dict:
        """Get loan details from a Book via LOS-Connect.

        Public docs path: GET /v2/los-connect/book/{book_uuid}/loans.
        """
        return self._get(f"/v2/los-connect/book/{book_uuid}/loans")

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

    def upload_paystub_pdf(self, book_uuid: str, file: Union[str, Path, BinaryIO]) -> dict:
        """Upload a pay stub PDF.

        Public docs path: POST /v2/book/{book_uuid}/document/paystub.
        """
        return self._upload(f"/v2/book/{book_uuid}/document/paystub", file)

    def upload_image(self, book_pk: int, file: Union[str, Path, BinaryIO], return_image_pk: Optional[bool] = None) -> dict:
        """Upload an image to a Book.

        Public docs body fields: pk or book_uuid, upload (file), optional return_image_pk.
        """
        data: dict[str, str] = {"pk": str(book_pk)}
        if return_image_pk is not None:
            data["return_image_pk"] = "true" if return_image_pk else "false"
        return self._upload("/v1/book/upload/image", file, data=data)

    def finalize_image_group(self, book_pk: int, form_type: Optional[str] = None) -> dict:
        """Mark an image group complete.

        Public docs path: POST /v1/book/upload/image/done.
        """
        body: dict[str, Any] = {"pk": book_pk}
        if form_type:
            body["form_type"] = form_type
        return self._post("/v1/book/upload/image/done", json=body)

    def upload_aggregator_json(self, book_pk: int, file: Union[str, Path, BinaryIO],
                                upload_intent: Optional[str] = None,
                                aggregate_source: Optional[str] = None) -> dict:
        """Upload Plaid / MX / Yodlee aggregator JSON to a Book.

        Public docs path: POST /v1/book/upload/json (multipart file upload).
        """
        params: dict[str, str] = {}
        if upload_intent:
            params["upload_intent"] = upload_intent
        if aggregate_source:
            params["aggregate_source"] = aggregate_source
        if isinstance(file, (str, Path)):
            with open(file, "rb") as f:
                return self.upload_aggregator_json(book_pk, f, upload_intent, aggregate_source)
        resp = self._session.post(
            f"{self.BASE_URL}/v1/book/upload/json",
            headers=self._headers(),
            params=params or None,
            data={"pk": str(book_pk)},
            files={"upload": file},
            timeout=120,
        )
        self._raise_for_status(resp)
        return resp.json()

    def import_plaid_asset_report(self, book_pk: int, audit_copy_token: str,
                                   form_type: Optional[str] = None,
                                   doc_name: Optional[str] = None) -> dict:
        """Import Plaid Asset Report via audit copy token (production only)."""
        body: dict[str, Any] = {"pk": book_pk, "audit_copy_token": audit_copy_token}
        if form_type:
            body["form_type"] = form_type
        if doc_name:
            body["doc_name"] = doc_name
        return self._post("/v1/book/import/plaid/asset", json=body)

    def cancel_document(self, doc_uuid: Optional[str] = None, doc_pk: Optional[int] = None,
                         accept_charges: Optional[bool] = None) -> dict:
        """Cancel document verification.

        Public docs path: POST /v1/document/cancel with body {doc_pk | doc_uuid}.
        """
        body: dict[str, Any] = {}
        if doc_uuid is not None:
            body["doc_uuid"] = doc_uuid
        if doc_pk is not None:
            body["doc_pk"] = doc_pk
        if accept_charges is not None:
            body["accept_charges"] = accept_charges
        return self._post("/v1/document/cancel", json=body)

    def delete_document(self, doc_uuid: Optional[str] = None, doc_id: Optional[int] = None) -> dict:
        """Delete a document.

        Public docs path: POST /v1/document/remove with body {doc_id | doc_uuid}.
        """
        body: dict[str, Any] = {}
        if doc_uuid is not None:
            body["doc_uuid"] = doc_uuid
        if doc_id is not None:
            body["doc_id"] = doc_id
        return self._post("/v1/document/remove", json=body)

    def download_document(self, doc_uuid: str) -> bytes:
        """Download a document file.

        Public docs path: GET /v2/document/download?doc_uuid=.
        """
        return self._get_binary("/v2/document/download", params={"doc_uuid": doc_uuid})

    def upgrade_document(self, upgrade_type: str, doc_uuid: Optional[str] = None,
                          doc_pk: Optional[int] = None) -> dict:
        """Upgrade a document's processing type.

        Public docs path: POST /v1/document/upgrade with body {doc_pk | doc_uuid, upgrade_type}.
        """
        body: dict[str, Any] = {"upgrade_type": upgrade_type}
        if doc_uuid is not None:
            body["doc_uuid"] = doc_uuid
        if doc_pk is not None:
            body["doc_pk"] = doc_pk
        return self._post("/v1/document/upgrade", json=body)

    def upgrade_mixed_document(self, upgrade_type: str, mixed_doc_uuid: Optional[str] = None,
                                mixed_doc_pk: Optional[int] = None) -> dict:
        """Upgrade a mixed document's processing type.

        Public docs path: POST /v1/document/mixed/upgrade.
        """
        body: dict[str, Any] = {"upgrade_type": upgrade_type}
        if mixed_doc_uuid is not None:
            body["mixed_doc_uuid"] = mixed_doc_uuid
        if mixed_doc_pk is not None:
            body["mixed_doc_pk"] = mixed_doc_pk
        return self._post("/v1/document/mixed/upgrade", json=body)

    def get_mixed_document_status(self, mixed_doc_uuid: Optional[str] = None,
                                    doc_uuid: Optional[str] = None,
                                    pk: Optional[int] = None) -> dict:
        """Get processing status of a mixed document.

        Public docs path: GET /v1/document/mixed/status with one of pk, doc_uuid, mixed_doc_uuid.
        """
        params: dict[str, Any] = {}
        if mixed_doc_uuid is not None:
            params["mixed_doc_uuid"] = mixed_doc_uuid
        if doc_uuid is not None:
            params["doc_uuid"] = doc_uuid
        if pk is not None:
            params["pk"] = pk
        return self._get("/v1/document/mixed/status", params=params)

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
    # DATA EXTRACTION -- CAPTURE
    # =========================================================================

    def get_book_forms(self, book_pk: Optional[int] = None, book_uuid: Optional[str] = None) -> dict:
        """Get all extracted form data for a Book.

        Public docs path: GET /v1/book/forms?pk= or ?book_uuid=.
        """
        params: dict[str, Any] = {}
        if book_pk is not None:
            params["pk"] = book_pk
        if book_uuid is not None:
            params["book_uuid"] = book_uuid
        return self._get("/v1/book/forms", params=params)

    def get_book_paystubs(self, book_uuid: str) -> dict:
        """Get all extracted pay stub data for a Book.

        Public docs path: GET /v2/book/{book_uuid}/paystub.
        """
        return self._get(f"/v2/book/{book_uuid}/paystub")

    def get_document_forms(self, doc_uuid: Optional[str] = None, doc_pk: Optional[int] = None,
                            include_all: Optional[bool] = None,
                            include_bboxes: Optional[bool] = None) -> dict:
        """Get extracted form fields for a specific document.

        Public docs path: GET /v1/document/forms/fields?doc_uuid= or ?pk=.
        """
        params: dict[str, Any] = {}
        if doc_uuid is not None:
            params["doc_uuid"] = doc_uuid
        if doc_pk is not None:
            params["pk"] = doc_pk
        if include_all is not None:
            params["include_all"] = include_all
        if include_bboxes is not None:
            params["include_bboxes"] = include_bboxes
        return self._get("/v1/document/forms/fields", params=params)

    def get_document_paystubs(self, doc_uuid: str, include_page_doc_info: Optional[bool] = None) -> dict:
        """Get extracted pay stub data for a specific document.

        Public docs path: GET /v2/document/{doc_uuid}/paystub.
        """
        params: dict[str, Any] = {}
        if include_page_doc_info is not None:
            params["include_page_doc_info"] = include_page_doc_info
        return self._get(f"/v2/document/{doc_uuid}/paystub", params=params or None)

    def get_form(self, form_uuid: Optional[str] = None, form_pk: Optional[int] = None) -> dict:
        """Get form data.

        Public docs path: GET /v1/form?uuid= or ?pk=.
        """
        params: dict[str, Any] = {}
        if form_uuid is not None:
            params["uuid"] = form_uuid
        if form_pk is not None:
            params["pk"] = form_pk
        return self._get("/v1/form", params=params)

    # Back-compat alias for the prior method name.
    get_form_fields = get_form

    def get_paystub(self, paystub_uuid: str) -> dict:
        """Get data for a specific pay stub.

        Public docs path: GET /v2/paystub/{paystub_uuid}.
        """
        return self._get(f"/v2/paystub/{paystub_uuid}")

    def get_book_transactions(self, book_pk: Optional[int] = None, book_uuid: Optional[str] = None,
                                uploaded_doc_pk: Optional[int] = None,
                                uploaded_doc_uuid: Optional[str] = None,
                                only_tagged: Optional[bool] = None,
                                distinct_fields: Optional[str] = None) -> dict:
        """Get transactions for a Book.

        Public docs path: GET /v1/transaction?book_pk= or ?book_uuid=.
        """
        params: dict[str, Any] = {}
        if book_pk is not None:
            params["book_pk"] = book_pk
        if book_uuid is not None:
            params["book_uuid"] = book_uuid
        if uploaded_doc_pk is not None:
            params["uploaded_doc_pk"] = uploaded_doc_pk
        if uploaded_doc_uuid is not None:
            params["uploaded_doc_uuid"] = uploaded_doc_uuid
        if only_tagged is not None:
            params["only_tagged"] = only_tagged
        if distinct_fields is not None:
            params["distinct_fields"] = distinct_fields
        return self._get("/v1/transaction", params=params)

    # =========================================================================
    # FRAUD DETECTION -- DETECT (v2, uses book_uuid)
    # =========================================================================

    def get_book_fraud_signals(self, book_uuid: str) -> dict:
        """
        Get book-level fraud signals including authenticity scores and reason codes.
        Returns signals for all documents in the book.
        """
        return self._get(f"/v2/detect/book/{book_uuid}/signals")

    def get_document_fraud_signals(self, uploaded_doc_uuid: str,
                                    exclude_dashboard_url: Optional[bool] = None) -> dict:
        """Get document-level fraud signals (authenticity score + reason codes).

        Public docs path: GET /v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals.
        Note: path segment is `uploaded_doc`, not `document`.
        """
        params: dict[str, Any] = {}
        if exclude_dashboard_url is not None:
            params["exclude_dashboard_url"] = exclude_dashboard_url
        return self._get(f"/v2/detect/uploaded_doc/{uploaded_doc_uuid}/signals", params=params or None)

    def get_suspicious_activity_flags(self, book_uuid: str) -> dict:
        """Legacy suspicious-activity flag endpoint (still in the public docs reference).

        Public docs path: GET /v1/book/{book_uuid}/suspicious-activity-flags.
        """
        return self._get(f"/v1/book/{book_uuid}/suspicious-activity-flags")

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

    def get_cashflow_features(self, book_uuid: str) -> dict:
        """Get pre-engineered cash flow analytics features.

        Public docs path: GET /v2/book/{book_uuid}/cash_flow_features.
        """
        return self._get(f"/v2/book/{book_uuid}/cash_flow_features")

    def get_enriched_transactions(self, book_uuid: str, offset: Optional[int] = None,
                                    limit: Optional[int] = None,
                                    include_pending_plaid_transactions: Optional[bool] = None) -> dict:
        """Get enriched transactions with categories and tags.

        Public docs path: GET /v2/book/{book_uuid}/enriched_txns.
        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if include_pending_plaid_transactions is not None:
            params["include_pending_plaid_transactions"] = include_pending_plaid_transactions
        return self._get(f"/v2/book/{book_uuid}/enriched_txns", params=params or None)

    def get_risk_score(self, book_uuid: str) -> dict:
        """Get cash flow risk score (probability of default).

        Public docs path: GET /v2/book/{book_uuid}/cash_flow_risk_score.
        """
        return self._get(f"/v2/book/{book_uuid}/cash_flow_risk_score")

    def get_analytics_excel(self, book_uuid: str) -> bytes:
        """Download SMB analytics as Excel file.

        Public docs path: GET /v2/book/{book_uuid}/lender_analytics/xlsx.
        """
        return self._get_binary(f"/v2/book/{book_uuid}/lender_analytics/xlsx")

    # =========================================================================
    # INCOME CALCULATIONS (v2, uses book_uuid)
    # =========================================================================

    def get_income_calculations(self, book_uuid: str, guideline: Optional[str] = None) -> dict:
        """Get income calculations based on configured guidelines.

        Public docs path: GET /v2/book/{book_uuid}/income-calculations (hyphenated).
        Guideline: FANNIE_MAE | FREDDIE_MAC | FHA | VA | USDA.
        """
        params = {"guideline": guideline} if guideline else None
        return self._get(f"/v2/book/{book_uuid}/income-calculations", params=params)

    def get_income_summary(self, book_uuid: str, guideline: Optional[str] = None) -> dict:
        """Get income summary.

        Public docs path: GET /v2/book/{book_uuid}/income/summary (slash, not hyphen).
        """
        params = {"guideline": guideline} if guideline else None
        return self._get(f"/v2/book/{book_uuid}/income/summary", params=params)

    def configure_income_entity(self, book_uuid: str, config: dict) -> dict:
        """Configure income entity settings.

        Public docs path: POST /v2/book/{book_uuid}/income/entity_config (slash).
        Body: entity_details, borrower_details, xid, employment_start_date, income_type.
        """
        return self._post(f"/v2/book/{book_uuid}/income/entity_config", json=config)

    def save_income_guideline(self, book_uuid: str, guideline: Optional[str] = None) -> dict:
        """Save income calculation guideline.

        Public docs path: PUT /v2/book/{book_uuid}/income-guideline (hyphen).
        """
        params = {"guideline": guideline} if guideline else None
        return self._put(f"/v2/book/{book_uuid}/income-guideline", params=params)

    def calculate_self_employed_income(self, book_uuid: str, params: dict) -> dict:
        """Calculate Fannie Mae self-employed income.

        Public docs path: POST /v2/book/{book_uuid}/income/self-employed/calculate.
        Body: borrower_uuid, business_uuid, income_guideline, meta_info.
        """
        return self._post(f"/v2/book/{book_uuid}/income/self-employed/calculate", json=params)

    def get_bsic(self, book_uuid: str) -> dict:
        """Get Bank Statement Income Calculator results.

        Public docs path: GET /v2/book/{book_uuid}/income/bank-statement-v2.
        """
        return self._get(f"/v2/book/{book_uuid}/income/bank-statement-v2")

    def get_bsic_excel(self, book_uuid: str) -> bytes:
        """Get BSIC results as Excel.

        Public docs path: GET /v2/book/{book_uuid}/income/bank-statement-v2/xlsx
        (separate endpoint — not an Accept header on the JSON endpoint).
        """
        return self._get_binary(f"/v2/book/{book_uuid}/income/bank-statement-v2/xlsx")

    # =========================================================================
    # BUSINESS HISTORY
    # =========================================================================

    def get_business_identifier(self, book_uuid: str) -> dict:
        """Get the business identifier for a Book.

        Public docs path: GET /v2/book/{book_uuid}/business.
        """
        return self._get(f"/v2/book/{book_uuid}/business")

    def get_business_overview(self, business_id: str) -> dict:
        """Get business overview.

        Public docs path: GET /v1/businesses/{business_id}.
        """
        return self._get(f"/v1/businesses/{business_id}")

    def get_business_summary(self, business_id: str, begin_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              updated_since: Optional[str] = None) -> dict:
        """Get business summary.

        Public docs path: GET /v1/businesses/{business_id}/summary.
        """
        params: dict[str, Any] = {}
        if begin_date is not None:
            params["begin_date"] = begin_date
        if end_date is not None:
            params["end_date"] = end_date
        if updated_since is not None:
            params["updated_since"] = updated_since
        return self._get(f"/v1/businesses/{business_id}/summary", params=params or None)

    def get_business_transactions(self, business_id: str, offset: Optional[int] = None,
                                    limit: Optional[int] = None,
                                    start_date: Optional[str] = None,
                                    end_date: Optional[str] = None,
                                    updated_since: Optional[str] = None) -> dict:
        """Get business transactions.

        Public docs path: GET /v1/businesses/{business_id}/transactions.
        """
        params: dict[str, Any] = {}
        for k, v in dict(offset=offset, limit=limit, start_date=start_date,
                          end_date=end_date, updated_since=updated_since).items():
            if v is not None:
                params[k] = v
        return self._get(f"/v1/businesses/{business_id}/transactions", params=params or None)

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
    #
    # Public docs use action-suffix paths for per-webhook routes:
    #   list:   GET   /v1/account/settings/webhooks  (plural)
    #   per:    *     /v1/account/settings/webhook/{webhook_uuid}/...  (singular)
    # =========================================================================

    def add_org_webhook(self, url: str, events: list, **kwargs) -> dict:
        """Add an org-level webhook.

        Public docs path: POST /v1/account/settings/webhook.
        """
        return self._post("/v1/account/settings/webhook", json={"url": url, "events": events, **kwargs})

    def list_org_webhooks(self) -> dict:
        """List all org-level webhooks.

        Public docs path: GET /v1/account/settings/webhooks.
        """
        return self._get("/v1/account/settings/webhooks")

    def get_org_webhook(self, webhook_uuid: str) -> dict:
        """Retrieve a specific org-level webhook.

        Public docs path: GET /v1/account/settings/webhook/{webhook_uuid}.
        """
        return self._get(f"/v1/account/settings/webhook/{webhook_uuid}")

    def update_org_webhook(self, webhook_uuid: str, **kwargs) -> dict:
        """Update an org-level webhook.

        Public docs path: POST /v1/account/settings/webhook/{webhook_uuid}/update.
        """
        return self._post(f"/v1/account/settings/webhook/{webhook_uuid}/update", json=kwargs)

    def delete_org_webhook(self, webhook_uuid: str) -> dict:
        """Delete an org-level webhook.

        Public docs path: DELETE /v1/account/settings/webhook/{webhook_uuid}/delete.
        """
        return self._delete(f"/v1/account/settings/webhook/{webhook_uuid}/delete")

    def list_org_webhook_events(self, webhook_uuid: str) -> dict:
        """List the events a specific org-level webhook is subscribed to.

        Public docs path: GET /v1/account/settings/webhook/{webhook_uuid}/events.
        (Per-webhook subscription list, not a global event-type catalogue.)
        """
        return self._get(f"/v1/account/settings/webhook/{webhook_uuid}/events")

    def test_org_webhook(self, webhook_uuid: str, event_uuid: Optional[str] = None) -> dict:
        """Send a test event to an org-level webhook.

        Public docs path: POST /v1/account/settings/webhook/{webhook_uuid}/test.
        """
        body: dict[str, Any] = {}
        if event_uuid is not None:
            body["event_uuid"] = event_uuid
        return self._post(f"/v1/account/settings/webhook/{webhook_uuid}/test", json=body)

    def rotate_org_webhook_secret(self, webhook_uuid: str, secret_key: str) -> dict:
        """Rotate the HMAC signing secret for an org-level webhook.

        Public docs path: POST /v1/account/settings/webhook/{webhook_uuid}/rotate-secret.
        """
        return self._post(
            f"/v1/account/settings/webhook/{webhook_uuid}/rotate-secret",
            json={"secret_key": secret_key},
        )

    # Back-compat alias for the prior method name.
    configure_org_webhook_secret = rotate_org_webhook_secret

    # =========================================================================
    # WEBHOOKS -- ACCOUNT-LEVEL (legacy)
    # =========================================================================

    def configure_account_webhook(self, webhook_endpoint: str, event: list) -> dict:
        """Configure account-level webhook.

        Public docs path: POST /v1/account/settings/update/webhook_endpoint.
        """
        return self._post(
            "/v1/account/settings/update/webhook_endpoint",
            json={"webhook_endpoint": webhook_endpoint, "event": event},
        )

    def get_account_webhook_config(self) -> dict:
        """Get account-level webhook configuration.

        Public docs path: GET /v1/account/settings/webhook_details.
        """
        return self._get("/v1/account/settings/webhook_details")

    def test_account_webhook(self) -> dict:
        """Test account-level webhook.

        Public docs path: GET /v1/account/settings/test_webhook_endpoint.
        """
        return self._get("/v1/account/settings/test_webhook_endpoint")

    def rotate_account_webhook_secret(self, secret_key: str) -> dict:
        """Rotate signing secret for account-level webhooks.

        Public docs path: POST /v1/account/settings/webhook/rotate-secret.
        """
        return self._post(
            "/v1/account/settings/webhook/rotate-secret",
            json={"secret_key": secret_key},
        )

    # Back-compat alias for the prior method name.
    configure_account_webhook_secret = rotate_account_webhook_secret

    # =========================================================================
    # HELPERS
    # =========================================================================

    def wait_for_book(self, book_pk: Optional[int] = None, book_uuid: Optional[str] = None,
                       timeout: int = 600, interval: int = 10) -> dict:
        """Poll book status until processing completes or timeout.

        Prefer webhooks for production use. Pass either book_pk or book_uuid.
        """
        start = time.time()
        while time.time() - start < timeout:
            envelope = self.get_book_status(book_pk=book_pk, book_uuid=book_uuid)
            # Public API wraps the payload in an envelope: { status, response, message, ... }
            payload = envelope.get("response") if isinstance(envelope, dict) else None
            if isinstance(payload, dict):
                book_status = payload.get("status", "") or payload.get("book_status", "")
            else:
                book_status = ""
            if book_status in ("VERIFIED", "VERIFICATION_COMPLETE", "COMPLETED", "DONE"):
                return envelope
            time.sleep(interval)
        ident = book_pk if book_pk is not None else book_uuid
        raise TimeoutError(f"Book {ident} did not complete within {timeout}s")


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
        print("Usage: python scripts/ocrolus_client.py <command> [args...]")
        print("Commands: list-books, create-book <name>, book-status <pk>, book-forms <pk>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list-books":
        print(json.dumps(client.list_books(), indent=2))
    elif cmd == "create-book" and len(sys.argv) >= 3:
        print(json.dumps(client.create_book(sys.argv[2]), indent=2))
    elif cmd == "book-status" and len(sys.argv) >= 3:
        print(json.dumps(client.get_book_status(book_pk=int(sys.argv[2])), indent=2))
    elif cmd == "book-forms" and len(sys.argv) >= 3:
        print(json.dumps(client.get_book_forms(book_pk=int(sys.argv[2])), indent=2))
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)
