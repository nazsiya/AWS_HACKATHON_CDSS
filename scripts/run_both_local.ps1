# Start CDSS backend API and doctor-dashboard frontend for local development.
# Run from repo root: .\scripts\run_both_local.ps1
# Backend: http://localhost:8081  |  Frontend: http://localhost:5173

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path (Join-Path $repoRoot "src"))) { $repoRoot = (Get-Location).Path }

$env:PORT = "8081"
$env:PYTHONPATH = Join-Path $repoRoot "src"

Write-Host "Starting CDSS backend on http://localhost:8081 ..." -ForegroundColor Cyan
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:repoRoot
    $env:PORT = "8081"
    $env:PYTHONPATH = Join-Path $using:repoRoot "src"
    & python scripts/run_api_local.py
}

# Give API a moment to bind
Start-Sleep -Seconds 2

Write-Host "Starting doctor-dashboard on http://localhost:5173 ..." -ForegroundColor Cyan
Set-Location (Join-Path $repoRoot "frontend\apps\doctor-dashboard")

# Ensure .env.local points at 8081
$envLocal = Join-Path (Get-Location) ".env.local"
if (Test-Path $envLocal) {
    $content = Get-Content $envLocal -Raw
    if ($content -notmatch "VITE_API_URL=http://localhost:8081") {
        Write-Host "Tip: Set VITE_API_URL=http://localhost:8081 and VITE_USE_MOCK=false in .env.local" -ForegroundColor Yellow
    }
} else {
    @"
VITE_API_URL=http://localhost:8081
VITE_USE_MOCK=false
"@ | Set-Content $envLocal -Encoding utf8
    Write-Host "Created .env.local with VITE_API_URL=http://localhost:8081" -ForegroundColor Green
}

try {
    npm run dev
} finally {
    Stop-Job $apiJob -ErrorAction SilentlyContinue
    Remove-Job $apiJob -ErrorAction SilentlyContinue
}
