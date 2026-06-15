# Workflow — SMB Cash-Flow Underwriting (bank statements)

End-to-end pipeline for small-business cash-flow underwriting from bank statements.
**Every endpoint, event, and timing rule below was validated against the live API.**

> Sibling workflows live beside this file (e.g. `mortgage-income.md`, added later).
> For exact params see `references/endpoints.md`; for events see `references/webhooks.md`.

## When to use

The applicant submits **bank statements** and you need cash-flow metrics (monthly
revenue/expense, average balance, NSF counts, deposit trends) and fraud signals to
make an underwriting decision. For mortgage *income* from pay stubs/W-2s/tax forms,
use the mortgage workflow instead.

## The sequence

| # | Step | Call | Driven by |
|---|------|------|-----------|
| 1 | Create book | `POST /v1/book/add` (`book_class` = `INSTANT` for machine-only) | — |
| 2 | Upload statements | `POST /v1/book/upload` (one per PDF) or `POST /v1/book/upload/mixed` | — |
| 3 | Get classification | `GET /v2/book/{book_uuid}/classification-summary` | `book.classified` |
| 4 | Get **capture** (transactions) | `GET /v1/transaction?book_uuid={uuid}` | `book.verified` |
| 5 | Get **analysis** | `GET /v2/book/{book_uuid}/summary` + `/enriched_txns` + `/cash_flow_features` | `book.completed` |
| 6 | Get fraud signals | `GET /v2/detect/book/{book_uuid}/signals` | `book.detect.signal_found` / `book.completed` |
| 7 | Write one consistent output file | — | — |

Persist both ids from step 1: integer **`pk`** (v1 calls) and **`uuid`** (v2 calls).

## Timing — what's ready when (this trips people up)

- **Capture (transactions) is ready at `book.verified`.**
- **Analytics is ready at `book.completed`** (or `book.analytics_v2.generated`). The
  analytics/income endpoints (`summary`, `enriched_txns`, `cash_flow_features`) return
  **HTTP 425 "Too Early"** if you call them at `book.verified`. Wait for `book.completed`.
- Book-level status vocabulary: book reaches `book_status="VERIFIED"`; individual docs
  reach `"VERIFICATION_COMPLETE"`. Gate on the **book** status, not per-doc.

## Capture for bank statements = transactions, not forms

The form endpoints (`/v2/book/{uuid}/forms`, `/v1/book/forms`, `/v1/document/forms/fields`)
return **empty** for bank statements — bank-statement capture lives in **transactions**:

- `GET /v1/transaction?book_uuid={uuid}` — raw ledger lines (this is the capture output;
  ready at `book.verified`). Scope to one doc with `&uploaded_doc_uuid={doc_uuid}`.
- Header fields (account holder, statement period, etc.) come from each form's
  `uniqueness_values` in the `classification-summary` response.
- `GET /v2/book/{uuid}/enriched_txns` is the **analytics-grade** version (counterparty,
  revenue/expense flags, categorization) — it's an *analysis* endpoint (step 5), not capture.

## Analysis endpoints (step 5)

- `GET /v2/book/{book_uuid}/summary` — monthly revenue/expense/net, daily balances, top counterparties.
- `GET /v2/book/{book_uuid}/enriched_txns` — categorized line items.
- `GET /v2/book/{book_uuid}/cash_flow_features` — the wide underwriting feature set (hundreds of metrics).

## Consistent output file

Write all results into one JSON document per book:

```json
{
  "book":           {"pk": 0, "uuid": "", "name": "", "book_class": "INSTANT"},
  "product_type":   "SMB",
  "classification": { "...": "classification-summary response" },
  "capture":        { "...": "/v1/transaction response (txns)" },
  "analysis": {
    "summary":            { "...": "" },
    "enriched_txns":      { "...": "" },
    "cash_flow_features": { "...": "" }
  },
  "detect":         { "...": "/v2/detect/book/{uuid}/signals response" },
  "_meta": {"generated_at": "ISO-8601", "events_received": [], "endpoints_called": []}
}
```

## Webhooks (production) vs polling

Drive steps 3–6 off webhooks (`book.classified`, `book.verified`, `book.completed`,
`book.detect.signal_found`). Register org-level via `POST /v1/account/settings/webhook`,
then subscribe events in the dashboard. Read `event_name` (not `event_type`) and verify
the HMAC-SHA256 signature over the raw body. If you can't receive callbacks (local dev),
poll `GET /v1/book/status?book_uuid={uuid}` until `book_status="VERIFIED"`, then poll an
analytics endpoint until it stops returning `425`.

## Gotchas

- **`book_class` is set at creation and can't change.** `INSTANT` = machine-only; `COMPLETE`
  = human-in-the-loop. The document types an org can process are configured **per org**,
  not by `book_class` — unsupported types are rejected (`status=REJECTED`).
- ISO applications are **not** captured under `INSTANT` (`rejection_reason="INSTANT NOT SUPPORTED"`);
  use `COMPLETE` or `INSTANT_CLASSIFY_ISO_CAPTURE` if the book includes an ISO app.
- Most responses are envelopes returning HTTP 200 even on logical errors — check the
  envelope `status`/`code`, not just the HTTP status.
