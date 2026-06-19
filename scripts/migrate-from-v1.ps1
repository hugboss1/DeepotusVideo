# ============================================================
# DEEPOTUS VIDEO GEN -- Migrate from v1.0/v1.1/v1.2/v1.3.x to v1.4
# ============================================================
# Use this when your existing install is too old for the incremental
# upgrade-from-vX.Y.ps1 scripts (typically: v1.0 or v1.1 installs).
#
# What it does:
#   1. Backs up your old install folder (renames to *.bak.<timestamp>)
#   2. Creates a fresh v1.4 folder at the SAME path
#   3. Copies your DATA from the backup to the new install:
#      - backend\.env (preserves your FAL_KEY, ELEVENLABS keys, paths)
#      - assets\images\* (your source images)
#      - assets\outputs\* (your generated videos history)
#      - backend\deepotus.db (job history, will auto-migrate on first run)
#   4. Tells you what to do next (install deps, add HeyGen key, run)
#
# Your old folder is preserved as <oldfolder>.bak.<timestamp> -- nothing
# is destroyed. If something goes wrong, just delete the new folder and
# rename the .bak back to its original name.
#
# Usage (from the unzipped v1.4 folder):
#   powershell -ExecutionPolicy Bypass -File scripts\migrate-from-v1.ps1 -InstallPath "C:\Users\YourName\X-content\deepotus-video-gen"
#
# The InstallPath is the path of your EXISTING (old) install.
# That same path becomes the new v1.4 install.
# ============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$InstallPath
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Split-Path -Parent $scriptDir

if (-not (Test-Path $InstallPath)) {
    Write-Host "Target path does not exist: $InstallPath" -ForegroundColor Red
    Write-Host "If this is a brand-new install (no old version), use install.ps1 instead." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "$InstallPath\backend")) {
    Write-Host "Path doesn't look like a deepotus install (no backend\): $InstallPath" -ForegroundColor Red
    exit 1
}

if ($InstallPath -eq $sourceRoot) {
    Write-Host "InstallPath cannot be the same as the v1.4 source folder you ran this from." -ForegroundColor Red
    Write-Host "Run from the unzipped v1.4 folder, target your OLD install path." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " MIGRATE -> v1.4 (Composition Edition)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "v1.4 source: $sourceRoot"
Write-Host "Old install: $InstallPath"
Write-Host ""

# Detect the old version (best-effort, just for the log)
$detectedVersion = "unknown"
$mainPy = Join-Path $InstallPath "backend\app\main.py"
$routesPy = Join-Path $InstallPath "backend\app\api\routes.py"
if (Test-Path $routesPy) {
    $routesContent = Get-Content $routesPy -Raw
    if ($routesContent -match '"version":\s*"([\d.]+)"') {
        $detectedVersion = $matches[1]
    } elseif ($routesContent -match 'generate/batch') {
        $detectedVersion = "1.3.x (no version marker)"
    } elseif ($routesContent -match 'prompt/build') {
        $detectedVersion = "1.2.x"
    } else {
        $detectedVersion = "1.0 or 1.1"
    }
}
Write-Host "Detected current version: $detectedVersion" -ForegroundColor Yellow
Write-Host ""

# Step 1: Identify what data we need to preserve
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dataItemsToPreserve = @(
    @{ src = "backend\.env"; required = $true; desc = "Your env file (FAL_KEY, paths, etc.)" },
    @{ src = "assets\images"; required = $false; desc = "Your source images" },
    @{ src = "assets\outputs"; required = $false; desc = "Generated videos history" },
    @{ src = "backend\deepotus.db"; required = $false; desc = "Job history database" },
    @{ src = "assets\library"; required = $false; desc = "Asset library (if you applied consolidation pack)" },
    @{ src = "assets\compositions"; required = $false; desc = "Saved compositions (if any)" }
)

Write-Host "Step 1/4: Checking what data to preserve" -ForegroundColor Cyan
$preserveCount = 0
foreach ($item in $dataItemsToPreserve) {
    $fullPath = Join-Path $InstallPath $item.src
    if (Test-Path $fullPath) {
        Write-Host "  [FOUND] $($item.src) -- $($item.desc)" -ForegroundColor Green
        $preserveCount++
    } elseif ($item.required) {
        Write-Host "  [MISSING] $($item.src) -- $($item.desc) (required, will continue without)" -ForegroundColor Yellow
    }
}
Write-Host "Will preserve $preserveCount items." -ForegroundColor Green
Write-Host ""

# Step 2: Rename old install to .bak
$backupPath = "$InstallPath.bak.$timestamp"
Write-Host "Step 2/4: Backing up old install" -ForegroundColor Cyan
Write-Host "  Renaming: $InstallPath" -ForegroundColor Yellow
Write-Host "       to: $backupPath" -ForegroundColor Yellow
Rename-Item -Path $InstallPath -NewName (Split-Path $backupPath -Leaf)
Write-Host "  [OK] Backup created" -ForegroundColor Green
Write-Host ""

# Step 3: Copy v1.4 source to install path
Write-Host "Step 3/4: Installing v1.4 to $InstallPath" -ForegroundColor Cyan
Copy-Item -Path $sourceRoot -Destination $InstallPath -Recurse
# Remove the migrate script itself from the new install (it's no longer needed there)
$migrateInNew = Join-Path $InstallPath "scripts\migrate-from-v1.ps1"
if (Test-Path $migrateInNew) {
    # Keep it for reference, just rename so it's not run again by mistake
    # Actually keep as-is for future use, it's harmless
}
Write-Host "  [OK] v1.4 codebase installed" -ForegroundColor Green
Write-Host ""

# Step 4: Restore data from backup
Write-Host "Step 4/4: Restoring your data" -ForegroundColor Cyan
$restored = 0
foreach ($item in $dataItemsToPreserve) {
    $srcInBackup = Join-Path $backupPath $item.src
    $dstInNew = Join-Path $InstallPath $item.src
    if (-not (Test-Path $srcInBackup)) {
        continue
    }
    # Ensure parent dir exists
    $dstParent = Split-Path -Parent $dstInNew
    if (-not (Test-Path $dstParent)) {
        New-Item -ItemType Directory -Force -Path $dstParent | Out-Null
    }
    # If dst exists (template files copied by v1.4 install), remove first
    if (Test-Path $dstInNew) {
        Remove-Item $dstInNew -Recurse -Force
    }
    Copy-Item -Path $srcInBackup -Destination $dstInNew -Recurse
    Write-Host "  [OK] Restored: $($item.src)" -ForegroundColor Green
    $restored++
}
Write-Host ""
Write-Host "Restored $restored data items from your old install." -ForegroundColor Green
Write-Host ""

# Add HEYGEN_API_KEY placeholder to the restored .env if not present
$envFile = Join-Path $InstallPath "backend\.env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -notmatch "HEYGEN_API_KEY=") {
        Add-Content -Path $envFile -Value "`n# --- HeyGen (v1.4 avatar + composition) ---`nHEYGEN_API_KEY=`n"
        Write-Host "Added HEYGEN_API_KEY= placeholder to your restored backend\.env." -ForegroundColor Cyan
    }
}

Write-Host "==============================================" -ForegroundColor Green
Write-Host " MIGRATION COMPLETE" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your old install is preserved at:" -ForegroundColor White
Write-Host "  $backupPath" -ForegroundColor Yellow
Write-Host "(safe to delete after you've verified v1.4 works)"
Write-Host ""
Write-Host "===== NEXT STEPS =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your v1.0/v1.1 install is too old to reuse its .venv (deps changed in v1.2+)." -ForegroundColor Yellow
Write-Host "We need to recreate the virtual env and reinstall everything fresh." -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Delete the old venv (if it was copied -- it shouldn't have been):" -ForegroundColor White
Write-Host "      Remove-Item $InstallPath\backend\.venv -Recurse -Force -ErrorAction SilentlyContinue"
Write-Host "      Remove-Item $InstallPath\frontend\node_modules -Recurse -Force -ErrorAction SilentlyContinue"
Write-Host ""
Write-Host "2. Install Python deps (creates new .venv):" -ForegroundColor White
Write-Host "      cd $InstallPath\backend"
Write-Host "      py -m venv .venv"
Write-Host "      .\.venv\Scripts\Activate.ps1"
Write-Host "      python -m pip install --upgrade pip"
Write-Host "      pip install -r requirements.txt"
Write-Host ""
Write-Host "3. Install frontend deps:" -ForegroundColor White
Write-Host "      cd ..\frontend"
Write-Host "      npm install"
Write-Host ""
Write-Host "4. Add your HeyGen API key to backend\.env:" -ForegroundColor White
Write-Host "      notepad $InstallPath\backend\.env"
Write-Host "      Find HEYGEN_API_KEY= and paste your key (sk_V2_hgu_...)"
Write-Host ""
Write-Host "5. Launch:" -ForegroundColor White
Write-Host "      cd $InstallPath"
Write-Host "      powershell -ExecutionPolicy Bypass -File .\scripts\run.ps1"
Write-Host ""
Write-Host "6. Hard-reload the browser (Ctrl+F5)."
Write-Host ""
Write-Host "If anything goes wrong, you can roll back by:" -ForegroundColor Yellow
Write-Host "  Remove-Item $InstallPath -Recurse -Force"
Write-Host "  Rename-Item $backupPath $InstallPath"
Write-Host ""
