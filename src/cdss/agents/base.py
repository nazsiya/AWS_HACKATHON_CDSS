"""
Base agent interface for Bedrock multi-agent CDSS.
All domain agents extend this and use Claude 3 Haiku via Bedrock.
"""

from abc import ABC, abstractmethod
from typing import Any

from cdss.core.bedrock_client import get_bedrock_client
from cdss.core.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for CDSS agents (Patient, Surgery, Resource, Scheduling, Engagement)."""

    name: str = "BaseAgent"
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"

    def __init__(self) -> None:
        self._client = get_bedrock_client()

    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]:
        """Return list of tool definitions for this agent (Bedrock tool use)."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return system prompt defining agent role and DISHA context."""
        pass

    def invoke(self, user_message: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke Bedrock with system prompt + user message. Override for tool use."""
        # Placeholder: actual Bedrock Converse API / InvokeModel usage in implementation
        logger.info("invoke", extra={"agent": self.name, "message_len": len(user_message)})
        return {"response": "", "metadata": {"agent": self.name}}
