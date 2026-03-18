# Phase 4 verification: AI summary and AI chatbot
# Run from repo root: .\scripts\run_phase4_verify.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8081" }
$env:BASE_URL = $baseUrl

Write-Host "Phase 4: Verifying AI summary and AI chatbot (BASE_URL=$baseUrl)" -ForegroundColor Cyan
Write-Host ""

# Check if server is up
try {
    $r = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -ne 200) { throw "Health returned $($r.StatusCode)" }
} catch {
    Write-Host "API at $baseUrl is not reachable. Start it first:" -ForegroundColor Yellow
    Write-Host "  `$env:PORT=\"8081\"; python scripts/run_api_local.py" -ForegroundColor Gray
    Write-Host "Then run this script again." -ForegroundColor Gray
    exit 1
}

python scripts/verify_phase4_ai.py
exit $LASTEXITCODE
