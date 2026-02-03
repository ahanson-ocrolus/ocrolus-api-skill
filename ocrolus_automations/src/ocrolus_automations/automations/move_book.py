"""
Move-book automation: copy a book from Org1 to Org2 (or any source/target orgs).

Steps:
1) Auth to source org
2) GET book status for source book; extract doc UUIDs + names (configurable path)
3) Auth to target org
4) Create target book (unless dry-run)
5) For each doc: stream download from source -> spooled buffer -> upload to target (no disk persist)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.log_config import get_logger
from ocrolus_automations.utils.streams import SpooledTransfer, stream_copy

logger = get_logger(__name__)

# Default JSON paths to extract doc list from GET /v1/book/status response.
# Override via extract_docs_from_status() or env/config if your API shape differs.
DEFAULT_DOCS_PATH_KEYS = ["documents", "docs", "document_list"]


def extract_docs_from_status(
    status: dict[str, Any],
    doc_list_paths: list[str] | None = None,
    doc_uuid_key: str = "uuid",
    doc_name_key: str = "name",
) -> list[tuple[str, str]]:
    """
    Extract (doc_uuid, doc_name) list from book status JSON.
    Tries each key in doc_list_paths (default: documents, docs, document_list).
    Logs top-level keys once for debugging if extraction fails.
    """
    paths = doc_list_paths or DEFAULT_DOCS_PATH_KEYS
    for key in paths:
        val = status.get(key)
        if isinstance(val, list) and val:
            out: list[tuple[str, str]] = []
            for i, item in enumerate(val):
                if not isinstance(item, dict):
                    continue
                uuid_val = item.get(doc_uuid_key) or item.get("doc_uuid") or item.get("id")
                name_val = item.get(doc_name_key) or item.get("filename") or item.get("file_name") or f"doc_{i}"
                if uuid_val:
                    out.append((str(uuid_val), str(name_val)))
            if out:
                return out
    # Debug: log raw keys so user can plug in correct path
    logger.debug(
        "Book status top-level keys (use these to configure doc extraction): %s",
        list(status.keys()),
    )
    return []


@dataclass
class MoveBookResult:
    success: bool
    failures: list[str]
    target_book_uuid: str | None
    created_target_book: bool
    total_docs: int
    transferred_docs: int


def run_move_book(
    source_book_uuid: str,
    target_book_name: str,
    org_source: str = "org1",
    org_target: str = "org2",
    dry_run: bool = False,
    max_docs: int | None = None,
    client: OcrolusClient | None = None,
    doc_list_paths: list[str] | None = None,
    doc_uuid_key: str = "uuid",
    doc_name_key: str = "name",
    return_result: bool = False,
) -> int | MoveBookResult:
    """
    Run the move-book automation. Returns exit code (0 = success, non-zero if any doc failed).
    """
    cl = client or OcrolusClient()
    failures: list[str] = []

    # 1) Auth source
    cl.get_token(org_source)
    logger.info("Auth success (source org: %s)", org_source)

    # 2) Book status and doc list
    status = cl.get_book_status(source_book_uuid, org_source)
    # API may wrap payload in {"status", "message", "response": { ... docs ... }}
    payload = status.get("response", status) if isinstance(status, dict) else status
    docs = extract_docs_from_status(payload, doc_list_paths, doc_uuid_key, doc_name_key)
    if max_docs is not None:
        docs = docs[:max_docs]
    logger.info("Found %s docs", len(docs))
    if not docs:
        logger.warning("No documents to transfer")
        result = MoveBookResult(
            success=True,
            failures=[],
            target_book_uuid=None,
            created_target_book=False,
            total_docs=0,
            transferred_docs=0,
        )
        return result if return_result else 0

    # 3) Auth target
    cl.get_token(org_target)
    logger.info("Auth success (target org: %s)", org_target)

    # 4) Create target book (unless dry-run)
    target_book_uuid: str | None = None
    if not dry_run:
        target_book_uuid = cl.create_book(target_book_name, org_target)
        logger.info("Creating target book -> uuid=%s", target_book_uuid)
    else:
        logger.info("Dry-run: would create target book with name=%s", target_book_name)

    # 5) Transfer each doc
    transferred = 0
    for i, (doc_uuid, doc_name) in enumerate(docs, 1):
        logger.info("Transferring doc %s/%s (uuid=%s, name=%s)", i, len(docs), doc_uuid, doc_name)
        if dry_run:
            logger.info("Dry-run: would download %s and upload to target book", doc_uuid)
            continue
        try:
            resp = cl.download_document(doc_uuid, org_source)
            with SpooledTransfer() as spool:
                stream_copy(resp.iter_content(chunk_size=64 * 1024), spool)
                stream = spool.get_stream()
                filename = doc_name if "." in doc_name else f"{doc_name}.pdf"
                cl.upload_document(target_book_uuid or "", filename, stream, org_target)
            logger.info("Upload success for doc %s", doc_uuid)
            transferred += 1
        except Exception as e:
            logger.exception("Upload failure for doc %s: %s", doc_uuid, e)
            failures.append(f"{doc_uuid}: {e}")

    if failures:
        logger.error("Failures: %s", failures)
        result = MoveBookResult(
            success=False,
            failures=failures,
            target_book_uuid=target_book_uuid,
            created_target_book=bool(target_book_uuid),
            total_docs=len(docs),
            transferred_docs=transferred,
        )
        return result if return_result else 1

    result = MoveBookResult(
        success=True,
        failures=[],
        target_book_uuid=target_book_uuid,
        created_target_book=bool(target_book_uuid),
        total_docs=len(docs),
        transferred_docs=transferred if not dry_run else 0,
    )
    return result if return_result else 0
