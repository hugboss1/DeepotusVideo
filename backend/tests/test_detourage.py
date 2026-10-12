# -*- coding: utf-8 -*-
"""t186 (G4, tâche A) — le détourage : UN registre (`detourage.REGISTRE`, 15 entrées, schémas fal relus le
12/10/2026), le catalogue (natures `detourage_image` / `detourage_video`), le devis (`kind: detourage`) et les
sites qui détourent (/images/process, /matte, /matte-models, sprites, Card Forge, Studio3D, décor Avatar).

Ce que le banc tient :
  [0] requêtes PURES (`build_request`) : SAM 3 (endpoint, prompt, apply_mask) ; Bria vidéo v3 (Transparent,
      mov_proresks, video_url) ; BiRefNet v2 image en « General Use (Heavy) » ; un modèle à sujet SANS sujet ->
      ValueError ; chaque entrée vidéo envoie `video_url` et jamais `image_url` (et inversement) ; Bria RMBG
      n'envoie PAS `prompt` (facturé 0,03 au lieu de 0,018) ; un modèle local -> ValueError ;
  [1] catalogue : local-rembg disponible sans clé (voie local) ; 10 modèles image, 5 vidéo, dans l'ordre du
      registre ; sans FAL_KEY les modèles fal restent LISTÉS (dispo False, cle FAL_KEY) ; `prompt` vrai pour
      sam3-sujet / bria-objet / sam31-video ; note « a_mesurer » pour pixelcut / feynobg / bria-objet /
      birefnet-v2, jamais pour une voie locale ;
  [2] /images/process remove-bg : `modele=pixelcut` passe par `detourage.detourer_image` (espion) ; sans modele,
      `method:"api"` reste fal rembg (témoin) ; sans FAL_KEY -> 503 nommant FAL_KEY et ZÉRO ligne `depenses` ;
      sam3-sujet sans sujet -> 400 ; modèle inconnu -> 400 ; témoin : ideogram-rmbg écrit UNE ligne `depenses` ;
      la VRAIE couture `detourer_image` (seams de matte_service remplacés) range un PNG ; local-chroma en vrai ;
  [3] devis : ideogram x3 = 0,03 ; bria-video-v3 10 s = 0,5 ; veed 61 images = 3 tranches x 0,012 ; sam31
      33 images = 3 x 0,01 ; pixelcut -> 0 « à mesurer » ; la branche `matte` MORTE a disparu (une seule
      `kind == "matte"` dans pricing.py) et le devis matte est inchangé ;
  [4] /matte-models : >= 5 modèles vidéo, anciens champs gardés (id, label, default, usd_note) + nouveaux ;
      /matte model=bria-video-v3 construit la bonne requête (espion _fal_subscribe), sortie .mov servie ;
      sam31-video sans sujet -> 400 ; veed -> .webm confiné et servi ; ancienne clé `general` OK ; sans clé 503
      avant la garde ;
  [5] la sortie webm (VP9 avec alpha) se LIT avec son alpha : décodeur libvpx-vp9 imposé (matte_service.
      decodeur_entree) — preuve par pixels sur un vrai fichier ; Montage, vignette du rack et décor l'emploient ;
  [6] sites : sprites (`modele` dans normalize_opts, 400 pour un id inconnu, 503 sans clé, coût du job), Card
      Forge /rembg (`modele` : 503 sans clé, 400 sans sujet, détourage par le registre), Studio3D vues
      (`modele`), décor Avatar (`modele` vidéo du registre + aperçu par son jumeau image).
  [8] écrans (tâche B) : les six sites — Spritelab, Studio3D (vues), Card Forge (capture), décor Avatar (DzModelesIA,
      clé dz_detour_<site>, envoi de modele et sujet, défaut d'avant gardé, aucune option grisée sans clé), rack VFX
      (vfxrack, bloc du bundle rafraîchi) et nœud Studio « Détourage » (maillon encartsia), les aides exécutées sous node.

AUCUN appel réseau réel : les fal_client.* sont des gardes qui COMPTENT ; les seams de matte_service sont des
enregistreurs.
Run (depuis backend/) : & $PY tests/test_detourage.py"""
import asyncio
import inspect
import io
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzdetour_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
os.environ["FAL_KEY"] = "test-key"
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY"):
    os.environ[_k] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable")
    sys.exit(0)

from loguru import logger  # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


import fal_client  # noqa: E402

RESEAU = {"n": 0, "noms": []}


def _garde(nom):
    async def _refus(*a, **k):
        RESEAU["n"] += 1
        RESEAU["noms"].append(nom)
        raise RuntimeError(f"GARDE RESEAU : {nom} appelé dans un banc")
    return _refus


for _nom in ("submit_async", "subscribe_async", "run_async", "upload_file_async", "upload_async",
             "upload_image_async"):
    setattr(fal_client, _nom, _garde(_nom))

from PIL import Image  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import detourage as DT, catalogue_ia as CI, pricing as P, matte_service as MT  # noqa: E402
from app.services.storage import init_db, async_session_factory, JobRecord  # noqa: E402
from app.api import routes as R  # noqa: E402

W = pathlib.Path(_tmp)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())


def n_depenses():
    con = sqlite3.connect(str(W / "t.db"))
    try:
        return con.execute("SELECT COUNT(*) FROM depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        con.close()


def png_bytes(rgba=(255, 0, 0, 255), size=(32, 32)):
    b = io.BytesIO()
    Image.new("RGBA", size, rgba).save(b, "PNG")
    return b.getvalue()


# ── seams de matte_service : des enregistreurs ──────────────────────────────
SEAMS = {"up": [], "sub": [], "dl": []}
REPONSE = {"v": None}
FAKE = {}


async def _up(p):
    SEAMS["up"].append(pathlib.Path(p).name)
    return "http://fal.test/in"


async def _sub(endpoint, arguments):
    SEAMS["sub"].append((endpoint, dict(arguments)))
    if REPONSE["v"] is not None:
        return REPONSE["v"]
    if "video_url" in arguments:
        return {"video": {"url": "http://fal.test/out.vid"}}
    return {"image": {"url": "http://fal.test/out.png"}}


async def _dl(url, dest):
    SEAMS["dl"].append(pathlib.Path(dest).name)
    dest = pathlib.Path(dest)
    if dest.suffix in (".mov", ".webm") and FAKE.get(dest.suffix):
        shutil.copy2(FAKE[dest.suffix], dest)
    else:
        # un sujet au centre, fond transparent : une vraie couche détourée
        im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        for x in range(16, 48):
            for y in range(16, 48):
                im.putpixel((x, y), (0, 255, 0, 255))
        b = io.BytesIO()
        im.save(b, "PNG")
        dest.write_bytes(b.getvalue())


MT._upload, MT._fal_subscribe, MT._download = _up, _sub, _dl


def raz():
    for v in SEAMS.values():
        v.clear()
    REPONSE["v"] = None


# ════════════════════════════════════════════════════════════════════════════
print("\n[0] requêtes pures")
ids = list(DT.REGISTRE)
check("le registre compte 15 entrées", len(ids) == 15, str(ids))
ep, a = DT.build_request("sam3-sujet", "http://u/i.png", "le chat")
check("sam3-sujet : endpoint fal-ai/sam-3/image, prompt, apply_mask True, png",
      ep == "fal-ai/sam-3/image" and a.get("prompt") == "le chat" and a.get("apply_mask") is True
      and a.get("output_format") == "png" and a.get("image_url") == "http://u/i.png", str((ep, a)))
ep, a = DT.build_request("bria-video-v3", "http://u/v.mp4")
check("bria-video-v3 : Transparent, mov_proresks, preserve_audio, video_url",
      ep == "bria/video/background-removal/v3" and a.get("background_color") == "Transparent"
      and a.get("output_container_and_codec") == "mov_proresks" and a.get("preserve_audio") is True
      and a.get("video_url") == "http://u/v.mp4", str((ep, a)))
ep, a = DT.build_request("birefnet-v2", "http://u/i.png")
check("birefnet-v2 : modèle par défaut « General Use (Heavy) », 2048, refine, png",
      ep == "fal-ai/birefnet/v2" and a.get("model") == "General Use (Heavy)"
      and a.get("operating_resolution") == "2048x2048" and a.get("refine_foreground") is True
      and a.get("output_format") == "png", str(a))
for mid in ("sam3-sujet", "bria-objet", "sam31-video"):
    refus = []
    for vide in (None, "", "   "):
        try:
            DT.build_request(mid, "http://u/x", vide)
            refus.append(None)
        except ValueError as e:
            refus.append(str(e))
    check(f"{mid} sans sujet (None, vide, blancs) -> ValueError qui demande le sujet",
          all(r and "sujet" in r for r in refus), str(refus))
for mid, e in DT.REGISTRE.items():
    if e["voie"] == "local":
        continue
    _, a = DT.build_request(mid, "http://u/x", "sujet" if e["prompt"] else None)
    if e["nature"] == "detourage_video":
        check(f"{mid} : video_url, jamais image_url", "video_url" in a and "image_url" not in a, str(a))
    else:
        check(f"{mid} : image_url, jamais video_url", "image_url" in a and "video_url" not in a, str(a))
_, a = DT.build_request("bria-rmbg", "http://u/i.png", "un chat")
check("bria-rmbg n'envoie PAS prompt (même si on lui en donne un)", list(a) == ["image_url"], str(a))
check("bria-rmbg vise fal-ai/bria/background/remove",
      DT.build_request("bria-rmbg", "http://u")[0] == "fal-ai/bria/background/remove")
check("pixelcut : output_format rgba", DT.build_request("pixelcut", "http://u")[1].get("output_format") == "rgba")
check("ideogram / feynobg / rembg-fal : image_url seule",
      all(list(DT.build_request(m, "http://u")[1]) == ["image_url"] for m in ("ideogram-rmbg", "feynobg", "rembg-fal")))
_, a = DT.build_request("veed-video-rapide", "http://u")
check("veed : output_codec vp9, réglages facultatifs laissés au défaut",
      a.get("output_codec") == "vp9" and "subject_is_person" not in a and "refine_foreground_edges" not in a, str(a))
_, a = DT.build_request("pixelcut-video", "http://u")
check("pixelcut-video : background transparent, webm_vp9",
      a.get("background") == "transparent" and a.get("output_format") == "webm_vp9", str(a))
_, a = DT.build_request("sam31-video", "http://u", "la danseuse")
check("sam31-video : prompt, apply_mask, VP9 (.webm)",
      a.get("prompt") == "la danseuse" and a.get("apply_mask") is True and a.get("video_output_type") == "VP9 (.webm)",
      str(a))
_, a = DT.build_request("bria-objet", "http://u", "la tasse")
check("bria-objet : prompt, remove_background True, autocrop False",
      a.get("prompt") == "la tasse" and a.get("remove_background") is True and a.get("autocrop") is False, str(a))
ep, a = DT.build_request("birefnet-v2-video", "http://u")
check("birefnet-v2-video = les ARGS_FIXED du matte + model « General Use (Light) »",
      ep == MT.ENDPOINT and a == dict(MT.ARGS_FIXED, video_url="http://u", model="General Use (Light)"), str(a))
for mid in ("local-rembg", "local-chroma"):
    try:
        DT.build_request(mid, "http://u")
        check(f"{mid} -> ValueError (local)", False)
    except ValueError:
        check(f"{mid} -> ValueError (local : aucune requête fal)", True)
try:
    DT.build_request("zzz", "http://u")
    check("modèle inconnu -> ValueError", False)
except ValueError:
    check("modèle inconnu -> ValueError", True)
check("ordre : les locales d'abord", ids[:2] == ["local-rembg", "local-chroma"], str(ids))
check("libellés courts posés",
      DT.REGISTRE["sam3-sujet"]["label"] == "SAM 3 — garder un sujet nommé"
      and DT.REGISTRE["local-chroma"]["label"] == "Fond uni / chroma (local)"
      and DT.REGISTRE["bria-video-v3"]["label"] == "Bria VRMBG 3.0", "")

# ════════════════════════════════════════════════════════════════════════════
print("\n[1] catalogue")
check("natures inscrites", {"detourage_image", "detourage_video"} <= set(CI.natures()), str(CI.natures()))
img = CI.lister("detourage_image")
vid = CI.lister("detourage_video")
ix = {e["id"]: e for e in img}
vx = {e["id"]: e for e in vid}
check("local-rembg : dispo sans clé, voie local", ix["local-rembg"]["dispo"] is True
      and ix["local-rembg"]["voie"] == "local" and ix["local-rembg"]["cle"] is None, str(ix["local-rembg"]))
check(">= 9 modèles image (10)", len(img) == 10, str(len(img)))
check(">= 5 modèles vidéo", len(vid) == 5, str(len(vid)))
check("ordre du registre gardé", [e["id"] for e in img + vid] == ids, str([e["id"] for e in img + vid]))
check("champs : id, label, voie, usd, unite, jumeau None, note, prompt, nature, cle, dispo",
      all({"id", "label", "voie", "usd", "unite", "jumeau", "note", "prompt", "nature", "cle", "dispo"} <= set(e)
          and e["jumeau"] is None for e in img + vid), str(img[0]))
check("unités : image / s / 30 images / 16 images",
      ix["ideogram-rmbg"]["unite"] == "image" and vx["bria-video-v3"]["unite"] == "s"
      and vx["veed-video-rapide"]["unite"] == "30 images" and vx["sam31-video"]["unite"] == "16 images", "")
settings.FAL_KEY = ""
img0 = {e["id"]: e for e in CI.lister("detourage_image")}
vid0 = {e["id"]: e for e in CI.lister("detourage_video")}
settings.FAL_KEY = "test-key"
fal0 = [e for e in list(img0.values()) + list(vid0.values()) if e["voie"] == "fal"]
check("sans FAL_KEY : les 13 modèles fal restent LISTÉS, dispo False, cle FAL_KEY",
      len(fal0) == 13 and all(e["dispo"] is False and e["cle"] == "FAL_KEY" for e in fal0), str(len(fal0)))
check("sans FAL_KEY : les locales restent disponibles", img0["local-chroma"]["dispo"] is True)
check("prompt vrai pour sam3-sujet / bria-objet / sam31-video, faux ailleurs",
      {e["id"] for e in img + vid if e["prompt"]} == {"sam3-sujet", "bria-objet", "sam31-video"}, "")
check("note a_mesurer : pixelcut, feynobg, bria-objet, birefnet-v2",
      all(ix[i]["note"] == CI.NOTE_A_MESURER and ix[i]["usd"] == 0.0
          for i in ("pixelcut", "feynobg", "bria-objet", "birefnet-v2")), "")
check("aucune note pour une voie locale (gratuite, pas « à mesurer »)",
      ix["local-rembg"]["note"] == "" and ix["local-chroma"]["note"] == "" and ix["local-rembg"]["usd"] == 0.0, "")
check("prix connus : bria-rmbg 0,018, ideogram 0,01, sam3 0,005, rembg-fal 0,003",
      ix["bria-rmbg"]["usd"] == 0.018 and ix["ideogram-rmbg"]["usd"] == 0.01 and ix["sam3-sujet"]["usd"] == 0.005
      and ix["rembg-fal"]["usd"] == 0.003 and ix["ideogram-rmbg"]["note"] == "", "")
check("vidéo : bria 0,05/s, veed 0,012/30, pixelcut 0,022/30, sam31 0,01/16 ; birefnet à mesurer",
      vx["bria-video-v3"]["usd"] == 0.05 and vx["veed-video-rapide"]["usd"] == 0.012
      and vx["pixelcut-video"]["usd"] == 0.022 and vx["sam31-video"]["usd"] == 0.01
      and vx["birefnet-v2-video"]["note"] == CI.NOTE_A_MESURER, "")


async def _req(meth, path, body=None, params=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        if meth == "GET":
            return await c.get("/api" + path, params=params)
        return await c.post("/api" + path, json=body)


def call(meth, path, body=None, params=None):
    r = loop.run_until_complete(_req(meth, path, body, params))
    try:
        js = r.json()
    except Exception:  # noqa: BLE001
        js = r.text
    return r.status_code, js


st, js = call("GET", "/ia/catalogue", params={"nature": "detourage_video"})
check("GET /ia/catalogue?nature=detourage_video : 5 entrées", st == 200 and len(js["modeles"]) == 5, str(js)[:200])

# ════════════════════════════════════════════════════════════════════════════
print("\n[2] /images/process remove-bg")
SRC = "source.png"
Image.new("RGB", (64, 64), (10, 200, 30)).save(settings.images_path / SRC)
ESPION = []
_vrai_detourer = DT.detourer_image


async def _espion(mid, chemin, prompt=None, dossier=None):
    ESPION.append((mid, pathlib.Path(chemin).name, prompt))
    nom = "gen_espion.png"
    (pathlib.Path(dossier or settings.images_path) / nom).write_bytes(png_bytes())
    return nom


DT.detourer_image = _espion
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "pixelcut"})
check("modele=pixelcut : passe par detourage.detourer_image (espion), image rendue",
      st == 200 and ESPION == [("pixelcut", SRC, None)] and js.get("images") == ["gen_espion.png"], f"{st} {js}")
check("aucun appel réseau", RESEAU["n"] == 0, str(RESEAU))

# témoin : sans modele, method api = fal rembg (chemin d'avant, inchangé)
from app.services import fal_service as FS  # noqa: E402
from app.services import image_providers as IPm  # noqa: E402
_vrai_up_img = inspect.getattr_static(FS.FalSeedanceClient, "upload_image")
_vrai_sub = fal_client.subscribe_async
_vrai_dl_ip = IPm._download
TEMOIN = []


async def _up_img(p):
    return "http://fal.test/up.png"


async def _sub_temoin(model, arguments=None, **kw):
    TEMOIN.append((model, arguments))
    return {"image": {"url": "http://fal.test/out.png"}}


async def _dl_ip(urls, *a, **k):
    nom = "gen_temoin.png"
    (settings.images_path / nom).write_bytes(png_bytes())
    return [nom]


FS.FalSeedanceClient.upload_image = staticmethod(_up_img)
fal_client.subscribe_async = _sub_temoin
IPm._download = _dl_ip
ESPION.clear()
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "method": "api"})
check("TÉMOIN sans modele : method api -> fal-ai/imageutils/rembg (chemin d'avant), jamais l'espion",
      st == 200 and [t[0] for t in TEMOIN] == ["fal-ai/imageutils/rembg"] and ESPION == [], f"{st} {js} {TEMOIN}")
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "method": "local"})
check("TÉMOIN sans modele : method local sans rembg -> 400 d'avant (« rembg »), jamais l'espion",
      st == 400 and "rembg" in str(js) and ESPION == [], f"{st} {js}")
FS.FalSeedanceClient.upload_image = _vrai_up_img
fal_client.subscribe_async = _vrai_sub
IPm._download = _vrai_dl_ip

d0 = n_depenses()
settings.FAL_KEY = ""
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "pixelcut"})
check("sans FAL_KEY : 503 qui nomme FAL_KEY", st == 503 and "FAL_KEY" in str(js), f"{st} {js}")
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "sam3-sujet"})
check("ORDRE : sam3-sujet SANS sujet ET sans clé -> 503 FAL_KEY (la clé avant le sujet)", st == 503
      and "FAL_KEY" in str(js), f"{st} {js}")
check("sans FAL_KEY : ZÉRO ligne depenses, espion jamais appelé", n_depenses() == d0 and ESPION == [],
      f"{d0} -> {n_depenses()} {ESPION}")
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "local-chroma"})
check("sans FAL_KEY : une voie LOCALE part quand même (aucune clé exigée)", st == 200 and bool(ESPION)
      and ESPION[-1][0] == "local-chroma", f"{st} {js}")
settings.FAL_KEY = "test-key"
ESPION.clear()
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "sam3-sujet"})
check("sam3-sujet sans sujet -> 400, rien de lancé, zéro dépense", st == 400 and ESPION == [] and n_depenses() == d0,
      f"{st} {js}")
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "sam3-sujet",
                                          "sujet": "le carré"})
check("sam3-sujet AVEC sujet : transmis à detourer_image", st == 200 and ESPION == [("sam3-sujet", SRC, "le carré")],
      f"{st} {js} {ESPION}")
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "zzz"})
check("modèle inconnu -> 400", st == 400, f"{st} {js}")
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "bria-video-v3"})
check("un modèle VIDÉO refusé sur une image -> 400", st == 400, f"{st} {js}")
d1 = n_depenses()
st, js = call("POST", "/images/process", {"op": "remove-bg", "filename": SRC, "modele": "ideogram-rmbg"})
check("TÉMOIN : ideogram-rmbg (0,01 $) passe la garde et écrit UNE ligne depenses", st == 200
      and n_depenses() == d1 + 1, f"{st} {d1} -> {n_depenses()}")
DT.detourer_image = _vrai_detourer

# la vraie couture, seams remplacés
raz()
nom = loop.run_until_complete(DT.detourer_image("pixelcut", settings.images_path / SRC))
check("detourer_image(pixelcut) : envoi, requête pixelcut, PNG rangé dans les images",
      SEAMS["up"] == [SRC] and SEAMS["sub"] == [("pixelcut/background-removal",
                                                 {"image_url": "http://fal.test/in", "output_format": "rgba"})]
      and (settings.images_path / nom).is_file() and nom.endswith(".png"), f"{nom} {SEAMS}")
check("le PNG rangé garde son alpha", Image.open(settings.images_path / nom).mode == "RGBA")
raz()
REPONSE["v"] = {"images": [{"url": "http://fal.test/o.png"}]}
nom = loop.run_until_complete(DT.detourer_image("ideogram-rmbg", settings.images_path / SRC))
check("réponse en `images[]` acceptée aussi", (settings.images_path / nom).is_file(), nom)
raz()
dd = W / "ailleurs"
dd.mkdir()
nom = loop.run_until_complete(DT.detourer_image("bria-objet", settings.images_path / SRC, "la tasse", dossier=dd))
check("dossier= : le PNG va où on le demande, sujet transmis",
      (dd / nom).is_file() and SEAMS["sub"][-1][1].get("prompt") == "la tasse", str(SEAMS))
raz()
REPONSE["v"] = {"rien": 1}
try:
    loop.run_until_complete(DT.detourer_image("feynobg", settings.images_path / SRC))
    check("réponse sans image -> RuntimeError nommée", False)
except RuntimeError as e:
    check("réponse sans image -> RuntimeError nommée", "aucune image" in str(e), str(e))
raz()
try:
    loop.run_until_complete(DT.detourer_image("sam31-video", settings.images_path / SRC, "x"))
    check("detourer_image refuse un modèle vidéo", False)
except ValueError:
    check("detourer_image refuse un modèle vidéo (ValueError)", True)
# local-chroma en vrai : un carré rouge sur fond vert uni
im = Image.new("RGB", (80, 80), (0, 200, 0))
for x in range(25, 55):
    for y in range(25, 55):
        im.putpixel((x, y), (220, 20, 20))
im.save(settings.images_path / "chroma.png")
nom = loop.run_until_complete(DT.detourer_image("local-chroma", settings.images_path / "chroma.png"))
o = Image.open(settings.images_path / nom).convert("RGBA")
check("local-chroma en vrai : fond transparent, sujet opaque, aucun envoi",
      o.getpixel((2, 2))[3] == 0 and o.getpixel((40, 40))[3] == 255 and SEAMS["up"] == [], str(o.getpixel((2, 2))))
if "rembg" not in sys.modules:
    try:
        loop.run_until_complete(DT.detourer_image("local-rembg", settings.images_path / SRC))
        check("local-rembg sans rembg installé -> ValueError nommée (400 côté route)", False)
    except ValueError as e:
        check("local-rembg sans rembg installé -> ValueError nommée (400 côté route)", "rembg" in str(e), str(e))

# ════════════════════════════════════════════════════════════════════════════
print("\n[3] devis")


def tot(op):
    return P.estimate(op)["total_usd"]


check("ideogram x3 = 0,03", abs(tot({"kind": "detourage", "modele": "ideogram-rmbg", "images": 3}) - 0.03) < 1e-9)
check("bria-video-v3 10 s = 0,5", abs(tot({"kind": "detourage", "modele": "bria-video-v3", "secondes": 10}) - 0.5) < 1e-9)
check("veed 61 images = 3 tranches x 0,012",
      abs(tot({"kind": "detourage", "modele": "veed-video-rapide", "images_video": 61}) - 0.036) < 1e-9)
check("sam31 33 images = 3 x 0,01",
      abs(tot({"kind": "detourage", "modele": "sam31-video", "images_video": 33}) - 0.03) < 1e-9)
check("veed 2 s sans images_video : fps 30 par défaut -> 60 images -> 2 tranches",
      abs(tot({"kind": "detourage", "modele": "veed-video-rapide", "secondes": 2}) - 0.024) < 1e-9)
check("pixelcut-video 2 s à 24 i/s -> 48 images -> 2 tranches x 0,022",
      abs(tot({"kind": "detourage", "modele": "pixelcut-video", "secondes": 2, "fps": 24}) - 0.044) < 1e-9)
e = P.estimate({"kind": "detourage", "modele": "pixelcut", "images": 2})
check("pixelcut -> 0 avec « à mesurer » dans le libellé", e["total_usd"] == 0.0
      and "à mesurer" in e["breakdown"][0]["label"] and e["breakdown"][0]["label"].startswith("Pixelcut"), str(e))
e = P.estimate({"kind": "detourage", "modele": "local-rembg", "images": 4})
check("voie locale : ligne 0 $ du fournisseur « local », sans « à mesurer »",
      e["total_usd"] == 0.0 and e["breakdown"][0]["provider"] == "local"
      and "mesurer" not in e["breakdown"][0]["label"], str(e))
e = P.estimate({"kind": "detourage", "modele": "bria-rmbg"})
check("ligne nommée par le libellé du registre, une image par défaut",
      e["breakdown"][0]["label"].startswith("Bria RMBG 2.0") and abs(e["total_usd"] - 0.018) < 1e-9, str(e))
e = P.estimate({"kind": "detourage", "modele": "zzz"})
check("modèle inconnu : ligne 0 $ qui le DIT (non chiffré)", e["total_usd"] == 0.0
      and "inconnu" in e["breakdown"][0]["label"], str(e))
src_pr = pathlib.Path(P.__file__).read_text(encoding="utf-8")
check("branche matte MORTE supprimée : une seule `kind == \"matte\"`", src_pr.count('kind == "matte"') == 1,
      str(src_pr.count('kind == "matte"')))
e = P.estimate({"kind": "matte", "duration_s": 12})
check("devis matte inchangé (première branche)", e["breakdown"] == [
    {"provider": "fal", "label": "Détourage vidéo (BiRefNet) — prix à mesurer", "units": 12.0, "unit": "s", "usd": 0.0}],
      str(e))
for k in ("bria_rmbg_usd", "pixelcut_rmbg_usd", "ideogram_rmbg_usd", "feynobg_usd", "sam3_image_usd",
          "bria_objet_usd", "bria_video_usd_per_s", "veed_rmbg_usd_per_30f", "pixelcut_video_usd_per_30f",
          "sam31_video_usd_per_16f"):
    check(f"DEFAULTS porte {k}", k in P.DEFAULTS)
check("chaque entrée fal du registre a sa clé de prix dans DEFAULTS",
      all(e["prix"] in P.DEFAULTS for e in DT.REGISTRE.values() if e["voie"] == "fal"), "")

# ════════════════════════════════════════════════════════════════════════════
print("\n[4] /matte-models et /matte")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
                "-pix_fmt", "yuv420p", str(W / "clip.mp4")], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red@0.5:size=64x64:rate=10:duration=1",
                "-vf", "format=yuva444p10le", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                str(W / "fake.mov")], check=True)
# un webm VP9 AVEC alpha : moitié gauche opaque rouge, moitié droite transparente
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=red:size=64x64:rate=10:duration=1",
                "-vf", "format=rgba,geq=r='255':g='0':b='0':a='if(lt(X,32),255,0)'",
                "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", str(W / "fake.webm")],
               check=True)
FAKE[".mov"], FAKE[".webm"] = W / "fake.mov", W / "fake.webm"


async def _jobs():
    async with async_session_factory() as s:
        s.add(JobRecord(id="job-d1", status="done", progress=100, image_filename="x",
                        final_video_path=str(W / "clip.mp4")))
        await s.commit()


loop.run_until_complete(_jobs())
st, mm = call("GET", "/matte-models")
mods = mm.get("models") or []
check(">= 5 modèles vidéo listés", st == 200 and len(mods) >= 5, str(mm)[:300])
check("anciens champs gardés : id/label des trois clés en tête, default general, usd_note",
      [m["id"] for m in mods[:3]] == list(MT.MATTE_MODELS) and mm.get("default") == "general"
      and all(m["label"] == MT.MATTE_MODELS[m["id"]]["label"] for m in mods[:3]) and "mesurer" in mm.get("usd_note", ""),
      str(mods[:3]))
check("nouveaux champs sur chaque modèle : usd, unite, note, prompt, dispo, cle",
      all({"id", "label", "usd", "unite", "note", "prompt", "dispo", "cle"} <= set(m) for m in mods), str(mods[-1]))
check("les modèles du registre sont proposés (bria, veed, pixelcut, sam31)",
      {"bria-video-v3", "veed-video-rapide", "pixelcut-video", "sam31-video"} <= {m["id"] for m in mods},
      str([m["id"] for m in mods]))
check("le registre vidéo complet est servi à part (`registre`, 5 entrées)", len(mm.get("registre") or []) == 5,
      str(mm.get("registre"))[:200])


async def attendre(c, mid):
    s = {}
    for _ in range(200):
        s = (await c.get(f"/api/matte/{mid}")).json()
        if s.get("status") in ("done", "failed"):
            return s
        await asyncio.sleep(0.02)
    return s


async def _matte():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        raz()
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "bria-video-v3"})
        check("POST /matte model=bria-video-v3 : 200", r.status_code == 200, r.text[:200])
        s = await attendre(c, r.json().get("matte_id"))
        check("bria-video-v3 : la bonne requête (endpoint, Transparent, mov_proresks, video_url)",
              SEAMS["sub"] == [("bria/video/background-removal/v3",
                                {"video_url": "http://fal.test/in", "background_color": "Transparent",
                                 "output_container_and_codec": "mov_proresks", "preserve_audio": True})], str(SEAMS))
        check("bria-video-v3 : sortie .mov servie", s.get("status") == "done" and s["file"].endswith(".mov")
              and (await c.get(s["url"])).status_code == 200, str(s))
        raz()
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "sam31-video"})
        check("sam31-video sans sujet -> 400, aucun appel", r.status_code == 400 and SEAMS["sub"] == [], r.text[:200])
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "sam31-video", "sujet": "la mire"})
        s = await attendre(c, r.json().get("matte_id"))
        check("sam31-video avec sujet : prompt transmis, sortie .webm",
              bool(SEAMS["sub"]) and SEAMS["sub"][-1][1].get("prompt") == "la mire"
              and s.get("file", "").endswith(".webm"), f"{SEAMS} {s}")
        raz()
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "veed-video-rapide"})
        s = await attendre(c, r.json().get("matte_id"))
        rf = await c.get(s.get("url") or "/api/matte/file/x.webm")
        check("veed : .webm confiné sous outputs/mattes et servi en video/webm",
              s.get("status") == "done" and MT.matte_path(s["file"]).parent == MT.mattes_dir().resolve()
              and rf.status_code == 200 and rf.headers["content-type"].startswith("video/webm"), str(s))
        raz()
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "general"})
        s = await attendre(c, r.json().get("matte_id"))
        check("ancienne clé general : BiRefNet vidéo, arguments d'avant, note « à mesurer »",
              SEAMS["sub"] == [(MT.ENDPOINT, dict(MT.ARGS_FIXED, video_url="http://fal.test/in",
                                                  model="General Use (Light)"))] and s.get("status") == "done"
              and "mesurer" in r.json().get("usd_note", ""), str(SEAMS))
        check("modèle image refusé sur /matte -> 400",
              (await c.post("/api/matte", json={"job_id": "job-d1", "model": "pixelcut"})).status_code == 400)
        d0 = n_depenses()
        settings.FAL_KEY = ""
        raz()
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "bria-video-v3"})
        check("sans clé : 503 nommant FAL_KEY, zéro dépense, aucun appel", r.status_code == 503
              and "FAL_KEY" in r.text and n_depenses() == d0 and SEAMS["sub"] == [], r.text[:200])
        r = await c.post("/api/matte", json={"job_id": "job-d1", "model": "sam31-video"})
        check("ORDRE /matte : sam31-video sans sujet ET sans clé -> 503 FAL_KEY, zéro dépense", r.status_code == 503
              and "FAL_KEY" in r.text and n_depenses() == d0, r.text[:200])
        settings.FAL_KEY = "test-key"


loop.run_until_complete(_matte())
for bad in ("../x.webm", "x.mp4", "a b.webm", "x.webm.exe", "x.WEBM.mov.mp4", ""):
    try:
        MT.matte_path(bad)
        check(f"nom refusé : {bad!r}", False)
    except ValueError:
        check(f"nom refusé : {bad!r}", True)

# ════════════════════════════════════════════════════════════════════════════
print("\n[5] le webm garde son alpha à la lecture")
check("decodeur_entree : libvpx-vp9 pour un .webm, rien pour un .mov",
      MT.decodeur_entree(W / "a.webm") == ["-c:v", "libvpx-vp9"] and MT.decodeur_entree(W / "a.mov") == [])
outp = W / "f.png"
subprocess.run(["ffmpeg", "-y", "-v", "error", *MT.decodeur_entree(W / "fake.webm"), "-i", str(W / "fake.webm"),
                "-frames:v", "1", "-pix_fmt", "rgba", str(outp)], check=True)
px = Image.open(outp).convert("RGBA")
check("pixels : gauche opaque, droite transparente (alpha lu)", px.getpixel((8, 32))[3] > 200
      and px.getpixel((56, 32))[3] < 50, f"{px.getpixel((8, 32))} {px.getpixel((56, 32))}")
from app.services import effects_preview as FXP, decor_service as DS, montage_service as MS  # noqa: E402
check("vignette du rack et Montage passent par decodeur_entree",
      "decodeur_entree" in pathlib.Path(FXP.__file__).read_text(encoding="utf-8")
      and "decodeur_entree" in pathlib.Path(MS.__file__).read_text(encoding="utf-8"), "")
cmd = DS.commande(W / "m.webm", W / "clip.mp4", {"couleur": "#00ff00"}, 64, 64, W / "o.mp4")
i = cmd.index(str(W / "m.webm"))
check("décor : le matte webm est lu par libvpx-vp9", cmd[i - 3:i] == ["-c:v", "libvpx-vp9", "-i"], str(cmd[i - 4:i + 1]))
cmd = DS.commande(W / "m.mov", W / "clip.mp4", {"couleur": "#00ff00"}, 64, 64, W / "o.mp4")
check("décor : un matte .mov garde la commande d'avant (pas de décodeur imposé)", "libvpx-vp9" not in cmd)

# ════════════════════════════════════════════════════════════════════════════
print("\n[6] sites")
from app.services import sprite_service as SS  # noqa: E402
o = SS.normalize_opts({"modele": "bria-rmbg"})
check("sprites : normalize_opts porte modele (et sujet None)", o.get("modele") == "bria-rmbg" and o.get("sujet") is None,
      str({k: o.get(k) for k in ("modele", "sujet")}))
check("sprites : sans modele, la clé vaut None (défaut inchangé)", SS.normalize_opts({}).get("modele") is None)
o = SS.normalize_opts({"modele": "sam3-sujet"})
check("sprites : normalize_opts ne juge PAS le sujet (rangé brut ; la route le contrôle APRÈS la clé)",
      o["modele"] == "sam3-sujet" and o["sujet"] is None)
for bad in ({"modele": "zzz"}, {"modele": "bria-video-v3"}):
    try:
        SS.normalize_opts(bad)
        check(f"sprites : {bad} refusé", False)
    except ValueError:
        check(f"sprites : {bad} refusé (ValueError -> 400)", True)
o = SS.normalize_opts({"modele": "sam3-sujet", "sujet": "le héros"})
check("sprites : sam3-sujet avec sujet accepté", o["sujet"] == "le héros")
e = R._cout_job_sprite({"frames": 10, "remove_bg": "none", "modele": "ideogram-rmbg"}, P.load())
check("sprites : le coût d'un job avec modele = 10 détourages ideogram (0,10 $)", abs(e["total_usd"] - 0.10) < 1e-9,
      str(e))
e = R._cout_job_sprite({"frames": 10, "remove_bg": "api"}, P.load())
check("sprites : le coût d'un job SANS modele est celui d'avant (sprite2d)",
      e == P.estimate({"kind": "sprite2d", "frames": 10, "remove_bg": "api"}), str(e))
# un vrai job sprite (images) avec un modèle du registre : chaque image détourée par la couture
for i in range(2):
    Image.new("RGB", (48, 48), (0, 200, 0)).save(settings.images_path / f"f{i}.png")
raz()
r = loop.run_until_complete(SS.generate_sprites({"source": {"kind": "images", "filenames": ["f0.png", "f1.png"]},
                                                 "modele": "bria-rmbg", "cell": {"size": 128}}, "spdt01"))
check("sprites : generate_sprites avec modele détoure chaque image par le registre (2 appels bria)",
      [s[0] for s in SEAMS["sub"]] == ["fal-ai/bria/background/remove"] * 2 and r.get("remove_bg") == "bria-rmbg"
      and r.get("bg_failed") == [], f"{SEAMS['sub']} {r.get('remove_bg')} {r.get('bg_failed')}")
st, js = call("POST", "/assets/sprite", {"source": {"kind": "images", "filenames": [SRC]}, "modele": "zzz"})
check("POST /assets/sprite modele inconnu -> 400", st == 400, f"{st} {str(js)[:120]}")
d0 = n_depenses()
settings.FAL_KEY = ""
st, js = call("POST", "/assets/sprite", {"source": {"kind": "images", "filenames": [SRC]}, "modele": "pixelcut"})
settings.FAL_KEY = "test-key"
check("POST /assets/sprite sans clé -> 503 FAL_KEY, zéro dépense", st == 503 and "FAL_KEY" in str(js)
      and n_depenses() == d0, f"{st} {js}")
settings.FAL_KEY = ""
st, js = call("POST", "/assets/sprite", {"source": {"kind": "images", "filenames": [SRC]}, "modele": "sam3-sujet"})
settings.FAL_KEY = "test-key"
check("ORDRE /assets/sprite : sam3-sujet sans sujet ET sans clé -> 503 FAL_KEY, zéro dépense", st == 503
      and "FAL_KEY" in str(js) and n_depenses() == d0, f"{st} {js}")
st, js = call("POST", "/assets/sprite", {"source": {"kind": "images", "filenames": [SRC]}, "modele": "sam3-sujet"})
check("/assets/sprite : sam3-sujet sans sujet (clé posée) -> 400", st == 400, f"{st} {js}")
try:
    import rembg as _rembg  # noqa: F401
    _a_rembg = True
except ImportError:
    _a_rembg = False
if not _a_rembg:
    st, js = call("POST", "/assets/sprite", {"source": {"kind": "images", "filenames": [SRC]}, "modele": "local-rembg"})
    check("/assets/sprite : local-rembg sans rembg installé -> 400 d'emblée (comme l'ancien chemin local)",
          st == 400 and "rembg" in str(js), f"{st} {js}")
settings.FAL_KEY = ""
st, js = call("POST", "/assets/3d/zz-inconnu/views/0/detourer", {"modele": "sam3-sujet"})
settings.FAL_KEY = "test-key"
check("ORDRE vues 3D : sam3-sujet sans sujet ET sans clé -> 503 FAL_KEY (avant même le jeu de vues)", st == 503
      and "FAL_KEY" in str(js), f"{st} {js}")

# Card Forge
from app.services.cards import capture as CAP  # noqa: E402
check("Card Forge /rembg accepte un corps {modele, sujet}", "body" in inspect.signature(CAP.post_rembg).parameters,
      str(inspect.signature(CAP.post_rembg)))
# Studio3D : detourer_vue accepte modele / sujet
from app.services import asset3d_views as AV  # noqa: E402
sig = inspect.signature(AV.detourer_vue).parameters
check("Studio3D : detourer_vue(..., modele=None, sujet=None)", "modele" in sig and "sujet" in sig
      and sig["modele"].default is None, str(sig))
# décor : modele vidéo du registre accepté, aperçu par le jumeau image
check("décor : DS.modele garde les anciennes clés et accepte un id vidéo du registre",
      DS.modele("matting") == "matting" and DS.modele("bria-video-v3") == "bria-video-v3"
      and DS.modele("pixelcut") == DS.MODELE_DEFAUT and DS.modele(None) == DS.MODELE_DEFAUT, "")
check("décor : un jumeau image pour l'aperçu de chaque modèle vidéo",
      all(DT.REGISTRE[DT.REGISTRE[m]["apercu"]]["nature"] == "detourage_image"
          for m in DT.ids("detourage_video")), "")

print("\n[7] Card Forge /rembg et décor Avatar, par HTTP")
from app.services.cards import core as CC  # noqa: E402
did = CC.create_deck("import")["id"]
carte = Image.new("RGB", (630, 880), (216, 183, 106))
for x in range(200, 430):
    for y in range(300, 580):
        carte.putpixel((x, y), (30, 30, 120))
_b = io.BytesIO()
carte.save(_b, "PNG")


async def _cartes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        r = await c.post(f"/api/cards/{did}/capture/card?side=recto", content=_b.getvalue(),
                         headers={"Content-Type": "image/png"})
        check("Card Forge : recto déposé", r.status_code == 200, r.text[:200])
        raz()
        r = await c.post(f"/api/cards/{did}/capture/rembg", json={"modele": "sam3-sujet"})
        check("Card Forge : sam3-sujet sans sujet -> 400, aucun appel", r.status_code == 400 and SEAMS["sub"] == [],
              r.text[:200])
        settings.FAL_KEY = ""
        d0 = n_depenses()
        r = await c.post(f"/api/cards/{did}/capture/rembg", json={"modele": "bria-rmbg"})
        settings.FAL_KEY = "test-key"
        check("Card Forge : sans clé -> 503 FAL_KEY, zéro dépense", r.status_code == 503 and "FAL_KEY" in r.text
              and n_depenses() == d0 and SEAMS["sub"] == [], r.text[:200])
        settings.FAL_KEY = ""
        r = await c.post(f"/api/cards/{did}/capture/rembg", json={"modele": "sam3-sujet"})
        settings.FAL_KEY = "test-key"
        check("ORDRE Card Forge : sam3-sujet sans sujet ET sans clé -> 503 FAL_KEY", r.status_code == 503
              and "FAL_KEY" in r.text and n_depenses() == d0, r.text[:200])
        r = await c.post(f"/api/cards/{did}/capture/rembg", json={"modele": "zzz"})
        check("Card Forge : modèle inconnu -> 400", r.status_code == 400, r.text[:200])
        r = await c.post(f"/api/cards/{did}/capture/rembg", json={"modele": "bria-rmbg"})
        js = r.json()
        check("Card Forge : modele=bria-rmbg -> requête Bria RMBG, couche rangée, prix 0,018",
              r.status_code == 200 and [s[0] for s in SEAMS["sub"]] == ["fal-ai/bria/background/remove"]
              and js.get("voie") == "fal" and js.get("modele") == "bria-rmbg" and abs(js.get("prix_usd") - 0.018) < 1e-9
              and (CAP.cap_dir(did) / CAP.SUJET_NAME).is_file(), r.text[:300])
        check("Card Forge : le dossier temporaire de détourage est retiré",
              not list(CAP.cap_dir(did).glob("_detourage_*")), str(list(CAP.cap_dir(did).iterdir())))

        # décor Avatar : une prise déposée
        with open(W / "clip.mp4", "rb") as fh:
            dep = (await c.post("/api/avatar-live/recast/source",
                                files={"fichier": ("prise.mp4", fh, "video/mp4")})).json().get("depot")
        check("décor : prise déposée", bool(dep), str(dep))
        raz()
        r = await c.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                                 "modele": "bria-video-v3"})
        js = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        check("décor aperçu, modele vidéo bria-video-v3 : passe par son jumeau image Bria RMBG",
              r.status_code == 200 and [s[0] for s in SEAMS["sub"]] == ["fal-ai/bria/background/remove"]
              and js.get("modele") == "bria-video-v3" and js.get("modele_apercu") == "bria-rmbg", r.text[:300])
        raz()
        r = await c.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                                 "modele": "sam31-video"})
        check("décor aperçu sam31-video sans sujet -> 400, aucun appel", r.status_code == 400 and SEAMS["sub"] == [],
              r.text[:200])
        raz()
        r = await c.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"}})
        check("décor aperçu SANS modele : BiRefNet image Portrait, comme avant",
              r.status_code == 200 and SEAMS["sub"] and SEAMS["sub"][0][0] == "fal-ai/birefnet/v2"
              and SEAMS["sub"][0][1].get("model") == "Portrait", r.text[:200])
        raz()
        r = await c.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                          "modele": "veed-video-rapide"})
        jid = r.json().get("job_id") if r.status_code == 200 else None
        j = {}
        for _ in range(300):
            if not jid:
                break
            j = (await c.get(f"/api/jobs/{jid}")).json()
            if j.get("status") in ("done", "failed"):
                break
            await asyncio.sleep(0.1)
        check("décor vidéo avec VEED (sortie .webm) : requête VEED, job composé jusqu'au bout",
              r.status_code == 200 and [s[0] for s in SEAMS["sub"]] == ["veed/video-background-removal/fast"]
              and j.get("status") == "done", f"{r.text[:200]} {j.get('status')} {j.get('error')}")
        settings.FAL_KEY = ""
        d0 = n_depenses()
        r = await c.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                          "modele": "bria-video-v3"})
        settings.FAL_KEY = "test-key"
        check("décor sans clé -> 503 FAL_KEY, zéro dépense", r.status_code == 503 and "FAL_KEY" in r.text
              and n_depenses() == d0, r.text[:200])
        settings.FAL_KEY = ""
        r = await c.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                          "modele": "sam31-video"})
        r2 = await c.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                                  "modele": "sam31-video"})
        settings.FAL_KEY = "test-key"
        check("ORDRE décor et aperçu : sam31-video sans sujet ET sans clé -> 503 FAL_KEY (libellé, pas l'id)",
              r.status_code == 503 and r2.status_code == 503 and "FAL_KEY" in r.text and "SAM 3.1" in r.text
              and n_depenses() == d0, r.text[:200] + r2.text[:200])
        r = await c.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"},
                                                          "modele": "bria-rmbg"})
        check("décor : un id du registre de nature IMAGE -> 400 (plus de repli muet sur portrait)",
              r.status_code == 400 and n_depenses() == d0, r.text[:200])


loop.run_until_complete(_cartes())


# ── [8] écrans (tâche B) : les six sites choisissent leur modèle dans le registre ─────────────────────────────────
print("\n[8] écrans : les six sites")
import json as _json  # noqa: E402
import re as _re  # noqa: E402
_RAC = pathlib.Path(__file__).resolve().parents[2]
_FR = _RAC / "frontend"


def _lire(rel):
    return (_FR / rel).read_bytes().decode("utf-8")


def _sans_cle_grise(txt):
    """NÉGATIF (règle du 11/10/2026) : aucune option désactivée pour une clé manquante."""
    return not _re.search(r"disabled[^;\n]{0,80}(dispo|sansCle|cle_absente|\.cle\b)", txt) \
        and not _re.search(r"(dispo|sansCle)[^;\n]{0,40}disabled\s*=\s*(true|!0)", txt)


_SITES = {
    # site : (fichier, nature, clé localStorage, motifs d'envoi de modele et de sujet, page qui charge dz-modeles-ia)
    "spritelab": ("spritelab/spritelab.js", "detourage_image", "dz_detour_spritelab",
                  ['remove_bg: "none", modele: v', "c.sujet = sj", "...detourCorps(),"], "spritelab/index.html"),
    "studio3d": ("studio3d/vues.js", "detourage_image", "dz_detour_studio3d",
                 ["{ modele: v }", "c.sujet = sj", "/detourer`, corps);"], "studio3d/index.html"),
    "cartes": ("cardforge/js/mod-capture.js", "detourage_image", "dz_detour_cartes",
               ["{ modele: v }", "c.sujet = sj", 'M.api.raw("POST", "rembg", corpsDetour)'], "cardforge/index.html"),
    "avatar": ("avatar/avatar.js", "detourage_video", "dz_detour_avatar",
               ['modele: $("dModele").value }, detourSujet())', "{ sujet: sj }"], "avatar/index.html"),
}
for site, (rel, nature, ls, envois, page) in _SITES.items():
    t = _lire(rel)
    check(f"{site} : DzModelesIA.select(…, \"{nature}\") ", f'DzModelesIA.select(sel, "{nature}"' in t, rel)
    check(f"{site} : choix mémorisé {ls} (accès gardé par try/catch)",
          t.count(f'"{ls}"') == 1 and _re.search(r"try \{ (?:voulu = )?localStorage\.getItem\(DETOUR_LS\)", t) is not None
          and "try { localStorage.setItem(DETOUR_LS" in t, rel)
    check(f"{site} : envoie modele et sujet", all(m in t for m in envois), [m for m in envois if m not in t])
    check(f"{site} : aucune option grisée pour une clé manquante", _sans_cle_grise(t), rel)
    h = _lire(page)
    check(f"{site} : {page} charge /shared/dz-modeles-ia.js AVANT le script du lab",
          0 <= h.find('src="/shared/dz-modeles-ia.js"') < max(h.find(f'src="{pathlib.Path(rel).name}"'),
                                                               h.find('src="js/core.js"'), h.find('src="studio3d.js"')), page)
_sl = _lire("spritelab/index.html")
check("spritelab : #removeBg porte les ids du registre (défaut d'avant rembg-fal) et garde « Aucun » ; champ sujet",
      '<option value="rembg-fal" selected>' in _sl and '<option value="local-chroma">' in _sl
      and '<option value="none">' in _sl and 'id="removeBgSujet"' in _sl and 'value="api"' not in _sl)
_s3 = _lire("studio3d/index.html")
check("studio3d : #vuesDetourModele (défaut d'avant : masque des coins) et #vuesDetourSujet",
      'id="vuesDetourModele"' in _s3 and '<option value="coins">' in _s3 and 'id="vuesDetourSujet"' in _s3)
check("studio3d : le masque des coins garde le corps d'avant { via: \"local\" }",
      'if (!v || v === DETOUR_COINS) return { via: "local" };' in _lire("studio3d/vues.js"))
check("cartes : garder le défaut (voie d'avant) n'envoie AUCUN corps",
      'if (!v || v === detourDefaut(offreIA(IA, !!info("recto")).voie)) return undefined;' in _lire("cardforge/js/mod-capture.js"))
_av = _lire("avatar/avatar.js")
check("avatar : les trois réglages BiRefNet d'avant restent (portrait par défaut), BiRefNet v2 vidéo du registre écarté",
      'if (!sel.value) sel.value = "portrait";' in _av and "removeChild(ob)" in _av
      and '<option value="portrait"' in _lire("avatar/index.html") and 'id="dSujet"' in _lire("avatar/index.html"))
# preuve 8799 du 12/10 : texte() traduit par l'id (detour.modele.<id>) — sans `id: o.value`, les trois réglages
# d'avant s'affichaient tous « BiRefNet v2 vidéo », le libellé de l'entrée du registre qu'ils remplacent
check("avatar : chaque réglage d'avant garde SON libellé (texte() reçoit l'id de l'option, pas celui du registre)",
      "Object.assign({}, bire, { id: o.value, label: o.textContent })" in _av)

# rack VFX (couche vfxrack, rafraîchie dans le bundle)
_vr = _lire("patches/vfxrack.js")
check("vfxrack : modèles de /api/matte-models avec prix (vfxMatteLbl), sujet SAM 3.1, choix mémorisé dz_detour_vfx",
      "children:vfxMatteLbl(o)" in _vr and 'vfxPost("/api/matte",vfxMatteCorps(clip.src.job_id))' in _vr
      and 'var VFX_DETOUR_LS="dz_detour_vfx";' in _vr and "c.sujet=String(VFX_MATTE.sujet" in _vr
      and "vfxMatteSujetRow(mtick)" in _vr and _sans_cle_grise(_vr))
_BUN = (_FR / "dist/assets/index-BEOJX8L5.js").read_bytes().decode("utf-8")
_b, _e = "/*__DZ_VFXRACK_BEGIN__*/", "/*__DZ_VFXRACK_END__*/"
_bloc = _BUN[_BUN.index(_b) + len(_b):_BUN.index(_e)].strip("\r\n")
check("bundle : le bloc VFXRACK EST la couche (refresh_layer --layer vfxrack), matte multi-modèles compris",
      _bloc == _vr.strip("\r\n").lstrip("﻿") and "vfxMatteCorps(" in _bloc, len(_bloc))

# nœud Studio « Détourage » (maillon de queue encartsia)
check("bundle : le nœud Détourage lit le catalogue detourage_image, garde son réglage dans ses PROPS (aucun localStorage), "
      "envoie modele/sujet et pose une `method` cohérente",
      'fetch("/api/ia/catalogue?nature=detourage_image")' in _BUN and "dz_detour_studio" not in _BUN
      and 'onChange:function(v){set("method",dzDetMeth(v));set("modele",v)}' in _BUN
      and 'var c={method:dzDetMeth(v),modele:v};' in _BUN and "c.sujet=sj" in _BUN and '"data-dzdetour":"1"' in _BUN
      and 'options:dzDetOpts(dzDv,dzDetR)' in _BUN and 'body.method=p.method||"api"' not in _BUN)
check("bundle : compteurs figés intacts (useState 731, DzTracks 181)",
      _BUN.count("x.useState(") == 731 and _BUN.count("DzTracks") == 181,
      f"{_BUN.count('x.useState(')} {_BUN.count('DzTracks')}")
_node = shutil.which("node")
if _node:
    _i0 = _BUN.index("var dzDetCat=")
    _aides = _BUN[_i0:_BUN.index("function DzImgProcPanel(", _i0)]
    _p0 = _BUN.index("function dzPrixUsd(")
    _prix = _BUN[_p0:_BUN.index("function dzPrixImg(", _p0)]
    _CAT = [{"id": "local-rembg", "label": "rembg (local, gratuit)", "voie": "local", "usd": 0, "unite": "image",
             "dispo": True, "prompt": False},
            {"id": "sam3-sujet", "label": "SAM 3", "voie": "fal", "usd": 0.005, "unite": "image", "dispo": False,
             "cle": "FAL_KEY", "prompt": True},
            {"id": "pixelcut", "label": "Pixelcut", "voie": "fal", "usd": 0, "unite": "image", "dispo": True,
             "prompt": False}]
    _js = ("var DICO={'ia.voie.local':'local, gratuit','ia.prix.a_mesurer':'prix à mesurer',"
           "'ia.cle.a_ajouter':'clé {cle} à ajouter dans Réglages','ia.etat.chargement':'chargement…',"
           "'detour.champ.sujet_requis':'Dites quel sujet garder.','studio.imgproc.api_cloud':'API cloud (fal)'};"
           "function dzT(k,v){var t=DICO[k]||k;for(var x in (v||{}))t=t.split('{'+x+'}').join(v[x]);return t}"
           "var MEM={};var localStorage={getItem:function(k){return MEM[k]||null},setItem:function(k,v){MEM[k]=v}};"
           "var window={};var CAT=" + _json.dumps(_CAT, ensure_ascii=False) + ";var tir=0;"
           "function fetch(u){tir++;return Promise.resolve({ok:true,json:function(){return Promise.resolve({modeles:CAT})}})}"
           + _prix + _aides +
           ";var avant=dzDetOpts('rembg-fal',function(){});"
           "setTimeout(function(){var apres=dzDetOpts('rembg-fal',null);"
           "var r={avant:avant,apres:apres,tir:tir,"
           "v0:dzDetVal({}),v1:dzDetVal({method:'local'}),v2:dzDetVal({method:'api'}),"
           "c0:dzDetCorps({}),c1:dzDetCorps({method:'local'}),c2:dzDetCorps({modele:'sam3-sujet'}),"
           "c3:dzDetCorps({modele:'sam3-sujet',sujet:' le chat '}),c4:dzDetCorps({modele:'pixelcut'}),"
           "p:dzDetPrompt('sam3-sujet'),m0:dzDetMeth('local-rembg'),m1:dzDetMeth('pixelcut'),m2:dzDetMeth('local-chroma'),"
           "c5:dzDetCorps({modele:'local-chroma',method:'local'})};"
           "console.log(JSON.stringify(r))},20);")
    _pr = subprocess.run([_node, "-e", _js], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        _o = _json.loads(_pr.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        _o = {}
    check("bundle (aides réelles sous node) : « chargement… » avant la réponse, puis fal d'abord, prix, local gratuit, "
          "mention de clé (choisissable)",
          _o.get("avant") == [{"value": "rembg-fal", "label": "chargement…"}]
          and _o.get("apres") == [{"value": "sam3-sujet", "label": "SAM 3 · $0.005/image · clé FAL_KEY à ajouter dans Réglages"},
                                  {"value": "pixelcut", "label": "Pixelcut · prix à mesurer"},
                                  {"value": "local-rembg", "label": "rembg (local, gratuit) · local, gratuit"}]
          and _o.get("tir") == 1, (_pr.stdout + _pr.stderr)[-500:])
    check("bundle : défaut d'avant (api ou rien -> rembg-fal, local -> local-rembg) ; `method` cohérente (locale/api)",
          _o.get("v0") == "rembg-fal" and _o.get("v1") == "local-rembg" and _o.get("v2") == "rembg-fal"
          and _o.get("m0") == "local" and _o.get("m1") == "api" and _o.get("m2") == "local"
          and _o.get("c5") == {"corps": {"method": "local", "modele": "local-chroma"}}, str(_o)[:300])
    check("bundle : corps — défauts par `method` (chemin d'avant), sujet exigé par SAM 3, sinon `modele`",
          _o.get("c0") == {"corps": {"method": "api"}} and _o.get("c1") == {"corps": {"method": "local"}}
          and _o.get("c2") == {"err": "Dites quel sujet garder."}
          and _o.get("c3") == {"corps": {"method": "api", "modele": "sam3-sujet", "sujet": "le chat"}}
          and _o.get("c4") == {"corps": {"method": "api", "modele": "pixelcut"}} and _o.get("p") is True, str(_o)[:400])
    # le rack : les fonctions t186 de la couche, exécutées sous node
    _i1 = _vr.index('var VFX_DETOUR_LS="dz_detour_vfx";')
    _vfx = _vr[_i1:_vr.index("/* petit utilitaire", _i1)]
    _js2 = ("var DICO={'ia.prix.a_mesurer':'prix à mesurer','ia.cle.a_ajouter':'clé {cle} à ajouter dans Réglages',"
            "'detour.champ.sujet_requis':'Dites quel sujet garder.','detour.champ.sujet':'Sujet à garder'};"
            "function dzT(k,v){var t=DICO[k]||k;for(var x in (v||{}))t=t.split('{'+x+'}').join(v[x]);return t}"
            "var MEM={dz_detour_vfx:'sam31-video'};var localStorage={getItem:function(k){return MEM[k]||null},"
            "setItem:function(k,v){MEM[k]=v}};" + _prix +
            "var window={};var r={jsx:function(t,p){return {t:t,p:p}}};"
            "var VFX_MATTE={busy:!1,model:'general',arm:null,models:null};" + _vfx +
            ";var o={m0:VFX_MATTE.model};VFX_MATTE.models=["
            "{id:'general',label:'Général',usd:0,unite:'s',registre:'birefnet-v2-video',dispo:true,prompt:false},"
            "{id:'veed-video-rapide',label:'VEED rapide',usd:0.012,unite:'30 images',registre:'veed-video-rapide',dispo:false,cle:'FAL_KEY',prompt:false},"
            "{id:'sam31-video',label:'SAM 3.1',usd:0.01,unite:'16 images',registre:'sam31-video',dispo:true,prompt:true}];"
            "var notes=[];o.l0=vfxMatteLbl(VFX_MATTE.models[0]);o.l1=vfxMatteLbl(VFX_MATTE.models[1]);"
            "o.bloque=vfxMatteSansSujet(function(m){notes.push(m)});o.notes=notes;o.row=!!vfxMatteSujetRow(function(){});"
            "VFX_MATTE.sujet='le chien';o.c=vfxMatteCorps('j1');o.d=vfxMatteDevis(10);"
            "vfxMatteChoix('general');o.c2=vfxMatteCorps('j1');o.d2=vfxMatteDevis(10);o.mem=MEM.dz_detour_vfx;"
            "o.row2=vfxMatteSujetRow(function(){});vfxMatteChoix('disparu');vfxMatteValide();o.m3=VFX_MATTE.model;"
            "console.log(JSON.stringify(o));")
    _pr = subprocess.run([_node, "-e", _js2], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        _o = _json.loads(_pr.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        _o = {}
    check("vfxrack (fonctions réelles sous node) : choix mémorisé relu, prix par tranche, mention de clé, sujet exigé",
          _o.get("m0") == "sam31-video" and _o.get("l0") == "Général · prix à mesurer"
          and _o.get("l1") == "VEED rapide · $0.012/30 images · clé FAL_KEY à ajouter dans Réglages"
          and _o.get("bloque") is True and _o.get("notes") == ["Dites quel sujet garder."] and _o.get("row") is True,
          (_pr.stdout + _pr.stderr)[-500:])
    check("vfxrack : corps {job_id, model, sujet} ; devis kind detourage, et kind matte d'avant pour BiRefNet",
          _o.get("c") == {"job_id": "j1", "model": "sam31-video", "sujet": "le chien"}
          and _o.get("d") == {"kind": "detourage", "modele": "sam31-video", "secondes": 10}
          and _o.get("c2") == {"job_id": "j1", "model": "general"} and _o.get("d2") == {"kind": "matte", "duration_s": 10}
          and _o.get("mem") == "general" and _o.get("row2") is None and _o.get("m3") == "general", str(_o)[:400])
else:
    check("node présent", False)

# relecture de conformité (tâche B)
_COM = _json.loads((_FR / "shared/i18n/commun.json").read_text("utf-8"))
_noms = {k: e["label"] for k, e in list(DT.REGISTRE.items()) + list(MT.MATTE_MODELS.items())}
_ecarts = [k for k, lb in _noms.items() if f"detour.modele.{k.replace('-', '_')}" in _COM
           and _COM[f"detour.modele.{k.replace('-', '_')}"]["fr"] != lb]
check("libellés : les clés detour.modele.<id> portent le libellé EXACT du serveur (et les suffixes français sont tous couverts)",
      not _ecarts and all(f"detour.modele.{k.replace('-', '_')}" in _COM for k in ("local-rembg", "local-chroma", "sam3-sujet",
      "bria-objet", "rembg-fal", "birefnet-v2-video", "veed-video-rapide", "pixelcut-video", "sam31-video")), _ecarts)
check("libellés : DzModelesIA, le nœud Studio et le rack traduisent le nom par detour.modele.<id>",
      "function libelle(m)" in _lire("shared/dz-modeles-ia.js") and "function dzDetNom(" in _BUN and "function vfxMatteNom(" in _vr)
_cap = _lire("cardforge/js/mod-capture.js")
check("cartes : un autre modèle que la voie d'avant dit SON prix (bouton, attente, contrôle « tarif changé ») ; fal à 0 $ « à mesurer »",
      "return detourAjuste(off);" in _cap and 'dzT("cartes.t186.detourer_a_mesurer")' in _cap
      and 'dzT("cartes.t186.fal_a_mesurer")' in _cap and "off.gratuit = m.voie === \"local\";" in _cap)
_vu = _lire("studio3d/vues.js")
check("studio3d : un modèle fal passe par le devis (kind detourage) puis confirmer ; title des ciseaux dynamique",
      'devis({ kind: "detourage", modele: corps.modele, images: 1 })' in _vu and "await confirmer(" in _vu
      and "detourer(i, toast, confirmer)" in _vu and "studio3d.t186.det_title" in _vu)
check("bundle : « Méthode » et son aide servent au repli (catalogue injoignable)",
      'dzDetCat?dzT("detour.champ.modele"):dzT("studio.imgproc.methode")' in _BUN and 'dzT("studio.imgproc.methode_aide")' in _BUN)
check("code mort retiré : detourage.verifier et detourage.detourer_video", not hasattr(DT, "verifier")
      and not hasattr(DT, "detourer_video"))

check("aucun appel réseau réel", RESEAU["n"] == 0, str(RESEAU))
print(f"\n=== {ok} passed, {fail} failed ===")
try:
    from app.services.storage import _engine
    loop.run_until_complete(_engine.dispose())
except Exception:  # noqa: BLE001
    pass
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
