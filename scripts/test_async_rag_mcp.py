#!/usr/bin/env python3
"""
Run Phase 6 validations: async (EventBridge detail build), RAG (ingest + query dry-run), MCP adapter.

No AWS required: uses dry-run and mocks where needed. Use for CI or local verification.

  python scripts/test_async_rag_mcp.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_async_build_detail() -> bool:
    """Validate MCP EventBridge detail build (no boto3)."""
    path = REPO_ROOT / "scripts" / "async" / "put_eventbridge_event.py"
    mod = _load_module("put_eventbridge_event", path)
    build_detail = mod.build_detail

    detail = build_detail("patient_profile_request", {"patient_id": "PT-1001", "include_visits": True})
    assert "message_id" in detail and "trace_id" in detail
    assert detail.get("source_agent") == "supervisor"
    assert detail.get("target_agent") == "patient"
    assert "payload" in detail and detail["payload"].get("patient_id") == "PT-1001"
    return True


def test_rag_ingest_dry_run() -> bool:
    """RAG ingest with dry-run produces valid store."""
    path = REPO_ROOT / "scripts" / "rag" / "ingest_embeddings.py"
    mod = _load_module("ingest_embeddings", path)
    ingest_documents = mod.ingest_documents

    docs = [{"id": "d1", "text": "Sample protocol.", "metadata": {}}]
    results = ingest_documents(docs, dry_run=True)
    assert len(results) == 1
    assert "embedding" in results[0] and len(results[0]["embedding"]) == 1536
    return True


def test_rag_query_similarity() -> bool:
    """RAG top-k similarity with mock store."""
    path = REPO_ROOT / "scripts" / "rag" / "query_similarity.py"
    mod = _load_module("query_similarity", path)
    cosine_similarity = mod.cosine_similarity
    load_store = mod.load_store
    top_k_similar = mod.top_k_similar

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps({
            "documents": [
                {"id": "a", "text": "x", "embedding": [1.0, 0.0, 0.0]},
                {"id": "b", "text": "y", "embedding": [0.9, 0.1, 0.0]},
                {"id": "c", "text": "z", "embedding": [0.0, 0.0, 1.0]},
            ],
            "dimension": 3,
        }))
        path_f = f.name
    try:
        store = load_store(path_f)
        assert len(store) == 3
        q = [1.0, 0.0, 0.0]
        top = top_k_similar(store, q, k=2)
        assert len(top) == 2
        assert top[0][1]["id"] == "a"
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0
    finally:
        Path(path_f).unlink(missing_ok=True)
    return True


def test_mcp_hospital() -> bool:
    """Hospital MCP adapter shape and error fallback."""
    from cdss.mcp.adapter import get_hospital_data

    assert "ots" in get_hospital_data("ot_status")
    assert "beds" in get_hospital_data("beds")
    assert "equipment" in get_hospital_data("equipment")
    out = get_hospital_data("unknown")
    assert "error" in out
    return True


def test_mcp_abdm() -> bool:
    """ABDM MCP adapter shape and empty patient_id error."""
    from cdss.mcp.adapter import get_abdm_record

    out = get_abdm_record("PT-1")
    assert isinstance(out, dict)
    assert "patient_id" in out or "error" in out
    out_empty = get_abdm_record("")
    assert "error" in out_empty
    return True


def main() -> int:
    failures = []
    for name, fn in [
        ("async build_detail", test_async_build_detail),
        ("RAG ingest dry-run", test_rag_ingest_dry_run),
        ("RAG query similarity", test_rag_query_similarity),
        ("MCP hospital", test_mcp_hospital),
        ("MCP ABDM", test_mcp_abdm),
    ]:
        try:
            fn()
            print("[PASS] %s" % name)
        except Exception as e:
            print("[FAIL] %s: %s" % (name, e), file=sys.stderr)
            failures.append(name)

    if failures:
        print("Failed: %s" % failures, file=sys.stderr)
        return 1
    print("All Phase 6 validations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
