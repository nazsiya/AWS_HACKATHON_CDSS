# Phases 1–4 verification with real database (Aurora)
# Run from repo root. Requires API running with DATABASE_URL set (Aurora connected).
# Usage: .\scripts\run_phases_1_to_4_verify.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Join-Path $PSScriptRoot ".."
Set-Location $repoRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8080" }
$env:BASE_URL = $baseUrl
$env:REAL_DB = "1"

Write-Host "Phases 1-4 verification (real database)" -ForegroundColor Cyan
Write-Host "  BASE_URL=$baseUrl" -ForegroundColor Gray
Write-Host "  Ensure API is started with DATABASE_URL set (Aurora)." -ForegroundColor Gray
Write-Host ""

try {
    $r = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -UseBasicParsing -TimeoutSec 5
    $h = $r.Content | ConvertFrom-Json
    if ($h.database -ne "connected") {
        Write-Host "WARNING: /health database=$($h.database). For real DB verification set DATABASE_URL and start API." -ForegroundColor Yellow
    }
} catch {
    Write-Host "API at $baseUrl is not reachable. Start the API with DATABASE_URL set first:" -ForegroundColor Yellow
    Write-Host '  $env:DATABASE_URL = "postgresql://..."; $env:PYTHONPATH="src"; python scripts/run_api_local.py' -ForegroundColor Gray
    Write-Host "Then run this script again." -ForegroundColor Gray
    exit 1
}

# Ensure PYTHONPATH includes src
$env:PYTHONPATH = "src"

python scripts/verify_phases_1_to_4_real_db.py
exit $LASTEXITCODE
