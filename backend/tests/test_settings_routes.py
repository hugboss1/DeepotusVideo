# -*- coding: utf-8 -*-
"""Routeur des reglages (plan Settings T2, tache #15, 29/09/2026) — /api/reglages/diagnostic et
/api/reglages/diagnostic/cle, montes sur l'APPLICATION REELLE (banc-miroir : il relit les reponses JSON, jamais le
module seul). Zero reseau : le hook `_get` du diagnostic et le producteur des soldes sont remplaces.
Run : & $PY tests/test_settings_routes.py   (depuis backend/)"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzregl_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
(_tmp / ".env").write_text("FAL_KEY=abcd1234efgh5678\nMESHY_API_KEY=\nOPENAI_MODEL=gpt-4o-mini\n", encoding="utf-8")
(_tmp / "logs").mkdir(exist_ok=True)
(_tmp / "logs" / "deepotus-2026-09-29.log").write_text(
    "2026-09-29 09:00:00.000 | ERROR    | app.z:h:3 - panne simulee\n", encoding="utf-8")

from loguru import logger                                          # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402
from app.config import APP_VERSION                                 # noqa: E402
from app.main import app                                           # noqa: E402
from app.api import settings_routes as SR                          # noqa: E402
from app.services import diagnostic as D                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


async def _faux_soldes():
    return {"heygen": {"available": True, "credits": 766, "usd": 30.64}}
SR._soldes = _faux_soldes
APPELS = []
async def _faux_get(url, headers=None, timeout=15.0):
    APPELS.append((url, dict(headers or {})))
    if "queue.fal.run" in url:
        return 404, {"detail": "Request not found"}
    return 401, {"error": {"message": "invalid key"}}
D._get = _faux_get

c = TestClient(app)   # sans `with` : le lifespan (init_db, boucles) ne part pas
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E401,E702
import _jeton_appareil as _JA  # noqa: E402 — tache #56 : le reseau local exige un jeton d'appareil (garde exterieure)
lan = TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app))

print("\n[1] GET /api/reglages/diagnostic : l'ecran unique")
r = c.get("/api/reglages/diagnostic")
check("1.1 200", r.status_code == 200, str(r.status_code))
j = r.json() if r.status_code == 200 else {}
check("1.2 version = APP_VERSION", j.get("version") == APP_VERSION, str(j.get("version")))
cles = {k["cle"]: k for k in j.get("cles", [])}
check("1.3 toutes les cles autorisees listees (FIGMA_TOKEN compris)", {"FAL_KEY", "MESHY_API_KEY", "FIGMA_TOKEN"} <= set(cles), "")
f = cles.get("FAL_KEY") or {}
check("1.4 FAL_KEY definie et testable, apercu masque", f.get("definie") is True and f.get("testable") is True
      and f.get("apercu", "").startswith("abcd") and f.get("apercu", "").endswith("5678"), json.dumps(f))
check("1.5 AUCUNE valeur de cle en clair dans la reponse", "abcd1234efgh5678" not in json.dumps(j), "")
check("1.6 cle vide = non definie ; reglage (OPENAI_MODEL) non testable", (cles.get("MESHY_API_KEY") or {}).get("definie") is False
      and (cles.get("OPENAI_MODEL") or {}).get("testable") is False, "")
check("1.7 poids disque present (categories, total)", "categories" in j.get("disque", {}) and j["disque"]["total_octets"] >= 0, "")
check("1.8 journal lu depuis DATA_ROOT/logs", [l.get("message") for l in j.get("journal", [])] == ["panne simulee"], json.dumps(j.get("journal")))
check("1.9 soldes repris du producteur unique (/cost/balances)", (j.get("soldes") or {}).get("heygen", {}).get("credits") == 766, "")
check("1.10 aucun appel reseau pour afficher l'ecran", APPELS == [], json.dumps(APPELS))

print("\n[2] POST /api/reglages/diagnostic/cle : un test, la cle relue du .env")
r = c.post("/api/reglages/diagnostic/cle", json={"nom": "FAL_KEY"})
check("2.1 FAL_KEY relue du .env et acceptee (404 fal)", r.status_code == 200 and r.json().get("ok") is True, r.text[:200])
check("2.2 c'est bien la cle du .env qui est partie (en-tete), sans jamais revenir dans la reponse",
      APPELS and APPELS[-1][1].get("Authorization") == "Key abcd1234efgh5678" and "abcd1234efgh5678" not in r.text, "")
r2 = c.post("/api/reglages/diagnostic/cle", json={"nom": "OPENAI_API_KEY", "valeur": "sk-x"})
check("2.3 valeur fournie (avant enregistrement) : 401 -> refusee", r2.json().get("ok") is False, r2.text[:200])
r3 = c.post("/api/reglages/diagnostic/cle", json={"nom": "PATH"})
check("2.4 cle hors liste refusee en le disant (400)", r3.status_code == 400 and "PATH" in r3.json().get("detail", ""), r3.text[:200])
r4 = c.post("/api/reglages/diagnostic/cle", json={"nom": "X_API_KEY"})
check("2.5 X : test de groupe, pas de verdict par cle", r4.json().get("ok") is None, r4.text[:200])

print("\n[3] boucle locale")
check("3.1 GET depuis le reseau local : 403 (les apercus de cles sont des Reglages)", lan.get("/api/reglages/diagnostic").status_code == 403, "")
check("3.2 POST depuis le reseau local : 403", lan.post("/api/reglages/diagnostic/cle", json={"nom": "FAL_KEY"}).status_code == 403, "")

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
