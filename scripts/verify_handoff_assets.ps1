param(
  [switch]$RequireVideos
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$requiredFiles = @(
  "report/README.md",
  "report/tables/model_change_summary.csv",
  "report/tables/inference_runtime.csv",
  "report/tables/candidate_ranking_v2_100.csv",
  "report/tables/opa_100_case_summary.csv",
  "report/tables/rgb_vs_mask_comparison.csv",
  "report/tables/score_calibration_v1.csv",
  "report/tables/occlusion_explainability_v1.csv",
  "report/tables/robustness_ablation.csv",
  "report/tables/lite_mode_comparison.csv",
  "report/tables/persistent_worker_comparison.csv",
  "report/tables/lightopa_model_comparison.csv",
  "report/logs/api_simopa_worker_smoke.txt",
  "report/logs/candidate_ranking_v2_100.txt",
  "report/logs/persistent_worker_comparison.txt",
  "report/logs/evidence_summary.txt",
  "report/logs/lightopa_residual_training.txt",
  "report/screenshots/web/web_demo_desktop.png",
  "report/screenshots/web/web_demo_presentation.png",
  "report/screenshots/web/web_demo_mobile.png",
  "start_demo.ps1",
  "stop_demo.ps1",
  "scripts/start_demo_server.ps1",
  "scripts/stop_demo_server.ps1",
  "scripts/capture_web_demo.ps1",
  "scripts/export_handoff_package.ps1",
  "scripts/verify_core.ps1",
  "scripts/verify_handoff_assets.ps1",
  "scripts/verify_repo_hygiene.ps1"
)

$requiredDirs = @(
  "report/screenshots/cases",
  "report/screenshots/explainability",
  "report/screenshots/web",
  "report/videos"
)

$missing = @()

foreach ($file in $requiredFiles) {
  if (-not (Test-Path $file -PathType Leaf)) {
    $missing += "missing file: $file"
  }
}

foreach ($dir in $requiredDirs) {
  if (-not (Test-Path $dir -PathType Container)) {
    $missing += "missing directory: $dir"
  }
}

$casePanels = @(Get-ChildItem -Path "report/screenshots/cases" -Filter "*.png" -ErrorAction SilentlyContinue)
if ($casePanels.Count -lt 5) {
  $missing += "expected at least 5 case panel PNGs; found $($casePanels.Count)"
}

$heatmaps = @(Get-ChildItem -Path "report/screenshots/explainability" -Filter "*.png" -ErrorAction SilentlyContinue)
if ($heatmaps.Count -lt 5) {
  $missing += "expected at least 5 explainability PNGs; found $($heatmaps.Count)"
}

if ($RequireVideos) {
  $videos = @(Get-ChildItem -Path "report/videos" -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne ".gitkeep" })
  if ($videos.Count -eq 0) {
    $missing += "report/videos has no recording files"
  }
}

if ($missing.Count -gt 0) {
  $missing | ForEach-Object { Write-Host $_ }
  throw "Handoff artifact check failed."
}

Write-Host "Handoff artifact check passed."
Write-Host "  required_files: $($requiredFiles.Count)"
Write-Host "  case_panels:    $($casePanels.Count)"
Write-Host "  heatmaps:       $($heatmaps.Count)"
if ($RequireVideos) {
  Write-Host "  videos:         $($videos.Count)"
}
