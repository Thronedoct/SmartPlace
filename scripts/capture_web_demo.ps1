param(
  [string]$Url = "http://127.0.0.1:8000/",
  [string]$OutputDir = "report/screenshots/web",
  [string]$Session = "smartplace-demo",
  [int]$TimeoutMs = 120000
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) {
  throw "npx.cmd was not found. Install Node.js/npm before running this script."
}

$resolvedOutputDir = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $resolvedOutputDir | Out-Null

$desktopPath = Join-Path $resolvedOutputDir "web_demo_desktop.png"
$presentationPath = Join-Path $resolvedOutputDir "web_demo_presentation.png"
$mobilePath = Join-Path $resolvedOutputDir "web_demo_mobile.png"

function Convert-ToJsPath([string]$Path) {
  return $Path.Replace("\", "/")
}

$urlJson = $Url | ConvertTo-Json -Compress
$desktopJson = (Convert-ToJsPath $desktopPath) | ConvertTo-Json -Compress
$presentationJson = (Convert-ToJsPath $presentationPath) | ConvertTo-Json -Compress
$mobileJson = (Convert-ToJsPath $mobilePath) | ConvertTo-Json -Compress
$timeoutJson = $TimeoutMs | ConvertTo-Json -Compress

$scriptPath = Join-Path ([System.IO.Path]::GetTempPath()) "smartplace_capture_web_demo.js"
$captureCode = @"
async (page) => {
  const url = $urlJson;
  const desktopPath = $desktopJson;
  const presentationPath = $presentationJson;
  const mobilePath = $mobileJson;
  const timeoutMs = $timeoutJson;
  const issues = [];

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      issues.push(message.type() + ": " + message.text());
    }
  });
  page.on("pageerror", (error) => {
    issues.push("pageerror: " + error.message);
  });

  await page.setViewportSize({ width: 1440, height: 950 });
  await page.goto(url, { waitUntil: "networkidle", timeout: timeoutMs });

  await page.waitForSelector("#demo-case-list button[data-available='true']", { timeout: timeoutMs });
  await page.locator("#demo-case-list button[data-available='true']").first().click();
  await page.waitForFunction(() => {
    return document.querySelector("#stage-title")?.textContent?.length > 0;
  }, null, { timeout: timeoutMs });

  await page.locator(".primary-action").click();
  await page.waitForFunction(() => {
    return document.querySelectorAll("#candidate-list .candidate-item").length >= 3;
  }, null, { timeout: timeoutMs });

  const state = await page.evaluate(() => ({
    title: document.title,
    serviceStatus: document.querySelector("#service-status")?.textContent?.trim() || "",
    modelBadge: document.querySelector("#model-badge")?.textContent?.trim() || "",
    requestId: document.querySelector("#request-meta")?.textContent?.trim() || "",
    confidence: document.querySelector("#confidence-tier")?.textContent?.trim() || "",
    candidateCount: document.querySelectorAll("#candidate-list .candidate-item").length,
    exportJsonDisabled: document.querySelector("#export-json")?.disabled ?? true,
    exportCsvDisabled: document.querySelector("#export-csv")?.disabled ?? true,
  }));

  await page.screenshot({ path: desktopPath, fullPage: false });

  await page.locator("#presentation-toggle").click();
  await page.waitForTimeout(250);
  await page.screenshot({ path: presentationPath, fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  await page.screenshot({ path: mobilePath, fullPage: true });

  if (state.candidateCount < 3) {
    throw new Error("Expected at least 3 candidates, got " + state.candidateCount);
  }
  if (state.exportJsonDisabled || state.exportCsvDisabled) {
    throw new Error("Export buttons stayed disabled after recommendation.");
  }
  if (mobileOverflow) {
    throw new Error("Mobile viewport has horizontal overflow.");
  }
  if (issues.length > 0) {
    throw new Error("Console issues: " + issues.join(" | "));
  }

  return JSON.stringify({
    state,
    screenshots: [desktopPath, presentationPath, mobilePath],
    mobileOverflow,
  }, null, 2);
}
"@

Set-Content -Path $scriptPath -Value $captureCode -Encoding UTF8

Write-Host "Capturing SmartPlace Web demo screenshots" -ForegroundColor Cyan
Write-Host "  url:     $Url"
Write-Host "  output:  $resolvedOutputDir"

& npx.cmd --yes --package "@playwright/cli" playwright-cli --session $Session open "about:blank"
if ($LASTEXITCODE -ne 0) {
  throw "Playwright open failed with exit code $LASTEXITCODE"
}

& npx.cmd --yes --package "@playwright/cli" playwright-cli --session $Session run-code --filename $scriptPath
if ($LASTEXITCODE -ne 0) {
  throw "Playwright capture failed with exit code $LASTEXITCODE"
}

& npx.cmd --yes --package "@playwright/cli" playwright-cli --session $Session close
if ($LASTEXITCODE -ne 0) {
  Write-Host "Playwright close returned exit code $LASTEXITCODE" -ForegroundColor Yellow
}

Write-Host "Captured screenshots:" -ForegroundColor Green
Write-Host "  $desktopPath"
Write-Host "  $presentationPath"
Write-Host "  $mobilePath"
