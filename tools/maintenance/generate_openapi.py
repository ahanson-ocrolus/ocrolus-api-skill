#!/usr/bin/env python3
"""
Ocrolus API -- OpenAPI / Swagger Specification Generator
=========================================================

Generates OpenAPI 3.0.3 (YAML) and Swagger 2.0 (JSON) specs from the
Ocrolus API endpoint inventory.

Usage:
    python maintenance/generate_openapi.py
    python maintenance/generate_openapi.py --output-dir ./docs
    python maintenance/generate_openapi.py --format openapi3
    python maintenance/generate_openapi.py --format swagger2
    python maintenance/generate_openapi.py --format both
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------

# Each entry: (tag, operation_id, summary, method, path, params, request_body, response_type, deprecated, notes)
# params: list of dicts {name, in, type, format, required, description}
# request_body: dict with properties or None
# response_type: "json" | "binary" | "excel"

ENDPOINTS = [
    # ── Authentication ──
    ("Authentication", "grantToken", "Obtain OAuth 2.0 Bearer Token",
     "POST", "https://auth.ocrolus.com/oauth/token",
     [], {"grant_type": "string", "client_id": "string", "client_secret": "string"},
     "json", False,
     "OAuth 2.0 client_credentials grant. Returns JWT with 24h expiry. Refresh at 12h."),

    # ── Book Operations ──
    ("Book Operations", "createBook", "Create a new Book",
     "POST", "/v1/book/create", [],
     {"name": "string", "book_type": "string"},
     "json", False, "Returns dict with book_pk (int) and book_uuid (str)."),

    ("Book Operations", "deleteBook", "Delete a Book",
     "POST", "/v1/book/delete", [],
     {"book_pk": "integer"}, "json", False, None),

    ("Book Operations", "updateBook", "Update Book properties",
     "POST", "/v1/book/update", [],
     {"book_pk": "integer", "name": "string"}, "json", False, None),

    ("Book Operations", "getBook", "Get Book information",
     "GET", "/v1/book/{book_pk}",
     [{"name": "book_pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False, None),

    ("Book Operations", "listBooks", "List all Books",
     "GET", "/v1/books", [], None, "json", False, None),

    ("Book Operations", "getBookStatus", "Get Book processing status",
     "GET", "/v1/book/status",
     [{"name": "book_pk", "in": "query", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False,
     "Some tenants may use /v1/book/{book_pk}/status instead. Run validate_endpoints.py to confirm."),

    ("Book Operations", "getBookFromLoan", "Get Book associated with a loan",
     "GET", "/v1/book/loan/{loan_id}",
     [{"name": "loan_id", "in": "path", "type": "string", "required": True, "description": "Loan identifier"}],
     None, "json", False, None),

    ("Book Operations", "getLoanFromBook", "Get loan details from a Book",
     "GET", "/v1/book/{book_pk}/loan",
     [{"name": "book_pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False, None),

    # ── Document Upload & Management ──
    ("Document Upload", "uploadPdf", "Upload a PDF document",
     "POST", "/v1/book/upload", [],
     {"_multipart": True, "book_pk": "integer", "upload": "file", "form_type": "string"},
     "json", False, "Max file size: 200MB. form_type is optional; cannot be used for bank statements."),

    ("Document Upload", "uploadMixedPdf", "Upload a mixed document PDF",
     "POST", "/v1/book/upload/mixed", [],
     {"_multipart": True, "book_pk": "integer", "upload": "file"},
     "json", False, "Contains multiple document types in a single PDF."),

    ("Document Upload", "uploadPaystub", "Upload a pay stub PDF",
     "POST", "/v1/book/upload/paystub", [],
     {"_multipart": True, "book_pk": "integer", "upload": "file"},
     "json", False, None),

    ("Document Upload", "uploadImage", "Upload an image",
     "POST", "/v1/book/upload/image", [],
     {"_multipart": True, "book_pk": "integer", "upload": "file", "image_group": "string"},
     "json", False, None),

    ("Document Upload", "finalizeImageGroup", "Finalize an image group",
     "POST", "/v1/book/finalize-image-group", [],
     {"book_pk": "integer", "image_group": "string"},
     "json", False, None),

    ("Document Upload", "uploadPlaidJson", "Upload Plaid aggregator JSON",
     "POST", "/v1/book/upload/plaid", [],
     {"book_pk": "integer"}, "json", False, None),

    ("Document Upload", "importPlaidAsset", "Import Plaid Asset Report",
     "POST", "/v1/book/import/plaid/asset", [],
     {"audit_copy_token": "string"},
     "json", False, "Production only. Requires auditor_id: 'ocrolus'."),

    ("Document Upload", "cancelDocument", "Cancel document verification",
     "POST", "/v1/document/{doc_uuid}/cancel",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, None),

    ("Document Upload", "deleteDocument", "Delete a document",
     "POST", "/v1/document/{doc_uuid}/delete",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, None),

    ("Document Upload", "downloadDocument", "Download a document file",
     "GET", "/v1/document/{doc_uuid}/download",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "binary", False, None),

    ("Document Upload", "upgradeDocument", "Upgrade document processing type",
     "POST", "/v1/document/{doc_uuid}/upgrade",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     {"target_type": "string"}, "json", False, None),

    ("Document Upload", "upgradeMixedDocument", "Upgrade mixed document processing",
     "POST", "/v1/document/mixed/upgrade", [],
     {"mixed_doc_id": "string", "target_type": "string"}, "json", False, None),

    ("Document Upload", "getMixedDocumentStatus", "Get mixed document status",
     "GET", "/v1/document/mixed/status",
     [{"name": "mixed_doc_id", "in": "query", "type": "string", "required": True, "description": "Mixed document ID"}],
     None, "json", False, None),

    # ── Classification (v2) ──
    ("Classification", "getBookClassification", "Get book classification summary",
     "GET", "/v2/book/{book_uuid}/classification-summary",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Identifies 300+ document types with confidence scores (0-1)."),

    ("Classification", "getMixedDocClassification", "Get mixed doc classification summary",
     "GET", "/v2/mixed-document/{mixed_doc_uuid}/classification-summary",
     [{"name": "mixed_doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Mixed document UUID"}],
     None, "json", False, None),

    ("Classification", "getGroupedMixedDocSummary", "Get grouped mixed doc summary",
     "GET", "/v2/index/mixed-doc/{mixed_doc_uuid}/summary",
     [{"name": "mixed_doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Mixed document UUID"}],
     None, "json", False, "Organizes forms into logical groups with uniqueness values."),

    # ── Data Extraction / Capture (v1) ──
    ("Data Extraction", "getBookForms", "Get book form data",
     "GET", "/v1/book/{book_pk}/forms",
     [{"name": "book_pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False, None),

    ("Data Extraction", "getBookPaystubs", "Get book pay stub data",
     "GET", "/v1/book/{book_pk}/paystubs",
     [{"name": "book_pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False, None),

    ("Data Extraction", "getDocumentForms", "Get document form data",
     "GET", "/v1/document/{doc_uuid}/forms",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, None),

    ("Data Extraction", "getDocumentPaystubs", "Get document pay stub data",
     "GET", "/v1/document/{doc_uuid}/paystubs",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, None),

    ("Data Extraction", "getFormFields", "Get form field data",
     "GET", "/v1/form/{form_uuid}/fields",
     [{"name": "form_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Form UUID"}],
     None, "json", False, "Returns confidence scores per field (0-1)."),

    ("Data Extraction", "getPaystub", "Get pay stub data",
     "GET", "/v1/paystub/{paystub_uuid}",
     [{"name": "paystub_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Pay stub UUID"}],
     None, "json", False, None),

    ("Data Extraction", "getBookTransactions", "Get book transactions",
     "GET", "/v1/book/{book_pk}/transactions",
     [{"name": "book_pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False, None),

    # ── Fraud Detection / Detect (v2) ──
    ("Fraud Detection", "getBookFraudSignals", "Get book-level fraud signals",
     "GET", "/v2/detect/book/{book_uuid}/signals",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False,
     "Returns authenticity scores (0-100), reason codes, and signal types for all documents."),

    ("Fraud Detection", "getDocumentFraudSignals", "Get document-level fraud signals",
     "GET", "/v2/detect/document/{doc_uuid}/signals",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, None),

    ("Fraud Detection", "getFraudVisualization", "Get fraud signal visualization",
     "GET", "/v2/detect/visualization/{visualization_uuid}",
     [{"name": "visualization_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Visualization UUID"}],
     None, "binary", False,
     "Returns binary image with fraud signal overlays. Cannot be hotlinked."),

    ("Fraud Detection", "getSuspiciousActivityFlags", "Get suspicious activity flags (LEGACY)",
     "GET", "/v1/book/{book_uuid}/suspicious-activity-flags",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", True, "DEPRECATED. Use /v2/detect/ endpoints instead."),

    # ── Cash Flow Analytics (v2) ──
    ("Cash Flow Analytics", "getBookSummary", "Get cash flow analytics summary",
     "GET", "/v2/book/{book_uuid}/summary",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Returns daily balances, PII, and time series data."),

    ("Cash Flow Analytics", "getCashFlowFeatures", "Get cash flow features",
     "GET", "/v2/book/{book_uuid}/cash_flow_features",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"},
      {"name": "min_days_to_include", "in": "query", "type": "integer", "required": False, "description": "Min days for most recent month (default 0, use 32 for full months only)"}],
     None, "json", False, None),

    ("Cash Flow Analytics", "getEnrichedTransactions", "Get enriched transactions",
     "GET", "/v2/book/{book_uuid}/enriched_txns",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Returns transactions with categories and tags."),

    ("Cash Flow Analytics", "getRiskScore", "Get cash flow risk score",
     "GET", "/v2/book/{book_uuid}/cash_flow_risk_score",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Returns probability of default."),

    ("Cash Flow Analytics", "getBenchmarking", "Get cash flow benchmarking (Beta)",
     "GET", "/v2/book/{book_uuid}/benchmarking",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "NAICS4-based benchmarking. Beta feature."),

    ("Cash Flow Analytics", "getAnalyticsExcel", "Download SMB analytics Excel",
     "GET", "/v2/book/{book_uuid}/lender_analytics/xlsx",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "excel", False, "Returns .xlsx binary content."),

    # ── Income Calculations (v2) ──
    ("Income Calculations", "getIncomeCalculations", "Get income calculations",
     "GET", "/v2/book/{book_uuid}/income-calculations",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, None),

    ("Income Calculations", "getIncomeSummary", "Get income summary",
     "GET", "/v2/book/{book_uuid}/income-summary",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, None),

    ("Income Calculations", "configureIncomeEntity", "Configure income entity",
     "POST", "/v2/book/{book_uuid}/income-entity",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"config": "object"}, "json", False, None),

    ("Income Calculations", "saveIncomeGuideline", "Save income guideline",
     "PUT", "/v2/book/{book_uuid}/income-guideline",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"guideline": "object"}, "json", False, None),

    ("Income Calculations", "calculateSelfEmployedIncome", "Calculate Fannie Mae self-employed income",
     "POST", "/v2/book/{book_uuid}/self-employed-income",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"params": "object"}, "json", False, "Call BEFORE getIncomeCalculations."),

    ("Income Calculations", "getBsic", "Get BSIC results",
     "GET", "/v2/book/{book_uuid}/bsic",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Bank Statement Income Calculator results."),

    # ── Tag Management (v2, Beta) ──
    ("Tag Management", "createTag", "Create a custom transaction tag",
     "POST", "/v2/analytics/tags", [],
     {"name": "string"}, "json", False, None),

    ("Tag Management", "getTag", "Retrieve a tag",
     "GET", "/v2/analytics/tags/{tag_uuid}",
     [{"name": "tag_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Tag UUID"}],
     None, "json", False, None),

    ("Tag Management", "modifyTag", "Modify a tag",
     "PUT", "/v2/analytics/tags/{tag_uuid}",
     [{"name": "tag_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Tag UUID"}],
     {"name": "string"}, "json", False, None),

    ("Tag Management", "deleteTag", "Delete a tag",
     "DELETE", "/v2/analytics/tags/{tag_uuid}",
     [{"name": "tag_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Tag UUID"}],
     None, "json", False, "System tags cannot be deleted."),

    ("Tag Management", "listTags", "List all tags",
     "GET", "/v2/analytics/tags",
     [{"name": "is_system_tag", "in": "query", "type": "boolean", "required": False, "description": "Filter system vs custom tags"}],
     None, "json", False, None),

    ("Tag Management", "getRevenueDeductionTags", "Get revenue deduction tags",
     "GET", "/v2/analytics/revenue-deduction-tags", [],
     None, "json", False, None),

    ("Tag Management", "updateRevenueDeductionTags", "Update revenue deduction tags",
     "PUT", "/v2/analytics/revenue-deduction-tags", [],
     {"tag_names": "array"}, "json", False, "Replaces the full collection."),

    ("Tag Management", "overrideTransactionTag", "Override transaction tag",
     "PUT", "/v2/analytics/book/{book_uuid}/transactions",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"txn_pk": "integer", "tag_uuids": "array"}, "json", False, None),

    # ── Encore / Book Copy (v1) ──
    ("Encore / Book Copy", "createBookCopyJobs", "Create book copy jobs",
     "POST", "/v1/book/copy-jobs", [],
     {"jobs": "array"}, "json", False, "Max 50 jobs per call."),

    ("Encore / Book Copy", "listBookCopyJobs", "List book copy jobs",
     "GET", "/v1/book/copy-jobs",
     [{"name": "direction", "in": "query", "type": "string", "required": False, "description": "'outbound' or 'inbound'"}],
     None, "json", False, None),

    ("Encore / Book Copy", "acceptBookCopyJob", "Accept a book copy job",
     "POST", "/v1/book/copy-jobs/{job_id}/accept",
     [{"name": "job_id", "in": "path", "type": "string", "required": True, "description": "Copy job ID"}],
     {"name": "string"}, "json", False, None),

    ("Encore / Book Copy", "rejectBookCopyJob", "Reject a book copy job",
     "POST", "/v1/book/copy-jobs/{job_id}/reject",
     [{"name": "job_id", "in": "path", "type": "string", "required": True, "description": "Copy job ID"}],
     None, "json", False, None),

    ("Encore / Book Copy", "runBookCopyKickouts", "Run automated kick-outs",
     "POST", "/v1/book/copy-jobs/run-kickouts", [],
     None, "json", False, "Runs on all AWAITING_RECIPIENT jobs."),

    ("Encore / Book Copy", "getBookCopySettings", "Get book copy settings",
     "GET", "/v1/settings/book-copy", [],
     None, "json", False, None),

    # ── Webhooks - Org Level ──
    ("Webhooks (Org)", "addOrgWebhook", "Add org-level webhook",
     "POST", "/v1/account/settings/webhook", [],
     {"url": "string", "events": "array"}, "json", False, None),

    ("Webhooks (Org)", "listOrgWebhooks", "List org-level webhooks",
     "GET", "/v1/account/settings/webhooks", [],
     None, "json", False, None),

    ("Webhooks (Org)", "getOrgWebhook", "Retrieve org-level webhook",
     "GET", "/v1/account/settings/webhooks/{webhook_id}",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     None, "json", False, None),

    ("Webhooks (Org)", "updateOrgWebhook", "Update org-level webhook",
     "PUT", "/v1/account/settings/webhooks/{webhook_id}",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     {"url": "string", "events": "array"}, "json", False, None),

    ("Webhooks (Org)", "deleteOrgWebhook", "Delete org-level webhook",
     "DELETE", "/v1/account/settings/webhooks/{webhook_id}",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     None, "json", False, None),

    ("Webhooks (Org)", "listOrgWebhookEvents", "List webhook event types",
     "GET", "/v1/account/settings/webhooks/events", [],
     None, "json", False, None),

    ("Webhooks (Org)", "testOrgWebhook", "Test org-level webhook",
     "POST", "/v1/account/settings/webhooks/{webhook_id}/test",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     None, "json", False, None),

    ("Webhooks (Org)", "configureOrgWebhookSecret", "Configure org webhook secret",
     "POST", "/v1/account/settings/webhooks/secret", [],
     {"secret": "string"}, "json", False, "Secret must be 16-128 characters."),

    # ── Webhooks - Account Level ──
    ("Webhooks (Account)", "configureAccountWebhook", "Configure account webhook",
     "POST", "/v1/webhook/configure", [],
     {"url": "string", "events": "array"}, "json", False, None),

    ("Webhooks (Account)", "getAccountWebhookConfig", "Get account webhook config",
     "GET", "/v1/webhook/configuration", [],
     None, "json", False, None),

    ("Webhooks (Account)", "testAccountWebhook", "Test account webhook",
     "POST", "/v1/webhook/test", [],
     None, "json", False, None),

    ("Webhooks (Account)", "configureAccountWebhookSecret", "Configure account webhook secret",
     "POST", "/v1/webhook/secret", [],
     {"secret": "string"}, "json", False, None),
]


# ---------------------------------------------------------------------------
# Type mapping helpers
# ---------------------------------------------------------------------------

def _oas3_type(t: str) -> dict:
    """Map simple type string to OpenAPI 3 schema."""
    if t == "integer":
        return {"type": "integer"}
    if t == "boolean":
        return {"type": "boolean"}
    if t == "array":
        return {"type": "array", "items": {"type": "string"}}
    if t == "object":
        return {"type": "object"}
    if t == "file":
        return {"type": "string", "format": "binary"}
    return {"type": "string"}


def _swagger2_type(t: str) -> dict:
    if t == "integer":
        return {"type": "integer"}
    if t == "boolean":
        return {"type": "boolean"}
    if t == "array":
        return {"type": "array", "items": {"type": "string"}}
    if t == "object":
        return {"type": "object"}
    if t == "file":
        return {"type": "file"}
    return {"type": "string"}


# ---------------------------------------------------------------------------
# OpenAPI 3.0.3 generator
# ---------------------------------------------------------------------------

def generate_openapi3() -> dict:
    """Generate OpenAPI 3.0.3 spec as a dict."""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Ocrolus API",
            "description": (
                "Ocrolus document automation platform API. Covers Classify (document identification), "
                "Capture (data extraction), Detect (fraud detection), and Analyze (financial metrics).\n\n"
                "## Authentication\n"
                "Use OAuth 2.0 client_credentials grant to obtain a Bearer JWT token (24h expiry).\n\n"
                "## Key Conventions\n"
                "- v1 endpoints use `book_pk` (integer)\n"
                "- v2 endpoints use `book_uuid` (UUID string)\n"
                "- Never mix them -- v1 rejects UUIDs, v2 rejects PKs\n\n"
                "## Validation Note\n"
                "Some endpoint paths have conflicting documentation. Run `validate_endpoints.py` "
                "against your tenant to confirm paths before production use."
            ),
            "version": "3.0.0",
            "contact": {
                "name": "Ocrolus API Support",
                "url": "https://docs.ocrolus.com",
            },
        },
        "servers": [
            {"url": "https://api.ocrolus.com", "description": "Production API"},
            {"url": "https://auth.ocrolus.com", "description": "Authentication"},
        ],
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "OAuth 2.0 Bearer JWT token (24h expiry, refresh at 12h)",
                },
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "clientCredentials": {
                            "tokenUrl": "https://auth.ocrolus.com/oauth/token",
                            "scopes": {},
                        }
                    },
                },
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                        "status_code": {"type": "integer"},
                    },
                },
                "TokenResponse": {
                    "type": "object",
                    "properties": {
                        "access_token": {"type": "string"},
                        "token_type": {"type": "string", "example": "Bearer"},
                        "expires_in": {"type": "integer", "example": 86400},
                    },
                },
                "Book": {
                    "type": "object",
                    "properties": {
                        "pk": {"type": "integer", "description": "Book primary key (v1)"},
                        "uuid": {"type": "string", "format": "uuid", "description": "Book UUID (v2)"},
                        "name": {"type": "string"},
                        "status": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
                "FraudSignals": {
                    "type": "object",
                    "properties": {
                        "documents": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "doc_uuid": {"type": "string", "format": "uuid"},
                                    "authenticity_score": {"type": "integer", "minimum": 0, "maximum": 100},
                                    "reason_codes": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "code": {"type": "string", "example": "110-H"},
                                                "description": {"type": "string"},
                                                "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                                            },
                                        },
                                    },
                                    "signals": {"type": "array", "items": {"type": "object"}},
                                },
                            },
                        },
                    },
                },
            },
        },
        "tags": [],
        "paths": {},
    }

    # Collect unique tags
    seen_tags = set()
    tag_descriptions = {
        "Authentication": "OAuth 2.0 token management",
        "Book Operations": "Create, read, update, delete Books (v1, book_pk)",
        "Document Upload": "Upload and manage documents within Books",
        "Classification": "Document classification / Classify (v2, book_uuid)",
        "Data Extraction": "Data extraction / Capture (v1, book_pk)",
        "Fraud Detection": "Fraud detection / Detect (v2, book_uuid)",
        "Cash Flow Analytics": "Cash flow analytics / Analyze (v2, book_uuid)",
        "Income Calculations": "Income calculations (v2, book_uuid)",
        "Tag Management": "Transaction tag management (v2, Beta)",
        "Encore / Book Copy": "Book copy / Encore operations (v1)",
        "Webhooks (Org)": "Organization-level webhook management (recommended)",
        "Webhooks (Account)": "Account-level webhook management (legacy)",
    }

    for ep in ENDPOINTS:
        tag = ep[0]
        if tag not in seen_tags:
            seen_tags.add(tag)
            spec["tags"].append({"name": tag, "description": tag_descriptions.get(tag, "")})

    # Build paths
    for tag, op_id, summary, method, path, params, req_body, resp_type, deprecated, notes in ENDPOINTS:
        # Skip external auth URL for paths (document separately)
        if path.startswith("https://"):
            # Add auth as a special entry under /oauth/token
            api_path = "/oauth/token"
            spec["paths"].setdefault(api_path, {})
            operation = {
                "tags": [tag],
                "operationId": op_id,
                "summary": summary,
                "security": [],  # No auth needed to get token
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["grant_type", "client_id", "client_secret"],
                                "properties": {
                                    "grant_type": {"type": "string", "example": "client_credentials"},
                                    "client_id": {"type": "string"},
                                    "client_secret": {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Token granted",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TokenResponse"}}},
                    },
                    "401": {"description": "Invalid credentials", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            }
            if notes:
                operation["description"] = notes
            spec["paths"][api_path][method.lower()] = operation
            continue

        spec["paths"].setdefault(path, {})
        operation = {
            "tags": [tag],
            "operationId": op_id,
            "summary": summary,
            "responses": {},
        }

        if deprecated:
            operation["deprecated"] = True
        if notes:
            operation["description"] = notes

        # Parameters
        if params:
            operation["parameters"] = []
            for p in params:
                param = {
                    "name": p["name"],
                    "in": p["in"],
                    "required": p.get("required", False),
                    "description": p.get("description", ""),
                    "schema": {"type": p["type"]},
                }
                if p.get("format"):
                    param["schema"]["format"] = p["format"]
                operation["parameters"].append(param)

        # Request body
        if req_body:
            is_multipart = req_body.pop("_multipart", False) if isinstance(req_body, dict) else False
            if is_multipart:
                props = {}
                for k, v in req_body.items():
                    props[k] = _oas3_type(v)
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {"type": "object", "properties": props}
                        }
                    },
                }
            else:
                props = {}
                for k, v in req_body.items():
                    props[k] = _oas3_type(v)
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "properties": props}
                        }
                    },
                }

        # Responses
        if resp_type == "binary":
            operation["responses"]["200"] = {
                "description": "Success",
                "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
            }
        elif resp_type == "excel":
            operation["responses"]["200"] = {
                "description": "Success",
                "content": {
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
            }
        else:
            operation["responses"]["200"] = {
                "description": "Success",
                "content": {"application/json": {"schema": {"type": "object"}}},
            }

        # Common error responses
        operation["responses"]["400"] = {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
        operation["responses"]["401"] = {"description": "Unauthorized", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
        operation["responses"]["404"] = {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}

        spec["paths"][path][method.lower()] = operation

    return spec


# ---------------------------------------------------------------------------
# Swagger 2.0 generator
# ---------------------------------------------------------------------------

def generate_swagger2() -> dict:
    """Generate Swagger 2.0 spec as a dict."""
    spec = {
        "swagger": "2.0",
        "info": {
            "title": "Ocrolus API",
            "description": (
                "Ocrolus document automation platform API. "
                "Covers Classify, Capture, Detect, and Analyze capabilities."
            ),
            "version": "3.0.0",
            "contact": {"name": "Ocrolus", "url": "https://docs.ocrolus.com"},
        },
        "host": "api.ocrolus.com",
        "basePath": "/",
        "schemes": ["https"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Bearer JWT token from OAuth 2.0 client_credentials grant",
            },
        },
        "security": [{"Bearer": []}],
        "tags": [],
        "paths": {},
    }

    seen_tags = set()
    for ep in ENDPOINTS:
        tag = ep[0]
        if tag not in seen_tags:
            seen_tags.add(tag)
            spec["tags"].append({"name": tag})

    for tag, op_id, summary, method, path, params, req_body, resp_type, deprecated, notes in ENDPOINTS:
        if path.startswith("https://"):
            api_path = "/oauth/token"
            spec["paths"].setdefault(api_path, {})
            operation = {
                "tags": [tag],
                "operationId": op_id,
                "summary": summary,
                "consumes": ["application/x-www-form-urlencoded"],
                "produces": ["application/json"],
                "security": [],
                "parameters": [
                    {"name": "grant_type", "in": "formData", "type": "string", "required": True},
                    {"name": "client_id", "in": "formData", "type": "string", "required": True},
                    {"name": "client_secret", "in": "formData", "type": "string", "required": True},
                ],
                "responses": {
                    "200": {"description": "Token granted"},
                    "401": {"description": "Invalid credentials"},
                },
            }
            if notes:
                operation["description"] = notes
            spec["paths"][api_path][method.lower()] = operation
            continue

        spec["paths"].setdefault(path, {})
        operation = {
            "tags": [tag],
            "operationId": op_id,
            "summary": summary,
            "produces": ["application/json"],
            "parameters": [],
            "responses": {
                "200": {"description": "Success"},
                "400": {"description": "Bad request"},
                "401": {"description": "Unauthorized"},
                "404": {"description": "Not found"},
            },
        }

        if deprecated:
            operation["deprecated"] = True
        if notes:
            operation["description"] = notes

        if resp_type == "binary":
            operation["produces"] = ["application/octet-stream"]
        elif resp_type == "excel":
            operation["produces"] = ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]

        # Path/query params
        for p in (params or []):
            param = {
                "name": p["name"],
                "in": p["in"],
                "required": p.get("required", False),
                "type": p["type"],
                "description": p.get("description", ""),
            }
            if p.get("format"):
                param["format"] = p["format"]
            operation["parameters"].append(param)

        # Request body
        if req_body:
            is_multipart = False
            body = dict(req_body)
            if "_multipart" in body:
                is_multipart = body.pop("_multipart")

            if is_multipart:
                operation["consumes"] = ["multipart/form-data"]
                for k, v in body.items():
                    s2type = _swagger2_type(v)
                    operation["parameters"].append({
                        "name": k, "in": "formData",
                        "type": s2type.get("type", "string"),
                        "required": k in ("book_pk", "upload"),
                    })
            else:
                operation["consumes"] = ["application/json"]
                props = {}
                for k, v in body.items():
                    props[k] = _swagger2_type(v)
                operation["parameters"].append({
                    "name": "body", "in": "body", "required": True,
                    "schema": {"type": "object", "properties": props},
                })

        spec["paths"][path][method.lower()] = operation

    return spec


# ---------------------------------------------------------------------------
# YAML writer (no PyYAML dependency)
# ---------------------------------------------------------------------------

def _to_yaml(obj, indent=0) -> str:
    """Simple YAML serializer for dicts/lists/scalars. No external deps."""
    prefix = "  " * indent
    lines = []

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                if not val:
                    lines.append(f"{prefix}{key}: {'{}' if isinstance(val, dict) else '[]'}")
                else:
                    lines.append(f"{prefix}{key}:")
                    lines.append(_to_yaml(val, indent + 1))
            elif isinstance(val, bool):
                lines.append(f"{prefix}{key}: {'true' if val else 'false'}")
            elif isinstance(val, (int, float)):
                lines.append(f"{prefix}{key}: {val}")
            elif val is None:
                lines.append(f"{prefix}{key}: null")
            else:
                # String - quote if it contains special chars
                s = str(val)
                if any(c in s for c in (':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '"', "'", '\n')):
                    s = s.replace('\\', '\\\\').replace('"', '\\"')
                    lines.append(f'{prefix}{key}: "{s}"')
                else:
                    lines.append(f"{prefix}{key}: {s}")
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        for item in obj:
            if isinstance(item, dict):
                first = True
                for key, val in item.items():
                    if first:
                        if isinstance(val, (dict, list)) and val:
                            lines.append(f"{prefix}- {key}:")
                            lines.append(_to_yaml(val, indent + 2))
                        elif isinstance(val, bool):
                            lines.append(f"{prefix}- {key}: {'true' if val else 'false'}")
                        elif isinstance(val, (int, float)):
                            lines.append(f"{prefix}- {key}: {val}")
                        elif val is None:
                            lines.append(f"{prefix}- {key}: null")
                        else:
                            s = str(val)
                            if any(c in s for c in (':', '#', '{', '}', '[', ']', ',')):
                                s = s.replace('"', '\\"')
                                lines.append(f'{prefix}- {key}: "{s}"')
                            else:
                                lines.append(f"{prefix}- {key}: {s}")
                        first = False
                    else:
                        sub = _to_yaml({key: val}, indent + 1)
                        lines.append(sub)
            elif isinstance(item, str):
                s = item
                if any(c in s for c in (':', '#', '{', '}', '[', ']', ',')):
                    s = s.replace('"', '\\"')
                    lines.append(f'{prefix}- "{s}"')
                else:
                    lines.append(f"{prefix}- {s}")
            else:
                lines.append(f"{prefix}- {item}")
    else:
        return str(obj)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate Ocrolus API OpenAPI/Swagger specs")
    parser.add_argument("--output-dir", default="./docs", help="Output directory")
    parser.add_argument("--format", choices=["openapi3", "swagger2", "both"], default="both",
                        help="Which format(s) to generate")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    generated = []

    if args.format in ("openapi3", "both"):
        spec = generate_openapi3()
        yaml_path = os.path.join(args.output_dir, "ocrolus-api-openapi3.yaml")
        with open(yaml_path, "w") as f:
            f.write("# Ocrolus API - OpenAPI 3.0.3 Specification\n")
            f.write(f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            f.write(_to_yaml(spec))
            f.write("\n")
        generated.append(("OpenAPI 3.0.3 YAML", yaml_path))

        # Also write as JSON for programmatic use
        json_path = os.path.join(args.output_dir, "ocrolus-api-openapi3.json")
        with open(json_path, "w") as f:
            json.dump(spec, f, indent=2)
        generated.append(("OpenAPI 3.0.3 JSON", json_path))

    if args.format in ("swagger2", "both"):
        spec = generate_swagger2()
        json_path = os.path.join(args.output_dir, "ocrolus-api-swagger2.json")
        with open(json_path, "w") as f:
            json.dump(spec, f, indent=2)
        generated.append(("Swagger 2.0 JSON", json_path))

    # Count endpoints
    tag_counts = {}
    for ep in ENDPOINTS:
        tag_counts[ep[0]] = tag_counts.get(ep[0], 0) + 1

    print(f"\nOcrolus API Specification Generated")
    print(f"{'=' * 50}")
    print(f"Total endpoints documented: {len(ENDPOINTS)}")
    print()
    for tag, count in tag_counts.items():
        print(f"  {tag:<30} {count:>3} endpoints")
    print()
    for label, path in generated:
        print(f"  {label}: {path}")
    print()
    print("Tip: Import the OpenAPI 3 JSON into Swagger UI, Postman,")
    print("or any API documentation tool for interactive exploration.")


if __name__ == "__main__":
    main()
