# ============================================================
# DEEPOTUS VIDEO GEN -- Upgrade from v1.7.2 to v1.8.0
# ============================================================
# "Reef Edition" -- major UI refonte (Sidebar shell + Node Studio +
# Scheduler + Persona creator + Splash/onboarding + token system).
#
# PRESERVES your data:
#   - backend\.env                       (your API keys)
#   - assets\images\, assets\outputs\    (your media + renders)
#   - assets\news\                       (your news sources + cache)
#   - backend\deepotus.db                (your job history)
#   - backend\app\personas\deepotus.json (your brand bible)
# Code-only backup written to <TargetPath>\_codebak_<timestamp>\.
#
# No new Python deps. No new DB columns. No backend behaviour change
# beyond the version string bump (1.7.2 -> 1.8.0).
#
# IMPORTANT: rebuild the frontend after upgrade, or use the bundled
# pre-built dist. The upgrade copies the src/ tree; if you serve via
# vite dev, hot reload picks up the new shell automatically.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\upgrade-from-v1.7.2.ps1 -TargetPath "C:\Users\olivi\X-content\deepotus-video-gen"
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetPath
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Split-Path -Parent $scriptDir

if (-not (Test-Path $TargetPath)) {
    Write-Host "Target path not found: $TargetPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "$TargetPath\backend\app")) {
    Write-Host "Target does not look like a deepotus install: $TargetPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Red
Write-Host " UPGRADE -> v1.8.0 (Reef Edition)" -ForegroundColor Red
Write-Host "==============================================" -ForegroundColor Red
Write-Host ""
Write-Host "Target: $TargetPath"
Write-Host ""

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$codeBak = Join-Path $TargetPath "_codebak_$timestamp"
Write-Host "Backing up current code to: $codeBak" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $codeBak | Out-Null
foreach ($rel in @("backend\app", "frontend\src", "frontend\index.html",
                    "frontend\public", "scripts", "README.md",
                    "backend\requirements.txt", "frontend\package.json")) {
    $src = Join-Path $TargetPath $rel
    if (Test-Path $src) {
        $dst = Join-Path $codeBak $rel
        $dstParent = Split-Path -Parent $dst
        if (-not (Test-Path $dstParent)) {
            New-Item -ItemType Directory -Force -Path $dstParent | Out-Null
        }
        if ((Get-Item $src).PSIsContainer) {
            robocopy $src $dst /E /NFL /NDL /NJH /NJS | Out-Null
        } else {
            Copy-Item $src $dst -Force
        }
    }
}
Write-Host "  Backup complete." -ForegroundColor Green
Write-Host ""

Write-Host "Applying v1.8.0 code..." -ForegroundColor Cyan
$assetsSrc = Join-Path $sourceRoot "assets"
robocopy $sourceRoot $TargetPath /E /NFL /NDL /NJH /NJS `
    /XD "node_modules" ".venv" "dist" "__pycache__" ".git" "$assetsSrc" `
        "$codeBak" `
    /XF "*.db" ".env" "deepotus.json" `
    | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) {
    Write-Host "robocopy reported errors (exit $rc). Restore from: $codeBak" -ForegroundColor Red
    exit 1
}
Write-Host "  Code applied (robocopy exit $rc -- OK)." -ForegroundColor Green
Write-Host ""

Write-Host "Preserved (untouched):" -ForegroundColor Cyan
foreach ($p in @("backend\.env", "assets\images", "assets\outputs",
                 "assets\news", "backend\deepotus.db",
                 "backend\app\personas\deepotus.json")) {
    $full = Join-Path $TargetPath $p
    if (Test-Path $full) {
        Write-Host "  [KEPT] $p" -ForegroundColor Green
    } else {
        Write-Host "  [n/a]  $p (not present in this install)" -ForegroundColor Yellow
    }
}
Write-Host ""

Write-Host "Rebuild the frontend (one time)..." -ForegroundColor Cyan
$nodeMods = Join-Path $TargetPath "frontend\node_modules"
if (Test-Path $nodeMods) {
    Push-Location (Join-Path $TargetPath "frontend")
    try {
        & npm run build 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Frontend built." -ForegroundColor Green
        } else {
            Write-Host "  Build returned $LASTEXITCODE -- run manually." -ForegroundColor Yellow
        }
    } finally { Pop-Location }
} else {
    Write-Host "  frontend\node_modules absent -- run:" -ForegroundColor Yellow
    Write-Host "    cd $TargetPath\frontend; npm install; npm run build"
}
Write-Host ""

Write-Host "NEXT STEPS" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Start the app:"
Write-Host "     powershell -ExecutionPolicy Bypass -File `"$TargetPath\scripts\launch.ps1`""
Write-Host ""
Write-Host "Then hard-reload the browser (Ctrl+F5). The new Reef shell"
Write-Host "should appear: red Deepotus logo in the sidebar, Studio (node"
Write-Host "editor) on launch, Scheduler / Quick / News / Templates /"
Write-Host "Library / Settings in the nav. Splash + onboarding fire on"
Write-Host "first visit; replay via the topbar octopus icon or Cmd-K."
Write-Host ""
Write-Host "Rollback: code backup is at $codeBak" -ForegroundColor Cyan
Write-Host ""
