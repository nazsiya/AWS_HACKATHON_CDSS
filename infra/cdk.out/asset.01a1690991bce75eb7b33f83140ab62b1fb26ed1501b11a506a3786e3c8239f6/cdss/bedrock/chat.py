"""
Bedrock chat helpers used by Supervisor/router fallbacks.

If Bedrock config is not available (no `BEDROCK_CONFIG_SECRET_NAME`), the functions
return safe stub responses instead of raising.
If the configured model (e.g. Claude) fails, falls back to Nova Lite.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


SAFETY_DISCLAIMER = (
    "AI is for clinical support only. All decisions require qualified medical judgment."
)

# Fallback when primary model (e.g. Claude) fails (model not enabled, wrong region, etc.)
FALLBACK_MODEL_ID = "apac.amazon.nova-lite-v1:0"
_ANTHROPIC_PREFIX = "anthropic."


@dataclass(frozen=True)
class ChatResult:
    reply: str
    safety_disclaimer: str = SAFETY_DISCLAIMER
    message: str | None = None


def _load_bedrock_config() -> tuple[str, str] | None:
    secret_name = os.environ.get("BEDROCK_CONFIG_SECRET_NAME", "").strip()
    if not secret_name:
        return None
    try:
        import boto3

        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        raw = sm.get_secret_value(SecretId=secret_name).get("SecretString", "{}")
        cfg = json.loads(raw)
        model_id = (cfg.get("model_id") or FALLBACK_MODEL_ID).strip()
        bedrock_region = cfg.get("region") or region
        # Force Nova Lite when Anthropic models aren't enabled in this region/account.
        # This avoids slow failures + fallback on every request.
        if model_id.lower().startswith(_ANTHROPIC_PREFIX):
            model_id = FALLBACK_MODEL_ID
        return model_id, bedrock_region
    except Exception:
        return None


def _converse_reply(
    client,
    model_id: str,
    system_text: str,
    messages: list,
    max_tokens: int = 600,
    temperature: float = 0.2,
) -> str:
    """Call Bedrock Converse with the given model; return reply text or raise."""
    resp = client.converse(
        modelId=model_id,
        system=[{"text": system_text}],
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    content = resp.get("output", {}).get("message", {}).get("content", []) or []
    text = next((c.get("text", "") for c in content if isinstance(c, dict) and c.get("text")), "").strip()
    return text or "OK"


def invoke_chat(prompt: str) -> ChatResult:
    cfg = _load_bedrock_config()
    if cfg is None:
        return ChatResult(
            reply="Bedrock is not configured. Set BEDROCK_CONFIG_SECRET_NAME to enable AI responses.",
            message="BedrockUnavailable",
        )
    model_id, bedrock_region = cfg
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=bedrock_region)
        system = (
            "You are a clinical decision support assistant. "
            "Be conservative, avoid definitive diagnosis, and recommend clinician review when uncertain."
        )
        messages = [{"role": "user", "content": [{"text": prompt[:6000]}]}]
        reply = _converse_reply(client, model_id, system, messages, max_tokens=400, temperature=0.1)
        return ChatResult(reply=reply)
    except Exception as exc:
        if model_id != FALLBACK_MODEL_ID:
            try:
                import boto3

                client = boto3.client("bedrock-runtime", region_name=bedrock_region)
                system = (
                    "You are a clinical decision support assistant. "
                    "Be conservative, avoid definitive diagnosis, and recommend clinician review when uncertain."
                )
                messages = [{"role": "user", "content": [{"text": prompt[:6000]}]}]
                reply = _converse_reply(client, FALLBACK_MODEL_ID, system, messages, max_tokens=400, temperature=0.1)
                return ChatResult(reply=reply)
            except Exception:
                pass
        hint = str(exc).strip()[:120].replace("\n", " ")
        reply = "AI is temporarily unavailable."
        if hint and "temporarily unavailable" not in hint.lower():
            reply += f" ({hint})"
        return ChatResult(reply=reply, message=str(exc))


def invoke_chat_multi_turn(messages_list: list) -> ChatResult:
    """
    Multi-turn conversational chat. messages_list: [{"role": "user"|"assistant", "text": "..."}, ...].
    Builds Bedrock Converse messages and returns the latest reply.
    """
    cfg = _load_bedrock_config()
    if cfg is None:
        return ChatResult(
            reply="Bedrock is not configured. Set BEDROCK_CONFIG_SECRET_NAME to enable AI responses.",
            message="BedrockUnavailable",
        )
    if not messages_list or not isinstance(messages_list, list):
        return ChatResult(reply="No conversation history provided.")
    model_id, bedrock_region = cfg
    system = (
        "You are a clinical decision support assistant for doctors. "
        "Be concise and structured. If data is missing, say what is missing and what to check next. "
        "Avoid definitive diagnosis; doctor-in-the-loop."
    )
    messages = []
    for m in messages_list[-20:]:  # last 20 turns to stay within context
        role = (m.get("role") or "user").strip().lower()
        if role not in ("user", "assistant"):
            role = "user"
        text = (m.get("text") or m.get("content") or str(m)).strip()[:4000]
        if not text:
            continue
        messages.append({"role": role, "content": [{"text": text}]})
    if not messages:
        return ChatResult(reply="No valid messages in conversation.")
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=bedrock_region)
        reply = _converse_reply(client, model_id, system, messages, max_tokens=450, temperature=0.1)
        return ChatResult(reply=reply)
    except Exception as exc:
        if model_id != FALLBACK_MODEL_ID:
            try:
                import boto3

                client = boto3.client("bedrock-runtime", region_name=bedrock_region)
                reply = _converse_reply(client, FALLBACK_MODEL_ID, system, messages, max_tokens=450, temperature=0.1)
                return ChatResult(reply=reply)
            except Exception:
                pass
        hint = str(exc).strip()[:120].replace("\n", " ")
        reply = "AI is temporarily unavailable."
        if hint and "temporarily unavailable" not in hint.lower():
            reply += f" ({hint})"
        return ChatResult(reply=reply, message=str(exc))


def invoke_chat_with_context(user_message: str, context_label: str, data: dict) -> ChatResult:
    """
    Provide a response grounded in supplied (already authorized) structured data.
    """
    cfg = _load_bedrock_config()
    if cfg is None:
        return ChatResult(
            reply=json.dumps({"context": context_label, "data": data}, default=str)[:2000],
            message="BedrockUnavailable",
        )
    model_id, bedrock_region = cfg
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=bedrock_region)
        system = (
            "You are a clinical decision support assistant. "
            "Answer only using the provided structured context. If information is missing, say so and suggest next checks."
        )
        context_json = json.dumps(data, ensure_ascii=False, default=str)
        prompt = (
            f"Context label: {context_label}\n"
            f"Context JSON:\n{context_json[:12000]}\n\n"
            f"User question: {user_message[:1200]}"
        )
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        reply = _converse_reply(client, model_id, system, messages, max_tokens=500, temperature=0.1)
        return ChatResult(reply=reply)
    except Exception as exc:
        if model_id != FALLBACK_MODEL_ID:
            try:
                import boto3

                client = boto3.client("bedrock-runtime", region_name=bedrock_region)
                system = (
                    "You are a clinical decision support assistant. "
                    "Answer only using the provided structured context. If information is missing, say so and suggest next checks."
                )
                context_json = json.dumps(data, ensure_ascii=False, default=str)
                prompt = (
                    f"Context label: {context_label}\n"
                    f"Context JSON:\n{context_json[:12000]}\n\n"
                    f"User question: {user_message[:1200]}"
                )
                messages = [{"role": "user", "content": [{"text": prompt}]}]
                reply = _converse_reply(client, FALLBACK_MODEL_ID, system, messages, max_tokens=500, temperature=0.1)
                return ChatResult(reply=reply)
            except Exception:
                pass
        hint = str(exc).strip()[:120].replace("\n", " ")
        reply = "AI is temporarily unavailable."
        if hint and "temporarily unavailable" not in hint.lower():
            reply += f" ({hint})"
        return ChatResult(reply=reply, message=str(exc))
