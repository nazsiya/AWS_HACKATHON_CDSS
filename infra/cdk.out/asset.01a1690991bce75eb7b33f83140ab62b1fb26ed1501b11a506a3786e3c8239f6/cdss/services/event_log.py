"""
Inter-agent event logging for CDSS (Req 8 audit – MCP event logs).

Logs every cross-agent call with correlation_id, source_agent, target_agent,
action, timestamp, success, and duration_ms. Stored in RDS for audit trail.

Per project-conventions.mdc: structured messages with correlationId;
no PHI in logs; audit trails for clinically relevant actions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def log_agent_event(
    source_agent: str,
    target_agent: str,
    action: str,
    correlation_id: Optional[str] = None,
    success: bool = True,
    duration_ms: int = 0,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Log an inter-agent communication event for audit.

    Args:
        source_agent: Calling agent (e.g. "supervisor", "patient_agent")
        target_agent: Target agent or service (e.g. "surgery_agent", "mcp_adapter")
        action: Action performed (e.g. "get_hospital_data", "classify_intent")
        correlation_id: Unique ID linking related events; auto-generated if None
        success: Whether the action succeeded
        duration_ms: Time taken in milliseconds
        context: Additional structured data (no PHI)

    Returns:
        correlation_id for chaining
    """
    cid = correlation_id or str(uuid.uuid4())

    # Persist to RDS
    _persist_event_log(cid, source_agent, target_agent, action, success, duration_ms, context)

    # Structured log (no PHI)
    logger.info(
        "AgentEvent source=%s target=%s action=%s success=%s duration_ms=%d",
        source_agent, target_agent, action, success, duration_ms,
        extra={
            "correlation_id": cid,
            "source_agent": source_agent,
            "target_agent": target_agent,
            "action": action,
            "success": success,
            "duration_ms": duration_ms,
        },
    )

    return cid


def _persist_event_log(
    correlation_id: str,
    source_agent: str,
    target_agent: str,
    action: str,
    success: bool,
    duration_ms: int,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist event to RDS agent_event_log table. Fails silently if DB unavailable."""
    try:
        from cdss.db.session import get_session
        from cdss.db.models import AgentEventLog

        with get_session() as session:
            entry = AgentEventLog(
                correlation_id=correlation_id,
                source_agent=source_agent,
                target_agent=target_agent,
                action=action,
                success=success,
                duration_ms=duration_ms,
                context=context or {},
                created_at=datetime.now(timezone.utc),
            )
            session.add(entry)
            session.flush()
    except Exception as e:
        logger.debug("Event log persistence failed (non-fatal): %s", e)
