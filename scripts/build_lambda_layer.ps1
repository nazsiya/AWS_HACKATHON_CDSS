# Build Lambda layer.zip for CDSS (infrastructure/main.tf).
# Run from repo root. Puts layer.zip in infrastructure/.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LayerDir = Join-Path $RepoRoot "infrastructure\layer"
$PythonDir = Join-Path $LayerDir "python"
$OutZip = Join-Path $RepoRoot "infrastructure\layer.zip"

if (-not (Test-Path $PythonDir)) {
    Write-Host "Creating minimal python layer (pip install into infrastructure/layer/python)."
    New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
    $ReqPath = Join-Path $RepoRoot "infrastructure\layer_requirements.txt"
    if (-not (Test-Path $ReqPath)) {
        @"
boto3>=1.28.0
botocore>=1.31.0
"@ | Set-Content -Path $ReqPath -Encoding utf8
        Write-Host "Created $ReqPath - add more deps as needed."
    }
    Push-Location $LayerDir
    try {
        pip install -t python -r "$ReqPath" --quiet 2>$null
        if ($LASTEXITCODE -ne 0) { pip install -t python boto3 botocore --quiet }
    } finally { Pop-Location }
}

if (-not (Test-Path $PythonDir)) {
    Write-Error "infrastructure/layer/python not found. Create it or add layer_requirements.txt and run again."
}

Write-Host "Building layer.zip from infrastructure/layer/python..."
Remove-Item $OutZip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $PythonDir -DestinationPath $OutZip -Force
$size = (Get-Item $OutZip).Length / 1MB
Write-Host "Done: infrastructure/layer.zip ($([math]::Round($size, 2)) MB)"
