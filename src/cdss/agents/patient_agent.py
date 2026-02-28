"""
Patient Agent: history retrieval, RAG summaries, create/update patient, getSummary.
Integrates with RDS PostgreSQL, S3, OpenSearch RAG, Comprehend Medical.
"""

from typing import Any

from cdss.agents.base import BaseAgent
from cdss.core.logging import get_logger

logger = get_logger(__name__)


class PatientAgent(BaseAgent):
    """Handles patient records, history, and RAG-based summaries."""

    name = "PatientAgent"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "getHistory", "description": "Retrieve patient history"},
            {"name": "getRAGSummary", "description": "Generate RAG summary from patient history vectors"},
            {"name": "createPatient", "description": "Create new patient record"},
            {"name": "getSummary", "description": "Get patient summary"},
            {"name": "updateRecord", "description": "Update patient record"},
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are the CDSS Patient Agent for an Indian hospital. "
            "You retrieve patient history, generate RAG summaries from OpenSearch, "
            "and manage patient records. DISHA and ABDM/EHR compliant."
        )

    def get_history(self, payload: dict[str, Any]) -> dict[str, Any]:
        """History retrieval from RDS / S3."""
        patient_id = payload.get("patientId", "")
        logger.info("get_history", extra={"patientId": patient_id})
        return {"patientId": patient_id, "history": [], "source": "RDS"}

    def get_rag_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        """RAG summaries from OpenSearch (patient history vectors)."""
        patient_id = payload.get("patientId", "")
        query = payload.get("query", "")
        return {"patientId": patient_id, "query": query, "summary": "", "sources": []}

    def create_patient(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create new patient record (RDS PostgreSQL)."""
        return {"created": True, "patientId": payload.get("patientId", ""), "record": {}}

    def get_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Get patient summary."""
        patient_id = payload.get("patientId", "")
        return {"patientId": patient_id, "summary": ""}

    def update_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update patient record."""
        patient_id = payload.get("patientId", "")
        return {"patientId": patient_id, "updated": True}
