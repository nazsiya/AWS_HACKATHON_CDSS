"""
CDSS Shared Utilities — Response Builder
Standardized Lambda response formatting.
"""

import json
from typing import Optional


def success_response(body: dict, status_code: int = 200) -> dict:
    """Build a successful API Gateway Lambda response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body),
    }


def error_response(message: str, status_code: int = 500, error_code: Optional[str] = None) -> dict:
    """Build an error API Gateway Lambda response."""
    body = {
        "error": True,
        "message": message,
    }
    if error_code:
        body["error_code"] = error_code

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body),
    }


def agent_response(content: str, agent_name: str, metadata: Optional[dict] = None) -> dict:
    """Build a standardized agent response."""
    response = {
        "agent": agent_name,
        "content": content,
        "type": "agent_response",
    }
    if metadata:
        response["metadata"] = metadata
    return response
