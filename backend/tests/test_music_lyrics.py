# -*- coding: utf-8 -*-
"""T102 (plan-son-vfx T6, P4) — chanson chantée : registre étendu (ACE-Step, MiniMax Music 2.0), paroles
structurées normalisées par style de modèle, charge utile fal EXACTE (tags pour ACE-Step, lyrics_prompt pour
Music 2.0), squelette nourri par la persona, prix PAR SECONDE annoncé avant le tir — et la garde des plafonds
reçoit la durée (sinon un modèle à la seconde serait chiffré comme une génération).
Schémas relus le 06/10/2026 sur fal (openapi queue) : ace-step duration 5-240 s, tags requis ; minimax-music/v2
prompt 10-2000 (le plan disait 300), lyrics_prompt 10-3000 ; minimax-music/v3 : 404 (n'entre pas).
Run: python tests/test_music_lyrics.py (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzlyr_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["FAL_KEY"] = "test-key"
os.environ["ELEVENLABS_API_KEY"] = ""
os.environ["HEYGEN_API_KEY"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from loguru import logger
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
from app.services import music_service as MS, pricing as P

print("\n[1] registre")
ace, m20 = MS.MUSIC_MODELS.get("ace-step"), MS.MUSIC_MODELS.get("minimax-music-20")
check("ACE-Step : endpoint, paroles, durée 5-240, graine, prix à la seconde",
      ace is not None and ace["endpoint"] == "fal-ai/ace-step" and ace["lyrics"] and ace["seed"]
      and ace["duration"] == (5, 240) and ace["usd_unit"] == "s" and ace["usd"] == 0.0002, str(ace))
check("Music 2.0 : endpoint v2, paroles OBLIGATOIRES, prompt borné à 2000 (schéma relu)",
      m20 is not None and m20["endpoint"] == "fal-ai/minimax-music/v2" and m20["lyrics_required"]
      and m20["prompt_max"] == 2000 and m20["usd"] == 0.03 and m20["usd_unit"] == "gen", str(m20))
check("aucun « Music 3 » inventé (v3 : 404 le 06/10)",
      not any("v3" in v["endpoint"] or "music-03" in v["endpoint"] for v in MS.MUSIC_MODELS.values()))
check("les anciennes entrées gardent leur prix par génération",
      all(MS.MUSIC_MODELS[k].get("usd_unit", "gen") == "gen" for k in ("lyria3", "stable-audio-25",
                                                                         "minimax-music-26", "cassetteai")))

print("\n[2] paroles normalisées")
L = "[Verse]\nSous la mer\n\n[Refrain]\nDeepotus\n\n[Pont]\nremonte"
check("ace : balises minuscules, refrain -> [chorus], pont -> [bridge]",
      MS.normalize_lyrics(L, "ace") == "[verse]\nSous la mer\n\n[chorus]\nDeepotus\n\n[bridge]\nremonte",
      repr(MS.normalize_lyrics(L, "ace")))
check("ace instrumental = [inst]", MS.normalize_lyrics("", "ace", instrumental=True) == "[inst]")
check("minimax : balises capitalisées", MS.normalize_lyrics(L, "minimax")
      == "[Verse]\nSous la mer\n\n[Chorus]\nDeepotus\n\n[Bridge]\nremonte", repr(MS.normalize_lyrics(L, "minimax")))
check("tag inconnu laissé tel quel", MS.normalize_lyrics("[Solo]\nla", "ace") == "[Solo]\nla")

print("\n[3] charge utile exacte")
args, notes = MS._payload(ace, "dark ambient, 70 bpm", {"lyrics": L, "duration_s": 45, "seed": 7,
                                                        "instrumental": False})
check("ACE-Step envoie tags + lyrics + duration + seed, jamais prompt",
      args == {"tags": "dark ambient, 70 bpm", "lyrics": MS.normalize_lyrics(L, "ace"), "duration": 45, "seed": 7},
      str(args))
args, _ = MS._payload(ace, "lofi", {"lyrics": "", "instrumental": True})
check("ACE-Step instrumental : [inst], durée par défaut = milieu de la plage",
      args == {"tags": "lofi", "lyrics": "[inst]", "duration": 120}, str(args))
args, _ = MS._payload(m20, "hymne pirate", {"lyrics": L})
check("Music 2.0 envoie prompt + lyrics_prompt (minimax), rien d'autre",
      args == {"prompt": "hymne pirate", "lyrics_prompt": MS.normalize_lyrics(L, "minimax")}, str(args))
args, _ = MS._payload(m20, "p" * 2500, {"lyrics": L})
check("Music 2.0 : prompt tronqué à 2000", len(args["prompt"]) == 2000)
try:
    MS._payload(m20, "x" * 20, {"lyrics": "court"}); check("Music 2.0 paroles < 10 : refus", False)
except MS.MusicError as e:
    check("Music 2.0 sans paroles suffisantes : 400 explicite", e.status == 400 and "paroles" in e.message, e.message)
try:
    MS._payload(m20, "x" * 20, {"lyrics": "[Verse]\n[Chorus]\nla"}); check("Music 2.0 balises sans texte : refus", False)
except MS.MusicError as e:
    check("Music 2.0 : les BALISES ne comptent pas comme paroles (16 car. dont 2 chantés : refus)", e.status == 400, e.message)
args, _ = MS._payload(MS.MUSIC_MODELS["minimax-music-26"], "x", {"lyrics": "[verse]\nla", "instrumental": False})
check("2.6 inchangé : lyrics en convention minimax + is_instrumental False",
      args == {"prompt": "x", "lyrics": "[Verse]\nla", "is_instrumental": False}, str(args))

print("\n[4] squelette persona")
sk = MS.lyrics_skeleton("deepotus", theme="la remontée")
check("[Verse]/[Chorus]/[Bridge], nom de la persona, thème",
      "[Verse]" in sk and "[Chorus]" in sk and "[Bridge]" in sk and "Deepotus" in sk and "remontée" in sk, sk)
check("persona inconnue : squelette quand même (le nom brut)", "[Verse]" in MS.lyrics_skeleton("zz_inconnue"))

print("\n[5] catalogue et prix")
cat = MS.catalog()
row = [m for m in cat["models"] if m["id"] == "ace-step"][0]
check("catalogue expose usd_unit, lyrics_style, lyrics_required",
      row["usd_unit"] == "s" and row["lyrics_style"] == "ace" and row["lyrics_required"] is False
      and [m for m in cat["models"] if m["id"] == "minimax-music-20"][0]["lyrics_required"] is True)
e = P.estimate({"kind": "music", "model": "ace-step", "duration_s": 120})
check("estimation 120 s ACE-Step = 0,024 $", abs(e["total_usd"] - 0.024) < 1e-9, str(e))
e = P.estimate({"kind": "music", "model": "ace-step"})
check("sans durée : la durée par défaut de _payload (120 s) est chiffrée", abs(e["total_usd"] - 0.024) < 1e-9, str(e))
e = P.estimate({"kind": "music", "model": "minimax-music-20", "duration_s": 120})
check("Music 2.0 : 0,03 $ la génération, la durée n'y change rien", abs(e["total_usd"] - 0.03) < 1e-9, str(e))

print("\n[6] routes")
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api import routes as R
OPS = []
async def _plaf(op, cat, ref=None):
    OPS.append(op); raise HTTPException(402, "stop banc")
R._plafond = _plaf
async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        r = await c.get("/api/music/lyrics-skeleton", params={"theme": "abysses"})
        check("GET /music/lyrics-skeleton", r.status_code == 200 and "abysses" in r.json()["lyrics"], r.text[:200])
        r = await c.post("/api/audio/music", json={"model": "ace-step", "prompt": "lofi", "duration_s": 200})
        check("/audio/music : la garde reçoit la durée (ACE-Step à la seconde)",
              r.status_code == 402 and OPS[-1] == {"kind": "music", "model": "ace-step", "duration_s": 200}, str(OPS[-1:]))
asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
