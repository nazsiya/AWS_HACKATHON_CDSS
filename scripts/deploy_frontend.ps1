# Deploy frontend (doctor-dashboard and optionally patient-dashboard) to S3 and invalidate CloudFront.
# Run from repo root. Requires: Terraform already applied, AWS CLI configured.
# Optional: pass API URL and bucket names; otherwise they are read from terraform output.

param(
    [string] $ApiUrl = "",
    [string] $WsUrl = "",
    [string] $StaffBucket = "",
    [string] $PatientBucket = "",
    [string] $StaffCfId = "",
    [string] $PatientCfId = "",
    [switch] $StaffOnly,
    [switch] $SkipInvalidation
)

$ErrorActionPreference = "Stop"
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }
$InfraDir = Join-Path $RepoRoot "infrastructure"
$DoctorDist = Join-Path $RepoRoot "frontend\apps\doctor-dashboard\dist"
$PatientDist = Join-Path $RepoRoot "frontend\apps\patient-dashboard\dist"

function Get-TerraformOutput {
    param([string] $Name)
    Push-Location $InfraDir
    try {
        $v = terraform output -raw $Name 2>$null
        if (-not $v) { return "" }
        return $v.Trim()
    } finally { Pop-Location }
}

# Resolve API URL and buckets from Terraform if not provided
if (-not $ApiUrl)   { $ApiUrl   = Get-TerraformOutput "api_gateway_url" }
if (-not $StaffBucket) { $StaffBucket = Get-TerraformOutput "s3_bucket_name" }
if (-not $PatientBucket) { $PatientBucket = Get-TerraformOutput "s3_bucket_corpus" }
if (-not $WsUrl)    { $WsUrl    = Get-TerraformOutput "websocket_url" }
if (-not $StaffCfId)   { $StaffCfId   = Get-TerraformOutput "staff_app_cf_id" }
if (-not $PatientCfId) { $PatientCfId = Get-TerraformOutput "patient_portal_cf_id" }
$CognitoPoolId = Get-TerraformOutput "cognito_user_pool_id"
$CognitoStaffClientId = Get-TerraformOutput "cognito_staff_client_id"
$CognitoRegion = "ap-south-1"

if (-not $ApiUrl) {
    Write-Warning "API URL not set. Set VITE_API_URL or run from repo with Terraform applied and pass -ApiUrl."
}
if (-not $StaffBucket) {
    Write-Error "Staff S3 bucket unknown. Apply Terraform first or pass -StaffBucket."
}

# Build doctor-dashboard with production env
$DoctorEnv = @{
    VITE_API_URL   = $ApiUrl
    VITE_WS_URL    = $WsUrl
    VITE_USE_MOCK  = "false"
}
if ($CognitoPoolId) {
    $DoctorEnv["VITE_COGNITO_USER_POOL_ID"] = $CognitoPoolId
    $DoctorEnv["VITE_COGNITO_CLIENT_ID"]    = $CognitoStaffClientId
    $DoctorEnv["VITE_COGNITO_REGION"]       = $CognitoRegion
}
Write-Host "Building doctor-dashboard with VITE_API_URL=$ApiUrl"
Push-Location (Join-Path $RepoRoot "frontend\apps\doctor-dashboard")
try {
    foreach ($k in $DoctorEnv.Keys) { [Environment]::SetEnvironmentVariable($k, $DoctorEnv[$k], "Process") }
    npm run build 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Build failed" }
} finally { Pop-Location }

if (-not (Test-Path $DoctorDist)) {
    Write-Error "Build output not found: $DoctorDist"
}

Write-Host "Uploading doctor-dashboard to s3://$StaffBucket/"
aws s3 sync $DoctorDist "s3://$StaffBucket/" --delete
if ($LASTEXITCODE -ne 0) { Write-Error "S3 sync failed" }

if (-not $SkipInvalidation -and $StaffCfId) {
    Write-Host "Invalidating CloudFront distribution $StaffCfId"
    aws cloudfront create-invalidation --distribution-id $StaffCfId --paths "/*"
}

if (-not $StaffOnly -and $PatientBucket) {
    Write-Host "Building patient-dashboard..."
    Push-Location (Join-Path $RepoRoot "frontend\apps\patient-dashboard")
    try {
        [Environment]::SetEnvironmentVariable("VITE_API_URL", $ApiUrl, "Process")
        [Environment]::SetEnvironmentVariable("VITE_USE_MOCK", "false", "Process")
        npm run build 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Patient-dashboard build failed" }
    } finally { Pop-Location }
    if (Test-Path $PatientDist) {
        Write-Host "Uploading patient-dashboard to s3://$PatientBucket/"
        aws s3 sync $PatientDist "s3://$PatientBucket/" --delete
        if (-not $SkipInvalidation -and $PatientCfId) {
            aws cloudfront create-invalidation --distribution-id $PatientCfId --paths "/*"
        }
    }
}

Write-Host "Deploy done. Staff app: s3://$StaffBucket/ (CloudFront: $StaffCfId)"
if ($CognitoPoolId) {
    Write-Host ""
    Write-Host "To enable demo login on the deployed link, run once:"
    Write-Host "  python scripts/auth/create_superuser.py --demo           # admin/doctor"
    Write-Host "  python scripts/auth/create_superuser.py --demo-patient    # patient"
    Write-Host "  Set DEMO_PASSWORD and PATIENT_DEMO_PASSWORD in env when running; do not commit credentials."
}
