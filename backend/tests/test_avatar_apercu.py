# -*- coding: utf-8 -*-
"""Avatar live t168d (10/10/2026) — contrôler le détourage AVANT de payer la vidéo : UNE image du milieu de la prise
est détourée par BiRefNet image (fal-ai/birefnet/v2, le modèle choisi : Portrait, Matting, Général) puis posée en
local sur le fond choisi ; le décor vidéo reçoit ensuite le MÊME modèle. Sur de VRAIS fichiers ; le faux BiRefNet
rend un PNG où seul un carré rouge est opaque ; l'aperçu est jugé AU PIXEL. Aucun réseau.
Run (depuis backend/) : & $PY tests/test_avatar_apercu.py"""
import os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzapercu_"))
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
from PIL import Image                                               # noqa: E402
SUJET = _tmp / "sujet.png"   # ce que rend BiRefNet image : sujet opaque (carré rouge), le reste transparent
_s = Image.new("RGBA", (1024, 576), (0, 0, 0, 0)); _s.paste((255, 0, 0, 255), (352, 128, 672, 448)); _s.save(SUJET)
Image.new("RGB", (800, 600), (20, 40, 200)).save(_tmp / "images" / "ciel.png")
MATTE = _tmp / "matte.mov"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black@0.0:s=640x360:d=4:r=24,format=rgba",
                "-f", "lavfi", "-i", "color=c=red:s=200x200:d=4:r=24,format=rgba",
                "-filter_complex", "[0][1]overlay=220:80:format=auto,format=yuva444p10le",
                "-c:v", "prores_ks", "-profile:v", "4444", str(MATTE)], check=True, timeout=120)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import decor_service as DS, pricing, plafonds     # noqa: E402

APPELS, ENVOIS = [], []


async def f_up(path):
    ENVOIS.append(pathlib.Path(path).name)
    return "https://fal.test/" + pathlib.Path(path).name


async def f_sub(endpoint, arguments):
    APPELS.append((endpoint, dict(arguments)))
    if endpoint == DS.ENDPOINT_IMAGE:
        return {"image": {"url": "https://fal.test/sujet.png"}}
    return {"video": {"url": "https://fal.test/matte.mov"}}


async def f_dl(url, dest):
    shutil.copy2(SUJET if url.endswith(".png") else MATTE, dest)

DS._upload, DS._fal_subscribe, DS._download = f_up, f_sub, f_dl


def proche(c, ref, tol=40):
    return all(abs(a - b) <= tol for a, b in zip(c, ref))


print("\n[P] le prix")
e = pricing.estimate({"kind": "matte_image", "images": 1})
check("P1 une image BiRefNet : ligne fal « à mesurer » (fal n'affiche que $0), jamais une erreur",
      e["breakdown"] and e["breakdown"][0]["provider"] == "fal" and "à mesurer" in e["breakdown"][0]["label"], str(e))
check("P2 modèle : portrait par défaut, matting et general reconnus, le reste ramené au défaut",
      [DS.modele(m) for m in (None, "matting", "GENERAL", "pirate")] == ["portrait", "matting", "general", "portrait"])

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    with open(SRC, "rb") as fh:
        dep = loc.post("/api/avatar-live/recast/source", files={"fichier": ("prise.mp4", fh, "video/mp4")}).json()["depot"]

    print("\n[A] l'aperçu")
    r = loc.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"}, "modele": "matting"})
    d = r.json() if r.status_code == 200 else {}
    check("A1 200 : l'image source et l'aperçu servis, le modèle, l'instant (milieu de la prise : 2 s)",
          r.status_code == 200 and d.get("modele") == "matting" and abs(d.get("instant_s", 0) - 2) < 0.1
          and d.get("apercu", "").startswith("/api/avatar-live/decor/apercu/"), r.text[:300])
    a = APPELS[-1] if APPELS else ("", {})
    check("A2 fal reçoit UNE image (png) sur BiRefNet IMAGE, avec le modèle choisi (Matting)",
          a[0] == "fal-ai/birefnet/v2" and a[1].get("model") == "Matting" and a[1].get("refine_foreground") is True
          and ENVOIS and ENVOIS[-1].endswith(".png"), str(a))
    ap = loc.get(d.get("apercu", "/x"))
    im = Image.open(__import__("io").BytesIO(ap.content)).convert("RGB") if ap.status_code == 200 else None
    check("A3 l'aperçu au PIXEL : fond vert aux coins, sujet rouge au centre, à la taille de la prise (640×360)",
          im is not None and im.size == (640, 360) and proche(im.getpixel((5, 5)), (0, 255, 0))
          and proche(im.getpixel((320, 180)), (255, 0, 0)), str(im and (im.size, im.getpixel((5, 5)), im.getpixel((320, 180)))))
    src_img = loc.get(d.get("source", "/x"))
    check("A4 l'image source est servie aussi (pour comparer)", src_img.status_code == 200 and src_img.headers.get("content-type") == "image/png")
    r = loc.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"image": "ciel.png"}})
    d2 = r.json() if r.status_code == 200 else {}
    im2 = Image.open(__import__("io").BytesIO(loc.get(d2.get("apercu", "/x")).content)).convert("RGB") if r.status_code == 200 else None
    check("A5 fond image de la Bibliothèque : bleu aux coins ; modèle par défaut Portrait",
          im2 is not None and proche(im2.getpixel((5, 5)), (20, 40, 200)) and APPELS[-1][1].get("model") == "Portrait", r.text[:200])

    print("\n[G] gardes")
    n = len(APPELS)
    check("G1 fond illisible : 400, rien envoyé",
          loc.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "vert"}}).status_code == 400
          and len(APPELS) == n)
    check("G2 source inconnue : 404, rien envoyé",
          loc.post("/api/avatar-live/decor/apercu", json={"source": {"depot": "f" * 24 + ".mp4"}, "fond": {"couleur": "#000000"}}).status_code == 404
          and len(APPELS) == n)
    from app.config import settings
    settings.FAL_KEY = ""
    r = loc.post("/api/avatar-live/decor/apercu", json={"source": {"depot": dep}, "fond": {"couleur": "#000000"}})
    check("G3 sans clé fal : 400 qui le dit, rien envoyé", r.status_code == 400 and "fal" in r.text.lower() and len(APPELS) == n, r.text[:200])
    settings.FAL_KEY = "test-key"
    # « ..%2F » n'atteint pas la route (le catch-all de l'application répond) : on vérifie qu'AUCUNE donnée ne fuit
    rr = loc.get("/api/avatar-live/decor/apercu/..%2F..%2Ft.db")
    check("G4 aperçu : chemin remonté sans fuite (jamais la base), nom inconnu -> 404",
          not rr.content.startswith(b"SQLite format") and rr.headers.get("content-type") != "image/png"
          and loc.get("/api/avatar-live/decor/apercu/" + "0" * 32 + ".png").status_code == 404
          and loc.get("/api/avatar-live/decor/apercu/t.db").status_code == 404)
    check("G5 depuis le Wi-Fi sans jeton : refusé", lan.post("/api/avatar-live/decor/apercu", json={}).status_code in (401, 403))

    print("\n[V] le décor vidéo reçoit le modèle de l'aperçu")
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"}, "modele": "matting"})
    jid = r.json().get("job_id", "") if r.status_code == 200 else ""
    fin = time.time() + 90
    j = {}
    while jid and time.time() < fin:
        j = loc.get(f"/api/jobs/{jid}").json()
        if j.get("status") in ("done", "failed"):
            break
        time.sleep(0.3)
    v = [x for x in APPELS if x[0] == "fal-ai/birefnet/v2/video"]
    check("V1 BiRefNet VIDÉO avec Matting (le modèle vu à l'aperçu), job rendu",
          r.status_code == 200 and r.json().get("modele") == "matting" and v and v[-1][1].get("model") == "Matting"
          and j.get("status") == "done", r.text[:200] + str(j.get("error")))
    r = loc.post("/api/avatar-live/decor", json={"source": {"depot": dep}, "fond": {"couleur": "#00ff00"}})
    check("V2 sans modèle : Portrait, comme avant t168d", r.status_code == 200 and r.json().get("modele") == "portrait")

print("\n[R] recensement")
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
k = ("avatar_live", "POST", "/decor/apercu")
check("R1 /decor/apercu atteint un puits ET appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
