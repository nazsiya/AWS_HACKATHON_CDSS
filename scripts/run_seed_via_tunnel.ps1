# Run CDSS DB migrations + seed via SSM tunnel.
# Prerequisite: SSM tunnel must already be running (e.g. .\scripts\start_ssm_tunnel.ps1 in another terminal).
# Uses localhost:5433 -> Aurora:5432. Set DB password via env or .env.

param(
    [string]$Password = $env:CDSS_DB_PASSWORD,
    [string]$DbHost = "localhost",
    [string]$Port = "5433",
    [string]$Database = "cdssdb",
    [string]$User = "cdssdb"
)

$ErrorActionPreference = "Stop"

if (-not $Password) {
    Write-Host "Set CDSS_DB_PASSWORD or pass -Password 'yourpassword'" -ForegroundColor Yellow
    Write-Host "Example: `$env:CDSS_DB_PASSWORD='<your-password>'; .\scripts\run_seed_via_tunnel.ps1" -ForegroundColor Gray
    exit 1
}

$url = "postgresql://${User}:$Password@${DbHost}:${Port}/${Database}"
$env:DATABASE_URL = $url

Write-Host "DATABASE_URL set (host=$DbHost port=$Port db=$Database)" -ForegroundColor Green
Write-Host "Ensure the SSM tunnel is running in another terminal (.\scripts\start_ssm_tunnel.ps1)" -ForegroundColor Gray
Write-Host "Running migrations..." -ForegroundColor Cyan
python scripts/run_migrations.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Running seed..." -ForegroundColor Cyan
python -m cdss.db.seed
exit $LASTEXITCODE
