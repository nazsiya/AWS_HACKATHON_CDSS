"""
Add missing columns to existing CDSS tables (e.g. patients) when Aurora was created
from an older or different schema. Safe to run multiple times (IF NOT EXISTS).
"""

from __future__ import annotations

from sqlalchemy import text


# (table_name, column_name, pg_type)
PATIENTS_ADD_COLUMNS = [
    ("patients", "language", "VARCHAR(32)"),
    ("patients", "abha_id", "VARCHAR(64)"),
    ("patients", "conditions", "JSONB"),
    ("patients", "allergies", "JSONB"),
    ("patients", "address_json", "JSONB"),
    ("patients", "emergency_contact_json", "JSONB"),
    ("patients", "blood_group", "VARCHAR(10)"),
    ("patients", "ward", "VARCHAR(64)"),
    ("patients", "severity", "VARCHAR(32)"),
    ("patients", "status", "VARCHAR(32)"),
    ("patients", "vitals", "JSONB"),
    ("patients", "surgery_readiness", "JSONB"),
    ("patients", "last_visit", "DATE"),
]

VISITS_ADD_COLUMNS = [
    ("visits", "extracted_entities", "JSONB"),
]


def run(engine) -> None:
    """Run ALTER TABLE ... ADD COLUMN IF NOT EXISTS for each missing column."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if "patients" not in inspector.get_table_names():
        return
    with engine.connect() as conn:
        for table, column, pg_type in PATIENTS_ADD_COLUMNS:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{column}" {pg_type}'))
        if "visits" in inspector.get_table_names():
            for table, column, pg_type in VISITS_ADD_COLUMNS:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{column}" {pg_type}'))
        conn.commit()
