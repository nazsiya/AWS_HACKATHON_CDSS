# Bastion Host + SSH Tunnel to Aurora

Steps to access Aurora from your laptop using a bastion host.

---

## 1. Get your public IP

```bash
curl -s ifconfig.me
# Example: 203.0.113.42 → use 203.0.113.42/32
```

---

## 2. Add bastion variables to terraform.tfvars

Edit `infrastructure/terraform.tfvars`:

```hcl
enable_bastion         = true
bastion_ssh_public_key = "ssh-rsa AAAA... your-key-content"   # from ~/.ssh/id_rsa.pub
bastion_allowed_cidr   = "YOUR_IP/32"                         # e.g. 203.0.113.42/32
```

**Get your SSH public key:**
```bash
cat ~/.ssh/id_rsa.pub
```

---

## 3. Apply Terraform

```bash
cd infrastructure
terraform apply
```

After apply, note the output:
```
bastion_public_ip = "54.x.x.x"
aurora_cluster_endpoint = "emergency-medical-triage-dev-aurora-cluster.cluster-xxx.us-east-1.rds.amazonaws.com"
```

---

## 4. Start SSH tunnel

Replace `BASTION_IP` and `AURORA_ENDPOINT` with values from `terraform output`:

```bash
ssh -i ~/.ssh/id_rsa -N -L 5432:AURORA_ENDPOINT:5432 ec2-user@BASTION_IP
```

**Example:**
```bash
ssh -i ~/.ssh/id_rsa -N -L 5432:emergency-medical-triage-dev-aurora-cluster.cluster-cub0km86ov53.us-east-1.rds.amazonaws.com:5432 ec2-user@54.123.45.67
```

Keep this terminal open. The tunnel forwards local port 5432 to Aurora.

---

## 5. Run RDS test (in another terminal)

Override the RDS config to use localhost:

```bash
# Create a temporary config that points to localhost (tunnel)
export RDS_CONFIG_OVERRIDE='{"host":"127.0.0.1","port":5432,"database":"triagedb","username":"triagemaster","region":"us-east-1"}'
```

The test reads from Secrets Manager by default. To use the tunnel, you need the test to connect to 127.0.0.1. The easiest way: run the test with the tunnel active — but the test fetches host from Secrets Manager (the real Aurora endpoint). So we need to either:
- Add support in the test for `RDS_HOST_OVERRIDE=127.0.0.1`, or
- Use psql directly.

**Option A – Use psql (password auth):**
```bash
psql -h 127.0.0.1 -p 5432 -U triagemaster -d triagedb
# Password: your db_password from terraform.tfvars
```

**Option B – Run the RDS test through the tunnel:**

With the tunnel running, in another terminal:
```bash
RDS_HOST_OVERRIDE=127.0.0.1 pytest tests/test_rds.py -v
```

---

## 6. One-time: grant IAM auth (if using IAM token)

Connect with password first and run:

```sql
GRANT rds_iam TO triagemaster;
```

---

## Summary

| Step | Command |
|------|---------|
| 1. Get IP | `curl -s ifconfig.me` → `x.x.x.x/32` |
| 2. Add to tfvars | `enable_bastion`, `bastion_ssh_public_key`, `bastion_allowed_cidr` |
| 3. Apply | `terraform apply` |
| 4. Tunnel | `ssh -i ~/.ssh/id_rsa -N -L 5432:AURORA_ENDPOINT:5432 ec2-user@BASTION_IP` |
| 5. Connect | `psql -h 127.0.0.1 -p 5432 -U triagemaster -d triagedb` or run RDS test |
