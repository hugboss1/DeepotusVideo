# Voixbox (t166) — télécharge les poids de la RVC WebUI (son README, « Download models ») depuis le dépôt Hugging Face
# officiel lj1995/VoiceConversionWebUI, avec le magasin de certificats de Windows (truststore). Lancé par
# installer.ps1 DEPUIS le dossier du dépôt rvc-webui.
import os
os.environ.pop("SSLKEYLOGFILE", None)          # Avast (voir installer.ps1)
import shutil
import zipfile

import truststore
truststore.inject_into_ssl()
from huggingface_hub import hf_hub_download, snapshot_download

R = "lj1995/VoiceConversionWebUI"
snapshot_download(R, allow_patterns=["hubert_base/*"], local_dir="assets")
hf_hub_download(R, "rmvpe.pt", local_dir="assets/rmvpe")
for f in ("pretrained_v2/f0G40k.pth", "pretrained_v2/f0D40k.pth"):    # v2, 40 kHz, avec hauteur : le défaut
    hf_hub_download(R, f, local_dir="assets")
zipfile.ZipFile(hf_hub_download(R, "mute.zip", local_dir=".model-downloads")).extractall("logs")
app_bin = os.path.join(os.environ.get("LOCALAPPDATA", ""), "DeepotusVideoGen", "bin")
for f in ("ffmpeg.exe", "ffprobe.exe"):                                # la WebUI les veut à sa racine
    if not os.path.exists(f) and os.path.exists(os.path.join(app_bin, f)):
        shutil.copy2(os.path.join(app_bin, f), f)
print("poids OK")
