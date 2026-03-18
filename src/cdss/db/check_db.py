"""
Verify CDSS database connection and schema (Aurora RDS or local Postgres).
Usage: python -m cdss.db.check_db
Uses DATABASE_URL or RDS_CONFIG_SECRET_NAME + AWS_REGION. Reports connection status, table existence, and row counts.
"""

from __future__ import annotations

import sys
from sqlalchemy import inspect, text


def check_db() -> int:
    """Connect, check schema, print table row counts. Returns 0 if OK, 1 on error."""
    try:
        from cdss.db.session import get_engine
        from cdss.db.models import Base
    except ImportError as e:
        print("Import error:", e, file=sys.stderr)
        return 1

    try:
        engine = get_engine()
    except RuntimeError as e:
        print("Database not configured:", e, file=sys.stderr)
        return 1

    expected_tables = {t for t in Base.metadata.tables.keys()}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database: connected")
    except Exception as e:
        print("Database: connection failed:", e, file=sys.stderr)
        return 1

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    missing = expected_tables - existing
    if missing:
        print("CDSS schema: incomplete (missing tables:", ", ".join(sorted(missing)), ")")
        print("Run: python -m cdss.db.migrations.run")
        return 1

    print("CDSS schema: present (all tables exist)")
    print("\nRow counts:")
    for table in sorted(expected_tables):
        try:
            with engine.connect() as conn:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")
        except Exception as e:
            print(f"  {table}: error - {e}")
    return 0


def main() -> int:
    return check_db()


if __name__ == "__main__":
    sys.exit(main())
