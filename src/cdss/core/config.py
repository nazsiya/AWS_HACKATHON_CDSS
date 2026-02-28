"""
CDSS configuration (env-based).
Secrets from AWS Secrets Manager; region ap-south-1.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    """Application config from environment."""

    aws_region: str = os.environ.get("AWS_REGION", "ap-south-1")
    stage: str = os.environ.get("STAGE", "dev")
    bedrock_model_id: str = os.environ.get(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
    )
    opensearch_endpoint: Optional[str] = os.environ.get("OPENSEARCH_ENDPOINT")
    dynamodb_sessions_table: str = os.environ.get("DYNAMODB_SESSIONS_TABLE", "cdss-sessions")
    dynamodb_medication_table: str = os.environ.get(
        "DYNAMODB_MEDICATION_TABLE", "cdss-medication-schedules"
    )
    s3_bucket_documents: str = os.environ.get("S3_BUCKET_DOCUMENTS", "cdss-medical-documents")
    s3_bucket_corpus: str = os.environ.get("S3_BUCKET_CORPUS", "cdss-knowledge-corpus")
    event_bus_name: str = os.environ.get("EVENT_BUS_NAME", "cdss-events")
    pinpoint_app_id: Optional[str] = os.environ.get("PINPOINT_APP_ID")
    disha_audit_log_group: str = os.environ.get("DISHA_AUDIT_LOG_GROUP", "/cdss/disha-audit")


def get_config() -> Config:
    """Return singleton-like config (create new each time; override with caching if needed)."""
    return Config()
