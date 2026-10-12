# -*- coding: utf-8 -*-
"""t187 (G5, plan « Génération IA enrichie ») — les bruitages texte ET vidéo, et la musique à jour.

UN registre (`sfx_service.SFX_MODELS`, 10 entrées, schémas fal relus le 12/10/2026), le catalogue (natures
`sfx_texte`, `sfx_video`, `musique`), le devis (`kind: sfx` avec `modele`, `kind: sfx_video`, `kind: music`), les
routes `/audio/sfx` (accepte `modele`), `/audio/sfx-video` (neuve, payante) et `/audio/music` (refus avant la garde).

Ce que le banc tient :
  [0] requêtes PURES (`build_request`) : celles du plan à la lettre (Sonilo, Mirelo text_prompt, ElevenLabs via fal
      text + duration_seconds, Kling v2a = EXACTEMENT {video_url, sound_effect_prompt}) ; Mirelo envoie TOUJOURS
      num_samples (défaut fal : 2) ; Hunyuan sans description -> ValueError ; un modèle vidéo sans vidéo ->
      ValueError ; ElevenLabs direct -> ValueError (aucune requête fal) ; durée bornée au modèle, type gardé ;
  [1] catalogue : jumeaux ElevenLabs direct <-> via fal, voie « elevenlabs » pour le direct ; >= 5 texte, >= 5 vidéo ;
      sans clé les modèles restent LISTÉS (dispo False, nom de la clé) ; prix Sonilo / Kling ; « à mesurer » ailleurs ;
  [2] /audio/sfx : sans modele = ElevenLabs direct (témoin, espion generate_sfx) ; modele=sonilo-1.1 -> fal (espion
      _fal_subscribe) ; sans clé ElevenLabs mais avec FAL_KEY -> elevenlabs-v2-fal + note « via fal » ; ordre des
      refus (400 id -> 503 clé -> 400 description) ; sans clé : ZÉRO ligne `depenses` ; témoin : UNE ligne quand la
      garde passe ; variations : Mirelo en un appel (num_samples), Sonilo en N appels ;
  [3] /audio/sfx-video : PAYANTES le liste, la route est gardée et atteint `generer_sfx` ; ordre des refus ;
      confinement du nom de fichier et du clip ; devis = même chiffre que la réponse du tir ; garder_voix ->
      keep_speech_vocal ; vidéo sonorisée -> job fini + son extrait ; Kling par clip_id ; la garde passe AVANT le tir ;
  [4] musique : lyria-3.5, elevenlabs-music-2.5, minimax-music-3, stable-audio-3, mureka-9.5 au registre et au
      catalogue ; défaut toujours lyria3 ; charges utiles exactes ; ElevenLabs Music arrondi à la minute supérieure ;
      Mureka avec / sans paroles ; MiniMax 3 sans paroles -> 400 AVANT la garde ; sans FAL_KEY -> 503 ; cassetteai ;
  [5] écrans (statique + aides exécutées sous node) : Son & VFX (sélecteur sfx_texte, prix lu au devis du backend,
      jamais d'option grisée) et tiroir Sons (sélecteur, « Depuis la vidéo » sur un clip vidéo sélectionné, garder la
      voix pour Sonilo, devis de la route).

AUCUN appel réseau réel : les fal_client.* sont des gardes qui COMPTENT ; les seams de sfx_service sont des
enregistreurs.
Run (depuis backend/) : & $PY tests/test_sfx_modeles.py"""
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

_tmp = tempfile.mkdtemp(prefix="dzsfx187_")
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

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import sfx_service as S, catalogue_ia as CI, pricing as P, music_service as MS  # noqa: E402
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
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True, capture_output=True, timeout=120)


# de vrais fichiers : un son de 1 s, une vidéo de 2 s AVEC son, une vidéo de 2 s sans son
FIX = W / "fixtures"
FIX.mkdir()
WAV = FIX / "son.wav"
MP4_SON = FIX / "sonorisee.mp4"
MP4 = FIX / "source.mp4"
_ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(WAV))
_ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=64x64:d=2", "-f", "lavfi", "-i", "sine=frequency=330:duration=2",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(MP4_SON))
_ffmpeg("-f", "lavfi", "-i", "color=c=red:s=64x64:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(MP4))
UPLOADS = settings.outputs_path / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
shutil.copy2(MP4, UPLOADS / "plan.mp4")

# ── seams de sfx_service : des enregistreurs ────────────────────────────────
SEAMS = {"up": [], "sub": [], "dl": []}
REPONSE = {"v": None}


async def _up(p):
    SEAMS["up"].append(pathlib.Path(p).name)
    return "http://fal.test/in"


async def _sub(endpoint, arguments):
    SEAMS["sub"].append((endpoint, dict(arguments)))
    if REPONSE["v"] is not None:
        return REPONSE["v"]
    return {"audio": {"url": "http://fal.test/out.wav"}}


async def _dl(url, dest):
    SEAMS["dl"].append(pathlib.Path(dest).name)
    dest = pathlib.Path(dest)
    shutil.copy2(MP4_SON if dest.suffix in (".mp4", ".mov", ".webm") else WAV, dest)


S._upload, S._fal_subscribe, S._download = _up, _sub, _dl


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


# ════════════════════════════════════════════════════════════════════════════
print("\n[0] requêtes pures")
check("le registre compte 10 entrées", len(S.SFX_MODELS) == 10, str(list(S.SFX_MODELS)))
ep, a = S.build_request("sonilo-1.1", prompt="porte qui grince", duree=4)
check("sonilo", ep == "sonilo/v1.1/text-to-sound-effects"
      and a == {"prompt": "porte qui grince", "duration": 4, "audio_format": "wav"}, a)
ep, a = S.build_request("mirelo-1.6", prompt="pluie", duree=6)
check("mirelo text_prompt", a.get("text_prompt") == "pluie" and "prompt" not in a, a)
check("mirelo : num_samples TOUJOURS envoyé (défaut fal 2 = deux sons facturés)", a.get("num_samples") == 1, a)
ep, a = S.build_request("elevenlabs-v2-fal", prompt="tonnerre", duree=3)
check("eleven fal = text + duration_seconds", a.get("text") == "tonnerre" and a.get("duration_seconds") == 3, a)
check("eleven fal : prompt_influence seulement si donné, borné 0..1",
      "prompt_influence" not in a and S.build_request("elevenlabs-v2-fal", prompt="x", influence=1.7)[1].get(
          "prompt_influence") == 1.0 and "prompt_influence" not in S.build_request("sonilo-1.1", prompt="x",
                                                                                     influence=0.5)[1])
check("eleven fal : endpoint v2 et mp3_44100_128",
      ep == "fal-ai/elevenlabs/sound-effects/v2" and a.get("output_format") == "mp3_44100_128", (ep, a))
ep, a = S.build_request("kling-v2a", prompt="pas sur gravier", video_url="https://x/v.mp4")
check("kling v2a", a == {"video_url": "https://x/v.mp4", "sound_effect_prompt": "pas sur gravier"}, a)
check("kling v2a : endpoint", ep == "fal-ai/kling-video/video-to-audio", ep)
ep, a = S.build_request("stable-audio-3-sfx", prompt="vent", duree=500)
check("stable audio 3 SFX : durée bornée à 120, wav",
      ep == "fal-ai/stable-audio-3/small/sfx/text-to-audio" and a == {"prompt": "vent", "duration": 120.0,
                                                                     "output_format": "wav"}, a)
ep, a = S.build_request("sonilo-video", prompt="", video_url="https://x/v.mp4", garder_voix=True)
check("sonilo vidéo : video_url, keep_speech_vocal, wav, pas de prompt vide",
      ep == "sonilo/v1.1/video-to-sound-effects"
      and a == {"video_url": "https://x/v.mp4", "keep_speech_vocal": True, "audio_format": "wav"}, a)
ep, a = S.build_request("mirelo-video", prompt="foule", video_url="https://x/v.mp4", duree=95)
check("mirelo vidéo : text_prompt, durée bornée à 60, num_samples 1",
      ep == "mirelo-ai/sfx1.6/video-to-video" and a == {"video_url": "https://x/v.mp4", "text_prompt": "foule",
                                                         "duration": 60.0, "num_samples": 1}, a)
ep, a = S.build_request("thinksound", video_url="https://x/v.mp4", prompt="porte")
check("thinksound : video_url + prompt", ep == "fal-ai/thinksound" and a == {"video_url": "https://x/v.mp4",
                                                                              "prompt": "porte"}, a)
for mid, kw, quoi in (("hunyuan-foley", {"video_url": "https://x/v.mp4"}, "description"),
                      ("sonilo-video", {}, "vidéo"),
                      ("elevenlabs-direct", {"prompt": "x"}, "API directe"),
                      ("zzz", {}, "inconnu"),
                      ("sonilo-1.1", {"prompt": "  "}, "description")):
    try:
        S.build_request(mid, **kw)
        check(f"{mid} sans {quoi} -> ValueError", False)
    except ValueError as e:
        check(f"{mid} ({quoi}) -> ValueError : {str(e)[:60]}", True)
ep, a = S.build_request("hunyuan-foley", video_url="https://x/v.mp4", prompt="pluie sur tôle")
check("hunyuan : video_url ET text_prompt", a == {"video_url": "https://x/v.mp4", "text_prompt": "pluie sur tôle"}, a)
check("durée « auto » (None, 0, '') -> rien d'envoyé",
      all("duration" not in S.build_request("sonilo-1.1", prompt="x", duree=d)[1] for d in (None, 0, "")))
check("ordre : ElevenLabs direct en tête, son jumeau fal juste après",
      list(S.SFX_MODELS)[:2] == ["elevenlabs-direct", "elevenlabs-v2-fal"], list(S.SFX_MODELS)[:2])

# ════════════════════════════════════════════════════════════════════════════
print("\n[1] deux voies ElevenLabs, catalogue")
t = {e["id"]: e for e in CI.lister("sfx_texte")}
v = {e["id"]: e for e in CI.lister("sfx_video")}
check("jumeaux eleven", t["elevenlabs-direct"]["jumeau"] == "elevenlabs-v2-fal"
      and t["elevenlabs-v2-fal"]["jumeau"] == "elevenlabs-direct")
check("direct = voie elevenlabs", t["elevenlabs-direct"]["voie"] == "elevenlabs"
      and t["elevenlabs-direct"]["cle"] == "ELEVENLABS_API_KEY")
check(">= 5 sfx texte, >= 5 sfx vidéo", len(t) >= 5 and len(CI.lister("sfx_video")) >= 5, (len(t), len(v)))
check("sans clé ElevenLabs : le direct reste LISTÉ, dispo False (choisissable, refusé au tir)",
      t["elevenlabs-direct"]["dispo"] is False, t["elevenlabs-direct"])
settings.FAL_KEY = ""
t0 = {e["id"]: e for e in CI.lister("sfx_texte") + CI.lister("sfx_video")}
settings.FAL_KEY = "test-key"
check("sans FAL_KEY : les 9 modèles fal restent LISTÉS, dispo False, cle FAL_KEY",
      sum(1 for e in t0.values() if e["voie"] == "fal" and e["dispo"] is False and e["cle"] == "FAL_KEY") == 9, "")
check("prix : sonilo 0,0018 $/s, sonilo vidéo 0,009 $/s, kling 0,035 $ la vidéo",
      t["sonilo-1.1"]["usd"] == 0.0018 and t["sonilo-1.1"]["unite"] == "s"
      and v["sonilo-video"]["usd"] == 0.009 and v["kling-v2a"]["usd"] == 0.035 and v["kling-v2a"]["unite"] == "video", "")
check("« à mesurer » : eleven fal, mirelo (x2), stable audio, hunyuan, thinksound",
      all(x["note"] == CI.NOTE_A_MESURER and x["usd"] == 0.0 for x in
          (t["elevenlabs-v2-fal"], t["mirelo-1.6"], t["stable-audio-3-sfx"], v["mirelo-video"], v["hunyuan-foley"],
           v["thinksound"])), "")
check("ElevenLabs direct : grille d'avant (40 crédits/s x 0,00024 $)", abs(t["elevenlabs-direct"]["usd"] - 0.0096) < 1e-12,
      t["elevenlabs-direct"]["usd"])
check("prompt exigé : hunyuan et kling (vidéo), tous les modèles texte ; voix : sonilo vidéo seul",
      {k for k, e in v.items() if e["prompt"]} == {"hunyuan-foley", "kling-v2a"}
      and all(e["prompt"] for e in t.values()) and {k for k, e in v.items() if e["voix"]} == {"sonilo-video"}, "")
st, js = call("GET", "/ia/catalogue", params={"nature": "sfx_video"})
check("GET /ia/catalogue?nature=sfx_video : 5 entrées", st == 200 and len(js["modeles"]) == 5, str(js)[:200])
check("devis : sonilo 10 s x2 = 0,036 $", abs(P.estimate({"kind": "sfx", "modele": "sonilo-1.1", "secondes": 10,
                                                          "echantillons": 2})["total_usd"] - 0.036) < 1e-9)
check("devis : sonilo sans durée = défaut du schéma (8 s) = 0,0144 $",
      abs(P.estimate({"kind": "sfx", "modele": "sonilo-1.1"})["total_usd"] - 0.0144) < 1e-9)
check("devis : sonilo vidéo 12 s = 0,108 $ ; kling 12 s = 0,035 $",
      abs(P.estimate({"kind": "sfx_video", "modele": "sonilo-video", "secondes": 12})["total_usd"] - 0.108) < 1e-9
      and abs(P.estimate({"kind": "sfx_video", "modele": "kling-v2a", "secondes": 12})["total_usd"] - 0.035) < 1e-9)
_e = P.estimate({"kind": "sfx_video", "modele": "thinksound", "secondes": 12})
check("devis : thinksound = 0 et la ligne dit « prix à mesurer » (aucune durée de calcul inventée)",
      _e["total_usd"] == 0.0 and "prix à mesurer" in _e["breakdown"][0]["label"], _e)
check("devis : sans modele, la grille ElevenLabs d'avant inchangée (3 s x2 = 0,0576 $)",
      abs(P.estimate({"kind": "sfx", "duration_s": 3, "n": 2})["total_usd"] - 0.0576) < 1e-9
      and P.estimate({"kind": "sfx", "duration_s": 3, "n": 2})["breakdown"][0]["provider"] == "elevenlabs")

# ════════════════════════════════════════════════════════════════════════════
print("\n[2] /audio/sfx")
ESP_EL = []
_vrai_gen = S.generate_sfx


def _espion_el(prompt, duration_s=None, prompt_influence=0.3, variations=1):
    ESP_EL.append((prompt, duration_s, variations))
    return [{"filename": "sfx_espion.mp3", "url": "/api/audio/sfx_espion.mp3", "name": "sfx_espion.mp3",
             "size_kb": 1, "dur": 1.0}], None


S.generate_sfx = _espion_el
settings.ELEVENLABS_API_KEY = "el-test"
raz()
d0 = n_depenses()
st, js = call("POST", "/audio/sfx", {"prompt": "porte qui claque", "duration_s": 2, "variations": 2})
check("TÉMOIN sans modele, clé ElevenLabs posée : ElevenLabs direct (espion generate_sfx), aucun appel fal",
      st == 200 and ESP_EL == [("porte qui claque", 2.0, 2)] and SEAMS["sub"] == [] and js.get("modele") ==
      "elevenlabs-direct" and "note" not in js, f"{st} {js} {ESP_EL}")
check("TÉMOIN : la garde passe et écrit UNE ligne depenses (ElevenLabs, 0,0384 $)", n_depenses() == d0 + 1,
      f"{d0} -> {n_depenses()}")
raz()
d0 = n_depenses()
st, js = call("POST", "/audio/sfx", {"prompt": "porte qui grince", "duration_s": 4, "modele": "sonilo-1.1"})
check("modele=sonilo-1.1 -> fal (espion _fal_subscribe), son rangé dans le dossier audio",
      st == 200 and SEAMS["sub"] == [("sonilo/v1.1/text-to-sound-effects",
                                      {"prompt": "porte qui grince", "duration": 4.0, "audio_format": "wav"})]
      and len(js.get("items", [])) == 1 and (S._audio_dir() / js["items"][0]["filename"]).is_file(), f"{st} {js} {SEAMS}")
_meta = S.load_meta().get(js["items"][0]["filename"]) if st == 200 else {}
check("sidecar : kind sfx, modèle nommé, provider fal", (_meta or {}).get("kind") == "sfx"
      and _meta.get("model") == "sonilo-1.1" and _meta.get("provider") == "fal", _meta)
check("sonilo 4 s : la garde écrit UNE ligne depenses", n_depenses() == d0 + 1, f"{d0} -> {n_depenses()}")
check("ElevenLabs direct jamais appelé pour un modèle fal", len(ESP_EL) == 1, ESP_EL)
raz()
st, js = call("POST", "/audio/sfx", {"prompt": "pluie", "modele": "mirelo-1.6", "variations": 3})
check("mirelo, 3 variations : UN appel avec num_samples 3",
      st == 200 and len(SEAMS["sub"]) == 1 and SEAMS["sub"][0][1].get("num_samples") == 3, f"{st} {SEAMS['sub']}")
raz()
REPONSE["v"] = {"audio": [{"url": "http://fal.test/a.wav"}, {"url": "http://fal.test/b.wav"}], "model": "m"}
st, js = call("POST", "/audio/sfx", {"prompt": "pluie", "modele": "mirelo-1.6", "variations": 2})
check("mirelo rend une LISTE `audio` : deux sons rangés", st == 200 and len(js.get("items", [])) == 2, f"{st} {js}")
raz()
st, js = call("POST", "/audio/sfx", {"prompt": "vent", "modele": "sonilo-1.1", "variations": 2})
check("sonilo, 2 variations : DEUX appels (pas de num_samples au schéma)",
      st == 200 and len(SEAMS["sub"]) == 2 and all("num_samples" not in a for _, a in SEAMS["sub"]), SEAMS["sub"])
# sans clé ElevenLabs, avec FAL_KEY : le jumeau fal, « via fal »
settings.ELEVENLABS_API_KEY = ""
raz()
st, js = call("POST", "/audio/sfx", {"prompt": "tonnerre", "duration_s": 3})
check("sans clé ElevenLabs, avec FAL_KEY : elevenlabs-v2-fal + note « via fal »",
      st == 200 and js.get("modele") == "elevenlabs-v2-fal" and js.get("note") == "via fal"
      and SEAMS["sub"] and SEAMS["sub"][0][0] == "fal-ai/elevenlabs/sound-effects/v2"
      and SEAMS["sub"][0][1].get("text") == "tonnerre" and SEAMS["sub"][0][1].get("duration_seconds") == 3.0,
      f"{st} {js} {SEAMS['sub']}")
# ordre des refus
raz()
d0 = n_depenses()
st, js = call("POST", "/audio/sfx", {"prompt": "x", "modele": "zzz"})
check("modèle inconnu -> 400 nommé", st == 400 and "inconnu" in detail(js), f"{st} {js}")
st, js = call("POST", "/audio/sfx", {"prompt": "x", "modele": "kling-v2a"})
check("modèle VIDÉO sur /audio/sfx -> 400", st == 400 and "Kling" in detail(js), f"{st} {js}")
st, js = call("POST", "/audio/sfx", {"prompt": "x", "modele": "elevenlabs-direct"})
check("elevenlabs-direct sans sa clé -> 503 qui nomme ELEVENLABS_API_KEY",
      st == 503 and "ELEVENLABS_API_KEY" in detail(js), f"{st} {js}")
settings.FAL_KEY = ""
st, js = call("POST", "/audio/sfx", {"prompt": "x"})
check("sans AUCUNE clé, sans modele -> 503 ELEVENLABS_API_KEY", st == 503 and "ELEVENLABS_API_KEY" in detail(js),
      f"{st} {js}")
st, js = call("POST", "/audio/sfx", {"prompt": "", "modele": "sonilo-1.1"})
check("sans FAL_KEY : 503 FAL_KEY AVANT le refus de la description vide", st == 503 and "FAL_KEY" in detail(js),
      f"{st} {js}")
st, js = call("POST", "/audio/sfx", {"prompt": "x", "modele": "zzz"})
check("sans clé : un id inconnu reste un 400 (l'id passe avant la clé)", st == 400, f"{st} {js}")
check("sans clé : ZÉRO ligne depenses, aucun appel fal", n_depenses() == d0 and SEAMS["sub"] == [],
      f"{d0} -> {n_depenses()} {SEAMS['sub']}")
settings.FAL_KEY = "test-key"
st, js = call("POST", "/audio/sfx", {"prompt": "", "modele": "sonilo-1.1"})
check("clé posée, description vide -> 400", st == 400, f"{st} {js}")
st, js = call("POST", "/audio/sfx", {"prompt": "x", "modele": "sonilo-1.1", "duration_s": "abc"})
check("durée illisible -> 400", st == 400, f"{st} {js}")
check("refus 400 : zéro ligne depenses, aucun appel fal", n_depenses() == d0 and SEAMS["sub"] == [], "")
S.generate_sfx = _vrai_gen
_PLAF = R._plafond
OPS = []


async def _plaf_402(op, cat, ref=None):
    OPS.append(op)
    raise HTTPException(402, "stop banc")


R._plafond = _plaf_402
raz()
st, js = call("POST", "/audio/sfx", {"prompt": "vent", "modele": "sonilo-1.1", "duration_s": 300, "variations": 2})
check("la garde reçoit LE devis du modèle (durée bornée 180, 2 échantillons) et arrête AVANT le tir",
      st == 402 and OPS[-1] == {"kind": "sfx", "modele": "sonilo-1.1", "secondes": 180.0, "echantillons": 2}
      and SEAMS["sub"] == [], f"{st} {OPS[-1:]} {SEAMS['sub']}")
R._plafond = _PLAF

# ════════════════════════════════════════════════════════════════════════════
print("\n[3] /audio/sfx-video")
_src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
check("PAYANTES le liste", '("routes", "POST", "/audio/sfx-video")' in _src)
_rec = RP.recenser()
_k = ("routes", "POST", "/audio/sfx-video")
check("recensement : la route est gardée et atteint le puits generer_sfx",
      _k in _rec and _rec[_k]["garde"] and "generer_sfx" in _rec[_k]["puits"], str(_rec.get(_k)))
check("recensement : /audio/sfx atteint aussi generer_sfx (et reste gardée)",
      "generer_sfx" in _rec[("routes", "POST", "/audio/sfx")]["puits"] and _rec[("routes", "POST", "/audio/sfx")]["garde"])
raz()
d0 = n_depenses()
st, js = call("POST", "/audio/sfx-video", {"modele": "zzz", "video_filename": "plan.mp4"})
check("modèle inconnu -> 400", st == 400 and "inconnu" in detail(js), f"{st} {js}")
st, js = call("POST", "/audio/sfx-video", {"modele": "sonilo-1.1", "video_filename": "plan.mp4"})
check("modèle TEXTE sur /audio/sfx-video -> 400", st == 400, f"{st} {js}")
settings.FAL_KEY = ""
st, js = call("POST", "/audio/sfx-video", {"modele": "hunyuan-foley"})
check("sans FAL_KEY -> 503 qui nomme FAL_KEY, AVANT la vidéo et la description manquantes",
      st == 503 and "FAL_KEY" in detail(js), f"{st} {js}")
st, js = call("POST", "/audio/sfx-video", {"modele": "sonilo-video", "video_filename": "plan.mp4", "devis": True})
check("sans FAL_KEY, le DEVIS reste servi (le modèle sans clé garde son prix)",
      st == 200 and js.get("devis") is True and js.get("modele") == "sonilo-video", f"{st} {js}")
settings.FAL_KEY = "test-key"
check("sans clé : ZÉRO ligne depenses, rien envoyé", n_depenses() == d0 and SEAMS["sub"] == [] and SEAMS["up"] == [],
      f"{d0} -> {n_depenses()}")
for corps, code, quoi in (({"modele": "sonilo-video"}, 400, "aucune vidéo"),
                          ({"modele": "sonilo-video", "video_filename": "../plan.mp4"}, 400, "« .. »"),
                          ({"modele": "sonilo-video", "video_filename": "a\\plan.mp4"}, 400, "antislash"),
                          ({"modele": "sonilo-video", "video_filename": "uploads/plan.mp4"}, 400, "séparateur"),
                          ({"modele": "sonilo-video", "video_filename": "C:plan.mp4"}, 400, "lecteur"),
                          ({"modele": "sonilo-video", "video_filename": "plan.txt"}, 400, "extension"),
                          ({"modele": "sonilo-video", "video_filename": "absent.mp4"}, 404, "absente"),
                          ({"modele": "sonilo-video", "clip_id": "../x"}, 400, "clip_id refusé"),
                          ({"modele": "sonilo-video", "clip_id": "inconnu-123"}, 404, "clip inconnu")):
    st, js = call("POST", "/audio/sfx-video", corps)
    check(f"confinement : {quoi} -> {code}", st == code, f"{st} {js}")
st, js = call("POST", "/audio/sfx-video", {"modele": "hunyuan-foley", "video_filename": "plan.mp4"})
check("hunyuan sans description -> 400", st == 400 and "description" in detail(js), f"{st} {js}")
st, js = call("POST", "/audio/sfx-video", {"modele": "kling-v2a", "video_filename": "plan.mp4", "prompt": " "})
check("kling sans description -> 400 (sinon fal pose « Car tires screech… »)", st == 400, f"{st} {js}")
check("refus : zéro ligne depenses, rien envoyé", n_depenses() == d0 and SEAMS["sub"] == [] and SEAMS["up"] == [], "")
st, devis = call("POST", "/audio/sfx-video", {"modele": "sonilo-video", "video_filename": "plan.mp4", "devis": True})
check("devis sonilo vidéo, source de 2 s = 0,018 $, rien tiré ni écrit",
      st == 200 and abs(devis.get("usd", -1) - 0.018) < 1e-3 and abs(devis.get("secondes", 0) - 2.0) < 0.1
      and SEAMS["sub"] == [] and n_depenses() == d0, f"{st} {devis}")
raz()
st, js = call("POST", "/audio/sfx-video", {"modele": "sonilo-video", "video_filename": "plan.mp4",
                                           "prompt": "pas dans la neige", "garder_voix": True})
check("sonilo vidéo : la vidéo part (upload), keep_speech_vocal True, un son rangé",
      st == 200 and SEAMS["up"] == ["plan.mp4"] and SEAMS["sub"]
      and SEAMS["sub"][0] == ("sonilo/v1.1/video-to-sound-effects",
                              {"video_url": "http://fal.test/in", "prompt": "pas dans la neige",
                               "keep_speech_vocal": True, "audio_format": "wav"})
      and len(js.get("items", [])) == 1 and js.get("videos") == [], f"{st} {js} {SEAMS}")
check("même chiffre avant (devis) et après (réponse du tir)", st == 200 and js.get("usd") == devis.get("usd"),
      f"{devis.get('usd')} / {js.get('usd') if isinstance(js, dict) else js}")
check("TÉMOIN : la garde passe et écrit UNE ligne depenses (0,018 $)", n_depenses() == d0 + 1, f"{d0} -> {n_depenses()}")
raz()
REPONSE["v"] = {"video": [{"url": "http://fal.test/sono.mp4"}], "model": "m"}
st, js = call("POST", "/audio/sfx-video", {"modele": "mirelo-video", "video_filename": "plan.mp4", "prompt": "foule"})
_jid = (js.get("videos") or [{}])[0].get("job_id") if isinstance(js, dict) else None


async def _job(j):
    async with async_session_factory() as s:
        return await s.get(JobRecord, j)
_jr = loop.run_until_complete(_job(_jid)) if _jid else None
check("mirelo vidéo -> vidéo SONORISÉE : job fini (provider sfx_video), fichier présent",
      st == 200 and _jr is not None and _jr.status == "done" and _jr.provider == "sfx_video"
      and pathlib.Path(_jr.final_video_path).is_file(), f"{st} {js}")
check("mirelo vidéo : sa piste son EXTRAITE en mp3 dans le dossier audio",
      st == 200 and len(js["items"]) == 1 and js["items"][0]["filename"].endswith(".mp3")
      and (S._audio_dir() / js["items"][0]["filename"]).stat().st_size > 0, f"{js}")
check("mirelo vidéo : la durée de la source part (2 s), num_samples 1",
      SEAMS["sub"] and abs(SEAMS["sub"][0][1].get("duration", 0) - 2.0) < 0.1
      and SEAMS["sub"][0][1].get("num_samples") == 1, SEAMS["sub"])
# un clip du Montage : son job
_cid = "clip-job-187"


async def _mk_job():
    from app.services.storage import JobRecord as JR
    async with async_session_factory() as s:
        s.add(JR(id=_cid, status="done", progress=100, title="plan", image_filename="plan.mp4",
                 final_video_path=str(UPLOADS / "plan.mp4"), video_path=str(UPLOADS / "plan.mp4")))
        await s.commit()
loop.run_until_complete(_mk_job())
raz()
REPONSE["v"] = {"video": {"url": "http://fal.test/k.mp4"}, "audio": {"url": "http://fal.test/k.wav"}}
st, js = call("POST", "/audio/sfx-video", {"modele": "kling-v2a", "clip_id": _cid, "prompt": "pas sur gravier"})
check("kling par clip_id : EXACTEMENT {video_url, sound_effect_prompt}",
      st == 200 and SEAMS["sub"] == [("fal-ai/kling-video/video-to-audio",
                                      {"video_url": "http://fal.test/in", "sound_effect_prompt": "pas sur gravier"})],
      f"{st} {js} {SEAMS['sub']}")
check("kling rend son ET vidéo : un son (celui du modèle, pas d'extraction) et un job",
      st == 200 and len(js["items"]) == 1 and js["items"][0]["filename"].endswith(".wav") and len(js["videos"]) == 1,
      f"{js}")
check("kling : 0,035 $ la vidéo", st == 200 and abs(js.get("usd", 0) - 0.035) < 1e-9, js.get("usd") if isinstance(js, dict) else js)
R._plafond = _plaf_402
raz()
OPS.clear()
st, js = call("POST", "/audio/sfx-video", {"modele": "sonilo-video", "clip_id": _cid})
check("la garde reçoit l'op sfx_video (durée de la source) et arrête AVANT tout envoi",
      st == 402 and OPS and OPS[-1]["kind"] == "sfx_video" and OPS[-1]["modele"] == "sonilo-video"
      and abs(OPS[-1]["secondes"] - 2.0) < 0.1 and SEAMS["up"] == [] and SEAMS["sub"] == [], f"{st} {OPS} {SEAMS}")
R._plafond = _PLAF
check("aucun appel réseau réel (gardes fal_client)", RESEAU["n"] == 0, RESEAU["noms"])

# ════════════════════════════════════════════════════════════════════════════
print("\n[4] musique")
for mid in ("lyria-3.5", "elevenlabs-music-2.5", "minimax-music-3", "stable-audio-3", "mureka-9.5"):
    check(f"{mid} au registre", mid in MS.MUSIC_MODELS)
check("défaut toujours lyria3", MS.DEFAULT_MUSIC_MODEL == "lyria3" and MS.catalog()["default"] == "lyria3")
mu = {e["id"]: e for e in CI.lister("musique")}
check("catalogue musique : lyria-3.5, elevenlabs-music-2.5 ; lyria3 = défaut",
      "lyria-3.5" in mu and "elevenlabs-music-2.5" in mu and mu["lyria3"]["defaut"] is True, list(mu))
check("catalogue musique : « à mesurer » pour lyria-3.5, minimax-music-3, stable-audio-3",
      all(mu[k]["note"] == CI.NOTE_A_MESURER for k in ("lyria-3.5", "minimax-music-3", "stable-audio-3")), "")
check("catalogue musique : ElevenLabs 0,60 $/min ; Mureka 0,75 $ (0,225 $ avec paroles)",
      mu["elevenlabs-music-2.5"]["usd"] == 0.60 and mu["elevenlabs-music-2.5"]["unite"] == "min"
      and mu["mureka-9.5"]["usd"] == 0.75 and mu["mureka-9.5"]["usd_paroles"] == 0.225, "")
check("cassetteai : endpoint en minuscules (catalogue fal), durée 10-180 (schéma)",
      MS.MUSIC_MODELS["cassetteai"]["endpoint"] == "cassetteai/music-generator"
      and MS.MUSIC_MODELS["cassetteai"]["duration"] == (10, 180))
args, _ = MS._payload(MS.MUSIC_MODELS["elevenlabs-music-2.5"], "lofi", {"duration_s": 61, "instrumental": True})
check("ElevenLabs Music : prompt, music_length_ms (ms), force_instrumental, mp3_44100_128 — rien d'autre",
      args == {"prompt": "lofi", "music_length_ms": 61000, "force_instrumental": True,
               "output_format": "mp3_44100_128"}, args)
args, _ = MS._payload(MS.MUSIC_MODELS["stable-audio-3"], "drone", {"duration_s": 200, "seed": 4})
check("Stable Audio 3 : `duration` (pas seconds_total), graine", args == {"prompt": "drone", "duration": 200,
                                                                        "seed": 4}, args)
args, notes = MS._payload(MS.MUSIC_MODELS["lyria-3.5"], "épique", {"duration_s": 90, "negative_prompt": "voix"})
check("Lyria 3.5 : prompt + negative_prompt ; la durée ignorée est DITE",
      args == {"prompt": "épique", "negative_prompt": "voix"} and notes, (args, notes))
L = "[Verse]\nSous la mer profonde\n[Refrain]\nDeepotus"
args, _ = MS._payload(MS.MUSIC_MODELS["mureka-9.5"], "pop", {"lyrics": L})
check("Mureka avec paroles : prompt, lyrics (balises minimax), model mureka-9.5",
      args == {"model": "mureka-9.5", "prompt": "pop", "lyrics": MS.normalize_lyrics(L, "minimax")}, args)
args, _ = MS._payload(MS.MUSIC_MODELS["mureka-9.5"], "pop", {"lyrics": "[Verse]\n"})
check("Mureka sans paroles chantées : model + prompt seulement", args == {"model": "mureka-9.5", "prompt": "pop"}, args)
args, _ = MS._payload(MS.MUSIC_MODELS["minimax-music-3"], "hymne", {"lyrics": L, "duration_s": 90})
check("MiniMax Music 3 : prompt, lyrics, duration", args == {"prompt": "hymne", "lyrics": MS.normalize_lyrics(L, "minimax"),
                                                             "duration": 90}, args)
try:
    MS._payload(MS.MUSIC_MODELS["minimax-music-3"], "hymne", {"lyrics": "[Verse]\nla"})
    check("MiniMax Music 3 sans paroles -> 400", False)
except MS.MusicError as e:
    check("MiniMax Music 3 sans paroles -> MusicError 400", e.status == 400 and "paroles" in e.message, e.message)
for sec, usd in ((61, 1.20), (60, 0.60), (3, 0.60), (600, 6.0), (None, 0.60)):
    e = P.estimate({"kind": "music", "model": "elevenlabs-music-2.5", "duration_s": sec})
    check(f"ElevenLabs Music {sec} s = {usd} $ (minute entamée)", abs(e["total_usd"] - usd) < 1e-9, e)
check("Mureka : 0,225 $ avec paroles, 0,75 $ sur description seule",
      abs(P.estimate({"kind": "music", "model": "mureka-9.5", "paroles": True})["total_usd"] - 0.225) < 1e-9
      and abs(P.estimate({"kind": "music", "model": "mureka-9.5"})["total_usd"] - 0.75) < 1e-9)
check("Lyria 3.5 : 0 et « prix à mesurer »",
      "prix à mesurer" in P.estimate({"kind": "music", "model": "lyria-3.5"})["breakdown"][0]["label"])
d0 = n_depenses()
st, js = call("POST", "/audio/music", {"model": "minimax-music-3", "prompt": "hymne", "lyrics": "court"})
check("/audio/music MiniMax 3 sans paroles -> 400 AVANT la garde, zéro ligne depenses",
      st == 400 and n_depenses() == d0, f"{st} {js}")
st, js = call("POST", "/audio/music", {"model": "zzz", "prompt": "x"})
check("/audio/music modèle inconnu -> 400", st == 400, f"{st} {js}")
settings.FAL_KEY = ""
st, js = call("POST", "/audio/music", {"model": "lyria-3.5", "prompt": "x"})
check("/audio/music sans FAL_KEY -> 503 qui nomme FAL_KEY, zéro ligne", st == 503 and "FAL_KEY" in detail(js)
      and n_depenses() == d0, f"{st} {js}")
settings.FAL_KEY = "test-key"
R._plafond = _plaf_402
OPS.clear()
st, js = call("POST", "/audio/music", {"model": "mureka-9.5", "prompt": "pop", "lyrics": L})
check("/audio/music Mureka : la garde reçoit `paroles` True", st == 402 and OPS[-1] == {
    "kind": "music", "model": "mureka-9.5", "duration_s": None, "paroles": True}, OPS[-1:])
st, js = call("POST", "/audio/music", {"model": "mureka-9.5", "prompt": "pop"})
check("/audio/music Mureka sans paroles : `paroles` False (0,75 $)", st == 402 and OPS[-1].get("paroles") is False,
      OPS[-1:])
st, js = call("POST", "/audio/music", {"model": "ace-step", "prompt": "lofi", "duration_s": 200})
check("/audio/music ACE-Step : l'op d'avant inchangé (pas de clé `paroles`)",
      st == 402 and OPS[-1] == {"kind": "music", "model": "ace-step", "duration_s": 200}, OPS[-1:])
R._plafond = _PLAF

# ════════════════════════════════════════════════════════════════════════════
print("\n[5] écrans")
_RAC = _ICI.parent.parent
_FR = _RAC / "frontend"
_BUN = (_FR / "dist/assets/index-BEOJX8L5.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_SFXS = (_FR / "patches/sfxstudio.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_SONV = (_FR / "patches/son-vfx-montage.js").read_bytes().decode("utf-8").replace("\r\n", "\n")


def _bloc(tag):
    b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    return _BUN.split(b, 1)[1].split(e, 1)[0].strip("\n") if _BUN.count(b) == 1 else ""


check("le bloc SFXSTUDIO du bundle EST la source (rafraîchi)", _bloc("SFXSTUDIO") == _SFXS.lstrip("﻿").strip("\n"))
check("le bloc SONVFX du bundle EST la source (rafraîchi)", _bloc("SONVFX") == _SONV.lstrip("﻿").strip("\n"))
_carte = _SONV[_SONV.find("var sfxCard=svmSfx()?"):_SONV.find("/* presets de post-traitement")]
check("Son & VFX : la carte SFX pose le sélecteur sfx_texte de la couche (Choix) avec sa durée et ses 2 variations",
      re.search(r'r\.jsx\(svmSfx\(\)\.Choix\|\|"span",\s*\{dur:sfxDur,n:2\}\)', _carte), _carte[:300])
check("Son & VFX : plus aucun prix écrit en dur dans la carte SFX générée (« $0.03 » parti)",
      "$0.03" not in _carte.split("r.jsxs(\"div\",{className:\"svm-card\",children:[\n      r.jsx(SvmLabel,{children:dzT(\"son.sfx.pack_titre\")")[0])
check("Montage : le tiroir Sons reçoit le clip SÉLECTIONNÉ (clip:sel)",
      "onInsert:sfxInsert,playheadSec:ph,clip:sel,defaultTab:\"sfx\"}" in _SONV)
check("tiroir : POST /api/audio/sfx porte le modèle choisi (svxSfxCorps dans svxGenSfx)",
      "body.variations=Math.round(svxClamp(o.variations!=null?o.variations:1,1,4));svxSfxCorps(body,o);" in _SFXS)
check("tiroir : l'onglet Générer pose la rangée Modèle + « Depuis la vidéo » (svxSfxR), le prix d'avant en crédits "
      "ne parle plus que pour ElevenLabs direct (svxSfxCout)",
      "svxSfxR(gAuto?0:gDur,gVar,props.clip,gPrompt,refresh,fireNote)," in _SFXS
      and "children:cost==null?svxSfxCout(gDur,gVar,1):svxSfxCout(gDur,gVar,0)" in _SFXS)
check("tiroir : la couche exporte Choix (la carte SFX de Son & VFX le monte)",
      "genSfx:svxGenSfx,fxPresets:svxFxPresets,Choix:SvxSfxChoix};" in _SFXS)
_Q0 = _SFXS.find("/* ── t187 (G5, génération IA enrichie) : le MODÈLE du bruitage")
_Q1 = _SFXS.find("/* ── export contrat")
_QUEUE = _SFXS[_Q0:_Q1] if 0 < _Q0 < _Q1 else ""
check("la queue t187 est APRÈS la dernière édition G1 de la couche (le bouton fermer du mètre)",
      _QUEUE and _SFXS.rfind('__dzGl("dz-action-fermer")') < _Q0, (_Q0, _Q1))
check("aucune option grisée pour une clé absente : pas de « disabled » dans la queue hors bouton occupé",
      _QUEUE.count("disabled:") == 1 and "disabled:!!SVX_SFXM.busy" in _QUEUE, _QUEUE.count("disabled:"))
check("aucun useState ajouté (compteurs figés) : la queue rafraîchit par useReducer",
      "x.useState(" not in _QUEUE and _QUEUE.count("x.useReducer(") == 2)
check("le prix vient du SERVEUR : /api/cost/estimate (texte) et /api/audio/sfx-video devis:true (vidéo), aucun tarif recopié",
      '"/api/cost/estimate",{kind:"sfx"' in _QUEUE and '"/api/audio/sfx-video",Object.assign({devis:!0},corps)' in _QUEUE
      and not re.search(r"0\.0018|0\.009|0\.035", _QUEUE))
_DICO = {}
for _f in ("son.json", "sfx.json", "commun.json"):
    _DICO.update(json.loads((_FR / "shared/i18n" / _f).read_text(encoding="utf-8")))
for _k in ("son.sfx.modele", "son.sfx.depuis_video", "son.sfx.garder_voix"):
    check(f"clé {_k} : fr et en au dictionnaire, utilisée par la couche",
          _k in _DICO and _DICO[_k].get("fr") and _DICO[_k].get("en") and f'dzT("{_k}")' in _QUEUE, _DICO.get(_k))
check("son.sfx.prix_aide (prix recopié « crédits ElevenLabs ») retirée", "son.sfx.prix_aide" not in _DICO)

_node = shutil.which("node")
# le rail Musique : le prix d'une carte (svmMusicPrice), exécuté sous node sur les entrées du catalogue servi
_i = _SONV.find("function svmMusicPrice(")
_fn = _SONV[_i:_SONV.find("\n\n", _i)] if _i > 0 else ""
_MCAT = {m["id"]: m for m in MS.catalog()["models"]}
if _node and _fn:
    _cas = [["lyria-3.5", 30, ""], ["elevenlabs-music-2.5", 61, ""], ["elevenlabs-music-2.5", 60, ""],
            ["mureka-9.5", 0, "[Verse]\nSous la mer"], ["mureka-9.5", 0, "[Verse]\n"], ["ace-step", 120, ""],
            ["lyria3", 30, ""], ["minimax-music-3", 60, "[Verse]\nla la la la la"]]
    _jsm = ("var DICO=" + json.dumps(_DICO, ensure_ascii=False) + ";function dzT(k){return (DICO[k]&&DICO[k].fr)||k}\n"
            + _fn + "\nvar CAT=" + json.dumps(_MCAT, ensure_ascii=False) + ",CAS=" + json.dumps(_cas, ensure_ascii=False)
            + ";process.stdout.write(JSON.stringify(CAS.map(function(c){return svmMusicPrice(CAT[c[0]],c[1],c[2])})))")
    (W / "prix_musique.js").write_text(_jsm, encoding="utf-8")
    _pm = subprocess.run([_node, str(W / "prix_musique.js")], capture_output=True, text=True, encoding="utf-8",
                         errors="replace")
    try:
        _px = json.loads(_pm.stdout)
    except Exception:  # noqa: BLE001
        _px = [_pm.stderr[-300:]]
    check("rail Musique : à 0 $ la carte dit « prix à mesurer » (Lyria 3.5, MiniMax Music 3), jamais « $0.00 »",
          _px[0] == "prix à mesurer" and _px[7] == "prix à mesurer", _px)
    check("rail Musique : ElevenLabs Music à la minute ENTAMÉE (61 s = ~$1.20, 60 s = ~$0.60)",
          _px[1] == "~$1.20 · 61 s" and _px[2] == "~$0.60 · 60 s", _px)
    check("rail Musique : Mureka ~$0.225 avec paroles chantées, ~$0.75 sur description (balises seules = sans paroles)",
          _px[3] == "~$0.225" and _px[4] == "~$0.75", _px)
    check("rail Musique : prix d'avant inchangés (ACE-Step 120 s ~$0.024, Lyria 3 ~$0.10)",
          _px[5] == "~$0.024 · 120 s" and _px[6] == "~$0.10", _px)
else:
    check("node présent, svmMusicPrice extraite", False, (_node, len(_fn)))
check("rail Musique : la carte du modèle CHOISI passe ses paroles au prix (Mureka)",
      'dur,model===v.id&&showLyr?lyrics:"")})]}),' in _SONV)
if not _node or not _QUEUE:
    check("node présent et queue extraite", False, (_node, len(_QUEUE)))
else:
    settings.ELEVENLABS_API_KEY = ""
    settings.FAL_KEY = "test-key"
    _CAT = {n: CI.lister(n) for n in ("sfx_texte", "sfx_video")}
    _EST = {}
    for _m in _CAT["sfx_texte"]:
        _op = {"kind": "sfx", "modele": _m["id"], "secondes": 4, "echantillons": 2}
        _EST[json.dumps(_op, separators=(",", ":"))] = P.estimate(_op)["total_usd"]
    _HARN = r"""
var DICO=__DICO__,CAT=__CAT__,EST=__EST__;
function dzT(k,v){var t=(DICO[k]&&DICO[k].fr)||k;for(var x in (v||{}))t=t.split("{"+x+"}").join(String(v[x]));return t}
var LS={},CALLS=[],NOTES=[],SUBS=[];
var localStorage={getItem:function(k){return k in LS?LS[k]:null},setItem:function(k,v){LS[k]=String(v)}};
var window={localStorage:localStorage};
function rep(st,js){return Promise.resolve({ok:st<400,status:st,json:function(){return Promise.resolve(js)}})}
function fetch(u,o){o=o||{};var b=o.body?JSON.parse(o.body):null;CALLS.push({u:u,m:o.method||"GET",b:b});
  if(u.indexOf("/api/ia/catalogue?nature=")===0)return rep(200,{modeles:CAT[u.split("=")[1]]||[]});
  if(u==="/api/cost/estimate"){var k=JSON.stringify({kind:b.kind,modele:b.modele,secondes:b.secondes,echantillons:b.echantillons});
    return rep(200,{total_usd:k in EST?EST[k]:-1})}
  if(u==="/api/audio/sfx-video"&&b.devis)return rep(200,{devis:true,usd:0.018,secondes:2,modele:b.modele});
  if(u==="/api/audio/sfx-video")return rep(200,{ok:true,items:[{filename:"sfx_pas_1.wav"}],videos:[],usd:0.018,modele:b.modele});
  return rep(404,{detail:"inconnu "+u})}
function el(t,p){return {t:t,p:p||{}}}
var r={jsx:el,jsxs:el,Fragment:"Fragment"};
function SvmLabel(p){return el("div",p)}
/* moteur de hooks PAR INSTANCE : useReducer (rafraîchissement) et useEffect ([] : une fois) */
var CUR=null;
var x={useReducer:function(f,i){var I=CUR,k=I.hi++;if(!(k in I.H))I.H[k]=i;
    return [I.H[k],function(){I.H[k]=f(I.H[k]);I.sale=true}]},
  useEffect:function(f,d){var I=CUR,k=I.hi++;if(!(k in I.H)){I.H[k]=1;I.eff.push(f)}}};
function monter(C,props){var I={H:{},hi:0,eff:[],C:C,props:props,sale:false};
  I.rendre=function(){CUR=I;I.hi=0;I.sale=false;var t=I.C(I.props);var e=I.eff;I.eff=[];e.forEach(function(f){f()});CUR=null;I.t=t;return t};
  I.rendre();return I}
async function tick(){for(var i=0;i<12;i++)await new Promise(function(res){setImmediate(res)})}
function kids(n){var c=n&&n.p&&n.p.children;if(c==null)return [];return (Array.isArray(c)?c:[c]).reduce(function(a,v){return a.concat(Array.isArray(v)?v:[v])},[])}
function tout(n,acc){acc=acc||[];if(!n||typeof n!=="object")return acc;acc.push(n);kids(n).forEach(function(k){tout(k,acc)});return acc}
function txt(n){if(n==null||n===false)return "";if(typeof n!=="object")return String(n);return kids(n).map(txt).join("")}
var OUT={};
(async function(){
__QUEUE__
  /* 1. le sélecteur texte : catalogue chargé, défaut sans clé ElevenLabs = le jumeau fal, prix du serveur */
  var I=monter(SvxSfxChoix,{dur:4,n:2});
  OUT.avant=txt(I.t);
  await tick();I.rendre();await tick();I.rendre();
  var sel=tout(I.t).filter(function(n){return n.t==="select"})[0];
  OUT.options=kids(sel).map(function(o){return o.p.value});
  OUT.textes=kids(sel).map(function(o){return txt(o)});
  OUT.disabled=tout(I.t).filter(function(n){return "disabled" in n.p}).length;
  OUT.valeur=sel.p.value;
  OUT.devis=CALLS.filter(function(c){return c.u==="/api/cost/estimate"}).map(function(c){return c.b});
  OUT.prix=txt(tout(I.t).filter(function(n){return /svx-sfxmprix/.test(n.p.className||"")})[0]);
  OUT.cout_fal=svxSfxCout(4,2,0);
  var b0={};svxSfxCorps(b0,{});OUT.corps_defaut=b0;
  sel.p.onChange({target:{value:"sonilo-1.1"}});
  await tick();I.rendre();await tick();I.rendre();
  OUT.ls=LS["dz_sfx_modele"];OUT.valeur2=tout(I.t).filter(function(n){return n.t==="select"})[0].p.value;
  OUT.prix2=txt(tout(I.t).filter(function(n){return /svx-sfxmprix/.test(n.p.className||"")})[0]);
  var b1={};svxSfxCorps(b1,{});OUT.corps_choisi=b1;
  var b2={};svxSfxCorps(b2,{modele:"mirelo-1.6"});OUT.corps_explicite=b2;
  svxSfxChoisir("sfx_texte","elevenlabs-direct");OUT.cout_direct=svxSfxCout(4,2,0);OUT.cout_auto=svxSfxCout(4,2,1);
  svxSfxChoisir("sfx_texte","sonilo-1.1");
  /* 2. la rangée : hors Montage rien ; sans clip vidéo l'indication ; clip vidéo : la section */
  OUT.r_biblio=tout(svxSfxR(3,1,void 0,"","","")).filter(function(n){return n.t===SvxSfxVideo}).length+"|"+
    tout(svxSfxR(3,1,void 0,"","","")).filter(function(n){return /svx-sfxvnone/.test(n.p.className||"")}).length;
  OUT.r_null=txt(tout(svxSfxR(3,1,null,"","","")).filter(function(n){return /svx-sfxvnone/.test(n.p.className||"")})[0]);
  OUT.r_audio=tout(svxSfxR(3,1,{id:"a",tr:"a1",src:{job_id:"j"}},"","","")).filter(function(n){return n.t===SvxSfxVideo}).length;
  var CLIP={id:"c1",label:"Plan 1",tr:"v1",src:{job_id:"job-1"}};
  OUT.r_video=tout(svxSfxR(3,1,CLIP,"","","")).filter(function(n){return n.t===SvxSfxVideo}).length;
  /* 3. « Depuis la vidéo » : devis de la route, garder la voix (Sonilo), 1er clic arme, 2e tire */
  CALLS.length=0;
  var note=function(m){NOTES.push(m)};
  var V=monter(SvxSfxVideo,{clip:CLIP,prompt:"pas dans la neige",refresh:function(){OUT.refresh=(OUT.refresh||0)+1},note:note});
  await tick();V.rendre();await tick();V.rendre();
  var vsel=tout(V.t).filter(function(n){return n.t==="select"})[0];
  OUT.v_options=kids(vsel).map(function(o){return o.p.value});
  OUT.v_valeur=vsel.p.value;
  OUT.v_voix=tout(V.t).filter(function(n){return n.p["data-dzsfxvoix"]}).length;
  OUT.v_devis=CALLS.filter(function(c){return c.u==="/api/audio/sfx-video"}).map(function(c){return c.b});
  var go=tout(V.t).filter(function(n){return n.p["data-dzsfxvgo"]})[0];
  OUT.v_bouton=txt(go);OUT.v_disabled=go.p.disabled;
  tout(V.t).filter(function(n){return n.p["data-dzsfxvoix"]})[0].p.onChange({target:{checked:true}});
  await tick();V.rendre();await tick();V.rendre();
  OUT.v_devis2=CALLS.filter(function(c){return c.u==="/api/audio/sfx-video"}).map(function(c){return c.b}).slice(-1)[0];
  CALLS.length=0;
  tout(V.t).filter(function(n){return n.p["data-dzsfxvgo"]})[0].p.onClick();V.rendre();await tick();V.rendre();
  OUT.v_arme=CALLS.filter(function(c){return c.u==="/api/audio/sfx-video"&&!c.b.devis}).length;
  OUT.v_arme_txt=txt(tout(V.t).filter(function(n){return n.p["data-dzsfxvgo"]})[0]);
  tout(V.t).filter(function(n){return n.p["data-dzsfxvgo"]})[0].p.onClick();await tick();V.rendre();
  OUT.v_tir=CALLS.filter(function(c){return c.u==="/api/audio/sfx-video"&&!c.b.devis}).map(function(c){return c.b});
  OUT.v_notes=NOTES.slice();
  /* 4. Hunyuan sans description : refus AVANT tout tir */
  svxSfxChoisir("sfx_video","hunyuan-foley");CALLS.length=0;NOTES.length=0;
  var H=monter(SvxSfxVideo,{clip:CLIP,prompt:"  ",refresh:null,note:note});
  await tick();H.rendre();
  tout(H.t).filter(function(n){return n.p["data-dzsfxvgo"]})[0].p.onClick();
  tout(H.t).filter(function(n){return n.p["data-dzsfxvgo"]})[0].p.onClick();
  await tick();
  OUT.h_tir=CALLS.filter(function(c){return c.u==="/api/audio/sfx-video"&&!c.b.devis}).length;
  OUT.h_note=NOTES.slice();
  OUT.h_voix=tout(H.t).filter(function(n){return n.p["data-dzsfxvoix"]}).length;
  process.stdout.write(JSON.stringify(OUT));
})().catch(function(e){process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""
    _js = (_HARN.replace("__DICO__", json.dumps(_DICO, ensure_ascii=False))
           .replace("__CAT__", json.dumps(_CAT, ensure_ascii=False))
           .replace("__EST__", json.dumps(_EST)).replace("__QUEUE__", _QUEUE))
    _fjs = W / "ecran_sfx.js"
    _fjs.write_text(_js, encoding="utf-8")
    _p = subprocess.run([_node, str(_fjs)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=120)
    try:
        O = json.loads(_p.stdout)
    except Exception:  # noqa: BLE001
        O = {"erreur": (_p.stdout + _p.stderr)[-1500:]}
    check("la queue s'exécute sous node", "erreur" not in O, O.get("erreur"))
    if "erreur" not in O:
        check("avant le catalogue : « prix… », jamais un chiffre inventé", "prix…" in O["avant"], O["avant"])
        check("le sélecteur liste les 5 modèles sfx_texte dans l'ordre du registre",
              O["options"] == ["elevenlabs-direct", "elevenlabs-v2-fal", "sonilo-1.1", "mirelo-1.6",
                               "stable-audio-3-sfx"], O["options"])
        check("sans clé ElevenLabs : le direct reste CHOISISSABLE, « clé ELEVENLABS_API_KEY à ajouter dans Réglages », "
              "aucun élément disabled",
              "clé ELEVENLABS_API_KEY à ajouter dans Réglages" in O["textes"][0] and O["disabled"] == 0, O["textes"][0])
        check("chaque option dit son prix : Sonilo « $0.0018/s », ElevenLabs via fal « prix à mesurer »",
              "$0.0018/s" in O["textes"][2] and "prix à mesurer" in O["textes"][1], O["textes"])
        check("sans clé ElevenLabs, le défaut affiché = elevenlabs-v2-fal (le défaut du serveur)",
              O["valeur"] == "elevenlabs-v2-fal", O["valeur"])
        check("aucun choix mémorisé : le corps n'impose rien (le serveur choisit, « via fal »)",
              O["corps_defaut"] == {}, O["corps_defaut"])
        check("le devis demandé au serveur = kind sfx, modèle effectif, durée, 2 variations",
              {"kind": "sfx", "modele": "elevenlabs-v2-fal", "secondes": 4, "echantillons": 2} in O["devis"], O["devis"])
        check("ElevenLabs via fal : le prix affiché dit « prix à mesurer » ; l'estimation en crédits se tait",
              O["prix"] == "prix à mesurer" and O["cout_fal"] == "", (O["prix"], O["cout_fal"]))
        check("choisir Sonilo : mémorisé (dz_sfx_modele), sélecteur à jour, prix = le devis du serveur (~$0.014)",
              O["ls"] == "sonilo-1.1" and O["valeur2"] == "sonilo-1.1" and O["prix2"] == "~$0.014", (O["ls"], O["prix2"]))
        check("le corps de POST /api/audio/sfx porte le modèle choisi ; un modèle explicite de l'appelant prime",
              O["corps_choisi"] == {"modele": "sonilo-1.1"} and O["corps_explicite"] == {"modele": "mirelo-1.6"},
              (O["corps_choisi"], O["corps_explicite"]))
        check("ElevenLabs direct : l'estimation d'avant en crédits (≈ 320 crédits ; auto : ≈ 40 crédits/s)",
              O["cout_direct"] == "≈ 320 crédits" and O["cout_auto"].startswith("≈ 40 crédits/s"),
              (O["cout_direct"], O["cout_auto"]))
        check("rangée : hors Montage (clip absent) ni section ni indication ; sans clip : l'indication ; clip audio : "
              "pas de section ; clip vidéo : la section",
              O["r_biblio"] == "0|0" and "Sélectionnez un clip vidéo" in O["r_null"] and O["r_audio"] == 0
              and O["r_video"] == 1, (O["r_biblio"], O["r_null"], O["r_audio"], O["r_video"]))
        check("« Depuis la vidéo » : les 5 modèles sfx_video, Sonilo par défaut, « Garder la voix » proposé",
              O["v_options"] == ["sonilo-video", "mirelo-video", "kling-v2a", "hunyuan-foley", "thinksound"]
              and O["v_valeur"] == "sonilo-video" and O["v_voix"] == 1, (O["v_options"], O["v_voix"]))
        check("le devis vient de la route (devis:true, clip_id du clip, modèle, garder_voix)",
              {"devis": True, "clip_id": "job-1", "modele": "sonilo-video", "garder_voix": False} in O["v_devis"],
              O["v_devis"])
        check("le bouton annonce SON prix (devis du serveur) et n'est pas grisé",
              O["v_bouton"] == "Depuis la vidéo · ~$0.018" and not O["v_disabled"], (O["v_bouton"], O["v_disabled"]))
        check("cocher « Garder la voix » re-demande le devis avec garder_voix true",
              (O["v_devis2"] or {}).get("garder_voix") is True, O["v_devis2"])
        check("1er clic : ARME seulement (aucun tir), le bouton redit le même prix",
              O["v_arme"] == 0 and O["v_arme_txt"].startswith("~$0.018"), (O["v_arme"], O["v_arme_txt"]))
        check("2e clic : UN tir {prompt, clip_id, modele, garder_voix}, la liste est rafraîchie",
              O["v_tir"] == [{"prompt": "pas dans la neige", "clip_id": "job-1", "modele": "sonilo-video",
                              "garder_voix": True}] and O.get("refresh") == 1, (O["v_tir"], O.get("refresh")))
        check("après le tir : la note redit le MÊME prix (~$0.018)",
              O["v_notes"] and "sfx_pas_1.wav" in O["v_notes"][-1] and "~$0.018" in O["v_notes"][-1], O["v_notes"])
        check("Hunyuan sans description : refus nommé, AUCUN tir ; pas de « Garder la voix »",
              O["h_tir"] == 0 and O["h_note"] and "Décrivez" in O["h_note"][0] and O["h_voix"] == 0,
              (O["h_tir"], O["h_note"], O["h_voix"]))

print(f"\n=== {ok} passed, {fail} failed ===")
try:
    loop.close()
except Exception:  # noqa: BLE001
    pass
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
