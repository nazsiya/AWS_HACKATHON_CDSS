#!/usr/bin/env python3
"""
Run a SQL query against the CDSS database (Aurora or local).
Use with SSM tunnel: set DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb
  python scripts/run_db_query.py -q "SELECT * FROM patients LIMIT 5"
  python scripts/run_db_query.py -f path/to/query.sql
  echo "SELECT 1" | python scripts/run_db_query.py
"""
import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Load .env so DATABASE_URL is set when not in environment
try:
    from dotenv import load_dotenv
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a SQL query against CDSS database")
    parser.add_argument("-q", "--query", help="SQL query string")
    parser.add_argument("-f", "--file", help="Path to .sql file")
    parser.add_argument("--csv", action="store_true", help="Print result rows as CSV")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("Set DATABASE_URL (e.g. postgresql://cdssdb:PASSWORD@localhost:5433/cdssdb)", file=sys.stderr)
        return 1

    if args.query:
        sql = args.query
    elif args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        sql = path.read_text(encoding="utf-8").strip()
    elif not sys.stdin.isatty():
        sql = sys.stdin.read().strip()
    else:
        parser.print_help()
        return 0

    if not sql:
        print("No query provided.", file=sys.stderr)
        return 1

    if "postgresql://" in db_url and "postgresql+psycopg2" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("Install sqlalchemy and psycopg2-binary: pip install sqlalchemy psycopg2-binary", file=sys.stderr)
        return 1

    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        keys = result.keys()

    if args.csv:
        import csv
        out = csv.writer(sys.stdout)
        out.writerow(keys)
        for row in rows:
            out.writerow(row)
    else:
        if not rows:
            print("(0 rows)")
        else:
            col_widths = [max(len(str(k)), max((len(str(r[i])) for r in rows), default=0)) for i, k in enumerate(keys)]
            fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
            print(fmt.format(*keys))
            print("-" * (sum(col_widths) + 2 * (len(keys) - 1)))
            for row in rows:
                print(fmt.format(*[str(x) for x in row]))
            print(f"({len(rows)} row(s))")

    return 0


if __name__ == "__main__":
    sys.exit(main())
