"""
CDSS Shared Utilities — DynamoDB Session Manager
Manages agent conversation sessions for context persistence.
"""

import json
import time
import uuid
import logging
from typing import Optional
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from .config import AWS_REGION, SESSIONS_TABLE

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class SessionManager:
    """Manages agent conversation sessions in DynamoDB."""

    def __init__(self, table_name: Optional[str] = None):
        self.table_name = table_name or SESSIONS_TABLE
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.table = dynamodb.Table(self.table_name)

    def create_session(self, doctor_id: str, patient_id: Optional[str] = None) -> dict:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        now = int(time.time())

        item = {
            "session_id": session_id,
            "doctor_id": doctor_id,
            "patient_id": patient_id or "general",
            "messages": [],
            "agent_routing": [],
            "created_at": now,
            "updated_at": now,
            "ttl": now + 86400,  # 24-hour TTL
            "status": "active",
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Created session {session_id} for doctor {doctor_id}")
            return item
        except ClientError as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve an existing session."""
        try:
            response = self.table.get_item(Key={"session_id": session_id})
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def add_message(self, session_id: str, role: str, text: str, agent: Optional[str] = None) -> None:
        """Add a message to the session history."""
        now = int(time.time())
        message = {
            "role": role,
            "text": text,
            "agent": agent,
            "timestamp": now,
        }

        try:
            self.table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET messages = list_append(if_not_exists(messages, :empty), :msg), updated_at = :now",
                ExpressionAttributeValues={
                    ":msg": [message],
                    ":empty": [],
                    ":now": now,
                },
            )
        except ClientError as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            raise

    def get_conversation_history(self, session_id: str, max_messages: int = 10) -> list:
        """Get recent conversation history for context."""
        session = self.get_session(session_id)
        if not session:
            return []
        messages = session.get("messages", [])
        return messages[-max_messages:]

    def record_routing(self, session_id: str, intent: str, target_agent: str) -> None:
        """Record an agent routing decision for auditing."""
        now = int(time.time())
        routing = {
            "intent": intent,
            "target_agent": target_agent,
            "timestamp": now,
        }

        try:
            self.table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET agent_routing = list_append(if_not_exists(agent_routing, :empty), :route), updated_at = :now",
                ExpressionAttributeValues={
                    ":route": [routing],
                    ":empty": [],
                    ":now": now,
                },
            )
        except ClientError as e:
            logger.error(f"Failed to record routing for session {session_id}: {e}")

    def close_session(self, session_id: str) -> None:
        """Mark a session as closed."""
        try:
            self.table.update_item(
                Key={"session_id": session_id},
                UpdateExpression="SET #s = :status, updated_at = :now",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":status": "closed",
                    ":now": int(time.time()),
                },
            )
        except ClientError as e:
            logger.error(f"Failed to close session {session_id}: {e}")
