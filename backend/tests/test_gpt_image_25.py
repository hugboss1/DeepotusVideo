"""Tâche 6 du plan retours-ia (I) — GPT Image 2.5 Flare et Sunburst, en
direct (OpenAI) et via fal.

Ce que le banc tient :
  [0] registres : les quatre ids sont dans `image_providers.PROVIDERS` avec la
      BONNE clé (`needs`), dans `pricing._IMAGE_MODELS` à 0,053 $ l'image, et
      dans `material_store.MODELS` ; `clean_model` les garde (témoin : un id
      inconnu donne `flux`) ; état vide : un `pricing.json` absent donne les
      quatre défauts ;
  [1] requêtes pures : `build_fal_gpt_request` garde sa signature (épinglée
      par test_cards_face) et son endpoint gpt-image-2 ; la variante 2.5 vise
      `openai/gpt-image-2.5/{flare|sunburst}/{text-to-image|edit}`, qualité
      `high` ÉCRITE, `background="transparent"` pour flare seulement, avec
      `output_format` png ; `build_openai_request` idem (gpt-image-2 inchangé,
      témoin) ;
  [2] `/image-models` : les directs avec OPENAI_API_KEY, les `-fal` (et
      `gpt-image-2-fal`) avec FAL_KEY, aucun sans sa clé — clés SIMULÉES dans
      `settings`, jamais lues ;
  [3] routage de `/images/generate` : un id `-fal` part par
      `IP._fal_gpt_generate` (espion), JAMAIS par OpenAI, et sans
      OPENAI_API_KEY il n'est pas refusé ; un direct 2.5 part par
      `IP._openai_generate` (espion) avec `background` ; `nano-banana-pro`
      part vers Nano Banana Pro, pas vers FLUX ;
  [4] `/images/process` (edit) : même règle ; `nano-banana-pro` n'est plus
      servi par Kontext ;
  [5] `/materials/generate` et son job : un `-fal` sans clé OpenAI est
      accepté et part par fal ;
  [6] `materialforge.js` : `MODEL_COST`/`MODEL_SEC` portent les quatre ids,
      et `node --check` passe.

AUCUN appel réel : `_openai_generate`, `_fal_gpt_generate`, `_banana_generate`
et `routes._flux_generate` sont des espions ; `fal_client.*` et tout
`httpx.AsyncClient.post` hors du client de test sont des gardes qui COMPTENT.

Run: & $PY tests/test_gpt_image_25.py   (un processus, depuis backend/)
"""
import asyncio
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="gpt25_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ["FAL_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-oa"
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
           "HEYGEN_API_KEY"):
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


QUATRE = ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst",
          "gpt-image-2.5-flare-fal", "gpt-image-2.5-sunburst-fal")
DIRECTS = QUATRE[:2]
VIA_FAL = QUATRE[2:]

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
ESP = {"openai": [], "falgpt": [], "banana": [], "flux": [], "upload": 0}


def _png():
    name = f"esp_{len(ESP['openai']) + len(ESP['falgpt']) + len(ESP['banana']) + len(ESP['flux'])}_{os.urandom(3).hex()}.png"
    Image.new("RGB", (64, 64), (120, 90, 60)).save(settings.images_path / name)
    return name


async def _esp_openai(model, prompt, size, n, image_path, **kw):
    ESP["openai"].append({"model": model, "size": size, "n": n,
                          "image": image_path, **kw})
    return [_png()]


async def _esp_falgpt(prompt, size, n, image_path, **kw):
    ESP["falgpt"].append({"size": size, "n": n, "image": image_path, **kw})
    return [_png()]


async def _esp_banana(prompt, size, n, image_path, ratio=None, pro=False):
    ESP["banana"].append({"pro": pro, "image": image_path, "ratio": ratio})
    return [_png()]


async def _esp_flux(prompt, size, n, **kw):
    ESP["flux"].append({"model": kw.get("model"), **kw})
    return {"images": [_png()], "seed": 1}

IP._openai_generate = _esp_openai
IP._fal_gpt_generate = _esp_falgpt
IP._banana_generate = _esp_banana
R._flux_generate = _esp_flux


def reset():
    for k in ("openai", "falgpt", "banana", "flux"):
        ESP[k].clear()


def cles(fal=True, openai=True):
    settings.FAL_KEY = "test-key" if fal else ""
    settings.OPENAI_API_KEY = "test-oa" if openai else ""


SRC = "source.png"
Image.new("RGB", (128, 128), (10, 20, 30)).save(settings.images_path / SRC)

asyncio.run(init_db())


async def _req(meth, path, body=None):
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://t") as c:
        if meth == "GET":
            return await c.get("/api" + path)
        return await c.post("/api" + path, json=body)


def call(meth, path, body=None):
    try:
        r = asyncio.run(_req(meth, path, body))
        try:
            js = r.json()
        except Exception:
            js = {"_texte": r.text}
        return r.status_code, js
    except Exception as e:  # noqa: BLE001
        return -1, {"_temoin": temoin(e)}


# ── [0] registres ───────────────────────────────────────────────────────────
print("[0] registres")
for mid in QUATRE:
    meta = IP.PROVIDERS.get(mid) or {}
    attendu = "FAL_KEY" if mid.endswith("-fal") else "OPENAI_API_KEY"
    check(f"providers_{mid}_needs", meta.get("needs") == attendu, repr(meta))
    spec = P._IMAGE_MODELS.get(mid)
    check(f"pricing_table_{mid}", bool(spec) and spec[1] == (
        "fal" if mid.endswith("-fal") else "openai"), repr(spec))
    devis = P.estimate({"kind": "image", "model": mid, "n": 2})
    check(f"pricing_estimate_{mid}_0053",
          abs(devis["total_usd"] - 2 * 0.053) < 1e-9, repr(devis))
    check(f"ms_models_{mid}", mid in MS.MODELS, repr(MS.MODELS))
    check(f"clean_model_garde_{mid}", MS.clean_model(mid) == mid,
          MS.clean_model(mid))
for cle in ("gpt_image_25_flare_usd", "gpt_image_25_sunburst_usd",
            "gpt_image_25_flare_fal_usd", "gpt_image_25_sunburst_fal_usd"):
    check(f"defaut_{cle}", P.DEFAULTS.get(cle) == 0.053, repr(P.DEFAULTS.get(cle)))
# état vide : aucun pricing.json -> les défauts
_pf = P._PRICING_FILE
check("etat_vide_pas_de_pricing_json", not Path(_pf).exists(), str(_pf))
check("etat_vide_load_donne_les_defauts",
      all(P.load().get(c) == 0.053 for c in ("gpt_image_25_flare_usd",
                                               "gpt_image_25_sunburst_fal_usd")),
      "")
# voisins complétés au passage (mêmes lignes)
for mid in ("nano-banana-pro", "gpt-image-2-fal"):
    check(f"ms_models_voisin_{mid}", MS.clean_model(mid) == mid,
          MS.clean_model(mid))
check("temoin_clean_model_inconnu_flux",
      MS.clean_model("gpt-image-9-inconnu") == "flux",
      MS.clean_model("gpt-image-9-inconnu"))
check("temoin_estimate_flux_inchange",
      abs(P.estimate({"kind": "image", "model": "flux", "n": 1})["total_usd"]
          - P.DEFAULTS["flux_image_usd"]) < 1e-9, "")

# ── [1] requêtes pures ──────────────────────────────────────────────────────
print("[1] requetes pures")
sig = list(inspect.signature(IP.build_fal_gpt_request).parameters)
check("fal_gpt_signature_preservee",
      sig[:4] == ["prompt", "size", "n", "image_url"], repr(sig))
m, a = IP.build_fal_gpt_request("p", "portrait_4_3", 1, None)
check("temoin_fal_gpt2_endpoint_inchange", m == "openai/gpt-image-2", m)
check("temoin_fal_gpt2_sans_background", "background" not in a, repr(a))
m, a = IP.build_fal_gpt_request("p", "portrait_4_3", 1, None,
                                background="transparent")
check("temoin_fal_gpt2_background_ferme", "background" not in a, repr(a))
for var in ("flare", "sunburst"):
    try:
        m, a = IP.build_fal_gpt_request("p", "square_hd", 1, None,
                                        model=f"gpt-image-2.5-{var}")
        m2, a2 = IP.build_fal_gpt_request("p", "square_hd", 1, "http://u",
                                          model=f"gpt-image-2.5-{var}")
        mt, at = IP.build_fal_gpt_request("p", "square_hd", 1, None,
                                          model=f"gpt-image-2.5-{var}",
                                          background="transparent")
    except Exception as e:  # noqa: BLE001
        m = m2 = mt = temoin(e)
        a = a2 = at = {}
    check(f"fal_{var}_t2i_endpoint",
          m == f"openai/gpt-image-2.5/{var}/text-to-image", m)
    check(f"fal_{var}_edit_endpoint",
          m2 == f"openai/gpt-image-2.5/{var}/edit"
          and a2.get("image_urls") == ["http://u"], f"{m2} {a2}")
    check(f"fal_{var}_quality_high", a.get("quality") == "high", repr(a))
    check(f"fal_{var}_png", at.get("output_format") == "png", repr(at))
    # doc fal (vérifiée en revue le 27/09) : `background` auto/transparent/
    # opaque accepté par flare ET sunburst, t2i comme edit
    check(f"fal_{var}_background_transparent",
          at.get("background") == "transparent", repr(at))
    try:
        _, ae = IP.build_fal_gpt_request("p", "square_hd", 1, "http://u",
                                         model=f"gpt-image-2.5-{var}",
                                         background="transparent")
    except Exception as e:  # noqa: BLE001
        ae = {"_t": temoin(e)}
    check(f"fal_{var}_edit_background_transparent",
          ae.get("background") == "transparent", repr(ae))
    try:
        url, p = IP.build_openai_request(f"gpt-image-2.5-{var}", "p",
                                         "square", 1, False,
                                         background="transparent")
        url2, p2 = IP.build_openai_request(f"gpt-image-2.5-{var}", "p",
                                           "square", 1, True)
    except Exception as e:  # noqa: BLE001
        url = url2 = temoin(e)
        p = p2 = {}
    check(f"openai_{var}_model", p.get("model") == f"gpt-image-2.5-{var}",
          repr(p))
    check(f"openai_{var}_generations", url.endswith("/v1/images/generations"),
          url)
    check(f"openai_{var}_edits", url2.endswith("/v1/images/edits")
          and p2.get("quality") == "high", f"{url2} {p2}")
    check(f"openai_{var}_quality_high", p.get("quality") == "high", repr(p))
    if var == "flare":
        check("openai_flare_background", p.get("background") == "transparent"
              and p.get("output_format") == "png", repr(p))
    else:
        # la doc OpenAI ne dit rien du fond pour sunburst : fermé en direct
        check("openai_sunburst_background_ignore", "background" not in p,
              repr(p))
url, p = IP.build_openai_request("gpt-image-2", "p", "square", 1, False)
check("temoin_openai_gpt2_payload_inchange",
      set(p) == {"model", "prompt", "n", "size"}, repr(p))

# ── [2] /image-models ───────────────────────────────────────────────────────
print("[2] /image-models")


def ids_liste(fal, openai):
    cles(fal, openai)
    st, js = call("GET", "/image-models")
    return st, [m.get("id") for m in (js.get("models") or [])], js


st, ids, js = ids_liste(True, True)
check("image_models_200", st == 200, repr(js))
# le DÉFAUT est figé : un ajout au catalogue ne le déplace pas
check("defaut_deux_cles_flux", js.get("default") == "flux", repr(js))
_st, _ids, _js = ids_liste(True, False)
check("defaut_fal_seul_flux", _js.get("default") == "flux", repr(_js))
_st, _ids, _js = ids_liste(False, True)
check("defaut_openai_seul_gpt_image_2", _js.get("default") == "gpt-image-2",
      repr(_js))
cles(True, True)
for mid in QUATRE + ("gpt-image-2-fal",):
    check(f"image_models_deux_cles_{mid}", mid in ids, repr(ids))
st, ids, js = ids_liste(True, False)
for mid in VIA_FAL + ("gpt-image-2-fal",):
    check(f"image_models_fal_seul_{mid}", mid in ids, repr(ids))
for mid in DIRECTS:
    check(f"image_models_fal_seul_sans_{mid}", mid not in ids, repr(ids))
st, ids, js = ids_liste(False, True)
for mid in DIRECTS:
    check(f"image_models_openai_seul_{mid}", mid in ids, repr(ids))
for mid in VIA_FAL + ("gpt-image-2-fal",):
    check(f"image_models_openai_seul_sans_{mid}", mid not in ids, repr(ids))
st, ids, js = ids_liste(False, False)
check("image_models_etat_vide", st == 200 and ids == [], repr(js))
# chaque id listé a un prix tabulé (sinon l'écran afficherait celui de FLUX)
st, ids, js = ids_liste(True, True)
check("image_models_tous_tabules",
      [i for i in ids if i not in P._IMAGE_MODELS] == [], repr(ids))

# ── [3] /images/generate ────────────────────────────────────────────────────
print("[3] /images/generate")
for mid in VIA_FAL:
    reset()
    cles(True, False)   # sans clé OpenAI : pas de refus
    st, js = call("POST", "/images/generate", {"prompt": "chat", "model": mid})
    check(f"gen_{mid}_200_sans_openai", st == 200, repr(js))
    check(f"gen_{mid}_par_fal_gpt", len(ESP["falgpt"]) == 1
          and ESP["falgpt"][0].get("model") == mid[:-4], repr(ESP["falgpt"]))
    check(f"gen_{mid}_jamais_openai", ESP["openai"] == [], repr(ESP["openai"]))
    check(f"gen_{mid}_modele_rendu", js.get("model") == mid, repr(js))
reset()
cles(True, True)
st, js = call("POST", "/images/generate",
              {"prompt": "chat", "model": "gpt-image-2.5-flare-fal",
               "background": "transparent"})
check("gen_flare_fal_background_transmis",
      st == 200 and ESP["falgpt"] and ESP["falgpt"][0].get("background")
      == "transparent", f"{st} {ESP['falgpt']}")
reset()
cles(False, True)
st, js = call("POST", "/images/generate",
              {"prompt": "chat", "model": "gpt-image-2.5-sunburst-fal"})
check("gen_fal_sans_fal_key_503_nomme",  # P1 #11 (28/09) : cle absente -> 503, plus 400
      st == 503 and "FAL_KEY" in str(js), f"{st} {js}")
check("gen_fal_sans_fal_key_aucun_appel",
      ESP["falgpt"] == [] and ESP["openai"] == [], repr(ESP))
for mid in DIRECTS:
    reset()
    cles(False, True)
    st, js = call("POST", "/images/generate",
                  {"prompt": "chat", "model": mid,
                   "background": "transparent"})
    check(f"gen_{mid}_200", st == 200, repr(js))
    check(f"gen_{mid}_par_openai_generate", len(ESP["openai"]) == 1
          and ESP["openai"][0]["model"] == mid, repr(ESP["openai"]))
    check(f"gen_{mid}_background_transmis",
          bool(ESP["openai"]) and ESP["openai"][0].get("background")
          == "transparent", repr(ESP["openai"]))
    check(f"gen_{mid}_jamais_fal", ESP["falgpt"] == [], repr(ESP["falgpt"]))
reset()
cles(True, True)
st, js = call("POST", "/images/generate",
              {"prompt": "chat", "model": "nano-banana-pro"})
check("gen_nano_banana_pro_200", st == 200, repr(js))
check("gen_nano_banana_pro_par_banana_pro",
      len(ESP["banana"]) == 1 and ESP["banana"][0]["pro"] is True,
      repr(ESP["banana"]))
check("gen_nano_banana_pro_pas_flux", ESP["flux"] == [], repr(ESP["flux"]))
check("gen_nano_banana_pro_modele_rendu", js.get("model") == "nano-banana-pro",
      repr(js))
reset()
st, js = call("POST", "/images/generate", {"prompt": "chat", "model": "flux"})
check("temoin_gen_flux_par_flux", st == 200 and len(ESP["flux"]) == 1
      and ESP["banana"] == [] and ESP["falgpt"] == [], f"{st} {ESP}")

# ── [4] /images/process (edit) ──────────────────────────────────────────────
print("[4] /images/process")
for mid in VIA_FAL:
    reset()
    cles(True, False)
    st, js = call("POST", "/images/process",
                  {"op": "edit", "filename": SRC, "prompt": "or",
                   "model": mid})
    check(f"edit_{mid}_200_sans_openai", st == 200, repr(js))
    check(f"edit_{mid}_par_fal_gpt_avec_image",
          len(ESP["falgpt"]) == 1 and ESP["falgpt"][0]["image"] is not None
          and ESP["falgpt"][0].get("model") == mid[:-4], repr(ESP["falgpt"]))
    check(f"edit_{mid}_ni_openai_ni_kontext",
          ESP["openai"] == [] and ESP["flux"] == [], repr(ESP))
reset()
cles(True, True)
st, js = call("POST", "/images/process",
              {"op": "edit", "filename": SRC, "prompt": "or",
               "model": "gpt-image-2.5-sunburst"})
check("edit_sunburst_direct_par_openai",
      st == 200 and len(ESP["openai"]) == 1
      and ESP["openai"][0]["model"] == "gpt-image-2.5-sunburst"
      and ESP["openai"][0]["image"] is not None, f"{st} {ESP['openai']}")
reset()
st, js = call("POST", "/images/process",
              {"op": "variations", "filename": SRC,
               "model": "nano-banana-pro"})
check("edit_nano_banana_pro_par_banana_pro",
      st == 200 and len(ESP["banana"]) == 1 and ESP["banana"][0]["pro"],
      f"{st} {ESP['banana']}")
check("edit_nano_banana_pro_pas_kontext", ESP["flux"] == [], repr(ESP["flux"]))
reset()
st, js = call("POST", "/images/process",
              {"op": "edit", "filename": SRC, "prompt": "or", "model": "flux"})
check("temoin_edit_flux_par_kontext",
      st == 200 and ESP["flux"] and ESP["flux"][0]["model"]
      == "fal-ai/flux-kontext/dev", f"{st} {ESP['flux']}")

# ── [4b] erreur du fournisseur hors RuntimeError → 502, pas 500 ─────────────
print("[4b] erreurs fournisseur")
ESP_TO = {"n": 0}


async def _esp_timeout(*a, **k):
    ESP_TO["n"] += 1
    raise httpx.ReadTimeout("delai depasse (banc) Bearer test-key")

IP._fal_gpt_generate = _esp_timeout
cles(True, True)
st, js = call("POST", "/images/generate",
              {"prompt": "chat", "model": "gpt-image-2.5-flare-fal"})
check("timeout_generate_502", st == 502, f"{st} {js}")
check("timeout_generate_sans_cle", "test-key" not in str(js), repr(js))
check("timeout_generate_nomme_modele",
      "gpt-image-2.5-flare-fal" in str(js), repr(js))
st, js = call("POST", "/images/process",
              {"op": "edit", "filename": SRC, "prompt": "or",
               "model": "gpt-image-2.5-sunburst-fal"})
check("timeout_process_502", st == 502, f"{st} {js}")
check("timeout_process_sans_cle", "test-key" not in str(js), repr(js))
check("timeout_espion_appele_deux_fois", ESP_TO["n"] == 2, repr(ESP_TO))
IP._fal_gpt_generate = _esp_falgpt

# ── [5] /materials/generate ─────────────────────────────────────────────────
print("[5] /materials/generate")
for mid in VIA_FAL:
    reset()
    cles(True, False)
    st, js = call("POST", "/materials/generate",
                  {"prompt": "pierre", "model": mid, "res": 512})
    check(f"mat_{mid}_accepte_sans_openai", st == 200 and js.get("job_id"),
          repr(js))
    job = R._MAT_JOBS.get(js.get("job_id") or "", {})
    check(f"mat_{mid}_job_termine", job.get("status") == "done",
          repr({k: job.get(k) for k in ("status", "error", "step")}))
    check(f"mat_{mid}_par_fal_gpt",
          len(ESP["falgpt"]) == 1 and ESP["falgpt"][0].get("model")
          == mid[:-4], repr(ESP["falgpt"]))
    check(f"mat_{mid}_ni_openai_ni_flux",
          ESP["openai"] == [] and ESP["flux"] == [], repr(ESP))
reset()
cles(True, False)
st, js = call("POST", "/materials/generate",
              {"prompt": "pierre", "model": "gpt-image-2.5-flare", "res": 512})
check("temoin_mat_direct_sans_openai_503", st == 503  # P1 #11 : 400 -> 503
      and "OPENAI_API_KEY" in str(js), f"{st} {js}")
reset()
cles(True, True)
st, js = call("POST", "/materials/generate",
              {"prompt": "pierre", "model": "nano-banana-pro", "res": 512})
job = R._MAT_JOBS.get(js.get("job_id") or "", {})
check("mat_nano_banana_pro_par_banana_pro",
      job.get("status") == "done" and len(ESP["banana"]) == 1
      and ESP["banana"][0]["pro"] and ESP["flux"] == [],
      f"{job.get('status')} {job.get('error')} {ESP}")

# ── [6] materialforge.js ────────────────────────────────────────────────────
print("[6] materialforge.js")
JS = ICI.parent.parent / "frontend" / "materialforge" / "materialforge.js"
src = JS.read_text(encoding="utf-8")


def bloc(nom):
    mm = re.search(r"const " + nom + r"\s*=\s*\{(.*?)\};", src, re.S)
    return mm.group(1) if mm else ""


for nom in ("MODEL_COST", "MODEL_SEC"):
    b = bloc(nom)
    check(f"{nom}_trouve", bool(b), nom)
    for mid in QUATRE + ("nano-banana-pro", "gpt-image-2-fal"):
        check(f"{nom}_{mid}", re.search(r'"' + re.escape(mid) + r'"\s*:\s*\d',
                                        b) is not None, b.strip()[:200])
node = shutil.which("node")
if node:
    r = subprocess.run([node, "--check", str(JS)], capture_output=True,
                       text=True)
    check("materialforge_node_check", r.returncode == 0, r.stderr[:300])
else:
    check("materialforge_node_check", False, "node introuvable")

# ── garde réseau et plantages ───────────────────────────────────────────────
check("aucun_appel_reseau", RESEAU["n"] == 0, repr(RESEAU["noms"]))
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont levé — voir les lignes FAIL ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
