"""
API middleware: CORS, JWT validation, request logging.
Used by Lambda handlers and API Gateway authorizers.
"""

import json
from typing import Any, Callable

from cdss.core.logging import get_logger

logger = get_logger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Request-ID",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def with_cors(handler: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Attach CORS headers to Lambda response."""

    def wrapped(event: dict[str, Any], context: Any) -> dict[str, Any]:
        if event.get("httpMethod") == "OPTIONS":
            return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}
        response = handler(event, context)
        response.setdefault("headers", {}).update(CORS_HEADERS)
        return response

    return wrapped


def with_request_logging(
    handler: Callable[..., dict[str, Any]]
) -> Callable[..., dict[str, Any]]:
    """Log request ID and path for audit (DISHA)."""

    def wrapped(event: dict[str, Any], context: Any) -> dict[str, Any]:
        request_id = event.get("requestContext", {}).get("requestId", "")
        path = event.get("path", event.get("rawPath", ""))
        logger.info("request", extra={"requestId": request_id, "path": path})
        return handler(event, context)

    return wrapped


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON body from API Gateway event."""
    body = event.get("body") or "{}"
    if isinstance(body, str):
        return json.loads(body)
    return body
