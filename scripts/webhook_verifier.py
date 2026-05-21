"""
Ocrolus Webhook Signature Verifier
===================================

Standalone Flask handler for receiving and verifying Ocrolus webhook events.
Includes HMAC-SHA256 signature verification, event routing, and secret rotation.

Requirements:
    pip install flask

Usage:
    export OCROLUS_WEBHOOK_SECRET="your-secret-here"
    python webhook_verifier.py

    # Or import the verifier into your existing app:
    from webhook_verifier import verify_signature, OcrolusWebhookHandler
"""

import hashlib
import hmac
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Callable, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ocrolus-webhooks")


# =============================================================================
# SIGNATURE VERIFICATION
# =============================================================================

def verify_signature(
    body: bytes,
    timestamp: str,
    request_id: str,
    received_signature: str,
    secret: str,
) -> bool:
    """
    Verify Ocrolus webhook HMAC-SHA256 signature.

    Signed message format: "{timestamp}.{request_id}.{body}"

    Args:
        body: Raw request body bytes (NOT parsed JSON)
        timestamp: Webhook-Timestamp header value
        request_id: Webhook-Request-Id header value
        received_signature: Webhook-Signature header value
        secret: Your webhook secret

    Returns:
        True if signature matches.
    """
    signed_message = f"{timestamp}.{request_id}.".encode() + body
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_signature)


def verify_with_rotation(
    body: bytes,
    timestamp: str,
    request_id: str,
    received_signature: str,
    secrets: list[str],
) -> bool:
    """
    Verify signature against multiple secrets for zero-downtime rotation.

    During secret rotation, temporarily validate against both old and new secrets.
    """
    return any(
        verify_signature(body, timestamp, request_id, received_signature, s)
        for s in secrets
        if s
    )


def is_timestamp_valid(timestamp: str, max_age_seconds: int = 300) -> bool:
    """
    Check if webhook timestamp is within acceptable window.
    Rejects replayed webhooks older than max_age_seconds (default 5 minutes).
    """
    try:
        ts = int(timestamp)
        now = int(datetime.now(timezone.utc).timestamp())
        return abs(now - ts) <= max_age_seconds
    except (ValueError, TypeError):
        return False


# =============================================================================
# EVENT HANDLER REGISTRY
# =============================================================================

class OcrolusWebhookHandler:
    """
    Registry for webhook event handlers with signature verification.

    IMPORTANT: The event_type_field and event names used here must match
    your tenant's actual webhook payloads. Run validate_endpoints.py --webhooks
    to discover the correct field name and event strings before deploying.

    Usage:
        # After running: python validate_endpoints.py --webhooks
        # Suppose it reports: event type field = "event_type", events = ["doc.complete", ...]

        handler = OcrolusWebhookHandler(
            secret="your-secret",
            event_type_field="event_type",  # from validation output
        )

        @handler.on("doc.complete")  # use EXACT string from validation output
        def handle_doc_complete(event):
            print(f"Document ready: {event}")

        # In your Flask route:
        result = handler.process(request.headers, request.get_data())
    """

    def __init__(
        self,
        secret: Optional[str] = None,
        rotation_secret: Optional[str] = None,
        event_type_field: str = "event_type",
    ):
        """
        Args:
            secret: Webhook HMAC secret (or set OCROLUS_WEBHOOK_SECRET env var)
            rotation_secret: Old secret during rotation (or set OCROLUS_WEBHOOK_SECRET_OLD env var)
            event_type_field: The JSON field name Ocrolus uses for the event type
                in webhook payloads. Default is "event_type" but this is UNVALIDATED --
                run validate_endpoints.py --webhooks to confirm the actual field name.
        """
        self.secrets = [
            s for s in [
                secret or os.environ.get("OCROLUS_WEBHOOK_SECRET", ""),
                rotation_secret or os.environ.get("OCROLUS_WEBHOOK_SECRET_OLD", ""),
            ] if s
        ]
        self.event_type_field = event_type_field
        self._handlers: dict[str, list[Callable]] = {}
        self._default_handler: Optional[Callable] = None

    def on(self, event_type: str):
        """Decorator to register a handler for a specific event type."""
        def decorator(func: Callable):
            self._handlers.setdefault(event_type, []).append(func)
            return func
        return decorator

    def on_default(self, func: Callable):
        """Decorator to register a default handler for unmatched events."""
        self._default_handler = func
        return func

    def process(self, headers: dict, body: bytes) -> dict:
        """
        Verify signature and dispatch event to registered handlers.

        Returns:
            dict with 'status' ('ok', 'invalid_signature', 'stale_timestamp', 'error')
        """
        timestamp = headers.get("Webhook-Timestamp", "")
        request_id = headers.get("Webhook-Request-Id", "")
        signature = headers.get("Webhook-Signature", "")

        # Step 1: Verify timestamp freshness
        if not is_timestamp_valid(timestamp):
            logger.warning(f"Stale or invalid timestamp: {timestamp}")
            return {"status": "stale_timestamp"}

        # Step 2: Verify HMAC signature
        if not verify_with_rotation(body, timestamp, request_id, signature, self.secrets):
            logger.warning(f"Invalid signature for request {request_id}")
            return {"status": "invalid_signature"}

        # Step 3: Parse and dispatch
        try:
            event = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON body: {e}")
            return {"status": "error", "message": "Invalid JSON"}

        # Extract event type using the configured field name.
        # Also try common alternatives so events aren't silently dropped
        # if the field name doesn't match.
        event_type = event.get(self.event_type_field)
        if event_type is None:
            # Fallback: try other plausible field names
            for alt_key in ("event_type", "event_name", "type", "event", "eventType"):
                if alt_key in event and alt_key != self.event_type_field:
                    event_type = event[alt_key]
                    logger.warning(
                        f"Event type not found in field '{self.event_type_field}', "
                        f"but found in '{alt_key}' = '{event_type}'. "
                        f"Update event_type_field parameter to '{alt_key}'."
                    )
                    break
            else:
                event_type = "unknown"
                logger.warning(
                    f"Could not find event type in any known field. "
                    f"Payload keys: {list(event.keys())}. "
                    f"Run validate_endpoints.py --webhooks to discover the correct field name."
                )

        logger.info(f"Received event: {event_type} (request_id={request_id})")

        handlers = self._handlers.get(event_type, [])
        if handlers:
            for h in handlers:
                try:
                    h(event)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")
        elif self._default_handler:
            try:
                self._default_handler(event)
            except Exception as e:
                logger.error(f"Default handler error: {e}")
        else:
            logger.info(f"No handler registered for event: {event_type}")

        return {"status": "ok", "event_type": event_type}


# =============================================================================
# STANDALONE FLASK APP
# =============================================================================

def create_app():
    """Create a Flask app with Ocrolus webhook handling."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Flask is required: pip install flask")
        sys.exit(1)

    app = Flask(__name__)

    # CONFIGURE THESE after running: python validate_endpoints.py --webhooks
    # The field name and event strings below are PLACEHOLDERS that may not
    # match your tenant's actual payloads.
    EVENT_TYPE_FIELD = os.environ.get("OCROLUS_EVENT_TYPE_FIELD", "event_type")

    handler = OcrolusWebhookHandler(event_type_field=EVENT_TYPE_FIELD)

    # --- Register event handlers ---
    # IMPORTANT: Replace these event name strings with the canonical names
    # from your validate_endpoints.py --webhooks output.
    # These are UNVALIDATED PLACEHOLDERS.

    @handler.on("document.verification_complete")  # REPLACE with validated name
    def on_doc_complete(event):
        logger.info(f"Document verified: {event}")

    @handler.on("document.detect_succeeded")  # REPLACE with validated name
    def on_detect_complete(event):
        logger.info(f"Fraud detection complete: {event}")

    @handler.on("document.classification_succeeded")  # REPLACE with validated name
    def on_classification(event):
        logger.info(f"Classification complete: {event}")

    @handler.on("book.processing_complete")  # REPLACE with validated name
    def on_book_complete(event):
        logger.info(f"Book processing complete: {event}")

    @handler.on("book.copy.request_accepted")  # REPLACE with validated name
    def on_copy_accepted(event):
        logger.info(f"Book copy accepted: {event}")

    # The default handler catches ALL events that don't match above.
    # During initial setup, this is your safety net -- it will log the
    # actual event names Ocrolus sends, so you can update the handlers.
    @handler.on_default
    def on_unknown(event):
        logger.warning(
            f"Unhandled event: {event.get(EVENT_TYPE_FIELD, 'NO_FIELD')} "
            f"(all keys: {list(event.keys())})"
        )

    # --- Routes ---

    @app.route("/webhooks/ocrolus", methods=["POST"])
    def webhook_endpoint():
        result = handler.process(request.headers, request.get_data())

        if result["status"] == "invalid_signature":
            return jsonify({"error": "Invalid signature"}), 401
        if result["status"] == "stale_timestamp":
            return jsonify({"error": "Stale timestamp"}), 401

        # Always respond 200 quickly (within 5s timeout)
        return jsonify(result), 200

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting webhook verifier on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
