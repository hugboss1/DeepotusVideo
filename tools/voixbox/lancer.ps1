# Voixbox (t166) — démarre le service local de voix (127.0.0.1:17495). Laisse cette fenêtre ouverte pendant le Direct.
#   powershell -ExecutionPolicy Bypass -File tools\voixbox\lancer.ps1
param([string]$Dossier = (Join-Path $PSScriptRoot "rvc-webui"))
Remove-Item Env:SSLKEYLOGFILE -ErrorAction SilentlyContinue      # Avast (voir installer.ps1)
$env:VOIXBOX_RVC_WEBUI = $Dossier
$env:PYTHONIOENCODING = "utf-8"
& "$Dossier\.venv\Scripts\python.exe" (Join-Path $PSScriptRoot "server.py")
