# Voixbox (t166) — ouvre la RVC WebUI (http://127.0.0.1:7865) pour ENTRAÎNER une voix. Voir README.md.
#   powershell -ExecutionPolicy Bypass -File tools\voixbox\webui.ps1
param([string]$Dossier = (Join-Path $PSScriptRoot "rvc-webui"))
Remove-Item Env:SSLKEYLOGFILE -ErrorAction SilentlyContinue      # Avast (voir installer.ps1)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = $Dossier                                        # ses sous-processus d'entraînement importent infer/
$env:PYTHONSAFEPATH = "1"     # comme le Python embarqué officiel (._pth) : train/x.py ne doit pas masquer le paquet train
Set-Location $Dossier
& ".venv\Scripts\python.exe" webui.py
