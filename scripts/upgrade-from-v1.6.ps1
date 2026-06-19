# ============================================================
# DEEPOTUS VIDEO GEN -- Upgrade from v1.6 (or v1.5) to v1.7
# ============================================================
# "News-to-Video Edition"
#
# Full self-contained code swap that PRESERVES your data:
#   - backend\.env                       (your API keys)
#   - assets\images\, assets\outputs\    (your media + renders)
#   - assets\news\                       (your news sources + cache)
#   - backend\deepotus.db                (your job history)
#   - backend\app\personas\deepotus.json (your brand bible)
# None of the above are touched. A code-only backup is written to
# <TargetPath>\_codebak_<timestamp>\ before any file is overwritten.
#
# v1.7 ADDS Python deps (feedparser, trafilatura). This script runs
# pip install -r requirements.txt --upgrade into the target venv when
# it exists. No DB migration (auto-migrates; no new columns).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\upgrade-from-v1.6.ps1 -TargetPath "C:\Users\olivi\X-content\deepotus-video-gen"
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
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " UPGRADE -> v1.7 (News-to-Video)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: $TargetPath"
Write-Host ""

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

# ---- 1. Code-only backup (small, fast, rollback-safe) ----
$codeBak = Join-Path $TargetPath "_codebak_$timestamp"
Write-Host "Backing up current code to: $codeBak" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $codeBak | Out-Null
foreach ($rel in @("backend\app", "frontend\src", "scripts", "README.md",
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

# ---- 2. Copy v1.7 code over the target (excludes user data) ----
Write-Host "Applying v1.7 code..." -ForegroundColor Cyan
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

# ---- 3. Preservation check ----
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

# ---- 4. Install new Python deps (feedparser, trafilatura) ----
$venvPy = Join-Path $TargetPath "backend\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    Write-Host "Installing new Python deps into the venv..." -ForegroundColor Cyan
    & $venvPy -m pip install -q -U -r (Join-Path $TargetPath "backend\requirements.txt")
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Python deps up to date." -ForegroundColor Green
    } else {
        Write-Host "  pip returned $LASTEXITCODE -- run it manually:" -ForegroundColor Yellow
        Write-Host "    cd $TargetPath\backend; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt --upgrade"
    }
} else {
    Write-Host "venv not found -- after install run:" -ForegroundColor Yellow
    Write-Host "  cd $TargetPath\backend; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt --upgrade"
}
Write-Host ""

# ---- 5. Next steps ----
Write-Host "NEXT STEPS" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. (If you have not yet) install frontend deps once:"
Write-Host "     cd $TargetPath\frontend; npm install"
Write-Host ""
Write-Host "2. Start the app:"
Write-Host "     powershell -ExecutionPolicy Bypass -File `"$TargetPath\scripts\launch.ps1`""
Write-Host ""
Write-Host "Then hard-reload the browser (Ctrl+F5). Header should show v1.7"
Write-Host "and a News tab. No DB migration needed (auto-migrates)."
Write-Host ""
Write-Host "Rollback: code backup is at $codeBak" -ForegroundColor Cyan
Write-Host ""
