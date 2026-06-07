param(
  [ValidateSet("mock", "simopa", "simopa-lite", "simopa-worker", "simopa-lite-worker")]
  [string]$Scorer = "simopa-worker",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8000,
  [string]$Python = ".\.venv\Scripts\python.exe",
  [string]$ModelPython = $env:SMARTPLACE_MODEL_PYTHON,
  [string]$Device = "auto",
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not (Test-Path $Python)) {
  Write-Host "Local virtualenv Python not found at $Python; falling back to python on PATH." -ForegroundColor Yellow
  $Python = "python"
}

$env:SMARTPLACE_SCORER = $Scorer
$env:SMARTPLACE_SIMOPA_DEVICE = $Device

if ($Scorer.StartsWith("simopa")) {
  if ($ModelPython) {
    $env:SMARTPLACE_MODEL_PYTHON = $ModelPython
  } else {
    Write-Host "SMARTPLACE_MODEL_PYTHON is not set." -ForegroundColor Yellow
    Write-Host "Pass -ModelPython <path-to-model-python.exe> if SimOPA model loading fails." -ForegroundColor Yellow
  }
}

$uvicornArgs = @("-m", "uvicorn", "server.app:app", "--host", $HostName, "--port", "$Port")

Write-Host "Starting SmartPlace demo server" -ForegroundColor Cyan
Write-Host "  scorer: $Scorer"
Write-Host "  host:   http://${HostName}:$Port/"
if ($env:SMARTPLACE_MODEL_PYTHON) {
  Write-Host "  model:  $env:SMARTPLACE_MODEL_PYTHON"
}

if ($Foreground) {
  & $Python @uvicornArgs
  exit $LASTEXITCODE
}

$process = Start-Process -FilePath $Python -ArgumentList $uvicornArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
Set-Content -Path ".server.pid" -Value $process.Id
Write-Host "  pid:    $($process.Id)"

Start-Sleep -Seconds 3
$healthUrl = "http://${HostName}:$Port/api/health"
try {
  $response = Invoke-WebRequest -UseBasicParsing $healthUrl -TimeoutSec 10
  Write-Host "Server started. Health status: $($response.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "Server process started, but health check did not respond yet." -ForegroundColor Yellow
  Write-Host $_.Exception.Message
}

Write-Host "Open http://${HostName}:$Port/"
Write-Host "Stop with .\stop_demo.ps1"
