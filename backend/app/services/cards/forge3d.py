# -*- coding: utf-8 -*-
"""Card Forge — P9 « Forge 3D ». Backend, phase 1 : export par couches.

Monté par `cards/__init__.py` sous `/api/cards/{did}/forge3d`. Chemins RELATIFS.
CE FICHIER APPARTIENT À P9 (règle 8) : aucun autre module ne l'importe, il
n'importe le routeur d'aucun autre.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import re
import struct
import time
import zipfile
import zlib
from functools import reduce
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from loguru import logger

from .contract import deck_dir
# Couture intra-pièce (legs 6, revue finale 2a) : la géométrie pure vit dans
# forge3d_scene.py (zéro FastAPI) — RÉEXPORTÉE ici pour que tests et route
# n'aient pas à changer d'orthographe. Ce fichier garde le contrat HTTP
# (routes, bornes, blocs miroir).
from .forge3d_scene import (quad_mesh, relief_mesh, mesh_measures,
                            write_scene_glb, _write_stl_binary)

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
# `layer`    : source — une couche du manifeste (role + side).
# `plane`    : plan texturé, GRATUIT (quad aux dimensions de la carte).
# `relief`   : dalle en relief, GRATUITE — grille déplacée par l'alpha,
#              solide FERMÉ par construction (imprimable).
# `assemble` : fusionne les amonts en une scène.
# `artifact` : sorties (GLB + metadata + aperçu + STL si fermé).
NODE_KINDS = [
    {"kind": "layer", "params": ["role", "side"]},
    {"kind": "plane", "params": ["depth_mm"]},
    {"kind": "relief", "params": ["depth_mm", "base_mm", "grid"]},
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


@router.get("/info")
async def get_info(did: str):
    """Ce que l'écran doit savoir sans rien recalculer."""
    from .core import read_deck
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    if read_deck(did) is None:
        raise HTTPException(404, "Deck introuvable")
    return {"schema": MANIFEST_SCHEMA, "layer_roles": LAYER_ROLES,
            "node_kinds": NODE_KINDS,
            "graph_limits": {
               "plane_depth_mm": list(PLANE_DEPTH_MM),
               "relief_depth_mm_max": RELIEF_DEPTH_MM_MAX,
               "relief_base_mm": list(RELIEF_BASE_MM),
               "relief_grid": list(RELIEF_GRID),
               "relief_grid_default": RELIEF_GRID_DEFAULT,
               "max_elements": MAX_GRAPH_ELEMENTS,
            }}


def _out_dir(did: str, create: bool = False) -> Path:
    d = deck_dir(did) / "forge3d"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


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
        elif n["kind"] == "artifact":
            nom = str(n.get("name") or "artefact")
            node["name"] = re.sub(r"[^A-Za-z0-9._-]", "_", nom)[:60] or "artefact"
        nodes.append(node)
    edges = []
    edges_in = g.get("edges")
    edges_in = edges_in if isinstance(edges_in, list) else []
    edges_in = edges_in[:_GRAPH_ITER_MAX]      # même borne anti-gel
    for e in edges_in:
        if not isinstance(e, dict):
            continue
        ef, et = e.get("from"), e.get("to")
        # même garde qu'au-dessus : `x in ids` hache x AVANT de comparer —
        # {"from": ["x"]} lève sinon (un id ne peut être qu'une chaîne).
        if isinstance(ef, str) and isinstance(et, str) and ef in ids and et in ids:
            edges.append({"from": ef, "to": et})
    return {"nodes": nodes, "edges": edges}


# ── LA GÉOMÉTRIE PURE, L'ASSEMBLAGE GLB ET L'ÉCRITURE STL ─────────────────────
# `quad_mesh`, `relief_mesh`, `mesh_measures`, `write_scene_glb` et
# `_write_stl_binary` vivent maintenant dans forge3d_scene.py (couture
# legs 6, revue finale 2a) — importés/réexportés en haut de ce fichier.
# Ce module garde le contrat HTTP : routes, bornes, blocs miroir.


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
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
def _resolve_graph_elements(graph: dict) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Chaque chaîne layer->(plane|relief)->assemble devient un candidat
    (nœud de traitement, nœud layer source), dans l'ORDRE DES NŒUDS du
    graphe (pas l'ordre des edges, pas l'ordre de résolution). Aucune E/S
    ici : c'est une garde, elle tourne AVANT tout travail lourd.

    Rend AUSSI `ignored` (REQUIS, revue) : le contrat `artifact@1` se fige à
    CETTE tâche — taire un nœud écarté serait un mensonge par omission, et
    l'argument « l'écran ne PEUT PAS produire ces topologies » expire dès la
    tâche 5 (2b). Trois motifs, chacun nommé : une source SURNUMÉRAIRE (la
    première arête entrante gagne, patron déjà en vigueur — les suivantes
    sont d'authentiques pertes, pas un bug) ; un traitement SANS AUCUNE
    source ; un traitement bien sourcé mais qui NE REJOINT PAS d'assemble."""
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    incoming: dict[str, list[str]] = {}
    outgoing: dict[str, list[str]] = {}
    for e in graph["edges"]:
        incoming.setdefault(e["to"], []).append(e["from"])
        outgoing.setdefault(e["from"], []).append(e["to"])
    candidats: list[tuple[dict, dict]] = []
    ignores: list[dict] = []
    for n in graph["nodes"]:
        if n["kind"] not in ("plane", "relief"):
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
        relie_assemble = any(
            nodes_by_id.get(tid, {}).get("kind") == "assemble"
            for tid in outgoing.get(n["id"], []))
        if not relie_assemble:
            ignores.append({"node": n["id"],
                            "why": "traitement non relie a un assemble"})
            continue
        candidats.append((n, src))
    return candidats, ignores


def _layer_filename(layer_node: dict, card_label: str) -> str:
    """Le nom de fichier ESTAMPILLÉ que `post_layers` a écrit (phase 1) pour
    cette source : la couche composite si `composite: true`, sinon le rôle."""
    side = layer_node["side"]
    if layer_node.get("composite"):
        return f"composite_{card_label}_{side}.png"
    return f"{layer_node['role']}_{card_label}_{side}.png"


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
            409, "graphe vide : 0 element resolu (aucun noeud plane/relief "
                 "relie a la fois a une couche source et a l'assemblage) - "
                 "exporte les couches d'abord et relie "
                 "layer -> plane/relief -> assemble")
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
        elements = []
        for proc, layer in candidats:
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
            nom_el = layer.get("role") or "composite"
            if proc["kind"] == "plane":
                mesh = quad_mesh(w_mm, h_mm, uv_window=uv_window)
                elements.append({"name": nom_el, "mesh": mesh, "png": raw,
                                 "alpha": True, "z_mm": proc["depth_mm"]})
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
                elements.append({"name": nom_el, "mesh": mesh, "png": raw,
                                 "alpha": False, "z_mm": 0.0})
        t_resolve = time.perf_counter()

        extras = {"deck": doc_name, "card": card_label, "format": g.fmt,
                  "size_mm": [w_mm, h_mm], "unit": "metre",
                  "schema": ARTIFACT_SCHEMA}
        glb = write_scene_glb(elements, name=art_name, extras=extras)
        glb_name = f"{art_name}.glb"
        (out / glb_name).write_bytes(glb)
        t_glb = time.perf_counter()

        meta = {
            # tiret ASCII GARDÉ (contrainte d'encodage maison) ; le reste de
            # la prose est accentué — json.dumps ci-dessous est en
            # ensure_ascii=False, le fichier livré porte déjà des accents.
            "name": f"{doc_name} - carte {card_label}",
            "description": "Carte 3D par éléments séparés, construite localement.",
            "image": f"{art_name}_preview.png",
            "animation_url": glb_name,
            "attributes": [
                {"trait_type": "deck", "value": doc_name},
                {"trait_type": "carte", "value": card_label},
                {"trait_type": "elements_3d", "value": len(elements)},
                {"trait_type": "engines", "value": "local"},
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
        tous_fermes = all(bool(el["mesh"].get("closed")) for el in elements)
        if tous_fermes:
            stl_bytes = _write_stl_binary(elements, art_name)
            stl_name = f"{art_name}.stl"
            (out / stl_name).write_bytes(stl_bytes)
            stl_bordereau = {"written": True, "name": stl_name,
                             "bytes": len(stl_bytes)}
        else:
            stl_bordereau = {
                "written": False,
                "why": "au moins un element n'est pas un solide ferme "
                       "(un plan texture n'a pas de volume) - le STL est "
                       "refuse plutot que livre casse"}
        t_stl = time.perf_counter()

        return {"artifact": {
            "glb": {"name": glb_name, "bytes": len(glb)},
            "metadata": {"name": meta_name, "bytes": len(meta_bytes)},
            "stl": stl_bordereau,
            # honnête : l'aperçu n'existe qu'après la capture client
            # (POST /preview/{art}, ci-dessous) — jamais un mensonge.
            "preview": {"expected": f"{art_name}_preview.png",
                       "written": False},
            "elements": len(elements),
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
    except Exception as e:
        logger.exception("cards/forge3d: construction du graphe impossible")
        raise HTTPException(500, f"Construction du graphe impossible : {e}")


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
