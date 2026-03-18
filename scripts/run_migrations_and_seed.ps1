# Run migrations then seed. Use in a second terminal while the tunnel is running.
# Terminal 1: .\scripts\start_ssm_tunnel.ps1  (or start_ssh_tunnel.ps1)
# Terminal 2: .\scripts\set_db_url_iam.ps1 then .\scripts\run_migrations_and_seed.ps1  (Aurora uses IAM auth)
# Or: .env with DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb (only if not using IAM auth)

$ErrorActionPreference = "Stop"
$repoRoot = Join-Path $PSScriptRoot ".."
Push-Location $repoRoot

# Load .env; do not overwrite DATABASE_URL if already set (e.g. IAM token from set_db_url_iam.ps1)
$existingDbUrl = $env:DATABASE_URL
$envFile = Join-Path $repoRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $k = $matches[1].Trim(); $v = $matches[2].Trim()
            if ($k -eq "DATABASE_URL" -and $existingDbUrl) { return }
            [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
        }
    }
}
if ($existingDbUrl) { $env:DATABASE_URL = $existingDbUrl }

# Optional: warn if tunnel port not listening
$tcp = Get-NetTCPConnection -LocalPort 5433 -ErrorAction SilentlyContinue
if (-not $tcp) {
    Write-Host "WARNING: Nothing listening on port 5433. Start the tunnel first: .\scripts\start_ssm_tunnel.ps1 (or start_ssh_tunnel.ps1)" -ForegroundColor Yellow
    Write-Host "Continuing anyway in case you use a different tunnel or local DB..." -ForegroundColor Gray
}

Write-Host "Running migrations..." -ForegroundColor Cyan
$env:PYTHONPATH = "src"
python scripts/run_migrations.py
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }

Write-Host "`nSeeding database..." -ForegroundColor Cyan
python scripts/seed_db.py
$exit = $LASTEXITCODE
Pop-Location
exit $exit
