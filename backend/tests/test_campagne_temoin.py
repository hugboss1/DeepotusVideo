# -*- coding: utf-8 -*-
"""t359 (28/10/2026) — Veille & prospection P8, côté PC : la CAMPAGNE TÉMOIN d'un espace démonstration.
Le système de l'agent dit, pour un espace démonstration, que la campagne est un témoin qui ne publie jamais ;
`GET /api/agent/campagnes/temoins` liste les espaces démonstration (nom, prospect d'origine, conversation existante) ;
`POST /api/agent/campagnes/temoin` {espace_id} ouvre la conversation « campagnes » de l'espace (la même ensuite) ;
un espace qui n'est pas une démonstration : 409.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_campagne_temoin.py"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztemoin359_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
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


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                             # noqa: E402
from app.services import agent_campagnes as AC, espaces as E         # noqa: E402

with TestClient(app) as c:
    A = E.creer({"nom": "Prospection"})["id"]
    D = E.creer_demonstration("Démo · Studio Lune", "#ef4444", {"espace": A, "prospect": "pr_00000001"})["id"]
    s = AC.systeme_pour("campagnes", D, "fr")
    check("1 système d'un espace démonstration : campagne TÉMOIN, rien n'est jamais publié", "TÉMOIN" in s and "jamais publi" in s, s[-600:])
    check("2 un espace ordinaire n'a pas ce paragraphe", "TÉMOIN" not in AC.systeme_pour("campagnes", A, "fr"))
    r = c.get("/api/agent/campagnes/temoins")
    l = r.json().get("temoins") if r.status_code == 200 else None
    check("3 liste des espaces démonstration (nom, prospect, sans conversation)", l == [{"espace_id": D, "nom": "Démo · Studio Lune",
          "prospect": "pr_00000001", "conversation_id": None}], (r.status_code, r.text[:300]))
    r = c.post("/api/agent/campagnes/temoin", json={"espace_id": D})
    cid = (r.json() or {}).get("id")
    check("4 ouvrir : une conversation « campagnes » de l'espace démonstration", r.status_code == 200 and r.json().get("role") == "campagnes"
          and r.json().get("espace_id") == D and "témoin" in (r.json().get("titre") or "").lower(), r.text[:300])
    r2 = c.post("/api/agent/campagnes/temoin", json={"espace_id": D})
    check("5 rouvrir : la même conversation", r2.status_code == 200 and r2.json().get("id") == cid)
    check("6 la liste la donne", c.get("/api/agent/campagnes/temoins").json()["temoins"][0]["conversation_id"] == cid)
    check("7 un espace ordinaire : 409", c.post("/api/agent/campagnes/temoin", json={"espace_id": A}).status_code == 409)
    check("8 espace inconnu : 400 ou 404", c.post("/api/agent/campagnes/temoin", json={"espace_id": "es_inconnu00"}).status_code in (400, 404))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
