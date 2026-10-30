# -*- coding: utf-8 -*-
"""t377 (30/10/2026) — Assets 2D : une illustration par carte d'outil, et l'onglet en français ET en anglais
(maillon de queue dza2d, après dzga3d).

Ce que le banc prouve :
  1. le bundle : plus aucun texte français en dur dans DzAssets2D (« Choisir un outil », les quatre phrases,
     « Ouvrir », les infobulles du guide) ; chaque clé a2d.* employée existe, FR et EN non vides, mêmes variables,
     aucune orpheline ; le français déjà affiché est repris À L'IDENTIQUE ;
  2. les illustrations : quatre WebP 640 × 360 dans les statiques (frontend/dist/assets2d/cartes/<outil>.webp),
     légers (< 40 Ko) ;
  3. DzAssets2D JOUÉ sous node en FR puis en EN : titre, phrases, « Ouvrir » / « Open », infobulles ; chaque carte
     porte son image, chargée paresseusement (`loading="lazy"`), décorative (`alt=""`), l'icône restant dessous ;
  4. le maillon : appliqué, inverse avant_dza2d exact, appelé EN TÊTE de avant_dzga3d, hors couche, sonde de
     dzga3d, aucun .bak laissé, comptes figés intacts, dictionnaire assemblé à jour.
Run : & $PY tests/test_assets2d_cartes_ecran.py   (depuis backend/)
"""
import json, os, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))
import _i18n_l1_aide as AIDE                                         # noqa: E402

try:
    import patch_bundle_dza2d as M                                   # noqa: E402
except Exception as e:                                               # le banc rougit, ne meurt pas
    M = None
    print(f"  (import du maillon impossible : {e!r})")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUN = BUNDLE.read_bytes().decode("utf-8")
_d = RACINE / "frontend" / "shared" / "i18n" / "a2d.json"
DICO = json.loads(_d.read_text(encoding="utf-8")) if _d.exists() else {}
i0, i1 = BUN.find("function DzAssets2D("), BUN.find("function DzGameAssetsHub(")
FN = BUN[i0:i1] if 0 < i0 < i1 else ""
OUTILS = ["sprites", "tiles", "pixel", "cards"]

print("\n[1] le bundle")
ANCIENS = ['"Choisir un outil"', 'p:"Une image ou une vidéo', 'p:"Tuiles sans raccord', 'p:"Retouche au pixel',
           'p:"Cartes à jouer', 'children:"Ouvrir"', '"Ouvrir "+', '"Le chapitre « "', '"Pas encore de chapitre « "']
reste = [a for a in ANCIENS if a in FN]
check("1.1 DzAssets2D : plus aucun texte français en dur", FN and not reste, str(reste))
employees = set(re.findall(r'dzT\("(a2d\.[a-z0-9_.]+)"', FN))
check("1.2 chaque clé employée existe, FR et EN non vides", employees and all(
    k in DICO and DICO[k]["fr"] and DICO[k]["en"] for k in employees), str(sorted(k for k in employees if k not in DICO)))
check("1.3 toutes les clés du dictionnaire servent (aucune orpheline)", set(DICO) == employees, str(set(DICO) ^ employees))
check("1.4 clés à trois segments, mêmes variables en FR et en EN", DICO and all(
    k.count(".") == 2 and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
    for k, v in DICO.items()))
IDEM = {"a2d.outils.choisir": "Choisir un outil", "a2d.carte.ouvrir": "Ouvrir", "a2d.carte.ouvrir_titre": "Ouvrir {outil}",
        "a2d.carte.guide_titre": "Le chapitre « {outil} » du guide",
        "a2d.carte.guide_absent": "Pas encore de chapitre « {outil} » dans le guide",
        "a2d.carte.sprites": "Une image ou une vidéo devient des cadres puis une planche de sprites : directions, squelette, "
                             "hitboxes, exports pour le moteur.",
        "a2d.carte.tiles": "Tuiles sans raccord, blob 47 / 16, variantes et formes, feuilles exportées vers Tiled, LDtk et Godot.",
        "a2d.carte.pixel": "Retouche au pixel : ligne de temps des cadres, tuile iso 2:1 et ses diagonales, rastériser une "
                           "image générée.",
        "a2d.carte.cards": "Cartes à jouer : gabarits imprimeur, dos et mire, langues, art en lot, livret."}
check("1.5 le français déjà à l'écran est repris à l'identique", DICO and all(DICO.get(k, {}).get("fr") == v
                                                                             for k, v in IDEM.items()))
check("1.6 aucun état React ni confirmation neufs", BUN.count("x.useState(") == 731
      and BUN.count("await window.__dzDialogue.confirmer(") == 30)

print("\n[2] les illustrations dans les statiques")
DOS = RACINE / "frontend" / "dist" / "assets2d" / "cartes"
try:
    from PIL import Image
except ImportError:                                                  # Pillow du python embarqué
    Image = None
for o in OUTILS:
    f = DOS / f"{o}.webp"
    dims = None
    if f.exists() and Image:
        with Image.open(f) as im:
            dims = (im.format, im.size)
    check(f"2.1 {o}.webp : WebP 640 × 360, < 40 Ko", f.exists() and f.stat().st_size < 40_000
          and (Image is None or dims == ("WEBP", (640, 360))), str(dims))

print("\n[3] DzAssets2D joué sous node")
PRELUDE = ("var window={dispatchEvent:function(){}};\n"
           + (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes().decode("utf-8")
           + "\nvar LANG='fr';function dzT(k,v){var e=window.DZ_I18N[k];var s=e?e[LANG]:k;"
           "if(v)s=s.replace(/\\{(\\w+)\\}/g,function(m,n){return v[n]!=null?String(v[n]):m});return s}\n"
           + AIDE.PRELUDE_DZGLYPH)
h0 = BUN.find("var __dzCatHue=")
h1 = BUN.find("};", BUN.find("var __dzCatSVG=")) + 2 if h0 > 0 else -1
MAPS = BUN[h0:h1] if 0 < h0 < h1 else ""
JEU = PRELUDE + r"""
function CustomEvent(t,o){this.type=t}var localStorage={setItem:function(){}};
function K(p){return {K:1,p:p}}var r={jsx:function(t,p,k){return {t:t,p:p,k:k}},jsxs:function(t,p,k){return {t:t,p:p,k:k}}};
""" + MAPS + "\n" + FN + r"""
function kids(n){var c=n&&n.p&&n.p.children;return c==null?[]:(Array.isArray(c)?c:[c])}
function tous(n,acc){acc=acc||[];if(n&&typeof n==="object"){acc.push(n);kids(n).forEach(function(k){tous(k,acc)})}return acc}
function jouer(lang){LANG=lang;var T=DzAssets2D({go:function(){}}),ns=tous(T);
  var o={textes:[],titres:[],imgs:[],svg:[]};
  ns.forEach(function(n){if(n.p&&typeof n.p.title==="string")o.titres.push(n.p.title);
    kids(n).forEach(function(k){if(typeof k==="string")o.textes.push(k)})});
  ns.filter(function(n){return n.p&&n.p.className==="dzA2dC"}).forEach(function(c){var cs=tous(c);
    var im=cs.filter(function(n){return n.t==="img"})[0];
    o.imgs.push(im?[im.p.src,im.p.loading,im.p.alt,im.p.decoding||""]:null);
    o.svg.push(cs.some(function(n){return n.p&&n.p.dangerouslySetInnerHTML&&/<svg|⟦/.test(n.p.dangerouslySetInnerHTML.__html)}))});
  return o}
console.log(JSON.stringify({fr:jouer("fr"),en:jouer("en")}));
"""
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dza2d_"))
p = _TMP / "a2d.js"
p.write_text(JEU, encoding="utf-8")
r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    J = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
except Exception:                                                    # noqa: BLE001
    J = {"erreur": r.stdout[-400:] + r.stderr[-800:]}
check("3.0 DzAssets2D s'exécute sous node", "fr" in J, str(J)[:600])
if "fr" in J:
    for lang in ("fr", "en"):
        att = [DICO[k][lang] for k in ("a2d.outils.choisir", "a2d.carte.sprites", "a2d.carte.tiles", "a2d.carte.pixel",
                                       "a2d.carte.cards", "a2d.carte.ouvrir")] if DICO else ["?"]
        manque = [a for a in att if a not in J[lang]["textes"]]
        check(f"3.1 {lang} : titre, phrases et « Ouvrir » dans la langue", not manque, str(manque))
    check("3.2 en : infobulles traduites", "Open Sprite Lab" in J["en"]["titres"]
          and "The “Card Forge” chapter of the guide" in J["en"]["titres"], str(J["en"]["titres"]))
    check("3.3 fr : infobulles d'avant reprises", "Ouvrir Sprite Lab" in J["fr"]["titres"]
          and "Le chapitre « Card Forge » du guide" in J["fr"]["titres"], str(J["fr"]["titres"]))
    fr_restant = [t for t in J["en"]["textes"] + J["en"]["titres"]
                  if re.search(r"[éèàùç«»]|Ouvrir|Choisir|chapitre", t)]
    check("3.4 en : aucun texte français restant", not fr_restant, str(fr_restant))
    check("3.5 chaque carte a son illustration, paresseuse et décorative",
          J["fr"]["imgs"] == [[f"/assets2d/cartes/{o}.webp", "lazy", "", "async"] for o in OUTILS], str(J["fr"]["imgs"]))
    check("3.6 l'icône de la catégorie reste dessous (repli si l'image manque)", all(J["fr"]["svg"]), str(J["fr"]["svg"]))

print("\n[4] le maillon de queue")
check("4.0 le maillon existe", M is not None)
if M is not None:
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dza2d.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("4.1 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout,
          (r.stdout + r.stderr)[-300:])
    avant = AIDE.avant_dza2d(BUN) if hasattr(AIDE, "avant_dza2d") else ""
    check("4.2 l'inverse avant_dza2d défait le maillon, et le rejouer redonne le bundle à l'octet",
          avant and M.MARKER not in avant and '"Choisir un outil"' in avant and M.appliquer(avant) == BUN)
    src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
    _g = src_aide[src_aide.index("def avant_dzga3d("):]
    _g = _g[:_g.index("\ndef ", 5)]
    check("4.3 avant_dzga3d défait d'abord dza2d (maillon posé après lui)",
          "bundle = avant_dza2d(bundle)" in _g and _g.index("avant_dza2d(") < _g.index("_m.defaire("))
    check("4.4 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(BUN, z) for _a, z in M.PAIRES))
    check("4.5 le maillon suit dzga3d (sonde de son marqueur)", any(j == "/*dzga3d*/" for _t, j, _n in M.SONDE_AMONT))
    check("4.6 aucun .bak_dza2d laissé, un seul marqueur", not (BUNDLE.parent / (BUNDLE.name + ".bak_dza2d")).exists()
          and BUN.count(M.MARKER) == 1)
    check("4.7 lecture et écriture du bundle en octets", "read_text(" not in pathlib.Path(M.__file__).read_text(
        encoding="utf-8") and BUNDLE.read_bytes().count(b"\r\n") > 15000
        and BUNDLE.read_bytes().count(b"\n") == BUNDLE.read_bytes().count(b"\r\n"))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("4.8 dictionnaire assemblé à jour", r.returncode == 0)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
