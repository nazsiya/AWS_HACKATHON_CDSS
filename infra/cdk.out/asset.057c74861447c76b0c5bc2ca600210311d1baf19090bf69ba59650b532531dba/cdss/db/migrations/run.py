"""
Create CDSS schema and tables from SQLAlchemy models.
Usage: python -m cdss.db.migrations.run [--dry-run]
Uses DATABASE_URL or RDS_CONFIG_SECRET_NAME + AWS_REGION (same as check_db).
With --dry-run, only prints tables that would be created; no DB connection.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text


def run(dry_run: bool = False) -> int:
    if dry_run:
        from cdss.db.models import Base
        tables = sorted(Base.metadata.tables.keys())
        print("Dry-run: would create tables:", ", ".join(tables))
        return 0

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

    Base.metadata.create_all(bind=engine)
    print("CDSS schema: tables created successfully.")

    # Ensure PostgreSQL sequences/defaults for integer PKs (avoids "null value in column id" on insert)
    try:
        _ensure_serial_defaults(engine)
    except Exception as e:
        print("Note: ensure_serial_defaults skipped:", e, file=sys.stderr)

    return 0


def _ensure_serial_defaults(engine) -> None:
    """Set DEFAULT nextval(...) for integer PK columns that may have been created without it."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if inspector.dialect.name != "postgresql":
        return

    tables_with_serial = [
        "audit_log", "visits", "schedule_slots", "medications", "reminders",
        "consents", "medical_conditions", "allergies", "surgery_requirements",
        "surgical_team", "resource_status_log", "doctor_replacements",
        "conversation_summaries", "medication_adherence_log",
        "language_translations", "agent_event_log", "alert_log", "escalation_log"
    ]
    with engine.connect() as conn:
        for table in tables_with_serial:
            if table not in inspector.get_table_names():
                continue
            seq_name = f"{table}_id_seq"
            try:
                conn.execute(text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name};"))
                conn.execute(text(
                    f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{seq_name}'::regclass);"
                ))
                conn.execute(text(f"ALTER SEQUENCE {seq_name} OWNED BY {table}.id;"))
            except Exception:
                pass
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create CDSS database schema from models")
    parser.add_argument("--dry-run", action="store_true", help="Only list tables; no DB connection")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
