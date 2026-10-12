# -*- coding: utf-8 -*-
"""t188 (G6, plan « Génération IA enrichie ») — les VFX IA : une vidéo (ou une image) -> une vidéo retouchée.

UN registre (`vfx_ia.REGISTRE`, 12 gestes, schémas et prix fal relus le 12/10/2026), le catalogue (nature `vfx`,
alias GET /vfx-ia/modeles), le devis (`kind: vfx_ia`, une seule fonction de taux `pricing.taux_vfx`), la route
payante POST /vfx-ia et les deux écrans (rail « VFX IA » de Son & VFX, section « IA » du rack VFX).

Ce que le banc tient :
  [0] requêtes PURES (`build_request`) : celles du plan à la lettre (relight + image, kling keep_audio, reframe
      9:16), puis chaque geste : insertion (start/resume/duration toujours envoyée), LTX (num_frames depuis la
      durée, 24 i/s, jamais enable_detail_refine), VOID (mask_prompt), Topaz (model Proteus), PixVerse (effet de la
      liste COMPLÈTE du schéma, 154 valeurs exactes ; hors liste -> ValueError) ; options hors schéma -> ValueError ;
  [1] catalogue : 12 gestes (>= 10), sans clé LISTÉS (dispo False, FAL_KEY), prix par défaut, colorisation « à
      mesurer », schéma des options servi ; GET /vfx-ia/modeles = /ia/catalogue?nature=vfx ;
  [2] devis : flux3 5 s = 0,15 $ (plan) ; MP arrondi au supérieur (1280x720x121 = 112 MP) et côté court (854x480) ;
      Topaz par tranche de 10 s et classe de la hauteur de SORTIE ; PixVerse 5 / 8 / 10 s ; VOID passe 2 + masque ;
      insertion sur la scène générée + jetons non chiffrés dits ; colorisation 0 « prix à mesurer » ;
  [3] route : PAYANTES la liste, recensement (gardée, puits appliquer_vfx) ; ordre des refus (400 id -> 503 FAL_KEY
      AVANT tout -> 400 champ / option / source) ; sans clé : ZÉRO ligne depenses, devis servi ; confinement vidéo,
      clip et image ; durée illisible -> 400 avant la garde (devis compris) ; bornes par geste ; devis = garde =
      usd rendu ; témoin UNE ligne depenses ; arguments EXACTS à fal ; job fini (provider vfx_ia) ; Bibliothèque
      (mère = source, relation vfx_ia, kind video, recette) ; la garde arrête AVANT tout envoi ;
  [4] écrans (statique) : couches = blocs du bundle, rail inséré en fin de couche, branches centre et bas du rail,
      section IA sous « Détourer », aucun prix ni effet recopié, aucun disabled pour la clé, i18n fr/en, compteurs
      figés (useState 731, DzTracks 181) ;
  [5] écrans sous node, DANS UN DOM MINIMAL : le rail Son & VFX monte avec les aides EXPORTÉES par la couche vfxrack
      (window.DzVfx.ia — la liaison entre les deux couches), les cartes se cliquent dans le DOM, les champs suivent
      le schéma, 1er clic = devis, 2e clic = tir, même chiffre ; sans clé, cartes choisissables et 503 au clic ; la
      section IA du rack sur un plan sélectionné (clip_id = son job).

AUCUN appel réseau réel : les fal_client.* sont des gardes qui COMPTENT ; les seams de vfx_ia sont des
enregistreurs. Run (depuis backend/) : & $PY tests/test_vfx_ia.py"""
import asyncio
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzvfx188_")
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
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
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

from fastapi import HTTPException  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from PIL import Image  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import vfx_ia as V, catalogue_ia as CI, pricing as P  # noqa: E402
from app.services.storage import init_db, async_session_factory, JobRecord  # noqa: E402
from app.api import routes as R  # noqa: E402
import _recensement_payant as RP  # noqa: E402

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


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, capture_output=True, timeout=180)


def _video(nom, secondes, couleur="red"):
    _ffmpeg("-f", "lavfi", "-i", f"color=c={couleur}:s=64x64:d={secondes}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(UPLOADS / nom))


UPLOADS = settings.outputs_path / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
_video("plan.mp4", 2)
_video("plan4.mp4", 4, "green")
_video("long21.mp4", 21, "blue")
shutil.copy2(UPLOADS / "plan.mp4", UPLOADS / "plan.mov")
(UPLOADS / "faux.mp4").write_bytes(b"pas une video")
Image.new("RGB", (32, 32), (200, 180, 40)).save(settings.images_path / "lumiere.png")
Image.new("RGB", (32, 32), (20, 80, 200)).save(settings.images_path / "affiche.png")
(settings.images_path / "notes.txt").write_text("x", encoding="utf-8")

# ── seams de vfx_ia : des enregistreurs ─────────────────────────────────────
SEAMS = {"up": [], "sub": [], "dl": []}
REPONSE = {"v": None}


async def _up(p):
    SEAMS["up"].append(pathlib.Path(p).name)
    return "http://fal.test/" + pathlib.Path(p).name


async def _sub(endpoint, arguments):
    SEAMS["sub"].append((endpoint, dict(arguments)))
    if REPONSE["v"] is not None:
        return REPONSE["v"]
    return {"video": {"url": "http://fal.test/sortie.mp4"}, "seed": 42}


async def _dl(url, dest):
    SEAMS["dl"].append(pathlib.Path(dest).name)
    shutil.copy2(UPLOADS / "plan.mp4", dest)


V._upload, V._fal_subscribe, V._download = _up, _sub, _dl


def raz():
    for v in SEAMS.values():
        v.clear()
    REPONSE["v"] = None


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


def detail(js):
    return str(js.get("detail") if isinstance(js, dict) else js)


def refuse(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError as e:
        return str(e)
    return None


# ════════════════════════════════════════════════════════════════════════════
print("\n[0] requêtes pures")
check("le registre compte les 12 gestes du plan, dans l'ordre",
      list(V.REGISTRE) == ["relight-h3", "inserer-h3", "effacer-perso", "effacer-objet", "jour-nuit", "eau",
                           "coloriser", "retoucher-kling", "retoucher-flux3", "recadrer", "agrandir",
                           "effets-pixverse"], list(V.REGISTRE))
ep, a = V.build_request("relight-h3", video_url="https://x/v.mp4", image_url="https://x/l.png")
check("relight", ep == "minimax/h3-max/relight" and a["reference_image_url"] == "https://x/l.png", a)
check("relight : résolution 768P et cadre « adaptive » par défaut (le 16:9 du schéma recadrerait un plan vertical)",
      a == {"video_url": "https://x/v.mp4", "reference_image_url": "https://x/l.png", "resolution": "768P",
            "aspect_ratio": "adaptive"}, a)
try:
    V.build_request("relight-h3", video_url="https://x/v.mp4")
    check("relight sans image refusé", False)
except ValueError:
    check("relight sans image refusé", True)
ep, a = V.build_request("retoucher-kling", video_url="https://x/v.mp4", prompt="ciel orageux")
check("kling edit garde le son", a.get("keep_audio") is True and a["prompt"] == "ciel orageux", a)
check("kling edit : EXACTEMENT {keep_audio, video_url, prompt}",
      ep == "fal-ai/kling-video/o3/pro/video-to-video/edit"
      and a == {"keep_audio": True, "video_url": "https://x/v.mp4", "prompt": "ciel orageux"}, a)
ep, a = V.build_request("retoucher-kling", video_url="u", prompt="p", image_url="https://x/r.png")
check("kling edit : l'image de référence part en image_urls (liste)", a.get("image_urls") == ["https://x/r.png"], a)
ep, a = V.build_request("recadrer", video_url="https://x/v.mp4", options={"aspect_ratio": "9:16"})
check("reframe 9:16", a["aspect_ratio"] == "9:16", a)
check("reframe : 720p par défaut (le 1080p du schéma coûte le double)", a.get("resolution") == "720p", a)
check("kling sans description refusé", refuse(V.build_request, "retoucher-kling", video_url="u") is not None)
check("flux3 : {video_url, prompt}", V.build_request("retoucher-flux3", video_url="u", prompt="neige")
      == ("blackforestlabs/flux-3/edit-video", {"video_url": "u", "prompt": "neige"}))
ep, a = V.build_request("inserer-h3", video_url="u", prompt="un dragon passe",
                        options={"start_time": 2, "resume_time": 3})
check("insertion : start_time / resume_time, duration TOUJOURS envoyée (5 par défaut, facturée), 768p",
      ep == "minimax/h3-max/insert-video" and a == {"video_url": "u", "prompt": "un dragon passe", "start_time": 2.0,
                                                    "resume_time": 3.0, "duration": 5, "resolution": "768p"}, a)
check("insertion : start_time requis", "start_time" in (refuse(V.build_request, "inserer-h3", video_url="u",
                                                               options={"resume_time": 3}) or ""))
check("insertion : reprise avant le début refusée", "précède" in (refuse(
    V.build_request, "inserer-h3", video_url="u", options={"start_time": 4, "resume_time": 3}) or ""))
check("insertion : start_time < 1,625 s refusé (schéma)", refuse(V.build_request, "inserer-h3", video_url="u",
                                                                options={"start_time": 1, "resume_time": 3}))
check("insertion : duration hors 5-13 refusée", refuse(V.build_request, "inserer-h3", video_url="u",
                                                      options={"start_time": 2, "resume_time": 3, "duration": 20}))
ep, a = V.build_request("effacer-perso", video_url="u", secondes=5.04)
check("LTX plaque propre : num_frames = durée x 24 (arrondi au-dessus), 24 i/s, 720p, rien d'autre",
      ep == "fal-ai/ltx-2.3-quality/clean-plate"
      and a == {"video_url": "u", "resolution": "720p", "num_frames": 121, "frames_per_second": 24}, a)
check("LTX : enable_detail_refine n'est JAMAIS envoyé (x4 le prix), ni comme option",
      all("enable_detail_refine" not in V.REGISTRE[m]["options"] and "enable_detail_refine" not in V.REGISTRE[m]["fixe"]
          for m in V.REGISTRE) and refuse(V.build_request, "jour-nuit", video_url="u",
                                          options={"enable_detail_refine": True}))
check("LTX : 9 images au moins (schéma)", V.build_request("jour-nuit", video_url="u", secondes=0.1)[1]["num_frames"] == 9)
check("eau, jour-nuit, coloriser : leurs endpoints LTX 2.3 quality",
      V.build_request("eau", video_url="u")[0] == "fal-ai/ltx-2.3-quality/water-simulation"
      and V.build_request("jour-nuit", video_url="u")[0] == "fal-ai/ltx-2.3-quality/day-to-night"
      and V.build_request("coloriser", video_url="u")[0] == "fal-ai/ltx-2.3-quality/colorization")
ep, a = V.build_request("effacer-objet", video_url="u", prompt="un mur de briques",
                        options={"mask_prompt": "la chaise rouge", "enable_pass2_refinement": True})
check("VOID : prompt (le fond), mask_prompt (l'objet), passe 2",
      ep == "fal-ai/void-video-inpainting" and a == {"video_url": "u", "prompt": "un mur de briques",
                                                    "mask_prompt": "la chaise rouge", "enable_pass2_refinement": True}, a)
check("VOID : l'objet à effacer est exigé (sans masque fourni, il fait générer le masque SAM 3)",
      "mask_prompt" in (refuse(V.build_request, "effacer-objet", video_url="u", prompt="mur") or ""))
ep, a = V.build_request("agrandir", video_url="u")
check("Topaz : model « Proteus », facteur 2 par défaut", ep == "topaz/upscale/video/precision"
      and a == {"model": "Proteus", "video_url": "u", "upscale_factor": 2}, a)
check("Topaz : facteur hors 1-4 refusé", refuse(V.build_request, "agrandir", video_url="u", options={"upscale_factor": 5}))
ep, a = V.build_request("effets-pixverse", image_url="https://x/i.png", options={"effect": "Earth Zoom", "duration": 8})
check("PixVerse : une IMAGE (pas de vidéo), l'effet, la durée en chaîne (schéma), 720p",
      ep == "fal-ai/pixverse/v5.5/effects"
      and a == {"image_url": "https://x/i.png", "effect": "Earth Zoom", "duration": "8", "resolution": "720p"}, a)
check("PixVerse : un effet HORS de l'énumération du schéma est refusé, nommé",
      "Effet Inventé" in (refuse(V.build_request, "effets-pixverse", image_url="i", options={"effect": "Effet Inventé"}) or ""))
check("PixVerse : la casse compte (« earth zoom » n'est pas « Earth Zoom »)",
      refuse(V.build_request, "effets-pixverse", image_url="i", options={"effect": "earth zoom"}) is not None)
check("PixVerse : une valeur avec apostrophe et point d'interrogation passe telle quelle (« Who's Arrested? »)",
      V.build_request("effets-pixverse", image_url="i", options={"effect": "Who's Arrested?"})[1]["effect"]
      == "Who's Arrested?")
check("PixVerse : 1080p en 10 s refusé, nommé", "1080p" in (refuse(
    V.build_request, "effets-pixverse", image_url="i",
    options={"effect": "Earth Zoom", "duration": "10", "resolution": "1080p"}) or ""))
check("PixVerse : l'effet est requis", refuse(V.build_request, "effets-pixverse", image_url="i"))
# l'énumération `effect` relue au schéma fal le 12/10/2026 : 154 valeurs (décision de l'utilisateur : la liste
# COMPLÈTE). Témoins pris au relevé : premières et dernières, apostrophes, deux-points, quasi-doublons du schéma.
_EP = V.EFFETS_PIXVERSE
check("PixVerse : la liste COMPLÈTE du schéma relu (154 valeurs, sans doublon, ordre du schéma)",
      len(_EP) == 154 and len(set(_EP)) == 154 and _EP[:3] == ("Kiss Me AI", "Kiss", "Muscle Surge")
      and _EP[-3:] == ("Somber Embrace", "Beam me up", "Suit Swagger"), (len(_EP), _EP[:3], _EP[-3:]))
check("PixVerse : valeurs témoins recopiées EXACTEMENT (apostrophes, ponctuation, quasi-doublons)",
      all(v in _EP for v in ("Who's Arrested?", "It's Snowy", "Grinch's Xmas Hijack", "IT'S THE FIRST OF THE MONTH",
                             "Black Myth: Wukong", "Sharksnap!", "Where did this cobweb come from?",
                             "3D Figurine Factor", "3D Figurine Factory", "Flora Nymph Gown", "Flora Nymph Go",
                             "Kiss me", "Kiss Me AI", "Earth Zoom", "Product close-up", "Blocky Mini-Me"))
      and "Who’s Arrested?" not in _EP)
check("option inconnue -> ValueError nommée", "zzz" in (refuse(V.build_request, "recadrer", video_url="u",
                                                               options={"zzz": 1}) or ""))
check("option hors énumération -> ValueError", refuse(V.build_request, "recadrer", video_url="u",
                                                      options={"aspect_ratio": "2:1"}))
check("booléen attendu -> ValueError", refuse(V.build_request, "effacer-objet", video_url="u", prompt="m",
                                              options={"mask_prompt": "x", "enable_pass2_refinement": "oui"}))
check("geste hors registre -> ValueError", refuse(V.build_request, "zzz", video_url="u"))
check("geste vidéo sans vidéo -> ValueError", refuse(V.build_request, "agrandir"))

# ════════════════════════════════════════════════════════════════════════════
print("\n[1] catalogue")
check(">= 10 VFX au catalogue", len(CI.lister("vfx")) >= 10)
_cat = {e["id"]: e for e in CI.lister("vfx")}
check("12 gestes, voie fal, clé FAL_KEY, unités du registre", len(_cat) == 12
      and all(e["voie"] == "fal" and e["cle"] == "FAL_KEY" for e in _cat.values())
      and _cat["jour-nuit"]["unite"] == "mp" and _cat["agrandir"]["unite"] == "tranche10s"
      and _cat["effets-pixverse"]["unite"] == "effet" and _cat["effacer-objet"]["unite"] == "video")
check("prix par défaut : relight 0,08 $/s (768P), insertion 0,06 $/s (768p), LTX 0,0024075 $/MP, Kling 0,168, FLUX 0,03, "
      "reframe 0,10 (720p), Topaz 0,10 (720p), PixVerse 0,20 (720p, 5 s), VOID 0,10 (le masque est exigé)",
      [_cat[k]["usd"] for k in ("relight-h3", "inserer-h3", "jour-nuit", "retoucher-kling", "retoucher-flux3",
                                "recadrer", "agrandir", "effets-pixverse", "effacer-objet")]
      == [0.08, 0.06, 0.0024075, 0.168, 0.03, 0.10, 0.10, 0.20, 0.10], {k: v["usd"] for k, v in _cat.items()})
check("colorisation : 0 « à mesurer » (la page n'affiche aucun prix ; pas le tarif des sœurs)",
      _cat["coloriser"]["usd"] == 0.0 and _cat["coloriser"]["note"] == "a_mesurer"
      and all(_cat[k]["note"] == "" for k in _cat if k != "coloriser"))
check("le schéma des options est servi (les effets PixVerse compris) — l'écran ne recopie rien",
      _cat["effets-pixverse"]["options"]["effect"]["choix"] == list(V.EFFETS_PIXVERSE)
      and _cat["effets-pixverse"]["options"]["effect"]["requis"] is True
      and _cat["recadrer"]["options"]["aspect_ratio"]["defaut"] == "9:16"
      and _cat["inserer-h3"]["options"]["start_time"]["num"] == [1.625, 60.0])
check("phrase, entrée, description et image par geste",
      _cat["relight-h3"]["image"] == "requis" and _cat["effets-pixverse"]["entree"] == "image"
      and _cat["retoucher-kling"]["prompt"] == "requis" and _cat["agrandir"]["prompt"] is None
      and all(e["phrase"] for e in _cat.values()))
settings.FAL_KEY = ""
_sans = CI.lister("vfx")
settings.FAL_KEY = "test-key"
check("sans FAL_KEY : les 12 gestes restent LISTÉS (dispo False, nom de la clé, prix gardé)",
      len(_sans) == 12 and all(e["dispo"] is False and e["cle"] == "FAL_KEY" for e in _sans)
      and _sans[0]["usd"] == 0.08)
st, js = call("GET", "/vfx-ia/modeles")
st2, js2 = call("GET", "/ia/catalogue", params={"nature": "vfx"})
check("GET /vfx-ia/modeles = alias de /ia/catalogue?nature=vfx", st == 200 and st2 == 200 and js == js2
      and js["nature"] == "vfx" and len(js["modeles"]) == 12, f"{st} {st2}")

# ════════════════════════════════════════════════════════════════════════════
print("\n[2] devis")
e = P.estimate({"kind": "vfx_ia", "modele": "retoucher-flux3", "secondes": 5})
check("flux3 5 s = 0,15 $", abs(e["total_usd"] - 0.15) < 1e-9, e)
e = P.estimate(V.op_vfx("jour-nuit", 121 / 24, {"resolution": "720p"}, 1280, 720))
check("LTX : 1280x720 x 121 images = 112 MP (arrondi au supérieur) x 0,0024075 = 0,2696 $ (exemple de la page fal)",
      e["breakdown"][0]["units"] == 112 and abs(e["total_usd"] - 0.2696) < 1e-9 and "112 MP" in e["breakdown"][0]["label"], e)
check("LTX 480p : côté court 480, l'autre suit le format (16:9 -> 854x480), vertical -> 480x854",
      V.megapixels(5, "480p", 1920, 1080)[2:] == (854, 480) and V.megapixels(5, "480p", 1080, 1920)[2:] == (480, 854)
      and V.megapixels(5, "720p")[2:] == (1280, 720))
check("LTX : dimensions illisibles -> 16:9 supposé", V.megapixels(5, "720p", None, None)[0]
      == V.megapixels(5, "720p", 1280, 720)[0])
e = P.estimate(V.op_vfx("agrandir", 12, {}, 1280, 720))
check("Topaz : 12 s -> 2 tranches de 10 s ; 720 x2 = 1440 de haut -> classe 4k (0,60) = 1,20 $",
      abs(e["total_usd"] - 1.2) < 1e-9 and e["breakdown"][0]["units"] == 2, e)
check("Topaz : la classe = hauteur de SORTIE (360 x2 = 720 -> 720p ; 540 x2 = 1080 -> 1080p ; 1080 x1 -> 1080p)",
      abs(P.estimate(V.op_vfx("agrandir", 9, {}, 640, 360))["total_usd"] - 0.10) < 1e-9
      and abs(P.estimate(V.op_vfx("agrandir", 9, {}, 960, 540))["total_usd"] - 0.20) < 1e-9
      and abs(P.estimate(V.op_vfx("agrandir", 9, {"upscale_factor": 1}, 1920, 1080))["total_usd"] - 0.20) < 1e-9)
check("Topaz : hauteur inconnue -> 1080 supposée (prudent : x2 = 4k)",
      abs(P.estimate(V.op_vfx("agrandir", 5, {}))["total_usd"] - 0.60) < 1e-9)
_px = [P.estimate(V.op_vfx("effets-pixverse", None, {"effect": "Earth Zoom", "duration": d, "resolution": r}))["total_usd"]
       for d, r in (("5", "540p"), ("5", "720p"), ("5", "1080p"), ("8", "720p"), ("10", "720p"), ("8", "1080p"))]
check("PixVerse : 5 s 0,15 (540p) / 0,20 (720p) / 0,40 (1080p) ; 8 s = x2 ; 10 s = x2,2",
      [round(x, 4) for x in _px] == [0.15, 0.2, 0.4, 0.4, 0.44, 0.8], _px)
_vo = [P.estimate(V.op_vfx("effacer-objet", 3, o))["total_usd"] for o in
       ({"mask_prompt": "x"}, {"mask_prompt": "x", "enable_pass2_refinement": True}, {})]
check("VOID : 0,05 + 0,05 de masque SAM 3 = 0,10 ; passe 2 : 0,10 + 0,05 = 0,15 ; sans masque : 0,05",
      [round(x, 4) for x in _vo] == [0.1, 0.15, 0.05], _vo)
e = P.estimate(V.op_vfx("inserer-h3", 30, {"start_time": 2, "resume_time": 3, "duration": 7}))
check("insertion : facturée sur la SCÈNE générée (7 s x 0,06 = 0,42), pas sur la durée de la source ; jetons de "
      "référence au-delà de 4 096 dits non chiffrés",
      abs(e["total_usd"] - 0.42) < 1e-9 and "4 096" in e["breakdown"][0]["label"], e)
e = P.estimate(V.op_vfx("inserer-h3", 30, {"start_time": 2, "resume_time": 3, "resolution": "480p"}))
check("insertion 480p, durée par défaut : 5 s x 0,05 = 0,25", abs(e["total_usd"] - 0.25) < 1e-9, e)
e = P.estimate(V.op_vfx("relight-h3", 3, {"resolution": "2K"}))
check("relight 2K : 3 s x 0,32 = 0,96", abs(e["total_usd"] - 0.96) < 1e-9, e)
e = P.estimate(V.op_vfx("coloriser", 4, {}, 1280, 720))
check("colorisation : 0 $ et la ligne dit « prix à mesurer »", e["total_usd"] == 0.0
      and "prix à mesurer" in e["breakdown"][0]["label"], e)
e = P.estimate({"kind": "vfx_ia", "modele": "zzz"})
check("geste inconnu : « non chiffré », 0 $", e["total_usd"] == 0.0 and "non chiffré" in e["breakdown"][0]["label"], e)
check("UNE fonction de taux pour toutes les unités (taux_vfx), lue dans DEFAULTS",
      all(V.REGISTRE[m]["prix"] in P.DEFAULTS for m in V.REGISTRE)
      and {V.REGISTRE[m]["unite"] for m in V.REGISTRE} == {"s", "mp", "video", "tranche10s", "effet"})

# ════════════════════════════════════════════════════════════════════════════
print("\n[3] POST /vfx-ia")
_src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("PAYANTES le liste", '("routes", "POST", "/vfx-ia")' in _src)
_rec = RP.recenser()
_k = ("routes", "POST", "/vfx-ia")
check("recensement : la route est gardée et atteint le puits appliquer_vfx",
      _k in _rec and _rec[_k]["garde"] and "appliquer_vfx" in _rec[_k]["puits"], str(_rec.get(_k)))
check("PUITS : appliquer_vfx", "appliquer_vfx" in RP.PUITS)
raz()
d0 = n_depenses()
st, js = call("POST", "/vfx-ia", {"modele": "zzz", "video_filename": "plan.mp4"})
check("geste hors registre -> 400 (avant la clé)", st == 400 and "inconnu" in detail(js), f"{st} {js}")
settings.FAL_KEY = ""
st, js = call("POST", "/vfx-ia", {"modele": "retoucher-kling"})
check("sans FAL_KEY -> 503 qui nomme FAL_KEY, AVANT la vidéo et la description manquantes",
      st == 503 and "FAL_KEY" in detail(js), f"{st} {js}")
st, js = call("POST", "/vfx-ia", {"modele": "retoucher-flux3", "video_filename": "plan.mp4", "prompt": "neige",
                                  "devis": True})
check("sans FAL_KEY, le DEVIS reste servi (le geste sans clé garde son prix : 2 s x 0,03)",
      st == 200 and js.get("devis") is True and abs(js.get("usd", 0) - 0.06) < 1e-6, f"{st} {js}")
settings.FAL_KEY = "test-key"
check("sans clé : ZÉRO ligne depenses, rien envoyé", n_depenses() == d0 and SEAMS["sub"] == [] and SEAMS["up"] == [],
      f"{d0} -> {n_depenses()}")
for corps, code, quoi in (
        ({"modele": "retoucher-kling", "video_filename": "plan4.mp4"}, 400, "kling sans description"),
        ({"modele": "recadrer", "video_filename": "plan.mp4", "options": {"zzz": 1}}, 400, "option inconnue"),
        ({"modele": "recadrer", "video_filename": "plan.mp4", "options": {"aspect_ratio": "2:1"}}, 400, "hors énumération"),
        ({"modele": "recadrer", "video_filename": "plan.mp4", "options": "9:16"}, 400, "options pas un objet"),
        ({"modele": "inserer-h3", "video_filename": "plan4.mp4", "options": {"resume_time": 3}}, 400, "start_time requis"),
        ({"modele": "effets-pixverse", "image_filename": "affiche.png", "options": {"effect": "Effet Inventé"}}, 400,
         "effet hors de l'énumération"),
        ({"modele": "effets-pixverse", "image_filename": "affiche.png",
          "options": {"effect": "Earth Zoom", "duration": "10", "resolution": "1080p"}}, 400, "1080p en 10 s"),
        ({"modele": "relight-h3", "video_filename": "plan.mp4"}, 400, "relight sans image"),
        ({"modele": "effets-pixverse", "options": {"effect": "Earth Zoom"}}, 400, "PixVerse sans image"),
        ({"modele": "agrandir", "video_filename": "plan.mp4", "image_filename": "affiche.png"}, 400,
         "image sur un geste qui n'en prend pas"),
        ({"modele": "agrandir"}, 400, "aucune vidéo"),
        ({"modele": "agrandir", "video_filename": "../plan.mp4"}, 400, "« .. »"),
        ({"modele": "agrandir", "video_filename": "a\\plan.mp4"}, 400, "antislash"),
        ({"modele": "agrandir", "video_filename": "uploads/plan.mp4"}, 400, "séparateur"),
        ({"modele": "agrandir", "video_filename": "C:plan.mp4"}, 400, "lecteur"),
        ({"modele": "agrandir", "video_filename": "plan.txt"}, 400, "extension"),
        ({"modele": "agrandir", "video_filename": "absent.mp4"}, 404, "vidéo absente"),
        ({"modele": "agrandir", "clip_id": "../x"}, 400, "clip_id refusé"),
        ({"modele": "agrandir", "clip_id": "inconnu-123"}, 404, "clip inconnu"),
        ({"modele": "relight-h3", "video_filename": "plan.mp4", "image_filename": "../lumiere.png"}, 400, "image « .. »"),
        ({"modele": "relight-h3", "video_filename": "plan.mp4", "image_filename": "a/lumiere.png"}, 400, "image séparateur"),
        ({"modele": "relight-h3", "video_filename": "plan.mp4", "image_filename": "notes.txt"}, 400, "image extension"),
        ({"modele": "relight-h3", "video_filename": "plan.mp4", "image_filename": "absente.png"}, 404, "image absente"),
        ({"modele": "retoucher-kling", "video_filename": "plan.mp4", "prompt": "x"}, 400, "kling source de 2 s (3 à 15 s)"),
        ({"modele": "retoucher-flux3", "video_filename": "plan.mov", "prompt": "x"}, 400, "flux3 .mov (MP4 seulement)"),
        ({"modele": "jour-nuit", "video_filename": "long21.mp4"}, 400, "LTX : 21 s > 481 images"),
        ({"modele": "relight-h3", "video_filename": "long21.mp4", "image_filename": "lumiere.png"}, 400,
         "relight : 21 s > 15 s"),
        ({"modele": "inserer-h3", "video_filename": "plan4.mp4", "options": {"start_time": 2, "resume_time": 5}}, 400,
         "reprise hors de la vidéo")):
    st, js = call("POST", "/vfx-ia", corps)
    check(f"refus : {quoi} -> {code}", st == code, f"{st} {js}")
st, js = call("POST", "/vfx-ia", {"modele": "retoucher-kling", "video_filename": "plan.mp4", "prompt": "x"})
check("kling : le refus de durée NOMME les bornes", "3 à 15 s" in detail(js), detail(js))
st, js = call("POST", "/vfx-ia", {"modele": "jour-nuit", "video_filename": "long21.mp4"})
check("LTX : le refus nomme 481 images (pas de coupe silencieuse)", "481 images" in detail(js), detail(js))
st, js = call("POST", "/vfx-ia", {"modele": "agrandir", "video_filename": "faux.mp4"})
check("durée illisible (ffprobe rend 0) -> 400 nommé AVANT la garde", st == 400 and "illisible" in detail(js), f"{st} {js}")
st, js = call("POST", "/vfx-ia", {"modele": "agrandir", "video_filename": "faux.mp4", "devis": True})
check("durée illisible : le devis refuse aussi (400), jamais un prix de 0 s", st == 400, f"{st} {js}")
check("refus : zéro ligne depenses, rien envoyé", n_depenses() == d0 and SEAMS["sub"] == [] and SEAMS["up"] == [],
      f"{d0} -> {n_depenses()} {SEAMS}")
# ── un tir complet : FLUX 3, puis la Bibliothèque et le job ────────────────────
st, devis = call("POST", "/vfx-ia", {"modele": "retoucher-flux3", "video_filename": "plan.mp4", "prompt": "neige",
                                     "devis": True})
check("devis flux3, source de 2 s = 0,06 $, rien tiré ni écrit",
      st == 200 and abs(devis.get("usd", -1) - 0.06) < 1e-6 and abs(devis.get("secondes", 0) - 2.0) < 0.1
      and SEAMS["sub"] == [] and n_depenses() == d0 and devis.get("detail"), f"{st} {devis}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "retoucher-flux3", "video_filename": "plan.mp4", "prompt": "neige"})
check("flux3 : la vidéo part (upload), EXACTEMENT {video_url, prompt}",
      st == 200 and SEAMS["up"] == ["plan.mp4"]
      and SEAMS["sub"] == [("blackforestlabs/flux-3/edit-video", {"video_url": "http://fal.test/plan.mp4", "prompt": "neige"})],
      f"{st} {js} {SEAMS}")
check("même chiffre avant (devis) et après (réponse du tir)", st == 200 and js.get("usd") == devis.get("usd"),
      f"{devis.get('usd')} / {js.get('usd') if isinstance(js, dict) else js}")
check("TÉMOIN : la garde passe et écrit UNE ligne depenses", n_depenses() == d0 + 1, f"{d0} -> {n_depenses()}")
_jid = js.get("job_id") if isinstance(js, dict) else None


async def _job(j):
    async with async_session_factory() as s:
        return await s.get(JobRecord, j)
_jr = loop.run_until_complete(_job(_jid)) if _jid else None
check("la vidéo rendue devient un job FINI (provider vfx_ia), son fichier vfxia_* existe",
      _jr is not None and _jr.status == "done" and _jr.provider == "vfx_ia" and js["filename"].startswith("vfxia_")
      and pathlib.Path(_jr.final_video_path).is_file() and _jr.image_filename == js["filename"], f"{js}")
_lc = sqlite3.connect(str(W / "t.db"))
try:
    _lig = _lc.execute("SELECT parent_filename, relation, source, kind, job_id, recette FROM library_assets "
                       "WHERE filename=?", (js.get("filename", ""),)).fetchone()
except sqlite3.OperationalError as _x:
    _lig = (str(_x),)
finally:
    _lc.close()
check("Bibliothèque : la vidéo a pour MÈRE la source (relation vfx_ia, source sonvfx, kind video, job_id)",
      _lig and tuple(_lig[:5]) == ("plan.mp4", "vfx_ia", "sonvfx", "video", _jid), _lig)
check("Bibliothèque : la recette garde le geste, l'endpoint, la description",
      _lig and len(_lig) > 5 and json.loads(_lig[5] or "{}").get("modele") == "retoucher-flux3"
      and json.loads(_lig[5] or "{}").get("endpoint") == "blackforestlabs/flux-3/edit-video"
      and json.loads(_lig[5] or "{}").get("prompt") == "neige", _lig)
# ── Kling par clip_id (le job d'un plan du Montage) ──────────────────────────
_cid = "clip-job-188"


async def _mk_job():
    async with async_session_factory() as s:
        s.add(JobRecord(id=_cid, status="done", progress=100, title="plan", image_filename="plan4.mp4",
                        final_video_path=str(UPLOADS / "plan4.mp4"), video_path=str(UPLOADS / "plan4.mp4")))
        await s.commit()
loop.run_until_complete(_mk_job())
raz()
st, js = call("POST", "/vfx-ia", {"modele": "retoucher-kling", "clip_id": _cid, "prompt": "ciel orageux"})
check("kling par clip_id : EXACTEMENT {keep_audio: True, video_url, prompt} ; 4 s x 0,168 = 0,672 $",
      st == 200 and SEAMS["sub"] == [("fal-ai/kling-video/o3/pro/video-to-video/edit",
                                      {"keep_audio": True, "video_url": "http://fal.test/plan4.mp4",
                                       "prompt": "ciel orageux"})]
      and abs(js.get("usd", 0) - 0.672) < 1e-6, f"{st} {js} {SEAMS['sub']}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "jour-nuit", "video_filename": "plan.mp4"})
check("jour-nuit : num_frames 48 (2 s x 24), 24 i/s, 720p ; 64x64 -> 720x720 x 48 = 25 MP x 0,0024075",
      st == 200 and SEAMS["sub"] == [("fal-ai/ltx-2.3-quality/day-to-night",
                                      {"video_url": "http://fal.test/plan.mp4", "resolution": "720p",
                                       "num_frames": 48, "frames_per_second": 24})]
      and abs(js.get("usd", 0) - 0.0602) < 1e-6, f"{st} {js} {SEAMS['sub']}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "agrandir", "video_filename": "plan.mp4"})
check("agrandir : Proteus x2 ; 64 x2 = 128 de haut -> classe 720p, 1 tranche = 0,10 $",
      st == 200 and SEAMS["sub"] == [("topaz/upscale/video/precision", {"model": "Proteus",
                                                                       "video_url": "http://fal.test/plan.mp4",
                                                                       "upscale_factor": 2})]
      and abs(js.get("usd", 0) - 0.10) < 1e-9, f"{st} {js}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "effacer-objet", "video_filename": "plan.mp4", "prompt": "un mur",
                                  "options": {"mask_prompt": "la chaise", "enable_pass2_refinement": True}})
check("effacer un objet : mask_prompt + passe 2 -> 0,15 $",
      st == 200 and SEAMS["sub"][0][1] == {"video_url": "http://fal.test/plan.mp4", "prompt": "un mur",
                                           "mask_prompt": "la chaise", "enable_pass2_refinement": True}
      and abs(js.get("usd", 0) - 0.15) < 1e-9, f"{st} {js}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "relight-h3", "video_filename": "plan.mp4", "image_filename": "lumiere.png",
                                  "options": {"resolution": "1080P"}})
check("relight : la vidéo PUIS l'image de la lumière partent, reference_image_url ; 2 s x 0,16 (1080P) = 0,32",
      st == 200 and SEAMS["up"] == ["plan.mp4", "lumiere.png"]
      and SEAMS["sub"][0][1] == {"video_url": "http://fal.test/plan.mp4", "reference_image_url": "http://fal.test/lumiere.png",
                                 "resolution": "1080P", "aspect_ratio": "adaptive"}
      and abs(js.get("usd", 0) - 0.32) < 1e-9, f"{st} {js} {SEAMS}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "inserer-h3", "video_filename": "plan4.mp4", "prompt": "un dragon",
                                  "image_filename": "affiche.png",
                                  "options": {"start_time": 2, "resume_time": 3, "duration": 6}})
check("insertion : reference_image_urls (liste), start/resume/duration ; 6 s x 0,06 = 0,36",
      st == 200 and SEAMS["sub"][0][1] == {"video_url": "http://fal.test/plan4.mp4",
                                           "reference_image_urls": ["http://fal.test/affiche.png"],
                                           "prompt": "un dragon", "start_time": 2.0, "resume_time": 3.0,
                                           "duration": 6.0, "resolution": "768p"}
      and abs(js.get("usd", 0) - 0.36) < 1e-9, f"{st} {js} {SEAMS['sub']}")
raz()
st, js = call("POST", "/vfx-ia", {"modele": "effets-pixverse", "image_filename": "affiche.png", "clip_id": _cid,
                                  "options": {"effect": "Earth Zoom", "duration": "8"}})
check("PixVerse : SEULE l'image part (le clip est ignoré), {image_url, effect, duration, resolution} ; 8 s 720p = 0,40",
      st == 200 and SEAMS["up"] == ["affiche.png"]
      and SEAMS["sub"] == [("fal-ai/pixverse/v5.5/effects", {"image_url": "http://fal.test/affiche.png",
                                                             "effect": "Earth Zoom", "duration": "8",
                                                             "resolution": "720p"})]
      and abs(js.get("usd", 0) - 0.40) < 1e-9, f"{st} {js} {SEAMS}")
_lc = sqlite3.connect(str(W / "t.db"))
_lig = _lc.execute("SELECT parent_filename, relation FROM library_assets WHERE filename=?",
                   (js.get("filename", "") if isinstance(js, dict) else "",)).fetchone()
_lc.close()
check("PixVerse : la mère de la vidéo est l'IMAGE animée", _lig == ("affiche.png", "vfx_ia"), _lig)
st, js = call("POST", "/vfx-ia", {"modele": "coloriser", "video_filename": "plan.mp4", "devis": True})
check("colorisation : devis 0 $ « prix à mesurer »", st == 200 and js.get("usd") == 0.0
      and "prix à mesurer" in js.get("detail", ""), f"{st} {js}")
raz()
REPONSE["v"] = {"seed": 3}
st, js = call("POST", "/vfx-ia", {"modele": "agrandir", "video_filename": "plan.mp4"})
check("réponse fal sans vidéo -> 502 nommé (rien rangé)", st == 502 and "aucune vidéo" in detail(js), f"{st} {js}")
_PLAF = R._plafond
OPS = []


async def _plaf_402(op, cat, ref=None):
    OPS.append(op)
    raise HTTPException(402, "stop banc")


R._plafond = _plaf_402
raz()
st, js = call("POST", "/vfx-ia", {"modele": "retoucher-kling", "clip_id": _cid, "prompt": "pluie"})
check("la garde reçoit l'op vfx_ia (durée de la source) et arrête AVANT tout envoi",
      st == 402 and OPS and OPS[-1]["kind"] == "vfx_ia" and OPS[-1]["modele"] == "retoucher-kling"
      and abs(OPS[-1]["secondes"] - 4.0) < 0.1 and SEAMS["up"] == [] and SEAMS["sub"] == [], f"{st} {OPS} {SEAMS}")
R._plafond = _PLAF
check("aucun appel réseau réel (gardes fal_client)", RESEAU["n"] == 0, RESEAU["noms"])

# ════════════════════════════════════════════════════════════════════════════
print("\n[4] écrans (statique)")
_RAC = _ICI.parent.parent
_FR = _RAC / "frontend"
_BUN = (_FR / "dist/assets/index-BEOJX8L5.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_SONV = (_FR / "patches/son-vfx-montage.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_VFXR = (_FR / "patches/vfxrack.js").read_bytes().decode("utf-8").replace("\r\n", "\n")


def _bloc(tag):
    b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    return _BUN.split(b, 1)[1].split(e, 1)[0].strip("\n") if _BUN.count(b) == 1 else ""


check("le bloc SONVFX du bundle EST la source (rafraîchi)", _bloc("SONVFX") == _SONV.lstrip("﻿").strip("\n"))
check("le bloc VFXRACK du bundle EST la source (rafraîchi)", _bloc("VFXRACK") == _VFXR.lstrip("﻿").strip("\n"))
_QS0 = _SONV.find("/* ═══════════ t188 (G6) : le rail « VFX IA » de Son & VFX")
_QSON = _SONV[_QS0:] if _QS0 > 0 else ""
_QV0 = _VFXR.find("/* ── t188 (G6) : VFX IA")
_QVFX = _VFXR[_QV0:] if _QV0 > 0 else ""
check("les queues t188 sont APRÈS la dernière édition G1 de chaque couche",
      _QSON and _QVFX and _SONV.rfind('__dzGl("dz-etat-verrouille")') < _QS0
      and _VFXR.rfind('__dzGlT("dz-action-ajouter",dzT("vfx.pile.ajouter"),"+")') < _QV0, (_QS0, _QV0))
check("Son & VFX : « VFX IA » entre dans SVM_GENS après « VFX particules » (onglet VFX)",
      'SVM_GENS.splice(4,0,{id:"vfxia",name:dzT("vfx.ia.rail"),desc:dzT("vfx.ia.rail_desc"),' in _QSON
      and 'SVM_GEN_TAB.vfxia="vfx";' in _QSON)
check("Son & VFX : le centre monte SvmVfxIa et le bas du rail son panneau quand « VFX IA » est choisi",
      'selGen==="vfxia"?r.jsx(SvmVfxIa,{onNote:fireNote,go:props.go}):selGen==="vfx"?r.jsx(SvmParticles,' in _SONV
      and 'var railBottom=selGen==="vfxia"?svmVfxIaRail():\n    selGen==="voiceover"?' in _SONV)
check("Son & VFX : les gestes en cartes .svm-model (comme le rail Musique)",
      'r.jsxs("button",{className:"svm-model","data-sel":m&&m.id===v.id?"":void 0,"data-dzvfxia":v.id,' in _QSON)
_mrow = _VFXR.find("    matteRow(),r.jsx(VfxIaRack,{clip:clip,onNote:fireNote}),")
check("rack : la section « IA » suit la rangée « Détourer » (matteRow, toujours là)",
      _mrow > 0 and _VFXR.count("matteRow(),") == 1 and 'dzT("vfx.matte.detourer")' in _VFXR)
check("rack : la couche exporte ses aides pour le rail (window.DzVfx.ia), APRÈS l'export du contrat",
      "window.DzVfx.ia={catalogue:vfxIaCatalogue,images:vfxIaImages," in _QVFX
      and _VFXR.find("window.DzVfx.ia=") > _VFXR.find("window.DzVfx={ready:!0,"))
_Q = _QSON + _QVFX
check("le prix et les options viennent du SERVEUR : catalogue /api/vfx-ia/modeles, devis POST /api/vfx-ia devis:true ; "
      "aucun tarif ni effet recopié",
      'fetch("/api/vfx-ia/modeles")' in _QVFX and 'vfxIaPost(Object.assign({devis:!0},corps))' in _QVFX
      and not re.search(r"0\.0024|0\.168|0\.03\b|0\.08\b|Earth Zoom|Proteus|768P", _Q))
check("aucun « disabled » dans les queues (jamais grisé pour une clé ; occupé = data-off)",
      "disabled" not in _Q and '"data-off":busy?"":void 0' in _QVFX and '"data-off":busy?"":void 0' in _QSON)
check("aucun useState ajouté au compteur : hooks par l'alias US=x.useState", "x.useState(" not in _Q
      and _Q.count("var US=x.useState,EF=x.useEffect") == 2)
check("aucun dialogue natif", not re.search(r"\b(alert|confirm|prompt)\(", _Q.replace("vfxIa", "")))
check("compteurs figés du bundle : useState 731, DzTracks 181",
      _BUN.count("x.useState(") == 731 and _BUN.count("DzTracks") == 181,
      (_BUN.count("x.useState("), _BUN.count("DzTracks")))
_DICO = {}
for _f in sorted((_FR / "shared/i18n").glob("*.json")):
    _DICO.update(json.loads(_f.read_text(encoding="utf-8")))
_VFXJ = json.loads((_FR / "shared/i18n/vfx.json").read_text(encoding="utf-8"))
_ids = [m.replace("-", "_") for m in V.REGISTRE]
check("vfx.json : un titre et une phrase par geste (fr ET en), plus vfx.ia.rail",
      all(_VFXJ.get(f"vfx.ia.{i}.{s}", {}).get("fr") and _VFXJ.get(f"vfx.ia.{i}.{s}", {}).get("en")
          for i in _ids for s in ("titre", "phrase")) and _VFXJ.get("vfx.ia.rail", {}).get("en") == "AI VFX")
_cles = sorted(set(re.findall(r'dzT\("(vfx\.ia\.[a-z0-9_.]+)"', _Q)))
check("chaque clé vfx.ia.* des queues est au dictionnaire (fr et en), et chaque clé vfx.ia.* sert",
      _cles and all(c in _VFXJ and _VFXJ[c]["fr"] and _VFXJ[c]["en"] for c in _cles)
      and sorted(k for k in _VFXJ if k.startswith("vfx.ia.")) == _cles,
      sorted(set(_cles) ^ {k for k in _VFXJ if k.startswith("vfx.ia.")}))
check("la phrase de l'écran pour chaque geste existe AUSSI au registre (catalogue, messages)",
      all(V.REGISTRE[m]["phrase"] for m in V.REGISTRE))
_MJ = (_FR / "patches/montage.js").read_text(encoding="utf-8")
check("Montage : le provider vfx_ia rangé dans « Studio » (table des groupes)", 'vfx_ia:"Studio"};' in _MJ)

# ════════════════════════════════════════════════════════════════════════════
print("\n[5] écrans sous node, dans un DOM minimal")
_node = shutil.which("node")
if not _node or not _QSON or not _QVFX:
    check("node présent, queues extraites", False, (_node, len(_QSON), len(_QVFX)))
else:
    _CAT = CI.lister("vfx")
    settings.FAL_KEY = ""
    _CATSANS = CI.lister("vfx")
    settings.FAL_KEY = "test-key"
    _DEVIS = {}
    for _m, _corps in (("retoucher-flux3", {"prompt": "neige"}),
                       ("recadrer", {"options": {"aspect_ratio": "16:9"}}),
                       ("effacer-objet", {"prompt": "un mur", "options": {"mask_prompt": "la chaise"}})):
        _b = dict({"modele": _m, "clip_id": _cid}, **_corps)
        _s, _d = call("POST", "/vfx-ia", dict(_b, devis=True))
        _DEVIS[_m] = _d if _s == 200 else {"erreur": _s}
    _DICO_FR = {k: v for k, v in _DICO.items() if k.startswith(("vfx.", "son.", "ia."))}
    _HARN = r"""
var DICO=__DICO__,CAT=__CAT__,CATSANS=__CATSANS__,DEVIS=__DEVIS__,SANSCLE=false;
function dzT(k,v){var t=(DICO[k]&&DICO[k].fr)||k;for(var x2 in (v||{}))t=t.split('{'+x2+'}').join(String(v[x2]));return t}
var CALLS=[],NOTES=[];
var window={DZ_I18N:DICO,DzVfx:{ready:!0}};   /* l'export du contrat précède la queue (vérifié en [4]) */
function rep(st,js){return Promise.resolve({ok:st<400,status:st,json:function(){return Promise.resolve(js)}})}
function fetch(u,o){o=o||{};var b=o.body?JSON.parse(o.body):null;CALLS.push({u:u,m:o.method||"GET",b:b});
  if(u==="/api/vfx-ia/modeles")return rep(200,{nature:"vfx",modeles:SANSCLE?CATSANS:CAT});
  if(u==="/api/images")return rep(200,{images:[{filename:"vieux.png",mtime:1},{filename:"lumiere.png",mtime:9}]});
  if(u.indexOf("/api/jobs?video=1")===0)return rep(200,[{job_id:"job-1",title:"Plan mer",status:"done",duration_s:4},
    {job_id:"job-2",title:"En cours",status:"running"}]);
  if(u==="/api/vfx-ia"&&SANSCLE&&!b.devis)return rep(503,{detail:"clé FAL_KEY absente : ajoutez-la dans Réglages"});
  if(u==="/api/vfx-ia"&&b.devis)return DEVIS[b.modele]?rep(200,DEVIS[b.modele]):rep(400,{detail:"devis inconnu"});
  if(u==="/api/vfx-ia")return rep(200,{ok:true,modele:b.modele,job_id:"j-new",filename:"vfxia_abcd1234.mp4",usd:(DEVIS[b.modele]||{}).usd});
  return rep(404,{detail:"inconnu "+u})}
/* ── React minimal : éléments, hooks PAR INSTANCE (useState, useEffect [] une fois) ── */
function el(t,p,k){return {t:t,p:p||{},k:k}}
var r={jsx:el,jsxs:el,Fragment:"Fragment"};
function SvmLabel(p){return el("div",{className:"svm-label",children:p.children})}
var CUR=null;
var x={useState:function(i){var I=CUR,k=I.hi++;if(!(k in I.H))I.H[k]=i;
    return [I.H[k],function(v){I.H[k]=typeof v==="function"?v(I.H[k]):v;I.sale=true}]},
  useEffect:function(f,d){var I=CUR,k=I.hi++,s=JSON.stringify(d);if(I.H[k]!==s){I.H[k]=s;I.eff.push(f)}}};
var SVM_GENS=[{id:"music"},{id:"sfx"},{id:"voiceover"},{id:"vfx"},{id:"post"}],SVM_GEN_TAB={music:"audio",vfx:"vfx",post:"post"};
/* ── DOM minimal : l'arbre rendu devient des nœuds, les gestionnaires deviennent des écouteurs ── */
function Noeud(tag){this.tagName=tag;this.attrs={};this.children=[];this.parentNode=null;this.ev={};this.text=""}
Noeud.prototype.appendChild=function(n){n.parentNode=this;this.children.push(n);return n};
Noeud.prototype.getAttribute=function(a){return a in this.attrs?this.attrs[a]:null};
Noeud.prototype.hasAttribute=function(a){return a in this.attrs};
Noeud.prototype.addEventListener=function(t,f){(this.ev[t]=this.ev[t]||[]).push(f)};
Noeud.prototype.dispatchEvent=function(e){var n=this;e.target=e.target||this;
  while(n){(n.ev[e.type]||[]).forEach(function(f){f(e)});if(e.stop)break;n=n.parentNode}};
Noeud.prototype.tous=function(acc){acc=acc||[];this.children.forEach(function(c){acc.push(c);c.tous(acc)});return acc};
Noeud.prototype.qsa=function(f){return this.tous().filter(f)};
Noeud.prototype.textContent=function(){return this.tagName==="#text"?this.text:this.children.map(function(c){return c.textContent()}).join("")};
var EVT={onClick:"click",onChange:"change"};
function construire(n,parent){
  if(n==null||n===false||n===true)return;
  if(Array.isArray(n)){n.forEach(function(c){construire(c,parent)});return}
  if(typeof n!=="object"){var t=new Noeud("#text");t.text=String(n);parent.appendChild(t);return}
  if(typeof n.t==="function"){construire(monterEnfant(n),parent);return}
  if(n.t==="Fragment"){construire(n.p.children,parent);return}
  var d=parent.appendChild(new Noeud(n.t));
  Object.keys(n.p).forEach(function(k){var v=n.p[k];
    if(k==="children")return;
    if(EVT[k]){d.addEventListener(EVT[k],function(e){v(e)});return}
    if(k==="value"){d.value=v;d.attrs.value=String(v);return}
    if(k==="checked"){d.checked=!!v;return}
    if(k==="style")return;
    if(v!==void 0&&v!==null&&v!==false)d.attrs[k==="className"?"class":k]=String(v)});
  construire(n.p.children,d)}
/* les composants enfants gardent leurs hooks d'un rendu à l'autre, par place */
var ENF={},PLACE=0;
function monterEnfant(n){var cle="e"+(PLACE++);var I=ENF[cle];
  if(!I||I.C!==n.t){I=ENF[cle]={H:{},hi:0,eff:[],C:n.t}}
  var sauve=CUR;CUR=I;I.hi=0;var t=n.t(n.p);var e=I.eff;I.eff=[];CUR=sauve;e.forEach(function(f){f()});return t}
function Racine(C,props){this.I={H:{},hi:0,eff:[],C:C};this.props=props}
Racine.prototype.rendre=function(){var I=this.I;CUR=I;I.hi=0;PLACE=0;var t=I.C(this.props);var e=I.eff;I.eff=[];CUR=null;
  e.forEach(function(f){f()});this.dom=new Noeud("racine");construire(t,this.dom);return this.dom};
async function tick(){for(var i=0;i<12;i++)await new Promise(function(res){setImmediate(res)})}
async function cycle(R){R.rendre();await tick();R.rendre();await tick();return R.rendre()}
function cls(c){return function(n){return (" "+(n.attrs["class"]||"")+" ").indexOf(" "+c+" ")>=0}}
function attr(a,v){return function(n){return v===void 0?n.hasAttribute(a):n.attrs[a]===v}}
function cliquer(n){n.dispatchEvent({type:"click"})}
function changer(n,v){n.dispatchEvent({type:"change",target:{value:v,checked:v}})}
var OUT={};
(async function(){
__QVFX__
__QSON__
  /* 1. le rail : la queue sonvfx a inséré « VFX IA » après « VFX particules » */
  OUT.gens=SVM_GENS.map(function(g){return g.id});OUT.tab=SVM_GEN_TAB.vfxia;
  OUT.ia_exporte=!!(window.DzVfx&&window.DzVfx.ia&&window.DzVfx.ia.Champs===VfxIaChamps);
  var R=new Racine(SvmVfxIa,{onNote:function(m){NOTES.push(m)},go:function(v){OUT.go=v}});
  var D=await cycle(R);
  var cartes=D.qsa(cls("svm-model"));
  OUT.cartes=cartes.map(function(c){return c.getAttribute("data-dzvfxia")});
  OUT.textes=cartes.map(function(c){return c.textContent()});
  OUT.sel0=cartes.filter(attr("data-sel")).map(function(c){return c.getAttribute("data-dzvfxia")});
  OUT.source=D.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.source")}).map(function(s){
    return {v:s.value,opts:s.qsa(function(o){return o.tagName==="option"}).map(function(o){return o.attrs.value})}})[0];
  OUT.disabled=D.qsa(attr("disabled")).length;
  /* 2. cliquer la carte FLUX 3 DANS LE DOM : elle se sélectionne, le champ de description apparaît */
  cliquer(D.qsa(attr("data-dzvfxia","retoucher-flux3"))[0]);D=await cycle(R);
  OUT.sel1=D.qsa(cls("svm-model")).filter(attr("data-sel")).map(function(c){return c.getAttribute("data-dzvfxia")});
  OUT.champs1=D.qsa(function(n){return n.tagName==="textarea"||n.tagName==="select"||n.tagName==="input"}).map(function(n){return n.tagName+":"+(n.attrs["aria-label"]||"")});
  var bouton=function(){return D.qsa(cls("svm-nbgold"))[0]};
  OUT.bouton0=bouton().textContent();
  /* sans description : refus côté écran, aucun appel */
  CALLS.length=0;cliquer(bouton());await tick();
  OUT.sans_desc={appels:CALLS.filter(function(c){return c.u==="/api/vfx-ia"}).length,note:NOTES.slice(-1)[0]};
  var ta=D.qsa(function(n){return n.tagName==="textarea"})[0];changer(ta,"neige");D=await cycle(R);
  /* 1er clic : devis seulement */
  CALLS.length=0;cliquer(bouton());await tick();D=await cycle(R);
  OUT.devis_appels=CALLS.filter(function(c){return c.u==="/api/vfx-ia"}).map(function(c){return c.b});
  OUT.bouton1=bouton().textContent();
  OUT.devis_txt=D.qsa(cls("svm-note")).map(function(n){return n.textContent()}).filter(function(t){return t.indexOf("Devis")===0})[0];
  /* 2e clic : le tir, même corps sans devis */
  cliquer(bouton());await tick();D=await cycle(R);
  OUT.tir=CALLS.filter(function(c){return c.u==="/api/vfx-ia"&&!c.b.devis}).map(function(c){return c.b});
  OUT.note_tir=NOTES.slice(-1)[0];
  OUT.resultat=D.qsa(cls("svm-primarybtn")).map(function(n){return n.textContent()});
  cliquer(D.qsa(cls("svm-primarybtn"))[0]);
  /* 3. une saisie qui change DÉSARME le devis */
  CALLS.length=0;cliquer(bouton());await tick();D=await cycle(R);
  ta=D.qsa(function(n){return n.tagName==="textarea"})[0];changer(ta,"pluie");D=await cycle(R);
  cliquer(bouton());await tick();D=await cycle(R);
  OUT.desarme=CALLS.filter(function(c){return c.u==="/api/vfx-ia"}).map(function(c){return !!c.b.devis});
  /* 4. recadrer : l'énumération du SCHÉMA devient un <select>, défaut 9:16 servi */
  cliquer(D.qsa(attr("data-dzvfxia","recadrer"))[0]);D=await cycle(R);
  var fmt=D.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.opt.format")})[0];
  OUT.format={v:fmt&&fmt.value,opts:fmt?fmt.qsa(function(o){return o.tagName==="option"}).map(function(o){return o.attrs.value}):[]};
  changer(fmt,"16:9");D=await cycle(R);CALLS.length=0;cliquer(bouton());await tick();
  OUT.devis_recadrer=CALLS.filter(function(c){return c.u==="/api/vfx-ia"}).map(function(c){return c.b})[0];
  /* 5. PixVerse : part d'une IMAGE (sélecteur d'images, les plus récentes d'abord), effets du schéma servi */
  cliquer(D.qsa(attr("data-dzvfxia","effets-pixverse"))[0]);D=await cycle(R);
  OUT.pix_source=D.qsa(cls("svm-note")).map(function(n){return n.textContent()}).filter(function(t){return t===dzT("vfx.ia.source_image")}).length;
  var im=D.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.image")})[0];
  OUT.pix_images=im?im.qsa(function(o){return o.tagName==="option"}).map(function(o){return o.attrs.value}):[];
  var ef=D.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.opt.effet")+" *"})[0];
  OUT.pix_effets=ef?ef.qsa(function(o){return o.tagName==="option"}).length:0;
  /* la liste est LONGUE : le champ de filtre la réduit (sans casse), le <select> suit */
  var flt=D.qsa(function(n){return n.tagName==="input"&&n.attrs["aria-label"]===dzT("vfx.ia.filtrer")})[0];
  OUT.pix_filtre_ph=flt&&flt.attrs.placeholder;
  changer(flt,"snow");D=await cycle(R);
  ef=D.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.opt.effet")+" *"})[0];
  OUT.pix_filtres=ef.qsa(function(o){return o.tagName==="option"}).map(function(o){return o.attrs.value});
  changer(ef,"It's Snowy");D=await cycle(R);
  flt=D.qsa(function(n){return n.tagName==="input"&&n.attrs["aria-label"]===dzT("vfx.ia.filtrer")})[0];changer(flt,"zoom");D=await cycle(R);
  ef=D.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.opt.effet")+" *"})[0];
  OUT.pix_garde=ef.value+"|"+ef.qsa(function(o){return o.tagName==="option"}).map(function(o){return o.attrs.value}).join(",");
  changer(flt,"");changer(ef,"");D=await cycle(R);
  CALLS.length=0;NOTES.length=0;cliquer(bouton());await tick();
  OUT.pix_manque={appels:CALLS.length,note:NOTES.slice(-1)[0]};
  /* 6. sans FAL_KEY : cartes listées avec la mention, cliquables ; devis servi ; le tir rend le 503 en note */
  SANSCLE=true;VFX_IA.cat=null;VFX_IA.prom=null;ENF={};
  var R2=new Racine(SvmVfxIa,{onNote:function(m){NOTES.push(m)}});var D2=await cycle(R2);
  OUT.sans_textes=D2.qsa(cls("svm-model")).map(function(c){return c.textContent()});
  OUT.sans_disabled=D2.qsa(attr("disabled")).length;
  cliquer(D2.qsa(attr("data-dzvfxia","retoucher-flux3"))[0]);D2=await cycle(R2);
  var ta2=D2.qsa(function(n){return n.tagName==="textarea"})[0];changer(ta2,"neige");D2=await cycle(R2);
  NOTES.length=0;cliquer(D2.qsa(cls("svm-nbgold"))[0]);await tick();D2=await cycle(R2);
  cliquer(D2.qsa(cls("svm-nbgold"))[0]);await tick();D2=await cycle(R2);
  OUT.sans_note=NOTES.slice(-1)[0];
  SANSCLE=false;VFX_IA.cat=null;VFX_IA.prom=null;
  /* 7. le rack : la section IA sur le plan sélectionné (clip_id = son job), gestes vidéo seulement */
  ENF={};var R3=new Racine(VfxIaRack,{clip:{id:"c1",src:{job_id:"clip-job-188"}},onNote:function(m){NOTES.push(m)}});
  var D3=await cycle(R3);
  var gsel=D3.qsa(function(n){return n.tagName==="select"&&n.attrs["aria-label"]===dzT("vfx.ia.geste")})[0];
  OUT.rack_gestes=gsel?gsel.qsa(function(o){return o.tagName==="option"}).map(function(o){return o.attrs.value}):[];
  OUT.rack_titre=D3.qsa(cls("vfx-mlbl")).map(function(n){return n.textContent()})[0];
  changer(gsel,"effacer-objet");D3=await cycle(R3);
  OUT.rack_phrase=D3.qsa(cls("vfx-iaphrase")).map(function(n){return n.textContent()})[0];
  var ta3=D3.qsa(function(n){return n.tagName==="textarea"})[0];changer(ta3,"un mur");D3=await cycle(R3);
  var obj=D3.qsa(function(n){return n.tagName==="input"&&n.attrs["aria-label"]===dzT("vfx.ia.opt.objet")+" *"})[0];
  changer(obj,"la chaise");D3=await cycle(R3);
  CALLS.length=0;cliquer(D3.qsa(cls("vfx-btn"))[0]);await tick();D3=await cycle(R3);
  OUT.rack_devis=CALLS.filter(function(c){return c.u==="/api/vfx-ia"}).map(function(c){return c.b});
  OUT.rack_hint=D3.qsa(cls("vfx-mhint")).map(function(n){return n.textContent()}).filter(function(t){return t.indexOf("Devis")===0})[0];
  cliquer(D3.qsa(cls("vfx-btn"))[0]);await tick();
  OUT.rack_tir=CALLS.filter(function(c){return c.u==="/api/vfx-ia"&&!c.b.devis}).map(function(c){return c.b});
  ENF={};var R4=new Racine(VfxIaRack,{clip:{id:"c2",src:{}},onNote:function(){}});
  OUT.rack_sans_job=R4.rendre().children.length;
  process.stdout.write(JSON.stringify(OUT));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
    _js = (_HARN.replace("__DICO__", json.dumps(_DICO_FR, ensure_ascii=False))
           .replace("__CATSANS__", json.dumps(_CATSANS, ensure_ascii=False))
           .replace("__CAT__", json.dumps(_CAT, ensure_ascii=False))
           .replace("__DEVIS__", json.dumps(_DEVIS, ensure_ascii=False))
           .replace("__QVFX__", _QVFX).replace("__QSON__", _QSON))
    _fjs = W / "ecran_vfx_ia.js"
    _fjs.write_text(_js, encoding="utf-8")
    _p = subprocess.run([_node, str(_fjs)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=120)
    try:
        O = json.loads(_p.stdout)
    except Exception:  # noqa: BLE001
        O = {"erreur": (_p.stdout + _p.stderr)[-1500:]}
    check("les deux queues s'exécutent sous node", "erreur" not in O, O.get("erreur"))
    if "erreur" not in O:
        _fl = _DEVIS["retoucher-flux3"]
        check("rail : « VFX IA » inséré après « VFX particules », onglet VFX",
              O["gens"] == ["music", "sfx", "voiceover", "vfx", "vfxia", "post"] and O["tab"] == "vfx", O["gens"])
        check("LIAISON des couches : le rail monte avec les aides EXPORTÉES par le rack (window.DzVfx.ia)",
              O["ia_exporte"] is True)
        check("rail : les 12 gestes en cartes .svm-model dans le DOM, le premier choisi",
              O["cartes"] == list(V.REGISTRE) and O["sel0"] == ["relight-h3"], O["cartes"])
        check("chaque carte : titre traduit, prix du serveur avec unité (le MP LTX en entier : $0.0024075, jamais « $0.002 »), phrase",
              O["textes"][0].startswith("Rééclairer$0.08/s") and "donnez une image de la lumière" in O["textes"][0]
              and "$0.0024075/MP" in O["textes"][4] and "$0.1/10 s" not in O["textes"][10]
              and "$0.10/10 s" in O["textes"][10] and "$0.20/5 s" in O["textes"][11]
              and "prix à mesurer" in O["textes"][6], O["textes"])
        check("source : les vidéos TERMINÉES de la Bibliothèque, la première choisie",
              O["source"] == {"v": "job-1", "opts": ["job-1"]}, O["source"])
        check("aucun élément disabled dans le rail", O["disabled"] == 0, O["disabled"])
        check("clic DOM sur la carte FLUX 3 : elle se sélectionne, la description apparaît",
              O["sel1"] == ["retoucher-flux3"] and O["champs1"][-1] == "textarea:Description", (O["sel1"], O["champs1"]))
        check("sans description : refus nommé côté écran, AUCUN appel",
              O["sans_desc"]["appels"] == 0 and O["sans_desc"]["note"] == "Décrivez d'abord le changement voulu.",
              O["sans_desc"])
        check("1er clic : UN devis (devis:true, clip_id = le job choisi, modèle, description, options vides)",
              O["devis_appels"] == [{"devis": True, "modele": "retoucher-flux3", "clip_id": "job-1", "prompt": "neige",
                                     "options": {}}] and O["bouton1"] == "Lancer pour de bon", O["devis_appels"])
        check("le devis s'affiche : LE chiffre du serveur et son détail",
              O["devis_txt"] == f"Devis : $0.12 — {_fl['detail']} · cliquer encore pour lancer", O["devis_txt"])
        check("2e clic : UN tir, même corps sans devis ; la note redit le MÊME chiffre",
              O["tir"] == [{"modele": "retoucher-flux3", "clip_id": "job-1", "prompt": "neige", "options": {}}]
              and O["note_tir"] == "Vidéo ajoutée à la Bibliothèque (Rendus) : vfxia_abcd1234.mp4 ($0.12)",
              (O["tir"], O["note_tir"]))
        check("après le tir : « Ouvrir le Montage » mène au Montage", O["resultat"] == ["Ouvrir le Montage"]
              and O.get("go") == "montage", (O["resultat"], O.get("go")))
        check("une saisie modifiée DÉSARME : devis, puis nouveau devis (aucun tir sur l'ancien chiffre)",
              O["desarme"] == [True, True], O["desarme"])
        check("recadrer : l'énumération du schéma en <select>, défaut 9:16 du serveur ; le choix part en options",
              O["format"] == {"v": "9:16", "opts": ["1:1", "4:5", "5:4", "9:16", "16:9"]}
              and (O["devis_recadrer"] or {}).get("options") == {"aspect_ratio": "16:9"}, (O["format"], O["devis_recadrer"]))
        check("PixVerse : « part d'une image », images récentes d'abord, les 154 effets servis (+ « Choisir… »)",
              O["pix_source"] == 1 and O["pix_images"] == ["", "lumiere.png", "vieux.png"] and O["pix_effets"] == 155,
              (O["pix_source"], O["pix_images"], O["pix_effets"]))
        check("PixVerse : un filtre au-dessus de la longue liste (« Filtrer les 154 choix… »), sans casse",
              O["pix_filtre_ph"] == "Filtrer les 154 choix…"
              and O["pix_filtres"] == ["", "It's Snowy", "Snow Globe Maker"], (O["pix_filtre_ph"], O["pix_filtres"]))
        check("PixVerse : le choix courant reste dans la liste filtrée (« It's Snowy » sous le filtre « zoom »)",
              O["pix_garde"] == "It's Snowy|,Eye Zoom Challenge,Earth Zoom,It's Snowy,Art Zoom Challenge,Hitchcock Dolly Zoom",
              O["pix_garde"])
        check("PixVerse sans image : refus nommé, aucun appel", O["pix_manque"]["appels"] == 0
              and O["pix_manque"]["note"] == "Choisissez l'image à animer.", O["pix_manque"])
        check("sans FAL_KEY : chaque carte garde son prix ET dit « clé FAL_KEY à ajouter dans Réglages », rien de grisé",
              all("clé FAL_KEY à ajouter dans Réglages" in t for t in O["sans_textes"]) and len(O["sans_textes"]) == 12
              and O["sans_disabled"] == 0 and "$0.03/s" in O["sans_textes"][8], O["sans_textes"][:2])
        check("sans FAL_KEY : le clic va jusqu'au serveur, qui refuse en 503 — la note le dit",
              (O["sans_note"] or "").startswith("Échec : clé FAL_KEY"), O["sans_note"])
        check("rack : section « IA », les 11 gestes qui partent d'une VIDÉO (PixVerse reste au rail)",
              O["rack_titre"] == "IA" and O["rack_gestes"] == [m for m in V.REGISTRE if m != "effets-pixverse"],
              (O["rack_titre"], O["rack_gestes"]))
        check("rack : la phrase du geste sous le sélecteur", O["rack_phrase"] == _VFXJ["vfx.ia.effacer_objet.phrase"]["fr"],
              O["rack_phrase"])
        check("rack : 1er clic = devis sur clip_id = le job du plan, objet à effacer en options",
              O["rack_devis"] == [{"devis": True, "modele": "effacer-objet", "clip_id": "clip-job-188",
                                   "prompt": "un mur", "options": {"mask_prompt": "la chaise"}}], O["rack_devis"])
        check("rack : le devis affiché = celui du serveur (0,10 $ : 0,05 + masque SAM 3)",
              (O["rack_hint"] or "").startswith("Devis : $0.10 — ") and abs(_DEVIS["effacer-objet"]["usd"] - 0.10) < 1e-9,
              O["rack_hint"])
        check("rack : 2e clic = le tir", O["rack_tir"] == [{"modele": "effacer-objet", "clip_id": "clip-job-188",
                                                          "prompt": "un mur", "options": {"mask_prompt": "la chaise"}}],
              O["rack_tir"])
        check("rack : un plan sans job (pas une vidéo rendue) n'a pas de section IA", O["rack_sans_job"] == 0,
              O["rack_sans_job"])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
