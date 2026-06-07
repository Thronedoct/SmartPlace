$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$pidPath = ".server.pid"

if (-not (Test-Path $pidPath)) {
  Write-Host "No .server.pid file found. Nothing to stop." -ForegroundColor Yellow
  exit 0
}

$serverPid = (Get-Content $pidPath | Select-Object -First 1).Trim()
if (-not $serverPid) {
  Remove-Item -LiteralPath $pidPath -ErrorAction SilentlyContinue
  Write-Host ".server.pid was empty and has been removed." -ForegroundColor Yellow
  exit 0
}

$process = Get-Process -Id ([int]$serverPid) -ErrorAction SilentlyContinue
if (-not $process) {
  Write-Host "No running process found for pid $serverPid." -ForegroundColor Yellow
  Remove-Item -LiteralPath $pidPath -ErrorAction SilentlyContinue
  exit 0
}

Stop-Process -InputObject $process -ErrorAction Stop
Write-Host "Stopped SmartPlace demo server process $serverPid." -ForegroundColor Green

Remove-Item -LiteralPath $pidPath -ErrorAction SilentlyContinue
