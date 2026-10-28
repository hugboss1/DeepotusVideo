# -*- coding: utf-8 -*-
"""t356 (28/10/2026) — Veille & prospection P5, tâche 3 : les ROUTES du canal e-mail (/api/prospects/{eid}/email…).
Lire (jamais un secret), régler (refus 422 avec message), poser un secret, essai vers l'expéditeur seulement, reprendre.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_email_routes.py"""
import os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmailr356_"))
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
from app.services import email_canal as M, espaces as E              # noqa: E402

c = TestClient(app)
A = E.creer({"nom": "Prospection"})["id"]
U = f"/api/prospects/{A}/email"
r = c.get(U)
check("1 lire : vierge, non prêt", r.status_code == 200 and r.json()["pret"] is False, r.text[:200])
r = c.post(U, json={"expediteur": {"nom": "Léa", "adresse": "nope"}})
check("2 réglage fautif : 422 avec message", r.status_code == 422 and r.json()["detail"]["code"] == "champ" and r.json()["detail"]["message"], r.text[:200])
r = c.post(U, json={"mode": "smtp", "expediteur": {"nom": "Léa", "adresse": "lea@deepotus.fr"},
                    "identite": {"raison_sociale": "Deepotus SAS", "adresse_postale": "Paris"},
                    "smtp": {"hote": "smtp.deepotus.fr", "port": 465, "securite": "ssl", "utilisateur": "lea@deepotus.fr"},
                    "imap": {"hote": "imap.deepotus.fr", "port": 993, "utilisateur": "lea@deepotus.fr"}})
check("3 réglé : 200", r.status_code == 200 and r.json()["manques"] == ["mdp"], r.text[:200])
r = c.post(U + "/secret", json={"quoi": "mdp", "valeur": "TresSecret!"})
check("4 secret posé : prêt, jamais rendu", r.status_code == 200 and r.json()["pret"] and "TresSecret" not in r.text and "TresSecret" not in c.get(U).text)
ENVOIS = []
M.envoyer = lambda eid, msg: ENVOIS.append(msg) or {"message_id": str(msg["Message-ID"])}
r = c.post(U + "/test")
check("5 essai : à l'expéditeur seulement, hors journal", r.status_code == 200 and ENVOIS and ENVOIS[0]["To"] == "lea@deepotus.fr"
      and not M._doc(A)["journal"], r.text[:200])


def refuse(eid, msg):
    raise M.RefusEmail("identifiants SMTP refusés : vérifiez l'utilisateur et le mot de passe", "config")


M.envoyer = refuse
r = c.post(U + "/test")
check("6 essai refusé : 409 avec message", r.status_code == 409 and "identifiants" in r.json()["detail"]["message"], r.text[:200])
M.noter(A, "plainte", "x@y.fr", None)
check("7 en pause, reprendre : 200, pause levée", c.get(U).json()["pause"]["active"] and c.post(U + "/reprendre").json()["pause"]["active"] is False)
check("8 espace inconnu : 404", c.get("/api/prospects/es_inconnu00/email").status_code == 404)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
