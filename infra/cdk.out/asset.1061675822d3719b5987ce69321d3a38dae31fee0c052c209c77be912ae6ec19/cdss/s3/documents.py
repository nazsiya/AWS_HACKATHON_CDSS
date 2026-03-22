"""
S3 document helpers (transcripts, uploads).

Phase 1–2: store consultation transcripts as text objects.
"""

from __future__ import annotations

import os


def _bucket() -> str:
    b = os.environ.get("S3_BUCKET_DOCUMENTS", "").strip()
    if not b:
        raise ValueError("S3_BUCKET_DOCUMENTS is not configured")
    return b


def _safe_id(value: str) -> str:
    v = (value or "").strip()
    if not v or "/" in v or "\\" in v or ".." in v:
        raise ValueError("Invalid identifier")
    return v


def put_consultation_transcript(patient_id: str, visit_id: int, text: str) -> str:
    """
    Upload transcript text and return the S3 object key.
    """
    pid = _safe_id(patient_id)
    vid = int(visit_id)
    key = f"consultations/{pid}/{vid}.txt"
    import boto3

    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
    s3.put_object(
        Bucket=_bucket(),
        Key=key,
        Body=(text or "").encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
        ServerSideEncryption="AES256",
    )
    return key


def get_consultation_transcript(key: str) -> str:
    """
    Fetch transcript text by key.
    """
    if not key or ".." in key:
        raise ValueError("Invalid key")
    import boto3

    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
    resp = s3.get_object(Bucket=_bucket(), Key=key)
    body = resp["Body"].read()
    return body.decode("utf-8", errors="replace")

"""
Consultation transcript upload to S3 (documents bucket).
Returns S3 key on success, None when bucket not configured or on failure.
Per project-conventions: no PHI in logs.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

S3_BUCKET_DOCUMENTS_ENV = "S3_BUCKET_DOCUMENTS"


def put_consultation_transcript(patient_id: str, visit_id: int, transcript_text: str) -> str | None:
    """
    Upload consultation transcript text to S3. Key: consultations/{patient_id}/{visit_id}/{timestamp}.txt.
    Returns the S3 key (str) on success, None when bucket not set or upload fails.
    """
    bucket = os.environ.get(S3_BUCKET_DOCUMENTS_ENV)
    if not bucket or not bucket.strip():
        logger.debug("S3_BUCKET_DOCUMENTS not set; transcript upload skipped")
        return None
    if not (transcript_text or "").strip():
        return None
    try:
        import boto3
        from botocore.exceptions import ClientError

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"consultations/{patient_id}/{visit_id}/{ts}.txt"
        client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=transcript_text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        return key
    except ClientError as e:
        logger.warning("S3 put_consultation_transcript failed: %s", e.response.get("Error", {}).get("Code"))
        return None
    except Exception as e:
        logger.warning("Transcript upload error: %s", e)
        return None


def get_consultation_transcript(s3_key: str) -> str | None:
    """
    Download consultation transcript text from S3 by key.
    Returns transcript text or None when bucket not set or key not found.
    """
    bucket = os.environ.get(S3_BUCKET_DOCUMENTS_ENV)
    if not bucket or not bucket.strip() or not (s3_key or "").strip():
        return None
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        resp = client.get_object(Bucket=bucket, Key=s3_key)
        body = resp.get("Body")
        if body is None:
            return None
        return body.read().decode("utf-8")
    except ClientError as e:
        logger.warning("S3 get_consultation_transcript failed: %s", e.response.get("Error", {}).get("Code"))
        return None
    except Exception as e:
        logger.warning("Transcript download error: %s", e)
        return None
