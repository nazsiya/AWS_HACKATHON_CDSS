# Phase 1.3 verification - PowerShell (no && required)
# Run from repo root: .\scripts\run_phase1_verify.ps1
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repoRoot "src"))) { $repoRoot = (Get-Location).Path }
Set-Location $repoRoot
$env:PYTHONPATH = "src"
python scripts/verify_phase1_local_api.py
exit $LASTEXITCODE
