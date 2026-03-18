# Bastion and database seed – from reference and CDSS

This doc summarizes **how to set up the bastion and seed data** using:

1. **Reference** (`reference/docs/`) – Emergency Medical Triage project (SSH bastion).
2. **CDSS** (this repo) – SSM bastion, no SSH keys; same goal: reach Aurora and run migrations/seed.

---

## Reference: Bastion setup (SSH tunnel)

**Source:** `reference/docs/infrastructure/bastion-setup.md`

| Step | Action |
|------|--------|
| 1 | Get your public IP: `curl -s ifconfig.me` → use `x.x.x.x/32` |
| 2 | Edit `infrastructure/terraform.tfvars`: set `enable_bastion = true`, `bastion_ssh_public_key` (from `cat ~/.ssh/id_rsa.pub`), `bastion_allowed_cidr = "YOUR_IP/32"` |
| 3 | Apply Terraform: `cd infrastructure && terraform apply` |
| 4 | Start **SSH** tunnel (keep terminal open): `ssh -i ~/.ssh/id_rsa -N -L 5432:AURORA_ENDPOINT:5432 ec2-user@BASTION_IP` — use `terraform output` for `AURORA_ENDPOINT` and `bastion_public_ip` |
| 5 | In another terminal, connect: `psql -h 127.0.0.1 -p 5432 -U triagemaster -d triagedb` (password from tfvars `db_password`), or run tests with `RDS_HOST_OVERRIDE=127.0.0.1` |

Reference uses **SSH** and **local port 5432**; database name and user are project-specific (e.g. `triagedb`, `triagemaster`).

---

## Reference: Migrations and seed

**Source:** `reference/docs/backend/implementation-history.md`, `DEPLOY.md`

- **Migrations:** RDS Data API (`aws rds-data execute-statement`) or **psql via bastion** (after SSH tunnel).
- **Seed:** One-time script that writes seed data to DB/S3/JSON (e.g. hospital data). No single “seed” command documented in bastion-setup; connection for any DB work is via the SSH tunnel to `127.0.0.1:5432`.

---

## CDSS: Bastion setup (SSM tunnel, no SSH)

**Source:** `docs/database-connection-guide.md`, `docs/BASTION_AND_DB_QUERIES.md`, `scripts/start_ssm_tunnel.ps1`

CDSS uses a **bastion with SSM only** (no SSH keys). Terraform creates the bastion and IAM for SSM; you use AWS Session Manager for port-forwarding.

| Step | Action |
|------|--------|
| 1 | Ensure Terraform applied: `cd infrastructure && terraform apply` (with `TF_VAR_db_username` and `TF_VAR_db_password` set if needed; or from `.env` `DATABASE_URL`). Bastion instance ID: `terraform output -raw bastion_instance_id`. |
| 2 | Start **SSM tunnel** (starts bastion if stopped, waits for SSM Online, then port-forward): `.\scripts\start_ssm_tunnel.ps1` — **leave this terminal open**. |
| 3 | Tunnel forwards **localhost:5433** → Aurora:5432 (port 5433 to avoid clashing with local Postgres). |

No SSH key or `bastion_allowed_cidr` needed; SSM uses IAM and the instance profile `AmazonSSMManagedInstanceCore`.

---

## CDSS: Migrations and seed (into AWS database)

**Source:** `docs/database-connection-guide.md`, `docs/BASTION_AND_DB_QUERIES.md`, `docs/db-migrations.md`

With the **tunnel running** (step 2 above), use a **second terminal**:

### 1. Set DATABASE_URL (tunnel + Aurora password)

Use the Aurora master password (same as Terraform `db_password`):

```powershell
$env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
```

Use **port 5433** (tunnel), database name **cdssdb**.

### 2. Run migrations

```powershell
cd D:\AI_Hackathon_CDSS
$env:PYTHONPATH = "src"
python -m cdss.db.migrations.run
```

Or from repo root (script loads `.env`): `python scripts/run_migrations.py` if that script exists and uses `DATABASE_URL`.

### 3. Seed data

```powershell
python -m cdss.db.seed
# or
python scripts/seed_db.py
```

Optional: `python -m cdss.db.seed --force` to clear and re-insert sample data.

### 4. Run queries (optional)

```powershell
python scripts/run_db_query.py -q "SELECT * FROM patients LIMIT 5"
```

---

## Summary table

| Topic | Reference (EMT) | CDSS |
|-------|------------------|------|
| **Bastion access** | SSH key + `enable_bastion`, `bastion_ssh_public_key`, `bastion_allowed_cidr` in tfvars | SSM only; no SSH key; `start_ssm_tunnel.ps1` |
| **Tunnel command** | `ssh -i ~/.ssh/id_rsa -N -L 5432:AURORA:5432 ec2-user@BASTION_IP` | `.\scripts\start_ssm_tunnel.ps1` (uses `aws ssm start-session`) |
| **Local port** | 5432 | 5433 |
| **Connect / DATABASE_URL** | `127.0.0.1:5432` or `RDS_HOST_OVERRIDE=127.0.0.1` | `localhost:5433` in `DATABASE_URL` |
| **Migrations** | RDS Data API or psql via tunnel | `python -m cdss.db.migrations.run` with `DATABASE_URL=...@localhost:5433/cdssdb` |
| **Seed** | One-time script (project-specific) | `python -m cdss.db.seed` or `python scripts/seed_db.py` with same `DATABASE_URL` |

---

## Quick CDSS checklist

1. **Tunnel:** `.\scripts\start_ssm_tunnel.ps1` (leave open).
2. **Second terminal:** `$env:DATABASE_URL = "postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"`.
3. **Migrations:** `$env:PYTHONPATH = "src"; python -m cdss.db.migrations.run`.
4. **Seed:** `python -m cdss.db.seed` or `python scripts/seed_db.py`.

All database access for production uses this bastion + tunnel; there is no local Postgres path in CDSS.
