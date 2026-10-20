# -*- coding: utf-8 -*-
"""t254 (Photolab M5, photocraft 0.10) — plume et texte : le pont et le VRAI moteur.
[1] liste blanche (PM.commande_autorisee) : les 20 commandes ouvertes (13 path.*, 7 type.*) passent avec les
    paramètres que l'écran envoie ; formes et bornes refusées (ancres non [i, j], point non [x, y], t hors ]0, 1[,
    nom de tracé trop long, clé de regroupement illisible, échelle nulle…) ; hitTest / caret / navigate restent fermées.
[2] VRAI moteur : chaque geste agit (ancre déplacée, poignée tournée, segment courbé, point converti, ancre ajoutée /
    retirée, tracé transformé, tracé de détourage, fond et contour copiés-collés, masque de texte, texte sur tracé,
    taille ±) et nomme EXACTEMENT son état d'historique ; `coalesce` fond la pose et le recalcul de courbure (Plume
    de courbure, Plume libre) ou la création et l'attache au tracé en UN état.
[3] chaque nom d'état de [2] est traduit par ETATS_MOTEUR (mod-historique.js) en fr ET en en.
Section VRAI moteur rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY -X utf8 tests/test_photolab_m5.py   (depuis backend/)"""
import json, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt254_"))
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
from app.services import photolab_neuves as PN                # noqa: E402
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


OUVERTES_M5 = ("path.moveAnchors", "path.moveHandle", "path.bendSegment", "path.convertPoint", "path.addAnchor",
               "path.deleteAnchor", "path.transform", "path.clippingPath.set", "path.clippingPath.clear",
               "path.style.copyFill", "path.style.copyStroke", "path.style.pasteFill", "path.style.pasteStroke",
               "type.createSelection", "type.attachToPath", "type.detachFromPath", "type.increaseSize",
               "type.decreaseSize", "type.increaseSizeMore", "type.decreaseSizeMore")
FERMEES_M5 = ("type.hitTest", "type.caret", "type.navigate")
K = lambda x, y, s=False: {"anchor": [x, y], "in": [x, y], "out": [x, y], "smooth": s}
CHEMIN = {"subpaths": [{"closed": False, "op": "combine", "knots": [K(20, 20), K(100, 20), K(100, 100)]}], "fillRule": "nonzero"}
# (commande, paramètres tels que l'écran les envoie)
ADMIS = (
    ("path.moveAnchors", {"name": "work", "anchors": [[0, 1]], "move": [10, 5]}),
    ("path.moveAnchors", {"name": "layer", "layer": 4, "anchors": [[0, 0], [0, 2]], "move": [-3.5, 0], "curvature": True}),
    ("path.moveAnchors", {"name": "work", "anchors": [[0, 0]], "move": [0, 0], "curvature": True, "coalesce": "pl-courbure-3"}),
    ("path.moveHandle", {"name": "work", "subpath": 0, "knot": 1, "handle": "out", "to": [130, 40], "independent": False}),
    ("path.moveHandle", {"name": "Tracé 1", "subpath": 0, "knot": 1, "handle": "in", "to": [90.5, 10], "independent": True}),
    ("path.bendSegment", {"name": "work", "subpath": 0, "knot": 0, "t": 0.5, "move": [0, -20]}),
    ("path.convertPoint", {"name": "work", "subpath": 0, "knot": 1}),
    ("path.convertPoint", {"name": "work", "subpath": 0, "knot": 1, "out": [140, 30]}),
    ("path.convertPoint", {"name": "work", "subpath": 0, "knot": 1, "curvature": True}),
    ("path.addAnchor", {"name": "work", "subpath": 0, "knot": 0, "t": 0.25}),
    ("path.deleteAnchor", {"name": "layer", "layer": 3, "subpath": 0, "knot": 1}),
    ("path.deleteAnchor", {"name": "work", "subpath": 0, "knot": 2, "coalesce": "pl-ancres-k2"}),
    ("path.transform", {"name": "work", "translateX": 10, "translateY": -4, "scaleX": 1.5, "scaleY": 1, "angle": 15}),
    ("path.clippingPath.set", {"name": "Tracé 1", "flatness": 2}),
    ("path.clippingPath.clear", {}),
    ("path.style.copyFill", {}), ("path.style.copyStroke", {}),
    ("path.style.pasteFill", {}), ("path.style.pasteStroke", {"layer": 4}),
    ("path.set", {"name": "work", "path": CHEMIN, "coalesce": "pl-courbure-3"}),
    ("shape.create", {"kind": "path", "path": CHEMIN, "fill": "#ff0000", "stroke": None, "coalesce": "pl-libre-1"}),
    ("type.create", {"x": 20, "y": 60, "text": "Bonjour", "size": 24, "orientation": "vertical", "coalesce": "pl-sur-trace-2"}),
    ("type.createSelection", {"text": "ABC", "x": 20, "y": 100, "font": "Inter", "weight": 400, "italic": False, "size": 40,
                              "orientation": "vertical", "operation": "add", "align": "center"}),
    ("type.createSelection", {"text": "Boîte", "box": [10, 10, 100, 50], "size": 20, "operation": "subtract"}),
    ("type.createSelection", {"layer": 5, "removeLayer": True, "operation": "intersect"}),
    ("type.attachToPath", {"layer": 5, "subpath": 0, "start": 12.5, "flip": False, "coalesce": "pl-sur-trace-2"}),
    ("type.attachToPath", {"layer": 5, "shape": 3, "subpath": 0, "start": 0, "flip": True}),
    ("type.detachFromPath", {"layer": 5}),
    ("type.increaseSize", {}), ("type.decreaseSize", {"layer": 5, "range": [0, 3]}),
    ("type.increaseSizeMore", {"layer": 5}), ("type.decreaseSizeMore", {}),
)
REFUS = (
    ("path.moveAnchors", {"anchors": [[0, 1]]}),                                     # sans move
    ("path.moveAnchors", {"anchors": [], "move": [1, 1]}),                           # aucune ancre
    ("path.moveAnchors", {"anchors": [[0, -1]], "move": [1, 1]}),
    ("path.moveAnchors", {"anchors": [[0, 1.5]], "move": [1, 1]}),
    ("path.moveAnchors", {"anchors": [0, 1], "move": [1, 1]}),
    ("path.moveAnchors", {"anchors": [[0, 1]], "move": [1, "2"]}),
    ("path.moveAnchors", {"anchors": [[0, 1]], "move": [1, 2, 3]}),
    ("path.moveAnchors", {"anchors": [[0, 1]], "move": [1, 2], "curvature": "oui"}),
    ("path.moveAnchors", {"anchors": [[0, 1]], "move": [1, 2], "coalesce": "a b/c"}),
    ("path.moveAnchors", {"anchors": [[0, 1]], "move": [1, 2], "coalesce": "x" * 80}),
    ("path.moveAnchors", {"name": "", "anchors": [[0, 1]], "move": [1, 2]}),
    ("path.moveAnchors", {"name": "x" * 65, "anchors": [[0, 1]], "move": [1, 2]}),
    ("path.moveAnchors", {"name": "C:/x.png", "anchors": [[0, 1]], "move": [1, 2]}),
    ("path.moveAnchors", {"anchors": [[0, 1]], "move": [1, 2], "zorg": 1}),
    ("path.moveHandle", {"subpath": 0, "knot": 1, "handle": "out"}),                 # sans to
    ("path.moveHandle", {"subpath": 0, "knot": 1, "handle": "milieu", "to": [1, 2]}),
    ("path.moveHandle", {"subpath": -1, "knot": 1, "handle": "in", "to": [1, 2]}),
    ("path.moveHandle", {"subpath": 0, "knot": 1, "handle": "in", "to": [1e9, 2]}),
    ("path.bendSegment", {"subpath": 0, "knot": 0, "t": 1.5, "move": [0, 1]}),
    ("path.bendSegment", {"subpath": 0, "knot": 0, "t": 0.5}),
    ("path.convertPoint", {"subpath": 0}),
    ("path.convertPoint", {"subpath": 0, "knot": 1, "out": "140,30"}),
    ("path.addAnchor", {"subpath": 0, "knot": 0, "t": 0}),
    ("path.addAnchor", {"subpath": 0, "knot": 0, "t": 1}),
    ("path.addAnchor", {"subpath": 0, "knot": "0", "t": 0.5}),
    ("path.deleteAnchor", {"subpath": 0}),
    ("path.transform", {"scaleX": 0}),
    ("path.transform", {"scaleY": 101}),
    ("path.transform", {"angle": 400}),
    ("path.transform", {"translateX": 40000}),
    ("path.transform", {"translateY": "3"}),
    ("path.clippingPath.set", {"flatness": 2}),                                      # sans nom
    ("path.clippingPath.set", {"name": "Tracé 1", "flatness": 101}),
    ("path.clippingPath.set", {"name": "Tracé 1", "flatness": -1}),
    ("path.style.pasteFill", {"layer": -2}),
    ("type.createSelection", {"text": "A", "x": 1, "y": 1, "operation": "replace"}),
    ("type.createSelection", {"text": "A", "x": 1, "y": 1, "orientation": "diagonale"}),
    ("type.createSelection", {"text": "A", "x": 1, "y": 1, "size": 5000}),
    ("type.createSelection", {"text": "A", "x": 1, "y": 1, "removeLayer": "oui"}),
    ("type.createSelection", {"text": "A", "x": 1, "y": 1, "color": "#ff0000", "path": "C:/x.txt"}),
    ("type.attachToPath", {"start": "0"}),
    ("type.attachToPath", {"shape": -1}),
    ("type.attachToPath", {"flip": 1}),
    ("type.increaseSize", {"by": "2"}),
    ("type.increaseSize", {"range": "0,3"}),
    ("path.set", {"name": "work", "path": CHEMIN, "coalesce": 3}),
    ("type.hitTest", {"x": 1, "y": 1}), ("type.caret", {"index": 0}), ("type.navigate", {"index": 0, "move": "end"}),
)


def liste_blanche(reg):
    print("\n[1] liste blanche du pont")
    check("1.0 les 20 commandes M5 ne sont plus dans COMMANDES_NEUVES_FERMEES ; hitTest, caret, navigate y restent",
          not (set(OUVERTES_M5) & PN.COMMANDES_NEUVES_FERMEES) and set(FERMEES_M5) <= PN.COMMANDES_NEUVES_FERMEES)
    for cid, p in ADMIS:
        a, m = admise(reg, cid, p)
        check(f"1a {cid} {sorted(p)} admis", a, m)
    for cid, p in REFUS:
        a, _ = admise(reg, cid, p)
        check(f"1b {cid} {json.dumps(p, ensure_ascii=False)[:90]} refusé", not a)


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
    info = lambda n="work", **kw: ex("path.info", {"name": n, **kw})["path"]["subpaths"][0]["knots"]
    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    noms = []

    def etat(label, attendu, h0, n=1):
        h1 = historique(s)
        check(f"{label} : {n} état(s) « {attendu} » de plus", h1[:-n] == h0 and h1[-n:] == [attendu] * n, h1[-3:])
        noms.append(attendu)

    def erreur(c, p):
        try:
            ex(c, p); return None
        except PM.MoteurErreur as e:
            return str(e)

    ex("path.set", {"name": "work", "path": CHEMIN})
    h0 = historique(s); ex("path.moveAnchors", {"name": "work", "anchors": [[0, 1]], "move": [10, 5]})
    check("2b Sélection directe : l'ancre 1 suit le glisser", info()[1]["anchor"] == [110, 25], info()[1])
    etat("2b déplacer des ancres", "Drag Anchor Points", h0)
    h0 = historique(s); ex("path.moveHandle", {"name": "work", "subpath": 0, "knot": 1, "handle": "out", "to": [130, 40]})
    check("2c poignée de sortie posée en [130, 40]", info()[1]["out"] == [130, 40], info()[1])
    etat("2c tirer une poignée", "Drag Direction Point", h0)
    h0 = historique(s); ex("path.bendSegment", {"name": "work", "subpath": 0, "knot": 0, "t": 0.5, "move": [0, -20]})
    check("2d segment courbé : ses deux poignées montent", info()[0]["out"][1] < 20 and info()[1]["in"][1] < 25, info()[:2])
    etat("2d courber un segment", "Drag Segment", h0)
    h0 = historique(s); ex("path.convertPoint", {"name": "work", "subpath": 0, "knot": 1})
    k1 = info()[1]
    check("2e Convertir le point (clic) : angle, poignées rentrées", k1["in"] == k1["anchor"] == k1["out"] and k1["smooth"] is False, k1)
    ex("path.convertPoint", {"name": "work", "subpath": 0, "knot": 1, "out": [140, 30]})
    k1 = info()[1]
    a1 = k1["anchor"]
    check("2e Convertir le point (glisser) : lisse, poignée d'entrée symétrique", k1["smooth"] is True and k1["out"] == [140, 30]
          and k1["in"] == [2 * a1[0] - 140, 2 * a1[1] - 30], k1)
    etat("2e convertir un point (deux fois)", "Convert Point", h0, 2)
    h0 = historique(s); r = ex("path.addAnchor", {"name": "work", "subpath": 0, "knot": 0, "t": 0.5})
    check("2f Ajouter un point d'ancrage : 4 ancres, la neuve en 1", len(info()) == 4 and r.get("anchor") == {"subpath": 0, "knot": 1}, r.get("anchor"))
    etat("2f ajouter une ancre", "Add Anchor Point", h0)
    h0 = historique(s); r = ex("path.deleteAnchor", {"name": "work", "subpath": 0, "knot": 1})
    check("2g Supprimer le point d'ancrage : 3 ancres, sous-tracé gardé", len(info()) == 3 and r.get("subpathRemoved") is False, r.get("subpathRemoved"))
    etat("2g retirer une ancre", "Delete Anchor Point", h0)
    m = erreur("path.deleteAnchor", {"name": "work", "subpath": 0, "knot": 9})
    check("2g une ancre absente : erreur du moteur (no knot)", m is not None and "no knot" in m, m)
    a0 = info()[0]["anchor"]
    h0 = historique(s); ex("path.transform", {"name": "work", "translateX": 10, "translateY": 0, "scaleX": 1, "scaleY": 1, "angle": 0})
    check("2h Transformation manuelle du tracé : décalé de 10 px", info()[0]["anchor"] == [a0[0] + 10, a0[1]], (a0, info()[0]))
    etat("2h transformer le tracé", "Transform Path", h0)
    m = erreur("path.clippingPath.set", {"name": "work", "flatness": 0})
    check("2i tracé de détourage du tracé de travail : refusé (il faut un tracé enregistré)", m is not None and "saved path" in m, m)
    ex("path.rename", {"name": "work", "to": "Tracé 1"})
    h0 = historique(s); ex("path.clippingPath.set", {"name": "Tracé 1", "flatness": 2})
    check("2i path.list nomme le tracé de détourage et sa tolérance", ex("path.list").get("clippingPath") == {"flatness": 2.0, "name": "Tracé 1"}, ex("path.list"))
    etat("2i tracé de détourage", "Clipping Path", h0)
    h0 = historique(s); ex("path.clippingPath.clear")
    check("2j retirer le tracé de détourage", ex("path.list").get("clippingPath") is None)
    etat("2j retirer le détourage", "Clear Clipping Path", h0)
    m = erreur("path.style.copyFill", {})
    check("2k copier le fond sans calque de forme : « not available right now »", m is not None and "not available" in m, m)
    ex("shape.create", {"kind": "rect", "rect": [10, 10, 50, 40], "fill": "#ff0000", "stroke": {"width": 3, "color": "#0000ff"}})
    h0 = historique(s); ex("path.style.copyFill"); ex("path.style.copyStroke")
    check("2k copier le fond et le contour : aucun état d'historique", historique(s) == h0, historique(s)[-2:])
    ex("shape.create", {"kind": "ellipse", "rect": [100, 50, 50, 40], "fill": "#00ff00"})
    h0 = historique(s); r = ex("path.style.pasteFill")
    check("2l coller le fond : l'ellipse devient rouge", r.get("fill") == "#ff0000", r.get("fill"))
    etat("2l coller le fond", "Paste Fill", h0)
    h0 = historique(s); r = ex("path.style.pasteStroke")
    check("2l coller le contour complet : l'ellipse a le contour bleu de 3 px", (r.get("stroke") or {}).get("width") == 3, r.get("stroke"))
    etat("2l coller le contour", "Paste Complete Stroke", h0)
    calque = ins()["activeLayer"]
    h0 = historique(s); ex("path.moveAnchors", {"name": "layer", "layer": calque, "anchors": [[0, 0]], "move": [5, 5]})
    check("2m Sélection directe sur un calque de forme (name layer + id)", info("layer", layer=calque)[0]["anchor"] == [130, 55], info("layer", layer=calque)[0])
    etat("2m ancre d'un calque de forme", "Drag Anchor Points", h0)
    # Plume de courbure / Plume libre : pose des ancres lisses rentrées + recalcul du moteur, UN état (coalesce)
    lisses = {"subpaths": [{"closed": False, "op": "combine", "knots": [K(20, 100, True), K(60, 30, True), K(120, 90, True), K(180, 20, True)]}], "fillRule": "nonzero"}
    h0 = historique(s)
    ex("path.set", {"name": "work", "path": lisses, "coalesce": "pl-courbure-1"})
    ex("path.moveAnchors", {"name": "work", "anchors": [[0, 0]], "move": [0, 0], "curvature": True, "coalesce": "pl-courbure-1"})
    ks = info()
    check("2n courbure : le moteur calcule les poignées des ancres lisses (la courbe passe par les ancres)",
          [k["anchor"] for k in ks] == [[20, 100], [60, 30], [120, 90], [180, 20]] and ks[1]["in"] != ks[1]["anchor"] and ks[1]["out"] != ks[1]["anchor"], ks[1])
    etat("2n Plume de courbure : pose + recalcul fondus", "Work Path", h0)
    h0 = historique(s)
    ex("shape.create", {"kind": "path", "path": {**lisses, "subpaths": [{**lisses["subpaths"][0], "closed": True}]}, "fill": "#0000ff", "coalesce": "pl-courbure-2"})
    ex("path.moveAnchors", {"name": "layer", "anchors": [[0, 0]], "move": [0, 0], "curvature": True, "coalesce": "pl-courbure-2"})
    check("2n courbure en mode Forme : la forme a ses poignées recalculées", info("layer")[1]["in"] != info("layer")[1]["anchor"], info("layer")[1])
    etat("2n Plume de courbure (forme) : un état", "New Shape Layer", h0)
    # Texte vertical, taille ±, texte sur tracé, masque de texte
    h0 = historique(s); r = ex("type.create", {"x": 20, "y": 10, "text": "Bonjour", "size": 24, "orientation": "vertical"})
    t = r["layer"]
    check("2o Texte vertical : calque de texte vertical", ex("type.info", {"layer": t}).get("orientation") == "Vertical")
    etat("2o texte vertical", "New Type Layer", h0)
    taille = lambda: ex("type.info", {"layer": t})["runs"][0]["style"]["size_pt"]
    h0 = historique(s); ex("type.increaseSize", {"layer": t}); a = taille(); ex("type.increaseSizeMore", {"layer": t}); b = taille()
    ex("type.decreaseSizeMore", {"layer": t}); ex("type.decreaseSize", {"layer": t})
    check("2p taille ± : plus grand, puis 10 de plus, puis retour à 24 pt", 24 < a < b and b - a == 10 and taille() == 24, (a, b, taille()))
    etat("2p taille ±", "Change Type Size", h0, 4)
    ex("path.set", {"name": "work", "path": {"subpaths": [{"closed": False, "op": "combine", "knots": [K(20, 100), K(180, 100)]}], "fillRule": "nonzero"}})
    h0 = historique(s)
    r = ex("type.create", {"x": 30, "y": 100, "text": "Sur le tracé", "size": 14, "coalesce": "pl-sur-trace-1"})
    ex("type.attachToPath", {"layer": r["layer"], "subpath": 0, "start": 10, "coalesce": "pl-sur-trace-1"})
    forme = ex("type.info", {"layer": r["layer"]}).get("shape")
    check("2q texte sur tracé : le calque suit le tracé de travail, décalé de 10 px", isinstance(forme, dict) and forme.get("Path", {}).get("start") == 10, forme)
    etat("2q texte sur tracé : création + attache fondues", "New Type Layer", h0)
    h0 = historique(s); ex("type.attachToPath", {"layer": r["layer"], "subpath": 0, "start": 0, "flip": True})
    etat("2q attache seule (sans coalesce)", "Type on a Path", h0)
    h0 = historique(s); ex("type.detachFromPath", {"layer": r["layer"]})
    check("2r libérer le texte du tracé : texte de point", ex("type.info", {"layer": r["layer"]}).get("shape") == "Point")
    etat("2r libérer du tracé", "Release Type from Path", h0)
    m = erreur("type.detachFromPath", {"layer": r["layer"]})
    check("2r déjà libre : « not on a path »", m is not None and "not on a path" in m, m)
    n0 = len(ins()["layers"])
    h0 = historique(s)
    r = ex("type.createSelection", {"text": "ABC", "x": 20, "y": 60, "size": 40, "font": "Inter", "operation": "new"})
    d = ins()
    check("2s Masque de texte : une sélection, aucun calque créé", r.get("selected") is True and d.get("hasSelection") and len(d["layers"]) == n0, (r, len(d["layers"])))
    etat("2s masque de texte", "Type Mask", h0)
    r = ex("type.createSelection", {"text": "Z", "x": 150, "y": 10, "size": 40, "orientation": "vertical", "operation": "add"})
    check("2s Masque de texte vertical en ajout : la sélection grandit", r.get("bounds", [0, 0, 0, 0])[2] > 100, r)
    r = ex("type.createSelection", {"text": "", "x": 1, "y": 1})
    check("2s texte vide : rien de sélectionné (l'écran n'envoie rien)", r.get("selected") is False, r)
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
