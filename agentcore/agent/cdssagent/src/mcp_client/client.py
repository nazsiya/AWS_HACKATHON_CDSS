import os

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

def _normalize_mcp_endpoint(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    # AgentCore Gateway URLs are commonly provided without the MCP suffix.
    return u if u.rstrip("/").endswith("/mcp") else f"{u.rstrip('/')}/mcp"


DEFAULT_MCP_ENDPOINT = "https://mcp.exa.ai/mcp"

def get_streamable_http_mcp_client() -> MCPClient:
    """
    Returns an MCP Client compatible with Strands
    """
    endpoint = (
        os.getenv("CDSS_MCP_ENDPOINT")
        or os.getenv("AGENTCORE_GATEWAY_URL")
        or os.getenv("CDSS_AGENTCORE_GATEWAY_URL")
        or DEFAULT_MCP_ENDPOINT
    )
    endpoint = _normalize_mcp_endpoint(endpoint) if "gateway.bedrock-agentcore" in endpoint else endpoint
    return MCPClient(lambda: streamablehttp_client(endpoint))