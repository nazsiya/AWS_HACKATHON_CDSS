"""
Amazon Transcribe: speech-to-text for voice interface.
"""

from typing import Optional

from cdss.core.config import get_config
from cdss.core.logging import get_logger

logger = get_logger(__name__)


def start_transcription_job(
    media_uri: str,
    language_code: str = "en-IN",
    job_name: Optional[str] = None,
) -> str:
    """Start Transcribe job; returns job name."""
    import boto3
    import uuid

    config = get_config()
    client = boto3.client("transcribe", region_name=config.aws_region)
    name = job_name or f"cdss-{uuid.uuid4().hex[:12]}"
    client.start_transcription_job(
        TranscriptionJobName=name,
        Media={"MediaFileUri": media_uri},
        LanguageCode=language_code,
    )
    return name


def get_transcription_result(job_name: str) -> str:
    """Get transcript text from completed job."""
    import boto3

    config = get_config()
    client = boto3.client("transcribe", region_name=config.aws_region)
    job = client.get_transcription_job(TranscriptionJobName=job_name)
    transcript_uri = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    # Fetch URI and parse JSON for transcript text
    import urllib.request
    import json
    with urllib.request.urlopen(transcript_uri) as r:
        data = json.loads(r.read().decode())
    return data.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")
