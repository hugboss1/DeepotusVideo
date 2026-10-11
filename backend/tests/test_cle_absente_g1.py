"""t183 / G1 — un modèle SANS CLÉ choisi : 503 AVANT toute garde de dépense.

Décision de l'utilisateur (11/10/2026) : un modèle dont la clé manque reste
TOUJOURS choisissable dans les sélecteurs (prix et mention « clé X à ajouter
dans Réglages ») ; le refus n'arrive qu'au lancement, en 503 qui nomme la clé,
AVANT `_garde_cout` et `_plafond` — donc ZÉRO ligne `depenses`.

  [1] vidéo : /generate, /generate/batch et /generate/composition avec Veo
      (Google) sans GEMINI_API_KEY -> 503 « GEMINI_API_KEY … Réglages »,
      _plafond jamais appelé, aucune dépense ; un modèle fal sans FAL_KEY idem
      (FAL_KEY nommée) ; TÉMOIN : avec la clé, la même requête atteint
      _plafond (espion qui répond 402 — rien n'est lancé).
  [2] Atelier : /atelier/providers rend `tous` (tout le registre raster, dispo
      et clé, prix du catalogue) ; la planche de référence d'une entité
      (/bible/entities/{id}/generate) avec un générateur sans clé (réglage DA)
      -> 503 qui nomme la clé, _plafond jamais appelé, zéro dépense ; TÉMOIN :
      avec la clé, la garde est atteinte ; l'image de production d'un plan
      (/shots/{id}/image) sans FAL_KEY -> 503 avant tout (TÉMOIN : avec la clé,
      le refus suivant — 400 « aucune vue » — prouve que le 503 venait de la clé).
  [3] Card Forge : GET face/ai-models et frame/ai-models listent les modèles
      sans clé (dispo faux, `cle` nommée), `cle_absente` dérivé de `dispo` ;
      lot/modeles nomme la clé (cle_nom) et lot/generer refuse en 503 en la
      nommant.

AUCUN appel réel : `_plafond` est un espion, `fal_client.*` et tout
`httpx.AsyncClient.post` hors du client de test sont des gardes qui COMPTENT.

Run: & $PY tests/test_cle_absente_g1.py   (un processus, depuis backend/)
"""
import asyncio
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="cleg1_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ["FAL_KEY"] = "test-key"
for _k in ("OPENAI_API_KEY", "ELEVENLABS_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY",
           "HEYGEN_API_KEY", "MESHY_API_KEY"):
    os.environ.pop(_k, None)
Path(TMP, "images").mkdir(parents=True, exist_ok=True)
Path(TMP, "outputs").mkdir(parents=True, exist_ok=True)
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))

import fal_client                                                # noqa: E402
import httpx                                                     # noqa: E402
from fastapi import HTTPException                                # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402
from PIL import Image                                            # noqa: E402

from app.config import settings                                  # noqa: E402
from app.main import app                                         # noqa: E402
from app.services.storage import init_db                         # noqa: E402
from app.api import routes as R                                  # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


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

# ── espion de la garde de dépense : il répond 402 (rien n'est lancé) ────────
PLAF = []


async def _plafond_espion(ops, categorie="", *a, **k):
    PLAF.append((categorie, ops))
    raise HTTPException(402, "ESPION _plafond : arrêt du banc")

R._plafond = _plafond_espion

SRC = "depart.png"
Image.new("RGB", (64, 64), (10, 20, 30)).save(settings.images_path / SRC)
asyncio.run(init_db())


async def _req(path, body, meth="POST"):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        if meth == "GET":
            return await c.get("/api" + path)
        if meth == "PUT":
            return await c.put("/api" + path, json=body)
        return await c.post("/api" + path, json=body)


def call(path, body=None, meth="POST"):
    r = asyncio.run(_req(path, body, meth))
    try:
        return r.status_code, r.json()
    except Exception:  # noqa: BLE001
        return r.status_code, {"_texte": r.text}


def n_depenses():
    con = sqlite3.connect(TMP + "/t.db")
    try:
        return con.execute("SELECT COUNT(*) FROM depenses").fetchone()[0]
    finally:
        con.close()


# ── [1] vidéo ───────────────────────────────────────────────────────────────
print("[1] vidéo : modèle sans clé -> 503 avant _plafond")
from app.services.fal_service import VIDEO_MODELS                # noqa: E402
VEO = next((k for k, m in VIDEO_MODELS.items() if m["provider"] == "google"), None)
FAL = next((k for k, m in VIDEO_MODELS.items() if m["provider"] != "google"), None)
check("TÉMOIN : un modèle vidéo Google (Veo) et un modèle fal au registre", bool(VEO) and bool(FAL), f"{VEO} {FAL}")


def corps(model):
    return {"image_filename": SRC, "custom_prompt": "un chat", "video_model": model, "duration_s": 5}


def routes(model):
    return (("/generate", corps(model)),
            ("/generate/batch", dict(corps(model), variations_count=2)),
            ("/generate/composition", {"seedance": corps(model),
                                       "heygen": {"script": "bonjour", "avatar_id": "a", "voice_id": "v"},
                                       "layout": "sequential"}))


def essai(model, cle_attendue, sans):
    for chemin, b in routes(model):
        PLAF.clear()
        r0, d0 = RESEAU["n"], n_depenses()
        st, js = call(chemin, b)
        check(f"{chemin} {model} sans {sans} -> 503 nomme {cle_attendue} et les Réglages",
              st == 503 and cle_attendue in str(js) and "Réglages" in str(js), f"{st} {js}")
        check(f"{chemin} {model} sans clé : _plafond JAMAIS appelé, ZÉRO dépense, aucun appel réseau",
              PLAF == [] and n_depenses() == d0 and RESEAU["n"] == r0, f"{PLAF} {d0}->{n_depenses()} {RESEAU}")


settings.GEMINI_API_KEY = ""
if hasattr(settings, "GOOGLE_API_KEY"):
    settings.GOOGLE_API_KEY = ""
check("TÉMOIN : settings.has_gemini faux", not settings.has_gemini)
essai(VEO, "GEMINI_API_KEY", "GEMINI_API_KEY")
settings.FAL_KEY = ""
essai(FAL, "FAL_KEY", "FAL_KEY")
settings.FAL_KEY = "test-key"

# TÉMOIN : avec la clé, /generate atteint la garde de dépense (l'espion arrête tout en 402)
settings.GEMINI_API_KEY = "test-gemini"
check("TÉMOIN : settings.has_gemini vrai une fois la clé posée", settings.has_gemini)
PLAF.clear()
st, js = call("/generate", corps(VEO))
check("TÉMOIN : Veo AVEC GEMINI_API_KEY -> la garde de dépense est atteinte (espion 402)",
      st == 402 and len(PLAF) == 1, f"{st} {js} {PLAF}")
PLAF.clear()
st, js = call("/generate", corps(FAL))
check("TÉMOIN : modèle fal AVEC FAL_KEY -> la garde de dépense est atteinte (espion 402)",
      st == 402 and len(PLAF) == 1, f"{st} {js} {PLAF}")
settings.GEMINI_API_KEY = ""

# ── [2] Atelier ─────────────────────────────────────────────────────────────
print("[2] Atelier : générateurs sans clé choisissables, 503 au tir")
settings.OPENAI_API_KEY = ""
st, pv = call("/atelier/providers", meth="GET")
tous = {e["id"]: e for e in (pv or {}).get("tous") or []}
check("/atelier/providers : `tous` liste aussi les générateurs SANS clé (gpt-image-2 : dispo faux, clé OPENAI_API_KEY)",
      st == 200 and (tous.get("gpt-image-2") or {}).get("dispo") is False
      and (tous.get("gpt-image-2") or {}).get("cle") == "OPENAI_API_KEY" and (tous.get("flux") or {}).get("dispo") is True,
      str(tous.get("gpt-image-2")))
check("/atelier/providers : prix et voie lus au catalogue, aucun vectoriel, `providers` (servis) gardé",
      all(isinstance(e.get("usd"), float) and e.get("voie") in ("fal", "openai") and e.get("sortie") == "raster"
          for e in tous.values()) and "recraft-4.1-vecteur" not in tous
      and "gpt-image-2" not in [p["id"] for p in pv.get("providers") or []], str(list(tous.values())[:2]))
st, ent = call("/bible/entities", {"kind": "object", "name": "Lanterne", "description": "lanterne de cuivre"})
EID = (ent or {}).get("id")
check("TÉMOIN : entité de la bible créée", st == 200 and bool(EID), f"{st} {ent}")
call("/atelier/settings", {"image_provider": "gpt-image-2"}, meth="PUT")
PLAF.clear()
d0, r0 = n_depenses(), RESEAU["n"]
st, js = call(f"/bible/entities/{EID}/generate", {})
check("planche DA, générateur gpt-image-2 sans OPENAI_API_KEY -> 503 qui nomme la clé et les Réglages",
      st == 503 and "OPENAI_API_KEY" in str(js) and "Réglages" in str(js), f"{st} {js}")
check("planche DA sans clé : _plafond JAMAIS appelé, ZÉRO dépense, aucun appel réseau",
      PLAF == [] and n_depenses() == d0 and RESEAU["n"] == r0, f"{PLAF} {d0}->{n_depenses()} {RESEAU}")
call("/atelier/settings", {"image_provider": "flux"}, meth="PUT")
PLAF.clear()
st, js = call(f"/bible/entities/{EID}/generate", {})
check("TÉMOIN : planche DA avec flux (FAL_KEY posée) -> la garde de dépense est atteinte (espion 402)",
      st == 402 and len(PLAF) == 1, f"{st} {js} {PLAF}")
st, ch = call("/chapters", {"title": "C", "script_text": "La lanterne vacille.\n\nLa pluie."})
st2, dec = call(f"/chapters/{(ch or {}).get('id')}/storyboard/decoupe", {"method": "paragraph"})
shots = (dec or {}).get("shots") or []
check("TÉMOIN : un plan découpé", bool(shots), f"{st} {st2} {str(dec)[:200]}")
SID = shots[0]["id"] if shots else "x"
settings.FAL_KEY = ""
PLAF.clear()
d0 = n_depenses()
st, js = call(f"/shots/{SID}/image", {"provider": "nano-banana-pro"})
check("image de production sans FAL_KEY -> 503 qui nomme FAL_KEY, _plafond jamais appelé, zéro dépense",
      st == 503 and "FAL_KEY" in str(js) and "Réglages" in str(js) and PLAF == [] and n_depenses() == d0, f"{st} {js}")
settings.FAL_KEY = "test-key"
st, js = call(f"/shots/{SID}/image", {"provider": "nano-banana-pro"})
check("TÉMOIN : avec FAL_KEY, le refus suivant (400 : aucune vue de référence) — le 503 venait bien de la clé",
      st == 400 and "référence" in str(js), f"{st} {js}")

# ── [3] Card Forge ──────────────────────────────────────────────────────────
print("[3] Card Forge : ai-models et lot")
st, dk = call("/cards/decks", {"name": "essai t183"})
DID = ((dk or {}).get("deck") or {}).get("id")
check("TÉMOIN : jeu créé", st == 200 and bool(DID), f"{st} {dk}")
for piece in ("face", "frame"):
    st, am = call(f"/cards/{DID}/{piece}/ai-models", meth="GET")
    mods = {m["id"]: m for m in (am or {}).get("models") or []}
    check(f"{piece}/ai-models : gpt-image-2 SANS clé listé (dispo faux, cle OPENAI_API_KEY), flux dispo",
          st == 200 and (mods.get("gpt-image-2") or {}).get("dispo") is False
          and (mods.get("gpt-image-2") or {}).get("cle") == "OPENAI_API_KEY" and (mods.get("flux") or {}).get("dispo") is True,
          f"{st} {mods.get('gpt-image-2')}")
    check(f"{piece}/ai-models : cle_absente faux (FAL_KEY posée), aucun vectoriel",
          am.get("cle_absente") is False and "recraft-4.1-vecteur" not in mods, str(am.get("cle_absente")))
settings.FAL_KEY = ""
st, am = call(f"/cards/{DID}/face/ai-models", meth="GET")
check("face/ai-models SANS aucune clé : la liste reste pleine (tout choisissable), cle_absente vrai (dérivé de dispo)",
      st == 200 and len(am.get("models") or []) >= 16 and am.get("cle_absente") is True
      and not any(m["dispo"] for m in am["models"]), f"{st} {len(am.get('models') or [])} {am.get('cle_absente')}")
settings.FAL_KEY = "test-key"
st, lm = call(f"/cards/{DID}/data/lot/modeles", meth="GET")
lmo = {m["id"]: m for m in (lm or {}).get("models") or []}
check("lot/modeles : gpt-image-2 sans clé nomme sa clé (cle_nom OPENAI_API_KEY)",
      st == 200 and (lmo.get("gpt-image-2") or {}).get("cle") is False
      and (lmo.get("gpt-image-2") or {}).get("cle_nom") == "OPENAI_API_KEY", f"{st} {lmo.get('gpt-image-2')}")
settings.OPENAI_API_KEY = "test-oa"

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
