# -*- coding: utf-8 -*-
"""Plan-templates T10 / D3 (tache #76 du suivi, PR G, 03/10/2026) — IMPORT FIGMA EDITABLE et EXPORT SVG, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : les images des calques sont importees comme ECHANTILLONS (un appel de plus, dit) ;
export = SVG schematique (et ouverture dans le Vectorlab, PR suivante).
Ce que le plan faisait faux : contraintes en modes anglais (refusees), masques sur des types qui n'en acceptent pas,
images des calques non recuperees, pas de recursion dans les groupes, debordements non bornes, 400 sans jeton.
Le banc ne SORT JAMAIS : les deux pas reseau de figma_import (_get_json, _get_bytes) sont remplaces.
Temoin positif : la base (016f2396) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_templates_figma.py"""
import asyncio, base64, io, json, os, pathlib, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzfig_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "016f2396"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/figma_gabarit.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a pas l'import Figma editable", r0.returncode != 0)
from PIL import Image                                               # noqa: E402
from app.services import figma_import as FI                         # noqa: E402
from app.services import figma_gabarit as FG                        # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
from app.config import settings                                     # noqa: E402
E = TemplateEngine()
IMG = pathlib.Path(settings.images_path)

_png = io.BytesIO(); Image.new("RGB", (8, 8), (255, 0, 0)).save(_png, "PNG"); PNG = _png.getvalue()
_jpg = io.BytesIO(); Image.new("RGB", (8, 8), (0, 0, 255)).save(_jpg, "JPEG"); JPG = _jpg.getvalue()


def bb(x, y, w, h):
    return {"x": 100 + x, "y": 200 + y, "width": w, "height": h}


def solide(r, g, b):
    return [{"type": "SOLID", "color": {"r": r, "g": g, "b": b, "a": 1}}]


CADRE = {"id": "1:2", "type": "FRAME", "name": "Mon reel", "absoluteBoundingBox": bb(0, 0, 1080, 1920), "fills": solide(0.0, 0.0, 0.2),
         "children": [
             {"type": "TEXT", "name": "Titre", "characters": "Bonjour", "absoluteBoundingBox": bb(40, 60, 1000, 120),
              "style": {"fontSize": 72, "fontFamily": "Inter", "textAlignHorizontal": "CENTER"}, "fills": solide(1, 1, 1),
              "constraints": {"horizontal": "LEFT_RIGHT", "vertical": "TOP"}},
             {"type": "GROUP", "name": "Groupe", "absoluteBoundingBox": bb(0, 300, 1080, 900), "children": [
                 {"type": "RECTANGLE", "name": "Photo principale", "absoluteBoundingBox": bb(90, 300, 900, 900), "cornerRadius": 24,
                  "fills": [{"type": "IMAGE", "imageRef": "abc123"}], "constraints": {"horizontal": "CENTER", "vertical": "CENTER"}}]},
             {"type": "ELLIPSE", "name": "Photo principale", "absoluteBoundingBox": bb(780, 1300, 240, 240), "fills": [{"type": "IMAGE", "imageRef": "def456"}]},
             {"type": "RECTANGLE", "name": "Trait", "absoluteBoundingBox": bb(40, 1250, 1000, 6), "fills": solide(0, 0.9, 1)},
             {"type": "RECTANGLE", "name": "Bandeau", "absoluteBoundingBox": bb(0, 1700, 1080, 220), "cornerRadius": 30, "fills": solide(0.5, 0, 0),
              "constraints": {"horizontal": "SCALE", "vertical": "BOTTOM"}},
             {"type": "TEXT", "name": "Signature", "characters": "<b>&co</b>", "absoluteBoundingBox": bb(40, 1760, 600, 80),
              "style": {"fontSize": 40, "fontFamily": "Comic Sans"}, "fills": solide(1, 1, 0)},
             {"type": "VECTOR", "name": "Logo", "absoluteBoundingBox": bb(900, 40, 100, 100), "fills": []},
             {"type": "RECTANGLE", "name": "Deborde", "absoluteBoundingBox": bb(1000, 1500, 200, 100), "fills": solide(0, 1, 0)},
             {"type": "RECTANGLE", "name": "Dehors", "absoluteBoundingBox": bb(2000, 0, 100, 100), "fills": solide(0, 1, 0)},
             {"type": "TEXT", "name": "Cache", "visible": False, "characters": "x", "absoluteBoundingBox": bb(0, 0, 10, 10), "style": {}},
         ]}

APPELS = []
REP = {}


async def faux_json(url, jeton):
    APPELS.append(url)
    for cle, v in REP.items():
        if cle in url:
            return v
    return {"err": "Figma 404: inconnu"}


async def faux_bytes(url):
    APPELS.append(url)
    return {"https://s3/abc": PNG, "https://s3/def": JPG}.get(url, b"")


FI._get_json, FI._get_bytes = faux_json, faux_bytes
URL = "https://www.figma.com/design/KeyABC/Fichier?node-id=1-2"

print("[C] la conversion d'un cadre")
tpl, images, avert = FG.convertir(CADRE)
R = {r["id"]: r for r in tpl["regions"]}
check("C1 la toile = le cadre (1080x1920, son fond) ; les calques en coordonnees DU CADRE ; recursion dans le groupe",
      tpl["canvas"]["width"] == 1080 and tpl["canvas"]["height"] == 1920 and tpl["canvas"]["background_color"] == "#000033"
      and (R["Titre"]["x"], R["Titre"]["y"], R["Titre"]["width"], R["Titre"]["height"]) == (40, 60, 1000, 120) and "Photo_principale" in R, str(list(R)))
check("C2 TEXT -> texte : contenu, taille, couleur, centre, fonte LIVREE reconnue ; contraintes Figma -> modes du reagencement (etirer/debut)",
      R["Titre"]["type"] == "text" and R["Titre"]["text"] == "Bonjour" and R["Titre"]["size"] == 72 and R["Titre"]["color"] == "#ffffff"
      and R["Titre"]["align"] == "center" and R["Titre"]["font"] == "Inter" and R["Titre"]["constraints"] == {"h": "etirer", "v": "debut"}, str(R["Titre"]))
check("C3 remplissage IMAGE -> case image (slot UNIQUE tire du nom, coins arrondis -> masque arrondi, ellipse -> masque ellipse, centre/centre) ; ses images a recuperer",
      R["Photo_principale"]["type"] == "image_slot" and R["Photo_principale"]["slot_name"] == "photo_principale" and R["Photo_principale"]["mask"] == {"shape": "rounded", "radius": 24}
      and R["Photo_principale_2"]["slot_name"] == "photo_principale_2" and R["Photo_principale_2"]["mask"] == {"shape": "ellipse"}
      and R["Photo_principale"]["constraints"] == {"h": "centre", "v": "centre"} and images == [("photo_principale", "abc123"), ("photo_principale_2", "def456")], str(images))
check("C4 rectangle plein fin -> separateur ; grand -> bandeau de fond (SCALE/BOTTOM -> etirer/fin) ; un calque qui deborde est COUPE a la toile",
      R["Trait"]["type"] == "separator" and R["Trait"]["color"] == "#00e6ff" and R["Bandeau"]["type"] == "brand_strip" and R["Bandeau"]["background_color"] == "#800000"
      and R["Bandeau"]["constraints"] == {"h": "etirer", "v": "fin"} and (R["Deborde"]["x"], R["Deborde"]["width"]) == (1000, 80), str(R["Deborde"]))
textes = " | ".join(avert)
check("C5 tout ce qui est saute ou approxime est DIT : fonte non livree, vecteur sans equivalent, calque hors cadre, debordement coupe, coins du bandeau ; le calque cache est ignore",
      "Comic Sans" in textes and "Logo" in textes and "Dehors" in textes and "Deborde" in textes and "Bandeau" in textes and "Cache" not in textes and "Cache" not in R, textes)
check("C6 le gabarit converti est VALIDE pour le moteur (masques seulement sur des cases)", E._validate(tpl) is None)

print("\n[I] l'import (appels simules)")
REP.clear(); REP.update({"/nodes?ids=1:2": {"nodes": {"1:2": {"document": CADRE}}}, "/files/KeyABC/images": {"meta": {"images": {"abc123": "https://s3/abc", "def456": "https://s3/def"}}}})
APPELS.clear()
res = asyncio.run(FG.importer_gabarit(URL, "jeton", E, IMG))
t2 = E.get_template(res["template_id"])
check("I1 un gabarit utilisateur ENREGISTRE (nom du cadre) ; 2 appels API annonces (noeuds + liens d'images), puis les images",
      res["appels"] == 2 and res["name"] == "Mon reel" and t2["name"] == "Mon reel" and len([a for a in APPELS if "api.figma.com" in a]) == 2
      and APPELS[0] == "https://api.figma.com/v1/files/KeyABC/nodes?ids=1:2", str(APPELS))
check("I2 les images vont dans la Bibliotheque (PNG et JPEG reconnus) et deviennent les ECHANTILLONS des cases",
      res["images"] == ["figma_KeyABC_abc123.png", "figma_KeyABC_def456.jpg"] and (IMG / "figma_KeyABC_abc123.png").read_bytes() == PNG
      and t2["metadata"]["samples"] == {"photo_principale": "figma_KeyABC_abc123.png", "photo_principale_2": "figma_KeyABC_def456.jpg"}, str(res))
SANS_IMG = dict(CADRE, children=[CADRE["children"][0]])
REP["/nodes?ids=1:2"] = {"nodes": {"1:2": {"document": SANS_IMG}}}; APPELS.clear()
r2 = asyncio.run(FG.importer_gabarit(URL, "jeton", E, IMG))
check("I3 sans image, UN seul appel (le quota est menage)", r2["appels"] == 1 and len(APPELS) == 1, str(APPELS))
REP["/nodes?ids=1:2"] = {"nodes": {"1:2": {"document": CADRE}}}; REP["/files/KeyABC/images"] = {"meta": {"images": {"abc123": "https://s3/abc"}}}
r3 = asyncio.run(FG.importer_gabarit(URL, "jeton", E, IMG))
check("I4 une image introuvable : la case reste SANS echantillon (mire), c'est dit", any("photo_principale_2" in w and "récupérée" in w for w in r3["warnings"])
      and list((E.get_template(r3["template_id"])["metadata"]["samples"]).keys()) == ["photo_principale"], str(r3["warnings"][-2:]))


def erreur(coro):
    try:
        asyncio.run(coro); return None
    except (ValueError, RuntimeError) as e:
        return f"{type(e).__name__}: {e}"


REP.clear()
es = [erreur(FG.importer_gabarit("https://www.figma.com/design/KeyABC/F", "j", E, IMG)),
      erreur(FG.importer_gabarit(URL, "j", E, IMG))]
REP["/nodes?ids=1:2"] = {"nodes": {}}
es.append(erreur(FG.importer_gabarit(URL, "j", E, IMG)))
REP["/nodes?ids=1:2"] = {"nodes": {"1:2": {"document": dict(CADRE, absoluteBoundingBox=bb(0, 0, 0, 0))}}}
es.append(erreur(FG.importer_gabarit(URL, "j", E, IMG)))
REP["/nodes?ids=1:2"] = {"nodes": {"1:2": {"document": dict(CADRE, children=[CADRE["children"][6]])}}}
es.append(erreur(FG.importer_gabarit(URL, "j", E, IMG)))
check("I5 refus parlants : lien sans calque (ValueError -> 400), Figma en erreur et calque absent (RuntimeError -> 502), cadre de taille nulle, cadre sans calque reprenable (ValueError)",
      es[0].startswith("ValueError") and "node-id" in es[0] and es[1].startswith("RuntimeError") and "404" in es[1] and es[2].startswith("RuntimeError")
      and es[3].startswith("ValueError") and "FRAME" in es[3] and es[4].startswith("ValueError") and "reprenable" in es[4], str(es))

print("\n[S] l'export SVG")
from app.services import template_components as TC                 # noqa: E402
T = E.get_template(res["template_id"])
T["regions"].append({"id": "k1", "type": "component", "component": "cmp_bandeau_titre", "x": 40, "y": 1400, "width": 1000, "height": 220, "z_index": 99,
                     "overrides": {"titre": {"text": "COMPOSANT"}}})
T["regions"].append({"id": "vide", "type": "image_slot", "slot_name": "vide", "slot_label": "Case vide", "x": 0, "y": 0, "width": 100, "height": 100, "z_index": 0})
T["regions"].append({"id": 'bi"z<arre', "type": "text", "text": "F", "font": '"<x>"', "x": 0, "y": 500, "width": 100, "height": 100, "z_index": 1})
TSAVE = dict(T, id="", name="Avec composant")
TID_COMP = E.save_template(TSAVE)
svg = FG.vers_svg(E.resoudre(T), IMG)
racine = ET.fromstring(svg)
ns = "{http://www.w3.org/2000/svg}"
imgs = racine.findall(f"{ns}image")
check("S1 un SVG BIEN FORME a la taille de la toile, son fond ; les cases AVEC echantillon embarquent leur image (base64), la case vide est en pointilles avec son nom",
      racine.get("width") == "1080" and racine.get("height") == "1920" and racine.find(f"{ns}rect").get("fill") == "#000033" and len(imgs) == 2
      and base64.b64decode(imgs[0].get("href").split(",", 1)[1]) == PNG and 'stroke-dasharray' in svg and "Case vide" in svg, svg[:300])
txts = [t.text for t in racine.findall(f"{ns}text")]
check("S2 les textes (echappes), et le COMPOSANT deplie (son titre surcharge) y sont", "Bonjour" in txts and "<b>&co</b>" in txts and "COMPOSANT" in txts, str(txts))

print("\n[W] les routes")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
from app.services import library_index as LI                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
REP.clear(); REP.update({"/nodes?ids=1:2": {"nodes": {"1:2": {"document": CADRE}}}, "/files/KeyABC/images": {"meta": {"images": {"abc123": "https://s3/abc", "def456": "https://s3/def"}}}})
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    settings.FIGMA_TOKEN = ""
    w1 = c.post("/api/layout-templates/import-figma", json={"url": URL})
    settings.FIGMA_TOKEN = "jeton-de-banc"
    w2 = c.post("/api/layout-templates/import-figma", json={"url": URL})
    w3 = c.post("/api/layout-templates/import-figma", json={"url": "https://exemple.com"})
    REP["/nodes?ids=1:2"] = {"err": "Figma 429: quota"}
    w4 = c.post("/api/layout-templates/import-figma", json={"url": URL})
    lst = c.get("/api/images").json()
    tid = w2.json().get("template_id") if w2.status_code == 200 else "x"
    w5 = c.get(f"/api/layout-templates/{tid}/export.svg")
    w6 = c.get("/api/layout-templates/inconnu/export.svg").status_code
    w8 = c.get(f"/api/layout-templates/{TID_COMP}/export.svg")
with TestClient(app, client=("192.168.1.20", 50000), raise_server_exceptions=False) as c2:
    w7 = c2.post("/api/layout-templates/import-figma", json={"url": URL}).status_code
settings.FIGMA_TOKEN = ""
ent = {e["filename"]: e for e in lst.get("images") or []}
check("W1 sans jeton : 503 qui dit comment l'obtenir ; avec : 200 (gabarit, appels, avertissements) ; lien fautif 400 ; Figma en erreur (quota) 502 ; hors machine refuse",
      w1.status_code == 503 and "FIGMA_TOKEN" in w1.json()["detail"] and w2.status_code == 200 and w2.json()["appels"] == 2 and w2.json()["warnings"]
      and w3.status_code == 400 and w4.status_code == 502 and "429" in w4.json()["detail"] and w7 in (401, 403), f"{w1.status_code} {w2.status_code} {w3.status_code} {w4.status_code} {w7}")
check("W2 les images importees sont NOTEES dans la Bibliotheque (source Figma, pas devinee)",
      ent.get("figma_KeyABC_abc123.png", {}).get("source") == "figma" and ent.get("figma_KeyABC_abc123.png", {}).get("source_origin") != "heuristique", str(ent.get("figma_KeyABC_abc123.png")))
check("W3 export.svg : un fichier SVG a telecharger (nom du gabarit) ; 404 inconnu",
      w5.status_code == 200 and w5.headers.get("content-type", "").startswith("image/svg+xml") and 'filename="Mon_reel.svg"' in w5.headers.get("content-disposition", "")
      and w5.text.startswith("<svg") and w6 == 404, f"{w5.status_code} {w5.headers.get('content-disposition')}")
check("W4 la ROUTE exporte le gabarit RESOLU : un composant y est deplie (son titre surcharge), et le SVG reste bien forme meme avec une fonte et un id de region aux guillemets",
      w8.status_code == 200 and "COMPOSANT" in w8.text and ET.fromstring(w8.text) is not None, w8.text[:200])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
