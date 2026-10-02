# -*- coding: utf-8 -*-
"""Plan chapitres T19 (tache #66 du suivi, PR C, 02/10/2026) — la sortie « episode » SANS rendu.
DECISION DE L'UTILISATEUR (02/10) : creer un Episode (vue Episodes) depuis le storyboard, sans narrer ni rendre : le
payant reste dans la vue Episodes, avec son devis et ses plafonds.
Ce que le plan faisait faux, et que ce banc garde : un rendu payant lance d'ici sans plafond ; les SCENES du scenario
appariees aux PLANS par leur rang ; une narration repayee. Ici : un plan = une scene (son texte, son image), Ken Burns
(jamais « seedance », payant), la voix du Narrateur, AUCUN appel, AUCUN job, AUCUNE depense.
Data-dir isole, cles videes. Temoin positif : la base (45f981bf) n'a pas la route.
Run (depuis backend/) : & $PY tests/test_chapitres_episode.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzepisode_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
os.environ["ELEVENLABS_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "45f981bf"
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas la route de sortie « episode »", r1.returncode == 0 and b'"/chapters/{chapter_id}/episode"' not in r1.stdout)

sys.modules["fal_client"] = types.ModuleType("fal_client")
from PIL import Image                                               # noqa: E402
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
from app.services import elevenlabs_service as ELS                  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
APPELS = []
ELS.VoiceoverService.generate_long = lambda self, *a, **k: APPELS.append("tts")


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def compte(table):
    try:
        return sqlite3.connect(str(_DB)).execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


print("[R] la route")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    check("R1 chapitre inconnu : 404", c.post("/api/chapters/inconnu/episode", json={}).status_code == 404)
    vide = js(c.post("/api/chapters", json={"title": "Vide", "script_text": "x"}))
    r = c.post(f"/api/chapters/{vide.get('id')}/episode", json={})
    check("R2 sans storyboard : 400 qui dit quoi faire", r.status_code == 400 and "découpe" in r.text)
    T = "Vane entre sous la pluie.\n\nYsolde se tait.\n\nLa porte claque."
    ch = js(c.post("/api/chapters", json={"title": "L’Éveil", "script_text": T}))
    cid = ch.get("id")
    shots = js(c.post(f"/api/chapters/{cid}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [])
    Image.new("RGB", (54, 96), (200, 40, 40)).save(_tmp / "images" / "prod.png")
    Image.new("RGB", (54, 96), (40, 40, 200)).save(_tmp / "images" / "croquis.png")
    with sqlite3.connect(str(_DB)) as db:
        db.execute("UPDATE shots SET image='prod.png', sketch_image='croquis.png' WHERE id=?", (shots[0]["id"],))
        db.execute("UPDATE shots SET sketch_image='croquis.png' WHERE id=?", (shots[1]["id"],))
        db.execute("UPDATE shots SET sketch_image='disparu.png' WHERE id=?", (shots[2]["id"],))
    c.put(f"/api/shots/{shots[0]['id']}", json={"action": "Gros plan : Vane, trempé."})   # l'ACTION n'est pas la narration
    narr = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Narrateur", "description": "voix"}))
    sqlite3.connect(str(_DB)).execute("UPDATE bible_entities SET voice_id='voix-narr' WHERE id=?", (narr.get("id"),)).connection.commit()
    n_jobs, n_dep = compte("jobs"), compte("depenses")
    r = c.post(f"/api/chapters/{cid}/episode", json={})
    j = js(r)
    ep = js(c.get(f"/api/episodes/{j.get('episode_id')}"))
    sc = ep.get("scenes") or []
    check("R3 un Episode cree : le titre, le TEXTE du chapitre, la voix du NARRATEUR, une scene PAR PLAN (son texte d'origine)",
          r.status_code == 200 and ep.get("title") == "L’Éveil" and ep.get("script") == T and ep.get("voice_id") == "voix-narr"
          and [s.get("text") for s in sc] == ["Vane entre sous la pluie.", "Ysolde se tait.", "La porte claque."], f"{r.status_code} {ep}")
    check("R4 l'image : PRODUCTION d'abord, sinon croquis, et rien si le fichier a disparu ; « 2 avec image » dit",
          [s.get("image_filename") for s in sc] == ["prod.png", "croquis.png", None] and j.get("images") == 2 and j.get("scenes") == 3, str(sc))
    check("R5 Ken Burns partout (gratuit) — JAMAIS « seedance » (rendu video payant)", [s.get("motion") for s in sc] == ["kenburns"] * 3)
    check("R6 SANS RENDU : aucun appel de voix, aucun job, aucune depense, aucune narration",
          APPELS == [] and compte("jobs") == n_jobs and compte("depenses") == n_dep and ep.get("narration") is None
          and not (_tmp / "outputs" / "episodes" / str(j.get("episode_id"))).exists())
    lst = js(c.get("/api/episodes")).get("episodes", [])
    check("R7 il apparait dans la liste « Mes episodes » de la vue Episodes", any(e.get("id") == j.get("episode_id") and e.get("scene_count") == 3 for e in lst))
    src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
    check("R8 la route n'est PAS payante (absente du recensement, aucun puits appele)", "/chapters/{chapter_id}/episode" not in src)

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
import re as _re                                                     # noqa: E402
_at = _ICI.parent.parent / "frontend" / "atelier"
_js = (_at / "atelier.js").read_text(encoding="utf-8")
_html = (_at / "index.html").read_text(encoding="utf-8")
_fn = _js.split("async function versEpisode(")[1].split("\n}\n")[0] if "async function versEpisode(" in _js else ""
check("U1 le bouton 📺 Episode du storyboard, avec un title qui dit « SANS rendu »", _re.search(r'<button id="versEpisode" class="btn" title="[^"]*SANS rendu[^"]*">', _html) is not None
      and '$("#versEpisode").addEventListener("click", versEpisode);' in _js)
check("U2 le dialogue maison DIT que rien n'a ete narre ni rendu, et ouvre la vue Episodes dans un onglet",
      "window.__dzDialogue.confirmer(" in _fn and "Rien n'a été narré ni rendu" in _fn and 'window.open(r.vue, "_blank")' in _fn
      and "« Flux d'origine » → « Ouvrir ▾ »" in _fn          # le CHEMIN réel, relevé à l'écran le 02/10
      and not _re.search(r"(?<![.\w])(confirm|alert)\(", _fn))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
