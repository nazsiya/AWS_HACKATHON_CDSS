"""
Ensure integer primary key columns have a sequence default so INSERTs without id work.
Fixes NotNullViolation when tables were created without SERIAL/IDENTITY.
Safe to run multiple times.
"""

from __future__ import annotations

from sqlalchemy import text

# Tables with integer auto-increment primary key
SERIAL_TABLES = ["audit_log", "visits", "schedule_slots", "medications", "reminders"]


def run(engine) -> None:
    """Create sequence and set DEFAULT nextval for each table's id column if missing."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        for table in SERIAL_TABLES:
            if table not in existing_tables:
                continue
            seq_name = f"{table}_id_seq"
            conn.execute(text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}"))
            conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{seq_name}')"))
            conn.execute(text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id)::bigint FROM {table}), 0)::bigint)"))
        conn.commit()
