# Post-Deploy Checklist — Connect Backend to Database

After running **deploy** (Terraform + frontend), do the following **once** so the deployed dashboard shows real data and the "Backend is not connected to the database" banner disappears.

---

## 1. Start the DB tunnel (Terminal 1 — leave open)

**SSH** (if your IP is in `infrastructure/terraform.tfvars` → `bastion_allowed_cidr`):

```powershell
cd D:\AI_Hackathon_CDSS
.\scripts\start_ssh_tunnel.ps1
```

**If SSH times out**, use **SSM** (HTTPS 443; no port 22):

```powershell
.\scripts\start_ssm_tunnel.ps1
```

Wait until the script indicates the tunnel is active (localhost:5433 → Aurora).

---

## 2. Run migrations, seed, and RDS IAM grant (Terminal 2)

With the tunnel running in Terminal 1:

```powershell
cd D:\AI_Hackathon_CDSS
.\scripts\run_after_tunnel.ps1
```

This sets `DATABASE_URL` with an IAM token (Aurora uses IAM auth), runs migrations, seeds the database, and runs `GRANT rds_iam TO cdssadmin` so Lambda can connect.

---

## 3. Refresh the dashboard

Open the deployed dashboard (e.g. https://d2yy4v2hr1otkm.cloudfront.net) and refresh. The banner should be gone and you should see real data. No API restart or redeploy needed.

---

## Scripts reference

| Script | Purpose |
|--------|--------|
| `.\scripts\deploy.ps1` | Pre-check + Terraform apply |
| `.\scripts\deploy_frontend.ps1` | Build and deploy doctor/patient dashboard to S3 + CloudFront |
| `.\scripts\start_ssh_tunnel.ps1` | SSH tunnel to Aurora (port 5433) |
| `.\scripts\start_ssm_tunnel.ps1` | SSM tunnel (use if SSH times out) |
| `.\scripts\run_after_tunnel.ps1` | Migrations + seed + RDS IAM grant (tunnel must be up) |
| `.\scripts\connect_backend_to_db.ps1` | Tries to start tunnel in a new window, then runs run_after_tunnel steps |

See internal runbooks or contact the team for detailed troubleshooting (tunnel, IAM, DB).
