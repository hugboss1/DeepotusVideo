"""t182 / G0 — catalogue unique « deux voies » et nouveaux modèles d'image fal.

Ce que le banc tient :
  [0] catalogue_ia.lister("image") rend TOUTES les entrées image, chacune avec
      voie, cle, dispo, usd (float), unite, jumeau, label ; les jumeaux sont
      symétriques et de voies différentes (gpt-image-2 <-> gpt-image-2-fal…) ;
  [1] dispo suit la clé : sans OPENAI_API_KEY, les ids openai sont dispo=False
      mais PRÉSENTS ; sans FAL_KEY, les ids fal idem ;
  [2] les nouveaux ids fal (nano-banana-2.1, flux-3, seedream-5-pro,
      ideogram-4.5, qwen-image-3, recraft-4.1-vecteur) sont dans PROVIDERS,
      la table de prix (avec LEUR clé de prix : jamais le repli FLUX) ; les
      raster dans pricing._IMAGE_MODELS et le `models` de /image-models
      (t183 : la couche dz-champ-ia n'a plus de miroir CATALOGUE_IMAGE, elle lit
      `tous`) ; recraft (SVG) dans pricing._IMAGE_MODELS_VECTEUR et NULLE PART
      côté raster (ni _IMAGE_MODELS, ni IP.available()) ; les ids raster sont
      dans material_store.MODELS et MODEL_COST/MODEL_SEC de materialforge ;
      recraft (SVG) n'est PAS une texture : absent de material_store et
      écarté du sélecteur de materialforge ; gpt-image-1-mini est dans
      PROVIDERS ;
  [3] build_fal_image_request vise le bon endpoint et la bonne forme de taille
      (aspect_ratio / image_size / resolution) pour t2i et edit, sans
      `num_images` là où le schéma fal n'en a pas (flux-3, recraft), avec
      `image_url` (singulier) pour l'edit d'ideogram ; recraft refuse l'edit ;
  [4b] /images/generate model=recraft SANS sortie="svg" -> 400 avant toute
      dépense (aucun tir) ; AVEC sortie="svg" -> _fal_image_generate ;
  [4] /images/generate avec un nouvel id part par IP._fal_image_generate
      (espion), jamais par OpenAI ni FLUX ni Nano Banana ;
      /images/process op=edit avec flux-3 idem, AVEC l'image source ;
  [5] /image-models garde `models` filtré (compat) et ajoute `tous` (toutes
      les entrées, champs de [0]) ; chaque entrée de `models` porte voie, cle,
      usd ; GET /ia/catalogue?nature=image idem ; nature inconnue -> 400 ;
  [5b] recraft absent de `models`, présent dans `tous` avec sortie="svg" ;
      toutes les autres entrées sortie="raster" ;
  [6] un prix inconnu (clé de prix à 0) donne usd=0.0 et `note` = le CODE
      "a_mesurer" (traduit par le front) ; un prix connu n'a pas de note ;
  [2c] dérives entre registres : FAL_IMAGES ⊂ PROVIDERS (FAL_KEY), ids svg de
      FAL_IMAGES == _IMAGE_MODELS_VECTEUR, tables de prix ⊂ PROVIDERS ∪ {flux}
      et disjointes, `sortie`/`edit` du catalogue = est_vectoriel / FAL_IMAGES ;
  [4c] /images/process op=edit avec recraft -> 400 AVANT la garde de dépense :
      aucun tir, ZÉRO ligne `depenses` écrite (témoin : un edit flux-3 en
      écrit une) ; la façade IP.generate refuse recraft sans sortie="svg" ;
  [7] la VRAIE couture _fal_image_generate (fal_client.subscribe_async,
      téléversement et _download remplacés par des enregistreurs) : flux-3
      n=3 -> 3 tirs, seedream n=3 -> 1 tir num_images=3, extension .svg pour
      recraft et .png sinon, RuntimeError sans image, recraft + référence ->
      ValueError sans téléversement, références plafonnées à REF_MAX.

AUCUN appel réel : `_fal_image_generate` (sauf en [7]), `_openai_generate`,
`_banana_generate`, `_fal_gpt_generate` et `routes._flux_generate` sont des
espions ; `fal_client.*` et tout `httpx.AsyncClient.post` hors du client de
test sont des gardes qui COMPTENT.

Run: & $PY tests/test_catalogue_ia.py   (un processus, depuis backend/)
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="catia_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ["FAL_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-oa"
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
           "HEYGEN_API_KEY", "MESHY_API_KEY"):
    os.environ.pop(_k, None)
Path(TMP, "images").mkdir(parents=True, exist_ok=True)
Path(TMP, "outputs").mkdir(parents=True, exist_ok=True)
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import fal_client                                                # noqa: E402
import httpx                                                     # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402
from PIL import Image                                            # noqa: E402

from app.config import settings                                  # noqa: E402

settings.ELEVENLABS_API_KEY = ""

from app.main import app                                         # noqa: E402
from app.services import catalogue_ia as CI                      # noqa: E402
from app.services import image_providers as IP                   # noqa: E402
from app.services import pricing as P                            # noqa: E402
from app.services import material_store as MS                    # noqa: E402
from app.services.storage import init_db                         # noqa: E402
from app.api import routes as R                                  # noqa: E402

ok = fail = 0
_plantages = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def temoin(e):
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


NOUVEAUX = ["nano-banana-2.1", "flux-3", "seedream-5-pro", "ideogram-4.5",
            "qwen-image-3", "recraft-4.1-vecteur"]
RASTER = [i for i in NOUVEAUX if i != "recraft-4.1-vecteur"]

# ── gardes réseau : tout appel est COMPTÉ et refusé ─────────────────────────
RESEAU = {"n": 0, "noms": []}


def _garde(nom):
    async def _refus(*a, **k):
        RESEAU["n"] += 1
        RESEAU["noms"].append(nom)
        raise RuntimeError(f"GARDE RESEAU : {nom} appelé dans un banc")
    return _refus


for _nom in ("submit_async", "subscribe_async", "run_async",
             "upload_file_async", "upload_async", "upload_image_async"):
    setattr(fal_client, _nom, _garde(_nom))

_vrai_post = httpx.AsyncClient.post


async def _post_garde(self, url, *a, **k):
    if str(getattr(self, "base_url", "")).startswith("http://t"):
        return await _vrai_post(self, url, *a, **k)
    RESEAU["n"] += 1
    RESEAU["noms"].append(f"httpx.post {url}")
    raise RuntimeError(f"GARDE RESEAU : httpx.post {url}")

httpx.AsyncClient.post = _post_garde

# ── espions ─────────────────────────────────────────────────────────────────
ESP = {"falimg": [], "interdit": []}


def _png():
    name = f"esp_{os.urandom(4).hex()}.png"
    Image.new("RGB", (64, 64), (120, 90, 60)).save(settings.images_path / name)
    return name


async def _esp_falimg(model, prompt, size, n, image_paths=None, **kw):
    ESP["falimg"].append({"model": model, "size": size, "n": n,
                          "images": list(image_paths or [])})
    return [_png()]


def _interdit(nom):
    async def _f(*a, **k):
        ESP["interdit"].append(nom)
        raise AssertionError(f"voie interdite : {nom}")
    return _f


_VRAIE_FALIMG = IP._fal_image_generate          # pour [7]
IP._fal_image_generate = _esp_falimg
IP._openai_generate = _interdit("openai")
IP._banana_generate = _interdit("banana")
IP._fal_gpt_generate = _interdit("falgpt")
R._flux_generate = _interdit("flux")


def reset():
    for k in ESP:
        ESP[k].clear()


SRC = "source.png"
Image.new("RGB", (128, 128), (10, 20, 30)).save(settings.images_path / SRC)

asyncio.run(init_db())


async def _req(meth, path, body=None, params=None):
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://t") as c:
        if meth == "GET":
            return await c.get("/api" + path, params=params)
        if meth == "PUT":
            return await c.put("/api" + path, json=body)
        return await c.post("/api" + path, json=body)


def call(meth, path, body=None, params=None):
    try:
        r = asyncio.run(_req(meth, path, body, params))
        try:
            js = r.json()
        except Exception:
            js = {"_texte": r.text}
        return r.status_code, js
    except Exception as e:  # noqa: BLE001
        return -1, {"_temoin": temoin(e)}


CHAMPS = ("voie", "cle", "dispo", "usd", "unite", "jumeau", "label", "sortie")

# ── [0] lister('image') ─────────────────────────────────────────────────────
print("[0] lister('image')")
img = CI.lister("image")
ids = {e["id"] for e in img}
check("TÉMOIN : au moins 17 entrées image (11 d'avant + 6)", len(img) >= 17, str(len(img)))
_REG = set(P._IMAGE_MODELS) | set(P._IMAGE_MODELS_VECTEUR)
check("ids = pricing._IMAGE_MODELS + _IMAGE_MODELS_VECTEUR (une seule source)", ids == _REG,
      str(ids ^ _REG))
for e in img:
    check(f"{e['id']} a ses champs", all(k in e for k in CHAMPS), str(e))
    check(f"{e['id']} usd float", isinstance(e.get("usd"), float), repr(e.get("usd")))
jumeaux = [e for e in img if e["jumeau"]]
check("TÉMOIN : au moins trois paires de jumeaux (six entrées jumelées)", len(jumeaux) >= 6, str(len(jumeaux)))
for e in jumeaux:
    j = next((x for x in img if x["id"] == e["jumeau"]), None)
    check(f"jumeau symétrique {e['id']}", j is not None and j["jumeau"] == e["id"]
          and j["voie"] != e["voie"], str(j))
par_id = {e["id"]: e for e in img}
check("gpt-image-2 <-> gpt-image-2-fal", par_id["gpt-image-2"]["jumeau"] == "gpt-image-2-fal")
check("flux-3 sans jumeau, voie fal, clé FAL_KEY", par_id["flux-3"]["jumeau"] is None
      and par_id["flux-3"]["voie"] == "fal" and par_id["flux-3"]["cle"] == "FAL_KEY", str(par_id["flux-3"]))
check("gpt-image-1-mini voie openai, clé OPENAI_API_KEY",
      par_id["gpt-image-1-mini"]["voie"] == "openai"
      and par_id["gpt-image-1-mini"]["cle"] == "OPENAI_API_KEY", str(par_id["gpt-image-1-mini"]))

# ── [1] dispo suit la clé ───────────────────────────────────────────────────
print("[1] dispo suit la clé")
settings.OPENAI_API_KEY = ""
img2 = {e["id"]: e for e in CI.lister("image")}
check("gpt-image-2 présent sans clé", "gpt-image-2" in img2)
check("gpt-image-2 dispo=False sans clé", img2["gpt-image-2"]["dispo"] is False, str(img2["gpt-image-2"]))
check("gpt-image-2-fal reste dispo", img2["gpt-image-2-fal"]["dispo"] is True)
settings.OPENAI_API_KEY = "test-oa"
settings.FAL_KEY = ""
img3 = {e["id"]: e for e in CI.lister("image")}
check("flux-3 présent sans FAL_KEY", "flux-3" in img3)
check("flux-3 dispo=False sans FAL_KEY", img3["flux-3"]["dispo"] is False)
check("gpt-image-2 dispo=True (sa clé est là)", img3["gpt-image-2"]["dispo"] is True)
settings.FAL_KEY = "test-key"

# ── [2] registres alignés ───────────────────────────────────────────────────
print("[2] registres alignés")
cat_js = (ICI.parent.parent / "frontend/shared/dz-champ-ia.js").read_text(encoding="utf-8")
# t183 (G1) : plus de miroir codé en dur dans la couche — elle lit `tous` (raster) de /image-models
check("dz-champ-ia sans miroir CATALOGUE_IMAGE, lit `tous` raster",
      "CATALOGUE_IMAGE" not in cat_js and "d.tous" in cat_js and 'e.sortie !== "svg"' in cat_js)
mf = (ICI.parent.parent / "frontend/materialforge/materialforge.js").read_text(encoding="utf-8")


def bloc(nom):
    mm = re.search(r"const " + nom + r"\s*=\s*\{(.*?)\};", mf, re.S)
    return mm.group(1) if mm else ""


for i in NOUVEAUX:
    meta = IP.PROVIDERS.get(i) or {}
    check(f"{i} dans PROVIDERS (FAL_KEY)", meta.get("needs") == "FAL_KEY", repr(meta))
    spec = (P._IMAGE_MODELS_VECTEUR if i == "recraft-4.1-vecteur" else P._IMAGE_MODELS).get(i)
    check(f"{i} dans sa table de prix, voie fal, clé de prix connue", bool(spec) and spec[1] == "fal"
          and spec[2] in P.DEFAULTS, repr(spec))
    devis = P.estimate({"kind": "image", "model": i, "n": 1})
    check(f"{i} devis = SA clé (pas le repli FLUX)",
          abs(devis["total_usd"] - float(P.DEFAULTS.get(spec[2] if spec else "", -1))) < 1e-9
          and spec[0] in devis["breakdown"][0].get("label", ""), repr(devis))
    check(f"{i} dans lister", i in ids)
    check(f"{i} passe par la façade", IP.via_facade(i))
for i in RASTER:
    check(f"{i} dans _IMAGE_MODELS (raster)", i in P._IMAGE_MODELS)
    check(f"{i} dans material_store", i in MS.MODELS and MS.clean_model(i) == i)
    # t183 : MODEL_COST supprimé (crédit = usd du catalogue) ; MODEL_SEC garde les durées indicatives
    check(f"MODEL_SEC {i}", re.search(r'"' + re.escape(i) + r'"\s*:\s*\d', bloc("MODEL_SEC")) is not None)
check("recraft (SVG) n'est PAS une texture : absent de material_store",
      "recraft-4.1-vecteur" not in MS.MODELS)
check("recraft hors des registres raster : ni _IMAGE_MODELS ni la couche dz-champ-ia",
      "recraft-4.1-vecteur" not in P._IMAGE_MODELS and "recraft" not in cat_js)
settings.FAL_KEY = "test-key"
check("recraft hors de IP.available() (générateurs des planches)",
      "recraft-4.1-vecteur" not in [x["id"] for x in IP.available()]
      and "flux-3" in [x["id"] for x in IP.available()])
check("materialforge écarte les modèles vectoriels de son sélecteur (champ sortie)",
      re.search(r"\.filter\(\(m\) => m\.sortie !== \"svg\"\)", mf) is not None)

# ── [2c] dérives entre registres ────────────────────────────────────────────
print("[2c] dérives entre registres")
check("FAL_IMAGES ⊂ PROVIDERS", set(IP.FAL_IMAGES) <= set(IP.PROVIDERS),
      str(set(IP.FAL_IMAGES) - set(IP.PROVIDERS)))
check("chaque id de FAL_IMAGES exige FAL_KEY",
      all(IP.PROVIDERS[i]["needs"] == "FAL_KEY" for i in IP.FAL_IMAGES if i in IP.PROVIDERS))
_svg = {i for i in IP.FAL_IMAGES if IP.est_vectoriel(i)}
check("ids svg de FAL_IMAGES == _IMAGE_MODELS_VECTEUR", _svg == set(P._IMAGE_MODELS_VECTEUR),
      str(_svg ^ set(P._IMAGE_MODELS_VECTEUR)))
check("TÉMOIN : au moins un id svg", len(_svg) >= 1)
check("tables de prix ⊂ PROVIDERS ∪ {flux}",
      (set(P._IMAGE_MODELS) | set(P._IMAGE_MODELS_VECTEUR)) <= (set(IP.PROVIDERS) | {"flux"}),
      str((set(P._IMAGE_MODELS) | set(P._IMAGE_MODELS_VECTEUR)) - set(IP.PROVIDERS) - {"flux"}))
check("_IMAGE_MODELS et _IMAGE_MODELS_VECTEUR disjoints",
      not (set(P._IMAGE_MODELS) & set(P._IMAGE_MODELS_VECTEUR)))
_cat = CI.lister("image")
check("sortie du catalogue = est_vectoriel",
      all(e["sortie"] == ("svg" if IP.est_vectoriel(e["id"]) else "raster") for e in _cat),
      str([(e["id"], e["sortie"]) for e in _cat if e["sortie"] != ("svg" if IP.est_vectoriel(e["id"]) else "raster")]))
check("edit du catalogue = FAL_IMAGES (True hors FAL_IMAGES)",
      all(e["edit"] is (bool(IP.FAL_IMAGES[e["id"]]["edit"]) if e["id"] in IP.FAL_IMAGES else True) for e in _cat))
check("recraft : sortie svg, edit False",
      any(e["id"] == "recraft-4.1-vecteur" and e["sortie"] == "svg" and e["edit"] is False for e in _cat))
# t184 (G2) : les natures vidéo s'ajoutent (image -> vidéo, first-last-frame)
check("natures() publiques = détourage (t186), image, musique, sfx_texte, sfx_video (t187), objets3d (t189), vfx (t188), vidéo",
      CI.natures() == ("detourage_image", "detourage_video", "image", "musique", "objets3d", "sfx_texte", "sfx_video",
                       "vfx", "video_fl", "video_i2v"), str(CI.natures()))
check("gpt-image-1-mini dans PROVIDERS (OPENAI_API_KEY)",
      (IP.PROVIDERS.get("gpt-image-1-mini") or {}).get("needs") == "OPENAI_API_KEY")
check("gpt-image-1-mini hors façade (chemin OpenAI des routes)", not IP.via_facade("gpt-image-1-mini"))

# ── [3] requêtes fal pures ──────────────────────────────────────────────────
print("[3] requêtes fal pures")
ep, a = IP.build_fal_image_request("flux-3", "un chat", "portrait_16_9", [])
check("flux-3 t2i endpoint", ep == "blackforestlabs/flux-3/text-to-image", ep)
check("flux-3 aspect 9:16 + 1k", a.get("aspect_ratio") == "9:16" and a.get("resolution") == "1k", str(a))
ep, a = IP.build_fal_image_request("flux-3", "un chat", "square", ["https://x/a.png"], n=3)
check("flux-3 edit endpoint + image_urls", ep == "blackforestlabs/flux-3/edit-image"
      and a.get("image_urls") == ["https://x/a.png"], str((ep, a)))
check("flux-3 sans num_images (absent du schéma fal)", "num_images" not in a, str(a))
ep, a = IP.build_fal_image_request("seedream-5-pro", "x", "landscape_16_9", [], n=2)
check("seedream t2i image_size + num_images", ep == "bytedance/seedream/v5/pro/text-to-image"
      and a.get("image_size") == "landscape_16_9" and a.get("num_images") == 2, str((ep, a)))
ep, a = IP.build_fal_image_request("seedream-5-pro", "x", "inconnu", ["u"])
check("seedream edit, taille inconnue -> square_hd", ep == "bytedance/seedream/v5/pro/edit"
      and a.get("image_size") == "square_hd" and a.get("image_urls") == ["u"], str((ep, a)))
ep, a = IP.build_fal_image_request("nano-banana-2.1", "x", "square_hd", [])
check("nano 2.1 aspect 1:1 + 1K", ep == "google/nano-banana-2.1" and a.get("aspect_ratio") == "1:1"
      and a.get("resolution") == "1K", str((ep, a)))
ep, a = IP.build_fal_image_request("nano-banana-2.1", "x", "square_hd", ["u1", "u2"])
check("nano 2.1 edit", ep == "google/nano-banana-2.1/edit" and a.get("image_urls") == ["u1", "u2"], str((ep, a)))
ep, a = IP.build_fal_image_request("ideogram-4.5", "x", "portrait_4_3", [])
check("ideogram t2i image_size + quality high", ep == "ideogram/v4.5"
      and a.get("image_size") == "portrait_4_3" and a.get("quality") == "high", str((ep, a)))
ep, a = IP.build_fal_image_request("ideogram-4.5", "x", "portrait_4_3", ["u1", "u2"])
check("ideogram edit : image_url SINGULIER + références", ep == "ideogram/v4.5/edit"
      and a.get("image_url") == "u1" and a.get("reference_image_urls") == ["u2"]
      and "image_urls" not in a, str((ep, a)))
ep, a = IP.build_fal_image_request("qwen-image-3", "x", "landscape_4_3", [])
check("qwen t2i", ep == "alibaba/qwen-image-3/text-to-image" and a.get("image_size") == "landscape_4_3", str((ep, a)))
ep, a = IP.build_fal_image_request("recraft-4.1-vecteur", "x", "square", [], n=2)
check("recraft t2i, sans num_images", ep == "fal-ai/recraft/v4.1/text-to-vector"
      and a.get("image_size") == "square" and "num_images" not in a, str((ep, a)))
try:
    IP.build_fal_image_request("recraft-4.1-vecteur", "x", "square", ["https://x/a.png"])
    check("recraft refuse l'edit", False)
except ValueError:
    check("recraft refuse l'edit", True)

# ── [4] routage ─────────────────────────────────────────────────────────────
print("[4] routage")
for mid in RASTER:
    reset()
    st, js = call("POST", "/images/generate", {"prompt": "chat", "n": 1, "model": mid})
    check(f"generate {mid} 200", st == 200 and js.get("model") == mid, f"{st} {js}")
    check(f"{mid} passé par _fal_image_generate", [x["model"] for x in ESP["falimg"]] == [mid], str(ESP))
    check(f"{mid} ni OpenAI ni FLUX ni Banana", ESP["interdit"] == [], str(ESP["interdit"]))
reset()
st, js = call("POST", "/images/process", {"op": "edit", "filename": SRC, "prompt": "en bleu", "model": "flux-3"})
check("process edit flux-3 200", st == 200 and js.get("model") == "flux-3", f"{st} {js}")
check("edit flux-3 par _fal_image_generate AVEC la source",
      len(ESP["falimg"]) == 1 and len(ESP["falimg"][0]["images"]) == 1
      and Path(str(ESP["falimg"][0]["images"][0])).name == SRC, str(ESP))
check("edit flux-3 ni Kontext ni OpenAI", ESP["interdit"] == [], str(ESP["interdit"]))
reset()
settings.FAL_KEY = ""
st, js = call("POST", "/images/generate", {"prompt": "chat", "n": 1, "model": "flux-3"})
check("sans FAL_KEY : 503 qui nomme la clé, aucun tir", st == 503 and "FAL_KEY" in str(js)
      and ESP["falimg"] == [], f"{st} {js}")
settings.FAL_KEY = "test-key"

# ── [4b] recraft : SVG sur demande seulement ────────────────────────────────
print("[4b] recraft vectoriel")
reset()
st, js = call("POST", "/images/generate", {"prompt": "logo", "n": 1, "model": "recraft-4.1-vecteur"})
check("recraft sans sortie=svg -> 400 Vectorlab", st == 400 and "Vectorlab" in str(js), f"{st} {js}")
check("recraft refusé : aucun tir", ESP["falimg"] == [] and ESP["interdit"] == [], str(ESP))
reset()
st, js = call("POST", "/images/generate", {"prompt": "logo", "n": 1, "model": "recraft-4.1-vecteur", "sortie": "raster"})
check("recraft sortie=raster -> 400", st == 400 and ESP["falimg"] == [], f"{st} {js}")
reset()
st, js = call("POST", "/images/generate", {"prompt": "logo", "n": 1, "model": "recraft-4.1-vecteur", "sortie": "svg"})
check("recraft sortie=svg -> 200", st == 200 and js.get("model") == "recraft-4.1-vecteur", f"{st} {js}")
check("recraft sortie=svg passe par _fal_image_generate",
      [x["model"] for x in ESP["falimg"]] == ["recraft-4.1-vecteur"] and ESP["interdit"] == [], str(ESP))

# ── [4c] recraft en retouche : refus AVANT la garde de dépense ──────────────
print("[4c] recraft en retouche, façade")
import sqlite3                                                   # noqa: E402


def n_depenses():
    con = sqlite3.connect(TMP + "/t.db")
    try:
        return con.execute("SELECT COUNT(*) FROM depenses").fetchone()[0]
    finally:
        con.close()


reset()
d0 = n_depenses()
st, js = call("POST", "/images/process", {"op": "edit", "filename": SRC, "prompt": "en bleu",
                                          "model": "recraft-4.1-vecteur"})
check("process edit recraft -> 400 « pas de retouche »", st == 400 and "pas de retouche" in str(js), f"{st} {js}")
check("process edit recraft : aucun tir", ESP["falimg"] == [] and ESP["interdit"] == [], str(ESP))
check("process edit recraft : ZÉRO ligne depenses écrite", n_depenses() == d0, f"{d0} -> {n_depenses()}")
reset()
st, js = call("POST", "/images/process", {"op": "variations", "filename": SRC, "model": "recraft-4.1-vecteur"})
check("process variations recraft -> 400, zéro dépense", st == 400 and n_depenses() == d0
      and ESP["falimg"] == [], f"{st} {js}")
reset()
st, js = call("POST", "/images/process", {"op": "edit", "filename": SRC, "prompt": "en bleu", "model": "flux-3"})
check("TÉMOIN : un edit flux-3 écrit bien une ligne depenses", st == 200 and n_depenses() == d0 + 1,
      f"{st} {d0} -> {n_depenses()}")
reset()
try:
    asyncio.run(IP.generate("recraft-4.1-vecteur", "logo", "square", 1))
    check("façade : recraft sans sortie=svg -> RuntimeError", False)
except RuntimeError as e:
    check("façade : recraft sans sortie=svg -> RuntimeError", "Vectorlab" in str(e) and ESP["falimg"] == [], str(e))
out = asyncio.run(IP.generate("recraft-4.1-vecteur", "logo", "square", 1, sortie="svg"))
check("façade : recraft avec sortie=svg -> couture", [x["model"] for x in ESP["falimg"]] == ["recraft-4.1-vecteur"]
      and out.get("images"), str(ESP))

# ── [4d] planche de référence (Atelier DA) : le réglage image_provider ─────
# Route RÉELLE POST /bible/entities/{id}/generate (generate_bible_reference),
# réglage posé par PUT /atelier/settings.
print("[4d] planche DA avec un modèle vectoriel")
reset()
st, js = call("POST", "/bible/entities", {"kind": "object", "name": "Lanterne", "description": "une lanterne de cuivre"})
eid = (js or {}).get("id") or ((js or {}).get("entity") or {}).get("id")
check("TÉMOIN : entité de bible créée", st == 200 and bool(eid), f"{st} {js}")
st, _ = call("PUT", "/atelier/settings", {"image_provider": "recraft-4.1-vecteur"})
check("TÉMOIN : réglage image_provider posé", st == 200, str(st))
d0 = n_depenses()
st, js = call("POST", f"/bible/entities/{eid}/generate", {})
check("planche avec recraft -> 400 (raster attendu)", st == 400 and "SVG" in str(js), f"{st} {js}")
check("planche avec recraft : ZÉRO ligne depenses, aucun tir",
      n_depenses() == d0 and ESP["falimg"] == [] and ESP["interdit"] == [], f"{d0} -> {n_depenses()} {ESP}")
reset()
call("PUT", "/atelier/settings", {"image_provider": "flux-3"})
d0 = n_depenses()
st, js = call("POST", f"/bible/entities/{eid}/generate", {})
check("TÉMOIN : planche avec flux-3 passe la garde (une ligne depenses) et tire par la couture",
      n_depenses() == d0 + 1 and "flux-3" in [x["model"] for x in ESP["falimg"]], f"{st} {d0} -> {n_depenses()} {str(js)[:150]}")
call("PUT", "/atelier/settings", {"image_provider": "flux"})

# ── [8] modèle SANS CLÉ choisi : 503 AVANT la garde de dépense ─────────────
# Décision de l'utilisateur (11/10/2026) : un modèle sans clé reste
# choisissable dans les listes ; c'est le serveur qui refuse le tir, en 503
# qui nomme la clé et renvoie aux Réglages, sans écrire de dépense.
print("[8] modèle sans clé choisi : 503 avant la dépense")
settings.OPENAI_API_KEY = ""
for chemin, corps in (("/images/generate", {"prompt": "chat", "n": 1, "model": "gpt-image-2"}),
                      ("/images/process", {"op": "edit", "filename": SRC, "prompt": "en bleu", "model": "gpt-image-2"}),
                      ("/materials/generate", {"prompt": "pierre", "model": "gpt-image-2", "res": 512})):
    reset()
    r0, d0 = RESEAU["n"], n_depenses()
    st, js = call("POST", chemin, corps)
    check(f"{chemin} gpt-image-2 sans OPENAI_API_KEY -> 503 nomme la clé et les Réglages",
          st == 503 and "OPENAI_API_KEY" in str(js) and "Réglages" in str(js), f"{st} {js}")
    check(f"{chemin} sans clé : ZÉRO ligne depenses, aucun appel fournisseur",
          n_depenses() == d0 and RESEAU["n"] == r0 and ESP["interdit"] == [] and ESP["falimg"] == [],
          f"{d0} -> {n_depenses()} {ESP} {RESEAU}")
settings.OPENAI_API_KEY = "test-oa"
mf_src = (ICI.parent.parent / "frontend/materialforge/materialforge.js").read_text(encoding="utf-8")
check("Material Forge construit #model depuis `tous` (modèles sans clé compris, raster seulement)",
      "d.tous" in mf_src and 'e.sortie !== "svg"' in mf_src and 'dzT("matiere.t182_modele.cle_a_ajouter"' in mf_src)
import json as _json                                             # noqa: E402
_i18n = ICI.parent.parent / "frontend/shared/i18n"
_com = _json.loads((_i18n / "commun.json").read_text(encoding="utf-8"))
_mat = _json.loads((_i18n / "matiere.json").read_text(encoding="utf-8"))
check("mention : la clé de zone du Material Forge (règle L8 : un lab = une zone) = ia.cle.a_ajouter de commun",
      _mat.get("matiere.t182_modele.cle_a_ajouter", {}).get("fr") == _com.get("ia.cle.a_ajouter", {}).get("fr")
      and _mat.get("matiere.t182_modele.cle_a_ajouter", {}).get("en") == _com.get("ia.cle.a_ajouter", {}).get("en")
      and bool(_com.get("ia.cle.a_ajouter")), str((_mat.get("matiere.t182_modele.cle_a_ajouter"), _com.get("ia.cle.a_ajouter"))))
check("Material Forge : aucune option désactivée pour une clé absente",
      not re.search(r"sansCle[^\n]{0,80}disabled", mf_src))
check("dz-champ-ia : les modèles d'image sans clé sont marqués choisissables (sansCle)",
      "sansCle: sans" in cat_js and "sans = e.dispo === false" in cat_js and 'dzT("ia.cle.a_ajouter"' in cat_js)

# ── [5] routes de lecture ───────────────────────────────────────────────────
print("[5] /image-models et /ia/catalogue")
st, r = call("GET", "/image-models")
check("image-models 200", st == 200, f"{st} {r}")
mods = r.get("models") or []
check("models filtré conservé", bool(mods) and all(m.get("id") for m in mods))
check("models porte voie, cle, usd", all(all(k in m for k in ("voie", "cle", "usd")) for m in mods),
      str([m for m in mods if not all(k in m for k in ("voie", "cle", "usd"))][:2]))
mids = [m["id"] for m in mods]
for i in RASTER:
    check(f"{i} dans models (FAL_KEY posée)", i in mids)
tous = r.get("tous") or []
check("tous présent, toutes les entrées", len(tous) == len(img) and len(tous) >= len(mods), f"{len(tous)} {len(img)}")
check("tous porte les champs de [0]", all(all(k in e for k in CHAMPS) for e in tous))
settings.OPENAI_API_KEY = ""
st, r = call("GET", "/image-models")
check("sans clé OpenAI : models sans gpt-image-2, tous AVEC (dispo=False)",
      "gpt-image-2" not in [m["id"] for m in r.get("models", [])]
      and any(e["id"] == "gpt-image-2" and e["dispo"] is False for e in r.get("tous", [])), str(r)[:300])
settings.OPENAI_API_KEY = "test-oa"
print("[5b] recraft hors de models, dans tous (sortie svg)")
st, r = call("GET", "/image-models")
check("recraft ABSENT de models (consommateurs raster)",
      "recraft-4.1-vecteur" not in [m["id"] for m in r.get("models", [])], str([m["id"] for m in r.get("models", [])]))
_rc = [e for e in r.get("tous", []) if e["id"] == "recraft-4.1-vecteur"]
check("recraft présent dans tous avec sortie=svg", len(_rc) == 1 and _rc[0].get("sortie") == "svg", str(_rc))
check("toutes les autres entrées de tous : sortie=raster",
      all(e.get("sortie") == "raster" for e in r.get("tous", []) if e["id"] != "recraft-4.1-vecteur"))
check("les entrées de models sont raster", all(m.get("id") in P._IMAGE_MODELS for m in r.get("models", [])))
st, r = call("GET", "/ia/catalogue", params={"nature": "image"})
check("catalogue image 200", st == 200 and r.get("nature") == "image"
      and len(r.get("modeles") or []) == len(img), f"{st} {str(r)[:200]}")
st, r = call("GET", "/ia/catalogue", params={"nature": "zzz"})
check("nature inconnue 400", st == 400, f"{st} {r}")
st, r = call("GET", "/ia/catalogue")
check("nature vide 400", st == 400, f"{st} {r}")

# ── [6] prix à mesurer ──────────────────────────────────────────────────────
print("[6] prix à mesurer")
cle_ideo = P._IMAGE_MODELS["ideogram-4.5"][2]
_avant = P.DEFAULTS[cle_ideo]
P.DEFAULTS[cle_ideo] = 0.0
try:
    e = next(x for x in CI.lister("image") if x["id"] == "ideogram-4.5")
    check("prix inconnu = 0.0 + note codée « a_mesurer »", e["usd"] == 0.0 and e.get("note") == "a_mesurer", str(e))
finally:
    P.DEFAULTS[cle_ideo] = _avant
e = next(x for x in CI.lister("image") if x["id"] == "flux-3")
check("prix connu : usd > 0, pas de note", e["usd"] > 0 and not e.get("note"), str(e))

# ── [2b] node --check et copie dist ─────────────────────────────────────────
print("[2b] node --check et copie dist")
node = shutil.which("node")
for f in ("frontend/shared/dz-champ-ia.js", "frontend/materialforge/materialforge.js"):
    if node:
        rr = subprocess.run([node, "--check", str(ICI.parent.parent / f)], capture_output=True, text=True)
        check(f"node --check {f}", rr.returncode == 0, rr.stderr[:200])
    else:
        check(f"node --check {f}", False, "node introuvable")
a = (ICI.parent.parent / "frontend/shared/dz-champ-ia.js").read_bytes()
b = (ICI.parent.parent / "frontend/dist/shared/dz-champ-ia.js").read_bytes()
check("copie dist octet pour octet", a == b)

# ── [7] la VRAIE couture _fal_image_generate ────────────────────────────────
print("[7] couture _fal_image_generate (réelle, réseau remplacé)")
from app.services import fal_service as FS                      # noqa: E402

TIRS, DL, UP = [], [], []
REPONSES = []                   # réponses successives de subscribe_async


async def _sub(endpoint, arguments=None, **k):
    TIRS.append((endpoint, dict(arguments or {})))
    return REPONSES.pop(0) if REPONSES else {"images": [{"url": "u1"}]}


async def _dl(urls, ext=".png"):
    DL.append((list(urls), ext))
    return [f"f{i}{ext}" for i in range(len(urls))]


async def _up(chemin):
    UP.append(chemin)
    return f"https://up/{len(UP)}"

import inspect                                                   # noqa: E402
# getattr_static : on garde le DESCRIPTEUR (staticmethod) pour le remettre tel quel
_garde_sub, _vrai_dl = fal_client.subscribe_async, IP._download
_vrai_up = inspect.getattr_static(FS.FalSeedanceClient, "upload_image")
fal_client.subscribe_async = _sub
IP._download = _dl
FS.FalSeedanceClient.upload_image = staticmethod(_up)


def raz(*rep):
    TIRS.clear(); DL.clear(); UP.clear(); REPONSES.clear(); REPONSES.extend(rep)


try:
    raz()
    out = asyncio.run(_VRAIE_FALIMG("flux-3", "chat", "square", 3))
    check("flux-3 n=3 -> 3 tirs (pas de num_images)", len(TIRS) == 3
          and all("num_images" not in a for _, a in TIRS), str(TIRS))
    check("flux-3 : 3 images, extension .png", DL == [(["u1", "u1", "u1"], ".png")] and len(out) == 3, str(DL))
    raz()
    asyncio.run(_VRAIE_FALIMG("seedream-5-pro", "chat", "square", 3))
    check("seedream n=3 -> 1 tir num_images=3", len(TIRS) == 1 and TIRS[0][1].get("num_images") == 3, str(TIRS))
    raz({"image": {"url": "u2"}})
    asyncio.run(_VRAIE_FALIMG("recraft-4.1-vecteur", "logo", "square", 1))
    check("recraft : forme {image:{url}} lue, extension .svg", DL == [(["u2"], ".svg")], str(DL))
    raz({}, {"images": "pas une liste"})
    try:
        asyncio.run(_VRAIE_FALIMG("flux-3", "chat", "square", 2))
        check("aucune image -> RuntimeError", False)
    except RuntimeError as e:
        check("aucune image -> RuntimeError (message tronqué)", "no images" in str(e) and len(str(e)) < 300
              and DL == [], str(e))
    raz({"images": [{"url": "u3"}, "pas un dict", {"pas": "d'url"}]})
    asyncio.run(_VRAIE_FALIMG("qwen-image-3", "chat", "square", 1))
    check("entrées non-dict ou sans url ignorées", DL == [(["u3"], ".png")], str(DL))
    raz()
    try:
        asyncio.run(_VRAIE_FALIMG("recraft-4.1-vecteur", "logo", "square", 1,
                                  image_paths=[settings.images_path / SRC]))
        check("recraft + référence -> ValueError", False)
    except ValueError:
        check("recraft + référence -> ValueError, zéro téléversement, zéro tir", UP == [] and TIRS == [], str((UP, TIRS)))
    raz()
    refs = [settings.images_path / SRC] * (IP.REF_MAX + 3)
    asyncio.run(_VRAIE_FALIMG("seedream-5-pro", "chat", "square", 1, image_paths=refs))
    check(f"références plafonnées à REF_MAX ({IP.REF_MAX})", len(UP) == IP.REF_MAX
          and len(TIRS[0][1].get("image_urls") or []) == IP.REF_MAX
          and TIRS[0][0] == "bytedance/seedream/v5/pro/edit", str((len(UP), TIRS[:1])))
except Exception as e:  # noqa: BLE001
    check("section [7] sans exception", False, temoin(e))
finally:
    fal_client.subscribe_async = _garde_sub
    IP._download = _vrai_dl
    FS.FalSeedanceClient.upload_image = _vrai_up
check("[7] upload_image restauré tel quel (descripteur staticmethod)",
      inspect.getattr_static(FS.FalSeedanceClient, "upload_image") is _vrai_up
      and isinstance(_vrai_up, staticmethod))

# ── garde réseau et plantages ───────────────────────────────────────────────
check("aucun_appel_reseau", RESEAU["n"] == 0, repr(RESEAU["noms"]))
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont levé — voir les lignes FAIL ci-dessus")

print(f"\n{ok} ok, {fail} fail")
# dossier temporaire du banc : la base fermée d'abord (Windows verrouille un
# fichier sqlite ouvert), puis le dossier
try:
    from app.services.storage import _engine
    asyncio.run(_engine.dispose())
except Exception:  # noqa: BLE001
    pass
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
