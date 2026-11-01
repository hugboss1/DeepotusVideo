"""t184 / G2 (plan « Génération IA enrichie ») — vidéo : nouveaux modèles i2v
et first-last-frame (image de début ET de fin).

  [0] Veo 3.1 sur fal : une image de fin passe par l'endpoint FL SÉPARÉ avec
      first_frame_url / last_frame_url (jamais image_url), durée « 8s » ;
      sans image de fin, l'endpoint i2v avec image_url.
  [1] Wan 3.0 : start_image_url + end_image_url, jamais image_url.
  [2] Kling v3 Turbo Pro refuse proprement une image de fin (ValueError
      « pas d'image de fin ») ; ses arguments suivent son schéma (image_url,
      durée en chaîne, ni négatif ni audio).
  [3] catalogue : video_fl = seulement les modèles qui acceptent une fin ;
      jumeaux Veo fal <-> Google ; voie gemini pour les Google natifs.
  [4] prix : chaque nouvel id a son tarif au registre et la garde de coût
      (video_request_op / estimate) le chiffre > 0 ; schémas relus le 11/10
      recopiés au registre (durées, résolutions, H3 en MAJUSCULES).
  [5] /video-models : voie, cle, jumeau, fl ; Veo fast fal accepte une fin
      (end_image vrai) — c'est ce que lit le bascule de Quick (dzEndOK).
  [6] chaque nouveau modèle SANS FAL_KEY : /generate -> 503 qui nomme
      FAL_KEY, AVANT _plafond, zéro dépense, aucun appel réseau.
  [7] le client fal (couture `_soumettre` espionnée, aucun réseau) envoie
      Veo + image de fin à l'endpoint FL avec first/last.

AUCUN appel réel : `_plafond` et `_soumettre` sont des espions, `fal_client.*`
et tout `httpx.AsyncClient.post` hors du client de test sont COMPTÉS.

Run: & $PY tests/test_video_fl.py   (un processus, depuis backend/)
"""
import asyncio
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="videofl_")
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
from app.services import fal_service as F                        # noqa: E402
from app.services import catalogue_ia as CI                      # noqa: E402
from app.services import pricing as P                            # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def fa(mid, image_url, prompt, **kw):
    """(endpoint, args) de build_fal_args, ou un témoin si ça lève."""
    try:
        ep, a, _ = F.build_fal_args(mid, image_url=image_url, prompt=prompt, **kw)
        return ep, a
    except Exception as e:  # noqa: BLE001
        return f"EXC {type(e).__name__}: {e}", {}


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

NOUVEAUX = ("veo-3.1-fal", "veo-3.1-lite-fal", "h3-max", "wan-3.0", "gemini-omni-flash",
            "ltx-2.5-fast", "kling-v3-turbo-pro")

# ── [0] Veo first-last-frame ────────────────────────────────────────────────
print("[0] Veo first-last-frame passe par l'endpoint FL avec first/last")
for mid, base in (("veo-3.1-fast-fal", "fal-ai/veo3.1/fast"), ("veo-3.1-fal", "fal-ai/veo3.1"),
                  ("veo-3.1-lite-fal", "fal-ai/veo3.1/lite")):
    ep, a = fa(mid, "https://x/a.png", "travelling", duration=8, resolution="720p",
               end_image_url="https://x/b.png", negative_prompt="flou", seed=3)
    check(f"{mid} : endpoint FL", ep == base + "/first-last-frame-to-video", ep)
    check(f"{mid} : first/last", a.get("first_frame_url") == "https://x/a.png"
          and a.get("last_frame_url") == "https://x/b.png", a)
    check(f"{mid} : pas d'image_url ni d'end_image_url sur FL",
          "image_url" not in a and "end_image_url" not in a, a)
    check(f"{mid} : durée '8s', 720p, audio coupé, négatif et seed gardés",
          a.get("duration") == "8s" and a.get("resolution") == "720p" and a.get("generate_audio") is False
          and a.get("negative_prompt") == "flou" and a.get("seed") == 3, a)
    ep, a = fa(mid, "https://x/a.png", "x", duration=8, resolution="720p")
    check(f"{mid} : sans fin -> i2v avec image_url", ep == base + "/image-to-video"
          and a.get("image_url") == "https://x/a.png" and "first_frame_url" not in a, (ep, a))

# ── [1] Wan 3.0 ─────────────────────────────────────────────────────────────
print("[1] Wan 3.0 : start_image_url")
ep, a = fa("wan-3.0", "https://x/a.png", "x", duration=5, resolution="720p",
           end_image_url="https://x/b.png", seed=4)
check("wan endpoint", ep == "alibaba/wan-3.0/image-to-video", ep)
check("wan start/end", a.get("start_image_url") == "https://x/a.png"
      and a.get("end_image_url") == "https://x/b.png" and "image_url" not in a, a)
check("wan durée entière, 720p, audio coupé, seed", a.get("duration") == 5 and a.get("resolution") == "720p"
      and a.get("audio") is False and a.get("seed") == 4 and "aspect_ratio" not in a, a)

# ── [2] Kling turbo ─────────────────────────────────────────────────────────
print("[2] Kling turbo refuse la fin proprement")
try:
    F.build_fal_args("kling-v3-turbo-pro", image_url="https://x/a.png", prompt="x", duration=5,
                     end_image_url="https://x/b.png")
    _err = "aucune erreur"
except ValueError as e:
    _err = str(e)
check("refus fin = texte i18n ia.video.pas_de_fin (fr : « n'accepte pas d'image de fin », liste des modèles)",
      _err == F.refus_fin("Kling v3 Turbo Pro") and "n'accepte pas d'image de fin" in _err
      and "Veo 3.1 Fast (fal)" in _err and "Kling v3 Turbo Pro" not in _err.split("(", 1)[1], _err)
check("refus fin en anglais : guillemets droits, liste", '"first and last frame"' in F.refus_fin("X", "en")
      and "has no last-frame input" in F.refus_fin("X", "en"), F.refus_fin("X", "en"))
ep, a = fa("kling-v3-turbo-pro", "https://x/a.png", "x", duration=5, negative_prompt="n",
           aspect_ratio="9:16", resolution="1080p", seed=1)
check("kling turbo : endpoint, image_url (pas start_image_url)", ep == "fal-ai/kling-video/v3/turbo/pro/image-to-video"
      and a.get("image_url") == "https://x/a.png" and "start_image_url" not in a, (ep, a))
check("kling turbo : durée CHAÎNE '5', ni négatif, ratio, résolution, seed, audio",
      a.get("duration") == "5" and set(a) == {"prompt", "image_url", "duration"}, a)
ep, a = fa("kling-v3-pro", "u", "p", duration=7, end_image_url="e", negative_prompt="n")
check("TÉMOIN : Kling v3 Pro garde start_image_url, durée entière, négatif",
      a.get("start_image_url") == "u" and a.get("end_image_url") == "e" and a.get("duration") == 7
      and a.get("negative_prompt") == "n", a)

# ── [3] catalogue ───────────────────────────────────────────────────────────
print("[3] catalogue : video_fl = seulement les modèles qui acceptent une fin ; jumeaux Veo")
check("natures vidéo inscrites", {"video_i2v", "video_fl"} <= set(CI.natures()), CI.natures())
fl = {e["id"] for e in CI.lister("video_fl")}
check("veo fast/std/lite fal dans FL", {"veo-3.1-fast-fal", "veo-3.1-fal", "veo-3.1-lite-fal"} <= fl, fl)
check("h3, wan, omni, ltx dans FL", {"h3-max", "wan-3.0", "gemini-omni-flash", "ltx-2.5-fast"} <= fl, fl)
check("kling turbo, pixverse, Veo Google exclus de FL",
      not ({"kling-v3-turbo-pro", "pixverse-v6", "veo-3.1-google"} & fl), fl)
i2v = {e["id"]: e for e in CI.lister("video_i2v")}
# t406 : les Veo Google, arrêtés par Google le 22/10/2026, sortent du catalogue
_actifs = {k for k, m in F.VIDEO_MODELS.items() if not F.est_retire(m)}
check("video_i2v = tout le registre sauf les retirés", set(i2v) == _actifs, set(i2v) ^ _actifs)
for f_ in ("veo-3.1-fast-fal", "veo-3.1-fal", "veo-3.1-lite-fal"):
    check(f"{f_} : plus de jumeau Google (retiré)", i2v[f_]["jumeau"] is None, i2v[f_].get("jumeau"))
check("jumeau gemini-omni-flash <-> gemini-omni-flash-google",
      i2v["gemini-omni-flash"]["jumeau"] == "gemini-omni-flash-google"
      and i2v["gemini-omni-flash-google"]["jumeau"] == "gemini-omni-flash",
      (i2v["gemini-omni-flash"].get("jumeau"), i2v["gemini-omni-flash-google"].get("jumeau")))
check("omni google voie gemini, clé GEMINI_API_KEY, indispo sans clé",
      i2v["gemini-omni-flash-google"]["voie"] == "gemini" and i2v["gemini-omni-flash-google"]["cle"] == "GEMINI_API_KEY"
      and i2v["gemini-omni-flash-google"]["dispo"] is False, i2v["gemini-omni-flash-google"])
check("nouveaux : voie fal, FAL_KEY, unité s, prix 720p > 0, note vide",
      all(i2v[m]["voie"] == "fal" and i2v[m]["cle"] == "FAL_KEY" and i2v[m]["unite"] == "s"
          and i2v[m]["usd"] > 0 and i2v[m]["note"] == "" for m in NOUVEAUX),
      [(m, i2v[m]) for m in NOUVEAUX])
check("prix catalogue = video_rate 720p (h3 : colonne 768P = 0,08)",
      i2v["h3-max"]["usd"] == 0.08 and i2v["veo-3.1-lite-fal"]["usd"] == 0.03
      and i2v["ltx-2.5-fast"]["usd"] == 0.09, (i2v["h3-max"]["usd"], i2v["veo-3.1-lite-fal"]["usd"]))
_fl = {e["id"]: e for e in CI.lister("video_fl")}
check("video_fl : jumeau nul quand le jumeau n'accepte pas de fin (Veo fal -> Google)",
      all(_fl[m]["jumeau"] is None for m in ("veo-3.1-fast-fal", "veo-3.1-fal", "veo-3.1-lite-fal")),
      [(m, _fl[m]["jumeau"]) for m in ("veo-3.1-fast-fal", "veo-3.1-fal", "veo-3.1-lite-fal")])
check("video_fl : tout jumeau restant est lui-même dans video_fl",
      all(e["jumeau"] is None or e["jumeau"] in _fl for e in _fl.values()))
check("pas de jumeau hors Veo", i2v["wan-3.0"]["jumeau"] is None and i2v["seedance-2.5"]["jumeau"] is None)

# ── [4] prix et schémas ─────────────────────────────────────────────────────
print("[3b] source unique : end_image ; endpoint_fl n'est qu'un routage ; négatif par modèle")
check("endpoint_fl => end_image (accepte_fin) pour chaque modèle",
      all(m["end_image"] for m in F.VIDEO_MODELS.values() if m.get("endpoint_fl")),
      [i for i, m in F.VIDEO_MODELS.items() if m.get("endpoint_fl") and not m["end_image"]])
check("catalogue_ia.accepte_fin EST fal_service.accepte_fin", CI.accepte_fin is F.accepte_fin)
check("accepte_fin == end_image partout",
      all(F.accepte_fin(m) == bool(m["end_image"]) for m in F.VIDEO_MODELS.values()))
# parité avec l'ancienne liste de familles (kling, pixverse, veo_fal) pour les ids d'avant t184
_avant = {"seedance-2": False, "seedance-2-fast": False, "seedance-2.5": False, "kling-v3-pro": True,
          "kling-v3-standard": True, "pixverse-v6": True, "veo-3.1-fast-fal": True}
_ecarts = []
for mid, attendu in _avant.items():
    _, a, notes = F.build_fal_args(mid, image_url="u", prompt="p", negative_prompt="n", duration=5)
    if ("negative_prompt" in a) != attendu or (not attendu and "negative_prompt unsupported -> dropped" not in notes):
        _ecarts.append((mid, a, notes))
check("négatif : parité des ids d'avant t184, note « dropped » sinon", not _ecarts, _ecarts)
_nouveaux_neg = {m: "negative_prompt" in F.build_fal_args(m, image_url="u", prompt="p", negative_prompt="n",
                                                          duration=8)[1]
                 for m in ("veo-3.1-fal", "veo-3.1-lite-fal", "h3-max", "wan-3.0", "gemini-omni-flash",
                           "ltx-2.5-fast", "kling-v3-turbo-pro")}
check("négatif des nouveaux = schémas (Veo oui, les autres non)", _nouveaux_neg == {
    "veo-3.1-fal": True, "veo-3.1-lite-fal": True, "h3-max": False, "wan-3.0": False,
    "gemini-omni-flash": False, "ltx-2.5-fast": False, "kling-v3-turbo-pro": False}, _nouveaux_neg)

print("[3c] pricing.json avec une ANCIENNE table vidéo partielle : fusion par modèle")
_pf = P._PRICING_FILE
_pf.parent.mkdir(parents=True, exist_ok=True)
_pf.write_text('{"video_usd_per_s": {"seedance-2.5": {"720p": 0.5}, "veo-3.1-fast-fal": {"*": 0.12},'
               ' "pixverse-v6": {"*": 0.5}}}', encoding="utf-8")
try:
    check("modèle absent de la table enregistrée : tarif par défaut (veo-3.1-fal 720p = 0,20)",
          P.video_rate("veo-3.1-fal", "720p") == 0.20, P.video_rate("veo-3.1-fal", "720p"))
    check("id surchargé : la valeur de l'utilisateur gagne (veo fast 0,12 ; s2.5 720p 0,5)",
          P.video_rate("veo-3.1-fast-fal", "1080p") == 0.12 and P.video_rate("seedance-2.5", "720p") == 0.5)
    check("un « * » de l'utilisateur l'emporte sur les colonnes par défaut (pixverse 720p et 1080p = 0,5)",
          P.video_rate("pixverse-v6", "720p") == 0.5 and P.video_rate("pixverse-v6", "1080p") == 0.5,
          (P.video_rate("pixverse-v6", "720p"), P.video_rate("pixverse-v6", "1080p")))
    check("fusion par résolution : s2.5 480p garde le défaut 0,2205",
          P.video_rate("seedance-2.5", "480p") == 0.2205, P.video_rate("seedance-2.5", "480p"))
    _vm = {m["id"]: m for m in asyncio.run(R.list_video_models())["models"]}
    check("/video-models sert le tarif fusionné (h3-max présent, veo fast 0,12)",
          _vm["h3-max"]["usd_per_s"].get("720p") == 0.08 and _vm["veo-3.1-fast-fal"]["usd_per_s"] == {"*": 0.12},
          (_vm["h3-max"]["usd_per_s"], _vm["veo-3.1-fast-fal"]["usd_per_s"]))
finally:
    _pf.unlink()

print("[4] prix au registre, garde de coût, schémas recopiés")
for mid in NOUVEAUX:
    check(f"{mid} dans video_usd_per_s", mid in P.DEFAULTS["video_usd_per_s"])
    try:
        op = P.video_request_op(mid, 8, "720p")
        tot = P.estimate({"kind": "campaign", "ops": [op]})["total_usd"]
    except Exception as e:  # noqa: BLE001
        op, tot = {"exc": str(e)}, -1
    check(f"{mid} : la garde chiffre > 0 et nomme le modèle", tot > 0 and op.get("model") == mid, (op, tot))
check("veo std 0,20 $/s, lite 1080p 0,05, wan 1080p 0,20, kling turbo 0,14",
      P.video_rate("veo-3.1-fal", "1080p") == 0.20 and P.video_rate("veo-3.1-lite-fal", "1080p") == 0.05
      and P.video_rate("wan-3.0", "1080p") == 0.20 and P.video_rate("kling-v3-turbo-pro", "720p") == 0.14)
check("défaut inchangé (seedance-2.5)", F.DEFAULT_VIDEO_MODEL == "seedance-2.5")
V = F.VIDEO_MODELS
check("durées : LTX paires 6..20, omni 3..10, wan 2..30, kling turbo 3..15, h3 5..15",
      V["ltx-2.5-fast"]["durations"] == [6, 8, 10, 12, 14, 16, 18, 20]
      and V["gemini-omni-flash"]["durations"] == list(range(3, 11))
      and V["wan-3.0"]["durations"] == list(range(2, 31))
      and V["kling-v3-turbo-pro"]["durations"] == list(range(3, 16))
      and V["h3-max"]["durations"] == list(range(5, 16)))
ep, a = fa("h3-max", "https://x/a.png", "x", duration=6, resolution="720p", end_image_url="https://x/b.png")
check("h3 : 720p -> '768P' (majuscules), prompt_expansion_mode requis, image_url + end_image_url",
      ep == "minimax/h3-max/image-to-video" and a.get("resolution") == "768P"
      and a.get("prompt_expansion_mode") == "balanced" and a.get("image_url") == "https://x/a.png"
      and a.get("end_image_url") == "https://x/b.png" and a.get("duration") == 6, (ep, a))
ep, a = fa("ltx-2.5-fast", "u", "p", duration=7, resolution="1080p", aspect_ratio="9:16", end_image_url="e")
check("ltx : 7 s -> 8 natif, 1080p, 9:16, audio coupé, fin", a.get("duration") == 8 and a.get("resolution") == "1080p"
      and a.get("aspect_ratio") == "9:16" and a.get("generate_audio") is False and a.get("end_image_url") == "e", a)
ep, a = fa("gemini-omni-flash", "u", "p", duration=12, resolution="720p", aspect_ratio="16:9", seed=2)
check("omni : 12 s -> 10, pas de seed ni d'audio", a.get("duration") == 10 and "seed" not in a
      and set(a) == {"prompt", "image_url", "duration", "aspect_ratio", "resolution"}, a)

# ── [5] /video-models ───────────────────────────────────────────────────────
print("[5] /video-models : voie, clé, jumeau, fl")
out = asyncio.run(R.list_video_models())
by = {m["id"]: m for m in out.get("models") or []}
check("ids = registre sauf les retirés (t406), défaut inchangé",
      set(by) == {k for k, m in V.items() if not F.est_retire(m)} and out.get("default") == "seedance-2.5")
check("veo fast fal : fl ET end_image vrais (Quick l'accepte)", by["veo-3.1-fast-fal"].get("fl") is True
      and by["veo-3.1-fast-fal"].get("end_image") is True, by["veo-3.1-fast-fal"])
check("kling turbo : fl faux", by["kling-v3-turbo-pro"].get("fl") is False and by["kling-v3-turbo-pro"].get("end_image") is False)
check("omni google : voie gemini, cle GEMINI_API_KEY, jumeau fal, fl",
      by["gemini-omni-flash-google"].get("voie") == "gemini" and by["gemini-omni-flash-google"].get("cle") == "GEMINI_API_KEY"
      and by["gemini-omni-flash-google"].get("jumeau") == "gemini-omni-flash"
      and by["gemini-omni-flash-google"].get("fl") is True, by["gemini-omni-flash-google"])
check("fl == end_image pour chaque modèle (le bascule de Quick lit end_image)",
      all(m.get("fl") == m.get("end_image") for m in by.values()),
      [i for i, m in by.items() if m.get("fl") != m.get("end_image")])
check("chaque entrée a un tarif $/s", all(m.get("usd_per_s") for m in by.values()),
      [i for i, m in by.items() if not m.get("usd_per_s")])
BUNDLE = ICI.parent.parent / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
_b = BUNDLE.read_text(encoding="utf-8") if BUNDLE.is_file() else ""
check("le bascule de Quick (dzEndOK) lit end_image de /video-models",
      "mm[m2.id]=!!m2.end_image;" in _b and _b.count("function dzEndOK(") == 1, len(_b))

# ── [6] sans FAL_KEY : 503 avant _plafond ───────────────────────────────────
print("[6] nouveaux modèles sans FAL_KEY -> 503 avant _plafond, zéro dépense")
PLAF = []


async def _plafond_espion(ops, categorie="", *a, **k):
    PLAF.append((categorie, ops))
    raise HTTPException(402, "ESPION _plafond : arrêt du banc")

R._plafond = _plafond_espion
SRC, FIN = "depart.png", "fin.png"
Image.new("RGB", (64, 64), (10, 20, 30)).save(settings.images_path / SRC)
Image.new("RGB", (64, 64), (90, 20, 30)).save(settings.images_path / FIN)
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


def corps(model):
    return {"image_filename": SRC, "image_filename_end": FIN, "custom_prompt": "un chat",
            "video_model": model, "duration_s": 5}


settings.FAL_KEY = ""
for mid in NOUVEAUX:
    PLAF.clear()
    r0, d0 = RESEAU["n"], n_depenses()
    st, js = call("/generate", corps(mid))
    check(f"{mid} sans FAL_KEY -> 503 nomme FAL_KEY", st == 503 and "FAL_KEY" in str(js), f"{st} {js}")
    check(f"{mid} sans clé : _plafond jamais appelé, zéro dépense, aucun réseau",
          PLAF == [] and n_depenses() == d0 and RESEAU["n"] == r0, f"{PLAF} {d0} {RESEAU}")
settings.FAL_KEY = "test-key"
PLAF.clear()
st, js = call("/generate", corps("veo-3.1-fast-fal"))
check("TÉMOIN : avec FAL_KEY, Veo fast + image de fin atteint _plafond (402 de l'espion)",
      st == 402 and len(PLAF) == 1, f"{st} {js} {PLAF}")

# ── [6a] t406 : un Veo Google (arrêté le 22/10/2026) est refusé en 410 AVANT la clé et _plafond
print("[6a] Veo Google retirés : 410 qui nomme Gemini Omni Flash (Google), avant la clé et _plafond")
settings.GEMINI_API_KEY = ""
for mid in ("veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google"):
    PLAF.clear()
    r0, d0 = RESEAU["n"], n_depenses()
    b = dict(corps(mid), image_filename_end=None)
    st, js = call("/generate", b)
    check(f"{mid} -> 410 (même sans clé) qui nomme le remplaçant",
          st == 410 and "Gemini Omni Flash (Google)" in str(js), f"{st} {js}")
    check(f"{mid} : _plafond jamais appelé, zéro dépense, aucun réseau",
          PLAF == [] and n_depenses() == d0 and RESEAU["n"] == r0, f"{PLAF} {d0} {RESEAU}")
PLAF.clear()
st, js = call("/generate", corps("gemini-omni-flash-google"))
check("TÉMOIN : Omni Google sans GEMINI_API_KEY -> 503 nomme la clé, avant _plafond",
      st == 503 and "GEMINI_API_KEY" in str(js) and PLAF == [], f"{st} {js} {PLAF}")
settings.GEMINI_API_KEY = "test-google"
PLAF.clear()
st, js = call("/generate", corps("gemini-omni-flash-google"))
check("TÉMOIN : Omni Google + image de fin avec la clé atteint _plafond (402 de l'espion)",
      st == 402 and len(PLAF) == 1, f"{st} {js} {PLAF}")
settings.GEMINI_API_KEY = ""

# ── [6b] image de fin sur un modèle qui n'en accepte pas : 400 avant _plafond
print("[6b] image de fin refusée en 400 AVANT _plafond (Kling turbo, PixVerse ; t406 : les Veo Google sont retirés)")
settings.GEMINI_API_KEY = "test-google"


def routes_fin(model):
    b = corps(model)
    return (("/generate", b), ("/generate/batch", dict(b, variations_count=2)),
            ("/generate/composition", {"seedance": b,
                                       "heygen": {"script": "bonjour", "avatar_id": "a", "voice_id": "v"},
                                       "layout": "sequential"}))


for mid in ("kling-v3-turbo-pro", "pixverse-v6"):
    for chemin, b in routes_fin(mid):
        PLAF.clear()
        r0, d0 = RESEAU["n"], n_depenses()
        st, js = call(chemin, b)
        check(f"{chemin} {mid} + fin -> 400 « n'accepte pas d'image de fin »",
              st == 400 and "n'accepte pas d'image de fin" in str(js), f"{st} {js}")
        check(f"{chemin} {mid} + fin : _plafond jamais appelé, zéro dépense, aucun réseau",
              PLAF == [] and n_depenses() == d0 and RESEAU["n"] == r0, f"{PLAF} {d0} {RESEAU}")


async def _req_en(path, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.post("/api" + path, json=body, headers={"Accept-Language": "en-US,en;q=0.9"})

PLAF.clear()
_r = asyncio.run(_req_en("/generate", corps("kling-v3-turbo-pro")))
check("refus en anglais (« has no last-frame input »), avant _plafond",
      _r.status_code == 400 and "has no last-frame input" in _r.text and PLAF == [], _r.text)
# rendu de gabarit : un slot Seedance avec image de fin (même garde, avant _plafond)
from app.services.elevenlabs_service import VoiceoverService             # noqa: E402
VoiceoverService.is_enabled = staticmethod(lambda: True)   # la voix n'est pas le sujet : le témoin atteint _plafond
TID = R.template_engine.list_templates()[0]["id"]


def gabarit(model):
    return (f"/layout-templates/{TID}/render",
            {"template_id": TID, "slot_values": {"a": {"source_kind": "seedance", "seedance": corps(model)}}})


for mid in ("kling-v3-turbo-pro", "pixverse-v6"):
    chemin, b = gabarit(mid)
    PLAF.clear()
    r0, d0 = RESEAU["n"], n_depenses()
    st, js = call(chemin, b)
    check(f"rendu de gabarit {mid} + fin -> 400 « n'accepte pas d'image de fin »",
          st == 400 and "n'accepte pas d'image de fin" in str(js), f"{st} {js}")
    check(f"rendu de gabarit {mid} + fin : _plafond jamais appelé, zéro dépense, aucun réseau",
          PLAF == [] and n_depenses() == d0 and RESEAU["n"] == r0, f"{PLAF} {d0} {RESEAU}")
PLAF.clear()
st, js = call(*gabarit("veo-3.1-fast-fal"))
check("TÉMOIN : rendu de gabarit Veo fast fal + fin atteint _plafond (402 de l'espion)",
      st == 402 and len(PLAF) == 1, f"{st} {js} {PLAF}")
for chemin, b in routes_fin("veo-3.1-fast-fal")[:2]:
    PLAF.clear()
    st, js = call(chemin, b)
    check(f"TÉMOIN : {chemin} Veo fast fal + fin passe la garde de fin (402 de l'espion _plafond)",
          st == 402 and len(PLAF) == 1, f"{st} {js}")
PLAF.clear()
_b = corps("kling-v3-turbo-pro")
_b.pop("image_filename_end")
st, js = call("/generate", _b)
check("TÉMOIN : Kling turbo SANS fin atteint _plafond", st == 402 and len(PLAF) == 1, f"{st} {js}")
settings.GEMINI_API_KEY = ""

# ── [7] client fal : couture _soumettre ─────────────────────────────────────
print("[7] le client fal envoie Veo + fin à l'endpoint FL")
SOUMIS = []


class _Handle:
    async def iter_events(self, with_logs=True):
        if False:
            yield None

    async def get(self):
        return {"video": {"url": "https://x/v.mp4"}}


async def _soumettre_espion(endpoint, arguments):
    SOUMIS.append((endpoint, dict(arguments)))
    return _Handle()

F.FalSeedanceClient._soumettre = staticmethod(_soumettre_espion)
r0 = RESEAU["n"]
res = asyncio.run(F.FalSeedanceClient().generate_video(
    image_url="https://x/a.png", end_image_url="https://x/b.png", prompt="p", duration=8,
    aspect_ratio="9:16", resolution="720p", model_id="veo-3.1-fast-fal"))
check("une seule soumission, à l'endpoint FL", len(SOUMIS) == 1
      and SOUMIS[0][0] == "fal-ai/veo3.1/fast/first-last-frame-to-video", SOUMIS)
check("first/last, pas d'image_url", SOUMIS and SOUMIS[0][1].get("first_frame_url") == "https://x/a.png"
      and SOUMIS[0][1].get("last_frame_url") == "https://x/b.png" and "image_url" not in SOUMIS[0][1], SOUMIS)
check("résultat relu, aucun réseau", res.get("video", {}).get("url") == "https://x/v.mp4" and RESEAU["n"] == r0)

check("aucun appel réseau dans tout le banc", RESEAU["n"] == 0, RESEAU)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
