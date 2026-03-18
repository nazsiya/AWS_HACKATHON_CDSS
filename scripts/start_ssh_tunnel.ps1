# Start SSH port-forward from local port 5433 to Aurora (per reference/docs/infrastructure/bastion-setup.md).
# Requires: Terraform applied with bastion_ssh_public_key and bastion_allowed_cidr set; private key for that key pair.
# Usage: .\scripts\start_ssh_tunnel.ps1
# Or: .\scripts\start_ssh_tunnel.ps1 -KeyPath "C:\Users\You\.ssh\id_rsa"
# Then in another terminal: $env:DATABASE_URL="postgresql://cdssadmin:PASSWORD@localhost:5433/cdssdb"; .\scripts\run_migrations_and_seed.ps1

param(
    [string]$KeyPath = ""
)

$ErrorActionPreference = "Stop"
$infraDir = Join-Path $PSScriptRoot "..\infrastructure"
$localPort = "5433"
$remotePort = "5432"
$user = "ec2-user"

# Resolve key: param > env SSH_KEY_PATH > repo .ssh/bastion_id_rsa > default ~/.ssh/id_rsa
if ($KeyPath) { $keyFile = $KeyPath }
elseif ($env:SSH_KEY_PATH) { $keyFile = $env:SSH_KEY_PATH }
else {
    $repoRoot = Join-Path $PSScriptRoot ".."
    $repoKey = Join-Path (Join-Path $repoRoot ".ssh") "bastion_id_rsa"
    if (Test-Path $repoKey) { $keyFile = $repoKey }
    else {
        $homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
        $keyFile = Join-Path (Join-Path $homeDir ".ssh") "id_rsa"
    }
}
if (-not (Test-Path $keyFile)) {
    Write-Host "Private key not found: $keyFile" -ForegroundColor Red
    Write-Host "Set -KeyPath or SSH_KEY_PATH to your key that matches bastion_ssh_public_key used in Terraform." -ForegroundColor Yellow
    exit 1
}

Push-Location $infraDir
try {
    $bastionIp = terraform output -raw bastion_public_ip 2>$null
    $auroraHost = terraform output -raw aurora_cluster_endpoint 2>$null
} finally { Pop-Location }

if (-not $bastionIp -or -not $auroraHost) {
    Write-Host "Run 'terraform output bastion_public_ip' and 'terraform output aurora_cluster_endpoint' from infrastructure/ - one is missing." -ForegroundColor Red
    exit 1
}

Write-Host "SSH tunnel: localhost:$localPort -> $auroraHost`:${remotePort} via $user@${bastionIp}" -ForegroundColor Cyan
Write-Host "Leave this terminal open. In another terminal set DATABASE_URL=postgresql://cdssadmin:PASSWORD@localhost:$localPort/cdssdb and run migrations/seed." -ForegroundColor Gray
Write-Host ""

# -N = no shell; -L = local port forward; -o StrictHostKeyChecking=accept-new = accept new host key once
ssh -o StrictHostKeyChecking=accept-new -i $keyFile -N -L "${localPort}:${auroraHost}:${remotePort}" "${user}@${bastionIp}"
