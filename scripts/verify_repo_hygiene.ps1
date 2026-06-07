param(
  [int]$MaxTrackedFileMB = 2
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$errors = @()

$forbiddenWorkingTreePaths = @(
  ".server.pid",
  ".playwright-cli",
  ".playwright-mcp",
  ".tmp-uvicorn.api-smoke.out.log",
  ".tmp-uvicorn.api-smoke.err.log",
  "server.out.log",
  "server.err.log",
  "server.api-smoke.out.log",
  "server.api-smoke.err.log"
)

foreach ($path in $forbiddenWorkingTreePaths) {
  if (Test-Path $path) {
    $errors += "unexpected local artifact exists: $path"
  }
}

$trackedFiles = @(git ls-files)
if ($LASTEXITCODE -ne 0) {
  throw "git ls-files failed with exit code $LASTEXITCODE"
}

$forbiddenTrackedPatterns = @(
  "^\.venv/",
  "^\.model-packages/",
  "^external/.+",
  "^models/.+",
  "^assets/datasets/opa/raw/",
  "^assets/datasets/opa/downloads/",
  "^server/uploads/",
  "^server/generated/",
  "^report/exports/"
)

foreach ($file in $trackedFiles) {
  foreach ($pattern in $forbiddenTrackedPatterns) {
    if ($file -match $pattern) {
      if ($file -eq "external/README.md" -or $file -eq "models/README.md") {
        continue
      }
      $errors += "forbidden tracked artifact: $file"
    }
  }
}

$maxBytes = $MaxTrackedFileMB * 1024 * 1024
$oversized = @()
foreach ($file in $trackedFiles) {
  if (-not (Test-Path $file -PathType Leaf)) {
    continue
  }
  $size = (Get-Item $file).Length
  if ($size -gt $maxBytes) {
    $oversized += "$file ($([math]::Round($size / 1MB, 2)) MB)"
  }
}

if ($oversized.Count -gt 0) {
  $errors += "tracked files exceed ${MaxTrackedFileMB}MB: $($oversized -join '; ')"
}

if ($errors.Count -gt 0) {
  $errors | ForEach-Object { Write-Host $_ }
  throw "Repository hygiene check failed."
}

Write-Host "Repository hygiene check passed."
Write-Host "  tracked_files: $($trackedFiles.Count)"
Write-Host "  max_file_mb:   $MaxTrackedFileMB"
