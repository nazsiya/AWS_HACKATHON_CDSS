"""
Comprehend Medical: entity extraction (NER) from medical text.
"""

from typing import Any

from cdss.core.config import get_config
from cdss.core.logging import get_logger

logger = get_logger(__name__)


def extract_medical_entities(text: str) -> dict[str, Any]:
    """
    Call Amazon Comprehend Medical DetectEntitiesV2.
    Returns entities: medications, conditions, procedures, etc.
    """
    import boto3

    config = get_config()
    client = boto3.client("comprehendmedical", region_name=config.aws_region)
    try:
        out = client.detect_entities_v2(Text=text)
        return {"entities": out.get("Entities", []), "unmapped": out.get("UnmappedAttributes", [])}
    except Exception as e:
        logger.exception("comprehend_medical_error", extra={"error": str(e)})
        return {"entities": [], "unmapped": [], "error": str(e)}
