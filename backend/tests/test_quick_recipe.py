# -*- coding: utf-8 -*-
"""Plan Quick T1 (tache #48 du suivi, 01/10/2026) — la recette Quick d'un rendu est ECRITE au demarrage du job
(AVANT tout appel payant) et RELUE par GET /jobs/{id}/recipe. Le banc lit le JSON sur le disque et la reponse HTTP.
Aucun reseau : l'upload fal et les appels HeyGen sont remplaces par des stubs qui LEVENT (le job echoue apres
l'ecriture — c'est ce qui prouve l'ordre). Data-dir isole (aucune cle reelle).
Temoin positif : la base (15c4c12) n'a pas de route /recipe.
Run (depuis backend/) : & $PY tests/test_quick_recipe.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqrec_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["HEYGEN_API_KEY"] = "test-heygen"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import fal_service, heygen_service, quick_recipe as QR  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


appels_payants = []
async def _stub(*_a, **_k):
    appels_payants.append(1)
    raise RuntimeError("stub: pas de reseau au banc")
fal_service.FalSeedanceClient.upload_image = staticmethod(_stub)
for nom in ("generate_video", "generate_video_v3", "create_video", "generate"):
    if hasattr(heygen_service.HeyGenClient, nom):
        setattr(heygen_service.HeyGenClient, nom, _stub)

RECETTE = {"v": 1, "tab": "seedance",
           "seedance": {"image": "a.png", "end": "", "prompt": "abysse", "vibe": "deep-sea", "model": "kling-v3-pro",
                        "duration": 10, "aspect": "9:16", "seed": "4421", "template": ""},
           "heygen": {"src": "avatar", "avatar": "", "voice": "", "script": "", "engine": "", "image": "", "motion": "", "expr": ""},
           "layout": "sequential"}
(settings.images_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nstub")
REC_DIR = settings.outputs_path / "_recipes"

r0 = subprocess.run(["git", "show", "15c4c12:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas de route /recipe", r0.returncode == 0 and b"/recipe" not in r0.stdout)
check("T2 temoin : les recettes vivent dans le data-dir isole", str(REC_DIR).startswith(str(_tmp)))


def _dernier_job(c):
    j = c.get("/api/jobs").json()
    items = j if isinstance(j, list) else (j.get("jobs") or j.get("items") or [])
    return items[0] if items else {}


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[A] Seedance")
    r = c.post("/api/generate", json={"image_filename": "a.png", "custom_prompt": "abysse", "video_model": "kling-v3-pro",
                                       "quick_recipe": RECETTE})
    job = _dernier_job(c)
    jid = job.get("job_id") or job.get("id")
    p = REC_DIR / f"{jid}.json"
    check("A1 200 ; le job a echoue sur le stub (appel payant tente APRES l'ecriture)", r.status_code == 200 and job.get("status") == "failed"
          and appels_payants, f"{r.status_code} {r.text[:200]} {job.get('status')}")
    check("A2 la recette est sur le disque, identique a l'envoi", p.is_file() and json.loads(p.read_text("utf-8")) == RECETTE, str(p))
    r2 = c.get(f"/api/jobs/{jid}/recipe")
    check("A3 GET /jobs/{id}/recipe la rend", r2.status_code == 200 and r2.json() == RECETTE, r2.text[:200])
    check("A4 job inconnu : 404", c.get("/api/jobs/nope/recipe").status_code == 404)
    # (un « ..%2F » dans l'URL tombe sur la page du catch-all, pas sur cette route : la garde se mesure sur le module)
    (settings.outputs_path / "hors.json").write_text(json.dumps({"v": 9}), encoding="utf-8")
    check("A5 un id qui remonte l'arborescence ne sort pas du dossier des recettes",
          QR.load("../hors") is None and QR.save("..", {"v": 1}) is False and QR.save("", {"v": 1}) is False)

    print("\n[B] HeyGen, sans recette")
    appels_payants.clear()
    rec = dict(RECETTE, tab="heygen")
    r = c.post("/api/generate/heygen", json={"avatar_id": "av1", "voice_id": "v1", "script": "salut", "quick_recipe": rec})
    job = _dernier_job(c)
    jid = job.get("job_id") or job.get("id")
    check("B1 HeyGen : la recette est relue, onglet heygen", r.status_code == 200 and c.get(f"/api/jobs/{jid}/recipe").json().get("tab") == "heygen",
          f"{r.status_code} {r.text[:200]}")
    r = c.post("/api/generate", json={"image_filename": "a.png", "custom_prompt": "x"})
    job2 = _dernier_job(c)
    j2 = job2.get("job_id") or job2.get("id")
    check("B2 sans recette : 404 et rien d'ecrit", r.status_code == 200 and c.get(f"/api/jobs/{j2}/recipe").status_code == 404
          and not (REC_DIR / f"{j2}.json").exists())

    print("\n[C] composition")
    avant = set(x.name for x in REC_DIR.glob("*.json"))
    rec = dict(RECETTE, tab="comp", layout="pip")
    r = c.post("/api/generate/composition", json={"seedance": {"image_filename": "a.png", "custom_prompt": "abysse"},
                                                  "heygen": {"avatar_id": "av1", "voice_id": "v1", "script": "salut"},
                                                  "quick_recipe": rec})
    neuves = [x for x in REC_DIR.glob("*.json") if x.name not in avant]
    check("C1 la recette de la composition est ecrite (AVANT les rendus, qui ont echoue)", r.status_code == 200 and len(neuves) == 1
          and json.loads(neuves[0].read_text("utf-8")) == rec, f"{r.status_code} {r.text[:200]} {[x.name for x in neuves]}")

print("\n[D] bornes")
check("D1 recette vide ou non-dict : rien d'ecrit", QR.save("j1", {}) is False and QR.save("j1", [1]) is False and not (REC_DIR / "j1.json").exists())
check("D2 recette enorme (> 64 Ko) : refusee", QR.save("j2", {"x": "a" * 70000}) is False and not (REC_DIR / "j2.json").exists())
(REC_DIR / "j3.json").write_text("{pas du json", encoding="utf-8")
(REC_DIR / "j4.json").write_text("[1,2]", encoding="utf-8")
check("D3 fichier illisible ou non-objet : None", QR.load("j3") is None and QR.load("j4") is None)

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
