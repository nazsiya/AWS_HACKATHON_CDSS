"""
Single Lambda entrypoint for API Gateway: routes by path to agent handlers.
"""

import json
from typing import Any

from cdss.api.handlers import engagement, patient, resource, scheduling, surgery, supervisor


ROUTES = {
    "/cdss/supervisor": supervisor,
    "/cdss/patient": patient,
    "/cdss/surgery": surgery,
    "/cdss/resource": resource,
    "/cdss/scheduling": scheduling,
    "/cdss/engagement": engagement,
}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route by path to the correct agent handler."""
    path = (event.get("path") or event.get("rawPath") or "").strip("/")
    # Support with or without leading slash
    path_key = "/" + path if not path.startswith("/") else path
    # Match longest prefix
    module = None
    for route, mod in sorted(ROUTES.items(), key=lambda x: -len(x[0])):
        if path_key.startswith(route) or path_key == route.strip("/"):
            module = mod
            break
    if not module:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "NotFound", "path": path_key}),
        }
    return module.handler(event, context)
