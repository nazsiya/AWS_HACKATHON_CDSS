# Running CDSS DB Migrations

This doc explains what you must provide to run migrations and how to fix common failures.

## Quick reference

| Goal | What to set |
|------|-----------------------------|
| **Dry-run only** (no DB, no AWS) | Nothing. Run: `python -m cdss.db.migrations.run --dry-run` |
| **Aurora (production)** | Start SSM tunnel: `.\scripts\start_ssm_tunnel.ps1`, then `DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb` |
| **Aurora in AWS** (Lambda / IAM auth) | `RDS_CONFIG_SECRET_NAME` + `AWS_REGION` + AWS credentials |

### Seed sample data (after migrations)

To fill the database with sample patients, visits, surgeries, resources, and audit entries:

```powershell
$env:PYTHONPATH = "src"
python -m cdss.db.migrations.run    # create tables first
python -m cdss.db.seed               # insert sample data (skips if patients already exist)
python -m cdss.db.seed --force       # clear seed data and re-insert
```

Or from repo root: `python scripts/seed_db.py [--force]`.

### Aurora: schedule_slots auto-increment (if seed fails with null id)

If `schedule_slots.id` was created without a default, seed fails with `null value in column "id"`. Fix in Aurora:

1. Ensure `schedule_slots.id` is INTEGER (not VARCHAR).
2. Create sequence and set default:

```sql
CREATE SEQUENCE IF NOT EXISTS schedule_slots_id_seq;
ALTER TABLE schedule_slots ALTER COLUMN id SET DEFAULT nextval('schedule_slots_id_seq');
ALTER SEQUENCE schedule_slots_id_seq OWNED BY schedule_slots.id;
```

Or run `python -m cdss.db.migrations.run` (it runs `ensure_serial_defaults` which does this for `schedule_slots`, `visits`, `medications`, `reminders`, `audit_log`).

Models and seed include `created_at` for `ScheduleSlot` and `Medication`; after the fix, `python -m cdss.db.seed --force` should complete successfully.

---

## 1. Dry-run (no secrets or DB)

From repo root with `src` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "src"
python -m cdss.db.migrations.run --dry-run
```

This only parses the SQL files and prints what would run. It does **not** need `RDS_CONFIG_SECRET_NAME`, AWS credentials, or a database.

---

## 2. Aurora via SSM tunnel (production)

All production and local use of the database goes through the **bastion** and **SSM tunnel** to Aurora.

1. Start the tunnel (leave the terminal open):
   ```powershell
   .\scripts\start_ssm_tunnel.ps1
   ```
2. In a **second** terminal, set the database URL (use the Aurora master password; port **5433** is the local tunnel port):
   - **PowerShell:** `$env:DATABASE_URL = "postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"`
   - **Bash:** `export DATABASE_URL="postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"`

3. Run migrations:
   ```powershell
   $env:PYTHONPATH = "src"
   python -m cdss.db.migrations.run
   ```

The URL must use **localhost:5433** (tunnel port). The user must have permission to create tables in the database. See **docs/database-connection-guide.md** and **docs/BASTION_AND_DB_QUERIES.md**.

---

## 3. Aurora in AWS (Secrets Manager + IAM auth)

Use this when the database is Aurora and you connect using IAM authentication (no password in the secret).

### What must be in place

1. **Terraform has been applied**  
   The secret is created by Terraform (`infrastructure/secrets.tf`). If you have not run `terraform apply`, the secret does not exist.

2. **Secret name**  
   Terraform creates the secret as `<name_prefix>/rds-config`, where `name_prefix = project_name + "-" + environment` (e.g. `cdss-dev`). So the full name is:
   - **`cdss-dev/rds-config`** when `project_name = "cdss"` and `environment = "dev"`  
   Set:
   - **PowerShell:** `$env:RDS_CONFIG_SECRET_NAME = "cdss-dev/rds-config"`
   - **Bash:** `export RDS_CONFIG_SECRET_NAME="cdss-dev/rds-config"`

3. **AWS region**  
   The secret lives in a specific region. Your CLI/SDK must use that same region:
   - **PowerShell:** `$env:AWS_REGION = "us-east-1"`  (or `ap-south-1` if you deployed there)
   - **Bash:** `export AWS_REGION=us-east-1`  
   Or set `AWS_DEFAULT_REGION`, or the `region` in `~/.aws/config` for your profile.

4. **AWS credentials**  
   Your environment (or profile) must have permission to call `secretsmanager:GetSecretValue` on that secret. For example:
   - AWS CLI configured: `aws configure` or `aws sso login`
   - Or env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`  
   To confirm the secret is readable:
   ```powershell
   aws secretsmanager get-secret-value --secret-id "cdss-dev/rds-config" --region us-east-1
   ```

5. **Database user has `rds_iam`**  
   IAM auth only works if the PostgreSQL user has been granted the `rds_iam` role. One-time, connect with the **master password** and run:
   ```sql
   GRANT rds_iam TO <your_db_username>;
   ```
   `<your_db_username>` is the value of `var.db_username` in Terraform (the one stored in the secret as `username`).

### Run migrations

```powershell
$env:PYTHONPATH = "src"
$env:RDS_CONFIG_SECRET_NAME = "cdss-dev/rds-config"
$env:AWS_REGION = "us-east-1"   # or the region where you applied Terraform
python -m cdss.db.migrations.run
```

---

## Common errors

| Error | Cause | What to do |
|-------|--------|------------|
| `RDS_CONFIG_SECRET_NAME not set` | Neither `RDS_CONFIG_SECRET_NAME` nor `DATABASE_URL` is set. | Set one of them (see above). Use `--dry-run` if you only want to parse SQL. |
| `ResourceNotFoundException` / Secret not found | Secret doesn’t exist or wrong region/account. | 1) Run `terraform apply` if needed. 2) Set `AWS_REGION` to the region where the secret was created. 3) Confirm with `aws secretsmanager get-secret-value --secret-id "cdss-dev/rds-config" --region <region>`. |
| `RDS config missing key: ...` | Secret exists but JSON doesn’t have `host`, `port`, `database`, `username`, `region`. | Fix the secret in Terraform/Console so it matches the expected shape (see `infrastructure/secrets.tf`). |
| Connection timeout / could not connect | Network or security: Lambda not in VPC, or RDS not reachable from your machine. | From your laptop: ensure Aurora is publicly reachable or use a bastion/SSH tunnel. For Lambda, ensure `enable_lambda_vpc` and security groups allow Lambda → RDS. |
| `password authentication failed` / IAM auth error | DB user does not have `rds_iam`, or token/region wrong. | Grant `rds_iam` to the user (see above). Ensure secret’s `region` matches the RDS cluster region. |

---

## Summary checklist (Aurora + IAM)

- [ ] Terraform applied (secret and Aurora exist).
- [ ] `RDS_CONFIG_SECRET_NAME` set to e.g. `cdss-dev/rds-config`.
- [ ] `AWS_REGION` (or equivalent) set to the region where the secret and RDS live.
- [ ] AWS credentials can read the secret (`aws secretsmanager get-secret-value ...` works).
- [ ] In PostgreSQL, `GRANT rds_iam TO <db_username>;` has been run once.
- [ ] From repo root, `PYTHONPATH=src` and run `python -m cdss.db.migrations.run`.

---

## Check if the database and schema exist

From repo root:

```powershell
$env:PYTHONPATH = "src"
$env:RDS_CONFIG_SECRET_NAME = "cdss-dev/rds-config"
$env:AWS_REGION = "us-east-1"   # or ap-south-1 if you deployed there
python -m cdss.db.check_db
```

Or with `DATABASE_URL` (tunnel to Aurora):

```powershell
$env:PYTHONPATH = "src"
$env:DATABASE_URL = "postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"
python -m cdss.db.check_db
```

- **Database: connected** — the cluster exists and you can reach it.
- **CDSS schema present** — migrations have been run and all tables exist.
- **CDSS schema incomplete** — run `python -m cdss.db.migrations.run`.
- **Cannot create engine** / **Secret not found** — fix credentials/region (see Common errors above).
