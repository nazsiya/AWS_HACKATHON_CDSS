# Pre-Terraform check: ensure layer.zip exists and remind about required variables.
# Run from repo root before: cd infrastructure; terraform apply

$ErrorActionPreference = "Stop"
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
$LayerZip = Join-Path $RepoRoot "infrastructure\layer.zip"

Write-Host "Pre-Terraform check for CDSS deploy" -ForegroundColor Cyan

# 1. Lambda layer
if (-not (Test-Path $LayerZip)) {
    Write-Host "layer.zip not found. Building it now..." -ForegroundColor Yellow
    & (Join-Path $RepoRoot "scripts\build_lambda_layer.ps1")
    if (-not (Test-Path $LayerZip)) {
        Write-Error "Failed to create infrastructure/layer.zip"
    }
} else {
    Write-Host "[OK] infrastructure/layer.zip exists"
}

# 2. Required Terraform variables (no default in variables.tf)
$dbUser = $env:TF_VAR_db_username
$dbPass = $env:TF_VAR_db_password
if (-not $dbUser -or -not $dbPass) {
    Write-Host ""
    Write-Host "Set Terraform variables before apply (required):" -ForegroundColor Yellow
    Write-Host '  $env:TF_VAR_db_username = "cdssadmin"'
    Write-Host '  $env:TF_VAR_db_password = "YOUR_AURORA_MASTER_PASSWORD"'
    Write-Host "  Or use -var / terraform.tfvars (terraform.tfvars is gitignored)."
    Write-Host ""
}

Write-Host "Next: cd infrastructure; terraform apply -input=false -auto-approve" -ForegroundColor Green
