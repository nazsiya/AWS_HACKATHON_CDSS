# Bastion and database connection

Steps to **create/start the bastion** and **run queries** against Aurora. You can use either **SSH** or **SSM** to tunnel.

- **SSM** (default): No SSH keys, no port 22; uses AWS Session Manager. Fails if the bastion never shows "Online" in Systems Manager.
- **SSH** (reference style): You add your public key and IP to Terraform; then `ssh -L 5433:aurora:5432 ec2-user@bastion`. Works as long as the bastion is reachable on port 22.

---

## Do everything (tunnel + migrations + seed)

**Option A – SSH tunnel** (recommended if SSM never becomes Online; per [reference/docs/infrastructure/bastion-setup.md](reference/docs/infrastructure/bastion-setup.md)):

1. **One-time:** Add to `infrastructure/terraform.tfvars` (use your public IP and SSH public key):
   ```hcl
   bastion_ssh_public_key = "ssh-rsa AAAA... your-key-from-cat-~/.ssh/id_rsa.pub"
   bastion_allowed_cidr   = "YOUR_IP/32"   # e.g. from curl -s ifconfig.me
   ```
   Then run `cd infrastructure && terraform apply -auto-approve` (bastion will get a key and port 22 open from your IP).

2. **Terminal 1** (leave open):
   ```powershell
   .\scripts\start_ssh_tunnel.ps1
   ```
   (Uses `~/.ssh/id_rsa` or set `-KeyPath` / `$env:SSH_KEY_PATH`.)

3. **Terminal 2:** Ensure `.env` has `DATABASE_URL=postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb`, then:
   ```powershell
   .\scripts\run_migrations_and_seed.ps1
   ```

**Option B – SSM tunnel** (no SSH keys; bastion stays SSM-only):

**Terminal 1** (leave open):

```powershell
.\scripts\start_ssm_tunnel.ps1
```

Wait until you see *"Bastion is running and SSM is Online"* and *"Starting tunnel"*. If the script exits with *SSM did not become Online*, use Option A (SSH) above.

**Terminal 2** (after tunnel is up):

Ensure `.env` has `DATABASE_URL=postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb` (port **5433**). Then:

```powershell
.\scripts\run_migrations_and_seed.ps1
```

That runs migrations then seed in one go. After this, you can run the local API, queries, or open the doctor dashboard.

---

## One-time: Create bastion and start tunnel

From the repo root (PowerShell):

```powershell
.\scripts\ensure_bastion_and_tunnel.ps1
```

This script:

1. Runs **Terraform** (init + apply if needed) so the bastion EC2 instance and VPC exist.
2. **Starts the bastion** if it is stopped.
3. Waits for **SSM** to show the instance as "Online".
4. Starts the **SSM port-forward**: `localhost:5433` → Aurora:5432.

**Leave that terminal open.** The tunnel is active while the session runs.

---

## Run queries against the database

In a **second terminal** (tunnel must be running in the first):

### 1. Set the database URL

**Aurora with IAM authentication** (recommended; no static password):

```powershell
.\scripts\set_db_url_iam.ps1
```

This generates a short-lived IAM token and sets `DATABASE_URL`. Then run any of the commands below in the same terminal.

**Or** use the Aurora master password (only if your cluster does not use IAM auth):

```powershell
$env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
```

Replace `YOUR_PASSWORD` with the real password. If you get *PAM authentication failed*, use `set_db_url_iam.ps1` instead (see [DEBUGGING_REPORT_2026_03_08.md](DEBUGGING_REPORT_2026_03_08.md)).

### 2. List all tables and row counts

To see every table in Aurora and how many rows it has (and optionally sample rows):

```powershell
# Tables + row counts only
python scripts/list_aurora_tables.py

# Tables + counts + first 3 rows per table
python scripts/list_aurora_tables.py --sample 3

# CSV: table_name, row_count
python scripts/list_aurora_tables.py --csv
```

Requires `DATABASE_URL` (and tunnel). If Aurora uses IAM auth, set `DATABASE_URL` using the same IAM token as the backend (see docs/DEBUGGING_REPORT_2026_03_08.md or run `.\scripts\run_dev_backend.ps1` in another terminal to get token in env, then run the script in a terminal where you copy that `DATABASE_URL`).

### 3. Run arbitrary queries

**Option A – Python script (no psql needed):**

```powershell
# Single query
python scripts/run_db_query.py -q "SELECT * FROM patients LIMIT 5"

# From a .sql file
python scripts/run_db_query.py -f path/to/query.sql

# CSV output
python scripts/run_db_query.py -q "SELECT id, name FROM patients" --csv
```

**Option B – psql (if installed):**

```powershell
psql $env:DATABASE_URL -c "SELECT * FROM patients LIMIT 5"
```

**Option C – Migrations + seed (one script):**

```powershell
.\scripts\run_migrations_and_seed.ps1
```

Or step by step:

```powershell
python scripts/run_migrations.py
python scripts/seed_db.py
```

---

## Later: Tunnel only (bastion already running)

If the bastion already exists and is running:

```powershell
.\scripts\start_ssm_tunnel.ps1
```

The script uses `terraform output bastion_instance_id` when run from a repo that has `infrastructure/` with Terraform state. Otherwise it falls back to a hardcoded instance ID.

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| **TargetNotConnected** | Bastion is stopped or not registered with SSM. Run `.\scripts\start_ssm_tunnel.ps1` (it starts the instance and waits for SSM). |
| **SSM never becomes Online (ConnectionLost / None)** | Use **SSH tunnel** instead: set `bastion_ssh_public_key` and `bastion_allowed_cidr` in `infrastructure/terraform.tfvars`, apply, then run `.\scripts\start_ssh_tunnel.ps1`. See "Do everything" → Option A above. |
| **Connection refused to localhost:5433** | Tunnel is not running. Start it in another terminal with `ensure_bastion_and_tunnel.ps1` or `start_ssm_tunnel.ps1`. |
| **SSH to bastion: Connection timed out (port 22)** | Use **SSM tunnel** instead: `.\scripts\start_ssm_tunnel.ps1` (no port 22). Then in another terminal: `.\scripts\set_db_url_iam.ps1` and `python scripts/list_aurora_tables.py`. See [DEBUGGING_REPORT_2026_03_08.md](DEBUGGING_REPORT_2026_03_08.md) §6. |
| **Password authentication failed** | Use the same password as Terraform `db_password` (e.g. in `infrastructure/terraform.tfvars`). |
| **relation "patients" does not exist** | Run migrations and seed: `python scripts/run_migrations.py` then `python scripts/seed_db.py` (with tunnel + DATABASE_URL set). |

See **docs/database-connection-guide.md** for more detail.
