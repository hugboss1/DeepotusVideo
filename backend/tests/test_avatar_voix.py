# -*- coding: utf-8 -*-
"""Avatar live G2 (t163, 10/10/2026) — la voix du Personnage : clonage instantané ElevenLabs (rattaché au
Personnage, consentement G0) et voix → voix sur une vidéo (piste extraite, convertie, recollée — le timing reste,
donc les lèvres). Aussi : le Recast « avec la voix du Personnage » chaîne la conversion après fal.

Sur de VRAIS fichiers (ffmpeg). AUCUN appel ElevenLabs ni fal : les seams rendent une voix « convertie » qui est un
autre son (sinus 880 Hz), reconnaissable par sa durée et son existence. La route payante passe la garde AVANT.
Run (depuis backend/) : & $PY tests/test_avatar_voix.py"""
import base64, io, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzvoix_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["ELEVENLABS_API_KEY"] = "test-eleven"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FF = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")


def mp4(nom, secs, son=True):
    p = _tmp / nom
    a = ["-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-shortest", "-c:a", "aac"] if son else []
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size=640x360:rate=24:duration={secs}", *a,
                    "-pix_fmt", "yuv420p", str(p)], check=True, timeout=180)
    return p


def mp3(secs, freq=880):
    p = _tmp / f"voix_{freq}_{secs}.mp3"
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={secs}",
                    "-c:a", "libmp3lame", str(p)], check=True, timeout=60)
    return p.read_bytes()


def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (600, 600), (200, 80, 40)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import avatar_voix as AV, recast_service as RS, pricing, plafonds, avatar_live as AL   # noqa: E402

CLONES, STS = [], []


async def f_clone(nom, fichiers, debruiter):
    CLONES.append((nom, [n for n, _ in fichiers], debruiter))
    return 200, {"voice_id": "vclone123", "requires_verification": False}


async def f_sts(voice_id, audio, debruiter):
    STS.append((voice_id, len(audio), debruiter))
    return 200, mp3(7)   # plus LONG que la prise : -shortest doit couper à la vidéo

AV._poster_clone, AV._poster_sts = f_clone, f_sts


def duree(p):
    from app.services.fal_video_tools import probe
    return probe(p)["duration_s"]


SRC = mp4("parle.mp4", 5)
MUET = mp4("muet.mp4", 5, son=False)

print("\n[P] prix")
d = pricing.estimate({"kind": "voix_sts", "duration_s": 60})
check("P1 une minute de voix → voix = 1 000 caractères ElevenLabs", d["breakdown"][0]["provider"] == "elevenlabs"
      and abs(d["breakdown"][0]["units"] - 1000) < 1e-6 and d["total_usd"] > 0, str(d))

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    pid = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()], "consentement": True}).json()["id"]

    print("\n[C] clonage")
    ech = mp3(30, 220)
    r = loc.post(f"/api/avatar-live/personnages/{pid}/voix", files=[("echantillons", ("a.mp3", ech, "audio/mpeg"))],
                 data={"debruiter": "true"})
    check("C1 cloné : voice_id rattaché au Personnage, marqué cloné et daté", r.status_code == 200
          and AL.lire_personnage(pid)["voix"].get("voice_id") == "vclone123"
          and AL.lire_personnage(pid)["voix"].get("clonee") is True, r.text[:200])
    check("C2 envoyé à ElevenLabs : nom du Personnage, l'échantillon, débruitage demandé",
          CLONES and CLONES[-1] == ("Deepotus · Oli", ["a.mp3"], True), str(CLONES))
    r = loc.post("/api/avatar-live/personnages/inconnu0000000/voix", files=[("echantillons", ("a.mp3", ech, "audio/mpeg"))])
    check("C3 Personnage inconnu : 404, rien envoyé", r.status_code == 404 and len(CLONES) == 1, r.text[:200])
    r = loc.post(f"/api/avatar-live/personnages/{pid}/voix", files=[("echantillons", (f"{i}.mp3", ech, "audio/mpeg")) for i in range(6)])
    check("C4 six échantillons : 400", r.status_code == 400 and len(CLONES) == 1, r.text[:200])
    check("C5 cloner depuis le Wi-Fi : écriture refusée", lan.post(f"/api/avatar-live/personnages/{pid}/voix",
          files=[("echantillons", ("a.mp3", ech, "audio/mpeg"))], headers={"Authorization": "Bearer " + "0" * 64}).status_code in (401, 403))
    from app.config import settings
    settings.ELEVENLABS_API_KEY = ""
    r = loc.post(f"/api/avatar-live/personnages/{pid}/voix", files=[("echantillons", ("a.mp3", ech, "audio/mpeg"))])
    check("C6 sans clé ElevenLabs : 409 qui le dit", r.status_code == 409 and "ElevenLabs" in r.text, r.text[:200])
    settings.ELEVENLABS_API_KEY = "test-eleven"

    print("\n[V] voix → voix")
    with open(SRC, "rb") as fh:
        dep = loc.post("/api/avatar-live/recast/source", files={"fichier": ("parle.mp4", fh, "video/mp4")}).json()["depot"]
    with open(MUET, "rb") as fh:
        dmuet = loc.post("/api/avatar-live/recast/source", files={"fichier": ("muet.mp4", fh, "video/mp4")}).json()["depot"]
    plafonds.enregistrer({"par_moteur": {"elevenlabs": 0.0001}})
    r = loc.post("/api/avatar-live/voix", json={"source": {"depot": dep}, "personnage_id": pid})
    check("V1 plafond ElevenLabs dépassé : 402 AVANT tout envoi", r.status_code == 402 and not STS, r.text[:200])
    plafonds.enregistrer({"par_moteur": {}})
    r = loc.post("/api/avatar-live/voix", json={"source": {"depot": dep}})
    check("V2 aucune voix (ni Personnage ni voice_id) : 400", r.status_code == 400 and "voix" in r.text.lower(), r.text[:200])
    r = loc.post("/api/avatar-live/voix", json={"source": {"depot": dep}, "personnage_id": pid})
    jid = r.json().get("job_id", "")
    fin = time.time() + 60
    while time.time() < fin and (j := loc.get(f"/api/jobs/{jid}").json()).get("status") not in ("done", "failed"):
        time.sleep(0.3)
    sortie = _tmp / "outputs" / "final" / f"{jid}.mp4"
    check("V3 job voix : done, provider recast / modèle voix, titre du Personnage", j.get("status") == "done"
          and j.get("provider") == "recast" and j.get("video_model") == "voix" and "Oli" in (j.get("title") or ""), str(j)[:300])
    check("V4 ElevenLabs a reçu la voix clonée du Personnage et un audio extrait", STS and STS[-1][0] == "vclone123"
          and STS[-1][1] > 1000, str(STS))
    check("V5 la sortie : vidéo de la source + son converti, même durée (le timing est gardé)",
          sortie.is_file() and RS.a_du_son(sortie) and abs(duree(sortie) - duree(SRC)) < 0.3, str(duree(sortie)) if sortie.is_file() else "absente")
    n = len(STS)
    r = loc.post("/api/avatar-live/voix", json={"source": {"depot": dmuet}, "voice_id": "autre"})
    jid2 = r.json().get("job_id", "")
    fin = time.time() + 60
    while time.time() < fin and (j := loc.get(f"/api/jobs/{jid2}").json()).get("status") not in ("done", "failed"):
        time.sleep(0.3)
    check("V6 vidéo muette : job failed qui le dit, rien envoyé à ElevenLabs", j.get("status") == "failed"
          and "piste son" in (j.get("error") or "") and len(STS) == n, str(j)[:200])

    print("\n[R] le Recast avec la voix du Personnage")
    async def f_up(path): return "https://fal.test/" + pathlib.Path(path).name
    async def f_sub(e, a): return {"video": {"url": "https://fal.test/o.mp4"}}
    async def f_dl(url, dest): shutil.copy2(MUET, dest)
    RS._upload, RS._fal_subscribe, RS._download = f_up, f_sub, f_dl
    r = loc.post("/api/avatar-live/recast", json={"source": {"depot": dep}, "personnage_id": pid, "modele": "remplacer",
                                                  "voix": True})
    devis = r.json().get("devis_usd", 0)
    jid3 = r.json().get("job_id", "")
    fin = time.time() + 60
    while time.time() < fin and (j := loc.get(f"/api/jobs/{jid3}").json()).get("status") not in ("done", "failed"):
        time.sleep(0.3)
    check("R1 le devis porte fal ET ElevenLabs (une seule garde)", r.status_code == 200
          and devis > pricing.estimate({"kind": "recast", "modele": "remplacer", "seconds": 5})["total_usd"], r.text[:200])
    check("R2 rendu fal muet → son de la source recollé → converti dans la voix du Personnage",
          j.get("status") == "done" and len(STS) == n + 1 and STS[-1][0] == "vclone123"
          and RS.a_du_son(_tmp / "outputs" / "final" / f"{jid3}.mp4"), str(j)[:200])
    r = loc.post("/api/avatar-live/recast", json={"source": {"depot": dep}, "modele": "objet", "consigne": "red jacket",
                                                  "voix": True})
    check("R3 voix demandée SANS Personnage ni voix : 400 avant tout envoi", r.status_code == 400, r.text[:200])

print("\n[S] recensement")
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
k = ("avatar_live", "POST", "/voix")
check("S1 /voix atteint un puits ET appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
