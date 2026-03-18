# Run the local CDSS API connected to Aurora via SSM tunnel.
# Prereq: In another terminal, start the tunnel first: .\scripts\start_ssm_tunnel.ps1
# Then run this script, then start the frontend (npm run dev in frontend/apps/doctor-dashboard).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repoRoot "src"))) { $repoRoot = (Get-Location).Path }

$env:PYTHONPATH = Join-Path $repoRoot "src"
$env:RDS_CONFIG_SECRET_NAME = "cdss-dev/rds-config"
$env:AWS_REGION = "ap-south-1"
$env:TUNNEL_LOCAL_PORT = "10021"

Write-Host "CDSS API → Aurora (tunnel localhost:10021). Ensure SSM tunnel is running in another terminal."
Set-Location $repoRoot
python scripts/run_api_local.py
