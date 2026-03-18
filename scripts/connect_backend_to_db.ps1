# Connect deployed backend to database: SSH tunnel + migrations + seed + RDS IAM grant.
# Uses SSH tunnel to deployed Aurora (terraform output: bastion_public_ip, aurora_cluster_endpoint).
# Aurora uses IAM auth – DATABASE_URL is set with IAM token via set_db_url_iam.ps1.
#
# Run from repo root: .\scripts\connect_backend_to_db.ps1
# Requires: AWS CLI configured; secret cdss-dev/rds-config; SSH key matching bastion_ssh_public_key (e.g. .ssh/bastion_id_rsa or ~/.ssh/id_rsa).

$ErrorActionPreference = "Stop"
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
Push-Location $RepoRoot

# Load .env (other vars); DATABASE_URL will be set via IAM token below
$EnvFile = Join-Path $RepoRoot ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $k = $matches[1].Trim()
            if ($k -eq "DATABASE_URL") { return }
            [System.Environment]::SetEnvironmentVariable($k, $matches[2].Trim(), "Process")
        }
    }
}

# 1) Tunnel: SSH to bastion (or SSM fallback if SSH times out per debug report §6).
$tcp = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
if (-not $tcp) {
    Write-Host "Port 5433 not listening. Opening new window for SSH tunnel to deployed Aurora." -ForegroundColor Cyan
    Write-Host "Tunnel uses: terraform output bastion_public_ip, aurora_cluster_endpoint." -ForegroundColor Gray
    Write-Host "Leave that window open. This script will wait 90s for the tunnel." -ForegroundColor Gray
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot'; .\scripts\start_ssh_tunnel.ps1"
    Write-Host "Waiting 90 seconds for SSH tunnel..." -ForegroundColor Yellow
    Start-Sleep -Seconds 90
    $tcp = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
}
if (-not $tcp) {
    Write-Host "SSH tunnel did not connect. Trying SSM tunnel (HTTPS 443; per debug report §6)..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot'; .\scripts\start_ssm_tunnel.ps1"
    Write-Host "Waiting 90 seconds for SSM tunnel..." -ForegroundColor Yellow
    Start-Sleep -Seconds 90
    $tcp = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
}
if (-not $tcp) {
    Write-Host "Tunnel still not up. Start it manually in another terminal:" -ForegroundColor Red
    Write-Host "  .\scripts\start_ssh_tunnel.ps1" -ForegroundColor White
    Write-Host "  or .\scripts\start_ssm_tunnel.ps1  (if SSH times out)" -ForegroundColor White
    Write-Host "Ensure your IP is in infrastructure/terraform.tfvars bastion_allowed_cidr (for SSH) and you have the SSH key." -ForegroundColor Gray
    Write-Host "Then re-run this script." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Tunnel is up (port 5433 -> deployed Aurora)." -ForegroundColor Green

# 2) Set DATABASE_URL with IAM token (per debug report §2, §5 – Aurora uses IAM auth; static password fails)
Write-Host "`nSetting DATABASE_URL with IAM auth token..." -ForegroundColor Cyan
. (Join-Path $RepoRoot "scripts\set_db_url_iam.ps1")
if (-not $env:DATABASE_URL) {
    Write-Host "Failed to set DATABASE_URL. Ensure AWS CLI configured and secret cdss-dev/rds-config exists." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 3) Migrations
Write-Host "`nRunning migrations..." -ForegroundColor Cyan
$env:PYTHONPATH = "src"
python scripts/run_migrations.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Migrations failed." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 4) Seed
Write-Host "`nSeeding database..." -ForegroundColor Cyan
python scripts/seed_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Seed failed." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 5) RDS IAM grant (DATABASE_URL already set with IAM token; run_rds_iam_grant preserves it)
Write-Host "`nRunning RDS IAM grant..." -ForegroundColor Cyan
& (Join-Path $RepoRoot "scripts\run_rds_iam_grant.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "RDS IAM grant failed." -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "`nDone. Backend can now connect to the database. Refresh the dashboard." -ForegroundColor Green
Pop-Location
