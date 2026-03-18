# Start CDSS backend for local dev: tunnel (new window) + API (this window).
# Run from repo root: .\scripts\run_dev_backend.ps1
# Then in another terminal: cd frontend\apps\doctor-dashboard; npm run dev

$ErrorActionPreference = "Stop"
$repoRoot = Join-Path $PSScriptRoot ".."
Push-Location $repoRoot

# Load .env from repo root so DATABASE_URL is set
$envFile = Join-Path $repoRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $k = $matches[1].Trim(); $v = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
        }
    }
    Write-Host "Loaded .env (DATABASE_URL set: $($env:DATABASE_URL -ne ''))" -ForegroundColor Gray
}

# Check tunnel port
$tcp = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
if (-not $tcp) {
    Write-Host ""
    Write-Host "WARNING: Nothing listening on port 5433 (DB tunnel)." -ForegroundColor Yellow
    Write-Host "Opening a new window to start the SSM tunnel (no port 22 needed; use this if SSH times out)." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot'; .\scripts\start_ssm_tunnel.ps1"
    Write-Host "Waiting 60 seconds for SSM tunnel to connect (bastion may need to start)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 60
} else {
    Write-Host "Tunnel already running on port 5433." -ForegroundColor Green
}

# Ensure PYTHONPATH
$env:PYTHONPATH = "src"
if (-not $env:DATABASE_URL) {
    Write-Host ""
    Write-Host "DATABASE_URL is not set. API will use mock data." -ForegroundColor Yellow
    Write-Host "Set DATABASE_URL in .env (e.g. postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb) for real DB." -ForegroundColor Gray
} else {
    Write-Host "Starting API with DATABASE_URL (port 5433)." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "CDSS Backend - leave this window open. Frontend: npm run dev in frontend\apps\doctor-dashboard" -ForegroundColor Cyan
Write-Host ""

# Generate temporary IAM token for the SSH tunnel connection (per DEBUGGING_REPORT: Aurora uses IAM auth).
$pyToken = @"
import boto3, json
from urllib.parse import quote_plus
try:
    sm = boto3.client('secretsmanager', region_name='ap-south-1')
    cfg = json.loads(sm.get_secret_value(SecretId='cdss-dev/rds-config')['SecretString'])
    host, username = cfg['host'], cfg.get('username', 'cdssadmin')
    database = cfg.get('database', 'cdssdb')
    token = boto3.client('rds', region_name='ap-south-1').generate_db_auth_token(DBHostname=host, Port=5432, DBUsername=username)
    print(f'postgresql://{username}:{quote_plus(token)}@localhost:5433/{database}?sslmode=require')
except Exception as e:
    pass
"@
$env:DATABASE_URL = python -c $pyToken

if (-not $env:DATABASE_URL) {
    Write-Host "Failed to generate AWS IAM token for database. Continuing with mock data." -ForegroundColor Yellow
}

python scripts/run_api_local.py
Pop-Location
