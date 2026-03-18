#!/usr/bin/env python3
"""
Verify CDSS database (Aurora RDS or local) is reachable and schema is present.
Run from repo root with same env as migrations:

  PowerShell (Aurora):
    $env:PYTHONPATH = "src"
    $env:RDS_CONFIG_SECRET_NAME = "cdss-dev/rds-config"
    $env:AWS_REGION = "ap-south-1"
    python scripts/check_aurora_db.py

  PowerShell (local Postgres):
    $env:PYTHONPATH = "src"
    $env:DATABASE_URL = "postgresql://user:pass@host:5432/cdssdb"
    python scripts/check_aurora_db.py

If Aurora is in a private VPC, run this from a bastion or Lambda inside the VPC, or use a tunnel.
"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from cdss.db.check_db import main

if __name__ == "__main__":
    sys.exit(main())
