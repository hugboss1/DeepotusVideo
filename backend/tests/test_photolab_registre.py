# -*- coding: utf-8 -*-
"""t138 (Photolab P3, tâche A1) — le parseur de la grammaire `params` du registre photocraft 0.3.0.
  [1] les 10 exemples bruts du relevé donnent les champs attendus (chaque attendu écrit en clair).
  [2] le registre réel (copie tests/photocraft_commandes_0.3.0.json) : 776 ids, périmètre P3 sans résidu,
      nombre EXACT de descriptions non `ok` figé pour attraper une régression du parseur.
  [3] aucun champ de type « ? » dans le périmètre P3.
Hors ligne : bibliothèque standard seulement, aucun moteur.
Run : & $PY -X utf8 tests/test_photolab_registre.py   (depuis backend/)"""
import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_registre as PR              # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def sous(champ, attendu):
    """Vrai si `champ` porte au moins toutes les paires de `attendu` (les clés en plus sont tolérées)."""
    return all(k in champ and champ[k] == v for k, v in attendu.items())


def champ(texte, cle):
    for c in PR.parser(texte)["champs"]:
        if c["cle"] == cle:
            return c
    return None


# Le registre réel, par id : lu une seule fois, sert aux sections 1 (textes bruts) et 2.
sys.path.insert(0, str(BACKEND / "tests"))  # t250 : registre de la version épinglée (vendor/photocraft.json)
import photocraft_version as _PV  # noqa: E402
COMMANDES = json.loads(_PV.fichier_commandes().read_text(encoding="utf-8"))
PAR_ID = {c["id"]: c for c in COMMANDES}
# t251 : la section [1] éprouve le PARSEUR sur des textes réels figés — ceux de 0.3.0, qui ne bougent plus (le texte
# de file.new ou des courbes a changé en 0.10 : ce n'est pas au parseur d'en répondre). [2] et suivantes : le registre
# de la version épinglée.
EX = {c["id"]: c for c in json.loads((BACKEND / "tests" / "photocraft_commandes_0.3.0.json").read_text(encoding="utf-8"))}
STRUCT = PR.structurer(COMMANDES)

# Nombre EXACT de descriptions du registre dont le parseur garde un fragment non typé (hors périmètre P3).
# Le relevé disait 138 avec le parseur de référence. Ici 126 : le portage reconnaît en plus `group` (str),
# `n` (int) et une union dont une variante est `[names]` (style.presets.edit et 11 autres commandes, toutes
# hors périmètre P3 sauf style.presets.edit qui devait être sans « ? »). Les corrections couleur / énumération
# ouverte ne changent aucune de ces descriptions (edit.fill garde `target`, etc.).
# t251 : 126 → 123 sur 0.3.0, la cible de canal (`target`, défaut du moteur) est désormais comprise — elle existait
# déjà sur paint.stroke/pencil/bucket/gradient et edit.transform. 0.10.0 : 203 (descriptions enrichies : 186 changées,
# 142 neuves ; le pont les traite en opaques bornés, comme avant). Compte par version épinglée.
# 0.10.0 : 203 au parseur seul, 201 après les corrections explicites (layer.select, contour d'ombre ; tools.setColors
# reste non ok : backgroundCmyk « same »).
# t252 : 197 — les corrections des outils de retouche ouverts (setSymmetry, symmetryFromPath, patternStamp, remove).
# t253 : 194 — échantillonneur (add, move) et morceau flottant compris après correction.
# t254 : 185 — les champs des tracés et du texte ouverts (name, subpath, knot, t, échelle, angle, shape) compris.
# t256 : 184 — `from` de history.newSnapshot compris (énumération).
# t256 PR 3 : 183 — `size` de edit.transform.warpGrid compris (énumération).
# #415 : 181 — view.newGuide (position) corrigé (la couleur reste « ? ») ; image.trap et edit.checkSpelling réécrits
# (photolab_registre.CHAMPS_REECRITS).
NB_NON_OK = {"0.3.0": 123, "0.10.0": 181}[_PV.VERSION]

print("\n[1] les dix exemples bruts")
r = PR.parser(EX["filter.blur.gaussianBlur"]["params"])
check("1a gaussianBlur -> un champ radius number 0.1..1000 défaut 1",
      r["ok"] and len(r["champs"]) == 1 and sous(r["champs"][0],
      {"cle": "radius", "type": "number", "min": 0.1, "max": 1000, "defaut": 1, "optionnel": False}), r)
bruit = PR.parser(EX["filter.noise.addNoise"]["params"])
check("1b addNoise : 4 champs dans l'ordre amount, distribution, monochromatic, seed",
      [c["cle"] for c in bruit["champs"]] == ["amount", "distribution", "monochromatic", "seed"], bruit)
check("1b addNoise.amount number 0.1..400 défaut 12.5", sous(bruit["champs"][0],
      {"type": "number", "min": 0.1, "max": 400, "defaut": 12.5}))
check("1b addNoise.distribution enum uniform|gaussian (fermée)", sous(bruit["champs"][1],
      {"type": "enum", "valeurs": ["uniform", "gaussian"]}) and not bruit["champs"][1].get("ouverte"))
check("1b addNoise.monochromatic bool", bruit["champs"][2]["type"] == "bool")
check("1b addNoise.seed int défaut 0", sous(bruit["champs"][3], {"type": "int", "defaut": 0}))
nouv = PR.parser(EX["file.new"]["params"])
check("1c file.new.mode enum rgb|gray|cmyk|lab défaut rgb", sous(nouv["champs"][2],
      {"cle": "mode", "type": "enum", "valeurs": ["rgb", "gray", "cmyk", "lab"], "defaut": "rgb"}), nouv["champs"][2])
check("1c file.new.depth enum de nombres 8|16|32 défaut 8", sous(nouv["champs"][3],
      {"cle": "depth", "type": "enum", "valeurs": [8, 16, 32], "defaut": 8}), nouv["champs"][3])
check("1c file.new.resolution = number unité ppi défaut 72", sous(nouv["champs"][5],
      {"cle": "resolution", "type": "number", "unite": "ppi", "defaut": 72}), nouv["champs"][5])
check("1c file.new.width int défaut 1920", sous(nouv["champs"][0], {"cle": "width", "type": "int", "defaut": 1920}))
check("1c file.new.background est une énumération (pas une couleur) avec #rrggbb parmi ses valeurs",
      sous(nouv["champs"][4], {"type": "enum"}) and "#rrggbb" in nouv["champs"][4]["valeurs"])
tc = champ(EX["layer.newAdjustmentLayer.blackWhite"]["params"], "tintColor")
check("1d blackWhite.tintColor = color forme hex", tc is not None and tc["type"] == "color" and tc["formes"] == ["hex"], tc)
fc = champ(EX["edit.fill"]["params"], "color")
check("1e edit.fill.color = color formes hex+rgba (testée avant l'énumération)",
      fc is not None and fc["type"] == "color" and fc["formes"] == ["hex", "rgba"] and "valeurs" not in fc, fc)
check("1e edit.fill.color : défaut en prose = {texte} jamais envoyé, note conservée",
      fc["defaut"] == {"texte": "foreground"} and fc["note"] == "contents=color", fc)
check("1e edit.fill.scale number % défaut 100", sous(champ(EX["edit.fill"]["params"], "scale"),
      {"type": "number", "unite": "%", "defaut": 100}))
check("1e edit.fill.pattern = union id|name", sous(champ(EX["edit.fill"]["params"], "pattern"),
      {"type": "union", "variantes": ["id", "name"]}))
courbes = PR.parser(EX["layer.newAdjustmentLayer.curves"]["params"])
check("1f curves : points/red/green/blue = json, ok", courbes["ok"] and
      [(c["cle"], c["type"]) for c in courbes["champs"]] == [("points", "json"), ("red", "json"), ("green", "json"), ("blue", "json")],
      courbes)
check("1f curves : la note finale est dans la queue, pas dans un champ",
      courbes["queue"].startswith("(curves as") and all("note" not in c for c in courbes["champs"]), courbes["queue"])
niv = PR.parser(EX["layer.newAdjustmentLayer.levels"]["params"])
check("1g levels.inBlack int-borné 0..253 défaut 0", sous(niv["champs"][0],
      {"cle": "inBlack", "type": "number", "min": 0, "max": 253, "defaut": 0, "entier": True}), niv["champs"][0])
check("1g levels.gamma 0.01..9.99 défaut 1", sous(niv["champs"][1], {"cle": "gamma", "min": 0.01, "max": 9.99, "defaut": 1}))
check("1g levels.red/green/blue = json", [c["type"] for c in niv["champs"][-3:]] == ["json"] * 3, niv["champs"][-3:])
sp = PR.parser(EX["layer.setProps"]["params"])
blend = [c for c in sp["champs"] if c["cle"] == "blend"][0]
check("1h setProps.blend = énumération OUVERTE (le … est retiré des valeurs)",
      sous(blend, {"type": "enum", "valeurs": ["Multiply"], "ouverte": True, "optionnel": True}), blend)
check("1h setProps.opacity number 0..1 optionnel", sous([c for c in sp["champs"] if c["cle"] == "opacity"][0],
      {"type": "number", "min": 0, "max": 1, "optionnel": True}))
sa = PR.parser(EX["layer.setAdjustment"]["params"])
check("1i setAdjustment : layerId optionnel, le « …params of that adjustment kind » n'est pas un champ",
      sa["champs"] == [{"cle": "layer", "type": "layerId", "optionnel": True}] and sa["ok"] and sa["inconnus"] == [], sa)
po = PR.parser(EX["layer.layerStyle.patternOverlay"]["params"])
pat = po["champs"][0]
check("1j patternOverlay.pattern = union id|name optionnel, défaut en prose {texte}",
      sous(pat, {"cle": "pattern", "type": "union", "variantes": ["id", "name"], "optionnel": True,
                 "defaut": {"texte": "first library pattern"}}), pat)
check("1j patternOverlay.link bool défaut true ; angle number deg défaut 0",
      sous([c for c in po["champs"] if c["cle"] == "link"][0], {"type": "bool", "defaut": True}) and
      sous([c for c in po["champs"] if c["cle"] == "angle"][0], {"type": "number", "unite": "deg", "defaut": 0}))
cu = PR.parser(EX["filter.other.custom"]["params"])
check("1k custom.kernel = intArray de 25", sous(cu["champs"][0], {"cle": "kernel", "type": "intArray", "n": 25}), cu["champs"][0])
check("1k custom.offset number -9999..9999 défaut 0", sous(cu["champs"][2], {"cle": "offset", "min": -9999, "max": 9999, "defaut": 0}))
arbre = PR.parser(EX["filter.render.tree"]["params"])
check("1l tree : la signature « → {…} » finale va dans la queue", arbre["queue"].startswith("→ {layer,newLayer"), arbre["queue"])
bo = PR.parser(EX["layer.layerStyle.blendingOptions"]["params"])
check("1m blendingOptions : blend enum ouverte, blendIf opaque (non éditable)",
      sous([c for c in bo["champs"] if c["cle"] == "blend"][0], {"type": "enum", "ouverte": True}) and
      [c for c in bo["champs"] if c["cle"] == "blendIf"][0]["type"] == "struct", bo["champs"])
liq = PR.parser(EX["filter.liquify"]["params"])
cl = {c["cle"]: c for c in liq["champs"]}
check("1p liquify : strokes struct, meshSize number px optionnel avec note, layer layerId optionnel, queue en « — »",
      cl["strokes"]["type"] == "struct" and
      sous(cl["meshSize"], {"type": "number", "unite": "px", "optionnel": True}) and
      cl["meshSize"]["note"].startswith("field resolution") and
      sous(cl["layer"], {"type": "layerId", "optionnel": True}) and liq["queue"].startswith("—"), liq)
check("1n texte sans objet en tête -> ok faux, aucun champ", PR.parser("pas un objet")["ok"] is False and
      PR.parser("pas un objet")["champs"] == [])
check("1n objet vide -> ok, aucun champ", PR.parser("{}")["ok"] and PR.parser("{}")["champs"] == [])
check("1n description absente (None / vide) -> ok faux sans exception", PR.parser(None)["ok"] is False and
      PR.parser("")["ok"] is False)
check("1o énumération ouverte avec « ... » ASCII",
      sous(PR.parser('{"mode":"a|b|..."}')["champs"][0], {"valeurs": ["a", "b"], "ouverte": True}))
check("1o couleur seule « #rrggbb » (sans la forme rgba)",
      PR.parser('{"c":"#rrggbb"}')["champs"][0] == {"cle": "c", "type": "color", "formes": ["hex"], "optionnel": False})
check("1o unités px/deg/mm/ppi/pt/% donnent number+unite",
      all(sous(PR.parser('{"v":%s=3}' % u)["champs"][0], {"type": "number", "unite": u, "defaut": 3})
          for u in ("px", "deg", "mm", "ppi", "pt", "%")))
check("1o u32 i32 int u64 -> int",
      [c["type"] for c in PR.parser('{"a":u32,"b":i32,"c":int,"d":u64}')["champs"]] == ["int"] * 4)
check("1o type inconnu -> « ? » avec le texte brut, ok faux, listé dans inconnus",
      (lambda r: r["ok"] is False and r["champs"][0]["type"] == "?" and r["champs"][0]["brut"] == "machin truc"
       and len(r["inconnus"]) == 1)(PR.parser('{"x":machin truc}')))

print("\n[2] le registre réel")
NB_CMD = {"0.3.0": 776, "0.10.0": 918}[_PV.VERSION]
check(f"2a la copie du registre contient {NB_CMD} entrées", len(COMMANDES) == NB_CMD, len(COMMANDES))
check(f"2b structurer rend {NB_CMD} ids, chacun avec id/label/menu/enabled/champs",
      len(STRUCT) == NB_CMD and all({"id", "label", "menu", "enabled", "champs"} <= set(v) for v in STRUCT.values()))
# t251 : le périmètre P3 est celui que l'écran atteint — sans les commandes 0.10 encore fermées (photolab_neuves).
from app.services.photolab_neuves import COMMANDES_NEUVES_FERMEES as _FERMEES   # noqa: E402
filtres = sorted(i for i, c in PAR_ID.items() if i.startswith("filter.") and c["menu"][:1] == ["Filter"] and i not in _FERMEES)
adj_calques = sorted(i for i in PAR_ID if i.startswith("layer.newAdjustmentLayer.") and i not in _FERMEES)
adj_image = sorted(i for i in PAR_ID if i.startswith("image.adjustments.") and i not in _FERMEES)
styles = sorted(i for i in PAR_ID if i.startswith(("layer.layerStyle.", "style.presets.")) and i not in _FERMEES)
galerie = sorted(i for i in PAR_ID if i.startswith("filter.gallery."))
# t256 : Rééclairer et Couleur en alpha (0.10) entrent au menu Filtre ; transferEffects, makeDefault, defaultFor aux styles.
NB_FILTRES, NB_STYLES, NB_LAYERSTYLE = {"0.3.0": (75, 24, 19), "0.10.0": (77, 27, 22)}[_PV.VERSION]
check(f"2c périmètre : {NB_FILTRES} filtres du menu Filtre", len(filtres) == NB_FILTRES, len(filtres))
check("2c périmètre : 16 layer.newAdjustmentLayer.*", len(adj_calques) == 16, len(adj_calques))
check("2c périmètre : 23 image.adjustments.* (22 réglages + colorLookup.list ; le plan disait 22 en tout)",
      len(adj_image) == 23 and "image.adjustments.colorLookup.list" in adj_image, len(adj_image))
check(f"2c périmètre : {NB_STYLES} styles ({NB_LAYERSTYLE} layer.layerStyle.* + 5 style.presets.*)",
      len(styles) == NB_STYLES and sum(i.startswith("layer.layerStyle.") for i in styles) == NB_LAYERSTYLE, len(styles))
check("2c galerie : 47 effets filter.gallery.*", len(galerie) == 47, len(galerie))
perimetre = filtres + adj_calques + adj_image + styles
check("2d tout le périmètre P3 est `ok` (aucun fragment non typé)",
      all(STRUCT[i]["ok"] for i in perimetre), [i for i in perimetre if not STRUCT[i]["ok"]])
check("2d les 47 effets de galerie sont aussi `ok`", all(STRUCT[i]["ok"] for i in galerie),
      [i for i in galerie if not STRUCT[i]["ok"]])
non_ok = sorted(i for i, v in STRUCT.items() if not v["ok"])
check(f"2e nombre EXACT de descriptions non ok sur tout le registre = {NB_NON_OK} (bouge -> régression du parseur)",
      len(non_ok) == NB_NON_OK, len(non_ok))
check("2f chaque description non ok a un fragment inconnu listé (aucun échec muet)",
      all(STRUCT[i]["inconnus"] for i in non_ok))
check("2g chaque champ porte cle/type/optionnel, les types sont dans l'ensemble connu",
      all({"cle", "type", "optionnel"} <= set(c) and c["type"] in PR.TYPES
          for v in STRUCT.values() for c in v["champs"]))
check(f"2h les {NB_FILTRES} filtres : 10 sous-menus du menu Filtre (le plan en comptait 11) + des entrées à la racine",
      len({PAR_ID[i]["menu"][1] for i in filtres if len(PAR_ID[i]["menu"]) > 1}) == 10,
      sorted({PAR_ID[i]["menu"][1] for i in filtres if len(PAR_ID[i]["menu"]) > 1}))
check("2i toute couleur du registre porte `formes` et jamais `valeurs` (testée avant l'énumération)",
      all("formes" in c and "valeurs" not in c for v in STRUCT.values() for c in v["champs"] if c["type"] == "color"))
check("2j toute énumération ouverte a au moins une valeur et ne finit pas par …",
      all(c["valeurs"] and not str(c["valeurs"][-1]).endswith(("…", "..."))
          for v in STRUCT.values() for c in v["champs"] if c["type"] == "enum"))
check("2k toute description du registre réel commence par un objet {…} (aucun ok faux par « pas d'objet »)",
      all(isinstance(c.get("params"), str) and c["params"].startswith("{") for c in COMMANDES))
check("2l entier : levels.inBlack (0..253) est entier, gaussianBlur.radius (0.1..1000) ne l'est pas",
      STRUCT["layer.newAdjustmentLayer.levels"]["champs"][0]["entier"] is True and
      STRUCT["filter.blur.gaussianBlur"]["champs"][0]["entier"] is False)
check("2m style.presets.edit : preset = union name|[names], to = str, index = int optionnel",
      (lambda ch: ch["preset"]["type"] == "union" and ch["to"]["type"] == "str" and
       ch["index"]["type"] == "int" and ch["index"]["optionnel"])({c["cle"]: c for c in STRUCT["style.presets.edit"]["champs"]}))

print("\n[3] périmètre P3 : aucun champ de type « ? »")
inconnus_p3 = [(i, c["cle"]) for i in perimetre for c in STRUCT[i]["champs"] if c["type"] == "?"]
check(f"3a aucun champ « ? » dans les {NB_FILTRES} filtres, 16 calques de réglage, 23 réglages destructifs, {NB_STYLES} styles",
      not inconnus_p3, inconnus_p3)
check("3b aucun champ « ? » dans la galerie non plus", not [(i, c["cle"]) for i in galerie
      for c in STRUCT[i]["champs"] if c["type"] == "?"])
types_p3 = sorted({c["type"] for i in perimetre for c in STRUCT[i]["champs"]})
print("  types vus dans le périmètre :", types_p3)
check("3c les types du périmètre sont tous connus", set(types_p3) <= set(PR.TYPES), types_p3)

# ── t138 A2 : la liste blanche ────────────────────────────────────────────────────────────────────────────────────
print("\n[4] liste blanche (verifier) sur le registre réel")
from app.services import photolab_moteur as PM                # noqa: E402
check("4.0 entier : une borne 0..1 (opacité, centre) est une FRACTION, jamais un entier",
      not (lambda ch: ch["opacity"].get("entier") or ch["fill"].get("entier"))(
          {c["cle"]: c for c in STRUCT["layer.setProps"]["champs"]})
      and not {c["cle"]: c for c in STRUCT["filter.blur.radialBlur"]["champs"]}["centerX"].get("entier"))


def admis(cid, params, kind=None):
    try:
        return PR.verifier(STRUCT, cid, params, kind) == (params or {}), None
    except ValueError as e:
        return False, str(e)


def refus(cid, params, kind=None):
    """Le message du refus, ou None si la commande passe (le banc échoue alors)."""
    try:
        PR.verifier(STRUCT, cid, params, kind)
        return None
    except ValueError as e:
        return str(e)


# Les commandes que l'écran P2 envoie RÉELLEMENT (relu dans frontend/photolab/js/mod-*.js le 08/10), avec leurs
# paramètres réels : mod-calques (nouveau, groupe, dupliquer, fusionner, supprimer, œil, fusion, opacité, fond,
# verrous, sélection de ligne, glisser-déposer, renommer), mod-deplacer (translate, transform, pickAt),
# mod-selection, mod-recadrer, mod-pipette (document.pixel puis setColors), mod-outils / mod-couleur (couleurs),
# mod-raccourcis (select.inverse ; Ctrl+Z passe par /historique) et le menu (commandes sans paramètres : {}).
P2 = [
    ("layer.new.layer", {}), ("layer.new.layer", {"name": "Calque 3"}), ("layer.delete", {}), ("layer.duplicate", {}),
    ("layer.groupLayers", {}), ("layer.mergeDown", {}), ("layer.new.layerFromBackground", {}),
    ("layer.new.layerViaCopy", {}),
    ("layer.select", {"layer": 4, "mode": "replace"}), ("layer.select", {"layer": 4, "mode": "toggle"}),
    ("layer.select", {"layer": 4, "mode": "range"}),
    ("layer.renameLayer", {"layer": 4, "name": "Ciel du soir"}),
    ("layer.setProps", {"layer": 4, "visible": False}), ("layer.setProps", {"layer": 4, "name": "Rouge", "visible": False}),
    ("layer.setProps", {"layer": 4, "opacity": 0.5}), ("layer.setProps", {"layer": 4, "fill": 0.25}),
    ("layer.setProps", {"layer": 4, "opacity": 1}), ("layer.setProps", {"layer": 4, "blend": "multiply"}),
    ("layer.setProps", {"layer": 4, "blend": "passThrough"}),
    ("layer.setProps", {"layer": 4, "locks": {"transparency": True, "pixels": False, "position": False,
                                              "artboard": False, "all": False}}),
    ("layer.moveTo", {"layer": 4, "target": 2, "position": "above"}),
    ("layer.moveTo", {"layer": 4, "target": 3, "position": "into"}),
    ("layer.translate", {"layer": 4, "dx": 12, "dy": -3}), ("layer.translate", {"dx": 1, "dy": 0}),
    ("edit.transform", {"matrix": [1, 0, 0, 1, 5, -7]}),
    ("layer.pickAt", {"x": 10, "y": 20, "target": "layer", "select": True}),
    ("layer.pickAt", {"x": 10, "y": 20, "target": "group", "select": True}),
    ("select.all", {}), ("select.deselect", {}), ("select.inverse", {}), ("select.reselect", {}),
    ("select.rect", {"x": 3, "y": 4, "width": 50, "height": 20, "mode": "replace", "ellipse": False,
                     "antiAlias": True, "feather": 0}),
    ("select.rect", {"x": 3, "y": 4, "width": 50, "height": 20, "mode": "add", "ellipse": True,
                     "antiAlias": False, "feather": 4}),
    ("select.lasso", {"points": [[1, 1], [40, 2], [20, 30]], "mode": "subtract", "antiAlias": True, "feather": 0}),
    ("select.magicWand", {"x": 5, "y": 6, "tolerance": 32, "contiguous": True, "antiAlias": True,
                          "sampleAllLayers": False, "mode": "intersect"}),
    ("select.quick", {"points": [[1, 1], [3, 4]], "size": 30, "mode": "add", "sampleAllLayers": False}),
    ("image.crop", {"x": 0, "y": 0, "width": 32, "height": 16, "deleteCroppedPixels": True}), ("image.crop", {}),
    ("document.pixel", {"x": 3, "y": 4}),
    ("tools.setColors", {"foreground": "#ff0000"}), ("tools.setColors", {"background": "#00AA33"}),
    ("tools.swapColors", {}), ("tools.defaultColors", {}),
    ("edit.undo", {}), ("edit.redo", {}),
    # banc réel t137 (test_photolab_ecran_api) : remplir le calque au premier plan
    ("edit.fill", {"contents": "foreground"}),
]
for cid, params in P2:
    a, err = admis(cid, params)
    check(f"4a P2 admise {cid} {params}", a, err)
for cid, params, kind in (("filter.blur.gaussianBlur", {"radius": 4}, None),
                          ("layer.layerStyle.innerGlow", {"source": "center", "layer": 3, "enabled": True}, None),
                          ("layer.newAdjustmentLayer.colorLookup", {"lut": "tealOrange"}, None),
                          ("image.adjustments.channelMixer", {"red": [100, 0, 0, 0], "monochrome": False}, None),
                          ("image.adjustments.levels", {"inBlack": 10, "red": {"outWhite": 200}}, None),
                          ("layer.setProps", {"blend": "linearDodge"}, None),
                          ("layer.setProps", {"blend": "Linear Dodge (Add)"}, None),
                          ("layer.setAdjustment", {"layer": 3, "gamma": 1.4}, "levels"),
                          ("filter.lensCorrection", {"profile": "auto"}, None),
                          ("filter.blur.radialBlur", {"centerX": 0.25}, None),
                          ("layer.layerStyle.dropShadow", {"blend": "multiply", "opacity": 75}, None),
                          ("image.adjustments.invert", None, None),
                          # décision du 08/10 : `entier` d'un number borné n'est qu'une indication pour l'écran
                          ("layer.setProps", {"opacity": 0.5}, None),
                          ("filter.blur.boxBlur", {"radius": 2.5}, None),
                          ("select.magicWand", {"x": 1, "y": 1, "tolerance": 12.5}, None),
                          # clé `points` : 100 000 valeurs (un lasso à main levée de 3000 points = 6000 nombres)
                          ("select.lasso", {"points": [[k % 500, k // 500] for k in range(3000)], "mode": "replace"}, None),
                          ("layer.newAdjustmentLayer.curves", {"points": [[0, 0], [128, 140], [255, 255]]}, None)):
    a, err = admis(cid, params, kind)
    check(f"4b P3 admise {cid} {params} kind={kind}", a, err)
REFUS = [
    ("image.mode.rgb", {"profile": "C:/x.icc"}, None, "hors liste"),      # t158 : rouverte, profil intégré seulement
    ("plugin.install", {"path": "x.wasm"}, None, "réservée"),
    ("brush.presets.importAbr", {"path": "../a.abr"}, None, "réservée"),
    ("gradient.presets.importGrd", {"path": "a.grd"}, None, "réservée"),
    ("prefs.set", {"path": "a.b", "value": 1}, None, "réservée"),
    ("measurementLog.export", {"path": "a.csv"}, None, "réservée"),
    ("file.saveAs", {}, None, "réservée"),
    ("FILTER.blur", {}, None, "illisible"),
    ("layer.newAdjustmentLayer.colorLookup", {"file": "../x.cube"}, None, "fichier"),
    ("layer.newAdjustmentLayer.colorLookup", {"lut": "../x.cube"}, None, "hors liste"),
    ("layer.newAdjustmentLayer.colorLookup", {"data": {"text": "TITLE x"}}, None, "fichier"),
    ("filter.distort.displace", {"mapPath": "m.psd"}, None, "fichier"),
    ("filter.blur.gaussianBlur", {"radius": "2"}, None, "nombre attendu"),
    ("filter.blur.gaussianBlur", {"radius": True}, None, "nombre attendu"),
    ("filter.blur.gaussianBlur", {"radius": 5000}, None, "0.1..1000"),
    ("filter.blur.gaussianBlur", {"radius": float("nan")}, None, "nombre attendu"),
    ("filter.blur.gaussianBlur", {"radius": 4, "zorglub": 1}, None, "paramètre inconnu : zorglub"),
    ("layer.setProps", {"blend": 3}, None, "mode de fusion inconnu"),
    ("layer.setProps", {"blend": "zorg"}, None, "mode de fusion inconnu"),
    ("layer.layerStyle.dropShadow", {"blend": "add"}, None, "mode de fusion inconnu"),
    ("layer.setAdjustment", {"points": [[0, 0], [255, 255]]}, "levels", "paramètre inconnu : points"),
    ("layer.setAdjustment", {"gamma": 1.2}, None, "réglage"),
    ("layer.setAdjustment", {"gamma": 1.2}, "zorg", "réglage"),
    ("filter.zorg", {}, None, "inconnue du moteur"),
    ("layer.renameLayer", {"layer": 2, "name": "C:\\x.png"}, None, "fichier"),
    ("layer.renameLayer", {"layer": 2, "name": "x" * 257}, None, "256"),
    ("layer.select", {"layer": -1}, None, "entier"),
    ("layer.select", {"layer": 2.5}, None, "entier"),
    ("layer.select", {"layer": 2, "mode": "zorg"}, None, "hors liste"),
    ("layer.select", {"layer": 1.5}, None, "entier"),
    ("image.adjustments.levels", {"red": {"x": list(range(6000))}}, None, "5000"),
    ("layer.setProps", {"visible": "oui"}, None, "booléen"),
    ("tools.setColors", {"foreground": "red"}, None, "couleur"),
    ("tools.setColors", {"foreground": [255, 0, 0]}, None, "couleur"),              # forme hex seule ici
    ("edit.fill", {"color": [255, 0, 0, 300]}, None, "couleur"),
    ("image.adjustments.levels", {"red": {"outWhite": "a/b"}}, None, "fichier"),
    ("image.adjustments.levels", {"red": {"path": 1}}, None, "fichier"),
    ("image.adjustments.levels", {"red": {"x": "y" * 65}}, None, "64"),
    ("image.adjustments.levels", {"red": [[[[[[[1]]]]]]]}, None, "profondeur"),
    ("image.adjustments.levels", {"red": list(range(5001))}, None, "5000"),
    ("layer.layerStyle.blendingOptions", {"blendIf": {"blend": 3}}, None, "mode de fusion"),
    ("filter.blur.gaussianBlur", ["radius"], None, "objet"),
    ("edit.profileInfo", {"profile": "/path/to/profile.icc"}, None, "fichier"),
]
for cid, params, kind, motif in REFUS:
    m = refus(cid, params, kind)
    check(f"4c refusée {cid} {str(params)[:60]} kind={kind} : message « …{motif}… »", m is not None and motif in m, m)
# Exemption d'une valeur d'énumération fermée = `not _valeur_fichier(v)` : une valeur de la liste qui a une
# EXTENSION de fichier (sans séparateur) est refusée elle aussi (registre factice : aucune commande réelle hors familles).
FAUX_REG = PR.structurer([{"id": "x.y", "params": '{"mode":"normal|lut.cube"}'}])
try:
    PR.verifier(FAUX_REG, "x.y", {"mode": "lut.cube"})
    m_ext = None
except ValueError as e:
    m_ext = str(e)
check("4c2 énumération fermée : « normal » admis, « lut.cube » (extension) refusé comme fichier",
      PR.verifier(FAUX_REG, "x.y", {"mode": "normal"}) == {"mode": "normal"} and m_ext is not None and "fichier" in m_ext, m_ext)
# Le banc t136 disait « levels {lightness:{outBlack:60}} acceptée » : `lightness` n'est PAS une clé du registre de
# image.adjustments.levels (inBlack gamma inWhite outBlack outWhite red green blue ; lightness/a/b ne sont nommés
# que dans la note de queue, pour un document Lab). Sur un document RVB le moteur l'ignorait en silence : refusé.
m = refus("image.adjustments.levels", {"lightness": {"outBlack": 60}})
check("4d levels {lightness:{outBlack:60}} : refusée (clé absente du registre)", m is not None and "lightness" in m, m)
check("4e verifier rend les paramètres tels quels (même objet de valeurs)",
      PR.verifier(STRUCT, "filter.blur.gaussianBlur", {"radius": 4}) == {"radius": 4}
      and PR.verifier(STRUCT, "select.all", None) == {})
check("4f KINDS : 16 variantes de doc.inspect -> les 16 kinds de layer.newAdjustmentLayer.*",
      len(PR.KINDS) == 16 and sorted(PR.KINDS.values()) == sorted(i.rsplit(".", 1)[1] for i in adj_calques)
      and PR.KINDS["Levels"] == "levels" and PR.KINDS["Invert"] == "invert", PR.KINDS)
check("4g kind_de : variante d'un calque de réglage (dict ou chaîne « Invert ») ; None sinon",
      PR.kind_de({"adjustment": {"Curves": {}}}) == "curves" and PR.kind_de({"adjustment": "Invert"}) == "invert"
      and PR.kind_de({"kind": "Pixel"}) is None and PR.kind_de({"adjustment": {"Zorg": {}}}) is None)
# t251 : photocraft 0.10 décrit le réglage par {"kind": "<kind de commande>", "params": {…}} (adjust_params::to_params)
check("4g2 kind_de forme 0.10 {kind, params} : kind connu rendu, inconnu None ; la forme 0.3.0 reste lue",
      PR.kind_de({"adjustment": {"kind": "curves", "params": {}}}) == "curves"
      and PR.kind_de({"adjustment": {"kind": "invert", "params": {}}}) == "invert"
      and PR.kind_de({"adjustment": {"kind": "zorg", "params": {}}}) is None
      and PR.kind_de({"adjustment": {"kind": "curves"}}) is None
      and PR.kind_de({"adjustment": {"Curves": {}}}) == "curves")
check("4g3 colorisation lue dans l'état 0.10 (params.colorize) comme dans l'état 0.3.0",
      PR._colorise({}, {"kind": "hueSaturation", "params": {"colorize": True}}) is True
      and PR._colorise({}, {"kind": "hueSaturation", "params": {"colorize": False}}) is False
      and PR._colorise({}, {"kind": "curves", "params": {"colorize": True}}) is False
      and PR._colorise({}, {"HueSaturation": {"colorize": True}}) is True
      and PR._colorise({"colorize": False}, {"kind": "hueSaturation", "params": {"colorize": True}}) is False)

print("\n[4s] schémas des champs `json` des réglages (relevé A4 sur le vrai moteur)")
NEW = "layer.newAdjustmentLayer."
IMG = "image.adjustments."


def famille(kind, bon, mauvais, nom):
    """`bon` admis par les TROIS familles (création, destructif, setAdjustment) ; chaque `mauvais` refusé par les trois."""
    for cid, k in ((NEW + kind, None), (IMG + kind, None), ("layer.setAdjustment", kind)):
        p = ({"layer": 3} if k else {})
        a, m = admis(cid, {**p, **bon}, k)
        check(f"4s {nom} : forme valide admise ({cid.rsplit('.', 1)[-1]}{' ' + k if k else ''})", a, m)
        for libelle, mv in mauvais:
            r = refus(cid, {**p, **mv}, k)
            check(f"4s {nom} : {libelle} refusé ({cid.rsplit('.', 1)[-1]}{' ' + k if k else ''})", r is not None)


famille("selectiveColor", {"method": "absolute", "reds": [10, 0, -5, 0], "blues": [0, 5, 0, -8], "neutrals": [1, 2, 3, 4],
                           "yellows": [0, 0, 0, 0], "greens": [1, 1, 1, 1], "cyans": [0, 0, 0, 0],
                           "magentas": [0, 0, 0, 0], "whites": [0, 0, 0, 0], "blacks": [-7, 0, 0, 9]},
        [("`reds` en OBJET {cyan…} (piège : ignoré en silence par le moteur)", {"reds": {"cyan": 10, "magenta": 0, "yellow": -5, "black": 0}}),
         ("`blues` en objet", {"blues": {"cyan": 1}}), ("3 nombres au lieu de 4", {"reds": [1, 2, 3]}),
         ("nombre hors -100..100", {"neutrals": [101, 0, 0, 0]}), ("texte dans le tableau", {"blacks": ["a", 0, 0, 0]}),
         ("gamme inconnue", {"oranges": [0, 0, 0, 0]})], "selectiveColor")
famille("gradientMap", {"stops": [[0, "#101030"], [0.4, "#c04020"], [1, "#fff0b0"]], "reverse": True},
        [("triplets [r,g,b] (piège : le moteur rend du blanc)", {"stops": [[0, [16, 16, 48]], [1, [255, 240, 176]]]}),
         ("un seul point", {"stops": [[0, "#101030"]]}), ("65 points", {"stops": [[i / 64, "#101030"] for i in range(65)]}),
         ("position 1.5", {"stops": [[0, "#101030"], [1.5, "#ffffff"]]}), ("position négative", {"stops": [[-0.1, "#101030"], [1, "#ffffff"]]}),
         ("couleur sans dièse", {"stops": [[0, "101030"], [1, "#ffffff"]]}),
         ("objets {position, color}", {"stops": [{"position": 0, "color": "#101030"}, {"position": 1, "color": "#fff"}]})], "gradientMap")
a, m = admis(NEW + "gradientMap", {"stops": [[i / 63, "#808080"] for i in range(64)]})
check("4s gradientMap : 64 points admis (borne haute)", a, m)
famille("curves", {"points": [[0, 0], [64, 40], [192, 220], [255, 255]], "blue": [[0, 0], [128, 150], [255, 255]],
                   "red": [[0, 0], [255, 255]], "green": [[10, 20], [200, 100]]},
        [("un seul point", {"points": [[0, 0]]}), ("20 points", {"points": [[i * 12, i * 12] for i in range(20)]}),
         ("x non croissants (doublon)", {"points": [[0, 0], [100, 10], [100, 50], [255, 255]]}),
         ("x décroissants", {"red": [[200, 0], [100, 255]]}), ("x hors 0..255", {"points": [[0, 0], [300, 10]]}),
         ("y négatif", {"blue": [[0, -1], [255, 255]]}), ("flottants", {"points": [[0, 0], [100.5, 10], [255, 255]]}),
         ("triplets", {"green": [[0, 0, 0], [255, 255, 255]]})], "curves")
a, m = admis(NEW + "curves", {"points": [[i * 13, i * 13] for i in range(19)]})
check("4s curves : 19 points admis (borne haute)", a, m)
famille("levels", {"inBlack": 20, "gamma": 1.3, "red": {"inBlack": 10, "gamma": 2, "inWhite": 200, "outBlack": 5, "outWhite": 250},
                   "green": {}, "blue": {"outWhite": 255}},
        [("clé inconnue dans un canal", {"red": {"lightness": 3}}), ("canal en tableau", {"red": [1, 2]}),
         ("inBlack 254 (borne 253)", {"green": {"inBlack": 254}}), ("gamma 50 (borne 9.99)", {"blue": {"gamma": 50}}),
         ("gamma 0", {"red": {"gamma": 0}}), ("inWhite 1 (borne 2)", {"red": {"inWhite": 1}}),
         ("texte", {"red": {"inBlack": "10"}})], "levels")
famille("channelMixer", {"red": [80, 20, 0, 0], "green": [5, 90, 5, 10], "blue": [0, 10, 90, -5], "gray": [30, 60, 10, 5],
                         "monochrome": True},
        [("3 nombres au lieu de 4", {"red": [80, 20, 0]}), ("5 nombres", {"gray": [1, 2, 3, 4, 5]}),
         ("250 % (borne 200)", {"red": [250, 0, 0, 0]}), ("-201", {"blue": [0, 0, -201, 0]}), ("objet", {"green": {"red": 1}})],
        "channelMixer")
famille("colorBalance", {"shadows": [10, -5, 0], "midtones": [0, 0, 20], "highlights": [-100, 100, 0], "preserveLuminosity": False},
        [("2 nombres", {"shadows": [1, 2]}), ("4 nombres", {"midtones": [1, 2, 3, 4]}), ("150", {"highlights": [150, 0, 0]}),
         ("objet", {"shadows": {"r": 1}})], "colorBalance")
famille("hueSaturation", {"hue": 25, "reds": {"hue": 10, "saturation": 5, "lightness": 0},
                          "blues": {"hue": 3, "saturation": 4, "lightness": 5, "range": [190, 210, 250, 270]},
                          "yellows": {}, "greens": {"hue": -180}, "cyans": {"range": [135, 165, 195, 225]},
                          "magentas": {"lightness": -100}},
        [("`range` à 3 nombres", {"reds": {"range": [1, 2, 3]}}), ("clé inconnue", {"reds": {"colorize": True}}),
         ("hue 500 (borne 180)", {"reds": {"hue": 500}}), ("saturation 101", {"blues": {"saturation": 101}}),
         ("gamme en tableau", {"reds": [1, 2, 3]}), ("gamme inconnue", {"oranges": {"hue": 1}})], "hueSaturation")
# un mauvais cas POUR CHAQUE gamme (une régression qui n'oublierait qu'une clé serait vue)
for g in ("reds", "yellows", "greens", "cyans", "blues", "magentas"):
    check(f"4s hueSaturation {g} : tableau refusé, objet à clé inconnue refusé, hue 181 refusé",
          all(refus(NEW + "hueSaturation", {g: v}) is not None for v in ([1, 2, 3], {"zorg": 1}, {"hue": 181})))
for g in ("reds", "yellows", "greens", "cyans", "blues", "magentas", "whites", "neutrals", "blacks"):
    check(f"4s selectiveColor {g} : objet, 3 nombres, 101 refusés",
          all(refus(NEW + "selectiveColor", {g: v}) is not None for v in ({"cyan": 1}, [1, 2, 3], [101, 0, 0, 0])))

# ── colorisation : bornes hue 0..360 et saturation 0..100 quand colorize est vrai ──
for cid in (NEW + "hueSaturation", IMG + "hueSaturation"):
    a, m = admis(cid, {"colorize": True, "hue": 200, "saturation": 40, "lightness": -5})
    check(f"4s colorize : hue 200 / saturation 40 admis ({cid.split('.')[0]})", a, m)
    check(f"4s colorize : hue 200 SANS colorize refusé (borne -180..180) ({cid.split('.')[0]})",
          refus(cid, {"hue": 200, "saturation": 40}) is not None)
    check(f"4s colorize : hue négatif et saturation 101 refusés ({cid.split('.')[0]})",
          refus(cid, {"colorize": True, "hue": -5}) is not None and refus(cid, {"colorize": True, "saturation": 101}) is not None
          and refus(cid, {"colorize": True, "hue": 361}) is not None)
    check("4s colorize false explicite : hue 200 refusé", refus(cid, {"colorize": False, "hue": 200}) is not None)
SA = "layer.setAdjustment"
col = {"HueSaturation": {"colorize": True, "hue": 200.0, "saturation": 40.0, "lightness": 0.0, "ranges": []}}
non = {"HueSaturation": {"colorize": False, "hue": 0.0, "saturation": 0.0, "lightness": 0.0, "ranges": []}}


def admis_etat(params, etat):
    try:
        PR.verifier(STRUCT, SA, params, "hueSaturation", etat)
        return True
    except ValueError:
        return False


check("4s colorize (état) : setAdjustment hue 200 admis sur un calque DÉJÀ colorisé", admis_etat({"layer": 3, "hue": 200}, col))
check("4s colorize (état) : …refusé sur un calque non colorisé", not admis_etat({"layer": 3, "hue": 200}, non))
check("4s colorize (état) : …refusé sans état", not admis_etat({"layer": 3, "hue": 200}, None))
check("4s colorize (état) : colorize:true dans les paramètres PRIME sur un état non colorisé",
      admis_etat({"layer": 3, "colorize": True, "hue": 200}, non))
check("4s colorize (état) : colorize:false dans les paramètres PRIME sur un état colorisé (hue 200 refusé)",
      not admis_etat({"layer": 3, "colorize": False, "hue": 200}, col))
check("4s colorize (état) : état colorisé, saturation 101 refusée, hue négatif refusé",
      not admis_etat({"layer": 3, "saturation": 101}, col) and not admis_etat({"layer": 3, "hue": -1}, col))
check("4s colorize (état) : état non colorisé, hue -180 / saturation -100 admis",
      admis_etat({"layer": 3, "hue": -180, "saturation": -100}, non))

# ── destructifs seuls (hors des 16 kinds) ──
a, m = admis(IMG + "hdrToning", {"curve": [[0, 0], [128, 160], [255, 255]], "strength": 1})
check("4s hdrToning.curve : courbe valide admise", a, m)
for libelle, c in (("un point", [[0, 0]]), ("x non croissants", [[0, 0], [0, 5]]), ("flottants", [[0, 0.5], [255, 255]]),
                   ("hors 0..255", [[0, 0], [256, 255]]), ("triplets", [[0, 0, 1], [5, 5, 1]])):
    check(f"4s hdrToning.curve : {libelle} refusé", refus(IMG + "hdrToning", {"curve": c}) is not None)
a, m = admis(IMG + "replaceColor", {"color": "#cc2222", "fuzziness": 50, "hue": 30})
check('4s replaceColor.color : "#rrggbb" admis', a, m)
for libelle, c in (("[r,g,b] (ignoré par le moteur)", [204, 34, 34]), ('"#rgb"', "#c22"), ("nom", "red"), ("sans dièse", "cc2222"),
                   ("nombre", 3)):
    check(f"4s replaceColor.color : {libelle} refusé", refus(IMG + "replaceColor", {"color": c}) is not None)
a, m = admis(IMG + "matchColor", {"source": 1, "sourceLayer": 4, "luminance": 120})
check("4s matchColor.sourceLayer : entier ≥ 0 admis", a, m)
for libelle, c in (("négatif", -1), ("flottant", 1.5), ("texte", "1"), ("booléen", True)):
    check(f"4s matchColor.sourceLayer : {libelle} refusé", refus(IMG + "matchColor", {"source": 1, "sourceLayer": c}) is not None)

# ── recensement : aucun champ opaque d'un réglage sans schéma (l'oubli d'une clé serait silencieux) ──
OPAQUES_P3 = {"json", "struct", "intArray", "union", "?"}
EXEMPTES = {("colorLookup", "data")}              # contenu de fichier LUT : refusé par CLES_CHEMIN, aucune forme à valider
sans_schema = []
for cid_r, d in STRUCT.items():
    nom = PR._kind_de_commande(cid_r)
    if nom is None:
        continue
    for ch in d["champs"]:
        if ch["type"] in OPAQUES_P3 and (nom, ch["cle"]) not in PR.SCHEMAS and (nom, ch["cle"]) not in EXEMPTES:
            sans_schema.append(f"{cid_r}.{ch['cle']}")
check("4s recensement : tout champ json/struct de layer.newAdjustmentLayer.* et image.adjustments.* a un schéma "
      "(exemption en clair : colorLookup.data)", not sans_schema, sans_schema)
check("4s recensement : le recensement voit bien les 3 destructifs hors kinds",
      all(any(PR._kind_de_commande(i) == n for i in STRUCT) for n in ("hdrToning", "replaceColor", "matchColor")))
check("4s image.adjustments.colorLookup.list n'est pas un réglage (pas de nom)", PR._kind_de_commande("image.adjustments.colorLookup.list") is None)
# colorBalance & co ne sont pas contraints hors de leur kind : le même nom de clé ailleurs reste libre.
a, m = admis("layer.newAdjustmentLayer.vibrance", {"vibrance": 10})
check("4s les schémas ne touchent que leur kind (vibrance inchangé)", a, m)
m = refus("layer.setAdjustment", {"layer": 3, "stops": [[0, "#000000"], [1, "#ffffff"]]}, "curves")
check("4s setAdjustment : les clés d'un autre kind restent refusées (stops sur un calque Courbes)", m is not None and "stops" in m, m)

print("\n[5] commande_autorisee délègue à la liste blanche")
try:
    PM.commande_autorisee("filter.blur.gaussianBlur", {"radius": 3})
    sans = None
except ValueError as e:
    sans = str(e)
check("5a sans registre : refus « registre du moteur indisponible » (jamais l'ancienne liste de refus)",
      sans is not None and "registre du moteur indisponible" in sans, sans)
check("5b avec registre : rend l'id", PM.commande_autorisee("filter.blur.gaussianBlur", {"radius": 3}, STRUCT)
      == "filter.blur.gaussianBlur")
check("5c avec registre et kind", PM.commande_autorisee("layer.setAdjustment", {"gamma": 2}, STRUCT, "levels")
      == "layer.setAdjustment")

print("\n[6] elaguer_inspect")
LUT = [0.1] * 1000
doc = {"name": "d", "revision": 3, "layers": [
    {"id": 1, "kind": "Pixel", "name": "Fond"},
    {"id": 2, "kind": "Group", "name": "G", "children": [
        {"id": 3, "kind": "Adjustment", "name": "Color Lookup 1",
         "adjustment": {"ColorLookup": {"lut": LUT, "name": "Warm Filter", "size": 33, "tetrahedral": False, "dither": True}}},
        {"id": 4, "kind": "Adjustment", "name": "Levels 1", "adjustment": {"Levels": {"space": "Rgb"}}}]},
    {"id": 5, "kind": "Adjustment", "name": "Invert 1", "adjustment": "Invert"}]}
el = PM.elaguer_inspect(doc)
cl = el["layers"][1]["children"][0]["adjustment"]["ColorLookup"]
check("6a lut d'un Color Lookup dans un groupe : None, lutElague True", cl["lut"] is None and cl["lutElague"] is True, cl)
check("6b les autres clés intactes (name, size, tetrahedral, dither ; Levels ; Invert ; calques)",
      {k: cl[k] for k in ("name", "size", "tetrahedral", "dither")} == {"name": "Warm Filter", "size": 33,
                                                                       "tetrahedral": False, "dither": True}
      and el["layers"][1]["children"][1]["adjustment"] == {"Levels": {"space": "Rgb"}}
      and el["layers"][2]["adjustment"] == "Invert" and el["revision"] == 3 and len(el["layers"]) == 3)
check("6c un document sans calque (ou sans document) passe tel quel", PM.elaguer_inspect({"documents": []}) == {"documents": []}
      and PM.elaguer_inspect(None) is None)
nul = PM.elaguer_inspect({"layers": [{"id": 9, "adjustment": {"ColorLookup": {"lut": None, "name": "x"}}}]})
check("6d lut déjà absente : rien n'est marqué élagué", "lutElague" not in nul["layers"][0]["adjustment"]["ColorLookup"], nul)

# t138 B5 (relecture) : l'exposition « -20..20=0 » est une valeur en EV décimale ; la correction est EXPLICITE, champ
# par champ, et ne touche rien d'autre (des `exposure` entiers existent ailleurs dans le registre).
print("\n[7] corrections explicites du registre (exposition en EV)")
_garde = PR.CORRECTIONS_CHAMPS
PR.CORRECTIONS_CHAMPS = {}
try:
    BRUT = PR.structurer(COMMANDES)
finally:
    PR.CORRECTIONS_CHAMPS = _garde
changes = [(i, a.get("cle"), {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)})
           for i in STRUCT for a, b in zip(BRUT[i]["champs"], STRUCT[i]["champs"]) if a != b]
# t251 : en 0.10 s'ajoutent les corrections de layer.select / tools.setColors / contour d'ombre (sans effet sur 0.3.0,
# où le parseur donne déjà ces types) — 7a/7b portent sur l'exposition seule, 7e sur les corrections de t251.
expo = [x for x in changes if x[1] == "exposure"]
check("7a exactement 2 champs « exposure » changent : l'exposition du réglage destructif et du calque de réglage",
      sorted((i, c) for i, c, _ in expo) == [("image.adjustments.exposure", "exposure"),
                                            ("layer.newAdjustmentLayer.exposure", "exposure")], expo)
check("7b changés en entier: False, unite: ev (bornes et défaut intacts)",
      all(d == {"entier": (True, False), "unite": (None, "ev")} for _, _, d in expo), expo)
t251 = sorted((i, c) for i, c, _ in changes if c != "exposure")
check("7e corrections t251 : seules layer.select.layer, tools.setColors.fore/background, dropShadow.contour (0.10) ; "
      "aucune sur 0.3.0", t251 == ([] if _PV.VERSION == "0.3.0" else sorted([
          ("layer.select", "layer"), ("tools.setColors", "foreground"), ("tools.setColors", "background"),
          ("layer.layerStyle.dropShadow", "contour"),
          # t252 : outils de retouche ouverts
          ("paint.patternStamp", "size"), ("paint.patternStamp", "spacing"), ("paint.patternStamp", "scale"),
          ("paint.remove", "size"), ("paint.remove", "spacing"), ("paint.setSymmetry", "rotation"),
          ("paint.symmetryFromPath", "name"),
          # t253 : échantillonneur, morceau flottant
          ("view.colorSamplers.add", "x"), ("view.colorSamplers.add", "y"), ("view.colorSamplers.move", "index"),
          ("view.colorSamplers.move", "x"), ("view.colorSamplers.move", "y"), ("view.colorSamplers.delete", "index"),
          ("select.float", "target"),
          # t254 : tracés et texte
          *[(c, "name") for c in ("path.moveAnchors", "path.moveHandle", "path.bendSegment", "path.convertPoint",
                                  "path.addAnchor", "path.deleteAnchor", "path.transform")],
          *[(c, k) for c in ("path.moveHandle", "path.bendSegment", "path.convertPoint", "path.addAnchor", "path.deleteAnchor")
            for k in ("subpath", "knot")],
          ("path.addAnchor", "t"), ("path.transform", "translateY"), ("path.transform", "scaleX"), ("path.transform", "scaleY"),
          ("path.transform", "angle"), ("path.clippingPath.set", "name"), ("type.attachToPath", "shape"),
          # t256 : le type d'effet de layer.layerStyle.defaultFor ; PR 2 : instantanés
          ("layer.layerStyle.defaultFor", "kind"), ("history.newSnapshot", "from"), ("history.deleteSnapshot", "snapshot"),
          ("history.renameSnapshot", "snapshot"), ("history.selectSnapshot", "snapshot"),
          # PR 3 : la grille de Ctrl+T › Déformer
          ("edit.transform.warpGrid", "size"),
          # #415 : Affichage › Nouveau repère…
          ("view.newGuide", "position")])), t251)
autres = [(i, c["cle"]) for i, v in STRUCT.items() for c in v["champs"]
          if c.get("cle") == "exposure" and i not in ("image.adjustments.exposure", "layer.newAdjustmentLayer.exposure")]
check("7c les autres `exposure` du registre ne sont pas touchés", all(
    next(c for c in BRUT[i]["champs"] if c["cle"] == k) == next(c for c in STRUCT[i]["champs"] if c["cle"] == k)
    for i, k in autres), autres)
check("7d même nombre de champs partout", all(len(BRUT[i]["champs"]) == len(STRUCT[i]["champs"]) for i in STRUCT))

# t251 (M2) : 0.10 ajoute à Coller / Symétrie / Rotation une cible de canal dont le DÉFAUT est posé par le moteur
# (« Channels panel target »). L'omettre = le comportement 0.3.0 : le champ est opaque mais OPTIONNEL, sinon l'écran
# grise l'entrée (relevé M1 : 9 entrées). Forme reconnue exactement, rien d'autre n'est rendu optionnel.
CIBLE = '{"target":"pixels"|"mask"|"quickMask"|{"channel":i}=Channels panel target (an unlinked mask, an alpha channel or the Quick Mask turns alone)}'
ch = PR.parser(CIBLE)
check("8a cible de canal : un champ union opaque, OPTIONNEL, variantes écrites, description comprise (ok)",
      ch["ok"] and len(ch["champs"]) == 1 and sous(ch["champs"][0], {"cle": "target", "type": "union", "optionnel": True,
      "variantes": ["pixels", "mask", "quickMask", '{"channel":i}']}), ch)
ch2 = PR.parser('{"center":[x,y]?,"target":"pixels"|"mask"|"quickMask"|{"channel":i}=Channels panel target (not pixels: the luminosity pasted into that mask or channel)}')
check("8b avec un autre champ devant (edit.paste) : center intact, target optionnel",
      ch2["ok"] and [c["cle"] for c in ch2["champs"]] == ["center", "target"] and ch2["champs"][1]["optionnel"] is True, ch2)
ch3 = PR.parser('{"target":"pixels"|"mask"}')
check("8c une autre forme d'union de chaînes n'est PAS rendue optionnelle par cette règle",
      not any(c.get("optionnel") for c in ch3["champs"]), ch3)
ch4 = PR.parser('{"target":"pixels"|"mask"|"quickMask"|{"channel":i}}')
check("8d la même forme SANS défaut du moteur reste requise", ch4["champs"] and ch4["champs"][0]["optionnel"] is False, ch4)

# t251 : un champ réparé par CORRECTIONS_CHAMPS sort des `inconnus` ; s'il était le seul, la description devient `ok`.
d_ombre = PR.structurer([{"id": "layer.layerStyle.dropShadow", "params":
                          '{"contour":"Linear|Cone"|{"name":str,"points":[[in 0..1,out 0..1],…]}="Linear","size":px=5}'}])
d_ombre = d_ombre["layer.layerStyle.dropShadow"]
check("8e champ corrigé (contour d'ombre) : hors des inconnus, description ok",
      d_ombre["ok"] is True and d_ombre["inconnus"] == [] and d_ombre["champs"][0]["type"] == "union", d_ombre)
d_autre = PR.structurer([{"id": "layer.layerStyle.dropShadow", "params": '{"contour":"Linear"|{"x":1}="Linear","zorg":machin}'}])
check("8f un AUTRE fragment inconnu garde la description non ok",
      d_autre["layer.layerStyle.dropShadow"]["ok"] is False
      and [x.split(":")[0] for x in d_autre["layer.layerStyle.dropShadow"]["inconnus"]] == ['"zorg"'], d_autre)
# t251 : les champs opaques que 0.10 ajoute aux réglages (pipettes des Niveaux/Courbes, points de Remplacement de
# couleur) sont FERMÉS comme les commandes neuves : refusés tant qu'un lot ne leur donne pas de schéma.
for cid_f, cle_f in (("layer.newAdjustmentLayer.levels", "eyedropper"), ("image.adjustments.curves", "eyedropper"),
                     ("image.adjustments.replaceColor", "points")):
    reg10 = PR.structurer(json.loads((BACKEND / "tests" / "photocraft_commandes_0.10.0.json").read_text(encoding="utf-8")))
    try:
        PR.verifier(reg10, cid_f, {cle_f: [[1, 2]]}); m = None
    except ValueError as e:
        m = str(e)
    check(f"8g {cid_f}.{cle_f} : champ 0.10 refusé (pas encore ouvert)", m is not None and "pas encore ouvert" in m, m)

# t251 : les commandes ajoutées par 0.10 restent FERMÉES tant qu'un lot ne les ouvre pas (la liste blanche suit le
# registre du moteur : sans cette garde, la montée de version ouvrirait 142 commandes en douce).
from app.services.photolab_neuves import COMMANDES_NEUVES_FERMEES as NEUVES   # noqa: E402
ids03 = {c["id"] for c in json.loads((BACKEND / "tests" / "photocraft_commandes_0.3.0.json").read_text(encoding="utf-8"))}
ids10 = {c["id"] for c in json.loads((BACKEND / "tests" / "photocraft_commandes_0.10.0.json").read_text(encoding="utf-8"))}
check("9a la liste des fermées = exactement les ids de 0.10.0 absents de 0.3.0 (moins celles qu'un lot a ouvertes)",
      NEUVES <= ids10 - ids03 and not (NEUVES & ids03), (len(NEUVES), len(ids10 - ids03)))
OUVERTES = {"paint.patch", "paint.contentAwareMove", "paint.patternStamp", "paint.redEye", "paint.remove",   # t252
            "paint.setSymmetry", "paint.symmetryFromPath", "paint.symmetryDisable",
            # t253
            "select.magneticLasso", "select.float", "select.drop", "select.loadLuminosity", "image.perspectiveCrop",
            "view.colorSamplers.add", "view.colorSamplers.move", "view.colorSamplers.delete", "view.colorSamplers.clear",
            "view.colorSamplers.list",
            # t254
            "path.moveAnchors", "path.moveHandle", "path.bendSegment", "path.convertPoint", "path.addAnchor",
            "path.deleteAnchor", "path.transform", "path.clippingPath.set", "path.clippingPath.clear",
            "path.style.copyFill", "path.style.copyStroke", "path.style.pasteFill", "path.style.pasteStroke",
            "type.createSelection", "type.attachToPath", "type.detachFromPath", "type.increaseSize", "type.decreaseSize",
            "type.increaseSizeMore", "type.decreaseSizeMore",
            # t255 : le panneau Actions
            "actions.assignSet", "actions.conditional", "actions.delete", "actions.dialog", "actions.get", "actions.insert",
            "actions.list", "actions.load", "actions.move", "actions.photoshopStep", "actions.play", "actions.record",
            "actions.rename", "actions.save", "actions.setColor", "actions.stop", "actions.stopMessage", "actions.toggle",
            # t256 : calques
            "layer.removeBackground", "filter.render.relight", "filter.other.colorToAlpha", "layer.showOnly",
            "layer.toggleLockTransparency", "layer.setLabelColor", "layer.mergeGroup", "layer.copyToDocument",
            "layer.new.frame", "layer.artboard.addBeside", "layer.layerStyle.transferEffects",
            "layer.layerStyle.makeDefault", "layer.layerStyle.defaultFor", "layer.layerMask.edit",
            "layer.smartObjects.convertToLayers", "layer.new.backgroundFromLayer", "layer.rasterize.layerStyle",
            # t256 PR 2 : instantanés
            "history.newSnapshot", "history.deleteSnapshot", "history.renameSnapshot", "history.selectSnapshot",
            "history.newDocument",
            # t256 PR 3 : Ctrl+T › Déformer
            "edit.transform.warpGrid"}
check("9b fermées = les 142 neuves moins celles ouvertes lot par lot (t252 : 8, t253 : 10, t254 : 20, t255 : 18, "
      "t256 : 17 + 5 + 1) -> 63",
      len(NEUVES) == 63 and NEUVES | OUVERTES == ids10 - ids03 and not (NEUVES & OUVERTES), len(NEUVES))
REG10 = PR.structurer(json.loads((BACKEND / "tests" / "photocraft_commandes_0.10.0.json").read_text(encoding="utf-8")))
for cid, p in (("layer.layerStyle.replace", {"layer": 1, "effects": []}), ("swatches.list", {}), ("swatches.add", {}), ("history.undo", {})):
    try:
        PR.verifier(REG10, cid, p); m = None
    except ValueError as e:
        m = str(e)
    check(f"9c {cid} : refusée par le pont même si le moteur 0.10 la connaît", m is not None and "pas encore ouverte" in m, m)
try:
    PR.verifier(REG10, "filter.blur.gaussianBlur", {"radius": 3}); m = None
except ValueError as e:
    m = str(e)
check("9d une commande 0.3.0 passe toujours sur le registre 0.10", m is None, m)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
