# -*- coding: utf-8 -*-
"""t314 tâche 3 — banc des routes /api/schema (devis, analyser, animation).
fal passe par les coutures de matte_service (_upload, _fal_subscribe, _download) remplacées ; l'OCR par
scan_ocr.lire_page remplacée ; jamais de réseau ni de PowerShell.
Run (depuis backend/) : & $PY tests/test_schema_routes.py"""
import io, json, math, os, pathlib, sqlite3, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzschrt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("FAL_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()
JOURNAL = []
logger.add(lambda m: JOURNAL.append(str(m)), level="DEBUG")

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")

from fastapi.testclient import TestClient                          # noqa: E402
from PIL import Image, ImageDraw                                    # noqa: E402
from app.config import settings                                     # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import matte_service as MT, scan_ocr as O, motion_code as MC, studio_graph as SG   # noqa: E402
from app.api import routes as R                                     # noqa: E402

SECRET = "Licorne"
OCR = {"mode": "ok", "appels": 0}


def faux_ocr(octets, langue="fr", **k):
    OCR["appels"] += 1
    if OCR["mode"] == "absent":
        raise O.ScanIndisponible("La lecture de texte locale n'existe que sous Windows.")
    if OCR["mode"] == "bizarre":
        raise OSError("disque")
    return {"langue": langue, "angle": 0, "largeur": 800, "hauteur": 500,
            "lignes": [{"texte": SECRET, "mots": [{"texte": SECRET, "x": 95, "y": 232, "l": 90, "h": 26}]}]}


O.lire_page = faux_ocr
FAL = {"sub": []}


async def _up(p):
    return "http://fal.test/in"


async def _sub(endpoint, arguments):
    FAL["sub"].append(endpoint)
    return {"image": {"url": "http://fal.test/out.png"}}


async def _dl(url, dest):
    im = Image.new("RGBA", (800, 500), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((60, 200, 220, 290), outline=(0, 0, 0, 255), width=4)
    d.rectangle((560, 200, 720, 290), outline=(0, 0, 0, 255), width=4)
    im.save(dest, format="PNG")


MT._upload, MT._fal_subscribe, MT._download = _up, _sub, _dl


def schema(bariole=False):
    im = Image.new("RGB", (800, 500), (255, 255, 255))
    d = ImageDraw.Draw(im)
    if bariole:
        im.putdata([((x * 37) % 256, (y * 91) % 256, ((x + y) * 13) % 256) for y in range(500) for x in range(800)])
        return _png(im)
    d.rectangle((60, 200, 220, 290), outline=(20, 20, 30), width=4)
    d.rectangle((560, 200, 720, 290), outline=(20, 20, 30), width=4)
    d.line((230, 245, 550, 245), fill=(20, 20, 30), width=4)
    d.polygon([(550, 245), (530, 236), (530, 254)], fill=(20, 20, 30))
    d.rectangle((95, 232, 185, 258), fill=(20, 20, 30))
    return _png(im)


def _png(im):
    f = io.BytesIO(); im.save(f, format="PNG"); return f.getvalue()


def envoi(c, octets, **champs):
    return c.post("/api/schema/analyser", files={"image": ("schema.png", octets, "image/png")},
                  data={k: str(v) for k, v in champs.items()})


def depenses():
    con = sqlite3.connect(str(_tmp / "t.db"))
    try:
        return con.execute("select count(*) from depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        con.close()


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[1] devis")
    r = c.get("/api/schema/devis")
    j = r.json()
    ids = [m["id"] for m in j.get("modeles", [])]
    check("devis : défaut local-chroma, gratuit en tête", r.status_code == 200 and j["defaut"] == "local-chroma"
          and ids[0] == "local-chroma" and j["modeles"][0]["usd"] == 0, j)
    check("devis : modèles fal payants, sans ceux à sujet, indisponibles sans clé", "bria-rmbg" in ids
          and "sam3-sujet" not in ids and all(m["usd"] > 0 or m["voie"] == "local" or m["id"] in ("birefnet-v2", "pixelcut", "feynobg")
                                              for m in j["modeles"])
          and next(m for m in j["modeles"] if m["id"] == "bria-rmbg")["disponible"] is False, j)

    print("\n[2] analyser (local)")
    r = envoi(c, schema())
    j = r.json()
    nat = [e["nature"] for e in j.get("elements", [])]
    check("3b local-chroma : 200, formes + flèche + étiquette", r.status_code == 200 and nat.count("forme") == 2
          and nat.count("fleche") == 1 and nat.count("etiquette") == 1, (r.status_code, nat, r.text[:200]))
    f = next(e for e in j["elements"] if e["nature"] == "forme")
    check("3b png en data URL décodable", f["png"].startswith("data:image/png;base64,")
          and Image.open(io.BytesIO(__import__("base64").b64decode(f["png"].split(",", 1)[1]))).mode == "RGBA")
    check("3b aucun appel fal, gratuit, lien rendu", FAL["sub"] == [] and j["usd"] == 0 and len(j["liens"]) == 1, j.get("liens"))
    r = c.post("/api/schema/analyser", files={"image": ("s.png", schema(True), "image/png")},
               headers={"Accept-Language": "en"})
    check("3c fond bariolé : 422 traduit", r.status_code == 422 and "background" in r.text.lower(), r.text)
    r = envoi(c, schema(), langue="zz")
    check("langue inconnue : 400", r.status_code == 400)
    r = envoi(c, b"pas une image")
    check("fichier non image : 4xx sans 500", 400 <= r.status_code < 500, r.status_code)
    OCR["mode"] = "absent"
    r = envoi(c, schema())
    check("3g OCR indisponible : 200 + avertissement, aucune étiquette", r.status_code == 200
          and "ocr_indisponible" in r.json()["avertissements"]
          and not any(e["nature"] == "etiquette" for e in r.json()["elements"]), r.text[:300])
    OCR["mode"] = "ok"

    print("\n[3] analyser (fal, payant)")
    d0 = depenses()
    r = envoi(c, schema(), detourage="bria-rmbg", max_usd="1")
    check("3e fal sans clé : 503 nommant FAL_KEY, aucune dépense, aucun appel", r.status_code == 503 and "FAL_KEY" in r.text
          and depenses() == d0 and FAL["sub"] == [], (r.status_code, r.text[:200]))
    settings.FAL_KEY = "cle-de-banc"
    r = envoi(c, schema(), detourage="bria-rmbg")
    check("3d fal sans accord : 409 avec le devis, aucun appel", r.status_code == 409 and FAL["sub"] == []
          and r.json()["detail"]["usd"] > 0 and depenses() == d0, r.text[:200])
    r = envoi(c, schema(), detourage="bria-rmbg", max_usd="0.001")
    check("3d fal accord trop bas : 409", r.status_code == 409 and FAL["sub"] == [])
    r = envoi(c, schema(), detourage="sam3-sujet", max_usd="1")
    check("modèle à sujet : 400", r.status_code == 400 and FAL["sub"] == [], r.text[:200])
    r = envoi(c, schema(), detourage="bria-rmbg", max_usd="1")
    j = r.json()
    check("3f fal accepté : 200, un appel, une dépense, image détourée utilisée", r.status_code == 200
          and FAL["sub"] == ["fal-ai/bria/background/remove"] and depenses() == d0 + 1 and j["usd"] > 0
          and "fond_estime" not in j["avertissements"]
          and [e["nature"] for e in j["elements"]].count("forme") == 2, (r.status_code, r.text[:300]))
    async def _panne(endpoint, arguments):
        FAL["sub"].append(endpoint)
        raise ConnectionError("réseau coupé")
    MT._fal_subscribe = _panne
    r = envoi(c, schema(), detourage="bria-rmbg", max_usd="1")
    check("fal en panne réseau : 502 qui nomme le modèle, jamais 500",
          r.status_code == 502 and "bria-rmbg" in r.text and "ConnectionError" in r.text, (r.status_code, r.text[:200]))
    MT._fal_subscribe = _sub
    OCR["mode"] = "bizarre"
    r = envoi(c, schema())
    check("OCR en erreur imprévue : 200 + ocr_indisponible", r.status_code == 200
          and "ocr_indisponible" in r.json()["avertissements"], r.text[:200])
    OCR["mode"] = "ok"
    settings.FAL_KEY = ""

    print("\n[4] animation")
    for n, (w, h) in enumerate(((160, 90), (320, 20), (90, 26)), 1):
        Image.new("RGBA", (w, h), (0, 0, 0, 255)).save(settings.images_path / f"vector_d1_cc{n}.png")
    corps = {"doc_id": "d1", "nom": "Mon schéma", "largeur": 800, "hauteur": 500, "fond": "#FFFFFF",
             "calques": [{"image": "vector_d1_cc1.png", "nom": "Forme 1", "nature": "forme",
                          "boite": {"x": 60, "y": 200, "w": 160, "h": 90}},
                         {"image": "vector_d1_cc2.png", "nom": "Flèche 1", "nature": "fleche",
                          "boite": {"x": 230, "y": 235, "w": 320, "h": 20},
                          "queue": {"x": 230, "y": 245}, "pointe": {"x": 550, "y": 245}},
                         {"image": "vector_d1_cc3.png", "nom": "Étiquette 1 : Client", "nature": "etiquette",
                          "boite": {"x": 95, "y": 232, "w": 90, "h": 26}}]}
    r = c.post("/api/schema/animation", json=corps)
    j = r.json()
    check("3h 200, graphe valide", r.status_code == 200 and not SG.valider(j["graph"])[1], r.text[:300])
    an = j["graph"]["nodes"][0]
    check("3h Animation : fond + un élément par calque", an["type"] == "Animation"
          and [e["filename"] for e in an["props"]["elements"]] == ["vector_d1_fond.png", "vector_d1_cc1.png",
                                                                  "vector_d1_cc2.png", "vector_d1_cc3.png"]
          and (settings.images_path / "vector_d1_fond.png").is_file(), an["props"]["elements"][:1])
    check("3h format 16:9 et script des noms", j["aspect"] == "16:9" and "Forme 1" in an["props"]["script"])
    check("3h page enregistrée et saine", MC.controler(MC.lire(j["page_id"])) == [])
    g = R._studio_graphs_dir() / f"{j['graph_id']}.json"
    check("3h graphe au magasin du Studio, id stable", g.is_file() and j["graph"]["id"] == j["graph_id"]
          and json.loads(g.read_text(encoding="utf-8"))["name"] == "Mon schéma — schéma animé" == j["nom_graphe"], g)
    r2 = c.post("/api/schema/animation", json=corps)
    check("3h renvoi : même id de graphe", r2.json()["graph_id"] == j["graph_id"])
    bad = dict(corps, calques=[dict(corps["calques"][0], image="absente.png")])
    r = c.post("/api/schema/animation", json=bad, headers={"Accept-Language": "en"})
    check("3i image absente : 400 qui la nomme", r.status_code == 400 and "absente.png" in r.text, r.text)
    for cas, b in (("doc_id", dict(corps, doc_id="../x")), ("zéro calque", dict(corps, calques=[])),
                   ("boîte", dict(corps, calques=[dict(corps["calques"][0], boite={"x": 1})])),
                   ("taille", dict(corps, largeur=-1))):
        check(f"refus {cas} : 400", c.post("/api/schema/animation", json=b).status_code == 400)
    check("corps non JSON : 400", c.post("/api/schema/animation", content=b"{x").status_code == 400)

print("\n[5] hors machine locale, journaux")
import _jeton_appareil as _JA                                       # noqa: E402
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    check("3a devis -> 403", c2.get("/api/schema/devis").status_code == 403)
    check("3a analyser -> 403", c2.post("/api/schema/analyser",
                                        files={"image": ("s.png", schema(), "image/png")}).status_code == 403)
    check("3a animation -> 403", c2.post("/api/schema/animation", json={}).status_code == 403)
check("3j journaux sans le texte lu", not any(SECRET in l for l in JOURNAL) and any("schema_routes" in l for l in JOURNAL))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
