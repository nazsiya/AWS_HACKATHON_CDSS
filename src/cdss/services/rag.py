"""
RAG service: OpenSearch for patient history vectors and knowledge base corpus.
S3 as knowledge base corpus source.
"""

from typing import Any, Optional

from cdss.core.config import get_config
from cdss.core.logging import get_logger

logger = get_logger(__name__)


def search_patient_history(
    patient_id: str,
    query: str,
    top_k: int = 5,
    index_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Search OpenSearch index for patient history vectors (RAG).
    Returns list of relevant chunks with scores.
    """
    config = get_config()
    if not config.opensearch_endpoint:
        logger.warning("OPENSEARCH_ENDPOINT not set; returning empty RAG results")
        return []
    # TODO: use opensearch-py to query vector index
    return []


def get_knowledge_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Retrieve chunks from knowledge base corpus (S3 + OpenSearch)."""
    # TODO: embed query, search corpus index
    return []
