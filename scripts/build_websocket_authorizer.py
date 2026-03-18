#!/usr/bin/env python3
"""
Build WebSocket authorizer Lambda zip with dependencies.
Run from repo root: python scripts/build_websocket_authorizer.py
Writes infrastructure/websocket_authorizer_lambda.zip.

Run this before the first 'terraform apply' when enable_websocket_authorizer is true,
so the zip exists for the Lambda deployment. Then run 'terraform apply' from the
infrastructure/ directory (cd infrastructure), not from the repo root.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORIZER_DIR = REPO_ROOT / "backend" / "api" / "websocket_authorizer"
OUT_ZIP = REPO_ROOT / "infrastructure" / "websocket_authorizer_lambda.zip"
DEPS_DIR = AUTHORIZER_DIR / "deps"


def main() -> int:
    if not (AUTHORIZER_DIR / "authorizer.py").exists():
        print("Error: backend/api/websocket_authorizer/authorizer.py not found", file=sys.stderr)
        return 1
    if DEPS_DIR.exists():
        shutil.rmtree(DEPS_DIR)
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    req = AUTHORIZER_DIR / "requirements.txt"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req), "-t", str(DEPS_DIR), "--quiet"],
        check=True,
        cwd=REPO_ROOT,
    )
    for f in AUTHORIZER_DIR.iterdir():
        if f.suffix == ".py":
            shutil.copy2(f, DEPS_DIR / f.name)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    shutil.make_archive(str(OUT_ZIP.with_suffix("")), "zip", DEPS_DIR)
    shutil.rmtree(DEPS_DIR)
    print("Built", OUT_ZIP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
