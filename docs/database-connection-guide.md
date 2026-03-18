# CDSS Database Connection Guide

Single reference for connecting to Aurora from your machine: IDs, why direct connect fails, and exact commands.

---

## Your resources (ap-south-1)

| Resource | Value |
|----------|--------|
| **Aurora endpoint** | `cdss-dev-aurora-instance.c3coggyeulk5.ap-south-1.rds.amazonaws.com:5432` |
| **Database name** | `cdssdb` (Terraform default; **not** `postgres` or `cdss_db`) |
| **Master user** | `cdssadmin` |
| **RDS security group** | `sg-052fefe84748d25cd` (cdss-dev-aurora-sg) |
| **Your IP in SG** | `101.127.84.93/32` (already allowed) |
| **Bastion instance** | From Terraform: `cd infrastructure && terraform output -raw bastion_instance_id` (e.g. `i-0b1eb845a0a77296c`) |
| **Bastion SG** | `sg-05e38417e23f88774` (cdss-dev-bastion-sg) |
| **VPC** | `vpc-0de2b26e7f9394477` |
| **RDS subnets** | subnet-07950d1e26581c0c7 (ap-south-1a), subnet-02f6398592f2062dd (ap-south-1b) |

---

## Why direct connection times out

Even with **PubliclyAccessible: true** and your IP in the RDS security group, connecting from your PC to the Aurora endpoint (**43.204.146.148:5432**) can **time out**. Common reasons:

- RDS subnets have **no route to an Internet Gateway** (private subnets), so the instance is not reachable from the internet.
- Or a firewall/NAT between you and AWS drops the traffic.

So you **must use the SSM tunnel** via the bastion instead of connecting directly to the RDS host.

---

## 1. Start the SSM tunnel (PowerShell)

PowerShell often breaks JSON in `--parameters`. Use **comma-separated** parameters (no JSON):

**Option A – Script (recommended)**

```powershell
cd D:\AI_Hackathon_CDSS
.\scripts\start_ssm_tunnel.ps1
```

Leave this terminal open. You should see: `Port 5433 opened for sessionId ...`

**Option B – One-liner**

**Option B – One-liner (after getting instance ID)**

```powershell
$id = terraform -chdir=infrastructure output -raw bastion_instance_id
aws ssm start-session --target $id --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters "host=cdss-dev-aurora-instance.c3coggyeulk5.ap-south-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433" --region ap-south-1
```

This forwards **localhost:5433** → Aurora:5432. Prefer **Option A** (`.\scripts\start_ssm_tunnel.ps1`), which also starts the bastion if stopped and waits for SSM.

---

## 2. Set DATABASE_URL and run migrations + seed

In a **second** terminal (with the tunnel still running in the first):

```powershell
cd D:\AI_Hackathon_CDSS
$env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
python scripts/run_migrations.py
python -m cdss.db.seed
```

Replace `YOUR_PASSWORD` with the **Aurora master password** (same as Terraform’s `db_password` when the cluster was created).

**Important:** Use database name **`cdssdb`** (no underscore). Terraform creates it in `infrastructure/rds.tf` as `database_name = "cdssdb"`.

---

## 3. Terraform variables for the password

Terraform expects **`db_username`** and **`db_password`** (snake_case), not `DB_USER` / `DB_PASSWORD`. So in `infrastructure/terraform.tfvars` you should have:

```hcl
db_username = "cdssadmin"
db_password = "REPLACE_WITH_AURORA_MASTER_PASSWORD"   # use a strong password; keep tfvars gitignored
```

If the cluster was created with different values (e.g. via `TF_VAR_db_password`), use that same password in `DATABASE_URL`.

---

## 4. Quick reference

| Goal | Command |
|------|--------|
| Start tunnel | `.\scripts\start_ssm_tunnel.ps1` |
| DATABASE_URL (tunnel) | `postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb` |
| Migrations | `python scripts/run_migrations.py` |
| Seed | `python -m cdss.db.seed` |
| Seed via script | `$env:CDSS_DB_PASSWORD='password'; .\scripts\run_seed_via_tunnel.ps1` |
| **Test API with real DB** | Tunnel running → `$env:DATABASE_URL="postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"; python scripts/test_api_local.py` |

Full tunnel/seed details are also in **config/aurora_tunnel_config.json**.

---

## 5. Running test_api_local.py (and other scripts) with real DB

If you set `DATABASE_URL` but **do not** use the tunnel, you will see connection errors such as:

- **"Audit log DB write failed"** and **"Patient handler error"** with `sqlalchemy.engine.raw_connection()` failing (timeout or connection refused).

**Cause:** From your PC you cannot reach the Aurora host directly (see [Why direct connection times out](#why-direct-connection-times-out)). If `DATABASE_URL` points at the Aurora endpoint (e.g. `cdss-dev-aurora-instance....rds.amazonaws.com:5432`), the connection will time out. If it points at `localhost:5433` but the **tunnel is not running**, nothing is listening on 5433 and the connection is refused.

**Correct steps:**

1. **Terminal 1 – start the SSM tunnel** (leave it open):
   ```powershell
   cd D:\AI_Hackathon_CDSS
   .\scripts\start_ssm_tunnel.ps1
   ```
   Wait until you see something like: `Port 5433 opened for sessionId ...`

2. **Terminal 2 – set DATABASE_URL to localhost via tunnel and run the test:**
   ```powershell
   cd D:\AI_Hackathon_CDSS
   $env:DATABASE_URL = "postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb"
   python scripts/test_api_local.py
   ```
   Replace `YOUR_PASSWORD` with the same Aurora master password used in Terraform (`db_password`). Use database name **`cdssdb`** (not `cdss_db` or `postgres`).

**Checklist:**

| Check | Action |
|-------|--------|
| Tunnel running? | Terminal 1 must have `start_ssm_tunnel.ps1` (or the `aws ssm start-session` one-liner) running; no "Connection closed" or exit. |
| Host in DATABASE_URL | Must be **localhost** (or **127.0.0.1**), not the Aurora hostname. |
| Port in DATABASE_URL | Must be **5433** (local tunnel port), not 5432. |
| Database name | **cdssdb** (no underscore). |
| Password | Same as `db_password` in Terraform / used when creating the cluster. |

Same steps apply for `run_api_local.py`, migrations, seed, or any script that uses `get_session()` and a real DB.

---

## 6. SSM tunnel error: "TargetNotConnected"

If you see:

```text
An error occurred (TargetNotConnected) when calling the StartSession operation: <instance-id> is not connected.
```

the **bastion EC2 instance is not available to SSM**. Common causes:

| Cause | What to do |
|-------|------------|
| **Instance stopped** | Run `.\scripts\start_ssm_tunnel.ps1` (it starts the instance and waits for SSM). Or in AWS Console → EC2 → Instances, find the bastion (name `cdss-dev-bastion`), start it, wait 2–3 minutes, then run the tunnel again. |
| **Instance terminated** | Run `terraform output bastion_instance_id` from `infrastructure/` to get the current ID. The script `start_ssm_tunnel.ps1` uses Terraform output automatically. |
| **SSM Agent / IAM** | Instance must have SSM Agent (default on Amazon Linux 2) and an IAM instance profile with `AmazonSSMManagedInstanceCore`. Check in EC2 → Instance → Security → IAM role. |
| **No outbound internet** | Bastion needs outbound access to SSM endpoints (443). If the subnet has no NAT Gateway / Internet Gateway, SSM can’t reach the instance. Use a public subnet or add VPC endpoints for SSM. |

**Quick check (PowerShell):**

```powershell
$id = terraform -chdir=infrastructure output -raw bastion_instance_id
aws ec2 describe-instance-status --instance-ids $id --region ap-south-1
```

- If you get `InvalidInstanceID.NotFound`, the instance no longer exists; run `terraform apply` in `infrastructure/` to recreate the bastion.
- If `InstanceState.Name` is `stopped`, run `.\scripts\start_ssm_tunnel.ps1` (it starts the instance and waits for SSM), or start it in the EC2 console and retry the tunnel.

**Production setup:** All database access uses the bastion and SSM tunnel to Aurora. There is no local Postgres path; start the tunnel with `.\scripts\start_ssm_tunnel.ps1`, then set `DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb` for migrations, seed, and API.
