# ============================================================
#  DEEPOTUS VIDEO GEN -- Build the Windows installer (v1.11)
#
#  Produces installer\output\DeepotusVideoGen-Setup-<ver>.exe with ZERO
#  prerequisites for the buyer: embedded Python runtime + bundled ffmpeg.
#
#  Pipeline:
#    1. Stage the app tree            -> installer\stage\app
#    2. Embedded CPython (python.org) -> stage\app\runtime\python
#    3. pip install -r requirements --target runtime\python\site-packages
#       (MUST run with a Python of the SAME minor version as the
#        embeddable zip, so binary wheels match)
#    4. ffmpeg essentials (gyan.dev)  -> stage\app\bin
#    5. Compile installer\deepotus.iss with Inno Setup (ISCC)
#
#  Usage:
#    powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1
#  Optional: -SkipDownloads to reuse cached runtime/ffmpeg from a previous run.
# ============================================================
param(
    [string]$AppDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    # SHORT staging root: the elevenlabs SDK ships 135-char filenames; staged
    # under a deep project tree they exceed MAX_PATH and abort the Inno
    # compiler. A 5-char root keeps the longest path well under 260.
    [string]$StageRoot = "D:\dz",
    [switch]$SkipDownloads
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$instDir  = Join-Path $AppDir "installer"
$stage    = $StageRoot
$stageApp = Join-Path $stage "app"
$cache    = Join-Path $instDir "_cache"
New-Item -ItemType Directory -Force -Path $stage, $cache | Out-Null

# ---- 0. Locate a build Python + matching embeddable version --------------
$buildPy = Join-Path $AppDir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $buildPy)) { $buildPy = (Get-Command python -ErrorAction Stop).Source }
$pyVer = (& $buildPy -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
$pyMM  = ($pyVer -split '\.')[0..1] -join '.'
Write-Host "Build python: $buildPy ($pyVer)" -ForegroundColor Cyan

# ---- 1. Stage the app tree ------------------------------------------------
Write-Host "Staging app tree..." -ForegroundColor Cyan
if (Test-Path $stageApp) { Remove-Item $stageApp -Recurse -Force }
robocopy $AppDir $stageApp /E /NFL /NDL /NJH /NJS `
    /XD node_modules .venv __pycache__ .git _design_pkg installer `
    /XF *.db .env _uvicorn.out.log _uvicorn.err.log | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
# The buyer runtime doesn't need frontend sources -- dist only.
foreach ($d in @("frontend\src", "frontend\node_modules")) {
    $p = Join-Path $stageApp $d
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}
if (-not (Test-Path (Join-Path $stageApp "frontend\dist\index.html"))) {
    throw "frontend\dist missing -- run 'npm run build' in frontend\ first"
}
if (-not (Test-Path (Join-Path $stageApp "assets\deepotus-logo.ico"))) {
    throw "assets\deepotus-logo.ico missing -- run scripts\create-desktop-shortcut.ps1 once"
}

# ---- 2. Embedded CPython ---------------------------------------------------
$embedZip = Join-Path $cache "python-$pyVer-embed-amd64.zip"
$runtime  = Join-Path $stageApp "runtime\python"
if (-not $SkipDownloads -or -not (Test-Path $embedZip)) {
    $url = "https://www.python.org/ftp/python/$pyVer/python-$pyVer-embed-amd64.zip"
    Write-Host "Downloading embedded Python: $url" -ForegroundColor Cyan
    Invoke-WebRequest $url -OutFile $embedZip -UseBasicParsing
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Expand-Archive $embedZip -DestinationPath $runtime -Force
# Enable site-packages in the ._pth file (embeddable disables it by default).
$pth = Get-ChildItem $runtime -Filter "python*._pth" | Select-Object -First 1
if (-not $pth) { throw "._pth not found in embeddable zip" }
$content = Get-Content $pth.FullName
if ($content -notcontains "site-packages") {
    Add-Content $pth.FullName "site-packages"
}
Write-Host "  runtime ready ($($pth.Name) patched)" -ForegroundColor Green

# ---- 3. Dependencies into runtime\python\site-packages ---------------------
Write-Host "Installing dependencies (pip --target, $pyMM wheels)..." -ForegroundColor Cyan
$sitePkgs = Join-Path $runtime "site-packages"
& $buildPy -m pip install --quiet --no-warn-script-location `
    --target $sitePkgs -r (Join-Path $AppDir "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install --target failed" }
$pkgCount = (Get-ChildItem $sitePkgs -Directory).Count
# Purge bytecode caches: they add ~28 chars per path and push deep packages
# (elevenlabs generated clients) past MAX_PATH, which aborts the Inno
# compiler with "path not found". Python regenerates them at runtime.
Get-ChildItem $sitePkgs -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force
Write-Host "  $pkgCount packages staged (bytecode purged)" -ForegroundColor Green

# ---- 4. ffmpeg essentials ---------------------------------------------------
$ffZip = Join-Path $cache "ffmpeg-release-essentials.zip"
if (-not $SkipDownloads -or -not (Test-Path $ffZip)) {
    $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    Write-Host "Downloading ffmpeg essentials: $url" -ForegroundColor Cyan
    Invoke-WebRequest $url -OutFile $ffZip -UseBasicParsing
}
$ffTmp = Join-Path $cache "ffmpeg-x"
if (Test-Path $ffTmp) { Remove-Item $ffTmp -Recurse -Force }
Expand-Archive $ffZip -DestinationPath $ffTmp -Force
$ffBin = Get-ChildItem $ffTmp -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if (-not $ffBin) { throw "ffmpeg.exe not found in archive" }
$binDir = Join-Path $stageApp "bin"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Copy-Item $ffBin.FullName $binDir -Force
Copy-Item (Join-Path $ffBin.DirectoryName "ffprobe.exe") $binDir -Force
Write-Host "  ffmpeg + ffprobe staged in app\bin" -ForegroundColor Green

# ---- 5. Compile with Inno Setup ---------------------------------------------
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Host "Inno Setup not found -- installing via winget..." -ForegroundColor Yellow
    winget install -e --id JRSoftware.InnoSetup --silent --accept-source-agreements --accept-package-agreements | Out-Null
    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "ISCC.exe not found after install -- install Inno Setup 6 manually" }
Write-Host "Compiling installer with: $iscc" -ForegroundColor Cyan
& $iscc "/DStageDir=$stage" (Join-Path $instDir "deepotus.iss") | Select-Object -Last 4

$out = Get-ChildItem (Join-Path $instDir "output") -Filter "*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($out) {
    Write-Host ""
    Write-Host "INSTALLER READY: $($out.FullName) ($([math]::Round($out.Length/1MB)) MB)" -ForegroundColor Green
} else {
    throw "ISCC did not produce an output exe"
}
