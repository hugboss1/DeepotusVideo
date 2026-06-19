# Building the Deepotus Video Gen installer (v1.15.0)

The original `deepotus.iss` / dev source tree was not present on this machine,
so this installer was built by **packaging the already-installed app tree**
(which is a complete, working app: embedded Python runtime + bundled ffmpeg +
patched frontend + backend). `deepotus.iss` in this folder is the script used.

## Why stage to a short root
The ElevenLabs SDK ships ~135-char filenames. Under the install path
(`%LOCALAPPDATA%\DeepotusVideoGen\...`) the longest file is **259 chars** —
at the Windows MAX_PATH (260) limit, which makes the Inno Setup **compiler**
fail when reading sources. Staging to a short root (`C:\Users\<you>\dz\app`,
~21-char base) brings the longest path to ~235 chars. Install-time is fine
(the original v1.14 installer already laid down the 259-char file).

## Steps (PowerShell)
```powershell
$src = "$env:LOCALAPPDATA\DeepotusVideoGen"
$stageApp = "C:\Users\$env:USERNAME\dz\app"
New-Item -ItemType Directory -Force $stageApp | Out-Null
# Stage CODE only — never user data, bytecode, logs, or dev plans:
robocopy $src $stageApp /E /XD __pycache__ "$src\docs\superpowers" `
    /XF *.pyc *.log .env *.db *.bak /R:1 /W:1

# Inno Setup 6 (user scope, no admin):
winget install -e --id JRSoftware.InnoSetup --silent --scope user `
    --accept-source-agreements --accept-package-agreements

# Compile (edit StageDir in deepotus.iss if your stage path differs):
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" `
    "C:\Users\$env:USERNAME\dz\deepotus.iss"
# -> DeepotusVideoGen-Setup-1.15.0.exe in the OutputDir set in the .iss
```

## What the installer does
- Installs per-user to `{localappdata}\DeepotusVideoGen` (no admin).
- Desktop + Start-menu shortcuts run `wscript.exe scripts\launch-silent.vbs`
  (starts uvicorn hidden, waits for /api/health, opens the browser).
- User DATA in `%LOCALAPPDATA%\DeepotusVideoGenData` is never touched by the
  installer or uninstaller — it survives install / uninstall / upgrade.

## Verified
- Compile: success, 94 MB output, ProductVersion 1.15.0.
- Silent test install (`/VERYSILENT /DIR=...`): 7406 files, uninstaller created.
- Smoke test on the packaged embedded runtime: `import app.main` OK,
  version 1.15.0, HeyGen list timeout 120 s.
