# -*- coding: utf-8 -*-
"""P1 #14 (29/09/2026) — GARDE « BOUCLE LOCALE » SUR LES ROUTES DE GENERATION PAYANTES.

Mesure du 29/09 (base caaa5a6) : les sept routes qui depensent une cle
fournisseur -- POST /generate, /generate/batch, /generate/heygen,
/generate/heygen-image, /generate/heygen-cinematic, /generate/composition,
/images/generate -- n'appelaient pas `_require_localhost` (les Reglages, eux,
le font). Pas une faille aujourd'hui (ecoute sur la boucle locale + garde
d'origine), mais a poser AVANT toute ouverture au reseau local (compagnon
mobile) : un client 192.168.x.y atteignait la route.
Decision : `_require_local_depense(req)` en TETE de chaque route (avant toute
lecture de fichier, garde de cout, cle ou job) -> 403 « Generation payante
reservee a la machine locale » ; les hotes admis sont ceux de
`_require_localhost` (une seule liste, _HOTES_LOCAUX).
Le banc : TestClient avec un client du reseau local (192.168.1.20) -> 403 sur
les sept, AUCUN appel au pipeline ni a la garde de cout (espions) ; client
local (testclient, 127.0.0.1) -> jamais 403. Temoin : les memes appels sur le
routes.py de la base (git show), monte dans une application a part.
Run : & $PY tests/test_p1_garde_localhost.py   (depuis backend/)
"""
import importlib.util, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp1lh_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                 # noqa: E402
logger.remove()
BASE = "caaa5a6"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:600]
    except Exception as e:                                  # pragma: no cover
        return f"(detail illisible : {e})"


import asyncio                                             # noqa: E402
from fastapi import FastAPI                                # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402
from app.services.storage import init_db                   # noqa: E402
asyncio.run(init_db())
from app.api import routes as RT                           # noqa: E402

ROUTES = [
    ("/api/generate", {"image_filename": "a.png", "custom_prompt": "x"}),
    ("/api/generate/batch", {"image_filename": "a.png", "custom_prompt": "x", "variations_count": 2}),
    ("/api/generate/heygen", {"avatar_id": "a", "voice_id": "v", "script": "bonjour"}),
    ("/api/generate/heygen-image", {"image_filename": "a.png", "voice_id": "v", "script": "bonjour"}),
    ("/api/generate/heygen-cinematic", {"image_filename": "a.png", "voice_id": "v", "script": "bonjour"}),
    ("/api/generate/composition", {"seedance": {"image_filename": "a.png", "custom_prompt": "x"},
                                   "heygen": {"avatar_id": "a", "voice_id": "v", "script": "bonjour"}}),
    ("/api/images/generate", {"prompt": "chat", "model": "flux"}),
]
LAN = ("192.168.1.20", 50000)


def _app(module):
    a = FastAPI()
    a.include_router(module.router, prefix="/api")
    return a


def _jouer(module):
    """{route: (code_lan, code_local, code_127, appels)} ; espions sur le pipeline et la garde de cout."""
    appels = []
    orig = {}
    for nom in ("_garde_cout",):
        if hasattr(module, nom):
            orig[nom] = getattr(module, nom)
            setattr(module, nom, lambda *a, _n=nom, **k: appels.append(_n) or 0.0)
    p = getattr(module, "pipeline", None)
    porig = {}
    if p is not None:
        for nom in ("run", "run_composition", "run_heygen", "run_heygen_image", "run_heygen_cinematic"):
            if hasattr(p, nom):
                porig[nom] = getattr(p, nom)
                setattr(p, nom, lambda *a, _n=nom, **k: appels.append(_n))
    out = {}
    try:
        app = _app(module)
        lan = TestClient(app, client=LAN)
        loc = TestClient(app)
        l127 = TestClient(app, client=("127.0.0.1", 50001))
        for url, corps in ROUTES:
            n0 = len(appels)
            r1 = lan.post(url, json=corps)
            n1 = len(appels)
            r2 = loc.post(url, json=corps)
            r3 = l127.post(url, json=corps)
            try:
                det = r1.json().get("detail")
            except Exception:                              # noqa: BLE001
                det = r1.text[:80]
            out[url] = {"lan": r1.status_code, "det": str(det)[:120], "appels_lan": n1 - n0,
                        "local": r2.status_code, "l127": r3.status_code}
    finally:
        for nom, f in orig.items():
            setattr(module, nom, f)
        for nom, f in porig.items():
            setattr(p, nom, f)
    return out


N = _jouer(RT)
OLD = None
try:
    src = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], cwd=ROOT, capture_output=True).stdout
    pth = pathlib.Path(TMP) / "routes_base.py"
    pth.write_bytes(src)
    sp = importlib.util.spec_from_file_location("app.api._routes_base_lh", str(pth))
    OLD = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(OLD)
except Exception as e:                                      # noqa: BLE001
    print("  (temoin indisponible :", e, ")")
O = _jouer(OLD) if OLD is not None else {}

print("\n[0] temoin : routes.py de la base (%s)" % BASE)
check("0.1 temoin charge", bool(O) and len(O) == 7, _d(len(O)))
check("0.2 TEMOIN : a la base, un client du reseau local n'est refuse (403) par AUCUNE des sept routes",
      all(v["lan"] != 403 for v in O.values()), _d({k: v["lan"] for k, v in O.items()}))

print("\n[1] client du reseau local : 403 sur les sept, avant tout travail")
for url, _c in ROUTES:
    v = N.get(url) or {}
    check(f"1.x {url} : 403 « reservee a la machine locale », aucun appel (pipeline, garde de cout)",
          v.get("lan") == 403 and "machine locale" in v.get("det", "") and v.get("appels_lan") == 0, _d(v))

print("\n[2] client local : jamais 403 (le comportement d'hier)")
for url, _c in ROUTES:
    v = N.get(url) or {}
    check(f"2.x {url} : testclient et 127.0.0.1 passent la garde", v.get("local") not in (None, 403) and v.get("l127") not in (None, 403),
          _d(v))
check("2.y les codes locaux sont ceux de la base (la garde ne change rien d'autre)",
      all((N.get(u) or {}).get("local") == (O.get(u) or {}).get("local") for u, _c in ROUTES),
      _d({u: [(N.get(u) or {}).get("local"), (O.get(u) or {}).get("local")] for u, _c in ROUTES}))

print("\n[3] une seule liste d'hotes")
check("3.1 _require_localhost et la garde de depense partagent _HOTES_LOCAUX",
      getattr(RT, "_HOTES_LOCAUX", None) == ("127.0.0.1", "::1", "localhost", "testclient"), _d(getattr(RT, "_HOTES_LOCAUX", None)))

import shutil                                               # noqa: E402
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
