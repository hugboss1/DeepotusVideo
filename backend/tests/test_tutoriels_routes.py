# -*- coding: utf-8 -*-
"""t319 (28/10/2026) (D5, tâche 4) — banc des routes /api/tutoriels (TestClient, données jetables, aucun réseau).
Plan docs/superpowers/plans/2026-10-28-t319-tutoriels.md.
  1. brouillon : lecture (proposé), enregistrement validé, proposition ; capture en cours 409, inconnue 404, id 400 ;
  2. fabrication (brouillons sur disque, rien dans docs/ ni frontend/), fabrication concurrente 409 ;
  3. parcours : export téléchargé, import du corps brut, lecture avec action locale, vidéo, liste, retrait ; import
     abîmé 400, corps vide 400 ;
  4. hors machine locale : 403 partout ; 5. L10 : refus en anglais.
Run (depuis backend/) : & $PY tests/test_tutoriels_routes.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztutor_"))
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
from app.api import tutoriels_routes as TR                          # noqa: E402
from app.services import capture_montage as M, tutoriels as T      # noqa: E402
FF = M._ffmpeg()
REPO = _ICI.parent.parent


def fausse_capture(cid, etat="terminee"):
    d = M.racine() / cid
    d.mkdir(parents=True)
    octets = subprocess.run([FF, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=960x600:r=30:d=5", "-c:v", "libvpx",
                             "-b:v", "1M", "-f", "webm", "-live", "1", "pipe:1"], capture_output=True).stdout
    (d / "scene.webm").write_bytes(octets)
    s = {"id": cid, "cree_utc": "2026-10-28T10:00:00+00:00", "debut_ms": 0, "fin_ms": 5000, "etat": etat,
         "duree_ms": 5000, "options": {"mode": "app"},
         "pistes": {"scene": {"mime": "video/webm", "ext": ".webm", "morceaux": 5, "octets": len(octets)}}}
    (d / "session.json").write_text(json.dumps(s), "utf-8")
    if etat == "terminee":
        (d / f"{cid}.dzclics.json").write_text(json.dumps({"version": 1, "id": cid, "duree_ms": 5000,
            "cadre": {"largeur": 960, "hauteur": 600, "mode": "app"}, "evenements": [
                {"type": "ecran", "t": 0, "ecran": "quick"},
                {"type": "clic", "t": 1200, "x": .4, "y": .3, "bouton": 0, "ecran": "quick",
                 "cible": {"balise": "button", "role": "", "t": "Galerie", "i": ""}, "fiche": "quick.galerie.bouton"},
                {"type": "clic", "t": 3600, "x": .7, "y": .6, "bouton": 0, "ecran": "quick",
                 "cible": {"balise": "button", "role": "", "t": "Lire l'aperçu", "i": ""},
                 "fiche": "montagecap.apercu.lire"}]}), "utf-8")


A, EC = "1" * 16, "4" * 16
fausse_capture(A); fausse_capture(EC, etat="en_cours")
avant_docs = sorted(str(p) for p in (REPO / "docs" / "guide" / "src" / "scenes").rglob("*"))

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("[1] brouillon")
    r = c.get(f"/api/tutoriels/captures/{A}").json()
    check("1.1 proposé : 2 étapes, capture et durée", r["propose"] is True and len(r["brouillon"]["etapes"]) == 2
          and r["capture"]["duree_ms"] == 5000, r)
    b = r["brouillon"]
    b["etapes"][0]["titre"]["fr"] = "Ouvrir la galerie"
    b["etapes"][1]["garde"] = False
    p = c.put(f"/api/tutoriels/captures/{A}", json={"brouillon": b})
    check("1.2 enregistré et relu", p.status_code == 200 and c.get(f"/api/tutoriels/captures/{A}").json()["propose"] is False
          and c.get(f"/api/tutoriels/captures/{A}").json()["brouillon"]["etapes"][0]["titre"]["fr"] == "Ouvrir la galerie", p.text)
    check("1.3 brouillon illisible -> 400", c.put(f"/api/tutoriels/captures/{A}", json={"brouillon": {"version": 9}}).status_code == 400)
    check("1.4 proposer n'écrit rien", c.post(f"/api/tutoriels/captures/{A}/proposer").json()["brouillon"]["etapes"][1]["garde"] is True
          and c.get(f"/api/tutoriels/captures/{A}").json()["brouillon"]["etapes"][1]["garde"] is False)
    check("1.5 en cours 409, inconnue 404, id 400", [c.get(f"/api/tutoriels/captures/{x}").status_code
                                                     for x in (EC, "9" * 16, "xyz")] == [409, 404, 400])
    check("1.6 corps JSON illisible -> 400", c.put(f"/api/tutoriels/captures/{A}", content=b"{x",
                                                   headers={"Content-Type": "application/json"}).status_code == 400)

    print("[2] fabrication")
    f = c.post(f"/api/tutoriels/captures/{A}/fabriquer", json={})
    check("2.1 brouillons fabriqués (étape écartée absente)", f.status_code == 200 and f.json()["scenes"] == 1
          and f.json()["dossier"] == f"tutoriels/{A}" and (T.racine_brouillons() / A / "guide" / "chapitre.fr.html").is_file(), f.text)
    check("2.2 rien publié : docs/guide/src/scenes intact", sorted(str(p) for p in (REPO / "docs" / "guide" / "src" / "scenes").rglob("*")) == avant_docs)
    TR._EN_COURS.add(A)
    check("2.3 fabrication concurrente -> 409", c.post(f"/api/tutoriels/captures/{A}/fabriquer", json={}).status_code == 409)
    TR._EN_COURS.discard(A)
    tout_ecarte = dict(b, etapes=[dict(e, garde=False) for e in b["etapes"]])
    check("2.4 aucune étape gardée -> 409", c.post(f"/api/tutoriels/captures/{A}/fabriquer", json={"brouillon": tout_ecarte}).status_code == 409)

    print("[3] parcours")
    x0 = c.post(f"/api/tutoriels/captures/{A}/parcours", json={})
    x = c.get(f"/api/tutoriels/captures/{A}/parcours")
    check("3.1 export préparé (nom), puis téléchargé par le lien (zip)", x0.status_code == 200 and x0.json()["nom"].endswith(".dzparcours")
          and x.status_code == 200 and x.content[:2] == b"PK" and x0.json()["nom"] in x.headers.get("content-disposition", ""),
          (x0.text, x.status_code, x.headers))
    TR._EN_COURS.add("x" + A)
    check("3.1b export concurrent -> 409", c.post(f"/api/tutoriels/captures/{A}/parcours", json={}).status_code == 409)
    TR._EN_COURS.discard("x" + A)
    check("3.1c un seul export gardé", len(list((T.racine_brouillons() / f"export-{A}").glob("*.dzparcours"))) == 1
          or c.post(f"/api/tutoriels/captures/{A}/parcours", json={}).status_code == 200
          and len(list((T.racine_brouillons() / f"export-{A}").glob("*.dzparcours"))) == 1)
    i = c.post("/api/tutoriels/parcours/importer", content=x.content, headers={"Content-Type": "application/octet-stream"})
    check("3.2 import du corps brut", i.status_code == 200 and T.PID.match(i.json()["id"]), i.text)
    pid = i.json()["id"]
    P = c.get(f"/api/tutoriels/parcours/{pid}").json()
    check("3.3 étapes gardées, action locale", len(P["etapes"]) == 1 and P["etapes"][0]["titre"]["fr"] == "Ouvrir la galerie"
          and P["etapes"][0]["action"]["cible"] == "quick.galerie.bouton", P)
    v = c.get(f"/api/tutoriels/parcours/{pid}/video")
    check("3.4 vidéo", v.status_code == 200 and v.content[:4] == b"\x1a\x45\xdf\xa3" and "webm" in v.headers["content-type"])
    check("3.5 liste", [y["id"] for y in c.get("/api/tutoriels/parcours").json()["parcours"]] == [pid])
    check("3.6 import abîmé 400, corps vide 400", c.post("/api/tutoriels/parcours/importer", content=b"PK\x03\x04abc").status_code == 400
          and c.post("/api/tutoriels/parcours/importer", content=b"").status_code == 400)
    check("3.7 aucun temporaire laissé", sorted(p.name for p in T.racine_parcours().iterdir()) == [pid],
          sorted(p.name for p in T.racine_parcours().iterdir()))
    check("3.8 retrait", c.delete(f"/api/tutoriels/parcours/{pid}").status_code == 200
          and c.get(f"/api/tutoriels/parcours/{pid}").status_code == 404)
    check("3.9 id invalide 400", c.get("/api/tutoriels/parcours/zzz").status_code == 400
          and c.delete("/api/tutoriels/parcours/zzz").status_code == 400)

    print("[5] L10")
    r5 = c.get(f"/api/tutoriels/captures/{EC}", headers={"Accept-Language": "en"})
    check("5.1 refus traduit", r5.status_code == 409 and "finished" in r5.json()["detail"].lower(), r5.text)
    r6 = c.get("/api/tutoriels/parcours/zzz", headers={"Accept-Language": "en"})
    check("5.2 refus neuf traduit", "walkthrough" in r6.json()["detail"].lower(), r6.text)

sys.path.insert(0, str(_ICI))
import _jeton_appareil as _JA                                       # noqa: E402
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    print("[4] hors machine locale")
    codes = [c2.get(f"/api/tutoriels/captures/{A}").status_code, c2.put(f"/api/tutoriels/captures/{A}", json={}).status_code,
             c2.post(f"/api/tutoriels/captures/{A}/proposer").status_code,
             c2.post(f"/api/tutoriels/captures/{A}/fabriquer", json={}).status_code,
             c2.post(f"/api/tutoriels/captures/{A}/parcours", json={}).status_code,
             c2.get(f"/api/tutoriels/captures/{A}/parcours").status_code,
             c2.get("/api/tutoriels/parcours").status_code,
             c2.post("/api/tutoriels/parcours/importer", content=b"x").status_code,
             c2.get("/api/tutoriels/parcours/" + "0" * 16).status_code,
             c2.get("/api/tutoriels/parcours/" + "0" * 16 + "/video").status_code,
             c2.delete("/api/tutoriels/parcours/" + "0" * 16).status_code]
    check("4.1 403 partout", codes == [403] * 11, codes)

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
