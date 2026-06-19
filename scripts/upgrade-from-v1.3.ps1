# ============================================================
# DEEPOTUS VIDEO GEN -- Upgrade from v1.3 to v1.3.1
# ============================================================
# Voice Mode Awareness patch. Small, surgical -- no new deps,
# no breaking changes, persona JSON untouched.
#
# This patch:
#   - Adds VoiceMode enum + voice_mode field to schemas
#   - Adds voice_mode column to DB (auto-migrated)
#   - Adds voice mode style hints injection in prompt builder
#   - Adds avoid_completely vocab filter on captions
#   - Reads voice_id + voice_settings from persona JSON (if enriched)
#   - Adds Voice Mode dropdown in Configuration panel
#   - Shows voice_mode in queue meta grid
#
# Compatible with both:
#   - vanilla v1.3 install (voice modes silently no-op until persona enriched)
#   - v1.3 + consolidation pack applied (voice modes fully active)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\upgrade-from-v1.3.ps1 -TargetPath "C:\path\to\install"
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
Write-Host " UPGRADE v1.3 -> v1.3.1 (Voice Mode Awareness)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $sourceRoot"
Write-Host "Target: $TargetPath"
Write-Host ""

# Files changed in v1.3.1 ONLY (persona JSON intentionally NOT in this list)
$files = @(
    "backend\app\models\schemas.py",
    "backend\app\services\storage.py",
    "backend\app\services\prompt_engine.py",
    "backend\app\services\elevenlabs_service.py",
    "backend\app\services\pipeline.py",
    "backend\app\api\routes.py",
    "frontend\src\App.jsx",
    "frontend\src\components\GenerationForm.jsx",
    "frontend\src\components\JobsList.jsx",
    "README.md"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$copied = 0
$backedUp = 0
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
    if (Test-Path $dst) {
        Copy-Item $dst "$dst.bak.$timestamp"
        $backedUp++
    }
    Copy-Item $src $dst -Force
    Write-Host "  [OK] $rel" -ForegroundColor Green
    $copied++
}

Write-Host ""
Write-Host "Copied $copied files. Backed up $backedUp existing files (.bak.$timestamp)." -ForegroundColor Green
Write-Host ""
Write-Host "DB will auto-migrate on next backend start (voice_mode column added)." -ForegroundColor Cyan
Write-Host ""
Write-Host "Persona JSON untouched. Voice modes activate automatically if you've"
Write-Host "applied the consolidation pack (voice_modes block in deepotus.json)."
Write-Host ""
Write-Host "Then launch as usual:" -ForegroundColor Cyan
Write-Host "  cd $TargetPath"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1"
Write-Host ""
Write-Host "(Hard-reload the browser with Ctrl+F5 after launch.)"
Write-Host ""
