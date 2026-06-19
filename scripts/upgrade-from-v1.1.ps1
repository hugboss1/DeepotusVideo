# ============================================================
# DEEPOTUS VIDEO GEN -- Upgrade from v1.1 to v1.2
# ============================================================
# Run from the v1.2 unpacked folder. This script copies only the
# changed files into your existing v1.1 install (preserving venv,
# node_modules, .env, and your data).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\upgrade-from-v1.1.ps1 -TargetPath "C:\path\to\old\install"
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
    Write-Host "Target path doesn't look like a deepotus install: $TargetPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " UPGRADE v1.1 -> v1.2" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $sourceRoot"
Write-Host "Target: $TargetPath"
Write-Host ""

# Files to copy (relative paths)
$files = @(
    "backend\requirements.txt",
    "backend\app\main.py",
    "backend\app\config.py",
    "backend\app\api\routes.py",
    "backend\app\models\schemas.py",
    "backend\app\personas\deepotus.json",
    "backend\app\services\prompt_engine.py",
    "backend\app\services\fal_service.py",
    "backend\app\services\pipeline.py",
    "backend\app\services\storage.py",
    "frontend\src\App.jsx",
    "frontend\src\api\client.js",
    "frontend\src\components\ImagePicker.jsx",
    "frontend\src\components\TemplateSelector.jsx",
    "frontend\src\components\GenerationForm.jsx",
    "frontend\src\components\JobsList.jsx",
    "frontend\src\components\Toast.jsx",
    "frontend\src\styles\globals.css",
    "scripts\install.ps1",
    "scripts\run.ps1",
    "scripts\setup-paths.ps1",
    "README.md"
)

$copied = 0
foreach ($rel in $files) {
    $src = Join-Path $sourceRoot $rel
    $dst = Join-Path $TargetPath $rel
    if (-not (Test-Path $src)) {
        Write-Host "  [SKIP] source missing: $rel" -ForegroundColor Yellow
        continue
    }
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    }
    Copy-Item $src $dst -Force
    Write-Host "  [OK] $rel" -ForegroundColor Green
    $copied++
}

Write-Host ""
Write-Host "Copied $copied files." -ForegroundColor Green
Write-Host ""
Write-Host "Now install the new Python deps (greenlet pin removed, new versions):" -ForegroundColor Cyan
Write-Host "  cd $TargetPath\backend"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  pip install -r requirements.txt --upgrade"
Write-Host ""
Write-Host "DB will auto-migrate on next backend start (new columns added without data loss)."
Write-Host ""
Write-Host "Then launch as usual:" -ForegroundColor Cyan
Write-Host "  cd $TargetPath"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1"
Write-Host ""
