param(
  [string]$OutputRoot = "report/exports",
  [string]$PackageName = "smartplace_handoff",
  [switch]$RequireVideos,
  [switch]$NoZip
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$allowedOutputRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "report\exports")).TrimEnd("\", "/")
$outputRootPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputRoot)).TrimEnd("\", "/")
$packagePath = Join-Path $outputRootPath $PackageName
$zipPath = Join-Path $outputRootPath "$PackageName.zip"

if (
  $outputRootPath -ne $allowedOutputRoot -and
  -not $outputRootPath.StartsWith("$allowedOutputRoot\", [System.StringComparison]::OrdinalIgnoreCase)
) {
  throw "OutputRoot must stay inside report/exports."
}

Write-Host "Verifying handoff assets before export" -ForegroundColor Cyan
$verifyArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\scripts\verify_handoff_assets.ps1")
if ($RequireVideos) {
  $verifyArgs += "-RequireVideos"
}
& powershell @verifyArgs
if ($LASTEXITCODE -ne 0) {
  throw "Handoff asset verification failed with exit code $LASTEXITCODE"
}

if (Test-Path $packagePath) {
  Remove-Item -LiteralPath $packagePath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $packagePath | Out-Null

$copyItems = @(
  "README.md",
  "HANDOFF_FULL_PROJECT.md",
  "requirements.txt",
  "requirements-model.txt",
  "start_demo.ps1",
  "stop_demo.ps1",
  "assets/demo_cases",
  "docs",
  "report/README.md",
  "report/tables",
  "report/logs",
  "report/screenshots",
  "scripts/start_demo_server.ps1",
  "scripts/stop_demo_server.ps1",
  "scripts/capture_web_demo.ps1",
  "scripts/export_handoff_package.ps1",
  "scripts/export_full_project_package.ps1",
  "scripts/verify_core.ps1",
  "scripts/verify_handoff_assets.ps1",
  "scripts/verify_repo_hygiene.ps1"
)

foreach ($item in $copyItems) {
  if (-not (Test-Path $item)) {
    throw "Export source does not exist: $item"
  }

  $target = Join-Path $packagePath $item
  $targetParent = Split-Path $target -Parent
  New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
  Copy-Item -LiteralPath $item -Destination $target -Recurse -Force
}

if (Test-Path "report/videos") {
  $videosTarget = Join-Path $packagePath "report/videos"
  New-Item -ItemType Directory -Force -Path (Split-Path $videosTarget -Parent) | Out-Null
  Copy-Item -LiteralPath "report/videos" -Destination $videosTarget -Recurse -Force
}

$manifestPath = Join-Path $packagePath "HANDOFF_PACKAGE.txt"
$manifest = @(
  "SmartPlace handoff package",
  "Generated at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
  "",
  "Use report/README.md as the teammate-facing evidence index.",
  "Use docs/ROADMAP.md as the project direction and status source.",
  "Use report/screenshots/web/ for final Web UI screenshots.",
  "Use report/tables/ and report/logs/ for report/PPT evidence.",
  "",
  "This package intentionally excludes raw datasets, model weights, external source trees, virtualenvs, and local dependency caches."
)
Set-Content -Path $manifestPath -Value $manifest -Encoding UTF8

if (-not $NoZip) {
  if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
  }
  Compress-Archive -Path (Join-Path $packagePath "*") -DestinationPath $zipPath -Force
}

Write-Host "Handoff package exported." -ForegroundColor Green
Write-Host "  folder: $packagePath"
if (-not $NoZip) {
  Write-Host "  zip:    $zipPath"
}
