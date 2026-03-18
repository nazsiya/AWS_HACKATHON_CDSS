# Run migrations + seed + RDS IAM grant (tunnel must already be up on port 5433).
# Per docs/DEBUGGING_REPORT_2026_03_08.md: Aurora uses IAM auth – do not use static password.
#
# Usage:
#   Terminal 1: .\scripts\start_ssh_tunnel.ps1   (or start_ssm_tunnel.ps1) – leave open
#   Terminal 2: .\scripts\run_after_tunnel.ps1
#
# Requires: AWS CLI configured; secret cdss-dev/rds-config.

$ErrorActionPreference = "Stop"
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
Push-Location $RepoRoot

$tcp = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
if (-not $tcp) {
    Write-Host "ERROR: Nothing on port 5433. Start the tunnel first:" -ForegroundColor Red
    Write-Host "  .\scripts\start_ssh_tunnel.ps1" -ForegroundColor White
    Write-Host "  or .\scripts\start_ssm_tunnel.ps1" -ForegroundColor White
    Write-Host "Leave that terminal open, then run this script again." -ForegroundColor Gray
    Pop-Location
    exit 1
}

# Load .env (do not overwrite DATABASE_URL)
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

Write-Host "Setting DATABASE_URL with IAM auth token..." -ForegroundColor Cyan
. (Join-Path $RepoRoot "scripts\set_db_url_iam.ps1")
if (-not $env:DATABASE_URL) {
    Write-Host "Failed to set DATABASE_URL. Ensure AWS CLI configured and secret cdss-dev/rds-config exists." -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "Running migrations..." -ForegroundColor Cyan
$env:PYTHONPATH = "src"
python scripts/run_migrations.py
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

Write-Host "Seeding database..." -ForegroundColor Cyan
python scripts/seed_db.py
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

Write-Host "Running RDS IAM grant..." -ForegroundColor Cyan
& (Join-Path $RepoRoot "scripts\run_rds_iam_grant.ps1")
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

Write-Host "Done. Refresh the deployed dashboard – banner should be gone." -ForegroundColor Green
Pop-Location
