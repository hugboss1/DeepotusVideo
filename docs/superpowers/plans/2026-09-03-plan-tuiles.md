# Game Assets — Tuiles : plan d'implémentation (lot 1 parité, lot 2 différenciant)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** faire du Tile Lab un vrai atelier de tuiles — un jeu blob 47 (ou 16) fabriqué depuis **deux matières**, dont chaque tuile est mesurée contre ses **voisines légales**, exporté vers **Tiled, LDtk et Godot**, avec variantes, aperçu 8×8, trois mesures nommées, tuiles isométriques et hexagonales ; puis (lot 2) une matière du Material Forge comme source, le style d'un lieu de la bible comme prompt, et un peintre minimal qui éprouve le jeu sans quitter l'application.

**Architecture :** tout le calcul est backend, en PIL pur (le python embarqué n'a pas numpy) : `tile_ops.py` (table du blob, masques, assemblage, variantes, auto-tuilage), `tile_metrics.py` (raccord de paires, répétition, éclairage), `tile_shapes.py` (losange 2:1, hexagone à sommet plat), `tile_export.py` (`.tsx`, `.ldtk`, `.tres`), `tile_store.py` (un dossier par jeu sous `outputs/tilesets/<tid>`), et un routeur `tiles_api.py` monté sous `/api/tiles`. Le front `/tilelab` (page autonome, **hors bundle**) gagne des onglets ; **le navigateur voit et manipule, Python écrit** (Pièges hérités) — même la carte du peintre est composée par Python. Chaque banc relit ce qui est écrit : le PNG (PIL), le `.tsx` (`xml.etree`), le `.ldtk` (`json`), le `.tres` (texte), jamais le code.

**Tech Stack :** Python 3.13.15 embarqué + Pillow 12.3.0, **sans numpy** (mesuré le 03/09/2026 : `"$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe" -c "import sys,PIL;print(sys.version.split()[0], PIL.__version__)"` → `3.13.15 12.3.0` ; `importlib.util.find_spec("numpy")` → `None`). FastAPI + `httpx.ASGITransport` pour les bancs de routes. Vanilla JS pour `/tilelab`.

---

## Périmètre

Les bacs de `### R10b. Game Assets — Tuiles — réponses (03/09/2026)` du brief (`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md:1524-1607`) sont le périmètre **exact**. Le lot 1 suit l'ordre des bacs : P1, P2, P3, P4, P5.

| Bac | Tâches | Quoi |
|---|---|---|
| P1 | T1, T2 | jeu blob 47/16 depuis deux matières, masques dessinés par code, raccord contre les voisines **légales** |
| P2 | T3, T4, T5 | exports Tiled `.tsx`, LDtk (`autoRuleGroups`), Godot `.tres` (terrains) — un banc relit chaque fichier |
| P3 | T6 | 1 à 5 variantes par tuile, aperçu 8×8 auto-tuilé à tirage aléatoire |
| P4 | T7 | raccord (existant), répétition (auto-corrélation), éclairage (gradient moyen), seuils nommés |
| P5 | T8 | losange 2:1 et hexagone, raccord testé sur les bords correspondants, et les trois exports étendus |
| — | T9 | l'écran `/tilelab` du lot 1 (onglets Tuile · Jeu · Formes) |
| D1 | T10 | une matière du Material Forge (R10c) devient un tileset |
| D2 | T11 | tuiles au style d'un lieu de la bible (R3) |
| D3 | T12 | peintre minimal avec auto-tiling, export PNG + JSON |
| E1 | — | éditeur de niveaux complet : **exclu**, voir « Écarté » |
| — | T13 | campagne de mutations `backend/tests/mutations_tuiles.py` |

Les liens vers les autres catégories se font **par identifiant, sans replanifier** : T10 consomme l'albedo (`basecolor`) d'une matière telle que `material_store` la range aujourd'hui — les bacs de `### R10c` (P1 delighting, P4 catalogue, D1 générateurs) ne sont **pas** de ce plan ; T11 consomme la planche et la palette d'un lieu de la bible telles qu'elles existent — les bacs de `### R3` (P1 bible relationnelle, P3 multi-références) ne sont **pas** de ce plan.

**Ce qui existe et que l'on réutilise sans le réécrire** (relu le 03/09/2026) :

| Existant | Chemin mesuré | Rôle ici |
|---|---|---|
| `seam_score(img)` | `backend/app/services/pixel_ops.py:180-192` | la métrique 0–100 de raccord d'une tuile avec elle-même |
| `tile_preview(img, grid)` | `backend/app/services/pixel_ops.py:196-212` | pavage 2×2/3×3 plafonné à 512 px |
| `normalize_seamless_opts` / `make_seamless` | `backend/app/services/pixel_ops.py:216-246` et `:306-344` | rend une image raccordable (offset 50/50 + croix + fermeture de boucle, ou miroir 2×2) |
| `pixelate` / `normalize_pixel_opts` | `backend/app/services/pixel_ops.py:60-104` et `:157-177` | le pipeline pixel-art local |
| ops `pixel`, `seamless`, `tile-preview` | `backend/app/api/routes.py:4673-4721` | la route `/images/process` que `/tilelab` appelle déjà |
| `LI.noter(files, source)` | `backend/app/services/library_index.py:65-99` | dépôt de provenance, résilient |
| `materials_root` / `material_dir` / `read_material` / `load_maps` | `backend/app/services/material_store.py:683-688`, `:699-716`, `:843-860`, `:939-949` | lecture d'une matière par `mid` (T10) |
| `_palette_colors(images_path, fnames, n)` | `backend/app/services/board_service.py:173-180` | palette quantifiée d'une planche (T11) |
| `GET /bible/entities?kind=place` | `backend/app/api/routes.py:5109-5119` | la liste des lieux (T11) |
| patron de banc de route | `backend/tests/test_images_process.py:19-98` | env avant import de `app`, `ASGITransport`, stubs `fal_client`/`httpx` |
| patron de campagne de mutations | `backend/tests/mutations_plaque_slicer.py:1-30` et `:360-428` | muter → rouge → remettre à l'octet près |

## Coût de patch

`/tilelab` est **autonome** : servi par `backend/app/main.py:332-355` en `StaticFiles` no-cache, **hors bundle**. Le hub Game Assets du bundle l'affiche déjà dans une iframe `src:"/tilelab/"` (`scripts/patch_bundle_tilelab.py:56-64`, section T-4b). **Aucune tâche de ce plan ne touche `frontend/dist`** ; `scripts/repatch_all.py` n'est **jamais** rejoué. Le seul mécanisme de bundle mobilisé est celui, déjà posé, qui affiche l'iframe.

| Tâche | Bundle | Backend | Front autonome `/tilelab` |
|---|---|---|---|
| T1 table + masques | **0** | `tile_ops.py` (nouveau) | — |
| T2 jeu + store + route | **0** | `tile_ops.py`, `tile_store.py`, `tiles_api.py` (nouveaux), `main.py` (+1 bloc `include_router`), `library_index.py` (+1 source, +1 préfixe) | — |
| T3 export Tiled | **0** | `tile_export.py` (nouveau), `tiles_api.py` | — |
| T4 export LDtk | **0** | `tile_export.py`, `tiles_api.py` | — |
| T5 export Godot | **0** | `tile_export.py`, `tiles_api.py` | — |
| T6 variantes + aperçu | **0** | `tile_ops.py`, `tiles_api.py` | — |
| T7 trois mesures | **0** | `tile_metrics.py` (nouveau), `tiles_api.py` | — |
| T8 iso/hex | **0** | `tile_shapes.py` (nouveau), `tile_export.py`, `tiles_api.py` | — |
| T9 écran lot 1 | **0** | — | `index.html`, `tilelab.css`, `jeu.js` (nouveau) |
| T10 matière → tileset | **0** | `tiles_api.py` (source `materiau`) | `jeu.js` (un sélecteur) |
| T11 style d'un lieu | **0** | `tiles_api.py` (`POST /prompt-lieu`) | `jeu.js` (une boîte de prompt) |
| T12 peintre | **0** | `tiles_api.py` (`POST /{tid}/carte`), `tile_ops.py` | `peintre.js` (nouveau), `index.html` |
| T13 mutations | **0** | `tests/mutations_tuiles.py` (nouveau) | — |

Une seule chose coûterait un patch de bundle et **n'est pas faite** : la chip « Tuiles » du filtre de provenance de la Bibliothèque, dont les libellés sont **codés en dur** dans `scripts/patch_bundle_libprov.py` (mesuré le 03/09). La source `tuiles` est indexée par `library_index.SOURCES` et filtrable par l'API ; la chip est en « Écarté ».

## Références vérifiées

Le souvenir n'est pas une mesure (Pièges hérités). Chaque tâche d'export **commence par relire la doc** avec la commande WebFetch donnée dans la tâche, et **fixe** dans son premier pas le sous-ensemble écrit.

| Source | Commande de relecture | Vérifié le | Ce qui est retenu |
|---|---|---|---|
| doc.mapeditor.org, *TMX Map Format* | `WebFetch https://doc.mapeditor.org/en/stable/reference/tmx-map-format/` | 03/09/2026 | attributs de `<tileset>` : `firstgid, source, name, class, tilewidth, tileheight, spacing, margin, tilecount, columns, objectalignment, tilerendersize, fillmode` ; `<grid orientation width height>` ; `<wangset name class tile>` ; `<wangcolor name class color tile probability>` ; `<wangtile tileid wangid>`. **Ordre du `wangid`** (cité) : « a comma-separated list of indexes (0-254) referring to the Wang colors in the Wang set in the order: **top, top-right, right, bottom-right, bottom, bottom-left, left, top-left** ». `<tile probability>` : « A percentage indicating the probability that this tile is chosen when it competes with others while editing with the terrain tool ». |
| ldtk.io, `JSON_SCHEMA.json` **1.5.3** | `WebFetch https://ldtk.io/files/JSON_SCHEMA.json` | 03/09/2026 | `AutoRuleDef` requis : `size, pattern, tileRectsIds, tileIds (nullable, déprécié depuis 1.5.0), chance, breakOnMatch, flipX, flipY, tileMode (Single|Stamp), active, uid`. `AutoLayerRuleGroup` requis : `uid, name, active, rules, isOptional, collapsed (nullable), color (nullable)`. `TilesetDef` requis : `__cHei, __cWid, customData, enumTags, identifier, padding, pxHei, pxWid, spacing, tags, tileGridSize, uid, savedSelections`. Racine requise : `bgColor, defs, externalLevels, iid, jsonVersion, levels, toc, worlds, appBuildId, backupLimit, backupOnSave, customCommands, defaultEntityHeight, defaultEntityWidth, defaultGridSize, defaultLevelBgColor, defaultPivotX, defaultPivotY, dummyWorldIid, exportLevelBg, exportTiled, flags, identifierStyle, imageExportMode, levelNamePattern, minifyJson, nextUid, simplifiedExport`. `LayerDef` requis : `__type, displayOpacity, gridSize, identifier, intGridValues, intGridValuesGroups, parallaxFactorX, parallaxFactorY, parallaxScaling, pxOffsetX, pxOffsetY, uid, autoRuleGroups, canSelectWhenInactive, excludedTags, guideGridHei, guideGridWid, hideFieldsWhenInactive, hideInList, inactiveOpacity, renderInWorldView, requiredTags, tilePivotX, tilePivotY, type, uiFilterTags, useAsyncRender`. `Level` requis : `__bgColor, __neighbours, fieldInstances, identifier, iid, pxHei, pxWid, uid, worldDepth, worldX, worldY, __smartColor, bgPivotX, bgPivotY, useAutoIdentifier`. |
| deepnight/ldtk, `AutoLayerRuleDef.hx` | `WebFetch https://raw.githubusercontent.com/deepnight/ldtk/master/src/electron.renderer/data/def/AutoLayerRuleDef.hx` | 03/09/2026 | sémantique du `pattern` **citée du code** : `if( pattern[coordId]==0 ) continue;` → **0 = cellule ignorée** ; `if( pattern[coordId]>0 && value != pattern[coordId] ) return false;` → **v > 0 = la cellule DOIT valoir v** ; `if( pattern[coordId]<0 && value == -pattern[coordId] ) return false;` → **−v = la cellule NE DOIT PAS valoir v**. Une constante `Const.AUTO_LAYER_ANYTHING` existe mais **n'est pas définie dans ce fichier** : ce plan ne s'en sert pas (les valeurs 0, 1 et −1 suffisent). |
| docs.godotengine.org, `class_tileset.html` | `WebFetch https://docs.godotengine.org/en/stable/classes/class_tileset.html` | 03/09/2026 | `TileShape` SQUARE=0, ISOMETRIC=1, HALF_OFFSET_SQUARE=2, HEXAGON=3 ; `TileLayout` STACKED=0, STACKED_OFFSET=1, STAIRS_RIGHT=2, STAIRS_DOWN=3, DIAMOND_RIGHT=4, DIAMOND_DOWN=5 ; `TileOffsetAxis` HORIZONTAL=0, VERTICAL=1 ; `TerrainMode` MATCH_CORNERS_AND_SIDES=0, MATCH_CORNERS=1, MATCH_SIDES=2 ; propriétés `tile_shape`, `tile_layout`, `tile_size` (`Vector2i(16,16)` par défaut), `tile_offset_axis`. |
| docs.godotengine.org, enum `CellNeighbor` | `WebFetch https://docs.godotengine.org/en/stable/classes/class_tileset.html#enum-tileset-cellneighbor` | 03/09/2026 | RIGHT_SIDE=0, RIGHT_CORNER=1, BOTTOM_RIGHT_SIDE=2, BOTTOM_RIGHT_CORNER=3, BOTTOM_SIDE=4, BOTTOM_CORNER=5, BOTTOM_LEFT_SIDE=6, BOTTOM_LEFT_CORNER=7, LEFT_SIDE=8, LEFT_CORNER=9, TOP_LEFT_SIDE=10, TOP_LEFT_CORNER=11, TOP_SIDE=12, TOP_CORNER=13, TOP_RIGHT_SIDE=14, TOP_RIGHT_CORNER=15. |
| godot-demo-projects, `2d/skeleton/level/tileset/tileset.tres` | `WebFetch https://raw.githubusercontent.com/godotengine/godot-demo-projects/master/2d/skeleton/level/tileset/tileset.tres` | 03/09/2026 | **fichier réel écrit par Godot 4** : en-tête `[gd_resource type="TileSet" format=3 uid="…"]` ; par tuile `X:Y/0/terrain_set = 0`, `X:Y/0/terrain = 0`, puis **seulement les bits posés** parmi `terrains_peering_bit/right_side`, `bottom_right_corner`, `bottom_side`, `bottom_left_corner`, `left_side`, `top_left_corner`, `top_side`, `top_right_corner` ; `texture_region_size = Vector2i(32, 32)` ; dans `[resource]` : `tile_size = Vector2i(32, 32)`, `terrain_set_0/mode = 0`, `terrain_set_0/terrain_0/name = "Terrain 0"`, `terrain_set_0/terrain_0/color = Color(0.5, 0.34375, 0.25, 1)`, `sources/1 = SubResource("TileSetAtlasSource_v5kxh")`. |
| godot-demo-projects, `2d/isometric/tileset/tileset.tres` | `WebFetch https://raw.githubusercontent.com/godotengine/godot-demo-projects/master/2d/isometric/tileset/tileset.tres` | 03/09/2026 | iso réel : `tile_shape = 1`, `tile_layout = 5`, `tile_size = Vector2i(128, 64)` (**2:1**) ; `[sub_resource type="TileSetAtlasSource"]` avec `texture = ExtResource("1")`, `margins = Vector2i(…)`, `texture_region_size = Vector2i(…)`, `0:0/0 = 0`. |
| godot-demo-projects, `2d/hexagonal_map/tileset.tres` | `WebFetch https://raw.githubusercontent.com/godotengine/godot-demo-projects/master/2d/hexagonal_map/tileset.tres` | 03/09/2026 | hex réel : `tile_shape = 3`, `tile_offset_axis = 1`, `tile_size = Vector2i(110, 94)`. Le rapport 110/94 = 1,170 est celui d'un hexagone **à sommet plat** (2/√3 = 1,1547) : `tile_offset_axis = 1` (VERTICAL) ⇒ hexagones à sommet plat rangés en colonnes. C'est la forme retenue en T8. |
| boristhebrave.com, *Tileset Roundup* | `WebFetch https://www.boristhebrave.com/2013/07/14/tileset-roundup/` | 03/09/2026 | cité : le blob « uses 48 tiles – 47 solid and 1 empty » ; « The corner tiles are only relevant if both edge tiles are solid, so I mark them as empty in any other case » ; bits de l'article : `topLeft + 2*top + 4*topRight + 8*left + 16*right + 32*bottomLeft + 64*bottom + 128*bottomRight`. |
| cr31.co.uk (blob/Wang) | `WebFetch https://www.cr31.co.uk/stagecast/wang/blob.html` | 03/09/2026 | **page vide à la lecture** — cr31 reste « de mémoire » et **ne sert pas d'argument**. Le 47 est établi par boristhebrave *et* par le dénombrement mesuré ci-dessous. |

### La numérotation, FIXÉE par ce plan

Ce plan **n'adopte pas** l'ordre de bits de boristhebrave. Il fixe l'ordre **horaire depuis le nord**, identique au `wangid` de Tiled — ce qui rend l'export Tiled une lecture bit à bit et évite une table de conversion :

| Bit | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|---|---|---|
| Nom | `N` | `NE` | `E` | `SE` | `S` | `SW` | `W` | `NW` |
| Tiled `wangid`, position | 1 top | 2 top-right | 3 right | 4 bottom-right | 5 bottom | 6 bottom-left | 7 left | 8 top-left |
| Godot `terrains_peering_bit/` | `top_side` | `top_right_corner` | `right_side` | `bottom_right_corner` | `bottom_side` | `bottom_left_corner` | `left_side` | `top_left_corner` |

Un bit de coin n'est retenu que si **ses deux arêtes adjacentes** sont posées (règle de boristhebrave, citée ci-dessus). Dénombrement : 1 (aucune arête) + 4 (une) + 4×2 (deux adjacentes) + 2 (deux opposées) + 4×4 (trois) + 16 (quatre) = **47**, plus la 48ᵉ tuile **vide**.

**Table BLOB47** (mesurée le 03/09 en exécutant `canon` sur 0..255 avec le python embarqué) :

```
0, 1, 4, 5, 7, 16, 17, 20, 21, 23, 28, 29, 31, 64, 65, 68, 69, 71, 80, 81,
84, 85, 87, 92, 93, 95, 112, 113, 116, 117, 119, 124, 125, 127, 193, 197,
199, 209, 213, 215, 221, 223, 241, 245, 247, 253, 255
```

**Table BLOB16** (arêtes seules, `m & (N|E|S|W)`) :

```
0, 1, 4, 5, 16, 17, 20, 21, 64, 65, 68, 69, 80, 81, 84, 85
```

### La garantie de raccord, FIXÉE par ce plan

L'anneau extérieur du masque (bande de `b = cote // 8` px) ne dépend **que des arêtes** : les quatre bandes valent leur bit d'arête, et les **quatre carrés de coin de l'anneau valent le OU des deux arêtes adjacentes**. Conséquence démontrable : pour deux voisines légales (chacune a le bit qui pointe vers l'autre), la colonne partagée est **entièrement matière A des deux côtés**, donc le raccord vaut exactement le raccord de la matière avec elle-même — **0,00 pour une matière miroir**. Le bit de coin, lui, ne façonne qu'une **encoche strictement intérieure** à l'anneau. Mesuré le 03/09 sur un prototype exécuté par le python embarqué : **1156 paires E légales et 1156 paires S légales, raccord maximal `0.0`** ; les 47 masques sont **deux à deux distincts**.

## Structure des fichiers

| Fichier | Responsabilité unique |
|---|---|
| `backend/app/services/tile_ops.py` (créer) | `N…NW`, `ORDRE`, `COINS`, `canon`, `BLOB47`, `BLOB16`, `index_de`, `masque_blob`, `masque_coeur`, `varier`, `assembler_jeu`, `atlas`, `carte_aleatoire`, `masque_voisins`, `composer_carte` |
| `backend/app/services/tile_metrics.py` (créer) | `seam_pair`, `paires_legales`, `raccord_jeu`, `repetition_score`, `eclairage_score`, `eclairage_jeu`, `SEUILS`, `verdict` |
| `backend/app/services/tile_shapes.py` (créer) | `dims_iso`, `dims_hex`, `DEC_ISO`, `DEC_HEX`, `masque_forme`, `texture_forme`, `seam_forme` |
| `backend/app/services/tile_export.py` (créer) | `ecrire_tsx`, `ecrire_ldtk`, `ecrire_tres` |
| `backend/app/services/tile_store.py` (créer) | `tilesets_root`, `is_valid_tid`, `new_tid`, `tileset_dir`, `write_meta`, `read_meta`, `list_tilesets` |
| `backend/app/services/tiles_api.py` (créer) | le routeur `/api/tiles` — une porte pour toutes les routes de tuiles |
| `backend/app/main.py:224-231` (modifier) | +1 bloc `__DZ_TILES_ROUTER_BEGIN__ / END__`, même patron que `__DZ_CARDS_ROUTER_*` |
| `backend/app/services/library_index.py:24-38` et `:43-51` (modifier) | +1 entrée `"tuiles"` dans `SOURCES`, +1 préfixe `("tile_", "tuiles")` |
| `frontend/tilelab/index.html:16-113` (modifier) | barre d'onglets + panneaux Jeu / Formes / Peintre |
| `frontend/tilelab/tilelab.css` (modifier) | styles des onglets, de la grille de tuiles, du peintre |
| `frontend/tilelab/jeu.js` (créer) | onglets Jeu et Formes : appels `/api/tiles`, vignettes, mesures, exports |
| `frontend/tilelab/peintre.js` (créer) | onglet Peintre : grille cliquable, POST de la grille, affichage du PNG rendu par Python |
| `backend/tests/test_tuiles.py` (créer) | ops, mesures, formes, store, routes, front en miroir |
| `backend/tests/test_tuiles_exports.py` (créer) | les trois fichiers écrits, relus par `xml.etree`, `json` et texte |
| `backend/tests/mutations_tuiles.py` (créer) | la campagne de mutations |

## Conventions des bancs

- **Scripts autonomes**, un processus par fichier : `python tests/test_tuiles.py` **depuis `backend/`**. Jamais `pytest tests`. UTF-8 forcé (`sys.stdout.reconfigure(encoding="utf-8")`).
- Les fonctions `test_*` sont au niveau module et un `_main()` en pied les lance : `scripts/run-tests.ps1` voit `^\s*def test_` et lance donc `pytest tests/test_tuiles.py` (un processus, le fichier seul), tandis que la campagne de mutations (T13) lance le script et lit ses lignes `FAIL <nom>`. Les deux voies donnent le même verdict.
- L'environnement (`DATABASE_URL`, `IMAGES_FOLDER`, `OUTPUTS_FOLDER`) est posé **avant tout import de `app`** — patron mesuré à `backend/tests/test_images_process.py:19-27`.
- **Bancs-miroirs, trois temps** : relire le PNG écrit (PIL), le `.tsx` (`xml.etree.ElementTree`), le `.ldtk` (`json`), le `.tres` (texte) — jamais le code qui prétend les produire ; vérifier que la surface lue est la vraie (le fichier sur disque, pas la réponse HTTP) ; **compter les assertions**, pas les noms de tests. Pour le front vanilla, le dépôt épingle des marqueurs dans le texte des fichiers (patron `backend/tests/test_etabli_canevas.py:1-10`) — c'est une mesure faible, elle est dite comme telle dans « Incertitudes ».
- Textures de banc **déterministes** : `_bruit` (bruit `random.Random` en miroir 2×2 — raccord exactement 0), `_rampe` (dégradé horizontal), `_uni`.

**Squelette commun**, à recopier tel quel en tête de `test_tuiles.py` **et** de `test_tuiles_exports.py` :

```python
# -*- coding: utf-8 -*-
"""Tuiles — lot 1 et lot 2 (plan 2026-09-03-plan-tuiles).
Run: python tests/test_tuiles.py   (depuis backend/)"""
import asyncio
import io
import json
import math
import os
import pathlib
import random
import sys
import tempfile
import traceback

sys.stdout.reconfigure(encoding="utf-8")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ.setdefault("FAL_KEY", "test-key")
pathlib.Path(_tmp, "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageChops, ImageStat            # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"


def _bruit(s=64, seed=1):
    """Bruit en MIROIR 2x2 : raccord exactement 0, donc tout raccord non nul
    mesuré plus loin vient des masques, jamais de la matière."""
    rng = random.Random(seed)
    h = s // 2
    q = Image.frombytes("RGB", (h, h),
                        bytes(rng.randrange(256) for _ in range(h * h * 3)))
    out = Image.new("RGB", (s, s))
    out.paste(q, (0, 0))
    out.paste(q.transpose(Image.FLIP_LEFT_RIGHT), (h, 0))
    out.paste(q.transpose(Image.FLIP_TOP_BOTTOM), (0, h))
    out.paste(q.transpose(Image.ROTATE_180), (h, h))
    return out


def _rampe(s=64):
    return Image.frombytes(
        "L", (s, 1), bytes(int(255 * x / (s - 1)) for x in range(s))
    ).resize((s, s)).convert("RGB")


def _uni(s=64, rgb=(120, 120, 120)):
    return Image.new("RGB", (s, s), rgb)


def _main():
    rouges = 0
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", nom)
            except Exception:
                rouges += 1
                print("FAIL", nom)
                traceback.print_exc()
    print(f"{'ROUGE' if rouges else 'OK'} — {rouges} echec(s)")
    sys.exit(1 if rouges else 0)
```

et en pied de fichier :

```python
if __name__ == "__main__":
    _main()
```

**Convention de commit** (tous les commits de ce plan) : sujet **sans accents**, corps accentué qui dit le POURQUOI **avec la mesure**, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, **aucun guillemet double** dans les `-m` (arguments en apostrophes simples).

---

## Lot 1 — parité

### Task 1 (P1a) : la table du blob et les masques dessinés par PIL

**Pourquoi, avec la mesure :** le brief dit « blob 47 (ou 16) » et ajoute que le nombre 47 est « de mémoire, non vérifié — à confirmer contre la référence au moment du plan ». On le confirme donc deux fois : par une lecture publique, et par un dénombrement exécuté. Et l'on fixe l'anneau de sorte que le raccord des voisines légales soit **exactement 0** — mesuré, pas espéré.

**Files:**
- Create: `backend/app/services/tile_ops.py`
- Create: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : relire la référence publique du blob et FIXER la numérotation**

Lancer exactement :

```
WebFetch https://www.boristhebrave.com/2013/07/14/tileset-roundup/
prompt: Quote exactly what the article says about the "blob" tileset: how many tiles it has, whether an empty tile is included, the rule about corner tiles, and the bit values assigned to each of the 8 neighbours.
```

Attendu (mesuré le 03/09/2026) : « uses 48 tiles – 47 solid and 1 empty » ; « The corner tiles are only relevant if both edge tiles are solid, so I mark them as empty in any other case » ; bits `topLeft + 2*top + 4*topRight + 8*left + 16*right + 32*bottomLeft + 64*bottom + 128*bottomRight`.

Si la page a changé : **ne pas modifier** le plan, écrire la divergence dans le message de commit et garder la numérotation de ce plan (elle est justifiée par l'alignement sur `wangid`, pas par l'article). La numérotation retenue reste celle du tableau « La numérotation, FIXÉE par ce plan » ci-dessus : `N=1, NE=2, E=4, SE=8, S=16, SW=32, W=64, NW=128`.

- [ ] **Step 2 : écrire le banc qui échoue — table, masques, raccord des paires légales**

Créer `backend/tests/test_tuiles.py` avec le **squelette commun** (section « Conventions des bancs ») puis, à la suite :

```python
from app.services import tile_ops as TO                  # noqa: E402


def test_table_du_blob_vaut_47_et_16():
    """47 masques canoniques, 16 en arêtes seules — le dénombrement du plan."""
    assert len(TO.BLOB47) == 47, len(TO.BLOB47)
    assert len(TO.BLOB16) == 16, len(TO.BLOB16)
    assert TO.BLOB47 == sorted(set(TO.BLOB47))
    assert TO.BLOB47[0] == 0 and TO.BLOB47[-1] == 255
    assert TO.BLOB16 == [0, 1, 4, 5, 16, 17, 20, 21,
                         64, 65, 68, 69, 80, 81, 84, 85], TO.BLOB16
    # la numérotation FIXÉE : horaire depuis le nord, ordre du wangid Tiled
    assert TO.ORDRE == ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    assert (TO.N, TO.NE, TO.E, TO.SE, TO.S, TO.SW, TO.W, TO.NW) == \
        (1, 2, 4, 8, 16, 32, 64, 128)


def test_canon_ote_un_coin_sans_ses_deux_aretes():
    """Règle citée de boristhebrave : un coin ne compte que si les deux
    arêtes adjacentes sont posées."""
    assert TO.canon(TO.NE) == 0                      # NE seul : effacé
    assert TO.canon(TO.N | TO.NE) == TO.N            # une seule arête
    assert TO.canon(TO.N | TO.E | TO.NE) == TO.N | TO.E | TO.NE   # gardé
    assert TO.canon(TO.N | TO.E) == TO.N | TO.E      # sans le coin : inchangé
    assert TO.canon(255) == 255
    # canon est idempotent et stable sur les 256 voisinages
    for m in range(256):
        assert TO.canon(TO.canon(m)) == TO.canon(m), m
    assert {TO.canon(m) for m in range(256)} == set(TO.BLOB47)


def test_index_de_est_une_bijection_sur_la_table():
    for i, m in enumerate(TO.BLOB47):
        assert TO.index_de(m, "blob47") == i, (i, m)
    assert TO.index_de(TO.NE, "blob47") == 0          # canonisé vers 0
    assert TO.index_de(TO.N | TO.E, "blob16") == TO.BLOB16.index(TO.N | TO.E)


def test_47_masques_deux_a_deux_distincts():
    """Un masque par entrée de table : si deux se confondent, le jeu ment."""
    vus = {TO.masque_blob(m, 64).tobytes() for m in TO.BLOB47}
    assert len(vus) == 47, len(vus)
    plein = TO.masque_blob(255, 64)
    assert plein.getextrema() == (255, 255)           # tout entouré : plein
    isole = TO.masque_blob(0, 64)
    assert isole.getpixel((0, 0)) == 0                # isolée : anneau ouvert
    assert isole.getpixel((32, 32)) == 255            # noyau toujours plein


def test_anneau_ne_depend_que_des_aretes():
    """L'anneau (b px) : bandes = bit d'arête, coins = OU des deux arêtes.
    C'est CE choix qui rend le raccord des voisines légales exactement 0."""
    cote, b = 64, 8
    for m in TO.BLOB47:
        mq = TO.masque_blob(m, cote)
        px = mq.load()
        attendu_e = 255 if (m & TO.E) else 0
        for y in range(b, cote - b):
            assert px[cote - 1, y] == attendu_e, (m, y)
        attendu_n = 255 if (m & TO.N) else 0
        for x in range(b, cote - b):
            assert px[x, 0] == attendu_n, (m, x)
        coin_ne = 255 if (m & TO.N or m & TO.E) else 0
        assert px[cote - 1, 0] == coin_ne, m


def test_raccord_des_paires_legales_est_nul():
    """LA mesure de P1 : chaque tuile contre ses voisines LÉGALES, pas contre
    elle-même. 1156 paires E et 1156 paires S, raccord max 0.00 (mesuré)."""
    A, B = _bruit(64, 1), _bruit(64, 2)
    tuiles = {m: Image.composite(A, B, TO.masque_blob(m, 64))
              for m in TO.BLOB47}

    def _seam(a, b, sens):
        w, h = a.size
        if sens == "E":
            x, y = a.crop((w - 1, 0, w, h)), b.crop((0, 0, 1, h))
        else:
            x, y = a.crop((0, h - 1, w, h)), b.crop((0, 0, w, 1))
        d = ImageStat.Stat(ImageChops.difference(x, y)).mean
        return sum(d) / len(d) / 255 * 100

    n_e = n_s = 0
    for ma, ta in tuiles.items():
        for mb, tb in tuiles.items():
            if (ma & TO.E) and (mb & TO.W):
                assert _seam(ta, tb, "E") == 0.0, (ma, mb)
                n_e += 1
            if (ma & TO.S) and (mb & TO.N):
                assert _seam(ta, tb, "S") == 0.0, (ma, mb)
                n_s += 1
    assert n_e == 1156, n_e
    assert n_s == 1156, n_s
```

- [ ] **Step 3 : lancer le banc, vérifier qu'il échoue**

Run (depuis `backend/`) : `python tests/test_tuiles.py`

Expected : `ModuleNotFoundError: No module named 'app.services.tile_ops'` — le fichier n'existe pas encore.

- [ ] **Step 4 : écrire `tile_ops.py` (table + masques)**

Créer `backend/app/services/tile_ops.py` :

```python
# -*- coding: utf-8 -*-
"""Tuiles raccordables : table du blob, masques, assemblage (plan
2026-09-03-plan-tuiles, P1).

NUMÉROTATION FIXÉE PAR LE PLAN — horaire depuis le nord :
    N=1, NE=2, E=4, SE=8, S=16, SW=32, W=64, NW=128
C'est exactement l'ordre du `wangid` de Tiled (« top, top-right, right,
bottom-right, bottom, bottom-left, left, top-left », doc.mapeditor.org lu le
03/09/2026), ce qui rend l'export Tiled une lecture bit à bit.

Un bit de COIN n'est retenu que si ses DEUX arêtes adjacentes sont posées
(règle citée de boristhebrave, 03/09/2026) : 47 voisinages distincts, plus la
48e tuile VIDE.

GARANTIE DE RACCORD : l'anneau extérieur (bande de `cote // 8` px) ne dépend
QUE des arêtes — les quatre bandes valent leur bit, les quatre carrés de coin
valent le OU des deux arêtes adjacentes. Deux voisines légales (chacune a le
bit qui pointe vers l'autre) présentent donc, sur la colonne partagée, de la
matière A des deux côtés : le raccord vaut celui de la matière avec elle-même,
soit 0.00 pour une matière miroir (mesuré : 1156 paires E, 1156 paires S,
max 0.0). Le bit de coin ne façonne qu'une ENCOCHE strictement intérieure.

PIL pur : le python embarqué n'a pas numpy (mesuré le 03/09).
"""
from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter

N, NE, E, SE, S, SW, W, NW = 1, 2, 4, 8, 16, 32, 64, 128
ORDRE = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
BITS = (N, NE, E, SE, S, SW, W, NW)
#: (bit du coin, arête A, arête B) — le coin ne vit que si A ET B sont posées
COINS = ((NE, N, E), (SE, E, S), (SW, S, W), (NW, W, N))
#: (nom, dx, dy, bit) — dx/dy en cases, y vers le bas
DIRS = (("N", 0, -1, N), ("NE", 1, -1, NE), ("E", 1, 0, E), ("SE", 1, 1, SE),
        ("S", 0, 1, S), ("SW", -1, 1, SW), ("W", -1, 0, W), ("NW", -1, -1, NW))

JEUX = ("blob47", "blob16")


def canon(m) -> int:
    """Voisinage 0..255 ramené à sa forme canonique."""
    m = int(m) & 255
    for coin, a, b in COINS:
        if m & coin and not (m & a and m & b):
            m &= ~coin
    return m & 255


BLOB47 = sorted({canon(m) for m in range(256)})
BLOB16 = sorted({m & (N | E | S | W) for m in range(256)})
TABLES = {"blob47": BLOB47, "blob16": BLOB16}
_INDEX = {jeu: {m: i for i, m in enumerate(t)} for jeu, t in TABLES.items()}


def cles(jeu: str = "blob47") -> list[int]:
    if jeu not in TABLES:
        raise ValueError(f"jeu inconnu: {jeu!r} (attendu {', '.join(JEUX)})")
    return TABLES[jeu]


def index_de(m, jeu: str = "blob47") -> int:
    """Index de tuile (0..46 ou 0..15) d'un voisinage quelconque."""
    m = canon(m) if jeu == "blob47" else (int(m) & (N | E | S | W))
    return _INDEX[jeu][m]


def masque_blob(m, cote: int = 64) -> Image.Image:
    """Masque « L » : 255 = matière A (terrain), 0 = matière B (fond)."""
    m = canon(m)
    b = max(2, cote // 8)
    r = max(2, cote // 6)
    im = Image.new("L", (cote, cote), 0)
    d = ImageDraw.Draw(im)
    d.rectangle((b, b, cote - b - 1, cote - b - 1), fill=255)      # le noyau
    if m & N:
        d.rectangle((b, 0, cote - b - 1, b - 1), fill=255)
    if m & S:
        d.rectangle((b, cote - b, cote - b - 1, cote - 1), fill=255)
    if m & W:
        d.rectangle((0, b, b - 1, cote - b - 1), fill=255)
    if m & E:
        d.rectangle((cote - b, b, cote - 1, cote - b - 1), fill=255)
    # carrés de coin de l'anneau = OU des deux arêtes : c'est CE choix qui
    # rend la colonne partagée de deux voisines légales entièrement pleine
    if m & N or m & E:
        d.rectangle((cote - b, 0, cote - 1, b - 1), fill=255)
    if m & S or m & E:
        d.rectangle((cote - b, cote - b, cote - 1, cote - 1), fill=255)
    if m & S or m & W:
        d.rectangle((0, cote - b, b - 1, cote - 1), fill=255)
    if m & N or m & W:
        d.rectangle((0, 0, b - 1, b - 1), fill=255)
    # encoche du coin diagonal ABSENT — strictement à l'intérieur de l'anneau,
    # donc invisible pour le raccord
    for bit, a, c, (cx, cy) in ((NE, N, E, (cote - b - r, b + r)),
                                (SE, E, S, (cote - b - r, cote - b - r)),
                                (SW, S, W, (b + r, cote - b - r)),
                                (NW, W, N, (b + r, b + r))):
        if (m & a) and (m & c) and not (m & bit):
            d.ellipse((cx - r, cy - r, cx + r - 1, cy + r - 1), fill=0)
    return im


def masque_coeur(cote: int = 64) -> Image.Image:
    """Masque des VARIANTES (P3) : 255 au centre, 0 DUR sur l'anneau de
    `cote // 8` px. Une variante ne touche donc jamais le bord et le raccord
    des paires légales reste exactement 0 (mesuré sur 10404 paires)."""
    b = max(2, cote // 8)
    m = Image.new("L", (cote, cote), 0)
    ImageDraw.Draw(m).rectangle((2 * b, 2 * b, cote - 2 * b - 1,
                                 cote - 2 * b - 1), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(b / 2))
    # le flou bave de ~3/255 sur l'anneau (mesuré) : on le remet à 0 DUR
    d = ImageDraw.Draw(m)
    d.rectangle((0, 0, cote - 1, b - 1), fill=0)
    d.rectangle((0, cote - b, cote - 1, cote - 1), fill=0)
    d.rectangle((0, 0, b - 1, cote - 1), fill=0)
    d.rectangle((cote - b, 0, cote - 1, cote - 1), fill=0)
    return m


def varier(mat: Image.Image, coeur: Image.Image, dx: int,
           dy: int) -> Image.Image:
    """Matière perturbée par un décalage cyclique, mais SEULEMENT au cœur."""
    return Image.composite(ImageChops.offset(mat, dx, dy), mat, coeur)
```

- [ ] **Step 5 : lancer le banc, vérifier qu'il passe**

Run (depuis `backend/`) : `python tests/test_tuiles.py`

Expected :

```
PASS test_47_masques_deux_a_deux_distincts
PASS test_anneau_ne_depend_que_des_aretes
PASS test_canon_ote_un_coin_sans_ses_deux_aretes
PASS test_index_de_est_une_bijection_sur_la_table
PASS test_raccord_des_paires_legales_est_nul
PASS test_table_du_blob_vaut_47_et_16
OK — 0 echec(s)
```

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tile_ops.py backend/tests/test_tuiles.py
git commit -m 'tuiles : la table du blob 47 et les masques dessines par PIL' -m 'La reference publique (boristhebrave, relue le 03/09) dit 48 tuiles, 47 pleines et une vide, et qu un coin ne compte que si ses deux aretes adjacentes sont posees. Le denombrement execute sur les 256 voisinages rend exactement 47 formes canoniques : la table est mesuree, pas recopiee. La numerotation est fixee horaire depuis le nord, dans l ordre meme du wangid de Tiled, pour que l export soit une lecture bit a bit. Enfin l anneau exterieur ne depend QUE des aretes (les coins de l anneau valent le OU des deux aretes) : les 1156 paires E et les 1156 paires S legales raccordent a 0.00 mesure, et le bit de coin ne faconne qu une encoche interieure.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 2 (P1b) : le jeu depuis deux matières, son dossier, sa route

**Pourquoi, avec la mesure :** un jeu de tuiles n'est utile que rangé et servi. Le dépôt range déjà les matières en « un dossier par objet » (`material_store.materials_root()` = `settings.outputs_path / "materials"`, mesuré) ; les tuiles suivent le même patron. La route rend l'atlas et **la mesure du raccord du jeu entier**, pas une promesse.

**Files:**
- Create: `backend/app/services/tile_store.py`
- Create: `backend/app/services/tiles_api.py`
- Modify: `backend/app/services/tile_ops.py` (ajout de `assembler_jeu` et `atlas`)
- Modify: `backend/app/main.py:224-231`
- Modify: `backend/app/services/library_index.py:24-38` et `:43-51`
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc qui échoue — assemblage, store, route**

Ajouter à `backend/tests/test_tuiles.py` :

```python
from app.services import tile_store as TS                # noqa: E402


def test_assembler_jeu_rend_47_tuiles_plus_la_vide():
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, jeu="blob47", cote=64, variantes=1)
    assert jeu["jeu"] == "blob47"
    assert jeu["variantes"] == 1
    assert len(jeu["tuiles"]) == 48, len(jeu["tuiles"])   # 47 + la vide
    assert jeu["vide"] == 47
    assert all(t.size == (64, 64) for t in jeu["tuiles"])
    # la 48e est la matière B nue : c'est la case sans terrain
    assert jeu["tuiles"][47].tobytes() == B.resize((64, 64),
                                                   Image.LANCZOS).tobytes()
    j16 = TO.assembler_jeu(A, B, jeu="blob16", cote=32, variantes=1)
    assert len(j16["tuiles"]) == 17, len(j16["tuiles"])
    assert j16["vide"] == 16


def test_atlas_range_les_tuiles_en_colonnes_fixes():
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 64, 1)
    img, colonnes, rangees = TO.atlas(jeu)
    assert colonnes == 8 and rangees == 6                 # 48 = 8 x 6
    assert img.size == (8 * 64, 6 * 64)
    # la tuile d'index 0 est en haut à gauche, la 47e en bas à droite
    assert img.crop((0, 0, 64, 64)).tobytes() == \
        jeu["tuiles"][0].convert("RGB").tobytes()
    assert img.crop((7 * 64, 5 * 64, 8 * 64, 6 * 64)).tobytes() == \
        jeu["tuiles"][47].convert("RGB").tobytes()


def test_store_refuse_un_tid_hors_motif():
    assert TS.is_valid_tid("tile_0123abcd")
    for mauvais in ("tile_XYZ", "../etc", "tile_0123abc", "", None,
                    "tile_0123abcd/x"):
        assert not TS.is_valid_tid(mauvais), mauvais
    # `tileset_dir` refuse par le MOTIF, pas seulement par le confinement :
    # `tile_XYZ` resterait sous la racine, et passerait si l'on n'avait que
    # la ceinture du confinement.
    for mauvais in ("../evasion", "tile_XYZ", "tile_0123abc",
                    "TILE_0123ABCD"):
        try:
            TS.tileset_dir(mauvais)
        except ValueError:
            continue
        raise AssertionError(f"tileset_dir a accepte {mauvais!r}")


def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _poser_image(nom, img):
    from app.config import settings
    img.save(settings.images_path / nom, "PNG")
    return nom


def test_route_jeu_ecrit_un_dossier_lisible():
    """Banc-miroir : on relit l'atlas SUR DISQUE avec PIL, pas la réponse."""
    from app.config import settings
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("tuile_a.png", _bruit(128, 1))
        b = _poser_image("tuile_b.png", _bruit(128, 2))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": a}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 64, "variantes": 1, "nom": "banc"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert TS.is_valid_tid(d["tid"]), d
            assert d["tuiles"] == 48 and d["colonnes"] == 8
            assert d["raccord"] == 0.0, d["raccord"]
            # le fichier ÉCRIT, relu par PIL
            dossier = TS.tileset_dir(d["tid"])
            with Image.open(dossier / "atlas.png") as im:
                assert im.size == (8 * 64, 6 * 64), im.size
            meta = json.loads((dossier / "meta.json").read_text("utf-8"))
            assert meta["jeu"] == "blob47" and meta["cote"] == 64
            assert meta["cles"] == TO.BLOB47
            # servi par la route de fichier
            r2 = await c.get(f"/api/tiles/{d['tid']}/fichier/atlas.png")
            assert r2.status_code == 200 and r2.content[:8] == b"\x89PNG\r\n\x1a\n"
            # et listé
            r3 = await c.get("/api/tiles")
            assert any(x["tid"] == d["tid"] for x in r3.json()["tilesets"])
            # une source inconnue est refusée en le disant
            r4 = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": "absente.png"},
                "matiere_b": {"image": b}})
            assert r4.status_code == 400 and "absente.png" in r4.text
            r5 = await c.get("/api/tiles/tile_zzzzzzzz/fichier/atlas.png")
            assert r5.status_code == 404, r5.text
            # un nom hors liste blanche est refusé MÊME si le fichier existe
            (dossier / "secret.txt").write_text("x", encoding="utf-8")
            r6 = await c.get(f"/api/tiles/{d['tid']}/fichier/secret.txt")
            assert r6.status_code == 404, r6.text
            assert "inconnu" in r6.text.lower(), r6.text

    asyncio.run(scenario())


def test_provenance_des_tuiles_est_declaree():
    from app.services import library_index as LI
    assert LI.SOURCES.get("tuiles") == "Tile Lab"
    assert LI.heuristique("tile_0123abcd_atlas.png") == "tuiles"
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_assembler_jeu_rend_47_tuiles_plus_la_vide` avec `AttributeError: module 'app.services.tile_ops' has no attribute 'assembler_jeu'`, plus `FAIL test_store_refuse_un_tid_hors_motif`, `FAIL test_route_jeu_ecrit_un_dossier_lisible`, `FAIL test_provenance_des_tuiles_est_declaree`, et en pied `ROUGE — 4 echec(s)`.

- [ ] **Step 3 : ajouter `assembler_jeu` et `atlas` à `tile_ops.py`**

Ajouter à la fin de `backend/app/services/tile_ops.py` :

```python
def assembler_jeu(mat_a: Image.Image, mat_b: Image.Image, jeu: str = "blob47",
                  cote: int = 64, variantes: int = 1,
                  graine: int = 1) -> dict:
    """Le jeu complet : `len(cles) * variantes` tuiles + la tuile VIDE.

    L'index d'une tuile est `index_de(m) * variantes + k` ; la VIDE est la
    dernière (`len(cles) * variantes`). Les variantes ne touchent que le cœur
    (masque_coeur), donc le raccord des paires légales reste 0.00 (mesuré sur
    10404 paires E avec 3 variantes)."""
    import random as _random

    table = cles(jeu)
    variantes = max(1, min(5, int(variantes)))
    cote = max(16, min(512, int(cote)))
    A = mat_a.convert("RGB").resize((cote, cote), Image.LANCZOS)
    B = mat_b.convert("RGB").resize((cote, cote), Image.LANCZOS)
    coeur = masque_coeur(cote)
    rng = _random.Random(int(graine))
    tuiles: list[Image.Image] = []
    for m in table:
        mq = masque_blob(m, cote)
        for k in range(variantes):
            if k == 0:
                a, b = A, B
            else:
                dx, dy = rng.randrange(cote), rng.randrange(cote)
                a, b = varier(A, coeur, dx, dy), varier(B, coeur, dx, dy)
            tuiles.append(Image.composite(a, b, mq))
    tuiles.append(B.copy())                       # la tuile VIDE, sans terrain
    return {"jeu": jeu, "cles": list(table), "cote": cote,
            "variantes": variantes, "graine": int(graine),
            "tuiles": tuiles, "vide": len(table) * variantes}


def atlas(jeu: dict, colonnes: int = 0):
    """(image RGB, colonnes, rangées). 8 colonnes par défaut pour blob47
    (48 = 8 x 6, la VIDE tombe pile en bas à droite), 4 pour blob16."""
    n = len(jeu["tuiles"])
    if not colonnes:
        colonnes = 8 if jeu["jeu"] == "blob47" else 4
    colonnes = max(1, int(colonnes))
    rangees = (n + colonnes - 1) // colonnes
    cote = jeu["cote"]
    img = Image.new("RGB", (colonnes * cote, rangees * cote), (0, 0, 0))
    for i, t in enumerate(jeu["tuiles"]):
        img.paste(t.convert("RGB"), ((i % colonnes) * cote,
                                     (i // colonnes) * cote))
    return img, colonnes, rangees
```

- [ ] **Step 4 : écrire `tile_store.py`**

Créer `backend/app/services/tile_store.py` :

```python
# -*- coding: utf-8 -*-
"""Rangement des jeux de tuiles : un dossier par jeu sous
`outputs/tilesets/<tid>` (plan 2026-09-03-plan-tuiles, P1).

Patron recopié de `material_store` (mesuré le 03/09 : `materials_root()` =
`settings.outputs_path / "materials"`, `material_dir` refuse tout `mid` hors
motif PUIS vérifie le confinement — ceinture et bretelles). Ici : motif
`^tile_[0-9a-f]{8}$`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

TID_RE = re.compile(r"^tile_[0-9a-f]{8}$")
#: les seuls noms de fichier servis par la route de fichier
FICHIERS = ("atlas.png", "apercu.png", "carte.png", "carte.json",
            "tileset.tsx", "projet.ldtk", "tileset.tres", "meta.json")


def tilesets_root() -> Path:
    from app.config import settings
    p = settings.outputs_path / "tilesets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_valid_tid(tid) -> bool:
    return isinstance(tid, str) and bool(TID_RE.match(tid))


def new_tid() -> str:
    root = tilesets_root()
    for _ in range(64):
        tid = "tile_" + uuid4().hex[:8]
        if not (root / tid).exists():
            return tid
    raise RuntimeError("Impossible d'allouer un identifiant de jeu de tuiles")


def tileset_dir(tid: str, create: bool = False) -> Path:
    """Dossier d'un jeu. Refuse tout `tid` hors motif, puis confine."""
    if not is_valid_tid(tid):
        raise ValueError(f"Identifiant de jeu de tuiles invalide: {tid!r}")
    root = tilesets_root()
    p = (root / tid).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ValueError(f"Chemin hors du dossier des tuiles: {tid!r}")
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def chemin_fichier(tid: str, nom: str) -> Path:
    """Chemin d'un fichier SERVI. `nom` est comparé à une liste blanche :
    aucun composant de chemin ne franchit cette porte."""
    if nom not in FICHIERS:
        raise ValueError(f"Fichier inconnu: {nom!r}")
    return tileset_dir(tid) / nom


def write_meta(tid: str, meta: dict) -> dict:
    d = tileset_dir(tid, create=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(d / "meta.json")
    return meta


def read_meta(tid: str) -> dict | None:
    try:
        f = tileset_dir(tid) / "meta.json"
    except ValueError:
        return None
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_tilesets() -> list[dict]:
    """Les jeux rangés, du plus récent au plus ancien."""
    out = []
    for d in tilesets_root().iterdir():
        if not d.is_dir() or not is_valid_tid(d.name):
            continue
        meta = read_meta(d.name)
        if meta is None:
            continue
        meta["tid"] = d.name
        meta["fichiers"] = sorted(p.name for p in d.iterdir()
                                  if p.name in FICHIERS)
        out.append(meta)
    out.sort(key=lambda m: m.get("cree_le", ""), reverse=True)
    return out
```

- [ ] **Step 5 : écrire `tiles_api.py` (la porte unique)**

Créer `backend/app/services/tiles_api.py` :

```python
# -*- coding: utf-8 -*-
"""Le routeur des tuiles — UNE porte pour toutes les routes de `/api/tiles`
(plan 2026-09-03-plan-tuiles). Monté par `main.py` sous `/api/tiles`, patron
du bloc `__DZ_CARDS_ROUTER_*` mesuré à `main.py:228-231`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from PIL import Image

from app.config import settings
from app.services import library_index as LI
from app.services import tile_ops as TO
from app.services import tile_store as TS

router = APIRouter()


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _charger_matiere(spec: dict, quoi: str) -> Image.Image:
    """Une matière = pour l'instant une image de la Bibliothèque. T10 ajoute
    la clé `materiau` (un `mid` du Material Forge)."""
    if not isinstance(spec, dict):
        raise HTTPException(400, f"{quoi}: objet attendu")
    nom = str(spec.get("image") or "").strip()
    if not nom:
        raise HTTPException(400, f"{quoi}: cle 'image' attendue")
    p = settings.images_path / nom
    if p.name != nom or not p.is_file():
        raise HTTPException(400, f"{quoi}: image introuvable: {nom}")
    with Image.open(p) as im:
        return im.convert("RGB").copy()


@router.post("/jeu")
async def creer_jeu(body: dict):
    """Fabrique un jeu de tuiles depuis DEUX matières et le range.
    Body: {matiere_a:{image}, matiere_b:{image}, jeu, cote, variantes,
    graine, nom}."""
    from app.services import tile_metrics as TM

    jeu_nom = str(body.get("jeu") or "blob47")
    if jeu_nom not in TO.JEUX:
        raise HTTPException(400, f"jeu inconnu: {jeu_nom}")
    a = _charger_matiere(body.get("matiere_a") or {}, "matiere_a")
    b = _charger_matiere(body.get("matiere_b") or {}, "matiere_b")
    try:
        cote = int(body.get("cote") or 64)
        variantes = int(body.get("variantes") or 1)
        graine = int(body.get("graine") or 1)
    except (TypeError, ValueError):
        raise HTTPException(400, "cote, variantes et graine sont des entiers")
    if not 16 <= cote <= 512:
        raise HTTPException(400, "cote doit tenir entre 16 et 512")
    if not 1 <= variantes <= 5:
        raise HTTPException(400, "variantes doit tenir entre 1 et 5")

    jeu = TO.assembler_jeu(a, b, jeu_nom, cote, variantes, graine)
    img, colonnes, rangees = TO.atlas(jeu)
    raccord = TM.raccord_jeu(jeu)

    tid = TS.new_tid()
    d = TS.tileset_dir(tid, create=True)
    img.save(d / "atlas.png", format="PNG")
    meta = {"tid": tid, "nom": str(body.get("nom") or "jeu de tuiles")[:80],
            "jeu": jeu_nom, "cles": jeu["cles"], "cote": cote,
            "variantes": variantes, "graine": graine,
            "tuiles": len(jeu["tuiles"]), "vide": jeu["vide"],
            "colonnes": colonnes, "rangees": rangees,
            "source_a": dict(body.get("matiere_a") or {}),
            "source_b": dict(body.get("matiere_b") or {}),
            "raccord": raccord, "cree_le": _maintenant()}
    TS.write_meta(tid, meta)
    try:
        await LI.noter([f"{tid}_atlas.png"], "tuiles")
    except Exception as e:                       # noqa: BLE001 — jamais bloquant
        logger.warning(f"index tuiles ignore: {e}")
    logger.info(f"tuiles/jeu {jeu_nom} {len(jeu['tuiles'])} tuiles "
                f"cote={cote} x{variantes} raccord={raccord} -> {tid}")
    return meta


@router.get("")
async def lister():
    return {"tilesets": TS.list_tilesets()}


@router.get("/{tid}")
async def lire(tid: str):
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    meta["tid"] = tid
    return meta


@router.get("/{tid}/fichier/{nom}")
async def fichier(tid: str, nom: str):
    try:
        p = TS.chemin_fichier(tid, nom)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if not p.is_file():
        raise HTTPException(404, f"fichier absent: {nom}")
    return FileResponse(str(p))
```

- [ ] **Step 6 : monter le routeur et déclarer la provenance**

Dans `backend/app/main.py`, **juste après** le bloc `__DZ_CARDS_ROUTER_END__` (mesuré à la ligne 232), insérer :

```python
# __DZ_TILES_ROUTER_BEGIN__
from app.services.tiles_api import router as tiles_router
app.include_router(tiles_router, prefix="/api/tiles")
# __DZ_TILES_ROUTER_END__
```

Dans `backend/app/services/library_index.py`, ajouter dans `SOURCES` (bloc `:24-38`), **entre** `"sprites"` et `"assets3d"` :

```python
    "tuiles": "Tile Lab",
```

et dans `_PREFIXES` (bloc `:43-51`), **avant** la ligne `("gen_", "generation")` :

```python
    ("tile_", "tuiles"),
```

- [ ] **Step 7 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles.py`

Expected : les 6 tests de T1 plus `PASS test_assembler_jeu_rend_47_tuiles_plus_la_vide`, `PASS test_atlas_range_les_tuiles_en_colonnes_fixes`, `PASS test_provenance_des_tuiles_est_declaree`, `PASS test_route_jeu_ecrit_un_dossier_lisible`, `PASS test_store_refuse_un_tid_hors_motif`, puis `OK — 0 echec(s)`.

> `tile_metrics.raccord_jeu` n'existe qu'à la T7. Jusque-là, poser dans `backend/app/services/tile_metrics.py` **uniquement** ce fragment (il sera complété en T7, et le banc de T7 en mesure le contenu) :
>
> ```python
> # -*- coding: utf-8 -*-
> """Mesures des jeux de tuiles (plan 2026-09-03-plan-tuiles, P4)."""
> from __future__ import annotations
>
> from PIL import ImageChops, ImageStat
>
> from app.services import tile_ops as TO
>
>
> def seam_pair(a, b, sens: str) -> float:
>     """Raccord 0-100 entre le bord de `a` et le bord OPPOSÉ de `b`.
>     `sens` = 'E' (droite de a contre gauche de b) ou 'S' (bas contre haut)."""
>     A, B = a.convert("RGB"), b.convert("RGB")
>     w, h = A.size
>     if sens == "E":
>         x, y = A.crop((w - 1, 0, w, h)), B.crop((0, 0, 1, h))
>     elif sens == "S":
>         x, y = A.crop((0, h - 1, w, h)), B.crop((0, 0, w, 1))
>     else:
>         raise ValueError(f"sens inconnu: {sens!r} (attendu 'E' ou 'S')")
>     d = ImageStat.Stat(ImageChops.difference(x, y)).mean
>     return round(sum(d) / len(d) / 255 * 100, 2)
>
>
> def paires_legales(jeu: dict, sens: str):
>     """Les couples d'index (ia, ib) dont les tuiles PEUVENT se toucher par
>     `sens` : a doit porter le bit qui pointe vers b, et b le bit inverse."""
>     bit_a, bit_b = (TO.E, TO.W) if sens == "E" else (TO.S, TO.N)
>     v = jeu["variantes"]
>     for i, ma in enumerate(jeu["cles"]):
>         if not (ma & bit_a):
>             continue
>         for j, mb in enumerate(jeu["cles"]):
>             if not (mb & bit_b):
>                 continue
>             for ka in range(v):
>                 for kb in range(v):
>                     yield i * v + ka, j * v + kb
>
>
> def raccord_jeu(jeu: dict) -> float:
>     """LE chiffre de P1 : le PIRE raccord parmi toutes les paires légales."""
>     pire = 0.0
>     for sens in ("E", "S"):
>         for ia, ib in paires_legales(jeu, sens):
>             pire = max(pire, seam_pair(jeu["tuiles"][ia],
>                                        jeu["tuiles"][ib], sens))
>     return round(pire, 2)
> ```

- [ ] **Step 8 : commit**

```bash
git add backend/app/services/tile_ops.py backend/app/services/tile_store.py backend/app/services/tile_metrics.py backend/app/services/tiles_api.py backend/app/main.py backend/app/services/library_index.py backend/tests/test_tuiles.py
git commit -m 'tuiles : un jeu depuis deux matieres, son dossier et sa porte' -m 'Le jeu complet fait 47 tuiles plus la VIDE, rangees en atlas 8 colonnes sur 6 rangees : la case sans terrain tombe pile en bas a droite. Le rangement recopie material_store, un dossier par jeu, motif d identifiant verifie PUIS confinement, et la route de fichier ne sert qu une liste blanche de noms. La reponse porte le raccord du jeu entier, mesure sur les 1156 paires E et 1156 paires S legales : 0.00. La provenance tuiles est declaree, donc l atlas est filtrable dans la Bibliotheque sans toucher au bundle.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 3 (P2a) : export Tiled `.tsx`

**Pourquoi, avec la mesure :** le brief demande les trois exports, et l'ordre de bits du plan a été choisi pour que Tiled soit une **lecture bit à bit** du voisinage. Le banc relit le XML écrit avec `xml.etree`, pas la fonction qui l'a produit.

**Files:**
- Create: `backend/app/services/tile_export.py`
- Modify: `backend/app/services/tiles_api.py` (route `POST /{tid}/export`)
- Create: `backend/tests/test_tuiles_exports.py`

- [ ] **Step 1 : relire la doc TMX/TSX et FIXER le sous-ensemble écrit**

Lancer exactement :

```
WebFetch https://doc.mapeditor.org/en/stable/reference/tmx-map-format/
prompt: Quote exactly the attributes of the <tileset> element, the <grid> element, the <wangset> element, the <wangcolor> element and the <wangtile> element. In particular, give the exact wording describing the order of the 8 indexes in the wangid attribute of <wangtile>. Also give the <tile> element's probability attribute wording.
```

Attendu (mesuré le 03/09/2026) : la phrase du `wangid` « in the order: top, top-right, right, bottom-right, bottom, bottom-left, left, top-left ».

**Sous-ensemble écrit, fixé ici** — et rien de plus :

| Élément | Attributs écrits | Pourquoi |
|---|---|---|
| `<tileset>` | `version="1.10"`, `tiledversion="1.10.2"`, `name`, `tilewidth`, `tileheight`, `tilecount`, `columns`, `spacing="0"`, `margin="0"` | un `.tsx` externe n'a **pas** de `firstgid` (il n'existe que dans un `.tmx`) |
| `<image>` | `source="atlas.png"`, `width`, `height` | chemin **relatif**, l'atlas est dans le même dossier |
| `<grid>` | `orientation`, `width`, `height` | écrit **seulement** pour l'iso (T8) : la doc dit « only used in case of isometric orientation » |
| `<wangset>` | `name="terrain"`, `tile="-1"` | pas d'attribut `type` : la lecture du 03/09 n'en montre pas sur `<wangset>` |
| `<wangcolor>` | `name`, `color`, `tile="-1"`, `probability="1"` | **deux** : `terrain` (`#e0a640`) = couleur 1, `fond` (`#3a4a5a`) = couleur 2 |
| `<wangtile>` | `tileid`, `wangid` (8 index) | `1` si le bit est posé, sinon `2` — jamais `0` : le blob n'a pas de « indifférent » |
| `<tile>` | `id`, `probability` | une seule fois par variante, `1 / variantes`, pour que Tiled tire au hasard |

- [ ] **Step 2 : écrire le banc qui échoue**

Créer `backend/tests/test_tuiles_exports.py` avec le **squelette commun** (en changeant la ligne `Run:` du docstring pour `python tests/test_tuiles_exports.py`), puis :

```python
import xml.etree.ElementTree as ET                        # noqa: E402

from app.services import tile_export as TE                # noqa: E402
from app.services import tile_ops as TO                   # noqa: E402


def _jeu(variantes=1, cote=32):
    return TO.assembler_jeu(_bruit(64, 1), _bruit(64, 2), "blob47", cote,
                            variantes)


def _meta(jeu, colonnes=8, rangees=6, forme="carre"):
    return {"nom": "banc", "jeu": jeu["jeu"], "cles": jeu["cles"],
            "cote": jeu["cote"], "variantes": jeu["variantes"],
            "tuiles": len(jeu["tuiles"]), "vide": jeu["vide"],
            "colonnes": colonnes, "rangees": rangees, "forme": forme}


def test_tsx_relu_par_xml_etree():
    """Banc-miroir : on PARSE le fichier écrit, on ne relit pas le code."""
    d = pathlib.Path(tempfile.mkdtemp())
    jeu = _jeu(variantes=2, cote=32)
    meta = _meta(jeu)
    p = TE.ecrire_tsx(d, meta)
    assert p.name == "tileset.tsx" and p.is_file()

    r = ET.parse(p).getroot()
    assert r.tag == "tileset"
    assert r.get("tilewidth") == "32" and r.get("tileheight") == "32"
    assert r.get("tilecount") == str(len(jeu["tuiles"]))     # 47*2 + 1 = 95
    assert r.get("columns") == "8"
    assert r.get("spacing") == "0" and r.get("margin") == "0"
    assert r.get("firstgid") is None, "un .tsx externe n a pas de firstgid"

    img = r.find("image")
    assert img is not None and img.get("source") == "atlas.png"
    assert img.get("width") == "256"                          # 8 x 32
    assert img.get("height") == str(meta["rangees"] * 32)
    assert r.find("grid") is None, "pas de <grid> pour un jeu carre"

    ws = r.find("wangset")
    assert ws is not None and ws.get("name") == "terrain"
    couleurs = ws.findall("wangcolor")
    assert [c.get("name") for c in couleurs] == ["terrain", "fond"]
    assert all(c.get("color", "").startswith("#") for c in couleurs)

    wt = ws.findall("wangtile")
    # une wangtile par tuile de terrain ET par variante, plus la VIDE
    assert len(wt) == len(jeu["tuiles"]), len(wt)
    par_id = {int(t.get("tileid")): t.get("wangid") for t in wt}
    assert set(par_id) == set(range(len(jeu["tuiles"])))

    # l'ordre du wangid est celui du plan : N, NE, E, SE, S, SW, W, NW
    for i, m in enumerate(jeu["cles"]):
        attendu = ",".join("1" if m & b else "2" for b in TO.BITS)
        for k in range(jeu["variantes"]):
            assert par_id[i * jeu["variantes"] + k] == attendu, (m, k)
    assert par_id[jeu["vide"]] == "2,2,2,2,2,2,2,2"           # la VIDE

    # la tuile toute entourée : huit fois la couleur 1
    plein = jeu["cles"].index(255)
    assert par_id[plein * jeu["variantes"]] == "1,1,1,1,1,1,1,1"

    # probability : 1 / variantes sur chaque tuile de terrain
    proba = {int(t.get("id")): t.get("probability")
             for t in r.findall("tile")}
    assert proba[0] == "0.5" and len(proba) == len(jeu["tuiles"]) - 1

    # à une variante, la probability vaut 1
    p1 = TE.ecrire_tsx(pathlib.Path(tempfile.mkdtemp()), _meta(_jeu(1, 32)))
    r1 = ET.parse(p1).getroot()
    assert {t.get("probability") for t in r1.findall("tile")} == {"1"}
```

- [ ] **Step 3 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles_exports.py`

Expected : `ModuleNotFoundError: No module named 'app.services.tile_export'`.

- [ ] **Step 4 : écrire `ecrire_tsx`**

Créer `backend/app/services/tile_export.py` :

```python
# -*- coding: utf-8 -*-
"""Exports d'un jeu de tuiles : Tiled `.tsx`, LDtk `.ldtk`, Godot `.tres`
(plan 2026-09-03-plan-tuiles, P2).

Chaque écriture est faite d'après une lecture DATÉE de la documentation du
format (voir la section « Références vérifiées » du plan). Rien n'est écrit
qui n'ait été lu : ni attribut deviné, ni champ « probablement accepté ».
Python écrit, le navigateur ne fait que voir (Pièges hérités).
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from app.services import tile_ops as TO

#: couleur 1 = le terrain, couleur 2 = le fond. Deux couleurs suffisent au
#: blob : chaque bit dit « voisin en terrain » ou « voisin en fond ».
COULEUR_TERRAIN = "#e0a640"
COULEUR_FOND = "#3a4a5a"
VERSION_TMX = "1.10"
VERSION_TILED = "1.10.2"


def _indente(el, niveau=0):
    """Indentation lisible — `ET.indent` existe depuis Python 3.9."""
    ET.indent(el, space=" ", level=niveau)


def ecrire_tsx(dossier: Path, meta: dict) -> Path:
    """Le `.tsx` de Tiled : l'élément <tileset> seul, sans firstgid.

    <grid orientation=…> n'est écrit que pour l'isométrique : la doc dit
    qu'il n'est « only used in case of isometric orientation » (03/09/2026).
    """
    cote = int(meta["cote"])
    colonnes, rangees = int(meta["colonnes"]), int(meta["rangees"])
    variantes = int(meta["variantes"])
    forme = meta.get("forme", "carre")
    largeur, hauteur = _taille_tuile(meta)

    ts = ET.Element("tileset", {
        "version": VERSION_TMX, "tiledversion": VERSION_TILED,
        "name": str(meta.get("nom") or "tuiles")[:60],
        "tilewidth": str(largeur), "tileheight": str(hauteur),
        "tilecount": str(int(meta["tuiles"])), "columns": str(colonnes),
        "spacing": "0", "margin": "0"})
    ET.SubElement(ts, "image", {
        "source": "atlas.png", "width": str(colonnes * largeur),
        "height": str(rangees * hauteur)})
    if forme == "iso":
        ET.SubElement(ts, "grid", {"orientation": "isometric",
                                   "width": str(largeur),
                                   "height": str(hauteur)})

    # probability : Tiled tire au hasard entre les variantes d'un même
    # voisinage. La VIDE n'entre pas en concurrence : pas de <tile> pour elle.
    proba = "1" if variantes == 1 else str(round(1 / variantes, 6)).rstrip("0")
    for i in range(int(meta["vide"])):
        ET.SubElement(ts, "tile", {"id": str(i), "probability": proba})

    ws = ET.SubElement(ts, "wangset", {"name": "terrain", "tile": "-1"})
    ET.SubElement(ws, "wangcolor", {"name": "terrain",
                                    "color": COULEUR_TERRAIN,
                                    "tile": "-1", "probability": "1"})
    ET.SubElement(ws, "wangcolor", {"name": "fond", "color": COULEUR_FOND,
                                    "tile": "-1", "probability": "1"})
    for i, m in enumerate(meta["cles"]):
        wangid = ",".join("1" if m & b else "2" for b in TO.BITS)
        for k in range(variantes):
            ET.SubElement(ws, "wangtile", {"tileid": str(i * variantes + k),
                                           "wangid": wangid})
    ET.SubElement(ws, "wangtile", {"tileid": str(int(meta["vide"])),
                                   "wangid": "2,2,2,2,2,2,2,2"})

    _indente(ts)
    p = Path(dossier) / "tileset.tsx"
    ET.ElementTree(ts).write(p, encoding="utf-8", xml_declaration=True)
    return p


def _taille_tuile(meta: dict) -> tuple[int, int]:
    """(largeur, hauteur) d'une case. Le carré et l'hexagone tiennent dans
    `cote`; l'isométrique est 2:1 (T8 pose `largeur`/`hauteur` dans meta)."""
    return int(meta.get("largeur") or meta["cote"]), \
        int(meta.get("hauteur") or meta["cote"])
```

- [ ] **Step 5 : brancher la route d'export**

Ajouter à la fin de `backend/app/services/tiles_api.py` :

```python
FORMATS = {"tiled": "tileset.tsx", "ldtk": "projet.ldtk",
           "godot": "tileset.tres"}


@router.post("/{tid}/export")
async def exporter(tid: str, body: dict):
    """Body: {format: 'tiled'|'ldtk'|'godot'}. Écrit le fichier dans le
    dossier du jeu et rend son nom — le fichier fait foi, pas la réponse."""
    from app.services import tile_export as TE

    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    fmt = str(body.get("format") or "").strip().lower()
    if fmt not in FORMATS:
        raise HTTPException(
            400, f"format inconnu: {fmt or '(vide)'} "
                 f"(attendu {', '.join(sorted(FORMATS))})")
    d = TS.tileset_dir(tid)
    p = {"tiled": TE.ecrire_tsx, "ldtk": TE.ecrire_ldtk,
         "godot": TE.ecrire_tres}[fmt](d, meta)
    logger.info(f"tuiles/export {fmt}: {tid} -> {p.name} "
                f"({p.stat().st_size} o)")
    return {"tid": tid, "format": fmt, "fichier": p.name,
            "octets": p.stat().st_size,
            "url": f"/api/tiles/{tid}/fichier/{p.name}"}
```

> `ecrire_ldtk` et `ecrire_tres` arrivent en T4 et T5 : jusque-là, la route ne répond que pour `tiled` (les deux autres lèvent `AttributeError`, ce que le banc de T4 puis de T5 transforme en vert). Pour que le module importe, ajouter dès maintenant à `tile_export.py` :
>
> ```python
> def ecrire_ldtk(dossier: Path, meta: dict) -> Path:      # T4
>     raise NotImplementedError("export LDtk : tache T4")
>
>
> def ecrire_tres(dossier: Path, meta: dict) -> Path:      # T5
>     raise NotImplementedError("export Godot : tache T5")
> ```

- [ ] **Step 6 : lancer les deux bancs, vérifier qu'ils passent**

Run : `python tests/test_tuiles_exports.py`

Expected :

```
PASS test_tsx_relu_par_xml_etree
OK — 0 echec(s)
```

Run : `python tests/test_tuiles.py`

Expected : `OK — 0 echec(s)` (rien n'a bougé côté T1/T2).

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/tile_export.py backend/app/services/tiles_api.py backend/tests/test_tuiles_exports.py
git commit -m 'tuiles : export Tiled tsx, le wangid lu bit a bit' -m 'La doc TMX relue le 03/09 donne l ordre du wangid : top, top-right, right, bottom-right, bottom, bottom-left, left, top-left. C est exactement la numerotation fixee par le plan, donc l export n a pas de table de conversion : chaque bit devient la couleur 1 quand il est pose, la couleur 2 sinon. Le sous-ensemble ecrit est ferme et dit dans le plan : un tsx externe n a pas de firstgid, la balise grid ne sert qu a l isometrique, et la probability repartit les variantes d un meme voisinage. Le banc PARSE le fichier ecrit avec xml.etree et compte 95 wangtiles pour 47 voisinages a deux variantes plus la case vide.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 4 (P2b) : export LDtk (tileset + `autoRuleGroups`)

**Pourquoi, avec la mesure :** le brief demande « les règles LDtk pour le blob ». Ce sont des motifs 3×3 sur un IntGrid, et la sémantique des valeurs est **citée du code de LDtk** (`0` ignoré, `v` doit valoir v, `−v` ne doit pas valoir v). Les 47 règles sont alors **mutuellement exclusives par construction** : tout voisinage de cellule pleine correspond à exactement une règle — c'est démontré au banc, pas affirmé.

**Files:**
- Modify: `backend/app/services/tile_export.py`
- Test: `backend/tests/test_tuiles_exports.py`

- [ ] **Step 1 : relire le schéma LDtk et la sémantique du motif, et FIXER le sous-ensemble écrit**

Lancer exactement les deux :

```
WebFetch https://ldtk.io/files/JSON_SCHEMA.json
prompt: List the "required" field names of the ROOT object of the schema, of the LayerDef object, of the Level object, of the TilesetDef object, of the AutoLayerRuleGroup object and of the AutoRuleDef object. Give them verbatim as arrays, and state the schema version.
```

```
WebFetch https://raw.githubusercontent.com/deepnight/ldtk/master/src/electron.renderer/data/def/AutoLayerRuleDef.hx
prompt: Explain the exact semantics of the `pattern` array values: what 0 means, what a positive value v means, what a negative value -v means. Quote the relevant code lines.
```

Attendu (mesuré le 03/09/2026) : schéma **1.5.3** ; `pattern` → `if( pattern[coordId]==0 ) continue;`, `if( pattern[coordId]>0 && value != pattern[coordId] ) return false;`, `if( pattern[coordId]<0 && value == -pattern[coordId] ) return false;` ; `tileIds` **déprécié depuis 1.5.0** au profit de `tileRectsIds`.

**Sous-ensemble écrit, fixé ici** : un projet `.ldtk` **minimal mais complet au sens du schéma** — la racine avec ses 28 champs requis, `defs.tilesets` (un `TilesetDef` avec ses 13 champs requis), `defs.layers` (un `LayerDef` IntGrid avec ses 27 champs requis, portant `autoRuleGroups`), `defs.entities = []`, `defs.enums = []`, `defs.externalEnums = []`, `defs.levelFields = []`, et `levels = []`. Un groupe de règles `blob`, une règle par voisinage canonique.

**Le motif 3×3, fixé ici** (index `y*3 + x`, `x` et `y` depuis le coin haut-gauche) :

| Index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| Case | NW | N | NE | W | **centre** | E | SW | S | SE |
| Valeur | coin | arête | coin | arête | **1** | arête | coin | arête | coin |

- **arête** : `1` si le bit est posé, `-1` sinon.
- **centre** : toujours `1` (la case peinte est du terrain).
- **coin** : `1` si le bit est posé ; `-1` si le bit est absent **alors que ses deux arêtes adjacentes sont posées** ; `0` (**ignoré**) sinon — c'est exactement ce que la canonisation a effacé, et écrire `-1` là serait un mensonge.

**Exclusivité, démontrée :** deux règles distinctes diffèrent sur au moins une case exacte (`1` ou `-1`) — si c'est une arête, un voisinage ne peut satisfaire les deux ; si c'est un coin, les deux règles ont alors les mêmes arêtes adjacentes posées, donc des exigences de coin contradictoires. Le banc l'éprouve sur les 256 voisinages.

- [ ] **Step 2 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles_exports.py` :

```python
def test_ldtk_relu_par_json():
    d = pathlib.Path(tempfile.mkdtemp())
    jeu = _jeu(variantes=3, cote=16)
    meta = _meta(jeu)
    p = TE.ecrire_ldtk(d, meta)
    assert p.name == "projet.ldtk" and p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))

    requis_racine = {"bgColor", "defs", "externalLevels", "iid", "jsonVersion",
                     "levels", "toc", "worlds", "appBuildId", "backupLimit",
                     "backupOnSave", "customCommands", "defaultEntityHeight",
                     "defaultEntityWidth", "defaultGridSize",
                     "defaultLevelBgColor", "defaultPivotX", "defaultPivotY",
                     "dummyWorldIid", "exportLevelBg", "exportTiled", "flags",
                     "identifierStyle", "imageExportMode", "levelNamePattern",
                     "minifyJson", "nextUid", "simplifiedExport"}
    assert requis_racine <= set(doc), sorted(requis_racine - set(doc))
    assert doc["jsonVersion"] == "1.5.3", doc["jsonVersion"]

    ts = doc["defs"]["tilesets"][0]
    requis_ts = {"__cHei", "__cWid", "customData", "enumTags", "identifier",
                 "padding", "pxHei", "pxWid", "spacing", "tags",
                 "tileGridSize", "uid", "savedSelections"}
    assert requis_ts <= set(ts), sorted(requis_ts - set(ts))
    assert ts["relPath"] == "atlas.png"
    assert ts["tileGridSize"] == 16
    assert ts["__cWid"] == meta["colonnes"] and ts["__cHei"] == meta["rangees"]
    assert ts["pxWid"] == meta["colonnes"] * 16

    couche = doc["defs"]["layers"][0]
    requis_couche = {"__type", "displayOpacity", "gridSize", "identifier",
                     "intGridValues", "intGridValuesGroups",
                     "parallaxFactorX", "parallaxFactorY", "parallaxScaling",
                     "pxOffsetX", "pxOffsetY", "uid", "autoRuleGroups",
                     "canSelectWhenInactive", "excludedTags", "guideGridHei",
                     "guideGridWid", "hideFieldsWhenInactive", "hideInList",
                     "inactiveOpacity", "renderInWorldView", "requiredTags",
                     "tilePivotX", "tilePivotY", "type", "uiFilterTags",
                     "useAsyncRender"}
    assert requis_couche <= set(couche), sorted(requis_couche - set(couche))
    assert couche["__type"] == "IntGrid" and couche["type"] == "IntGrid"
    assert [v["value"] for v in couche["intGridValues"]] == [1]
    assert couche["tilesetDefUid"] == ts["uid"]

    groupes = couche["autoRuleGroups"]
    assert len(groupes) == 1 and groupes[0]["name"] == "blob"
    requis_grp = {"uid", "name", "active", "rules", "isOptional", "collapsed",
                  "color"}
    assert requis_grp <= set(groupes[0]), sorted(requis_grp - set(groupes[0]))

    regles = groupes[0]["rules"]
    assert len(regles) == 47, len(regles)
    requis_regle = {"uid", "active", "size", "pattern", "tileRectsIds",
                    "tileIds", "chance", "breakOnMatch", "flipX", "flipY",
                    "tileMode"}
    for r in regles:
        assert requis_regle <= set(r), sorted(requis_regle - set(r))
        assert r["size"] == 3 and len(r["pattern"]) == 9
        assert r["pattern"][4] == 1, r["pattern"]
        assert r["tileMode"] == "Single" and r["breakOnMatch"] is True
        # tileRectsIds : une entrée par variante, chacune un id seul
        assert len(r["tileRectsIds"]) == 3, r["tileRectsIds"]
        assert all(len(x) == 1 for x in r["tileRectsIds"])
    assert {r["uid"] for r in regles} == set(
        r["uid"] for r in regles), "uid dupliques"

    # le motif du plan, lu case par case
    par_motif = {tuple(r["pattern"]): r for r in regles}
    plein = par_motif[(1,) * 9]
    assert plein["tileRectsIds"][0][0] == jeu["cles"].index(255) * 3
    isole = par_motif[(0, -1, 0, -1, 1, -1, 0, -1, 0)]
    assert isole["tileRectsIds"][0][0] == jeu["cles"].index(0) * 3


def test_les_47_regles_ldtk_sont_mutuellement_exclusives():
    """Tout voisinage de cellule pleine satisfait EXACTEMENT une règle —
    sémantique citée d AutoLayerRuleDef.hx : 0 ignore, v exige v, -v exclut v."""
    d = pathlib.Path(tempfile.mkdtemp())
    jeu = _jeu(variantes=1, cote=16)
    doc = json.loads(TE.ecrire_ldtk(d, _meta(jeu)).read_text("utf-8"))
    regles = doc["defs"]["layers"][0]["autoRuleGroups"][0]["rules"]
    ordre = ((0, TO.NW), (1, TO.N), (2, TO.NE), (3, TO.W),
             (5, TO.E), (6, TO.SW), (7, TO.S), (8, TO.SE))

    def satisfait(motif, voisinage):
        if motif[4] != 1:
            return False
        for i, bit in ordre:
            v = 1 if voisinage & bit else 0
            attendu = motif[i]
            if attendu == 0:
                continue
            if attendu > 0 and v != attendu:
                return False
            if attendu < 0 and v == -attendu:
                return False
        return True

    for voisinage in range(256):
        gagnantes = [r for r in regles if satisfait(r["pattern"], voisinage)]
        assert len(gagnantes) == 1, (voisinage, len(gagnantes))
        attendu = jeu["cles"].index(TO.canon(voisinage))
        assert gagnantes[0]["tileRectsIds"][0][0] == attendu, voisinage
```

- [ ] **Step 3 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles_exports.py`

Expected : `FAIL test_ldtk_relu_par_json` et `FAIL test_les_47_regles_ldtk_sont_mutuellement_exclusives`, tous deux avec `NotImplementedError: export LDtk : tache T4`, puis `ROUGE — 2 echec(s)`.

- [ ] **Step 4 : écrire `ecrire_ldtk`**

Remplacer, dans `backend/app/services/tile_export.py`, le corps provisoire de `ecrire_ldtk` par :

```python
#: LDtk 1.5.3 (schéma relu le 03/09/2026). `tileIds` est déprécié depuis
#: 1.5.0 mais reste requis : on l'écrit vide.
LDTK_VERSION = "1.5.3"


def _ident(nom: str) -> str:
    """Identifiant LDtk : lettres, chiffres et soulignés, initiale capitale."""
    s = "".join(c if c.isalnum() else "_" for c in nom).strip("_") or "Atlas"
    if s[0].isdigit():
        s = "T" + s
    return s[0].upper() + s[1:]


def _motif_blob(m: int) -> list[int]:
    """Motif 3x3 d'un voisinage canonique. Sémantique CITÉE du code de LDtk :
    0 = case ignorée, v > 0 = doit valoir v, -v = ne doit pas valoir v.

    Un coin absent n'exige `-1` QUE si ses deux arêtes sont posées ; sinon la
    canonisation l'a effacé et exiger quoi que ce soit serait un mensonge."""
    motif = [0] * 9
    motif[4] = 1
    for i, bit in ((1, TO.N), (3, TO.W), (5, TO.E), (7, TO.S)):
        motif[i] = 1 if m & bit else -1
    for i, (bit, a, b) in ((0, (TO.NW, TO.W, TO.N)), (2, (TO.NE, TO.N, TO.E)),
                           (6, (TO.SW, TO.S, TO.W)),
                           (8, (TO.SE, TO.E, TO.S))):
        if m & bit:
            motif[i] = 1
        elif (m & a) and (m & b):
            motif[i] = -1
        else:
            motif[i] = 0
    return motif


def ecrire_ldtk(dossier: Path, meta: dict) -> Path:
    """Un projet `.ldtk` minimal : le tileset, une couche IntGrid, et un
    groupe de 47 règles d'auto-layer mutuellement exclusives."""
    cote = int(meta["cote"])
    largeur, hauteur = _taille_tuile(meta)
    colonnes, rangees = int(meta["colonnes"]), int(meta["rangees"])
    variantes = int(meta["variantes"])
    nom = str(meta.get("nom") or "tuiles")[:60]

    uid_ts, uid_couche, uid_groupe = 1, 2, 3
    regles = []
    for i, m in enumerate(meta["cles"]):
        regles.append({
            "uid": 100 + i, "active": True, "size": 3,
            "pattern": _motif_blob(m),
            # une entrée par variante : « all the possible tile ID rectangles
            # (picked randomly) » (schéma 1.5.3)
            "tileRectsIds": [[i * variantes + k] for k in range(variantes)],
            "tileIds": [],            # requis, déprécié depuis 1.5.0
            "chance": 1.0, "breakOnMatch": True, "flipX": False,
            "flipY": False, "tileMode": "Single", "pivotX": 0, "pivotY": 0,
            "xModulo": 1, "yModulo": 1, "xOffset": 0, "yOffset": 0,
            "checker": "None", "outOfBoundsValue": None, "alpha": 1.0,
            "invalidated": False, "perlinActive": False, "perlinScale": 0.2,
            "perlinOctaves": 2.0, "perlinSeed": 0})

    doc = {
        "__header__": {"fileType": "LDtk Project JSON",
                       "app": "DeepotusVideoGen Tile Lab",
                       "schemaVersion": LDTK_VERSION},
        "iid": "dz-tiles-project", "jsonVersion": LDTK_VERSION,
        "appBuildId": 0, "nextUid": 1000,
        "identifierStyle": "Capitalize", "imageExportMode": "None",
        "exportTiled": False, "exportLevelBg": True, "simplifiedExport": False,
        "minifyJson": False, "externalLevels": False,
        "backupOnSave": False, "backupLimit": 10, "customCommands": [],
        "bgColor": "#40465B", "defaultLevelBgColor": "#696A79",
        "defaultGridSize": cote,
        "defaultEntityWidth": cote, "defaultEntityHeight": cote,
        "defaultPivotX": 0.0, "defaultPivotY": 0.0,
        "dummyWorldIid": "dz-tiles-world", "flags": [],
        "levelNamePattern": "Level_%idx", "toc": [], "worlds": [],
        "levels": [],
        "defs": {
            "entities": [], "enums": [], "externalEnums": [],
            "levelFields": [],
            "tilesets": [{
                "uid": uid_ts, "identifier": _ident(nom),
                "relPath": "atlas.png",
                "embedAtlas": None, "pxWid": colonnes * largeur,
                "pxHei": rangees * hauteur, "tileGridSize": cote,
                "spacing": 0, "padding": 0,
                "__cWid": colonnes, "__cHei": rangees,
                "tags": [], "tagsSourceEnumUid": None, "enumTags": [],
                "customData": [], "savedSelections": [],
                "cachedPixelData": None}],
            "layers": [{
                "__type": "IntGrid", "type": "IntGrid",
                "identifier": "Terrain", "uid": uid_couche,
                "gridSize": cote, "displayOpacity": 1.0,
                "inactiveOpacity": 0.6, "hideInList": False,
                "hideFieldsWhenInactive": False,
                "canSelectWhenInactive": True, "renderInWorldView": True,
                "pxOffsetX": 0, "pxOffsetY": 0,
                "parallaxFactorX": 0.0, "parallaxFactorY": 0.0,
                "parallaxScaling": True,
                "requiredTags": [], "excludedTags": [], "uiFilterTags": [],
                "useAsyncRender": False,
                "guideGridWid": 0, "guideGridHei": 0,
                "tilePivotX": 0.0, "tilePivotY": 0.0,
                "intGridValues": [{"value": 1, "identifier": "terrain",
                                   "color": COULEUR_TERRAIN, "tile": None,
                                   "groupUid": 0}],
                "intGridValuesGroups": [],
                "tilesetDefUid": uid_ts, "autoTilesetDefUid": uid_ts,
                "autoSourceLayerDefUid": None,
                "autoRuleGroups": [{
                    "uid": uid_groupe, "name": "blob", "active": True,
                    "isOptional": False, "collapsed": False,
                    "color": COULEUR_TERRAIN, "icon": None,
                    "usesWizard": False, "rules": regles,
                    "biomeRequirementMode": 0, "requiredBiomeValues": []}]}]},
    }
    p = Path(dossier) / "projet.ldtk"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p
```

Le jeu de banc s'appelle `banc`, donc `_ident("banc")` rend `"Banc"` : ajouter dans `test_ldtk_relu_par_json`, **juste après** la ligne `assert ts["relPath"] == "atlas.png"` :

```python
    assert ts["identifier"] == "Banc", ts["identifier"]
```

- [ ] **Step 5 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles_exports.py`

Expected :

```
PASS test_ldtk_relu_par_json
PASS test_les_47_regles_ldtk_sont_mutuellement_exclusives
PASS test_tsx_relu_par_xml_etree
OK — 0 echec(s)
```

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tile_export.py backend/tests/test_tuiles_exports.py
git commit -m 'tuiles : export LDtk, 47 regles d auto-layer exclusives' -m 'Le schema 1.5.3 relu le 03/09 donne les champs requis de la racine, de la couche, du tileset et de la regle ; le code AutoLayerRuleDef.hx donne la semantique du motif : zero ignore la case, v exige v, moins v exclut v. Un coin absent n exige donc moins un QUE si ses deux aretes sont posees, sinon la case reste ignoree : ecrire moins un partout serait un mensonge sur ce que la canonisation a efface. Le banc lit le JSON ecrit et EPROUVE l exclusivite sur les 256 voisinages : chacun satisfait exactement une regle, et elle designe la bonne tuile. Les variantes passent par tileRectsIds, tire au hasard par LDtk, tileIds etant deprecie depuis 1.5.0.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 5 (P2c) : export Godot `TileSet` `.tres` avec terrains

**Pourquoi, avec la mesure :** le `.tres` est du texte, et la seule façon honnête de l'écrire est de recopier la forme d'un fichier **réellement produit par Godot 4**. On en a lu trois (skeleton, isometric, hexagonal_map) le 03/09 ; le banc relit le fichier écrit et y retrouve les clés de ces fichiers réels.

**Files:**
- Modify: `backend/app/services/tile_export.py`
- Test: `backend/tests/test_tuiles_exports.py`

- [ ] **Step 1 : relire la doc Godot ET un `.tres` réel, et FIXER le sous-ensemble écrit**

Lancer exactement les trois :

```
WebFetch https://docs.godotengine.org/en/stable/classes/class_tileset.html
prompt: List the exact integer values of the TileShape, TileLayout, TileOffsetAxis and TerrainMode enums, and the property names tile_shape, tile_layout, tile_size, tile_offset_axis.
```

```
WebFetch https://docs.godotengine.org/en/stable/classes/class_tileset.html#enum-tileset-cellneighbor
prompt: List every constant of the CellNeighbor enum with its exact name and integer value.
```

```
WebFetch https://raw.githubusercontent.com/godotengine/godot-demo-projects/master/2d/skeleton/level/tileset/tileset.tres
prompt: Print verbatim ONLY the first line, every line containing "terrain", every line containing "texture_region_size", and the whole [resource] section.
```

Attendu (mesuré le 03/09/2026) : `TILE_SHAPE_SQUARE=0 … HEXAGON=3` ; `TILE_LAYOUT_DIAMOND_DOWN=5` ; `TILE_OFFSET_AXIS_VERTICAL=1` ; `TERRAIN_MODE_MATCH_CORNERS_AND_SIDES=0` ; et dans le fichier réel `X:Y/0/terrain_set = 0`, `X:Y/0/terrain = 0`, les huit `terrains_peering_bit/…` **posés seulement quand le bit l'est**, puis `terrain_set_0/mode = 0`, `terrain_set_0/terrain_0/name`, `terrain_set_0/terrain_0/color`, `sources/1 = SubResource(…)`.

**Sous-ensemble écrit, fixé ici :**

```
[gd_resource type="TileSet" format=3]

[ext_resource type="Texture2D" path="res://atlas.png" id="1"]

[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_dz0"]
texture = ExtResource("1")
texture_region_size = Vector2i(<largeur>, <hauteur>)
<x>:<y>/0 = 0
<x>:<y>/0/terrain_set = 0
<x>:<y>/0/terrain = 0
<x>:<y>/0/terrains_peering_bit/<nom> = 0      ← une ligne par bit POSÉ

[resource]
tile_size = Vector2i(<largeur>, <hauteur>)
terrain_set_0/mode = 0
terrain_set_0/terrain_0/name = "terrain"
terrain_set_0/terrain_0/color = Color(0.878, 0.651, 0.251, 1)
sources/0 = SubResource("TileSetAtlasSource_dz0")
```

Pas d'`uid://` (Godot en attribue un à l'import). La tuile **VIDE** est déclarée (`X:Y/0 = 0`) mais **sans** `terrain_set` ni `terrain` : la doc dit que ces champs valent `-1` quand ils sont absents, ce qui est exactement « pas de terrain ». La correspondance bit → nom est celle du tableau « La numérotation, FIXÉE par ce plan ».

- [ ] **Step 2 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles_exports.py` :

```python
def _lignes_tres(p):
    return [l.rstrip() for l in p.read_text(encoding="utf-8").splitlines()]


def test_tres_relu_ligne_a_ligne():
    d = pathlib.Path(tempfile.mkdtemp())
    jeu = _jeu(variantes=1, cote=32)
    meta = _meta(jeu)
    p = TE.ecrire_tres(d, meta)
    assert p.name == "tileset.tres" and p.is_file()
    L = _lignes_tres(p)

    assert L[0] == '[gd_resource type="TileSet" format=3]', L[0]
    assert '[ext_resource type="Texture2D" path="res://atlas.png" id="1"]' in L
    assert '[sub_resource type="TileSetAtlasSource" ' \
           'id="TileSetAtlasSource_dz0"]' in L
    assert 'texture = ExtResource("1")' in L
    assert "texture_region_size = Vector2i(32, 32)" in L
    assert "[resource]" in L
    assert "tile_size = Vector2i(32, 32)" in L
    assert "terrain_set_0/mode = 0" in L
    assert 'terrain_set_0/terrain_0/name = "terrain"' in L
    assert 'sources/0 = SubResource("TileSetAtlasSource_dz0")' in L
    assert "tile_shape" not in "\n".join(L), "carre : tile_shape par defaut"

    # la tuile toute entourée porte ses HUIT bits, nommés comme chez Godot
    plein = jeu["cles"].index(255)
    x, y = plein % meta["colonnes"], plein // meta["colonnes"]
    huit = {f"{x}:{y}/0/terrains_peering_bit/{n} = 0" for n in (
        "top_side", "top_right_corner", "right_side", "bottom_right_corner",
        "bottom_side", "bottom_left_corner", "left_side", "top_left_corner")}
    assert huit <= set(L), sorted(huit - set(L))
    assert f"{x}:{y}/0/terrain_set = 0" in L
    assert f"{x}:{y}/0/terrain = 0" in L

    # la tuile ISOLÉE (aucun voisin) n'a AUCUN bit de voisinage
    isole = jeu["cles"].index(0)
    xi, yi = isole % meta["colonnes"], isole // meta["colonnes"]
    assert not [l for l in L
                if l.startswith(f"{xi}:{yi}/0/terrains_peering_bit/")]
    assert f"{xi}:{yi}/0/terrain = 0" in L

    # la tuile VIDE est declaree SANS terrain : absent vaut -1 chez Godot
    xv, yv = meta["vide"] % meta["colonnes"], meta["vide"] // meta["colonnes"]
    assert f"{xv}:{yv}/0 = 0" in L
    assert f"{xv}:{yv}/0/terrain_set = 0" not in L
    assert f"{xv}:{yv}/0/terrain = 0" not in L

    # une tuile par case de l'atlas, ni plus ni moins
    declarees = [l for l in L if l.endswith("/0 = 0")]
    assert len(declarees) == len(jeu["tuiles"]), len(declarees)


def test_tres_nomme_les_bits_dans_l_ordre_du_plan():
    """N->top_side, NE->top_right_corner, … : la table du plan, éprouvée."""
    d = pathlib.Path(tempfile.mkdtemp())
    jeu = _jeu(variantes=1, cote=16)
    meta = _meta(jeu)
    L = set(_lignes_tres(TE.ecrire_tres(d, meta)))
    noms = dict(zip(TO.BITS, ("top_side", "top_right_corner", "right_side",
                              "bottom_right_corner", "bottom_side",
                              "bottom_left_corner", "left_side",
                              "top_left_corner")))
    for i, m in enumerate(jeu["cles"]):
        x, y = i % meta["colonnes"], i // meta["colonnes"]
        for bit, nom in noms.items():
            ligne = f"{x}:{y}/0/terrains_peering_bit/{nom} = 0"
            assert (ligne in L) == bool(m & bit), (m, nom)
```

- [ ] **Step 3 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles_exports.py`

Expected : `FAIL test_tres_relu_ligne_a_ligne` et `FAIL test_tres_nomme_les_bits_dans_l_ordre_du_plan`, tous deux `NotImplementedError: export Godot : tache T5`, puis `ROUGE — 2 echec(s)`.

- [ ] **Step 4 : écrire `ecrire_tres`**

Remplacer le corps provisoire de `ecrire_tres` dans `backend/app/services/tile_export.py` par :

```python
#: bit du plan -> nom de `CellNeighbor` chez Godot, en minuscules, tel que
#: les .tres réels de godot-demo-projects les écrivent (relus le 03/09/2026)
PEERING = (
    (TO.N, "top_side"), (TO.NE, "top_right_corner"), (TO.E, "right_side"),
    (TO.SE, "bottom_right_corner"), (TO.S, "bottom_side"),
    (TO.SW, "bottom_left_corner"), (TO.W, "left_side"),
    (TO.NW, "top_left_corner"))

#: TileShape : SQUARE=0, ISOMETRIC=1, HALF_OFFSET_SQUARE=2, HEXAGON=3
FORMES_GODOT = {"carre": None, "iso": 1, "hex": 3}
ID_SOURCE = "TileSetAtlasSource_dz0"


def ecrire_tres(dossier: Path, meta: dict) -> Path:
    """Le `.tres` Godot 4 : une TileSetAtlasSource, un terrain set en mode
    MATCH_CORNERS_AND_SIDES (0), un bit de voisinage par bit posé."""
    largeur, hauteur = _taille_tuile(meta)
    colonnes = int(meta["colonnes"])
    variantes = int(meta["variantes"])
    forme = meta.get("forme", "carre")

    L = ['[gd_resource type="TileSet" format=3]', "",
         '[ext_resource type="Texture2D" path="res://atlas.png" id="1"]', "",
         f'[sub_resource type="TileSetAtlasSource" id="{ID_SOURCE}"]',
         'texture = ExtResource("1")',
         f"texture_region_size = Vector2i({largeur}, {hauteur})"]

    for i, m in enumerate(meta["cles"]):
        for k in range(variantes):
            idx = i * variantes + k
            x, y = idx % colonnes, idx // colonnes
            L.append(f"{x}:{y}/0 = 0")
            L.append(f"{x}:{y}/0/terrain_set = 0")
            L.append(f"{x}:{y}/0/terrain = 0")
            for bit, nom in PEERING:
                if m & bit:
                    L.append(f"{x}:{y}/0/terrains_peering_bit/{nom} = 0")
    # la VIDE : déclarée, mais sans terrain — absent vaut -1 chez Godot
    v = int(meta["vide"])
    L.append(f"{v % colonnes}:{v // colonnes}/0 = 0")

    L += ["", "[resource]"]
    if FORMES_GODOT.get(forme) is not None:
        L.append(f"tile_shape = {FORMES_GODOT[forme]}")
        if forme == "iso":
            L.append("tile_layout = 5")          # DIAMOND_DOWN, comme la démo
        if forme == "hex":
            L.append("tile_offset_axis = 1")     # VERTICAL : sommet plat
    L += [f"tile_size = Vector2i({largeur}, {hauteur})",
          "terrain_set_0/mode = 0",              # MATCH_CORNERS_AND_SIDES
          'terrain_set_0/terrain_0/name = "terrain"',
          "terrain_set_0/terrain_0/color = Color(0.878, 0.651, 0.251, 1)",
          f'sources/0 = SubResource("{ID_SOURCE}")', ""]

    p = Path(dossier) / "tileset.tres"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
```

- [ ] **Step 5 : lancer les deux bancs, vérifier qu'ils passent**

Run : `python tests/test_tuiles_exports.py`

Expected :

```
PASS test_ldtk_relu_par_json
PASS test_les_47_regles_ldtk_sont_mutuellement_exclusives
PASS test_tres_nomme_les_bits_dans_l_ordre_du_plan
PASS test_tres_relu_ligne_a_ligne
PASS test_tsx_relu_par_xml_etree
OK — 0 echec(s)
```

Run : `python tests/test_tuiles.py` → `OK — 0 echec(s)`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tile_export.py backend/tests/test_tuiles_exports.py
git commit -m 'tuiles : export Godot tres, les bits de voisinage nommes' -m 'La doc donne les enums (TileShape, TerrainMode, CellNeighbor) mais pas la forme du fichier : on a donc relu trois tres reellement ecrits par Godot 4 dans godot-demo-projects le 03/09, et l on recopie leur forme. Une tuile pose X:Y/0 puis terrain_set, terrain, et SEULEMENT les bits poses, comme le fichier reel. La tuile vide est declaree sans terrain, ce qui vaut moins un chez Godot, soit exactement pas de terrain. Le banc relit le fichier ecrit ligne a ligne et verifie la correspondance bit par bit avec la table du plan, y compris qu une tuile isolee n a aucun bit.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 6 (P3) : variantes et aperçu 8×8 auto-tuilé

**Pourquoi, avec la mesure :** « la répétition se voit avant l'export » (brief). Un aperçu 8×8 tiré au hasard n'a de sens que s'il est **réellement auto-tuilé** : on tire une grille booléenne de terrain, on lit le voisinage de chaque case, on pose la tuile canonique et une variante au hasard. Le même moteur sert au peintre (D3, T12) : un seul propriétaire de la règle. Et les variantes ne doivent **rien** coûter au raccord : mesuré, **10404 paires E légales à 3 variantes, raccord max 0.00**.

**Files:**
- Modify: `backend/app/services/tile_ops.py` (ajout de `carte_aleatoire`, `masque_voisins`, `composer_carte`)
- Modify: `backend/app/services/tiles_api.py` (route `POST /{tid}/apercu`)
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def test_les_variantes_ne_touchent_pas_le_bord():
    """Le masque de cœur est 0 DUR sur l'anneau : la variante ne peut pas
    déplacer un pixel de bord, donc le raccord reste 0.00 (mesuré sur les
    10404 paires E légales d un jeu a 3 variantes)."""
    coeur = TO.masque_coeur(64)
    b = 8
    bords = (coeur.crop((0, 0, 64, b)), coeur.crop((0, 64 - b, 64, 64)),
             coeur.crop((0, 0, b, 64)), coeur.crop((64 - b, 0, 64, 64)))
    assert max(max(im.getextrema()) for im in bords) == 0
    assert coeur.getpixel((32, 32)) == 255

    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 64, variantes=3, graine=5)
    assert len(jeu["tuiles"]) == 47 * 3 + 1
    # les 3 variantes d'une même tuile diffèrent VRAIMENT
    i = jeu["cles"].index(255) * 3
    assert len({jeu["tuiles"][i + k].tobytes() for k in range(3)}) == 3
    # ... et ont exactement le même bord
    for k in (1, 2):
        assert jeu["tuiles"][i + k].crop((63, 0, 64, 64)).tobytes() == \
            jeu["tuiles"][i].crop((63, 0, 64, 64)).tobytes()


def test_raccord_du_jeu_a_variantes_reste_nul():
    from app.services import tile_metrics as TM
    jeu = TO.assembler_jeu(_bruit(64, 1), _bruit(64, 2), "blob47", 64, 3, 5)
    n = sum(1 for _ in TM.paires_legales(jeu, "E"))
    assert n == 10404, n                     # 1156 voisinages x 3 x 3
    assert TM.raccord_jeu(jeu) == 0.0


def test_masque_voisins_lit_les_huit_directions():
    g = [[0] * 3 for _ in range(3)]
    g[1][1] = 1
    assert TO.masque_voisins(g, 1, 1, boucle=False) == 0
    g[0][1] = 1                              # la case AU-DESSUS
    assert TO.masque_voisins(g, 1, 1, boucle=False) == TO.N
    g[1][2] = 1                              # la case À DROITE
    assert TO.masque_voisins(g, 1, 1, boucle=False) == TO.N | TO.E
    g[0][2] = 1                              # la diagonale NE, désormais légale
    assert TO.masque_voisins(g, 1, 1, boucle=False) == TO.N | TO.E | TO.NE
    # hors carte = vide quand boucle=False, et la carte boucle sinon
    plein = [[1] * 3 for _ in range(3)]
    assert TO.masque_voisins(plein, 0, 0, boucle=False) == \
        TO.canon(TO.E | TO.S | TO.SE)
    assert TO.masque_voisins(plein, 0, 0, boucle=True) == 255


def test_composer_carte_pose_les_bonnes_tuiles():
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 32, variantes=2, graine=3)
    g = TO.carte_aleatoire(8, densite=0.55, graine=1)
    assert len(g) == 8 and all(len(l) == 8 for l in g)
    assert set(v for l in g for v in l) <= {0, 1}
    # la même graine rend la même carte : la recette est rejouable
    assert TO.carte_aleatoire(8, 0.55, 1) == g

    img, plan = TO.composer_carte(g, jeu, graine=1, boucle=True)
    assert img.size == (8 * 32, 8 * 32)
    assert len(plan) == 8 and len(plan[0]) == 8
    for y in range(8):
        for x in range(8):
            t = plan[y][x]
            if not g[y][x]:
                assert t == jeu["vide"], (x, y)
            else:
                m = TO.masque_voisins(g, x, y, boucle=True)
                base = jeu["cles"].index(m) * jeu["variantes"]
                assert base <= t < base + jeu["variantes"], (x, y, m, t)
            # le pixel posé est bien celui de la tuile du plan
            assert img.crop((x * 32, y * 32, x * 32 + 32,
                             y * 32 + 32)).tobytes() == \
                jeu["tuiles"][t].convert("RGB").tobytes(), (x, y)


def test_route_apercu_ecrit_le_png_et_le_plan():
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("ap_a.png", _bruit(128, 4))
        b = _poser_image("ap_b.png", _bruit(128, 5))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": a}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 32, "variantes": 3, "nom": "ap"})
            tid = r.json()["tid"]
            r = await c.post(f"/api/tiles/{tid}/apercu",
                             json={"cases": 8, "densite": 0.55, "graine": 7})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["cases"] == 8 and d["graine"] == 7
            assert len(d["plan"]) == 8 and len(d["plan"][0]) == 8
            # le PNG ÉCRIT, relu par PIL
            with Image.open(TS.tileset_dir(tid) / "apercu.png") as im:
                assert im.size == (256, 256), im.size
            # la même graine redonne le même plan
            r2 = await c.post(f"/api/tiles/{tid}/apercu",
                              json={"cases": 8, "densite": 0.55, "graine": 7})
            assert r2.json()["plan"] == d["plan"]
            r3 = await c.post(f"/api/tiles/{tid}/apercu", json={"cases": 999})
            assert r3.status_code == 400 and "cases" in r3.text

    asyncio.run(scenario())
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_composer_carte_pose_les_bonnes_tuiles` (`AttributeError: … has no attribute 'carte_aleatoire'`), `FAIL test_masque_voisins_lit_les_huit_directions`, `FAIL test_route_apercu_ecrit_le_png_et_le_plan` (404 sur `/apercu`), puis `ROUGE — 3 echec(s)`. `test_les_variantes_ne_touchent_pas_le_bord` et `test_raccord_du_jeu_a_variantes_reste_nul` passent déjà (le mécanisme est en place depuis T1/T2).

- [ ] **Step 3 : ajouter l'auto-tuilage à `tile_ops.py`**

Ajouter à la fin de `backend/app/services/tile_ops.py` :

```python
def carte_aleatoire(cases: int = 8, densite: float = 0.55,
                    graine: int = 1) -> list[list[int]]:
    """Grille booléenne de terrain, rejouable à graine égale."""
    import random as _random

    rng = _random.Random(int(graine))
    d = min(1.0, max(0.0, float(densite)))
    return [[1 if rng.random() < d else 0 for _ in range(cases)]
            for _ in range(cases)]


def masque_voisins(grille, x: int, y: int, boucle: bool = True) -> int:
    """Le voisinage CANONIQUE de la case (x, y). `boucle=True` : la carte est
    un tore (l'aperçu 8x8) ; `boucle=False` : hors carte = vide (le peintre).
    """
    h = len(grille)
    w = len(grille[0]) if h else 0
    m = 0
    for _, dx, dy, bit in DIRS:
        nx, ny = x + dx, y + dy
        if boucle:
            nx, ny = nx % w, ny % h
        elif not (0 <= nx < w and 0 <= ny < h):
            continue
        if grille[ny][nx]:
            m |= bit
    return canon(m)


def composer_carte(grille, jeu: dict, graine: int = 1, boucle: bool = True):
    """(image RGB de la carte, plan [[index de tuile]]).

    C'est Python qui compose : le navigateur ne fait que voir (Pièges
    hérités). Le même moteur sert à l'aperçu 8x8 (P3) et au peintre (D3)."""
    import random as _random

    table = jeu["cles"]
    v = jeu["variantes"]
    idx = {m: i for i, m in enumerate(table)}
    rng = _random.Random(int(graine))
    cote = jeu["cote"]
    h = len(grille)
    w = len(grille[0]) if h else 0
    img = Image.new("RGB", (w * cote, h * cote), (0, 0, 0))
    plan = []
    for y in range(h):
        ligne = []
        for x in range(w):
            if grille[y][x]:
                t = idx[masque_voisins(grille, x, y, boucle)] * v \
                    + rng.randrange(v)
            else:
                t = jeu["vide"]
            img.paste(jeu["tuiles"][t].convert("RGB"), (x * cote, y * cote))
            ligne.append(t)
        plan.append(ligne)
    return img, plan
```

- [ ] **Step 4 : refabriquer le jeu depuis son `meta`, et brancher la route d'aperçu**

Ajouter à `backend/app/services/tiles_api.py` (le jeu n'est pas gardé en mémoire : on le refabrique **à l'identique** depuis son `meta`, ce qui prouve au passage que la recette est rejouable) :

```python
def _refaire_jeu(meta: dict) -> dict:
    """Refabrique le jeu à l'identique depuis son meta — même sources, même
    graine, donc mêmes octets. C'est la recette qui fait foi, pas un cache."""
    a = _charger_matiere(meta.get("source_a") or {}, "matiere_a")
    b = _charger_matiere(meta.get("source_b") or {}, "matiere_b")
    return TO.assembler_jeu(a, b, meta["jeu"], int(meta["cote"]),
                            int(meta["variantes"]), int(meta["graine"]))


def _bornes_apercu(body: dict) -> tuple[int, float, int]:
    """(cases, densite, graine) validés. UNE seule porte pour l'aperçu (P3)
    et pour les mesures (P4), qui tirent la même carte."""
    try:
        cases = int(body.get("cases") or 8)
        graine = int(body.get("graine") or 1)
        densite = float(body.get("densite") if body.get("densite")
                        is not None else 0.55)
    except (TypeError, ValueError):
        raise HTTPException(400, "cases et graine entiers, densite reelle")
    if not 4 <= cases <= 16:
        raise HTTPException(400, "cases doit tenir entre 4 et 16")
    if not 0.0 <= densite <= 1.0:
        raise HTTPException(400, "densite doit tenir entre 0 et 1")
    return cases, densite, graine


@router.post("/{tid}/apercu")
async def apercu(tid: str, body: dict):
    """Aperçu auto-tuilé, tirage aléatoire rejouable.
    Body: {cases 4..16, densite 0..1, graine}."""
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    cases, densite, graine = _bornes_apercu(body)

    jeu = _refaire_jeu(meta)
    grille = TO.carte_aleatoire(cases, densite, graine)
    img, plan = TO.composer_carte(grille, jeu, graine=graine, boucle=True)
    d = TS.tileset_dir(tid, create=True)
    img.save(d / "apercu.png", format="PNG")
    logger.info(f"tuiles/apercu {cases}x{cases} d={densite} g={graine}: {tid}")
    return {"tid": tid, "cases": cases, "densite": densite, "graine": graine,
            "plan": plan, "grille": grille,
            "url": f"/api/tiles/{tid}/fichier/apercu.png"}
```

- [ ] **Step 5 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles.py`

Expected : les tests de T1/T2 plus `PASS test_composer_carte_pose_les_bonnes_tuiles`, `PASS test_les_variantes_ne_touchent_pas_le_bord`, `PASS test_masque_voisins_lit_les_huit_directions`, `PASS test_raccord_du_jeu_a_variantes_reste_nul`, `PASS test_route_apercu_ecrit_le_png_et_le_plan`, puis `OK — 0 echec(s)`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tile_ops.py backend/app/services/tiles_api.py backend/tests/test_tuiles.py
git commit -m 'tuiles : variantes et apercu 8x8 vraiment auto-tuile' -m 'Une variante perturbe la matiere par un decalage cyclique, mais SEULEMENT au coeur : le masque de coeur est zero dur sur l anneau, verifie au banc, donc le bord d une variante est byte pour byte celui de la tuile de base et le raccord des 10404 paires E legales reste 0.00 mesure. L apercu n est pas un collage au hasard : on tire une grille booleenne de terrain, on lit le voisinage de chaque case et l on pose la tuile canonique plus une variante — le meme moteur servira au peintre, un seul proprietaire de la regle. Le jeu est refabrique depuis son meta plutot que garde en memoire : c est la recette qui fait foi, et la meme graine redonne le meme plan.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 7 (P4) : les trois mesures, chacune avec son seuil nommé

**Pourquoi, avec la mesure :** le brief demande « trois chiffres par tuile et par jeu, seuils nommés ». Chaque mesure est ici définie **par son calcul**, sa **complexité** et ses **valeurs témoins**, toutes exécutées le 03/09/2026 avec le python embarqué :

| Mesure | Calcul | Complexité | Témoins mesurés | Seuil nommé |
|---|---|---|---|---|
| **raccord** | `seam_pair` sur toutes les paires légales (existe depuis T2) | `2 × (nombre de paires) × cote` octets | jeu blob47 à 3 variantes : `0.0` sur 10404 paires E + 10404 paires S | `RACCORD_MAX = 1.0` |
| **répétition** | auto-corrélation par **décalages entiers de cases** sur la grille 8×8, en niveaux de gris réduits à `cases × 32` px | `(cases² − 1)` décalages × `(cases × 32)²` octets = **63 × 65 536 ≈ 4,1 × 10⁶** différences pour 8×8 — tenable en PIL pur | damier de période 2 : `100.0` ; aperçu auto-tuilé aléatoire (graines 1, 2, 3) : `19.08`, `20.53`, `21.95` ; image uniforme : `100.0` | `REPETITION_MAX = 70.0` |
| **éclairage** | gradient moyen : luminance réduite à 8×8 (`Image.BOX`), écart moitié gauche/droite et haut/bas, norme normalisée 255 | `cote²` octets lus une fois | uni : `0.0` ; rampe horizontale : `50.78` ; rampe verticale : `50.78` ; bruit miroir : `0.0` ; tuiles d'un jeu de bruit : max `0.87`, écart `0.87` | `ECLAIRAGE_MAX = 8.0` par tuile, `ECART_ECLAIRAGE_MAX = 5.0` sur le jeu |

La **répétition** est normalisée par la moyenne des décalages : `100 × (1 − meilleur / moyenne)`. Sans cette normalisation, deux matières voisines en teinte donneraient un score élevé sans aucune périodicité ; avec elle, `0` veut dire « aucun décalage n'apparie mieux que la moyenne » et `100` « un décalage apparie exactement ». C'est pour cela que le seuil `70.0` sépare franchement les témoins mesurés (`22` contre `100`).

**Files:**
- Modify: `backend/app/services/tile_metrics.py`
- Modify: `backend/app/services/tiles_api.py` (route `POST /{tid}/mesures`)
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def test_eclairage_lit_un_gradient_et_ignore_un_uni():
    from app.services import tile_metrics as TM
    assert TM.eclairage_score(_uni()) == 0.0
    assert TM.eclairage_score(_bruit(64, 1)) == 0.0
    h = TM.eclairage_score(_rampe())
    assert 45.0 < h < 55.0, h                      # mesuré : 50.78
    v = TM.eclairage_score(_rampe().transpose(Image.ROTATE_90))
    assert abs(v - h) < 0.01, (h, v)               # la norme ne prend pas parti
    assert TM.SEUILS["eclairage"] == 8.0
    assert TM.SEUILS["ecart_eclairage"] == 5.0


def test_repetition_voit_un_damier_et_pas_un_tirage():
    from app.services import tile_metrics as TM
    A, B = _bruit(64, 1), _bruit(64, 2)
    jeu = TO.assembler_jeu(A, B, "blob47", 64, 3, 5)
    damier = [[(x + y) % 2 for x in range(8)] for y in range(8)]
    img_d, _ = TO.composer_carte(damier, jeu, graine=1, boucle=True)
    assert TM.repetition_score(img_d) == 100.0     # période exacte
    assert TM.repetition_score(_uni(256)) == 100.0  # tout est périodique
    for g in (1, 2, 3):
        grille = TO.carte_aleatoire(8, 0.55, g)
        img, _ = TO.composer_carte(grille, jeu, graine=g, boucle=True)
        r = TM.repetition_score(img)
        assert r < TM.SEUILS["repetition"], (g, r)  # mesuré : 19.1 / 20.5 / 22.0
        assert 0.0 <= r <= 100.0
    assert TM.SEUILS["repetition"] == 70.0


def test_verdict_nomme_chaque_mesure():
    from app.services import tile_metrics as TM
    bon = TM.verdict({"raccord": 0.0, "repetition": 21.9,
                      "eclairage_max": 0.87, "ecart_eclairage": 0.87})
    assert bon == {"raccord": "ok", "repetition": "ok", "eclairage": "ok",
                   "ecart_eclairage": "ok"}
    mauvais = TM.verdict({"raccord": 4.2, "repetition": 98.0,
                          "eclairage_max": 30.0, "ecart_eclairage": 12.0})
    assert set(mauvais.values()) == {"attention"}, mauvais


def test_route_mesures_rend_trois_chiffres_par_jeu_et_par_tuile():
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("me_a.png", _bruit(128, 6))
        b = _poser_image("me_b.png", _bruit(128, 7))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": a}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 32, "variantes": 2, "nom": "me"})
            tid = r.json()["tid"]
            r = await c.post(f"/api/tiles/{tid}/mesures", json={"graine": 3})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["raccord"] == 0.0
            assert 0.0 <= d["repetition"] <= 100.0
            assert d["repetition"] < 70.0, d["repetition"]
            assert d["eclairage_max"] < 8.0, d["eclairage_max"]
            assert len(d["par_tuile"]) == 47 * 2 + 1
            assert all(set(t) == {"index", "eclairage"} for t in d["par_tuile"])
            assert d["verdict"] == {"raccord": "ok", "repetition": "ok",
                                    "eclairage": "ok", "ecart_eclairage": "ok"}
            assert d["seuils"]["repetition"] == 70.0
            # les mesures sont ÉCRITES dans le meta : elles survivent
            meta = json.loads(
                (TS.tileset_dir(tid) / "meta.json").read_text("utf-8"))
            assert meta["mesures"]["repetition"] == d["repetition"]

    asyncio.run(scenario())
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_eclairage_lit_un_gradient_et_ignore_un_uni` (`AttributeError: … has no attribute 'eclairage_score'`), `FAIL test_repetition_voit_un_damier_et_pas_un_tirage`, `FAIL test_verdict_nomme_chaque_mesure`, `FAIL test_route_mesures_rend_trois_chiffres_par_jeu_et_par_tuile`, puis `ROUGE — 4 echec(s)`.

- [ ] **Step 3 : compléter `tile_metrics.py`**

Dans `backend/app/services/tile_metrics.py`, remplacer d'abord l'en-tête d'imports par :

```python
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageStat

from app.services import tile_ops as TO
```

puis ajouter, **après** `raccord_jeu` :

```python
#: Seuils NOMMÉS, calibrés sur des témoins exécutés le 03/09/2026 avec le
#: python embarqué (voir le tableau de la tâche T7 du plan).
SEUILS = {
    #: raccord : le PIRE des paires légales. 0.00 mesuré sur un jeu de bruit
    #: miroir ; on tolère 1 point pour une matière au raccord imparfait.
    "raccord": 1.0,
    #: répétition : damier de période 2 -> 100.0 ; tirage auto-tuilé -> 19 à 22.
    "repetition": 70.0,
    #: éclairage : uni -> 0.0 ; rampe pleine -> 50.78 ; tuiles de bruit -> 0.87.
    "eclairage": 8.0,
    #: écart d'éclairage entre la tuile la plus et la moins marquée du jeu.
    "ecart_eclairage": 5.0,
}


def eclairage_score(img, cellules: int = 8) -> float:
    """Gradient moyen d'éclairage d'une tuile, 0-100.

    La luminance est réduite à `cellules x cellules` par moyennes de blocs
    (Image.BOX), puis l'on mesure l'écart entre les moitiés gauche/droite et
    haut/bas ; le score est la norme de ce gradient, normalisée 255. Un
    éclairage cuit dans la texture se voit : une rampe pleine rend 50.78, un
    aplat 0.00, un bruit miroir 0.00 (mesurés).

    Coût : `cote²` octets lus une fois par la réduction."""
    g = img.convert("L").resize((cellules, cellules), Image.BOX)
    px = list(g.tobytes())           # `getdata` est déprécié depuis Pillow 12
    h = cellules // 2

    def moy(idx):
        return sum(px[i] for i in idx) / len(idx)

    gauche = moy([y * cellules + x for y in range(cellules) for x in range(h)])
    droite = moy([y * cellules + x for y in range(cellules)
                  for x in range(h, cellules)])
    haut = moy([y * cellules + x for y in range(h) for x in range(cellules)])
    bas = moy([y * cellules + x for y in range(h, cellules)
               for x in range(cellules)])
    return round(math.hypot(gauche - droite, haut - bas) / 255 * 100, 2)


def eclairage_jeu(jeu: dict) -> tuple[float, float, list[dict]]:
    """(max, écart max-min, détail par tuile)."""
    par = [{"index": i, "eclairage": eclairage_score(t)}
           for i, t in enumerate(jeu["tuiles"])]
    vals = [p["eclairage"] for p in par]
    return round(max(vals), 2), round(max(vals) - min(vals), 2), par


def repetition_score(apercu, cases: int = 8, cote_reduit: int = 32) -> float:
    """Auto-corrélation par DÉCALAGES DE CASES sur l'aperçu, 0-100.

    L'aperçu est réduit en niveaux de gris à `cases x cote_reduit` px de côté,
    puis, pour chacun des `cases² - 1` décalages non nuls (cycliques, donc
    d'une case entière), l'on mesure la différence absolue moyenne avec
    l'aperçu d'origine. Le score vaut `100 x (1 - meilleur / moyenne)` : la
    normalisation par la moyenne est ce qui distingue une vraie périodicité
    d'une simple parenté de teinte entre deux matières.

    0 = aucun décalage n'apparie mieux que la moyenne ; 100 = un décalage
    apparie EXACTEMENT (damier de période 2, ou aplat).

    Coût : `(cases² - 1)` décalages sur `(cases x cote_reduit)²` octets, soit
    63 x 65 536 ≈ 4,1 x 10⁶ différences pour un aperçu 8x8 — deux appels PIL
    par décalage (`ImageChops.offset` puis `difference`), aucun numpy."""
    n = cases * cote_reduit
    g = apercu.convert("L").resize((n, n), Image.BOX)
    ecarts = []
    for cy in range(cases):
        for cx in range(cases):
            if cx == 0 and cy == 0:
                continue
            d = ImageChops.difference(
                g, ImageChops.offset(g, cx * cote_reduit, cy * cote_reduit))
            ecarts.append(ImageStat.Stat(d).mean[0])
    moyenne = sum(ecarts) / len(ecarts)
    if moyenne <= 1e-6:              # image parfaitement uniforme
        return 100.0
    return round(max(0.0, 1 - min(ecarts) / moyenne) * 100, 2)


def verdict(mesures: dict) -> dict:
    """Un mot par mesure : `ok` ou `attention`. Aucune mesure n'est muette."""
    return {
        "raccord": "ok" if mesures["raccord"] <= SEUILS["raccord"]
        else "attention",
        "repetition": "ok" if mesures["repetition"] < SEUILS["repetition"]
        else "attention",
        "eclairage": "ok" if mesures["eclairage_max"] <= SEUILS["eclairage"]
        else "attention",
        "ecart_eclairage": "ok"
        if mesures["ecart_eclairage"] <= SEUILS["ecart_eclairage"]
        else "attention",
    }
```

- [ ] **Step 4 : brancher la route de mesures**

Ajouter à `backend/app/services/tiles_api.py` :

```python
@router.post("/{tid}/mesures")
async def mesures(tid: str, body: dict):
    """Les TROIS chiffres du jeu, plus l'éclairage tuile par tuile.
    Body: {graine, cases, densite} — l'aperçu sert d'assiette à la répétition.
    """
    from app.services import tile_metrics as TM

    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    cases, densite, graine = _bornes_apercu(body)

    jeu = _refaire_jeu(meta)
    grille = TO.carte_aleatoire(cases, densite, graine)
    img, _plan = TO.composer_carte(grille, jeu, graine=graine, boucle=True)
    ecl_max, ecart, par_tuile = TM.eclairage_jeu(jeu)
    m = {"raccord": TM.raccord_jeu(jeu),
         "repetition": TM.repetition_score(img, cases),
         "eclairage_max": ecl_max, "ecart_eclairage": ecart}
    sortie = dict(m)
    sortie.update({"tid": tid, "par_tuile": par_tuile,
                   "verdict": TM.verdict(m), "seuils": dict(TM.SEUILS),
                   "graine": graine, "cases": cases})
    meta["mesures"] = m
    TS.write_meta(tid, meta)
    logger.info(f"tuiles/mesures {tid}: raccord={m['raccord']} "
                f"repetition={m['repetition']} eclairage={ecl_max}")
    return sortie
```

- [ ] **Step 5 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles.py`

Expected : tout ce qui précède plus `PASS test_eclairage_lit_un_gradient_et_ignore_un_uni`, `PASS test_repetition_voit_un_damier_et_pas_un_tirage`, `PASS test_route_mesures_rend_trois_chiffres_par_jeu_et_par_tuile`, `PASS test_verdict_nomme_chaque_mesure`, puis `OK — 0 echec(s)`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tile_metrics.py backend/app/services/tiles_api.py backend/tests/test_tuiles.py
git commit -m 'tuiles : trois mesures, trois seuils nommes, des temoins executes' -m 'Le raccord existait ; s ajoutent la repetition et l eclairage. La repetition est une auto-correlation par decalages de cases entieres sur l apercu reduit en niveaux de gris, normalisee par la moyenne des decalages — sans cette normalisation, deux matieres de teinte voisine donneraient un score eleve sans aucune periodicite. Les temoins sont executes, pas devines : un damier de periode deux rend 100.00, trois tirages auto-tuiles rendent 19.08, 20.53 et 21.95, donc le seuil 70 separe franchement. L eclairage est le gradient moyen de la luminance reduite en huit sur huit : aplat 0.00, rampe pleine 50.78, tuiles de bruit 0.87 au pire, d ou les seuils 8 par tuile et 5 d ecart. Chaque mesure rend un mot, ok ou attention : aucune n est muette.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 8 (P5) : losange 2:1 et hexagone, raccord sur les bords correspondants

**Pourquoi, avec la mesure :** une tuile iso ou hex ne raccorde pas parce qu'on l'a découpée en losange — elle raccorde si sa texture est **périodique sous le réseau de la forme**. On y arrive sans numpy avec **une seule transformation affine** : le carré unité de la matière est envoyé sur le réseau de la forme (`Image.transform(…, Image.AFFINE, …)` sur une matière pavée 5×5 pour couvrir les débords). Les vecteurs du réseau deviennent alors des multiples entiers de la taille de la matière, donc la texture est périodique **par construction**. Mesuré le 03/09 avec le python embarqué, sur une bande de 3 px de part et d'autre du bord partagé : **iso NE/SE/SW/NW = `0.0`** (272, 268, 269, 273 pixels comparés) ; **hex NE/SE/S/SW/NW/N = `0.0`** (169, 167, 107, 165, 166, 103 pixels).

**Dimensions fixées ici :** `dims_iso(H)` = `(2H, H)` — le 2:1 des `.tres` réels de Godot (`Vector2i(128, 64)`). `dims_hex(R)` = `(2R, 2·round(√3·R/2))` — hexagone **à sommet plat**, hauteur forcée paire pour que le demi-décalage du réseau soit entier ; `R = 32` donne `(64, 56)`. Le hex réel de Godot est `Vector2i(110, 94)` avec `tile_offset_axis = 1`, soit le même rapport (1,17 contre 2/√3 = 1,155).

**Ce que chaque export accepte, dit honnêtement :**

| Format | Iso | Hex |
|---|---|---|
| Tiled `.tsx` | `<grid orientation="isometric" width height/>` — la doc dit qu'il n'est « only used in case of isometric orientation » | **rien** : l'orientation hexagonale (`hexsidelength`, `staggeraxis`, `staggerindex`) est un attribut de `<map>`, pas de `<tileset>`. Le `.tsx` est écrit sans orientation, et la réponse de la route le **dit** |
| LDtk | non : LDtk 1.5 est orthogonal — l'issue #944 « Hex or Isometric tile support » est marquée close/completed le 06/10/2023, mais rien dans le schéma 1.5.3 relu ne porte d'orientation. **L'export LDtk d'un jeu iso ou hex est refusé en le disant** | idem |
| Godot `.tres` | `tile_shape = 1`, `tile_layout = 5`, `tile_size = Vector2i(2H, H)` | `tile_shape = 3`, `tile_offset_axis = 1`, `tile_size = Vector2i(2R, H)` |

**Files:**
- Create: `backend/app/services/tile_shapes.py`
- Modify: `backend/app/services/tile_ops.py` (ajout de `assembler_forme`)
- Modify: `backend/app/services/tile_export.py` (refus LDtk motivé)
- Modify: `backend/app/services/tiles_api.py` (`forme` accepté par `POST /jeu`)
- Test: `backend/tests/test_tuiles.py`, `backend/tests/test_tuiles_exports.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def test_dimensions_des_formes():
    from app.services import tile_shapes as TF
    assert TF.dims_iso(64) == (128, 64)              # le 2:1 des .tres Godot
    assert TF.dims_iso(32) == (64, 32)
    assert TF.dims_hex(32) == (64, 56)               # hauteur PAIRE, forcée
    w, h = TF.dims_hex(55)
    assert w == 110 and h % 2 == 0, (w, h)
    assert set(TF.DEC_ISO) == {"NE", "SE", "SW", "NW"}
    assert set(TF.DEC_HEX) == {"N", "NE", "SE", "S", "SW", "NW"}
    # les décalages de voisinage sont ENTIERS : sinon le réseau ne boucle pas
    for d in list(TF.DEC_ISO(128, 64).values()) + \
            list(TF.DEC_HEX(64, 56).values()):
        assert all(isinstance(v, int) for v in d), d


def test_masque_losange_et_hexagone():
    from app.services import tile_shapes as TF
    mi = TF.masque_forme("iso", 64)
    assert mi.size == (128, 64)
    assert mi.getpixel((64, 32)) == 255              # le centre
    assert mi.getpixel((0, 0)) == 0                  # le coin, hors losange
    assert mi.getpixel((2, 32)) == 255               # la pointe gauche
    mh = TF.masque_forme("hex", 32)
    assert mh.size == (64, 56)
    assert mh.getpixel((32, 28)) == 255
    assert mh.getpixel((0, 0)) == 0
    assert mh.getpixel((2, 28)) == 255               # la pointe gauche
    try:
        TF.masque_forme("triangle", 32)
    except ValueError:
        pass
    else:
        raise AssertionError("masque_forme a accepte une forme inconnue")


def test_raccord_des_bords_correspondants_est_nul():
    """LA mesure de P5 : chaque bord contre le bord correspondant du voisin.
    Mesuré : iso 4 bords à 0.0 (272, 268, 269, 273 px), hex 6 bords à 0.0
    (169, 167, 107, 165, 166, 103 px)."""
    from app.services import tile_shapes as TF
    mat = _bruit(64, 3)
    tailles = {}
    for arete in ("NE", "SE", "SW", "NW"):
        score, n = TF.seam_forme(mat, "iso", arete, 64)
        assert score == 0.0, (arete, score)
        assert n > 200, (arete, n)
        tailles[arete] = n
    assert tailles["NE"] == 272 and tailles["NW"] == 273, tailles
    for arete in ("N", "NE", "SE", "S", "SW", "NW"):
        score, n = TF.seam_forme(mat, "hex", arete, 32)
        assert score == 0.0, (arete, score)
        assert n > 100, (arete, n)


def test_assembler_forme_rend_un_jeu_exportable():
    A = _bruit(64, 1)
    jeu = TO.assembler_forme(A, "iso", 64)
    assert jeu["forme"] == "iso"
    assert jeu["largeur"] == 128 and jeu["hauteur"] == 64
    assert len(jeu["tuiles"]) == 1 and jeu["tuiles"][0].size == (128, 64)
    assert jeu["tuiles"][0].mode == "RGBA"           # hors forme = transparent
    assert jeu["tuiles"][0].getpixel((0, 0))[3] == 0
    assert jeu["tuiles"][0].getpixel((64, 32))[3] == 255
    jh = TO.assembler_forme(A, "hex", 32)
    assert (jh["largeur"], jh["hauteur"]) == (64, 56)


def test_route_jeu_accepte_iso_et_hex():
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("fo_a.png", _bruit(128, 8))
        async with _client() as c:
            for forme, taille in (("iso", (128, 64)), ("hex", (64, 56))):
                r = await c.post("/api/tiles/jeu", json={
                    "matiere_a": {"image": a}, "forme": forme,
                    "cote": 64 if forme == "iso" else 32, "nom": forme})
                assert r.status_code == 200, r.text
                d = r.json()
                assert d["forme"] == forme
                assert (d["largeur"], d["hauteur"]) == taille, d
                assert d["raccord"] == 0.0, d["raccord"]
                with Image.open(TS.tileset_dir(d["tid"]) / "atlas.png") as im:
                    assert im.size == (taille[0], taille[1]), im.size
                # LDtk refuse une forme non orthogonale, EN LE DISANT
                r2 = await c.post(f"/api/tiles/{d['tid']}/export",
                                  json={"format": "ldtk"})
                assert r2.status_code == 400, r2.text
                assert "orthogonal" in r2.text.lower(), r2.text
                # Tiled et Godot l'acceptent
                for fmt in ("tiled", "godot"):
                    r3 = await c.post(f"/api/tiles/{d['tid']}/export",
                                      json={"format": fmt})
                    assert r3.status_code == 200, r3.text
                # l'auto-tuilage est refusé sur une forme, en le disant
                r4 = await c.post(f"/api/tiles/{d['tid']}/apercu",
                                  json={"cases": 8})
                assert r4.status_code == 400 and "carre" in r4.text, r4.text
                # le meta décrit le jeu PRODUIT : une forme, une tuile
                meta = json.loads((TS.tileset_dir(d["tid"]) / "meta.json")
                                  .read_text("utf-8"))
                assert meta["jeu"] == "forme" and meta["variantes"] == 1
                assert meta["cles"] == [255], meta["cles"]

    asyncio.run(scenario())
```

Et à `backend/tests/test_tuiles_exports.py` :

```python
def test_exports_de_forme_disent_ce_qu_ils_portent():
    d = pathlib.Path(tempfile.mkdtemp())
    meta_iso = {"nom": "iso", "jeu": "forme", "cles": [255], "cote": 64,
                "largeur": 128, "hauteur": 64, "variantes": 1, "tuiles": 1,
                "vide": 1, "colonnes": 1, "rangees": 1, "forme": "iso"}
    r = ET.parse(TE.ecrire_tsx(d, meta_iso)).getroot()
    g = r.find("grid")
    assert g is not None and g.get("orientation") == "isometric"
    assert g.get("width") == "128" and g.get("height") == "64"
    assert r.get("tilewidth") == "128" and r.get("tileheight") == "64"
    L = _lignes_tres(TE.ecrire_tres(d, meta_iso))
    assert "tile_shape = 1" in L and "tile_layout = 5" in L
    assert "tile_size = Vector2i(128, 64)" in L

    d2 = pathlib.Path(tempfile.mkdtemp())
    meta_hex = dict(meta_iso, nom="hex", forme="hex", largeur=64, hauteur=56)
    r2 = ET.parse(TE.ecrire_tsx(d2, meta_hex)).getroot()
    # l'orientation hexagonale est un attribut de <map>, PAS de <tileset>
    assert r2.find("grid") is None
    assert r2.get("tilewidth") == "64" and r2.get("tileheight") == "56"
    L2 = _lignes_tres(TE.ecrire_tres(d2, meta_hex))
    assert "tile_shape = 3" in L2 and "tile_offset_axis = 1" in L2
    assert "tile_layout" not in "\n".join(L2)

    for meta in (meta_iso, meta_hex):
        try:
            TE.ecrire_ldtk(d, meta)
        except ValueError as e:
            assert "orthogonal" in str(e).lower(), str(e)
        else:
            raise AssertionError("LDtk a accepte une forme non orthogonale")
```

- [ ] **Step 2 : lancer les deux bancs, vérifier qu'ils échouent**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_dimensions_des_formes` (`ModuleNotFoundError: No module named 'app.services.tile_shapes'`) et les quatre autres nouveaux tests rouges, puis `ROUGE — 5 echec(s)`.

Run : `python tests/test_tuiles_exports.py`

Expected : `FAIL test_exports_de_forme_disent_ce_qu_ils_portent` (`AssertionError: LDtk a accepte une forme non orthogonale`), puis `ROUGE — 1 echec(s)`.

- [ ] **Step 3 : écrire `tile_shapes.py`**

Créer `backend/app/services/tile_shapes.py` :

```python
# -*- coding: utf-8 -*-
"""Formes de tuile : losange isométrique 2:1 et hexagone à sommet plat
(plan 2026-09-03-plan-tuiles, P5).

UNE SEULE IDÉE : la texture d'une tuile de forme n'est pas la matière
recadrée, c'est la matière envoyée sur le RÉSEAU de la forme par une
transformation affine. Les vecteurs du réseau deviennent alors des multiples
entiers de la taille de la matière, donc la texture est périodique sous le
réseau PAR CONSTRUCTION — et les bords correspondants raccordent exactement.

Mesuré le 03/09/2026 (bande de 3 px de part et d'autre du bord partagé) :
iso NE/SE/SW/NW = 0.0 sur 272 / 268 / 269 / 273 px ; hex NE/SE/S/SW/NW/N
= 0.0 sur 169 / 167 / 107 / 165 / 166 / 103 px.

PIL pur : `Image.transform(…, Image.AFFINE, …)` sur une matière pavée 5x5
(les coordonnées de la boîte englobante débordent d'un demi-motif de chaque
côté ; 5x5 couvre largement, et le pavage coûte 25 collages).
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

FORMES = ("carre", "iso", "hex")
#: taille du pavage de la matière source, en motifs
PAVAGE = 5


def dims_iso(cote: int = 64) -> tuple[int, int]:
    """Losange 2:1 — le rapport des .tres réels de Godot (128 x 64)."""
    h = max(8, int(cote) - (int(cote) % 2))
    return 2 * h, h


def dims_hex(rayon: int = 32) -> tuple[int, int]:
    """Hexagone à SOMMET PLAT : largeur 2R, hauteur racine(3) x R arrondie au
    PAIR — le demi-décalage du réseau doit être entier."""
    r = max(8, int(rayon))
    return 2 * r, 2 * round(math.sqrt(3) * r / 2)


def DEC_ISO(largeur: int, hauteur: int) -> dict[str, tuple[int, int]]:
    """Décalages de voisinage du réseau losange, en pixels ENTIERS."""
    w, h = largeur // 2, hauteur // 2
    return {"NE": (w, -h), "SE": (w, h), "SW": (-w, h), "NW": (-w, -h)}


def DEC_HEX(largeur: int, hauteur: int) -> dict[str, tuple[int, int]]:
    """Décalages du réseau hexagonal à sommet plat, en pixels ENTIERS."""
    w, h = 3 * largeur // 4, hauteur // 2
    return {"N": (0, -hauteur), "NE": (w, -h), "SE": (w, h),
            "S": (0, hauteur), "SW": (-w, h), "NW": (-w, -h)}


def dims(forme: str, cote: int) -> tuple[int, int]:
    if forme == "iso":
        return dims_iso(cote)
    if forme == "hex":
        return dims_hex(cote)
    if forme == "carre":
        return int(cote), int(cote)
    raise ValueError(f"forme inconnue: {forme!r} (attendu {', '.join(FORMES)})")


def decalages(forme: str, largeur: int, hauteur: int):
    if forme == "iso":
        return DEC_ISO(largeur, hauteur)
    if forme == "hex":
        return DEC_HEX(largeur, hauteur)
    raise ValueError(f"forme sans reseau propre: {forme!r}")


def masque_forme(forme: str, cote: int = 64) -> Image.Image:
    """Masque « L » de la forme : 255 dedans, 0 dehors."""
    w, h = dims(forme, cote)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    if forme == "iso":
        d.polygon([(w // 2, 0), (w - 1, h // 2), (w // 2, h - 1), (0, h // 2)],
                  fill=255)
    elif forme == "hex":
        cx, cy, r = w / 2, h / 2, w / 2
        d.polygon([(round(cx + r * math.cos(math.radians(60 * k))),
                    round(cy + r * math.sin(math.radians(60 * k))))
                   for k in range(6)], fill=255)
    else:
        d.rectangle((0, 0, w - 1, h - 1), fill=255)
    return im


def _pave(mat: Image.Image, k: int = PAVAGE) -> Image.Image:
    s = mat.width
    g = Image.new("RGB", (k * s, k * s))
    for gy in range(k):
        for gx in range(k):
            g.paste(mat, (gx * s, gy * s))
    return g


def _coeffs(forme: str, s: int, w: int, h: int, ox: int, oy: int):
    """Coefficients AFFINE de PIL : le pixel (x, y) de la SORTIE lit la source
    en (a·x + b·y + c, d·x + e·y + f). `ox, oy` = position, dans la sortie, du
    coin haut-gauche de la tuile centrale.

    Iso : le carré unité (u, v) est envoyé sur le losange par
    (x, y) = ((u+v)·w/2, (v-u)·h/2 + h/2), d'où u = x/w - y/h + 1/2 et
    v = x/w + y/h - 1/2.
    Hex : le réseau est engendré par (3R/2, h/2) et (0, h) ; relativement au
    centre, u = (x - R)/(3R/2) et v = (y - h/2)/h - u/2.
    """
    demi = PAVAGE // 2 * s
    if forme == "iso":
        a, b, c = s / w, -s / h, 0.5 * s
        d, e, f = s / w, s / h, -0.5 * s
    elif forme == "hex":
        r = w / 2
        a, b, c = 2 * s / (3 * r), 0.0, -2 * s / 3
        d, e, f = -s / (3 * r), s / h, -s / 6
    else:
        raise ValueError(f"forme sans reseau propre: {forme!r}")
    return (a, b, c + demi - a * ox - b * oy,
            d, e, f + demi - d * ox - e * oy)


def texture_forme(mat: Image.Image, forme: str, cote: int = 64,
                  taille=None, origine=(0, 0)) -> Image.Image:
    """La matière envoyée sur le réseau de la forme, en RGB."""
    w, h = dims(forme, cote)
    sortie = taille or (w, h)
    return _pave(mat.convert("RGB")).transform(
        sortie, Image.AFFINE,
        _coeffs(forme, mat.width, w, h, origine[0], origine[1]),
        Image.NEAREST)


def tuile_forme(mat: Image.Image, forme: str, cote: int = 64) -> Image.Image:
    """La tuile RGBA : texture du réseau, découpée par le masque de forme."""
    tex = texture_forme(mat, forme, cote).convert("RGBA")
    tex.putalpha(masque_forme(forme, cote))
    return tex


def seam_forme(mat: Image.Image, forme: str, arete: str, cote: int = 64,
               bande: int = 3):
    """(raccord 0-100, nombre de pixels comparés) sur le bord `arete`.

    On étend la texture à 3x3 tuiles, on pose le masque de forme au centre et
    au voisin, puis, sur la BANDE de `bande` px où les deux formes se
    touchent, on compare la texture lue par le centre et celle lue par le
    voisin (le même point du monde, à un vecteur du réseau près). 0 = les
    deux tuiles montrent la même chose au bord."""
    w, h = dims(forme, cote)
    dec = decalages(forme, w, h)
    if arete not in dec:
        raise ValueError(f"arete inconnue pour {forme}: {arete!r}")
    dx, dy = dec[arete]
    grand = texture_forme(mat, forme, cote, taille=(3 * w, 3 * h),
                          origine=(w, h))
    mq = masque_forme(forme, cote)
    centre = Image.new("L", grand.size, 0)
    centre.paste(mq, (w, h))
    voisin = Image.new("L", grand.size, 0)
    voisin.paste(mq, (w + dx, h + dy))
    contact = ImageChops.multiply(
        centre, voisin.filter(ImageFilter.MaxFilter(2 * bande + 1)))
    px_c, px_g = contact.load(), grand.load()
    total = n = 0
    for y in range(grand.height):
        for x in range(grand.width):
            if px_c[x, y] != 255:
                continue
            a, b = px_g[x, y], px_g[x + dx, y + dy]
            total += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
            n += 1
    if not n:
        return None, 0
    return round(total / (n * 3) / 255 * 100, 2), n
```

- [ ] **Step 4 : ajouter `assembler_forme` à `tile_ops.py`**

Ajouter à la fin de `backend/app/services/tile_ops.py` :

```python
def assembler_forme(mat: Image.Image, forme: str, cote: int = 64) -> dict:
    """Un jeu d'UNE tuile de forme (losange ou hexagone), prêt à exporter.

    P5 demande les masques et le raccord des bords correspondants, pas un
    blob hexagonal : la tuile de base suffit à prouver que le réseau boucle,
    et c'est elle que Tiled et Godot savent poser."""
    from app.services import tile_shapes as TF

    largeur, hauteur = TF.dims(forme, cote)
    return {"jeu": "forme", "forme": forme, "cles": [255], "cote": int(cote),
            "largeur": largeur, "hauteur": hauteur, "variantes": 1,
            "graine": 1, "tuiles": [TF.tuile_forme(mat, forme, cote)],
            "vide": 1}
```

- [ ] **Step 5 : refuser LDtk pour une forme non orthogonale, et accepter `forme` à la route**

Dans `backend/app/services/tile_export.py`, ajouter en tête de `ecrire_ldtk` (juste après le docstring) :

```python
    if meta.get("forme", "carre") != "carre":
        raise ValueError(
            "LDtk 1.5.3 est orthogonal : le schema relu le 03/09/2026 ne "
            "porte aucune orientation isometrique ou hexagonale. Exporte "
            f"cette forme ({meta['forme']}) vers Tiled ou Godot.")
```

Dans `backend/app/services/tiles_api.py`, remplacer le corps de `creer_jeu` **entre** la validation de `jeu_nom` et l'appel `TO.assembler_jeu` par une branche de forme, et adapter la fin :

```python
    forme = str(body.get("forme") or "carre")
    if forme not in ("carre", "iso", "hex"):
        raise HTTPException(400, f"forme inconnue: {forme}")
    if forme != "carre":
        jeu = TO.assembler_forme(a, forme, cote)
        img, colonnes, rangees = jeu["tuiles"][0].convert("RGB"), 1, 1
        from app.services import tile_shapes as TF
        raccord = max(
            TF.seam_forme(a, forme, ar, cote)[0] or 0.0
            for ar in TF.decalages(forme, jeu["largeur"], jeu["hauteur"]))
    else:
        jeu = TO.assembler_jeu(a, b, jeu_nom, cote, variantes, graine)
        img, colonnes, rangees = TO.atlas(jeu)
        raccord = TM.raccord_jeu(jeu)
```

Dans le dictionnaire `meta`, remplacer les trois lignes `"jeu": jeu_nom, "cles": jeu["cles"], "cote": cote,` / `"variantes": variantes, "graine": graine,` par — le `meta` doit décrire le jeu **produit**, pas le corps reçu, sinon `_refaire_jeu` reconstruirait autre chose :

```python
            "jeu": jeu["jeu"], "cles": jeu["cles"], "cote": cote,
            "variantes": jeu["variantes"], "graine": jeu["graine"],
            "forme": forme, "largeur": jeu.get("largeur", cote),
            "hauteur": jeu.get("hauteur", cote),
```

Et faire lire cette forme à `_refaire_jeu` : remplacer son corps par :

```python
def _refaire_jeu(meta: dict) -> dict:
    """Refabrique le jeu à l'identique depuis son meta — mêmes sources, même
    graine, donc mêmes octets. C'est la recette qui fait foi, pas un cache."""
    a = _charger_matiere(meta.get("source_a") or {}, "matiere_a")
    if meta.get("forme", "carre") != "carre":
        return TO.assembler_forme(a, meta["forme"], int(meta["cote"]))
    b = _charger_matiere(meta.get("source_b") or {}, "matiere_b")
    return TO.assembler_jeu(a, b, meta["jeu"], int(meta["cote"]),
                            int(meta["variantes"]), int(meta["graine"]))
```

`matiere_b` devient facultative pour une forme (une seule matière suffit) : remplacer la ligne `b = _charger_matiere(body.get("matiere_b") or {}, "matiere_b")` par :

```python
    b = (_charger_matiere(body["matiere_b"], "matiere_b")
         if body.get("matiere_b") else a)
```

Dans `exporter`, remplacer l'appel par une capture du refus motivé :

```python
    try:
        p = {"tiled": TE.ecrire_tsx, "ldtk": TE.ecrire_ldtk,
             "godot": TE.ecrire_tres}[fmt](d, meta)
    except ValueError as e:
        raise HTTPException(400, str(e))
```

Enfin, l'auto-tuilage ne vaut que pour un jeu carré (une forme n'a qu'une tuile, et `composer_carte` chercherait un voisinage absent de `cles`). Ajouter le garde et l'appeler en tête d'`apercu` et de `mesures`, juste après la lecture du `meta` :

```python
def _carre_seulement(meta: dict, quoi: str) -> None:
    if meta.get("forme", "carre") != "carre":
        raise HTTPException(
            400, f"{quoi} ne vaut que pour un jeu carre : une forme "
                 f"{meta['forme']} n a qu une tuile, sans voisinage")
```

```python
    _carre_seulement(meta, "l apercu auto-tuile")   # dans apercu
    _carre_seulement(meta, "la mesure de repetition")   # dans mesures
```

- [ ] **Step 6 : lancer les deux bancs, vérifier qu'ils passent**

Run : `python tests/test_tuiles.py`

Expected : tout ce qui précède plus `PASS test_assembler_forme_rend_un_jeu_exportable`, `PASS test_dimensions_des_formes`, `PASS test_masque_losange_et_hexagone`, `PASS test_raccord_des_bords_correspondants_est_nul`, `PASS test_route_jeu_accepte_iso_et_hex`, puis `OK — 0 echec(s)`.

Run : `python tests/test_tuiles_exports.py` → `PASS test_exports_de_forme_disent_ce_qu_ils_portent` et `OK — 0 echec(s)`.

- [ ] **Step 7 : commit**

```bash
git add backend/app/services/tile_shapes.py backend/app/services/tile_ops.py backend/app/services/tile_export.py backend/app/services/tiles_api.py backend/tests/test_tuiles.py backend/tests/test_tuiles_exports.py
git commit -m 'tuiles : losange 2 pour 1 et hexagone, bords correspondants a zero' -m 'Une tuile de forme ne raccorde pas parce qu on l a decoupee en losange : elle raccorde si sa texture est periodique sous le RESEAU de la forme. Une seule transformation affine y suffit, sans numpy — le carre unite de la matiere est envoye sur le reseau, donc ses vecteurs deviennent des multiples entiers de la taille de la matiere. Mesure sur la bande de contact : les quatre bords iso et les six bords hex raccordent a 0.00, sur 268 a 273 pixels pour l iso et 103 a 169 pour l hex. Les dimensions viennent des tres reels de Godot : 128 sur 64 pour le losange, hexagone a sommet plat de hauteur forcee paire pour que le demi-decalage du reseau reste entier. Et l on dit ce que chaque format porte : Tiled recoit la balise grid pour l isometrique seulement, car l orientation hexagonale appartient a la balise map ; Godot recoit tile_shape et tile_layout ou tile_offset_axis ; LDtk 1.5.3 est orthogonal, l export y est refuse en le disant.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 9 : l'écran `/tilelab` du lot 1 — onglets Tuile · Jeu · Formes

**Pourquoi, avec la mesure :** `/tilelab` est autonome (`main.py:332-355`), donc **coût de bundle nul**. La page fait 220 lignes de JS et une seule chose : image → tuile seamless. On lui ajoute une barre d'onglets et un fichier `jeu.js` qui parle à `/api/tiles` ; le pavage et les scores restent calculés côté client pour l'onglet Tuile (aucun fichier parasite en Bibliothèque), mais **tout ce qui est un fichier est écrit par Python** (Pièges hérités) : atlas, aperçu, exports.

**Files:**
- Modify: `frontend/tilelab/index.html:11-113`
- Modify: `frontend/tilelab/tilelab.css`
- Create: `frontend/tilelab/jeu.js`
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc-miroir qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def _front(rel):
    return (FRONT / "tilelab" / rel).read_text(encoding="utf-8")


def test_ecran_tilelab_porte_les_onglets_du_lot_1():
    """Banc-miroir de front vanilla : on épingle des marqueurs dans le texte
    des fichiers. Mesure FAIBLE (elle ne prouve pas le rendu) — elle garde
    seulement les points de contact avec l API, qui eux sont mesurés."""
    html = _front("index.html")
    assert 'id="tabTuile"' in html and 'id="tabJeu"' in html
    assert 'id="tabFormes"' in html
    assert 'src="jeu.js"' in html
    assert 'src="tilelab.js"' in html            # l'onglet Tuile survit
    for ident in ("panJeu", "panFormes", "matA", "matB", "jeuKind", "jeuCote",
                  "jeuVariantes", "jeuRun", "jeuAtlas", "jeuApercu",
                  "jeuMesures", "expTiled", "expLdtk", "expGodot",
                  "formeKind", "formeRun"):
        assert f'id="{ident}"' in html, ident

    js = _front("jeu.js")
    for route in ('"/api/tiles/jeu"', "/apercu", "/mesures", "/export"):
        assert route in js, route
    # les exports passent par le backend, jamais par une construction client
    assert "tileset.tsx" not in js and "wangid" not in js, \
        "le .tsx est ecrit par Python, pas par le navigateur"
    assert "atlas.png" not in js or "/fichier/atlas.png" in js
    # les trois mesures sont AFFICHÉES, avec leur verdict
    for mot in ("raccord", "repetition", "eclairage", "verdict"):
        assert mot in js, mot
    css = _front("tilelab.css")
    assert ".tl-tabs" in css and ".tl-grid" in css


def test_le_hub_du_bundle_pointe_toujours_sur_tilelab():
    """Coût de patch : AUCUNE tâche de ce plan ne touche frontend/dist. On
    vérifie seulement que l'ancre posée par patch_bundle_tilelab tient."""
    patch = (RACINE / "scripts" / "patch_bundle_tilelab.py").read_text("utf-8")
    assert 'src:"/tilelab/"' in patch
    assert 'tb("tiles","🧱 Tuiles")' in patch
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_ecran_tilelab_porte_les_onglets_du_lot_1` avec `AssertionError` sur `'id="tabTuile"'`, puis `ROUGE — 1 echec(s)`. `test_le_hub_du_bundle_pointe_toujours_sur_tilelab` passe déjà.

- [ ] **Step 3 : poser la barre d'onglets et les deux panneaux dans `index.html`**

Dans `frontend/tilelab/index.html`, remplacer la ligne `<main class="panes tl-panes">` par :

```html
<nav class="tl-tabs" role="tablist">
  <button id="tabTuile" class="tl-tab on" role="tab">🧱 Tuile</button>
  <button id="tabJeu" class="tl-tab" role="tab">🧩 Jeu</button>
  <button id="tabFormes" class="tl-tab" role="tab">🔷 Formes</button>
</nav>

<main class="panes tl-panes" id="panTuile">
```

puis, **juste avant** `<div id="toast" class="toast hidden"></div>`, insérer :

```html
<main class="panes tl-panes hidden" id="panJeu">
  <section class="pane">
    <div class="pane-head"><h2>Deux matières</h2></div>
    <div class="grid2">
      <label class="fld">Matière A <span class="unit">terrain</span>
        <select id="matA"></select></label>
      <label class="fld">Matière B <span class="unit">fond</span>
        <select id="matB"></select></label>
      <label class="fld">Jeu
        <select id="jeuKind">
          <option value="blob47" selected>Blob 47 (8 voisins)</option>
          <option value="blob16">Blob 16 (4 arêtes)</option>
        </select></label>
      <label class="fld">Côté <span class="unit">px</span>
        <select id="jeuCote"><option>32</option><option selected>64</option>
          <option>128</option></select></label>
      <label class="fld">Variantes <span class="unit">1 à 5</span>
        <input id="jeuVariantes" type="number" min="1" max="5" value="3"></label>
      <label class="fld">Graine
        <input id="jeuGraine" type="number" min="0" value="1"></label>
    </div>
    <div class="genrow">
      <button id="jeuRun" class="btn primary big"
              title="Local et gratuit (PIL)">🧩 Fabriquer le jeu</button>
      <span class="cost">gratuit · local</span>
    </div>
    <div id="jeuStatus" class="status hidden"></div>
  </section>

  <section class="pane">
    <div class="pane-head"><h2>Le jeu</h2>
      <span id="jeuInfo" class="counter">—</span></div>
    <figure class="tl-grid"><figcaption>Atlas</figcaption>
      <img id="jeuAtlas" alt="atlas du jeu de tuiles"></figure>
    <div class="genrow">
      <button id="jeuApercuBtn" class="btn">🎲 Aperçu 8×8</button>
      <button id="jeuMesuresBtn" class="btn">📏 Mesurer</button>
    </div>
    <figure class="tl-grid"><figcaption>Aperçu auto-tuilé</figcaption>
      <img id="jeuApercu" alt="apercu 8x8"></figure>
    <div id="jeuMesures" class="tl-scores"></div>
    <div class="exports">
      <button id="expTiled" class="btn">⬇ Tiled .tsx</button>
      <button id="expLdtk" class="btn">⬇ LDtk .ldtk</button>
      <button id="expGodot" class="btn">⬇ Godot .tres</button>
    </div>
  </section>
</main>

<main class="panes tl-panes hidden" id="panFormes">
  <section class="pane">
    <div class="pane-head"><h2>Forme de tuile</h2></div>
    <div class="grid2">
      <label class="fld">Matière
        <select id="formeMat"></select></label>
      <label class="fld">Forme
        <select id="formeKind">
          <option value="iso" selected>Losange isométrique 2:1</option>
          <option value="hex">Hexagone à sommet plat</option>
        </select></label>
      <label class="fld">Côté <span class="unit">px</span>
        <select id="formeCote"><option>32</option><option selected>64</option>
        </select></label>
    </div>
    <div class="genrow">
      <button id="formeRun" class="btn primary big">🔷 Fabriquer</button>
      <span class="cost">gratuit · local</span>
    </div>
    <div id="formeStatus" class="status hidden"></div>
  </section>
  <section class="pane">
    <div class="pane-head"><h2>La tuile</h2>
      <span id="formeInfo" class="counter">—</span></div>
    <figure class="tl-grid"><figcaption>Tuile de forme</figcaption>
      <img id="formeImg" alt="tuile de forme"></figure>
    <div class="exports">
      <button id="expFormeTiled" class="btn">⬇ Tiled .tsx</button>
      <button id="expFormeGodot" class="btn">⬇ Godot .tres</button>
    </div>
  </section>
</main>
```

et remplacer la ligne `<script src="tilelab.js"></script>` par :

```html
<script src="tilelab.js"></script>
<script src="jeu.js"></script>
```

- [ ] **Step 4 : écrire `jeu.js`**

Créer `frontend/tilelab/jeu.js` :

```javascript
/* Tile Lab — onglets Jeu et Formes (plan 2026-09-03-plan-tuiles, T9).
   RÈGLE : le navigateur voit et manipule, Python écrit. Aucun .tsx, .ldtk ni
   .tres n'est construit ici — on demande l'export au backend et l'on ouvre
   le fichier qu'il a écrit. */
"use strict";

(function () {
  const $ = (s) => document.querySelector(s);
  const api = {
    async get(p) {
      const r = await fetch("/api" + p);
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    async post(p, body) {
      const r = await fetch("/api" + p, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      return d;
    },
  };
  const etat = { tid: null, forme: null, images: [] };

  function statut(el, msg, err) {
    el.classList.remove("hidden");
    el.classList.toggle("err", !!err);
    el.textContent = msg;
  }
  function vider(el) { el.classList.add("hidden"); el.textContent = ""; }

  /* ── onglets ─────────────────────────────────────────────────────────── */
  const ONGLETS = [["tabTuile", "panTuile"], ["tabJeu", "panJeu"],
                   ["tabFormes", "panFormes"]];
  function onglet(actif) {
    ONGLETS.forEach(([t, p]) => {
      $("#" + t).classList.toggle("on", t === actif);
      $("#" + p).classList.toggle("hidden", t !== actif);
    });
  }
  ONGLETS.forEach(([t]) => { $("#" + t).onclick = () => onglet(t); });

  /* ── les listes de matières = les images de la Bibliothèque ──────────── */
  async function charger() {
    const d = await api.get("/images");
    etat.images = (d.images || []).map((i) => i.filename);
    const opts = etat.images.map((f) => `<option>${f}</option>`).join("");
    ["#matA", "#matB", "#formeMat"].forEach((s) => { $(s).innerHTML = opts; });
    if (etat.images.length > 1) $("#matB").selectedIndex = 1;
  }

  /* ── onglet Jeu ──────────────────────────────────────────────────────── */
  async function fabriquer() {
    const st = $("#jeuStatus");
    try {
      statut(st, "Fabrication du jeu…");
      const d = await api.post("/tiles/jeu", {
        matiere_a: { image: $("#matA").value },
        matiere_b: { image: $("#matB").value },
        jeu: $("#jeuKind").value,
        cote: parseInt($("#jeuCote").value, 10),
        variantes: parseInt($("#jeuVariantes").value, 10),
        graine: parseInt($("#jeuGraine").value, 10) || 1,
        nom: $("#matA").value.replace(/\.[a-z]+$/i, ""),
      });
      etat.tid = d.tid;
      $("#jeuAtlas").src = `/api/tiles/${d.tid}/fichier/atlas.png?t=${Date.now()}`;
      $("#jeuInfo").textContent =
        `${d.tuiles} tuiles · ${d.colonnes}×${d.rangees} · raccord ${d.raccord}`;
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }

  async function apercu() {
    if (!etat.tid) return;
    const st = $("#jeuStatus");
    try {
      statut(st, "Aperçu…");
      const g = Math.floor(Math.random() * 100000);
      const d = await api.post(`/tiles/${etat.tid}/apercu`,
                               { cases: 8, densite: 0.55, graine: g });
      $("#jeuApercu").src = d.url + "?t=" + Date.now();
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }

  async function mesurer() {
    if (!etat.tid) return;
    const st = $("#jeuStatus");
    try {
      statut(st, "Mesures…");
      const d = await api.post(`/tiles/${etat.tid}/mesures`, { graine: 1 });
      const puce = (nom, val, verdict, seuil) =>
        `<span class="tl-chip ${verdict === "ok" ? "good" : "warn"}">` +
        `${nom} : <b>${val}</b> <i>(seuil ${seuil})</i></span>`;
      $("#jeuMesures").innerHTML =
        puce("raccord", d.raccord, d.verdict.raccord, d.seuils.raccord) +
        puce("repetition", d.repetition, d.verdict.repetition,
             d.seuils.repetition) +
        puce("eclairage", d.eclairage_max, d.verdict.eclairage,
             d.seuils.eclairage) +
        puce("ecart", d.ecart_eclairage, d.verdict.ecart_eclairage,
             d.seuils.ecart_eclairage);
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }

  async function exporter(tid, format, st) {
    try {
      statut(st, "Export " + format + "…");
      const d = await api.post(`/tiles/${tid}/export`, { format });
      statut(st, `${d.fichier} écrit (${d.octets} o)`);
      window.open(d.url, "_blank");
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }

  $("#jeuRun").onclick = fabriquer;
  $("#jeuApercuBtn").onclick = apercu;
  $("#jeuMesuresBtn").onclick = mesurer;
  $("#expTiled").onclick = () => etat.tid &&
    exporter(etat.tid, "tiled", $("#jeuStatus"));
  $("#expLdtk").onclick = () => etat.tid &&
    exporter(etat.tid, "ldtk", $("#jeuStatus"));
  $("#expGodot").onclick = () => etat.tid &&
    exporter(etat.tid, "godot", $("#jeuStatus"));

  /* ── onglet Formes ───────────────────────────────────────────────────── */
  $("#formeRun").onclick = async () => {
    const st = $("#formeStatus");
    try {
      statut(st, "Fabrication…");
      const d = await api.post("/tiles/jeu", {
        matiere_a: { image: $("#formeMat").value },
        forme: $("#formeKind").value,
        cote: parseInt($("#formeCote").value, 10),
        nom: $("#formeKind").value,
      });
      etat.forme = d.tid;
      $("#formeImg").src =
        `/api/tiles/${d.tid}/fichier/atlas.png?t=${Date.now()}`;
      $("#formeInfo").textContent =
        `${d.largeur}×${d.hauteur} · raccord ${d.raccord}`;
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  };
  $("#expFormeTiled").onclick = () => etat.forme &&
    exporter(etat.forme, "tiled", $("#formeStatus"));
  $("#expFormeGodot").onclick = () => etat.forme &&
    exporter(etat.forme, "godot", $("#formeStatus"));

  /* poignée QA (harnais de la recette) */
  window.__tljeu = { get state() { return etat; }, onglet, fabriquer,
                     apercu, mesurer, charger };

  charger().catch(() => { /* la Bibliothèque vide n'empêche pas la page */ });
})();
```

- [ ] **Step 5 : ajouter les styles**

Ajouter à la fin de `frontend/tilelab/tilelab.css` :

```css
/* onglets du Tile Lab (plan 2026-09-03-plan-tuiles, T9) */
.tl-tabs { display: flex; gap: 4px; padding: 6px 12px 0; }
.tl-tab {
  background: transparent; color: var(--fg-dim, #9aa4b2);
  border: 0; border-bottom: 2px solid transparent;
  padding: 8px 14px; font: inherit; cursor: pointer;
}
.tl-tab:hover { color: var(--fg, #e6edf3); }
.tl-tab.on { color: var(--cyan, #4cc9f0); border-bottom-color: var(--cyan, #4cc9f0); }
.tl-tab:focus-visible { outline: 2px solid var(--cyan, #4cc9f0); outline-offset: 2px; }
.tl-grid { margin: 10px 0; }
.tl-grid img {
  max-width: 100%; image-rendering: pixelated;
  background: repeating-conic-gradient(#2a2f38 0 25%, #222730 0 50%) 0 0 / 16px 16px;
  border: 1px solid var(--line, #333941);
}
.tl-chip.warn { color: var(--amber, #f2b134); }
```

- [ ] **Step 6 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles.py`

Expected : tout ce qui précède plus `PASS test_ecran_tilelab_porte_les_onglets_du_lot_1` et `PASS test_le_hub_du_bundle_pointe_toujours_sur_tilelab`, puis `OK — 0 echec(s)`.

- [ ] **Step 7 : commit**

```bash
git add frontend/tilelab/index.html frontend/tilelab/tilelab.css frontend/tilelab/jeu.js backend/tests/test_tuiles.py
git commit -m 'tuiles : l ecran gagne les onglets Jeu et Formes, hors bundle' -m 'Tile Lab est une page autonome servie par main.py, donc l ecran coute zero patch de bundle : le hub compile pointe deja sur une iframe vers slash tilelab, et le banc verifie que cette ancre tient sans y toucher. Le navigateur voit et manipule, Python ecrit : aucun tsx, ldtk ni tres n est construit dans le JS, on demande l export au backend et l on ouvre le fichier qu il a ecrit. Le banc du front est un banc miroir de texte, mesure faible qui garde les points de contact avec l API — les mesures fortes sont cote backend.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

### Task 10 (D1) : une matière du Material Forge devient un tileset

**Pourquoi, avec la mesure :** c'est le différenciant nommé par le brief — « la même matière habille la 3D et le niveau 2D ; aucun outil de tuiles ne part d'une matière PBR locale ». Le coût est **une clé de plus** dans `_charger_matiere`, parce que `material_store` range déjà chaque carte en `<mid>/<kind>.png` (mesuré à `material_store.py:939-949`) et que l'albedo y est nommé `basecolor`. Aucun bac de `### R10c` n'est ouvert ici.

**Files:**
- Modify: `backend/app/services/tiles_api.py` (`_charger_matiere`)
- Modify: `frontend/tilelab/jeu.js`, `frontend/tilelab/index.html`
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def test_une_matiere_du_forge_devient_un_tileset():
    """D1 : l'albedo d'une matière PBR devient la tuile de base. On ÉCRIT une
    vraie matière sur disque (basecolor.png + meta.json), comme le Material
    Forge le fait, et l'on relit l'atlas produit."""
    from app.services import material_store as MS
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        mid = MS.new_mid()
        d = MS.material_dir(mid, create=True)
        _bruit(128, 11).save(d / "basecolor.png", "PNG")
        (d / "meta.json").write_text(
            json.dumps({"id": mid, "name": "pierre du banc"}),
            encoding="utf-8")
        b = _poser_image("d1_b.png", _bruit(128, 12))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"materiau": mid}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 32, "variantes": 1, "nom": "d1"})
            assert r.status_code == 200, r.text
            j = r.json()
            assert j["source_a"] == {"materiau": mid}, j["source_a"]
            assert j["raccord"] == 0.0
            with Image.open(TS.tileset_dir(j["tid"]) / "atlas.png") as im:
                assert im.size == (8 * 32, 6 * 32), im.size
            # le jeu se refabrique depuis son meta : la matière est relue
            r2 = await c.post(f"/api/tiles/{j['tid']}/apercu",
                              json={"cases": 6, "graine": 2})
            assert r2.status_code == 200, r2.text
            # un mid inconnu est refusé EN LE DISANT
            r3 = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"materiau": "mat_00000000"},
                "matiere_b": {"image": b}})
            assert r3.status_code == 400 and "mat_00000000" in r3.text
            # un mid hors motif aussi, sans jamais toucher au disque
            r4 = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"materiau": "../evasion"},
                "matiere_b": {"image": b}})
            assert r4.status_code == 400, r4.text

    asyncio.run(scenario())


def test_ecran_offre_les_matieres_du_forge():
    js = _front("jeu.js")
    assert "/materials" in js and "materiau" in js
    html = _front("index.html")
    assert 'id="srcA"' in html and 'id="srcB"' in html
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_une_matiere_du_forge_devient_un_tileset` avec `assert r.status_code == 200` (la route rend 400 : « matiere_a: cle 'image' attendue »), et `FAIL test_ecran_offre_les_matieres_du_forge`, puis `ROUGE — 2 echec(s)`.

- [ ] **Step 3 : accepter `materiau` dans `_charger_matiere`**

Dans `backend/app/services/tiles_api.py`, remplacer le corps de `_charger_matiere` par :

```python
def _charger_matiere(spec: dict, quoi: str) -> Image.Image:
    """Une matière : soit une image de la Bibliothèque (`{"image": nom}`),
    soit l'ALBEDO d'une matière du Material Forge (`{"materiau": mid}`).

    D1 : la même matière PBR habille la 3D et le niveau 2D. `material_store`
    range déjà chaque carte en `<mid>/<kind>.png` — on lit `basecolor`."""
    from app.services import material_store as MS

    if not isinstance(spec, dict):
        raise HTTPException(400, f"{quoi}: objet attendu")

    mid = str(spec.get("materiau") or "").strip()
    if mid:
        if not MS.is_valid_mid(mid):
            raise HTTPException(400, f"{quoi}: identifiant de matiere "
                                     f"invalide: {mid}")
        try:
            p = MS.material_dir(mid) / "basecolor.png"
        except ValueError as e:
            raise HTTPException(400, f"{quoi}: {e}")
        if not p.is_file():
            raise HTTPException(
                400, f"{quoi}: matiere {mid} sans carte basecolor "
                     f"(le Material Forge ne l a pas encore derivee)")
        with Image.open(p) as im:
            return im.convert("RGB").copy()

    nom = str(spec.get("image") or "").strip()
    if not nom:
        raise HTTPException(400, f"{quoi}: cle 'image' ou 'materiau' attendue")
    p = settings.images_path / nom
    if p.name != nom or not p.is_file():
        raise HTTPException(400, f"{quoi}: image introuvable: {nom}")
    with Image.open(p) as im:
        return im.convert("RGB").copy()
```

- [ ] **Step 4 : offrir le choix dans l'écran**

Dans `frontend/tilelab/index.html`, remplacer les deux labels `Matière A` et `Matière B` du panneau `panJeu` par :

```html
      <label class="fld">Matière A <span class="unit">terrain</span>
        <select id="srcA">
          <option value="image" selected>Image de la Bibliothèque</option>
          <option value="materiau">Matière du Material Forge</option>
        </select>
        <select id="matA"></select></label>
      <label class="fld">Matière B <span class="unit">fond</span>
        <select id="srcB">
          <option value="image" selected>Image de la Bibliothèque</option>
          <option value="materiau">Matière du Material Forge</option>
        </select>
        <select id="matB"></select></label>
```

Dans `frontend/tilelab/jeu.js`, remplacer la fonction `charger` et la construction du corps de `fabriquer` par :

```javascript
  async function charger() {
    const d = await api.get("/images");
    etat.images = (d.images || []).map((i) => i.filename);
    let mats = [];
    try {
      const m = await api.get("/materials");
      mats = (m.materials || []).map((x) => ({ id: x.id, nom: x.name || x.id }));
    } catch (e) { mats = []; }   /* le Forge peut n'avoir aucune matière */
    etat.materiaux = mats;
    remplir("#srcA", "#matA");
    remplir("#srcB", "#matB");
    const opts = etat.images.map((f) => `<option>${f}</option>`).join("");
    $("#formeMat").innerHTML = opts;
    if (etat.images.length > 1) $("#matB").selectedIndex = 1;
  }

  function remplir(selSrc, selVal) {
    const kind = $(selSrc).value;
    $(selVal).innerHTML = kind === "materiau"
      ? etat.materiaux.map((m) =>
          `<option value="${m.id}">${m.nom}</option>`).join("")
      : etat.images.map((f) => `<option>${f}</option>`).join("");
  }
  $("#srcA").onchange = () => remplir("#srcA", "#matA");
  $("#srcB").onchange = () => remplir("#srcB", "#matB");

  function source(selSrc, selVal) {
    const v = $(selVal).value;
    return $(selSrc).value === "materiau" ? { materiau: v } : { image: v };
  }
```

et, dans `fabriquer`, remplacer les deux lignes `matiere_a:` / `matiere_b:` par :

```javascript
        matiere_a: source("#srcA", "#matA"),
        matiere_b: source("#srcB", "#matB"),
```

Ajouter `materiaux: []` au littéral `etat` en tête du fichier.

- [ ] **Step 5 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles.py`

Expected : tout ce qui précède plus `PASS test_ecran_offre_les_matieres_du_forge` et `PASS test_une_matiere_du_forge_devient_un_tileset`, puis `OK — 0 echec(s)`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tiles_api.py frontend/tilelab/index.html frontend/tilelab/jeu.js backend/tests/test_tuiles.py
git commit -m 'tuiles : une matiere du Material Forge devient un tileset' -m 'Le differenciant du brief : la meme matiere PBR habille la 3D et le niveau 2D, ce qu aucun outil de tuiles ne fait depuis une matiere locale. Le cout est une cle de plus, parce que material_store range deja chaque carte en mid slash kind point png : on lit basecolor, rien d autre. Un identifiant hors motif est refuse AVANT de toucher au disque, et une matiere sans basecolor derivee est refusee en disant pourquoi. Le banc ecrit une vraie matiere sur disque, comme le Forge, puis relit l atlas produit : le raccord vaut 0.00 et le jeu se refabrique depuis son meta.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 11 (D2) : des tuiles au style d'un lieu de la bible

**Pourquoi, avec la mesure :** le brief dit « la planche et la palette du lieu (R3) contraignent le prompt du jeu de tuiles ». On ne replanifie **rien** de R3 : on lit le lieu tel qu'il existe aujourd'hui (`BibleEntity.kind == "place"`, avec `ref_image` et `style_notes`, mesuré à `storage.py:146-176`) et l'on quantifie sa planche avec `board_service._palette_colors`, la fonction que l'Atelier utilise déjà (`board_service.py:173-180`). La route **rend un prompt**, elle ne génère pas : la génération passe par `/images/generate` qui existe (`routes.py:4424-4436`) et sait déjà déposer sa provenance. C'est ce qui rend cette tâche testable **hors ligne**, sans un seul appel payant.

**Files:**
- Modify: `backend/app/services/tiles_api.py` (`POST /prompt-lieu`)
- Modify: `frontend/tilelab/index.html`, `frontend/tilelab/jeu.js`
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def test_prompt_lieu_porte_la_palette_de_la_planche():
    """D2 : la planche et la palette du lieu contraignent le prompt. La route
    RÉPOND un prompt — elle ne genere rien, donc le banc ne paie rien."""
    from app.services.storage import (BibleEntity, async_session_factory,
                                      init_db)

    async def scenario():
        await init_db()
        planche = _poser_image("lieu_planche.png", _uni(64, (200, 40, 30)))
        async with async_session_factory() as s:
            s.add(BibleEntity(id="lieu-banc", kind="place",
                              name="la crypte turquoise",
                              description="une crypte engloutie",
                              style_notes="pierre humide, lueur cyan",
                              ref_image=planche))
            await s.commit()
        async with _client() as c:
            r = await c.post("/api/tiles/prompt-lieu",
                             json={"entity_id": "lieu-banc",
                                   "surface": "sol de pierre"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["lieu"] == "la crypte turquoise"
            assert d["planche"] == planche
            # la palette est LUE de la planche, pas inventée
            assert len(d["palette"]) == 6, d["palette"]
            assert all(c0.startswith("#") and len(c0) == 7
                       for c0 in d["palette"])
            assert "#c8281e" in d["palette"], d["palette"]   # 200,40,30
            for morceau in ("sol de pierre", "la crypte turquoise",
                            "pierre humide, lueur cyan", "seamless",
                            "top-down", "#c8281e"):
                assert morceau in d["prompt"], morceau
            # aucune image n'a été générée : la route est un formateur
            assert "images" not in d and "filename" not in d

            r2 = await c.post("/api/tiles/prompt-lieu",
                              json={"entity_id": "inconnu"})
            assert r2.status_code == 404 and "inconnu" in r2.text
            # une entité qui n'est pas un lieu est refusée en le disant
            async with async_session_factory() as s:
                s.add(BibleEntity(id="perso-banc", kind="character",
                                  name="le pilote"))
                await s.commit()
            r3 = await c.post("/api/tiles/prompt-lieu",
                              json={"entity_id": "perso-banc"})
            assert r3.status_code == 400 and "lieu" in r3.text.lower()
            # un lieu sans planche donne quand même un prompt, sans palette
            async with async_session_factory() as s:
                s.add(BibleEntity(id="lieu-nu", kind="place", name="le vide"))
                await s.commit()
            r4 = await c.post("/api/tiles/prompt-lieu",
                              json={"entity_id": "lieu-nu"})
            assert r4.status_code == 200, r4.text
            assert r4.json()["palette"] == []
            assert "le vide" in r4.json()["prompt"]

    asyncio.run(scenario())


def test_ecran_offre_le_style_d_un_lieu():
    js = _front("jeu.js")
    assert "/tiles/prompt-lieu" in js and "/bible/entities?kind=place" in js
    html = _front("index.html")
    assert 'id="lieuSel"' in html and 'id="lieuPrompt"' in html
    assert 'id="lieuSurface"' in html and 'id="lieuRun"' in html
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_prompt_lieu_porte_la_palette_de_la_planche` (404 sur `/api/tiles/prompt-lieu`) et `FAIL test_ecran_offre_le_style_d_un_lieu`, puis `ROUGE — 2 echec(s)`.

- [ ] **Step 3 : écrire la route `prompt-lieu`**

Ajouter à `backend/app/services/tiles_api.py` :

```python
#: gabarit du prompt : la surface d'abord, la contrainte de tuile ensuite,
#: le style du lieu et sa palette en dernier — l'ordre où les modèles image
#: pèsent le plus les premiers mots.
GABARIT_LIEU = (
    "{surface}, texture de tuile pour {lieu}. {description}{style}"
    "Vue top-down, orthographique, seamless tileable, eclairage diffus "
    "uniforme, aucune ombre portee, aucun objet reconnaissable, aucun texte. "
    "Palette imposee : {palette}.")


@router.post("/prompt-lieu")
async def prompt_lieu(body: dict):
    """D2 : un prompt de tuile contraint par la planche et la palette d'un
    LIEU de la bible. Cette route ne genere rien — elle formate. La
    generation passe par POST /api/images/generate, qui existe et sait deja
    deposer sa provenance."""
    from sqlalchemy import select

    from app.services.board_service import _palette_colors
    from app.services.storage import BibleEntity, async_session_factory

    eid = str(body.get("entity_id") or "").strip()
    if not eid:
        raise HTTPException(400, "entity_id attendu")
    async with async_session_factory() as session:
        e = (await session.execute(
            select(BibleEntity).where(BibleEntity.id == eid))).scalar_one_or_none()
    if e is None:
        raise HTTPException(404, f"entite de bible inconnue: {eid}")
    if e.kind != "place":
        raise HTTPException(
            400, f"l entite {e.name!r} est de sorte {e.kind!r} : "
                 f"seul un lieu contraint un jeu de tuiles")

    palette: list[str] = []
    planche = (e.ref_image or "").strip()
    if planche and (settings.images_path / planche).is_file():
        try:
            couleurs = _palette_colors(settings.images_path, [planche], 6)
            palette = ["#%02x%02x%02x" % c for c in couleurs]
        except Exception as err:               # noqa: BLE001 — pas bloquant
            logger.warning(f"palette du lieu {eid} illisible: {err}")
            planche = ""
    else:
        planche = ""

    surface = str(body.get("surface") or "sol").strip()[:80]
    prompt = GABARIT_LIEU.format(
        surface=surface, lieu=e.name,
        description=(e.description.strip() + ". ") if e.description else "",
        style=(e.style_notes.strip() + ". ") if e.style_notes else "",
        palette=", ".join(palette) if palette else "libre")
    logger.info(f"tuiles/prompt-lieu {eid}: {len(palette)} couleurs")
    return {"entity_id": eid, "lieu": e.name, "planche": planche,
            "palette": palette, "surface": surface, "prompt": prompt}
```

- [ ] **Step 4 : offrir le lieu dans l'écran**

Dans `frontend/tilelab/index.html`, insérer dans le panneau `panJeu`, **juste avant** `<div class="genrow">` du premier `<section>` :

```html
    <fieldset class="pixelset">
      <legend>Style d'un lieu de la bible (D2)</legend>
      <div class="grid2">
        <label class="fld">Lieu <select id="lieuSel"></select></label>
        <label class="fld">Surface
          <input id="lieuSurface" type="text" value="sol de pierre"></label>
      </div>
      <div class="genrow">
        <button id="lieuRun" class="btn">🎨 Prompt du lieu</button>
      </div>
      <textarea id="lieuPrompt" class="fld" rows="4"
                placeholder="Le prompt contraint par la planche et la palette du lieu apparait ici — a coller dans le generateur d images."></textarea>
    </fieldset>
```

Dans `frontend/tilelab/jeu.js`, ajouter avant la poignée QA :

```javascript
  /* ── D2 : le style d'un lieu de la bible ─────────────────────────────── */
  async function chargerLieux() {
    try {
      const d = await api.get("/bible/entities?kind=place");
      $("#lieuSel").innerHTML = (d.entities || [])
        .map((e) => `<option value="${e.id}">${e.name}</option>`).join("");
    } catch (e) { $("#lieuSel").innerHTML = ""; }
  }
  $("#lieuRun").onclick = async () => {
    const st = $("#jeuStatus");
    try {
      statut(st, "Prompt du lieu…");
      const d = await api.post("/tiles/prompt-lieu", {
        entity_id: $("#lieuSel").value,
        surface: $("#lieuSurface").value,
      });
      $("#lieuPrompt").value = d.prompt;
      statut(st, `Palette du lieu : ${d.palette.join(" ") || "libre"}`);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  };
```

et ajouter `chargerLieux();` juste après l'appel `charger().catch(...)`.

- [ ] **Step 5 : lancer le banc, vérifier qu'il passe**

Run : `python tests/test_tuiles.py`

Expected : tout ce qui précède plus `PASS test_ecran_offre_le_style_d_un_lieu` et `PASS test_prompt_lieu_porte_la_palette_de_la_planche`, puis `OK — 0 echec(s)`.

- [ ] **Step 6 : commit**

```bash
git add backend/app/services/tiles_api.py frontend/tilelab/index.html frontend/tilelab/jeu.js backend/tests/test_tuiles.py
git commit -m 'tuiles : le style d un lieu de la bible contraint le prompt' -m 'On ne replanifie rien de la categorie Chapitres : on lit le lieu tel qu il existe, sa planche et ses notes de style, et l on quantifie la planche avec la fonction meme que l Atelier utilise pour ses palettes. La route REND un prompt, elle ne genere pas : la generation passe par la route d images qui existe et sait deja deposer sa provenance. C est ce qui rend la chose mesurable hors ligne — le banc ecrit un lieu, une planche d un rouge connu, et retrouve ce rouge dans la palette du prompt, sans un seul appel paye. Une entite qui n est pas un lieu est refusee en le disant, et un lieu sans planche donne quand meme un prompt, palette libre.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 12 (D3) : le peintre minimal avec auto-tiling

**Pourquoi, avec la mesure :** « teste le tileset sans quitter l'app » (brief). Le moteur existe déjà : `masque_voisins` + `composer_carte` (T6). Le peintre n'ajoute **aucune règle** — il envoie une grille booléenne, Python compose la carte et écrit `carte.png` + `carte.json`. Le navigateur voit et manipule ; il ne dessine pas le fichier. La grille du peintre est **bornée** (`boucle=False`) là où l'aperçu est torique : c'est la seule différence, et elle est mesurée.

**Files:**
- Modify: `backend/app/services/tiles_api.py` (`POST /{tid}/carte`)
- Create: `frontend/tilelab/peintre.js`
- Modify: `frontend/tilelab/index.html`, `frontend/tilelab/tilelab.css`
- Test: `backend/tests/test_tuiles.py`

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_tuiles.py` :

```python
def test_route_carte_compose_ce_que_le_peintre_a_pose():
    """D3 : le peintre envoie une GRILLE, Python compose. Le PNG et le JSON
    ecrits font foi — le navigateur n'en dessine aucun."""
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        a = _poser_image("pe_a.png", _bruit(128, 21))
        b = _poser_image("pe_b.png", _bruit(128, 22))
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={
                "matiere_a": {"image": a}, "matiere_b": {"image": b},
                "jeu": "blob47", "cote": 32, "variantes": 2, "nom": "pe"})
            tid = r.json()["tid"]
            # une croix de 5x5 : le centre est entouré des 4 arêtes seulement
            g = [[0] * 5 for _ in range(5)]
            for x in range(5):
                g[2][x] = 1
            for y in range(5):
                g[y][2] = 1
            r = await c.post(f"/api/tiles/{tid}/carte",
                             json={"grille": g, "graine": 1})
            assert r.status_code == 200, r.text
            d = r.json()
            plan = d["plan"]
            assert len(plan) == 5 and len(plan[0]) == 5
            # la carte du peintre est BORNÉE : hors grille = vide
            base = TO.BLOB47.index(TO.N | TO.E | TO.S | TO.W) * 2
            assert base <= plan[2][2] < base + 2, plan[2][2]
            assert plan[0][0] == d["vide"], plan[0][0]      # coin non peint
            # le bout gauche du bras : seule la case de DROITE est du terrain
            bout = TO.BLOB47.index(TO.E) * 2
            assert bout <= plan[2][0] < bout + 2, plan[2][0]
            # le PNG et le JSON ÉCRITS, relus
            dossier = TS.tileset_dir(tid)
            with Image.open(dossier / "carte.png") as im:
                assert im.size == (5 * 32, 5 * 32), im.size
            doc = json.loads((dossier / "carte.json").read_text("utf-8"))
            assert doc["plan"] == plan and doc["grille"] == g
            assert doc["cote"] == 32 and doc["tid"] == tid
            assert doc["colonnes"] == 8            # de quoi relire l'atlas
            # les refus, motivés
            r2 = await c.post(f"/api/tiles/{tid}/carte", json={"grille": []})
            assert r2.status_code == 400 and "grille" in r2.text
            r3 = await c.post(f"/api/tiles/{tid}/carte",
                              json={"grille": [[1, 0], [1]]})
            assert r3.status_code == 400 and "rectangulaire" in r3.text
            r4 = await c.post(f"/api/tiles/{tid}/carte",
                              json={"grille": [[1] * 200] * 200})
            assert r4.status_code == 400 and "128" in r4.text

    asyncio.run(scenario())


def test_ecran_porte_le_peintre():
    html = _front("index.html")
    assert 'id="tabPeintre"' in html and 'id="panPeintre"' in html
    for ident in ("peGrille", "peCases", "pePinceau", "peRun", "peImg",
                  "peVider", "peJson"):
        assert f'id="{ident}"' in html, ident
    assert 'src="peintre.js"' in html
    js = _front("peintre.js")
    assert "/carte" in js
    # le peintre n'a AUCUNE règle de tuilage : elle vit côté Python
    assert "canon" not in js and "masque_voisins" not in js
    assert "grille" in js
    css = _front("tilelab.css")
    assert ".pe-case" in css
```

- [ ] **Step 2 : lancer le banc, vérifier qu'il échoue**

Run : `python tests/test_tuiles.py`

Expected : `FAIL test_route_carte_compose_ce_que_le_peintre_a_pose` (404 sur `/carte`) et `FAIL test_ecran_porte_le_peintre` (`FileNotFoundError` sur `peintre.js`), puis `ROUGE — 2 echec(s)`.

- [ ] **Step 3 : écrire la route `carte`**

Ajouter à `backend/app/services/tiles_api.py` :

```python
CASES_MAX = 128


@router.post("/{tid}/carte")
async def carte(tid: str, body: dict):
    """D3 : la carte du peintre. Body: {grille [[0|1]], graine}.

    Le peintre envoie une grille booleenne ; c'est Python qui lit les
    voisinages, choisit les tuiles et compose l'image. La grille du peintre
    est BORNÉE (hors carte = vide), là où l'aperçu 8x8 est torique."""
    meta = TS.read_meta(tid)
    if meta is None:
        raise HTTPException(404, f"jeu de tuiles inconnu: {tid}")
    _carre_seulement(meta, "le peintre")
    grille = body.get("grille")
    if not isinstance(grille, list) or not grille:
        raise HTTPException(400, "grille: liste de lignes non vide attendue")
    largeur = len(grille[0]) if isinstance(grille[0], list) else 0
    if not largeur or any(not isinstance(l, list) or len(l) != largeur
                          for l in grille):
        raise HTTPException(400, "grille: toutes les lignes doivent avoir la "
                                 "meme longueur (grille rectangulaire)")
    if len(grille) > CASES_MAX or largeur > CASES_MAX:
        raise HTTPException(400, f"grille: au plus {CASES_MAX} cases de cote")
    grille = [[1 if v else 0 for v in ligne] for ligne in grille]
    try:
        graine = int(body.get("graine") or 1)
    except (TypeError, ValueError):
        raise HTTPException(400, "graine: entier attendu")

    jeu = _refaire_jeu(meta)
    img, plan = TO.composer_carte(grille, jeu, graine=graine, boucle=False)
    d = TS.tileset_dir(tid, create=True)
    img.save(d / "carte.png", format="PNG")
    doc = {"tid": tid, "jeu": meta["jeu"], "cote": int(meta["cote"]),
           "colonnes": int(meta["colonnes"]), "variantes": jeu["variantes"],
           "vide": jeu["vide"], "graine": graine,
           "grille": grille, "plan": plan}
    tmp = d / "carte.json.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    tmp.replace(d / "carte.json")
    logger.info(f"tuiles/carte {len(grille)}x{largeur}: {tid}")
    return {"tid": tid, "plan": plan, "vide": jeu["vide"],
            "url": f"/api/tiles/{tid}/fichier/carte.png",
            "json": f"/api/tiles/{tid}/fichier/carte.json"}
```

- [ ] **Step 4 : ajouter l'onglet Peintre à l'écran**

Dans `frontend/tilelab/index.html`, ajouter le bouton d'onglet après `tabFormes` :

```html
  <button id="tabPeintre" class="tl-tab" role="tab">🖌 Peintre</button>
```

et, **juste avant** `<div id="toast" class="toast hidden"></div>`, insérer :

```html
<main class="panes tl-panes hidden" id="panPeintre">
  <section class="pane">
    <div class="pane-head"><h2>Pinceau de terrain</h2>
      <span id="peInfo" class="counter">fabrique d'abord un jeu</span></div>
    <div class="grid2">
      <label class="fld">Cases <span class="unit">côté</span>
        <input id="peCases" type="number" min="4" max="32" value="12"></label>
      <label class="fld">Pinceau
        <select id="pePinceau">
          <option value="1" selected>Poser du terrain</option>
          <option value="0">Effacer</option>
        </select></label>
    </div>
    <div id="peGrille" class="pe-grille"></div>
    <div class="genrow">
      <button id="peRun" class="btn primary">🖌 Composer la carte</button>
      <button id="peVider" class="btn">Vider</button>
    </div>
    <div id="peStatus" class="status hidden"></div>
  </section>
  <section class="pane">
    <div class="pane-head"><h2>La carte</h2></div>
    <figure class="tl-grid"><figcaption>carte.png (écrite par Python)</figcaption>
      <img id="peImg" alt="carte peinte"></figure>
    <div class="exports">
      <a id="peJson" class="btn" target="_blank">⬇ carte.json</a>
    </div>
  </section>
</main>
```

et la balise de script :

```html
<script src="peintre.js"></script>
```

- [ ] **Step 5 : écrire `peintre.js`**

Créer `frontend/tilelab/peintre.js` :

```javascript
/* Tile Lab — peintre minimal avec auto-tiling (plan 2026-09-03-plan-tuiles,
   T12 / D3). Le peintre ne connaît AUCUNE règle de tuilage : il tient une
   grille de 0 et de 1, l'envoie, et affiche l'image que Python a composée.
   La règle blob a un seul propriétaire, et c'est tile_ops. */
"use strict";

(function () {
  const $ = (s) => document.querySelector(s);
  const etat = { grille: [], cases: 12 };

  function statut(msg, err) {
    const el = $("#peStatus");
    el.classList.remove("hidden");
    el.classList.toggle("err", !!err);
    el.textContent = msg;
  }

  function neuve(n) {
    etat.cases = n;
    etat.grille = Array.from({ length: n }, () => Array(n).fill(0));
    dessiner();
  }

  function dessiner() {
    const n = etat.cases;
    const g = $("#peGrille");
    g.style.gridTemplateColumns = `repeat(${n}, 1fr)`;
    g.innerHTML = etat.grille.map((ligne, y) => ligne.map((v, x) =>
      `<button class="pe-case${v ? " on" : ""}" data-x="${x}" data-y="${y}"` +
      ` aria-label="case ${x} ${y}"></button>`).join("")).join("");
  }

  let trace = false;
  function poser(el) {
    const x = +el.dataset.x, y = +el.dataset.y;
    if (Number.isNaN(x) || Number.isNaN(y)) return;
    etat.grille[y][x] = +$("#pePinceau").value;
    el.classList.toggle("on", !!etat.grille[y][x]);
  }
  $("#peGrille").addEventListener("mousedown", (e) => {
    if (!e.target.classList.contains("pe-case")) return;
    trace = true; poser(e.target); e.preventDefault();
  });
  $("#peGrille").addEventListener("mouseover", (e) => {
    if (trace && e.target.classList.contains("pe-case")) poser(e.target);
  });
  window.addEventListener("mouseup", () => { trace = false; });

  $("#peCases").onchange = () => {
    const n = Math.max(4, Math.min(32, parseInt($("#peCases").value, 10) || 12));
    $("#peCases").value = n;
    neuve(n);
  };
  $("#peVider").onclick = () => neuve(etat.cases);

  $("#peRun").onclick = async () => {
    const tid = (window.__tljeu && window.__tljeu.state.tid) || null;
    if (!tid) { statut("Fabrique d'abord un jeu dans l'onglet Jeu.", true); return; }
    try {
      statut("Composition…");
      const r = await fetch(`/api/tiles/${tid}/carte`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grille: etat.grille, graine: 1 }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      $("#peImg").src = d.url + "?t=" + Date.now();
      $("#peJson").href = d.json;
      $("#peInfo").textContent = `${etat.cases}×${etat.cases} cases · ${tid}`;
      statut("carte.png et carte.json écrits par Python.");
    } catch (e) { statut("Échec : " + e.message, true); }
  };

  window.__tlpeintre = { get state() { return etat; }, neuve };
  neuve(12);
})();
```

- [ ] **Step 6 : ajouter les styles du peintre**

Ajouter à la fin de `frontend/tilelab/tilelab.css` :

```css
/* peintre (plan 2026-09-03-plan-tuiles, T12) */
.pe-grille {
  display: grid; gap: 1px; margin: 10px 0;
  background: var(--line, #333941); border: 1px solid var(--line, #333941);
  max-width: 420px; user-select: none;
}
.pe-case {
  aspect-ratio: 1; min-height: 12px; padding: 0; border: 0;
  background: var(--bg-base, #171b21); cursor: crosshair;
}
.pe-case.on { background: var(--cyan, #4cc9f0); }
.pe-case:focus-visible { outline: 2px solid var(--cyan, #4cc9f0); outline-offset: -2px; }
```

- [ ] **Step 7 : ajouter l'onglet à la liste de `jeu.js`**

Dans `frontend/tilelab/jeu.js`, remplacer la constante `ONGLETS` par :

```javascript
  const ONGLETS = [["tabTuile", "panTuile"], ["tabJeu", "panJeu"],
                   ["tabFormes", "panFormes"], ["tabPeintre", "panPeintre"]];
```

- [ ] **Step 8 : lancer les deux bancs, vérifier qu'ils passent**

Run : `python tests/test_tuiles.py`

Expected : tout ce qui précède plus `PASS test_ecran_porte_le_peintre` et `PASS test_route_carte_compose_ce_que_le_peintre_a_pose`, puis `OK — 0 echec(s)`.

Run : `python tests/test_tuiles_exports.py` → `OK — 0 echec(s)`.

- [ ] **Step 9 : commit**

```bash
git add backend/app/services/tiles_api.py frontend/tilelab/peintre.js frontend/tilelab/index.html frontend/tilelab/tilelab.css frontend/tilelab/jeu.js backend/tests/test_tuiles.py
git commit -m 'tuiles : un peintre minimal qui eprouve le jeu sans quitter l app' -m 'Le peintre n ajoute aucune regle : le moteur d auto-tuilage est celui de l apercu, un seul proprietaire. Il tient une grille de zeros et de uns, l envoie, et affiche l image que Python a composee — le navigateur voit et manipule, Python ecrit, et le banc verifie que le JS ne contient ni canon ni masque_voisins. Seule difference avec l apercu : la carte du peintre est bornee, hors carte vaut vide, la ou l apercu est torique ; le banc le mesure sur une croix de cinq sur cinq dont le centre porte exactement les quatre aretes et dont les coins restent vides. Les refus sont motives : grille vide, grille non rectangulaire, plus de cent vingt-huit cases de cote.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

| Écarté | Pourquoi, avec la mesure |
|---|---|
| **E1 — Éditeur de niveaux complet** | Réponse 8 du brief : « un peintre **minimal** … teste le tileset sans quitter l'app ». Tiled et LDtk restent les éditeurs, et ce plan leur écrit de vrais fichiers (T3, T4). Le peintre (T12) n'a ni calques, ni objets, ni sauvegarde de projet, ni annulation : il compose une carte et l'écrit. Toute demande d'un de ces quatre points est un **autre** plan. |
| **Chip « Tuiles » du filtre de provenance de la Bibliothèque** | Seule chose de cette catégorie qui coûterait un patch de bundle : les libellés des chips sont **codés en dur** dans `scripts/patch_bundle_libprov.py` (mesuré le 03/09). La source `tuiles` **est** indexée (`library_index.SOURCES`, T2) et filtrable par l'API ; il ne manque que l'étiquette dans l'interface compilée. Le faire imposerait un patch de plus dans la chaîne et un `repatch_all` — pour une étiquette. |
| **Blob hexagonal à 64 tuiles** | P5 demande « masques losange 2:1 et hexagone, raccord testé sur les bords correspondants », pas un jeu de transitions hexagonal. T8 livre la forme, son réseau et ses six bords à 0.00 ; les 64 combinaisons d'arêtes d'un blob hexagonal seraient un jeu complet de plus, sans demande. |
| **Export LDtk d'un jeu iso ou hex** | Le schéma LDtk 1.5.3 relu le 03/09 ne porte **aucune** orientation isométrique ou hexagonale. L'export est refusé **en le disant** (T8), plutôt qu'écrit dans un format que LDtk lirait de travers. |
| **Vérification qu'un fichier exporté s'ouvre vraiment dans Tiled, LDtk ou Godot** | Aucun des trois logiciels n'est installé ni scriptable dans cet environnement (python embarqué, aucun binaire tiers). Les bancs prouvent la **forme** du fichier contre une documentation datée et contre des fichiers réels ; ils ne prouvent pas l'ouverture. Dit franchement en « Incertitudes ». |
| **Delighting de la matière source** | C'est `### R10c` P1, pas cette catégorie. La mesure d'éclairage (T7) **détecte** une matière au dégradé cuit (seuil `ECLAIRAGE_MAX = 8.0`, rampe pleine mesurée à 50.78) et le dit — elle ne le corrige pas. |

---

## Campagne de mutations

### Task 13 : `backend/tests/mutations_tuiles.py`

**Pourquoi, avec la mesure :** un banc vert ne prouve pas qu'il mesure quelque chose. La campagne casse **une** ligne à la fois, exige le rouge attendu, et remet le fichier **à l'octet près** (assertion de SHA-256) — patron mesuré à `backend/tests/mutations_plaque_slicer.py:1-30` et `:360-428`. Une mutation **VERTE** est une assertion qui manque : c'est ainsi que les trous se trouvent.

**Différence avec le patron :** les bancs de ce plan sont des **scripts autonomes** (contrainte du plan), donc la campagne lance `python tests/test_tuiles.py` et lit ses lignes `FAIL <nom>` — au lieu de `pytest -k`. Une collecte cassée se voit au code de sortie et à l'absence de la ligne de bilan `OK — …` / `ROUGE — …`.

**Files:**
- Create: `backend/tests/mutations_tuiles.py`

- [ ] **Step 1 : écrire le lanceur et la liste des mutations**

Créer `backend/tests/mutations_tuiles.py` :

```python
# -*- coding: utf-8 -*-
"""Campagne de mutations des tuiles : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_tuiles.py           # toutes
    python tests/mutations_tuiles.py 3 17      # celles-la

Il MUTE les sources du depot une a une et les REMET a l'octet pres
(assertion de SHA-256), donc il ne se lance pas pendant qu'un autre banc lit
ces fichiers. La liste est l'argument de la revue : chaque mutation nomme le
test qu'elle fait rougir, et une mutation VERTE est une assertion qui manque.

Difference avec mutations_plaque_slicer : les bancs des tuiles sont des
SCRIPTS autonomes, donc on lance `python tests/test_<x>.py` et l'on lit les
lignes `FAIL <nom>`. Une collecte cassee se voit au code de sortie ET a
l'absence de la ligne de bilan.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
OPS = "tests/test_tuiles.py"
EXP = "tests/test_tuiles_exports.py"

# (fichier, ancien, nouveau, banc, tests attendus rouges)
M = [
    # ── tile_ops.py : la table et les masques ────────────────────────────
    ("backend/app/services/tile_ops.py",
     "        if m & coin and not (m & a and m & b):",
     "        if m & coin and not (m & a or m & b):",
     OPS, ["test_table_du_blob_vaut_47_et_16",
           "test_canon_ote_un_coin_sans_ses_deux_aretes"]),
    ("backend/app/services/tile_ops.py",
     "            m &= ~coin",
     "            m |= coin",
     OPS, ["test_canon_ote_un_coin_sans_ses_deux_aretes"]),
    ("backend/app/services/tile_ops.py",
     "    if m & N or m & E:\n        d.rectangle((cote - b, 0, cote - 1, b - 1), fill=255)",
     "    if m & N and m & E:\n        d.rectangle((cote - b, 0, cote - 1, b - 1), fill=255)",
     OPS, ["test_anneau_ne_depend_que_des_aretes",
           "test_raccord_des_paires_legales_est_nul"]),
    ("backend/app/services/tile_ops.py",
     "    if m & N:\n        d.rectangle((b, 0, cote - b - 1, b - 1), fill=255)",
     "    if m & N:\n        d.rectangle((b, 0, cote - b - 1, b), fill=255)",
     OPS, ["test_anneau_ne_depend_que_des_aretes"]),
    ("backend/app/services/tile_ops.py",
     "        if (m & a) and (m & c) and not (m & bit):",
     "        if not (m & bit):",
     OPS, ["test_anneau_ne_depend_que_des_aretes",
           "test_raccord_des_paires_legales_est_nul"]),
    ("backend/app/services/tile_ops.py",
     "    r = max(2, cote // 6)",
     "    r = max(2, cote // 2)",
     OPS, ["test_anneau_ne_depend_que_des_aretes"]),
    ("backend/app/services/tile_ops.py",
     "    d.rectangle((cote - b, 0, cote - 1, cote - 1), fill=0)\n    return m",
     "    return m",
     OPS, ["test_les_variantes_ne_touchent_pas_le_bord"]),
    ("backend/app/services/tile_ops.py",
     "                a, b = varier(A, coeur, dx, dy), varier(B, coeur, dx, dy)",
     "                a, b = ImageChops.offset(A, dx, dy), ImageChops.offset(B, dx, dy)",
     OPS, ["test_les_variantes_ne_touchent_pas_le_bord",
           "test_raccord_du_jeu_a_variantes_reste_nul"]),
    ("backend/app/services/tile_ops.py",
     "    tuiles.append(B.copy())                       # la tuile VIDE, sans terrain",
     "    pass                                          # la tuile VIDE, sans terrain",
     OPS, ["test_assembler_jeu_rend_47_tuiles_plus_la_vide"]),
    ("backend/app/services/tile_ops.py",
     "        if boucle:\n            nx, ny = nx % w, ny % h",
     "        if False:\n            nx, ny = nx % w, ny % h",
     OPS, ["test_masque_voisins_lit_les_huit_directions"]),
    ("backend/app/services/tile_ops.py",
     "        elif not (0 <= nx < w and 0 <= ny < h):\n            continue",
     "        elif False:\n            continue",
     OPS, ["test_masque_voisins_lit_les_huit_directions"]),
    ("backend/app/services/tile_ops.py",
     "                t = idx[masque_voisins(grille, x, y, boucle)] * v \\\n                    + rng.randrange(v)",
     "                t = idx[masque_voisins(grille, x, y, boucle)] * v",
     OPS, ["test_composer_carte_pose_les_bonnes_tuiles"]),
    ("backend/app/services/tile_ops.py",
     "            else:\n                t = jeu[\"vide\"]",
     "            else:\n                t = 0",
     OPS, ["test_composer_carte_pose_les_bonnes_tuiles",
           "test_route_carte_compose_ce_que_le_peintre_a_pose"]),

    # ── tile_metrics.py : les trois mesures ──────────────────────────────
    ("backend/app/services/tile_metrics.py",
     "        x, y = A.crop((w - 1, 0, w, h)), B.crop((0, 0, 1, h))",
     "        x, y = A.crop((0, 0, 1, h)), B.crop((0, 0, 1, h))",
     OPS, ["test_raccord_des_paires_legales_est_nul"]),
    ("backend/app/services/tile_metrics.py",
     "        if not (ma & bit_a):\n            continue",
     "        if False:\n            continue",
     OPS, ["test_raccord_du_jeu_a_variantes_reste_nul"]),
    ("backend/app/services/tile_metrics.py",
     "    return round(max(0.0, 1 - min(ecarts) / moyenne) * 100, 2)",
     "    return round(max(0.0, 1 - sum(ecarts) / len(ecarts) / moyenne) * 100, 2)",
     OPS, ["test_repetition_voit_un_damier_et_pas_un_tirage"]),
    ("backend/app/services/tile_metrics.py",
     "    return round(math.hypot(gauche - droite, haut - bas) / 255 * 100, 2)",
     "    return round(abs(gauche - droite) / 255 * 100, 2)",
     OPS, ["test_eclairage_lit_un_gradient_et_ignore_un_uni"]),
    ("backend/app/services/tile_metrics.py",
     '    g = img.convert("L").resize((cellules, cellules), Image.BOX)',
     '    g = img.convert("L").resize((cellules, cellules), Image.NEAREST)',
     OPS, ["test_eclairage_lit_un_gradient_et_ignore_un_uni"]),
    ("backend/app/services/tile_metrics.py",
     '    "repetition": 70.0,',
     '    "repetition": 5.0,',
     OPS, ["test_repetition_voit_un_damier_et_pas_un_tirage"]),
    ("backend/app/services/tile_metrics.py",
     '        "repetition": "ok" if mesures["repetition"] < SEUILS["repetition"]\n        else "attention",',
     '        "repetition": "ok",',
     OPS, ["test_verdict_nomme_chaque_mesure"]),

    # ── tile_shapes.py : les formes ──────────────────────────────────────
    ("backend/app/services/tile_shapes.py",
     "    return 2 * r, 2 * round(math.sqrt(3) * r / 2)",
     "    return 2 * r, round(math.sqrt(3) * r)",
     OPS, ["test_dimensions_des_formes"]),
    ("backend/app/services/tile_shapes.py",
     '        a, b, c = 2 * s / (3 * r), 0.0, -2 * s / 3',
     '        a, b, c = 2 * s / (3 * r), 0.0, 0.0',
     OPS, ["test_raccord_des_bords_correspondants_est_nul"]),
    ("backend/app/services/tile_shapes.py",
     "        a, b, c = s / w, -s / h, 0.5 * s",
     "        a, b, c = s / w, s / h, 0.5 * s",
     OPS, ["test_raccord_des_bords_correspondants_est_nul"]),
    ("backend/app/services/tile_shapes.py",
     '    return {"N": (0, -hauteur), "NE": (w, -h), "SE": (w, h),\n            "S": (0, hauteur), "SW": (-w, h), "NW": (-w, -h)}',
     '    return {"N": (0, -hauteur), "NE": (w, -h + 1), "SE": (w, h),\n            "S": (0, hauteur), "SW": (-w, h), "NW": (-w, -h)}',
     OPS, ["test_raccord_des_bords_correspondants_est_nul"]),
    ("backend/app/services/tile_shapes.py",
     "    w, h = largeur // 2, hauteur // 2\n    return {\"NE\": (w, -h), \"SE\": (w, h), \"SW\": (-w, h), \"NW\": (-w, -h)}",
     "    w, h = largeur // 2, hauteur // 2\n    return {\"NE\": (w, h), \"SE\": (w, h), \"SW\": (-w, h), \"NW\": (-w, -h)}",
     OPS, ["test_raccord_des_bords_correspondants_est_nul"]),

    # ── tile_store.py : le confinement ───────────────────────────────────
    ("backend/app/services/tile_store.py",
     "    if not is_valid_tid(tid):\n        raise ValueError(f\"Identifiant de jeu de tuiles invalide: {tid!r}\")",
     "    pass",
     OPS, ["test_store_refuse_un_tid_hors_motif"]),
    ("backend/app/services/tile_store.py",
     "    if nom not in FICHIERS:\n        raise ValueError(f\"Fichier inconnu: {nom!r}\")",
     "    pass",
     OPS, ["test_route_jeu_ecrit_un_dossier_lisible"]),
    ("backend/app/services/tile_store.py",
     'TID_RE = re.compile(r"^tile_[0-9a-f]{8}$")',
     'TID_RE = re.compile(r"tile_[0-9a-f]{8}")',
     OPS, ["test_store_refuse_un_tid_hors_motif"]),

    # ── tile_export.py : les trois formats ───────────────────────────────
    ("backend/app/services/tile_export.py",
     '        wangid = ",".join("1" if m & b else "2" for b in TO.BITS)',
     '        wangid = ",".join("1" if m & b else "2" for b in reversed(TO.BITS))',
     EXP, ["test_tsx_relu_par_xml_etree"]),
    ("backend/app/services/tile_export.py",
     '    proba = "1" if variantes == 1 else str(round(1 / variantes, 6)).rstrip("0")',
     '    proba = "1"',
     EXP, ["test_tsx_relu_par_xml_etree"]),
    ("backend/app/services/tile_export.py",
     '    if forme == "iso":\n        ET.SubElement(ts, "grid", {"orientation": "isometric",',
     '    if forme != "carre":\n        ET.SubElement(ts, "grid", {"orientation": "isometric",',
     EXP, ["test_exports_de_forme_disent_ce_qu_ils_portent"]),
    ("backend/app/services/tile_export.py",
     "        elif (m & a) and (m & b):\n            motif[i] = -1\n        else:\n            motif[i] = 0",
     "        else:\n            motif[i] = -1",
     EXP, ["test_les_47_regles_ldtk_sont_mutuellement_exclusives"]),
    ("backend/app/services/tile_export.py",
     "        motif[i] = 1 if m & bit else -1",
     "        motif[i] = 1 if m & bit else 0",
     EXP, ["test_les_47_regles_ldtk_sont_mutuellement_exclusives"]),
    ("backend/app/services/tile_export.py",
     '            "tileRectsIds": [[i * variantes + k] for k in range(variantes)],',
     '            "tileRectsIds": [[i * variantes]],',
     EXP, ["test_ldtk_relu_par_json"]),
    ("backend/app/services/tile_export.py",
     '    if meta.get("forme", "carre") != "carre":',
     '    if False:',
     EXP, ["test_exports_de_forme_disent_ce_qu_ils_portent"]),
    ("backend/app/services/tile_export.py",
     "            for bit, nom in PEERING:\n                if m & bit:",
     "            for bit, nom in PEERING:\n                if True:",
     EXP, ["test_tres_relu_ligne_a_ligne",
           "test_tres_nomme_les_bits_dans_l_ordre_du_plan"]),
    ("backend/app/services/tile_export.py",
     '    (TO.N, "top_side"), (TO.NE, "top_right_corner"), (TO.E, "right_side"),',
     '    (TO.N, "bottom_side"), (TO.NE, "top_right_corner"), (TO.E, "right_side"),',
     EXP, ["test_tres_nomme_les_bits_dans_l_ordre_du_plan"]),
    ("backend/app/services/tile_export.py",
     '    L.append(f"{v % colonnes}:{v // colonnes}/0 = 0")',
     '    L.append(f"{v % colonnes}:{v // colonnes}/0 = 0")\n    L.append(f"{v % colonnes}:{v // colonnes}/0/terrain = 0")',
     EXP, ["test_tres_relu_ligne_a_ligne"]),
    ("backend/app/services/tile_export.py",
     '        if forme == "hex":\n            L.append("tile_offset_axis = 1")     # VERTICAL : sommet plat',
     '        if forme == "hex":\n            L.append("tile_offset_axis = 0")     # VERTICAL : sommet plat',
     EXP, ["test_exports_de_forme_disent_ce_qu_ils_portent"]),

    # ── tiles_api.py : les gardes de la porte ────────────────────────────
    ("backend/app/services/tiles_api.py",
     "    if not 4 <= cases <= 16:\n        raise HTTPException(400, \"cases doit tenir entre 4 et 16\")",
     "    pass",
     OPS, ["test_route_apercu_ecrit_le_png_et_le_plan"]),
    ("backend/app/services/tiles_api.py",
     "        if not MS.is_valid_mid(mid):",
     "        if False:",
     OPS, ["test_une_matiere_du_forge_devient_un_tileset"]),
    ("backend/app/services/tiles_api.py",
     "    if e.kind != \"place\":",
     "    if False:",
     OPS, ["test_prompt_lieu_porte_la_palette_de_la_planche"]),
    ("backend/app/services/tiles_api.py",
     "            palette = [\"#%02x%02x%02x\" % c for c in couleurs]",
     "            palette = []",
     OPS, ["test_prompt_lieu_porte_la_palette_de_la_planche"]),
    ("backend/app/services/tiles_api.py",
     "    if len(grille) > CASES_MAX or largeur > CASES_MAX:",
     "    if False:",
     OPS, ["test_route_carte_compose_ce_que_le_peintre_a_pose"]),
    ("backend/app/services/tiles_api.py",
     "    if not largeur or any(not isinstance(l, list) or len(l) != largeur\n                          for l in grille):",
     "    if False:",
     OPS, ["test_route_carte_compose_ce_que_le_peintre_a_pose"]),
    ("backend/app/services/tiles_api.py",
     "    img, plan = TO.composer_carte(grille, jeu, graine=graine, boucle=False)",
     "    img, plan = TO.composer_carte(grille, jeu, graine=graine, boucle=True)",
     OPS, ["test_route_carte_compose_ce_que_le_peintre_a_pose"]),
    ("backend/app/services/tiles_api.py",
     '    meta["mesures"] = m\n    TS.write_meta(tid, meta)',
     "    pass",
     OPS, ["test_route_mesures_rend_trois_chiffres_par_jeu_et_par_tuile"]),
    ("backend/app/services/tiles_api.py",
     '            400, f"{quoi} ne vaut que pour un jeu carre : une forme "',
     '            200, f"{quoi} ne vaut que pour un jeu carre : une forme "',
     OPS, ["test_route_jeu_accepte_iso_et_hex"]),
    ("backend/app/services/tiles_api.py",
     '            "jeu": jeu["jeu"], "cles": jeu["cles"], "cote": cote,',
     '            "jeu": jeu_nom, "cles": jeu["cles"], "cote": cote,',
     OPS, ["test_route_jeu_accepte_iso_et_hex"]),

    # ── library_index.py : la provenance ─────────────────────────────────
    ("backend/app/services/library_index.py",
     '    ("tile_", "tuiles"),',
     "",
     OPS, ["test_provenance_des_tuiles_est_declaree"]),
]


def rouges(banc):
    """(noms des tests rouges, sortie, erreur). Un banc de ce plan est un
    SCRIPT : il sort 0 tout vert, 1 avec des rouges, et imprime une ligne de
    bilan. Toute autre sortie, ou l'absence de bilan, = collecte cassee."""
    r = subprocess.run([PY, banc], capture_output=True, cwd=R / "backend",
                       timeout=1800)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    bilan = re.search(r"^(OK|ROUGE) — \d+ echec\(s\)$", txt, re.M)
    erreur = r.returncode not in (0, 1) or bilan is None
    return set(re.findall(r"^FAIL (\w+)$", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # l'arbre est en CRLF (autocrlf) : on apparie en LF et l'on reecrit
        # avec la fin de ligne du fichier ; la remise se fait a l'octet pres.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        txt = txt.replace(old, new)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if a not in rg]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1500:], file=sys.stderr)
        elif not manquants:
            verdict = "ROUGE"
        elif rg:
            verdict = "ROUGE(autres)"
        else:
            verdict = "VERTE"
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:16s} {pathlib.Path(rel).name:20s} "
              f"{old.strip()[:44]!r} -> {sorted(rg)}  "
              f"sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : lancer la campagne**

Run (depuis `backend/`) : `python tests/mutations_tuiles.py`

Expected : 50 lignes, **toutes `ROUGE`**, chacune terminée par `sha <10 chiffres>=<les mêmes 10 chiffres>` (le fichier est remis à l'octet près), puis une ligne JSON de bilan. Par exemple :

```
[ 0] ROUGE            tile_ops.py          "if m & coin and not (m & a and m & b):" -> ['test_canon_ote_un_coin_sans_ses_deux_aretes', 'test_table_du_blob_vaut_47_et_16']  sha 3f2a1b9c04=3f2a1b9c04
```

- [ ] **Step 3 : traiter chaque mutation VERTE**

Une ligne `VERTE` **n'est pas un succès** : elle dit qu'aucun test ne voit la faute. Pour chacune, **ajouter l'assertion manquante** au banc concerné, relancer la mutation seule (`python tests/mutations_tuiles.py <n>`), et vérifier qu'elle devient `ROUGE`. Une ligne `ERREUR(collecte)` veut dire que la mutation casse l'import : la remplacer par une mutation qui laisse le module importable (c'est le point de la mesure — on veut un test rouge, pas un banc mort).

- [ ] **Step 4 : lancer les deux bancs une dernière fois**

Run : `python tests/test_tuiles.py` → `OK — 0 echec(s)`
Run : `python tests/test_tuiles_exports.py` → `OK — 0 echec(s)`

- [ ] **Step 5 : commit**

```bash
git add backend/tests/mutations_tuiles.py backend/tests/test_tuiles.py backend/tests/test_tuiles_exports.py
git commit -m 'tuiles : campagne de mutations, 50 fautes qui doivent rougir' -m 'Un banc vert ne prouve pas qu il mesure quelque chose. La campagne casse une ligne a la fois, exige le rouge attendu, et remet le fichier a l octet pres avec une assertion de SHA-256. Elle vise ce qui porte le sens : la regle du coin dans la canonisation, le OU des aretes dans l anneau, le masque de coeur des variantes, la tuile vide, le decalage torique contre le decalage borne, le minimum contre la moyenne dans l auto-correlation, la norme du gradient d eclairage, les coefficients affines des deux formes, le motif LDtk qui distingue moins un de zero, le nom des bits Godot, et les gardes de la porte. Chaque mutation nomme le test qu elle fait rougir : une mutation verte est une assertion qui manque, pas un succes.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Auto-revue (faite le 03/09/2026)

**1. Couverture du périmètre.** Chaque bac de `### R10b` a sa tâche : P1 → T1, T2 ; P2 → T3, T4, T5 ; P3 → T6 ; P4 → T7 ; P5 → T8 ; D1 → T10 ; D2 → T11 ; D3 → T12 ; E1 → « Écarté ». Les huit réponses du brief sont couvertes : (1) blob 47 **et** 16 depuis deux matières, bords testés — T1, T2 ; (2) les trois exports — T3, T4, T5 ; (3) iso **et** hex, chacune avec masque et test de raccord — T8 ; (4) 1 à 5 variantes + aperçu 8×8 à tirage aléatoire — T6 ; (5) source depuis une matière (T10), par prompt au style d'un lieu (T11), par prompt libre (l'onglet Tuile existant + `/images/generate`) ; (6) trois mesures par tuile et par jeu — T7 ; (7) pixel-art par le pipeline local (onglet Tuile, inchangé) et texturées par le seamless (`make_seamless`, inchangé) ; (8) peintre minimal avec auto-tiling, export PNG + JSON — T12.

**2. Cohérence des types et des noms.** `assembler_jeu` rend toujours le dictionnaire `{jeu, cles, cote, variantes, graine, tuiles, vide}` ; `assembler_forme` y ajoute `forme, largeur, hauteur` et garde `cles=[255]`, `variantes=1`, `vide=1` pour que `atlas`, `_taille_tuile`, `ecrire_tsx` et `ecrire_tres` le lisent sans cas particulier. `meta` porte les mêmes clés plus `tid, nom, tuiles, colonnes, rangees, source_a, source_b, raccord, cree_le, forme, largeur, hauteur` et, après T7, `mesures`. `index_de(m, jeu)` est le seul convertisseur voisinage → index ; `TO.BITS` est le seul ordre de bits, lu par `ecrire_tsx` et `PEERING`. `seam_pair(a, b, sens)` prend `'E'` ou `'S'` partout ; `seam_forme(mat, forme, arete, cote, bande)` rend un couple `(score, n)` partout.

**3. Ordre de dépendance.** T2 appelle `tile_metrics.raccord_jeu` : le fragment est posé en T2 (Step 7), complété en T7. T3 pose `ecrire_ldtk`/`ecrire_tres` en `NotImplementedError`, remplacés en T4 et T5. T6 crée `_refaire_jeu`, que T7 et T12 réutilisent. T8 modifie `creer_jeu` créé en T2. T12 réutilise `composer_carte` créé en T6. Aucune tâche n'appelle une fonction définie plus loin sans l'avoir posée.

## Incertitudes non levées

1. **Aucun des trois logiciels cibles n'a ouvert un fichier écrit.** Tiled, LDtk et Godot ne sont ni installés ni scriptables ici. Les bancs prouvent la forme des fichiers contre une documentation **datée** et, pour Godot, contre trois `.tres` **réellement écrits par le moteur** ; ils ne prouvent pas l'ouverture. C'est la limite la plus lourde de ce plan, et elle ne se lève qu'à la main.
2. **L'issue LDtk #944 « Hex or Isometric tile support » est marquée close/completed (06/10/2023), mais rien dans le schéma 1.5.3 relu ne porte d'orientation.** Le plan refuse donc l'export LDtk d'un jeu iso ou hex, en le disant. Si LDtk le supporte par un champ non lu, ce refus est trop strict — à revérifier avant de conclure quoi que ce soit.
3. **Les bancs du front sont des bancs-miroirs de texte.** Ils épinglent des marqueurs dans `index.html`, `jeu.js`, `peintre.js` et `tilelab.css` ; ils ne prouvent **ni** que la page se rend, **ni** que les onglets basculent. C'est le patron du dépôt pour un front vanilla sans navigateur (`test_etabli_canevas.py`), et il a déjà laissé passer un effondrement visuel (mémoire du 28/08 : une grille en `overflow:hidden` contribuant ~0 à la hauteur). Une vérification à l'œil sur `/tilelab` reste nécessaire après T9 et T12.
4. **Le seuil `REPETITION_MAX = 70.0` est calibré sur trois tirages** (19,08 / 20,53 / 21,95) et un damier (100,0), tous avec des matières de bruit. Une paire de matières très proches en teinte pourrait remonter le plancher : si une exécution réelle dépasse 40, refaire la calibration et écrire la nouvelle mesure plutôt que de déplacer le seuil en silence.
5. **`ECLAIRAGE_MAX = 8.0` n'a pas de témoin « à peine trop ».** Les témoins mesurés sont 0,00 (aplat, bruit), 0,87 (tuiles réelles) et 50,78 (rampe pleine) — rien entre 1 et 50. Le seuil est donc placé au jugé dans un intervalle vide ; il faudra une matière réelle à l'éclairage légèrement cuit pour le confirmer.
6. **Le hexagone est à sommet plat, déduit d'un rapport.** `tile_offset_axis = 1` (VERTICAL) avec `tile_size = Vector2i(110, 94)` donne 1,170, proche de 2/√3 = 1,155 : la déduction « sommet plat » est solide mais reste une déduction, pas une phrase de la documentation.
7. **La tuile 48ᵉ (vide) n'existe pas dans LDtk.** Les règles d'auto-layer ne peignent que le terrain ; une case sans terrain reste vide dans le calque, ce qui est le comportement attendu, mais l'atlas exporté contient une case de plus que ce que les règles utilisent. Aucun banc ne dit si LDtk s'en plaint.
