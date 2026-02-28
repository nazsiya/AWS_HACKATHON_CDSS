"""
Amazon Translate: multilingual support (Hindi, Tamil, Telugu, Bengali).
"""

from cdss.core.config import get_config
from cdss.core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_LANGUAGES = {"en", "hi", "ta", "te", "bn"}


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using Amazon Translate."""
    if source_lang == target_lang or target_lang not in SUPPORTED_LANGUAGES:
        return text
    import boto3

    config = get_config()
    client = boto3.client("translate", region_name=config.aws_region)
    result = client.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang,
    )
    return result.get("TranslatedText", text)
