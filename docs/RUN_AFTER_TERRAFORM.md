# Run after Terraform apply (SSH bastion)

If Terraform apply is still running or the state file is locked, wait for it to finish. If it was killed (e.g. timeout), run apply again:

```powershell
cd d:\AI_Hackathon_CDSS\infrastructure
$env:TF_VAR_db_username = 'cdssadmin'
$env:TF_VAR_db_password = 'YOUR_SECURE_PASSWORD'
terraform apply -input=false -auto-approve
```

When apply completes, you should see `bastion_public_ip` and `aurora_cluster_endpoint` in the outputs.

---

## 1. Start SSH tunnel

From repo root, using the key generated in `.ssh/bastion_id_rsa`:

```powershell
cd d:\AI_Hackathon_CDSS
.\scripts\start_ssh_tunnel.ps1
```

(Or pass your key: `.\scripts\start_ssh_tunnel.ps1 -KeyPath "C:\Users\You\.ssh\id_rsa"`)

Leave this terminal open. Tunnel is `localhost:5433` → Aurora:5432.

---

## 2. Migrations + seed

In a **second terminal**:

```powershell
cd d:\AI_Hackathon_CDSS
.\scripts\run_migrations_and_seed.ps1
```

Ensure `.env` has `DATABASE_URL=postgresql://cdssadmin:YOUR_PASSWORD@localhost:5433/cdssdb` (password = Terraform `db_password`).

---

## 3. RDS IAM auth (one-time, for Lambda)

If Lambda will connect to Aurora using IAM auth (when `enable_lambda_vpc = true`), grant the role once. Either run the script (tunnel + `DATABASE_URL` in `.env`):

```powershell
.\scripts\run_rds_iam_grant.ps1
```

Or connect via tunnel with password and run in PostgreSQL:

```sql
GRANT rds_iam TO cdssadmin;
```

Use the same username as `TF_VAR_db_username` (e.g. `cdssadmin`). After that, Lambda can use the token from Secrets Manager.

---

## If password authentication fails

If migrations or seed fail with `password authentication failed for user "cdssadmin"`:

- The password in `.env` must match the Aurora master password (same as `TF_VAR_db_password` used when the cluster was created).
- If the cluster was created earlier with a different password, either put that password in `.env`, or reset the master password in **RDS Console** (Modify cluster → Master password) to match `.env`.

---

## If Terraform state is locked

Another Terraform process may still be running. Either wait for it to exit or stop it:

```powershell
Get-Process -Name terraform -ErrorAction SilentlyContinue | Stop-Process -Force
```

Then run `terraform apply` again as above.
