#!/usr/bin/env python3
"""
Seed CDSS RDS with sample data. Run after migrations.
From repo root: python scripts/seed_db.py [--force]
Requires DATABASE_URL or RDS_CONFIG_SECRET_NAME + AWS_REGION (same as migrations).

For Aurora (private VPC): start the SSM tunnel first, then set DATABASE_URL to
localhost:5433. See docs/database-connection-guide.md.
"""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

# Load .env from repo root so DATABASE_URL is used when set (avoids connecting to Aurora directly)
try:
    from dotenv import load_dotenv
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from cdss.db.seed import main

if __name__ == "__main__":
    sys.exit(main())
