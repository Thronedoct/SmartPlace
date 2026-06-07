param(
  [switch]$SkipEvidenceSummary,
  [switch]$SkipStaleScan
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$pythonFiles = @(
  "server/app.py",
  "server/mock_stdlib.py",
  "server/recommender.py",
  "server/scorer.py",
  "server/test_recommender.py"
)

$webFiles = @(
  "web/app.js",
  "web/modules/api.js",
  "web/modules/confidence.js",
  "web/modules/download.js",
  "web/modules/image-preview.js",
  "web/modules/overlay.js"
)

function Invoke-VerifyStep {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][scriptblock]$Command
  )

  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
}

Invoke-VerifyStep "Backend unit tests" {
  python -m unittest server.test_recommender
}

Invoke-VerifyStep "Python compile check" {
  python -m py_compile @pythonFiles
}

Invoke-VerifyStep "Web JavaScript syntax check" {
  foreach ($file in $webFiles) {
    node --check $file
    if ($LASTEXITCODE -ne 0) {
      throw "JavaScript syntax check failed for $file with exit code $LASTEXITCODE"
    }
  }
}

Invoke-VerifyStep "PowerShell script syntax check" {
  $scriptErrors = @()
  foreach ($file in Get-ChildItem -Path "scripts" -Filter "*.ps1") {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    foreach ($errorItem in $parseErrors) {
      $scriptErrors += "$($file.Name): $($errorItem.Message)"
    }
  }

  if ($scriptErrors.Count -gt 0) {
    $scriptErrors | ForEach-Object { Write-Host $_ }
    throw "PowerShell script syntax check failed."
  }
}

if (-not $SkipEvidenceSummary) {
  Invoke-VerifyStep "Evidence summary refresh" {
    python experiments/opa_baseline/run_evidence_summary.py
  }
}

if (-not $SkipStaleScan) {
  $rg = Get-Command rg -ErrorAction SilentlyContinue
  if ($rg) {
    Write-Host ""
    Write-Host "==> Stale wording scan" -ForegroundColor Cyan
    $stalePatterns = @(
      "phase-0",
      "Phase 0",
      "PHASE0",
      "Planned experiments",
      "opa_finetune",
      "opa_rgb_mask",
      "NEXT_ROUTE.md",
      "PHASE0_STATUS.md",
      "HIGH_SCORE_ROUTE.md",
      "WORKFLOW.md"
    )
    $patterns = $stalePatterns -join "|"
    $scanTargets = @("README.md", "docs", "experiments", "server", "web", "report", "OPAAndroidDemoSimp") |
      Where-Object { Test-Path $_ }
    if (-not $scanTargets) {
      throw "Stale wording scan has no existing targets."
    }
    $matches = & rg -n $patterns @scanTargets -S
    if ($LASTEXITCODE -eq 0) {
      $matches | ForEach-Object { Write-Host $_ }
      throw "Stale wording scan found outdated project wording."
    }
    if ($LASTEXITCODE -gt 1) {
      throw "Stale wording scan failed with exit code $LASTEXITCODE"
    }
    Write-Host "No stale wording found."
  } else {
    Write-Host ""
    Write-Host "==> Stale wording scan skipped: rg is not available" -ForegroundColor Yellow
  }
}

Invoke-VerifyStep "Git whitespace check" {
  git diff --check
}

Write-Host ""
Write-Host "Core verification passed." -ForegroundColor Green
