# -*- coding: utf-8 -*-
"""t314 tâche 2 — banc de schema_animation : calques → éléments du nœud Animation, page motion code, graphe Studio.
Aucun réseau, aucun navigateur (la page est seulement contrôlée par motion_code.controler).
Run (depuis backend/) : & $PY tests/test_schema_animation.py"""
import io, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzschanim_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from PIL import Image                                               # noqa: E402
from app.services import schema_animation as SA                     # noqa: E402
from app.services import animation_service as AS, motion_code as MC, studio_graph as SG   # noqa: E402


def png(w, h, c=(10, 10, 10, 255)):
    f = io.BytesIO(); Image.new("RGBA", (w, h), c).save(f, format="PNG"); return f.getvalue()


print("\n[1] format et durée")
check("2a 16:9", SA.aspect_pour(1600, 900) == "16:9")
check("2a 9:16", SA.aspect_pour(900, 1600) == "9:16")
check("2a 1:1", SA.aspect_pour(1000, 1000) == "1:1")
check("2a 4:5", SA.aspect_pour(800, 1000) == "4:5")
check("2a durée bornée", SA.duree_pour(1) == 4 and SA.duree_pour(100) == 30 and SA.duree_pour(10) == 8.5,
      (SA.duree_pour(1), SA.duree_pour(10)))

CALQUES = [
    {"image": "vector_d1_c1.png", "nom": "Forme 1 — Client", "nature": "forme",
     "boite": {"x": 400, "y": 200, "w": 200, "h": 100}, "largeur_png": 400, "hauteur_png": 200},
    {"image": "vector_d1_c2.png", "nom": "Flèche 1", "nature": "fleche",
     "boite": {"x": 600, "y": 240, "w": 300, "h": 20}, "largeur_png": 300, "hauteur_png": 20,
     "queue": {"x": 600, "y": 250}, "pointe": {"x": 900, "y": 250}},
    {"image": "vector_d1_c3.png", "nom": "Étiquette 1 : Client", "nature": "etiquette",
     "boite": {"x": 430, "y": 230, "w": 100, "h": 30}, "largeur_png": 100, "hauteur_png": 30},
]

print("\n[2] éléments")
els = SA.elements(CALQUES, 1000, 500, "16:9", 8)
check("2b un élément image par calque", len(els) == 3 and all(e["type"] == "image" for e in els)
      and [e["filename"] for e in els] == [c["image"] for c in CALQUES], els)
st = [e["start"] for e in els]
check("2b starts strictement croissants", all(a < b for a, b in zip(st, st[1:])), st)
check("2b tout est visible à la fin", all(AS.transform_at(e, 8 - 0.01) is not None for e in els))
check("2b rien n'est visible avant son entrée", AS.transform_at(els[2], max(0, els[2]["start"] - 0.05)) is None)
fin = AS.transform_at(els[0], 7.9)
check("2c centre du document → 50 %", abs(fin["x"] - 50) < 0.01 and abs(fin["y"] - 50) < 0.01, fin)
W, H = AS._wh("16:9")
f = 0.9 * min(W / 1000, H / 500)
check("2c échelle = ajustement × boîte / png (moitié)", abs(fin["scale"] - f * 200 / 400) < 1e-3, (fin["scale"], f / 2))
k = els[1]["keyframes"]
check("2d flèche : départ décalé vers sa queue, arrivée en place", k[0]["x"] < k[-1]["x"] and k[0]["opacity"] == 0
      and k[-1]["opacity"] == 1, k)
check("2d bornes du chorégraphe", all(0 <= c["x"] <= 100 and 0 <= c["y"] <= 100 and 0 <= c["opacity"] <= 1
                                      for e in els for c in e["keyframes"]))
try:
    SA.elements([], 1000, 500, "16:9", 8); check("2g aucun calque refusé", False)
except ValueError:
    check("2g aucun calque refusé", True)

print("\n[3] la page motion code")
avec = [dict(c, octets=png(c["largeur_png"], c["hauteur_png"])) for c in CALQUES]
avec[0]["nom"] = "location fetch( http://x.y"
page = SA.page(avec, 1000, 500, "16:9", 8, fond="#FFFFFF")
check("2e la page passe le contrôle du bac à sable", MC.controler(page) == [], MC.controler(page))
check("2e définit dzFrame et ne porte aucune URL", "dzFrame" in page and "http" not in page)
check("2e couleur de fond validée", "#FFFFFF" in page and "javascript" not in SA.page(avec, 1000, 500, "16:9", 8,
                                                                                         fond="red;}</style><script>"))

print("\n[4] le graphe")
g = SA.graphe("Mon schéma", els, "mc-0123456789abcdef", "Client\nServeur", "16:9", 8)
gv, avert, manques = SG.valider(g)
check("2f graphe valide sans avertissement", not avert and len(gv["edges"]) == 3, avert)
check("2f Animation en tête", g["nodes"][0]["id"] == "an1" and g["nodes"][0]["type"] == "Animation", g["nodes"][0])
an = g["nodes"][0]["props"]
check("2f props Animation", an["elements"] == els and an["durationS"] == 8 and an["script"] == "Client\nServeur"
      and an["selected"] == 0)
mc = next(n for n in g["nodes"] if n["type"] == "MotionCode")
check("2f MotionCode porte la page", mc["props"]["pageId"] == "mc-0123456789abcdef")
rn = next(n for n in g["nodes"] if n["type"] == "Render")
check("2f Render au format", rn["props"]["format"] == "16:9" and rn["props"]["name"], rn)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
