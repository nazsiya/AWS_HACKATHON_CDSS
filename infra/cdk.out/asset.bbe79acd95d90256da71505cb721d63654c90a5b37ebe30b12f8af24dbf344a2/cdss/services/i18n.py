"""
Internationalization helpers: request language + translation.
Multilingual support for CDSS – Amazon Translate + Comprehend.
Provides translation and language detection for patient-facing content.
Supports: en, hi, ta, te, bn. Falls back gracefully when AWS services are unavailable.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# Configurable supported languages (ISO 639-1 codes)
DEFAULT_SUPPORTED_LANGUAGES = "en,hi,ta,te,bn"

# Language display names for UI
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}

# R7 / Phase 3.4: Approved medical terminology (en -> Hindi, Tamil) for consistent translation.
# Used by /api/ai/translate and agent responses. See docs/TERMINOLOGY.md.
APPROVED_TERMINOLOGY: dict[str, dict[str, str]] = {
    "en": {"hi": "", "ta": ""},  # source English
    "Hypertension": {"hi": "उच्च रक्तचाप", "ta": "உயர் இரத்த அழுத்தம்"},
    "Diabetes": {"hi": "मधुमेह", "ta": "சர்க்கரை நோய்"},
    "Medication": {"hi": "दवा", "ta": "மருந்து"},
    "Dosage": {"hi": "खुराक", "ta": "மருந்தளவு"},
    "Blood pressure": {"hi": "रक्तचाप", "ta": "இரத்த அழுத்தம்"},
    "Consultation": {"hi": "परामर्श", "ta": "ஆலோசனை"},
    "Patient": {"hi": "रोगी", "ta": "நோயாளி"},
    "Doctor": {"hi": "डॉक्टर", "ta": "மருத்துவர்"},
    "Surgery": {"hi": "शल्य चिकित्सा", "ta": "அறுவை சிகிச்சை"},
    "Prescription": {"hi": "नुस्खा", "ta": "மருந்து பட்டியல்"},
    "Follow-up": {"hi": "अनुवर्ती", "ta": "பின்தொடர்வு"},
    "Allergy": {"hi": "एलर्जी", "ta": "அலர்ஜி"},
    "Symptoms": {"hi": "लक्षण", "ta": "அறிகுறிகள்"},
    "Treatment": {"hi": "उपचार", "ta": "சிகிச்சை"},
}


def get_approved_terminology_for_lang(target_lang: str) -> str:
    """
    Return a prompt snippet listing approved terms for the target language (hi, ta).
    Used so translation uses consistent medical terminology (R7 / Phase 3.4).
    """
    if target_lang not in ("hi", "ta"):
        return ""
    pairs = []
    for en_term, trans in APPROVED_TERMINOLOGY.items():
        if en_term == "en":
            continue
        val = trans.get(target_lang)
        if val:
            pairs.append(f"{en_term} → {val}")
    if not pairs:
        return ""
    return " Use these approved terms when applicable: " + "; ".join(pairs[:14]) + "."


def get_supported_languages() -> list[str]:
    """Return list of supported language codes from env or default."""
    raw = os.environ.get("SUPPORTED_LANGUAGES", DEFAULT_SUPPORTED_LANGUAGES)
    return [lang.strip().lower() for lang in raw.split(",") if lang.strip()]


def _get_translate_client():
    """Create Amazon Translate client for ap-south-1."""
    try:
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        return boto3.client("translate", region_name=region)
    except Exception as e:
        logger.debug("Translate client init failed: %s", e)
        return None


def _get_comprehend_client():
    """Create Amazon Comprehend client for ap-south-1."""
    try:
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        return boto3.client("comprehend", region_name=region)
    except Exception as e:
        logger.debug("Comprehend client init failed: %s", e)
        return None


def detect_language(text: str) -> str:
    """
    Detect dominant language of text using Amazon Comprehend.

    Returns ISO 639-1 language code (e.g. 'hi', 'en').
    Falls back to 'en' on any failure.
    """
    if not text or not text.strip():
        return "en"

    client = _get_comprehend_client()
    if not client:
        return _detect_language_heuristic(text)

    try:
        response = client.detect_dominant_language(Text=text[:5000])
        languages = response.get("Languages", [])
        if languages:
            # Return highest-confidence language
            best = max(languages, key=lambda x: x.get("Score", 0))
            code = best.get("LanguageCode", "en").lower()
            supported = get_supported_languages()
            return code if code in supported else "en"
        return "en"
    except Exception as e:
        logger.debug("Comprehend detect_language failed: %s", e)
        return _detect_language_heuristic(text)


def _detect_language_heuristic(text: str) -> str:
    """Simple heuristic fallback: check for Devanagari, Tamil, Telugu, Bengali scripts."""
    for char in text[:200]:
        cp = ord(char)
        # Devanagari (Hindi, Marathi)
        if 0x0900 <= cp <= 0x097F:
            return "hi"
        # Bengali
        if 0x0980 <= cp <= 0x09FF:
            return "bn"
        # Tamil
        if 0x0B80 <= cp <= 0x0BFF:
            return "ta"
        # Telugu
        if 0x0C00 <= cp <= 0x0C7F:
            return "te"
    return "en"


def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "auto",
) -> str:
    """
    Translate text to target language using Amazon Translate.

    Args:
        text: Input text (max 5000 chars per Translate API limit).
        target_lang: Target language code (e.g. 'hi').
        source_lang: Source language code or 'auto' for detection.

    Returns:
        Translated text. Returns original text on any failure.
    """
    if not text or not text.strip():
        return text

    # No-op if already in target language
    if source_lang == target_lang:
        return text

    supported = get_supported_languages()
    if target_lang not in supported:
        logger.debug("Target language '%s' not supported; returning original", target_lang)
        return text

    client = _get_translate_client()
    if not client:
        return _translate_bedrock_fallback(text, target_lang, source_lang)

    try:
        src = source_lang if source_lang != "auto" else "auto"
        response = client.translate_text(
            Text=text[:5000],
            SourceLanguageCode=src,
            TargetLanguageCode=target_lang,
            Settings={
                "Formality": "FORMAL",
                "Brevity": "ON",
            },
        )
        translated = response.get("TranslatedText", text)
        logger.info(
            "Translated text src=%s target=%s len=%d",
            response.get("SourceLanguageCode", src),
            target_lang,
            len(translated),
        )
        return translated
    except Exception as e:
        logger.debug("Amazon Translate failed: %s", e)
        return _translate_bedrock_fallback(text, target_lang, source_lang)


def _translate_bedrock_fallback(text: str, target_lang: str, source_lang: str) -> str:
    """
    Fallback translation using Bedrock Converse when Amazon Translate is unavailable.
    Useful for clinical terminology that may not be in Translate's dictionary.
    """
    try:
        import boto3

        secret_name = os.environ.get("BEDROCK_CONFIG_SECRET_NAME")
        region = os.environ.get("AWS_REGION", "ap-south-1")
        if not secret_name:
            return text

        import json
        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        config = json.loads(resp.get("SecretString", "{}"))
        model_id = config.get("model_id") or "anthropic.claude-3-haiku-20240307-v1:0"
        bedrock_region = config.get("region") or region

        target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
        prompt = (
            f"Translate the following text to {target_name}. "
            "This is clinical/medical content for a hospital system in India. "
            "Use formal medical terminology appropriate for the target language. "
            "Return ONLY the translated text, nothing else.\n\n"
            f"{text[:3000]}"
        )

        bedrock = boto3.client("bedrock-runtime", region_name=bedrock_region)
        response = bedrock.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.1},
        )
        output = response.get("output", {})
        content = output.get("message", {}).get("content", [])
        translated = next((c.get("text", "") for c in content if c.get("text")), "").strip()
        return translated if translated else text
    except Exception as e:
        logger.debug("Bedrock translation fallback failed: %s", e)
        return text


def translate_for_patient(
    text: str,
    patient_language: str | None,
    source_lang: str = "en",
) -> str:
    """
    Convenience: translate text to the patient's preferred language.
    If patient has no language preference or it's English, returns original.
    """
    lang = (patient_language or "en").strip().lower()
    if lang == "en" or lang == source_lang:
        return text
    return translate_text(text, lang, source_lang)


def get_request_language(event: dict) -> str:
    """
    Extract preferred language from API Gateway event.
    Checks Accept-Language header, then query param ?lang=xx.
    Returns ISO 639-1 code, default 'en'.
    """
    # Check query param first (explicit)
    params = event.get("queryStringParameters") or {}
    lang_param = (params.get("lang") or "").strip().lower()
    if lang_param and lang_param in get_supported_languages():
        return lang_param

    # Check Accept-Language header
    headers = event.get("headers") or {}
    accept_lang = headers.get("Accept-Language") or headers.get("accept-language") or ""
    if accept_lang:
        # Parse first language from "hi-IN,hi;q=0.9,en;q=0.8"
        first = accept_lang.split(",")[0].strip().split(";")[0].strip()
        code = first.split("-")[0].strip().lower()
        if code in get_supported_languages():
            return code

    return "en"
