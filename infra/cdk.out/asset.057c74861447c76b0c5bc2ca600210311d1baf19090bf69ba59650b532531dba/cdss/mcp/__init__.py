# MCP adapter layer for Hospital Systems and ABDM EHR
# Export adapter API only; events/schemas can be added when async MCP publish is implemented.

from cdss.mcp.adapter import get_abdm_record, get_hospital_data

__all__ = [
    "get_abdm_record",
    "get_hospital_data",
]
