# Voixbox — installation de la voix LOCALE (RVC) pour le Direct d'Avatar live (t166, 10/10/2026).
# Tout ce que ce script fait a été mesuré sur la machine de référence (RTX 2080 Ti 11 Go, Windows 11, Avast) :
#   - Avast pose SSLKEYLOGFILE : le Python téléchargé par uv plante (« no OPENSSL_Applink ») -> la variable est
#     retirée POUR CE SCRIPT SEULEMENT (aucun réglage du système n'est touché) ;
#   - l'interception TLS d'Avast fait échouer git et pip -> git passe par schannel, uv par --native-tls, Python par
#     truststore : tous lisent le magasin de certificats de Windows.
# Durée : 15 à 30 minutes ; environ 6 Go (torch CUDA 12.8 + dépendances + 560 Mo de poids).
#   powershell -ExecutionPolicy Bypass -File tools\voixbox\installer.ps1
param(
  [string]$Dossier = (Join-Path $PSScriptRoot "rvc-webui"),
  [string]$Commit = "81eed5e8f68b6bed1789f682fe78cdd324495afc"     # RVC WebUI épinglée (04/08/2026), licence MIT
)
$ErrorActionPreference = "Stop"
Remove-Item Env:SSLKEYLOGFILE -ErrorAction SilentlyContinue
function Etape($t) { Write-Host "`n== $t" -ForegroundColor Yellow }

Etape "1/6 uv (gestionnaire Python)"
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
  $outil = Join-Path $PSScriptRoot ".uvtool"
  if (-not (Test-Path "$outil\Scripts\uv.exe")) {
    py -3 -m venv $outil
    & "$outil\Scripts\python.exe" -m pip install --quiet uv==0.8.22
  }
  $uv = "$outil\Scripts\uv.exe"
}
& $uv --version

Etape "2/6 dépôt RVC WebUI ($($Commit.Substring(0,7)))"
if (-not (Test-Path "$Dossier\.git")) {
  git -c http.sslBackend=schannel clone --filter=blob:none https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git $Dossier
}
git -C $Dossier -c http.sslBackend=schannel fetch --quiet origin $Commit
git -C $Dossier checkout --quiet $Commit

Etape "3/6 Python 3.12 + torch CUDA 12.8"
Set-Location $Dossier
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $uv venv --native-tls --python 3.12 .venv }
& $uv pip install --native-tls --python .venv\Scripts\python.exe "torch==2.7.1+cu128" "torchaudio==2.7.1+cu128" --index-url https://download.pytorch.org/whl/cu128

Etape "4/6 dépendances de la WebUI (index officiels à la place des miroirs)"
(Get-Content requirments_cu128_py312.txt) `
  -replace 'https://mirrors\.nju\.edu\.cn/pytorch/whl/cu128', 'https://download.pytorch.org/whl/cu128' `
  -replace '--index-url https://mirrors\S*', '--index-url https://pypi.org/simple' `
  -replace '--extra-index-url https://mirrors\S*', '--extra-index-url https://download.pytorch.org/whl/cu128' |
  Set-Content -Encoding utf8 req_officiel.txt
& $uv pip install --native-tls --python .venv\Scripts\python.exe --index-strategy unsafe-best-match -r req_officiel.txt truststore huggingface_hub

Etape "5/6 poids (hubert, rmvpe, pré-entraînés v2 40k, silences) ~560 Mo"
& .venv\Scripts\python.exe (Join-Path $PSScriptRoot "poids.py")

Etape "6/6 vérification"
& .venv\Scripts\python.exe -c "import torch; print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucun GPU')"
Write-Host "`nVoixbox est installé. Suite : entraîner une voix (README.md, « Entraîner une voix »), puis lancer.ps1." -ForegroundColor Green
