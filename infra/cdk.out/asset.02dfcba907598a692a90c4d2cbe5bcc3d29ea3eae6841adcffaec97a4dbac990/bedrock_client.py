"""
CDSS Shared Utilities — Bedrock Client
Wrapper around Amazon Bedrock Runtime. Uses Converse API for Nova; invoke_model for Claude.
"""

import json
import logging
from typing import Optional

import boto3
from botocore.config import Config

from .config import AWS_REGION, BEDROCK_MODEL_ID, BEDROCK_MAX_TOKENS, BEDROCK_TEMPERATURE

logger = logging.getLogger(__name__)

# Use Converse API for Amazon Nova models (invoke_model with Anthropic body is Claude-only)
def _is_nova_model(model_id: str) -> bool:
    return "nova" in (model_id or "").lower()


class BedrockClient:
    """Client for invoking Amazon Bedrock (Claude or Nova)."""

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or BEDROCK_MODEL_ID
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                read_timeout=60,
            ),
        )

    def invoke(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[list] = None,
        max_tokens: int = BEDROCK_MAX_TOKENS,
        temperature: float = BEDROCK_TEMPERATURE,
    ) -> dict:
        """
        Invoke Bedrock. Uses Converse API for Nova; Claude Messages API for Claude.

        Returns:
            dict with 'content' (str), 'usage' (dict), 'stop_reason' (str)
        """
        if _is_nova_model(self.model_id):
            return self._invoke_converse(
                user_message, system_prompt, conversation_history, max_tokens, temperature
            )
        return self._invoke_claude(
            user_message, system_prompt, conversation_history, max_tokens, temperature
        )

    def _invoke_converse(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[list] = None,
        max_tokens: int = BEDROCK_MAX_TOKENS,
        temperature: float = BEDROCK_TEMPERATURE,
    ) -> dict:
        """Converse API (Nova and other models)."""
        system_content = [{"text": system_prompt}]
        messages = []
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": [{"text": msg.get("text", "")}],
                })
        messages.append({"role": "user", "content": [{"text": user_message}]})
        try:
            resp = self._client.converse(
                modelId=self.model_id,
                system=system_content,
                messages=messages,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                },
            )
            content_list = resp.get("output", {}).get("message", {}).get("content", []) or []
            text = next(
                (c.get("text", "") for c in content_list if isinstance(c, dict) and "text" in c),
                "",
            ).strip()
            usage = resp.get("usage", {}) or {}
            return {
                "content": text,
                "usage": {"inputTokens": usage.get("inputTokens"), "outputTokens": usage.get("outputTokens")},
                "stop_reason": resp.get("stopReason", "end_turn"),
                "model": self.model_id,
            }
        except Exception as e:
            logger.error("Bedrock Converse invocation failed: %s", e)
            raise

    def _invoke_claude(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[list] = None,
        max_tokens: int = BEDROCK_MAX_TOKENS,
        temperature: float = BEDROCK_TEMPERATURE,
    ) -> dict:
        """Claude via invoke_model (Anthropic message format)."""
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["text"]}],
                })
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": user_message}],
        })
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages,
        }
        try:
            response = self._client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            result = json.loads(response["body"].read())
            return {
                "content": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "stop_reason": result.get("stop_reason", "end_turn"),
                "model": self.model_id,
            }
        except Exception as e:
            logger.error("Bedrock Claude invocation failed: %s", e)
            raise

    def invoke_with_tools(
        self,
        user_message: str,
        system_prompt: str,
        tools: list,
        conversation_history: Optional[list] = None,
        max_tokens: int = BEDROCK_MAX_TOKENS,
    ) -> dict:
        """
        Invoke Bedrock with tool use. Uses Converse API for Nova; Claude Messages API for Claude.

        Returns:
            dict with 'content', 'tool_calls', 'stop_reason', 'usage'
        """
        if _is_nova_model(self.model_id):
            return self._invoke_with_tools_converse(
                user_message, system_prompt, tools, conversation_history, max_tokens
            )
        return self._invoke_with_tools_claude(
            user_message, system_prompt, tools, conversation_history, max_tokens
        )

    def _invoke_with_tools_converse(
        self,
        user_message: str,
        system_prompt: str,
        tools: list,
        conversation_history: Optional[list] = None,
        max_tokens: int = BEDROCK_MAX_TOKENS,
    ) -> dict:
        """Converse API with toolConfig for Nova."""
        tool_specs = []
        for t in tools:
            name = t.get("name", "")
            desc = t.get("description", "")
            schema = t.get("input_schema") or t.get("inputSchema") or {"type": "object", "properties": {}}
            if "input_schema" in t:
                schema = t["input_schema"]
            tool_specs.append({
                "toolSpec": {
                    "name": name,
                    "description": desc or name,
                    "inputSchema": {"json": schema},
                }
            })
        messages = []
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": [{"text": msg.get("text", "")}]})
        messages.append({"role": "user", "content": [{"text": user_message}]})
        try:
            resp = self._client.converse(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=messages,
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
                toolConfig={"tools": tool_specs, "toolChoice": {"auto": {}}},
            )
            content_list = resp.get("output", {}).get("message", {}).get("content", []) or []
            tool_calls = []
            text_content = ""
            for c in content_list:
                if isinstance(c, dict):
                    if "text" in c:
                        text_content += c.get("text", "")
                    if c.get("type") == "tool_use" or "toolUse" in c:
                        tu = c.get("toolUse", c)
                        tool_calls.append({
                            "id": tu.get("toolUseId", tu.get("id", "")),
                            "name": tu.get("name", ""),
                            "input": tu.get("input", {}),
                        })
            return {
                "content": text_content,
                "tool_calls": tool_calls,
                "stop_reason": resp.get("stopReason", "end_turn"),
                "usage": resp.get("usage", {}),
            }
        except Exception as e:
            logger.error("Bedrock Converse tool invocation failed: %s", e)
            raise

    def _invoke_with_tools_claude(
        self,
        user_message: str,
        system_prompt: str,
        tools: list,
        conversation_history: Optional[list] = None,
        max_tokens: int = BEDROCK_MAX_TOKENS,
    ) -> dict:
        """Claude via invoke_model with tools."""
        messages = []

        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["text"]}],
                })

        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": user_message}],
        })

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "system": system_prompt,
            "messages": messages,
            "tools": tools,
        }

        try:
            response = self._client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )

            result = json.loads(response["body"].read())

            tool_calls = []
            text_content = ""

            for block in result.get("content", []):
                if block["type"] == "text":
                    text_content += block["text"]
                elif block["type"] == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "name": block["name"],
                        "input": block["input"],
                    })

            return {
                "content": text_content,
                "tool_calls": tool_calls,
                "stop_reason": result.get("stop_reason", "end_turn"),
                "usage": result.get("usage", {}),
            }

        except Exception as e:
            logger.error("Bedrock tool invocation failed: %s", e)
            raise
