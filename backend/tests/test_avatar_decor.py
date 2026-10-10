# -*- coding: utf-8 -*-
"""Avatar live G3 (t164, 10/10/2026) — le décor différé : le sujet d'une vidéo est détouré par BiRefNet vidéo (fal,
le service du Montage : ProRes 4444 avec alpha) puis COMPOSÉ en local (ffmpeg, gratuit) sur un fond — couleur unie,
image de la Bibliothèque ou vidéo déposée (bouclée). Le son de la source est gardé.

Sur de VRAIS fichiers : le faux BiRefNet rend un vrai .mov ProRes 4444 où seul un carré rouge est opaque ; la
composition est jugée AU PIXEL (fond aux coins, sujet au centre). Aucun réseau.
Run (depuis backend/) : & $PY tests/test_avatar_decor.py"""
import io, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzdecor_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
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
SRC = _tmp / "prise.mp4"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=4", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=4", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", str(SRC)],
               check=True, timeout=120)
MATTE = _tmp / "matte.mov"   # ce que rend BiRefNet : sujet opaque (carré rouge), le reste transparent
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black@0.0:s=640x360:d=4:r=24,format=rgba",
                "-f", "lavfi", "-i", "color=c=red:s=200x200:d=4:r=24,format=rgba",
                "-filter_complex", "[0][1]overlay=220:80:format=auto,format=yuva444p10le",
                "-c:v", "prores_ks", "-profile:v", "4444", str(MATTE)], check=True, timeout=120)

from PIL import Image                                               # noqa: E402
Image.new("RGB", (800, 600), (20, 40, 200)).save(_tmp / "images" / "ciel.png")
FOND_VID = _tmp / "fond.mp4"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=yellow:s=320x180:d=1.5:r=24", "-pix_fmt", "yuv420p",
                str(FOND_VID)], check=True, timeout=60)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import decor_service as DS, recast_service as RS, pricing, plafonds   # noqa: E402

APPELS = []


async def f_up(path):
    return "https://fal.test/" + pathlib.Path(path).name


async def f_sub(endpoint, arguments):
    APPELS.append((endpoint, dict(arguments)))
    return {"video": {"url": "https://fal.test/matte.mov"}}


async def f_dl(url, dest):
    shutil.copy2(MATTE, dest)

DS._upload, DS._fal_subscribe, DS._download = f_up, f_sub, f_dl


def image_milieu(p):
    out = _tmp / f"{p.stem}_f.png"
    subprocess.run([FF, "-y", "-v", "error", "-ss", "1", "-i", str(p), "-frames:v", "1", str(out)], check=True, timeout=60)
    return Image.open(out).convert("RGB")


def proche(c, ref, tol=40):
    return all(abs(a - b) <= tol for a, b in zip(c, ref))


def attendre(loc, jid):
    fin = time.time() + 90
    j = {}
    while time.time() < fin:
        j = loc.get(f"/api/jobs/{jid}").json()
        if j.get("status") in ("done", "failed"):
            break
        time.sleep(0.3)
    return j


print("\n[F] le fond se lit")
check("F1 couleur #00ff00 acceptée, « vert » refusé", DS.fond_valide({"couleur": "#00ff00"}) and not DS.fond_valide({"couleur": "vert"}))
(_tmp / "images" / "notes.txt").write_text("pas une image", encoding="utf-8")   # une cible RÉELLE non-image
check("F2 image de la Bibliothèque : nom NU dans le dossier des images, sinon rien",
      DS.chemin_fond({"image": "ciel.png"}) is not None and DS.chemin_fond({"image": "../t.db"}) is None
      and DS.chemin_fond({"image": "absent.png"}) is None and DS.chemin_fond({"image": "notes.txt"}) is None
      and DS.chemin_fond({"image": "sous/ciel.png"}) is None)

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    with open(SRC, "rb") as fh:
        dep = loc.post("/api/avatar-live/recast/source", files={"fichier": ("prise.mp4", fh, "video/mp4")}).json()["depot"]
    with open(FOND_VID, "rb") as fh:
        dfond = loc.post("/api/avatar-live/recast/source", files={"fichier": ("fond.mp4", fh, "video/mp4")}).json()["depot"]

    print("\n[G] gardes")
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "vert"}})
    check("G1 fond illisible : 400, rien envoyé", r.status_code == 400 and not APPELS, r.text[:200])
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": "f" * 24 + ".mp4"}, "fond": {"couleur": "#00ff00"}})
    check("G2 source introuvable : 404", r.status_code == 404 and not APPELS, r.text[:200])
    check("G3 depuis le Wi-Fi : écriture refusée", lan.post("/api/avatar-live/decor", json={},
          headers={"Authorization": "Bearer " + "0" * 64}).status_code in (401, 403))

    print("\n[C] composer")
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"}})
    j = attendre(loc, r.json().get("job_id", ""))
    sortie = _tmp / "outputs" / "final" / f"{r.json().get('job_id', '')}.mp4"
    check("C1 couleur : job done, modèle « decor », BiRefNet appelé en ProRes 4444", j.get("status") == "done"
          and j.get("video_model") == "decor" and APPELS and APPELS[-1][0] == "fal-ai/birefnet/v2/video"
          and "PRORES4444" in APPELS[-1][1].get("video_output_type", ""), str(j)[:200] + str(APPELS[-1:]))
    im = image_milieu(sortie) if sortie.is_file() else Image.new("RGB", (2, 2))
    check("C2 au pixel : coin = le vert du fond, centre du carré = le rouge du sujet",
          proche(im.getpixel((10, 10)), (0, 255, 0)) and proche(im.getpixel((320, 180)), (255, 0, 0)),
          f"{im.getpixel((10, 10))} {im.getpixel((320, 180))}")
    check("C3 taille de la source gardée (640×360) et SON gardé", im.size == (640, 360) and RS.a_du_son(sortie), str(im.size))
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"image": "ciel.png"}})
    j = attendre(loc, r.json().get("job_id", ""))
    im = image_milieu(_tmp / "outputs" / "final" / f"{r.json().get('job_id', '')}.mp4")
    check("C4 image de la Bibliothèque (800×600 recadrée) : coin bleu, centre rouge, 640×360",
          j.get("status") == "done" and proche(im.getpixel((10, 10)), (20, 40, 200)) and proche(im.getpixel((320, 180)), (255, 0, 0))
          and im.size == (640, 360), f"{j.get('status')} {im.getpixel((10, 10))}")
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"video": dfond}})
    jid = r.json().get("job_id", "")
    j = attendre(loc, jid)
    from app.services.fal_video_tools import probe
    sortie = _tmp / "outputs" / "final" / f"{jid}.mp4"
    check("C5 vidéo de 1,5 s en fond d'une prise de 4 s : bouclée, la sortie dure la prise, coin jaune",
          j.get("status") == "done" and abs(probe(sortie)["duration_s"] - 4) < 0.3
          and proche(image_milieu(sortie).getpixel((10, 10)), (255, 255, 0)), str(j)[:200])

    print("\n[P] prix et garde")
    d = pricing.estimate({"kind": "matte", "duration_s": 4})
    check("P1 le devis est celui du détourage du Montage (taux « à mesurer » dit)", d["breakdown"][0]["provider"] == "fal")
    import _recensement_payant as RP                                 # noqa: E402
    rec = RP.recenser()
    k = ("avatar_live", "POST", "/decor")
    check("P2 /decor atteint un puits ET appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
