# Start CDSS backend (with real DB via IAM + tunnel) in a new window, then start doctor-dashboard frontend.
# Run from repo root: .\scripts\run_frontend_with_db.ps1
# Backend: http://localhost:8080  |  Frontend: http://localhost:5173

$ErrorActionPreference = "Stop"
$repoRoot = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
if (-not (Test-Path (Join-Path $repoRoot "src"))) { $repoRoot = (Get-Location).Path }

# Ensure frontend .env.local points at API on 8080 and uses real API (not mock)
$envLocalPath = Join-Path $repoRoot "frontend\apps\doctor-dashboard\.env.local"
$envLocalDir = Split-Path $envLocalPath
if (-not (Test-Path $envLocalDir)) { New-Item -ItemType Directory -Path $envLocalDir -Force | Out-Null }
@"
VITE_API_URL=http://localhost:8080
VITE_USE_MOCK=false
"@ | Set-Content $envLocalPath -Encoding utf8 -NoNewline
$content = Get-Content $envLocalPath -Raw
if ($content -notmatch "VITE_API_URL=http://localhost:8080") {
    "VITE_API_URL=http://localhost:8080`nVITE_USE_MOCK=false" | Set-Content $envLocalPath -Encoding utf8
}
Write-Host "Frontend .env.local: VITE_API_URL=http://localhost:8080, VITE_USE_MOCK=false" -ForegroundColor Green

# Start backend in a new window (tunnel + IAM token + API)
Write-Host "Starting backend with database in a new window (leave it open)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoRoot'; .\scripts\run_dev_backend.ps1"

# Wait for API to be ready
$maxAttempts = 30
$attempt = 0
do {
    Start-Sleep -Seconds 1
    $attempt++
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $j = $r.Content | ConvertFrom-Json
        if ($j.database -eq "connected") {
            Write-Host "Backend is up with database connected." -ForegroundColor Green
            break
        }
        if ($j.database -eq "unavailable") {
            Write-Host "Backend is up but database unavailable (tunnel or IAM?). Continuing anyway." -ForegroundColor Yellow
            break
        }
    } catch {
        if ($attempt -ge $maxAttempts) {
            Write-Host "Backend did not respond in time. Start it manually: .\scripts\run_dev_backend.ps1" -ForegroundColor Yellow
            break
        }
    }
} while ($attempt -lt $maxAttempts)

# Start frontend in this window
Write-Host "Starting doctor-dashboard at http://localhost:5173 ..." -ForegroundColor Cyan
Push-Location (Join-Path $repoRoot "frontend\apps\doctor-dashboard")
try {
    npm run dev
} finally {
    Pop-Location
}
