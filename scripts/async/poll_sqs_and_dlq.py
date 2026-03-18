#!/usr/bin/env python3
"""
Poll agent_events SQS queue and DLQ to inspect messages (for validation and debugging).

Does not delete messages unless --delete is passed. Use to verify events put by
put_eventbridge_event.py flow into SQS and to inspect DLQ after failures.

Usage (deployed only; requires AWS credentials and queue URLs):
  SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/123456789012/cdss-dev-agent-events \\
  SQS_DLQ_URL=https://sqs.ap-south-1.amazonaws.com/123456789012/cdss-dev-agent-events-dlq \\
  python scripts/async/poll_sqs_and_dlq.py

  python scripts/async/poll_sqs_and_dlq.py --max 5 --delete   # receive and delete up to 5 from main queue
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def receive_messages(
    queue_url: str,
    region: str | None = None,
    max_messages: int = 10,
    wait_seconds: int = 5,
    delete: bool = False,
) -> list[dict]:
    """Receive messages from SQS. Optionally delete after receive."""
    import boto3

    region = region or os.environ.get("AWS_REGION", "ap-south-1")
    client = boto3.client("sqs", region_name=region)
    received = []
    while len(received) < max_messages:
        resp = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=min(10, max_messages - len(received)),
            WaitTimeSeconds=wait_seconds,
            VisibilityTimeout=30,
            MessageAttributeNames=["All"],
        )
        batch = resp.get("Messages") or []
        if not batch:
            break
        for msg in batch:
            received.append(msg)
            if delete and msg.get("ReceiptHandle"):
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
    return received


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Poll agent_events SQS and/or DLQ")
    ap.add_argument("--queue", action="store_true", help="Poll main queue (SQS_QUEUE_URL)")
    ap.add_argument("--dlq", action="store_true", help="Poll DLQ (SQS_DLQ_URL)")
    ap.add_argument("--max", type=int, default=10, help="Max messages per queue (default 10)")
    ap.add_argument("--wait", type=int, default=5, help="Long poll wait seconds (default 5)")
    ap.add_argument("--delete", action="store_true", help="Delete messages after receive (main queue only)")
    args = ap.parse_args()

    if not args.queue and not args.dlq:
        args.queue = True
        args.dlq = True

    region = os.environ.get("AWS_REGION", "ap-south-1")
    results = []

    if args.queue:
        queue_url = os.environ.get("SQS_QUEUE_URL", "").strip()
        if not queue_url:
            print("SQS_QUEUE_URL not set (Terraform: sqs_queue_url). Skipping main queue.", file=sys.stderr)
        else:
            msgs = receive_messages(queue_url, region=region, max_messages=args.max, wait_seconds=args.wait, delete=args.delete)
            results.append(("Main queue", queue_url, msgs))

    if args.dlq:
        dlq_url = os.environ.get("SQS_DLQ_URL", "").strip()
        if not dlq_url:
            print("SQS_DLQ_URL not set (Terraform: sqs_dlq_url). Skipping DLQ.", file=sys.stderr)
        else:
            msgs = receive_messages(dlq_url, region=region, max_messages=args.max, wait_seconds=args.wait, delete=False)
            results.append(("DLQ", dlq_url, msgs))

    for label, url, msgs in results:
        print("\n--- %s (%d messages) ---" % (label, len(msgs)))
        print("URL: %s" % url)
        for i, m in enumerate(msgs):
            body = m.get("Body", "{}")
            try:
                data = json.loads(body)
                detail_type = data.get("detail-type", "?")
                detail = data.get("detail", {})
                trace_id = detail.get("trace_id", "?")
                print("  [%d] detail-type=%s trace_id=%s" % (i + 1, detail_type, trace_id))
                if args.max <= 3:
                    print("    body (snippet): %s" % (json.dumps(data)[:300] + "..." if len(json.dumps(data)) > 300 else json.dumps(data)))
            except json.JSONDecodeError:
                print("  [%d] (body not JSON): %s" % (i + 1, body[:200]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
