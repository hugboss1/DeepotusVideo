# -*- coding: utf-8 -*-
"""Avatar live t168c (10/10/2026) — brouillon 480p puis rendu final, à graine égale. Wan (replace, move) et Lucy
prennent `seed` (openapi relevé le 10/10), pas Kling. Sur de VRAIS fichiers (ffmpeg), AUCUN appel fal (espions) :
la graine part à fal et reste dans la recette du job ; « Finaliser » relance la MÊME recette (source, Personnage,
consigne, voix, graine) à la résolution finale, sous la même garde des plafonds ; Kling refuse le brouillon en le
disant ; un job qui n'est pas un brouillon ne se finalise pas.
Run (depuis backend/) : & $PY tests/test_avatar_brouillon.py"""
import base64, io, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzbrouillon_"))
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


FFMPEG = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
SRC = _tmp / "prise.mp4"
subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=24:duration=5",
                "-pix_fmt", "yuv420p", str(SRC)], check=True, timeout=180)


def png(c=(200, 80, 40)):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (600, 600), c).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import recast_service as RS, plafonds             # noqa: E402

APPELS = []


async def f_upload(path):
    return f"https://fal.test/{pathlib.Path(path).name}"


async def f_subscribe(endpoint, arguments):
    APPELS.append((endpoint, dict(arguments)))
    return {"video": {"url": "https://fal.test/sortie.mp4"}}


async def f_download(url, dest):
    shutil.copy2(SRC, dest)

RS._upload, RS._fal_subscribe, RS._download = f_upload, f_subscribe, f_download

print("\n[A] graine et arguments fal")
check("A1 graine : entier 0..2^31-1 ; booléen, texte ou hors borne refusés",
      [RS.lire_graine(v) for v in (7, "42", 0, -1, 2 ** 31, True, "x", None)] == [7, 42, 0, None, None, None, None, None])
check("A2 Wan et Lucy reçoivent `seed` ; Kling n'en reçoit pas (pas de graine chez fal)",
      RS.arguments({"modele": "remplacer", "resolution": "480p", "consigne": "", "orientation": "video", "graine": 9}, "V", ["I"]).get("seed") == 9
      and RS.arguments({"modele": "objet", "resolution": "480p", "consigne": "x", "orientation": "video", "graine": 9}, "V", []).get("seed") == 9
      and "seed" not in RS.arguments({"modele": "mouvement", "resolution": "source", "consigne": "", "orientation": "video",
                                      "graine": 9}, "V", ["I"]))
check("A3 le catalogue dit quels modèles ont un brouillon : Wan et Lucy oui, Kling non",
      [bool(RS.MODELES[k].get("graine")) for k in ("remplacer", "animer", "objet", "mouvement", "mouvement_pro")]
      == [True, True, True, False, False])


def attendre(c, jid):
    fin, j = time.time() + 60, {}
    while time.time() < fin:
        j = c.get(f"/api/jobs/{jid}").json()
        if j.get("status") in ("done", "failed"):
            return j
        time.sleep(0.3)
    return j


with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    pid = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png()], "consentement": True}).json()["id"]
    with open(SRC, "rb") as fh:
        dep = loc.post("/api/avatar-live/recast/source", files={"fichier": ("prise.mp4", fh, "video/mp4")}).json()["depot"]

    print("\n[M] le catalogue servi")
    m = loc.get("/api/avatar-live/recast/modeles").json()["modeles"]
    check("M1 « brouillon » : 480p pour Wan et Lucy, rien pour Kling",
          m["remplacer"]["brouillon"] == "480p" and m["objet"]["brouillon"] == "480p" and m["mouvement"]["brouillon"] is None)

    print("\n[B] le brouillon")
    base = {"source": {"depot": dep}, "personnage_id": pid, "modele": "remplacer", "resolution": "720p", "prereglage": "plage"}
    r = loc.post("/api/avatar-live/recast", json=dict(base, brouillon=True))
    d = r.json() if r.status_code == 200 else {}
    jb = d.get("job_id", "")
    check("B1 brouillon lancé EN 480p (la résolution demandée est ignorée), devis 5 s × 0,04 $ = 0,20 $",
          r.status_code == 200 and d.get("resolution") == "480p" and d.get("brouillon") is True
          and abs(d.get("devis_usd", 0) - 0.2) < 1e-6, r.text[:300])
    g = d.get("graine")
    j = attendre(loc, jb)
    check("B2 la graine tirée part à fal avec 480p ; le titre dit « brouillon 480p »",
          isinstance(g, int) and APPELS and APPELS[-1][1].get("seed") == g and APPELS[-1][1].get("resolution") == "480p"
          and j.get("status") == "done" and "brouillon 480p" in (j.get("title") or ""), str(APPELS[-1:]) + str(j.get("title")))
    rec = RS.lire_recette(jb)
    check("B3 la recette garde source, Personnage, préréglage, graine, 480p, brouillon",
          rec and rec["source"] == {"depot": dep} and rec["personnage_id"] == pid and rec["prereglage"] == "plage"
          and rec["graine"] == g and rec["resolution"] == "480p" and rec["brouillon"] is True, str(rec))
    b = loc.get("/api/avatar-live/recast/brouillons").json()["brouillons"]
    check("B4 /recast/brouillons le propose : finale 720p à 0,08 $/s, 5 s", jb in b and b[jb]["resolution_finale"] == "720p"
          and abs(b[jb]["prix_usd_s"] - 0.08) < 1e-9 and abs(b[jb]["duree_s"] - 5) < 0.2, str(b.get(jb)))

    print("\n[F] finaliser")
    plafonds.enregistrer({"par_moteur": {"fal": 0.30}})
    n_av = len(APPELS)
    r = loc.post("/api/avatar-live/recast/finaliser", json={"job_id": jb})
    check("F1 la finale passe la MÊME garde : plafond fal 0,30 $ < 0,40 $ -> 402, rien envoyé",
          r.status_code == 402 and "dz_plafond" in r.text and len(APPELS) == n_av, r.text[:200])
    plafonds.enregistrer({"par_moteur": {}})
    r = loc.post("/api/avatar-live/recast/finaliser", json={"job_id": jb})
    d = r.json() if r.status_code == 200 else {}
    jf = d.get("job_id", "")
    j = attendre(loc, jf) if jf else {}
    check("F2 finale : 720p, MÊME graine, devis 0,40 $, nouveau job, titre sans « brouillon »",
          r.status_code == 200 and d.get("resolution") == "720p" and d.get("graine") == g and jf != jb
          and abs(d.get("devis_usd", 0) - 0.4) < 1e-6 and j.get("status") == "done"
          and "brouillon" not in (j.get("title") or ""), r.text[:300])
    a = APPELS[-1][1]
    check("F3 fal reçoit la même source, le même Personnage et la même graine, en 720p",
          a.get("seed") == g and a.get("resolution") == "720p" and APPELS[-1][0] == "fal-ai/wan/v2.2-14b/animate/replace", str(a))
    rf = RS.lire_recette(jf)
    check("F4 la recette de la finale n'est PAS un brouillon et dit de quel brouillon elle vient",
          rf and rf["brouillon"] is False and rf["brouillon_de"] == jb and rf["graine"] == g, str(rf))
    b = loc.get("/api/avatar-live/recast/brouillons").json()["brouillons"]
    check("F4b le brouillon sait qu'il a déjà une version finale (l'écran le dit avant de faire repayer)",
          b.get(jb, {}).get("finales") == [jf] and jf not in b, str(b.get(jb)))
    check("F5 la finale ne se finalise pas (404 qui le dit)",
          loc.post("/api/avatar-live/recast/finaliser", json={"job_id": jf}).status_code == 404)
    check("F6 job inconnu ou id forgé : 404, aucune lecture hors du dossier",
          loc.post("/api/avatar-live/recast/finaliser", json={"job_id": "../../t"}).status_code == 404
          and loc.post("/api/avatar-live/recast/finaliser", json={"job_id": "0" * 8 + "-0000-0000-0000-" + "0" * 12}).status_code == 404)
    r = loc.post("/api/avatar-live/recast/finaliser", json={"job_id": jb, "resolution": "480p"})
    check("F7 « finaliser » en 480p refusé (400) : ce serait un second brouillon", r.status_code == 400, r.text[:200])

    print("\n[K] Kling et le téléphone")
    n_av = len(APPELS)
    r = loc.post("/api/avatar-live/recast", json=dict(base, modele="mouvement", brouillon=True))
    check("K1 Kling : brouillon refusé (400) en disant pourquoi, rien envoyé",
          r.status_code == 400 and "graine" in r.text and len(APPELS) == n_av, r.text[:200])
    r = loc.post("/api/avatar-live/recast", json=dict(base, prereglage=None))
    check("K2 un Recast Wan normal reçoit AUSSI une graine (gardée : on pourra le refaire)",
          r.status_code == 200 and isinstance(r.json().get("graine"), int), r.text[:200])
    check("K3 finaliser depuis le Wi-Fi sans jeton : refusé (401/403)",
          lan.post("/api/avatar-live/recast/finaliser", json={"job_id": jb}).status_code in (401, 403))
    # t168c (téléphone) : le compagnon appairé finalise SON brouillon, sous la même garde
    import asyncio                                                   # noqa: E402
    from app.services import appairage                                # noqa: E402
    jeton, _ = asyncio.run(appairage.reclamer(appairage.creer_secret().secret, "Pixel"))
    H = {"Authorization": "Bearer " + jeton}
    r = lan.post("/api/avatar-live/recast", json=dict(base, brouillon=True), headers=H)
    jt = r.json().get("job_id", "") if r.status_code == 200 else ""
    attendre(loc, jt) if jt else None
    plafonds.enregistrer({"par_moteur": {"fal": 0.30}})
    r402 = lan.post("/api/avatar-live/recast/finaliser", json={"job_id": jt}, headers=H)
    plafonds.enregistrer({"par_moteur": {}})
    r = lan.post("/api/avatar-live/recast/finaliser", json={"job_id": jt}, headers=H)
    check("K4 téléphone appairé : brouillon puis finale (200), et le plafond le bloque pareil (402)",
          bool(jt) and r402.status_code == 402 and r.status_code == 200 and r.json().get("resolution") == "720p", r.text[:200])

print("\n[R] recensement des routes payantes")
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
k = ("avatar_live", "POST", "/recast/finaliser")
check("R1 /recast/finaliser atteint un puits ET appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
