param(
  [ValidateSet("mock", "simopa", "simopa-lite", "simopa-worker", "simopa-lite-worker")]
  [string]$Scorer,
  [string]$HostName,
  [int]$Port,
  [string]$Python,
  [string]$ModelPython,
  [string]$Device,
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path $PSScriptRoot "scripts\start_demo_server.ps1"
$forward = @{}
foreach ($key in $PSBoundParameters.Keys) {
  $forward[$key] = $PSBoundParameters[$key]
}

& $scriptPath @forward
$exitCode = Get-Variable -Name LASTEXITCODE -ErrorAction SilentlyContinue
if ($exitCode) {
  exit ([int]$exitCode.Value)
}
exit 0
