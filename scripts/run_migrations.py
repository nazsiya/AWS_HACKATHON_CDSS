#!/usr/bin/env python3
"""
Create CDSS schema and tables. Run from any directory; path is set automatically.
  python scripts/run_migrations.py [--dry-run]
Requires DATABASE_URL or RDS_CONFIG_SECRET_NAME + AWS_REGION (same as db-migrations.md).
"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from cdss.db.migrations.run import main as migrations_main

def main():
    try:
        return migrations_main()
    except Exception as e:
        err_msg = str(e).lower()
        if "connection refused" in err_msg or "10061" in err_msg:
            print("\nFix: Start the SSM tunnel first: .\\scripts\\start_ssm_tunnel.ps1", file=sys.stderr)
        if "password authentication failed" in err_msg:
            print("\nFix: Use the Aurora master password in DATABASE_URL (same as Terraform db_password).", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
