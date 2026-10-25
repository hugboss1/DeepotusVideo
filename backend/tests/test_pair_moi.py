# -*- coding: utf-8 -*-
"""L4.1 T2 : `GET /api/pair/moi` — « qui suis-je ? » pour l'appareil. Le téléphone apprend son id depuis son jeton, pour
que ses conversations envoyées au PC portent le bon `appareil`.
  m1 jeton valide -> {appareil:{id,nom}}, id égal à celui rendu par `claim`
  m2 jeton révoqué -> 401
  m3 boucle locale sans jeton -> 404 {"detail": "pas d'appareil"}
  m4 LECTURE SEULE : la route n'est pas dans `_ECRITURES_OUVERTES`
Vraies requêtes (TestClient à l'IP voulue), base jetable.
Run : & $PY tests/test_pair_moi.py   (depuis le dépôt, PYTHONUTF8=1)."""
import os, pathlib, shutil, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PARENT = tempfile.mkdtemp(prefix="dzpairmoi_")
TMP = os.path.join(PARENT, "data")
os.makedirs(TMP)
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
for _d in ("images", "outputs"):
    os.makedirs(os.path.join(TMP, _d), exist_ok=True)
os.environ["IMAGES_FOLDER"] = os.path.join(TMP, "images")
os.environ["OUTPUTS_FOLDER"] = os.path.join(TMP, "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                           # noqa: E402
import app.main as MAIN                                              # noqa: E402
from app.main import app                                             # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


LAN = ("192.168.1.60", 50000)
LOC = ("127.0.0.1", 50000)


def _lanceur():
    with TestClient(app, client=LOC, raise_server_exceptions=False) as loc, \
            TestClient(app, client=LAN, raise_server_exceptions=False) as lan:
        secret = loc.post("/api/pair/start").json()["secret"]
        c = lan.post("/api/pair/claim", json={"secret": secret, "nom": "Oppo de Oli"}).json()
        jeton, ap = c["jeton"], c["appareil"]
        h = {"Authorization": "Bearer " + jeton}

        print("[m] qui suis-je ?")
        r = lan.get("/api/pair/moi", headers=h)
        check("m1 jeton valide : 200, id et nom de l'appareil, id égal à celui du claim",
              r.status_code == 200 and r.json() == {"appareil": {"id": ap["id"], "nom": "Oppo de Oli"}}, r.text[:160])
        check("m1b sans jeton depuis le réseau local : 401",
              lan.get("/api/pair/moi").status_code == 401)
        r = loc.get("/api/pair/moi")
        check("m3 boucle locale sans jeton : 404 « pas d'appareil »",
              r.status_code == 404 and r.json() == {"detail": "pas d'appareil"}, r.text[:160])
        check("m3b boucle locale avec le jeton : 200, le même appareil",
              loc.get("/api/pair/moi", headers=h).json().get("appareil", {}).get("id") == ap["id"])
        check("m3c boucle locale avec un jeton inconnu : 401",
              loc.get("/api/pair/moi", headers={"Authorization": "Bearer " + "0" * 64}).status_code == 401)
        check("m4 lecture seule : rien de /pair/moi dans _ECRITURES_OUVERTES, et POST refusé (403 depuis le réseau local)",
              not any("pair/moi" in p for _m, p in MAIN._ECRITURES_OUVERTES)
              and not MAIN._ecriture_ouverte("POST", "/api/pair/moi")
              and lan.post("/api/pair/moi", headers=h).status_code == 403)
        rv = loc.post(f"/api/devices/{ap['id']}/revoke")
        r = lan.get("/api/pair/moi", headers=h)
        check("m2 jeton révoqué : 401", rv.status_code == 200 and r.status_code == 401, f"{rv.status_code} {r.status_code}")
    shutil.rmtree(PARENT, ignore_errors=True)
    print(f"\n{ok} ok, {fail} fail")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_lanceur())
