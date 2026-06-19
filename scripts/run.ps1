# ============================================================
# DEEPOTUS VIDEO GEN -- Run Script
# Starts backend (port 8765) + frontend (port 5173) in two windows
# ============================================================

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " DEEPOTUS VIDEO GEN -- Starting services" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Backend in a new window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "cd '$projectRoot\backend'; .\.venv\Scripts\Activate.ps1; python -m app.main"
)

Start-Sleep -Seconds 2

# Frontend in another window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "cd '$projectRoot\frontend'; npm run dev"
)

Start-Sleep -Seconds 4

Write-Host ""
Write-Host "  Frontend URL:  http://localhost:5173"
Write-Host "  Backend API:   http://localhost:8765/docs"
Write-Host ""
Write-Host "Two PowerShell windows opened -- keep them running."
Write-Host "Close them to stop the services."
Write-Host ""

# Open browser after services have time to boot
Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"
