# Test AI assistance (chat) and AI summary using MOCK data (no Aurora/tunnel).
# Run from repo root: .\scripts\test_ai_with_mock.ps1
#
# This script:
#   1. Uses mock data (unsets DATABASE_URL so run_api_local.py uses in-memory mock).
#   2. Starts the API in a new window (or skips if -NoLaunchApi).
#   3. Runs Phase 4 verification (GET /health, POST /agent, POST /api/ai/summarize).
#   4. Prints a short "conversation": two AI chat messages + one AI summary response.
#
# Optional: .\scripts\test_ai_with_mock.ps1 -NoLaunchApi   (if API is already running)

param(
    [switch]$NoLaunchApi = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = Join-Path $PSScriptRoot ".."
Push-Location $repoRoot

# Force mock data: no database
$env:DATABASE_URL = ""
$env:PYTHONPATH = "src"
$baseUrl = "http://localhost:8080"

Write-Host "=== AI assistance & AI summary test (MOCK data) ===" -ForegroundColor Cyan
Write-Host "  DATABASE_URL unset -> API will use mock patients/surgeries." -ForegroundColor Gray
Write-Host ""

if (-not $NoLaunchApi) {
    $tcp = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    if ($tcp) {
        Write-Host "Port 8080 already in use. Using existing API (or start manually with mock)." -ForegroundColor Yellow
    } else {
        Write-Host "Starting API in a new window (mock data)..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot'; `$env:DATABASE_URL=''; `$env:PYTHONPATH='src'; python scripts/run_api_local.py"
        Write-Host "Waiting 8 seconds for API to start..." -ForegroundColor Gray
        Start-Sleep -Seconds 8
    }
} else {
    Write-Host "Skipping API launch (-NoLaunchApi). Ensure API is running on $baseUrl with mock data." -ForegroundColor Gray
}

# Wait for health
$maxAttempts = 5
$attempt = 0
$healthy = $false
while ($attempt -lt $maxAttempts) {
    try {
        $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get -TimeoutSec 5
        if ($health.status -eq "ok") {
            $healthy = $true
            Write-Host "  API health: OK (database=$($health.database))" -ForegroundColor Green
            break
        }
    } catch { }
    $attempt++
    if ($attempt -lt $maxAttempts) { Start-Sleep -Seconds 2 }
}
if (-not $healthy) {
    Write-Host "API did not become ready. Start manually: `$env:DATABASE_URL=''; `$env:PYTHONPATH='src'; python scripts/run_api_local.py" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "--- Phase 4 verification ---" -ForegroundColor Cyan
python scripts/verify_phase4_ai.py
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "--- Short conversation: AI assistance (chat) + AI summary ---" -ForegroundColor Cyan
Write-Host ""

# 1. AI chat: List patients
Write-Host "You: List patients" -ForegroundColor Yellow
try {
    $r1 = Invoke-RestMethod -Uri "$baseUrl/agent" -Method Post -Body '{"message":"List patients"}' -ContentType "application/json" -TimeoutSec 30
    $d1 = $r1.data
    if ($d1.reply) { Write-Host "AI: $($d1.reply)" } else { Write-Host "AI: (reply in data)" $d1 }
    if ($r1.safety_disclaimer) { Write-Host "  [$($r1.safety_disclaimer)]" -ForegroundColor DarkGray }
} catch { Write-Host "AI: Error: $_" -ForegroundColor Red }
Write-Host ""

# 2. AI chat: Drug interactions
Write-Host "You: Any drug interactions for metformin and amlodipine?" -ForegroundColor Yellow
try {
    $r2 = Invoke-RestMethod -Uri "$baseUrl/agent" -Method Post -Body '{"message":"Any drug interactions for metformin and amlodipine?"}' -ContentType "application/json" -TimeoutSec 30
    $d2 = $r2.data
    if ($d2.reply) { Write-Host "AI: $($d2.reply)" } else { Write-Host "AI: (reply in data)" $d2 }
    if ($r2.safety_disclaimer) { Write-Host "  [$($r2.safety_disclaimer)]" -ForegroundColor DarkGray }
} catch { Write-Host "AI: Error: $_" -ForegroundColor Red }
Write-Host ""

# 3. AI summary (ad-hoc text)
Write-Host "You (summarize): POST /api/ai/summarize with clinical text" -ForegroundColor Yellow
$summarizeBody = '{"text":"Patient has hypertension. Currently on amlodipine 5mg. Last BP 138/88. HbA1c 7.2."}'
try {
    $r3 = Invoke-RestMethod -Uri "$baseUrl/api/ai/summarize" -Method Post -Body $summarizeBody -ContentType "application/json" -TimeoutSec 30
    if ($r3.summary) { Write-Host "AI summary: $($r3.summary)" } else { Write-Host "AI summary: $($r3.error)" }
    if ($r3.safety_disclaimer) { Write-Host "  [$($r3.safety_disclaimer)]" -ForegroundColor DarkGray }
} catch { Write-Host "AI summary: Error: $_" -ForegroundColor Red }

Write-Host ""
Write-Host "=== Done. For interactive chat run: .\scripts\chat_agent_powershell.ps1 ===" -ForegroundColor Cyan
Pop-Location
