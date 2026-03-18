# Start SSM port-forward from local port to Aurora (bastion must be running).
# This script starts the bastion if stopped, waits for SSM Online, then starts the tunnel.
# Usage: .\scripts\start_ssm_tunnel.ps1
# Then in another terminal set DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb and run python -m cdss.db.seed or scripts/run_db_query.py

$ErrorActionPreference = "Stop"
$infraDir = Join-Path $PSScriptRoot "..\infrastructure"
$hostName = "cdss-dev-aurora-cluster.cluster-c3coggyeulk5.ap-south-1.rds.amazonaws.com"
$localPort = "5433"
$region = "ap-south-1"

# Prefer instance ID from Terraform output; fallback to last known ID
$targetId = $null
if (Test-Path $infraDir) {
    Push-Location $infraDir
    try {
        $targetId = terraform output -raw bastion_instance_id 2>$null
    } finally { Pop-Location }
}
if (-not $targetId) {
    $targetId = "i-0d3f3d64527edbb07"
    Write-Host "Using fallback bastion ID. Run from infra: terraform output bastion_instance_id to refresh." -ForegroundColor Gray
}

# --- Ensure bastion is running and SSM is Online ---
$state = aws ec2 describe-instance-status --instance-ids $targetId --region $region --query "InstanceStatuses[0].InstanceState.Name" --output text 2>$null
if ($state -eq "stopped") {
    Write-Host "Bastion is stopped. Starting instance $targetId..." -ForegroundColor Yellow
    aws ec2 start-instances --instance-ids $targetId --region $region | Out-Null
    Write-Host "Waiting for instance to be running..." -ForegroundColor Gray
    aws ec2 wait instance-running --instance-ids $targetId --region $region
    Write-Host "Waiting 45s for SSM agent to register..." -ForegroundColor Gray
    Start-Sleep -Seconds 45
} elseif ($state -ne "running") {
    Write-Host "Waiting for instance to be running..." -ForegroundColor Gray
    aws ec2 wait instance-running --instance-ids $targetId --region $region
    Start-Sleep -Seconds 25
}

$ping = aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$targetId" --region $region --query "InstanceInformationList[0].PingStatus" --output text 2>$null
if ($ping -ne "Online") {
    Write-Host "Waiting for SSM to become Online (current: $ping). After reboot this can take 2-5 min..." -ForegroundColor Yellow
    $maxWait = 300
    $waited = 0
    while ($waited -lt $maxWait) {
        $ping = aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$targetId" --region $region --query "InstanceInformationList[0].PingStatus" --output text 2>$null
        if ($ping -eq "Online") { break }
        Write-Host "  SSM status: $ping (waiting 10s)..."
        Start-Sleep -Seconds 10
        $waited += 10
    }
    if ($ping -ne "Online") {
        Write-Host "ERROR: SSM did not become Online. Try: (1) In AWS Console EC2, reboot the bastion instance $targetId. (2) Wait 3-5 min. (3) Run this script again. Or check Systems Manager > Fleet Manager for this instance." -ForegroundColor Red
        exit 1
    }
}
Write-Host "Bastion is running and SSM is Online." -ForegroundColor Green

# --- Start tunnel ---
$params = "host=$hostName,portNumber=5432,localPortNumber=$localPort"
Write-Host "Starting tunnel: localhost:$localPort -> ${hostName}:5432 (region $region)"
Write-Host "In another terminal, set DATABASE_URL with IAM token then run your command, e.g.:"
Write-Host "  .\scripts\set_db_url_iam.ps1"
Write-Host "  python scripts/list_aurora_tables.py"
Write-Host "Or use run_dev_backend.ps1 to start the API with Aurora."
Write-Host ""
aws ssm start-session `
  --target $targetId `
  --document-name AWS-StartPortForwardingSessionToRemoteHost `
  --parameters $params `
  --region $region
