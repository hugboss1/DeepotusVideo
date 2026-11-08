# t443b (08/11/2026) : génère les illustrations des fiches de l'écran Méthodes (FLUX via fal, ≈ 0,003 $ l'image),
# par le chemin même de l'app (_generate_image_core, garde des plafonds), dans une instance ISOLÉE (DEEPOTUS_DATA_DIR
# temporaire) ; seule la clé fal est lue dans le .env réel, jamais affichée. Une fiche qui a déjà son .webp est sautée.
# Usage : python scripts/methodes_illustrations.py <racine du dépôt> [--go] [--seulement slug,slug]   (sans --go : devis)
import asyncio
import json
import os
import pathlib
import sys
import tempfile

W = pathlib.Path(sys.argv[1]).resolve()
GO = "--go" in sys.argv
SEUL = []
if "--seulement" in sys.argv:
    SEUL = sys.argv[sys.argv.index("--seulement") + 1].split(",")

reel = pathlib.Path(os.environ["LOCALAPPDATA"]) / "DeepotusVideoGenData" / ".env"
cle = next((l.split("=", 1)[1].strip().strip('"') for l in reel.read_text("utf-8").splitlines()
            if l.startswith("FAL_KEY=")), "")
tmp = tempfile.mkdtemp(prefix="dzillus443_")
os.environ["DEEPOTUS_DATA_DIR"] = tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(tmp, "outputs"))
pathlib.Path(tmp, "images").mkdir()
pathlib.Path(tmp, "outputs").mkdir()
os.environ["FAL_KEY"] = cle
sys.path.insert(0, str(W / "backend"))

STYLE = ("Isometric miniature diorama on a dark navy studio table, soft warm rim light, a few clean low-poly objects, "
         "muted navy, cream and warm gold palette, gentle depth of field, polished 3D illustration. The scene shows: ")

# sujets réécrits en OBJETS pour l'image seule (FLUX dessine du faux texte dès qu'un sujet parle de mots ou d'étiquettes)
SUJETS = {
    "auto-edit": "a vertical phone on a tripod facing a small person, a film strip cut into pieces beside it, a tiny "
                 "speaker and a clapperboard",
    "give-each-picture-a-job": "five small blank picture cards connected by golden strings to one framed painting of a "
                               "samurai cat",
    "kinetic-film": "large abstract golden shapes flying fast with motion blur over glowing pulse bars",
    "nine-models-one-brief": "nine small painted wooden shop signboards in a 3 by 3 rack, three of them tilted aside",
    "apex-livery-studio": "the same racing kart three times side by side with three different colour schemes, "
                          "paint swatches nearby",
    "every-scenario": "five transparent glass plates stacked in depth showing a singer silhouette and colourful "
                      "abstract shapes",
    "one-logo-42-worlds": "the same round golden emblem in four small worlds: green terminal, starry sky, op art "
                          "stripes, neon city",
    "one-take-many-angles": "top view of a small character on a round stage surrounded by thirteen tiny film cameras",
    "image-to-3d-benchmark": "six small 3D statues of the same fox on pedestals, half painted, half grey clay",
    "bottled": "the same dark perfume bottle with a blank gold label on six small pedestals from morning to night",
    "maison-vespree": "the same dark champagne bottle with a blank gold label in three lights: afternoon, sunset, night",
    "motion-loops": "nine colourful geometric tiles on a tray, each with a small circular arrow sculpture",
    "content-engine": "a vertical phone on a small stand beside a stack of film reels and a tiny rocket climbing a "
                      "staircase of golden blocks",
    "grease-pencil-to-final-frame": "a pencil sketch on paper turning into a small finished painted scene with a "
                                    "lighthouse, a pencil lying beside it",
}
fiches = json.loads((W / "docs/superpowers/specs/assets/2026-11-08-scenario-explorations/fiches.json").read_text("utf-8"))
en = json.loads((W / "docs/superpowers/specs/assets/2026-11-08-scenario-explorations/fiches_en.json").read_text("utf-8"))
dest = W / "frontend" / "methodes" / "illustrations"
dest.mkdir(parents=True, exist_ok=True)
a_faire = [f for f in fiches if (not SEUL or f["slug"] in SEUL) and not (dest / f"{f['slug']}.webp").exists()]

try:
    import truststore  # le magasin de certificats de Windows, comme main.py
    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001
    pass
from app.config import settings  # noqa: E402
from app.services import pricing  # noqa: E402

devis = pricing.estimate({"kind": "image", "n": len(a_faire), "model": "flux"})
print(f"{len(a_faire)} illustration(s) à générer ; devis : {devis['total_usd']} $ ; clé fal posée : {bool(settings.FAL_KEY)}")
if not GO or not a_faire:
    sys.exit(0)

from fastapi import BackgroundTasks  # noqa: E402
from PIL import Image  # noqa: E402
from app.api.routes import _generate_image_core  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def une(f, sem, bilan):
    async with sem:
        prompt = STYLE + SUJETS.get(f["slug"], en[f["slug"]]["illustration_en"])
        try:
            out = await _generate_image_core({"prompt": prompt, "model": "flux", "size": "landscape_16_9", "n": 1,
                                              "source": "methodes"}, BackgroundTasks())
            src = settings.images_path / out["images"][0]
            with Image.open(src) as im:
                im = im.convert("RGB")
                w, h = im.size
                ch = int(w * 10 / 16)
                if ch <= h:
                    y = (h - ch) // 2
                    im = im.crop((0, y, w, y + ch))
                im = im.resize((640, 400), Image.LANCZOS)
                im.save(dest / f"{f['slug']}.webp", "WEBP", quality=80, method=6)
            bilan["ok"] += 1
        except Exception as e:  # noqa: BLE001
            bilan["ko"].append(f"{f['slug']}: {str(e)[:160]}")


async def main():
    await init_db()
    sem = asyncio.Semaphore(4)
    bilan = {"ok": 0, "ko": []}
    await asyncio.gather(*(une(f, sem, bilan) for f in a_faire))
    import sqlite3
    dep = sqlite3.connect(str(pathlib.Path(tmp, "t.db"))).execute(
        "SELECT COUNT(*), ROUND(SUM(estime_usd), 4) FROM depenses").fetchone()
    print(f"faites : {bilan['ok']} ; échecs : {len(bilan['ko'])} ; dépenses notées : {dep}")
    for k in bilan["ko"]:
        print("  ", k)


asyncio.run(main())
