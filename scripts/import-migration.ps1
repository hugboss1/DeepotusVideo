<#
  Deepotus Video Gen - IMPORT (run on the NEW PC / a lancer sur le NOUVEAU PC).
  Installs the app + all your data (generations, calendar, scheduled posts,
  keys) from the transfer folder. No reinstall needed.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\import-migration.ps1 -Src "E:\deepotus-transfer"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Src
)
$ErrorActionPreference = "Stop"
$LA      = $env:LOCALAPPDATA
$app     = Join-Path $LA "DeepotusVideoGen"
$data    = Join-Path $LA "DeepotusVideoGenData"
$srcApp  = Join-Path $Src "DeepotusVideoGen"
$srcData = Join-Path $Src "DeepotusVideoGenData"
if (-not (Test-Path $srcApp))  { throw "Source app missing: $srcApp" }
if (-not (Test-Path $srcData)) { throw "Source data missing: $srcData" }

# stop any running instance
$listen = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($listen) { Stop-Process -Id $listen.OwningProcess -Force -ErrorAction SilentlyContinue; Start-Sleep 2 }

function Invoke-Robo($s, $d) {
    robocopy $s $d /E /R:1 /W:1 /NFL /NDL /NJH /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($s -> $d), code $LASTEXITCODE" }
}

Write-Host "1/3  Installing the application..."
Invoke-Robo $srcApp $app
Write-Host "2/3  Restoring data (generations, calendar, keys)..."
Invoke-Robo $srcData $data

# 3. if the Windows user differs, rewrite absolute paths stored in the DB
$oldLA = $null
$infoP = Join-Path $Src "_migration-info.txt"
if (Test-Path $infoP) {
    foreach ($l in Get-Content $infoP) {
        if ($l -like "source_localappdata=*") { $oldLA = $l.Substring("source_localappdata=".Length).Trim() }
    }
}
if ($oldLA -and ($oldLA -ne $LA)) {
    Write-Host "3/3  Different Windows user - rewriting stored paths in the DB..." -ForegroundColor Yellow
    $py  = Join-Path $app "runtime\python\python.exe"
    $db  = Join-Path $data "deepotus.db"
    $tmp = Join-Path $env:TEMP "dz_pathfix.py"
    $lines = @(
        'import sqlite3, sys'
        'old, new, db = sys.argv[1], sys.argv[2], sys.argv[3]'
        'c = sqlite3.connect(db); cur = c.cursor()'
        'for col in ("video_path", "final_video_path", "audio_path"):'
        '    try:'
        '        cur.execute("UPDATE jobs SET %s=REPLACE(%s, ?, ?) WHERE %s LIKE ''C:%%''" % (col, col, col), (old, new))'
        '    except Exception:'
        '        pass'
        'c.commit(); c.close(); print("paths rewritten:", old, "->", new)'
    )
    Set-Content -Path $tmp -Value $lines -Encoding UTF8
    if (Test-Path $py) { & $py $tmp $oldLA $LA $db } else { Write-Host "  python runtime not found - paths NOT rewritten" -ForegroundColor Red }
} else {
    Write-Host "3/3  Same Windows user - stored paths already valid." -ForegroundColor Green
}

# recreate the Desktop + Start Menu shortcut
$mk = Join-Path $app "scripts\create-desktop-shortcut.ps1"
if (Test-Path $mk) {
    try { powershell -ExecutionPolicy Bypass -File $mk | Out-Null } catch { Write-Host "  (shortcut: $_)" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "IMPORT DONE." -ForegroundColor Green
Write-Host "Launch 'Deepotus Video Gen' (Desktop or Start Menu shortcut)." -ForegroundColor Green
Write-Host "IMPORTANT: do NOT run the app on BOTH PCs at once (scheduled posts could double-publish)." -ForegroundColor Yellow
