# -*- coding: utf-8 -*-
"""Plan Quick T6 (tache #53 du suivi, 01/10/2026) — presets Quick sur les quatre onglets : un preset EST la recette
de T1 (quick_recipe) nommee et rangee par onglet, dans la table neuve `quick_presets`. Le banc lit la reponse HTTP
ET la ligne SQLite (pas seulement l'echo de la route). Aucun reseau, data-dir isole (aucune cle reelle).
Temoin positif : la base (21ac7ace) n'a ni la table ni la route.
Run (depuis backend/) : & $PY tests/test_quick_presets.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqpre_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
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

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "21ac7ace"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/storage.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas de route /quick/presets", r0.returncode == 0 and b"/quick/presets" not in r0.stdout)
check("T2 temoin : la base n'a pas de table quick_presets", r1.returncode == 0 and b"quick_presets" not in r1.stdout)


def _ligne(pid):
    cx = sqlite3.connect(str(_DB))
    try:
        return cx.execute("SELECT name, tab, recipe FROM quick_presets WHERE id=?", (pid,)).fetchone()
    finally:
        cx.close()


RS = {"v": 1, "tab": "seedance", "seedance": {"prompt": "abysse", "duration": 10, "aspect": "9:16"}, "layout": "sequential"}
RH = {"v": 1, "tab": "heygen", "heygen": {"script": "Bonjour é", "avatar": "a1"}}
RV = {"v": 1, "tab": "voice", "voice": {"text": "dz"}}

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[A] creer")
    a = c.post("/api/quick/presets", json={"name": "  Abysse 10 s  ", "tab": "seedance", "recipe": RS})
    pa = a.json().get("id") if a.status_code == 200 else None
    check("A1 200 + id", a.status_code == 200 and pa, a.text[:200])
    row = _ligne(pa) if pa else None
    check("A2 la LIGNE SQLite porte nom rogne, onglet et recette JSON identique",
          row is not None and row[0] == "Abysse 10 s" and row[1] == "seedance" and json.loads(row[2]) == RS, str(row))
    h = c.post("/api/quick/presets", json={"name": "Présentation", "tab": "heygen", "recipe": RH})
    v = c.post("/api/quick/presets", json={"name": "Voix", "tab": "voice", "recipe": RV})
    ph = h.json().get("id")
    check("A3 heygen et voice acceptes ; l'unicode survit dans la base",
          h.status_code == 200 and v.status_code == 200 and json.loads(_ligne(ph)[2]) == RH, h.text[:200])

    print("\n[B] refus")
    check("B1 recette vide : 422", c.post("/api/quick/presets", json={"name": "x", "tab": "seedance", "recipe": {}}).status_code == 422)
    check("B2 onglet inconnu : 422", c.post("/api/quick/presets", json={"name": "x", "tab": "studio", "recipe": RS}).status_code == 422)
    check("B3 nom vide : 422", c.post("/api/quick/presets", json={"name": "", "tab": "seedance", "recipe": RS}).status_code == 422)
    gros = {"v": 1, "blob": "x" * (70 * 1024)}
    check("B4 recette > 64 Ko : 413", c.post("/api/quick/presets", json={"name": "g", "tab": "comp", "recipe": gros}).status_code == 413)

    print("\n[C] lister")
    tous = c.get("/api/quick/presets").json().get("presets", [])
    check("C1 sans filtre : les trois, le plus recent d'abord", [p["name"] for p in tous] == ["Voix", "Présentation", "Abysse 10 s"],
          str([p["name"] for p in tous]))
    sd = c.get("/api/quick/presets", params={"tab": "seedance"}).json().get("presets", [])
    check("C2 filtre par onglet ; la recette revient en OBJET", len(sd) == 1 and sd[0]["recipe"] == RS and sd[0]["id"] == pa, str(sd)[:200])
    check("C3 onglet sans preset : liste vide", c.get("/api/quick/presets", params={"tab": "comp"}).json() == {"presets": []})

    print("\n[D] supprimer")
    d = c.delete(f"/api/quick/presets/{pa}")
    check("D1 200 et la ligne a QUITTE la base", d.status_code == 200 and _ligne(pa) is None, d.text[:200])
    check("D2 inconnu : 404", c.delete(f"/api/quick/presets/{pa}").status_code == 404)
    check("D3 les autres restent", len(c.get("/api/quick/presets").json()["presets"]) == 2)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
