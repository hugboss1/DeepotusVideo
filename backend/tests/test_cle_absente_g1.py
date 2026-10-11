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


async def _req(path, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.post("/api" + path, json=body)


def call(path, body):
    r = asyncio.run(_req(path, body))
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

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
