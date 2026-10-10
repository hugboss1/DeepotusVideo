# Backend de PREUVE du guide v3 (port 8809 ; le 8799 est arrêté par d'autres sessions) : le code de ce dépôt, un
# dossier de données jetable, aucune clé (rien de payant n'est possible), une image de démonstration.
# Jamais le 8765 de l'utilisateur. Données de démonstration ensuite : semer_atelier.py, semer_sons.py.
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(__file__).resolve().parents[2] / "backend"      # le backend du dépôt (ou du worktree) de ce script
d = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_preuve_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(d / "images")
os.environ["OUTPUTS_FOLDER"] = str(d / "outputs")
for k in ("FAL_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MESHY_API_KEY",
          "GEMINI_API_KEY", "FIGMA_TOKEN", "TELEGRAM_BOT_TOKEN"):
    os.environ[k] = ""
(d / "images").mkdir(parents=True, exist_ok=True)
# t176 : le moteur du Photolab n'est pas dans un worktree (vendor/ ignoré) → celui de l'installation, s'il y est
_pc = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "DeepotusVideoGen" / "vendor" / "photocraft-0.3.0"
for _cli in sorted(_pc.rglob("photocraft-cli.exe")) if _pc.is_dir() else []:
    os.environ.setdefault("PHOTOCRAFT_CLI", str(_cli))
    break
sys.path.insert(0, str(WT))
os.chdir(WT)

from PIL import Image, ImageDraw  # noqa: E402

im = Image.new("RGB", (1080, 1920), (16, 20, 34))
dr = ImageDraw.Draw(im)
dr.ellipse((290, 560, 790, 1060), fill=(240, 180, 41))
dr.rectangle((0, 1500, 1080, 1920), fill=(40, 90, 120))
im.save(d / "images" / "demo-affiche.png")
print("donnees de preuve :", d, flush=True)

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8809")), log_level="warning")
