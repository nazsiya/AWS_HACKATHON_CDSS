# CDSS Data Layer (Aurora PostgreSQL)

- **Models:** `models.py` — SQLAlchemy 2.0 declarative models (patients, visits, surgeries, resources, schedule_slots, medications, reminders, audit_log).
- **Connection:** `session.py` — `get_rds_config(secret_name)` loads config from Secrets Manager; `get_engine()` / `get_session()` use IAM auth (`boto3.generate_db_auth_token`), cached per Lambda execution context. For local dev, set `DATABASE_URL` to use password-based connection instead.
- **Migrations:** `migrations/001_initial.sql` — initial schema. Run with:
  - **Dry-run (no AWS/DB):** `python -m cdss.db.migrations.run --dry-run`
  - **Local Postgres:** `DATABASE_URL=postgresql://user:pass@host:5432/dbname python -m cdss.db.migrations.run`
  - **Aurora (IAM):** `RDS_CONFIG_SECRET_NAME=cdss-dev/rds-config` and `AWS_REGION` set, then `python -m cdss.db.migrations.run`

**Full requirements and troubleshooting:** [docs/db-migrations.md](../../../docs/db-migrations.md).

**IAM auth:** The RDS user in the secret must have the `rds_iam` role in PostgreSQL (one-time, connect with password and run `GRANT rds_iam TO <username>;`).

**Dependencies:** `sqlalchemy>=2.0`, `psycopg2-binary` (see `backend/agents/requirements.txt`).
