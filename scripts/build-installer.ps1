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
    # compiler. A short root keeps the longest path well under 260.
    # Default derived from the profile (no machine-specific literal): the old
    # "D:\dz" default silently pointed at a CD-ROM drive on the build machine
    # (constat build v2.5.0) and every build had to override it by hand.
    [string]$StageRoot = (Join-Path $env:USERPROFILE "dz"),
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

# ---- 1b. Strip internal tooling from the shipped tree ----------------------
# The buyer gets the app, not the workshop. Without this the installer ships
# the whole bundle-patch chain, the migration/Claude-session kit, the QA
# scripts and the internal design docs -- several of which embed the author's
# machine paths. Only the three scripts the app itself invokes stay.
$keepScripts = @("launch-silent.vbs", "stop.ps1", "create-desktop-shortcut.ps1")
$stagedScripts = Join-Path $stageApp "scripts"
if (Test-Path $stagedScripts) {
    Get-ChildItem $stagedScripts -Force | Where-Object {
        $_.PSIsContainer -or ($keepScripts -notcontains $_.Name)
    } | Remove-Item -Recurse -Force
    $kept = (Get-ChildItem $stagedScripts -File).Name
    Write-Host "  scripts\ trimmed to: $($kept -join ', ')" -ForegroundColor Green
}
foreach ($d in @("docs\superpowers", "docs\plans", ".claude", ".pytest_cache",
                 "frontend\patches", "frontend\public")) {
    $p = Join-Path $stageApp $d
    if (Test-Path $p) { Remove-Item $p -Recurse -Force; Write-Host "  removed $d" -ForegroundColor Green }
}
# Fichiers de developpement du frontend : le buyer recoit dist/, pas la chaine
# de build. SOURCE.md documente la relation bundle<->sources pre-patch et
# contient les chemins de la machine de dev.
foreach ($f in @("frontend\SOURCE.md", "frontend\package.json",
                 "frontend\package-lock.json", "frontend\vite.config.js",
                 "frontend\tailwind.config.js", "frontend\postcss.config.js",
                 "frontend\index.html")) {
    $p = Join-Path $stageApp $f
    if (Test-Path $p) { Remove-Item $p -Force; Write-Host "  removed $f" -ForegroundColor Green }
}
# Bundle-patch backups (frontend\dist\assets\*.js.bak_*) are the dev patch
# chain, never loaded by the app: ~13 MB of dead weight the SPA mount would
# happily serve to anyone who guessed a filename. They shipped in every build
# up to 2.4.0; strip them here.
$stagedAssets = Join-Path $stageApp "frontend\dist\assets"
if (Test-Path $stagedAssets) {
    $baks = @(Get-ChildItem $stagedAssets -File -Filter "*.js.bak_*")
    if ($baks.Count -gt 0) {
        $bakMB = [math]::Round((($baks | Measure-Object Length -Sum).Sum) / 1MB, 1)
        $baks | Remove-Item -Force
        Write-Host "  removed $($baks.Count) bundle backup(s) ($bakMB MB)" -ForegroundColor Green
    }
}
# Backend tests are dev-only and pull in stub fixtures.
$stagedTests = Join-Path $stageApp "backend\tests"
if (Test-Path $stagedTests) { Remove-Item $stagedTests -Recurse -Force }
$stagedConftest = Join-Path $stageApp "backend\conftest.py"
if (Test-Path $stagedConftest) { Remove-Item $stagedConftest -Force }
# Last line of defence: no personal path may reach a buyer's disk.
$leaks = Get-ChildItem $stageApp -Recurse -File -Include *.ps1,*.cmd,*.vbs,*.py,*.md -ErrorAction SilentlyContinue |
    Select-String -Pattern 'C:\\Users\\olivi' -List -ErrorAction SilentlyContinue
if ($leaks) {
    Write-Warning "Personal paths found in staged files:"
    $leaks | ForEach-Object { Write-Warning "  $($_.Path)" }
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

# ---- 4b. gltfpack (meshoptimizer) -------------------------------------------
# app\services\mesh_optimize.py resolves it with shutil.which and the launcher
# puts app\bin on PATH. Without this step the 3D "optimize mesh" action fails
# on every install with "gltfpack introuvable" - the binary was documented as
# bundled but never actually downloaded.
$gpZip = Join-Path $cache "gltfpack-windows.zip"
if (-not $SkipDownloads -or -not (Test-Path $gpZip)) {
    $url = "https://github.com/zeux/meshoptimizer/releases/latest/download/gltfpack-windows.zip"
    Write-Host "Downloading gltfpack: $url" -ForegroundColor Cyan
    try {
        Invoke-WebRequest $url -OutFile $gpZip -UseBasicParsing
    } catch {
        Write-Warning "gltfpack download failed ($($_.Exception.Message)). 3D mesh optimization will be unavailable in this build."
        $gpZip = $null
    }
}
if ($gpZip -and (Test-Path $gpZip)) {
    $gpTmp = Join-Path $cache "gltfpack-x"
    if (Test-Path $gpTmp) { Remove-Item $gpTmp -Recurse -Force }
    Expand-Archive $gpZip -DestinationPath $gpTmp -Force
    $gpBin = Get-ChildItem $gpTmp -Recurse -Filter "gltfpack.exe" | Select-Object -First 1
    if ($gpBin) {
        Copy-Item $gpBin.FullName $binDir -Force
        Write-Host "  gltfpack staged in app\bin" -ForegroundColor Green
    } else {
        Write-Warning "gltfpack.exe not found in archive - 3D mesh optimization will be unavailable."
    }
}

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

# The .iss decides where the exe lands (OutputDir= - currently the OneDrive
# Desktop export folder); resolve it instead of assuming installer\output.
$outDir = (Select-String -Path (Join-Path $instDir "deepotus.iss") -Pattern '^OutputDir=(.+)$').Matches.Groups[1].Value.Trim()
if (-not $outDir) { $outDir = Join-Path $instDir "output" }
$out = Get-ChildItem $outDir -Filter "*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($out) {
    Write-Host ""
    Write-Host "INSTALLER READY: $($out.FullName) ($([math]::Round($out.Length/1MB)) MB)" -ForegroundColor Green
} else {
    throw "ISCC did not produce an output exe"
}
