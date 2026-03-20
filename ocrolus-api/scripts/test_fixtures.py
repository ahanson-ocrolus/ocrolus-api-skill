"""
Ocrolus API Test Fixtures
=========================

Test helpers and fixtures for validating Ocrolus API integrations.
Covers uploads, Plaid imports, income workflows, Detect, and webhooks.

Requirements:
    pip install requests pytest

Usage:
    # Run all tests against a live Ocrolus environment:
    export OCROLUS_CLIENT_ID="your_id"
    export OCROLUS_CLIENT_SECRET="your_secret"
    pytest test_fixtures.py -v

    # Or import fixtures into your own test suite:
    from test_fixtures import create_test_book, SAMPLE_PLAID_ASSET_REPORT
"""

import io
import json
import os
import tempfile
import time
from typing import Optional

import pytest

# Import the SDK client
import sys
sys.path.insert(0, os.path.dirname(__file__))
from ocrolus_client import OcrolusClient, OcrolusError, verify_webhook_signature


# =============================================================================
# SAMPLE DATA / FIXTURES
# =============================================================================

SAMPLE_PLAID_ASSET_REPORT = {
    "report": {
        "asset_report_id": "test-report-001",
        "client_report_id": "client-001",
        "date_generated": "2025-12-01T00:00:00Z",
        "days_requested": 90,
        "items": [
            {
                "accounts": [
                    {
                        "account_id": "acct-001",
                        "balances": {
                            "available": 5000.00,
                            "current": 5250.00,
                        },
                        "name": "Checking Account",
                        "official_name": "Personal Checking",
                        "type": "depository",
                        "subtype": "checking",
                        "historical_balances": [],
                        "transactions": [
                            {
                                "amount": -2500.00,
                                "date": "2025-11-15",
                                "name": "PAYROLL DEPOSIT",
                                "transaction_id": "txn-001",
                            },
                            {
                                "amount": 50.00,
                                "date": "2025-11-16",
                                "name": "GROCERY STORE",
                                "transaction_id": "txn-002",
                            },
                        ],
                    }
                ],
                "institution_id": "ins_001",
                "institution_name": "Test Bank",
            }
        ],
    }
}

SAMPLE_INCOME_GUIDELINE = {
    "guideline_type": "wage_earner",
    "pay_frequency": "biweekly",
    "months_of_history": 12,
}

SAMPLE_INCOME_ENTITY_CONFIG = {
    "entity_type": "wage_earner",
    "employer_name": "Test Corp",
    "employee_name": "Jane Doe",
}

SAMPLE_TAG_CONFIG = {
    "name": "test-rent-payments",
    "description": "Rent and lease payments for testing",
    "color": "#FF6B6B",
    "include_terms": ["rent", "lease", "apartment"],
    "exclude_terms": ["insurance"],
}

# NOTE: The field name "event_type" and value "document.verification_complete"
# are UNVALIDATED placeholders. After running validate_endpoints.py --webhooks,
# replace EVENT_TYPE_FIELD with the actual field name your tenant uses,
# and replace event values with canonical names from the validation output.
EVENT_TYPE_FIELD = os.environ.get("OCROLUS_EVENT_TYPE_FIELD", "event_type")

SAMPLE_WEBHOOK_EVENT = {
    EVENT_TYPE_FIELD: "document.verification_complete",  # REPLACE with validated name
    "book_pk": 12345,
    "book_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "doc_uuid": "d1e2f3a4-b5c6-7890-1234-567890abcdef",
    "timestamp": "2025-12-01T12:00:00Z",
}


def create_minimal_pdf() -> bytes:
    """Create a minimal valid PDF for upload testing."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n206\n%%EOF"
    )


def create_minimal_image() -> bytes:
    """Create a minimal valid PNG for image upload testing."""
    # 1x1 white pixel PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def client():
    """Create an authenticated OcrolusClient."""
    cid = os.environ.get("OCROLUS_CLIENT_ID")
    csecret = os.environ.get("OCROLUS_CLIENT_SECRET")
    if not cid or not csecret:
        pytest.skip("OCROLUS_CLIENT_ID and OCROLUS_CLIENT_SECRET required")
    return OcrolusClient(client_id=cid, client_secret=csecret)


@pytest.fixture
def test_book(client):
    """Create a test book and clean up after."""
    book = client.create_book(f"test-fixture-{int(time.time())}")
    yield book
    try:
        client.delete_book(book["pk"])
    except OcrolusError:
        pass  # Already deleted or doesn't exist


@pytest.fixture
def pdf_file():
    """Create a temporary PDF file."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(create_minimal_pdf())
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def image_file():
    """Create a temporary PNG file."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(create_minimal_image())
        f.flush()
        yield f.name
    os.unlink(f.name)


# =============================================================================
# TEST: AUTHENTICATION
# =============================================================================

class TestAuthentication:
    def test_token_acquisition(self, client):
        """Verify OAuth token can be obtained."""
        token = client._get_token()
        assert token is not None
        assert len(token) > 0

    def test_token_caching(self, client):
        """Verify token is cached and reused."""
        token1 = client._get_token()
        token2 = client._get_token()
        assert token1 == token2

    def test_invalid_credentials(self):
        """Verify bad credentials raise an error."""
        bad_client = OcrolusClient(client_id="invalid", client_secret="invalid")
        with pytest.raises(OcrolusError):
            bad_client._get_token()


# =============================================================================
# TEST: BOOK OPERATIONS
# =============================================================================

class TestBookOperations:
    def test_create_book(self, client):
        """Create a book and verify response has pk and uuid."""
        book = client.create_book(f"pytest-book-{int(time.time())}")
        assert "pk" in book
        assert "uuid" in book
        # Cleanup
        client.delete_book(book["pk"])

    def test_list_books(self, client):
        """Verify books can be listed."""
        result = client.list_books()
        assert isinstance(result, dict)

    def test_book_status(self, client, test_book):
        """Verify book status is retrievable."""
        status = client.get_book_status(test_book["pk"])
        assert isinstance(status, dict)


# =============================================================================
# TEST: DOCUMENT UPLOAD
# =============================================================================

class TestDocumentUpload:
    def test_upload_pdf(self, client, test_book, pdf_file):
        """Upload a PDF and verify response."""
        result = client.upload_pdf(test_book["pk"], pdf_file)
        assert isinstance(result, dict)

    def test_upload_pdf_from_bytes(self, client, test_book):
        """Upload a PDF from in-memory bytes."""
        pdf_bytes = create_minimal_pdf()
        result = client.upload_pdf(test_book["pk"], io.BytesIO(pdf_bytes))
        assert isinstance(result, dict)

    def test_upload_mixed_pdf(self, client, test_book, pdf_file):
        """Upload a mixed document PDF."""
        result = client.upload_mixed_pdf(test_book["pk"], pdf_file)
        assert isinstance(result, dict)

    def test_upload_image(self, client, test_book, image_file):
        """Upload an image."""
        result = client.upload_image(test_book["pk"], image_file)
        assert isinstance(result, dict)


# =============================================================================
# TEST: PLAID INTEGRATION
# =============================================================================

class TestPlaidIntegration:
    def test_upload_plaid_json(self, client, test_book):
        """Upload Plaid aggregator JSON."""
        try:
            result = client.upload_plaid_json(test_book["pk"], SAMPLE_PLAID_ASSET_REPORT)
            assert isinstance(result, dict)
        except OcrolusError as e:
            if e.status_code == 400:
                pytest.skip("Plaid JSON format may not match current API schema")
            raise

    @pytest.mark.skip(reason="Requires production Plaid audit copy token")
    def test_import_plaid_asset_report(self, client):
        """Import Plaid Asset Report via audit copy token."""
        token = os.environ.get("PLAID_AUDIT_COPY_TOKEN")
        if not token:
            pytest.skip("PLAID_AUDIT_COPY_TOKEN required")
        result = client.import_plaid_asset_report(token)
        assert isinstance(result, dict)


# =============================================================================
# TEST: INCOME WORKFLOWS
# =============================================================================

class TestIncomeWorkflows:
    @pytest.mark.skip(reason="Requires a book with processed income documents")
    def test_income_calculation_workflow(self, client):
        """
        Full income calculation workflow:
        1. Configure income entity
        2. Save income guideline
        3. Get income calculations
        4. Get income summary
        """
        book_uuid = os.environ.get("TEST_INCOME_BOOK_UUID")
        if not book_uuid:
            pytest.skip("TEST_INCOME_BOOK_UUID required")

        # Step 1: Configure entity
        entity_result = client.configure_income_entity(book_uuid, SAMPLE_INCOME_ENTITY_CONFIG)
        assert isinstance(entity_result, dict)

        # Step 2: Save guideline
        guideline_result = client.save_income_guideline(book_uuid, SAMPLE_INCOME_GUIDELINE)
        assert isinstance(guideline_result, dict)

        # Step 3: Get calculations
        calc_result = client.get_income_calculations(book_uuid)
        assert isinstance(calc_result, dict)

        # Step 4: Get summary
        summary_result = client.get_income_summary(book_uuid)
        assert isinstance(summary_result, dict)

    @pytest.mark.skip(reason="Requires Fannie Mae-eligible book")
    def test_fannie_mae_workflow(self, client):
        """Fannie Mae self-employed income: must call SE endpoint FIRST."""
        book_uuid = os.environ.get("TEST_SE_INCOME_BOOK_UUID")
        if not book_uuid:
            pytest.skip("TEST_SE_INCOME_BOOK_UUID required")

        # Step 1: Self-employed calculation (must be first)
        se_result = client.calculate_self_employed_income(book_uuid, {})
        assert isinstance(se_result, dict)

        # Step 2: General income calculation
        income_result = client.get_income_calculations(book_uuid)
        assert isinstance(income_result, dict)


# =============================================================================
# TEST: DETECT / FRAUD
# =============================================================================

class TestDetect:
    @pytest.mark.skip(reason="Requires book with completed Detect processing")
    def test_book_fraud_signals(self, client):
        """Get book-level fraud signals with authenticity scores."""
        book_uuid = os.environ.get("TEST_DETECT_BOOK_UUID")
        if not book_uuid:
            pytest.skip("TEST_DETECT_BOOK_UUID required")

        signals = client.get_book_fraud_signals(book_uuid)
        assert isinstance(signals, dict)
        # Verify authenticity score structure is present
        if "documents" in signals:
            for doc in signals["documents"]:
                if "authenticity_score" in doc:
                    score = doc["authenticity_score"]
                    assert 0 <= score <= 100, f"Score {score} out of range"


# =============================================================================
# TEST: TAG MANAGEMENT
# =============================================================================

class TestTagManagement:
    def test_list_tags(self, client):
        """List all tags."""
        result = client.list_tags()
        assert isinstance(result, dict)

    def test_list_system_tags(self, client):
        """List only system tags."""
        result = client.list_tags(is_system_tag=True)
        assert isinstance(result, dict)

    def test_tag_crud(self, client):
        """Create, read, update, delete a custom tag."""
        # Create
        tag = client.create_tag(**SAMPLE_TAG_CONFIG)
        assert "uuid" in tag or "tag_uuid" in tag
        tag_uuid = tag.get("uuid") or tag.get("tag_uuid")

        try:
            # Read
            fetched = client.get_tag(tag_uuid)
            assert fetched is not None

            # Update
            updated = client.modify_tag(tag_uuid, {"description": "Updated description"})
            assert isinstance(updated, dict)
        finally:
            # Delete
            client.delete_tag(tag_uuid)


# =============================================================================
# TEST: WEBHOOK SIGNATURE VERIFICATION
# =============================================================================

class TestWebhookVerification:
    """These tests run locally without API access."""

    def test_valid_signature(self):
        """Verify a correctly signed webhook passes verification."""
        import hashlib
        import hmac as hmac_mod

        secret = "test-secret-1234567890"
        body = json.dumps(SAMPLE_WEBHOOK_EVENT).encode()
        timestamp = "1701432000"
        request_id = "req-abc-123"

        signed_msg = f"{timestamp}.{request_id}.".encode() + body
        signature = hmac_mod.new(secret.encode(), signed_msg, hashlib.sha256).hexdigest()

        headers = {
            "Webhook-Timestamp": timestamp,
            "Webhook-Request-Id": request_id,
            "Webhook-Signature": signature,
        }

        assert verify_webhook_signature(headers, body, secret) is True

    def test_invalid_signature(self):
        """Verify a tampered webhook fails verification."""
        headers = {
            "Webhook-Timestamp": "1701432000",
            "Webhook-Request-Id": "req-abc-123",
            "Webhook-Signature": "invalid-signature",
        }
        body = json.dumps(SAMPLE_WEBHOOK_EVENT).encode()
        assert verify_webhook_signature(headers, body, "test-secret") is False

    def test_missing_headers(self):
        """Verify missing headers fail verification."""
        assert verify_webhook_signature({}, b"{}", "secret") is False

    def test_tampered_body(self):
        """Verify modified body fails verification."""
        import hashlib
        import hmac as hmac_mod

        secret = "test-secret-1234567890"
        original_body = json.dumps(SAMPLE_WEBHOOK_EVENT).encode()
        timestamp = "1701432000"
        request_id = "req-abc-123"

        signed_msg = f"{timestamp}.{request_id}.".encode() + original_body
        signature = hmac_mod.new(secret.encode(), signed_msg, hashlib.sha256).hexdigest()

        # Tamper with the body
        tampered_body = json.dumps({**SAMPLE_WEBHOOK_EVENT, "book_pk": 99999}).encode()

        headers = {
            "Webhook-Timestamp": timestamp,
            "Webhook-Request-Id": request_id,
            "Webhook-Signature": signature,
        }

        assert verify_webhook_signature(headers, tampered_body, secret) is False


# =============================================================================
# TEST: ENCORE / BOOK COPY
# =============================================================================

class TestEncore:
    def test_list_copy_jobs(self, client):
        """List book copy jobs."""
        try:
            result = client.list_book_copy_jobs()
            assert isinstance(result, dict)
        except OcrolusError as e:
            if e.status_code == 403:
                pytest.skip("Encore not enabled for this account")
            raise

    def test_get_copy_settings(self, client):
        """Get book copy settings/allow list."""
        try:
            result = client.get_book_copy_settings()
            assert isinstance(result, dict)
        except OcrolusError as e:
            if e.status_code in (403, 404):
                pytest.skip("Encore not enabled for this account")
            raise
