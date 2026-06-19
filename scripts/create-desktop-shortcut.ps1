# ============================================================
#  DEEPOTUS VIDEO GEN -- Create Desktop Shortcut (with brand icon)
#  Generates a multi-resolution .ico from the Deepotus PNG logo
#  via Pillow (already in the backend venv), then places a
#  "Deepotus Video Gen" shortcut on the Desktop pointing at
#  scripts\launch.ps1.
# ============================================================
param(
    [string]$AppDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [string]$LogoPng = $null
)
$ErrorActionPreference = "Stop"

$launch = Join-Path $AppDir "scripts\launch.ps1"
if (-not (Test-Path $launch)) {
    Write-Host "launch.ps1 not found at: $launch" -ForegroundColor Red
    exit 1
}

# Resolve the real Desktop (handles redirected / special folders)
try {
    $desktop = (New-Object -ComObject Shell.Application).NameSpace('shell:Desktop').Self.Path
} catch {
    $desktop = [Environment]::GetFolderPath('Desktop')
}
if ([string]::IsNullOrWhiteSpace($desktop)) {
    $desktop = Join-Path $env:USERPROFILE "Desktop"
}

# ---- 1. Locate the PNG logo (default: frontend\public\deepotus-logo.png) ----
if (-not $LogoPng -or -not (Test-Path $LogoPng)) {
    $candidates = @(
        (Join-Path $AppDir "frontend\public\deepotus-logo.png"),
        (Join-Path $AppDir "frontend\dist\deepotus-logo.png"),
        (Join-Path $AppDir "assets\deepotus-logo.png")
    )
    $LogoPng = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

# ---- 2. Generate multi-resolution .ico via Pillow ----
$iconPath = Join-Path $AppDir "assets\deepotus-logo.ico"
$assetsDir = Split-Path -Parent $iconPath
if (-not (Test-Path $assetsDir)) { New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null }

$regen = $true
if ((Test-Path $iconPath) -and $LogoPng -and (Test-Path $LogoPng)) {
    # Only regenerate when the source PNG is newer than the .ico.
    $regen = (Get-Item $LogoPng).LastWriteTime -gt (Get-Item $iconPath).LastWriteTime
}

if ($regen -and $LogoPng -and (Test-Path $LogoPng)) {
    $venvPy = Join-Path $AppDir "backend\.venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        Write-Host "venv python not found at $venvPy -- falling back to PowerShell icon." -ForegroundColor Yellow
    } else {
        Write-Host "Generating brand icon from $LogoPng ..." -ForegroundColor Cyan
        $pyScript = @"
from PIL import Image
import sys
src, dst = sys.argv[1], sys.argv[2]
img = Image.open(src).convert("RGBA")
# Square crop on the longest side, centred, so non-square PNGs (the
# deepotus logo is roughly square but with transparent margins) become
# crisp at every Windows icon size.
w, h = img.size
side = min(w, h)
left = (w - side) // 2
top  = (h - side) // 2
img = img.crop((left, top, left + side, top + side))
sizes = [(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(96,96),(128,128),(256,256)]
img.save(dst, format="ICO", sizes=sizes)
print("ico written:", dst)
"@
        $tmpPy = Join-Path $env:TEMP "deepotus_make_ico.py"
        Set-Content -Path $tmpPy -Value $pyScript -Encoding UTF8
        & $venvPy $tmpPy $LogoPng $iconPath
        Remove-Item $tmpPy -Force -ErrorAction SilentlyContinue
    }
}

# ---- 3. Create the desktop shortcut ----
# v1.10: target the silent VBS launcher (no console window). The app serves
# its own frontend, so a browser tab opens once the API is healthy.
$silent = Join-Path $AppDir "scripts\launch-silent.vbs"
$lnkPath = Join-Path $desktop "Deepotus Video Gen.lnk"
$wscript = Join-Path $env:WINDIR "System32\wscript.exe"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnkPath)
if (Test-Path $silent) {
    $sc.TargetPath   = $wscript
    $sc.Arguments    = "`"$silent`""
    $sc.Description  = "Launch Deepotus Video Gen (silent - no console window)"
} else {
    $psExe = (Get-Command powershell.exe).Source
    $sc.TargetPath   = $psExe
    $sc.Arguments    = "-NoExit -ExecutionPolicy Bypass -File `"$launch`""
    $sc.Description  = "Launch Deepotus Video Gen"
}
$sc.WorkingDirectory = $AppDir
if (Test-Path $iconPath) {
    $sc.IconLocation = "$iconPath,0"
} else {
    $sc.IconLocation = "$wscript,0"
}
$sc.Save()

Write-Host ""
Write-Host "Shortcut created:" -ForegroundColor Green
Write-Host "  $lnkPath"
Write-Host "Target: $psExe"
Write-Host "Runs:   $launch"
if (Test-Path $iconPath) {
    Write-Host "Icon:   $iconPath" -ForegroundColor Cyan
}
