# Install Python dependencies into the project virtual environment only.
# Run from repo root: .\scripts\install-python-deps.ps1
# Do not run pip install outside this script unless you use .\.venv\Scripts\pip.exe

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot + "\.."
$venvPip = Join-Path $repoRoot ".venv\Scripts\pip.exe"
$requirements = Join-Path $repoRoot "backend\agents\requirements.txt"

if (-not (Test-Path $venvPip)) {
    Write-Error "Virtual environment not found. Create it first: python -m venv .venv"
    exit 1
}

if (-not (Test-Path $requirements)) {
    Write-Error "Requirements file not found: $requirements"
    exit 1
}

Write-Host "Installing into .venv only: $requirements"
& $venvPip install -r $requirements
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done. Use .\.venv\Scripts\python.exe or activate .venv to run Python."
