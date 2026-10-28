# -*- coding: utf-8 -*-
"""t314 tâche 1 — banc de schema_calques : séparer, classer, relier et ordonner les éléments d'un schéma.
Schémas dessinés par Pillow (aucun fichier, aucun réseau) ; l'OCR est remplacé par des lignes données à la main.
Run (depuis backend/) : & $PY tests/test_schema_calques.py"""
import io, math, os, pathlib, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzschcal_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from PIL import Image, ImageDraw                                   # noqa: E402
from app.services import schema_calques as SC                       # noqa: E402

BLANC, NOIR = (255, 255, 255), (20, 20, 30)


def fond(w=800, h=500):
    im = Image.new("RGB", (w, h), BLANC)
    return im, ImageDraw.Draw(im)


def boite(d, x, y, w=160, h=90, plein=False, ep=4):
    if plein:
        d.rectangle((x, y, x + w, y + h), fill=(40, 90, 200))
    else:
        d.rectangle((x, y, x + w, y + h), outline=NOIR, width=ep)


def fleche(d, x1, y1, x2, y2, pointe=True, deux=False, ep=4, t=22):
    d.line((x1, y1, x2, y2), fill=NOIR, width=ep)
    def tete(xa, ya, xb, yb):
        a = math.atan2(yb - ya, xb - xa)
        p = [(xb, yb), (xb - t * math.cos(a - 0.45), yb - t * math.sin(a - 0.45)),
             (xb - t * math.cos(a + 0.45), yb - t * math.sin(a + 0.45))]
        d.polygon(p, fill=NOIR)
    if pointe:
        tete(x1, y1, x2, y2)
    if deux:
        tete(x2, y2, x1, y1)


def ligne(texte, x, y, l, h):
    return {"texte": texte, "mots": [{"texte": texte, "x": x, "y": y, "l": l, "h": h}]}


def par_nature(r, n):
    return [e for e in r["elements"] if e["nature"] == n]


def ordre(r):
    return [e["id"] for e in sorted(r["elements"], key=lambda e: e["ordre"])]


def boite_contient(e, x, y):
    b = e["boite"]
    return b["x"] <= x <= b["x"] + b["w"] and b["y"] <= y <= b["y"] + b["h"]


def forme_en(r, x, y):
    return next(e for e in par_nature(r, "forme") if boite_contient(e, x, y))


print("\n[1] deux formes et une flèche")
im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 230, 245, 550, 245)
r = SC.analyser(im, [])
F, L = par_nature(r, "forme"), par_nature(r, "fleche")
check("1a 2 formes, 1 flèche", len(F) == 2 and len(L) == 1, [e["nature"] for e in r["elements"]])
A, B = forme_en(r, 100, 210), forme_en(r, 600, 210)
check("1a flèche dirigée A→B", L and L[0].get("dirigee") is True and L[0].get("de") == A["id"] and L[0].get("vers") == B["id"],
      L and {k: L[0].get(k) for k in ("dirigee", "de", "vers")})
check("1a lien rendu", r["liens"] == [{"fleche": L[0]["id"], "de": A["id"], "vers": B["id"]}], r["liens"])
check("1a ordre A, flèche, B", ordre(r) == [A["id"], L[0]["id"], B["id"]], ordre(r))
check("1a pointe à droite", L[0]["pointe"]["x"] > L[0]["queue"]["x"], (L[0].get("queue"), L[0].get("pointe")))
check("1a fond estimé signalé", "fond_estime" in r["avertissements"], r["avertissements"])

im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 550, 245, 230, 245)
r = SC.analyser(im, [])
A, B = forme_en(r, 100, 210), forme_en(r, 600, 210)
L = par_nature(r, "fleche")
check("1b sens inverse : B→A, ordre B, flèche, A", L and L[0]["de"] == B["id"] and L[0]["vers"] == A["id"]
      and ordre(r) == [B["id"], L[0]["id"], A["id"]], (ordre(r), L and (L[0].get("de"), L[0].get("vers"))))

print("\n[2] étiquettes")
im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 230, 245, 550, 245)
d.rectangle((95, 232, 185, 258), fill=NOIR)          # « glyphes » de Client (un pavé sombre)
d.rectangle((590, 232, 690, 258), fill=NOIR)
lignes = [ligne("Client", 95, 232, 90, 26), ligne("Serveur", 590, 232, 100, 26)]
r = SC.analyser(im, lignes)
E = par_nature(r, "etiquette")
F = par_nature(r, "forme")
check("1c 2 étiquettes, 2 formes (glyphes absorbés)", len(E) == 2 and len(F) == 2, [e["nature"] for e in r["elements"]])
A, B = forme_en(r, 70, 210), forme_en(r, 700, 210)
eC = next((e for e in E if e["texte"] == "Client"), None)
check("1c parent de Client = A", eC and eC["parent"] == A["id"], eC)
check("1c nom de la forme", A["nom"] == "Forme 1 — Client", A["nom"])
fl = par_nature(r, "fleche")[0]
check("1c nom de la flèche", fl["nom"] == "Flèche 1 : Client → Serveur", fl["nom"])
o = ordre(r)
check("1c étiquette juste après son parent", o.index(eC["id"]) == o.index(A["id"]) + 1, o)
check("1c couleur du texte sombre", eC.get("couleur", "#FFFFFF")[1:3] < "80", eC.get("couleur"))
check("1c étiquette sans png, avec lignes", "png" not in eC and eC["lignes"][0]["texte"] == "Client", eC.keys())

print("\n[3] formes pleines, traits sans pointe")
im, d = fond()
boite(d, 60, 200, plein=True)
r = SC.analyser(im, [])
check("1d rectangle plein = forme", [e["nature"] for e in r["elements"]] == ["forme"], r["elements"])
im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 230, 245, 550, 245, pointe=False)
r = SC.analyser(im, [])
L = par_nature(r, "fleche")
check("1e trait sans pointe : flèche non dirigée, aucun lien", L and L[0]["dirigee"] is False and r["liens"] == [],
      (L, r["liens"]))
im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 230, 245, 550, 245, deux=True)
r = SC.analyser(im, [])
L = par_nature(r, "fleche")
check("1e double pointe : non dirigée", L and L[0]["dirigee"] is False and r["liens"] == [], L)

print("\n[4] l'ordre suit les flèches")
im, d = fond(900, 300)
boite(d, 700, 100, 140, 80); boite(d, 380, 100, 140, 80); boite(d, 60, 100, 140, 80)
fleche(d, 690, 140, 530, 140)        # A (droite) → B (milieu)
fleche(d, 370, 140, 210, 140)        # B → C (gauche)
r = SC.analyser(im, [])
A, B, C = forme_en(r, 710, 110), forme_en(r, 390, 110), forme_en(r, 70, 110)
formes_o = [i for i in ordre(r) if i in (A["id"], B["id"], C["id"])]
check("1f A, B, C (suit les flèches, pas la lecture)", formes_o == [A["id"], B["id"], C["id"]], (formes_o, A["id"]))

im, d = fond(800, 500)
boite(d, 60, 60); boite(d, 560, 300)
fleche(d, 230, 100, 600, 290)
fleche(d, 545, 385, 150, 160)
r = SC.analyser(im, [])
F = par_nature(r, "forme")
o = ordre(r)
check("1g cycle : deux formes une fois chacune, haut-gauche d'abord", len(F) == 2 and len(o) == len(set(o))
      and o[0] == forme_en(r, 70, 70)["id"], o)

im, d = fond()
d.ellipse((100, 100, 250, 250), outline=NOIR, width=5)
d.rectangle((500, 300, 650, 420), fill=(200, 60, 60))
d.ellipse((520, 60, 640, 180), fill=(60, 160, 60))
r = SC.analyser(im, [])
o = [e["boite"] for e in sorted(r["elements"], key=lambda e: e["ordre"])]
check("1h sans flèche : 3 formes, ordre de lecture", len(r["elements"]) == 3 and r["liens"] == []
      and o[0]["y"] < 120 and o[-1]["y"] > 250, o)

print("\n[5] bornes et découpes")
im, d = fond(1000, 1000)
for i in range(9):
    for j in range(6):
        d.rectangle((30 + i * 105, 30 + j * 160, 90 + i * 105, 120 + j * 160), fill=(30 + i * 20, 40, 90 + j * 20))
r = SC.analyser(im, [])
check("1i au plus 40 éléments dont « details »", len(r["elements"]) <= SC.MAX_ELEMENTS
      and len(par_nature(r, "details")) == 1, (len(r["elements"]), len(par_nature(r, "details"))))
im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 230, 245, 550, 245)
r = SC.analyser(im, [])
A = forme_en(r, 100, 210)
p = Image.open(io.BytesIO(A["png"]))
check("1j png RGBA de la taille de la boîte", p.mode == "RGBA" and p.size == (A["boite"]["w"], A["boite"]["h"]), (p.mode, p.size, A["boite"]))
cx, cy = p.size[0] // 2, p.size[1] // 2
check("1j centre d'un rectangle contour transparent", p.getpixel((cx, cy))[3] == 0, p.getpixel((cx, cy)))
check("1j bord opaque", p.getpixel((1, cy))[3] > 0 or p.getpixel((2, cy))[3] > 0, p.getpixel((1, cy)))
L = par_nature(r, "fleche")[0]
q = Image.open(io.BytesIO(L["png"]))
check("1j la flèche ne porte pas les rectangles", q.size[0] < 400 and q.size[1] < 60, q.size)

m, est = SC.masque_de(Image.new("RGBA", (50, 50), (0, 0, 0, 0)))
check("1k image transparente : masque lu, non estimé", est is False and m.mode == "L")
im, d = fond(); boite(d, 60, 200)
m, est = SC.masque_de(im)
check("1k opaque fond blanc : estimé", est is True)
bari = Image.new("RGB", (200, 200))
bari.putdata([((x * 37) % 256, (y * 91) % 256, ((x + y) * 13) % 256) for y in range(200) for x in range(200)])
try:
    SC.masque_de(bari); check("1k fond bariolé refusé", False)
except ValueError as e:
    check("1k fond bariolé refusé", str(e) == "fond_non_uni", e)

im, d = fond()
boite(d, 60, 200); boite(d, 560, 200)
fleche(d, 230, 245, 550, 245)
r = SC.analyser(im, [ligne("Client", 95, 232, 90, 26)], langue="en")
A = forme_en(r, 70, 210)
check("1l noms EN", A["nom"] == "Shape 1 — Client" and par_nature(r, "fleche")[0]["nom"].startswith("Arrow 1"),
      (A["nom"], par_nature(r, "fleche")[0]["nom"]))

im, d = fond(3000, 1800)
for k in range(4):
    boite(d, 100 + k * 700, 700, 450, 300, ep=12)
for k in range(3):
    fleche(d, 600 + k * 700, 850, 750 + k * 700, 850, ep=12, t=60)
t0 = time.perf_counter()
r = SC.analyser(im, [])
dt = time.perf_counter() - t0
check(f"1m 3000 px en {dt:.2f} s (< 5 s)", dt < 5 and len(par_nature(r, "forme")) == 4 and len(r["liens"]) == 3,
      ([e["nature"] for e in r["elements"]], r["liens"]))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
