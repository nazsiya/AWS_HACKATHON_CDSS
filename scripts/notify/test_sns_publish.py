#!/usr/bin/env python3
"""
Publish test messages to CDSS SNS topics (patient_reminders, doctor_escalations).

Use to validate SNS configuration and permissions. In production these topics
would be subscribed (email, SMS, Lambda) per docs/requirements.

Usage (deployed only; requires AWS credentials and topic ARNs):
  SNS_TOPIC_PATIENT_REMINDERS_ARN=arn:aws:sns:ap-south-1:... \\
  SNS_TOPIC_DOCTOR_ESCALATIONS_ARN=arn:aws:sns:ap-south-1:... \\
  python scripts/notify/test_sns_publish.py

  python scripts/notify/test_sns_publish.py --topic patient_reminders
  python scripts/notify/test_sns_publish.py --topic doctor_escalations --message "Test escalation"
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def publish_sns(
    topic_arn: str,
    message: str,
    subject: str | None = None,
    region: str | None = None,
) -> dict:
    """Publish a message to an SNS topic. Returns publish response."""
    import boto3

    region = region or os.environ.get("AWS_REGION", "ap-south-1")
    client = boto3.client("sns", region_name=region)
    params = {"TopicArn": topic_arn, "Message": message}
    if subject:
        params["Subject"] = subject
    return client.publish(**params)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Publish test messages to CDSS SNS topics")
    ap.add_argument(
        "--topic",
        choices=["patient_reminders", "doctor_escalations"],
        default=None,
        help="Topic to publish to (default: both)",
    )
    ap.add_argument("--message", default="CDSS test message (sns_publish)", help="Message body")
    ap.add_argument("--subject", default=None, help="Subject (optional)")
    args = ap.parse_args()

    region = os.environ.get("AWS_REGION", "ap-south-1")
    topics = []
    if args.topic == "patient_reminders" or not args.topic:
        arn = os.environ.get("SNS_TOPIC_PATIENT_REMINDERS_ARN", "").strip()
        if arn:
            topics.append(("patient_reminders", arn))
        elif not args.topic:
            print("SNS_TOPIC_PATIENT_REMINDERS_ARN not set. Skipping.", file=sys.stderr)
    if args.topic == "doctor_escalations" or not args.topic:
        arn = os.environ.get("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN", "").strip()
        if arn:
            topics.append(("doctor_escalations", arn))
        elif not args.topic:
            print("SNS_TOPIC_DOCTOR_ESCALATIONS_ARN not set. Skipping.", file=sys.stderr)

    if not topics:
        print("No topic ARNs set. Set SNS_TOPIC_PATIENT_REMINDERS_ARN and/or SNS_TOPIC_DOCTOR_ESCALATIONS_ARN.", file=sys.stderr)
        return 1

    for name, arn in topics:
        try:
            resp = publish_sns(arn, args.message, subject=args.subject, region=region)
            print("Published to %s: MessageId=%s" % (name, resp.get("MessageId", "?")))
        except Exception as e:
            print("Publish to %s failed: %s" % (name, e), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
