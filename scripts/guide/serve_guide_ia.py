# Backend de PREUVE du guide pour la génération IA (t193, G11) : comme serve_guide.py (code de ce dépôt, dossier de
# données jetable, port 8809 par défaut, jamais le 8765), mais avec une clé fal FACTICE et les tirs SIMULÉS :
#   - la génération d'image (image_providers.generate, _flux_generate de routes) rend une image fabriquée ici ;
#   - le détourage fal (matte_service : _upload, _fal_subscribe, _download) rend l'image source au fond effacé ;
#   - tout appel fal_client ou POST httpx sortant (hors 127.0.0.1) est INTERCEPTÉ, journalisé et refusé.
# Aucune dépense n'est possible : il n'y a pas de vraie clé, et rien ne sort. Les autres clés restent vides, si bien
# que les sélecteurs montrent aussi des options « clé … à ajouter » (OpenAI, Gemini…), choisissables, refusées au
# lancement. Données de démonstration ensuite : semer_vectorlab.py, semer_atelier.py, semer_sons.py, semer_videos.py.
import os
import pathlib
import sys
import tempfile
import uuid

WT = pathlib.Path(__file__).resolve().parents[2] / "backend"
d = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_ia_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(d / "images")
os.environ["OUTPUTS_FOLDER"] = str(d / "outputs")
for k in ("ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MESHY_API_KEY",
          "GEMINI_API_KEY", "FIGMA_TOKEN", "TELEGRAM_BOT_TOKEN", "DECART_API_KEY"):
    os.environ[k] = ""
os.environ["FAL_KEY"] = "guide-factice"
IMG = d / "images"
IMG.mkdir(parents=True, exist_ok=True)
_pcv = __import__("json").loads((WT.parent / "vendor" / "photocraft.json").read_text("utf-8"))["version"]  # t250 : version épinglée
_pc = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "DeepotusVideoGen" / "vendor" / f"photocraft-{_pcv}"
for _cli in sorted(_pc.rglob("photocraft-cli.exe")) if _pc.is_dir() else []:
    os.environ.setdefault("PHOTOCRAFT_CLI", str(_cli))
    break
sys.path.insert(0, str(WT))
os.chdir(WT)
print("donnees de preuve :", d, flush=True)

from PIL import Image, ImageDraw  # noqa: E402

im = Image.new("RGB", (1080, 1920), (16, 20, 34))
dr = ImageDraw.Draw(im)
dr.ellipse((290, 560, 790, 1060), fill=(240, 180, 41))
dr.rectangle((0, 1500, 1080, 1920), fill=(40, 90, 120))
im.save(IMG / "demo-affiche.png")

# ── aucun tir réel ──
import fal_client  # noqa: E402
import httpx  # noqa: E402


def _bloque(nom):
    async def f(*a, **k):
        print(f"!!! INTERCEPTÉ {nom}", flush=True)
        raise RuntimeError(f"preuve du guide : appel payant {nom} intercepté")
    return f


for _n in ("subscribe_async", "submit_async", "upload_file_async", "run_async"):
    if hasattr(fal_client, _n):
        setattr(fal_client, _n, _bloque(f"fal_client.{_n}"))
_post = httpx.AsyncClient.post


async def _post_garde(self, url, *a, **k):
    if "127.0.0.1" not in str(url) and "localhost" not in str(url):
        print(f"!!! INTERCEPTÉ POST {url}", flush=True)
        raise RuntimeError("preuve du guide : POST sortant intercepté")
    return await _post(self, url, *a, **k)


httpx.AsyncClient.post = _post_garde

# ── coutures : génération et détourage simulés ──
from app.services import matte_service as MT, image_providers as IP  # noqa: E402
from app.api import routes as R  # noqa: E402

COULEURS = [(232, 120, 40, 255), (70, 130, 220, 255), (200, 60, 140, 255)]


def _sujet(nom, couleur):
    """un « chat » plein sur fond vert uni : le détourage simulé efface le fond"""
    s = Image.new("RGBA", (1024, 1024), (40, 160, 90, 255))
    g = ImageDraw.Draw(s)
    g.ellipse((300, 260, 724, 820), fill=couleur)
    g.polygon([(330, 330), (400, 120), (470, 300)], fill=couleur)
    g.polygon([(554, 300), (624, 120), (694, 330)], fill=couleur)
    s.save(IMG / nom)
    return nom


async def _faux_generate(provider, prompt, size, n=1, **k):
    print(f"[couture] generate {provider} {size} {prompt!r}", flush=True)
    i = len(list(IMG.glob("gen_guide_*.png")))
    return {"images": [_sujet(f"gen_guide_{i}_{uuid.uuid4().hex[:6]}.png", COULEURS[i % 3])], "seed": None}


async def _faux_flux(prompt, size, n, seed=None, **k):
    return await _faux_generate("flux", prompt, size, n)


DERNIER = {}


async def _upload(path, *a, **k):
    DERNIER["src"] = pathlib.Path(path)
    return "https://guide.invalid/" + pathlib.Path(path).name


async def _fal_subscribe(endpoint, arguments, *a, **k):
    print(f"[couture] {endpoint}", flush=True)
    if "sam-3" in endpoint and "3d" in endpoint:
        # SAM 3 objets 3D : deux objets (un personnage debout, une table), métadonnées imbriquées comme fal
        meta = [{"object_index": 0, "rotation": [[0, 0, 0, 1]], "translation": [[-0.4, 0, 0]], "scale": [[1, 1, 1]]},
                {"object_index": 1, "rotation": [[0, 0.3827, 0, 0.9239]], "translation": [[0.8, 0, -0.6]],
                 "scale": [[1, 1, 1]]}]
        return {"model_glb": {"url": "https://guide.invalid/scene.glb"},
                "individual_glbs": [{"url": "https://guide.invalid/o0.glb"}, {"url": "https://guide.invalid/o1.glb"}],
                "metadata": meta}
    return {"image": {"url": "https://guide.invalid/detoure.png"}}


def _boite(w, h, p):
    from app.services import print3d
    t = [((0, 0, 0), (w, 0, 0), (w, h, 0)), ((0, 0, 0), (w, h, 0), (0, h, 0)),
         ((0, 0, p), (w, h, p), (w, 0, p)), ((0, 0, p), (0, h, p), (w, h, p)),
         ((0, 0, 0), (0, h, 0), (0, h, p)), ((0, 0, 0), (0, h, p), (0, 0, p)),
         ((w, 0, 0), (w, h, p), (w, h, 0)), ((w, 0, 0), (w, 0, p), (w, h, p)),
         ((0, h, 0), (w, h, 0), (w, h, p)), ((0, h, 0), (w, h, p), (0, h, p)),
         ((0, 0, 0), (w, 0, p), (w, 0, 0)), ((0, 0, 0), (0, 0, p), (w, 0, p))]
    return print3d.glb_de_triangles(t)


async def _download(url, dest, *a, **k):
    if str(url).endswith(".glb"):
        pathlib.Path(dest).write_bytes(_boite(0.5, 1.7, 0.4) if str(url).endswith("o0.glb") else _boite(1.2, 0.75, 0.8))
        return
    s = Image.open(DERNIER["src"]).convert("RGBA")
    fond = s.getpixel((5, 5))
    s.putdata([(0, 0, 0, 0) if abs(p[0] - fond[0]) + abs(p[1] - fond[1]) + abs(p[2] - fond[2]) < 60 else p
               for p in s.getdata()])
    s.save(dest, "PNG")


IP.generate = _faux_generate
R._flux_generate = _faux_flux
MT._upload, MT._fal_subscribe, MT._download = _upload, _fal_subscribe, _download


# ── un chapitre de démonstration du storyboard : aucune route gratuite ne pose une image de production, elle est
# écrite ici dans la base JETABLE (plan 1 : image de production ; plan 2 : croquis + bornes du Plateau) ──
def _vignette(nom, ciel, sol, texte):
    s = Image.new("RGB", (960, 540), ciel)
    g = ImageDraw.Draw(s)
    g.rectangle((0, 380, 960, 540), fill=sol)
    g.rectangle((610, 300, 820, 330), fill=(120, 80, 50))                 # la table
    g.rectangle((630, 330, 645, 400), fill=(120, 80, 50))
    g.rectangle((785, 330, 800, 400), fill=(120, 80, 50))
    g.ellipse((330, 150, 390, 210), fill=(230, 200, 170))                 # Ada
    g.rectangle((325, 210, 395, 380), fill=(60, 90, 160))
    g.rectangle((700, 270, 730, 300), fill=(250, 220, 120))               # la lampe
    g.text((24, 20), texte, fill=(255, 255, 255))
    s.save(IMG / nom)


_vignette("prod_plan1.png", (70, 80, 120), (60, 50, 45), "")
_vignette("croquis_plan2.png", (200, 200, 200), (150, 150, 150), "")
_vignette("plateau_debut_plan2.png", (40, 60, 90), (50, 60, 50), "")
_vignette("plateau_fin_plan2.png", (90, 70, 60), (50, 60, 50), "")


async def _semer_chapitre():
    import asyncio  # noqa: F401
    import json
    from app.services import storage as S
    await S.init_db()
    async with S.async_session_factory() as s:
        ch = S.Chapter(id=str(uuid.uuid4()), title="Le phare de Brume-Noire")
        ada = S.BibleEntity(id=str(uuid.uuid4()), kind="character", name="Ada", description="gardienne du phare")
        table = S.BibleEntity(id=str(uuid.uuid4()), kind="object", name="table", description="table en bois")
        s.add_all([ch, ada, table])
        s.add(S.Shot(id=str(uuid.uuid4()), chapter_id=ch.id, idx=0, action="Ada pose la lampe sur la table.",
                     entities=json.dumps([ada.id, table.id]), shot_type="medium", duration_s=5.0,
                     image="prod_plan1.png"))
        s.add(S.Shot(id=str(uuid.uuid4()), chapter_id=ch.id, idx=1, action="Ada se retourne vers la mer.",
                     entities=json.dumps([ada.id]), shot_type="wide", duration_s=5.0, sketch_image="croquis_plan2.png",
                     keyframe_image="plateau_debut_plan2.png", keyframe_end="plateau_fin_plan2.png",
                     motion_prompt="slow push-in toward Ada, she turns to the sea"))
        await s.commit()
    print("chapitre de démonstration :", ch.id, flush=True)


import asyncio  # noqa: E402

asyncio.run(_semer_chapitre())

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8809")), log_level="warning")
