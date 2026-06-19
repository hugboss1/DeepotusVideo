# ============================================================
# DEEPOTUS VIDEO GEN -- Upgrade from v1.2 to v1.3
# ============================================================
# Run from the v1.3 unpacked folder. This script copies only the
# changed files into your existing v1.2 install (preserving venv,
# node_modules, .env, persona JSON enrichment from consolidation pack,
# and your data).
#
# IMPORTANT: This upgrade is independent of the consolidation pack.
# It works on:
#   - a vanilla v1.2 install
#   - a v1.2 install where consolidation pack was already applied
# In the second case, your enriched persona JSON (voice_modes, vocabulary,
# voice_ids) will be preserved.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\upgrade-from-v1.2.ps1 -TargetPath "C:\path\to\old\install"
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
Write-Host " UPGRADE v1.2 -> v1.3 (Batch Multi-Seeds)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $sourceRoot"
Write-Host "Target: $TargetPath"
Write-Host ""

# Files to copy (relative paths). Persona JSON is intentionally NOT in this list
# so consolidation-pack enrichments are preserved. The persona is unchanged in v1.3.
$files = @(
    "backend\app\api\routes.py",
    "backend\app\models\schemas.py",
    "backend\app\services\pipeline.py",
    "backend\app\services\storage.py",
    "frontend\src\App.jsx",
    "frontend\src\api\client.js",
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
    # Backup existing file if present (so user can rollback)
    if (Test-Path $dst) {
        Copy-Item $dst "$dst.bak.$timestamp"
        $backedUp++
    }
    Copy-Item $src $dst -Force
    Write-Host "  [OK] $rel" -ForegroundColor Green
    $copied++
}

Write-Host ""
Write-Host "Copied $copied files. Backed up $backedUp existing files (suffix .bak.$timestamp)." -ForegroundColor Green
Write-Host ""
Write-Host "No new Python deps in v1.3 -- existing venv stays compatible." -ForegroundColor Cyan
Write-Host ""
Write-Host "DB will auto-migrate on next backend start (adds batch_id, batch_index, batch_size columns)." -ForegroundColor Cyan
Write-Host ""
Write-Host "Persona JSON was NOT touched -- if you applied the consolidation pack, your" -ForegroundColor Cyan
Write-Host "enrichment (voice_modes, vocabulary, voice_ids) is preserved." -ForegroundColor Cyan
Write-Host ""
Write-Host "Then launch as usual:" -ForegroundColor Cyan
Write-Host "  cd $TargetPath"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1"
Write-Host ""
Write-Host "(Hard-reload the browser with Ctrl+F5 after launch.)"
Write-Host ""
