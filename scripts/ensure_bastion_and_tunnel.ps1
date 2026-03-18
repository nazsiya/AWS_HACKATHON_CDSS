# Ensure bastion EC2 exists, is running, and start SSM tunnel to Aurora.
# Run from repo root: .\scripts\ensure_bastion_and_tunnel.ps1
# Then in a second terminal use scripts/run_db_query.py or psql to run queries via localhost:5433.

$ErrorActionPreference = "Stop"
$region = "ap-south-1"
$repoRoot = Join-Path $PSScriptRoot ".."
$infraDir = Join-Path $PSScriptRoot "..\infrastructure"
$localPort = "5433"

# Aurora endpoint (from config/aurora_tunnel_config.json or Terraform; update if your cluster differs)
$auroraHost = "cdss-dev-aurora-instance.c3coggyeulk5.ap-south-1.rds.amazonaws.com"

# Set Terraform DB vars from repo .env (DATABASE_URL) if not already set
if (-not $env:TF_VAR_db_username -or -not $env:TF_VAR_db_password) {
    $envPath = Join-Path $repoRoot ".env"
    if (Test-Path $envPath) {
        Get-Content $envPath | ForEach-Object {
            if ($_ -match '^\s*DATABASE_URL=(.+)$') {
                $url = $Matches[1].Trim()
                if ($url -match '^postgresql://([^:]+):([^@]+)@') {
                    $env:TF_VAR_db_username = $Matches[1]
                    $env:TF_VAR_db_password = $Matches[2]
                }
            }
        }
    }
}
if (-not $env:TF_VAR_db_username -or -not $env:TF_VAR_db_password) {
    Write-Host "Terraform needs db_username and db_password. Set them in infrastructure/terraform.tfvars or in .env as DATABASE_URL=postgresql://USER:PASSWORD@host/db" -ForegroundColor Yellow
}

Write-Host "=== 1. Ensure Terraform state (bastion + VPC + Aurora) ===" -ForegroundColor Cyan
Push-Location $infraDir
try {
    # Use cmd to run Terraform so stderr (e.g. ANSI/UTF-8 from plan) does not trigger PowerShell errors
    cmd /c "terraform init -input=false 2>nul"
    cmd /c "terraform plan -input=false -detailed-exitcode 2>nul"
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 2) {
        Write-Host "Applying Terraform to create/update bastion and networking..." -ForegroundColor Yellow
        cmd /c "terraform apply -input=false -auto-approve 2>nul"
        if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
    } elseif ($exitCode -eq 1) {
        Write-Host "Terraform plan failed." -ForegroundColor Red
        Pop-Location; exit 1
    } else {
        Write-Host "Terraform state OK (no changes or apply succeeded)." -ForegroundColor Green
    }

    $instanceId = terraform output -raw bastion_instance_id 2>$null
    if (-not $instanceId) {
        Write-Host "Could not get bastion_instance_id from Terraform output." -ForegroundColor Red
        Pop-Location; exit 1
    }
    Write-Host "Bastion instance ID: $instanceId" -ForegroundColor Gray
} finally {
    Pop-Location
}

Write-Host "`n=== 2. Ensure bastion EC2 instance is running ===" -ForegroundColor Cyan
$state = aws ec2 describe-instance-status --instance-ids $instanceId --region $region --query "InstanceStatuses[0].InstanceState.Name" --output text 2>$null
if ($state -eq "stopped") {
    Write-Host "Bastion is stopped. Starting..." -ForegroundColor Yellow
    aws ec2 start-instances --instance-ids $instanceId --region $region | Out-Null
    Write-Host "Waiting 45s for instance to boot and SSM agent to register..." -ForegroundColor Gray
    Start-Sleep -Seconds 45
} elseif ($state -ne "running") {
    Write-Host "Waiting for instance to be running..." -ForegroundColor Gray
    aws ec2 wait instance-running --instance-ids $instanceId --region $region
    Start-Sleep -Seconds 25
}

Write-Host "`n=== 3. Wait for SSM agent (TargetNotConnected -> Online) ===" -ForegroundColor Cyan
$maxWait = 120
$waited = 0
while ($waited -lt $maxWait) {
    $ping = aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$instanceId" --region $region --query "InstanceInformationList[0].PingStatus" --output text 2>$null
    if ($ping -eq "Online") {
        Write-Host "SSM status: Online. Tunnel can start." -ForegroundColor Green
        break
    }
    Write-Host "  SSM status: $ping (waiting 10s...)..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    $waited += 10
}
if ($waited -ge $maxWait) {
    Write-Host "SSM did not become Online within ${maxWait}s. Check instance IAM role (AmazonSSMManagedInstanceCore) and network." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== 4. Start SSM port-forward (leave this terminal open) ===" -ForegroundColor Cyan
Write-Host "Tunnel: localhost:$localPort -> $auroraHost`:5432" -ForegroundColor Gray
Write-Host "In a SECOND terminal run:" -ForegroundColor Yellow
Write-Host "  `$env:DATABASE_URL = `"postgresql://cdssadmin:YOUR_PASSWORD@localhost:$localPort/cdssdb`"" -ForegroundColor White
Write-Host "  python scripts/run_db_query.py -q `"SELECT * FROM patients LIMIT 5`"" -ForegroundColor White
Write-Host "  Or: psql `$env:DATABASE_URL -c `"SELECT * FROM patients LIMIT 5`"" -ForegroundColor White
Write-Host ""

$params = "host=$auroraHost,portNumber=5432,localPortNumber=$localPort"
aws ssm start-session `
  --target $instanceId `
  --document-name AWS-StartPortForwardingSessionToRemoteHost `
  --parameters $params `
  --region $region
