# -*- coding: utf-8 -*-
"""Plan Quick T8 (tache #54 du suivi, D2, 01/10/2026) — six curseurs camera (-10..10) traduits en PHRASE, par famille de
modele. Aucun modele du registre n'expose de controle camera via fal (mesure R1 du 03/09) : les curseurs deviennent du
texte. La traduction est PURE et deterministe ; le banc lit la phrase rendue, le prompt final construit par
prompt_engine (prompt libre ET gabarit), la route d'apercu, et le prompt d'un job Seedance REEL (fal espionne).
Aucun reseau, data-dir isole (aucune cle reelle).
Temoin positif : la base (b4e61bd5) n'a ni camera_lang ni camera_ctrl.
Run (depuis backend/) : & $PY tests/test_quick_camera.py"""
import os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqcam_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "b4e61bd5"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/camera_lang.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/models/schemas.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni camera_lang ni camera_ctrl", r0.returncode != 0 and r1.returncode == 0 and b"camera_ctrl" not in r1.stdout)

from app.services import camera_lang as CL                          # noqa: E402
from app.services.fal_service import VIDEO_MODELS                   # noqa: E402

print("\n[C] la phrase")
check("C1 zero partout, vide, None, non-dict : rien n'est dit",
      CL.phrase({a: 0 for a in CL.AXES}, "veo_fal") == "" and CL.phrase({}, "kling") == "" and CL.phrase(None, "kling") == ""
      and CL.phrase("zoom", "kling") == "")
bad = []
for fam in CL.FAMILLES:
    for a in CL.AXES:
        p1, p2, p3, p4 = CL.phrase({a: 9}, fam), CL.phrase({a: -9}, fam), CL.phrase({a: 2}, fam), CL.phrase({a: 5}, fam)
        if not (p1 and p2 and p3 and p4 and p1 != p2 and len({p1, p3, p4}) == 3):
            bad.append((fam, a, p1, p2, p3, p4))
check("C2 chaque famille x chaque axe : deux sens distincts, trois intensites distinctes", not bad, str(bad[:2]))
p = CL.phrase({"zoom": 6, "pan": -8, "tilt": 3}, "kling")
check("C3 kling parle kling ; ordre = AXES, pas l'ordre des cles recues",
      p == "Camera: zoom in, strongly pan left, slightly tilt up." and CL.phrase({"tilt": 3, "pan": -8, "zoom": 6}, "kling") == p, p)
check("C4 le neutre parle anglais de plateau", CL.phrase({"zoom": 7, "tilt": -4}, "neutre") == "Camera: pushing in, tilting down.",
      CL.phrase({"zoom": 7, "tilt": -4}, "neutre"))
check("C5 bornes : >10 ramene a 10, texte numerique accepte, valeur illisible muette",
      CL.phrase({"roll": 99}, "neutre") == CL.phrase({"roll": 10}, "neutre") == "Camera: strongly rolling clockwise."
      and CL.phrase({"zoom": "4"}, "neutre") == "Camera: pushing in." and CL.phrase({"zoom": "abc", "pan": None}, "neutre") == ""
      and CL.phrase({"zoom": float("nan")}, "neutre") == "", CL.phrase({"roll": 99}, "neutre"))
check("C6 famille inconnue : le vocabulaire neutre", CL.phrase({"zoom": 5}, "famille-qui-n-existe-pas") == CL.phrase({"zoom": 5}, "neutre"))
fams = {m.get("family") for m in VIDEO_MODELS.values()}
check("C7 chaque famille du registre video a un lexique (aucune ne tombe au neutre par oubli)", fams <= set(CL.FAMILLES), str(fams - set(CL.FAMILLES)))
check("C8 famille_du_modele : kling-v3-pro -> kling, inconnu/vide -> neutre (jamais d'exception)",
      CL.famille_du_modele("kling-v3-pro") == "kling" and CL.famille_du_modele("nope") == "neutre" and CL.famille_du_modele(None) == "neutre")

print("\n[P] le prompt construit")
from app.models.schemas import GenerateRequest, CameraMove          # noqa: E402
from app.services.prompt_engine import PromptEngine                 # noqa: E402
pe = PromptEngine()
pos, _n = pe.build_prompt(GenerateRequest(image_filename="a.png", custom_prompt="un trone abyssal", video_model="kling-v3-pro",
                                          camera_ctrl={"zoom": 7, "tilt": -4}))
check("P1 prompt libre + curseurs (kling) : la phrase kling est ajoutee", pos == "un trone abyssal Camera: zoom in, tilt down.", pos)
pos, _n = pe.build_prompt(GenerateRequest(image_filename="a.png", custom_prompt="trone", camera=CameraMove.CRANE_DOWN,
                                          camera_ctrl={"pan": 3}))
check("P2 camera nommee ET curseurs : les deux, la nommee d'abord", pos == "trone Camera: crane shot descending. Camera: slightly panning right.", pos)
pos, _n = pe.build_prompt(GenerateRequest(image_filename="a.png", custom_prompt="trone", camera_ctrl={"zoom": 0}))
check("P3 curseurs a zero : prompt intact", pos == "trone", pos)
tid = pe.list_templates()[0].id
pos, _n = pe.build_prompt(GenerateRequest(image_filename="a.png", template_id=tid, camera_ctrl={"roll": -9}))
check("P4 branche gabarit : la phrase s'ajoute aussi", pos.endswith("Camera: strongly rolling counter-clockwise."), pos[-90:])

print("\n[R] la route d'apercu et un vrai job")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import fal_service                                # noqa: E402
prompts = []
async def _espion_upload(*_a, **_k):
    raise RuntimeError("stub: pas de reseau au banc")
fal_service.FalSeedanceClient.upload_image = staticmethod(_espion_upload)
from app.config import settings                                     # noqa: E402
(settings.images_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nstub")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    r = c.post("/api/quick/camera-phrase", json={"ctrl": {"zoom": 7, "tilt": -4}, "model": "kling-v3-pro"})
    j = r.json() if r.status_code == 200 else {}
    check("R1 apercu = MEME traduction que le rendu (famille du modele)", j.get("family") == "kling"
          and j.get("phrase") == "Camera: zoom in, tilt down." and j.get("axes") == list(CL.AXES), r.text[:200])
    j2 = c.post("/api/quick/camera-phrase", json={"ctrl": "x", "model": None}).json()
    check("R2 corps invalide : phrase vide, famille neutre (pas d'erreur)", j2.get("phrase") == "" and j2.get("family") == "neutre", str(j2))
    check("R3 sans corps : 200 phrase vide", c.post("/api/quick/camera-phrase").json().get("phrase") == "")
    rg = c.post("/api/generate", json={"image_filename": "a.png", "custom_prompt": "abysse", "video_model": "kling-v3-pro",
                                       "camera_ctrl": {"zoom": 7, "tilt": -4}})
    jobs = c.get("/api/jobs").json()
    items = jobs if isinstance(jobs, list) else (jobs.get("jobs") or jobs.get("items") or [])
    fp = (items[0] if items else {}).get("final_prompt") or ""
    check("R4 un vrai /generate : le prompt FINAL du job porte la phrase (le job echoue ensuite sur le stub fal)",
          rg.status_code == 200 and fp.startswith("abysse") and "Camera: zoom in, tilt down." in fp, f"{rg.status_code} {fp[:160]}")

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
