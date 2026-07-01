<#
  Deepotus Video Gen - EXPORT (run on THIS PC / a lancer sur CE PC).
  Copies the app (code + runtime + new features) AND the data (generations,
  calendar, scheduled posts, keys) to a transfer folder/drive.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\export-migration.ps1 -Dest "E:\deepotus-transfer"
    # option: -SkipOutputs  (does NOT include the 1.9 GB of renders)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Dest,
    [switch]$SkipOutputs
)
$ErrorActionPreference = "Stop"
$LA   = $env:LOCALAPPDATA
$app  = Join-Path $LA "DeepotusVideoGen"
$data = Join-Path $LA "DeepotusVideoGenData"
if (-not (Test-Path $app))  { throw "App not found: $app" }
if (-not (Test-Path $data)) { throw "Data not found: $data" }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$destApp  = Join-Path $Dest "DeepotusVideoGen"
$destData = Join-Path $Dest "DeepotusVideoGenData"

$listen = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($listen) {
    Write-Host "NOTE: app is running (port 8765). The DB is copied as a safe snapshot, but close the app for a 100% clean export." -ForegroundColor Yellow
}

function Invoke-Robo($src, $dst, $extra) {
    $args = @($src, $dst, "/E", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NP") + $extra
    robocopy @args | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($src -> $dst), code $LASTEXITCODE" }
}

Write-Host "1/3  Copying the application (code + runtime + new features)..."
Invoke-Robo $app $destApp @()

Write-Host "2/3  Copying data (generations, calendar, keys)..."
$dataExtra = @()
if ($SkipOutputs) { $dataExtra = @("/XD", (Join-Path $data "assets\outputs")) }
Invoke-Robo $data $destData $dataExtra

Write-Host "3/3  Consistent DB snapshot (jobs + calendar + scheduled posts)..."
$py = Join-Path $app "runtime\python\python.exe"
if (Test-Path $py) {
    New-Item -ItemType Directory -Force -Path $destData | Out-Null
    & $py -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); s.close(); d.close(); print('db snapshot ok')" (Join-Path $data "deepotus.db") (Join-Path $destData "deepotus.db")
} else {
    Write-Host "  (python runtime not found - using the robocopy DB copy)" -ForegroundColor Yellow
}

# migration info (to rewrite paths if the Windows username differs)
@(
    "source_user=$env:USERNAME"
    "source_localappdata=$LA"
    "exported=$(Get-Date -Format s)"
    "app=DeepotusVideoGen"
    "data=DeepotusVideoGenData"
) | Set-Content -Path (Join-Path $Dest "_migration-info.txt") -Encoding UTF8

# bundle the import script + guide next to the transfer
foreach ($f in @("import-migration.ps1", "MIGRATION.md")) {
    $p = Join-Path $PSScriptRoot $f
    if (Test-Path $p) { Copy-Item $p $Dest -Force }
}

$gb = [math]::Round(((Get-ChildItem $Dest -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1GB, 2)
Write-Host ""
Write-Host "EXPORT DONE -> $Dest  ($gb GB)" -ForegroundColor Green
Write-Host "Copy THIS folder to the other laptop, then run import-migration.ps1 inside it." -ForegroundColor Green
