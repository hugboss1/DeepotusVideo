# Voixbox (t166) — range une voix entraînée par la WebUI là où Voixbox la cherche :
#   %LOCALAPPDATA%\DeepotusVideoGen\voix_rvc\<nom>\<nom>.pth  (+ l'index « added_… .index »)
#   powershell -ExecutionPolicy Bypass -File tools\voixbox\ranger-voix.ps1 -Nom oli
param(
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_-]{1,40}$')][string]$Nom,
  [string]$Dossier = (Join-Path $PSScriptRoot "rvc-webui"),
  [string]$Destination = (Join-Path $env:LOCALAPPDATA "DeepotusVideoGen\voix_rvc")   # = VOIXBOX_MODELES de Voixbox
)
$ErrorActionPreference = "Stop"
$pth = Join-Path $Dossier "assets\weights\$Nom.pth"
if (-not (Test-Path $pth)) { throw "Modèle introuvable : $pth — l'entraînement est-il allé jusqu'au bout ?" }
$index = Get-ChildItem (Join-Path $Dossier "logs\$Nom") -Filter "added_*.index" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
$dest = Join-Path $Destination $Nom
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item $pth $dest -Force
if ($index) { Copy-Item $index.FullName $dest -Force } else { Write-Warning "Pas d'index : la voix marchera, un peu moins fidèle." }
Write-Host "Voix « $Nom » rangée dans $dest. Dans l'application : Avatar live -> Direct -> Voix -> « Voix RVC locale — $Nom »." -ForegroundColor Green
