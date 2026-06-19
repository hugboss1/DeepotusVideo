# ============================================================
# DEEPOTUS VIDEO GEN -- Upgrade from v1.3.1 to v1.4
# ============================================================
# "Composition Edition": HeyGen integration + Seedance/HeyGen
# composition pipeline (sequential + split-screen).
#
# This patch:
#   - Adds heygen_service.py (HeyGen API client)
#   - Adds composition_service.py (ffmpeg compositing)
#   - Adds HeyGenForm.jsx (new UI panel)
#   - Replaces App.jsx with Provider tabs (Seedance/HeyGen/Composition)
#   - Updates schemas, pipeline, routes, storage with v1.4 fields
#   - Adds HEYGEN_API_KEY to .env.example (you set the real key in .env)
#   - Includes the ASCII-safe fal_service patch from v1.3.1 hotfix
#   - DB auto-migrates with new columns (provider, composition_id, etc.)
#
# Compatible with both:
#   - vanilla v1.3.1 install
#   - v1.3.1 + consolidation pack (voice modes still work via persona JSON)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\upgrade-from-v1.3.1.ps1 -TargetPath "C:\path\to\install"
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
Write-Host " UPGRADE v1.3.1 -> v1.4 (Composition Edition)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $sourceRoot"
Write-Host "Target: $TargetPath"
Write-Host ""

# Files to copy (relative). Persona JSON intentionally NOT in this list
# so consolidation pack enrichments are preserved.
$files = @(
    "backend\.env.example",
    "backend\app\config.py",
    "backend\app\models\schemas.py",
    "backend\app\services\storage.py",
    "backend\app\services\pipeline.py",
    "backend\app\services\fal_service.py",
    "backend\app\services\heygen_service.py",
    "backend\app\services\composition_service.py",
    "backend\app\api\routes.py",
    "frontend\src\App.jsx",
    "frontend\src\api\client.js",
    "frontend\src\components\GenerationForm.jsx",
    "frontend\src\components\JobsList.jsx",
    "frontend\src\components\HeyGenForm.jsx",
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

# Add HEYGEN_API_KEY to .env (not .env.example) if not present
$envFile = Join-Path $TargetPath "backend\.env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -notmatch "HEYGEN_API_KEY=") {
        Write-Host "Appending HEYGEN_API_KEY=  to your existing backend\.env" -ForegroundColor Cyan
        $newBlock = "`n# --- HeyGen (v1.4 avatar + composition) ---`nHEYGEN_API_KEY=`n"
        Add-Content -Path $envFile -Value $newBlock
    } else {
        Write-Host "HEYGEN_API_KEY already present in backend\.env (preserved)." -ForegroundColor Green
    }
} else {
    Write-Host "[WARN] backend\.env not found -- copy .env.example to .env and add your keys." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "No new Python deps in v1.4 (httpx already present). DB auto-migrates." -ForegroundColor Cyan
Write-Host ""
Write-Host "===== NEXT STEPS =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open backend\.env and set your HeyGen key:" -ForegroundColor White
Write-Host "      HEYGEN_API_KEY=sk_V2_hgu_..." -ForegroundColor Yellow
Write-Host "   Get it from: https://app.heygen.com/api"
Write-Host ""
Write-Host "2. Restart the app:" -ForegroundColor White
Write-Host "      cd $TargetPath"
Write-Host "      powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1"
Write-Host ""
Write-Host "3. Hard-reload the browser (Ctrl+F5)."
Write-Host ""
Write-Host "4. In the new Provider tabs at the top, try:"
Write-Host "   - HeyGen: pick an avatar, write a script, generate."
Write-Host "   - Composition: pick Seedance image+template AND HeyGen avatar+script,"
Write-Host "     choose layout (sequential / split-vstack / split-hstack)."
Write-Host ""
