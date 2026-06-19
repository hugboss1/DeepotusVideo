# ============================================================
# DEEPOTUS VIDEO GEN -- Path Setup Helper
# Interactively sets IMAGES_FOLDER and OUTPUTS_FOLDER in .env
# ============================================================

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $projectRoot "backend\.env"

if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: backend\.env not found. Run install.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " DEEPOTUS -- Configure paths" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press ENTER to keep the current value shown in [brackets]."
Write-Host "Use forward slashes / in paths (e.g. C:/Users/me/images)."
Write-Host ""

# Read current values
$envContent = Get-Content $envFile -Raw
$currentImages = if ($envContent -match "IMAGES_FOLDER=(.+)") { $matches[1].Trim() } else { "./assets/images" }
$currentOutputs = if ($envContent -match "OUTPUTS_FOLDER=(.+)") { $matches[1].Trim() } else { "./assets/outputs" }

# Prompt for new values
$newImages = Read-Host "IMAGES_FOLDER [$currentImages]"
if ([string]::IsNullOrWhiteSpace($newImages)) { $newImages = $currentImages }

$newOutputs = Read-Host "OUTPUTS_FOLDER [$currentOutputs]"
if ([string]::IsNullOrWhiteSpace($newOutputs)) { $newOutputs = $currentOutputs }

# Update .env (preserves all other lines)
$envContent = $envContent -replace "IMAGES_FOLDER=.*", "IMAGES_FOLDER=$newImages"
$envContent = $envContent -replace "OUTPUTS_FOLDER=.*", "OUTPUTS_FOLDER=$newOutputs"
Set-Content -Path $envFile -Value $envContent -Encoding UTF8 -NoNewline

Write-Host ""
Write-Host "[OK] Updated backend\.env:" -ForegroundColor Green
Write-Host "  IMAGES_FOLDER  = $newImages"
Write-Host "  OUTPUTS_FOLDER = $newOutputs"
Write-Host ""
Write-Host "Restart the backend to apply changes."
