# -*- coding: utf-8 -*-
"""Exports d'un jeu de tuiles : Tiled `.tsx`, LDtk `.ldtk`, Godot `.tres` (plan 2026-09-03-plan-tuiles T3-T5, tâche
t114). Python écrit, depuis la MÉTA du jeu (`meta.json`) : l'atlas est déjà rangé à côté (`atlas.png`), chaque
fichier le désigne par un chemin RELATIF.

L'INDEX D'UNE TUILE est celui de `tile_ops.assembler_jeu` : `index_de(voisinage) * variantes + k`, la VIDE en
dernier ; la case de l'atlas est `(i % colonnes, i // colonnes)`. La numérotation des bits (horaire depuis le nord)
est celle du `wangid` de Tiled — l'export Tiled est une lecture bit à bit.

CHAQUE FORMAT A ÉTÉ RELU LE 06/10/2026, ET QUATRE ÉCARTS AU PLAN (03/09) EN SONT SORTIS :
  * Tiled range les <wangset> DANS un conteneur <wangsets> (`mapwriter.cpp` : `writeStartElement("wangsets")`) ; le
    plan les posait directement sous <tileset>, où le lecteur de Tiled ne les cherche pas.
  * Tiled ÉCRIT toujours `type` sur <wangset> et le lit `mixed` quand il manque (`wangSetTypeFromString`). La doc TMX
    ne le liste pas, le plan l'omettait : juste pour blob47 (mixte), faux pour blob16 — un jeu d'ARÊTES (`edge`),
    dont les coins valent 0 (inutilisés).
  * LDtk 1.5.3 exige sur chaque règle `tileRandomX/YMin/Max` et `tileX/YOffset`, et ne requiert plus `tileIds`
    (déprécié, « no longer exported since 1.5.0 ») : le banc valide contre le SCHÉMA officiel, pas une liste.
  * blob16 : 16 règles LDtk aux coins ignorés, et `MATCH_SIDES` (2) chez Godot — le plan figeait 47 et le mode 0.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from app.services import tile_ops as TO

#: couleur 1 = le terrain, couleur 2 = le fond : chaque bit dit « voisin en terrain » ou « voisin en fond »
COULEUR_TERRAIN = "#e0a640"
COULEUR_FOND = "#3a4a5a"
VERSION_TMX = "1.10"
VERSION_TILED = "1.10.2"
ARETES = (TO.N, TO.E, TO.S, TO.W)


def _taille_tuile(meta: dict) -> tuple[int, int]:
    """(largeur, hauteur) d'une case : `cote` au carré (T8 posera `largeur`/`hauteur` pour l'isométrique)."""
    return int(meta.get("largeur") or meta["cote"]), int(meta.get("hauteur") or meta["cote"])


def _d_aretes(meta: dict) -> bool:
    return meta.get("jeu") == "blob16"


def _index(meta: dict):
    """[(voisinage canonique, [index de ses variantes])] dans l'ordre de l'atlas, puis l'index de la VIDE."""
    v = int(meta["variantes"])
    return [(m, [i * v + k for k in range(v)]) for i, m in enumerate(meta["cles"])], int(meta["vide"])


# ── TILED ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def ecrire_tsx(dossier: Path, meta: dict) -> Path:
    """Le `.tsx` de Tiled : <tileset> seul (un tileset externe n'a pas de `firstgid`), l'atlas, une <tile> par tuile
    de terrain portant sa `probability` (les variantes d'un voisinage se partagent le tirage), et le jeu Wang."""
    largeur, hauteur = _taille_tuile(meta)
    colonnes, rangees, variantes = int(meta["colonnes"]), int(meta["rangees"]), int(meta["variantes"])
    aretes = _d_aretes(meta)
    tuiles, vide = _index(meta)
    ts = ET.Element("tileset", {
        "version": VERSION_TMX, "tiledversion": VERSION_TILED, "name": str(meta.get("nom") or "tuiles")[:60],
        "tilewidth": str(largeur), "tileheight": str(hauteur), "tilecount": str(int(meta["tuiles"])),
        "columns": str(colonnes), "spacing": "0", "margin": "0"})
    ET.SubElement(ts, "image", {"source": "atlas.png", "width": str(colonnes * largeur),
                                "height": str(rangees * hauteur)})
    proba = "1" if variantes == 1 else f"{1 / variantes:.6f}".rstrip("0")
    for _m, ids in tuiles:                  # la VIDE n'entre pas en concurrence : pas de <tile> pour elle
        for i in ids:
            ET.SubElement(ts, "tile", {"id": str(i), "probability": proba})
    wss = ET.SubElement(ts, "wangsets")
    ws = ET.SubElement(wss, "wangset", {"name": "terrain", "type": "edge" if aretes else "mixed", "tile": "-1"})
    for nom, couleur in (("terrain", COULEUR_TERRAIN), ("fond", COULEUR_FOND)):
        ET.SubElement(ws, "wangcolor", {"name": nom, "color": couleur, "tile": "-1", "probability": "1"})
    for m, ids in tuiles:
        # bit posé → couleur 1, absent → 2 ; dans un jeu d'arêtes, les coins valent 0 (« pas de couleur »)
        wangid = ",".join("0" if aretes and b not in ARETES else ("1" if m & b else "2") for b in TO.BITS)
        for i in ids:
            ET.SubElement(ws, "wangtile", {"tileid": str(i), "wangid": wangid})
    vide_id = ",".join("0" if aretes and b not in ARETES else "2" for b in TO.BITS)
    ET.SubElement(ws, "wangtile", {"tileid": str(vide), "wangid": vide_id})
    ET.indent(ts, space=" ")
    p = Path(dossier) / "tileset.tsx"
    ET.ElementTree(ts).write(p, encoding="utf-8", xml_declaration=True)
    return p


# ── LDTK ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
LDTK_VERSION = "1.5.3"


def _ident(nom: str) -> str:
    """Identifiant LDtk : lettres, chiffres et soulignés, initiale capitale."""
    s = "".join(c if c.isalnum() else "_" for c in nom).strip("_") or "Atlas"
    if s[0].isdigit():
        s = "T" + s
    return s[0].upper() + s[1:]


def motif(m: int, aretes: bool = False) -> list[int]:
    """Motif 3×3 (index y*3 + x : NW N NE / W centre E / SW S SE) d'un voisinage canonique. Sémantique CITÉE du code
    de LDtk (AutoLayerRuleDef.hx) : 0 = case ignorée, v > 0 = doit valoir v, −v = ne doit pas valoir v.

    Arête : 1 posée, −1 absente. Coin : 1 posé ; −1 absent alors que ses DEUX arêtes sont posées ; 0 sinon — c'est
    ce que la canonisation a effacé, l'exiger serait un mensonge. Dans un jeu d'arêtes, les coins sont tous ignorés.
    Les règles d'un jeu sont alors mutuellement exclusives (éprouvé au banc sur les 256 voisinages)."""
    p = [0] * 9
    p[4] = 1
    for i, bit in ((1, TO.N), (3, TO.W), (5, TO.E), (7, TO.S)):
        p[i] = 1 if m & bit else -1
    if not aretes:
        for i, (coin, a, b) in ((0, (TO.NW, TO.W, TO.N)), (2, (TO.NE, TO.N, TO.E)), (6, (TO.SW, TO.S, TO.W)),
                                (8, (TO.SE, TO.E, TO.S))):
            p[i] = 1 if m & coin else (-1 if (m & a and m & b) else 0)
    return p


def ecrire_ldtk(dossier: Path, meta: dict) -> Path:
    """Un projet `.ldtk` minimal mais complet au sens du schéma 1.5.3 : le tileset, une couche IntGrid portant un
    groupe de règles d'auto-layer — une par voisinage canonique, ses variantes tirées au hasard (`tileRectsIds`)."""
    cote = int(meta["cote"])
    largeur, hauteur = _taille_tuile(meta)
    colonnes, rangees = int(meta["colonnes"]), int(meta["rangees"])
    nom = str(meta.get("nom") or "tuiles")[:60]
    aretes = _d_aretes(meta)
    tuiles, _vide = _index(meta)
    uid_ts, uid_couche, uid_groupe = 1, 2, 3
    regles = [{
        "uid": 100 + n, "active": True, "size": 3, "pattern": motif(m, aretes),
        "tileRectsIds": [[i] for i in ids],         # « all the possible tile IDs rectangles (picked randomly) »
        "alpha": 1.0, "chance": 1.0, "breakOnMatch": True, "flipX": False, "flipY": False, "tileMode": "Single",
        "pivotX": 0.0, "pivotY": 0.0, "xModulo": 1, "yModulo": 1, "xOffset": 0, "yOffset": 0,
        "tileXOffset": 0, "tileYOffset": 0, "tileRandomXMin": 0, "tileRandomXMax": 0, "tileRandomYMin": 0,
        "tileRandomYMax": 0, "checker": "None", "outOfBoundsValue": None, "invalidated": False,
        "perlinActive": False, "perlinScale": 0.2, "perlinOctaves": 2.0, "perlinSeed": 0}
        for n, (m, ids) in enumerate(tuiles)]
    doc = {
        "__header__": {"fileType": "LDtk Project JSON", "app": "DeepotusVideoGen Tile Lab",
                       "doc": "https://ldtk.io/json", "schema": "https://ldtk.io/files/JSON_SCHEMA.json",
                       "appAuthor": "Deepotus", "appVersion": LDTK_VERSION, "url": "https://ldtk.io"},
        "iid": "dz-tiles-project", "jsonVersion": LDTK_VERSION, "appBuildId": 0, "nextUid": 1000,
        "identifierStyle": "Capitalize", "imageExportMode": "None", "exportTiled": False, "exportLevelBg": True,
        "simplifiedExport": False, "minifyJson": False, "externalLevels": False, "backupOnSave": False,
        "backupLimit": 10, "customCommands": [], "bgColor": "#40465B", "defaultLevelBgColor": "#696A79",
        "defaultGridSize": cote, "defaultEntityWidth": cote, "defaultEntityHeight": cote,
        "defaultPivotX": 0.0, "defaultPivotY": 0.0, "dummyWorldIid": "dz-tiles-world", "flags": [],
        "levelNamePattern": "Level_%idx", "toc": [], "worlds": [], "levels": [],
        "defs": {
            "entities": [], "enums": [], "externalEnums": [], "levelFields": [],
            "tilesets": [{
                "uid": uid_ts, "identifier": _ident(nom), "relPath": "atlas.png", "embedAtlas": None,
                "pxWid": colonnes * largeur, "pxHei": rangees * hauteur, "tileGridSize": cote, "spacing": 0,
                "padding": 0, "__cWid": colonnes, "__cHei": rangees, "tags": [], "tagsSourceEnumUid": None,
                "enumTags": [], "customData": [], "savedSelections": [], "cachedPixelData": None}],
            "layers": [{
                "__type": "IntGrid", "type": "IntGrid", "identifier": "Terrain", "uid": uid_couche,
                "gridSize": cote, "displayOpacity": 1.0, "inactiveOpacity": 0.6, "hideInList": False,
                "hideFieldsWhenInactive": False, "canSelectWhenInactive": True, "renderInWorldView": True,
                "pxOffsetX": 0, "pxOffsetY": 0, "parallaxFactorX": 0.0, "parallaxFactorY": 0.0,
                "parallaxScaling": True, "requiredTags": [], "excludedTags": [], "uiFilterTags": [],
                "useAsyncRender": False, "guideGridWid": 0, "guideGridHei": 0, "tilePivotX": 0.0, "tilePivotY": 0.0,
                "intGridValues": [{"value": 1, "identifier": "terrain", "color": COULEUR_TERRAIN, "tile": None,
                                   "groupUid": 0}],
                "intGridValuesGroups": [], "tilesetDefUid": uid_ts, "autoSourceLayerDefUid": None,
                "autoRuleGroups": [{
                    "uid": uid_groupe, "name": "blob16" if aretes else "blob", "active": True,
                    "isOptional": False, "collapsed": False, "color": COULEUR_TERRAIN, "icon": None,
                    "usesWizard": False, "rules": regles, "biomeRequirementMode": 0,
                    "requiredBiomeValues": []}]}]},
    }
    p = Path(dossier) / "projet.ldtk"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


# ── GODOT ────────────────────────────────────────────────────────────────────────────────────────────────────────────
#: bit du plan → nom de `CellNeighbor`, en minuscules, tel que les .tres réels de godot-demo-projects l'écrivent
PEERING = ((TO.N, "top_side"), (TO.NE, "top_right_corner"), (TO.E, "right_side"),
           (TO.SE, "bottom_right_corner"), (TO.S, "bottom_side"), (TO.SW, "bottom_left_corner"),
           (TO.W, "left_side"), (TO.NW, "top_left_corner"))
#: TerrainMode : MATCH_CORNERS_AND_SIDES = 0, MATCH_SIDES = 2 (docs.godotengine.org, relu le 06/10/2026)
MODE_BLOB47, MODE_BLOB16 = 0, 2
ID_SOURCE = "TileSetAtlasSource_dz0"


def ecrire_tres(dossier: Path, meta: dict) -> Path:
    """Le `.tres` Godot 4, dans la forme d'un fichier réellement écrit par Godot (godot-demo-projects, relu) : une
    TileSetAtlasSource, un terrain set, un bit de voisinage par bit POSÉ — l'absent vaut −1, « pas de terrain ». La
    VIDE est déclarée sans terrain. Pas d'`uid://` : Godot en attribue un à l'import. L'atlas est cherché à
    `res://atlas.png` : on pose les deux fichiers à la racine du projet."""
    largeur, hauteur = _taille_tuile(meta)
    colonnes = int(meta["colonnes"])
    aretes = _d_aretes(meta)
    tuiles, vide = _index(meta)
    L = ['[gd_resource type="TileSet" format=3]', "",
         '[ext_resource type="Texture2D" path="res://atlas.png" id="1"]', "",
         f'[sub_resource type="TileSetAtlasSource" id="{ID_SOURCE}"]', 'texture = ExtResource("1")',
         f"texture_region_size = Vector2i({largeur}, {hauteur})"]
    for m, ids in tuiles:
        for i in ids:
            x, y = i % colonnes, i // colonnes
            L += [f"{x}:{y}/0 = 0", f"{x}:{y}/0/terrain_set = 0", f"{x}:{y}/0/terrain = 0"]
            L += [f"{x}:{y}/0/terrains_peering_bit/{nom} = 0" for bit, nom in PEERING
                  if m & bit and (not aretes or bit in ARETES)]
    L.append(f"{vide % colonnes}:{vide // colonnes}/0 = 0")
    L += ["", "[resource]", f"tile_size = Vector2i({largeur}, {hauteur})",
          f"terrain_set_0/mode = {MODE_BLOB16 if aretes else MODE_BLOB47}",
          'terrain_set_0/terrain_0/name = "terrain"', "terrain_set_0/terrain_0/color = Color(0.878, 0.651, 0.251, 1)",
          f'sources/0 = SubResource("{ID_SOURCE}")', ""]
    p = Path(dossier) / "tileset.tres"
    p.write_text("\n".join(L), encoding="utf-8")
    return p


FORMATS = {"tiled": ecrire_tsx, "ldtk": ecrire_ldtk, "godot": ecrire_tres}
