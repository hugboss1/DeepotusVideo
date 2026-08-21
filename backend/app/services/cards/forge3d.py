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
from functools import reduce
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
                            write_scene_glb, _write_stl_binary,
                            read_glb, glb_scene_mesh, glb_triangle_estimate,
                            material_pngs, holo_finish, apply_fit_inplace,
                            HOLO_KINDS, HOLO_PX)

router = APIRouter()

MANIFEST_SCHEMA = "card-3d/layers-manifest@1"
ARTIFACT_SCHEMA = "card-3d/artifact@1"

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

# ── LE VOCABULAIRE DU GRAPHE — BLOC MIROIR ──────────────────────────────────
# ═══ CF-FORGE3D-NODES-BEGIN ═══
# Miroir JS dans mod-forge3d.js ; test de parité champ à champ.
# `layer`     : source — une couche du manifeste (role + side).
# `plane`     : plan texturé, GRATUIT (quad aux dimensions de la carte).
# `relief`    : dalle en relief, GRATUITE — grille déplacée par l'alpha,
#               solide FERMÉ par construction (imprimable).
# `mesh3d`    : image→3D par moteur, PAYANT (prix affiché avant).
# `material`  : matière Material Forge + finition holo sur le nœud amont.
# `transform` : position/rotation/échelle en mm de carte de l'élément amont.
# `assemble`  : fusionne les amonts en une scène.
# `artifact`  : sorties (GLB + metadata + aperçu + STL si fermé).
NODE_KINDS = [
    {"kind": "layer", "params": ["role", "side"]},
    {"kind": "plane", "params": ["depth_mm"]},
    {"kind": "relief", "params": ["depth_mm", "base_mm", "grid"]},
    {"kind": "mesh3d", "params": ["engine", "texture_prompt", "ultra"]},
    {"kind": "material", "params": ["mat", "tile_mm", "finish", "aniso"]},
    {"kind": "transform", "params": ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"]},
    {"kind": "assemble", "params": []},
    {"kind": "artifact", "params": ["name"]},
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

MATERIAL_TILE_MM = (10.0, 200.0)
# UNE seule vérité pour les finitions : les recettes vivent dans le module
# scène, l'écran en reçoit la liste par /info. « aucune » est le seul mot que
# ce fichier ajoute (l'absence de finition n'est pas une recette).
MATERIAL_FINISHES = ("aucune",) + HOLO_KINDS
TRANSFORM_XY_MM = (-100.0, 100.0)
TRANSFORM_Z_MM = (0.0, 10.0)
TRANSFORM_ROT_DEG = (-180.0, 180.0)
TRANSFORM_SCALE = (0.1, 4.0)

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
            "graph_limits": {
               "plane_depth_mm": list(PLANE_DEPTH_MM),
               "relief_depth_mm_max": RELIEF_DEPTH_MM_MAX,
               "relief_base_mm": list(RELIEF_BASE_MM),
               "relief_grid": list(RELIEF_GRID),
               "relief_grid_default": RELIEF_GRID_DEFAULT,
               "max_elements": MAX_GRAPH_ELEMENTS,
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
            "materials": [{"id": m["id"], "name": m["name"]}
                          for m in materials_raw],
            "materials_degraded": materials_degraded,
            "material_limits": {"tile_mm": list(MATERIAL_TILE_MM),
                                "finishes": list(MATERIAL_FINISHES)},
            "transform_limits": {"xy_mm": list(TRANSFORM_XY_MM),
                                 "z_mm": list(TRANSFORM_Z_MM),
                                 "rot_deg": list(TRANSFORM_ROT_DEG),
                                 "scale": list(TRANSFORM_SCALE)}}


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
    et l'arête qui visait l'un des deux devenait ambiguë entre les deux."""
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
        node = {"id": brut or f"n{i + 1}", "kind": n["kind"]}
        # resynthese SANS collision possible : "n2x" + "n2x" donnait "n2x" deux
        # fois (mesure en revue) — on suffixe jusqu'a unicite.
        while node["id"] in ids:
            node["id"] += "x"
        ids.add(node["id"])
        if n["kind"] == "layer":
            r_val = n.get("role")
            node["role"] = r_val if isinstance(r_val, str) and r_val in roles else None
            node["side"] = "back" if n.get("side") == "back" else "front"
            node["composite"] = bool(n.get("composite"))
            if node["role"] is None and not node["composite"]:
                continue                      # une source sans source n'est rien
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
            if node["mat"] is None and node["finish"] == "aucune":
                continue          # une matière sans matière ni finition n'est rien
        elif n["kind"] == "transform":
            node["x_mm"] = _num(n.get("x_mm"), 0.0, *TRANSFORM_XY_MM)
            node["y_mm"] = _num(n.get("y_mm"), 0.0, *TRANSFORM_XY_MM)
            node["z_mm"] = _num(n.get("z_mm"), 0.0, *TRANSFORM_Z_MM)
            node["rot_deg"] = _num(n.get("rot_deg"), 0.0, *TRANSFORM_ROT_DEG)
            node["scale"] = _num(n.get("scale"), 1.0, *TRANSFORM_SCALE)
        elif n["kind"] == "artifact":
            nom = str(n.get("name") or "artefact")
            node["name"] = re.sub(r"[^A-Za-z0-9._-]", "_", nom)[:60] or "artefact"
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
_PROC_KINDS = ("plane", "relief", "mesh3d")
_CHAIN_MAX = 4        # material + transform + assemble, et une marge : la
                       # boucle de `_chaine_aval` ne suppose PAS le graphe
                       # acyclique (`clean_graph` ne coupe pas les cycles — un
                       # aller-retour d'arêtes ferait tourner un `while` nu).


def _chaine_aval(nid: str, nodes_by_id: dict, outgoing: dict) -> tuple:
    """La chaîne AVAL d'un traitement : `material` puis `transform` (0 ou 1 de
    chacun, dans N'IMPORTE QUEL ordre), jusqu'à `assemble`. Rend
    `(noeud material|None, noeud transform|None, atteint l'assemblage,
    ids des maillons PASSÉS)`.

    LE MODIFICATEUR PASSE AVANT L'ASSEMBLAGE quand les deux partent du même
    nœud : un graphe câblé à la fois `-> material` et `-> assemble` est
    ambigu, et prendre l'assemblage y jetterait la matière EN SILENCE. Deux
    matières (ou deux transforms) sur une même chaîne : refus — la seconde ne
    peut pas gagner sans que la première mente.

    L'ÉVENTAIL DE FRÈRES EST AVOUÉ, pas jeté en douce : deux arêtes parallèles
    vers deux matières, c'est la MÊME perte qu'une source surnuméraire à
    l'entrée (première arête gagnante), et l'entrée, elle, l'avoue depuis la
    tâche 4. L'écran ne produit pas cette topologie, mais l'API brute est
    ouverte à qui la poste — et le contrat `artifact@1` promet de nommer tout
    ce qui a été écarté."""
    mat = trs = None
    passes: list = []
    cur = nid
    for _ in range(_CHAIN_MAX):
        suivants = [nodes_by_id[t] for t in outgoing.get(cur, [])
                    if t in nodes_by_id]
        maillons = [s for s in suivants
                    if s["kind"] in ("material", "transform")]
        if not maillons:
            return (mat, trs,
                    any(s["kind"] == "assemble" for s in suivants), passes)
        nxt, freres = maillons[0], maillons[1:]
        passes.extend((f["id"], nxt["id"]) for f in freres)
        if nxt["kind"] == "material":
            if mat is not None:
                return mat, trs, False, passes
            mat = nxt
        else:
            if trs is not None:
                return mat, trs, False, passes
            trs = nxt
        cur = nxt["id"]
    return mat, trs, False, passes


def _resolve_graph_elements(graph: dict) -> tuple[list[dict], list[dict]]:
    """Chaque chaîne layer->(plane|relief|mesh3d)->[material]->[transform]->
    assemble devient UN candidat `{proc, layer, mat, trs}`, dans l'ORDRE DES
    NŒUDS du graphe (pas l'ordre des edges, pas l'ordre de résolution). Aucune
    E/S ici : c'est une garde, elle tourne AVANT tout travail lourd — le
    plafond `MAX_GRAPH_ELEMENTS` s'applique sur ce qu'elle rend, moteurs
    compris.

    Rend AUSSI `ignored` (REQUIS, revue) : le contrat `artifact@1` s'est figé à
    la tâche 4 — taire un nœud écarté serait un mensonge par omission. Quatre
    motifs, chacun nommé : une source SURNUMÉRAIRE (la première arête entrante
    gagne, patron déjà en vigueur — les suivantes sont d'authentiques pertes,
    pas un bug) ; un traitement SANS AUCUNE source ; un traitement bien sourcé
    mais dont la chaîne NE REJOINT PAS d'assemble (chaîne cassée, deux matières
    empilées, cycle) ; et, 2b, une MATIÈRE chaînée sur un `mesh3d` — le GLB du
    moteur porte déjà ses propres matériaux, la nôtre ne s'y substituerait pas,
    elle s'y ajouterait sans rien habiller."""
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    incoming: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for e in graph["edges"]:
        incoming.setdefault(e["to"], []).append(e["from"])
        outgoing.setdefault(e["from"], []).append(e["to"])
    candidats: list[dict] = []
    ignores: list[dict] = []
    for n in graph["nodes"]:
        if n["kind"] not in _PROC_KINDS:
            continue
        sources = []
        for fid in incoming.get(n["id"], []):
            sn = nodes_by_id.get(fid)
            if sn is not None and sn["kind"] == "layer":
                sources.append(sn)
        if not sources:
            ignores.append({
                "node": n["id"],
                "why": "traitement sans couche source (aucune arete layer "
                       "entrante)"})
            continue
        src, surnumeraires = sources[0], sources[1:]
        for autre in surnumeraires:
            ignores.append({
                "node": autre["id"],
                "why": f"source surnumeraire pour {n['id']} : {src['id']} "
                       "deja retenu (premiere arete gagnante)"})
        mat, trs, relie_assemble, passes = _chaine_aval(
            n["id"], nodes_by_id, outgoing)
        for perdant, retenu in passes:
            ignores.append({
                "node": perdant,
                "why": f"maillon surnumeraire dans la chaine de {n['id']} : "
                       f"{retenu} deja retenu (premiere arete gagnante)"})
        if not relie_assemble:
            ignores.append({"node": n["id"],
                            "why": "traitement non relie a un assemble"})
            continue
        if mat is not None and n["kind"] == "mesh3d":
            ignores.append({
                "node": mat["id"],
                "why": "matiere ignoree : le GLB du moteur porte deja ses "
                       "materiaux (chaine une matiere sur un plan ou un "
                       "relief)"})
            mat = None
        candidats.append({"proc": n, "layer": src, "mat": mat, "trs": trs})
    return candidats, ignores


def _trs_dict(node) -> dict | None:
    """Le nœud `transform` du graphe, traduit pour le writer (millimètres).
    Absent = None, et le writer garde alors le `z_mm` de la 2a."""
    if not isinstance(node, dict):
        return None
    return {"translate": [node["x_mm"], node["y_mm"], node["z_mm"]],
            "rotate_deg": node["rot_deg"], "scale": node["scale"]}


def _lire_manifeste(out: Path, card_label: str, side: str) -> dict | None:
    """Le manifeste d'export d'un côté, ou None. Illisible vaut ABSENT —
    jamais une exception qui deviendrait un 500 (même discipline que
    `_job_read`)."""
    p = out / f"layers_{card_label}_{side}.json"
    if not p.is_file():
        return None
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError):
        logger.warning(f"cards/forge3d: manifeste illisible ({p.name})")
        return None
    return m if isinstance(m, dict) else None


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


def _layer_filename(layer_node: dict, card_label: str) -> str:
    """Le nom de fichier ESTAMPILLÉ que `post_layers` a écrit (phase 1) pour
    cette source : la couche composite si `composite: true`, sinon le rôle."""
    side = layer_node["side"]
    if layer_node.get("composite"):
        return f"composite_{card_label}_{side}.png"
    return f"{layer_node['role']}_{card_label}_{side}.png"


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


def _habille(el: dict, mat_n, w_mm: float, h_mm: float,
             ignores: list) -> None:
    """La MATIÈRE et la FINITION d'un élément local, posées sur son
    dictionnaire (`mat_maps` / `finish`). Aucune des deux n'est vitale : une
    matière effacée de la boutique depuis que le graphe a été câblé, ou une
    recette de finition inconnue, laissent passer l'élément SANS habillage et
    entrent dans `ignores` avec leur motif — refuser tout l'artefact pour un
    accessoire absent serait disproportionné, le taire serait un mensonge."""
    if not isinstance(mat_n, dict):
        return
    if mat_n.get("mat"):
        try:
            el["mat_maps"] = material_pngs(tile_maps(
                mat_n["mat"],
                ("normal", "roughness", "metallic", "ao", "emissive"),
                mat_n["tile_mm"], w_mm, h_mm))
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
    if mat_n.get("finish") and mat_n["finish"] != "aucune":
        try:
            el["finish"] = holo_finish(mat_n["finish"],
                                       bool(mat_n.get("aniso")))
        except ValueError as e:
            ignores.append({"node": mat_n["id"],
                            "why": f"finition ignoree : {e}"})


def _element_externe(did: str, proc: dict, layer: dict, nom_el: str,
                     box_mm: list, trs_n, card_label: str) -> dict:
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
    job = _job_read(did, nid)
    if not isinstance(job, dict) or job.get("status") != "served":
        raise HTTPException(
            409, f"le noeud {nid} n'a pas servi son GLB — lance-le d'abord "
                 f"(POST mesh3d/{nid})")
    # I2 — UN GLB EST LIÉ À SA CARTE. Le job dit de QUELLE couche il est né
    # (`source.file`, écrit par la route au lancement) ; la chaîne, elle, vise
    # la couche de la carte qu'on construit MAINTENANT. Quand les deux
    # divergent — le nœud a été lancé sur la carte 1, on assemble la carte 2,
    # ou le côté du nœud `layer` a changé depuis — fusionner produirait un
    # artefact où l'illustration d'une AUTRE carte est présentée comme celle-ci.
    # Aucune mesure ne rattraperait ça après coup : c'est le bon fichier, au
    # mauvais endroit. Refus NOMMÉ, avec les deux noms, pour que le motif soit
    # actionnable (relancer le nœud) plutôt que mystérieux.
    attendu = _layer_filename(layer, card_label)
    servi = (job.get("source") or {}).get("file") if isinstance(
        job.get("source"), dict) else None
    if isinstance(servi, str) and servi and servi != attendu:
        raise HTTPException(
            409, f"le GLB du noeud {nid} a ete servi pour {servi} — cette "
                 f"construction attend {attendu} : relance-le pour cette carte")
    fichiers = job.get("files")
    nom_glb = (fichiers or {}).get("glb") if isinstance(fichiers, dict) else None
    nom_glb = str(nom_glb or "model.glb")
    if not re.match(r"^[A-Za-z0-9._-]{1,90}$", nom_glb) or set(nom_glb) == {"."}:
        raise HTTPException(
            409, f"le noeud {nid} annonce un fichier de nom invalide "
                 f"({nom_glb!r}) - relance le noeud")
    p_glb = _node_dir(did, nid) / nom_glb
    if not p_glb.is_file():
        raise HTTPException(
            409, f"le noeud {nid} n'a pas servi son GLB — {nom_glb} a disparu "
                 f"du noeud, relance-le")
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
    return {"name": nom_el, "node": nid, "glb": raw, "monde": monde,
            "fit": _fit_external(monde, box_mm, trs_n),
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
    candidats, ignores = _resolve_graph_elements(graph)
    # MOTIF 1/2 (distinct du "couche introuvable" ci-dessous, en revue) : le
    # graphe lui-même ne produit AUCUN élément — structurellement vide (aucun
    # nœud plane/relief) ou mal câblé (une source, ou l'assemblage, manque).
    # Un GLB à 0 élément est invalide au schéma glTF (minItems 1).
    if not candidats:
        raise HTTPException(
            409, "graphe vide : 0 element resolu (aucun noeud "
                 "plane/relief/mesh3d relie a la fois a une couche source et "
                 "a l'assemblage) - exporte les couches d'abord et relie "
                 "layer -> plane/relief/mesh3d -> assemble")
    if len(candidats) > MAX_GRAPH_ELEMENTS:
        raise HTTPException(
            400, f"trop d'elements ({len(candidats)}, maximum "
                 f"{MAX_GRAPH_ELEMENTS})")

    art_node = next((n for n in graph["nodes"] if n["kind"] == "artifact"),
                    None)
    art_name = art_node["name"] if art_node else "artefact"
    g = geom_of(doc)
    w_mm, h_mm = g.trim_mm
    # ── fenêtre UV coupe/toile (défaut de couture, revue finale 2a) : les
    # PNG couvrent la TOILE (fond perdu compris, canvas_px), le maillage
    # couvre la COUPE (trim_mm) — la fenêtre UV inset réconcilie les deux ;
    # sans elle, le fond perdu s'affiche sur l'artefact avec ~2,5 % de
    # distorsion anisotrope (63/69 != 88/94), mesuré en revue finale.
    # `bleed_px` vient de `g.bleed_off_px`, DÉJÀ la conversion canonique
    # (canvas_px - trim_px)/2 de contract.py:geom — pas une deuxième
    # dérivation locale (le domaine a déjà mesuré la dérive d'un recalcul
    # redondant : voir `_dpi_to_ppm` plus haut dans ce fichier).
    bleed_px = (round(g.bleed_off_px[0]), round(g.bleed_off_px[1]))
    u0, v0 = bleed_px[0] / g.canvas_px[0], bleed_px[1] / g.canvas_px[1]
    uv_window = (u0, v0, 1.0 - u0, 1.0 - v0)
    doc_name = doc.get("name") or did

    def work() -> dict:
        t0 = time.perf_counter()

        out = _out_dir(did, create=True)
        elements: list[dict] = []
        externes: list[dict] = []
        bordereau: list[dict] = []
        manifestes: dict = {}
        for ch in candidats:
            proc, layer = ch["proc"], ch["layer"]
            mat_n, trs_n = ch["mat"], ch["trs"]
            nom_el = layer.get("role") or "composite"
            if proc["kind"] == "mesh3d":
                side = layer["side"]
                if side not in manifestes:
                    manifestes[side] = _lire_manifeste(out, card_label, side)
                externes.append(_element_externe(
                    did, proc, layer, nom_el,
                    _layer_box_mm(manifestes[side], layer, w_mm, h_mm,
                                  g.bleed_mm),
                    trs_n, card_label))
                ex = externes[-1]
                bordereau.append({"name": nom_el, "kind": "externe",
                                  "node": proc["id"], "engine": ex["engine"],
                                  "credits": ex["credits"]})
                continue
            fname = _layer_filename(layer, card_label)
            p = out / fname
            # MOTIF 2/2 (distinct du "graphe vide" ci-dessus) : le graphe est
            # bien câblé, mais LA couche qu'il vise n'a jamais été livrée
            # pour cette carte/ce côté — exporte-les d'abord (phase 1).
            if not p.is_file():
                raise HTTPException(
                    409, f"exporte les couches d'abord : {fname} absent "
                         f"(POST /layers)")
            raw = p.read_bytes()
            im = _open_png(raw, fname)
            if proc["kind"] == "plane":
                mesh = quad_mesh(w_mm, h_mm, uv_window=uv_window)
                el = {"name": nom_el, "mesh": mesh, "png": raw,
                      "alpha": True, "z_mm": proc["depth_mm"]}
            else:
                # la géométrie/silhouette du relief ne doit voir QUE la
                # coupe — cropper la TOILE au rectangle de coupe (mêmes
                # bornes que `bleed_px` ci-dessus) AVANT l'échantillonnage,
                # sinon le fond perdu pèse sur la hauteur ET la silhouette.
                cx0, cy0 = bleed_px
                cx1 = g.canvas_px[0] - cx0
                cy1 = g.canvas_px[1] - cy0
                alpha_img = im.getchannel("A").crop((cx0, cy0, cx1, cy1))
                mesh = relief_mesh(alpha_img, w_mm, h_mm, proc["depth_mm"],
                                   proc["base_mm"], proc["grid"],
                                   uv_window=uv_window)
                el = {"name": nom_el, "mesh": mesh, "png": raw,
                      "alpha": False, "z_mm": 0.0}
            _habille(el, mat_n, w_mm, h_mm, ignores)
            trs = _trs_dict(trs_n)
            if trs is not None:
                el["trs"] = trs
            elements.append(el)
            bordereau.append({"name": nom_el, "kind": "local",
                              "node": proc["id"]})
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
# Identifiants GARANTIS SANS COLLISION avec un id de graphe reel : tout id
# qui traverse `clean_graph` est plafonne a 24 caracteres (voir son `[:24]`
# plus haut) — un identifiant interne de PLUS de 24 caracteres ne peut donc
# jamais etre celui d'un vrai noeud du client.
_PREVIEW_ASM_ID = "___apercu_noeud_assemble_synthetique___"
_PREVIEW_ART_ID = "___apercu_noeud_artefact_synthetique___"


def _apercu_mesh3d(did: str, nid: str) -> bytes:
    """Les octets bruts du GLB d'un noeud mesh3d SERVI, tels quels — meme
    garde et meme formulation que `_element_externe` (409 « n'a pas servi »),
    mais SANS la borne `MAX_EXT_GLB_BYTES` ni le controle de carte source :
    cette route ne fusionne ni ne construit rien, elle relit un fichier DEJA
    sur disque et le renvoie tel quel — le pire cas est une reponse HTTP
    volumineuse, jamais un artefact corrompu ou une ecriture disque
    incontrolee. `_element_externe`, LUI, refuse un GLB surdimensionne parce
    qu'il va le FUSIONNER en memoire avec d'autres — ce n'est pas le cas
    ici, donc pas la meme borne."""
    job = _job_read(did, nid)
    if not isinstance(job, dict) or job.get("status") != "served":
        raise HTTPException(
            409, f"le noeud {nid} n'a pas servi son GLB — lance-le d'abord "
                 f"(POST mesh3d/{nid})")
    fichiers = job.get("files")
    nom_glb = (fichiers or {}).get("glb") if isinstance(fichiers, dict) else None
    nom_glb = str(nom_glb or "model.glb")
    if not re.match(r"^[A-Za-z0-9._-]{1,90}$", nom_glb) or set(nom_glb) == {"."}:
        raise HTTPException(
            409, f"le noeud {nid} annonce un fichier de nom invalide "
                 f"({nom_glb!r}) - relance le noeud")
    p_glb = _node_dir(did, nid) / nom_glb
    if not p_glb.is_file():
        raise HTTPException(
            409, f"le noeud {nid} n'a pas servi son GLB — {nom_glb} a "
                 f"disparu du noeud, relance-le")
    return p_glb.read_bytes()


@router.post("/node-preview")
async def post_node_preview(did: str, body: dict | None = None):
    """Le GLB d'UN SEUL element du graphe — l'inspecteur partage du canvas
    (spec §5.6 point 4). `plane`/`relief` : sous-graphe SYNTHETIQUE {sa
    couche source, lui, sa matiere/son placement s'il en a un, un
    assemble+artifact FABRIQUES} passe a `_resolve_graph_elements` (le MEME
    resolveur que build3d — zero deuxieme version de la regle « premiere
    arete gagnante ») ; `mat`/`trs` viennent de `_chaine_aval` appliquee a
    `nid` sur le graphe REEL du client, pour que l'apercu montre l'option
    DEJA choisie sur ce noeud — meme si sa chaine ne rejoint pas encore un
    assemble reel, ce qui est precisement pourquoi l'assemble+artifact sont
    synthetiques : l'apercu doit marcher AVANT que le graphe soit complet.
    Grille de relief PLAFONNEE a `RELIEF_GRID_PREVIEW` AVANT resolution.
    `mesh3d` : les octets du job SERVI, tels quels (`_apercu_mesh3d`). Tout
    autre kind : refus nomme, ce noeud n'a rien a montrer en 3D.

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
    if kind not in ("plane", "relief", "mesh3d"):
        raise HTTPException(400, f"noeud non prévisualisable : {kind}")

    if kind == "mesh3d":
        if not _NID_RE.match(nid or ""):
            raise HTTPException(400, "Identifiant de noeud invalide")

        def work() -> bytes:
            return _apercu_mesh3d(did, nid)
    else:
        incoming: dict[str, list[str]] = {}
        outgoing: dict[str, list[str]] = {}
        for e in graph["edges"]:
            incoming.setdefault(e["to"], []).append(e["from"])
            outgoing.setdefault(e["from"], []).append(e["to"])
        src = next((nodes_by_id[fid] for fid in incoming.get(nid, [])
                   if fid in nodes_by_id
                   and nodes_by_id[fid]["kind"] == "layer"), None)
        if src is None:
            raise HTTPException(
                400, f"noeud {nid} sans couche source (relie une couche : "
                     f"layer -> {nid})")
        mat_n, trs_n, _relie, _passes = _chaine_aval(nid, nodes_by_id,
                                                      outgoing)
        proc = dict(node)
        if proc["kind"] == "relief":
            # PLAFONNE AVANT resolution (point impose du plan) : l'apercu
            # privilegie la vitesse, le vrai grid ne joue qu'au build.
            proc["grid"] = min(proc["grid"], RELIEF_GRID_PREVIEW)
        sub_nodes = [src, proc]
        sub_edges = [{"from": src["id"], "to": proc["id"]}]
        cur = proc["id"]
        for maillon in (mat_n, trs_n):
            if maillon is not None:
                sub_nodes.append(maillon)
                sub_edges.append({"from": cur, "to": maillon["id"]})
                cur = maillon["id"]
        sub_nodes.append({"id": _PREVIEW_ASM_ID, "kind": "assemble"})
        sub_nodes.append({"id": _PREVIEW_ART_ID, "kind": "artifact",
                          "name": "apercu"})
        sub_edges.append({"from": cur, "to": _PREVIEW_ASM_ID})
        sub_edges.append({"from": _PREVIEW_ASM_ID, "to": _PREVIEW_ART_ID})
        candidats, _ignores = _resolve_graph_elements(
            {"nodes": sub_nodes, "edges": sub_edges})
        if not candidats:
            # NE DEVRAIT JAMAIS ARRIVER (le sous-graphe ci-dessus est cable
            # a la main, une seule chaine possible) — doctrine jamais-500 :
            # un refus nomme plutot qu'un IndexError si un futur changement
            # de `_resolve_graph_elements` invalidait cette hypothese.
            raise HTTPException(
                400, f"noeud {nid} non prévisualisable : chaine irresoluble")
        ch = candidats[0]

        g = geom_of(doc)
        w_mm, h_mm = g.trim_mm
        bleed_px = (round(g.bleed_off_px[0]), round(g.bleed_off_px[1]))
        u0, v0 = bleed_px[0] / g.canvas_px[0], bleed_px[1] / g.canvas_px[1]
        uv_window = (u0, v0, 1.0 - u0, 1.0 - v0)

        def work() -> bytes:
            out = _out_dir(did)
            layer = ch["layer"]
            fname = _layer_filename(layer, card_label)
            p = out / fname
            if not p.is_file():
                raise HTTPException(
                    409, f"exporte les couches d'abord : {fname} absent "
                         f"(POST /layers)")
            raw = p.read_bytes()
            im = _open_png(raw, fname)
            nom_el = layer.get("role") or "composite"
            proc_n = ch["proc"]
            if proc_n["kind"] == "plane":
                mesh = quad_mesh(w_mm, h_mm, uv_window=uv_window)
                el = {"name": nom_el, "mesh": mesh, "png": raw,
                      "alpha": True, "z_mm": proc_n["depth_mm"]}
            else:
                cx0, cy0 = bleed_px
                cx1 = g.canvas_px[0] - cx0
                cy1 = g.canvas_px[1] - cy0
                alpha_img = im.getchannel("A").crop((cx0, cy0, cx1, cy1))
                mesh = relief_mesh(alpha_img, w_mm, h_mm, proc_n["depth_mm"],
                                   proc_n["base_mm"], proc_n["grid"],
                                   uv_window=uv_window)
                el = {"name": nom_el, "mesh": mesh, "png": raw,
                      "alpha": False, "z_mm": 0.0}
            ignores: list = []
            _habille(el, ch["mat"], w_mm, h_mm, ignores)
            trs = _trs_dict(ch["trs"])
            if trs is not None:
                el["trs"] = trs
            return write_scene_glb(
                [el], name="apercu",
                extras={"schema": ARTIFACT_SCHEMA, "preview": True})

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


@router.get("/material-thumb/{mid}")
async def get_material_thumb(did: str, mid: str):
    """La vignette de boutique d'une matiere, servie PAR PROVENANCE — le fond
    du corps de noeud `material` (Task 3, 2c) : PAS le composite de
    `read_material()["thumb"]`/`thumb_is_current` (celui-la gate sur
    `MESH_VERSION`, une histoire de viewport 3D qui ne concerne pas cette
    pastille 2D plate du canvas — une matiere reste un bon aplat de couleur
    meme quand la geometrie du viewport a change). `mid` valide AVANT toute
    lecture disque — aucun chemin n'est JAMAIS construit sur l'entree brute,
    le containment vient de `material_store.material_dir` (règle 8 :
    material_store est un service TRANSVERSE, deja consomme par `get_info`
    ci-dessus, pas une piece du lab). Jamais-500."""
    from .core import read_deck
    from .contract import is_valid_did
    from app.services import material_store as MSTORE
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    if not MSTORE.is_valid_mid(mid):
        raise HTTPException(400, "Identifiant de matière invalide")

    def work() -> Path | None:
        try:
            d = MSTORE.material_dir(mid)
        except ValueError:
            return None
        p = d / "thumb.png"
        return p if p.is_file() else None

    p = await asyncio.to_thread(work)
    if p is None:
        raise HTTPException(404, f"matière sans vignette : {mid}")
    return FileResponse(p, media_type="image/png",
                        headers={"Cache-Control": "no-store"})


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
    if not _re.match(r"^[A-Za-z0-9._-]{1,90}$", name or ""):
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
