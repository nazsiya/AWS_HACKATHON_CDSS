# Approved Medical Terminology (R7 / Phase 3.4)

This document lists the approved English → Hindi and English → Tamil terms used by the CDSS for consistent multilingual translation and agent responses. The same list is available in code (`cdss.services.i18n.APPROVED_TERMINOLOGY`) and via **GET /api/v1/terminology**.

## Purpose

- **Translation**: `/api/ai/translate` and supervisor agent responses use these terms when rendering content in Hindi or Tamil.
- **Consistency**: Ensures patient-facing and clinician-facing text uses the same regional terms across the system.
- **R7 acceptance**: Multilingual & cultural adaptation; Indian regional languages and terminology.

## Supported languages

| Code | Language |
|------|----------|
| en   | English  |
| hi   | Hindi    |
| ta   | Tamil    |
| te   | Telugu   |
| bn   | Bengali  |

## Approved terms (English → Hindi, Tamil)

| English       | Hindi              | Tamil                    |
|---------------|--------------------|---------------------------|
| Hypertension  | उच्च रक्तचाप       | உயர் இரத்த அழுத்தம்      |
| Diabetes      | मधुमेह             | சர்க்கரை நோய்            |
| Medication    | दवा                | மருந்து                   |
| Dosage        | खुराक              | மருந்தளவு                |
| Blood pressure| रक्तचाप             | இரத்த அழுத்தம்           |
| Consultation  | परामर्श            | ஆலோசனை                   |
| Patient       | रोगी               | நோயாளி                   |
| Doctor        | डॉक्टर             | மருத்துவர்               |
| Surgery       | शल्य चिकित्सा      | அறுவை சிகிச்சை          |
| Prescription  | नुस्खा             | மருந்து பட்டியல்         |
| Follow-up     | अनुवर्ती           | பின்தொடர்வு              |
| Allergy       | एलर्जी             | அலர்ஜி                   |
| Symptoms      | लक्षण              | அறிகுறிகள்               |
| Treatment     | उपचार              | சிகிச்சை                 |

## API

- **GET /api/v1/terminology** — Returns `{ "terminology": { "English term": { "hi": "Hindi", "ta": "Tamil" }, ... }, "languages": ["en", "hi", "ta", "te", "bn"] }`.
- **POST /api/ai/translate** — Request body `{ "text", "target_lang": "hi"|"ta", "source_lang" }`; translation uses the approved terms when applicable.
- **Agent (POST /agent)** — Send `Accept-Language: hi` or `?lang=ta` to receive agent replies translated to Hindi or Tamil using the same terminology.

## Extending the list

To add terms, update `src/cdss/services/i18n.APPROVED_TERMINOLOGY` and this document. Keep clinical terms consistent with hospital and regional usage.
