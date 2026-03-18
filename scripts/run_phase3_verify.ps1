# Phase 3 verification - API and frontend-backend connectivity
# Run from repo root: .\scripts\run_phase3_verify.ps1
# Option A: API already running (e.g. on 8081). Set BASE_URL and run connectivity check only.
# Option B: Start API with mock data (no DB), then run connectivity + optional agent check.

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path (Join-Path $repoRoot "src"))) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot

$baseUrl = $env:BASE_URL
if (-not $baseUrl) {
    $baseUrl = "http://localhost:8081"
    $env:BASE_URL = $baseUrl
    Write-Host "BASE_URL not set; using $baseUrl. Set env BASE_URL if your API is on another port." -ForegroundColor Cyan
}

$env:PYTHONPATH = Join-Path $repoRoot "src"

# 1. Quick connectivity (health + patients)
Write-Host "`n--- Phase 3: Frontend–backend connectivity ---" -ForegroundColor Cyan
python scripts/verify_phase3_connectivity.py
$connectivityExit = $LASTEXITCODE

# 2. Optional: agent endpoint (Phase 1.3) - can be slow if Bedrock is used
$skipAgent = $env:SKIP_PHASE1_AGENT -eq "1"
if ($connectivityExit -eq 0 -and -not $skipAgent) {
    Write-Host "`n--- Phase 1.3: Agent endpoint (optional) ---" -ForegroundColor Cyan
    $env:BASE_URL = $baseUrl
    python scripts/verify_phase1_local_api.py
}

if ($connectivityExit -ne 0) {
    Write-Host "`nTip: To run API with mock data (no DB): " -ForegroundColor Yellow
    Write-Host '  $env:DATABASE_URL = ""; $env:PORT = "8081"; python scripts/run_api_local.py' -ForegroundColor Gray
    Write-Host "  Then in another terminal: .\scripts\run_phase3_verify.ps1" -ForegroundColor Gray
    exit $connectivityExit
}
exit 0
