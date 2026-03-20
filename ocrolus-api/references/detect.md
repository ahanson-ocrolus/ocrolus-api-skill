# Ocrolus Detect -- Fraud Detection Reference

> Source: https://docs.ocrolus.com/docs/detect, authenticity-score, detect-signals, signal-visualization

## Overview

Detect is Ocrolus's ML-based fraud detection system. It identifies suspicious document modifications via **signals** and returns **authenticity scores** with **reason codes** for automated decisioning.

## Supported Document Types

- Bank statements
- Pay stubs
- W-2 forms

Other document types are NOT processed with Detect.

## API Endpoints (v2)

| Operation | Method | Path |
|-----------|--------|------|
| Book-Level Fraud Signals | GET | `/v2/detect/book/{book_uuid}/signals` |
| Document-Level Fraud Signals | GET | `/v2/detect/document/{doc_uuid}/signals` |
| Signal Visualization | GET | `/v2/detect/visualization/{visualization_uuid}` |

**IMPORTANT:** These are the current endpoints. The legacy paths (`/v1/.../fraud-signals`) and the Suspicious Activity Flags endpoint (`/v1/book/{book_uuid}/suspicious-activity-flags`) are deprecated.

## Authenticity Score

Every processed document receives an **Authenticity Score** (0-100):

| Score Range | Status | Interpretation |
|-------------|--------|---------------|
| 0-30 | VERY LOW | Strong indicators of fraud; immediate review required |
| 31-60 | LOW | Significant fraud indicators; manual review recommended |
| 61-80 | MEDIUM | Some indicators present; may warrant review |
| 81-100 | HIGH | Likely authentic; minimal review needed |

**How it's computed:** Weighs the severity of detected signals against confidence levels. Considers both what was tampered with and how confident the model is in the signal.

**Threshold guidance:**
- Scores below 61 are categorized as "low authenticity"
- Set thresholds based on your risk tolerance
- Lower threshold = more conservative (any tampering triggers review)
- Higher threshold = more permissive (only strong signals trigger review)

**Book-level display:** The Dashboard shows the **lowest** Authenticity Score of any document in the Book, so teams can prioritize the riskiest documents first.

**Availability:** Authenticity Scores are available for documents processed after November 15, 2023. Earlier books will not have scores.

## Reason Codes

Each document's assessment includes reason codes with three components:

| Component | Example | Description |
|-----------|---------|-------------|
| Code ID | `110-H` | Distinctive identifier for the signal type |
| Description | "bank statement account info tampered" | Human-readable explanation |
| Confidence | HIGH / MEDIUM / LOW | Model's certainty in the detection |

**Usage in automation:**
- Build rule-based decisioning using code IDs
- Route documents based on confidence levels (e.g., auto-reject HIGH confidence tampering, manual review for MEDIUM)
- Combine with Authenticity Score for layered decisioning

## Signal Types

Detect classifies signals into two categories:

### File Origin Signals
Evaluate whether a document was issued by a legitimate financial institution or payroll provider. These assess the document's source authenticity.

### File Tampering Signals
Identify alterations made to a document after it was initially generated. Displayed as colored overlays on document pages. Specific tampering categories:

| Signal Category | What It Detects |
|----------------|-----------------|
| Name/Address | Altered cardholder identification information |
| Account Numbers | Modified account or routing numbers |
| Dollar Amounts | Changed monetary values (balances, transactions) |
| Dates | Altered statement dates, transaction dates |
| Employer Info | Modified employer name, address, contact details |
| Payment Records | Altered transaction entries or payment amounts |
| Text Misalignment | Characters that don't align with surrounding text |
| Balance Reconciliation | Running balances that don't reconcile with transactions |
| Synthetic Paystub | Indicators of artificially generated pay stubs |

## Signal Visualization

The visualization endpoint returns an **image file** (not JSON) with fraud signal overlays:

```
GET /v2/detect/visualization/{visualization_uuid}
```

**Key details:**
- Returns a binary image with highlighted fraud regions
- `visualization_uuid` is obtained from the Book-Level or Document-Level signals response
- **Cannot be hotlinked** with `<img>` tags -- you must fetch and serve images yourself
- Can be fetched in-browser with JavaScript for display in your application

### Interpreting Visualizations
- Colored overlays highlight specific regions where tampering was detected
- Each overlay corresponds to a signal in the API response
- Signal metadata includes page numbers and coordinates for mapping

## Dashboard Status Icons

| Icon | Meaning |
|------|---------|
| Green circle | Uploaded successfully, no fraud signals |
| Red flag | Processed with fraud signals found |
| Green partial circle | Capture complete, Detect still processing |
| Gray hourglass | Still being processed |
| Red circle | Could not be processed |

## False Positive Considerations

Documents may show signals that aren't actual fraud:
- Legal name changes (marriage, etc.)
- Poor image conversion or scanning artifacts
- Non-standard fonts or formatting
- Bank-side formatting changes between statement periods

Always treat Detect results as indicators for review, not definitive fraud determinations.

## Integration Pattern

```python
# 1. Get book-level signals (overview)
signals = client.get_book_fraud_signals(book_uuid)

# 2. Check authenticity score
for doc in signals.get("documents", []):
    score = doc.get("authenticity_score", None)
    reason_codes = doc.get("reason_codes", [])

    if score is not None and score < 61:
        # Route to fraud analyst
        for code in reason_codes:
            print(f"  {code['code']}: {code['description']} ({code['confidence']})")

    # 3. Get visualizations for flagged documents
    for signal in doc.get("signals", []):
        viz_uuid = signal.get("visualization_uuid")
        if viz_uuid:
            image_bytes = client.get_fraud_visualization(viz_uuid)
            # Serve or store the image

# 4. Document-level detail when needed
doc_signals = client.get_document_fraud_signals(doc_uuid)
```

## Webhook Events for Detect

- `document.detect_succeeded` -- Detect processing completed for a document
- `document.detect_failed` -- Detect processing failed

Use these to trigger fraud review workflows without polling.
