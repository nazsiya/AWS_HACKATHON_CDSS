# Set DATABASE_URL with a fresh IAM auth token for Aurora (per DEBUGGING_REPORT).
# Run this in the same terminal before list_aurora_tables.py, run_db_query.py, migrations, or seed.
# Prerequisite: SSM tunnel must be running in another terminal (.\scripts\start_ssm_tunnel.ps1).
#
# Usage:
#   .\scripts\set_db_url_iam.ps1
#   python scripts/list_aurora_tables.py

$ErrorActionPreference = "Stop"
$repoRoot = Join-Path $PSScriptRoot ".."
Push-Location $repoRoot

$py = @'
import boto3, json, sys
from urllib.parse import quote_plus
try:
    sm = boto3.client("secretsmanager", region_name="ap-south-1")
    raw = sm.get_secret_value(SecretId="cdss-dev/rds-config")["SecretString"]
    cfg = json.loads(raw)
    host = cfg["host"]
    username = cfg.get("username", "cdssadmin")
    database = cfg.get("database", "cdssdb")
    token = boto3.client("rds", region_name="ap-south-1").generate_db_auth_token(DBHostname=host, Port=5432, DBUsername=username)
    print(f"postgresql://{username}:{quote_plus(token)}@localhost:5433/{database}?sslmode=require")
except Exception as e:
    print("Error: " + str(e), file=sys.stderr)
    sys.exit(1)
'@
$url = python -c $py 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $url -ForegroundColor Red
    Write-Host "Ensure: (1) AWS CLI configured, (2) Secret cdss-dev/rds-config exists, (3) SSM tunnel running (.\scripts\start_ssm_tunnel.ps1)." -ForegroundColor Yellow
    Pop-Location
    exit 1
}
$env:DATABASE_URL = $url.Trim()
Write-Host "DATABASE_URL set (IAM token). Run: python scripts/list_aurora_tables.py" -ForegroundColor Green
Pop-Location
