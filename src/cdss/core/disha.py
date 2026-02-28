"""
DISHA compliance helpers: audit logging, consent, data handling.
Ref: National Digital Health Mission / ABDM guidelines.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from cdss.core.config import get_config
from cdss.core.logging import get_logger

logger = get_logger(__name__)


def audit_log(
    action: str,
    resource_type: str,
    resource_id: str,
    actor_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> None:
    """
    Emit DISHA audit log (to CloudWatch log group or EventBridge).
    AES-256 encryption at rest via CloudWatch.
    """
    config = get_config()
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "resourceType": resource_type,
        "resourceId": resource_id,
        "actorId": actor_id,
        "requestId": request_id,
        "details": details or {},
        "logGroup": config.disha_audit_log_group,
    }
    logger.info("disha_audit", extra=payload)
    # Optional: put_events to EventBridge for central audit store
    # boto3.client('events').put_events(Entries=[...])


def mask_phi(text: str) -> str:
    """Mask PHI for logs (do not log raw PII)."""
    if not text or len(text) < 4:
        return "***"
    return text[:2] + "*" * (len(text) - 3) + text[-1] if len(text) > 3 else "***"
