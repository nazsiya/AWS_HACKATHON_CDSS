# One-command deploy: pre-check, Terraform apply, then next-step instructions.
# Run from repo root. Requires: infrastructure/terraform.tfvars with db_username and db_password set.

param(
    [switch] $SkipFrontend,
    [switch] $ApplyOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
$InfraDir = Join-Path $RepoRoot "infrastructure"
$Tfvars = Join-Path $InfraDir "terraform.tfvars"
$TfvarsExample = Join-Path $InfraDir "terraform.tfvars.example"

if (-not (Test-Path $Tfvars)) {
    if (Test-Path $TfvarsExample) {
        Copy-Item $TfvarsExample $Tfvars
        Write-Host "Created infrastructure/terraform.tfvars from example." -ForegroundColor Yellow
        Write-Host "Edit it and set db_password (and db_username if needed), then re-run this script." -ForegroundColor Yellow
        exit 1
    }
    Write-Error "infrastructure/terraform.tfvars not found. Create it with db_username and db_password (see terraform.tfvars.example)."
}

$content = Get-Content $Tfvars -Raw
if ($content -match "REPLACE_WITH_AURORA_MASTER_PASSWORD") {
    Write-Host "Set db_password in infrastructure/terraform.tfvars (replace REPLACE_WITH_AURORA_MASTER_PASSWORD), then re-run." -ForegroundColor Yellow
    exit 1
}

Write-Host "Running pre-terraform check..." -ForegroundColor Cyan
& (Join-Path $RepoRoot "scripts\pre_terraform_check.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Running Terraform apply..." -ForegroundColor Cyan
Push-Location $InfraDir
try {
    terraform apply -var-file=terraform.tfvars -input=false -auto-approve
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }

Write-Host ""
Write-Host "Terraform apply done." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start tunnel: .\scripts\start_ssh_tunnel.ps1  (or .\scripts\start_ssm_tunnel.ps1 if SSH times out)"
Write-Host "  2. In another terminal: .\scripts\run_after_tunnel.ps1  (migrations + seed + RDS IAM grant)"
Write-Host "  3. Deploy frontend (if not done): .\scripts\deploy_frontend.ps1"
Write-Host "  See docs\POST_DEPLOY_CHECKLIST.md for full steps."
Write-Host ""

if (-not $SkipFrontend -and -not $ApplyOnly) {
    $r = Read-Host "Deploy frontend now? (y/N)"
    if ($r -eq "y" -or $r -eq "Y") {
        & (Join-Path $RepoRoot "scripts\deploy_frontend.ps1")
    }
}
