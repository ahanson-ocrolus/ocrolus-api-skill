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
    ("Authentication", "oauthToken", "oauth/token — Obtain OAuth 2.0 Bearer Token",
     "POST", "https://auth.ocrolus.com/oauth/token",
     [], {"grant_type": "string", "client_id": "string", "client_secret": "string"},
     "json", False,
     "Body: form-encoded (NOT JSON). OAuth 2.0 client_credentials grant. Returns JWT with 24h expiry. No 'audience' param."),

    # ── Book Commands (write operations) ──
    ("Book Commands", "bookAdd", "book/add — Create a new Book",
     "POST", "/v1/book/add", [],
     {"name": "string", "book_type": "string"},
     "json", False, "CORRECTED from /v1/book/create. Returns pk (int) and uuid (str). Body: JSON."),

    ("Book Commands", "bookRemove", "book/remove — Delete a Book",
     "POST", "/v1/book/remove", [],
     {"book_id": "integer", "book_uuid": "string"},
     "json", False, "Body: JSON. Exactly one of book_id (integer) or book_uuid (UUID string). Note: /v1/book/delete is an alias that also works."),

    ("Book Commands", "bookUpdate", "book/update — Update Book properties",
     "POST", "/v1/book/update", [],
     {"pk": "integer", "book_uuid": "string", "name": "string"},
     "json", False, "Body: JSON. Provide pk (integer) or book_uuid (UUID string) + fields to update."),

    # ── Book Queries (read operations) ──
    ("Book Queries", "bookInfo", "book/{pk} — Get Book information",
     "GET", "/v1/book/{pk}",
     [{"name": "pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key (integer)"}],
     None, "json", False, "Path param: pk (integer)."),

    ("Book Queries", "booksList", "books — List all Books",
     "GET", "/v1/books",
     [{"name": "page", "in": "query", "type": "integer", "required": False, "description": "Page number"},
      {"name": "per_page", "in": "query", "type": "integer", "required": False, "description": "Results per page"}],
     None, "json", False, "Query params: page, per_page (both optional)."),

    ("Book Queries", "bookStatus", "book/status — Get Book processing status",
     "GET", "/v1/book/status",
     [{"name": "book_pk", "in": "query", "type": "integer", "required": True, "description": "Book primary key"}],
     None, "json", False,
     "Query param: book_pk (integer). Alt path: /v1/book/{pk}/status also works."),

    ("Book Queries", "bookFromLoan", "book/loan/{loan_id} — Get Book from loan",
     "GET", "/v1/book/loan/{loan_id}",
     [{"name": "loan_id", "in": "path", "type": "string", "required": True, "description": "Loan identifier"}],
     None, "json", False, "Path param: loan_id (string)."),

    ("Book Queries", "bookLoan", "book/{pk}/loan — Get loan from Book",
     "GET", "/v1/book/{pk}/loan",
     [{"name": "pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key (integer)"}],
     None, "json", False, "Path param: pk (integer)."),

    # ── File Uploads ──
    ("File Uploads", "bookUpload", "book/upload — Upload a PDF document",
     "POST", "/v1/book/upload", [],
     {"_multipart": True, "pk": "integer", "book_uuid": "string", "upload": "file", "form_type": "string", "doc_name": "string"},
     "json", False, "Form: multipart/form-data. Provide pk (integer) or book_uuid (UUID). Max 200MB. form_type and doc_name optional."),

    ("File Uploads", "bookUploadMixed", "book/upload/mixed — Upload a mixed document PDF",
     "POST", "/v1/book/upload/mixed", [],
     {"_multipart": True, "pk": "integer", "book_uuid": "string", "upload": "file"},
     "json", False, "Form: multipart/form-data. Provide pk (integer) or book_uuid (UUID). Multiple doc types in single PDF."),

    ("File Uploads", "bookUploadPaystub", "book/upload/paystub — Upload a pay stub PDF",
     "POST", "/v1/book/upload/paystub", [],
     {"_multipart": True, "pk": "integer", "book_uuid": "string", "upload": "file"},
     "json", False, "Form: multipart/form-data. Provide pk (integer) or book_uuid (UUID)."),

    ("File Uploads", "bookUploadImage", "book/upload/image — Upload an image",
     "POST", "/v1/book/upload/image", [],
     {"_multipart": True, "pk": "integer", "book_uuid": "string", "upload": "file", "image_group": "string"},
     "json", False, "Form: multipart/form-data. Provide pk (integer) or book_uuid (UUID)."),

    ("File Uploads", "bookFinalizeImageGroup", "book/finalize-image-group — Finalize an image group",
     "POST", "/v1/book/finalize-image-group", [],
     {"pk": "integer", "book_uuid": "string", "image_group": "string"},
     "json", False, "Body: JSON. Provide pk (integer) or book_uuid (UUID)."),

    ("File Uploads", "bookUploadPlaid", "book/upload/plaid — Upload Plaid aggregator JSON",
     "POST", "/v1/book/upload/plaid", [],
     {"pk": "integer", "book_uuid": "string"}, "json", False, "Body: JSON. Provide pk (integer) or book_uuid (UUID)."),

    ("File Uploads", "bookImportPlaidAsset", "book/import/plaid/asset — Import Plaid Asset Report",
     "POST", "/v1/book/import/plaid/asset", [],
     {"audit_copy_token": "string"},
     "json", False, "Body: JSON. Production only. Requires auditor_id: 'ocrolus'."),

    # ── File Commands (write operations on files) ──
    ("File Commands", "documentCancel", "document/cancel — Cancel document verification",
     "POST", "/v1/document/{doc_uuid}/cancel",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     {"doc_pk": "integer", "doc_uuid": "string", "accept_charges": "boolean"},
     "json", False, "Path param: doc_uuid (UUID). Body (JSON, optional): doc_pk or doc_uuid, accept_charges. Official spec also supports query-param style: /v1/document/cancel?doc_uuid=X"),

    ("File Commands", "documentDelete", "document/remove — Delete a document",
     "POST", "/v1/document/{doc_uuid}/delete",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     {"doc_id": "integer", "doc_uuid": "string"},
     "json", False, "Path param: doc_uuid (UUID). Body (JSON): doc_id (integer) or doc_uuid (UUID). Official spec also supports query-param style: /v1/document/remove?doc_uuid=X"),

    ("File Commands", "documentDownload", "document/{doc_uuid}/download — Download a document file",
     "GET", "/v1/document/{doc_uuid}/download",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "binary", False, "Path param: doc_uuid (UUID)."),

    ("File Commands", "documentUpgrade", "document/upgrade — Upgrade document processing",
     "POST", "/v1/document/{doc_uuid}/upgrade",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     {"doc_pk": "integer", "doc_uuid": "string", "upgrade_type": "string"},
     "json", False, "Path param: doc_uuid (UUID). Body (JSON): doc_pk or doc_uuid + upgrade_type. Official spec also supports: /v1/document/upgrade?doc_uuid=X"),

    ("File Commands", "documentMixedUpgrade", "document/mixed/upgrade — Upgrade mixed document",
     "POST", "/v1/document/mixed/upgrade", [],
     {"mixed_doc_pk": "integer", "mixed_doc_uuid": "string", "upgrade_type": "string"},
     "json", False, "Body (JSON): mixed_doc_pk (integer) or mixed_doc_uuid (UUID) + upgrade_type."),

    # ── File Queries (read operations on files) ──
    ("File Queries", "documentMixedStatus", "document/mixed/status — Get mixed document status",
     "GET", "/v1/document/mixed/status",
     [{"name": "pk", "in": "query", "type": "integer", "required": False, "description": "Mixed document primary key"},
      {"name": "doc_uuid", "in": "query", "type": "string", "format": "uuid", "required": False, "description": "Document UUID"},
      {"name": "mixed_doc_uuid", "in": "query", "type": "string", "format": "uuid", "required": False, "description": "Mixed document UUID"}],
     None, "json", False, "Query params: exactly one of pk (integer), doc_uuid (UUID), or mixed_doc_uuid (UUID)."),

    # ── Classification (v2) ──
    ("Classify", "bookClassificationSummary", "book/{book_uuid}/classification-summary — Book classification",
     "GET", "/v2/book/{book_uuid}/classification-summary",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID). Identifies 300+ document types with confidence scores (0-1)."),

    ("Classify", "mixedDocClassificationSummary", "mixed-document/{mixed_doc_uuid}/classification-summary",
     "GET", "/v2/mixed-document/{mixed_doc_uuid}/classification-summary",
     [{"name": "mixed_doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Mixed document UUID"}],
     None, "json", False, "Path param: mixed_doc_uuid (UUID)."),

    ("Classify", "groupedMixedDocSummary", "index/mixed-doc/{mixed_doc_uuid}/summary — Grouped classification",
     "GET", "/v2/index/mixed-doc/{mixed_doc_uuid}/summary",
     [{"name": "mixed_doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Mixed document UUID"}],
     None, "json", False, "Path param: mixed_doc_uuid (UUID). Organizes forms into logical groups with uniqueness values."),

    # ── Data Extraction / Capture (v1) ──
    ("Capture", "bookForms", "book/{pk}/forms — Get book form data",
     "GET", "/v1/book/{pk}/forms",
     [{"name": "pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key (integer)"}],
     None, "json", False, "Path param: pk (integer)."),

    ("Capture", "bookPaystubs", "book/{pk}/paystubs — Get book pay stub data",
     "GET", "/v1/book/{pk}/paystubs",
     [{"name": "pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key (integer)"}],
     None, "json", False, "Path param: pk (integer)."),

    ("Capture", "documentForms", "document/{doc_uuid}/forms — Get document form data",
     "GET", "/v1/document/{doc_uuid}/forms",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, "Path param: doc_uuid (UUID)."),

    ("Capture", "documentPaystubs", "document/{doc_uuid}/paystubs — Get document pay stub data",
     "GET", "/v1/document/{doc_uuid}/paystubs",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, "Path param: doc_uuid (UUID)."),

    ("Capture", "formFields", "form/{form_uuid}/fields — Get form field data",
     "GET", "/v1/form/{form_uuid}/fields",
     [{"name": "form_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Form UUID"}],
     None, "json", False, "Path param: form_uuid (UUID). Returns confidence scores per field (0-1)."),

    ("Capture", "paystubData", "paystub/{paystub_uuid} — Get pay stub data",
     "GET", "/v1/paystub/{paystub_uuid}",
     [{"name": "paystub_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Pay stub UUID"}],
     None, "json", False, "Path param: paystub_uuid (UUID)."),

    ("Capture", "bookTransactions", "book/{pk}/transactions — Get book transactions",
     "GET", "/v1/book/{pk}/transactions",
     [{"name": "pk", "in": "path", "type": "integer", "required": True, "description": "Book primary key (integer)"},
      {"name": "uploaded_doc_pk", "in": "query", "type": "integer", "required": False, "description": "Filter by uploaded document primary key"},
      {"name": "uploaded_doc_uuid", "in": "query", "type": "string", "format": "uuid", "required": False, "description": "Filter by uploaded document UUID"},
      {"name": "only_tagged", "in": "query", "type": "boolean", "required": False, "description": "Only return tagged transactions (requires distinct_fields=true)"},
      {"name": "distinct_fields", "in": "query", "type": "boolean", "required": False, "description": "Return only distinct field values"}],
     None, "json", False, "Path param: pk (integer). Query params (optional): uploaded_doc_pk, uploaded_doc_uuid, only_tagged, distinct_fields. Alt: /v1/transaction?book_pk=X also works."),

    # ── Fraud Detection / Detect (v2) ──
    ("Detect", "detectBookSignals", "detect/book/{book_uuid}/signals — Book-level fraud signals",
     "GET", "/v2/detect/book/{book_uuid}/signals",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False,
     "Path param: book_uuid (UUID). Returns authenticity scores (0-100), reason codes, and signal types."),

    ("Detect", "detectDocumentSignals", "detect/document/{doc_uuid}/signals — Document-level fraud signals",
     "GET", "/v2/detect/document/{doc_uuid}/signals",
     [{"name": "doc_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Document UUID"}],
     None, "json", False, "Path param: doc_uuid (UUID)."),

    ("Detect", "detectVisualization", "detect/visualization/{visualization_uuid} — Signal visualization",
     "GET", "/v2/detect/visualization/{visualization_uuid}",
     [{"name": "visualization_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Visualization UUID"}],
     None, "binary", False,
     "Path param: visualization_uuid (UUID). Returns binary image with fraud signal overlays."),

    ("Detect", "suspiciousActivityFlags", "book/{book_uuid}/suspicious-activity-flags — LEGACY",
     "GET", "/v1/book/{book_uuid}/suspicious-activity-flags",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", True, "DEPRECATED. Use /v2/detect/ endpoints instead. Path param: book_uuid (UUID)."),

    # ── Cash Flow Analytics (v2) ──
    ("Analyze", "bookSummary", "book/{book_uuid}/summary — Cash flow summary",
     "GET", "/v2/book/{book_uuid}/summary",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID). Returns daily balances, PII, and time series data."),

    ("Analyze", "bookCashFlowFeatures", "book/{book_uuid}/cash_flow_features — Cash flow features",
     "GET", "/v2/book/{book_uuid}/cash_flow_features",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"},
      {"name": "min_days_to_include", "in": "query", "type": "integer", "required": False, "description": "Min days for most recent month (default 0, use 32 for full months only)"}],
     None, "json", False, "Path param: book_uuid (UUID). Query param: min_days_to_include (integer, optional)."),

    ("Analyze", "bookEnrichedTxns", "book/{book_uuid}/enriched_txns — Enriched transactions",
     "GET", "/v2/book/{book_uuid}/enriched_txns",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID). Returns transactions with categories and tags."),

    ("Analyze", "bookCashFlowRiskScore", "book/{book_uuid}/cash_flow_risk_score — Risk score",
     "GET", "/v2/book/{book_uuid}/cash_flow_risk_score",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID). Returns probability of default."),

    ("Analyze", "bookBenchmarking", "book/{book_uuid}/benchmarking — Benchmarking (Beta)",
     "GET", "/v2/book/{book_uuid}/benchmarking",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID). NAICS4-based benchmarking. Beta feature."),

    ("Analyze", "bookLenderAnalyticsXlsx", "book/{book_uuid}/lender_analytics/xlsx — SMB analytics Excel",
     "GET", "/v2/book/{book_uuid}/lender_analytics/xlsx",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "excel", False, "Path param: book_uuid (UUID). Returns .xlsx binary content."),

    # ── Income Calculations (v2) ──
    ("Income", "bookIncomeCalculations", "book/{book_uuid}/income-calculations — Income calculations",
     "GET", "/v2/book/{book_uuid}/income-calculations",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"},
      {"name": "guideline", "in": "query", "type": "string", "required": False, "description": "Guideline: FANNIE_MAE, FREDDIE_MAC, FHA, VA, USDA"}],
     None, "json", False, "Path param: book_uuid (UUID). Query param: guideline (string, optional)."),

    ("Income", "bookIncomeSummary", "book/{book_uuid}/income-summary — Income summary",
     "GET", "/v2/book/{book_uuid}/income-summary",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID)."),

    ("Income", "bookIncomeEntity", "book/{book_uuid}/income-entity — Configure income entity",
     "POST", "/v2/book/{book_uuid}/income-entity",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"config": "object"}, "json", False, "Path param: book_uuid (UUID). Body: JSON."),

    ("Income", "bookIncomeGuideline", "book/{book_uuid}/income-guideline — Save income guideline",
     "PUT", "/v2/book/{book_uuid}/income-guideline",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"guideline": "object"}, "json", False, "Path param: book_uuid (UUID). Body: JSON."),

    ("Income", "bookSelfEmployedIncome", "book/{book_uuid}/self-employed-income — Fannie Mae self-employed",
     "POST", "/v2/book/{book_uuid}/self-employed-income",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"params": "object"}, "json", False, "Path param: book_uuid (UUID). Body: JSON. Call BEFORE income-calculations."),

    ("Income", "bookBsic", "book/{book_uuid}/bsic — BSIC results",
     "GET", "/v2/book/{book_uuid}/bsic",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     None, "json", False, "Path param: book_uuid (UUID). Bank Statement Income Calculator results."),

    # ── Tag Management (v2, Beta) ──
    ("Tag Management", "analyticsTagsCreate", "analytics/tags — Create a transaction tag",
     "POST", "/v2/analytics/tags", [],
     {"name": "string"}, "json", False, "Body: JSON."),

    ("Tag Management", "analyticsTagGet", "analytics/tags/{tag_uuid} — Retrieve a tag",
     "GET", "/v2/analytics/tags/{tag_uuid}",
     [{"name": "tag_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Tag UUID"}],
     None, "json", False, "Path param: tag_uuid (UUID)."),

    ("Tag Management", "analyticsTagModify", "analytics/tags/{tag_uuid} — Modify a tag",
     "PUT", "/v2/analytics/tags/{tag_uuid}",
     [{"name": "tag_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Tag UUID"}],
     {"name": "string"}, "json", False, "Path param: tag_uuid (UUID). Body: JSON."),

    ("Tag Management", "analyticsTagDelete", "analytics/tags/{tag_uuid} — Delete a tag",
     "DELETE", "/v2/analytics/tags/{tag_uuid}",
     [{"name": "tag_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Tag UUID"}],
     None, "json", False, "Path param: tag_uuid (UUID). System tags cannot be deleted."),

    ("Tag Management", "analyticsTagsList", "analytics/tags — List all tags",
     "GET", "/v2/analytics/tags",
     [{"name": "is_system_tag", "in": "query", "type": "boolean", "required": False, "description": "Filter system vs custom tags"}],
     None, "json", False, "Query param: is_system_tag (boolean, optional)."),

    ("Tag Management", "analyticsRevenueDeductionTagsGet", "analytics/revenue-deduction-tags — Get revenue deduction tags",
     "GET", "/v2/analytics/revenue-deduction-tags", [],
     None, "json", False, None),

    ("Tag Management", "analyticsRevenueDeductionTagsUpdate", "analytics/revenue-deduction-tags — Update revenue deduction tags",
     "PUT", "/v2/analytics/revenue-deduction-tags", [],
     {"tag_names": "array"}, "json", False, "Body: JSON. Replaces the full collection."),

    ("Tag Management", "analyticsBookTransactionsOverride", "analytics/book/{book_uuid}/transactions — Override transaction tag",
     "PUT", "/v2/analytics/book/{book_uuid}/transactions",
     [{"name": "book_uuid", "in": "path", "type": "string", "format": "uuid", "required": True, "description": "Book UUID"}],
     {"txn_pk": "integer", "tag_uuids": "array"}, "json", False, "Path param: book_uuid (UUID). Body: JSON."),

    # ── Encore / Book Copy (v1) ──
    ("Encore", "bookCopyJobsCreate", "book/copy-jobs — Create book copy jobs",
     "POST", "/v1/book/copy-jobs", [],
     {"jobs": "array"}, "json", False, "Body: JSON. Max 50 jobs per call."),

    ("Encore", "bookCopyJobsList", "book/copy-jobs — List book copy jobs",
     "GET", "/v1/book/copy-jobs",
     [{"name": "direction", "in": "query", "type": "string", "required": False, "description": "'outbound' or 'inbound'"}],
     None, "json", False, "Query param: direction (string, optional — 'outbound' or 'inbound')."),

    ("Encore", "bookCopyJobAccept", "book/copy-jobs/{job_id}/accept — Accept a copy job",
     "POST", "/v1/book/copy-jobs/{job_id}/accept",
     [{"name": "job_id", "in": "path", "type": "string", "required": True, "description": "Copy job ID"}],
     {"name": "string"}, "json", False, "Path param: job_id (string). Body: JSON."),

    ("Encore", "bookCopyJobReject", "book/copy-jobs/{job_id}/reject — Reject a copy job",
     "POST", "/v1/book/copy-jobs/{job_id}/reject",
     [{"name": "job_id", "in": "path", "type": "string", "required": True, "description": "Copy job ID"}],
     None, "json", False, "Path param: job_id (string)."),

    ("Encore", "bookCopyJobsRunKickouts", "book/copy-jobs/run-kickouts — Run automated kick-outs",
     "POST", "/v1/book/copy-jobs/run-kickouts", [],
     None, "json", False, "No params. Runs on all AWAITING_RECIPIENT jobs."),

    ("Encore", "settingsBookCopy", "settings/book-copy — Get book copy settings",
     "GET", "/v1/settings/book-copy", [],
     None, "json", False, "No params."),

    # ── Webhooks - Org Level ──
    ("Webhooks (Org Level)", "accountSettingsWebhookAdd", "account/settings/webhook — Add org-level webhook",
     "POST", "/v1/account/settings/webhook", [],
     {"url": "string", "events": "array"}, "json", False, "Body: JSON."),

    ("Webhooks (Org Level)", "accountSettingsWebhooksList", "account/settings/webhooks — List org-level webhooks",
     "GET", "/v1/account/settings/webhooks", [],
     None, "json", False, "No params."),

    ("Webhooks (Org Level)", "accountSettingsWebhookGet", "account/settings/webhooks/{webhook_id} — Retrieve webhook",
     "GET", "/v1/account/settings/webhooks/{webhook_id}",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     None, "json", False, "Path param: webhook_id (string)."),

    ("Webhooks (Org Level)", "accountSettingsWebhookUpdate", "account/settings/webhooks/{webhook_id} — Update webhook",
     "PUT", "/v1/account/settings/webhooks/{webhook_id}",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     {"url": "string", "events": "array"}, "json", False, "Path param: webhook_id (string). Body: JSON."),

    ("Webhooks (Org Level)", "accountSettingsWebhookDelete", "account/settings/webhooks/{webhook_id} — Delete webhook",
     "DELETE", "/v1/account/settings/webhooks/{webhook_id}",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     None, "json", False, "Path param: webhook_id (string)."),

    ("Webhooks (Org Level)", "accountSettingsWebhooksEvents", "account/settings/webhooks/events — List event types",
     "GET", "/v1/account/settings/webhooks/events", [],
     None, "json", False, "No params."),

    ("Webhooks (Org Level)", "accountSettingsWebhookTest", "account/settings/webhooks/{webhook_id}/test — Test webhook",
     "POST", "/v1/account/settings/webhooks/{webhook_id}/test",
     [{"name": "webhook_id", "in": "path", "type": "string", "required": True, "description": "Webhook ID"}],
     None, "json", False, "Path param: webhook_id (string)."),

    ("Webhooks (Org Level)", "accountSettingsWebhooksSecret", "account/settings/webhooks/secret — Configure secret",
     "POST", "/v1/account/settings/webhooks/secret", [],
     {"secret": "string"}, "json", False, "Body: JSON. Secret must be 16-128 characters."),

    # ── Webhooks - Account Level ──
    ("Webhooks (Account Level)", "webhookConfigure", "webhook/configure — Configure account webhook",
     "POST", "/v1/webhook/configure", [],
     {"url": "string", "events": "array"}, "json", False, "Body: JSON."),

    ("Webhooks (Account Level)", "webhookConfiguration", "webhook/configuration — Get account webhook config",
     "GET", "/v1/webhook/configuration", [],
     None, "json", False, "No params."),

    ("Webhooks (Account Level)", "webhookTest", "webhook/test — Test account webhook",
     "POST", "/v1/webhook/test", [],
     None, "json", False, "No params."),

    ("Webhooks (Account Level)", "webhookSecret", "webhook/secret — Configure account webhook secret",
     "POST", "/v1/webhook/secret", [],
     {"secret": "string"}, "json", False, "Body: JSON."),
]


# ---------------------------------------------------------------------------
# Public documentation links (docs.ocrolus.com/reference)
# Maps operationId → slug on the Ocrolus docs site
# ---------------------------------------------------------------------------

DOC_LINKS = {
    # Auth
    "oauthToken": "grant-authentication-token",
    # Book Operations
    "bookAdd": "create-a-book",
    "bookRemove": "delete-a-book",
    "bookUpdate": "update-book",
    "bookInfo": "book-info",
    "booksList": "book-list",
    "bookStatus": "book-status",
    "bookFromLoan": "book-from-loan",
    "bookLoan": "loan-from-book",
    # Document Upload & Management
    "bookUpload": "upload-document",
    "bookUploadMixed": "upload-mixed-document",
    "bookUploadPaystub": "upload-paystub",
    "bookUploadImage": "upload-image",
    "bookFinalizeImageGroup": "mark-image-group-complete",
    "bookUploadPlaid": "upload-json",
    "bookImportPlaidAsset": "import-plaid-asset-report",
    "documentCancel": "cancel-file-verification",
    "documentDelete": "delete-a-file",
    "documentDownload": "document-download",
    "documentUpgrade": "upgrade-doc",
    "documentMixedUpgrade": "upgrade-mixed-doc",
    "documentMixedStatus": "mixed-document-status",
    # Classification
    "bookClassificationSummary": "book-classification-summary",
    "mixedDocClassificationSummary": "mixed-doc-classification-summary",
    "groupedMixedDocSummary": "grouped-mixed-doc-classification-summary",
    # Data Extraction
    "bookForms": "book-form-data",
    "bookPaystubs": "book-paystub-data",
    "documentForms": "doc-form-data",
    "documentPaystubs": "doc-paystub-data",
    "formFields": "form-field-data",
    "paystubData": "paystub-data",
    "bookTransactions": "transactions",
    # Fraud Detection
    "detectBookSignals": "book-fraud-signals",
    "detectDocumentSignals": "doc-fraud-signals",
    "detectVisualization": "signal-visualization",
    "suspiciousActivityFlags": "suspicious-activity",
    # Cash Flow Analytics
    "bookSummary": "book-summary",
    "bookCashFlowFeatures": "cash-flow-features",
    "bookEnrichedTxns": "enriched-transactions",
    "bookCashFlowRiskScore": "risk-score",
    "bookLenderAnalyticsXlsx": "analytics-excel",
    # Income Calculations
    "bookIncomeCalculations": "income-calculations",
    "bookIncomeSummary": "income-summary",
    "bookIncomeEntity": "income-entity-config",
    "bookIncomeGuideline": "save-income-guideline",
    "bookSelfEmployedIncome": "self-employed-income-calculation-fm",
    "bookBsic": "bsic",
    # Tag Management
    "analyticsTagsCreate": "create-tag",
    "analyticsTagGet": "get-tag",
    "analyticsTagModify": "modify-tag",
    "analyticsTagDelete": "delete-tag",
    "analyticsTagsList": "get-all-tags",
    "analyticsRevenueDeductionTagsGet": "get-revenue-deduction-tags",
    "analyticsRevenueDeductionTagsUpdate": "update-revenue-deduction-tag",
    "analyticsBookTransactionsOverride": "override-transaction-tag",
    # Encore / Book Copy
    "bookCopyJobsCreate": "create-book-copy-jobs",
    "bookCopyJobsList": "list-book-copy-jobs",
    "bookCopyJobAccept": "copy-jobs-accept",
    "bookCopyJobReject": "copy-jobs-reject",
    "bookCopyJobsRunKickouts": "run-kick-outs",
    "settingsBookCopy": "get-book-copy-settings-allow-list",
    # Webhooks (Org)
    "accountSettingsWebhookAdd": "add-webhook",
    "accountSettingsWebhooksList": "list-webhooks",
    "accountSettingsWebhookGet": "get-webhook",
    "accountSettingsWebhookUpdate": "update-webhook",
    "accountSettingsWebhookDelete": "delete-webhook",
    "accountSettingsWebhooksEvents": "list-events",
    "accountSettingsWebhookTest": "test-org-webhook",
    "accountSettingsWebhooksSecret": "configure-webhook-secret-org-level",
    # Webhooks (Account)
    "webhookConfigure": "configure-webhook",
    "webhookConfiguration": "webhook-configuration",
    "webhookTest": "test-webhook",
    "webhookSecret": "configure-webhook-secret-account-level",
}

DOCS_BASE_URL = "https://docs.ocrolus.com/reference"

# Tag order mirrors the docs.ocrolus.com/reference sidebar
TAG_ORDER = [
    "Authentication",
    "Book Commands",
    "Book Queries",
    "File Uploads",
    "File Commands",
    "File Queries",
    "Classify",
    "Capture",
    "Detect",
    "Analyze",
    "Encore",
    "Income",
    "Tag Management",
    "Webhooks (Account Level)",
    "Webhooks (Org Level)",
]

TAG_DESCRIPTIONS = {
    "Authentication": "OAuth 2.0 token management",
    "Book Commands": "Create, update, and delete Books",
    "Book Queries": "Read Book information, status, and related loan data",
    "File Uploads": "Upload documents, paystubs, images, and Plaid data to Books",
    "File Commands": "Cancel, delete, download, and upgrade documents",
    "File Queries": "Retrieve file and mixed-document status",
    "Classify": "Identify document types with confidence scores",
    "Capture": "Extract structured data from documents (forms, paystubs, transactions)",
    "Detect": "Fraud detection signals, authenticity scores, and reason codes",
    "Analyze": "Cash flow analytics, enriched transactions, and risk scoring",
    "Income": "Income calculations, BSIC, and self-employed income",
    "Tag Management": "Transaction tag management (Beta)",
    "Encore": "Book copy jobs for organization-to-organization sharing",
    "Webhooks (Account Level)": "Account-level webhook management (legacy)",
    "Webhooks (Org Level)": "Organization-level webhook management (recommended)",
}


# ---------------------------------------------------------------------------
# Type mapping helpers
# ---------------------------------------------------------------------------

def _oas3_type(t: str, field_name: str = "") -> dict:
    """Map simple type string to OpenAPI 3 schema with example values for Postman."""
    # Field-specific examples that help Postman pre-fill useful placeholder values
    field_examples = {
        "name": "My Book",
        "book_type": "DEFAULT",
        "pk": 71250194,
        "book_id": 71250194,
        "book_uuid": "09c52985-2f05-4022-a738-9277cc335c7e",
        "doc_pk": 12345678,
        "doc_id": 12345678,
        "doc_uuid": "aaaa1111-bbbb-2222-cccc-333344445555",
        "mixed_doc_pk": 12345678,
        "mixed_doc_uuid": "aaaa1111-bbbb-2222-cccc-333344445555",
        "form_type": "bank_statement",
        "doc_name": "January 2026 Statement",
        "upgrade_type": "INSTANT",
        "image_group": "group-1",
        "audit_copy_token": "<plaid_audit_copy_token>",
        "accept_charges": True,
        "grant_type": "client_credentials",
        "client_id": "<your_client_id>",
        "client_secret": "<your_client_secret>",
        "url": "https://example.com/webhook",
        "secret": "<webhook_secret_16_to_128_chars>",
    }
    if t == "integer":
        schema = {"type": "integer"}
    elif t == "boolean":
        schema = {"type": "boolean"}
    elif t == "array":
        schema = {"type": "array", "items": {"type": "string"}}
    elif t == "object":
        schema = {"type": "object"}
    elif t == "file":
        schema = {"type": "string", "format": "binary"}
    else:
        schema = {"type": "string"}
    if field_name in field_examples:
        schema["example"] = field_examples[field_name]
    return schema


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

    tags_in_use = {ep[0] for ep in ENDPOINTS}
    for tag in TAG_ORDER:
        if tag in tags_in_use:
            spec["tags"].append({"name": tag, "description": TAG_DESCRIPTIONS.get(tag, "")})

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
                                    "client_id": {"type": "string", "example": "<your_client_id>"},
                                    "client_secret": {"type": "string", "example": "<your_client_secret>"},
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
            doc_slug = DOC_LINKS.get(op_id)
            desc_parts = []
            if notes:
                desc_parts.append(notes)
            if doc_slug:
                desc_parts.append(f"Docs: {DOCS_BASE_URL}/{doc_slug}")
            if desc_parts:
                operation["description"] = " | ".join(desc_parts)
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

        # Build description with doc link
        doc_slug = DOC_LINKS.get(op_id)
        desc_parts = []
        if notes:
            desc_parts.append(notes)
        if doc_slug:
            desc_parts.append(f"Docs: {DOCS_BASE_URL}/{doc_slug}")
        if desc_parts:
            operation["description"] = " | ".join(desc_parts)

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
            body_copy = dict(req_body) if isinstance(req_body, dict) else {}
            is_multipart = body_copy.pop("_multipart", False)
            if is_multipart:
                props = {}
                for k, v in body_copy.items():
                    props[k] = _oas3_type(v, k)
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
                for k, v in body_copy.items():
                    props[k] = _oas3_type(v, k)
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

    tags_in_use_sw2 = {ep[0] for ep in ENDPOINTS}
    for tag in TAG_ORDER:
        if tag in tags_in_use_sw2:
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
            doc_slug = DOC_LINKS.get(op_id)
            desc_parts = []
            if notes:
                desc_parts.append(notes)
            if doc_slug:
                desc_parts.append(f"Docs: {DOCS_BASE_URL}/{doc_slug}")
            if desc_parts:
                operation["description"] = " | ".join(desc_parts)
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

        # Build description with doc link
        doc_slug_sw2 = DOC_LINKS.get(op_id)
        desc_parts_sw2 = []
        if notes:
            desc_parts_sw2.append(notes)
        if doc_slug_sw2:
            desc_parts_sw2.append(f"Docs: {DOCS_BASE_URL}/{doc_slug_sw2}")
        if desc_parts_sw2:
            operation["description"] = " | ".join(desc_parts_sw2)

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
                        "required": k == "upload",
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
# Postman Collection v2.1 generator
# ---------------------------------------------------------------------------
#
# Produces a native Postman Collection JSON with tags as folders, so when
# imported the collection mirrors the docs.ocrolus.com/reference sidebar
# structure regardless of Postman's folder-strategy setting.

POSTMAN_EXAMPLES = {
    "name": "My Book",
    "book_type": "DEFAULT",
    "pk": "71250194",
    "book_id": "71250194",
    "book_uuid": "09c52985-2f05-4022-a738-9277cc335c7e",
    "book_pk": "71250194",
    "doc_pk": "12345678",
    "doc_id": "12345678",
    "doc_uuid": "aaaa1111-bbbb-2222-cccc-333344445555",
    "mixed_doc_pk": "12345678",
    "mixed_doc_uuid": "aaaa1111-bbbb-2222-cccc-333344445555",
    "uploaded_doc_pk": "12345678",
    "uploaded_doc_uuid": "aaaa1111-bbbb-2222-cccc-333344445555",
    "form_uuid": "bbbb2222-cccc-3333-dddd-444455556666",
    "paystub_uuid": "cccc3333-dddd-4444-eeee-555566667777",
    "visualization_uuid": "dddd4444-eeee-5555-ffff-666677778888",
    "tag_uuid": "eeee5555-ffff-6666-1111-777788889999",
    "webhook_id": "webhook_abc123",
    "loan_id": "LOAN-001",
    "job_id": "job_12345",
    "form_type": "bank_statement",
    "doc_name": "January 2026 Statement",
    "upgrade_type": "INSTANT",
    "image_group": "group-1",
    "audit_copy_token": "<plaid_audit_copy_token>",
    "accept_charges": "true",
    "grant_type": "client_credentials",
    "client_id": "{{OCROLUS_CLIENT_ID}}",
    "client_secret": "{{OCROLUS_CLIENT_SECRET}}",
    "url": "https://example.com/webhook",
    "secret": "<webhook_secret_16_to_128_chars>",
    "page": "1",
    "per_page": "50",
    "min_days_to_include": "0",
    "guideline": "FANNIE_MAE",
    "direction": "OUTBOUND",
    "is_system_tag": "false",
    "only_tagged": "true",
    "distinct_fields": "true",
    "target_type": "INSTANT",
}


def _postman_example(field_name: str, default: str = "") -> str:
    """Return a realistic example value for a Postman variable or field."""
    return POSTMAN_EXAMPLES.get(field_name, default)


def _postman_url(path: str, query_params: list, path_params: list) -> dict:
    """Build a Postman URL object for a given endpoint path and params."""
    if path.startswith("https://"):
        # Full URL (e.g., auth endpoint)
        from urllib.parse import urlparse
        parsed = urlparse(path)
        host = parsed.netloc.split(".")
        raw = path
        segments = [s for s in parsed.path.split("/") if s]
        url_obj = {
            "raw": raw,
            "protocol": parsed.scheme,
            "host": host,
            "path": segments,
        }
    else:
        # Relative path — use {{BASE_URL}} variable
        segments = []
        for seg in [s for s in path.split("/") if s]:
            if seg.startswith("{") and seg.endswith("}"):
                var_name = seg[1:-1]
                segments.append(":" + var_name)
            else:
                segments.append(seg)
        raw = "{{BASE_URL}}/" + "/".join(segments)
        url_obj = {
            "raw": raw,
            "host": ["{{BASE_URL}}"],
            "path": segments,
        }

    # Add path variables
    if path_params:
        url_obj["variable"] = []
        for p in path_params:
            url_obj["variable"].append({
                "key": p["name"],
                "value": _postman_example(p["name"], ""),
                "description": p.get("description", ""),
            })

    # Add query parameters
    if query_params:
        url_obj["query"] = []
        query_raw_parts = []
        for p in query_params:
            example = _postman_example(p["name"], "")
            url_obj["query"].append({
                "key": p["name"],
                "value": example,
                "description": p.get("description", ""),
                "disabled": not p.get("required", False),
            })
            query_raw_parts.append(f"{p['name']}={example}")
        if query_raw_parts:
            url_obj["raw"] = raw + "?" + "&".join(query_raw_parts)

    return url_obj


def _postman_body(req_body, is_auth_form: bool = False) -> dict:
    """Build a Postman request body object."""
    if not req_body:
        return None

    body_dict = dict(req_body)
    is_multipart = body_dict.pop("_multipart", False)

    if is_auth_form:
        # OAuth token uses x-www-form-urlencoded
        return {
            "mode": "urlencoded",
            "urlencoded": [
                {"key": k, "value": _postman_example(k, ""), "type": "text"}
                for k in body_dict.keys()
            ],
        }

    if is_multipart:
        fields = []
        for k, v in body_dict.items():
            if v == "file":
                fields.append({"key": k, "type": "file", "src": ""})
            else:
                fields.append({
                    "key": k,
                    "type": "text",
                    "value": _postman_example(k, ""),
                })
        return {"mode": "formdata", "formdata": fields}

    # JSON body
    example_body = {k: _postman_example(k, "") for k in body_dict.keys()}
    return {
        "mode": "raw",
        "raw": json.dumps(example_body, indent=2),
        "options": {"raw": {"language": "json"}},
    }


def generate_postman_collection() -> dict:
    """Generate a Postman Collection v2.1 with tags-as-folders structure."""
    collection = {
        "info": {
            "name": "Ocrolus API",
            "description": (
                "Ocrolus document automation platform API. Folders match the "
                "docs.ocrolus.com/reference sidebar structure.\n\n"
                "## Setup\n"
                "1. Set the `BASE_URL` collection variable to `https://api.ocrolus.com`\n"
                "2. Set `OCROLUS_CLIENT_ID` and `OCROLUS_CLIENT_SECRET` as secrets\n"
                "3. Call Authentication → oauth/token to get a bearer token\n"
                "4. Save the returned `access_token` to the `ACCESS_TOKEN` variable\n\n"
                "All other requests use `Authorization: Bearer {{ACCESS_TOKEN}}`."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{ACCESS_TOKEN}}", "type": "string"}],
        },
        "variable": [
            {"key": "BASE_URL", "value": "https://api.ocrolus.com", "type": "string"},
            {"key": "ACCESS_TOKEN", "value": "", "type": "string", "description": "Bearer token from /oauth/token"},
            {"key": "OCROLUS_CLIENT_ID", "value": "", "type": "string"},
            {"key": "OCROLUS_CLIENT_SECRET", "value": "", "type": "secret"},
        ],
        "item": [],
    }

    # Group endpoints by tag
    endpoints_by_tag = {}
    for ep in ENDPOINTS:
        tag = ep[0]
        endpoints_by_tag.setdefault(tag, []).append(ep)

    # Emit folders in docs-site order
    for tag in TAG_ORDER:
        if tag not in endpoints_by_tag:
            continue
        folder = {
            "name": tag,
            "description": TAG_DESCRIPTIONS.get(tag, ""),
            "item": [],
        }

        for (_, op_id, summary, method, path, params, req_body, resp_type, deprecated, notes) in endpoints_by_tag[tag]:
            path_params = [p for p in (params or []) if p.get("in") == "path"]
            query_params = [p for p in (params or []) if p.get("in") == "query"]

            is_auth = path.startswith("https://") and "auth.ocrolus.com" in path
            url_obj = _postman_url(path, query_params, path_params)

            headers = []
            if is_auth:
                headers.append({"key": "Content-Type", "value": "application/x-www-form-urlencoded"})
            elif req_body and isinstance(req_body, dict) and not req_body.get("_multipart"):
                headers.append({"key": "Content-Type", "value": "application/json"})
            headers.append({"key": "Accept", "value": "application/json"})

            body = _postman_body(req_body, is_auth_form=is_auth)

            # Build description with docs link
            desc_parts = []
            if notes:
                desc_parts.append(notes)
            doc_slug = DOC_LINKS.get(op_id)
            if doc_slug:
                desc_parts.append(f"**Docs:** {DOCS_BASE_URL}/{doc_slug}")
            if deprecated:
                desc_parts.append("**DEPRECATED.**")
            description = "\n\n".join(desc_parts)

            request_obj = {
                "name": summary,
                "request": {
                    "method": method,
                    "header": headers,
                    "url": url_obj,
                    "description": description,
                },
                "response": [],
            }
            if body is not None:
                request_obj["request"]["body"] = body
            # Auth endpoint has no auth
            if is_auth:
                request_obj["request"]["auth"] = {"type": "noauth"}

            folder["item"].append(request_obj)

        collection["item"].append(folder)

    return collection


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
    parser.add_argument("--format", choices=["openapi3", "swagger2", "postman", "all", "both"], default="all",
                        help="Which format(s) to generate (default: all). 'both' is legacy for openapi3+swagger2.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    generated = []

    emit_openapi3 = args.format in ("openapi3", "both", "all")
    emit_swagger2 = args.format in ("swagger2", "both", "all")
    emit_postman = args.format in ("postman", "all")

    if emit_openapi3:
        spec = generate_openapi3()
        yaml_path = os.path.join(args.output_dir, "ocrolus-api-annotated-openapi3.yaml")
        with open(yaml_path, "w") as f:
            f.write("# Ocrolus API - OpenAPI 3.0.3 Specification\n")
            f.write(f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            f.write(_to_yaml(spec))
            f.write("\n")
        generated.append(("OpenAPI 3.0.3 YAML", yaml_path))

        # Also write as JSON for programmatic use
        json_path = os.path.join(args.output_dir, "ocrolus-api-annotated-openapi3.json")
        with open(json_path, "w") as f:
            json.dump(spec, f, indent=2)
        generated.append(("OpenAPI 3.0.3 JSON", json_path))

    if emit_swagger2:
        spec = generate_swagger2()
        json_path = os.path.join(args.output_dir, "ocrolus-api-annotated-swagger2.json")
        with open(json_path, "w") as f:
            json.dump(spec, f, indent=2)
        generated.append(("Swagger 2.0 JSON", json_path))

    if emit_postman:
        collection = generate_postman_collection()
        pm_path = os.path.join(args.output_dir, "ocrolus-api.postman_collection.json")
        with open(pm_path, "w") as f:
            json.dump(collection, f, indent=2)
        generated.append(("Postman Collection v2.1", pm_path))

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
    print("Tips:")
    print("  - For Postman: import the .postman_collection.json for tag-based folders")
    print("  - For Swagger UI or other API tools: use the OpenAPI 3 YAML/JSON")


if __name__ == "__main__":
    main()
