# ============================================================
#  DEEPOTUS VIDEO GEN -- Desktop Launcher
#  Step 1: API keys (set them first)
#  Step 2: start backend (8765) + frontend (5173)
# ============================================================

$ErrorActionPreference = "Stop"
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$envFile     = Join-Path $projectRoot "backend\.env"
$envTemplate = Join-Path $projectRoot "backend\.env.template"

function Write-Rule { param($t) Write-Host $t -ForegroundColor Cyan }

Write-Host ""
Write-Rule "=============================================="
Write-Rule "  DEEPOTUS VIDEO GEN -- Launcher"
Write-Rule "=============================================="
Write-Host ""

# ---- STEP 1: API KEYS ----
Write-Host "STEP 1 of 2 -- API KEYS" -ForegroundColor Yellow
Write-Host ""
Write-Host "This app needs API keys to reach the AI providers."
Write-Host "Keys live ONLY in your local file:"
Write-Host "  $envFile"
Write-Host "Never paste a key into a chat or share it. Rotate it if you do."
Write-Host ""

if (-not (Test-Path $envFile)) {
    if (Test-Path $envTemplate) {
        Copy-Item $envTemplate $envFile
        Write-Host "Created backend\.env from the template." -ForegroundColor Green
    } else {
        New-Item -ItemType File -Path $envFile | Out-Null
        Write-Host "Created an empty backend\.env." -ForegroundColor Green
    }
}

Write-Host "Keys to set in backend\.env :"
Write-Host ""
Write-Host "  FAL_KEY            REQUIRED  -- Seedance video"
Write-Host "                     Get it:   https://fal.ai/dashboard/keys"
Write-Host "                     Format:   fal-..."
Write-Host ""
Write-Host "  HEYGEN_API_KEY     REQUIRED  -- HeyGen / Composition / Templates"
Write-Host "                     Get it:   https://app.heygen.com/api"
Write-Host "                     Format:   sk_V2_hgu_...  or  hg_..."
Write-Host ""
Write-Host "  ELEVENLABS_API_KEY OPTIONAL  -- voiceover"
Write-Host "                     Get it:   https://elevenlabs.io/app/settings/api-keys"
Write-Host ""
Write-Host "Rules: no spaces around '=', no quotes, no trailing spaces, save as UTF-8."
Write-Host ""

$envText = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
function Test-KeySet {
    param($name)
    if ($null -eq $envText) { return $false }
    foreach ($line in ($envText -split "`n")) {
        if ($line -match "^\s*$name\s*=\s*(.+?)\s*$") {
            return ($Matches[1].Trim().Length -gt 0)
        }
    }
    return $false
}
$falSet = Test-KeySet "FAL_KEY"
$hgSet  = Test-KeySet "HEYGEN_API_KEY"
Write-Host ("  FAL_KEY:        " + $(if ($falSet) { "set" } else { "NOT SET" }))
Write-Host ("  HEYGEN_API_KEY: " + $(if ($hgSet)  { "set" } else { "NOT SET" }))
Write-Host ""

$open = Read-Host "Open backend\.env now to edit your keys? [Y/n]"
if ($open -ne "n" -and $open -ne "N") {
    Start-Process notepad.exe $envFile
    Write-Host "Edit the file, SAVE it, then return to this window." -ForegroundColor Yellow
}
Write-Host ""
Read-Host "Press Enter once your keys are saved in backend\.env to continue"

# ---- STEP 2: LAUNCH ----
Write-Host ""
Write-Host "STEP 2 of 2 -- STARTING SERVICES" -ForegroundColor Yellow

$venv = Join-Path $projectRoot "backend\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) {
    Write-Host ""
    Write-Host "Python venv not found -- the app is not installed yet." -ForegroundColor Red
    Write-Host "Run the installer once, then relaunch:" -ForegroundColor Red
    Write-Host ("  powershell -ExecutionPolicy Bypass -File `"" + (Join-Path $scriptDir "install.ps1") + "`"")
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

& (Join-Path $scriptDir "run.ps1")

Write-Host ""
Write-Host "Launcher done. The two service windows stay open while you work." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173   API docs: http://localhost:8765/docs"
Write-Host ""
