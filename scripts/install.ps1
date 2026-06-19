# ============================================================
# DEEPOTUS VIDEO GEN -- Windows Install Script (v2)
# Auto-detects py.exe fallback if python.exe is unavailable
# Run from project root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " DEEPOTUS VIDEO GEN -- Install" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# --- Resolve a working Python command ---
# Returns a real Python command, skipping Microsoft Store stubs (which report 0.0.0.0).
function Resolve-PythonCommand {
    $candidates = @("python", "python3", "py")
    foreach ($name in $candidates) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        # Reject Microsoft Store stubs (FileVersion 0.0.0.0)
        $isStub = $false
        try {
            $info = (Get-Item $cmd.Source).VersionInfo
            if ($info.FileVersion -eq "0.0.0.0" -or [string]::IsNullOrEmpty($info.FileVersion)) {
                $isStub = $true
            }
        } catch { }
        if ($isStub) { continue }
        # Verify it actually responds to --version
        try {
            $output = & $name --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $output -match "Python") {
                return @{ Command = $name; Version = $output.Trim() }
            }
        } catch { }
    }
    return $null
}

# --- Check Python ---
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
$python = Resolve-PythonCommand
if ($python) {
    Write-Host "  [OK] $($python.Version) (using '$($python.Command)')" -ForegroundColor Green
    $PYTHON_CMD = $python.Command
}
else {
    Write-Host "  [ERR] Python not found." -ForegroundColor Red
    Write-Host "    Install Python 3.10+ from https://python.org and re-run this script."
    Write-Host "    Make sure to check 'Add python.exe to PATH' in the installer."
    exit 1
}

# --- Check Node.js ---
Write-Host "[2/6] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  [OK] Node.js $nodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "  [ERR] Node.js not found." -ForegroundColor Red
    Write-Host "    Install Node.js 20+ from https://nodejs.org and re-run this script."
    exit 1
}

# --- Check / install ffmpeg ---
Write-Host "[3/6] Checking ffmpeg..." -ForegroundColor Yellow
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    Write-Host "  [OK] ffmpeg is on PATH" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] ffmpeg not found." -ForegroundColor Yellow
    $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
    if ($hasWinget) {
        Write-Host "    Installing via winget..."
        winget install --silent --accept-package-agreements --accept-source-agreements Gyan.FFmpeg
        Write-Host "  [OK] ffmpeg installed (restart PowerShell to refresh PATH)" -ForegroundColor Green
    }
    else {
        Write-Host "    winget not available. Manual install required:" -ForegroundColor Yellow
        Write-Host "    1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        Write-Host "    2. Extract to C:\ffmpeg"
        Write-Host "    3. Add C:\ffmpeg\bin to System PATH"
    }
}

# --- Backend: Python virtual env ---
Write-Host "[4/6] Setting up Python virtual environment..." -ForegroundColor Yellow
Set-Location "$projectRoot\backend"

if (-not (Test-Path ".venv")) {
    & $PYTHON_CMD -m venv .venv
    Write-Host "  [OK] Created .venv" -ForegroundColor Green
}
else {
    Write-Host "  [OK] .venv already exists" -ForegroundColor Green
}

# Activate venv (for this session)
. ".\.venv\Scripts\Activate.ps1"

Write-Host "  Installing Python dependencies (this can take 2-3 minutes)..."
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "  [OK] Backend dependencies installed" -ForegroundColor Green

# --- .env setup ---
Write-Host "[5/6] Configuring environment..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  [WARN] Created backend\.env -- YOU MUST EDIT IT and add your fal.ai key" -ForegroundColor Yellow
}
else {
    Write-Host "  [OK] backend\.env already exists" -ForegroundColor Green
}

# --- Frontend ---
Write-Host "[6/6] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location "$projectRoot\frontend"
npm install --silent
Write-Host "  [OK] Frontend dependencies installed" -ForegroundColor Green

Set-Location $projectRoot

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " [OK] INSTALL COMPLETE" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit backend\.env and paste your FAL_KEY"
Write-Host "  2. (Optional) Add ELEVENLABS_API_KEY for voiceover"
Write-Host "  3. Verify IMAGES_FOLDER points to your image directory"
Write-Host "  4. Launch the app:  powershell -ExecutionPolicy Bypass -File scripts\run.ps1"
Write-Host ""
