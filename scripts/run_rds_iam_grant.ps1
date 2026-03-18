# Run one-time RDS IAM grant (GRANT rds_iam TO db_username) so Lambda can use IAM auth.
# Requires: tunnel running, DATABASE_URL in .env (or CDSS_DB_* env vars). Optional: TF_VAR_db_username.

$ErrorActionPreference = "Stop"
$RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { (Get-Location).Path }

# Load .env if present (do not overwrite DATABASE_URL if already set, e.g. IAM token from set_db_url_iam.ps1)
$EnvFile = Join-Path $RepoRoot ".env"
$existingDbUrl = $env:DATABASE_URL
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $k = $matches[1].Trim()
            if ($k -eq "DATABASE_URL" -and $existingDbUrl) { return }
            [System.Environment]::SetEnvironmentVariable($k, $matches[2].Trim(), "Process")
        }
    }
}
if ($existingDbUrl) { $env:DATABASE_URL = $existingDbUrl }

python (Join-Path $RepoRoot "scripts\run_rds_iam_grant.py")
exit $LASTEXITCODE
