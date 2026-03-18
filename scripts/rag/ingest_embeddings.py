#!/usr/bin/env python3
"""
Generate embeddings via Bedrock Titan Embed and store them for RAG testing.

Stores embeddings in a local JSON file by default so tests run without OpenSearch.
For production, use OpenSearch Serverless (see backend/ai/rag_config.json) or
pgvector; extend this script to write to that store when configured.

Usage:
  # Local JSON store (no AWS required for --dry-run)
  python scripts/rag/ingest_embeddings.py --dry-run

  # With Bedrock (requires AWS credentials and model access)
  AWS_REGION=ap-south-1 python scripts/rag/ingest_embeddings.py --output embeddings.json
  python scripts/rag/ingest_embeddings.py --doc "Post-op wound care protocol" --output embeddings.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Optional: add src for shared embedding client if we add one
# sys.path.insert(0, str(REPO_ROOT / "src"))

# Default dimension matches backend/ai/rag_config.json (OpenSearch knn_vector dimension)
DEFAULT_DIMENSION = 1536
# Titan Embed Text v1 supports 1536; v2 supports 256, 512, 1024
TITAN_EMBED_V1_ID = "amazon.titan-embed-text-v1"
TITAN_EMBED_V2_ID = "amazon.titan-embed-text-v2:0"


def get_embedding(
    text: str,
    region: str | None = None,
    model_id: str | None = None,
    dimensions: int = DEFAULT_DIMENSION,
) -> list[float]:
    """
    Call Bedrock to embed text. Returns a list of floats.

    Uses Titan Embed Text v1 (1536) by default to match rag_config.json.
    """
    import boto3

    region = region or os.environ.get("AWS_REGION", "ap-south-1")
    model_id = model_id or os.environ.get("BEDROCK_EMBED_MODEL_ID", TITAN_EMBED_V1_ID)
    client = boto3.client("bedrock-runtime", region_name=region)

    # Titan v1: body has inputText; no dimensions param (fixed 1536)
    # Titan v2: body has inputText, dimensions (256/512/1024)
    if "v1" in model_id or model_id == TITAN_EMBED_V1_ID:
        body = json.dumps({"inputText": text})
    else:
        body = json.dumps({"inputText": text, "dimensions": min(dimensions, 1024)})

    resp = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    result = json.loads(resp["body"].read())
    embedding = result.get("embedding")
    if not embedding:
        raise ValueError("Bedrock response missing 'embedding': %s" % result)
    return embedding


def ingest_documents(
    documents: list[dict],
    region: str | None = None,
    model_id: str | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Ingest a list of documents: each {"id", "text", "metadata"}.
    Returns list of {"id", "text", "metadata", "embedding"}.
    """
    out = []
    for doc in documents:
        doc_id = doc.get("id", "")
        text = doc.get("text", "")
        metadata = doc.get("metadata") or {}
        if not text:
            continue
        if dry_run:
            # Placeholder embedding for offline tests
            embedding = [0.0] * DEFAULT_DIMENSION
        else:
            embedding = get_embedding(text, region=region, model_id=model_id)
        out.append({"id": doc_id, "text": text, "metadata": metadata, "embedding": embedding})
    return out


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Ingest documents into embeddings store (Bedrock + local JSON or OpenSearch)")
    ap.add_argument("--doc", type=str, action="append", help="Document text to embed (can repeat)")
    ap.add_argument("--file", type=str, help="JSON file with list of {id, text, metadata}")
    ap.add_argument("--output", type=str, default="embeddings.json", help="Output JSON file path")
    ap.add_argument("--dry-run", action="store_true", help="Use placeholder embeddings (no Bedrock call)")
    ap.add_argument("--region", type=str, default=os.environ.get("AWS_REGION", "ap-south-1"))
    args = ap.parse_args()

    documents = []
    if args.file:
        p = Path(args.file)
        if not p.is_file():
            print("File not found: %s" % args.file, file=sys.stderr)
            return 1
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        documents = data if isinstance(data, list) else data.get("documents", [])
    if args.doc:
        for i, text in enumerate(args.doc):
            documents.append({"id": "doc-%d" % i, "text": text, "metadata": {}})
    if not documents:
        # Default sample for testing
        documents = [
            {"id": "protocol-1", "text": "Post-operative wound care: keep dressing clean and dry. Report fever or discharge.", "metadata": {"doc_type": "protocol"}},
            {"id": "protocol-2", "text": "Pre-op fasting: nil by mouth 6 hours before surgery for adults.", "metadata": {"doc_type": "protocol"}},
        ]

    try:
        results = ingest_documents(documents, region=args.region, dry_run=args.dry_run)
    except Exception as e:
        print("Ingest failed: %s" % e, file=sys.stderr)
        if "AccessDeniedException" in str(e):
            print("Hint: Enable Titan Embed model access in Bedrock console for this region.", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"documents": results, "dimension": DEFAULT_DIMENSION}, f, indent=2)
    print("Wrote %d embeddings to %s" % (len(results), out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
