# -*- coding: utf-8 -*-
"""Card Forge — P9 « Forge 3D ». Backend, phase 1 : export par couches.

Monté par `cards/__init__.py` sous `/api/cards/{did}/forge3d`. Chemins RELATIFS.
CE FICHIER APPARTIENT À P9 (règle 8) : aucun autre module ne l'importe, il
n'importe le routeur d'aucun autre.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import math
import os
import re
import shutil
import struct
import time
import uuid
import zipfile
import zlib
from functools import partial, reduce
from pathlib import Path

from fastapi import (APIRouter, BackgroundTasks, File, Form, HTTPException,
                     Request, UploadFile)
from fastapi.responses import FileResponse, Response
from loguru import logger

from .contract import deck_dir
# Couture intra-pièce (legs 6, revue finale 2a) : la géométrie pure vit dans
# forge3d_scene.py (zéro FastAPI) — RÉEXPORTÉE ici pour que tests et route
# n'aient pas à changer d'orthographe. Ce fichier garde le contrat HTTP
# (routes, bornes, blocs miroir).
from .forge3d_scene import (quad_mesh, relief_mesh, mesh_measures,
                            extrude_ring_mesh, ring_area_mm2,
                            write_scene_glb, _write_stl_binary,
                            read_glb, glb_scene_mesh, glb_triangle_estimate,
                            material_pngs, holo_finish, apply_fit_inplace,
                            glass_finish, GLASS_KINDS,
                            trs_de_face, HOLO_KINDS, HOLO_PX,
                            MOTIF_MAX, MOTIF_GAIN, MOTIF_GAIN_DEFAULT,
                            motif_probe)
# DEUXIÈME couture intra-pièce (délestage 2c, tâche 6) : la résolution des
# chaînes du graphe, la fabrique d'UN élément et les règles du GLB d'un nœud
# moteur SERVI vivent dans forge3d_apercu.py — le bloc que l'inspecteur et la
# construction PARTAGENT. RÉEXPORTÉ ici, même doctrine que ci-dessus : les
# tests et les routes ne changent pas d'orthographe. Le sidecar, lui,
# n'importe RIEN d'ici (voir son en-tête) : c'est ce qui rend la couture
# réelle plutôt que décorative.
from . import forge3d_apercu as _APERCU
# CINQ NOMS, PAS ONZE (revue adverse T6) : la première version en réexportait
# onze « pour la compat des tests », et le recensement a montré que SIX
# (`_PROC_KINDS`, `_CHAIN_MAX`, `_source_gagnante`, `_chaine_aval`,
# `_trs_dict`, `_geom_element`) n'étaient lus NULLE PART — ni ici, ni dans les
# tests, ni ailleurs dans le backend : ils n'apparaissaient plus que dans de la
# prose de commentaire. Une compatibilité que personne n'exerce n'est pas de la
# compatibilité, c'est une liste qui grossit. Les cinq qui restent sont LUS :
# trois par le code de ce fichier (`_layer_filename`, `_borne_apercu_glb`,
# `_sous_graphe_apercu`, plus `_resolve_graph_elements`), et deux par les tests
# à travers ce module (`_resolve_graph_elements`, `_PREVIEW_ASM_ID`) — ces
# deux-là sont ÉPINGLÉS comme réexports, sinon le prochain élagage les
# emporterait aussi.
from .forge3d_apercu import (_resolve_graph_elements, _layer_filename,
                             _PREVIEW_ASM_ID, _borne_apercu_glb,
                             _sous_graphe_apercu, nom_element,
                             # T5 : DEUX NOMS REVIENNENT, parce qu'ils sont
                             # LUS (le critère de l'élagage T6 de la 2c, pas
                             # une exception). Le nœud `extrude` est le seul
                             # traitement SANS couche source : sa résolution
                             # ne peut pas passer par `_resolve_graph_elements`
                             # (qui exige une source), mais elle doit
                             # descendre la MÊME chaîne aval et traduire le
                             # MÊME transform — deux recopies auraient dérivé.
                             _chaine_aval, _trs_dict)

router = APIRouter()

MANIFEST_SCHEMA = "card-3d/layers-manifest@1"
ARTIFACT_SCHEMA = "card-3d/artifact@1"
# M5 (revue 2c) : UN SCHEMA A PART pour l'apercu — jamais `ARTIFACT_SCHEMA`.
# Un GLB de node-preview n'est PAS un artefact (il n'est jamais écrit sur
# disque, il ne porte qu'UN élément, il peut disparaître au prochain clic) ;
# lui faire porter le schéma de l'artefact laisserait un lecteur externe
# croire à une sortie durable. `preview: True` dans les extras EST le
# discriminant explicite, ce nom de schéma en est le second, indépendant.
PREVIEW_SCHEMA = "card-3d/apercu@1"

# ── LA TABLE DES COUCHES — BLOC MIROIR ──────────────────────────────────────
# ═══ CF-FORGE3D-LAYERS-BEGIN ═══
# Le miroir JS est dans frontend/cardforge/js/mod-forge3d.js, entre les mêmes
# marqueurs ; test_cards_forge3d compare les deux champ à champ et dans l'ordre.
# Les z sont ceux de la Z_TABLE gelée du CORE (core.js:82).
LAYER_ROLES = [
    {"role": "fond-matiere", "z": [10], "module": "texture"},
    {"role": "illustration", "z": [20], "module": "face"},
    {"role": "voile-matiere", "z": [30], "module": "texture"},
    {"role": "cadre", "z": [40], "module": "frame"},
    {"role": "typographie", "z": [60], "module": "type"},
    {"role": "ornements", "z": [70], "module": "frame"},
]
# ═══ CF-FORGE3D-LAYERS-END ═══

# ── LES CÔTÉS D'UNE SOURCE — BLOC MIROIR (T5, D7) ───────────────────────────
# ═══ CF-FORGE3D-SIDES-BEGIN ═══
# Miroir JS dans mod-forge3d.js ; parité champ à champ, dans l'ordre.
# `front`/`back` : les deux faces PEINTES, celles que `post_layers` exporte
#                  après la preuve d'empilement des peintres (phase 1).
# `capture`      : les couches IMPORTÉES (P10). Elles n'ont pas de preuve
#                  d'empilement — elles n'ont jamais été empilées — et leur
#                  manifeste est le LEUR (`layers_{carte}_capture.json`,
#                  `source: "capture"`), écrit par la pièce Import. Ce n'est
#                  donc PAS une troisième face de la carte : c'est une
#                  troisième PROVENANCE, sur la face avant.
LAYER_SIDES = ("front", "back", "capture")
CAPTURE_SIDE = "capture"
# LES RÔLES QUE LA PROVENANCE `capture` PEUT PORTER, ET RIEN D'AUTRE (D7
# amendé) : le manifeste importé ne liste QUE ce qui existe sur le disque.
# `illustration` est le SUJET détouré (T3, `sujet_recto.png`) — un vrai rôle
# de peintre, tenu par un vrai fichier. `recto` est la FACE ENTIÈRE importée :
# un rôle qui dit ce qu'il est, jamais un rôle de peintre qu'il n'est pas (ni
# `cadre`, ni `fond-matiere` — aucune tâche n'a découpé de bordure ni de fond,
# et un manifeste ne nomme pas un fichier qui n'existe pas).
CAPTURE_ROLES = ("recto", "illustration")
# ═══ CF-FORGE3D-SIDES-END ═══

# ── LE VOCABULAIRE DU GRAPHE — BLOC MIROIR ──────────────────────────────────
# ═══ CF-FORGE3D-NODES-BEGIN ═══
# Miroir JS dans mod-forge3d.js ; test de parité champ à champ.
# `layer`     : source — une couche du manifeste (role + side).
# `plane`     : plan texturé, GRATUIT (quad aux dimensions de la carte).
# `relief`    : dalle en relief, GRATUITE — grille déplacée par l'alpha,
#               solide FERMÉ par construction (imprimable).
# `extrude`   : la COURONNE de contour (T5, D8) — le seul traitement qui
#               n'a PAS de couche source : sa forme vient du FORMAT de la
#               carte, pas d'une image. `contour` nomme laquelle des deux
#               courbes v1 il suit, `width_mm` de combien il rentre depuis la
#               coupe, `depth_mm` de combien il s'élève, `segments` la finesse
#               de ses arcs. Un nœud `material` en aval l'habille — c'est là
#               que le Sceau prismatique de la 3c se branche.
# `mesh3d`    : image→3D par moteur, PAYANT (prix affiché avant).
# `material`  : matière Material Forge + finition (holo ou VERRE, phase 5 D5)
#               sur le nœud amont ; ses `motifs` sont les calques incrustés
#               dans le canal G de l'épaisseur d'iridescence (3c, §6.2bis-d) —
#               une LISTE ORDONNÉE de `{src, gain}`, l'ordre étant l'ordre
#               d'addition. `ao` débraye l'occlusion de la matière (défaut
#               ALLUMÉ : l'état d'avant la phase 5, au bit près).
# `transform` : position/rotation/échelle en mm de carte de l'élément amont.
# `assemble`  : fusionne les amonts en une scène.
# `artifact`  : sorties (GLB + metadata + aperçu + STL si fermé).
# `export`    : POINT DE TÉLÉCHARGEMENT branché sur l'artefact — il choisit
#               LAQUELLE des sorties déjà écrites il sert, et n'en éteint
#               aucune (le bordereau reste entier : voir
#               `_resolve_graph_elements`).
NODE_KINDS = [
    {"kind": "layer", "params": ["role", "side"]},
    {"kind": "plane", "params": ["depth_mm"]},
    {"kind": "relief", "params": ["depth_mm", "base_mm", "grid"]},
    {"kind": "extrude",
     "params": ["contour", "width_mm", "depth_mm", "segments"]},
    {"kind": "mesh3d", "params": ["engine", "texture_prompt", "ultra"]},
    {"kind": "material",
     "params": ["mat", "tile_mm", "finish", "aniso", "ao", "motifs"]},
    {"kind": "transform", "params": ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"]},
    {"kind": "assemble", "params": []},
    {"kind": "artifact", "params": ["name"]},
    {"kind": "export", "params": ["format"]},
]
# ═══ CF-FORGE3D-NODES-END ═══

# Bornes des paramètres (publiées par /info, jamais recopiées à l'écran).
PLANE_DEPTH_MM = (0.0, 5.0)          # écart z entre plans empilés
RELIEF_DEPTH_MM_MAX = 3.0            # relief au-dessus de la base
RELIEF_BASE_MM = (0.1, 2.0)          # épaisseur de la dalle
RELIEF_GRID = (48, 256)              # subdivisions de la grille — axe X (gx)
                                      # SEUL ; gy suit le ratio h_mm/w_mm de
                                      # la carte (un tarot portrait à 256
                                      # donne gy=439, ~452k triangles)
RELIEF_GRID_DEFAULT = 160

# ── extrude (T5, D8) : la couronne de contour ──────────────────────────────
# LE PLANCHER PARTAGÉ AVEC LE SCEAU. `frame.py:SEAL_MIN_MM` (:519) vaut 0,2 mm
# — « le trait minimal d'un imprimeur foil (§6.2bis-b) ». Une couronne plus
# ÉTROITE que ce trait ne se dore pas, et une couronne moins HAUTE que lui ne
# se sent pas sous le doigt : le même chiffre borne donc la largeur ET la
# profondeur. VALEUR RECOPIÉE, JAMAIS IMPORTÉE (règle 8 : ce fichier n'importe
# le module d'aucune voisine — même patron que `_dpi_to_ppm` et
# `_SEAL_KIND_DEFAULT`), et le test de la pièce LIT `frame.py` pour épingler
# le jumeau au lieu de croire ce commentaire.
EXTRUDE_MIN_MM = 0.2
EXTRUDE_WIDTH_MM = (EXTRUDE_MIN_MM, 20.0)
EXTRUDE_DEPTH_MM = (EXTRUDE_MIN_MM, 5.0)
# LES DEUX CONTOURS NOMMÉS v1 (D8). Ils partagent la MÊME courbe — le
# rectangle arrondi de la COUPE, au rayon de coin du format — et se
# distinguent par leur largeur PAR DÉFAUT. Correspondance publiée, comme
# demandé : `sceau` reprend `frame.py:SEAL_DEFAULTS["width_mm"]` (:522, 1,2 mm
# — « l'anneau épouse la coupe et creuse vers l'intérieur sur width_mm »),
# `cadre` prend une bande de cadre plus large. Le vrai TRACÉ vectoriel de P2
# (contour SVG) est la v2 nommée du plan, pas un troisième mot ici.
EXTRUDE_CONTOURS = ("cadre", "sceau")
EXTRUDE_WIDTH_DEFAULT = {"cadre": 2.0, "sceau": 1.2}
EXTRUDE_DEPTH_DEFAULT = 0.6
# LE PLANCHER DE `segments`, MESURÉ (banc du 24/08, poker 63x88 r=3, largeur
# 1,2 mm — aire analytique 351,70 mm2) :
#   1 station par coin  ->  178,32 mm2, soit **-49,3 %** : l'arc devient un
#                           point, le rectangle arrondi devient un losange ;
#   2 stations (ici)    ->  345,12 mm2, -1,87 % (une corde par coin) ;
#   3 stations          ->  349,89 mm2, -0,51 % ; 25 -> -0,004 %.
# L'aire d'un capuchon ne s'ANNULE jamais par le compte de segments — elle
# converge par au-dessous, de façon monotone : ce qui l'annule, MESURÉ, c'est
# la LARGEUR à la demi-carte (à 31,5 mm sur un poker, l'appariement d'arêtes
# tombe et `mesh_measures` rend `closed: False`). D'où DEUX gardes de nature
# différente : ce plancher-ci contre la dégénérescence de FORME, et le rabot
# géométrique de `post_build3d` contre l'inversion du contour.
EXTRUDE_SEGMENTS = (1, 64)
EXTRUDE_SEGMENTS_DEFAULT = 24         # -0,004 % d'écart au volume analytique
RELIEF_GRID_PREVIEW = 96             # l'apercu d'UN noeud (node-preview, 2c)
                                      # privilegie la vitesse : le vrai grid
                                      # ne joue qu'au build (post_build3d,
                                      # 2a : 256 max) — celui-ci n'est JAMAIS
                                      # ecrit sur le noeud, juste plafonne
                                      # pour CETTE reponse ephemere.

# ── mesh3d (2b) : les 7 moteurs — 5 fal (asset3d_service) + Meshy direct ────
MESH3D_ENGINES = [
    {"id": "tripo",   "provider": "fal",   "label": "Tripo v2.5"},
    {"id": "hunyuan", "provider": "fal",   "label": "Hunyuan3D v2"},
    {"id": "trellis", "provider": "fal",   "label": "TRELLIS"},
    {"id": "rodin",   "provider": "fal",   "label": "Rodin"},
    {"id": "triposr", "provider": "fal",   "label": "TripoSR"},
    {"id": "meshy-6", "provider": "meshy", "label": "Meshy 6"},
    {"id": "meshy-7", "provider": "meshy", "label": "Meshy 7"},
]
MESH3D_DEFAULT_ENGINE = "meshy-7"     # la demande d'origine : « pour les textures »
MESH3D_PROMPT_MAX = 600
# littéraux PARTAGÉS entre le prix de /info (_engine_table) et le payload du
# job (Task 4) — une seule vérité, jamais recopiés d'un côté à l'autre.
MESH3D_TEXTURE_RES = "2k"
MESH3D_SHOULD_TEXTURE = True
MESH3D_UPLOAD_PX = 2048               # côté long envoyé aux moteurs — un moteur
                                      # texture en 2k, le 300 DPI n'y gagne rien
MESH3D_POLL_S = 4.0                   # période de poll Meshy (0.05 en mock)
MESH3D_TIMEOUT_S = 1800.0             # 30 min — après quoi le job échoue NOMMÉ
MESH3D_CLOSED_TRI_MAX = 1_500_000     # au-delà : closed=None (« non mesuré »),
                                      # le gate STL refuse MOTIVÉ (borne mémoire)
MAX_EXT_GLB_BYTES = 64 * 1024 * 1024  # même chiffre que MAX_LAYER_BYTES
MAX_APERCU_GLB_BYTES = 32 * 1024 * 1024  # CF2 (revue 2c) : borne PROPRE à
                                      # l'inspecteur, PAS `MAX_EXT_GLB_BYTES`
                                      # — celle-là borne une FUSION tenue en
                                      # mémoire (plusieurs GLB à la fois),
                                      # celle-ci borne ce qu'UN CLIC envoie
                                      # au model-viewer du navigateur (un
                                      # seul GLB, dans un onglet qui tourne
                                      # déjà) : la moitié suffit largement, et
                                      # un GLB au-delà appartient au noeud
                                      # artefact (qui, lui, sait fusionner et
                                      # dégrader), pas à un clic d'aperçu.

MATERIAL_TILE_MM = (10.0, 200.0)
# UNE seule vérité pour les finitions : les recettes vivent dans le module
# scène, l'écran en reçoit la liste par /info. « aucune » est le seul mot que
# ce fichier ajoute (l'absence de finition n'est pas une recette).
#
# DEUX FAMILLES DEPUIS LA PHASE 5 (D5), UN SEUL CHAMP : `finish` reste UNE
# chaîne, donc les finitions sont EXCLUSIVES par construction — on n'habille
# pas une vitre d'un film irisé. Les deux vocabulaires partent par le MÊME
# canal (/info, `material_limits`), séparément listés : l'écran doit savoir
# LAQUELLE des deux il montre (le canal d'épaisseur des motifs n'existe que
# côté holo), et il ne peut pas le deviner d'un simple « pas aucune ».
MATERIAL_FINISHES = ("aucune",) + HOLO_KINDS + GLASS_KINDS
# LES CINQ MAPS QU'UNE MATIÈRE PEUT DESCENDRE DANS LE GLB. Écrites une fois,
# ici, parce que `_habille` en RETIRE l'occlusion quand le nœud la débraye —
# deux listes qui dérivent, et la carte cuite ne serait plus celle qui est
# demandée. (§5.2 : la couleur de base vient de la COUCHE, jamais de la
# matière — d'où son absence de cette liste.)
MATERIAL_MAP_KINDS = ("normal", "roughness", "metallic", "ao", "emissive")
# ── LES SOURCES DE MOTIF (3c, §6.2bis-d) — vocabulaire FERMÉ ────────────────
# Trois formes, et PAS un quatrième magasin (décision 4 du plan 3c) : une image
# de calque du jeu (celle que P3 importe déjà), la matière de support importée
# de ce jeu, ou une matière de la boutique. Le sigle à téléverser passe donc
# par la route d'import EXISTANTE — l'utilisateur importe, puis choisit.
# `MOTIF_MAX` et `MOTIF_GAIN` viennent du module scène : c'est LUI qui encode,
# c'est lui qui borne (jamais deux plafonds qui dérivent).
_MOTIF_IMG_RE = re.compile(r"^img:(img_\d+\.png)$")
_MOTIF_MAT_RE = re.compile(r"^mat:(mat_[0-9a-f]{8})$")
MOTIF_PAPER = "paper"
MOTIF_MAX_BYTES = 64 * 1024 * 1024   # même plafond que MAX_LAYER_BYTES : un
                                      # motif est une image de carte, et il est
                                      # PESÉ avant d'être décodé (seul ordre
                                      # qui protège la mémoire, spec 2.5)
# L'AVEU SANS ACCENT, ÉCRIT UNE FOIS. Le bordereau part en ASCII (le reste de
# ce fichier écrit « ignoree », « perime ») — et « rien où incruster » y
# devenait « rien ou incruster », qui se lit comme une alternative et non
# comme un lieu (relevé en revue adverse, F4). La tournure choisie ne peut
# pas se relire de travers une fois l'accent tombé.
_SANS_HOLO = ("motif(s) poses sans finition holographique : aucun endroit "
              "ou s'incruster (le canal d'epaisseur n'existe qu'en argent "
              "ou dorure)")
TRANSFORM_XY_MM = (-100.0, 100.0)
TRANSFORM_Z_MM = (0.0, 10.0)
TRANSFORM_ROT_DEG = (-180.0, 180.0)
TRANSFORM_SCALE = (0.1, 4.0)

# ── le nœud `export` (2c) : le vocabulaire FERMÉ de ses formats ─────────────
# Ce ne sont PAS des sorties de plus : ce sont celles que `post_build3d` écrit
# déjà (le GLB, le STL quand le solide est fermé, le metadata.json ERC-721,
# l'aperçu figé) — un nœud d'export ne fait que NOMMER laquelle il sert. D'où
# le défaut : « glb », la seule sortie qui existe TOUJOURS (le STL peut être
# refusé motivé, l'aperçu n'existe qu'une fois figé).
# Même patron que `LAYER_MODES` / `MATERIAL_FINISHES` : un vocabulaire fermé,
# publié par /info, jamais recopié à l'écran.
EXPORT_FORMATS = ("glb", "stl", "metadata", "preview")

# ── bornes d'entrée — vérifiées AVANT tout décodage (spec 2.5) ──────────────
MAX_LAYER_BYTES = 64 * 1024 * 1024   # un PNG de carte, pas un film — même
                                      # chiffre que le précédent du domaine,
                                      # gltf.py:MAX_ATLAS_BYTES (copie, règle 8)
MAX_LAYER_FILES = 12                 # 6 rôles connus ; marge x2 avant qu'un
                                      # gros lot ne soit décodé pour rien
LAYER_MODES = {"isolee", "empreinte"}  # vocabulaire FERMÉ du CORE (core.js) ;
                                        # un autre mot est un bug à révéler,
                                        # pas une valeur à archiver

# ── bornes du graphe (Task 4) — vérifiées AVANT tout décodage d'image ───────
MAX_GRAPH_ELEMENTS = 12              # 6 rôles connus x 2 côtés — au-delà,
                                      # 400 nommé avant tout travail lourd
MAX_PREVIEW_BYTES = 8 * 1024 * 1024  # une capture d'écran model-viewer,
                                      # pas un film — même patron que
                                      # gltf.py:post_atlas (copie, règle 8)
_ART_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,60}$")
_GRAPH_ITER_MAX = 200                 # borne ANTI-GEL de clean_graph (revue) :
                                       # un graphe UI réel tient en ~15 nœuds ;
                                       # 200 est une borne large, JAMAIS
                                       # atteinte par un usage légitime — elle
                                       # existe pour qu'un JSON hostile à un
                                       # million de nœuds ne gèle pas la boucle
                                       # d'évènements. Le plafond MÉTIER
                                       # (MAX_GRAPH_ELEMENTS) s'applique APRÈS
                                       # résolution, dans build3d — deux
                                       # bornes, deux étages, pas la même chose.


def _panne(e: BaseException) -> str:
    """Le nom d'une panne, JAMAIS vide. `str(e)` seul rend "" sur une
    exception sans message (`raise OSError()`) — un marqueur de dégradation
    vide se relit exactement comme « tout va bien », ce qui est précisément
    le silence que ces marqueurs existent pour rompre."""
    return str(e) or type(e).__name__


def _engine_table() -> list[dict]:
    """Prix AVANT, jamais recopiés : fal en $ (pricing.estimate), Meshy en
    crédits (grille partagée meshy_service) + conversion $ directionnelle."""
    from app.services import pricing
    from app.services import meshy_service as MS
    p = pricing.load()
    rows = []
    for e in MESH3D_ENGINES:
        row = dict(e)
        if e["provider"] == "fal":
            row["price_usd"] = pricing.estimate(
                {"kind": "asset3d", "engine": e["id"]}, p)["total_usd"]
        else:
            cr = MS.credits_image_to_3d(e["id"], "standard", MESH3D_SHOULD_TEXTURE,
                                        MESH3D_TEXTURE_RES)
            row["credits"] = cr
            # M1 (revue) : la grille PARTAGÉE est la seule source du surcoût
            # ultra — jamais recopiée en dur ici (la docstring promet « jamais
            # recopiés », l'ancien `5 if ... else 0` la trahissait).
            row["ultra_extra_credits"] = MS._ultra_extra(e["id"], True)
            row["price_usd"] = round(cr * float(p.get("meshy_credit_usd", 0.02)), 4)
        rows.append(row)
    return rows


@router.get("/info")
async def get_info(did: str):
    """Ce que l'écran doit savoir sans rien recalculer."""
    from .core import read_deck
    from .contract import is_valid_did
    from app.config import settings
    from app.services import material_store
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")

    # Important 1 (revue) : le prix des moteurs (pricing.json + la grille
    # meshy_service) et la liste des matières (disque) sont tous deux de
    # l'IO — DÉPORTÉS par to_thread (même patron que post_layers/post_build3d
    # plus bas) : mesuré, 584 ms de boucle bloquée à 200 matières sans ce
    # détour. Important 2 (revue) : chacun dégrade PLUTÔT que de faire tomber
    # toute la route (doctrine 2.5, jamais 500) — une grille de prix ou une
    # boutique en panne ne doit pas priver l'écran du reste du contrat ; la
    # panne est NOMMÉE (mesh3d.degraded), jamais avalée en silence.
    try:
        engines = await asyncio.to_thread(_engine_table)
        mesh3d_degraded = None
    except Exception as e:
        logger.exception("cards/forge3d: table des moteurs mesh3d indisponible")
        engines = []
        mesh3d_degraded = _panne(e)
    try:
        materials_raw = await asyncio.to_thread(material_store.list_materials)
        materials_degraded = None
    except Exception as e:
        # Résidu de re-revue (Task 3) : la boutique dégradait en SILENCE —
        # `materials: []` était indiscernable d'une boutique réellement vide.
        # La panne est maintenant NOMMÉE, comme celle des moteurs.
        logger.exception("cards/forge3d: liste des matieres indisponible")
        materials_raw = []
        materials_degraded = _panne(e)

    return {"schema": MANIFEST_SCHEMA, "layer_roles": LAYER_ROLES,
            "node_kinds": NODE_KINDS,
            # T5 — LES PROVENANCES ET LEURS RÔLES, SERVIS. L'écran ne recopie
            # NI la liste des côtés NI celle des rôles importables : les deux
            # sont des vocabulaires fermés du contrat, exactement comme
            # `export_formats` et `finishes`.
            "layer_sides": list(LAYER_SIDES),
            "capture_side": CAPTURE_SIDE,
            "capture_roles": list(CAPTURE_ROLES),
            "graph_limits": {
               "plane_depth_mm": list(PLANE_DEPTH_MM),
               "relief_depth_mm_max": RELIEF_DEPTH_MM_MAX,
               "relief_base_mm": list(RELIEF_BASE_MM),
               "relief_grid": list(RELIEF_GRID),
               "relief_grid_default": RELIEF_GRID_DEFAULT,
               "extrude_contours": list(EXTRUDE_CONTOURS),
               "extrude_width_mm": list(EXTRUDE_WIDTH_MM),
               "extrude_width_default": dict(EXTRUDE_WIDTH_DEFAULT),
               "extrude_depth_mm": list(EXTRUDE_DEPTH_MM),
               "extrude_depth_default": EXTRUDE_DEPTH_DEFAULT,
               "extrude_segments": list(EXTRUDE_SEGMENTS),
               "extrude_segments_default": EXTRUDE_SEGMENTS_DEFAULT,
               "max_elements": MAX_GRAPH_ELEMENTS,
               "export_formats": list(EXPORT_FORMATS),
            },
            "mesh3d": {
                "engines": engines,
                "default_engine": MESH3D_DEFAULT_ENGINE,
                "has_fal": bool(settings.FAL_KEY),
                "has_meshy": settings.has_meshy or bool(settings.MESHY_MOCK),
                "meshy_mock": bool(settings.MESHY_MOCK),
                "prompt_max": MESH3D_PROMPT_MAX,
                "degraded": mesh3d_degraded,
            },
            # LES MAPS ET LA COULEUR DE CHAQUE MATIÈRE (phase 5, T4) : le
            # DISQUE fait foi (`read_material` les a déjà relevées — zéro I/O
            # de plus), et l'écran cesse de deviner. Sans elles, il ne pouvait
            # dire ni « cette matière porte une occlusion » ni « c'est CETTE
            # couleur qui teintera le translucide » : deux réglages qui
            # agissaient à l'aveugle.
            "materials": [{"id": m["id"], "name": m["name"],
                           "maps": list(m.get("maps") or []),
                           "color": (m.get("props") or {}).get("color")}
                          for m in materials_raw],
            "materials_degraded": materials_degraded,
            "material_limits": {"tile_mm": list(MATERIAL_TILE_MM),
                                "finishes": list(MATERIAL_FINISHES),
                                # LES DEUX FAMILLES, SÉPARÉMENT (D5) : l'écran
                                # doit savoir laquelle il montre — le bloc des
                                # motifs n'a de sens que sur l'holo (le canal
                                # d'épaisseur n'existe pas dans une vitre), et
                                # l'anisotropie non plus. Le déduire d'un
                                # « pas aucune » était juste tant qu'il n'y
                                # avait qu'une famille ; ça ne l'est plus.
                                "finishes_holo": list(HOLO_KINDS),
                                "finishes_glass": list(GLASS_KINDS),
                                "motif_max": MOTIF_MAX,
                                "motif_gain": list(MOTIF_GAIN),
                                # le DÉFAUT, pas seulement les bornes :
                                # `clean_graph` le pose et l'écran doit poser
                                # LE MÊME (un « 1 » recopié à l'écran ferait
                                # naître un calque que le serveur ramènerait
                                # aussitôt, sans que personne ne le voie).
                                "motif_gain_default": MOTIF_GAIN_DEFAULT},
            "transform_limits": {"xy_mm": list(TRANSFORM_XY_MM),
                                 "z_mm": list(TRANSFORM_Z_MM),
                                 "rot_deg": list(TRANSFORM_ROT_DEG),
                                 "scale": list(TRANSFORM_SCALE)}}


def _scan_motif_sources(did: str) -> dict:
    """Les sources de motif RÉELLEMENT présentes pour ce jeu — du disque,
    jamais devinées (même discipline que `get_fonts` de P3 ou la boutique de
    `get_info`). Chaque entrée porte le `src` EXACT que `clean_graph`
    accepte : l'écran n'a aucune recette à recomposer, donc aucune à faire
    dériver.

    Les images de calque sont triées PAR NUMÉRO, pas par nom : un tri
    lexical mettrait `img_10.png` entre `img_1.png` et `img_2.png` et le
    menu ne suivrait plus l'ordre d'import."""
    d = deck_dir(did) / "type"
    nums = []
    if d.is_dir():
        for p in d.iterdir():
            m = re.fullmatch(r"img_(\d+)\.png", p.name)
            if m and p.is_file():
                nums.append((int(m.group(1)), p.name))
    nums.sort()
    images = [{"src": f"img:{nom}", "label": nom} for _n, nom in nums]
    pap = deck_dir(did) / "texture" / "paper.png"
    paper = ({"src": MOTIF_PAPER, "label": "matiere de support importee"}
             if pap.is_file() else None)
    from app.services import material_store
    return {"images": images, "paper": paper,
            "materials": [{"src": "mat:" + m["id"], "label": m["name"]}
                          for m in material_store.list_materials()]}


@router.get("/motif-sources")
async def get_motif_sources(did: str):
    """Ce que l'écran peut poser en MOTIF sur une finition holographique.

    POURQUOI UNE ROUTE D'ICI, et pas trois appels côté navigateur : les images
    de calque appartiennent à la route de P3 et les matières à celle de la
    boutique — l'écran P9 qui irait les chercher lui-même ferait exactement ce
    que la règle 8 interdit entre pièces, et son menu dériverait le jour où un
    voisin change sa forme de réponse. L'agrégation est SERVEUR, et elle rend
    le vocabulaire du graphe, pas celui des voisins.

    Dégradation NOMMÉE (doctrine 2.5, jamais 500) : un disque en panne ou une
    boutique cassée rend des listes vides ET la panne — un menu vide muet se
    relit « ce jeu n'a rien », ce qui n'est pas la même phrase."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    try:
        out = await asyncio.to_thread(_scan_motif_sources, did)
        out["degraded"] = None
    except Exception as e:
        logger.exception("cards/forge3d: sources de motif indisponibles")
        out = {"images": [], "paper": None, "materials": [],
               "degraded": _panne(e)}
    return out


def _out_dir(did: str, create: bool = False) -> Path:
    d = deck_dir(did) / "forge3d"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _iso_now() -> str:
    """L'horodatage des bordereaux, UNE seule orthographe pour la pièce."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _dpi_to_ppm(dpi: float) -> int:
    """DPI -> pixels par mètre, arrondi demi-haut. 300 -> 11811, 600 -> 23622.

    COPIE LOCALE de la formule de `face.py:dpi_to_ppm` — le domaine impose
    ZÉRO import pièce->pièce (règle 8) : c'est déjà le patron établi par
    `frame.py:dpi_to_ppm` et `print.py:phys_ppm`, chacune sa propre copie,
    chacune sa parité testée contre P1. Le pHYs de cette pièce DOIT porter la
    même densité que celui de P1 pour la même carte : recalculer `ppm` depuis
    `canvas_px / (trim_mm + 2*bleed_mm)` (comme le proposait le plan) dérive
    de l'arrondi ENTIER de `canvas_px` — mesuré jusqu'à 9 px/m d'écart sur
    poker_eu/tarot_eu/mini/square_eu, et une densité X != Y sur plusieurs
    formats. La seule source qui ne dérive jamais est le DPI nominal lui-même."""
    d = float(dpi)
    return int(math.floor(d / 0.0254 + 0.5))


def _card_idx(raw) -> int:
    """Garde entière ≥ 0 — COPIE LOCALE du patron de `_num` ci-dessous (même
    règle 8) : `card` non numérique (« abc ») ou négatif retombe sur 0,
    JAMAIS une exception (spec 2.5, C1). C'est cet index qui distingue les
    fichiers d'une carte de ceux d'une autre dans le même deck — un
    `int(raw)` nu levait `ValueError` sur toute entrée non numérique."""
    try:
        v = float(raw)
    except (TypeError, ValueError, OverflowError):
        return 0
    if not math.isfinite(v):
        return 0
    n = int(v)
    return n if n >= 0 else 0


def _num(raw, default: float, lo: float, hi: float) -> float:
    """Garde numérique — COPIE LOCALE de `gltf.py:_num` (même règle 8 que
    `_dpi_to_ppm` ci-dessus : zéro import pièce->pièce). Toute entrée qui
    n'est pas un nombre fini retombe sur `default`, jamais une exception :
    c'est ce qui manquait à `int(proof_c.get("diff_px") or 0)`, où une liste
    ou un dict levait un `TypeError` non attrapé — 500 reproduit en revue."""
    try:
        v = float(raw)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(lo if v < lo else hi if v > hi else v)


def _motif_src_ok(src) -> bool:
    """Une source de motif est-elle DU VOCABULAIRE ? Liste blanche stricte,
    et la garde `isinstance` D'ABORD pour la même raison que partout dans
    `clean_graph` : un `src` non hachable (une liste, un dict) ne doit pas
    lever au premier `re.match` — jamais 500 sur une entrée hostile.

    Le motif `img:img_{n}.png` ne peut porter NI séparateur NI point autre que
    celui de l'extension : « img:../../meta.json » n'y ressemble pas de loin,
    et c'est délibérément ce contrôle-CI qui le refuse, pas la lecture du
    fichier plus tard (liste blanche AVANT le disque — le patron durci de la
    2c, `get_node_file`).

    `fullmatch`, ET PAS `match` + `$` — le piège pour la TROISIÈME fois dans
    ce dépôt : `$` accepte un saut de ligne FINAL, si bien que
    « img:img_1.png\\n » traversait le nettoyage et allait composer un chemin.
    `_scan_motif_sources`, juste à côté, utilise déjà `fullmatch` : deux
    orthographes de la même règle, et une seule des deux disait vrai."""
    if not isinstance(src, str):
        return False
    if src == MOTIF_PAPER:
        return True
    return bool(_MOTIF_IMG_RE.fullmatch(src) or _MOTIF_MAT_RE.fullmatch(src))


def _clean_motifs(raw) -> list:
    """La PILE de motifs d'un nœud matière, réparée : liste blanche des
    sources, part ramenée dans `MOTIF_GAIN`, plafond `MOTIF_MAX` — dans
    L'ORDRE reçu, qui est l'ordre d'addition (§6.2bis-d).

    Une source hors vocabulaire est JETÉE EN SILENCE, comme un nœud inconnu ou
    une arête orpheline : c'est le contrat de `clean_graph`, qui répare et ne
    raconte pas. L'aveu NOMMÉ appartient à la CONSTRUCTION (`_habille` ->
    `ignored`), seule à savoir si le fichier existe vraiment — une source bien
    formée mais absente du disque est un fait de disque, pas de grammaire."""
    out: list = []
    src_in = raw if isinstance(raw, list) else []
    for m in src_in[:_GRAPH_ITER_MAX]:
        if not isinstance(m, dict) or not _motif_src_ok(m.get("src")):
            continue
        out.append({"src": m["src"],
                    "gain": _num(m.get("gain"), MOTIF_GAIN_DEFAULT,
                                 *MOTIF_GAIN)})
        if len(out) >= MOTIF_MAX:
            break
    return out


def clean_graph(raw) -> dict:
    """Le graphe, réparé clé par clé — patron `clean_options` de P8. Un nœud
    inconnu est jeté, un paramètre hors bornes est ramené, une arête orpheline
    tombe. Ne lève JAMAIS (doctrine 2.5).

    Écart assumé au plan : le plan proposait une garde numérique `_num_or`
    dédiée, au corps STRICTEMENT identique à `_num` ci-dessus. La dupliquer
    dans ce même fichier n'a rien à voir avec la règle 8 (zéro import
    PIÈCE->PIÈCE, qui ne concerne que les frontières ENTRE modules) — ce
    serait juste deux fonctions qui dérivent l'une de l'autre sans raison.
    `clean_graph` réutilise donc `_num` telle quelle.

    Garde supplémentaire (constatée en auto-revue, absente du plan et de son
    test) : `n.get("kind") not in kinds` — et de même pour `role` — LÈVE si
    la valeur reçue est un type non hachable (une liste, un dict : un client
    qui envoie `{"kind": ["layer"]}` au lieu d'une chaîne). `x in un_set`
    hache `x` avant de comparer ; ce n'était pas couvert par le graphe
    « poubelle » du test (qui n'utilisait que des chaînes). D'où le
    `isinstance(..., str)` AVANT tout `in kinds`/`in roles` ci-dessous :
    un TypeError sur une entrée hostile serait exactement le 500 que cette
    fonction existe pour empêcher.

    I1/M1 (revue) : l'id est DÉSINFECTÉ comme `artifact.name` (même charset
    `[A-Za-z0-9._-]`) avant toute comparaison — un id brut du client peut
    porter n'importe quel caractère. La resynthèse anti-collision suffixe
    en BOUCLE jusqu'à unicité : un simple `f"n{i+1}x"` ne suffisait pas —
    mesuré en revue, deux nœuds bruts d'id "n2x" retombaient tous les deux
    sur EXACTEMENT "n2x" (la deuxième collision n'était jamais reconsidérée),
    et l'arête qui visait l'un des deux devenait ambiguë entre les deux.

    P1 (revue, 2c) : le suffixe vit DANS le budget de 24 caractères — un id
    réparé reste un id valide PARTOUT (`_NID_RE`, les routes mesh3d/
    node-preview, les dossiers de nœud). Le premier correctif (« +x » en
    boucle) rouvrait exactement le même défaut d'un cran plus loin : un
    `brut` déjà à 24 caractères + "x" fait 25, que `_NID_RE` (borne
    `{1,24}`) rejette ensuite — le nœud résynthétisé ne pouvait plus jamais
    lancer/poller/prévisualiser son mesh3d, atteignable dès que deux ids
    bruts partagent un préfixe de 24 caractères identiques."""
    from app.services import material_store
    from app.services import meshy_service as MS
    g = raw if isinstance(raw, dict) else {}
    kinds = {k["kind"] for k in NODE_KINDS}
    roles = {r["role"] for r in LAYER_ROLES}
    nodes, ids = [], set()
    nodes_in = g.get("nodes")
    nodes_in = nodes_in if isinstance(nodes_in, list) else []
    nodes_in = nodes_in[:_GRAPH_ITER_MAX]      # borne anti-gel (_GRAPH_ITER_MAX)
    for i, n in enumerate(nodes_in):
        if not isinstance(n, dict):
            continue
        k_val = n.get("kind")
        if not isinstance(k_val, str) or k_val not in kinds:
            continue
        brut = re.sub(r"[^A-Za-z0-9._-]", "_", str(n.get("id") or f"n{i + 1}"))[:24]
        node_id = brut or f"n{i + 1}"
        if node_id in ids:
            # P1 (revue) : le suffixe vit DANS le budget de 24 caracteres —
            # un id repare reste un id valide PARTOUT (_NID_RE, les routes,
            # les dossiers). L'ancien `node["id"] += "x"` poussait un brut
            # DEJA a 24 caracteres a 25, que _NID_RE rejette ensuite : le
            # noeud resynthetise ne pouvait plus jamais lancer/poller/
            # previsualiser (mesure en revue). `base` a 20 caracteres laisse
            # 3 chiffres de marge au compteur — largement assez :
            # `_GRAPH_ITER_MAX` borne le nombre total de noeuds donc de
            # collisions possibles sur un meme prefixe a 200.
            base, k = node_id[:20], 2
            while f"{base}_{k}" in ids:
                k += 1
            node_id = f"{base}_{k}"
        node = {"id": node_id, "kind": n["kind"]}
        ids.add(node["id"])
        if n["kind"] == "layer":
            # LE CÔTÉ D'ABORD, LE RÔLE ENSUITE — l'ordre compte depuis T5 :
            # le vocabulaire des rôles DÉPEND de la provenance. Une source
            # `capture` ne connaît que les rôles que le manifeste importé peut
            # porter (`CAPTURE_ROLES`) ; une face peinte ne connaît que les
            # six rôles de la Z_TABLE. Croiser les deux — un `cadre` en
            # provenance `capture`, un `recto` au recto peint — nommerait un
            # fichier que rien n'écrit jamais.
            s_val = n.get("side")
            node["side"] = (s_val if isinstance(s_val, str) and s_val in LAYER_SIDES
                            else "front")
            r_val = n.get("role")
            connus = (set(CAPTURE_ROLES) if node["side"] == CAPTURE_SIDE
                      else roles)
            node["role"] = r_val if isinstance(r_val, str) and r_val in connus else None
            node["composite"] = bool(n.get("composite"))
            if node["side"] == CAPTURE_SIDE:
                # PAS DE COMPOSITE IMPORTÉ : le composite est le RÉSULTAT de
                # l'empilement des peintres, et une capture n'a jamais été
                # empilée. La face entière importée porte le rôle `recto` —
                # elle se nomme, elle n'emprunte pas le nom d'une preuve.
                node["composite"] = False
            if node["role"] is None and not node["composite"]:
                continue                      # une source sans source n'est rien
        elif n["kind"] == "extrude":
            c_val = n.get("contour")
            node["contour"] = (c_val if isinstance(c_val, str)
                               and c_val in EXTRUDE_CONTOURS
                               else EXTRUDE_CONTOURS[0])
            node["width_mm"] = _num(n.get("width_mm"),
                                    EXTRUDE_WIDTH_DEFAULT[node["contour"]],
                                    *EXTRUDE_WIDTH_MM)
            node["depth_mm"] = _num(n.get("depth_mm"), EXTRUDE_DEPTH_DEFAULT,
                                    *EXTRUDE_DEPTH_MM)
            node["segments"] = int(_num(n.get("segments"),
                                        EXTRUDE_SEGMENTS_DEFAULT,
                                        *EXTRUDE_SEGMENTS))
        elif n["kind"] == "plane":
            node["depth_mm"] = _num(n.get("depth_mm"), 0.0, *PLANE_DEPTH_MM)
        elif n["kind"] == "relief":
            node["depth_mm"] = _num(n.get("depth_mm"), 0.6, 0.05, RELIEF_DEPTH_MM_MAX)
            node["base_mm"] = _num(n.get("base_mm"), 0.3, *RELIEF_BASE_MM)
            node["grid"] = int(_num(n.get("grid"), RELIEF_GRID_DEFAULT, *RELIEF_GRID))
        elif n["kind"] == "mesh3d":
            eng = str(n.get("engine") or "")
            connu = eng in {e["id"] for e in MESH3D_ENGINES}
            node["engine"] = eng if connu else MESH3D_DEFAULT_ENGINE
            node["texture_prompt"] = str(n.get("texture_prompt") or "").strip()[:MESH3D_PROMPT_MAX]
            # amendement du contrôleur (plan 2b) : un moteur inconnu est
            # réparé vers le défaut, mais un drapeau PAYANT ne survit jamais
            # à une réparation — l'utilisateur n'a pas consenti à l'ultra
            # d'un moteur qu'il n'a pas nommé.
            # M8 : UNE SEULE SOURCE D'ÉLIGIBILITÉ À L'ULTRA — la grille
            # partagée de `meshy_service`, celle-là même qui FACTURE le
            # surcoût et que `/info` publie en `ultra_extra_credits`. L'ancien
            # `== "meshy-7"` recopiait ici une règle de tarification : le jour
            # où un moteur de plus le propose, le devis l'annoncerait et le
            # nettoyage l'effacerait, chacun sûr d'avoir raison.
            node["ultra"] = (bool(n.get("ultra")) and connu
                             and MS._ultra_extra(node["engine"], True) > 0)
        elif n["kind"] == "material":
            mid = str(n.get("mat") or "")
            node["mat"] = mid if material_store.is_valid_mid(mid) else None
            node["tile_mm"] = _num(n.get("tile_mm"), 63.0, *MATERIAL_TILE_MM)
            node["finish"] = n.get("finish") if n.get("finish") in MATERIAL_FINISHES else "aucune"
            node["aniso"] = bool(n.get("aniso"))
            # L'OCCLUSION EST ALLUMÉE PAR DÉFAUT, ET C'EST LOAD-BEARING : elle
            # descendait déjà dans le GLB avant la phase 5 (le writer pose
            # `occlusionTexture` dès que la matière en porte une). Un défaut à
            # False aurait effacé l'occlusion de tous les graphes existants
            # SANS UN MOT, sur une tâche qui prétend l'EXPOSER. `is not False`
            # et pas `bool(...)` : c'est l'ABSENCE de la clé qui doit valoir
            # « allumée », pas sa véracité.
            node["ao"] = n.get("ao") is not False
            node["motifs"] = _clean_motifs(n.get("motifs"))
            if node["mat"] is None and node["finish"] == "aucune":
                continue          # une matière sans matière ni finition n'est rien
                                  # — des motifs seuls n'habillent RIEN (ils
                                  # s'incrustent dans une finition, ils ne la
                                  # remplacent pas)
        elif n["kind"] == "transform":
            node["x_mm"] = _num(n.get("x_mm"), 0.0, *TRANSFORM_XY_MM)
            node["y_mm"] = _num(n.get("y_mm"), 0.0, *TRANSFORM_XY_MM)
            node["z_mm"] = _num(n.get("z_mm"), 0.0, *TRANSFORM_Z_MM)
            node["rot_deg"] = _num(n.get("rot_deg"), 0.0, *TRANSFORM_ROT_DEG)
            node["scale"] = _num(n.get("scale"), 1.0, *TRANSFORM_SCALE)
        elif n["kind"] == "artifact":
            nom = str(n.get("name") or "artefact")
            node["name"] = re.sub(r"[^A-Za-z0-9._-]", "_", nom)[:60] or "artefact"
        elif n["kind"] == "export":
            # `isinstance` D'ABORD — mais pas pour la raison qu'on croit, et
            # la nuance compte : `EXPORT_FORMATS` est un TUPLE, dont le `in`
            # est un balayage linéaire de `==`. Une liste y passerait donc
            # SANS lever (`["glb"] in ("glb", …)` rend False, pas TypeError) :
            # le danger n'est pas un 500, c'est un `format` non hachable qui
            # traverse en silence si on relâche la garde plus tard (une
            # migration du tuple vers un `set`, et le TypeError apparaît).
            # Les précédents à hachage RÉEL de cette fonction sont les SETS :
            # `kinds`, `roles`, `vivants` — c'est là que le `in` hache avant
            # de comparer, et c'est là que l'absence de garde lèverait.
            # (`finish`, lui, n'a volontairement PAS de garde : il compare à
            # `MATERIAL_FINISHES`, un tuple. Écrire ici qu'il suit le même
            # patron que les sets apprendrait au lecteur suivant à retirer
            # une garde dont un set a besoin.)
            # Un format inconnu — ou d'un type qu'on ne sait pas lire —
            # RETOMBE sur le seul qui existe toujours plutôt que de tuer le
            # nœud : un point de téléchargement muet vaudrait moins qu'un
            # point de téléchargement réparé.
            fmt = n.get("format")
            node["format"] = (fmt if isinstance(fmt, str) and fmt in EXPORT_FORMATS
                              else EXPORT_FORMATS[0])
        nodes.append(node)
    # Important 3 (revue, amendement du contrôleur) : une arête ne doit
    # survivre que si SES DEUX BOUTS ont survécu au nettoyage. `ids` porte
    # TOUT id vu (y compris un nœud jeté par une branche kind-spécifique :
    # layer sans source, material sans matière ni finition) — filtrer les
    # arêtes dessus laissait des arêtes PENDANTES vers un nœud absent de
    # `nodes` (le graphe 2a en portait déjà, sans test pour le révéler).
    # `vivants` est le sous-ensemble RÉELLEMENT présent dans la sortie.
    # L'id d'un nœud jeté reste « brûlé » dans `ids` (la boucle anti-collision
    # ci-dessus l'a déjà consommé) : c'est acceptable, ça ne fait que décaler
    # une resynthèse future, jamais une collision.
    vivants = {n["id"] for n in nodes}
    edges = []
    edges_in = g.get("edges")
    edges_in = edges_in if isinstance(edges_in, list) else []
    edges_in = edges_in[:_GRAPH_ITER_MAX]      # même borne anti-gel
    for e in edges_in:
        if not isinstance(e, dict):
            continue
        ef, et = e.get("from"), e.get("to")
        # même garde qu'au-dessus : `x in vivants` hache x AVANT de comparer —
        # {"from": ["x"]} lève sinon (un id ne peut être qu'une chaîne).
        if isinstance(ef, str) and isinstance(et, str) and ef in vivants and et in vivants:
            edges.append({"from": ef, "to": et})
    return {"nodes": nodes, "edges": edges}


# ── LA GÉOMÉTRIE PURE, L'ASSEMBLAGE GLB ET L'ÉCRITURE STL ─────────────────────
# `quad_mesh`, `relief_mesh`, `mesh_measures`, `write_scene_glb` et
# `_write_stl_binary` vivent maintenant dans forge3d_scene.py (couture
# legs 6, revue finale 2a) — importés/réexportés en haut de ce fichier.
# Ce module garde le contrat HTTP : routes, bornes, blocs miroir.
#
# `tile_maps`, LUI, VIT ICI et pas là-bas (décision de revue Task 5, 2b) : il
# a besoin de la BOUTIQUE de matières (`material_store`) pour aller chercher
# les maps et cuire les niveaux, quand forge3d_scene.py, lui, est PUR — il ne
# reçoit que des images et rend des octets. Le plan 2b plaçait cette fonction
# dans le module scène ; la pureté de ce module a primé sur la lettre du plan.


def tile_maps(mid, kinds, tile_mm, w_mm, h_mm, out_px=1024):
    """Les maps d'une matière de la boutique, TUILÉES au pas physique
    `tile_mm` sur une toile au ratio de la carte — collage par pavage PIL,
    donc DÉTERMINISTE (aucun aléa, aucun bruit : deux appels rendent les mêmes
    octets). Les niveaux de la matière sont CUITS (`bake_levels`), comme sur
    tous les chemins de sortie du lab Matières : l'écran et le moteur
    reçoivent le même pixel.

    LE TUILAGE EST CUIT DANS LES PIXELS, et c'est le point : le sampler du GLB
    peut rester CLAMP_TO_EDGE partout (invariant de `write_scene_glb` depuis
    la 2a) au lieu de basculer en REPEAT pour ces textures-là — un REPEAT sur
    une carte dont les UV débordent d'un cheveu répéterait le bord, pas le
    motif.

    `mid` introuvable -> ValueError NOMMÉE (l'appelant en fait un refus motivé,
    jamais un 500 — doctrine 2.5). Idem pour une cote nulle, négative ou pas
    numérique du tout : les cotes passent d'abord par `_num` (qui ne lève
    JAMAIS — une chaîne y devient 0.0), et c'est la garde de positivité qui
    refuse, NOMMÉMENT. Sans ce passage, `"31,5"` sortait en TypeError nu sur
    la comparaison, et les trois divisions plus bas en ZeroDivisionError :
    deux 500 sur une simple donnée d'entrée.

    `out_px` est borné à `SC.HOLO_PX` (8..2048) — LE MÊME plafond que les
    finitions, exprès : les deux textures habillent la même carte, un plafond
    dissymétrique n'aurait aucun sens (bornes symétriques, revue Task 5)."""
    from app.services import material_store as MSTORE
    tile_mm = _num(tile_mm, 0.0, -1e6, 1e6)
    w_mm = _num(w_mm, 0.0, -1e6, 1e6)
    h_mm = _num(h_mm, 0.0, -1e6, 1e6)
    if tile_mm <= 0 or w_mm <= 0 or h_mm <= 0:
        raise ValueError(f"cotes de tuilage invalides : tile={tile_mm} "
                         f"w={w_mm} h={h_mm} (toutes strictement positives)")
    out_px = int(_num(out_px, 1024.0, *HOLO_PX))
    mat = MSTORE.read_material(mid)
    if mat is None:
        raise ValueError(f"matière introuvable : {mid}")
    maps = MSTORE.load_maps(mid, kinds=list(set(kinds) | {"basecolor"}))
    maps = MSTORE.bake_levels(maps, mat.get("props"))
    # la toile prend le RATIO de la carte : `out_px` est le GRAND côté, l'autre
    # s'en déduit — une toile carrée étirerait le motif d'un tiers sur une
    # carte 63x88.
    W = out_px if w_mm >= h_mm else max(8, int(round(out_px * w_mm / h_mm)))
    H = out_px if h_mm > w_mm else max(8, int(round(out_px * h_mm / w_mm)))
    # BORNE L'ALLOCATION DÉRIVÉE (résidu de re-revue Task 5) : mêmes entrées
    # légales, jamais 127 Mo d'intermédiaire — même classe que la faute des
    # bornes d'entrée. `tile_mm` va jusqu'à 200 mm et `w_mm` peut valoir
    # 31,75 mm (mini US) : `W * tile_mm / w_mm` atteignait 12 900 px pour une
    # toile de 2048, soit une tuile de 500 Mo en RGB. Une tuile PLUS GRANDE
    # que la toile est de toute façon collée une fois puis rognée — la borner
    # au grand côté de la toile ne change RIEN au pixel rendu.
    tpx = max(4, min(max(W, H), int(round(W * tile_mm / w_mm))))
    out = {}
    from PIL import Image as _I
    for kind in kinds:
        src = maps.get(kind)
        if src is None:
            continue
        # `resize` NU, et pas `material_store.resize_maps` : celui-ci passe par
        # `clean_preview_res`, qui SNAPPERAIT `tpx` sur la liste blanche des
        # tailles servies (128/256/...) et détruirait le pas physique — la
        # raison d'être de cette fonction. Coût connu : une normale
        # rééchantillonnée n'est plus exactement unitaire (`resize_maps`, lui,
        # renormalise) ; l'écart est sous le bruit d'un octet à ces tailles.
        #
        # Filtre EXPLICITE, convention de `material_store.resize_maps:1033` :
        # LANCZOS pour les maps de couleur, BICUBIC pour les maps de données.
        # Le défaut de PIL a déjà changé d'une version à l'autre — l'implicite
        # ferait dépendre nos octets de la version de Pillow installée, et le
        # déterminisme est une PROMESSE ici.
        filtre = (_I.LANCZOS if kind in ("basecolor", "emissive")
                  else _I.BICUBIC)
        tuile = src.resize((tpx, tpx), filtre)
        toile = _I.new(src.mode, (W, H))
        for y in range(0, H, tpx):
            for x in range(0, W, tpx):
                toile.paste(tuile, (x, y))
        out[kind] = toile
    return out


_HEX6_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _paper_hex(raw) -> str:
    """Validation STRICTE `^#[0-9a-fA-F]{6}$` — toute entrée qui n'est pas
    EXACTEMENT de cette forme (mot CSS, court #fff, casse invalide, absent)
    retombe sur "#ffffff", jamais une exception (C2, même discipline que
    `_card_idx`/`_num`)."""
    s = str(raw or "")
    return s if _HEX6_RE.match(s) else "#ffffff"


def _paper_rgba(hexcolor: str) -> tuple[int, int, int, int]:
    """Le papier validé, en RGBA OPAQUE — la base d'empilement de la
    contre-preuve (C2) : la preuve client empile sur PAPER (le fond que le
    moteur peint réellement, core.js) ; empiler sur transparent ici ne
    reproduisait pas le composite dès que le papier de la pièce Matières
    passe à « none » (couche fond-matière entièrement transparente)."""
    r = int(hexcolor[1:3], 16)
    g = int(hexcolor[3:5], 16)
    b = int(hexcolor[5:7], 16)
    return (r, g, b, 255)


def _phys_chunk(ppm_x: int, ppm_y: int) -> bytes:
    data = struct.pack(">IIB", ppm_x, ppm_y, 1)
    return (struct.pack(">I", len(data)) + b"pHYs" + data
            + struct.pack(">I", zlib.crc32(b"pHYs" + data) & 0xFFFFFFFF))


# ── L'espace de couleur — COPIE LOCALE de `face.py:png_srgb_chunks` (règle 8
# : zéro import pièce->pièce, même patron que `_dpi_to_ppm`/`_num` ci-dessus,
# chacune sa propre copie, chacune sa parité testée contre P1). C3 : les
# deux critiques de P1 avaient relevé « ni iCCP, ni sRGB, ni gAMA, ni cHRM » —
# `_stamp_phys` d'ici n'écrivait jusqu'ici que pHYs, la moitié d'un fichier
# de prépresse (spec §4.3). Les couches sont des rendus d'ÉCRAN (canvas 2D,
# jamais un scan étalonné) : intention de rendu PERCEPTUELLE, gamma 1/2,2
# (x100000, valeur libpng) et primaires + point blanc sRGB — les valeurs
# EXACTES que P1 écrit (face.py:671-676 — SRGB_INTENT_PERCEPTUAL/SRGB_GAMA/
# SRGB_CHRM), copiées ici à l'octet, jamais réinventées.
SRGB_INTENT_PERCEPTUAL = 0
SRGB_GAMA = 45455                  # 1/2,2 x 100000, valeur libpng
SRGB_CHRM = (31270, 32900,         # point blanc D65
             64000, 33000,         # rouge
             30000, 60000,         # vert
             15000, 6000)          # bleu


def _chunk(typ: str, payload: bytes) -> bytes:
    t = typ.encode("ascii")
    return (struct.pack(">I", len(payload)) + t + payload
            + struct.pack(">I", zlib.crc32(t + payload) & 0xFFFFFFFF))


def _srgb_chunks() -> list[bytes]:
    """`sRGB` + `gAMA` + `cHRM`, dans l'ordre où libpng (et P1) les écrivent."""
    return [
        _chunk("sRGB", bytes([SRGB_INTENT_PERCEPTUAL])),
        _chunk("gAMA", struct.pack(">I", SRGB_GAMA)),
        _chunk("cHRM", struct.pack(">8I", *SRGB_CHRM)),
    ]


# les 4 chunks de prépresse que `_stamp_phys` pose : un PNG qui en porte déjà
# un est réécrit, jamais doublé (même logique pour les 4, pas seulement pHYs)
_PREPRESS_TYPES = {b"pHYs", b"sRGB", b"gAMA", b"cHRM"}


def _stamp_phys(png: bytes, ppm: tuple[float, float]) -> bytes:
    """Insère sRGB + gAMA + cHRM puis pHYs après l'IHDR — ordre P1 (IHDR ·
    sRGB · gAMA · cHRM · pHYs, `face.py:png_finalize`) : même espace de
    couleur et même densité que l'écran, relus dans les octets par les
    tests. Un PNG déjà estampillé (n'importe lequel des 4 chunks) est
    réécrit, jamais doublé.

    La boucle est BORNÉE et s'arrête à IEND : un PNG à queue parasite (des
    octets après IEND — navigateurs et outils en écrivent bel et bien) passe
    le décodage PIL sans broncher, mais faisait planter `struct.unpack` sur
    un fragment de moins de 4 octets — 500 non attrapé, reproduit en revue."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(400, "PNG attendu")
    ihdr_end = 8 + 8 + struct.unpack(">I", png[8:12])[0] + 4
    out, off = [png[:ihdr_end]], ihdr_end
    out.extend(_srgb_chunks())
    out.append(_phys_chunk(int(round(ppm[0])), int(round(ppm[1]))))
    while off + 8 <= len(png):
        ln = struct.unpack(">I", png[off:off + 4])[0]
        typ = png[off + 4:off + 8]
        end = off + 8 + ln + 4
        if end > len(png):
            break
        if typ not in _PREPRESS_TYPES:
            out.append(png[off:end])
        off = end
        if typ == b"IEND":
            break
    return b"".join(out)


def _open_png(raw: bytes, nom: str):
    """Ouvre un PNG et le convertit en RGBA, ou lève 400 — JAMAIS 500 (spec
    2.5). `format` est lu AVANT `convert()` : la conversion RGBA renvoie une
    image NEUVE dont `.format` vaut None — le vérifier après serait un
    contrôle qui ne contrôle rien.

    COPIE UNIQUE (revue) : `post_layers` et `post_build3d` portaient chacun
    leur propre `_ouvre` imbriquée, quasi identiques — la duplication
    INTRA-fichier contredit la doctrine écrite dans la docstring de
    `clean_graph` (deux fonctions qui dérivent l'une de l'autre sans raison,
    ce que la règle 8 ne couvre PAS puisqu'elle ne concerne que les
    frontières ENTRE modules). La dérive avait déjà commencé : l'une disait
    « reçu », l'autre « recu » — unifiée ici sur « reçu ». `post_preview`
    la consomme aussi, pour un PNG VRAIMENT vérifié (décodé, pas seulement
    sa signature magique)."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        raise HTTPException(400, f"{nom} : PNG illisible ({e})")
    fmt = (im.format or "").upper()
    if fmt != "PNG":
        raise HTTPException(
            400, f"{nom} : PNG attendu, {fmt or 'format inconnu'} reçu")
    return im.convert("RGBA")


@router.post("/layers")
async def post_layers(did: str,
                      layers: list[UploadFile] = File(...),
                      composite: UploadFile = File(...),
                      side: str = Form("front"),
                      card: str = Form("0"),
                      paper: str = Form("#ffffff"),
                      modes: str = Form("{}"),
                      client_proof: str = Form("{}")):
    """N couches PNG alpha + composite -> contre-preuve PIL, estampille,
    ZIP + manifeste. Le navigateur a DÉJÀ prouvé l'empilement chez lui
    (même moteur, pixel strict) ; ici on ré-empile en second avis et on
    écrit LES DEUX mesures dans le manifeste.

    `card` (C1) : l'index de la carte courante, tel que l'écran l'a rendu
    (même valeur que le temps de preuve). Sans lui, les sorties ne portaient
    que deck+side : exporter la carte B écrasait les fichiers de la carte A.
    Les noms de sortie et le manifeste portent désormais `c{idx+1:02d}`.

    `paper` (C2) : la base RÉELLEMENT peinte par le moteur (`PAPER` de
    core.js, jamais une constante recopiée ailleurs). La contre-preuve
    empilait sur transparent ; le ZIP seul ne reproduisait alors pas le
    composite dès que le papier de la pièce Matières passe à « none ».

    `await up.read()` reste async (c'est de l'E/S) ; tout le reste — décodage,
    empilement, mesures, estampilles, zip, écritures — est du calcul pur et
    tourne dans `work()`, déporté par `asyncio.to_thread` (patron des sœurs :
    gltf.py:post_build, gltf.py:post_atlas, print.py:post_card). Mesuré :
    l'inline gelait la boucle d'évènements de 0,45 s (poker 300 DPI) à plus
    de 2,6 s (tarot 600 DPI)."""
    from .core import read_deck, geom_of
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    g = geom_of(doc)
    w, h = g.canvas_px
    face = "back" if str(side).strip().lower() == "back" else "front"
    # C1 : l'identite de la CARTE dans toute la chaine — sans elle, exporter
    # la carte B ecrase les fichiers de la carte A (sorties nommees par
    # deck+side seulement, avant ce correctif).
    idx = _card_idx(card)
    card_label = f"c{idx + 1:02d}"
    # C2 : la base papier — validee AVANT le calcul, jamais recalculee dans
    # `work()` a partir d'une valeur non sure.
    paper_hex = _paper_hex(paper)

    # ── bornes AVANT décodage : compte, puis rôle — aucune des deux ne lit
    #    un octet du corps du fichier ─────────────────────────────────────
    if len(layers) > MAX_LAYER_FILES:
        raise HTTPException(
            400, f"trop de couches ({len(layers)}, maximum {MAX_LAYER_FILES})")
    valid_roles = {r["role"] for r in LAYER_ROLES}
    noms: list[str] = []
    seen: set[str] = set()
    for up in layers:
        nom = (up.filename or "").rsplit(".", 1)[0]
        if nom not in valid_roles:
            raise HTTPException(400, f"{nom!r} : rôle de couche inconnu")
        if nom in seen:
            raise HTTPException(400, f"{nom!r} : couche envoyée deux fois")
        seen.add(nom)
        noms.append(nom)

    # ── modes / preuve client : JSON valide mais pas un objet -> réparé,
    #    jamais 500 (spec 2.5) ; le mode est validé contre le vocabulaire
    #    fermé du CORE ────────────────────────────────────────────────────
    try:
        modes_d = json.loads(modes or "{}")
    except ValueError:
        modes_d = {}
    if not isinstance(modes_d, dict):
        modes_d = {}
    for role, mode in modes_d.items():
        if str(mode) not in LAYER_MODES:
            raise HTTPException(
                400, f"mode inconnu pour {role!r} : {mode!r} "
                     f"(attendu {sorted(LAYER_MODES)})")
    try:
        proof_c = json.loads(client_proof or "{}")
    except ValueError:
        proof_c = {}
    if not isinstance(proof_c, dict):
        proof_c = {}

    # ── lecture des octets (E/S -> reste async), bornée AVANT tout décodage
    raw_par_role: dict[str, bytes] = {}
    for up, nom in zip(layers, noms):
        raw = await up.read()
        if len(raw) > MAX_LAYER_BYTES:
            raise HTTPException(
                413, f"{nom} : fichier trop lourd ({len(raw)} o, "
                     f"maximum {MAX_LAYER_BYTES} o)")
        raw_par_role[nom] = raw
    raw_comp = await composite.read()
    if len(raw_comp) > MAX_LAYER_BYTES:
        raise HTTPException(
            413, f"composite : fichier trop lourd ({len(raw_comp)} o, "
                 f"maximum {MAX_LAYER_BYTES} o)")

    def work() -> dict:
        from PIL import Image, ImageChops

        images: dict[str, "Image.Image"] = {}
        for nom, raw in raw_par_role.items():
            im = _open_png(raw, nom)
            if im.size != (w, h):
                raise HTTPException(409, f"{nom} : trame {im.size} != {(w, h)}")
            images[nom] = im
        comp = _open_png(raw_comp, "composite")
        if comp.size != (w, h):
            raise HTTPException(409, f"composite : trame {comp.size} != {(w, h)}")

        ordre = [r["role"] for r in LAYER_ROLES if r["role"] in images]
        if not ordre:
            raise HTTPException(409, "aucune couche reconnue")

        # ── contre-preuve : empilement PIL, ecart MESURE au composite ──────
        # C2 : la base est le PAPIER reellement peint par le moteur (validee
        # en amont dans `paper_hex`), pas transparent — le composite REEL
        # (cote navigateur) est peint sur ce meme papier avant les couches ;
        # empiler sur transparent divergeait en masse des que la couche
        # fond-matiere ne couvre plus tout le canevas (papier « none »).
        pile = Image.new("RGBA", (w, h), _paper_rgba(paper_hex))
        for nom in ordre:
            pile = Image.alpha_composite(pile, images[nom])
        diff = ImageChops.difference(pile, comp)
        # getdata() est déprécié (retrait Pillow 14) — équivalence mesurée
        # (scratchpad/bench_forge3d.py) : fast-path getbbox() si aucun écart,
        # sinon histogramme du canal fusionné (0 == pixels IDENTIQUES sur les
        # 4 bandes, donc w*h - ce compte = pixels qui diffèrent).
        if diff.getbbox() is None:
            diff_px = 0
        else:
            fusion = reduce(ImageChops.lighter, diff.split())
            diff_px = w * h - fusion.histogram()[0]

        ppm = float(_dpi_to_ppm(g.dpi))
        phys_ppm = int(round(ppm))    # la valeur EXACTE que `_phys_chunk`
                                       # écrit dans les octets (même arrondi)
        # dimensions physiques TOTALES de la trame (w, h) == canvas_px, donc
        # trim + fond perdu des DEUX côtés — pas trim_mm seul, qui ne couvre
        # que la carte coupée et sous-évaluerait bbox_mm sur toute couche qui
        # déborde dans le fond perdu.
        size_mm_totale = (g.trim_mm[0] + 2.0 * g.bleed_mm,
                          g.trim_mm[1] + 2.0 * g.bleed_mm)
        zip_entries: dict[str, bytes] = {}
        rows = []
        for nom in ordre:
            data = _stamp_phys(raw_par_role[nom], (ppm, ppm))
            fn = f"{nom}_{card_label}_{face}.png"
            zip_entries[fn] = data
            alpha = images[nom].getchannel("A")
            bbox = alpha.getbbox()
            # coverage : w*h - (pixels d'alpha nul), même mesure histogramme
            cover = ((w * h - alpha.histogram()[0]) / float(w * h) * 100.0)
            meta = next(r for r in LAYER_ROLES if r["role"] == nom)
            # bbox_mm : la MEME boîte, convertie par les dimensions physiques
            # (bbox_px * size_mm_totale / canvas_px) — None si bbox_px l'est,
            # jamais une conversion inventée sur une couche vide.
            # ORIGINE (I2, revue) : coin de TOILE (fond perdu compris), comme
            # bbox_px — PAS le coin de COUPE de P2/P3 (frame.py:164) ;
            # soustraire bleed_mm pour la convention slots.
            bbox_mm = None if bbox is None else [
                round(bbox[0] * size_mm_totale[0] / w, 2),
                round(bbox[1] * size_mm_totale[1] / h, 2),
                round(bbox[2] * size_mm_totale[0] / w, 2),
                round(bbox[3] * size_mm_totale[1] / h, 2),
            ]
            rows.append({
                "role": nom, "z": meta["z"], "module": meta["module"],
                "file": fn,
                "mode": str(modes_d.get(nom, "isolee")),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "bbox_px": list(bbox) if bbox else None,
                "bbox_mm": bbox_mm,
                "coverage_pct": round(cover, 2),
            })
        comp_fn = f"composite_{card_label}_{face}.png"
        comp_data = _stamp_phys(raw_comp, (ppm, ppm))
        zip_entries[comp_fn] = comp_data

        manifest = {
            "schema": MANIFEST_SCHEMA,
            "deck": {"id": did, "name": doc.get("name")},
            "card": {"index": idx, "label": card_label},
            "side": face,
            "format": g.fmt,
            "paper": paper_hex,
            "canvas_px": [w, h],
            "canvas_mm": [size_mm_totale[0], size_mm_totale[1]],
            "size_mm": [g.trim_mm[0], g.trim_mm[1]],
            "bleed_mm": g.bleed_mm,
            "phys_ppm": phys_ppm,
            "layers": rows,
            "composite": {"file": comp_fn,
                          "sha256": hashlib.sha256(comp_data).hexdigest(),
                          "bytes": len(comp_data)},
            "proof": {
                "client": {"stack_ok": bool(proof_c.get("stack_ok")),
                           "diff_px": int(_num(proof_c.get("diff_px"), 0,
                                               0, w * h)),
                           "note": "empilement navigateur, meme moteur, strict"},
                "backend": {"diff_px": int(diff_px),
                            "note": "re-empilement PIL alpha-over, second avis"},
            },
            "at": _iso_now(),
        }
        # ── ZIP : octets EN MÉMOIRE, jamais de relecture disque ────────────
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            for fn, data in zip_entries.items():
                z.writestr(fn, data)
            z.writestr("layers.json", json.dumps(manifest, ensure_ascii=False,
                                                 indent=2))
        zname = f"couches_{card_label}_{face}.zip"
        zip_bytes = zbuf.getvalue()
        manifest["zip"] = {"name": zname, "bytes": len(zip_bytes)}

        out = _out_dir(did, create=True)
        for fn, data in zip_entries.items():
            (out / fn).write_bytes(data)
        (out / zname).write_bytes(zip_bytes)
        (out / f"layers_{card_label}_{face}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return manifest

    try:
        manifest = await asyncio.to_thread(work)
    except HTTPException:
        raise
    except ModuleNotFoundError as e:           # pragma: no cover - env casse
        raise HTTPException(503, f"Module requis absent : {e}")
    except Exception as e:
        logger.exception("cards/forge3d: export de couches impossible")
        raise HTTPException(500, f"Export de couches impossible : {e}")
    return {"layers": manifest}


# ── L'ASSEMBLEUR — LE GRAPHE GRATUIT EXÉCUTÉ, L'ARTEFACT LIVRÉ (Task 4) ─────
# `post_build3d` résout les chaînes layer->(plane|relief)->assemble d'un
# graphe NETTOYÉ (clean_graph, l'UNIQUE porte d'entrée), assemble le résultat
# en UN GLB (write_scene_glb, Task 3), écrit un metadata.json compatible
# ERC-721 et tente le STL (gate sur le drapeau `closed` DÉCLARÉ par les
# constructeurs de maillage — Task 2 — jamais une re-mesure ici : coûte 7 s +
# ~340 Mo de pic par élément au grid max, mesuré en revue de la tâche 2).
#
# LA RÉSOLUTION elle-même (`_resolve_graph_elements`, `_chaine_aval`,
# `_source_gagnante`) et la fabrique d'UN élément (`_element_local`) vivent
# dans forge3d_apercu.py depuis la couture de délestage (2c, tâche 6) : c'est
# le bloc que cette route PARTAGE avec l'inspecteur, et les phrases d'aveu
# devaient cesser d'être recopiées de part et d'autre. Réexportées en tête de
# fichier — les noms n'ont pas bougé.
def _lire_manifeste(out: Path, card_label: str, side: str) -> dict | None:
    """Le manifeste d'export d'un côté, ou None. Illisible vaut ABSENT —
    jamais une exception qui deviendrait un 500 (même discipline que
    `_job_read`).

    CE QUE CETTE FONCTION VALIDAIT AVANT T5, EXACTEMENT : rien. Elle lisait le
    JSON et rendait le dictionnaire — ni le sha256 des fichiers, ni les
    boîtes, ni même que le contenu parlait du côté qu'on lui demandait. Le
    plan la décrivait avec des portes qu'elle n'avait pas ; la mesure a
    tranché, et la seule porte qui manquait VRAIMENT est celle-ci.

    LA COHÉRENCE NOM <-> CONTENU (T5). Le nom du fichier PORTE le côté ; le
    contenu le REDIT. Les deux doivent dire la même chose, sans quoi un
    `layers_c01_capture.json` contenant `side: "front"` ferait résoudre des
    couches importées contre le manifeste des peintres — le piège relevé en
    revue 3c, un fichier qui ment sur ce qu'il est.

    LA TOLÉRANCE AU MUET S'ARRÊTE À LA PROVENANCE IMPORTÉE (ronde T5, M8). Un
    manifeste de PEINTRE sans clé `side` n'est pas un menteur : il en existe
    d'écrits avant que la clé existe, et les refuser casserait des jeux réels.
    Un manifeste de CAPTURE, lui, n'a aucun héritage à protéger — T5 est sa
    NAISSANCE : tous ceux qui existent portent leur côté, et un fichier muet à
    ce nom-là ne peut venir que d'une main. Mesuré : `side` supprimé, la
    construction rendait 200.

    Le refus est un ABSENT NOMMÉ dans le journal, pas une exception : cette
    fonction est appelée depuis la construction, et faire tomber un artefact
    entier sur un fichier de côté abîmé serait disproportionné — l'appelant,
    lui, sait dire « exporte les couches d'abord »."""
    p = out / f"layers_{card_label}_{side}.json"
    if not p.is_file():
        return None
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError):
        logger.warning(f"cards/forge3d: manifeste illisible ({p.name})")
        return None
    if not isinstance(m, dict):
        return None
    dit = m.get("side")
    if dit is None and side == CAPTURE_SIDE:
        logger.warning(
            f"cards/forge3d: manifeste importe muet sur son cote ({p.name}) "
            f"- ignore")
        return None
    if dit is not None and dit != side:
        logger.warning(
            f"cards/forge3d: manifeste incoherent ({p.name} annonce "
            f"side={dit!r}) - ignore")
        return None
    return m


def _layer_box_mm(manifest, layer_node: dict, w_mm: float, h_mm: float,
                  bleed_mm: float) -> list:
    """La boîte mm de LA couche d'un élément, DANS LE REPÈRE DU MAILLAGE.

    DEUX REPÈRES, ET C'EST LE PIÈGE : le manifeste mesure `bbox_mm` dans celui
    de la TOILE — origine au coin de toile (fond perdu COMPRIS), y vers le BAS
    comme les pixels dont elle est tirée. Nos maillages, eux, vivent dans celui
    de la COUPE — origine au coin de coupe, y vers le HAUT. Poser un GLB de
    moteur sur la boîte brute le décalerait du fond perdu sur les deux axes ET
    le retournerait en y : même famille de défaut que la fenêtre UV
    coupe/toile de la 2a, et tout aussi invisible sur une carte sans fond
    perdu (celle sur laquelle on regarde toujours en premier).

    Couche absente du manifeste, boîte NON MESURÉE (couche entièrement
    transparente) ou couverture NULLE : TOUTE LA CARTE. Une couche vide n'a
    pas de place à elle, et rétrécir un maillage sur une boîte vide n'aurait
    aucun sens."""
    plein = [0.0, 0.0, float(w_mm), float(h_mm)]
    role = layer_node.get("role")
    if not isinstance(manifest, dict) or layer_node.get("composite") or not role:
        return plein
    rows = manifest.get("layers")
    row = next((r for r in (rows if isinstance(rows, list) else [])
                if isinstance(r, dict) and r.get("role") == role), None)
    if not isinstance(row, dict) or _num(row.get("coverage_pct"), 0.0, 0.0, 100.0) <= 0:
        return plein
    b = row.get("bbox_mm")
    if not isinstance(b, (list, tuple)) or len(b) != 4:
        return plein
    x0, y0, x1, y1 = (_num(v, 0.0, -1e6, 1e6) for v in b)
    # UNE SEULE SOURCE POUR LE CHANGEMENT DE REPÈRE : LE MANIFESTE. La hauteur
    # de toile et le fond perdu viennent de LUI (`canvas_mm`, `bleed_mm`), pas
    # d'une re-dérivation depuis la géométrie courante du deck. C'est le même
    # argument que `_dpi_to_ppm` plus haut dans ce fichier : `bbox_mm` a été
    # mesurée CONTRE ces chiffres-là, à l'export — les recalculer ici ferait
    # dépendre le retournement en y d'une géométrie qui a pu changer de format
    # depuis, pendant que la boîte relue, elle, n'a pas bougé. Mélanger les
    # deux sources serait le pire des trois : une conversion à moitié d'époque.
    # Repli sur la dérivation canonique quand un manifeste ancien ou abîmé ne
    # porte pas le chiffre.
    cm = manifest.get("canvas_mm")
    toile_h = (_num(cm[1], 0.0, 0.0, 1e6)
               if isinstance(cm, (list, tuple)) and len(cm) == 2
               and _num(cm[1], 0.0, 0.0, 1e6) > 0
               else float(h_mm) + 2.0 * float(bleed_mm))
    saignee = (_num(manifest["bleed_mm"], 0.0, 0.0, 1e6)
               if isinstance(manifest.get("bleed_mm"), (int, float))
               and not isinstance(manifest.get("bleed_mm"), bool)
               else float(bleed_mm))
    boite = [x0 - saignee, toile_h - y1 - saignee,
             x1 - saignee, toile_h - y0 - saignee]
    if boite[2] - boite[0] <= 0 or boite[3] - boite[1] <= 0:
        return plein
    return boite


def _fit_external(monde: dict, box_mm: list, trs: dict | None) -> dict:
    """LE PLACEMENT d'un GLB de moteur : échelle UNIFORME pour tenir dans la
    boîte mm de SA couche (max-fit, proportions gardées), centré sur cette
    boîte, posé à z. Le transform de l'utilisateur COMPOSE : son échelle
    MULTIPLIE, sa rotation et sa translation S'AJOUTENT.

    `trs` est le NŒUD `transform` DU GRAPHE (x_mm/y_mm/z_mm/rot_deg/scale),
    pas le dict TRS du writer (`_trs_dict`) : un externe n'a pas de nœud à
    lui dans lequel poser un transform séparé — le fit et le transform de
    l'utilisateur se composent en UN SEUL TRS, celui du parent de fusion.

    POLITIQUE, pas mécanique — d'où sa place ICI et non dans le module scène
    (même partage des rôles que `tile_maps`) : la scène sait POSER un TRS,
    elle n'a pas à décider LEQUEL.

    TOUT le z vient du transform, et il n'y a PAS de paramètre `z_mm` : le
    plan en prévoyait un, que sa propre règle épinglait à 0.0 (« ne pas le
    compter deux fois »). Un paramètre qui doit TOUJOURS valoir zéro n'est pas
    un paramètre, c'est un piège — le premier appelant qui y passe autre chose
    double le décalage sans qu'aucun test ne s'en aperçoive. La base du
    maillage est POSÉE SUR le plan z du transform (`z - s x min(z)`), jamais
    enfoncée dedans.

    Une cote nulle (maillage parfaitement plat sur un axe) vaut 1.0 plutôt
    qu'un refus : un décalque est un maillage légitime, et le rapport
    d'échelle d'un axe sans épaisseur n'a simplement pas de sens — c'est
    l'AUTRE axe qui décide alors, ce que le `min` fait déjà.

    `monde` est le maillage DÉJÀ MESURÉ dans le repère de la scène
    (`glb_scene_mesh(..., world=True)`), pas les octets du GLB : c'est la
    taille RENDUE qui doit tenir dans la boîte. Un exportateur qui pose une
    conversion d'axes ou une échelle d'unité sur son nœud racine — le nôtre le
    fait, avec son mm->m — rendrait un fit calculé sur du brut faux de
    plusieurs ordres de grandeur, et la pièce invisible dans l'artefact sans
    qu'aucune structure ne soit fautive. Recevoir le maillage plutôt que les
    octets évite AUSSI de le dépaqueter deux fois : l'appelant le garde pour
    le STL (voir `_element_externe`), et cette fonction redevient de la
    politique PURE — aucune lecture de GLB ici."""
    pos = monde["positions"]
    xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    mw = (x1 - x0) or 1.0
    mh = (y1 - y0) or 1.0
    bw = (box_mm[2] - box_mm[0]) or 1.0
    bh = (box_mm[3] - box_mm[1]) or 1.0
    t = trs if isinstance(trs, dict) else {}
    s = min(bw / mw, bh / mh) * _num(t.get("scale"), 1.0, *TRANSFORM_SCALE)
    cx = (box_mm[0] + box_mm[2]) / 2.0 - s * (x0 + x1) / 2.0
    cy = (box_mm[1] + box_mm[3]) / 2.0 - s * (y0 + y1) / 2.0
    cz = -s * min(zs)
    return {"scale": s,
            "translate": [cx + _num(t.get("x_mm"), 0.0, *TRANSFORM_XY_MM),
                          cy + _num(t.get("y_mm"), 0.0, *TRANSFORM_XY_MM),
                          cz + _num(t.get("z_mm"), 0.0, *TRANSFORM_Z_MM)],
            "rotate_deg": _num(t.get("rot_deg"), 0.0, *TRANSFORM_ROT_DEG)}


def _efface(p: Path) -> None:
    """Un livrable PÉRIMÉ, retiré — un fichier qu'on vient de refuser ne doit
    pas rester servi par `/file`. Une erreur d'effacement ne fait JAMAIS
    échouer la construction (l'artefact, lui, est bon) : elle se journalise."""
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning(f"cards/forge3d: {p.name} perime non efface")


def _motif_path(did: str, src: str) -> Path:
    """Le CHEMIN d'une source de motif — liste blanche D'ABORD, disque
    ENSUITE (patron durci de `get_node_file`, 2c). Trois formes, trois
    magasins DÉJÀ EXISTANTS (décision 4 du plan 3c : pas de quatrième).

    RÈGLE 8 TENUE : les images de calque de P3 vivent sous `decks/{did}/type/`
    et la matière de support sous `decks/{did}/texture/` — ce sont des
    FICHIERS sur le disque du jeu, composés ici depuis `contract.deck_dir`
    (le chemin du domaine), jamais en important le routeur du voisin.
    `material_store`, lui, est un service TRANSVERSE que cette pièce consomme
    déjà (`get_info`, `tile_maps`) : c'est SA fonction de chemin qui garde son
    confinement, pas une recomposition d'ici."""
    m = _MOTIF_IMG_RE.match(src)
    if m:
        return deck_dir(did) / "type" / m.group(1)
    if src == MOTIF_PAPER:
        return deck_dir(did) / "texture" / "paper.png"
    m = _MOTIF_MAT_RE.match(src)
    if m:
        from app.services import material_store as MSTORE
        return MSTORE.map_path(m.group(1), "basecolor")
    raise ValueError(f"source de motif hors vocabulaire : {src!r}")


def _motif_bytes(did: str, src: str) -> bytes:
    """Les OCTETS d'une source de motif. ValueError NOMMÉE si la source est
    hors vocabulaire, absente du disque, illisible ou trop lourde — l'appelant
    en fait un aveu au bordereau, jamais un 500.

    LE MESSAGE D'ABSENCE NOMME LE BON MAGASIN (correction de revue adverse,
    F4). Une matière de la boutique est APP-WIDE : elle vit à côté de
    l'application, pas dans le jeu. Répondre « fichier absent de ce jeu » est
    le message qu'une machine ÉTRANGÈRE produira dès qu'un deck voyagera sans
    sa boutique — et il enverrait chercher exactement au mauvais endroit.

    Le fichier est PESÉ avant d'être lu : ces images viennent de nos propres
    routes d'import (déjà bornées), mais un dossier de jeu est un dossier
    ORDINAIRE que rien n'empêche de remplir à la main."""
    p = _motif_path(did, src)
    ou = ("absente de la boutique de ce poste (les matieres ne voyagent pas "
          "avec le jeu)" if _MOTIF_MAT_RE.fullmatch(src)
          else "fichier absent de ce jeu")
    try:
        if not p.is_file():
            raise ValueError(ou)
        poids = p.stat().st_size
        if poids > MOTIF_MAX_BYTES:
            raise ValueError(f"{poids // 1048576} Mo : au-dela du plafond "
                             f"de {MOTIF_MAX_BYTES // 1048576} Mo")
        return p.read_bytes()
    except ValueError as e:
        raise ValueError(f"motif « {src} » : {e}")
    except OSError as e:
        raise ValueError(f"motif « {src} » : illisible ({_panne(e)})")


def _motifs_resolus(did, mat_n: dict, ignores: list) -> list:
    """La pile de motifs d'un nœud matière, RÉSOLUE en octets — et ce qui n'a
    pas pu l'être, AVOUÉ nommément (doctrine `ignored`, la même que la matière
    introuvable juste en dessous). Un calque mort ne coûte ni l'artefact ni la
    finition : il est retiré de la pile et il est DIT, avec sa source.

    CHAQUE CALQUE EST DÉCODÉ ICI, UN PAR UN (correction de revue adverse, F2).
    La phrase ci-dessus n'était vraie que d'un fichier ABSENT : un fichier
    PRÉSENT MAIS CORROMPU (PNG tronqué sur le disque du jeu — mesuré sur
    l'application vivante) échouait au fond de `holo_finish`, atterrissait
    dans l'`except` de `_habille` et emportait la RECETTE ENTIÈRE, avec un
    aveu qui parlait de « finition ignorée » sans nommer le calque. Ce module
    est le SEUL à savoir d'où vient chaque calque : c'est donc ici que la
    validation appartient, `motif_probe` par `motif_probe`."""
    pile: list = []
    for m in (mat_n.get("motifs") or []):
        src = m.get("src")
        try:
            if did is None:
                raise ValueError(f"motif « {src} » : sources de jeu "
                                 f"indisponibles dans ce contexte")
            octets = _motif_bytes(did, src)
            try:
                motif_probe(octets)
            except ValueError as e:
                raise ValueError(f"motif « {src} » : {e}")
            pile.append((octets, m.get("gain")))
        except ValueError as e:
            ignores.append({"node": mat_n["id"],
                            "why": f"{e}, calque retire de la pile"})
    return pile


def _couleur_matiere(mid) -> str | None:
    """LA COULEUR DU NŒUD — `props.color` de la matière choisie, ou `None`.

    D'OÙ ELLE VIENT, DIT UNE FOIS : le nœud `material` ne porte pas de teinte
    à lui ; la seule couleur qu'un graphe nomme est celle de la MATIÈRE de la
    boutique qu'il désigne (`material_store`, `props["color"]`, un hex —
    exactement celle que le lab Matières peint sur sa vignette). Le
    `translucide` en teinte son absorption ; les deux autres recettes n'en font
    rien.

    NE LÈVE JAMAIS : une matière effacée depuis que le graphe a été câblé rend
    `None`, et la recette part sans teinte. L'aveu de la matière introuvable
    est déjà fait plus haut par `_habille` — le redire ici doublerait la
    ligne au bordereau pour un seul fait."""
    if not mid:
        return None
    try:
        from app.services import material_store as MSTORE
        mat = MSTORE.read_material(str(mid))
    except Exception:                                   # noqa: BLE001
        return None
    props = (mat or {}).get("props")
    col = props.get("color") if isinstance(props, dict) else None
    return col if isinstance(col, str) else None


def _habille(el: dict, mat_n, w_mm: float, h_mm: float,
             ignores: list, did=None) -> None:
    """La MATIÈRE et la FINITION d'un élément local, posées sur son
    dictionnaire (`mat_maps` / `finish`). Aucune des deux n'est vitale : une
    matière effacée de la boutique depuis que le graphe a été câblé, ou une
    recette de finition inconnue, laissent passer l'élément SANS habillage et
    entrent dans `ignores` avec leur motif — refuser tout l'artefact pour un
    accessoire absent serait disproportionné, le taire serait un mensonge.

    `did` (3c) est le jeu dont les MOTIFS se lisent : ce module ne peut pas le
    déduire de `el` (un élément ne porte que des pixels), et le sidecar qui
    appelle cette fonction ne le connaît pas — c'est donc le point d'appel
    d'ici (`_element_local`) qui le lie, en gardant la signature à cinq
    positions que le sidecar utilise. Sans lui, une pile de motifs est AVOUÉE
    non résoluble plutôt que silencieusement vide."""
    if not isinstance(mat_n, dict):
        return
    if mat_n.get("mat"):
        # L'OCCLUSION SE DÉBRAYE À LA SOURCE, pas au writer : la carte n'est
        # même plus CUITE ni embarquée quand le nœud l'éteint (un GLB plus
        # léger, et pas seulement une clé en moins). `is not False` — l'absence
        # vaut « allumée », comme dans `clean_graph`, pour que le sidecar
        # d'aperçu (qui peut recevoir un nœud non nettoyé) tombe du même côté.
        kinds = tuple(k for k in MATERIAL_MAP_KINDS
                      if k != "ao" or mat_n.get("ao") is not False)
        try:
            el["mat_maps"] = material_pngs(tile_maps(
                mat_n["mat"], kinds, mat_n["tile_mm"], w_mm, h_mm))
            if not el["mat_maps"]:
                # une matière qui n'a QUE sa couleur de base n'habille RIEN
                # ici (la base, c'est LA COUCHE — spec §5.2) : le dire, sinon
                # le réglage semble avoir pris et n'a rien fait.
                ignores.append({
                    "node": mat_n["id"],
                    "why": "matiere sans aucune map utilisable (normale, "
                           "rugosite, metal, occlusion, emission) : la "
                           "couleur de base vient de la couche, pas de la "
                           "matiere"})
        except ValueError as e:
            ignores.append({"node": mat_n["id"],
                            "why": f"matiere introuvable ou illisible sur "
                                   f"disque, element laisse nu : {e}"})
    if mat_n.get("finish") in GLASS_KINDS:
        # LE VERRE (phase 5, D5) — l'autre famille, au même point d'entrée.
        # Ni anisotropie (le peigne d'un métal brossé n'a rien à faire sur une
        # vitre) ni motifs : le canal d'épaisseur qui les porte n'existe que
        # dans une recette holographique. Des calques posés puis basculés vers
        # le verre sont donc AVOUÉS, exactement comme sans finition — c'est le
        # même silence que `_SANS_HOLO` existe pour rompre.
        try:
            el["finish"] = glass_finish(mat_n["finish"],
                                        color=_couleur_matiere(mat_n.get("mat")))
        except ValueError as e:
            ignores.append({"node": mat_n["id"],
                            "why": f"finition ignoree : {e}"})
        if mat_n.get("motifs"):
            ignores.append({"node": mat_n["id"],
                            "why": f"{len(mat_n['motifs'])} {_SANS_HOLO}"})
    elif mat_n.get("finish") and mat_n["finish"] != "aucune":
        try:
            el["finish"] = holo_finish(mat_n["finish"],
                                       bool(mat_n.get("aniso")),
                                       motifs=_motifs_resolus(did, mat_n,
                                                              ignores))
        except ValueError as e:
            ignores.append({"node": mat_n["id"],
                            "why": f"finition ignoree : {e}"})
    elif mat_n.get("motifs"):
        # DES MOTIFS SANS FINITION NE S'INCRUSTENT NULLE PART (3c) : le canal
        # G d'épaisseur n'existe QUE dans une recette holographique. Le taire
        # laisserait l'écran croire que le sceau est passé — c'est exactement
        # le silence que le bordereau `ignored` existe pour rompre.
        ignores.append({
            "node": mat_n["id"],
            "why": f"{len(mat_n['motifs'])} {_SANS_HOLO}"})


# ── LE SCEAU PRISMATIQUE, PORTÉE 3D (3c, décision 4 du plan) ────────────────
# §6.2bis-d : « "3D uniquement" est une configuration de premier rang [...] et
# SEUL le nœud 3D de bout de chaîne reçoit le matériau iridescent ». La vérité
# du Sceau vit dans `doc.frame.seal` (livré par la T1) ; P9 la LIT dans le
# document du jeu — une lecture d'état partagé, pas un import du routeur de P2
# (règle 8 : ce fichier n'importe le routeur d'aucun autre, et n'importe pas
# frame.py du tout). D'où ce lecteur LOCAL, au même patron de copie que
# `_dpi_to_ppm`, avec sa parité testée contre `frame.seal_of`.
_SEAL_EXTRUDE_WHY = ("sceau 3D : l'extrusion de contour « sceau » EST le "
                     "corps du Sceau du document - son metal et sa largeur "
                     "viennent de lui")
_SEAL_MESH_WHY = ("sceau 3D : la COUCHE ENTIERE recoit la finition — "
                  "l'isolation d'une sous-region n'existe pas dans l'export "
                  "par couches (only_z porte sur une bande entiere)")
# COPIE LOCALE du défaut de `frame.SEAL_DEFAULTS["kind"]` (règle 8, même patron
# que `_dpi_to_ppm`), avec sa parité testée. Un Sceau dont le document ne dit
# PAS le métal en nomme un quand même — par le schéma partagé, qui a un défaut.
_SEAL_KIND_DEFAULT = "argent"
# ... et la LARGEUR par défaut, même copie avouée (`frame.SEAL_DEFAULTS`),
# même parité testée. C'est aussi celle que `EXTRUDE_WIDTH_DEFAULT` donne au
# contour `sceau` : une seule vérité, écrite une fois.
_SEAL_WIDTH_DEFAULT = EXTRUDE_WIDTH_DEFAULT["sceau"]


def _sceau_du_doc(doc) -> dict:
    """`{on, kind, mesh}` — les TROIS champs du Sceau que la 3D consomme, lus
    défensivement dans le document du jeu. Ne lève jamais.

    DEUX CAS QUE `frame.seal_of` CONFOND, et qu'il faut séparer ici. Un métal
    ABSENT n'est pas un métal INCONNU : le premier est « non dit », et le
    schéma partagé lui donne un défaut (argent) — le document le nomme donc,
    par omission, et P9 le cuit comme P2 le peindrait. Le second est « dit,
    mais illisible » : y répondre par l'argent livrerait un métal FAUX sans un
    mot, exactement ce que la ValueError nommée de `holo_finish` existe pour
    empêcher. D'où le `None`, dont l'appelant fait un aveu. La parité avec P2
    est testée sur les deux branches, divergence comprise."""
    d = doc if isinstance(doc, dict) else {}
    f = d.get("frame")
    s = f.get("seal") if isinstance(f, dict) else None
    s = s if isinstance(s, dict) else {}
    sc = s.get("scope")
    sc = sc if isinstance(sc, dict) else {}
    k = s.get("kind", _SEAL_KIND_DEFAULT)
    return {"on": s.get("on") is True,
            "kind": k if k in HOLO_KINDS else None,
            "mesh": sc.get("mesh") is True,
            # LA LARGEUR AUSSI (ronde T5, R3) : le corps 3D du Sceau est une
            # COURONNE, et une couronne a une largeur. Sans elle, l'écran
            # dessinerait une bande de 1,2 mm pendant que la 3D en livrerait
            # une autre. Bornée comme tout ce qui vient d'un document ; le
            # défaut est celui du schéma partagé.
            "width_mm": _num(s.get("width_mm"), _SEAL_WIDTH_DEFAULT,
                             *EXTRUDE_WIDTH_MM)}


def _scelle(el: dict, layer: dict, mat_n, sceau: dict, ignores: list) -> dict:
    """La finition du Sceau posée sur UN élément, quand elle lui revient.
    Rend l'entrée à joindre au bordereau de cet élément (ou `{}`).

    LA RÈGLE, EN UNE PHRASE : le Sceau COMBLE LE SILENCE du graphe, il ne
    couvre jamais une parole. Un nœud `material` qui NOMME une finition
    l'emporte — y compris quand cette finition a échoué (un motif corrompu),
    parce que substituer alors la recette du Sceau masquerait la panne sous un
    résultat plausible. Un `material` qui ne nomme rien (« aucune », le défaut
    du menu) laisse le Sceau parler, et le bordereau le DIT.

    L'HONNÊTETÉ DE PORTÉE EST OBLIGATOIRE ET VA AU BORDEREAU, PAS À `ignored`
    (qui ne nomme que ce qui a été PERDU — invariant de la 2c, épinglé) :
    appliquer le Sceau est un FAIT à dire, pas une perte. L'inverse — le Sceau
    écarté par un nœud explicite — est bien une perte, et va donc, lui, dans
    `ignored`."""
    if not (sceau.get("on") and sceau.get("mesh")):
        return {}
    if (layer or {}).get("role") != "cadre":
        return {}
    if sceau.get("kind") is None:
        ignores.append({"node": (mat_n or {}).get("id") or "seal",
                        "why": "sceau 3D ignore : metal hors des recettes "
                               f"connues ({', '.join(HOLO_KINDS)})"})
        return {}
    nomme = (isinstance(mat_n, dict)
             and mat_n.get("finish") not in (None, "", "aucune"))
    if nomme:
        ignores.append({
            "node": mat_n["id"],
            "why": f"sceau 3D ecarte sur cette couche : le noeud material y "
                   f"nomme deja « {mat_n['finish']} » — l'explicite l'emporte "
                   f"sur l'implicite"})
        return {}
    el["finish"] = holo_finish(sceau["kind"], False)
    return {"seal": {"kind": sceau["kind"], "why": _SEAL_MESH_WHY}}


def _nom_element(layer_node) -> str:
    """LE NOM D'UN ÉLÉMENT DE COUCHE, provenance comprise (T5).

    `nom_element` (le sidecar) ne connaît que deux faces et ne suffixe que le
    verso. Une TROISIÈME provenance a exactement le même besoin, pour la même
    raison (M3, 2d) : une carte peut porter son `illustration` peinte ET son
    `illustration` importée dans le même artefact — deux nœuds, deux maillages
    et deux MATÉRIAUX homonymes si le nom ne les sépare pas. Le suffixe ne
    touche QUE la provenance importée : un artefact recto/verso garde ses
    octets à l'identique."""
    if isinstance(layer_node, dict) and layer_node.get("side") == CAPTURE_SIDE:
        return f"{layer_node.get('role') or CAPTURE_SIDE}_{CAPTURE_SIDE}"
    return nom_element(layer_node)


# ── LE NŒUD `extrude` (T5, D8) — LE SEUL TRAITEMENT SANS COUCHE SOURCE ─────
# `_resolve_graph_elements` (le sidecar) exige de chaque traitement une couche
# entrante : c'est juste pour un plan, un relief ou un moteur, qui tirent tous
# leur matière d'une PNG. Une extrusion, elle, tire sa forme du FORMAT — elle
# n'a rien à recevoir. Sa résolution vit donc ici, et elle réutilise les DEUX
# primitives de la descente de chaîne plutôt que de les recopier.
def _resoud_extrudes(graph: dict, ignores: list) -> list[dict]:
    """Les candidats `extrude` du graphe, au même type que ceux du sidecar
    (`{proc, layer, mat, trs}`) — avec `layer: None`, qui EST le
    discriminant : pas une couche absente, une couche qui n'a pas lieu d'être.

    Deux pertes avouées, comme partout : une extrusion dont la chaîne ne
    rejoint pas d'assemble, et une arête ENTRANTE (l'écran ne peut pas en
    dessiner — sa grammaire ne mène pas à `extrude` — mais l'API brute, si)."""
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    outgoing: dict[str, list[str]] = {}
    entrants: dict[str, int] = {}
    for e in graph["edges"]:
        outgoing.setdefault(e["from"], []).append(e["to"])
        entrants[e["to"]] = entrants.get(e["to"], 0) + 1
    out: list[dict] = []
    for n in graph["nodes"]:
        if n["kind"] != "extrude":
            continue
        if entrants.get(n["id"]):
            ignores.append({
                "node": n["id"],
                "why": f"{entrants[n['id']]} arete(s) entrante(s) ignoree(s) "
                       f"sur une extrusion : sa forme vient du format de la "
                       f"carte, pas d'une couche"})
        mat_n, trs_n, relie = _chaine_aval(n["id"], nodes_by_id, outgoing,
                                           ignores)
        if not relie:
            ignores.append({"node": n["id"],
                            "why": "extrusion non reliee a un assemble"})
            continue
        out.append({"proc": n, "layer": None, "mat": mat_n, "trs": trs_n})
    return out


def _resoud_tout(graph: dict) -> tuple[list[dict], list[dict]]:
    """LES ÉLÉMENTS DU GRAPHE, dans l'ORDRE DES NŒUDS — couches sourcées ET
    extrusions mêlées.

    L'ordre des nœuds est un contrat de la 2c (le bordereau, donc l'écran, le
    suit). `sorted` est STABLE : un graphe SANS extrusion rend exactement la
    liste du sidecar, dans exactement le même ordre — les octets d'un artefact
    d'avant T5 ne bougent pas d'un cran."""
    candidats, ignores = _resolve_graph_elements(graph)
    extras = _resoud_extrudes(graph, ignores)
    if not extras:
        return candidats, ignores
    rang = {n["id"]: i for i, n in enumerate(graph["nodes"])}
    tout = sorted(candidats + extras,
                  key=lambda c: rang.get(c["proc"]["id"], 0))
    return tout, ignores


def _nom_extrude(proc: dict) -> str:
    """Le nom d'un élément d'extrusion — PRÉFIXÉ, et c'est la leçon M3 de la
    2d : `cadre` tout court entrerait en collision avec la couche `cadre` d'un
    graphe qui porte les deux, et le GLB sortirait deux nœuds ET deux
    matériaux homonymes que Blender fusionne."""
    return f"extrude_{proc['contour']}"


def _element_extrude(proc: dict, nom_el: str, mat_n, trs_n, g,
                     ignores: list, did=None, largeur=None) -> dict:
    """UN élément d'EXTRUSION prêt pour l'assemblage : la couronne du contour,
    habillée et placée comme n'importe quel élément local.

    LE RABOT GÉOMÉTRIQUE EST ICI, PAS DANS `clean_graph` : la borne dépend du
    FORMAT de la carte, que le nettoyage du graphe ne connaît pas (il tourne
    aussi sur un graphe posté sans deck en tête). Au-delà de la demi-carte, le
    contour rentré s'inverse — MESURÉ : à `min(w, h) / 2` pile, l'appariement
    d'arêtes tombe et le solide n'est plus fermé. On rabote, et on le DIT :
    livrer une couronne muette plus étroite que demandée serait un mensonge
    silencieux, refuser tout l'artefact pour un curseur trop poussé serait
    disproportionné.

    OÙ IL MORD VRAIMENT (relevé en ronde T5, M7) : `clean_graph` plafonne
    déjà la largeur à 20 mm, et la demi-carte du plus petit format du lab
    (micro, 31,75 x 44,45) vaut 15,87 mm — le rabot n'est donc atteignable
    QUE sur `micro`, et par un graphe qui y demande plus de 15,67 mm. Sur un
    poker (demi-carte 31,5 mm) il ne peut pas mordre : la première rédaction
    de ce commentaire le justifiait par un cas poker inatteignable, ce qui
    apprenait à chercher le défaut au mauvais endroit. Le comportement, lui,
    ne bouge pas — c'est le patron pré-T5 (`clean_graph` rabote en silence,
    la route rabote en le DISANT) ; la dette de classe est nommée ici."""
    w_mm, h_mm = g.trim_mm
    # `largeur` (R3) : celle du Sceau du document, quand c'est LUI le corps.
    d = float(proc["width_mm"] if largeur is None else largeur)
    d_max = min(w_mm, h_mm) / 2.0 - EXTRUDE_MIN_MM
    if d > d_max:
        rabote = max(EXTRUDE_MIN_MM, d_max)
        ignores.append({
            "node": proc["id"],
            "why": f"largeur d'extrusion ramenee de {d:g} a {rabote:g} mm : "
                   f"au-dela de la demi-carte ({min(w_mm, h_mm) / 2.0:g} mm) "
                   f"le contour rentre s'inverse et la couronne cesse d'etre "
                   f"un solide ferme"})
        d = rabote
    mesh = extrude_ring_mesh(w_mm, h_mm, g.corner_mm, d,
                             float(proc["depth_mm"]), int(proc["segments"]))
    el = {"name": nom_el, "mesh": mesh, "alpha": False, "z_mm": 0.0}
    habille = (_habille if did is None else partial(_habille, did=did))
    habille(el, mat_n, w_mm, h_mm, ignores)
    trs = _trs_dict(trs_n)
    if trs is not None:
        el["trs"] = trs
    return el


# ── LES COUCHES IMPORTÉES (T5, D7) — LE MANIFESTE EST LE CONTRAT ───────────
# LE DOSSIER DE LA PIÈCE IMPORT, RECOPIÉ (règle 8 : ce fichier n'importe le
# module d'aucune voisine — même patron que `_dpi_to_ppm` et
# `_SEAL_KIND_DEFAULT`, avec sa parité testée contre `capture.cap_dir`). P9 a
# besoin d'y RELIRE la source d'une couche importée pour savoir si la copie
# qu'elle a sous la main est encore d'actualité ; le NOM du fichier, lui, vient
# du manifeste, jamais d'une convention d'ici.
_CAPTURE_DIR = "capture"


def _dit_provenance(row: dict) -> str:
    """LA PHRASE DU BORDEREAU pour une couche importée — et elle ne maquille
    PAS une constante de format en mesure (ronde T5, R4).

    `coverage_pct` mesure la part OPAQUE de la toile. Sur la face entière,
    c'est le rapport coupe/toile : 85,45 % sur tout poker, quel que soit ce
    qu'il y a dessus — un aplat noir et une photographie donnent le MÊME
    chiffre. L'afficher là comme une couverture apprend à lire une constante
    de format comme un relevé (la leçon T4-a, mot pour mot). La face entière
    dit donc ce qu'elle EST et ce qu'elle PÈSE en pixels ; seul le sujet, dont
    le chiffre décrit vraiment son contenu, publie un pourcentage — et il
    NOMME son cadre, parce qu'il en existe deux (celui du détourage, celui de
    la toile)."""
    px = row.get("source_px")
    taille = (f" ({int(px[0])}x{int(px[1])} px)"
              if isinstance(px, (list, tuple)) and len(px) == 2 else "")
    if row.get("role") == CAPTURE_ROLES[0]:
        return f"face entiere importee{taille}"
    couv = _num(row.get("coverage_pct"), 0.0, 0.0, 100.0)
    return (f"couche importee{taille} : "
            f"{f'{couv:.1f}'.replace('.', ',')} % de la toile")


def _preuve_capture(did: str, out: Path, card_label: str, layer: dict,
                    manifeste, g, ignores: list) -> dict:
    """LE MANIFESTE IMPORTÉ, VÉRIFIÉ AVANT DE CONSTRUIRE — ou 409 nommé.

    Les couches de P10 n'ont AUCUNE preuve d'empilement : elles n'ont jamais
    été empilées (D7). Ce qui en tient lieu est ici, et c'est mesurable —
    l'EMPREINTE. Le manifeste nomme un fichier et son sha256 ; on vérifie que
    le fichier que la résolution va lire est CELUI-LÀ, octet pour octet. Un
    manifeste qui ment sur ses empreintes est refusé NOMMÉ, jamais suivi.

    SEPT portes, chacune avec son mot : le manifeste absent, la provenance qui
    n'est pas `capture`, le rôle que le manifeste ne porte pas, le fichier
    qu'il nomme et qui n'est pas celui qu'on lit, l'empreinte de la copie —
    et, depuis la ronde T5 (B1), les DEUX portes du PÉRIMÉ :

      · LE FORMAT. Mesuré : un manifeste publié en poker, un PATCH vers tarot,
        et la construction rendait 200 avec la face ANAMORPHOSÉE de 22,7 %,
        une fenêtre UV décalée de 2,8 px et un bordereau affichant les
        millimètres du poker. La copie est rendue à la toile d'UN format ; un
        autre format la rend fausse, pas approximative.
      · LA SOURCE. Mesuré : re-déposer un recto (rouge -> vert) sans republier
        laissait l'artefact porter la couche ROUGE. La copie est datée, sa
        source vit ; le manifeste porte l'empreinte qu'elle avait, et on la
        confronte au disque.

    Le test de la livraison prouvait que REPUBLIER marche — il ne jouait jamais
    le cas où l'on ne republie PAS, celui-là même que les trois raisons de la
    route invoquent. Les deux refus disent « republie », parce que c'est le
    geste qui répare.

    UNE SOURCE DISPARUE N'EST PAS UN MENSONGE : la copie reste ce qu'elle
    était, on ne peut simplement plus le vérifier. C'est un AVEU au bordereau,
    pas un refus — effacer sa capture n'a jamais périmé un artefact.

    Rend la LIGNE du manifeste (l'appelant y lit la provenance à afficher)."""
    role = layer.get("role")
    fname = _layer_filename(layer, card_label)
    if not isinstance(manifeste, dict):
        raise HTTPException(
            409, f"aucun manifeste de couches importees pour {card_label} : "
                 f"publie-le depuis la piece Import "
                 f"(POST capture/manifeste) avant de construire")
    if manifeste.get("source") != CAPTURE_SIDE:
        raise HTTPException(
            409, f"le manifeste {card_label}/{CAPTURE_SIDE} n'annonce pas la "
                 f"provenance « {CAPTURE_SIDE} » : il ne decrit pas des "
                 f"couches importees")
    rows = manifeste.get("layers")
    rows = rows if isinstance(rows, list) else []
    row = next((r for r in rows if isinstance(r, dict) and r.get("role") == role),
               None)
    if row is None:
        dispo = ", ".join(sorted({str(r.get("role")) for r in rows
                                  if isinstance(r, dict) and r.get("role")}))
        raise HTTPException(
            409, f"le manifeste importe ne porte pas la couche « {role} » "
                 f"(il porte : {dispo or 'aucune'}) — relance l'import ou "
                 f"choisis un autre role")
    if row.get("file") != fname:
        raise HTTPException(
            409, f"le manifeste importe nomme « {row.get('file')} » pour "
                 f"« {role} », la resolution lit « {fname} » : le manifeste "
                 f"et le graphe ne parlent pas du meme fichier")
    p = out / fname
    if not p.is_file():
        raise HTTPException(
            409, f"couche importee absente du disque : {fname} — republie le "
                 f"manifeste depuis la piece Import")
    vu = hashlib.sha256(p.read_bytes()).hexdigest()
    if vu != row.get("sha256"):
        raise HTTPException(
            409, f"empreinte de {fname} differente de celle du manifeste "
                 f"importe : le fichier a change depuis la publication "
                 f"(republie le manifeste)")
    # ── LE PÉRIMÉ, PORTE 1 : LE FORMAT ──────────────────────────────────
    fmt = manifeste.get("format")
    if fmt != g.fmt:
        raise HTTPException(
            409, f"couches importees publiees en {fmt}, ce jeu est en "
                 f"{g.fmt} : la face a ete rendue a la toile d'un autre "
                 f"format et serait anamorphosee — republie le manifeste "
                 f"depuis la piece Import")
    toile = manifeste.get("canvas_px")
    if list(toile or []) != list(g.canvas_px):
        raise HTTPException(
            409, f"couches importees publiees pour une toile de "
                 f"{toile} px, ce jeu en demande {list(g.canvas_px)} "
                 f"(densite ou fond perdu changes) — republie le manifeste "
                 f"depuis la piece Import")
    # ── LE PÉRIMÉ, PORTE 2 : LA SOURCE ──────────────────────────────────
    src_nom = row.get("source_file")
    src_sha = row.get("source_sha256")
    if not (isinstance(src_nom, str) and isinstance(src_sha, str)):
        raise HTTPException(
            409, f"le manifeste importe ne dit pas de quelle source vient "
                 f"« {role} » : il a ete ecrit par une version qui ne "
                 f"datait pas ses copies — republie le manifeste")
    ps = deck_dir(did) / _CAPTURE_DIR / src_nom
    if not ps.is_file():
        ignores.append({
            "node": fname,
            "why": f"empreinte de source non verifiable : {src_nom} n'est "
                   f"plus dans le dossier d'import (la copie est servie "
                   f"telle quelle)"})
    elif hashlib.sha256(ps.read_bytes()).hexdigest() != src_sha:
        raise HTTPException(
            409, f"la source « {src_nom} » a change depuis la publication : "
                 f"la couche « {role} » decrit l'image precedente — republie "
                 f"le manifeste depuis la piece Import")
    return row


def _sceau_extrusion(proc: dict, mat_n, sceau: dict, ignores: list):
    """LE SCEAU DU DOCUMENT, quand il revient à CETTE extrusion (ronde T5,
    R3) — `{kind, width_mm}` ou `None`.

    CE QUI ÉTAIT CASSÉ, MESURÉ : portée 3D cochée + couche importée +
    extrusion `sceau` — c'est-à-dire EXACTEMENT la configuration que la preuve
    de bout doit produire — rendait 200 sans la moindre iridescence, sans une
    clé au bordereau, `ignored` vide. `_scelle` sort sur `role != "cadre"`, et
    une extrusion n'a pas de couche du tout : le Sceau n'avait aucun corps où
    se poser, et personne ne le disait. La branche `mesh3d` de cette même
    route confesse pourtant le principe depuis la 2b (« le pire des deux :
    l'utilisateur a coché, l'écran n'a rien à répondre ») — T5 rouvrait le
    silence qu'elle avait fermé.

    LA RÈGLE EST CELLE DE `_scelle`, MOT POUR MOT : le Sceau COMBLE LE
    SILENCE, il ne couvre jamais une parole. Un nœud `material` qui NOMME une
    finition l'emporte — y compris quand elle échoue.

    LA LARGEUR VIENT DU DOCUMENT, elle aussi : `contour: "sceau"` NOMME
    l'anneau du Sceau, et l'anneau du Sceau a la largeur que le document lui
    donne. Le nœud garde la sienne quand le Sceau ne le touche pas (portée
    éteinte, matériau explicite) ; quand il le touche, la substitution est
    DITE au bordereau avec les deux chiffres — un curseur qui cesse d'agir
    sans un mot serait le même silence, un cran plus loin."""
    if not (sceau.get("on") and sceau.get("mesh")):
        return None
    if proc.get("contour") != "sceau":
        return None
    if sceau.get("kind") is None:
        ignores.append({"node": proc["id"],
                        "why": "sceau 3D ignore : metal hors des recettes "
                               f"connues ({', '.join(HOLO_KINDS)})"})
        return None
    if isinstance(mat_n, dict) and mat_n.get("finish") not in (None, "", "aucune"):
        ignores.append({
            "node": mat_n["id"],
            "why": f"sceau 3D ecarte sur cette extrusion : le noeud material "
                   f"y nomme deja « {mat_n['finish']} » — l'explicite "
                   f"l'emporte sur l'implicite"})
        return None
    return {"kind": sceau["kind"], "width_mm": sceau.get("width_mm")}


_SANS_CORPS = ("sceau 3D sans corps : la portee mesh est cochee mais ce "
               "graphe n'a ni couche « cadre » ni extrusion « sceau » - "
               "ajoute une extrusion de contour sceau (ou une couche cadre) "
               "pour lui donner un volume")


def _element_local(out: Path, proc: dict, layer: dict, nom_el: str,
                   mat_n, trs_n, card_label: str, g, ignores: list,
                   did=None) -> dict:
    """UN élément LOCAL (`plane`/`relief`) prêt pour l'assemblage — le CORPS
    vit dans forge3d_apercu.py (couture de délestage), qui le partage entre
    `build3d` et l'inspecteur. ICI, le PONT : les deux primitives que le
    sidecar ne peut pas importer sans dépendre de ce fichier lui sont DONNÉES,
    par leur nom (`_open_png` sert aussi trois routes d'ici ; `_habille` a
    besoin de `tile_maps`, qui a besoin de `_num`).

    N2 (re-revue tâche 1) : `g` REMPLACE les quatre paramètres dérivés
    (w_mm/h_mm, bleed_px, canvas_px, uv_window — trois tuples de même forme au
    même rang). Ils sont désormais dérivés UNE fois, DEDANS (`_geom_element`) :
    le swap silencieux de deux tuples au point d'appel n'est plus formulable.

    3c : le JEU est LIÉ ici, pas passé au sidecar. Les motifs d'une finition
    se lisent dans les fichiers du jeu, et le sidecar — qui ne connaît que des
    pixels et des nœuds — n'a aucune raison d'apprendre ce qu'est un `did`. Le
    lier ici garde son contrat d'injection à cinq positions INTACT (un appelant
    qui ne donne pas de jeu obtient l'ancienne fonction, et une pile de motifs
    y est AVOUÉE non résoluble, jamais silencieusement vide)."""
    habille = (_habille if did is None
               else partial(_habille, did=did))
    return _APERCU.element_local(out, proc, layer, nom_el, mat_n, trs_n,
                                 card_label, g, ignores,
                                 ouvre_png=_open_png, habille=habille)


def _glb_servi_path(did: str, nid: str) -> tuple[dict, Path]:
    """Le job SERVI d'un nœud mesh3d et le CHEMIN de son GLB sur disque.

    LE MAGASIN EST ICI, LES RÈGLES SONT LÀ-BAS (couture de délestage) : la
    lecture du `job.json` (`_job_read`, ses reprises Windows) et le confinement
    du dossier (`_node_dir`, sa double garde) appartiennent à ce fichier ; les
    TROIS refus partagés par `_element_externe` (fusion, build3d) et
    `_apercu_mesh3d` (inspecteur, node-preview) — job non servi, nom de fichier
    invalide, fichier disparu du nœud — et leurs phrases vivent dans
    forge3d_apercu.py. Chaque appelant garde SES gates PROPRES au-delà :
    `_element_externe` vérifie ENCORE la carte-source et `MAX_EXT_GLB_BYTES`
    (une fusion en mémoire) ; `_apercu_mesh3d` vérifie `MAX_APERCU_GLB_BYTES`
    (un clic dans l'inspecteur — deux dangers différents, deux bornes
    différentes, voir CF2). N'OUVRE PAS le fichier : ni celle-ci, ni ses
    appelants n'ont besoin des octets pour ces trois refus.

    `_job_read` traverse DÉJÀ `_node_dir` (c'est là qu'il va chercher le
    fichier) : l'appeler une seconde fois ici ne peut donc pas déplacer un
    refus de confinement APRÈS un refus de job — l'ordre observable est celui
    d'avant la couture."""
    job = _job_read(did, nid)
    return job, _APERCU._glb_servi_path(job, _node_dir(did, nid), nid)


def _element_externe(did: str, proc: dict, layer: dict, nom_el: str,
                     box_mm: list, trs_n, card_label: str,
                     w_mm: float) -> dict:
    """UN GLB de moteur, prêt pour la fusion — ou un refus NOMMÉ.

    LEGS DE LA TÂCHE 4, l'asymétrie I4 : `served` n'implique PLUS
    « utilisable ». Un GLB au-delà de `MAX_EXT_GLB_BYTES` arrive bel et bien
    `served` (il est PAYÉ, on ne le jette pas) avec `closed: None` et une note.
    Le gate de taille se fait donc ICI, sur le chiffre RELU AU JOB — sans
    OUVRIR le fichier : l'ouvrir pour décider s'il est trop gros à ouvrir
    serait exactement la borne qu'on prétend poser. Le job.json de la tâche 4
    porte ce chiffre dans `bytes` (le `stat` du binaire au moment de la
    livraison) ; un job plus ancien qui n'en aurait pas retombe sur un `stat`
    — une mesure de métadonnée, toujours pas une lecture."""
    nid = proc["id"]
    job, p_glb = _glb_servi_path(did, nid)
    # I2 — UN GLB EST LIÉ À SA CARTE. Le job dit de QUELLE couche il est né
    # (`source.file`, écrit par la route au lancement) ; la chaîne, elle, vise
    # la couche de la carte qu'on construit MAINTENANT. Quand les deux
    # divergent — le nœud a été lancé sur la carte 1, on assemble la carte 2,
    # ou le côté du nœud `layer` a changé depuis — fusionner produirait un
    # artefact où l'illustration d'une AUTRE carte est présentée comme celle-ci.
    # Aucune mesure ne rattraperait ça après coup : c'est le bon fichier, au
    # mauvais endroit. Refus NOMMÉ, avec les deux noms, pour que le motif soit
    # actionnable (relancer le nœud) plutôt que mystérieux.
    #
    # PAS le même refus pour l'inspecteur (M4) : `_apercu_mesh3d` ne fait PAS
    # cette vérification — sa question est « qu'a produit CE nœud », pas
    # « ce nœud convient-il à CETTE carte ». La carte n'entre pas dans la
    # question posée par un clic sur un nœud.
    attendu = _layer_filename(layer, card_label)
    servi = (job.get("source") or {}).get("file") if isinstance(
        job.get("source"), dict) else None
    if isinstance(servi, str) and servi and servi != attendu:
        raise HTTPException(
            409, f"le GLB du noeud {nid} a ete servi pour {servi} — cette "
                 f"construction attend {attendu} : relance-le pour cette carte")
    # LE JOB DIT, LE DISQUE CONFIRME — et c'est le PLUS GRAND des deux qui
    # décide. Un `stat` n'ouvre rien (c'est une métadonnée, pas un octet de
    # contenu) : le prendre en second avis ferme le trou d'un job.json édité à
    # la main qui annoncerait 12 o devant un fichier de 700 Mo. Un job plus
    # ancien, sans le champ `bytes` de la tâche 4, retombe sur le seul `stat`.
    taille = job.get("bytes")
    if isinstance(taille, bool) or not isinstance(taille, (int, float)) \
            or taille < 0:
        taille = 0
    taille = max(int(taille), p_glb.stat().st_size)
    if taille > MAX_EXT_GLB_BYTES:
        raise HTTPException(
            400, f"le noeud {nid} porte un GLB trop lourd ({int(taille)} o, "
                 f"maximum {MAX_EXT_GLB_BYTES} o) : non fusionnable - "
                 f"relance-le sur un maillage plus leger")
    raw = p_glb.read_bytes()
    credits = job.get("consumed_credits")
    # UN SEUL DÉPAQUETAGE : le maillage de scène sert au fit MAINTENANT et au
    # STL PLUS TARD — le mesurer deux fois coûtait une seconde lecture du
    # document et une seconde matérialisation des positions par externe.
    # AVEU DE PIC MÉMOIRE, dans l'idiome du fichier : le pic tient, POUR
    # CHAQUE externe résolu, ses octets de GLB (bornés par
    # `MAX_EXT_GLB_BYTES`) ET son maillage de scène, jusqu'à ce que la fusion
    # soit écrite — soit au pire `MAX_GRAPH_ELEMENTS` fois les deux. Les
    # octets sont relâchés dès `write_scene_glb` rendu (voir `post_build3d`,
    # seul endroit où ils ne servent plus à rien) ; seuls les maillages
    # survivent jusqu'au STL, et ce cache-là est exactement ce qui évite de
    # redépaqueter les mêmes documents une seconde fois.
    monde = glb_scene_mesh(raw, world=True)
    # LE CÔTÉ EN DERNIER (2d), et c'est l'ordre qui compte : le fit répond
    # « quelle taille, quelle place DANS SA COUCHE » — une question qui ne
    # connaît pas les faces, et dont la boîte vient déjà du manifeste du BON
    # côté (`_layer_box_mm`). Le retournement, lui, répond « de quel côté de la
    # carte » : il s'applique PAR-DESSUS le placement fini, exactement comme
    # pour un élément local, et par la MÊME fonction.
    return {"name": nom_el, "node": nid, "glb": raw, "monde": monde,
            "fit": trs_de_face(_fit_external(monde, box_mm, trs_n), w_mm,
                               layer["side"]),
            "engine": job.get("engine"), "closed": job.get("closed"),
            "closed_note": job.get("closed_note"),
            "credits": credits if isinstance(credits, int) else None}


@router.post("/build3d")
async def post_build3d(did: str, body: dict | None = None):
    """Exécute le graphe 100 % GRATUIT : GLB assemblé + metadata.json
    ERC-721 + STL prouvé-ou-refusé-motivé, bordereau chiffré (poids réels,
    jamais estimés). `graph_used` est le graphe NETTOYÉ — celui qui a
    réellement tourné, pas l'entrée brute du client."""
    from .core import read_deck, geom_of
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    body = body if isinstance(body, dict) else {}
    idx = _card_idx(body.get("card"))
    card_label = f"c{idx + 1:02d}"
    graph = clean_graph(body.get("graph"))

    # ── résolution du graphe : PURE, sans E/S — borne AVANT tout travail ────
    candidats, ignores = _resoud_tout(graph)
    # MOTIF 1/2 (distinct du "couche introuvable" ci-dessous, en revue) : le
    # graphe lui-même ne produit AUCUN élément — structurellement vide (aucun
    # nœud plane/relief) ou mal câblé (une source, ou l'assemblage, manque).
    # Un GLB à 0 élément est invalide au schéma glTF (minItems 1).
    if not candidats:
        raise HTTPException(
            409, "graphe vide : 0 element resolu (aucun noeud "
                 "plane/relief/mesh3d relie a la fois a une couche source et "
                 "a l'assemblage, ni aucune extrusion reliee a l'assemblage) "
                 "- exporte les couches d'abord et relie "
                 "layer -> plane/relief/mesh3d -> assemble")
    if len(candidats) > MAX_GRAPH_ELEMENTS:
        raise HTTPException(
            400, f"trop d'elements ({len(candidats)}, maximum "
                 f"{MAX_GRAPH_ELEMENTS})")

    art_node = next((n for n in graph["nodes"] if n["kind"] == "artifact"),
                    None)
    art_name = art_node["name"] if art_node else "artefact"
    g = geom_of(doc)
    # `w_mm`/`h_mm` servent ENCORE ici (les extras du GLB, la boîte de couche
    # d'un externe). La fenêtre UV coupe/toile et le fond perdu en pixels, eux,
    # ne servaient QU'À `_element_local` : ils sont dérivés DEDANS depuis `g`
    # (`_geom_element`, N2) — cette route n'en garde plus de copie, donc plus
    # aucune chance d'en dériver une seconde qui divergerait de l'autre.
    w_mm, h_mm = g.trim_mm
    doc_name = doc.get("name") or did
    sceau = _sceau_du_doc(doc)      # 3c : la portée 3D du Sceau prismatique

    def work() -> dict:
        t0 = time.perf_counter()

        out = _out_dir(did, create=True)
        elements: list[dict] = []
        externes: list[dict] = []
        bordereau: list[dict] = []
        manifestes: dict = {}
        # LE SCEAU A-T-IL TROUVÉ UN CORPS, OU SEULEMENT PARLÉ ? (R3) La
        # question se pose à la FIN, une fois tous les éléments vus : cocher
        # la portée 3D sur un graphe qui n'a ni cadre ni couronne ne doit pas
        # rendre le silence de la 2b.
        sceau_vu = False
        for ch in candidats:
            proc, layer = ch["proc"], ch["layer"]
            mat_n, trs_n = ch["mat"], ch["trs"]
            # ── L'EXTRUSION (T5) : le seul élément sans couche source. Elle
            #    court AVANT la dérivation du nom et du côté, qui parlent
            #    toutes deux d'une couche qu'elle n'a pas.
            if layer is None:
                nom_el = _nom_extrude(proc)
                # LE SCEAU D'ABORD (R3) : c'est lui qui décide de la LARGEUR
                # de la couronne quand c'est son corps qu'on construit, et la
                # géométrie se cuit après — pas l'inverse.
                avant = len(ignores)
                sc = _sceau_extrusion(proc, mat_n, sceau, ignores)
                if sc is not None or len(ignores) > avant:
                    sceau_vu = True
                elements.append(_element_extrude(
                    proc, nom_el, mat_n, trs_n, g, ignores, did,
                    largeur=(sc or {}).get("width_mm")))
                dit = {}
                if sc is not None:
                    elements[-1]["finish"] = holo_finish(sc["kind"], False)
                    dit = {"seal": {"kind": sc["kind"],
                                    "width_mm": sc["width_mm"],
                                    "why": _SEAL_EXTRUDE_WHY}}
                    if abs(float(sc["width_mm"])
                           - float(proc["width_mm"])) > 1e-9:
                        # LA SUBSTITUTION SE DIT (jamais un curseur qui cesse
                        # d'agir en silence) : les DEUX chiffres, et lequel a
                        # gagné.
                        dit["seal"]["node_width_mm"] = proc["width_mm"]
                bordereau.append({"name": nom_el, "kind": "local",
                                  "node": proc["id"],
                                  "contour": proc["contour"], **dit})
                continue
            nom_el = _nom_element(layer)
            # LE CÔTÉ AU BORDEREAU, ET SEULEMENT QUAND IL Y EN A UN À DIRE
            # (M3) : la clé n'apparaît que sur un élément de verso. L'ajouter
            # partout ferait changer le bordereau — donc l'écran — de TOUS les
            # artefacts recto, pour une information qu'ils n'ont pas.
            cote = {"side": "back"} if layer["side"] == "back" else {}
            if layer["side"] == CAPTURE_SIDE:
                # LA PROVENANCE S'AVOUE, ET AVEC SON CHIFFRE (D7). Le
                # manifeste importé est vérifié AVANT la construction — c'est
                # l'empreinte qui remplace la preuve d'empilement que ces
                # couches n'ont pas — et la couverture MESURÉE du fichier
                # entre au bordereau : « importée » sans chiffre ne serait
                # qu'une étiquette.
                if CAPTURE_SIDE not in manifestes:
                    manifestes[CAPTURE_SIDE] = _lire_manifeste(
                        out, card_label, CAPTURE_SIDE)
                row = _preuve_capture(did, out, card_label, layer,
                                      manifestes[CAPTURE_SIDE], g, ignores)
                cote = {"side": CAPTURE_SIDE, "import": _dit_provenance(row)}
            if proc["kind"] == "mesh3d":
                side = layer["side"]
                if side not in manifestes:
                    manifestes[side] = _lire_manifeste(out, card_label, side)
                externes.append(_element_externe(
                    did, proc, layer, nom_el,
                    _layer_box_mm(manifestes[side], layer, w_mm, h_mm,
                                  g.bleed_mm),
                    trs_n, card_label, w_mm))
                ex = externes[-1]
                bordereau.append({"name": nom_el, "kind": "externe",
                                  "node": proc["id"], "engine": ex["engine"],
                                  "credits": ex["credits"], **cote})
                # LE SCEAU NON PLUS NE MONTE PAS SUR UN GLB DE MOTEUR, et il
                # faut le DIRE — exactement comme la matière chaînée sur un
                # mesh3d, avouée depuis la 2b (`_resolve_graph_elements`). Sans
                # cette ligne, allumer la portée 3D sur un cadre porté par un
                # moteur ne faisait RIEN, en silence : le pire des deux
                # (l'utilisateur a coché, l'écran n'a rien à répondre).
                if (sceau.get("on") and sceau.get("mesh")
                        and layer.get("role") == "cadre"):
                    sceau_vu = True          # il a PARLÉ, même pour refuser
                    ignores.append({
                        "node": proc["id"],
                        "why": "sceau 3D ignore sur cette couche : le GLB du "
                               "moteur porte deja ses materiaux (la portee 3D "
                               "du Sceau habille un plan ou un relief)"})
                continue
            elements.append(_element_local(
                out, proc, layer, nom_el, mat_n, trs_n, card_label, g,
                ignores, did))
            # LE SCEAU, PORTÉE 3D (3c) : APRÈS l'habillage, parce que la règle
            # est « combler le silence » — il faut d'abord savoir si le graphe
            # a parlé. La clé `seal` n'apparaît que sur l'élément qui la
            # reçoit, exactement comme `cote` juste au-dessus : l'ajouter
            # partout changerait le bordereau de TOUS les artefacts pour une
            # information qu'ils n'ont pas.
            avant = len(ignores)
            scelle = _scelle(elements[-1], layer, mat_n, sceau, ignores)
            if scelle or len(ignores) > avant:
                sceau_vu = True
            bordereau.append({"name": nom_el, "kind": "local",
                              "node": proc["id"], **cote, **scelle})
        if sceau.get("on") and sceau.get("mesh") and not sceau_vu:
            ignores.append({"node": "seal", "why": _SANS_CORPS})
        t_resolve = time.perf_counter()

        extras = {"deck": doc_name, "card": card_label, "format": g.fmt,
                  "size_mm": [w_mm, h_mm], "unit": "metre",
                  "schema": ARTIFACT_SCHEMA}
        perdus: list[dict] = []
        glb = write_scene_glb(elements, name=art_name, extras=extras,
                              externals=externes or None, out_ignored=perdus)
        for p_ig in perdus:
            rang = p_ig.get("index")
            ignores.append({
                "node": (externes[rang]["node"]
                         if isinstance(rang, int) and 0 <= rang < len(externes)
                         else art_name),
                "why": p_ig.get("why")})
        # LES OCTETS DES EXTERNES NE SERVENT PLUS : la fusion les a recopiés
        # dans le buffer, et le STL travaille sur le maillage de scène déjà
        # mesuré. Les garder jusqu'à la fin de la requête, c'est garder
        # jusqu'à `MAX_GRAPH_ELEMENTS x MAX_EXT_GLB_BYTES` pour rien.
        for ex in externes:
            ex["glb"] = b""
        glb_name = f"{art_name}.glb"
        # ── APERÇU PÉRIMÉ (legs 4) : la capture précédente montre l'ANCIEN
        #    GLB. La laisser, c'est laisser le metadata (`image`) pointer une
        #    vignette qui MENT sur le fichier qu'elle est censée illustrer —
        #    le bordereau, lui, redit honnêtement `written: false`.
        _efface(out / f"{art_name}_preview.png")
        (out / glb_name).write_bytes(glb)
        t_glb = time.perf_counter()

        meta = {
            # tiret ASCII GARDÉ (contrainte d'encodage maison) ; le reste de
            # la prose est accentué — json.dumps ci-dessous est en
            # ensure_ascii=False, le fichier livré porte déjà des accents.
            "name": f"{doc_name} - carte {card_label}",
            # « construite localement » N'EST PLUS VRAI dès qu'un moteur a
            # livré un élément (2b) : la phrase suit ce qui s'est réellement
            # passé, elle ne le décrit pas de mémoire.
            "description": (
                "Carte 3D par éléments séparés, construite localement."
                if not externes else
                "Carte 3D par éléments séparés : assemblage local, maillages "
                "de moteur fusionnés à leur couche."),
            "image": f"{art_name}_preview.png",
            "animation_url": glb_name,
            "attributes": [
                {"trait_type": "deck", "value": doc_name},
                {"trait_type": "carte", "value": card_label},
                {"trait_type": "elements_3d",
                 "value": len(elements) + len(externes)},
                # MESURÉ, jamais annoncé : « local » n'apparaît que s'il y a
                # vraiment un élément construit ici, et chaque moteur n'y est
                # que s'il a vraiment livré un GLB fusionné. Trié pour que
                # deux constructions du même graphe portent la même chaîne.
                {"trait_type": "engines",
                 "value": "+".join(sorted(
                     ({"local"} if elements else set())
                     | {str(ex["engine"] or "moteur") for ex in externes}))
                     or "local"},
                {"trait_type": "schema", "value": ARTIFACT_SCHEMA},
            ],
        }
        meta_bytes = json.dumps(meta, ensure_ascii=False,
                                indent=2).encode("utf-8")
        meta_name = f"{art_name}.metadata.json"
        (out / meta_name).write_bytes(meta_bytes)

        # ── STL : gate sur le drapeau `closed` DÉCLARÉ par les constructeurs
        #    de maillage (relief_mesh -> True, quad_mesh -> False), jamais
        #    une re-mesure de `mesh_measures` ici (l'instrument des TESTS,
        #    pas de la route — coût mesuré en revue de la tâche 2). ─────────
        #
        #    LES EXTERNES (2b) : le `closed` CACHÉ AU JOB par la tâche 4,
        #    RELU — jamais re-mesuré non plus. Trois états et non deux (legs
        #    de la tâche 4) : True imprimable, False ouvert, et None « pas
        #    mesuré » — un GLB trop lourd ou trop dense arrive `served` sans
        #    verdict, et un verdict absent n'est PAS un verdict favorable.
        motif = None
        if not all(bool(el["mesh"].get("closed")) for el in elements):
            motif = ("au moins un element n'est pas un solide ferme "
                     "(un plan texture n'a pas de volume) - le STL est "
                     "refuse plutot que livre casse")
        for ex in externes:
            if motif is not None or ex["closed"] is True:
                continue
            if ex["closed"] is False:
                motif = (f"l'element externe {ex['name']} (noeud "
                         f"{ex['node']}) n'est pas un solide ferme - le STL "
                         f"est refuse plutot que livre casse")
            else:
                motif = (f"fermeture non mesuree pour l'element externe "
                         f"{ex['name']} (noeud {ex['node']}) : "
                         + str(ex["closed_note"]
                               or "le moteur n'a pas rendu la mesure"))
        if motif is None:
            # LE STL N'A PAS DE NŒUD pour porter un transform : ce qui, dans
            # le GLB, vit sur le nœud d'un élément doit être CUIT dans ses
            # sommets ici. Cela vaut pour les externes (leur fit) COMME pour
            # les locaux qui traversent un `transform` — l'oublier pour les
            # seconds imprimait une pièce à l'origine, non tournée, pendant
            # que le GLB la montrait déplacée : deux fichiers, deux vérités.
            # `el["trs"]` porte DÉJÀ la forme d'un fit (`_trs_dict` est
            # l'adaptateur : translate/rotate_deg/scale), et
            # `apply_fit_inplace` applique le même T x R x S que `_node_trs`
            # écrit dans le nœud — une seule règle de composition pour les
            # deux sorties.
            pieces = []
            for el in elements:
                if not isinstance(el.get("trs"), dict):
                    pieces.append(el)
                    continue
                # COPIE des positions : le maillage local est encore référencé
                # par `elements` (et son `closed` par le gate ci-dessus) — le
                # transformer sur place changerait ce que d'autres ont déjà lu.
                pieces.append({"name": el["name"], "z_mm": 0.0,
                               "mesh": apply_fit_inplace(
                                   {"positions": list(el["mesh"]["positions"]),
                                    "indices": el["mesh"]["indices"]},
                                   el["trs"])})
            for ex in externes:
                # ici la transformation SUR PLACE est légitime : ce maillage
                # de scène n'appartient qu'à cet appel (voir `_element_externe`).
                pieces.append({"name": ex["name"], "z_mm": 0.0,
                               "mesh": apply_fit_inplace(ex["monde"],
                                                         ex["fit"])})
            stl_bytes = _write_stl_binary(pieces, art_name)
            stl_name = f"{art_name}.stl"
            (out / stl_name).write_bytes(stl_bytes)
            stl_bordereau = {"written": True, "name": stl_name,
                             "bytes": len(stl_bytes)}
        else:
            # MÊME raison que l'aperçu périmé ci-dessus : un STL d'une passe
            # précédente que cette passe-ci REFUSE reste servi par /file et
            # contredit le bordereau qui vient de dire « non ».
            _efface(out / f"{art_name}.stl")
            stl_bordereau = {"written": False, "why": motif}
        t_stl = time.perf_counter()

        return {"artifact": {
            "glb": {"name": glb_name, "bytes": len(glb)},
            "metadata": {"name": meta_name, "bytes": len(meta_bytes)},
            "stl": stl_bordereau,
            # honnête : l'aperçu n'existe qu'après la capture client
            # (POST /preview/{art}, ci-dessous) — jamais un mensonge.
            "preview": {"expected": f"{art_name}_preview.png",
                       "written": False},
            # `elements` reste un NOMBRE : l'écran 2a le concatène dans une
            # phrase (mod-forge3d.js, « N élément(s) — ») et en changer le
            # type y afficherait « [object Object] ». Le détail par élément
            # vit à côté, dans `elements_detail`.
            "elements": len(elements) + len(externes),
            "elements_detail": bordereau,
            # REQUIS (revue) : chaque nœud écarté de la résolution, avoué —
            # jamais tu. Liste vide si rien n'a été ignoré (pas absente).
            "ignored": ignores,
            "graph_used": graph,
            "ms": {"resolve": int((t_resolve - t0) * 1000),
                  "glb": int((t_glb - t_resolve) * 1000),
                  "stl": int((t_stl - t_glb) * 1000),
                  "total": int((t_stl - t0) * 1000)},
        }}

    try:
        return await asyncio.to_thread(work)
    except HTTPException:
        raise
    except ModuleNotFoundError as e:           # pragma: no cover - env casse
        raise HTTPException(503, f"Module requis absent : {e}")
    except ValueError as e:
        # LA FUSION ET LES LECTEURS GLB refusent par `ValueError` NOMMÉE
        # (image `uri`, chunk tronqué, indice hors bornes, mesh sans
        # primitive) — c'est leur contrat, écrit dans forge3d_scene.py : un
        # module PUR n'a pas de code HTTP à rendre. Le message part TEL QUEL,
        # jamais réécrit : il nomme déjà exactement ce qui cloche dans le
        # binaire du moteur, et le paraphraser ne ferait que le diluer.
        logger.warning(f"cards/forge3d: GLB externe refuse : {_panne(e)}")
        raise HTTPException(409, _panne(e))
    except Exception as e:
        logger.exception("cards/forge3d: construction du graphe impossible")
        raise HTTPException(500, f"Construction du graphe impossible : {e}")


# ── LE JOB mesh3d — UN JOB DE FOND PAR NŒUD (Task 4, 2b) ────────────────────
# Modèle : le patron `/assets/3d` de routes.py (pré-enregistrer, travailler en
# tâche de fond, poller), MAIS l'état durable est `nodes/{nid}/job.json`,
# DECK-LOCAL — pas un JobRecord de la file générale. Un nœud de graphe n'est
# pas un rendu de la bibliothèque : il vit et meurt avec son deck, et son
# bordereau doit survivre à un redémarrage sans polluer les autres écrans.
#
# POURQUOI `BackgroundTasks` ET NON `asyncio.create_task` — la seule vraie
# question d'intégration de cette tâche, tranchée par la MESURE : les tests
# parlent à l'application par un transport ASGI en process, et un appel = UNE
# boucle d'évènements (`asyncio.run`). Une tâche créée par `create_task` meurt
# avec cette boucle — mesuré : son fichier n'est jamais écrit. `BackgroundTasks`
# est exécuté par le serveur APRÈS l'envoi de la réponse mais DANS le même
# appel ASGI : le client reçoit son `queued` tout de suite, et la tâche va
# jusqu'au bout dans les deux mondes. C'est aussi le patron déjà en vigueur
# ailleurs dans le dépôt (routes.py:/assets/3d) — un seul modèle d'exécution.
MESH3D_JOB_SCHEMA = "card-3d/mesh3d-job@1"
MESH3D_POLYCOUNT = 30000              # cible de triangles demandée au moteur
MESH3D_TEXTURES_MAX = 12              # textures rapatriées par job (borne :
                                       # le fournisseur en annonce autant qu'il
                                       # veut, notre disque non)
MESH3D_LAUNCH_GRACE_S = 30.0          # délai au-delà duquel un marqueur de
                                       # lancement sans tâche est PÉRIMÉ (voir
                                       # _MESH3D_RUNNING / _mesh3d_vivant)
MESH3D_POLL_RETRIES = 5               # reprises d'un poll Meshy en échec : un
                                       # blip réseau ne doit pas tuer un job
                                       # DÉJÀ PAYÉ de vingt minutes
# Reprises des DEUX SENS de l'accès à job.json. Sous Windows, lecteur et
# écrivain se disputent le fichier DESTINATION : le lecteur qui perd voit
# PermissionError à l'ouverture, l'écrivain qui perd voit `os.replace` échouer
# (WinError 5). Les deux sont PASSAGERS et n'ont rien à voir avec l'absence ni
# avec la panne. Trois essais espacés de 20 ms couvrent largement la fenêtre
# mesurée, sans jamais retarder le cas courant : seule cette erreur-là est
# retentée, dans un cas comme dans l'autre.
_JOB_IO_ESSAIS = 3
_JOB_IO_PAUSE_S = 0.02
# charset ET longueur de `clean_graph` — un nid qui passe ici traverse le
# nettoyeur INCHANGÉ — MOINS les noms qui ne sont QUE des points. Constaté en
# auto-revue, absent du plan : `..` satisfait `[A-Za-z0-9._-]{1,24}`, et ce
# nid-là n'est pas un nom de dossier, c'est un SAUT — `nodes/..` désigne
# `forge3d/`, que la réinitialisation du nœud efface au `rmtree`. Un seul
# lancement sur un nœud nommé `..` détruisait donc TOUTES les couches
# exportées du deck. `clean_graph` ne pouvait pas l'attraper : pour lui, un id
# n'est jamais un chemin.
_NID_RE = re.compile(r"^(?!\.+$)[A-Za-z0-9._-]{1,24}$")

# Registre MÉMOIRE des jobs vivants DE CE PROCESSUS : (did, nid) -> la tâche
# de fond, ou l'INSTANT DE LANCEMENT (un float) tant qu'elle n'a pas démarré.
# Ce marqueur intermédiaire n'est pas un détail : le serveur ne lance la tâche
# qu'APRÈS avoir envoyé la réponse, donc un poll très rapide tomberait sur
# « queued sans tâche » et déclarerait ORPHELIN un job parfaitement vivant.
# La route le pose donc elle-même, avant de rendre. Il PÉRIME au bout de
# MESH3D_LAUNCH_GRACE_S : si l'envoi de la réponse échoue (client parti), le
# serveur ne lance jamais la tâche de fond — sans péremption, le nœud resterait
# bloqué en 409 jusqu'au redémarrage. Le registre, lui, ne survit pas au
# processus : c'est PRÉCISÉMENT son utilité — un `running` sur disque sans
# entrée ici est un orphelin de redémarrage, avoué au lieu de tourner en rond.
# Registre PER-PROCESS : un déploiement multi-workers casserait la détection
# d'orphelins (le worker B ne voit pas les tâches du worker A et les
# déclarerait mortes) — main.py lance UN SEUL worker.
_MESH3D_RUNNING: dict[tuple[str, str], object] = {}


class _JobRemplace(Exception):
    """Signal INTERNE : une relance a remplacé ce job pendant qu'il tournait.

    Le porteur de ce signal doit SE TAIRE — ne rien écrire, ne rien dépenser,
    ne rien dire dans le bordereau : le dossier et le `job.json` appartiennent
    désormais à quelqu'un d'autre. Ce n'est pas une panne, c'est une
    succession."""


def _node_dir(did: str, nid: str, create: bool = False) -> Path:
    """`.../forge3d/nodes/{nid}` — le dossier DURABLE d'un nœud.

    DOUBLE GARDE-FOU, la doctrine de `contract.deck_dir` : le motif `_NID_RE`
    interdit déjà séparateurs et noms de saut, le confinement ci-dessous est
    la ceinture par-dessus les bretelles — au cas où le motif viendrait à être
    élargi un jour. Ce dossier est effacé au `rmtree` à chaque relance : s'en
    échapper d'un seul cran détruirait les couches exportées du deck."""
    racine = (_out_dir(did) / "nodes").resolve()
    d = (racine / nid).resolve()
    if d.parent != racine or d == racine:
        raise HTTPException(400, "Identifiant de noeud invalide")
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _job_write(did: str, nid: str, job: dict) -> dict:
    """job.json écrit ATOMIQUEMENT (fichier temporaire + `os.replace`) : un
    poll concurrent lit toujours un JSON ENTIER, jamais la moitié d'une
    écriture en cours — l'écran poll pendant que la tâche de fond écrit.

    L'AUTRE MOITIÉ DE LA COURSE, mesurée elle aussi : quand c'est le poll qui
    tient le fichier DESTINATION, c'est `os.replace` qui échoue (WinError 5).
    Laissée telle quelle, l'exception remontait jusqu'à `_run_mesh3d`, qui
    déclarait le job FAILED avec le WinError pour motif : un simple poll
    tuait un job PAYÉ, et le crédit était consommé pour rien. On retente donc
    ce refus-là, exactement comme `_job_read` retente le sien ; s'il persiste
    au-delà des essais, il repart tel quel — un disque vraiment bloqué reste
    une panne, et l'aveu doit le dire."""
    d = _node_dir(did, nid, create=True)
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    for reste in range(_JOB_IO_ESSAIS - 1, -1, -1):
        try:
            os.replace(tmp, d / "job.json")
            return job
        except PermissionError:
            if not reste:
                raise
            time.sleep(_JOB_IO_PAUSE_S)
    return job


def _job_read(did: str, nid: str) -> dict | None:
    """Le job sur disque, ou None. Un fichier illisible (tronqué à la main,
    disque en panne) vaut ABSENT — jamais une exception qui deviendrait 500.

    MAIS « momentanément verrouillé » N'EST PAS « absent ». Sous Windows,
    pendant l'`os.replace` de `_job_write`, ouvrir le fichier DESTINATION
    échoue en `PermissionError` (violation de partage) : les octets sont là,
    ils sont juste hors d'atteinte pendant une fraction de milliseconde. Le
    confondre avec l'absence faisait rendre 404 « aucun job sur ce noeud »
    PENDANT qu'un job PAYANT tournait — et l'écran, qui a raison de tenir un
    job nul pour terminal, concluait « jamais lancé » et ARRÊTAIT son poll :
    le nœud finissait sa course en dépensant, sans laisser une trace à
    l'écran, et le pied de coût le recomptait comme restant à lancer.
    On retente donc brièvement, et seulement sur ce refus-là : le chemin
    courant (aucun job, `is_file()` faux) ne paie pas un millième de seconde,
    et une vraie corruption vaut toujours ABSENT, du premier coup."""
    p = _node_dir(did, nid) / "job.json"
    for reste in range(_JOB_IO_ESSAIS - 1, -1, -1):
        if not p.is_file():
            return None
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except PermissionError:
            # le seul cas retentable : l'écriture concurrente tient le fichier
            if reste:
                time.sleep(_JOB_IO_PAUSE_S)
                continue
            logger.warning(f"cards/forge3d: job.json verrouille apres "
                           f"{_JOB_IO_ESSAIS} essais ({did}/{nid})")
            return None
        except (ValueError, OSError, UnicodeDecodeError):
            logger.exception(f"cards/forge3d: job.json illisible ({did}/{nid})")
            return None
        return j if isinstance(j, dict) else None
    return None


def _job_write_si(did: str, nid: str, job: dict, run_id: str) -> bool:
    """CLÔTURE D'IDENTITÉ : n'écrit que si le `job.json` sur disque porte
    ENCORE notre `run_id`. Rend False sinon — l'appelant doit se taire.

    Sans cette clôture, un runner RASSIS (dont l'envoi de la réponse a traîné
    au-delà de la péremption du marqueur, pendant qu'une relance réinitialisait
    le dossier et lançait un second job) ressuscitait le dossier effacé et
    écrivait SON bordereau par-dessus celui du job vivant : l'écran voyait la
    progression d'un job qui n'existe plus, et le vrai job disparaissait du
    bordereau tout en continuant à dépenser."""
    actuel = _job_read(did, nid) or {}
    if actuel.get("run_id") != run_id:
        return False
    _job_write(did, nid, job)
    return True


def _mesh3d_vivant(did: str, nid: str) -> bool:
    """Un job de ce nœud tourne-t-il ENCORE dans CE processus ? Un marqueur de
    lancement (float) compte pour vivant tant qu'il n'a pas PÉRIMÉ."""
    t = _MESH3D_RUNNING.get((did, nid))
    if t is None:
        return False
    if isinstance(t, float):
        return (time.monotonic() - t) < MESH3D_LAUNCH_GRACE_S
    return not t.done()


def _mesh3d_price(engine: str, provider: str, ultra: bool) -> dict:
    """Le prix ANNONCÉ AVANT le lancement — MÊMES sources que `/info` : le
    barème `pricing` pour fal (en $), la grille partagée de `meshy_service`
    pour Meshy (en crédits) + la conversion $ directionnelle. Les littéraux de
    texture sont les constantes du module : une seule vérité pour le devis ET
    pour la requête, jamais recopiés de l'un vers l'autre."""
    from app.services import pricing
    from app.services import meshy_service as MS
    if provider == "fal":
        return {"usd": pricing.estimate({"kind": "asset3d",
                                         "engine": engine})["total_usd"]}
    cr = MS.credits_image_to_3d(engine, "standard", MESH3D_SHOULD_TEXTURE,
                                MESH3D_TEXTURE_RES, ultra=bool(ultra))
    return {"credits": cr,
            "usd": round(cr * float(pricing.load().get("meshy_credit_usd",
                                                       0.02)), 4)}


def _mesh3d_prepare_upload(src: Path, dest: Path) -> dict:
    """La couche source, réduite au côté long des moteurs — ALPHA CONSERVÉ
    (c'est lui qui porte la silhouette dont vit un moteur image->3D).

    UNE SEULE LECTURE, DEUX EMPREINTES (M1) : la route ne relit plus le
    fichier pour le hacher de son côté — c'est ici, là où les octets sont
    DÉJÀ en main, que les deux provenances se calculent. `sha256` est celui de
    la COUCHE LIVRÉE (l'entrée du job, celle du manifeste de la phase 1) ;
    `upload_sha256` est celui des octets RÉELLEMENT ENVOYÉS au moteur (la
    vignette réduite). Les deux, parce qu'ils répondent à deux questions
    différentes — « de quelle couche vient cet artefact » et « qu'a vu le
    moteur exactement » — et parce qu'une seule des deux mentirait sur
    l'autre."""
    from PIL import Image
    raw = src.read_bytes()
    im = Image.open(io.BytesIO(raw))
    im.load()
    im = im.convert("RGBA")
    im.thumbnail((MESH3D_UPLOAD_PX, MESH3D_UPLOAD_PX), Image.LANCZOS)
    tampon = io.BytesIO()
    im.save(tampon, "PNG")
    octets = tampon.getvalue()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(octets)
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "upload_sha256": hashlib.sha256(octets).hexdigest(),
            "upload_bytes": len(octets)}


def _data_uri(p: Path) -> str:
    """Le PNG d'envoi en URI de données — Meshy accepte `image_url` sous cette
    forme, ce qui évite d'exposer un fichier local sur le réseau."""
    return ("data:image/png;base64,"
            + base64.b64encode(p.read_bytes()).decode("ascii"))


def _mesh3d_closed(raw: bytes) -> tuple:
    """`closed` MESURÉ UNE FOIS, à l'import du GLB du moteur — puis CACHÉ dans
    le job : l'écran et le futur gate STL le RELISENT, personne ne le
    recalcule (la mesure alloue ~3 entrées de dictionnaire par triangle).

    Rend `(closed, note, triangles)`. `closed` vaut None quand la mesure est
    REFUSÉE — maillage au-delà de la borne mémoire, ou GLB que nos lecteurs ne
    savent pas ramener au type commun. La note dit LEQUEL, et le job reste
    SERVI : le binaire est payé, il ne se perd pas pour un chiffre manquant."""
    try:
        doc, _ = read_glb(raw)
        tris = glb_triangle_estimate(doc)
        if tris > MESH3D_CLOSED_TRI_MAX:
            return None, (f"fermeture non mesurée : maillage trop lourd "
                          f"({tris} triangles, plafond "
                          f"{MESH3D_CLOSED_TRI_MAX})"), tris
        rep = mesh_measures(glb_scene_mesh(raw))
        return bool(rep["closed"]), None, int(rep["triangles"])
    except ValueError as e:
        return None, f"fermeture non mesurée : {e}", 0


async def _mesh3d_rapatrie(url: str, dest: Path) -> None:
    """UN binaire Meshy ramené dans le nœud (`_fetch_url` est mock-aware),
    borné au même plafond que le reste du domaine AVANT d'atteindre le disque.

    C'est le SEUL endroit de la chaîne où la borne peut encore agir : ici, le
    fichier n'est pas écrit tant que nous n'avons pas dit oui. Côté fal, la
    couture de téléchargement écrit elle-même — quand nous voyons la taille,
    le fichier est déjà là et payé : la mesure de fermeture dégrade alors au
    lieu de refuser (voir `_run_mesh3d`)."""
    from app.services import meshy_service as MS
    data = await MS._fetch_url(url)
    if len(data) > MAX_EXT_GLB_BYTES:
        raise RuntimeError(f"meshy: {dest.name} trop lourd ({len(data)} o, "
                           f"maximum {MAX_EXT_GLB_BYTES} o)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(dest.write_bytes, data)


@router.post("/mesh3d/{nid}")
async def post_mesh3d(did: str, nid: str, background_tasks: BackgroundTasks,
                      body: dict | None = None):
    """Lance le job PAYANT d'UN nœud mesh3d : gardes d'abord, PRIX annoncé
    avant, dossier du nœud RÉINITIALISÉ, puis tâche de fond. Rend le job tel
    qu'il vient d'être écrit (`queued`) — l'écran poll `GET /mesh3d/{nid}`.

    Relancer un nœud REPART DE ZÉRO (legs 4 du plan) : le dossier est effacé
    avant la première ligne du nouveau job. Un `model.glb` de la passe
    précédente qui survivrait ferait mentir le bordereau du nouveau job."""
    from .core import read_deck
    from .contract import is_valid_did
    from app.config import settings
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    if not _NID_RE.match(nid or ""):
        raise HTTPException(400, "Identifiant de noeud invalide")
    body = body if isinstance(body, dict) else {}
    card_label = f"c{_card_idx(body.get('card')) + 1:02d}"
    graph = clean_graph(body.get("graph"))

    # ── résolution PURE, sans E/S — tout ce qui peut être refusé sans
    #    toucher au disque l'est ici (doctrine : bornes d'abord) ────────────
    node = next((n for n in graph["nodes"]
                 if n["id"] == nid and n["kind"] == "mesh3d"), None)
    if node is None:
        raise HTTPException(400, f"noeud mesh3d {nid} absent du graphe")
    provider = next((e["provider"] for e in MESH3D_ENGINES
                     if e["id"] == node["engine"]), None)
    if provider is None:               # `clean_graph` l'interdit déjà ; garde
        raise HTTPException(400, f"moteur inconnu : {node['engine']!r}")
    # LA source : première arête layer -> nid, même règle de « première arête
    # gagnante » que `_resolve_graph_elements` pour plane/relief.
    par_id = {n["id"]: n for n in graph["nodes"]}
    src = next((par_id[e["from"]] for e in graph["edges"]
                if e["to"] == nid
                and par_id.get(e["from"], {}).get("kind") == "layer"), None)
    if src is None:
        raise HTTPException(
            400, f"noeud mesh3d {nid} sans couche source (relie une couche : "
                 f"layer -> {nid})")

    fname = _layer_filename(src, card_label)
    p_src = _out_dir(did) / fname
    # MÊME motif et MÊMES mots que build3d : le graphe est bien câblé, mais LA
    # couche visée n'a pas été livrée pour cette carte/ce côté. Ce contrôle
    # passe AVANT celui des clés, EXPRÈS : envoyer l'utilisateur dans les
    # Réglages alors que ce sont SES couches qui manquent, c'est le mauvais
    # écran et une clé posée pour rien.
    if not p_src.is_file():
        raise HTTPException(
            409, f"exporte les couches d'abord : {fname} absent (POST /layers)")
    # M1 : la BORNE de poids se vérifie ici, sur un `stat` — 4xx AVANT tout
    # travail. Le hachage, lui, ne se fait plus en double : il appartient à
    # `_mesh3d_prepare_upload`, seul endroit où les octets sont déjà lus.
    taille_src = p_src.stat().st_size
    if taille_src > MAX_LAYER_BYTES:
        raise HTTPException(
            413, f"{fname} : couche trop lourde ({taille_src} o, maximum "
                 f"{MAX_LAYER_BYTES} o)")

    # ── les clés : refusées AVANT de réinitialiser quoi que ce soit — un
    #    refus ne doit jamais détruire le job précédent ───────────────────────
    if provider == "fal" and not settings.FAL_KEY:
        raise HTTPException(400, "FAL_KEY not configured. Add it in Settings.")
    if provider == "meshy" and not (settings.has_meshy or settings.MESHY_MOCK):
        raise HTTPException(503, "MESHY_API_KEY not configured — add it in "
                                 "Settings (or set MESHY_MOCK=1 for the local "
                                 "simulator)")

    # ── C1 : LE VERROU, POSÉ D'UN SEUL TENANT ──────────────────────────────
    # Le contrôle et la pose ne doivent RIEN avoir entre eux : pas un `await`,
    # pas une E/S. Avec le devis, le rmtree, le hachage et l'écriture entre les
    # deux, deux POST rapprochés passaient TOUS LES DEUX le contrôle, effaçaient
    # TOUS LES DEUX le dossier et lançaient DEUX jobs PAYANTS — puis le second
    # marqueur écrasait le premier et le `finally` du survivant retirait
    # l'entrée, déclarant orphelin un job bel et bien vivant. La boucle
    # d'évènements ne peut pas s'intercaler entre ces deux lignes.
    if _mesh3d_vivant(did, nid):
        raise HTTPException(409, f"un job court déjà sur ce noeud ({nid})")
    jeton = time.monotonic()
    _MESH3D_RUNNING[(did, nid)] = jeton        # AUCUN await entre les deux

    try:
        price = await asyncio.to_thread(_mesh3d_price, node["engine"],
                                        provider, node["ultra"])
        d = _node_dir(did, nid)

        def _reinitialise() -> None:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
            restes = sorted(x.name for x in d.iterdir())
            if restes:                # Windows : un verrou peut survivre
                raise OSError(f"vestiges non effaces : {restes[:4]}")

        try:
            await asyncio.to_thread(_reinitialise)
        except OSError as e:
            raise HTTPException(
                409, f"reinitialisation du noeud {nid} impossible : {e}")

        # C2 : l'identité de CE lancement. Le runner la présente à chaque
        # écriture ; un runner dont le run_id n'est plus celui du disque se
        # tait (voir `_job_write_si`).
        job = {"schema": MESH3D_JOB_SCHEMA, "node": nid,
               "engine": node["engine"], "provider": provider,
               "run_id": uuid.uuid4().hex,
               "status": "queued", "progress": 0, "step": "En file",
               "error": None, "price": price,
               # `sha256` est rempli par le runner, sur les octets qu'il lit
               # VRAIMENT pour l'envoi (M1) — annoncer ici une empreinte que
               # personne n'a encore relue serait une promesse, pas une mesure.
               "source": {"role": src.get("role"), "side": src["side"],
                          "file": fname, "bytes": taille_src, "sha256": None},
               "closed": None, "closed_note": None, "started": _iso_now(),
               "files": {}}
        await asyncio.to_thread(_job_write, did, nid, job)
        background_tasks.add_task(_run_mesh3d, did, nid, dict(node), provider,
                                  dict(job["source"]), job["run_id"])
    except BaseException:
        # un refus (ou une annulation) ne doit JAMAIS laisser le nœud verrouillé
        if _MESH3D_RUNNING.get((did, nid)) is jeton:
            _MESH3D_RUNNING.pop((did, nid), None)
        raise
    return {"job": job}


async def _run_mesh3d(did: str, nid: str, node: dict, provider: str,
                      source: dict, run_id: str) -> None:
    """La tâche de fond d'UN nœud. Tout le travail lourd (image, octets,
    mesures, écritures) part en `to_thread` ; seul le réseau reste `await`.
    Toute panne finit en `status: failed` avec le message LITTÉRAL du
    fournisseur — jamais réécrit, jamais avalé (doctrine erreurs du lab).

    C2 — CLÔTURE D'IDENTITÉ : `run_id` est celle de CE lancement. Elle est
    présentée AVANT la première dépense et AVANT CHAQUE écriture ; dès qu'elle
    ne correspond plus à celle du disque, ce runner se tait et sort. Sans elle,
    un runner rassis (envoi de réponse traînant au-delà de la péremption du
    marqueur) ressuscitait un dossier réinitialisé, dépensait une seconde fois
    et écrivait son bordereau par-dessus celui du job vivant."""
    from app.services import asset3d_service as A3D
    from app.services import meshy_service as MS
    cle = (did, nid)
    moi = asyncio.current_task()
    job: dict = {}
    try:
        # La clôture PASSE AVANT TOUT — avant le registre, avant le dossier,
        # avant le premier octet dépensé. Un runner remplacé ne doit pas même
        # recréer le dossier qu'une relance vient d'effacer.
        # (Aucun `job` de repli n'est nécessaire : si `job.json` manque, la
        # clôture échoue et on sort — le disque est la seule source du
        # bordereau, jamais un dictionnaire reconstruit de mémoire.)
        job = _job_read(did, nid) or {}
        if job.get("run_id") != run_id:
            raise _JobRemplace(f"{did}/{nid}")
        _MESH3D_RUNNING[cle] = moi

        async def avance(step: str, progress: int, **extra) -> None:
            job.update({"status": "running", "step": step,
                        "progress": int(progress)}, **extra)
            if not await asyncio.to_thread(_job_write_si, did, nid, job, run_id):
                raise _JobRemplace(f"{did}/{nid}")

        engine = node["engine"]
        d = _node_dir(did, nid, create=True)
        upload = d / "upload_src.png"
        empreintes = await asyncio.to_thread(
            _mesh3d_prepare_upload, _out_dir(did) / source["file"], upload)
        # M1 : la provenance porte les empreintes RELUES, pas celles promises
        # par la route — et cette écriture est le DERNIER contrôle de clôture
        # avant la moindre dépense.
        await avance("Préparation", 10, source={**source, **empreintes})
        consommes = None
        textures: list[str] = []

        if provider == "fal":
            # Les coutures sont résolues PAR LE MODULE au moment de l'appel
            # (`A3D._upload`, jamais un `from ... import _upload` figé à
            # l'import) : c'est ce qui rend le moteur remplaçable en test,
            # donc cette route testable sans dépenser un centime.
            url = await A3D._upload(str(upload))
            args = A3D.build_engine_args(engine, [url],
                                         {"format": "glb", "textures": True})
            await avance(f"Moteur {engine}", 40)
            res = await A3D._run_engine(engine, args)
            res = res if isinstance(res, dict) else {}
            if not res.get("mesh_url"):
                raise RuntimeError(f"{engine}: aucun mesh dans la réponse fal")
            # I3 : l'URL de l'artefact PAYÉ est persistée AVANT d'être suivie —
            # si le téléchargement casse, elle reste dans le bordereau (les URL
            # fal vivent assez pour un second essai à la main ; la jeter serait
            # perdre le seul lien vers ce qu'on vient d'acheter).
            await avance(f"Moteur {engine}", 70, mesh_url=res["mesh_url"])
            await asyncio.to_thread(A3D._download, res["mesh_url"],
                                    d / "model.glb")
            if res.get("preview_url"):
                await asyncio.to_thread(A3D._download, res["preview_url"],
                                        d / "preview.png")
        else:
            payload = {"image_url": await asyncio.to_thread(_data_uri, upload),
                       "ai_model": engine,
                       "should_texture": MESH3D_SHOULD_TEXTURE,
                       "enable_pbr": True,
                       "texture_resolution": MESH3D_TEXTURE_RES,
                       "topology": "triangle",
                       "target_polycount": MESH3D_POLYCOUNT}
            if node.get("texture_prompt"):
                payload["texture_prompt"] = node["texture_prompt"]
            if node.get("ultra"):
                payload["ultra_mode"] = True
            # dernier contrôle de clôture avant la dépense (C2)
            await avance(f"Moteur {engine}", 25)
            tid = await MS.create_task("openapi/v1/image-to-3d", payload)
            await avance("Meshy PENDING", 30, task_id=tid)
            # I2 : la tâche PAYÉE entre au journal PARTAGÉ de meshy_service —
            # sans cette ligne, `repatriate` refuse un id qu'il ne connaît pas
            # et `expiring_soon` ne peut prévenir personne avant que les URL
            # Meshy n'expirent : le binaire acheté se volatilise en silence.
            # Une panne de base ne doit JAMAIS faire échouer un job déjà payé —
            # on journalise l'incident et on continue.
            try:
                await MS.record_created(tid, "openapi/v1/image-to-3d", payload)
            except Exception:
                logger.exception(f"cards/forge3d: tache meshy {tid} non "
                                 "journalisee (le job continue)")
            periode = 0.05 if MS.mock_enabled() else MESH3D_POLL_S
            budget = time.monotonic() + MESH3D_TIMEOUT_S
            echecs = 0
            while True:
                # I1 : un blip réseau ne tue pas un job payé de vingt minutes.
                # Les reprises sont BORNÉES et vivent DANS le budget global :
                # au-delà, l'échec porte le message littéral du dernier essai.
                try:
                    task = await MS.get_task("openapi/v1/image-to-3d", tid)
                    echecs = 0
                except Exception as e:
                    echecs += 1
                    if echecs > MESH3D_POLL_RETRIES or time.monotonic() > budget:
                        raise
                    await avance(
                        f"Meshy (reprise {echecs}/{MESH3D_POLL_RETRIES}) : "
                        f"{_panne(e)}",
                        max(30, int(_num(job.get("progress"), 30, 0, 95))))
                    await asyncio.sleep(min(periode * 2 ** echecs, 30.0))
                    continue
                statut = str(task.get("status") or "")
                # 100 % est RÉSERVÉ aux fichiers arrivés sur disque : un moteur
                # qui se dit fini n'a encore rien livré ICI.
                await avance(f"Meshy {statut}",
                             max(30, int(_num(task.get("progress"), 0, 0, 95))))
                if statut == "SUCCEEDED":
                    break
                if statut in ("FAILED", "CANCELED"):
                    err = task.get("task_error")
                    msg = err.get("message") if isinstance(err, dict) else None
                    raise RuntimeError(f"meshy: {msg or f'tâche {statut}'}")
                if time.monotonic() > budget:
                    raise RuntimeError(
                        "meshy: délai dépassé "
                        f"({int(MESH3D_TIMEOUT_S // 60)} min)")
                await asyncio.sleep(periode)

            # I2 (suite) : l'état terminal entre au journal partagé. Effet de
            # bord ASSUMÉ — `record_state` déclenche le rapatriement de fond de
            # meshy_service dans outputs/meshy3d/<id>/ EN PLUS du nôtre dans le
            # nœud : c'est le filet de sécurité VOULU (les URL Meshy expirent,
            # un binaire payé ne doit pas dépendre d'un seul dossier), pas un
            # doublon accidentel.
            try:
                await MS.record_state(task, "openapi/v1/image-to-3d")
            except Exception:
                logger.exception(f"cards/forge3d: etat de la tache meshy {tid} "
                                 "non journalise (le job continue)")
            urls = task.get("model_urls")
            urls = urls if isinstance(urls, dict) else {}
            if not urls.get("glb"):
                raise RuntimeError(
                    "meshy: aucun GLB dans la réponse (formats livrés : "
                    f"{sorted(urls) or 'aucun'})")
            await avance("Rapatriement", 92)
            await _mesh3d_rapatrie(urls["glb"], d / "model.glb")
            if task.get("thumbnail_url"):
                await _mesh3d_rapatrie(task["thumbnail_url"], d / "preview.png")
            # M3 : la boucle EXTERNE est bornée elle aussi. Sur une réponse
            # LÉGITIME, cette tranche ne change rien — le compteur de la boucle
            # interne plafonne déjà les fichiers écrits, et aucun test ne peut
            # donc la distinguer de son absence. Elle est de la même famille
            # que `_GRAPH_ITER_MAX` plus haut : une borne ANTI-GEL, là pour
            # qu'une réponse hostile à un million d'entrées ne fasse pas tourner
            # la boucle d'évènements dans le vide.
            for i, t in enumerate((task.get("texture_urls")
                                   or [])[:MESH3D_TEXTURES_MAX]):
                if not isinstance(t, dict):
                    continue
                for genre, u in t.items():
                    if len(textures) >= MESH3D_TEXTURES_MAX:
                        break
                    if not isinstance(u, str) or not u:
                        continue
                    nom = re.sub(r"[^A-Za-z0-9._-]", "_",
                                 f"{i}_{genre}")[:40] + ".png"
                    await _mesh3d_rapatrie(u, d / "textures" / nom)
                    textures.append(f"textures/{nom}")
            # la SEULE vérité comptable est ce que le fournisseur a débité
            consommes = int(_num(task.get("consumed_credits"), 0, 0, 10 ** 7))

        # ── `closed`, mesuré UNE fois — borne sur la TAILLE avant de lire ───
        glb = d / "model.glb"
        if not glb.is_file():
            raise RuntimeError(f"{engine}: aucun model.glb ramené par le moteur")
        await avance("Mesure", 95)
        taille = glb.stat().st_size
        if taille > MAX_EXT_GLB_BYTES:
            # Le fichier est DÉJÀ sur le disque (c'est la couture de
            # téléchargement qui l'y a mis) et il est PAYÉ : refuser ne le
            # récupérerait pas, ça ne ferait que le rendre inutilisable. On
            # dégrade donc comme pour un maillage trop dense — mesure refusée,
            # motif nommé, artefact conservé. La borne, elle, garde tout son
            # mordant là où elle peut encore agir : `_mesh3d_rapatrie`, qui
            # décide s'il ÉCRIT ou non les octets qu'il vient de recevoir.
            closed, note, tris = None, (
                f"fermeture non mesurée : GLB trop lourd ({taille} o, "
                f"plafond {MAX_EXT_GLB_BYTES} o)"), 0
        else:
            octets = await asyncio.to_thread(glb.read_bytes)
            closed, note, tris = await asyncio.to_thread(_mesh3d_closed, octets)

        files = {"glb": "model.glb"}
        if (d / "preview.png").is_file():
            files["preview"] = "preview.png"
        if textures:
            files["textures"] = textures
        job.update({"status": "served", "progress": 100, "step": "Livré",
                    "error": None, "closed": closed, "closed_note": note,
                    "triangles": tris, "bytes": taille, "files": files,
                    "finished": _iso_now()})
        if consommes is not None:
            job["consumed_credits"] = consommes
        await asyncio.to_thread(_job_write_si, did, nid, job, run_id)
    except _JobRemplace:
        # succession, pas panne : une relance a pris la main, ce runner n'a
        # rien à dire — surtout pas dans un bordereau qui ne lui appartient plus.
        logger.info(f"cards/forge3d: job mesh3d {did}/{nid} remplace par une "
                    "relance - abandon silencieux")
    except Exception as e:
        logger.exception(f"cards/forge3d: job mesh3d {did}/{nid} en echec")
        job.update({"status": "failed", "step": "Echec", "error": _panne(e),
                    "finished": _iso_now()})
        try:
            # même clôture pour l'aveu d'échec : un runner remplacé ne fait pas
            # échouer le job de son successeur.
            await asyncio.to_thread(_job_write_si, did, nid, job, run_id)
        except OSError:               # disque HS : le journal garde la trace
            logger.exception(f"cards/forge3d: echec du job {did}/{nid} "
                             "non persiste")
    finally:
        # JAMAIS l'entrée d'un autre : un runner rassis qui retirerait le
        # marqueur de son successeur ferait déclarer orphelin un job vivant.
        if _MESH3D_RUNNING.get(cle) is moi:
            _MESH3D_RUNNING.pop(cle, None)


@router.get("/mesh3d/{nid}")
async def get_mesh3d(did: str, nid: str):
    """L'état d'un job, tel qu'il est sur disque. Rend LE JOB lui-même (une
    ressource), là où les POST de la pièce rendent une enveloppe nommée par ce
    qu'ils viennent de produire (`layers`, `artifact`, `preview`, `job`).

    Un `queued`/`running` SANS tâche vivante dans ce processus est un orphelin
    de redémarrage : il est réécrit en `failed` NOMMÉ et PERSISTÉ — sans quoi
    l'écran repolluerait « en cours » à chaque rechargement, pour toujours."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    if not _NID_RE.match(nid or ""):
        raise HTTPException(400, "Identifiant de noeud invalide")
    job = await asyncio.to_thread(_job_read, did, nid)
    if job is None:
        raise HTTPException(404, f"aucun job sur ce noeud ({nid})")
    if job.get("status") in ("queued", "running") and not _mesh3d_vivant(did, nid):
        job.update({"status": "failed", "step": "Interrompu",
                    "error": "interrompu (aucune tache vivante) - "
                             "relancer le noeud",
                    # l'aveu est DÉFINITIF : un runner en retard ne peut plus
                    # le contredire — sa clôture échoue et il abandonne sans
                    # dépenser.
                    "run_id": None,
                    "finished": _iso_now()})
        try:
            await asyncio.to_thread(_job_write, did, nid, job)
        except OSError:
            logger.exception(f"cards/forge3d: orphelin {did}/{nid} non persiste")
    return job


# ── L'APERCU D'UN SEUL NOEUD (Task 1, 2c) — le vrai 3D d'UN element, borne ──
# `POST /node-preview` sert l'inspecteur unique du canvas (spec §5.6 point 4) :
# selectionner un noeud montre son GLB REEL, sans construire tout l'artefact.
# Reponse EPHEMERE (jamais ecrite sur disque), tout le travail lourd en
# to_thread, jamais un 500 — meme doctrine que build3d/mesh3d ci-dessus.
#
# LE SOUS-GRAPHE SYNTHETIQUE et son id hors alphabet vivent dans
# forge3d_apercu.py (`_sous_graphe_apercu`, `_PREVIEW_ASM_ID`) : la ROUTE reste
# ici, la REGLE est la-bas, avec les phrases d'aveu qu'elle produit.

def _apercu_mesh3d(did: str, nid: str) -> Path:
    """Le CHEMIN du GLB d'un noeud mesh3d SERVI — JAMAIS ses octets : cette
    fonction ne LIT PAS le fichier, `FileResponse` le sert en flux au moment
    de l'envoi (CF2, revue 2c) — un clic dans l'inspecteur ne doit pas
    charger tout le GLB en RAM avant de commencer a repondre.

    Les trois refus communs (job non servi, nom de fichier invalide, fichier
    disparu) viennent de `_glb_servi_path` — meme garde, meme formulation que
    `_element_externe` (409 « n'a pas servi »). PAS son controle de
    carte-source (M4) : la question de l'inspecteur est « qu'a produit CE
    noeud », jamais « ce noeud convient-il a la carte en cours d'edition » —
    la carte n'entre pas dans cette question-la, seul `build3d` (qui, lui,
    FUSIONNE ce GLB dans un artefact precis) a besoin d'y repondre.

    La borne de poids, elle, est PROPRE a l'inspecteur
    (`MAX_APERCU_GLB_BYTES`, applique par `_borne_apercu_glb` dans le
    sidecar — PAS `MAX_EXT_GLB_BYTES`, qui borne une fusion en memoire, un
    danger different).

    M6 (revue) : le TRS eventuellement chaine sur ce noeud (matiere,
    placement) n'est PAS applique ici, a la difference de `plane`/`relief`
    (qui, eux, composent leur chaine via `_element_local`) — l'inspecteur
    montre le noeud BRUT tel que le moteur l'a rendu ; c'est `build3d`
    (`_fit_external`) qui compose le placement de l'utilisateur au moment de
    fusionner le GLB dans l'artefact. Incoherence CONNUE et deliberee : le
    jour ou l'inspecteur doit montrer le placement pour un mesh3d aussi, il
    faudra reconstruire une scene (comme pour plane/relief) au lieu de
    streamer le GLB brut — un chantier a part, pas un correctif ici."""
    job, p_glb = _glb_servi_path(did, nid)
    return _borne_apercu_glb(job, p_glb, nid, MAX_APERCU_GLB_BYTES)


@router.post("/node-preview")
async def post_node_preview(did: str, body: dict | None = None):
    """Le GLB d'UN SEUL element du graphe — l'inspecteur partage du canvas
    (spec §5.6 point 4). `plane`/`relief` : le sous-graphe SYNTHETIQUE est
    resolu par `_sous_graphe_apercu` (forge3d_apercu.py, le MEME resolveur
    que build3d) et l'element construit par `_element_local` (la MEME fonction
    que la boucle de build3d) — l'apercu montre l'option DEJA choisie sur ce
    noeud, meme si sa chaine ne rejoint pas encore un assemble reel. Grille de
    relief PLAFONNEE a `RELIEF_GRID_PREVIEW` AVANT resolution. `mesh3d` : le
    GLB du job SERVI, en flux (`_apercu_mesh3d`, `FileResponse`). Tout autre
    kind : refus nomme.

    I1 (revue) : AUCUN aveu ne s'evapore — les noeuds ecartes de CETTE
    resolution (source surnumeraire, maillon surnumeraire, ce que le
    resolveur lui-meme ecarte, ce que `_habille` n'a pas su habiller) sont
    tous JOINTS dans `extras["ignored"]` du GLB rendu : le schema
    `PREVIEW_SCHEMA` (PAS `ARTIFACT_SCHEMA`, M5 — un apercu ephemere ne
    revendique pas le schema d'un artefact durable) promet la meme chose que
    `artifact@1` : rien n'est tu.

    AUCUNE ecriture disque : cette reponse est EPHEMERE, contrairement a
    build3d qui livre un artefact durable."""
    from .core import read_deck, geom_of
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    body = body if isinstance(body, dict) else {}
    card_label = f"c{_card_idx(body.get('card')) + 1:02d}"
    graph = clean_graph(body.get("graph"))
    nid = str(body.get("nid") or "")
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    node = nodes_by_id.get(nid)
    if node is None:
        raise HTTPException(400, f"noeud {nid} absent du graphe")
    kind = node["kind"]
    if kind not in ("plane", "relief", "mesh3d", "extrude"):
        raise HTTPException(400, f"noeud non prévisualisable : {kind}")

    if kind == "mesh3d":
        if not _NID_RE.match(nid or ""):
            raise HTTPException(400, "Identifiant de noeud invalide")
        try:
            p_glb = await asyncio.to_thread(_apercu_mesh3d, did, nid)
        except HTTPException:
            raise
        except ModuleNotFoundError as e:       # pragma: no cover - env casse
            raise HTTPException(503, f"Module requis absent : {e}")
        except Exception as e:
            logger.exception("cards/forge3d: apercu de noeud impossible")
            raise HTTPException(500, f"Apercu de noeud impossible : {e}")
        # CF2 : FileResponse SERT en flux (jamais chargé en mémoire ici) —
        # les octets restent byte-identiques au fichier sur disque.
        #
        # N3 — LA FENÊTRE TOCTOU, DITE (re-revue tâche 1). `_apercu_mesh3d` a
        # vérifié que le fichier EXISTE ; `FileResponse`, lui, ne l'ouvre qu'à
        # l'ENVOI, après cette ligne. Une relance concurrente du même nœud
        # `rmtree` son dossier ENTIER : entre les deux, le fichier peut avoir
        # disparu, et starlette lève alors RuntimeError — un 500, malgré la
        # doctrine. C'est le PRIX ACCEPTÉ du streaming : lire 32 Mio en RAM
        # pour fermer cette fenêtre coûterait bien plus cher que le 500 d'une
        # course rarissime (relancer un nœud PENDANT qu'on le regarde), et le
        # remède existe déjà côté écran — re-cliquer le nœud. Les deux autres
        # routes de ce fichier qui servaient des octets ont fait le choix
        # INVERSE, et pour la bonne raison : leurs fichiers sont des vignettes
        # (`get_material_thumb` M3, `get_node_file` M2), pas des GLB.
        return FileResponse(p_glb, media_type="model/gltf-binary",
                            headers={"Cache-Control": "no-store"})

    # ── plane/relief : sous-graphe synthetique, le MEME resolveur que
    #    build3d — AUCUN aveu de la resolution ne s'evapore (I1) ──────────
    ignored: list[dict] = []
    if kind == "extrude":
        # UNE EXTRUSION N'A PAS DE SOUS-GRAPHE À SYNTHÉTISER : sa forme vient
        # du format, et `_sous_graphe_apercu` exigerait d'elle une couche
        # source qu'elle n'aura jamais. Sa chaîne AVAL, elle, se descend par la
        # MÊME primitive que partout — et comme ailleurs dans l'inspecteur,
        # l'aperçu montre l'option DÉJÀ posée sur le nœud même si la chaîne ne
        # rejoint pas encore un assemble.
        outgoing: dict[str, list[str]] = {}
        for e in graph["edges"]:
            outgoing.setdefault(e["from"], []).append(e["to"])
        mat_n, trs_n, _relie = _chaine_aval(nid, nodes_by_id, outgoing,
                                            ignored)
        ch = {"proc": node, "layer": None, "mat": mat_n, "trs": trs_n}
    else:
        ch = _sous_graphe_apercu(graph, nid, node, RELIEF_GRID_PREVIEW,
                                 ignored)
    g = geom_of(doc)

    def work() -> bytes:
        if ch["layer"] is None:
            el = _element_extrude(ch["proc"], _nom_extrude(ch["proc"]),
                                  ch["mat"], ch["trs"], g, ignored, did)
            return write_scene_glb(
                [el], name="apercu",
                extras={"schema": PREVIEW_SCHEMA, "preview": True,
                        "ignored": ignored})
        if ch["layer"]["side"] == CAPTURE_SIDE:
            # MÊME CONTRAT QUE LA CONSTRUCTION (D7) : l'inspecteur vérifie le
            # manifeste importé AVANT de lire le fichier. Sans ce contrôle,
            # une couche importée absente tomberait sur le refus GÉNÉRIQUE du
            # sidecar (« exporte les couches d'abord (POST /layers) ») — une
            # consigne juste pour les peintres et fausse pour un import.
            _preuve_capture(did, _out_dir(did), card_label, ch["layer"],
                            _lire_manifeste(_out_dir(did), card_label,
                                            CAPTURE_SIDE), g, ignored)
        el = _element_local(
            _out_dir(did), ch["proc"], ch["layer"],
            _nom_element(ch["layer"]), ch["mat"], ch["trs"],
            card_label, g, ignored, did)
        # APERÇU == FICHIER (barre de qualité §6.2bis :443) : le Sceau à
        # portée 3D habille l'élément ICI AUSSI, sinon l'inspecteur montrerait
        # un cadre nu que la construction livrerait iridescent. Il n'y a pas
        # de bordereau dans un aperçu — l'aveu de portée appartient au build,
        # qui écrit un livrable ; ce qui est PERDU, lui, part dans `ignored`,
        # que l'aperçu porte déjà dans ses extras.
        _scelle(el, ch["layer"], ch["mat"], _sceau_du_doc(doc), ignored)
        # I1 : `ignored` porte ICI tout ce qui a ete ecarte — les entrees
        # d'avant l'appel (source/maillon surnumeraire, sub_ignores) ET
        # celles que `_element_local`/`_habille` viennent d'y ajouter
        # (matiere introuvable, finition ignoree).
        return write_scene_glb(
            [el], name="apercu",
            extras={"schema": PREVIEW_SCHEMA, "preview": True,
                    "ignored": ignored})

    try:
        glb = await asyncio.to_thread(work)
    except HTTPException:
        raise
    except ModuleNotFoundError as e:           # pragma: no cover - env casse
        raise HTTPException(503, f"Module requis absent : {e}")
    except ValueError as e:
        logger.warning(f"cards/forge3d: apercu de noeud refuse : {_panne(e)}")
        raise HTTPException(409, _panne(e))
    except Exception as e:
        logger.exception("cards/forge3d: apercu de noeud impossible")
        raise HTTPException(500, f"Apercu de noeud impossible : {e}")
    return Response(content=glb, media_type="model/gltf-binary",
                    headers={"Cache-Control": "no-store"})


# `no-store` sur les REFUS aussi, pas seulement sur les 200 (vignettes de
# matiere et apercus de noeud). Ces deux routes servent des octets qui CHANGENT
# sous le meme chemin : « matiere sans vignette » devient « vignette servie »
# des qu'on la capture, « aucun apercu sur ce noeud » des que le job rapatrie
# son PNG. Un 404 mis en cache par heuristique laisserait l'ecran sur l'aplat
# de couleur (ou le pictogramme par defaut) alors que le fichier est la.
_NO_STORE = {"Cache-Control": "no-store"}


@router.get("/material-thumb/{mid}")
async def get_material_thumb(did: str, mid: str):
    """La vignette de boutique d'une matiere, servie PAR PROVENANCE — le fond
    du corps de noeud `material` (Task 3, 2c). `mid` valide AVANT toute
    lecture disque — aucun chemin n'est JAMAIS construit sur l'entree brute,
    le containment vient de `material_store.material_dir` (règle 8 :
    material_store est un service TRANSVERSE, deja consomme par `get_info`
    ci-dessus, pas une piece du lab).

    I4 (revue) : GATE sur `material_store.thumb_is_current` — LA MEME
    doctrine que la boutique elle-meme (`read_material()["thumb"]`), pas une
    exemption pour cette pastille 2D. Une vignette d'avant MESH_VERSION 2
    rendait la matiere EN MIROIR (voir la docstring de `thumb_is_current`) :
    la servir telle quelle remettrait ce defaut sur le canvas. PERIMEE vaut
    ABSENTE (404 nomme) — l'ecran retombe alors sur un aplat de couleur, comme
    la boutique le fait deja pour sa propre carte.

    M3 (revue) : les octets sont LUS ICI, dans `work()`, jamais servis par
    `FileResponse` — celui-ci RE-STAT le fichier au moment de l'ENVOI, APRÈS
    ce to_thread : une suppression concurrente entre ce controle et l'envoi y
    leve RuntimeError, donc un 500 (le meme TOCTOU que `get_file` evite deja
    en lisant les octets avant de repondre). Jamais-500."""
    from .core import read_deck
    from .contract import is_valid_did
    from app.services import material_store as MSTORE
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide",
                            headers=dict(_NO_STORE))
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable", headers=dict(_NO_STORE))
    if not MSTORE.is_valid_mid(mid):
        raise HTTPException(400, "Identifiant de matière invalide",
                            headers=dict(_NO_STORE))

    def work() -> bytes | None:
        try:
            d = MSTORE.material_dir(mid)
        except ValueError:
            return None
        if not MSTORE.thumb_is_current(d):
            return None
        try:
            return (d / "thumb.png").read_bytes()
        except OSError:
            return None

    data = await asyncio.to_thread(work)
    if data is None:
        raise HTTPException(404, f"matière sans vignette : {mid}",
                            headers=dict(_NO_STORE))
    return Response(content=data, media_type="image/png",
                    headers=dict(_NO_STORE))


# ── L'APERCU D'UN NOEUD, SERVI PAR PROVENANCE (Task 5, 2c) ─────────────────
# LISTE BLANCHE, PAS UN MOTIF — et c'est la seule chose qui compte ici. Le
# dossier durable d'un noeud (`nodes/{nid}/`) porte `job.json` (l'etat interne :
# `run_id`, credits consommes, motif d'echec), `model.glb` et les TEXTURES
# rapatriees du moteur, c'est-a-dire des octets PAYES. Seul l'apercu est un
# affichage public. Un motif de nom — meme celui de `get_file`,
# `^[A-Za-z0-9._-]{1,90}$` — aurait ouvert le dossier ENTIER a la premiere
# lettre pres ; une liste, elle, ne peut pas deriver : ajouter un fichier au
# dossier n'ajoute rien a la surface publique tant que personne ne l'ecrit ici.
# La table porte AUSSI le type de contenu : le jour ou un second nom s'ajoute,
# son media-type s'ajoute avec lui, jamais deduit d'une extension a cote.
_NODE_FILES_PUBLICS = {"preview.png": "image/png"}

# LE PLAFOND DE LECTURE. Les octets sont chargés EN RAM ici (l'écart assumé
# expliqué dans la docstring ci-dessous), et le chemin qui ECRIT ce fichier —
# le téléchargement de l'aperçu chez le fournisseur, dans `_run_mesh3d` — ne
# le borne pas : une réponse de moteur inattendue devient donc une lecture
# illimitée en mémoire, UNE PAR REQUÊTE. 4 Mio est large pour une vignette de
# job (celles de meshy pèsent quelques dizaines de Kio) et ridicule à côté des
# 32 Mio que `node-preview` refuse déjà de charger.
_NODE_FILE_MAX = 4 * 1024 * 1024

# le refus NOMMÉ de `work()` : `None` dit « absent » (404), cette sentinelle
# dit « trop lourd » (413). Un entier ou un `False` s'y confondrait avec des
# octets vides ; une identité, non.
_NODE_FILE_TROP_LOURD = object()


@router.get("/node-file/{nid}/{name}")
async def get_node_file(did: str, nid: str, name: str):
    """La vignette d'apercu d'un noeud moteur, telle que le job l'a rapatriee.

    MANQUE REMONTE EN TASK 3, OUVERT ICI PAR DECISION DU CONTROLEUR : un job
    meshy ecrit bien `nodes/{nid}/preview.png` (`_run_mesh3d`), mais aucune
    route ne le servait — `GET /file/{name}` interdit le separateur, donc rien
    sous `nodes/` n'etait atteignable. L'ecran prenait la branche « a defaut »
    du plan (pictogramme moteur + etat lu) plutot que d'ouvrir une surface
    d'API en douce.

    CONFINEMENT : `_NID_RE` d'abord (il refuse le separateur ET les noms qui ne
    sont que des points — `..` n'est pas un nom de dossier, c'est un SAUT),
    puis `_node_dir`, qui re-verifie le parent apres `resolve()`. Ceinture et
    bretelles, la doctrine de `contract.deck_dir`.

    LES OCTETS SONT LUS ICI, jamais servis par `FileResponse` — ECART ASSUME
    au point impose du plan, pour la raison DEJA ecrite deux fonctions plus
    haut (`get_material_thumb`, M3) et dans `get_file` : `FileResponse`
    RE-STAT le fichier au moment de l'ENVOI, donc APRES ce controle. Ici la
    fenetre n'est pas theorique — le dossier d'un noeud est `rmtree`
    INTEGRALEMENT a chaque relance (`post_mesh3d`), donc une relance
    concurrente entre le controle et l'envoi ferait lever RuntimeError, c'est-
    a-dire un 500 sur la doctrine « jamais-500 » de cette piece. Et le motif
    de `node-preview` (qui, lui, GARDE `FileResponse`) ne s'applique pas : la
    il s'agit d'un GLB de 32 Mio qu'on refuse de charger en RAM avant de
    repondre ; ici, d'une vignette. Deux dangers differents, deux reponses
    differentes."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide",
                            headers=dict(_NO_STORE))
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable", headers=dict(_NO_STORE))
    if not _NID_RE.match(nid or ""):
        raise HTTPException(400, "Identifiant de noeud invalide",
                            headers=dict(_NO_STORE))
    media = _NODE_FILES_PUBLICS.get(name or "")
    if media is None:
        raise HTTPException(
            400, f"fichier non public : {name!r} — seul l'aperçu du noeud est "
                 f"servi ({', '.join(sorted(_NODE_FILES_PUBLICS))})",
            headers=dict(_NO_STORE))

    def work():
        try:
            p = _node_dir(did, nid) / name
        except HTTPException:
            return None
        if not p.is_file():
            return None
        # LE POIDS SE MESURE AVANT LA LECTURE, pas apres : une borne qui lit
        # d'abord ne borne rien. `stat` est deja fait par `is_file` — un de
        # plus coute une syscall et ferme la porte.
        try:
            taille = p.stat().st_size
        except OSError:
            return None
        if taille > _NODE_FILE_MAX:
            return _NODE_FILE_TROP_LOURD
        try:
            return p.read_bytes()
        except OSError:
            return None

    data = await asyncio.to_thread(work)
    if data is _NODE_FILE_TROP_LOURD:
        raise HTTPException(
            413, f"aperçu trop lourd pour être servi ({nid}) : au-delà de "
                 f"{_NODE_FILE_MAX // (1024 * 1024)} Mio, ce n'est plus une "
                 f"vignette — relance le noeud pour en réécrire une.",
            headers=dict(_NO_STORE))
    if data is None:
        raise HTTPException(404, f"aucun aperçu sur ce noeud ({nid})",
                            headers=dict(_NO_STORE))
    # `no-store` : un apercu CHANGE sous le meme nom (une relance le reecrit
    # apres avoir efface le dossier) — le figer en cache ferait afficher le
    # modele d'avant a cote de l'etat d'apres.
    return Response(content=data, media_type=media, headers=dict(_NO_STORE))


@router.post("/preview/{art}")
async def post_preview(did: str, art: str, request: Request):
    """Reçoit la capture d'aperçu du navigateur (model-viewer `.toBlob()`) et
    l'écrit telle quelle — RIEN de la carte n'est rendu au serveur (patron du
    domaine). Corps brut, borné, PNG vérifié : mêmes gardes que
    gltf.py:post_atlas (règle 8, copie locale)."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    if not _ART_NAME_RE.match(art or ""):
        raise HTTPException(400, "Nom d'artefact invalide")
    data = await request.body()
    if not data:
        raise HTTPException(400, "Corps vide : le PNG d'apercu est attendu tel quel")
    if len(data) > MAX_PREVIEW_BYTES:
        raise HTTPException(
            413, f"apercu trop lourd ({len(data)} o, maximum "
                 f"{MAX_PREVIEW_BYTES} o)")
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise HTTPException(400, "PNG attendu (signature absente)")

    def work() -> dict:
        # `_open_png` decode VRAIMENT le corps (pas seulement sa signature
        # magique, deja verifiee ci-dessus en garde rapide) : un PNG tronque
        # ou corrompu derriere un en-tete valide est aussi refuse ici, pas
        # seulement ecrit tel quel en esperant qu'il soit bon (revue,
        # dedoublonnage de `_ouvre` -> `_open_png`, patron unique du fichier).
        _open_png(data, "apercu")
        out = _out_dir(did, create=True)
        name = f"{art}_preview.png"
        (out / name).write_bytes(data)
        return {"name": name, "bytes": len(data)}

    try:
        info = await asyncio.to_thread(work)
    except HTTPException:
        raise
    except OSError as e:
        logger.exception("cards/forge3d: ecriture de l'apercu impossible")
        raise HTTPException(500, f"Ecriture de l'apercu impossible : {e}")
    return {"preview": info}


# ── LA BIBLIOTHÈQUE — PUBLIER L'ARTEFACT (Task 6, 2c) ──────────────────────
# Spec §5.6 point 7. Le pari, et il tient en une phrase : AUCUNE route neuve
# côté Bibliothèque. Les routes `/api/assets/3d/{short}/{glb,preview,manifest}`
# lisent `outputs/assets3d/{short}/model.{fmt}` et `preview.png` — on écrit
# donc CETTE disposition-là, et le viewer, le téléchargement, les favoris et
# « Optimiser » marchent sans une ligne de plus. Le seul changement d'écran est
# un patch bundle de DEUX filtres (`asset3d` -> `asset3d||card3d`).
#
# LE PROVIDER EST `card3d`, PAS `asset3d` — provenance HONNÊTE : ces octets ne
# viennent pas d'un moteur image->3D payant, ils viennent d'ici. `kind` reste
# « asset3d » côté écran (c'est un objet 3D, pas une catégorie de fabricant) :
# la distinction est la même que celle entre « ce que c'est » et « d'où ça
# vient ».
NAMESPACE_CARD3D = uuid.UUID("ac928da5-740b-48d6-8913-93a83055aeeb")

# CE QUE LE DOSSIER `{short}` A LE DROIT DE SERVIR, et donc ce que chaque
# publication doit RÉTABLIR EN ENTIER (S2, revue adverse). Les deux derniers ne
# sont jamais écrits ici : c'est « Optimiser » (routes.py, chantier 10a) qui
# les pose à côté du modèle — raison de plus pour les balayer, ils décrivent un
# maillage qui vient d'être remplacé.
_LIBRARY_SERVIS = ("preview.png", "shot_0.png", "metadata.json",
                   "model.opt.glb", "optimize.json")


def _copie_servie(src: Path, dest: Path) -> None:
    """Une copie vers un chemin PUBLIQUEMENT SERVI : écrite à côté, puis
    PROMUE par `os.replace` — jamais par-dessus le fichier que quelqu'un est en
    train de lire (M3, revue adverse).

    `copyfile` tronque puis réécrit EN PLACE : un `FileResponse` déjà en cours
    de streaming sur `model.glb` lit alors la fin du nouveau fichier après le
    début de l'ancien — un GLB ÉPISSÉ, à un octet près valide, mesuré par la
    revue. `os.replace`, lui, ne touche pas l'inode ouvert : le lecteur en
    cours finit tranquillement l'ancien, les suivants ouvrent le nouveau.

    Sous Windows, `os.replace` sur une cible OUVERTE lève `PermissionError` —
    exactement la course que `_job_write` retente déjà (mêmes bornes,
    `_JOB_IO_ESSAIS` / `_JOB_IO_PAUSE_S`, mêmes raisons : passager, sans
    rapport avec une vraie panne disque). Au-delà des essais, l'erreur repart
    telle quelle : un fichier vraiment verrouillé reste une panne, et l'aveu
    doit le dire."""
    # LE TEMPORAIRE NE COMMENCE PAS PAR `model.` — et ce n'est pas un détail :
    # la route `manifest` de la Bibliothèque déclare un FORMAT pour tout
    # fichier dont le nom commence par `model.` (routes.py). Un
    # `model.glb.tmp`, même le temps d'un `os.replace`, se serait annoncé
    # comme un format « glb.tmp » téléchargeable. Le point de tête le sort de
    # toutes les listes publiques du dossier.
    tmp = dest.with_name("." + dest.name + ".tmp")
    shutil.copyfile(src, tmp)
    for reste in range(_JOB_IO_ESSAIS - 1, -1, -1):
        try:
            os.replace(tmp, dest)
            return
        except PermissionError:
            if not reste:
                # le temporaire ne reste PAS derrière : un fichier à moitié
                # promu dans un dossier public est du bruit que personne ne
                # sait lire.
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(_JOB_IO_PAUSE_S)


def _library_job_id(did: str, art: str) -> tuple[str, str]:
    """`(job_id, short)` DÉRIVÉS du couple (deck, artefact) — l'idempotence
    est une propriété de CONSTRUCTION, pas une vérification : re-publier ne
    peut pas fabriquer un second objet, même si la base a été vidée entre les
    deux. Le couple ENTIER entre dans la dérivation : deux artefacts d'un même
    deck sont deux objets (publier la carte 2 n'écrase pas la carte 1).

    `short` = les 8 premiers du `job_id`, parce que c'est CE calcul que
    l'écran fait déjà (`z.job_id.slice(0,8)` dans le bundle) et que
    `_delete_provider_output_dir` fait aussi côté serveur (`job.id[:8]`) : une
    seule règle, pas trois. Exposition assumée, identique à celle d'`asset3d`
    (qui coupe un uuid4 au même endroit) : 32 bits de dossier, donc une
    collision de dossier reste possible entre deux objets — l'accepter ici et
    pas là n'aurait aucun sens, c'est la MÊME disposition de fichiers."""
    u = uuid.uuid5(NAMESPACE_CARD3D, f"{did}/{art}")
    return str(u), u.hex[:8]


@router.post("/library/{art}")
async def post_library(did: str, art: str):
    """« Publier dans la Bibliothèque » : copie l'artefact CONSTRUIT dans
    `outputs/assets3d/{short}/` et pose (ou met à jour) son JobRecord
    `provider="card3d"`. Rend `{job_id, short, provider}`.

    RIEN N'EST CONSTRUIT ICI : publier n'est pas fabriquer. Sans `{art}.glb`
    sur disque, c'est un 409 NOMMÉ — pas un build implicite qui dépenserait
    du temps (voire des crédits, si la chaîne portait un moteur) sur un clic
    dont ce n'était pas la promesse.

    ÉCART ASSUMÉ AU PLAN — `final_video_path` reste VIDE. Le plan y posait le
    chemin du GLB copié ; trois écrans de l'app listent les rendus par
    `status==="done" && final_video_path && provider!=="asset3d" &&
    provider!=="sprite2d"` (l'onglet « rendus » de la Bibliothèque, le
    sélecteur « Existing render » du Studio, le Scheduler). La carte y serait
    apparue comme une VIDÉO, avec un lecteur incapable de l'ouvrir. Un GLB
    n'est pas un rendu vidéo : la colonne reste vide, et les trois écrans
    l'ignorent par construction — sans un seul filtre de plus à patcher."""
    from .core import read_deck
    from .contract import is_valid_did
    from app.config import settings
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    if not _ART_NAME_RE.match(art or ""):
        raise HTTPException(400, "Nom d'artefact invalide")
    job_id, short = _library_job_id(did, art)
    doc_name = doc.get("name") or did
    titre = f"Carte 3D · {doc_name} · {art}"

    # ── M8 : LE DOSSIER `{short}` PEUT DÉJÀ APPARTENIR À QUELQU'UN ─────────
    # `short` fait 32 bits, et `asset3d` coupe un uuid4 au MÊME endroit :
    # deux objets peuvent viser le même dossier. Sans cette garde, publier
    # ÉCRASERAIT `outputs/assets3d/{short}/model.glb` — c'est-à-dire un
    # maillage PAYÉ chez un moteur, définitivement, sans un mot. Et le défaut
    # ne serait pas une malchance ponctuelle : notre id est DÉTERMINISTE, donc
    # chaque re-publication de cette carte frapperait la MÊME victime.
    # Le contrôle tombe AVANT le premier octet écrit — un refus nommé coûte un
    # renommage d'artefact, un écrasement coûte le maillage.
    from sqlalchemy import select as _select
    from app.services.storage import (JobRecord as _JR,
                                      async_session_factory as _sf)
    async with _sf() as s0:
        # PRÉFIXE, pas un balayage de table : la colonne est la clé primaire,
        # et `LIKE 'xxxxxxxx%'` sur une clé texte reste une requête bornée. La
        # table des jobs est de toute façon petite (l'écran en poll 50 à la
        # fois) — mais charger la table pour poser une question à un seul
        # enregistrement serait un mauvais patron à laisser derrière soi.
        autre = (await s0.execute(
            _select(_JR.id, _JR.provider).where(_JR.id.like(f"{short}%"))
        )).all()
    for autre_id, autre_prov in autre:
        if autre_id != job_id:
            raise HTTPException(
                409, f"le dossier {short} appartient déjà à un autre objet 3D "
                     f"(job {autre_id}, provider {autre_prov or 'inconnu'}) : "
                     f"publier écraserait ses fichiers — renomme l'artefact "
                     f"« {art} » et republie")

    def work() -> dict:
        out = _out_dir(did)
        src_glb = out / f"{art}.glb"
        if not src_glb.is_file():
            raise HTTPException(
                409, f"construis l'artefact d'abord : {art}.glb absent "
                     f"(bouton « Construire », nœud artefact)")
        dest = settings.outputs_path / "assets3d" / short
        dest.mkdir(parents=True, exist_ok=True)
        # `model.glb` : LE NOM QUE LA ROUTE EXISTANTE LIT (`model.{fmt}`), pas
        # le nôtre. Publier, c'est parler la langue de la Bibliothèque.
        _copie_servie(src_glb, dest / "model.glb")
        fichiers = ["model.glb"]
        # L'APERÇU EST FACULTATIF, et son absence est TOLÉRÉE : « figer
        # l'aperçu » peut n'avoir jamais tourné. La vignette de la
        # Bibliothèque retombe alors sur son propre repli — pas une erreur,
        # un état.
        src_ap = out / f"{art}_preview.png"
        if src_ap.is_file():
            _copie_servie(src_ap, dest / "preview.png")
            fichiers.append("preview.png")
            # ── SOUS LES DEUX NOMS (trouvaille T7, navigateur réel) ────────
            # La tuile 3D de la Bibliothèque pose `/preview` en src PRIMAIRE
            # et retombe UNE FOIS sur `/shot/0` par `onError` (le bundle garde
            # ce repli unique dans `dataset.f`). Le second nom n'existait dans
            # aucun de nos dossiers : le repli tombait donc dans le vide — et
            # avec lui deux choses qui, elles, ne sont PAS cosmétiques : la
            # liste `shots` du manifeste, et « copier le shot dans la
            # bibliothèque d'images » (`/shot/{i}/save`), qui rend une carte
            # publiée réutilisable comme source d'image.
            # LES MÊMES OCTETS, pas une seconde capture : c'est UNE image, à
            # deux endroits où l'écran sait la chercher.
            _copie_servie(src_ap, dest / "shot_0.png")
            fichiers.append("shot_0.png")
        # LE METADATA VOYAGE AUSSI, et c'est un bonus honnête : aucune route
        # ne le sert aujourd'hui, mais la provenance de ces octets (deck,
        # carte, moteurs, schéma) reste lisible À CÔTÉ du modèle plutôt que
        # seulement dans le deck qui l'a produit.
        moteurs = None
        src_meta = out / f"{art}.metadata.json"
        if src_meta.is_file():
            _copie_servie(src_meta, dest / "metadata.json")
            fichiers.append("metadata.json")
            try:
                meta = json.loads(src_meta.read_text(encoding="utf-8"))
                # M5 (revue adverse) : `isinstance` D'ABORD, et trois
                # exceptions de plus. Un metadata bien formé JSON mais de la
                # mauvaise FORME traversait le `except` : `[1,2,3]` levait
                # AttributeError sur `.get`, `{"attributes": 5}` TypeError sur
                # l'itération — deux 500 sur un fichier qu'on ne fait que
                # RECOPIER, alors que le commentaire ci-dessous promet
                # exactement le contraire. Sondé, pas imaginé.
                #
                # C'EST LE `except` QUI TIENT LA PROMESSE, pas ce `isinstance`
                # (mesuré : retirer le test de type seul laisse la suite
                # verte, l'AttributeError retombant dans le filet élargi —
                # mutant ÉQUIVALENT, consigné plutôt que chassé). Il reste
                # parce qu'un chemin nominal ne doit pas passer par une
                # exception pour décider d'une forme : lire la forme est une
                # question, la lever une panne.
                attrs = meta.get("attributes") if isinstance(meta, dict) else None
                moteurs = next(
                    (a.get("value") for a in (attrs or [])
                     if isinstance(a, dict)
                     and a.get("trait_type") == "engines"), None)
            except (ValueError, TypeError, AttributeError, OSError,
                    UnicodeDecodeError):
                # un metadata illisible ne fait pas échouer la publication :
                # le MODÈLE est bon, c'est lui qu'on publie. La trace, elle,
                # dira simplement qu'on n'a pas su lire les moteurs.
                logger.warning(f"cards/forge3d: metadata illisible a la "
                               f"publication ({art})")
        # ── PUBLIER L'ENSEMBLE, PAS LES AJOUTS (S2, revue adverse) ─────────
        # Sans ce balayage, re-publier ne faisait qu'ÉCRASER ce qui existe :
        # un artefact reconstruit SANS figer l'aperçu (le rebuild efface le
        # PNG périmé du deck, c'est `_efface` plus haut) laissait la vignette
        # de la publication PRÉCÉDENTE servie sous le même `short` — l'image
        # d'un modèle qui n'est plus là. Même faute, plus grave, pour
        # `model.opt.glb` : la Bibliothèque propose « GLB optimisé » dès que le
        # fichier existe, et il aurait servi le maillage optimisé de l'ANCIEN
        # modèle. Le dossier `{short}` n'est pas un dépôt qui s'accumule,
        # c'est l'IMAGE de l'artefact à cette publication-ci.
        for nom in _LIBRARY_SERVIS:
            if nom not in fichiers:
                (dest / nom).unlink(missing_ok=True)
        return {"files": fichiers, "engines": moteurs,
                "bytes": src_glb.stat().st_size}

    try:
        info = await asyncio.to_thread(work)
    except HTTPException:
        raise
    except OSError as e:
        logger.exception("cards/forge3d: publication impossible")
        raise HTTPException(500, f"Publication impossible : {e}")

    from datetime import datetime
    from app.services.storage import JobRecord, async_session_factory
    from app.models.schemas import JobStatus
    # UPSERT — get puis update, sinon insert. L'id étant DÉRIVÉ, re-publier
    # tombe forcément sur la même ligne : c'est ce qui rend la publication
    # idempotente SANS clause de doublon à écrire.
    async with async_session_factory() as s:
        jr = await s.get(JobRecord, job_id)
        neuf = jr is None
        if neuf:
            jr = JobRecord(id=job_id)
            s.add(jr)
        jr.provider = "card3d"
        jr.status = JobStatus.DONE.value
        jr.progress = 100
        jr.title = titre
        jr.current_step = "Publié"
        jr.error = None
        # `image_filename` est NON NUL en base. M6 (revue adverse) : ce N'EST
        # PAS « preview.png », même si `asset3d` l'écrit. Ce nom-là PASSE le
        # contrôle d'extension du tiroir de file d'attente du bundle, qui le
        # résoudrait en `/api/images/preview.png` — c'est-à-dire une image de
        # la bibliothèque d'images SANS AUCUN RAPPORT si elle existe (et un
        # cadre cassé sinon). Un nom DÉRIVÉ, sans extension, ne peut pas être
        # pris pour un fichier d'images : il ne désigne rien, ce qui est la
        # vérité. Rien ne lit cette colonne pour l'onglet 3D — la vignette y
        # vient de `/api/assets/3d/{short}/preview`, par le short.
        jr.image_filename = f"card3d_{short}"
        jr.completed_at = datetime.utcnow()
        jr.cost_meta = json.dumps(
            {"deck": did, "deck_name": doc_name, "art": art, "job": short,
             "engines": info["engines"], "files": info["files"],
             "bytes": info["bytes"]}, ensure_ascii=False)
        await s.commit()
    logger.info(f"cards/forge3d: {'publie' if neuf else 'republie'} "
                f"{art} -> bibliotheque 3d ({short})")
    return {"job_id": job_id, "short": short, "provider": "card3d",
            "title": titre, "files": info["files"]}


@router.get("/file/{name}")
async def get_file(did: str, name: str):
    """Un livrable, tel qu'il a été construit (patron P8)."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    import re as _re
    # `fullmatch` + `\Z`, PAS `match` + `$` — CINQUIÈME occurrence du même
    # piège dans ce chantier (clôture T1-b : « toute liste blanche naît en
    # fullmatch/\Z »). En Python, `$` apparie AUSSI juste avant un saut de
    # ligne final : « artefact.glb\n », qui arrive tel quel d'une URL
    # percent-encodée `%0A`, passait ce contrôle. INERTE ici — le motif
    # n'accepte ni séparateur ni point-point, et le `\n` final ferait de toute
    # façon échouer l'ouverture du fichier — mais une liste blanche qui décide
    # d'un accès au disque ne se garde pas « par chance ».
    if not _re.fullmatch(r"[A-Za-z0-9._-]{1,90}\Z", name or ""):
        raise HTTPException(400, "Nom invalide")
    p = _out_dir(did) / name
    if not p.is_file():
        raise HTTPException(404, "Fichier inconnu")
    kind = ("model/gltf-binary" if name.endswith(".glb") else
            "model/stl" if name.endswith(".stl") else
            "application/zip" if name.endswith(".zip") else
            "image/png" if name.endswith(".png") else
            "application/json")
    return Response(p.read_bytes(), media_type=kind, headers={
        "Content-Disposition": f'attachment; filename="{p.name}"',
        "Cache-Control": "no-store"})
