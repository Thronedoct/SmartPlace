param(
  [string]$OutputRoot = "report/exports",
  [string]$PackageName = "smartplace_project_no_dataset",
  [switch]$IncludeRawDataset,
  [int]$MaxPackageSizeMB = 1024,
  [switch]$ListOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$repoRootForUri = $repoRoot
if (-not $repoRootForUri.EndsWith("\")) {
  $repoRootForUri = "$repoRootForUri\"
}
$repoRootUri = [System.Uri]::new($repoRootForUri)

$allowedOutputRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "report\exports")).TrimEnd("\", "/")
$outputRootPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputRoot)).TrimEnd("\", "/")
$zipPath = Join-Path $outputRootPath "$PackageName.zip"

if (
  $outputRootPath -ne $allowedOutputRoot -and
  -not $outputRootPath.StartsWith("$allowedOutputRoot\", [System.StringComparison]::OrdinalIgnoreCase)
) {
  throw "OutputRoot must stay inside report/exports."
}

Write-Host "Verifying core handoff assets before project export" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_handoff_assets.ps1
if ($LASTEXITCODE -ne 0) {
  throw "Handoff asset verification failed with exit code $LASTEXITCODE"
}

New-Item -ItemType Directory -Force -Path $outputRootPath | Out-Null

$excludedDirRelatives = @(
  ".git",
  ".venv",
  "venv",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  ".playwright-mcp",
  ".playwright-cli",
  ".idea",
  ".vscode",
  ".gradle",
  "build",
  "report\exports",
  "server\uploads",
  "server\generated",
  "assets\tmp",
  "assets\datasets\opa\downloads"
)

if (-not $IncludeRawDataset) {
  $excludedDirRelatives += "assets\datasets\opa\raw"
}

$excludedDirPaths = $excludedDirRelatives |
  ForEach-Object { [System.IO.Path]::GetFullPath((Join-Path $repoRoot $_)).TrimEnd("\", "/") }

$excludedDirNames = @(
  ".git",
  ".venv",
  "venv",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  ".playwright-mcp",
  ".playwright-cli",
  ".idea",
  ".vscode",
  ".gradle",
  "build"
)

$excludedFilePatterns = @(
  "*.pyc",
  "*.pyo",
  ".server.pid",
  "server.out.log",
  "server.err.log",
  "server.api-smoke.out.log",
  "server.api-smoke.err.log",
  ".DS_Store",
  "Thumbs.db"
)

function Test-ExcludedDir {
  param([Parameter(Mandatory = $true)][string]$Path)
  $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd("\", "/")
  $dirName = Split-Path $fullPath -Leaf
  foreach ($excludedName in $excludedDirNames) {
    if ($dirName.Equals($excludedName, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }
  foreach ($excluded in $excludedDirPaths) {
    if ($fullPath.Equals($excluded, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }
  return $false
}

function Test-ExcludedFile {
  param([Parameter(Mandatory = $true)][System.IO.FileInfo]$File)
  foreach ($pattern in $excludedFilePatterns) {
    if ($File.Name -like $pattern) {
      return $true
    }
  }
  return $false
}

function Convert-ToZipPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  $fileUri = [System.Uri]::new($Path)
  $relative = [System.Uri]::UnescapeDataString($repoRootUri.MakeRelativeUri($fileUri).ToString())
  return ($relative -replace "\\", "/")
}

Write-Host "Scanning package contents" -ForegroundColor Cyan
$files = New-Object System.Collections.Generic.List[System.IO.FileInfo]
$stack = New-Object System.Collections.Generic.Stack[System.IO.DirectoryInfo]
$stack.Push([System.IO.DirectoryInfo]::new($repoRoot))

while ($stack.Count -gt 0) {
  $dir = $stack.Pop()
  foreach ($item in $dir.EnumerateFileSystemInfos()) {
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
      continue
    }

    if ($item -is [System.IO.DirectoryInfo]) {
      if (-not (Test-ExcludedDir -Path $item.FullName)) {
        $stack.Push($item)
      }
      continue
    }

    $file = [System.IO.FileInfo]$item
    if (-not (Test-ExcludedFile -File $file)) {
      $files.Add($file)
    }
  }
}

$badEntries = @()
foreach ($file in $files) {
  $zipName = Convert-ToZipPath -Path $file.FullName
  if ($zipName.StartsWith("report/exports/", [System.StringComparison]::OrdinalIgnoreCase)) {
    $badEntries += $zipName
  }
  if (-not $IncludeRawDataset -and $zipName.StartsWith("assets/datasets/opa/raw/", [System.StringComparison]::OrdinalIgnoreCase)) {
    $badEntries += $zipName
  }
}

if ($badEntries.Count -gt 0) {
  $badEntries | Select-Object -First 20 | ForEach-Object { Write-Host "unexpected entry: $_" }
  throw "Package preflight failed: excluded paths would be included."
}

$totalBytes = ($files | Measure-Object Length -Sum).Sum
$totalMB = [math]::Round($totalBytes / 1MB, 1)
if ($totalMB -gt $MaxPackageSizeMB) {
  throw "Package preflight failed: estimated input size ${totalMB}MB exceeds MaxPackageSizeMB=${MaxPackageSizeMB}. Increase the limit only if this is expected."
}

Write-Host "Package preflight passed." -ForegroundColor Green
Write-Host "  files:              $($files.Count)"
Write-Host "  estimated_input_mb: $totalMB"
Write-Host "  include_raw_data:   $([bool]$IncludeRawDataset)"
Write-Host "  output_zip:         $zipPath"

if ($ListOnly) {
  Write-Host "ListOnly set; no zip written."
  return
}

if (Test-Path $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}

$zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
  foreach ($file in $files) {
    $entryName = Convert-ToZipPath -Path $file.FullName
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
      $zip,
      $file.FullName,
      $entryName,
      [System.IO.Compression.CompressionLevel]::Optimal
    ) | Out-Null
  }

  $manifest = @(
    "SmartPlace project handoff package",
    "Generated at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "",
    "Start here:",
    "  README.md",
    "  HANDOFF_FULL_PROJECT.md",
    "  report/README.md",
    "",
    "Includes source, docs, report evidence, model weights, external reference source, and local model package cache.",
    "Includes OPA raw dataset: $([bool]$IncludeRawDataset)",
    "Excludes .git, virtual environments, caches, report/exports, dataset download archives, uploads, and generated temp files."
  ) -join "`r`n"
  $entry = $zip.CreateEntry("PROJECT_PACKAGE_MANIFEST.txt", [System.IO.Compression.CompressionLevel]::Optimal)
  $writer = [System.IO.StreamWriter]::new($entry.Open(), [System.Text.UTF8Encoding]::new($false))
  try {
    $writer.Write($manifest)
  } finally {
    $writer.Dispose()
  }
} finally {
  $zip.Dispose()
}

$zipInfo = Get-Item $zipPath
Write-Host "Project package exported." -ForegroundColor Green
Write-Host ("  zip_size_mb: {0:N1}" -f ($zipInfo.Length / 1MB))
Write-Host "  zip: $zipPath"
