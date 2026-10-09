"""t128 : l'éditeur de courbe de Bézier du rack VFX (frontend/patches/vfxrack.js). La couche vit dans la portée du
bundle (r.jsx, x.useState) : on l'évalue sous node avec des bouchons et on interroge ses fonctions PURES — lecture et
écriture de « cubic-bezier(a,b,c,d) » (la forme que animation_service.ease lit déjà), point de départ d'un preset
(miroir EXACT de animation_service._BEZIER), conversion pointeur -> courbe, tracé SVG."""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from app.services.animation_service import _BEZIER, ease

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NODE = shutil.which("node")
if not NODE:
    print("SKIP: node introuvable")
    sys.exit(0)

HARNAIS = r"""
const fs = require("fs");
const src = fs.readFileSync(process.argv[1], "utf8");
const win = { addEventListener() {}, DzVfx: null }, doc = { addEventListener() {}, hidden: false };
const f = new Function("r", "x", "window", "document", "fetch", "localStorage", src +
  "\n;return { vfxBezLire, vfxBezEcrire, vfxBezDepart, vfxBezPoint, vfxBezChemin, VFX_BEZ_GEO, VFX_EASES, VFX_BEZ_PRESETS };");
const o = f({ jsx() {}, jsxs() {} }, { useState(v) { return [v, () => {}]; }, useEffect() {}, useRef() { return {}; } },
  win, doc, () => Promise.reject(), { getItem() { return null; }, setItem() {} });
const G = o.VFX_BEZ_GEO;
const res = {
  lire: ["cubic-bezier(0.42,0,0.58,1)", "cubic-bezier( 0.1 , -0.5, .9,1.6 )", "cubic-bezier(0.1,0.2,0.3)", "smooth",
         "cubic-bezier(a,0,1,1)", "cubic-bezier(1.5,0,0.2,1)", null, "cubic-bezier(0.1, ,0.3,1)"].map(o.vfxBezLire),
  ecrire: [[0.42, 0, 0.58, 1], [0.123456, -3, 1.7, 5], [-1, 0.5, 2, 0.5]].map(o.vfxBezEcrire),
  depart: Object.fromEntries(["smooth", "linear", "easeInOutSine", "anticipate", "overshoot", "easeOutBounce", "cubic-bezier(0.2,0.3,0.4,0.5)"].map((n) => [n, o.vfxBezDepart(n)])),
  presets: o.VFX_BEZ_PRESETS,
  geo: G,
  point: [o.vfxBezPoint(G.m, G.m + G.c), o.vfxBezPoint(G.m + G.c, G.m), o.vfxBezPoint(G.m + G.c / 2, G.m + G.c / 4), o.vfxBezPoint(-50, 9999), o.vfxBezPoint(9999, -9999)],
  chemin: o.vfxBezChemin([0.42, 0, 0.58, 1]),
  eases: o.VFX_EASES.map((e) => e[0]),
};
process.stdout.write(JSON.stringify(res));
"""

# t144 : la couche passe par dzT (traduction L4) ; le banc exécute/lit son texte français d'avant la traduction
# (test_i18n_l4 garantit qu'elle se défait exactement)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _i18n_l1_aide as AIDE  # noqa: E402
import tempfile  # noqa: E402
_TMP = tempfile.mkdtemp(prefix="dzbez_")
_COUCHE = os.path.join(_TMP, "vfxrack.js")
with open(os.path.join(RACINE, "frontend", "patches", "vfxrack.js"), "rb") as _fh:
    _src = AIDE.couche_avant_i18n_l4(_fh.read().decode("utf-8"), "vfxrack")
with open(_COUCHE, "wb") as _fh:
    _fh.write(_src.encode("utf-8"))
r = subprocess.run([NODE, "-e", HARNAIS, _COUCHE], capture_output=True, text=True, encoding="utf-8")
shutil.rmtree(_TMP, ignore_errors=True)
if r.returncode:
    print("ECHEC du harnais node :", r.stderr[-800:])
    sys.exit(1)
R = json.loads(r.stdout)
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


L = R["lire"]
check("lire : la forme canonique", L[0] == [0.42, 0, 0.58, 1], L[0])
check("lire : espaces, .9, y hors [0,1] admis", L[1] == [0.1, -0.5, 0.9, 1.6], L[1])
check("lire : trois nombres, un nom, une lettre, x hors [0,1], rien, un nombre vide -> null", L[2:] == [None] * 6, L[2:])
E = R["ecrire"]
check("écrire : la forme que le backend lit", E[0] == "cubic-bezier(0.42,0,0.58,1)" and abs(ease(E[0], 0.5) - 0.5) < 1e-6, E[0])
check("écrire : 2 décimales, x borné à [0,1], y à [-1,2]", E[1] == "cubic-bezier(0.12,-1,1,2)" and E[2] == "cubic-bezier(0,0.5,1,0.5)", E[1:])
P = R["presets"]
check("presets : miroir EXACT de animation_service._BEZIER (+ linéaire)",
      {k: tuple(v) for k, v in P.items() if k != "linear"} == {k: tuple(v) for k, v in _BEZIER.items()} and P.get("linear") == [0, 0, 1, 1], P)
D = R["depart"]
check("départ : un preset Bézier part de SES poignées, un Bézier écrit des siennes",
      D["smooth"] == list(_BEZIER["smooth"]) and D["overshoot"] == list(_BEZIER["overshoot"])
      and D["cubic-bezier(0.2,0.3,0.4,0.5)"] == [0.2, 0.3, 0.4, 0.5], D)
check("départ : une courbe sans poignées (rebond) part de la courbe douce symétrique", D["easeOutBounce"] == [0.42, 0, 0.58, 1], D["easeOutBounce"])
G = R["geo"]
pt = R["point"]
check("pointeur : coin bas-gauche = (0,0), haut-droit = (1,1), le milieu en haut au quart = (0.5,0.75)",
      pt[0] == [0, 0] and pt[1] == [1, 1] and pt[2] == [0.5, 0.75], pt[:3])
check("pointeur : x borné à [0,1], y à la zone visible", pt[3][0] == 0 and pt[4][0] == 1 and pt[3][1] >= -1 and pt[4][1] <= 2
      and pt[3][1] == round(-G["m"] / G["c"], 2) and pt[4][1] == round(1 + G["m"] / G["c"], 2), pt[3:])
c = R["chemin"]
x0, y0 = G["m"], G["m"] + G["c"]
check("tracé : part de (0,0) et finit en (1,1), poignées au bon endroit",
      c.startswith(f"M{x0} {y0} C") and c.endswith(f"{G['m'] + G['c']} {G['m']}")
      and f"{G['m'] + 0.42 * G['c']:g} {y0}" in c, c)
check("la liste déroulante garde ses presets ET propose la courbe éditable", R["eases"][:10] == ["smooth", "linear", "easeIn", "easeOut", "easeInOut",
      "easeInOutSine", "anticipate", "overshoot", "easeOutBack", "easeOutBounce"] and R["eases"][-1] == "bezier", R["eases"])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
