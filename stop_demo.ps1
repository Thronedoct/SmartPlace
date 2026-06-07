$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path $PSScriptRoot "scripts\stop_demo_server.ps1"
& $scriptPath
$exitCode = Get-Variable -Name LASTEXITCODE -ErrorAction SilentlyContinue
if ($exitCode) {
  exit ([int]$exitCode.Value)
}
exit 0
