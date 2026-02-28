"""MCP integrations: Clinical Protocols, Hospital Systems, ABDM/EHR, Telemedicine."""

from cdss.services.mcp.abdm_ehr import AbdmEhrClient
from cdss.services.mcp.clinical_protocols import ClinicalProtocolsMCP
from cdss.services.mcp.hospital_systems import HospitalSystemsMCP
from cdss.services.mcp.telemedicine import TelemedicineMCP

__all__ = [
    "ClinicalProtocolsMCP",
    "HospitalSystemsMCP",
    "AbdmEhrClient",
    "TelemedicineMCP",
]
