# -*- coding: utf-8 -*-
"""Veille YouTube (28/10/2026) : la collecte du 28/10 a rendu 25 limites « CalledProcessError : Command '[…yt-dlp.EXE'…' »
sans la cause. Désormais : la RAISON de yt-dlp (sa ligne ERROR) est dite, jamais la commande ; une vidéo en échec est
retentée une fois après une pause ; un blocage de YouTube (« Sign in to confirm you're not a bot », 429) suspend la
source pour la collecte avec UNE ligne claire ; stdin fermé (processus lancé sans console). Aucun réseau.
Run (depuis backend/) : & $PY tests/test_veille_youtube.py"""
import asyncio, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzyt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import veille_collecte as VC                       # noqa: E402

BOT = b"WARNING: x\nERROR: [youtube] abc: Sign in to confirm you\xe2\x80\x99re not a bot. Use --cookies-from-browser\n"
APPELS = []


def faux_run(args, **kw):
    APPELS.append(kw)
    raise subprocess.CalledProcessError(1, args, output=b"", stderr=BOT)


print("[1] la raison de yt-dlp, jamais la commande")
VC._ytdlp_commande = lambda: [r"C:\Users\x\yt-dlp.EXE"]
VC._RUN = faux_run
e = None
try:
    asyncio.run(VC._ytdlp_defaut("ySnpi1mxyEc", 10))
except Exception as x:  # noqa: BLE001
    e = x
check("1.1 une erreur YouTube nommée, avec la ligne ERROR de yt-dlp", isinstance(e, VC.EchecYoutube)
      and "Sign in to confirm" in str(e) and "yt-dlp.EXE" not in str(e) and "--write-comments" not in str(e), repr(e))
check("1.2 blocage reconnu", isinstance(e, VC.EchecYoutube) and e.bloque is True)
check("1.3 stdin fermé (processus sans console)", APPELS and APPELS[0].get("stdin") is subprocess.DEVNULL, APPELS[:1])


def faux_run_autre(args, **kw):
    raise subprocess.CalledProcessError(1, args, output=b"", stderr=b"ERROR: [youtube] xyz: Video unavailable\n")


VC._RUN = faux_run_autre
e = None
try:
    asyncio.run(VC._ytdlp_defaut("xyz", 10))
except Exception as x:  # noqa: BLE001
    e = x
check("1.4 vidéo indisponible : raison dite, pas un blocage", isinstance(e, VC.EchecYoutube) and "Video unavailable" in str(e)
      and e.bloque is False, repr(e))

print("[2] dans la collecte")
DORMI = []


async def dormir(s):
    DORMI.append(s)


VC._DORMIR = dormir
PERIM = VC.valider_perimetre({"concurrents": [{"id": f"c{i}", "youtube": ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"]}
                                              for i in range(3)]})
ESSAIS = []


async def ytdlp_bloque(video, maxi):
    ESSAIS.append(video)
    raise VC.EchecYoutube("Sign in to confirm you're not a bot", bloque=True)


VC._YTDLP = ytdlp_bloque
r = asyncio.run(VC.collecter(PERIM, _tmp / "brut1", VC._horloge() + 600, lambda l: None))
yt = [l for l in r["limites"] if l.startswith("youtube")]
check("2.1 blocage : UNE ligne claire, la source suspendue (pas 9 lignes)", len(yt) == 1 and "bloqu" in yt[0]
      and "Sign in to confirm" in yt[0], yt)
check("2.2 blocage : une seule nouvelle tentative, après une pause", len(ESSAIS) == 2 and DORMI and DORMI[0] > 0, (ESSAIS, DORMI))

ESSAIS.clear(); DORMI.clear()
ETAT = {"n": 0}


async def ytdlp_passager(video, maxi):
    ESSAIS.append(video)
    ETAT["n"] += 1
    if ETAT["n"] == 1:
        raise VC.EchecYoutube("HTTP Error 503", bloque=False)
    return {"title": "t", "comments": [{"id": "k", "text": "great tool", "author": "@someone", "timestamp": 1760000000}]}


VC._YTDLP = ytdlp_passager
r = asyncio.run(VC.collecter(PERIM, _tmp / "brut2", VC._horloge() + 600, lambda l: None))
check("2.3 panne passagère : retentée, la vidéo est collectée", r["ajoutes"].get("youtube", 0) >= 1
      and not [l for l in r["limites"] if l.startswith("youtube")], r)

ESSAIS.clear()


async def ytdlp_indispo(video, maxi):
    ESSAIS.append(video)
    raise VC.EchecYoutube("Video unavailable", bloque=False)


VC._YTDLP = ytdlp_indispo
r = asyncio.run(VC.collecter(PERIM, _tmp / "brut3", VC._horloge() + 600, lambda l: None))
yt = [l for l in r["limites"] if l.startswith("youtube")]
check("2.4 vidéo indisponible : une ligne par vidéo, avec la raison, sans la commande",
      len(yt) == 9 and all("Video unavailable" in l and "yt-dlp" not in l for l in yt), yt[:2])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
