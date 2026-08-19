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

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from loguru import logger

from .contract import deck_dir

router = APIRouter()

MANIFEST_SCHEMA = "card-3d/layers-manifest@1"

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
RELIEF_GRID = (48, 256)              # subdivisions de la grille
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
    for e in edges_in:
        if not isinstance(e, dict):
            continue
        ef, et = e.get("from"), e.get("to")
        # même garde qu'au-dessus : `x in ids` hache x AVANT de comparer —
        # {"from": ["x"]} lève sinon (un id ne peut être qu'une chaîne).
        if isinstance(ef, str) and isinstance(et, str) and ef in ids and et in ids:
            edges.append({"from": ef, "to": et})
    return {"nodes": nodes, "edges": edges}


# ── LA GÉOMÉTRIE LOCALE — PLAN, RELIEF, MESURES ─────────────────────────────
# `quad_mesh`/`relief_mesh` produisent le maillage minimal qu'un traitement
# `plane`/`relief` du graphe fabrique ; `mesh_measures` en tire la preuve de
# fermeture/volume — COPIE LOCALE réduite du principe de `mesh_report` de P8
# (règle 8 : zéro import pièce->pièce, même patron que `_dpi_to_ppm`/`_num`
# ci-dessus). Type commun aux trois : {positions, normals, uvs, indices},
# consommé plus loin par `write_scene_glb` (Task 3).
def quad_mesh(w_mm: float, h_mm: float) -> dict:
    """Un quad aux dimensions de la carte, UV pleines, normale +z."""
    return {
        "positions": [0.0, 0.0, 0.0, w_mm, 0.0, 0.0, w_mm, h_mm, 0.0,
                      0.0, h_mm, 0.0],
        "normals": [0.0, 0.0, 1.0] * 4,
        "uvs": [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],   # v inversé (image)
        "indices": [0, 1, 2, 0, 2, 3],
    }


def relief_mesh(alpha_img, w_mm: float, h_mm: float, depth_mm: float,
                base_mm: float, grid: int) -> dict:
    """LA DALLE EN RELIEF : une grille (grid x grid') dont la face du dessus
    est déplacée par l'alpha de la couche (0 -> base, 255 -> base+depth), face
    du dessous plate à z=0, murs périphériques — un solide FERMÉ PAR
    CONSTRUCTION : chaque arête appartient à exactement deux triangles parce
    que dessus, dessous et murs partagent leurs anneaux de bord. C'est
    l'« extrusion » gratuite v1 : un vrai suivi de contour (marching squares +
    triangulation à trous) viendra si le besoin le prouve."""
    gx = max(2, int(grid))
    gy = max(2, int(round(grid * (h_mm / w_mm))))
    a = alpha_img.convert("L").resize((gx + 1, gy + 1))
    px = list(a.getdata())          # (gx+1)*(gy+1) échantillons

    def z_at(i, j):
        return base_mm + (px[j * (gx + 1) + i] / 255.0) * depth_mm

    pos, uv = [], []
    # dessus : (gx+1)*(gy+1) sommets déplacés
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, z_at(i, j)]
            uv += [i / gx, j / gy]
    top = lambda i, j: j * (gx + 1) + i                      # noqa: E731
    n_top = (gx + 1) * (gy + 1)
    # dessous : mêmes (x, y), z=0 (UV répliquées, sans importance au dos)
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, 0.0]
            uv += [i / gx, j / gy]
    bot = lambda i, j: n_top + j * (gx + 1) + i              # noqa: E731

    # ÉCART AU PLAN (winding corrigé, prouvé par ce fichier de test) : le
    # sens des sommets ci-dessous est l'INVERSE de celui écrit dans le plan.
    # Avec x croissant vers +i et y DÉCROISSANT vers +j (j=0 = haut de la
    # carte), le repère (x, y, z) est direct ; l'ordre du plan
    # [aa, bb, cc, aa, cc, dd] pour le dessus calcule une aire signée
    # négative (sens horaire vu depuis +z) — sa normale pointe donc -z, VERS
    # l'intérieur du solide, et symétriquement le dessous du plan pointait
    # +z. Les deux étaient donc inversées (mesuré : volume_mm3 négatif alors
    # que `closed` restait vrai — une inversion UNIFORME du maillage ne
    # casse pas le partage d'arêtes, seulement le signe). Corrigé ici en
    # permutant les deux derniers sommets de chaque triangle, dessus comme
    # dessous comme murs — la fermeture ET le volume positif sont
    # maintenant prouvés par `test_le_relief_est_un_solide_ferme_...`.
    idx = []
    for j in range(gy):
        for i in range(gx):
            aa, bb = top(i, j), top(i + 1, j)
            cc, dd = top(i + 1, j + 1), top(i, j + 1)
            idx += [aa, cc, bb, aa, dd, cc]                  # dessus, +z
            a2, b2 = bot(i, j), bot(i + 1, j)
            c2, d2 = bot(i + 1, j + 1), bot(i, j + 1)
            idx += [a2, b2, c2, a2, c2, d2]                  # dessous, -z
    # murs : les 4 bords, quads entre anneau du dessus et anneau du dessous
    def wall(t1, t2, b1, b2):
        idx.extend([t1, b2, b1, t1, t2, b2])
    for i in range(gx):                                       # j=0 et j=gy
        wall(top(i, 0), top(i + 1, 0), bot(i, 0), bot(i + 1, 0))
        wall(top(i + 1, gy), top(i, gy), bot(i + 1, gy), bot(i, gy))
    for j in range(gy):                                       # i=0 et i=gx
        wall(top(0, j + 1), top(0, j), bot(0, j + 1), bot(0, j))
        wall(top(gx, j), top(gx, j + 1), bot(gx, j), bot(gx, j + 1))

    # normales : dessus par gradient discret, dessous -z, murs approximés par
    # renormalisation des sommets partagés — suffisant, le glTF les porte.
    nrm = [0.0] * len(pos)
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
        ux, uy, uz = (pos[i1] - pos[i0], pos[i1 + 1] - pos[i0 + 1], pos[i1 + 2] - pos[i0 + 2])
        vx, vy, vz = (pos[i2] - pos[i0], pos[i2 + 1] - pos[i0 + 1], pos[i2 + 2] - pos[i0 + 2])
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for k in (i0, i1, i2):
            nrm[k] += cx; nrm[k + 1] += cy; nrm[k + 2] += cz
    for k in range(0, len(nrm), 3):
        ln = math.sqrt(nrm[k] ** 2 + nrm[k + 1] ** 2 + nrm[k + 2] ** 2) or 1.0
        nrm[k] /= ln; nrm[k + 1] /= ln; nrm[k + 2] /= ln
    return {"positions": pos, "normals": nrm, "uvs": uv, "indices": idx}


def mesh_measures(mesh: dict) -> dict:
    """Fermeture et volume signé, MESURES locales — copie du principe de
    `mesh_report` de P8 (règle 8 : pas d'import pièce->pièce), réduite aux
    deux chiffres dont l'artefact a besoin (closed, volume)."""
    pos, idx = mesh["positions"], mesh["indices"]
    edges: dict = {}
    vol = 0.0
    for t in range(0, len(idx) - 2, 3):
        tri = (idx[t], idx[t + 1], idx[t + 2])
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            ka = (round(pos[a * 3], 6), round(pos[a * 3 + 1], 6), round(pos[a * 3 + 2], 6))
            kb = (round(pos[b * 3], 6), round(pos[b * 3 + 1], 6), round(pos[b * 3 + 2], 6))
            e = (ka, kb) if ka <= kb else (kb, ka)
            edges[e] = edges.get(e, 0) + 1
        a3, b3, c3 = tri[0] * 3, tri[1] * 3, tri[2] * 3
        vol += (pos[a3] * (pos[b3 + 1] * pos[c3 + 2] - pos[b3 + 2] * pos[c3 + 1])
                - pos[a3 + 1] * (pos[b3] * pos[c3 + 2] - pos[b3 + 2] * pos[c3])
                + pos[a3 + 2] * (pos[b3] * pos[c3 + 1] - pos[b3 + 1] * pos[c3])) / 6.0
    closed = bool(edges) and all(n == 2 for n in edges.values())
    return {"closed": closed, "volume_mm3": vol,
            "triangles": len(idx) // 3, "vertices": len(pos) // 3}


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

        def _ouvre(raw: bytes, nom: str):
            """Un corps mal formé fait 400, JAMAIS 500 (spec 2.5). `format`
            est lu AVANT `convert()` : la conversion RGBA renvoie une image
            neuve dont `.format` vaut None — le vérifier après serait un
            contrôle qui ne contrôle rien."""
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

        images: dict[str, "Image.Image"] = {}
        for nom, raw in raw_par_role.items():
            im = _ouvre(raw, nom)
            if im.size != (w, h):
                raise HTTPException(409, f"{nom} : trame {im.size} != {(w, h)}")
            images[nom] = im
        comp = _ouvre(raw_comp, "composite")
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
    kind = "application/zip" if name.endswith(".zip") else \
        "image/png" if name.endswith(".png") else "application/json"
    return Response(p.read_bytes(), media_type=kind, headers={
        "Content-Disposition": f'attachment; filename="{p.name}"',
        "Cache-Control": "no-store"})
