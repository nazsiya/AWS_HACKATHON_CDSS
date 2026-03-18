#!/usr/bin/env python3
"""
Query stored embeddings for top-k similarity (cosine or L2).

Reads the JSON produced by ingest_embeddings.py. For production, replace with
OpenSearch/pgvector similarity search; this script validates the pipeline and
serves as a test harness.

Usage:
  python scripts/rag/query_similarity.py --store embeddings.json --query "wound care after surgery" --top 3
  python scripts/rag/query_similarity.py --store embeddings.json --query "fasting before operation" --top 5
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if len(a) != len(b):
        raise ValueError("Vector length mismatch")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def l2_distance(a: list[float], b: list[float]) -> float:
    """L2 (Euclidean) distance. Lower is more similar."""
    if len(a) != len(b):
        raise ValueError("Vector length mismatch")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def load_store(path: str) -> list[dict]:
    """Load documents with embeddings from JSON store."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("documents", data) if isinstance(data, dict) else data


def embed_query_for_test(query: str, dimension: int = 1536) -> list[float]:
    """
    Placeholder query embedding for offline testing (zeros).
    In production, call Bedrock Titan Embed with query text.
    """
    # For real use, call get_embedding from ingest_embeddings
    return [0.0] * dimension


def top_k_similar(
    store: list[dict],
    query_embedding: list[float],
    k: int = 5,
    use_cosine: bool = True,
) -> list[tuple[float, dict]]:
    """
    Return top-k documents by similarity (cosine) or by inverse L2 distance.
    Each item is (score, document). For cosine, higher is better; for L2, we use -distance.
    """
    scored = []
    for doc in store:
        emb = doc.get("embedding")
        if not emb:
            continue
        if use_cosine:
            score = cosine_similarity(query_embedding, emb)
        else:
            score = -l2_distance(query_embedding, emb)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Top-k similarity search over stored embeddings")
    ap.add_argument("--store", type=str, default="embeddings.json", help="JSON store from ingest_embeddings.py")
    ap.add_argument("--query", type=str, required=True, help="Query text (embedding from Bedrock if not --dry-run)")
    ap.add_argument("--top", type=int, default=5, help="Number of results")
    ap.add_argument("--dry-run", action="store_true", help="Use placeholder query embedding (no Bedrock)")
    ap.add_argument("--metric", choices=["cosine", "l2"], default="cosine")
    args = ap.parse_args()

    store_path = Path(args.store)
    if not store_path.is_file():
        print("Store not found: %s. Run ingest_embeddings.py first." % args.store, file=sys.stderr)
        return 1

    store = load_store(str(store_path))
    if not store:
        print("Store is empty.", file=sys.stderr)
        return 1

    dimension = len(store[0].get("embedding", []))
    if args.dry_run:
        query_embedding = embed_query_for_test(args.query, dimension)
    else:
        # Call Bedrock Titan Embed (same as ingest_embeddings)
        try:
            import os
            import boto3
            region = os.environ.get("AWS_REGION", "ap-south-1")
            model_id = os.environ.get("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v1")
            client = boto3.client("bedrock-runtime", region_name=region)
            body = json.dumps({"inputText": args.query})
            resp = client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(resp["body"].read())
            query_embedding = result.get("embedding")
            if not query_embedding:
                raise ValueError("Bedrock response missing 'embedding'")
        except Exception as e:
            print("Failed to embed query: %s. Use --dry-run for offline test." % e, file=sys.stderr)
            return 1

    if len(query_embedding) != dimension:
        print("Query embedding dimension %d != store dimension %d" % (len(query_embedding), dimension), file=sys.stderr)
        return 1

    use_cosine = args.metric == "cosine"
    results = top_k_similar(store, query_embedding, k=args.top, use_cosine=use_cosine)
    print("Top-%d for query: %s" % (args.top, args.query[:60] + ("..." if len(args.query) > 60 else "")))
    for i, (score, doc) in enumerate(results, 1):
        print("  %d. score=%.4f id=%s text=%s" % (i, score, doc.get("id", "?"), (doc.get("text", "")[:70] + "...")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
