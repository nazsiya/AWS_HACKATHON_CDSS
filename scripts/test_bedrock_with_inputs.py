#!/usr/bin/env python3
"""
Test Bedrock patient (doctor-facing) and visit (patient-facing) summaries with your own sample inputs.

Usage:
  # Use the bundled sample JSON (edit scripts/sample_bedrock_inputs.json with your data):
  python scripts/test_bedrock_with_inputs.py

  # Use your own JSON file:
  python scripts/test_bedrock_with_inputs.py path/to/your_inputs.json

  # Quick one-off test with inline transcript (patient/visit summary only):
  python scripts/test_bedrock_with_inputs.py --transcript "Patient has fever and cough for 3 days." --context "No known allergies."

  # Doctor summary only with inline patient data (pass JSON string for patient and visits):
  python scripts/test_bedrock_with_inputs.py --doctor-summary

Requires: BEDROCK_CONFIG_SECRET_NAME and AWS_REGION set (or edit below). AWS credentials must allow
Secrets Manager read and Bedrock InvokeModel.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Default env for local runs (override with your secret name and region)
if not os.environ.get("BEDROCK_CONFIG_SECRET_NAME"):
    os.environ.setdefault("BEDROCK_CONFIG_SECRET_NAME", "cdss-dev/bedrock-config")
if not os.environ.get("AWS_REGION"):
    os.environ.setdefault("AWS_REGION", "ap-south-1")

# Ensure project src is on path (so we use local cdss, not site-packages)
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _obj(namespace_dict: dict) -> SimpleNamespace:
    """Turn a dict into an object with attributes (for patient/visit)."""
    out = SimpleNamespace()
    for k, v in namespace_dict.items():
        if k == "visit_date" and isinstance(v, str):
            # patient_summary expects .isoformat(); allow plain string from JSON
            class _StrDate:
                def isoformat(self) -> str:
                    return v
            v = _StrDate()
        setattr(out, k, v)
    return out


def run_doctor_summary(patient: dict, recent_visits: list[dict]) -> str | None:
    """Doctor-facing: clinical summary from patient record + recent visits."""
    from cdss.bedrock.patient_summary import get_patient_summary

    p = _obj(patient)
    visits = [_obj(v) for v in recent_visits]
    for v in visits:
        if hasattr(v, "visit_date") and isinstance(getattr(v, "visit_date"), str):
            # Keep as string; patient_summary uses isoformat if present
            pass
    return get_patient_summary(p, visits)


def run_patient_summary(transcript_text: str, patient_context: str = "") -> tuple[str | None, dict | None]:
    """Patient-facing: visit summary + extracted entities from consultation transcript."""
    from cdss.bedrock.visit_summary import generate_visit_summary, extract_medical_entities

    summary = generate_visit_summary(transcript_text, patient_context)
    entities = extract_medical_entities(transcript_text)
    return summary, entities


def _check_bedrock_connection() -> str | None:
    """
    Try to load Bedrock config and run one Converse call.
    Returns None on success, or an error message string on failure.
    """
    secret_name = (os.environ.get("BEDROCK_CONFIG_SECRET_NAME") or "").strip()
    if not secret_name:
        return "BEDROCK_CONFIG_SECRET_NAME is not set. Set it in this terminal or in the script defaults."
    try:
        import boto3
        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        config = json.loads(resp.get("SecretString", "{}"))
        model_id = config.get("model_id") or "anthropic.claude-3-haiku-20240307-v1:0"
        br_region = config.get("region") or region
        br = boto3.client("bedrock-runtime", region_name=br_region)
        br.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "Say OK."}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        return None
    except Exception as e:
        err = str(e).strip()
        if "AccessDeniedException" in err or "ResourceNotFoundException" in err:
            return f"AWS error: {err}\n  → Check: (1) AWS credentials (aws sts get-caller-identity), (2) Secret exists: {secret_name!r} in {region}, (3) IAM allows secretsmanager:GetSecretValue and bedrock:InvokeModel."
        if "Unable to locate credentials" in err or "NoCredentialsError" in err:
            return f"AWS credentials not found: {err}\n  → Run: aws configure (or set AWS_PROFILE / AWS_ACCESS_KEY_ID etc.)."
        return f"Bedrock connection failed: {err}"


def main() -> int:
    # Ensure Bedrock env is set so cdss.bedrock sees it (same session as imports)
    os.environ.setdefault("BEDROCK_CONFIG_SECRET_NAME", "cdss-dev/bedrock-config")
    os.environ.setdefault("AWS_REGION", "ap-south-1")
    secret = os.environ.get("BEDROCK_CONFIG_SECRET_NAME", "")
    if secret:
        print(f"Using Bedrock config: BEDROCK_CONFIG_SECRET_NAME={secret!r}, AWS_REGION={os.environ.get('AWS_REGION', '')!r}\n")

    parser = argparse.ArgumentParser(
        description="Test Bedrock doctor and patient summaries with sample inputs."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default=REPO_ROOT / "scripts" / "sample_bedrock_inputs.json",
        help="Path to JSON file with doctor_summary and/or patient_summary inputs. Default: scripts/sample_bedrock_inputs.json",
    )
    parser.add_argument(
        "--transcript",
        type=str,
        help="Override: consultation transcript text for patient/visit summary.",
    )
    parser.add_argument(
        "--context",
        type=str,
        default="",
        help="Override: patient context string (e.g. conditions) when using --transcript.",
    )
    parser.add_argument(
        "--doctor-only",
        action="store_true",
        help="Run only doctor-facing patient summary (from JSON or default sample).",
    )
    parser.add_argument(
        "--patient-only",
        action="store_true",
        help="Run only patient-facing visit summary + entities (from JSON or --transcript).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify Bedrock connection (Secrets Manager + one Converse call) and exit.",
    )
    args = parser.parse_args()

    if args.check_only:
        os.environ.setdefault("BEDROCK_CONFIG_SECRET_NAME", "cdss-dev/bedrock-config")
        os.environ.setdefault("AWS_REGION", "ap-south-1")
        print(f"Checking Bedrock: BEDROCK_CONFIG_SECRET_NAME={os.environ.get('BEDROCK_CONFIG_SECRET_NAME')!r}, AWS_REGION={os.environ.get('AWS_REGION')!r}")
        err = _check_bedrock_connection()
        if err:
            print("\nFAILED:\n", err, file=sys.stderr)
            return 1
        print("OK – Bedrock config loaded and Converse succeeded.")
        return 0

    input_path = Path(args.input_file)
    run_doctor = not args.patient_only
    run_patient = not args.doctor_only

    if args.transcript is not None:
        run_patient = True
        transcript_text = args.transcript
        patient_context = args.context or ""
    else:
        transcript_text = ""
        patient_context = ""

    data = {}
    if run_doctor or (run_patient and not args.transcript):
        if not input_path.is_file():
            print(f"Input file not found: {input_path}", file=sys.stderr)
            return 1
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
        if not args.transcript:
            ps = data.get("patient_summary") or {}
            transcript_text = (ps.get("transcript_text") or "").strip()
            patient_context = (ps.get("patient_context") or "").strip()

    # If we need Bedrock, verify connection first and show the real error if it fails
    if run_doctor or (run_patient and transcript_text):
        err = _check_bedrock_connection()
        if err:
            print("Bedrock is not available.\n", file=sys.stderr)
            print(err, file=sys.stderr)
            return 1

    if run_doctor:
        doc = data.get("doctor_summary") or {}
        patient = doc.get("patient") or {}
        visits = doc.get("recent_visits") or []
        print("--- Doctor-facing: Patient summary (clinical) ---")
        try:
            result = run_doctor_summary(patient, visits)
            if result:
                print(result)
            else:
                print("(No summary returned; check BEDROCK_CONFIG_SECRET_NAME and Bedrock access.)")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print()

    if run_patient:
        if not transcript_text:
            print("--- Patient-facing: Visit summary + entities ---")
            print("No transcript provided. Use 'patient_summary.transcript_text' in JSON or --transcript.")
        else:
            print("--- Patient-facing: Visit summary ---")
            try:
                summary, entities = run_patient_summary(transcript_text, patient_context)
                if summary:
                    print(summary)
                else:
                    print("(No visit summary returned.)")
                print()
                print("--- Extracted entities ---")
                print(json.dumps(entities or {}, indent=2))
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
