# -*- coding: utf-8 -*-
"""t316 (28/10/2026) (D2, tâche 2) — banc des routes /api/skins (app/api/skins_routes.py), sous TestClient.
Plan docs/superpowers/plans/2026-10-28-t316-skins.md, spec boîte à outils §8.5.
  1. liste de l'espace courant (choisi par défaut = livre-deepotus, livrés), actif + contexte (logo de l'ESPACE) ;
  2. créer (copie d'un livré), lire avec contexte, enregistrer, livré non modifiable (409), id hostile (400/404),
     corps illisible (400) ;
  3. choix : d'un skin de l'espace, sans habillage, d'un skin d'un autre espace (409, en-tête X-Dz-Espace) ;
  4. images : PUT (Pillow), GET (image/png), DELETE ; pas une image (415) ;
  5. export (application/zip, pièce jointe) puis import (skin neuf de l'espace courant, ignorés dits) ;
  6. hors machine locale : 403 partout, rien d'écrit.
Données jetables, aucun réseau. Run (depuis backend/) : & $PY tests/test_skins_routes.py"""
import io, json, os, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzskinsrt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


from app.main import app                                            # noqa: E402
from app.services import skins as K, espaces                        # noqa: E402
from PIL import Image                                                 # noqa: E402


def png(l=30, h=30):
    b = io.BytesIO(); Image.new("RGBA", (l, h), (10, 200, 10, 255)).save(b, "PNG"); return b.getvalue()


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    eid = espaces.lire()["actif"]
    autre = espaces.creer({"nom": "Client Rouge", "couleur": "#cc0000"})["id"]
    print("[1] liste et actif")
    r = c.get("/api/skins"); j = r.json()
    check("1.1 GET /api/skins : espace courant, choisi par défaut livre-deepotus, cinq livrés, aucun skin",
          r.status_code == 200 and j["espace"] == eid and j["choisi"] == "livre-deepotus" and len(j["livres"]) == 5 and j["skins"] == [], j)
    j = c.get("/api/skins/actif").json()
    check("1.2 GET /actif : skin Deepotus (signature active) + contexte (logo de l'ESPACE)",
          j["skin"]["id"] == "livre-deepotus" and j["skin"]["signature"]["actif"] is True
          and j["contexte"]["logo_espace"] == f"/api/espaces/{eid}/logo" and j["contexte"]["kit"]["brand_color"], j)

    print("[2] créer, lire, enregistrer")
    r = c.post("/api/skins", json={"base": "livre-jeu", "nom": "Mon jeu"}); s = r.json()
    check("2.1 POST : copie d'un livré dans l'espace", r.status_code == 200 and s["espace_id"] == eid and s["nom"] == "Mon jeu" and s["base"] == "livre-jeu", s)
    j = c.get(f"/api/skins/{s['id']}").json()
    check("2.2 GET /{id} : skin + contexte", j["skin"]["id"] == s["id"] and j["contexte"]["espace"]["id"] == eid)
    r = c.put(f"/api/skins/{s['id']}", json={"bandeau": {"titre": "Partie 1", "x": 2}, "nom": "Jeu du soir"})
    check("2.3 PUT : enregistré et normalisé", r.status_code == 200 and r.json()["bandeau"]["titre"] == "Partie 1"
          and r.json()["bandeau"]["x"] <= 1 and r.json()["nom"] == "Jeu du soir", r.json())
    check("2.4 PUT sur un livré -> 409 ; DELETE d'un livré -> 409", c.put("/api/skins/livre-neon", json={}).status_code == 409
          and c.delete("/api/skins/livre-neon").status_code == 409)
    check("2.5 id hostile -> 400 (ou 404 si la route ne le reçoit pas), introuvable -> 404",
          c.get("/api/skins/ABC").status_code == 400 and c.get("/api/skins/0123456789abcdef").status_code == 404
          and c.put("/api/skins/..%2F..%2Fx", json={}).status_code in (400, 404, 405))
    check("2.6 corps illisible -> 400 ; base non textuelle -> 400",
          c.post("/api/skins", content=b"[1,", headers={"Content-Type": "application/json"}).status_code == 400
          and c.post("/api/skins", json={"base": 3}).status_code == 400)

    print("[3] choix")
    r = c.put("/api/skins/choix", json={"skin_id": s["id"]})
    check("3.1 choisir un skin de l'espace", r.status_code == 200 and c.get("/api/skins").json()["choisi"] == s["id"]
          and c.get("/api/skins/actif").json()["skin"]["nom"] == "Jeu du soir")
    check("3.2 sans habillage : actif null", c.put("/api/skins/choix", json={"skin_id": ""}).json() == {"choisi": ""}
          and c.get("/api/skins/actif").json()["skin"] is None)
    r = c.put("/api/skins/choix", json={"skin_id": s["id"]}, headers={"X-Dz-Espace": autre})
    check("3.3 un skin d'un autre espace -> 409 (X-Dz-Espace)", r.status_code == 409, r.text)
    j = c.get("/api/skins", headers={"X-Dz-Espace": autre}).json()
    check("3.4 l'autre espace a son propre choix (défaut) et aucun skin", j["espace"] == autre and j["choisi"] == "livre-deepotus" and j["skins"] == [], j)

    print("[4] images")
    r = c.put(f"/api/skins/{s['id']}/images/logo", content=png(), headers={"Content-Type": "image/png"})
    check("4.1 PUT logo : relu, source « image »", r.status_code == 200 and r.json()["logo"]["source"] == "image", r.text)
    r = c.get(f"/api/skins/{s['id']}/images/logo")
    check("4.2 GET logo : image/png", r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG")
    check("4.3 pas une image -> 415 ; nom inconnu -> 400", c.put(f"/api/skins/{s['id']}/images/fond", content=b"<svg/>").status_code == 415
          and c.put(f"/api/skins/{s['id']}/images/autre", content=png()).status_code == 400)
    check("4.4 DELETE logo : logo de l'espace", c.delete(f"/api/skins/{s['id']}/images/logo").json()["logo"]["source"] == "espace"
          and c.get(f"/api/skins/{s['id']}/images/logo").status_code == 404)

    print("[5] export / import")
    c.put(f"/api/skins/{s['id']}/images/fond", content=png(64, 36))
    r = c.get(f"/api/skins/{s['id']}/export")
    check("5.1 export : application/zip en pièce jointe", r.status_code == 200 and r.headers["content-type"] == "application/zip"
          and "attachment" in r.headers["content-disposition"] and r.content[:2] == b"PK", r.headers)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        noms = sorted(z.namelist())
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        with zipfile.ZipFile(io.BytesIO(r.content)) as src:
            for n in src.namelist():
                z.writestr(n, src.read(n))
        z.writestr("../hors.txt", "x")
    r2 = c.post("/api/skins/import", content=b.getvalue(), headers={"Content-Type": "application/zip", "X-Dz-Espace": autre})
    j = r2.json()
    check("5.2 import dans l'espace de la requête : skin neuf, fond repris, entrée hors liste dite",
          r2.status_code == 200 and j["espace_id"] == autre and j["images"] == ["fond"] and j["ignores"] == ["../hors.txt"]
          and noms == ["images/fond.png", "skin.json"], (r2.text, noms))
    check("5.3 import d'un non-zip -> 400", c.post("/api/skins/import", content=b"pas un zip").status_code == 400)
    check("5.4 DELETE d'un skin -> supprimé, 404 ensuite", c.delete(f"/api/skins/{j['id']}").json() == {"supprime": j["id"]}
          and c.get(f"/api/skins/{j['id']}").status_code == 404)

sys.path.insert(0, str(_ICI))
import _jeton_appareil as _JA                                       # noqa: E402
# un téléphone APPAIRÉ (jeton valide) : il passe la garde réseau, la garde locale le refuse quand même
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c:
    print("[6] hors machine locale (appareil appairé)")
    avant = sorted(str(p) for p in K.racine().rglob("*"))
    codes = [c.get("/api/skins").status_code, c.get("/api/skins/actif").status_code, c.put("/api/skins/choix", json={"skin_id": ""}).status_code,
             c.post("/api/skins", json={}).status_code, c.post("/api/skins/import", content=b"x").status_code,
             c.get(f"/api/skins/{s['id']}").status_code, c.put(f"/api/skins/{s['id']}", json={}).status_code,
             c.delete(f"/api/skins/{s['id']}").status_code, c.get(f"/api/skins/{s['id']}/export").status_code,
             c.put(f"/api/skins/{s['id']}/images/logo", content=png()).status_code]
    check("6.1 403 partout, rien d'écrit", codes == [403] * 10 and sorted(str(p) for p in K.racine().rglob("*")) == avant, codes)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
