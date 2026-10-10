# -*- coding: utf-8 -*-
"""Avatar live G5 (t166, 10/10/2026) — la voix en direct côté application : ouverture d'un Direct AVEC voix (cloud :
une seule garde pour l'image et la voix, deux références au registre ; local : gratuit), segments PCM imputés sur la
réserve de la session, refus au-delà, fin qui note le réel de chaque moteur, téléphone limité à SA session.
Aucun réseau : Decart, ElevenLabs et Voixbox sont remplacés par leurs seams.
Run (depuis backend/) : & $PY tests/test_avatar_voix_direct.py"""
import asyncio, base64, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzvoixdirect_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["DECART_API_KEY"] = "dct_test"
os.environ["ELEVENLABS_API_KEY"] = "el_test"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loguru import logger                                           # noqa: E402
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (600, 600), (200, 80, 40)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import avatar_live as AL, voix_direct as VD, plafonds, appairage   # noqa: E402

ELEVEN, LOCAL = [], []


async def f_jeton(url, entetes, corps):
    return 200, {"apiKey": "ek_court", "expiresAt": "x"}


async def f_eleven(voice_id, pcm):
    ELEVEN.append((voice_id, len(pcm)))
    return 200, b"\x01\x00" * (len(pcm) // 2 + 327)      # 2 % plus long, comme le VRAI (mesuré le 10/10)


async def f_voixbox(chemin, params=None, corps=None):
    LOCAL.append((chemin, dict(params or {}), len(corps or b"")))
    if corps is None:      # GET /health
        return 200, json.dumps({"ok": True, "moteur": "rvc", "modeles": [{"nom": "oli", "index": True}]}).encode(), {}
    return 200, b"\x02\x00" * (len(corps) // 2), {"X-Latence-Ms": "80"}

AL._poster, VD._poster_eleven, VD._poster_voixbox = f_jeton, f_eleven, f_voixbox
VD._nvidia_smi = lambda: "Fausse RTX, 8192"   # le banc ne dépend pas du GPU de la machine
VD._GPU.update(t=0.0, v=None)
SEG = b"\x00\x10" * 16000                                           # 1 s de PCM 16 kHz


def lignes():
    return [l for l in asyncio.run(plafonds.tableau())["lignes"] if l["categorie"] == "direct"]


with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    sans = loc.post("/api/avatar-live/personnages", json={"nom": "Muet", "images": [png()], "consentement": True}).json()["id"]
    pid = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()], "consentement": True,
                                                         "voix": {"fournisseur": "elevenlabs", "voice_id": "voli"}}).json()["id"]

    print("\n[O] ouvrir un direct avec voix")
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": sans, "duree_s": 60, "voix": {"moteur": "cloud"}})
    check("O1 cloud sans voix au Personnage : 400 qui dit de la cloner, aucune réserve", r.status_code == 400
          and "clonez" in r.text and not lignes(), r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60, "voix": {"moteur": "radio"}})
    check("O2 moteur inconnu : 400", r.status_code == 400, r.text[:200])
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 60, "voix": {"moteur": "cloud"}})
    s1 = r.json()
    lg = {l["moteur"]: l for l in lignes()}
    check("O3 cloud : ouverte, la voix du Personnage annoncée ; UNE garde a réservé decart (1,20 $) ET elevenlabs (60 s)",
          r.status_code == 200 and s1.get("voix") == {"moteur": "cloud", "voice_id": "voli"}
          and abs(lg.get("decart", {}).get("estime_usd", 0) - 1.2) < 1e-6 and lg.get("elevenlabs", {}).get("estime_usd", 0) > 0,
          r.text[:200] + str(lg))

    print("\n[S] segments")
    r = loc.post(f"/api/avatar-live/sessions/voix?session_id={s1['session_id']}", content=SEG)
    check("S1 un segment d'1 s : converti par ElevenLabs avec la voix du Personnage, RECALÉ à la longueur reçue (pas de dérive), latence en en-tête",
          r.status_code == 200 and r.content == b"\x01\x00" * 16000 and ELEVEN[-1] == ("voli", 32000)
          and r.headers.get("x-latence-ms") is not None, r.text[:200])
    check("S2 segment de longueur impaire : 400 ; vide : 400",
          loc.post(f"/api/avatar-live/sessions/voix?session_id={s1['session_id']}", content=b"\x00" * 3).status_code == 400
          and loc.post(f"/api/avatar-live/sessions/voix?session_id={s1['session_id']}", content=b"").status_code == 400)
    n0 = len(ELEVEN)
    r = loc.post(f"/api/avatar-live/sessions/voix?session_id={s1['session_id']}", content=SEG * 11)
    check("S2b segment de 11 s : 413, rien envoyé, rien imputé", r.status_code == 413 and len(ELEVEN) == n0, r.text[:200])
    check("S3 session inconnue : 404", loc.post("/api/avatar-live/sessions/voix?session_id=nope", content=SEG).status_code == 404)
    for _ in range(59):
        loc.post(f"/api/avatar-live/sessions/voix?session_id={s1['session_id']}", content=SEG)
    n = len(ELEVEN)
    r = loc.post(f"/api/avatar-live/sessions/voix?session_id={s1['session_id']}", content=SEG)
    check("S4 au-delà des 60 s réservées : 409 « réserve épuisée », ElevenLabs n'est PAS appelé",
          r.status_code == 409 and "puis" in r.text and len(ELEVEN) == n, r.text[:200])

    print("\n[F] la fin note le réel de chaque moteur")
    r = loc.post("/api/avatar-live/sessions/fin", json={"session_id": s1["session_id"], "secondes": 61})
    f = r.json()
    lg = {l["moteur"]: l for l in lignes()}
    check("F1 fin : 60 s de voix notées au réel sous leur propre référence (pas de double compte avec decart)",
          r.status_code == 200 and abs(f.get("voix_s", 0) - 60) < 1e-6 and lg["elevenlabs"]["reel_usd"] is not None
          and abs(lg["decart"]["reel_usd"] - 1.2) < 1e-6
          and abs(lg["elevenlabs"]["reel_usd"] - f["voix_usd"]) < 1e-6, str(f) + str(lg))

    print("\n[L] local (Voixbox) : gratuit")
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 30,
                                                    "voix": {"moteur": "local", "modele": "oli", "transpose": 40}})
    s2 = r.json()
    nb = len(lignes())
    check("L1 local : ouverte, transposition bornée à 12, aucune réserve de voix au registre",
          r.status_code == 200 and s2["voix"] == {"moteur": "local", "modele": "oli", "transpose": 12}
          and sum(1 for l in lignes() if l["moteur"] == "elevenlabs") == 1, r.text[:200])
    r = loc.post(f"/api/avatar-live/sessions/voix?session_id={s2['session_id']}", content=SEG)
    check("L2 segment local : Voixbox reçoit le modèle et la transposition", r.status_code == 200
          and LOCAL[-1] == ("/convertir", {"modele": "oli", "transpose": 12}, 32000), str(LOCAL[-1:]))
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "voix": {"moteur": "local", "modele": "../x"}})
    check("L3 nom de modèle piégé : 400", r.status_code == 400, r.text[:200])
    loc.post("/api/avatar-live/sessions/fin", json={"session_id": s2["session_id"], "secondes": 5})
    r = loc.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 30})
    s3 = r.json()
    r = loc.post(f"/api/avatar-live/sessions/voix?session_id={s3['session_id']}", content=SEG)
    check("L4 session ouverte SANS voix : un segment est refusé (409)", r.status_code == 409, r.text[:200])

    print("\n[M] le téléphone")
    jeton, _ = asyncio.run(appairage.reclamer(appairage.creer_secret().secret, "Pixel"))
    H = {"Authorization": "Bearer " + jeton}
    r = lan.post("/api/avatar-live/sessions", json={"personnage_id": pid, "duree_s": 30, "voix": {"moteur": "cloud"}}, headers=H)
    sm = r.json()
    r = lan.post(f"/api/avatar-live/sessions/voix?session_id={sm['session_id']}", content=SEG, headers=H)
    check("M1 le téléphone convertit sa voix sur SA session (écriture ouverte)", r.status_code == 200, r.text[:200])
    r = lan.post(f"/api/avatar-live/sessions/voix?session_id={s3['session_id']}", content=SEG, headers=H)
    check("M2 ...mais pas sur celle du PC (404)", r.status_code == 404, r.text[:200])
    e = loc.get("/api/avatar-live/voix-direct/etat").json()
    check("M3 l'état se lit : cloud disponible ; local = GPU + Voixbox + voix entraînées",
          e["cloud"]["disponible"] is True and e["local"]["modeles"] == [{"nom": "oli", "index": True}], str(e))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
