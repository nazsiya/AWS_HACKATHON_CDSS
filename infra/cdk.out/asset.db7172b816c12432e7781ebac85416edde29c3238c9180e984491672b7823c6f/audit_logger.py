"""
CDSS Shared Utilities — Audit Logger
Provides DISHA-aligned auditing to RDS (Aurora) and DynamoDB (Session Store).
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from cdss.db.session import get_session
from cdss.db.models import AuditLog
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Unified logger for clinical and system actions.
    Writes to RDS 'audit_log' table for formal compliance and 
    updates DynamoDB session context for real-time tracking.
    """

    def __init__(self, session_manager: Optional[SessionManager] = None):
        self.session_manager = session_manager or SessionManager()

    def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> None:
        """
        Log an action to both RDS and the session manager.
        """
        # 1. Log to RDS for formal audit (DISHA compliance)
        try:
            with get_session() as session:
                audit_entry = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource=f"{resource_type}:{resource_id}" if resource_id else resource_type,
                    details=details or {},
                    timestamp=datetime.utcnow()
                )
                session.add(audit_entry)
                # Commit is handled by the get_session context manager
            logger.info(f"Audit record persisted to RDS: {action} on {resource_type}:{resource_id}")
        except Exception as e:
            logger.error(f"Failed to write to RDS audit log: {e}")

        # 2. Update Session Manager if session_id is provided
        if session_id:
            try:
                # We reuse SessionManager's add_message or record_routing as appropriate
                # For general actions, we can add a system message
                log_msg = f"[Audit]: {action} on {resource_type}"
                if resource_id:
                    log_msg += f" ({resource_id})"
                
                self.session_manager.add_message(
                    session_id=session_id,
                    role="system",
                    text=log_msg,
                    agent="AuditLogger"
                )
            except Exception as e:
                logger.warn(f"Failed to update session with audit info: {e}")

    def log_routing(
        self,
        session_id: str,
        intent: str,
        target_agent: str,
        doctor_id: str,
        patient_id: Optional[str] = None
    ) -> None:
        """
        Specialized method for logging supervisor routing decisions.
        """
        # Log to RDS
        self.log_action(
            user_id=doctor_id,
            action=f"ROUTE_TO_{target_agent.upper()}",
            resource_type="PATIENT",
            resource_id=patient_id,
            details={"intent": intent, "session_id": session_id},
            session_id=session_id
        )

        # Log to DynamoDB session (for agent context)
        try:
            self.session_manager.record_routing(session_id, intent, target_agent)
        except Exception as e:
            logger.warn(f"Failed to record routing in SessionManager: {e}")
