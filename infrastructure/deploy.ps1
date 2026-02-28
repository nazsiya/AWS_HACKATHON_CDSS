# Deploy CDSS infrastructure with Terraform
# Usage: .\deploy.ps1 [-Stage dev] [-Apply]
#   -Stage: dev (default) or prod
#   -Apply: if set, runs terraform apply; otherwise only init + plan

param(
    [ValidateSet("dev", "prod")]
    [string] $Stage = "dev",
    [switch] $Apply
)

Set-Location $PSScriptRoot

Write-Host "=== CDSS Infrastructure Deploy (Stage: $Stage) ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Running terraform init..." -ForegroundColor Yellow
terraform init
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Running terraform plan -var stage=$Stage..." -ForegroundColor Yellow
terraform plan -var "stage=$Stage"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Apply) {
    Write-Host ""
    Write-Host "Running terraform apply -var stage=$Stage (auto-approve)..." -ForegroundColor Yellow
    terraform apply -var "stage=$Stage" -auto-approve
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
    Write-Host "Done. API URL: $(terraform output -raw api_gateway_url 2>$null)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "To apply changes, run: .\deploy.ps1 -Stage $Stage -Apply" -ForegroundColor Green
}
