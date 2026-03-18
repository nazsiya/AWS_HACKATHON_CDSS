#!/usr/bin/env python3
"""
List all tables and row counts (and optional sample data) in the CDSS Aurora database.

Requires DATABASE_URL (tunnel must be running; use IAM token if Aurora has IAM auth).
  With tunnel + DATABASE_URL set:
    python scripts/list_aurora_tables.py
  With sample rows (first 3 per table):
    python scripts/list_aurora_tables.py --sample 3
  CSV output:
    python scripts/list_aurora_tables.py --csv
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from dotenv import load_dotenv
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="List Aurora tables and row counts")
    parser.add_argument("--sample", type=int, default=0, metavar="N", help="Show first N rows per table (0 = counts only)")
    parser.add_argument("--csv", action="store_true", help="Output table list as CSV")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("Set DATABASE_URL (e.g. postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb)", file=sys.stderr)
        print("If Aurora uses IAM auth, run the same token injection as run_dev_backend.ps1 first.", file=sys.stderr)
        return 1

    if "postgresql://" in db_url and "postgresql+psycopg2" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("Install: pip install sqlalchemy psycopg2-binary", file=sys.stderr)
        return 1

    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            # List tables in public schema
            r = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [row[0] for row in r.fetchall()]
    except Exception as e:
        err_msg = str(e).lower()
        if "connection refused" in err_msg or "5433" in str(e):
            print("Connection to localhost:5433 refused.", file=sys.stderr)
            print("Start the DB tunnel first (leave it open in another terminal):", file=sys.stderr)
            print("  .\\scripts\\start_ssm_tunnel.ps1", file=sys.stderr)
            print("  or  .\\scripts\\start_ssh_tunnel.ps1", file=sys.stderr)
            print("Then run this script again.", file=sys.stderr)
        else:
            print(f"Database error: {e}", file=sys.stderr)
        return 1

    if not tables:
        print("No tables in public schema.")
        return 0

    if args.csv:
        print("table_name,row_count")
    else:
        print("Aurora (public schema) – tables and row counts")
        print("-" * 50)

    with engine.connect() as conn:
        for table in tables:
            try:
                count_r = conn.execute(text(f'SELECT count(*) FROM "{table}"'))
                count = count_r.scalar()
            except Exception as e:
                count = f"error: {e}"
            if args.csv:
                print(f'"{table}",{count}')
            else:
                print(f"  {table}: {count}")

            if args.sample and args.sample > 0 and isinstance(count, int) and count > 0:
                try:
                    sample_r = conn.execute(
                        text(f'SELECT * FROM "{table}" LIMIT :n'),
                        {"n": args.sample}
                    )
                    keys = list(sample_r.keys())
                    rows = sample_r.fetchall()
                    for i, row in enumerate(rows):
                        parts = [f"{k}={row[j]}" for j, k in enumerate(keys)]
                        print(f"    [{i+1}] " + " | ".join(parts))
                except Exception as e:
                    print(f"    (sample error: {e})")

    if not args.csv:
        print("-" * 50)
        print(f"Total tables: {len(tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
