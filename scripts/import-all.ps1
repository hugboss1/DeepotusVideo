<#
  Deepotus Video Gen - IMPORT ALL-IN-ONE (run on the NEW PC / a lancer sur le NOUVEAU PC).
  One command restores EVERYTHING from the transfer folder:
    1. the app (code + runtime + patches)
    2. all data (generations, calendar, scheduled posts, API keys)
    3. DB path rewrite if the Windows username differs
    4. Desktop + Start Menu shortcut
    5. Claude Code sessions/chats/memory (if claude-home is in the bundle)

  Usage (from inside the transfer folder - Src defaults to the script's folder):
    powershell -ExecutionPolicy Bypass -File .\import-all.ps1
  or double-click IMPORT-TOUT.cmd next to it.
#>
[CmdletBinding()]
param([string]$Src = "")

$ErrorActionPreference = "Stop"
if (-not $Src -or $Src.Trim() -eq "") { $Src = $PSScriptRoot }
$Src = (Resolve-Path $Src).Path

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  DEEPOTUS VIDEO GEN - IMPORT ALL-IN-ONE" -ForegroundColor Cyan
Write-Host "  Source: $Src" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# sanity: the bundle must contain the app + data folders
foreach ($d in @("DeepotusVideoGen", "DeepotusVideoGenData")) {
    if (-not (Test-Path (Join-Path $Src $d))) {
        throw "This does not look like a Deepotus transfer folder (missing $d). Run this script from INSIDE the transfer folder."
    }
}

# free disk space check (bundle size + 1 GB margin)
$bundleBytes = (Get-ChildItem $Src -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
$targetDrive = (Get-Item $env:LOCALAPPDATA).PSDrive
$freeBytes = $targetDrive.Free
if ($freeBytes -lt ($bundleBytes + 1GB)) {
    $needGb = [math]::Round(($bundleBytes + 1GB) / 1GB, 1)
    $freeGb = [math]::Round($freeBytes / 1GB, 1)
    throw "Not enough free space on $($targetDrive.Name): - need ~$needGb GB, only $freeGb GB free."
}

# STEP 1+2+3+4: app + data + DB path rewrite + shortcut
Write-Host "[1/2] App + data + calendar + keys..." -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -NoProfile -File (Join-Path $Src "import-migration.ps1") -Src $Src
if ($LASTEXITCODE -ne 0) { throw "import-migration.ps1 failed (code $LASTEXITCODE)" }

# STEP 5: Claude Code sessions (optional part of the bundle)
$claudeSrc = Join-Path $Src "claude-home"
if (Test-Path $claudeSrc) {
    Write-Host ""
    Write-Host "[2/2] Claude Code sessions/chats/memory..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -NoProfile -File (Join-Path $Src "import-claude-sessions.ps1") -Src $Src
    if ($LASTEXITCODE -ne 0) { Write-Host "  (Claude sessions import reported an error - the app itself is fine)" -ForegroundColor Yellow }
} else {
    Write-Host "[2/2] No claude-home in the bundle - skipping Claude sessions." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  ALL DONE - everything is restored." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "Launch 'Deepotus Video Gen' from the Desktop or Start Menu shortcut."
Write-Host "A fresh installer (DeepotusVideoGen-Setup-*.exe) is also in this folder"
Write-Host "if you ever need a clean reinstall on another machine."
Write-Host ""
Write-Host "IMPORTANT: do NOT run the app on BOTH PCs at the same time" -ForegroundColor Yellow
Write-Host "(scheduled posts could double-publish)." -ForegroundColor Yellow
