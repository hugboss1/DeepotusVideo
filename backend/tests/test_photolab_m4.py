# -*- coding: utf-8 -*-
"""t253 (Photolab M4, photocraft 0.10) — sélection, recadrage, échantillons : le pont et le VRAI moteur.
[1] liste blanche (PM.commande_autorisee) : les commandes ouvertes passent avec les paramètres que l'écran envoie ;
    formes et bornes refusées (coins non quadruples, points hors forme, échantillon sans coordonnées…).
[2] VRAI moteur : chaque geste agit (sélection posée, document recadré, échantillon lu) et nomme EXACTEMENT son état
    d'historique ; les échantillons n'en font pas et se relisent par view.colorSamplers.list.
[3] chaque nom d'état de [2] est traduit par ETATS_MOTEUR (mod-historique.js) en fr ET en en.
Section VRAI moteur rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY -X utf8 tests/test_photolab_m4.py   (depuis backend/)"""
import json, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt253_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.setdefault("FAL_KEY", "test-key")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_registre as PR              # noqa: E402
import photocraft_version as _PV                                # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


def admise(reg, cid, params):
    try:
        PM.commande_autorisee(cid, params, reg)
        return True, ""
    except ValueError as e:
        return False, str(e)


COINS = [[20, 10], [180, 20], [170, 110], [30, 100]]
# (commande, paramètres tels que l'écran les envoie)
ADMIS = (
    ("select.magneticLasso", {"points": [[48, 28], [112, 28], [112, 72], [48, 72]], "width": 10, "contrast": 10,
                              "close": "magnetic", "trace": True, "mode": "replace", "antiAlias": True, "feather": 0}),
    ("select.rect", {"x": 0, "y": 40, "width": 200, "height": 1, "line": "row", "mode": "replace", "antiAlias": True, "feather": 0}),
    ("select.rect", {"x": 70, "y": 0, "width": 1, "height": 120, "line": "column", "mode": "add", "antiAlias": True, "feather": 0}),
    ("select.loadLuminosity", {}),
    ("select.float", {"dx": 30, "dy": -10, "copy": True}),
    ("select.drop", {}),
    ("image.perspectiveCrop", {"corners": COINS, "interpolation": "bicubic"}),
    ("image.crop", {"x": -10, "y": -10, "width": 220, "height": 140, "deleteCroppedPixels": True, "contentAware": True}),
    ("view.colorSamplers.add", {"x": 60.5, "y": 40}),
    ("view.colorSamplers.move", {"index": 0, "x": 12, "y": 12.5}),
    ("view.colorSamplers.delete", {"index": 1}),
    ("view.colorSamplers.clear", {}),
    ("view.colorSamplers.list", {}),
)
REFUS = (
    ("image.perspectiveCrop", {"corners": COINS[:3]}),
    ("image.perspectiveCrop", {"corners": [[0, 0], [1, 1], [2, 2], "x"]}),
    ("image.perspectiveCrop", {"corners": [[0, 0, 0], [1, 1], [2, 2], [3, 3]]}),
    ("image.perspectiveCrop", {"corners": "0,0,1,1"}),
    ("image.perspectiveCrop", {"corners": COINS, "interpolation": "zorg"}),
    ("select.magneticLasso", {"points": [[1, 2]], "width": 0}),
    ("select.magneticLasso", {"points": [[1, 2], [3, 4], [5, 6]], "contrast": 101}),
    ("select.magneticLasso", {"points": [[1, 2], [3, 4], [5, 6]], "close": "zorg"}),
    ("select.rect", {"x": 0, "y": 0, "width": 1, "height": 1, "line": "diagonal"}),
    ("view.colorSamplers.add", {"x": "60", "y": 40}),
    ("view.colorSamplers.add", {"x": 1}),
    ("view.colorSamplers.move", {"index": -1, "x": 1, "y": 1}),
    ("view.colorSamplers.delete", {"index": 1.5}),
    ("select.float", {"dx": "3", "dy": 0}),
    ("select.float", {"dx": 3, "dy": 0, "target": "zorg"}),
    ("image.crop", {"x": 0, "y": 0, "width": 10, "height": 10, "contentAware": "oui"}),
)


def liste_blanche(reg):
    print("\n[1] liste blanche du pont")
    for cid, p in ADMIS:
        a, m = admise(reg, cid, p)
        check(f"1a {cid} {sorted(p)} admis", a, m)
    for cid, p in REFUS:
        a, _ = admise(reg, cid, p)
        check(f"1b {cid} {p} refusé", not a)


def historique(s):
    h = s.appeler("doc.inspect").get("history")
    return list(h) if isinstance(h, list) else []


def moteur():
    print("\n[2] VRAI moteur : chaque geste agit et nomme son état")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check(f"2a le binaire photocraft-cli {PM.VERSION} est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check(f"2a le binaire photocraft-cli {PM.VERSION} est présent (sinon cette section est rouge)", False, e)
        return []
    s = PM.session()
    ex = lambda c, p=None: s.appeler("engine.execute", {"command": c, "params": p or {}})
    ins = lambda: s.appeler("doc.inspect")
    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    ex("select.rect", {"x": 50, "y": 30, "width": 60, "height": 40}); ex("edit.fill", {"color": "#202020"}); ex("select.deselect")
    noms = []

    def etat(label, attendu, h0):
        h1 = historique(s)
        check(f"{label} : un état « {attendu} » de plus", h1[:-1] == h0 and h1[-1:] == [attendu], h1[-3:])
        noms.append(attendu)

    h0 = historique(s); ex(*ADMIS[0])
    i = ins()
    check("2b Lasso magnétique : les points suivent les bords du carré sombre", i.get("hasSelection") and i.get("selectionBounds") == [50, 30, 60, 40], i.get("selectionBounds"))
    etat("2b Lasso magnétique", "Magnetic Lasso", h0)
    ex("select.deselect")
    h0 = historique(s); ex(*ADMIS[1])
    # le moteur ne prolonge PAS la ligne (line ne fait que nommer l'état) : l'écran envoie toute la largeur / hauteur
    check("2c Sélection d'une rangée : la ligne y = 40 sur toute la largeur", ins().get("selectionBounds") == [0, 40, 200, 1], ins().get("selectionBounds"))
    etat("2c Rangée", "Single Row Marquee", h0)
    h0 = historique(s); ex(ADMIS[2][0], {**ADMIS[2][1], "mode": "replace"})
    check("2c Sélection d'une colonne : la colonne x = 70 sur toute la hauteur", ins().get("selectionBounds") == [70, 0, 1, 120], ins().get("selectionBounds"))
    etat("2c Colonne", "Single Column Marquee", h0)
    ex("select.deselect")
    h0 = historique(s); ex("select.loadLuminosity")
    check("2d Charger la luminosité : une sélection sur tout le document clair", ins().get("hasSelection") is True)
    etat("2d Charger la luminosité", "Load Selection", h0)
    ex("select.rect", {"x": 50, "y": 30, "width": 20, "height": 20})
    h0 = historique(s)
    r = ex("select.float", {"dx": 30, "dy": 10, "copy": True})
    check("2e Flotter (copie) : un morceau flottant décalé de [30, 10]", r.get("offset") == [30, 10], r)
    r = ex("select.drop")
    check("2e Déposer : posé, la sélection a suivi", r.get("dropped") is True and ins().get("selectionBounds") == [80, 40, 20, 20], (r, ins().get("selectionBounds")))
    etat("2e Flotter puis déposer (Alt-glisser du Déplacement)", "Move", h0)
    ex("select.deselect")
    h0 = historique(s)
    a = ex("view.colorSamplers.add", {"x": 60.5, "y": 40.5})
    check("2f Échantillonneur : ajouté, numéro 1, couleur lue sous le point", a.get("index") == 0 and a["point"]["number"] == 1 and a["point"]["rgb"] == [32, 32, 32], a)
    ex("view.colorSamplers.add", {"x": 10, "y": 10})
    ex("view.colorSamplers.move", {"index": 0, "x": 12, "y": 12})
    l = ex("view.colorSamplers.list")
    check("2f liste : 2 points, le 1 déplacé en [12, 12] (blanc), au plus 10", l.get("max") == 10 and len(l.get("samplers") or []) == 2
          and l["samplers"][0]["position"] == [12.0, 12.0] and l["samplers"][0]["rgb"] == [255, 255, 255], l)
    check("2f les échantillons ne font aucun état d'historique", historique(s) == h0, historique(s)[-2:])
    ex("view.colorSamplers.clear")
    check("2f tout effacer : liste vide", ex("view.colorSamplers.list").get("samplers") == [])
    h0 = historique(s)
    r = ex("image.crop", {"x": -10, "y": -10, "width": 220, "height": 140, "contentAware": True})
    check("2g Recadrage qui agrandit avec « Contenu pris en compte » : 220 × 140", ins().get("width") == 220 and ins().get("height") == 140, r)
    etat("2g Recadrage", "Crop", h0)
    h0 = historique(s)
    r = ex("image.perspectiveCrop", {"corners": COINS, "interpolation": "bicubic"})
    check("2h Recadrage de perspective : quadrilatère redressé en 150 × 91 (côtés moyens)", ins().get("width") == 150 and ins().get("height") == 91, r)
    etat("2h Recadrage de perspective", "Perspective Crop", h0)
    try:
        ex("image.perspectiveCrop", {"corners": [[0, 0], [10, 10], [100, 0], [0, 100]]}); m = None
    except PM.MoteurErreur as e:
        m = str(e)
    check("2i quadrilatère non convexe : refusé par le moteur (l'écran le vérifie avant)", m is not None and "convex" in m, m)
    return noms


def traductions(noms):
    print("\n[3] noms d'historique traduits (ETATS_MOTEUR -> photolab.json fr/en)")
    src = (RACINE / "frontend/photolab/js/mod-historique.js").read_text(encoding="utf-8")
    bloc = src[src.index("export const ETATS_MOTEUR"):]
    bloc = bloc[:bloc.index("};")]
    table = dict(re.findall(r'"([^"]+)":\s*"(photolab\.[a-z0-9_.]+)"', bloc))
    dico = json.loads((RACINE / "frontend/shared/i18n/photolab.json").read_text(encoding="utf-8"))
    for n in sorted(set(noms)):
        cle = table.get(n)
        check(f"3a « {n} » -> {cle}", cle is not None and bool((dico.get(cle) or {}).get("fr"))
              and bool((dico.get(cle) or {}).get("en")), cle)


reg = PR.structurer(_PV.commandes())
try:
    liste_blanche(reg)
    traductions(moteur())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
