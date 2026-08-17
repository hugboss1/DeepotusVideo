# -*- coding: utf-8 -*-
"""Card Forge — P8 « Export 3D ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/gltf`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P8. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8).

Le maillage vient de `contract.card_mesh(geom, solid)` — jamais de
`cards.solid` en direct : c'est `contract` qui bascule de la référence à
l'implémentation de P5 le jour où elle existe, et c'est le seul point de
bascule.

CE QUE CETTE PIÈCE LIVRE, ET QUE LA BARRE (Meshy) NE LIVRE PAS
──────────────────────────────────────────────────────────────
  * `.glb` ET `.gltf` (Meshy : `.glb` seul, pas de `.gltf` du tout).
  * ZIP des **8** maps PBR nommées exactement `basecolor · normal ·
    roughness · metallic · ao · height · emissive · orm` (Meshy : 5, ni AO
    ni height), `height` et `normal` RE-DERIVES en virgule flottante et
    ecrits en 16 bits REELS (des dizaines de milliers de niveaux, pas un
    octet duplique) — la profondeur est relue dans les octets a chaque
    construction, et le conteneur est REFUSE s'il ne porte rien de plus.
  * un BORDEREAU CHIFFRÉ **avant** téléchargement : chaque fichier est
    réellement construit, pesé à l'octet et daté. Meshy affiche un menu de
    huit extensions et un bouton à badge PRO, sans un seul chiffre.
  * les dimensions PHYSIQUES : le nœud porte l'échelle qui met la carte à
    63 x 88 x 0,32 mm dans un viewer qui compte en mètres, et `extras` les
    écrit en toutes lettres. Meshy n'a qu'une hauteur en cm.
  * 0 crédit, 0 compte, 0 plafond mensuel, 0 rétention : tout est écrit dans
    `outputs/decks/<did>/gltf/`, sur ce disque, tout de suite.

TROIS PIÈGES DE PROD, traités au niveau MODULE :
  * `gltf_builder` ignore SILENCIEUSEMENT un nom de maillage inconnu et rend
    une SPHÈRE. « card » est enregistré par `GB._BUILDERS.setdefault(...)` au
    CHARGEMENT du module (voir `_register_card_builder`), jamais dans le corps
    d'une route, et `GET /info` publie
    `mesh_stats("card")["triangles"] != mesh_stats("sphere")["triangles"]`.
  * NE PAS incrémenter `MESH_VERSION` : la constante entre dans la clé du
    cache d'aperçu ET dans `thumb_is_current` — la bumper périmerait toutes
    les vignettes du Material Forge. Elle est LUE ici, jamais écrite.
  * `build_glb` force `metallicFactor`/`roughnessFactor` à 1.0 dès qu'une ORM
    existe : les niveaux sont cuits par `pbr_service.bake_levels` AVANT
    encodage. Et **aucun `uv_repeat`, aucun `tiling`/`rotation`** : les trois
    îlots recto/verso/tranche déborderaient les uns sur les autres.

Aucune ligne de `gltf_builder.py` ni de `material_store.py` ne bouge : les
`extras` et l'échelle physique sont ajoutés APRÈS coup, en réécrivant le seul
chunk JSON du GLB produit (`_glb_read` / `_glb_write`).
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import re
import threading
import time
import zipfile
import zlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from loguru import logger

from .contract import (
    MM_PER_INCH, THICKNESS_MM_DEFAULT, THICKNESS_MM_MAX, THICKNESS_MM_MIN,
    UV_ISLANDS, CardGeom, card_mesh, deck_dir, geom, rnd,
)

router = APIRouter()

# ── constantes de la pièce ──────────────────────────────────────────────────
# Les 8 maps, dans l'ordre du contrat. La liste n'est PAS recopiée : elle est
# lue sur `pbr_service.MAP_KINDS` au premier appel (`map_names()`), pour qu'un
# ajout côté service ne laisse pas cette pièce mentir. La constante ci-dessous
# n'est que le repli quand PIL/pbr_service est absent (503).
MAP_NAMES_FALLBACK = ("basecolor", "normal", "roughness", "metallic",
                      "ao", "height", "emissive", "orm")

# Les 4 emplacements REELLEMENT lus par un moteur glTF. `height` n'a pas
# d'équivalent en glTF cœur (il part dans le ZIP et dans `extras`) ;
# roughness/metallic/ao séparés sont volontairement omis dès qu'une ORM existe
# — `build_glb` les écarte, les encoder gonfle le fichier sans être lu.
GLB_SLOTS = ("basecolor", "normal", "orm", "emissive")

RES_CHOICES = (1024, 2048, 4096)
RES_MIN, RES_MAX = 256, 4096
RES_DEFAULT = 2048

FILE_FORMATS = ("glb", "gltf", "zip", "obj", "stl", "3mf", "ply", "dxf",
                "proof")
# « auto » = les deux codecs sont produits et le plus LÉGER gagne, texture par
# texture. Voir `_encode` : sur de l'aplat le PNG bat le JPEG, sur une photo
# c'est l'inverse — un défaut fixe se tromperait une fois sur deux.
IMG_FORMATS = ("auto", "png", "jpeg")
JPEG_Q_MIN, JPEG_Q_MAX, JPEG_Q_DEFAULT = 60, 100, 92

# Finitions : elles ne changent QUE les props de matière (donc les facteurs et
# les extensions KHR), jamais la géométrie ni le placage.
#
# `emissive` EST UN CORRECTIF, pas une décoration. Mesuré le 11/08 sur le GLB
# livré en finition « Mat (papier) » : `emissiveFactor = [1,1,1]` au-dessus
# d'une emissive.png dont 6,52 % des pixels dépassent 8/255 (maximum 219). Une
# carte en PAPIER MAT sortait donc AUTO-ILLUMINÉE : dans n'importe quelle
# visionneuse glTF, lumières éteintes, le titre et les ornements brillaient
# tout seuls. Le papier n'émet pas de lumière — les trois finitions papier
# passent à 0.0 et le facteur du fichier vaut alors [0,0,0], vérifié sur les
# octets (`test_finition_papier_n_emet_aucune_lumiere`).
#
# Dorure et holographique gardent une émission FAIBLE et ASSUMÉE : sans HDRI,
# un moteur ne rend une feuille d'or que par sa réflexion, et une carte
# holographique posée dans une scène neutre serait grise. La valeur est écrite
# dans `extras.render.emissive` et affichée à l'écran — jamais implicite.
FINISHES: dict[str, dict] = {
    "mat": {"label": "Mat (papier)", "roughness": 0.86, "metallic": 0.0,
            "clearcoat": 0.0, "clearcoat_roughness": 0.0, "sheen": 0.0,
            "emissive": 0.0},
    "satin": {"label": "Satiné", "roughness": 0.54, "metallic": 0.0,
              "clearcoat": 0.25, "clearcoat_roughness": 0.22, "sheen": 0.0,
              "emissive": 0.0},
    "vernis": {"label": "Vernis sélectif", "roughness": 0.30, "metallic": 0.0,
               "clearcoat": 0.85, "clearcoat_roughness": 0.08, "sheen": 0.0,
               "emissive": 0.0},
    "foil": {"label": "Dorure à chaud", "roughness": 0.32, "metallic": 0.72,
             "clearcoat": 0.40, "clearcoat_roughness": 0.12, "sheen": 0.0,
             "emissive": 0.30},
    "holo": {"label": "Holographique", "roughness": 0.24, "metallic": 0.55,
             "clearcoat": 1.0, "clearcoat_roughness": 0.06, "sheen": 0.55,
             "sheen_color": "#a8d0ff", "emissive": 0.45},
}
DEFAULT_FINISH = "mat"

# ── ce que les trois wrap glTF valent, en clair ─────────────────────────────
# `gltf_builder` pose REPEAT (10497) sur son unique sampler : c'est le bon
# défaut pour une texture qui carrelle, et le MAUVAIS pour un ATLAS. Mesuré :
# les gouttières font 40 px en u et 41 px en v ; en REPEAT, le filtrage
# bilinéaire du bord droit de l'atlas va chercher la colonne 0 — soit l'autre
# face de la carte — et les niveaux de mip ramènent ce mélange sur toute la
# tranche. `finalize_glb` réécrit donc les samplers en CLAMP_TO_EDGE. C'est la
# même intention que « aucun KHR_texture_transform » (piège 12), appliquée à
# l'échantillonnage au lieu des coordonnées.
WRAP_REPEAT = 10497
WRAP_CLAMP = 33071

# ── le PIVOT ────────────────────────────────────────────────────────────────
# Reproche mesuré : le maillage est centré (min/max symétriques) et rien ne
# permettait de le poser. Un import moteur qui veut la carte SUR une table doit
# alors corriger l'origine à la main, carte par carte. Le pivot se pose sur le
# NŒUD (translation), jamais sur les positions : la géométrie, les accesseurs
# et le chunk binaire restent identiques à l'octet d'un pivot à l'autre — c'est
# ce qui garantit que changer le pivot ne peut pas changer la carte.
PIVOTS = ("centre", "bas", "dos")
DEFAULT_PIVOT = "centre"

# QUI PORTE LE PIVOT, ET COMMENT. La liste était écrite à la main dans les
# `extras` (« le MEME ecart part dans les cinq formats… OBJ, STL et 3MF ») et
# elle avait PÉRIMÉ : le PLY et le DXF sont sortis depuis, ils cuisent eux
# aussi l'écart dans leurs positions (mesuré : pivot « bas » -> y de 0 à 88 mm
# dans les six fichiers). Une phrase qui nomme trois formats sur cinq n'est pas
# fausse, elle est incomplète — et c'est la même faute, en plus discret. Les
# deux familles sont donc des CONSTANTES, publiées par `/info` et reprises
# telles quelles par l'écran et par la notice.
PIVOT_NODE_FORMATS = ("glb", "gltf")        # porté par node.translation
PIVOT_BAKED_FORMATS = ("obj", "stl", "3mf", "ply", "dxf")   # cuit en positions

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,90}$")
MAX_ATLAS_BYTES = 64 * 1024 * 1024          # une image d'atlas, pas un film
CARD_MAX = 500                              # garde-fou du scope « deck »

# ═══════════════════════════════════════════════════════════════════════════
# UN FICHIER EXPORTÉ NE PORTE PAS LA CARTE DE VISITE DE QUI L'A ÉCRIT
# ═══════════════════════════════════════════════════════════════════════════
# Un relevé extérieur a compté le nom du producteur dans 8 pièces jointes sur
# 15, à huit endroits différents : `asset.generator` dès le 55e octet du
# `.gltf`, `materials[].extras.generator` posé par le constructeur générique,
# le nom de la scène, l'espace de noms du manifeste, la première ligne de
# commentaire de l'OBJ et du MTL, l'en-tête 80 octets du STL, le commentaire
# du PLY, le nom de calque du DXF, la `<metadata name="Application">` du 3MF,
# le `tEXt` de chacun des huit PNG et la bannière des deux LISEZMOI.
#
# Ces fichiers partent chez un tiers — c'est leur seule raison d'être. Ce
# qu'ils doivent dire d'eux-mêmes est ce qu'ils CONTIENNENT : l'unité, les
# dimensions, le compte de triangles, la densité. Le nom de l'outil n'aide
# personne à monter la carte dans un moteur, et il voyage indéfiniment.
#
# Les espaces de noms de schéma restent STABLES (un consommateur peut s'y
# accrocher) : ils décrivent la forme du document, pas son producteur.
MANIFEST_SCHEMA = "card-3d/maps-manifest@3"
OBJ_MANIFEST_SCHEMA = "card-3d/obj-manifest@1"
DECK_MANIFEST_SCHEMA = "card-3d/deck-manifest@1"

# Clés d'`extras` qui nomment un producteur, quel que soit l'étage du document.
# `finalize_glb` les retire du fichier avant écriture : le constructeur
# générique en pose deux (asset et matériau) que cette pièce ne contrôle pas.
IDENTITY_KEYS = ("generator", "producer", "author", "software", "application",
                 "copyright", "artist", "company", "vendor")

# `1 unité glTF = 1 mètre` est la convention du format (spec 2.0, §3.6). Un
# maillage dont la demi-hauteur vaut 1.0 mesure donc 2 mètres : sans échelle
# sur le nœud, un viewer annoncerait « 1,43 x 2,00 m » pour une carte à jouer.
GLTF_UNIT_M = 1.0


# ═══════════════════════════════════════════════════════════════════════════
# 1. LE MAILLAGE « card », ENREGISTRÉ AU CHARGEMENT DU MODULE
# ═══════════════════════════════════════════════════════════════════════════
# `gltf_builder.build_mesh` retombe SILENCIEUSEMENT sur la sphère quand le nom
# est inconnu (piège 9 de la spec) : un GLB de carte serait une boule, sans le
# moindre message. On enregistre donc « card » ici, à l'import, par
# `setdefault` — jamais par affectation : si un jour un autre module le pose,
# on ne l'écrase pas en silence.
#
# `_BUILDERS[nom]()` ne prend AUCUN argument, alors que le maillage d'une carte
# dépend du format et de l'épaisseur. Le contexte est donc porté par une
# variable de module, posée sous VERROU juste avant `build_glb` et retirée
# après (`_mesh_context`). Sans le verrou, deux exports concurrents — deux
# onglets, ou l'export deck qui boucle — se voleraient le contexte et une carte
# sortirait à l'épaisseur de l'autre.
#
# ET UNE COURSE, MESURÉE : `cards/__init__.py` importe `solid` AVANT `gltf`, et
# P5 pose lui aussi `_BUILDERS.setdefault("card", …)` — vers un maillage FIXE
# (format et épaisseur d'usine). Le premier arrivé gagne, et ce n'est pas nous.
# Un export de Tarot 70x120 en 0,9 mm serait donc sorti à la taille d'un poker
# de 0,32 mm, SANS UN MOT : le GLB aurait été juste, mais pas celui du jeu.
# La clé « card » reste posée (piège 9, et elle sert à qui n'a pas de
# contexte) ; les exports, eux, passent par une clé PRIVÉE dont P8 est le seul
# propriétaire. `finalize_glb` rebaptise ensuite le maillage « card » dans le
# fichier : le nom privé ne fuit pas.
_MESH_LOCK = threading.RLock()
_MESH_CTX: dict | None = None
CTX_MESH = "cf_card_ctx"


def default_card_mesh() -> dict:
    """Le maillage de la carte par DÉFAUT (format et épaisseur d'usine).

    C'est lui que rend `gltf_builder.build_mesh("card")` hors contexte, donc
    aussi `mesh_stats("card")` : le compte de triangles publié par `/info` est
    celui-là, stable et documenté."""
    return card_mesh(geom(_DEFAULT_MESH_FMT), {"thickness_mm": THICKNESS_MM_DEFAULT})


_DEFAULT_MESH_FMT = "poker_eu"


def _card_builder():
    """Adaptateur `_BUILDERS` : (positions, normales, uv, indices).

    `build_mesh` recalcule les tangentes APRÈS coup à partir de ces UV — c'est
    ce qui garde le repère TBN cohérent avec les trois îlots."""
    m = _MESH_CTX if isinstance(_MESH_CTX, dict) else default_card_mesh()
    return m["positions"], m["normals"], m["uvs"], m["indices"]


def _register_card_builder() -> bool:
    """`setdefault` au CHARGEMENT du module — jamais dans le corps d'une route.

    Deux clés : « card » (celle de la spec, éventuellement déjà posée par P5)
    et `CTX_MESH`, privée, qui lit le CONTEXTE et dont P8 est seul
    propriétaire. Rend True si « card » est enregistré, par nous ou par
    l'autre."""
    try:
        from app.services import gltf_builder as GB
    except Exception as e:                    # pragma: no cover - env cassé
        logger.warning(f"cards/gltf: gltf_builder indisponible ({e})")
        return False
    GB._BUILDERS.setdefault("card", _card_builder)
    GB._BUILDERS.setdefault(CTX_MESH, _card_builder)
    return "card" in GB._BUILDERS and CTX_MESH in GB._BUILDERS


CARD_MESH_REGISTERED = _register_card_builder()


def card_builder_owner() -> str:
    """Qui répond pour « card » dans `gltf_builder._BUILDERS` — nous, ou P5.

    Publié par `/info` : quand la table dit « P5 », c'est que le maillage
    arrondi est là ; quand elle dit « P8 », c'est le contexte de cette pièce.
    Dans les deux cas l'EXPORT passe par `CTX_MESH`, donc par la géométrie du
    jeu ouvert."""
    try:
        from app.services import gltf_builder as GB
        fn = GB._BUILDERS.get("card")
    except Exception:                          # pragma: no cover - env cassé
        return "absent"
    if fn is None:
        return "absent"
    return "gltf" if fn is _card_builder else getattr(
        fn, "__module__", "?").rsplit(".", 1)[-1]


class _mesh_context:
    """Contexte du maillage « card » — verrou pris, contexte posé, contexte
    retiré, verrou rendu. Tout `build_glb(mesh="card")` passe par ici."""

    def __init__(self, mesh: dict):
        self.mesh = mesh

    def __enter__(self):
        global _MESH_CTX
        _MESH_LOCK.acquire()
        _MESH_CTX = self.mesh
        return self.mesh

    def __exit__(self, *exc):
        global _MESH_CTX
        _MESH_CTX = None
        _MESH_LOCK.release()
        return False


def mesh_bbox(mesh: dict) -> tuple[list, list]:
    """Boîte englobante du maillage, en unités du maillage."""
    pos = mesh.get("positions") or [0.0, 0.0, 0.0]
    lo = [min(pos[i::3]) for i in range(3)]
    hi = [max(pos[i::3]) for i in range(3)]
    return lo, hi


def physical_scale(mesh: dict, height_mm: float) -> float:
    """Facteur qui met le maillage à sa taille PHYSIQUE, en mètres.

    Mesuré sur la boîte englobante RÉELLE, pas déduit de la convention
    « demi-hauteur = 1.0 » : le jour où P5 livre son maillage arrondi avec une
    autre échelle, les dimensions annoncées restent justes."""
    lo, hi = mesh_bbox(mesh)
    span = hi[1] - lo[1]
    if not (span > 1e-9) or not (height_mm > 0):
        return 1.0
    return (height_mm / 1000.0) / span * GLTF_UNIT_M


def outline_perimeter_mm(mesh: dict, height_mm: float) -> float | None:
    """PÉRIMÈTRE RÉEL DU CONTOUR, mesuré sur le maillage livré.

    LE CHIFFRE QUI SE DÉDUISAIT. La densité de l'îlot de tranche était calculée
    sur ``2 x (largeur + hauteur)`` — le périmètre d'un rectangle À COINS VIFS.
    Or la carte livrée a des coins ARRONDIS : mesuré sur les octets du GLB
    (anneau médian, 28 segments), le contour fait 296,80 mm et non 302,0. Le
    chiffre publié dans le ``tEXt`` des huit PNG, dans le manifeste, dans la
    notice et à l'écran était donc faux de 1,7 % — et la densité qui en découle
    avec (172,2 DPI annoncés pour 175,3 réels). Un commentaire du fichier
    disait d'ailleurs « ~296,9 mm » pendant que le code écrivait 302,0 : la
    valeur juste était connue, elle n'était simplement pas mesurée.

    On la MESURE donc, sur le maillage qui part dans le fichier : enveloppe
    convexe des sommets projetés en (x, y) — pour une carte (contour convexe)
    c'est exactement la silhouette que la bande de tranche enroule, et ça reste
    juste si P5 change son rayon de coin, son nombre de segments ou son profil.
    """
    pos = mesh.get("positions") or []
    if len(pos) < 9:
        return None
    pts = sorted({(round(pos[i * 3], 9), round(pos[i * 3 + 1], 9))
                  for i in range(len(pos) // 3)})
    if len(pts) < 3:
        return None

    def cross(o, a, b) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return None
    per = 0.0
    for k, a in enumerate(hull):
        b = hull[(k + 1) % len(hull)]
        per += math.hypot(a[0] - b[0], a[1] - b[1])
    # unités de maillage -> mm (physical_scale rend des mètres)
    return per * physical_scale(mesh, height_mm) / GLTF_UNIT_M * 1000.0


def mesh_triangles(mesh: dict) -> int:
    return len(mesh.get("indices") or []) // 3


def _uv_tri(mesh: dict, t: int) -> list:
    """Les 6 coordonnées UV d'un triangle : u0 v0 u1 v1 u2 v2."""
    uv = mesh.get("uvs") or []
    idx = mesh.get("indices") or []
    out = []
    for k in range(3):
        i = idx[t * 3 + k]
        out += [uv[i * 2], uv[i * 2 + 1]]
    return out


def mesh_report(mesh: dict) -> dict:
    """LE COMPTE DE MAILLAGE, MESURÉ — et il part dans le fichier.

    Il manquait partout : ni `extras`, ni `manifest.json`, ni `LISEZMOI.txt` ne
    contenaient le mot « triangle » ni le nombre 224 (relevé du 11/08, recherche
    sur les trois documents). C'est le PREMIER chiffre que regarde quiconque
    ouvre un modèle 3D, et c'était le seul absent d'un bordereau qui pèse par
    ailleurs chaque PNG à l'octet.

    `closed` n'est pas décoratif non plus : il commande `doubleSided`. Un solide
    fermé n'a pas de face arrière visible ; le laisser en double face doublait
    le coût d'ombrage ET masquait une éventuelle inversion de normales au lieu
    de la révéler. On soude les arêtes par COORDONNÉES (pas par index) : les
    quads de l'atlas dupliquent les sommets aux coutures UV, un comptage par
    index dirait « ouvert » sur un solide parfaitement fermé."""
    pos = mesh.get("positions") or []
    idx = mesh.get("indices") or []
    edges: dict = {}
    for t in range(0, len(idx) - 2, 3):
        tri = (idx[t], idx[t + 1], idx[t + 2])
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            ka = (round(pos[a * 3], 6), round(pos[a * 3 + 1], 6),
                  round(pos[a * 3 + 2], 6))
            kb = (round(pos[b * 3], 6), round(pos[b * 3 + 1], 6),
                  round(pos[b * 3 + 2], 6))
            e = (ka, kb) if ka <= kb else (kb, ka)
            edges[e] = edges.get(e, 0) + 1
    libres = sum(1 for n in edges.values() if n != 2)
    isl = uv_islands(mesh)
    # ── LE CONTRÔLE D'IMPRIMABILITÉ QUI MANQUAIT ────────────────────────────
    # Reproche fondé : la barre calcule un verdict d'imprimabilité, ici la
    # solidité du maillage était vraie mais GARANTIE PAR CONSTRUCTION, jamais
    # vérifiée ni montrée — et le STL est justement le format où ça compte. Le
    # volume signé est la mesure qui manquait : positif ET fermé = un solide
    # qu'un trancheur accepte ; négatif = normales retournées (un slicer
    # imprime alors le complémentaire, sans un mot).
    vol = 0.0
    for t in range(0, len(idx) - 2, 3):
        a, b, c = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
        x1, y1, z1 = pos[a], pos[a + 1], pos[a + 2]
        x2, y2, z2 = pos[b], pos[b + 1], pos[b + 2]
        x3, y3, z3 = pos[c], pos[c + 1], pos[c + 2]
        vol += (x1 * (y2 * z3 - z2 * y3)
                - y1 * (x2 * z3 - z2 * x3)
                + z1 * (x2 * y3 - y2 * x3)) / 6.0
    ferme = bool(edges) and libres == 0
    return {
        "triangles": len(idx) // 3,
        "vertices": len(pos) // 3,
        "edges": len(edges),
        "free_edges": libres,
        "closed": ferme,
        "volume_units3": rnd(vol, 12),
        "normals_outward": vol > 0.0,
        # `printable` est un ET de deux mesures publiées juste au-dessus
        # (`free_edges` et le signe de `volume_units3`) : la phrase qui le
        # commentait n'ajoutait aucun nombre et voyageait dans chaque fichier.
        "printable": bool(ferme and vol > 0.0),
        "attributes": ["POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"],
        # MESURÉ, plus déclaré. Voir `uv_islands`.
        "uv_islands": isl["islands"],
        "uv_islands_tri": isl["triangles_per_island"],
        "uv_islands_uv": isl["bbox_uv"],
        "atlas_rects": len(UV_ISLANDS),
        "edges_welded_by": "position",
    }


def uv_islands(mesh: dict) -> dict:
    """LES ÎLOTS UV, COMPTÉS SUR LE MAILLAGE — plus jamais `len(UV_ISLANDS)`.

    LE CHIFFRE QUI SE DÉCLARAIT. `uv_islands` valait `len(UV_ISLANDS)`, une
    CONSTANTE de trois : le nombre de rectangles que le contrat réserve dans
    l'atlas. Ce n'est pas le même objet qu'un îlot — un rectangle peut porter
    plusieurs morceaux disjoints (les remplissages de coin arrondi), et le
    jour où P5 change son maillage la constante continue de dire « 3 » sans
    rien mesurer. Un relevé extérieur a d'ailleurs annoncé « 5 îlots, pas 3 »
    sur un fichier livré : impossible à trancher tant que le nombre affiché
    n'était pas une mesure.

    Ici on compte les COMPOSANTES CONNEXES par ARÊTE UV partagée — la
    définition d'une coque UV dans un modeleur, et la plus stricte : deux
    triangles qui ne se touchent que par un sommet comptent pour deux îlots.
    Les sommets sont d'abord soudés par COORDONNÉE UV exacte (l'atlas duplique
    les sommets à chaque couture, un comptage par index dirait n'importe quoi).
    """
    uv = mesh.get("uvs") or []
    idx = mesh.get("indices") or []
    nt = len(idx) // 3
    if nt <= 0 or len(uv) < 6:
        return {"islands": 0, "triangles_per_island": [], "bbox_uv": [],
                "note": "aucun maillage"}
    key: dict = {}
    rep = []
    for i in range(len(uv) // 2):
        k = (uv[i * 2], uv[i * 2 + 1])
        if k not in key:
            key[k] = i
        rep.append(key[k])
    shared: dict = {}
    for t in range(nt):
        tri = (rep[idx[t * 3]], rep[idx[t * 3 + 1]], rep[idx[t * 3 + 2]])
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            shared.setdefault((a, b) if a <= b else (b, a), []).append(t)
    par = list(range(nt))

    def find(a: int) -> int:
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for ts in shared.values():
        for j in range(1, len(ts)):
            ra, rb = find(ts[0]), find(ts[j])
            if ra != rb:
                par[ra] = rb
    groups: dict = {}
    for t in range(nt):
        groups.setdefault(find(t), []).append(t)
    out = []
    for ts in groups.values():
        us, vs = [], []
        for t in ts:
            for k in range(3):
                i = idx[t * 3 + k]
                us.append(uv[i * 2])
                vs.append(uv[i * 2 + 1])
        out.append((len(ts), [rnd(min(us), 4), rnd(min(vs), 4),
                              rnd(max(us), 4), rnd(max(vs), 4)]))
    out.sort(key=lambda r: -r[0])
    return {
        "islands": len(out),
        "triangles_per_island": [n for n, _ in out],
        "bbox_uv": [b for _, b in out],
        "note": ("Composantes connexes par ARETE UV partagee, sommets soudes "
                 "par coordonnee UV exacte. Mesure sur le maillage livre, "
                 f"pas sur les {len(UV_ISLANDS)} rectangles reserves par le "
                 "contrat."),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. GLB : relire et réécrire le chunk JSON (extras + échelle physique)
# ═══════════════════════════════════════════════════════════════════════════
_GLB_MAGIC = 0x46546C67
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942


def _glb_read(glb: bytes) -> tuple[dict, bytes]:
    """GLB -> (document glTF, chunk binaire). Lève ValueError si le fichier
    n'est pas un GLB."""
    import struct
    if len(glb) < 20 or glb[:4] != b"glTF":
        raise ValueError("GLB invalide (en-tête manquant)")
    total = struct.unpack("<I", glb[8:12])[0]
    off, js, bin_ = 12, None, b""
    while off + 8 <= min(total, len(glb)):
        clen, ctype = struct.unpack("<II", glb[off:off + 8])
        data = glb[off + 8:off + 8 + clen]
        if ctype == _CHUNK_JSON:
            js = data
        elif ctype == _CHUNK_BIN:
            bin_ = data
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    if js is None:
        raise ValueError("GLB invalide (chunk JSON absent)")
    return json.loads(js.decode("utf-8").rstrip("\x00 ")), bytes(bin_)


def _glb_write(doc: dict, bin_: bytes) -> bytes:
    """(document glTF, chunk binaire) -> GLB. Bourrage JSON en ESPACES et BIN
    en ZÉROS, alignement 4 octets — la spec GLB l'impose et un lecteur strict
    (Blender, three.js en mode validation) refuse le fichier sinon."""
    import struct
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    bins = bytes(bin_)
    if len(bins) % 4:
        bins += b"\x00" * (4 - len(bins) % 4)
    total = 12 + 8 + len(js) + (8 + len(bins) if bins else 0)
    out = bytearray()
    out += struct.pack("<III", _GLB_MAGIC, 2, total)
    out += struct.pack("<II", len(js), _CHUNK_JSON) + js
    if bins:
        out += struct.pack("<II", len(bins), _CHUNK_BIN) + bins
    return bytes(out)


def pivot_offset(mesh: dict, pivot: str) -> list:
    """Translation à poser sur le nœud, en unités de MAILLAGE.

    « centre » : rien (le maillage est déjà symétrique).
    « bas »    : le bas de la boîte englobante arrive à y = 0 — la carte est
                 POSÉE, debout, sur le plan du sol d'un moteur.
    « dos »    : la carte est couchée face en l'air, son dos à z = 0 (l'épaisseur
                 entière au-dessus du plan) — le cas d'une carte sur une table.
    """
    lo, hi = mesh_bbox(mesh)
    if pivot == "bas":
        return [0.0, -lo[1], 0.0]
    if pivot == "dos":
        return [0.0, 0.0, -lo[2]]
    return [0.0, 0.0, 0.0]


_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
               "MAT2": 4, "MAT3": 9, "MAT4": 16}


def exact_accessor_bounds(doc: dict, bin_: bytes) -> int:
    """RÉÉCRIT `accessor.min` / `accessor.max` AVEC LES VALEURS DU BUFFER.

    LE DÉFAUT, MESURÉ SUR LE FICHIER LIVRÉ. `gltf_builder` arrondit les bornes
    à six décimales : l'accesseur POSITION annonçait
    `min = [-0.715909, -1.0, -0.003636]` quand le chunk binaire porte
    `[-0.7159090638160706, -1.0, -0.003636363660916686]`. Quatre composantes
    sur six ne correspondaient pas. Physiquement l'écart est nul (0,0000028 mm),
    mais la spec glTF 2.0 §5.1 impose que ces deux champs soient les bornes
    EXACTES des données, et le validateur de référence (KhronosGroup/glTF-
    Validator) remonte `ACCESSOR_MIN_MISMATCH` / `ACCESSOR_MAX_MISMATCH` au
    niveau **ERREUR** : un fichier par ailleurs impeccable échouait à la
    validation automatique pour une question d'arrondi évitable.

    On ne touche pas `gltf_builder` : on relit le chunk binaire du GLB qu'il
    vient d'écrire et on repose les bornes, composante par composante. Les
    valeurs écrites sont les flottants 32 bits EXACTS lus dans le buffer (leur
    représentation décimale en double les restitue au bit près), donc le
    validateur compare deux fois le même nombre.

    Rend le nombre d'accesseurs corrigés (0 = les bornes étaient déjà exactes).
    """
    import struct
    views = doc.get("bufferViews") or []
    fixed = 0
    for acc in (doc.get("accessors") or []):
        if "min" not in acc or "max" not in acc:
            continue
        if int(acc.get("componentType", 0)) != 5126:      # FLOAT seulement
            continue
        n = _COMPONENTS.get(str(acc.get("type")), 0)
        cnt = int(acc.get("count") or 0)
        k = acc.get("bufferView")
        if not n or not cnt or not isinstance(k, int) or k >= len(views):
            continue
        bv = views[k]
        off = int(bv.get("byteOffset") or 0) + int(acc.get("byteOffset") or 0)
        stride = int(bv.get("byteStride") or 0) or n * 4
        if off + (cnt - 1) * stride + n * 4 > len(bin_):
            continue
        lo = [float("inf")] * n
        hi = [float("-inf")] * n
        for e in range(cnt):
            vals = struct.unpack_from("<" + "f" * n, bin_, off + e * stride)
            for c in range(n):
                v = vals[c]
                if v < lo[c]:
                    lo[c] = v
                if v > hi[c]:
                    hi[c] = v
        if any(not math.isfinite(v) for v in lo + hi):
            continue
        if acc["min"] != lo or acc["max"] != hi:
            fixed += 1
        acc["min"] = list(lo)
        acc["max"] = list(hi)
    return fixed


def scrub_identity(node, dropped: list | None = None) -> list:
    """Retire, à tous les étages d'un document glTF, les champs qui nomment un
    producteur — et rend la liste de ce qui est parti.

    Le constructeur générique en pose deux que cette pièce n'écrit pas :
    `asset.generator` et `materials[].extras.generator`. Les supprimer au coup
    par coup se serait périmé au premier champ ajouté ailleurs ; on balaie donc
    le document entier, et la liste rendue permet de le VÉRIFIER au lieu de le
    supposer (voir `test_aucun_fichier_livre_ne_nomme_son_producteur`)."""
    out = [] if dropped is None else dropped
    if isinstance(node, dict):
        for k in list(node.keys()):
            if k in IDENTITY_KEYS and isinstance(node[k], str):
                out.append(f"{k}={node.pop(k)}")
            else:
                scrub_identity(node[k], out)
    elif isinstance(node, list):
        for v in node:
            scrub_identity(v, out)
    return out


def finalize_glb(glb: bytes, extras: dict, scale: float,
                 name: str = "card", closed: bool = False,
                 offset: list | None = None) -> bytes:
    """Pose sur le GLB ce que `build_glb` ne sait pas dire : les `extras`
    documentés, l'ÉCHELLE PHYSIQUE du nœud, et les DEUX corrections d'atlas
    que le constructeur générique ne peut pas connaître.

    Aucune ligne de `gltf_builder.py` n'est touchée : on relit le chunk JSON du
    fichier qu'il vient de produire, on l'annote, on le réécrit. Le chunk
    binaire (géométrie et textures) est recopié tel quel, à l'octet.

    1. SAMPLERS EN CLAMP_TO_EDGE. `gltf_builder` pose REPEAT (10497) — bon
       défaut pour une texture qui carrelle, faux sur un atlas : le filtrage du
       bord droit va chercher la colonne 0, c'est-à-dire l'autre face de la
       carte, et le mip l'étale. Mesuré avant : `wrapS = wrapT = 10497`.
    2. doubleSided=false SUR UN SOLIDE FERMÉ. Mesuré : 336 arêtes, chacune
       utilisée exactement deux fois, 0 arête libre — et le matériau partait
       quand même en double face. Coût d'ombrage doublé, et une inversion de
       normales serait restée invisible. `closed` vient de `mesh_report`, pas
       d'une supposition."""
    doc, bin_ = _glb_read(glb)
    doc.setdefault("asset", {})["extras"] = extras

    # 3. BORNES D'ACCESSEUR EXACTES : le validateur glTF de référence refusait
    #    le fichier sur un arrondi à six décimales. Voir `exact_accessor_bounds`.
    n_fixed = exact_accessor_bounds(doc, bin_)
    if isinstance(extras.get("mesh"), dict):
        extras["mesh"]["accessor_bounds_fixed"] = n_fixed

    for s in (doc.get("samplers") or []):
        s["wrapS"] = WRAP_CLAMP
        s["wrapT"] = WRAP_CLAMP
    for m in (doc.get("materials") or []):
        if closed:
            m["doubleSided"] = False
        # Le constructeur générique pose aussi, dans `materials[].extras`, un
        # paragraphe français sur la doctrine du metallicFactor. Un matériau
        # glTF porte des facteurs et des index de texture, pas un mode
        # d'emploi : `levelsBaked` et `settings` restent, la phrase part. Elle
        # est dans la notice, une fois, dans le document fait pour être lu.
        (m.get("extras") or {}).pop("note", None)

    nodes = doc.get("nodes") or []
    if nodes:
        s = float(scale)
        if abs(s - 1.0) > 1e-12:
            nodes[0]["scale"] = [s, s, s]
        # glTF applique T x R x S : la translation est donc en unités du PARENT,
        # pas du maillage. `pivot_offset` rend l'écart en unités de maillage, on
        # le met à l'échelle ici — sans quoi la carte partirait 22 fois trop
        # loin (1/0.044).
        if offset and any(abs(float(v)) > 1e-12 for v in offset):
            nodes[0]["translation"] = [rnd(float(v) * s, 9) for v in offset]
        nodes[0]["name"] = str(name or "card")[:80]
        nodes[0]["extras"] = extras.get("card", {})
    # Le nom de scène du constructeur générique nomme, lui aussi, l'outil : il
    # est réécrit sur TOUTES les scènes, pas seulement la première.
    for sc in (doc.get("scenes") or []):
        sc["name"] = str(name or "card")[:80]
    meshes = doc.get("meshes") or []
    if meshes:
        # le nom PRIVÉ de la clé de contexte ne fuit pas dans le fichier.
        meshes[0]["name"] = "card"
    # Dernier geste avant l'écriture, et le seul qui compte pour un fichier qui
    # part chez un tiers : plus un champ ne nomme le producteur.
    scrub_identity(doc)
    return _glb_write(doc, bin_)


def glb_report(glb: bytes) -> dict:
    """Ce que le GLB contient VRAIMENT, relu sur les octets produits.

    C'est la mesure qui remplit le bordereau — pas la liste de ce qu'on a
    voulu mettre dedans."""
    doc, bin_ = _glb_read(glb)
    mat = (doc.get("materials") or [{}])[0]
    pbr = mat.get("pbrMetallicRoughness") or {}
    images = doc.get("images") or []
    used: list[str] = []
    for slot in GLB_SLOTS:
        idx = None
        if slot == "basecolor":
            idx = (pbr.get("baseColorTexture") or {}).get("index")
        elif slot == "orm":
            idx = (pbr.get("metallicRoughnessTexture") or {}).get("index")
        elif slot == "normal":
            idx = (mat.get("normalTexture") or {}).get("index")
        elif slot == "emissive":
            idx = (mat.get("emissiveTexture") or {}).get("index")
        if idx is not None:
            used.append(slot)
    node = (doc.get("nodes") or [{}])[0]
    views = doc.get("bufferViews") or []

    def _img_bytes(im: dict) -> int:
        k = im.get("bufferView")
        if not isinstance(k, int) or k < 0 or k >= len(views):
            return 0
        return int(views[k].get("byteLength") or 0)

    prim = ((doc.get("meshes") or [{}])[0].get("primitives") or [{}])[0]
    wraps = sorted({int(s.get("wrapS", 0)) for s in (doc.get("samplers") or [])}
                   | {int(s.get("wrapT", 0)) for s in (doc.get("samplers") or [])})
    em = mat.get("emissiveFactor") or [0.0, 0.0, 0.0]
    # BORNES D'ACCESSEUR : on RE-MESURE sur les octets finaux au lieu de croire
    # la correction. `exact_accessor_bounds` sur une copie du document rend le
    # nombre d'accesseurs qu'il DEVRAIT encore corriger : zéro = le fichier
    # passe `ACCESSOR_MIN_MISMATCH` du validateur glTF de référence.
    reste = exact_accessor_bounds(json.loads(json.dumps(doc)), bin_)
    borns = [a for a in (doc.get("accessors") or []) if "min" in a]
    # ── LA BOÎTE, RELUE DANS LE BUFFER ─────────────────────────────────────
    # L'écran ne montrait qu'UN relevé de taille, celui de la visionneuse, et
    # il tombait pile sur l'attendu. De l'extérieur, rien ne distingue alors
    # une mesure d'une recopie de l'attendu — le reproche a été fait, et il
    # était juste.
    # Celui-ci est INDÉPENDANT : les bornes viennent des float32 de POSITION
    # relus un à un dans le chunk binaire (`exact_accessor_bounds`, dont la
    # ligne au-dessus vérifie qu'il ne reste rien à corriger), multipliées par
    # l'échelle du nœud. La visionneuse, elle, fait parser le GLB par un moteur
    # 3D dans le navigateur. Deux chemins sans rien en commun : leur accord au
    # micromètre se constate, il ne se décrète pas.
    bbox_mm = None
    ipos = (prim.get("attributes") or {}).get("POSITION")
    accs = doc.get("accessors") or []
    if isinstance(ipos, int) and 0 <= ipos < len(accs):
        lo = accs[ipos].get("min")
        hi = accs[ipos].get("max")
        sc = node.get("scale") or [1.0, 1.0, 1.0]
        if (isinstance(lo, list) and isinstance(hi, list)
                and len(lo) == 3 and len(hi) == 3):
            bbox_mm = [rnd((float(hi[i]) - float(lo[i]))
                           * float(sc[i if i < len(sc) else 0]) * 1000.0, 4)
                       for i in range(3)]
    return {
        "bbox_mm": bbox_mm,
        "textures": used,
        "texture_count": len(used),
        "images": [im.get("name") for im in images],
        "image_bytes": {str(im.get("name")): _img_bytes(im) for im in images},
        "metallicFactor": pbr.get("metallicFactor"),
        "roughnessFactor": pbr.get("roughnessFactor"),
        "extensions": sorted(doc.get("extensionsUsed") or []),
        "node_scale": node.get("scale"),
        "node_translation": node.get("translation") or [0.0, 0.0, 0.0],
        "materials": len(doc.get("materials") or []),
        "bin_bytes": len(bin_),
        "extras": (doc.get("asset") or {}).get("extras", {}),
        # ── relu sur les octets, pas déduit des réglages ────────────────────
        "attributes": sorted(prim.get("attributes") or {}),
        "double_sided": bool(mat.get("doubleSided")),
        "emissive_factor": [rnd(float(c), 3) for c in em],
        "emits_light": any(float(c) > 0.0 for c in em),
        "occlusion": (mat.get("occlusionTexture") or {}).get("index") is not None,
        "accessors_bornes": len(borns),
        "accessors_bornes_exactes": reste == 0,
        "accessors_bornes_note": (
            f"{len(borns)} accesseur(s) declarent min/max ; {reste} "
            "s'ecarte(nt) des octets du buffer. 0 = le fichier passe "
            "ACCESSOR_MIN_MISMATCH du validateur glTF de reference."),
        "wrap": wraps,
        "wrap_label": ("CLAMP_TO_EDGE" if wraps == [WRAP_CLAMP]
                       else "REPEAT" if wraps == [WRAP_REPEAT]
                       else "mixte " + str(wraps)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. ENTRÉES CLIENT — un corps mal formé ne fait JAMAIS 500 (spec 2.5)
# ═══════════════════════════════════════════════════════════════════════════
def _num(raw, default: float, lo: float, hi: float) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(lo if v < lo else hi if v > hi else v)


def clean_res(raw) -> int:
    """Définition de l'atlas. Toute valeur est admise entre 256 et 4096, pas
    seulement 1k/2k/4k : le chiffre s'écrit."""
    return int(round(_num(raw, RES_DEFAULT, RES_MIN, RES_MAX)))


def clean_finish(raw) -> str:
    s = str(raw or "").strip().lower()
    return s if s in FINISHES else DEFAULT_FINISH


def clean_formats(raw) -> list[str]:
    """Liste blanche, ordre stable, jamais vide (glb au minimum)."""
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return ["glb", "gltf", "zip"]        # les trois cochés par défaut
    got = [f for f in FILE_FORMATS if f in {str(x).strip().lower() for x in raw}]
    return got or ["glb"]


def clean_options(body) -> dict:
    """Toutes les options d'un export, réparées. Ne lève jamais."""
    b = body if isinstance(body, dict) else {}
    fin = clean_finish(b.get("finish"))
    return {
        "res": clean_res(b.get("res")),
        "formats": clean_formats(b.get("formats")),
        "finish": fin,
        # VRAI PAR DÉFAUT, et ce n'est plus un pari : `height` et `normal` sont
        # RE-DÉRIVÉS en virgule flottante (`derive_deep`) et portent alors des
        # dizaines de milliers de niveaux au lieu de deux cents. Si la mesure
        # faite sur le PNG écrit ne le confirmait pas, `map_png` REFUSERAIT le
        # conteneur et livrerait 8 bits en le disant. La case ne peut donc pas
        # produire d'octets vides ; décocher n'économise que du poids.
        "bits16": bool(b.get("bits16", True)),
        "img": (str(b.get("img") or "").strip().lower()
                if str(b.get("img") or "").strip().lower() in IMG_FORMATS
                else "auto"),
        "jpeg_q": int(round(_num(b.get("jpeg_q"), JPEG_Q_DEFAULT,
                                 JPEG_Q_MIN, JPEG_Q_MAX))),
        # ABSENT veut dire « celle de P5 », pas « celle d'usine ». Une valeur
        # par défaut posée ici écrasait `doc.solid.thickness_mm` en silence :
        # un tarot réglé à 0,9 mm sortait à 0,32 mm, mesuré.
        "thickness_mm": (None if b.get("thickness_mm") is None else
                         _num(b.get("thickness_mm"), THICKNESS_MM_DEFAULT,
                              THICKNESS_MM_MIN, THICKNESS_MM_MAX)),
        "pivot": (str(b.get("pivot") or "").strip().lower()
                  if str(b.get("pivot") or "").strip().lower() in PIVOTS
                  else DEFAULT_PIVOT),
        "scope": "deck" if str(b.get("scope") or "").strip().lower() == "deck"
                 else "card",
        "cards": b.get("cards") if isinstance(b.get("cards"), list) else None,
        "derive": b.get("derive") if isinstance(b.get("derive"), dict) else None,
    }


def props_of(finish: str) -> dict:
    """Props de matière pour `gltf_builder.build_glb`.

    `tiling` reste à 1.0 et `rotation` à 0.0 : un `KHR_texture_transform` sur
    un ATLAS ferait déborder les îlots recto / verso / tranche les uns sur les
    autres (piège 12 de la spec)."""
    f = FINISHES.get(finish) or FINISHES[DEFAULT_FINISH]
    p = {
        "color": "#ffffff", "opacity": 1.0,
        "metallic": f["metallic"], "roughness": f["roughness"],
        # `emissive_strength` MULTIPLIE la couleur : à 0.0 le fichier porte
        # `emissiveFactor = [0,0,0]` et la carte n'émet rien. Voir FINISHES.
        "emissive": "#ffffff",
        "emissive_strength": float(f.get("emissive", 0.0)),
        "clearcoat": f["clearcoat"],
        "clearcoat_roughness": f["clearcoat_roughness"],
        "sheen": f.get("sheen", 0.0),
        "sheen_color": f.get("sheen_color", "#ffffff"),
        "normal_scale": 1.0, "ao_strength": 1.0,
        "tiling": 1.0, "rotation": 0.0,
    }
    return p


# ═══════════════════════════════════════════════════════════════════════════
# 4. DECK, GÉOMÉTRIE, CHEMINS
# ═══════════════════════════════════════════════════════════════════════════
def _deck(did: str) -> dict:
    """Document du deck, ou l'erreur HTTP qui va bien. Lecture seule : cette
    pièce n'écrit jamais le document (spec 2.2 §10, CORE seul)."""
    from .core import read_deck                     # magasin de CORE
    from .contract import is_valid_did
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = read_deck(did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable")
    return doc


def _geom(doc: dict) -> CardGeom:
    from .core import geom_of
    return geom_of(doc)


def solid_of(doc: dict, override: float | None = None) -> dict:
    """Le sous-arbre `doc.solid` (P5), tel quel, épaisseur éventuellement
    forcée. On le passe ENTIER à `card_mesh` : rayon de coin, segments et
    biseau appartiennent à P5, et un export qui ne garderait que l'épaisseur
    livrerait une carte moins arrondie que celle de l'écran."""
    solid = (doc or {}).get("solid")
    out = dict(solid) if isinstance(solid, dict) else {}
    out["thickness_mm"] = thickness_of(doc, override)
    return out


def thickness_of(doc: dict, override: float | None = None) -> float:
    """Épaisseur en mm. `doc.solid.thickness_mm` appartient à P5 : on le LIT,
    on ne l'écrit jamais, et son absence n'est pas une panne (spec : les
    couplages inter-pièces sont en lecture et tolèrent l'absence)."""
    if override is not None:
        return _num(override, THICKNESS_MM_DEFAULT, THICKNESS_MM_MIN,
                    THICKNESS_MM_MAX)
    solid = (doc or {}).get("solid")
    raw = solid.get("thickness_mm") if isinstance(solid, dict) else None
    return _num(raw, THICKNESS_MM_DEFAULT, THICKNESS_MM_MIN, THICKNESS_MM_MAX)


def derive_keys() -> tuple:
    """Les noms que `pbr_service.normalize_derive` sait lire. On les LIT sur le
    service : recopier la liste ici la périmerait au premier ajout."""
    try:
        from app.services import pbr_service as PBR
        return tuple(PBR.DERIVE_DEFAULTS)
    except Exception:                          # pragma: no cover - env cassé
        return ("normal_strength", "roughness_bias", "ao_strength",
                "ao_radius", "height_detail")


def derive_of(doc: dict, override: dict | None = None) -> dict:
    """Réglages de dérivation PBR venus de P6 — LE COUPLAGE ÉTAIT MORT.

    LE DÉFAUT, MESURÉ. Cette fonction rendait `doc.texture.pbr`, c'est-à-dire
    l'ENVELOPPE, alors que `pbr_service.normalize_derive` attend
    `normal_strength`, `roughness_bias`, `ao_strength`… au PREMIER niveau et
    que P6 les écrit un cran plus bas, sous `doc.texture.pbr.derive`.
    `normalize_derive` ignore les clés inconnues SANS UN MOT : tout le monde
    recevait `DERIVE_DEFAULTS`. Contre-épreuve faite atlas figé, mêmes options,
    seul `derive` changeant : 8 maps sur 8 identiques À L'OCTET malgré des
    réglages opposés. Les douze curseurs de la pièce 06 étaient décoratifs pour
    le fichier livré — et l'aperçu de P6, lui, les respectait : l'écran et le
    fichier divergeaient.

    On accepte les deux dispositions (sous-arbre `.derive`, ou clés à plat
    dans `pbr`) et on ne retient QUE les clés que le service sait lire, pour
    ne pas maquiller un réglage inconnu en réglage appliqué.
    """
    if isinstance(override, dict):
        return override
    tex = (doc or {}).get("texture")
    pbr = tex.get("pbr") if isinstance(tex, dict) else None
    if not isinstance(pbr, dict):
        return {}
    known = set(derive_keys())
    sub = pbr.get("derive")
    src = sub if isinstance(sub, dict) else pbr
    return {k: v for k, v in src.items() if k in known}


def derive_source(doc: dict, override: dict | None = None) -> dict:
    """D'où viennent les réglages de dérivation, et combien ont été repris.
    Publié par `/info` et affiché : un couplage qu'on ne voit pas est un
    couplage qui peut mourir en silence (c'est exactement ce qui est arrivé)."""
    if isinstance(override, dict):
        return {"source": "requete", "keys": sorted(override), "count": len(override)}
    tex = (doc or {}).get("texture")
    pbr = tex.get("pbr") if isinstance(tex, dict) else None
    if not isinstance(pbr, dict):
        return {"source": "defauts", "keys": [], "count": 0}
    got = derive_of(doc)
    lv = pbr.get("levels") if isinstance(pbr.get("levels"), dict) else None
    return {
        "source": ("texture.pbr.derive" if isinstance(pbr.get("derive"), dict)
                   else "texture.pbr" if got else "defauts"),
        "keys": sorted(got), "count": len(got),
        # deux homonymes indépendants, et c'est un piège : la case cochée dans
        # « Matières » n'est PAS celle qui commande le ZIP.
        "p6_bits16": bool(pbr.get("bits16")),
        # ── L'AUTRE COUPLAGE, ET IL EST VOLONTAIREMENT NON REPRIS ────────────
        # `doc.texture.pbr.levels` (rugosité / métal réglés dans « Matières »)
        # n'entre PAS dans l'export : les niveaux cuits ici viennent de la
        # FINITION choisie sur cet écran (`props_of`). Deux réglages du même
        # nombre, deux propriétaires — le taire serait le même défaut que le
        # couplage mort qu'on vient de réparer, à l'envers. On le NOMME.
        "p6_levels": lv,
        "p6_levels_note": (
            "La piece 06 a enregistre des niveaux (" +
            ", ".join(f"{k}={v}" for k, v in sorted(lv.items())) +
            ") : ils ne sont PAS repris. Les niveaux cuits dans ce ZIP "
            "viennent de la FINITION choisie ici, seule proprietaire de la "
            "matiere exportee." if lv else ""),
    }


def gltf_dir(did: str, create: bool = False) -> Path:
    d = deck_dir(did, create=create) / "gltf"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir(did: str, create: bool = False) -> Path:
    d = gltf_dir(did, create=create) / "out"
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def atlas_path(did: str, i: int, create: bool = False) -> Path:
    return gltf_dir(did, create=create) / f"atlas_{int(i):03d}.png"


def atlas_indices(did: str) -> list[int]:
    try:
        d = gltf_dir(did)
    except ValueError:
        return []
    if not d.is_dir():
        return []
    out = []
    for p in d.glob("atlas_*.png"):
        try:
            out.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return sorted(out)


def slug_of(doc: dict) -> str:
    from app.services import material_store as MS
    return MS.slug(doc.get("name") or "", fallback="carte")


#: OÙ LE FICHIER EST POSÉ — et pourquoi ce chemin est RELATIF.
#: L'écran doit pouvoir dire où retrouver l'export : c'est le seul des
#: quatorze points que la pièce perdait, alors que l'information était déjà
#: sous la main. Mais un chemin ABSOLU sur Windows commence par
#: `C:\Users\<nom du compte>\…` : l'afficher publierait le nom de la personne
#: qui fait tourner l'outil dans chaque capture d'écran et dans chaque
#: réponse d'API. On publie donc la queue du chemin, relative au dossier du
#: jeu, et jamais la racine.
OUT_DIR_REL = "gltf/out"


def disk_evidence(did: str) -> dict:
    """Ce que ce disque porte, maintenant : le compte de fichiers déjà écrits
    pour ce jeu, leur poids, et l'âge du plus ancien qui y est TOUJOURS.

    Trois nombres qui se recomptent sur le dossier, à comparer au bordereau.
    """
    try:
        d = out_dir(did)
    except ValueError:
        return {}
    if not d.is_dir():
        return {"files": 0, "bytes": 0, "listed": 0, "missing": 0,
                "oldest_age_hours": 0.0, "dir": OUT_DIR_REL}
    stats, total, oldest = 0, 0, None
    for p in d.iterdir():
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        stats += 1
        total += st.st_size
        oldest = st.st_mtime if oldest is None else min(oldest, st.st_mtime)
    age_h = ((time.time() - oldest) / 3600.0) if oldest else 0.0
    # ── « expire : 0 » N'ÉTAIT PAS UNE MESURE ───────────────────────────────
    # C'était le littéral 0, écrit en dur, servi à côté de nombres qui, eux,
    # se recomptent. Ce qui SE mesure, c'est l'écart entre le dernier bordereau
    # et le dossier : combien de fichiers listés ne sont plus là. Zéro se
    # constate alors au lieu de se promettre.
    listed = missing = 0
    try:
        man = json.loads((gltf_dir(did) / "build.json").read_text("utf-8"))
        for f in (man.get("files") or []):
            listed += 1
            if not (d / str(f.get("name") or "")).is_file():
                missing += 1
    except (OSError, ValueError, TypeError, AttributeError):
        listed = missing = 0
    return {
        "files": stats,
        "bytes": total,
        "listed": listed,
        "missing": missing,
        "oldest_age_hours": rnd(age_h, 2),
        "dir": OUT_DIR_REL,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. LA CONSTRUCTION — tout est mesuré sur les octets produits
# ═══════════════════════════════════════════════════════════════════════════
def islands_px(res_w: int, res_h: int) -> dict:
    """Les trois îlots de l'atlas, en pixels. Le contrat les donne en UV ; ici
    on les traduit une fois, et l'écran les reçoit — il n'en recalcule aucun."""
    out = {}
    for k, (u0, v0, u1, v1) in UV_ISLANDS.items():
        out[k] = [int(round(u0 * res_w)), int(round(v0 * res_h)),
                  int(round((u1 - u0) * res_w)), int(round((v1 - v0) * res_h))]
    return out


def res_fit(g: CardGeom) -> int | None:
    """LA DÉFINITION JUSTE — la plus petite qui n'agrandisse PAS la source.

    LE REPROCHE, ET IL REVENAIT DANS LES DEUX DUELS : « 60 % de chaque îlot est
    de l'interpolation », « un atlas 1k contiendrait l'information vraie avec
    de la marge, le réglage par défaut est 2k ». C'était mesuré, écrit à
    l'écran… et rien ne permettait de le CORRIGER. Annoncer un sur-
    échantillonnage n'est pas le supprimer.

    On cherche donc la plus petite définition à laquelle l'îlot recto contient
    la coupe rendue SANS l'agrandir ni la réduire sur aucun des deux axes —
    par ESSAI sur `islands_px`, pas par une formule qui ignorerait l'arrondi du
    pavage. Au-dessous, on perdrait de l'information ; au-dessus, on paie des
    texels qui n'en portent aucune.

    Reste l'anisotropie : le rectangle du contrat (`UV_ISLANDS`, propriété de
    `cards/contract.py`) n'a pas le rapport de la carte, et cette pièce n'a pas
    le droit de le redécouper. Les texels restent donc non carrés à toute
    définition — c'est écrit, chiffré, et ça ne se corrige pas ici."""
    tw, th_px = int(g.trim_px[0]), int(g.trim_px[1])
    for r in range(RES_MIN, RES_MAX + 1):
        f = islands_px(r, r).get("front")
        if f and f[2] >= tw and f[3] >= th_px:
            return r
    return None


def atlas_density(g: CardGeom, res_w: int, res_h: int,
                  th_mm: float | None = None, mesh: dict | None = None) -> dict:
    """Définition de la face dans l'atlas — et SURTOUT la part qui porte
    réellement de l'information.

    LE CHIFFRE QUI MENTAIT. Cette fonction ne rendait que `dpi`, la densité de
    TEXELS de l'îlot, et l'écran la comparait à 300 en vert : « 404.8 x 555.6
    DPI, au-dessus de l'impression (300) ». Or l'îlot est rempli par le moteur
    de rendu, qui travaille à `g.dpi` : à 2048, l'îlot recto fait 1004 x 1925 px
    pour une source rognée de 744 x 1039 px, soit un AGRANDISSEMENT de x1,349 et
    x1,853. On ne dépasse pas sa source en l'étirant : l'information reste à
    300 DPI, et 44 % des pixels de l'îlot n'achètent rien.

    Trois nombres différents, donc trois noms différents, et un seul a le droit
    d'être comparé à 300 :
      `dpi`           densité de TEXELS. C'est elle qu'écrit le chunk pHYs des
                      PNG livrés — annoncer autre chose que ce que portent les
                      octets serait le même mensonge à l'envers.
      `dpi_source`    densité du rendu qui remplit l'îlot (`trim_px / trim_mm`).
      `dpi_effective` min des deux axes ET de la source : le détail réellement
                      restituable. `print_ok` se prononce sur CELUI-LÀ.

    `anisotropy` dit le reste : les texels ne sont pas carrés (1,373x), le
    détail visible est plafonné par le petit axe."""
    isl = islands_px(res_w, res_h)["front"]
    w_mm, h_mm = g.trim_mm
    ppm = (isl[2] / w_mm if w_mm else 0.0, isl[3] / h_mm if h_mm else 0.0)
    dpi = (ppm[0] * MM_PER_INCH, ppm[1] * MM_PER_INCH)
    src = (g.trim_px[0] / w_mm * MM_PER_INCH if w_mm else 0.0,
           g.trim_px[1] / h_mm * MM_PER_INCH if h_mm else 0.0)
    src_dpi = min(src)
    eff = min(dpi[0], dpi[1], src_dpi)
    up = (isl[2] / g.trim_px[0] if g.trim_px[0] else 0.0,
          isl[3] / g.trim_px[1] if g.trim_px[1] else 0.0)
    lo, hi = min(ppm), max(ppm)
    return {
        "front_px": [isl[2], isl[3]],
        "px_per_mm": [rnd(ppm[0], 2), rnd(ppm[1], 2)],
        "dpi": [rnd(dpi[0], 1), rnd(dpi[1], 1)],
        "canvas_px": list(g.canvas_px),
        # ── ce qui manquait, et qui rend le vert honnête ────────────────────
        "source_px": list(g.trim_px),
        "dpi_source": rnd(src_dpi, 1),
        "dpi_effective": rnd(eff, 1),
        # La cible est le DPI DE LA CARTE, pas 300 en dur : un jeu réglé à 600
        # doit être jugé sur 600. La tolérance d'1 DPI est l'arrondi du pixel
        # (`trim_px = R(88/25.4*300) = 1039` rend 299,9 et non 300,0), pas une
        # marge de confort.
        "dpi_target": int(g.dpi),
        "print_ok": eff >= float(g.dpi) - 1.0,
        "upsample": [rnd(up[0], 3), rnd(up[1], 3)],
        "wasted_px": max(0, isl[2] * isl[3] - g.trim_px[0] * g.trim_px[1]),
        "anisotropy": rnd(hi / lo, 3) if lo > 0 else 0.0,
        # ── LE SUR-ÉCHANTILLONNAGE DEVIENT ACTIONNABLE ──────────────────────
        # `res_fit` est la définition à laquelle l'îlot cesse d'agrandir la
        # source. `useful_pct` dit, à la définition COURANTE, quelle part des
        # texels de l'îlot porte de l'information.
        **_fit_block(g, isl, res_w),
        # ── UN pHYs POUR TROIS ÎLOTS : LA RÉSERVE, CHIFFRÉE ──────────────────
        # Reproche mesuré et fondé : le chunk pHYs des huit PNG porte la densité
        # du RECTO, et un PNG n'a qu'une densité. L'îlot de tranche, lui, couvre
        # ~296,9 mm de périmètre sur 0,32 mm d'épaisseur avec 2048 x 82 px : sa
        # densité réelle est d'un autre ORDRE DE GRANDEUR. Un outil d'impression
        # qui prend le pHYs au pied de la lettre — ce que la notice l'invitait à
        # faire — se trompe donc sur cette zone. On ne peut pas écrire trois
        # densités dans un chunk qui n'en accepte qu'une : on écrit celle du
        # recto (la seule qui compte pour la face imprimée) et on CHIFFRE
        # l'écart, dans le tEXt du PNG, dans le manifeste et à l'écran.
        **_edge_density(g, res_w, res_h, th_mm, mesh),
    }


def _fit_block(g: CardGeom, isl: list, res_w: int) -> dict:
    """Ce que la définition courante gaspille, et celle qui ne gaspille pas."""
    have = isl[2] * isl[3]
    src = int(g.trim_px[0]) * int(g.trim_px[1])
    fit = res_fit(g)
    out = {
        "useful_px": min(src, have),
        "useful_pct": rnd(100.0 * min(src, have) / have, 1) if have else 0.0,
        "res_fit": fit,
        "upsample_now": [rnd(isl[2] / g.trim_px[0], 3) if g.trim_px[0] else 0.0,
                         rnd(isl[3] / g.trim_px[1], 3) if g.trim_px[1] else 0.0],
    }
    if not fit:
        out["fit_note"] = ("Aucune definition entre "
                           f"{RES_MIN} et {RES_MAX} px ne contient la coupe "
                           "sans la reduire.")
        return out
    f = islands_px(fit, fit)["front"]
    out["fit_front_px"] = [f[2], f[3]]
    out["fit_upsample"] = [rnd(f[2] / g.trim_px[0], 3) if g.trim_px[0] else 0.0,
                           rnd(f[3] / g.trim_px[1], 3) if g.trim_px[1] else 0.0]
    out["fit_texels"] = fit * fit
    out["texels"] = res_w * res_w
    out["fit_gain_pct"] = (rnd(100.0 * (res_w * res_w - fit * fit)
                               / (res_w * res_w), 1) if res_w else 0.0)
    # ── LA PHRASE DOIT SUIVRE LE SENS, ET ELLE NE LE SUIVAIT PAS ────────────
    # Mesuré le 12/08 à 1024 px : cette note écrivait « l'atlas perd -119.8 %
    # de ses texels ». Un pourcentage négatif de perte est un gain, et une
    # phrase qui dit le contraire de son nombre est un chiffre faux. Sous la
    # définition juste on ne gaspille pas : on RÉDUIT la coupe, c'est-à-dire
    # qu'on jette de l'information. Deux situations opposées, deux phrases.
    out["fit_direction"] = ("egal" if fit == res_w else
                            "trop_grand" if res_w > fit else "trop_petit")
    queue = (f" L'agrandissement en hauteur ({out['fit_upsample'][1]}x) ne "
             "descend pas a 1 : c'est l'anisotropie du rectangle du contrat, "
             "et cette piece n'a pas le droit de redecouper l'atlas.")
    if fit == res_w:
        out["fit_note"] = (
            f"Definition JUSTE : l'ilot recto fait {f[2]} x {f[3]} px et "
            "contient la coupe sans l'agrandir en largeur." + queue)
    elif res_w > fit:
        out["fit_note"] = (
            f"A {fit} px, l'ilot recto fait {f[2]} x {f[3]} px : il cesse "
            f"d'agrandir la coupe en largeur ({out['fit_upsample'][0]}x) et "
            f"l'atlas perd {out['fit_gain_pct']} % de ses texels SANS perdre "
            "un pixel d'information." + queue)
    else:
        out["fit_note"] = (
            f"Cette definition REDUIT la coupe (x{out['upsample_now'][0]} en "
            f"largeur) : de l'information est jetee avant meme l'encodage. A "
            f"{fit} px, l'ilot fait {f[2]} x {f[3]} px et la contient entiere ;"
            f" l'atlas gagne {abs(out['fit_gain_pct'])} % de texels et cesse "
            "d'en jeter." + queue)
    return out


def _edge_density(g: CardGeom, res_w: int, res_h: int,
                  th_mm: float | None = None, mesh: dict | None = None) -> dict:
    """Densité de l'îlot de TRANCHE — celle que le pHYs ne dit pas.

    LE PÉRIMÈTRE EST MESURÉ, plus déduit. Voir `outline_perimeter_mm` : la
    carte a des coins arrondis, `2 x (l + h)` la surestimait de 1,7 % et la
    densité annoncée avec. Sans maillage sous la main (aucun appelant n'est
    dans ce cas aujourd'hui), on retombe sur le rectangle et on l'ÉCRIT, pour
    qu'un chiffre déduit ne se fasse jamais passer pour un chiffre mesuré."""
    e = islands_px(res_w, res_h).get("edge")
    if not e:
        return {}
    th = float(th_mm) if th_mm else THICKNESS_MM_DEFAULT
    w_mm, h_mm = g.trim_mm[0], g.trim_mm[1]
    mesure = outline_perimeter_mm(mesh, h_mm) if isinstance(mesh, dict) else None
    perim = float(mesure) if mesure and mesure > 0 else 2.0 * (w_mm + h_mm)
    src = "maillage livre" if mesure else "rectangle a coins vifs (estimation)"
    dx = e[2] / perim * MM_PER_INCH if perim else 0.0     # le long du perimetre
    dy = e[3] / th * MM_PER_INCH if th else 0.0           # en travers
    lo, hi = (dx, dy) if dx <= dy else (dy, dx)
    return {
        "edge_px": [e[2], e[3]],
        "edge_dpi": [rnd(dx, 1), rnd(dy, 1)],
        "edge_perim_mm": rnd(perim, 2),
        "edge_perim_source": src,
        "edge_ratio": rnd(hi / lo, 1) if lo > 0 else 0.0,
        "edge_note": (
            f"L'ilot de tranche fait {e[2]} x {e[3]} px pour un perimetre de "
            f"{rnd(perim, 2)} mm (mesure sur le contour du {src}, coins "
            f"arrondis compris) sur {rnd(th, 3)} mm d'epaisseur : "
            f"{rnd(dx, 1)} DPI le long du perimetre contre {rnd(dy, 1)} DPI en "
            "travers. Le chunk pHYs porte la densite du RECTO et ne vaut donc "
            "PAS pour cette zone."),
    }


def _jpeg(img, q: int, dpi: tuple[float, float] | None = None) -> bytes:
    """JPEG d'une texture — AVEC SA DENSITÉ.

    LE DÉFAUT, MESURÉ : les PNG du ZIP portent `pHYs` (404,8 x 555,6 DPI) et le
    JPEG du GLB — le fichier le plus téléchargé des cinq — sortait à la densité
    JFIF par défaut, c'est-à-dire `(1, 1)` sans unité : la définition tombait en
    silence au moment précis où l'on change de codec. Sans conséquence sur le
    rendu 3D, mais c'est une métadonnée perdue sans un mot.

    JFIF n'admet qu'une densité ENTIÈRE (deux entiers 16 bits + une unité) : on
    écrit donc l'arrondi, et `_encode` publie l'écart mesuré au lieu de laisser
    croire que les deux fichiers portent le même nombre."""
    buf = io.BytesIO()
    kw = {}
    if dpi and dpi[0] > 0 and dpi[1] > 0:
        kw["dpi"] = (dpi[0], dpi[1])
    img.convert("RGB").save(buf, format="JPEG", quality=int(q),
                            subsampling=0, optimize=True, **kw)
    return buf.getvalue()


def jpeg_density(data: bytes) -> tuple[int, int, int] | None:
    """(x, y, unité) lus dans le segment APP0/JFIF du JPEG livré. 1 = DPI."""
    if data[:2] != b"\xff\xd8":
        return None
    off = 2
    while off + 4 <= len(data):
        if data[off] != 0xFF:
            return None
        marker = data[off + 1]
        ln = int.from_bytes(data[off + 2:off + 4], "big")
        if marker == 0xE0 and data[off + 4:off + 8] == b"JFIF":
            unit = data[off + 11]
            x = int.from_bytes(data[off + 12:off + 14], "big")
            y = int.from_bytes(data[off + 14:off + 16], "big")
            return (x, y, unit)
        if marker in (0xDA, 0xD9):
            return None
        off += 2 + ln
    return None


def _encode(img, kind: str, opt: dict,
            dpi: tuple[float, float] | None = None) -> tuple[bytes, dict]:
    """Octets d'une texture DU GLB, et le compte-rendu de l'encodage.

    « auto » n'est pas une devinette : les DEUX codecs sont produits et le plus
    léger gagne. Une illustration de carte est de l'aplat et du trait — le PNG
    y est souvent PLUS PETIT que le JPEG q92 (mesuré : 183 Ko contre 313 Ko sur
    l'atlas d'essai) — alors qu'une face photographique inverse le résultat.
    Un défaut fixe se serait trompé une fois sur deux, en silence.

    `normal` et `orm` restent TOUJOURS en PNG : le JPEG déplace les valeurs de
    canal, et sur une normal map cela penche les normales, sur une ORM cela
    déplace la rugosité et la métallicité. Le ZIP, lui, est PNG de bout en
    bout."""
    from app.services import material_store as MS
    png = MS.png_bytes(img, kind, 8)
    if kind not in ("basecolor", "emissive") or opt["img"] == "png":
        return png, {"codec": "png", "bytes": len(png), "png": len(png),
                     "jpeg": None}
    jpg = _jpeg(img, opt["jpeg_q"], dpi)
    if opt["img"] == "jpeg" or len(jpg) < len(png):
        # La densité écrite est RELUE dans le segment JFIF du fichier produit,
        # avec l'écart d'arrondi : JFIF n'accepte que des entiers, le PNG porte
        # 404,8 x 555,6 DPI et le JPEG ne peut écrire que 405 x 556.
        den = jpeg_density(jpg)
        rep = {"codec": "jpeg", "bytes": len(jpg), "png": len(png),
               "jpeg": len(jpg), "quality": int(opt["jpeg_q"]),
               "jfif_density": list(den) if den else None}
        if den and dpi:
            rep["dpi_ecart_pct"] = [
                rnd(abs(den[0] - dpi[0]) / dpi[0] * 100.0, 3) if dpi[0] else 0.0,
                rnd(abs(den[1] - dpi[1]) / dpi[1] * 100.0, 3) if dpi[1] else 0.0]
            rep["dpi_note"] = (
                f"JFIF n'admet qu'une densite ENTIERE : {den[0]} x {den[1]} DPI "
                f"ecrits pour {rnd(dpi[0], 1)} x {rnd(dpi[1], 1)} DPI dans le "
                "pHYs des PNG. Avant, le JPEG sortait sans densite du tout.")
        return jpg, rep
    return png, {"codec": "png", "bytes": len(png), "png": len(png),
                 "jpeg": len(jpg)}


# ═══════════════════════════════════════════════════════════════════════════
# 5 bis. LES PNG DU ZIP : CE QU'ILS DISENT D'EUX-MÊMES
# ═══════════════════════════════════════════════════════════════════════════
# DEUX DÉFAUTS MESURÉS, corrigés ici, et aucun ne touche `material_store` :
#
# (a) AUCUN CHUNK COLORIMÉTRIQUE NI PHYSIQUE. Inventaire des chunks des huit
#     PNG livrés le 11/08 : IHDR, IDAT, IEND — rien d'autre. Un outil qui ouvre
#     le ZIP devait donc DEVINER que basecolor et emissive sont en sRGB et que
#     roughness / metallic / ao / height / normal sont linéaires ; et surtout,
#     sans `pHYs`, il n'existe AUCUNE définition dans le fichier. Le panneau
#     annonçait « 404.8 x 555.6 DPI » et le PNG, une fois glissé dans un outil
#     d'impression, n'en portait pas la moindre trace : toute revendication de
#     définition tombait au premier import. Les trois chunks coûtent 13, 12 et
#     21 octets.
#
# (b) LE « 16 BITS » ÉTAIT UN ÉLARGISSEMENT. `material_store._png16` duplique
#     l'octet (`v -> v*257`) : l'IHDR annonçait 16 bits et les 12 582 912
#     échantillons de normal.png tombaient TOUS sur le réseau k*257, sans une
#     exception — 155 niveaux distincts, 7,28 bits utiles. Coût mesuré : le
#     réencodage 8 bits SANS PERTE rendait 47,0 % sur normal et 44,3 % sur
#     height. On ne devine plus : `map_png` LIT la profondeur de la source (le
#     mode PIL), n'écrit 16 bits que si elle en porte, et écrit dans le
#     manifeste la profondeur RÉELLE, le nombre de niveaux distincts et le
#     surcoût mesuré quand l'utilisateur force quand même.

_SRGB_MAPS = ("basecolor", "emissive")


def _png_chunk(typ: bytes, data: bytes) -> bytes:
    import binascii
    import struct
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF))


def png_chunk_types(data: bytes) -> list[str]:
    """Les types de chunk d'un PNG, dans l'ordre. Sert à PROUVER que pHYs et
    sRGB/gAMA sont là — le test lit les octets, pas une intention."""
    import struct
    out, off = [], 8
    while off + 8 <= len(data):
        ln = struct.unpack(">I", data[off:off + 4])[0]
        out.append(data[off + 4:off + 8].decode("latin-1", "replace"))
        off += 12 + ln
    return out


def png_phys(data: bytes) -> tuple[int, int] | None:
    """(px/m en x, px/m en y) lus dans le chunk pHYs, ou None."""
    import struct
    off = 8
    while off + 8 <= len(data):
        ln = struct.unpack(">I", data[off:off + 4])[0]
        if data[off + 4:off + 8] == b"pHYs" and ln >= 9:
            x, y, unit = struct.unpack(">IIB", data[off + 8:off + 17])
            return (x, y) if unit == 1 else None
        off += 12 + ln
    return None


def png_decorate(data: bytes, kind: str, ppm: tuple[float, float],
                 caveat: str = "") -> bytes:
    """Insère pHYs (+ sRGB ou gAMA, + un tEXt qui dit l'espace) après l'IHDR.

    `ppm` est la densité de la FACE en pixels par millimètre — exactement celle
    que l'écran affiche. Un outil d'impression qui ouvre basecolor.png lira donc
    le chiffre du panneau, pas un autre.

    `caveat` porte la RÉSERVE que le chunk lui-même ne peut pas porter : un PNG
    n'a qu'une densité, l'atlas en a trois. Elle voyage dans le tEXt, avec les
    chiffres de l'îlot de tranche — sans quoi un outil d'impression prend le
    pHYs au pied de la lettre sur une zone où il est faux d'un ordre de
    grandeur."""
    import struct
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return data
    ihdr_len = struct.unpack(">I", data[8:12])[0]
    cut = 8 + 12 + ihdr_len
    px = max(1, int(round(ppm[0] * 1000.0)))
    py = max(1, int(round(ppm[1] * 1000.0)))
    add = _png_chunk(b"pHYs", struct.pack(">IIB", px, py, 1))
    if kind in _SRGB_MAPS:
        add += _png_chunk(b"sRGB", b"\x00")
        add += _png_chunk(b"gAMA", struct.pack(">I", 45455))
        space = b"sRGB"
    else:
        add += _png_chunk(b"gAMA", struct.pack(">I", 100000))
        space = b"lineaire (gamma 1.0) - donnee, pas une couleur"
    # Le tEXt dit L'ESPACE DE COULEUR, pas qui a écrit le fichier : c'est
    # l'information dont un moteur a besoin et que le PNG ne code nulle part
    # ailleurs quand la map est linéaire.
    add += _png_chunk(b"tEXt", b"Comment\x00espace de couleur : " + space)
    if caveat:
        add += _png_chunk(b"tEXt", b"Warning\x00"
                          + caveat.encode("latin-1", "replace")[:900])
    return data[:cut] + add + data[cut:]


# ═══════════════════════════════════════════════════════════════════════════
# 5 ter. LES 16 BITS — PRODUITS, PAS ÉLARGIS
# ═══════════════════════════════════════════════════════════════════════════
# LE MENSONGE QUE CE BLOC SUPPRIME. Un audit a redécodé `normal.png` à la main
# (zlib puis défiltrage) : l'IHDR annonçait 16 bits et les 12 582 912
# échantillons tombaient TOUS sur le réseau k*257 — 200 valeurs distinctes,
# 7,64 bits utiles. C'était une map 8 bits élargie, un octet dupliqué. Le tour
# précédent avait répondu en AVERTISSANT mieux ; c'était encore la mauvaise
# réponse : « un bordereau qui dénonce un gaspillage que l'outil vient de
# commettre reste un gaspillage ».
#
# On ne dilate plus rien. `height` et `normal` sont RE-DÉRIVÉS ICI, en virgule
# flottante, avec exactement les mêmes formules que la dérivation 8 bits (même
# rayon de flou, même autocontraste, même Sobel, même renormalisation) —
# seulement sans repasser par un octet entre chaque étape. Un flou est une
# moyenne pondérée : la moyenne de voisins 8 bits n'est PAS un nombre 8 bits,
# et c'est très exactement l'information qu'un conteneur élargi jetait.
#
# Les deux garde-fous, tous deux mesurés sur les octets écrits :
#   * on ne publie « 16 bits » que si le PNG livré porte PLUS de 256 valeurs
#     distinctes ET des échantillons hors du réseau k*257. Sinon on REFUSE le
#     conteneur et on livre 8 bits, en disant pourquoi (`png_16_or_8`).
#   * l'écart avec la map 8 bits de référence est mesuré à chaque construction
#     et publié : si les deux divergeaient, ce ne serait plus la même map.
_DEEP_PASSES = 3
# Au-delà, le gain de précision ne paie plus le temps ; en deçà, le flou de
# référence n'est pas reproduit. Trois passes = le choix de la pile d'images.


def _fe(fn, **kw):
    """`ImageMath.lambda_eval` — l'arithmétique d'image en C, mode « F »."""
    from PIL import ImageMath
    return ImageMath.lambda_eval(fn, **kw)


def _clamp_f(im, lo: float, hi: float):
    return _fe(lambda e: e["min"](e["max"](e["a"], e["lo"]), e["hi"]),
               a=im, lo=float(lo), hi=float(hi))


def box_radius(radius: float, passes: int = _DEEP_PASSES) -> float:
    """Le rayon de boîte qui approche un flou gaussien d'écart-type `radius`.

    C'est la formule de Gwosdek et al. (2011), celle-là même qu'utilise la pile
    d'images pour son flou gaussien : trois passes de boîte FRACTIONNAIRE. On
    la reprend pour que la version flottante rende la MÊME image que la version
    8 bits, à la précision près — pas une image voisine."""
    s2 = float(radius) * float(radius) / passes
    ln = math.floor((math.sqrt(12.0 * s2 + 1.0) - 1.0) / 2.0)
    a = (2 * ln + 1) * (ln * (ln + 1) - 3 * s2) / (6 * (s2 - (ln + 1) ** 2))
    return ln + a


def _box1d_f(im, r: float, dx: int, dy: int):
    """Boîte fractionnaire CYCLIQUE sur un axe, en flottant.

    Cyclique parce que la dérivation de référence l'est : les maps doivent
    rester raccordables. `offset` reboucle, ce qui est exactement le bord
    voulu — et gratuit."""
    from PIL import ImageChops
    n = int(math.floor(r))
    frac = r - n
    acc = im
    for k in range(1, n + 1):
        acc = _fe(lambda e: e["a"] + e["b"] + e["c"], a=acc,
                  b=ImageChops.offset(im, dx * k, dy * k),
                  c=ImageChops.offset(im, -dx * k, -dy * k))
    if frac > 0:
        acc = _fe(lambda e: e["a"] + (e["b"] + e["c"]) * e["f"], a=acc,
                  b=ImageChops.offset(im, dx * (n + 1), dy * (n + 1)),
                  c=ImageChops.offset(im, -dx * (n + 1), -dy * (n + 1)),
                  f=float(frac))
    return _fe(lambda e: e["a"] * e["k"], a=acc, k=1.0 / (2.0 * r + 1.0))


def gauss_f(im, radius: float, passes: int = _DEEP_PASSES):
    """Flou gaussien en virgule flottante, bords cycliques."""
    r = box_radius(radius, passes)
    for _ in range(passes):
        im = _box1d_f(im, r, 1, 0)
        im = _box1d_f(im, r, 0, 1)
    return im


def autocontrast_window(im_f, cutoff: int = 1) -> tuple[int, int]:
    """Les bornes (lo, hi) que l'autocontraste 8 bits choisirait.

    On les calcule sur l'histogramme 8 bits de la même image : la fenêtre de
    normalisation est donc IDENTIQUE à celle de la map 8 bits. Seule la
    quantification change — ce qui est tout l'objet de ce bloc."""
    h = im_f.convert("L").histogram()
    n = sum(h)
    cut = int(n * cutoff // 100)
    for lo in range(256):
        if cut > h[lo]:
            cut -= h[lo]
            h[lo] = 0
        else:
            h[lo] -= cut
            cut = 0
        if cut <= 0:
            break
    cut = int(n * cutoff // 100)
    for hi in range(255, -1, -1):
        if cut > h[hi]:
            cut -= h[hi]
            h[hi] = 0
        else:
            h[hi] -= cut
            cut = 0
        if cut <= 0:
            break
    lo = next((i for i in range(256) if h[i]), 0)
    hi = next((i for i in range(255, -1, -1) if h[i]), 255)
    return lo, hi


def derive_deep(atlas, derive: dict) -> dict | None:
    """`height` et `normal` en virgule flottante, 0..255, mêmes formules.

    Rend `{"height": F, "normal": (Fx, Fy, Fz), "ms": …}` — des canaux
    flottants, pas des octets : c'est `png16_bytes` qui quantifie, en 16 bits,
    une seule fois, à la toute fin."""
    try:
        from PIL import ImageChops                # noqa: F401  (present ?)
        from app.services import pbr_service as PBR
        d = PBR.normalize_derive(derive)
    except Exception:                             # pragma: no cover - env cassé
        return None
    t0 = time.perf_counter()
    try:
        lum = atlas.convert("F")
        # ── height : luminance -> flou cyclique -> autocontraste (clip 1 %)
        radius = 1.0 + 3.0 * (1.0 - d["height_detail"])
        blur = gauss_f(lum, radius)
        lo, hi = autocontrast_window(blur, 1)
        if hi <= lo:
            hgt = blur
        else:
            hgt = _fe(lambda e: (e["a"] - e["lo"]) * e["k"],
                      a=blur, lo=float(lo), k=255.0 / (hi - lo))
        hgt = _clamp_f(hgt, 0.0, 255.0)
        # ── normal : Sobel de la hauteur, puis x²+y²+z² = 1
        gx, gy = _sobel_f(hgt)
        s = float(d["normal_strength"]) * 4.0
        sign = -1.0 if d["normal_invert_y"] else 1.0
        nx = _clamp_f(_fe(lambda e: 128.0 - e["g"] * e["s"], g=gx, s=s), 0.0, 255.0)
        ny = _clamp_f(_fe(lambda e: 128.0 + e["g"] * e["s"] * e["w"],
                          g=gy, s=s, w=sign), 0.0, 255.0)
        ux = _fe(lambda e: (e["a"] - 128.0) * (1.0 / 127.0), a=nx)
        uy = _fe(lambda e: (e["a"] - 128.0) * (1.0 / 127.0), a=ny)
        sq = _clamp_f(_fe(lambda e: e["x"] * e["x"] + e["y"] * e["y"],
                          x=ux, y=uy), 0.0, 1.0)
        nz = _fe(lambda e: ((1.0 - e["s"]) ** 0.5) * 255.0, s=sq)
    except Exception as exc:                      # pragma: no cover - env cassé
        logger.warning("cards/gltf: derivation 16 bits indisponible ({})", exc)
        return None
    return {"height": (hgt,), "normal": (nx, ny, nz),
            "ms": int((time.perf_counter() - t0) * 1000)}


def _sobel_f(h):
    """(d/dx, d/dy) en niveaux par pixel — le Sobel de la dérivation 8 bits,
    même noyau, même division par 8, sans l'aller-retour par un octet."""
    from PIL import ImageChops

    def n(dx, dy):
        # `offset` déplace le CONTENU : (-dx,-dy) va donc chercher le voisin
        # (+dx,+dy). Vérifié par réponse impulsionnelle dans les tests.
        return ImageChops.offset(h, -dx, -dy)

    gx = _fe(lambda e: ((e["a"] + 2 * e["b"] + e["c"])
                        - (e["d"] + 2 * e["f"] + e["g"])) * 0.125,
             a=n(1, -1), b=n(1, 0), c=n(1, 1),
             d=n(-1, -1), f=n(-1, 0), g=n(-1, 1))
    gy = _fe(lambda e: ((e["a"] + 2 * e["b"] + e["c"])
                        - (e["d"] + 2 * e["f"] + e["g"])) * 0.125,
             a=n(-1, 1), b=n(0, 1), c=n(1, 1),
             d=n(-1, -1), f=n(0, -1), g=n(1, -1))
    return gx, gy


# ── L'ÉCRITURE 16 BITS, ET SA RELECTURE ────────────────────────────────────
# Le PNG est écrit ICI et pas par la pile d'images, pour deux raisons :
#   * aucun mode d'image standard ne porte du RVB 16 bits — la normale n'a
#     donc aucun encodeur tout fait, et l'octet dupliqué était né de là ;
#   * on choisit le filtre. « Up » (type 2) coûte 0,2 s et rend le fichier
#     43 % plus petit que le filtre nul, tout en restant défiltrable en
#     O(log h) opérations d'image (`_undo_up`) — donc RELISIBLE par nous, sur
#     les octets livrés, à chaque construction.
def _be16_planes(im_f):
    """(octets forts, octets faibles) d'un canal flottant 0..255 porté sur
    0..65535. Arrondi, pas troncature : `+0.5` avant la conversion entière."""
    i32 = _fe(lambda e: e["min"](e["max"](e["a"] * e["k"] + 0.5, 0.0), 65535.0),
              a=im_f, k=65535.0 / 255.0).convert("I")
    b = i32.tobytes()                              # int32, petit-boutiste
    return b[1::4], b[0::4]


def png16_samples(chans) -> tuple[bytes, int, int, int]:
    """Le tableau d'échantillons 16 bits gros-boutistes, entrelacé — c'est-à-
    dire EXACTEMENT ce que le PNG contiendra une fois défiltré."""
    w, h = chans[0].size
    n = len(chans)
    buf = bytearray(w * n * 2 * h)
    for ci, c in enumerate(chans):
        hi, lo = _be16_planes(c)
        buf[ci * 2::n * 2] = hi
        buf[ci * 2 + 1::n * 2] = lo
    return bytes(buf), w, h, n


def _up_filter(px: bytes, stride: int, h: int) -> bytes:
    """Le flux filtré « Up » : ligne 0 brute, puis chaque ligne moins la
    précédente, octet par octet, modulo 256."""
    from PIL import Image, ImageChops
    im = Image.frombytes("L", (stride, h), px)
    sh = Image.new("L", (stride, h))
    sh.paste(im.crop((0, 0, stride, h - 1)), (0, 1))
    # `subtract_modulo`, pas `subtract` : la soustraction saturante de la pile
    # d'images écrête à 0 et le filtre PNG est modulo 256. Une seule opération
    # en C au lieu de trois — et surtout, la BONNE.
    d = ImageChops.subtract_modulo(im, sh).tobytes()
    rows = [b"\x00" + px[:stride]]
    rows += [b"\x02" + d[y * stride:(y + 1) * stride] for y in range(1, h)]
    return b"".join(rows)


def _undo_up(filtered: bytes, stride: int, h: int) -> bytes:
    """Défiltrage « Up » en O(log h) : somme préfixe par doublement.

    Ligne à ligne, ce serait 2048 boucles Python sur 12 Ko — deux secondes et
    demie. Par doublement, onze opérations d'image en C : la relecture des
    octets livrés redevient assez peu chère pour être faite À CHAQUE
    construction, ce qui est tout l'intérêt."""
    from PIL import Image, ImageChops
    im = Image.frombytes("L", (stride, h), filtered)
    k = 1
    while k < h:
        sh = Image.new("L", (stride, h))
        sh.paste(im.crop((0, 0, stride, h - k)), (0, k))
        im = ImageChops.add_modulo(im, sh)
        k *= 2
    return im.tobytes()


def png16_bytes(chans) -> bytes:
    """Un PNG 16 bits (gris ou RVB) écrit par cette pièce."""
    import struct
    px, w, h, n = png16_samples(chans)
    stride = w * n * 2
    ctype = {1: 0, 3: 2}[n]
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, ctype,
                                              0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(_up_filter(px, stride, h), 6))
            + _png_chunk(b"IEND", b""))


def depth_verdict(depth: dict) -> dict:
    """CE QUE LES DEUX MAPS PROFONDES PORTENT VRAIMENT, en une ligne.

    Aucune mention d'un document interne, aucun inventaire de la machine hôte :
    seulement ce que les octets livrés disent d'eux-mêmes."""
    rows = {}
    for k in ("height", "normal"):
        d = depth.get(k) or {}
        if not d:
            continue
        rows[k] = {"bits": d.get("bits"), "levels": d.get("levels"),
                   "bits_effective": d.get("bits_effective"),
                   "real16": bool(d.get("real16")),
                   "refused16": bool(d.get("refused16")),
                   "lattice_pct": d.get("lattice_pct"),
                   "cost_16": d.get("cost_16", 0),
                   "accord_8": d.get("accord_8")}
    if not rows:
        return {"delivered": {}, "deep": False, "cost_bytes": 0, "verdict": ""}
    deep = all(v["real16"] for v in rows.values())
    cost = sum(int(v.get("cost_16") or 0) for v in rows.values())
    if deep:
        gain = " et ".join(f"{k} {v['levels']} niveaux" for k, v in rows.items())
        txt = (f"16 bits REELS sur height et normal : {gain}, mesures dans le "
               f"PNG livre (zlib + defiltrage). Cout : +{cost} octets pour une "
               "profondeur qui existe.")
    elif all(v["bits"] == 8 for v in rows.values()):
        # DEUX SITUATIONS, DEUX PHRASES — et l'une des deux était FAUSSE.
        # Ce verdict écrivait « le conteneur 16 bits a donc ete REFUSE » y
        # compris quand la case n'avait PAS été cochée : le manifeste et le
        # LISEZMOI racontaient alors un refus qui n'avait jamais eu lieu, et
        # une dérivation profonde qui n'avait jamais tourné. Mesuré le 12/08
        # sur un export `bits16=false`. On lit donc le drapeau au lieu de
        # supposer.
        if any(v.get("refused16") for v in rows.values()):
            txt = ("8 bits sur height et normal : les 16 bits ont ete DEMANDES "
                   "puis REFUSES — les octets ecrits ne portaient pas plus de "
                   "256 valeurs distinctes. Un conteneur vide coute des octets "
                   "et n'ajoute aucun niveau.")
        else:
            txt = ("8 bits sur height et normal : les 16 bits n'ont pas ete "
                   "demandes (case decochee). La profondeur reste MESUREE dans "
                   "les octets livres : " + ", ".join(
                       f"{k} {v['levels']} niveaux distincts"
                       for k, v in rows.items()) + ".")
    else:
        txt = ("Profondeurs melangees : " + ", ".join(
            f"{k} {v['bits']} bits / {v['levels']} niveaux"
            for k, v in rows.items()) + ".")
    return {"delivered": rows, "deep": deep, "cost_bytes": cost,
            "verdict": txt}


def png_source_bits(img) -> int:
    """Profondeur RÉELLE de la source, lue sur le mode PIL. `L` et `RGB`
    portent 8 bits par canal : les élargir n'ajoute que des octets."""
    return 16 if str(getattr(img, "mode", "")) in ("I", "I;16", "I;16B", "F") else 8


def png_levels(img) -> int:
    """Niveaux distincts du canal LE PLUS RICHE — pas de la luminance.

    Convertir une normal map en L avant de compter écraserait trois canaux en
    un et sous-estimerait la profondeur : on compte donc par canal et on garde
    le maximum. C'est la mesure qui contredisait le badge « 16 bits » : 155
    niveaux sur normal.png, 208 sur height.png, jamais 65 536."""
    try:
        h = img.histogram()
        n = max(1, len(h) // 256)
        return max(sum(1 for c in h[k * 256:(k + 1) * 256] if c)
                   for k in range(n))
    except Exception:                          # pragma: no cover - env cassé
        return 0


def png_probe(data: bytes) -> dict:
    """CE QUE LE PNG CONTIENT VRAIMENT — décodé, pas lu dans l'en-tête.

    LE MENSONGE QUE CECI REND IMPOSSIBLE. Un audit a relu `normal.png` à la
    main : l'IHDR annonçait 16 bits et les 12 582 912 échantillons tombaient
    TOUS sur le réseau k*257 — 202 valeurs distinctes, 7,66 bits utiles. Deux
    verdicts successifs se sont contredits sur le même octet, l'un ayant lu
    l'en-tête et s'étant arrêté là. Lire l'IHDR ne prouve RIEN sur la
    profondeur des DONNÉES : il faut désentrelacer le zlib et regarder les
    échantillons.

    On le fait ici, sur les octets qui partent dans l'archive :
      `bits_container`  la profondeur déclarée par l'IHDR ;
      `levels`          le nombre de valeurs distinctes RÉELLEMENT présentes ;
      `lattice_pct`     en 16 bits, le pourcentage d'échantillons de la forme
                        k*257 (octet fort == octet faible). 100,0 % = c'est
                        une map 8 bits élargie, sans une exception ;
      `real16`          vrai UNIQUEMENT si un échantillon au moins sort de ce
                        réseau. C'est LUI qui autorise le mot « réels ».

    Le décodage rapide exige des lignes en filtre 0 — c'est le cas de tout ce
    que cette pièce écrit en 16 bits. Sinon on rend `decoded=False` et
    l'appelant retombe sur la mesure faite sur l'image source (le PNG est sans
    perte : les deux coïncident, mais on ne prétend pas avoir relu le fichier).
    """
    import struct as _s
    out: dict = {"decoded": False}
    try:
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return out
        off, idat = 8, []
        w = h = bits = ctype = 0
        while off + 8 <= len(data):
            ln = _s.unpack(">I", data[off:off + 4])[0]
            typ = data[off + 4:off + 8]
            if typ == b"IHDR":
                w, h, bits, ctype = _s.unpack(">IIBB", data[off + 8:off + 18])
            elif typ == b"IDAT":
                idat.append(data[off + 8:off + 8 + ln])
            off += 12 + ln
        out.update({"bits_container": bits, "w": w, "h": h})
        nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype, 1)
        stride = w * nch * bits // 8
        raw = zlib.decompress(b"".join(idat))
        if len(raw) != h * (stride + 1):
            return out
        # Les deux SEULS filtrages que cette pièce écrit, donc les deux seuls
        # qu'elle prétend relire : nul partout (les PNG 8 bits qu'elle passe à
        # la pile d'images), ou « Up » à partir de la 2e ligne (ses PNG 16
        # bits). Tout autre filtrage rend `decoded=False` : on ne devine pas.
        heads = raw[0::stride + 1]
        px = b"".join([raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
                       for y in range(h)])
        if heads == b"\x00" * h:
            out["filter"] = "nul"
        elif heads == b"\x00" + b"\x02" * (h - 1):
            px = _undo_up(px, stride, h)
            out["filter"] = "up"
        else:
            return out
        out["decoded"] = True
        out["samples"] = w * h * nch
        # UNE SEULE DÉFINITION DE « NIVEAUX », partout : le nombre de valeurs
        # distinctes du canal LE PLUS RICHE. Compter les trois canaux en vrac
        # donne un autre nombre (249 contre 217 sur emissive.png, mesuré) — et
        # deux nombres pour la même colonne d'un même tableau, c'est déjà une
        # contradiction. `levels_pooled` reste publié, nommé.
        if bits == 16:
            hi, lo = px[0::2], px[1::2]
            xr = (int.from_bytes(hi, "big") ^ int.from_bytes(lo, "big"))
            on = xr.to_bytes(len(hi), "big").count(0)
            # `cast("H")` lit dans l'ordre de la MACHINE alors que PNG est
            # gros-boutiste : les valeurs sortent permutees. On ne s'en sert
            # QUE pour des COMPTES de valeurs distinctes, et une permutation
            # d'octets est une bijection — le cardinal ne bouge pas. Aucun de
            # ces nombres n'est jamais compare a un niveau 8 bits.
            mv = memoryview(px).cast("H")
            per = [len(set(mv[c::nch])) for c in range(nch)]
            out["on_lattice"] = on
            out["off_lattice"] = len(hi) - on
            out["lattice_pct"] = rnd(100.0 * on / max(1, len(hi)), 3)
            out["real16"] = out["off_lattice"] > 0
            out["levels_pooled"] = len(set(mv))
        else:
            per = [len(set(px[c::nch])) for c in range(nch)]
            out["lattice_pct"] = None
            out["real16"] = False
            out["levels_pooled"] = len(set(px))
        out["levels_per_channel"] = per
        out["levels"] = max(per)
    except Exception:                          # pragma: no cover - PNG exotique
        return {"decoded": False}
    return out


def png_levels_bytes(data: bytes) -> dict:
    """Niveaux relus dans le PNG LIVRÉ, quel que soit son filtrage.

    Le décodeur maison ci-dessus exige des lignes en filtre 0 — c'est le cas
    de nos 16 bits, pas de ce que Pillow écrit en 8 bits (filtres adaptatifs).
    Pour ceux-là, on RE-OUVRE les octets produits avec Pillow, qui défiltre en
    C : c'est toujours une lecture du FICHIER, pas de l'image de départ. On ne
    le fait pas en 16 bits RVB, où Pillow tronque à 8 — c'est précisément pour
    ce cas que le décodeur maison existe."""
    pr = png_probe(data)
    if pr.get("decoded"):
        return pr
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            if str(im.mode) in ("I", "I;16", "I;16B", "F"):
                return pr                       # 16 bits : jamais via Pillow
            hist = im.histogram()
            n = max(1, len(hist) // 256)
            per = [sum(1 for c in hist[k * 256:(k + 1) * 256] if c)
                   for k in range(n)]
        return {"decoded": True, "bits_container": 8, "levels": max(per),
                "levels_per_channel": per, "lattice_pct": None,
                "real16": False, "via": "pillow"}
    except Exception:                          # pragma: no cover - env cassé
        return pr


def _accord_8(chans, ref8) -> dict | None:
    """L'ÉCART entre la map profonde et la map 8 bits de référence.

    Les deux doivent être LA MÊME IMAGE, à la quantification près : si elles
    divergeaient, on aurait remplacé la map de l'utilisateur par une autre
    sous prétexte de précision. On requantifie donc la version flottante en 8
    bits et on compare, canal par canal, sur les pixels."""
    try:
        from PIL import Image, ImageChops
        # ON REQUANTIFIE PAR LE MÊME CHEMIN QUE LE FICHIER : flottant -> entier
        # 16 bits (arrondi), puis 16 -> 8 bits (65535 = 255 x 257, donc
        # `(V + 128) // 257` EST l'arrondi). Passer par `convert("L")`, qui
        # tronque, donnait un écart maximal FAUX d'un niveau — et un chiffre
        # faux vaut moins que pas de chiffre.
        def q8(c):
            i16 = _fe(lambda e: e["min"](e["max"](e["a"] * e["k"] + 0.5, 0.0),
                                         65535.0),
                      a=c, k=65535.0 / 255.0).convert("I")
            return _fe(lambda e: (e["a"] + 128) / 257, a=i16).convert("L")

        mine = (q8(chans[0]) if len(chans) == 1 else
                Image.merge("RGB", tuple(q8(c) for c in chans)))
        if mine.size != ref8.size or mine.mode != ref8.mode:
            return None
        hist = ImageChops.difference(mine, ref8).histogram()
        n = max(1, len(hist) // 256)
        per, mean, mx, tot = [], 0.0, 0, 0
        for k in range(n):
            hc = hist[k * 256:(k + 1) * 256]
            t = sum(hc)
            tot += t
            s = sum(i * c for i, c in enumerate(hc))
            m = max((i for i, c in enumerate(hc) if c), default=0)
            mean += s
            mx = max(mx, m)
            per.append({"moyen": rnd(s / max(1, t), 4), "max": int(m)})
        return {"ecart_moyen": rnd(mean / max(1, tot), 4), "ecart_max": int(mx),
                "par_canal": per}
    except Exception:                              # pragma: no cover - env cassé
        return None


def map_png(img, kind: str, force16: bool, ppm: tuple[float, float],
            caveat: str = "", deep=None, ref8=None) -> tuple:
    """Les octets d'un PNG du ZIP, et sa fiche de profondeur MESURÉE SUR EUX.

    `deep` porte les canaux flottants re-dérivés (`derive_deep`) quand cette
    map peut être écrite en 16 bits RÉELS. Sans eux, la case « 16 bits » ne
    déclenche RIEN : élargir un octet en le dupliquant a déjà été fait, mesuré,
    et c'est le mensonge que ce fichier existe pour ne plus commettre."""
    from app.services import material_store as MS
    src_bits = png_source_bits(img)
    lv = png_levels(img)
    want16 = bool(force16) and kind in ("height", "normal")
    # DÉCORÉ des deux côtés : `cost_16` doit être la différence entre les deux
    # fichiers RÉELLEMENT livrables, pas entre un PNG nu et un PNG annoté.
    data8 = png_decorate(MS.png_bytes(img, kind, 8), kind, ppm, caveat)
    rep = {
        "bits_source": src_bits,
        "levels": lv,
        "bits_effective": rnd(math.log2(lv), 2) if lv > 1 else 0.0,
        "widened": False,
        "bytes_8": len(data8),
        "bytes_16": None,
        "cost_16": 0,
        "real16": False,
        "deep": False,
        "measured_on": "image source (PNG sans perte)",
    }

    def as8(why: str) -> tuple:
        """La livraison 8 bits, relue dans le fichier écrit."""
        pr = png_levels_bytes(data8)
        rep["bits"] = 8
        rep["bits_container"] = pr.get("bits_container", 8)
        if pr.get("decoded"):
            rep["levels"] = pr["levels"]
            rep["levels_per_channel"] = pr.get("levels_per_channel")
            rep["bits_effective"] = (rnd(math.log2(pr["levels"]), 2)
                                     if pr["levels"] > 1 else 0.0)
            rep["measured_on"] = ("octets du PNG livre (defiltrage de la pile d'images)"
                                  if pr.get("via") == "pillow" else
                                  "octets du PNG livre (zlib + defiltrage)")
        rep["verdict"] = f"8 bits reels — {rep['levels']} niveaux distincts"
        rep["note"] = why or (
            f"8 bits : {rep['levels']} niveaux distincts, mesures sur "
            f"{rep['measured_on']}.")
        return data8, rep

    if not want16:
        return as8("")

    if not deep:
        # ON REFUSE D'ÉLARGIR. C'est la correction du reproche, à la lettre :
        # « que l'ecrivain REFUSE d'elargir en 16 bits tant que la source ne
        # depasse pas 8 bits ». Sans re-dérivation profonde, les 16 bits ne
        # peuvent être qu'un octet dupliqué — on n'écrit pas le conteneur.
        rep["refused16"] = True
        return as8(
            "16 bits DEMANDES mais REFUSES : sans re-derivation en virgule "
            "flottante, ecrire 16 bits ne ferait que dupliquer chaque octet "
            "(v -> v*257). Le fichier annoncerait une profondeur qu'il n'a "
            "pas ; il sort donc en 8 bits.")

    # LE PRIX COMPLET DES SEIZE BITS, chronométré : l'écriture ET la
    # relecture. Ne compter que la dérivation donnerait un chiffre juste pour
    # une question qu'on ne pose pas.
    _t = time.perf_counter()
    data16 = png_decorate(png16_bytes(deep), kind, ppm, caveat)
    pr = png_probe(data16)
    rep["ms16"] = int((time.perf_counter() - _t) * 1000)
    if not pr.get("decoded"):                      # pragma: no cover - défensif
        rep["refused16"] = True
        return as8("16 bits REFUSES : les octets ecrits n'ont pas pu etre "
                   "relus, donc rien ne prouve leur profondeur.")
    levels = int(pr.get("levels") or 0)
    real = bool(pr.get("real16")) and levels > 256
    if not real:
        # Le conteneur ne porte pas plus que 8 bits : on ne le livre pas.
        rep["refused16"] = True
        rep["refused_levels"] = levels
        rep["refused_bytes"] = len(data16) - len(data8)
        return as8(
            f"16 bits REFUSES : le PNG 16 bits ecrit ne porte que {levels} "
            f"valeurs distinctes pour +{len(data16) - len(data8)} octets. Un "
            "conteneur qui n'ajoute aucun niveau n'est pas une profondeur.")
    rep.update({
        "bits": 16,
        "bits_container": pr.get("bits_container", 16),
        "bytes_16": len(data16),
        "cost_16": len(data16) - len(data8),
        "levels": levels,
        "levels_per_channel": pr.get("levels_per_channel"),
        "levels_8": lv,
        "bits_effective": rnd(math.log2(levels), 2) if levels > 1 else 0.0,
        "lattice_pct": pr.get("lattice_pct"),
        "off_lattice": pr.get("off_lattice"),
        "samples": pr.get("samples"),
        "real16": True,
        "deep": True,
        "filter": pr.get("filter"),
        "measured_on": "octets du PNG livre (zlib + defiltrage)",
    })
    if ref8 is not None:
        rep["accord_8"] = _accord_8(deep, ref8)
    rep["verdict"] = f"16 bits reels — {levels} niveaux distincts"
    rep["note"] = (
        f"16 bits REELS, re-derives en virgule flottante : {levels} valeurs "
        f"distinctes sur {rep.get('samples', 0)} echantillons "
        f"({rep['bits_effective']} bits utiles), dont "
        f"{rep.get('off_lattice', 0)} HORS du reseau k*257 — une map 8 bits "
        f"elargie y tomberait a 100 %. La version 8 bits de la meme map n'en "
        f"porte que {lv}. Cout : +{rep['cost_16']} octets.")
    return data16, rep


def card_extras(g: CardGeom, th_mm: float, res_w: int, res_h: int,
                opt: dict, doc_name: str, idx: int,
                mesh: dict | None = None) -> dict:
    """Ce que le fichier DIT de lui-même. Un GLB qui ne porte pas ses unités
    est un objet flottant, et un modèle 3D qui ne dit pas son nombre de
    triangles ne se compare à rien."""
    w_mm, h_mm = g.trim_mm
    fin = FINISHES.get(opt["finish"]) or FINISHES[DEFAULT_FINISH]
    mrep = mesh_report(mesh) if isinstance(mesh, dict) else None
    n_isl = (mrep or {}).get("uv_islands", len(UV_ISLANDS))
    if mrep is not None and isinstance(mesh, dict):
        # Le volume en MILLIMÈTRES CUBES : c'est l'unité du trancheur, pas
        # celle du maillage. Un pavé plein de 63 x 88 x 0,32 mm ferait
        # 1 774,08 mm3 ; l'écart est celui des coins arrondis de P5.
        mm = physical_scale(mesh, h_mm) * 1000.0
        mrep["volume_mm3"] = rnd(float(mrep.get("volume_units3") or 0.0)
                                 * mm * mm * mm, 3)
        mrep["volume_box_mm3"] = rnd(w_mm * h_mm * th_mm, 3)
    return {
        "mesh": mrep,
        "card": {
            "deck": doc_name,
            "index": idx,
            "format": g.fmt,
            "label": g.label,
            "size_mm": [rnd(w_mm, 3), rnd(h_mm, 3), rnd(th_mm, 3)],
            "width_mm": rnd(w_mm, 3), "height_mm": rnd(h_mm, 3),
            "thickness_mm": rnd(th_mm, 3),
            "size_in": [rnd(w_mm / MM_PER_INCH, 4), rnd(h_mm / MM_PER_INCH, 4),
                        rnd(th_mm / MM_PER_INCH, 4)],
            "corner_mm": rnd(g.corner_mm, 3),
            "unit": "metre",
            "unit_scale_m": GLTF_UNIT_M,
            "pivot": opt["pivot"],
            # ── LA PORTÉE DU PIVOT : UNE LISTE, PLUS UN PARAGRAPHE ───────────
            # Ce champ portait une phrase française de trois lignes. Elle
            # disait vrai, mais un fichier livré n'est pas un support de
            # rédaction : la même information tient dans deux listes, qu'un
            # importateur peut LIRE au lieu de la parser, et qui ne périment
            # pas au prochain format ajouté.
            "pivot_formats": {"node": list(PIVOT_NODE_FORMATS),
                              "baked": list(PIVOT_BAKED_FORMATS)},
        },
        "atlas": {
            "res": [res_w, res_h],
            "islands_uv": {k: list(v) for k, v in UV_ISLANDS.items()},
            "islands_px": islands_px(res_w, res_h),
            "rects": len(UV_ISLANDS),
            "islands_measured": n_isl,
            "materials": 1,
            "texture_transform": False,     # ni uv_repeat ni KHR_texture_transform
            "density": atlas_density(g, res_w, res_h, th_mm, mesh),
        },
        "render": {
            "metallicFactor": 1.0,
            "roughnessFactor": 1.0,
            "levels_baked": True,           # les niveaux sont cuits dans les maps
            "finish": opt["finish"],
            "finish_label": fin["label"],
            "roughness": fin["roughness"],
            "metallic": fin["metallic"],
            "clearcoat": fin["clearcoat"],
            "emissive": float(fin.get("emissive", 0.0)),
            "wrap": "CLAMP_TO_EDGE",
        },
        "maps": {
            "in_glb": list(GLB_SLOTS),
            "in_zip": list(map_names()),
            "orm_channels": {"R": "ao", "G": "roughness", "B": "metallic"},
        },
    }


def map_names() -> tuple:
    try:
        from app.services import pbr_service as PBR
        return tuple(PBR.MAP_KINDS)
    except Exception:                          # pragma: no cover - env cassé
        return MAP_NAMES_FALLBACK


def build_maps(atlas, opt: dict, derive: dict) -> tuple[dict, dict]:
    """Les 8 maps, cuites. Rend (maps, rapport)."""
    from app.services import pbr_service as PBR
    maps = PBR.derive_maps(atlas, derive)
    maps = PBR.bake_levels(maps, props_of(opt["finish"]))
    report = PBR.map_report(maps, base=maps.get("basecolor"))
    report["effective"] = PBR.effective_levels(maps)
    return maps, report


# ═══════════════════════════════════════════════════════════════════════════
# 5 ter. LA DIFFUSION — deux formats de plus, écrits depuis LE MÊME maillage
# ═══════════════════════════════════════════════════════════════════════════
# LE REPROCHE, ET IL EST JUSTE : deux formats de sortie (glb, gltf) contre huit
# chez la barre. OBJ et STL sont les deux qui manquaient vraiment, et ils ne
# coûtent rien parce que TOUT est déjà en mémoire : mêmes positions, mêmes
# normales, mêmes UV, mêmes indices, mêmes maps. Aucun second maillage, aucun
# second placage — c'est la garantie « aperçu == fichier livré » qui l'exige.
#
# OBJ : le format de repli universel (un outil de quinze ans l'avale). Il part
#       en ZIP avec son .mtl ET les PNG qu'il référence, sinon la matière ne
#       suit pas et l'utilisateur reçoit une carte grise.
# STL : la liste de triangles nue — impression 3D et découpe. Aucune UV, aucune
#       matière : le format n'en a pas, et le prétendre serait un mensonge de
#       plus. Le LISEZMOI le dit.
#
# UNITÉ : les deux sont écrits en MILLIMÈTRES, pas en unités de maillage. Un
# STL en « demi-hauteur = 1.0 » sortirait d'un slicer à 2 mètres de haut.
# FBX et USDZ restent absents, et l'écran le DIT au lieu de le taire.
OBJ_STL_UNIT_MM = True


def _mm_positions(mesh: dict, scale: float, offset: list | None = None) -> list:
    """Positions du maillage en MILLIMÈTRES, PIVOT COMPRIS.

    LE DÉFAUT, MESURÉ : le GLB sortait posé debout (y de 0 à 88 mm, le pivot
    étant porté par la translation du nœud) pendant que le STL et l'OBJ
    sortaient centrés (y de -44 à +44 mm). La même carte n'avait pas le même
    point zéro selon le fichier ouvert, et l'écran ne le disait pas au moment
    du choix. OBJ et STL n'ont AUCUNE notion de nœud ni de transformation :
    le seul endroit où le pivot peut vivre, chez eux, c'est dans les
    positions. On l'y applique donc, avec le même écart, calculé une seule
    fois par `pivot_offset`.

    `scale` met le maillage en mètres (convention glTF) ; x1000 le met en mm,
    l'unité de fait d'OBJ, de STL et de 3MF."""
    f = float(scale) * 1000.0
    o = [float(v) for v in (offset or [0.0, 0.0, 0.0])]
    pos = mesh.get("positions") or []
    return [(pos[i] + o[i % 3]) * f for i in range(len(pos))]


def build_obj(mesh: dict, scale: float, name: str, extras: dict,
              maps_used: list, offset: list | None = None) -> tuple[str, str]:
    """(.obj, .mtl) — texte pur, depuis les mêmes accesseurs que le GLB."""
    pos = _mm_positions(mesh, scale, offset)
    nrm = mesh.get("normals") or []
    uv = mesh.get("uvs") or []
    idx = mesh.get("indices") or []
    c = extras["card"]
    o = [f"# {c['label']}",
         f"# {c['size_mm'][0]} x {c['size_mm'][1]} x {c['size_mm'][2]} mm "
         f"— coordonnees en MILLIMETRES",
         f"# {len(idx) // 3} triangles, {len(pos) // 3} sommets, "
         f"{len(UV_ISLANDS)} ilots UV, atlas unique",
         f"mtllib {name}.mtl", f"o {name}"]
    o += [f"v {pos[i]:.5f} {pos[i + 1]:.5f} {pos[i + 2]:.5f}"
          for i in range(0, len(pos), 3)]
    # OBJ compte v vers le HAUT, l'image vers le bas : vt = 1 - v.
    o += [f"vt {uv[i]:.6f} {1.0 - uv[i + 1]:.6f}" for i in range(0, len(uv), 2)]
    o += [f"vn {nrm[i]:.5f} {nrm[i + 1]:.5f} {nrm[i + 2]:.5f}"
          for i in range(0, len(nrm), 3)]
    o.append(f"usemtl {name}")
    o.append("s off")
    for t in range(0, len(idx) - 2, 3):
        a, b, d = idx[t] + 1, idx[t + 1] + 1, idx[t + 2] + 1
        o.append(f"f {a}/{a}/{a} {b}/{b}/{b} {d}/{d}/{d}")

    # ── LE MTL VIOLAIT LA DOCTRINE QUE LE GLB DÉFEND ────────────────────────
    # Mesuré : « Pr 0.860 » était écrit à côté de « map_Pr roughness.png ».
    # Tout le discours de cette pièce est que les niveaux sont CUITS dans les
    # maps (bake_levels) et qu'il faut donc laisser le facteur à 1.0 sous peine
    # de double comptage — c'est exactement ce que fait le GLB avec
    # metallicFactor / roughnessFactor. Un importateur MTL qui multiplie
    # obtenait 0,86 x une rugosité déjà cuite. Le scalaire ne survit donc que
    # là où AUCUNE map ne le porte.
    r = extras["render"]
    # MÊME DOCTRINE QUE LE GLB, dans tous les formats : une finition qui
    # n'émet pas ne référence pas de map d'émission. Sans ça l'OBJ aurait
    # brillé (Ke neutre x map) là où le GLB reste noir — deux fichiers du même
    # lot, deux rendus différents.
    if float(r.get("emissive") or 0.0) <= 0.0:
        maps_used = [k for k in maps_used if k != "emissive"]
    has = lambda k: k in maps_used                            # noqa: E731
    m = [f"# finition {r['finish_label']}",
         "# Les niveaux sont CUITS dans les maps : tout canal qui porte une",
         "# map garde son scalaire NEUTRE (1.0), sinon un importateur qui",
         "# multiplie compterait la finition deux fois.",
         f"newmtl {name}", "Ka 0.000 0.000 0.000", "Kd 1.000 1.000 1.000",
         "Ks 0.000 0.000 0.000", "d 1.0", "illum 2"]
    ke = 1.0 if has("emissive") else float(r["emissive"])
    m.append(f"Ke {ke:.3f} {ke:.3f} {ke:.3f}")
    m.append(f"Pr {1.0 if has('roughness') else r['roughness']:.3f}")
    m.append(f"Pm {1.0 if has('metallic') else r['metallic']:.3f}")
    slots = (("basecolor", "map_Kd"), ("normal", "norm"), ("roughness", "map_Pr"),
             ("metallic", "map_Pm"), ("ao", "map_Ka"), ("emissive", "map_Ke"),
             ("height", "disp"))
    for kind, key in slots:
        if kind in maps_used:
            m.append(f"{key} {kind}.png")
    return "\n".join(o) + "\n", "\n".join(m) + "\n"


def build_stl(mesh: dict, scale: float, name: str,
              offset: list | None = None) -> bytes:
    """STL binaire, en millimètres. Une normale par facette, recalculée depuis
    la géométrie : le format n'a ni UV ni matière et n'en aura jamais."""
    import struct
    pos = _mm_positions(mesh, scale, offset)
    idx = mesh.get("indices") or []
    n = len(idx) // 3
    out = bytearray()
    # Les 80 octets d'en-tête d'un STL binaire sont libres : ils portent ce
    # que le format ne sait pas coder (l'unité), pas le nom d'un logiciel.
    head = f"{name} - millimetres - {n} triangles".encode("ascii", "ignore")
    out += head[:80].ljust(80, b"\x00")
    out += struct.pack("<I", n)
    for t in range(0, len(idx) - 2, 3):
        p = [pos[idx[t + k] * 3:idx[t + k] * 3 + 3] for k in range(3)]
        ux, uy, uz = (p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2])
        vx, vy, vz = (p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2])
        nx, ny, nz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out += struct.pack("<3f", nx / ln, ny / ln, nz / ln)
        for q in p:
            out += struct.pack("<3f", q[0], q[1], q[2])
        out += struct.pack("<H", 0)
    return bytes(out)


# ── 3MF : LA SEULE ABSENCE QUI COÛTAIT VRAIMENT ─────────────────────────────
# Le reproche était juste et il était chiffré : trois conteneurs de maillage
# contre huit chez la barre, et sur les cinq manquants, DEUX seulement étaient
# refusés avec un motif écrit. Le 3MF est celui dont le silence coûtait le
# plus cher : norme OUVERTE (ISO/ASTM 52915), écrivable en stdlib puisque
# c'est un ZIP de XML, et surtout le SEUL format d'impression 3D qui
# transporte la COULEUR — alors que le STL qu'on livre n'a, de notre propre
# aveu, aucune matière. Pour une carte à jouer imprimée, c'est exactement le
# format qui manquait.
#
# La couleur est ÉCHANTILLONNÉE sur la basecolor livrée, au barycentre UV de
# chaque triangle : ce n'est pas une teinte inventée, c'est la carte.
_3MF_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_3MF_MAT = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"


def _weld(pos: list, idx: list) -> tuple[list, list]:
    """Soude les sommets par POSITION. L'atlas duplique les sommets à chaque
    couture UV (228 pour 114 positions) : un 3MF non soudé serait vu comme une
    coquille ouverte par tout contrôleur d'imprimabilité, alors que le solide
    est fermé."""
    key: dict = {}
    out: list = []
    remap = []
    for i in range(len(pos) // 3):
        k = (round(pos[i * 3], 6), round(pos[i * 3 + 1], 6),
             round(pos[i * 3 + 2], 6))
        j = key.get(k)
        if j is None:
            j = key[k] = len(out) // 3
            out += [pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]]
        remap.append(j)
    return out, [remap[i] for i in idx]


def tri_colors(mesh: dict, base) -> list:
    """Une couleur par triangle, LUE dans la basecolor au barycentre UV."""
    uv = mesh.get("uvs") or []
    idx = mesh.get("indices") or []
    if base is None or not uv:
        return ["#f2efe6"] * (len(idx) // 3)
    im = base.convert("RGB")
    w, h = im.size
    px = im.load()
    out = []
    for t in range(0, len(idx) - 2, 3):
        u = sum(uv[idx[t + k] * 2] for k in range(3)) / 3.0
        v = sum(uv[idx[t + k] * 2 + 1] for k in range(3)) / 3.0
        x = min(w - 1, max(0, int(u * w)))
        y = min(h - 1, max(0, int(v * h)))
        r, g, b = px[x, y][:3]
        out.append(f"#{r:02X}{g:02X}{b:02X}")
    return out


def build_3mf(mesh: dict, scale: float, name: str, extras: dict,
              base=None, offset: list | None = None) -> bytes:
    """3MF (ISO/ASTM 52915) — millimètres et COULEUR par triangle.

    Contrairement au STL, ce fichier porte son unité DANS le format
    (`unit="millimeter"`) : aucun slicer n'a à deviner l'échelle."""
    pos = _mm_positions(mesh, scale, offset)
    idx = mesh.get("indices") or []
    cols = tri_colors(mesh, base)
    vpos, vidx = _weld(pos, idx)
    palette: list = []
    at: dict = {}
    for c in cols:
        if c not in at:
            at[c] = len(palette)
            palette.append(c)
    c = extras["card"]
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<model unit="millimeter" xml:lang="en-US" xmlns="{_3MF_CORE}" '
         f'xmlns:m="{_3MF_MAT}">',
         f'<metadata name="Title">{_xml(str(c["label"]))}</metadata>',
         '<resources>',
         '<m:colorgroup id="1">']
    x += [f'<m:color color="{col}" />' for col in palette]
    x += ['</m:colorgroup>',
          f'<object id="2" name="{_xml(name)}" type="model" pid="1" '
          'pindex="0"><mesh><vertices>']
    x += [f'<vertex x="{vpos[i]:.5f}" y="{vpos[i + 1]:.5f}" '
          f'z="{vpos[i + 2]:.5f}" />' for i in range(0, len(vpos), 3)]
    x.append('</vertices><triangles>')
    for t in range(0, len(vidx) - 2, 3):
        p = at[cols[t // 3]]
        x.append(f'<triangle v1="{vidx[t]}" v2="{vidx[t + 1]}" '
                 f'v3="{vidx[t + 2]}" pid="1" p1="{p}" />')
    x += ['</triangles></mesh></object>', '</resources>',
          '<build><item objectid="2" /></build>', '</model>']
    model = "\n".join(x).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/'
                   '2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.'
                   'openxmlformats-package.relationships+xml" />'
                   '<Default Extension="model" ContentType="application/vnd.'
                   'ms-package.3dmanufacturing-3dmodel+xml" /></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/'
                   '01/3dmodel" /></Relationships>')
        z.writestr("3D/3dmodel.model", model)
    return buf.getvalue()


def _xml(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ── PLY ET DXF : DEUX ABSENCES DE PLUS, ET UNE EXCUSE QUI ÉTAIT FAUSSE ───────
# Le reproche chiffré portait sur cinq formats manquants ; le 3MF a été écrit
# au tour précédent. Restaient FBX, USDZ, BLEND et DXF, tous les quatre
# « refusés avec un motif » — sauf que le motif du DXF était FAUX : cet écran
# affichait « format de DESSIN 2D ». Le DXF porte des entités 3DFACE depuis
# 1988 ; c'est la langue des chaînes de CAO et de découpe. Un motif faux est
# pire qu'une absence, alors on l'écrit.
#
# PLY vient avec : le camp qui a PERDU le duel en livrait un, et il porte ce
# que ni le STL ni le DXF ne savent transporter — une COULEUR PAR SOMMET et
# les UV. C'est le format des chaînes de scan et des imprimantes couleur.
#
# Les deux sont écrits depuis LES MÊMES accesseurs que le GLB : mêmes
# positions, mêmes indices, même pivot, même échelle en millimètres. Aucun
# second maillage.
def vertex_colors(mesh: dict, base) -> list:
    """Une couleur par SOMMET, lue dans la basecolor à ses UV. `tri_colors`
    échantillonne au barycentre d'un triangle (3MF n'a pas mieux) ; PLY porte
    la couleur au sommet, donc on y échantillonne au sommet."""
    uv = mesh.get("uvs") or []
    n = len(uv) // 2
    if base is None or not uv:
        return [(242, 239, 230)] * n
    im = base.convert("RGB")
    w, h = im.size
    px = im.load()
    out = []
    for i in range(n):
        x = min(w - 1, max(0, int(uv[i * 2] * w)))
        y = min(h - 1, max(0, int(uv[i * 2 + 1] * h)))
        out.append(tuple(px[x, y][:3]))
    return out


def build_ply(mesh: dict, scale: float, name: str, extras: dict,
              base=None, offset: list | None = None) -> bytes:
    """PLY binaire petit-boutiste, en MILLIMÈTRES, couleur par sommet.

    Les sommets ne sont PAS soudés (228 pour 114 positions) : l'atlas duplique
    à chaque couture UV, et souder ici perdrait les UV et les normales que ce
    format sait justement porter. Le 3MF, lui, soude — c'est un format
    d'impression, il n'a que la géométrie à défendre."""
    import struct
    pos = _mm_positions(mesh, scale, offset)
    nrm = mesh.get("normals") or []
    uv = mesh.get("uvs") or []
    idx = mesh.get("indices") or []
    cols = vertex_colors(mesh, base)
    c = extras["card"]
    head = "\n".join([
        "ply",
        "format binary_little_endian 1.0",
        f"comment {c['label']}",
        "comment unit millimeter",
        f"comment size {c['size_mm'][0]} x {c['size_mm'][1]} x "
        f"{c['size_mm'][2]} mm",
        "comment couleur par sommet echantillonnee dans basecolor",
        f"element vertex {len(pos) // 3}",
        "property float x", "property float y", "property float z",
        "property float nx", "property float ny", "property float nz",
        "property float s", "property float t",
        "property uchar red", "property uchar green", "property uchar blue",
        f"element face {len(idx) // 3}",
        "property list uchar int vertex_indices",
        "end_header", ""]).encode("ascii")
    out = bytearray(head)
    for i in range(len(pos) // 3):
        r, g, b = cols[i] if i < len(cols) else (242, 239, 230)
        out += struct.pack(
            "<8f3B",
            pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2],
            nrm[i * 3] if len(nrm) > i * 3 + 2 else 0.0,
            nrm[i * 3 + 1] if len(nrm) > i * 3 + 2 else 0.0,
            nrm[i * 3 + 2] if len(nrm) > i * 3 + 2 else 1.0,
            uv[i * 2] if len(uv) > i * 2 + 1 else 0.0,
            # MÊME CONVENTION QUE L'OBJ : PLY compte v vers le haut.
            1.0 - uv[i * 2 + 1] if len(uv) > i * 2 + 1 else 0.0,
            r, g, b)
    for t in range(0, len(idx) - 2, 3):
        out += struct.pack("<B3i", 3, idx[t], idx[t + 1], idx[t + 2])
    return bytes(out)


def build_dxf(mesh: dict, scale: float, name: str,
              offset: list | None = None) -> str:
    """DXF R12 (AC1009), entités 3DFACE, coordonnées en MILLIMÈTRES.

    L'en-tête porte `$INSUNITS = 4` (millimètres) et `$EXTMIN`/`$EXTMAX`
    calculés sur les points écrits. Comme le STL, ce format ne transporte ni
    UV ni matière : ce sont des faces nues. Il est là parce que les chaînes de
    CAO et de découpe ne lisent souvent que lui — pas parce qu'il apporterait
    une information de plus."""
    pos = _mm_positions(mesh, scale, offset)
    idx = mesh.get("indices") or []
    xs = pos[0::3] or [0.0]
    ys = pos[1::3] or [0.0]
    zs = pos[2::3] or [0.0]
    g: list[str] = []

    def pair(code, val):
        g.append(str(code))
        g.append(val if isinstance(val, str) else f"{val}")

    pair(0, "SECTION"), pair(2, "HEADER")
    pair(9, "$ACADVER"), pair(1, "AC1009")
    pair(9, "$INSUNITS"), pair(70, 4)              # 4 = millimetres
    pair(9, "$EXTMIN"), pair(10, f"{min(xs):.6f}")
    pair(20, f"{min(ys):.6f}"), pair(30, f"{min(zs):.6f}")
    pair(9, "$EXTMAX"), pair(10, f"{max(xs):.6f}")
    pair(20, f"{max(ys):.6f}"), pair(30, f"{max(zs):.6f}")
    pair(0, "ENDSEC")
    pair(0, "SECTION"), pair(2, "ENTITIES")
    for t in range(0, len(idx) - 2, 3):
        p = [pos[idx[t + k] * 3:idx[t + k] * 3 + 3] for k in range(3)]
        # Calque « 0 » : le calque par défaut de tout DXF depuis R12. Un nom de
        # calque est une chaîne visible dans chaque logiciel de CAO qui ouvre
        # le fichier — ce n'est pas un endroit où signer.
        pair(0, "3DFACE"), pair(8, "0")
        for k, q in enumerate(p):
            pair(10 + k, f"{q[0]:.6f}")
            pair(20 + k, f"{q[1]:.6f}")
            pair(30 + k, f"{q[2]:.6f}")
        # Un 3DFACE a QUATRE sommets : pour un triangle, le quatrième répète le
        # troisième. C'est la convention, pas un remplissage.
        pair(13, f"{p[2][0]:.6f}"), pair(23, f"{p[2][1]:.6f}")
        pair(33, f"{p[2][2]:.6f}")
    pair(0, "ENDSEC"), pair(0, "EOF")
    return "\r\n".join(g) + "\r\n"


# ── LA PLANCHE DE CONTRÔLE : LA VUE D'INSPECTION QUI MANQUAIT ────────────────
# Reproche répété dans les DEUX duels : « pour un exporteur qui demande qu'on
# lui fasse confiance sur ses îlots et ses maps, ne pas pouvoir les REGARDER
# dans le produit est une lacune réelle ». L'écran savait déjà montrer l'atlas
# et le fil de fer UV ; il ne savait pas montrer les huit canaux. La planche
# les met côte à côte, à la même échelle, dans un fichier qu'on peut peser.
#
# Elle est fabriquée depuis les MÊMES images que les PNG du ZIP, avant
# encodage : ce n'est pas une seconde dérivation, c'est la même.
def build_proof(maps: dict, extras: dict, res_w: int, res_h: int,
                tile: int = 256) -> bytes:
    """Contact sheet des 8 maps + l'atlas, en un PNG. Aucun chiffre inventé :
    seuls la définition, la taille physique et les noms de canaux y sont
    écrits, et tous viennent des mêmes `extras` que le fichier livré."""
    from PIL import Image, ImageDraw
    kinds = [k for k in map_names() if k in maps]
    cols = 4
    rows = max(1, (len(kinds) + cols - 1) // cols)
    bar, pad, top = 16, 6, 22
    W = cols * (tile + pad) + pad
    H = top + rows * (tile + bar + pad) + pad
    sheet = Image.new("RGB", (W, H), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    c = extras["card"]
    d.text((pad, 6), f"{c['label']} - {c['size_mm'][0]} x "
                     f"{c['size_mm'][1]} x {c['size_mm'][2]} mm - atlas "
                     f"{res_w} x {res_h} px - apercu 8 bits des maps livrees",
           fill=(200, 226, 240))
    for i, k in enumerate(kinds):
        x = pad + (i % cols) * (tile + pad)
        y = top + (i // cols) * (tile + bar + pad)
        im = maps[k].convert("RGB").resize((tile, tile), Image.LANCZOS)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + tile - 1, y + tile - 1], outline=(70, 78, 92))
        d.text((x + 2, y + tile + 3), k, fill=(127, 224, 255))
    buf = io.BytesIO()
    sheet.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_obj_zip(mesh: dict, scale: float, name: str, extras: dict,
                  pngs: dict, depth: dict | None = None,
                  report: dict | None = None, opt: dict | None = None,
                  offset: list | None = None) -> bytes:
    """L'OBJ et son MTL avec les PNG qu'il référence — un seul fichier, ouvrable
    tel quel. Un .obj livré seul arrive gris dans le logiciel d'en face.

    L'ARCHIVE OBJ ÉTAIT UNE CITOYENNE DE SECONDE ZONE. Mesuré : son LISEZMOI
    faisait 292 octets — un moignon — alors que la fiche présentait la notice
    de montage comme « présente dans les deux ZIP », avec ses explications sur
    metallicFactor, le CLAMP et le height ; et elle n'avait AUCUN
    manifest.json. Deux archives qui contiennent les mêmes octets de PNG
    doivent porter la même documentation, sinon l'une des deux ment sur ce
    qu'elle est."""
    obj, mtl = build_obj(mesh, scale, name, extras, list(pngs), offset)
    entries = _png_entries(pngs, depth or {}, report or {})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}.obj", obj)
        z.writestr(f"{name}.mtl", mtl)
        for kind, data in pngs.items():
            z.writestr(f"{kind}.png", data)
        z.writestr("manifest.json", json.dumps(
            _manifest(extras, entries, depth or {}, report or {}, opt or {},
                      f"{name}.obj", OBJ_MANIFEST_SCHEMA),
            ensure_ascii=False, indent=2))
        z.writestr("LISEZMOI.txt",
                   "OBJ + MTL, coordonnees en MILLIMETRES.\n"
                   "Le MTL pointe les PNG de cette archive : gardez-les a cote "
                   "du .obj.\n"
                   "OBJ ne connait ni ORM packee ni PBR normalise : la "
                   "rugosite, le metal et l'AO partent en maps separees "
                   "(Pr/Pm/Ka, extension PBR de Wavefront).\n"
                   "Les scalaires du MTL restent NEUTRES la ou une map les "
                   "porte : les niveaux sont deja cuits dans les images.\n"
                   "Pour un moteur moderne, preferez le .glb.\n\n"
                   + _readme(extras, entries, opt or {},
                             mesh_file=f"{name}.obj",
                             conf=depth_verdict(depth or {})))
    return buf.getvalue()


def build_one(doc: dict, idx: int, opt: dict) -> dict:
    """Construit TOUS les livrables d'une carte et les écrit dans `out/`.

    Rend le bordereau : un fichier = un nom, un genre, un poids EXACT et un
    libellé. Rien n'est estimé — tout est pesé après écriture."""
    from PIL import Image
    from app.services import gltf_builder as GB
    from app.services import material_store as MS

    did = doc["id"]
    g = _geom(doc)
    th = thickness_of(doc, opt.get("thickness_mm"))
    derive = derive_of(doc, opt.get("derive"))
    src = atlas_path(did, idx)
    if not src.is_file():
        raise HTTPException(409, f"Aucun atlas pour la carte {idx + 1} : "
                                 "composez-le depuis l'écran avant d'exporter")

    t0 = time.perf_counter()
    with Image.open(src) as im:
        atlas = im.convert("RGB")
    res = int(opt["res"])
    if atlas.width != res or atlas.height != res:
        # L'écran compose déjà à la bonne taille ; ce filet sert aux atlas
        # importés à la main (glisser-deposer) et aux appels hors ecran.
        atlas = atlas.resize((res, res), Image.LANCZOS)
    res_w, res_h = atlas.width, atlas.height

    maps, report = build_maps(atlas, opt, derive)
    t_maps = time.perf_counter() - t0

    mesh = card_mesh(g, solid_of(doc, opt.get("thickness_mm")))
    scale = physical_scale(mesh, g.trim_mm[1])
    pivot = pivot_offset(mesh, opt["pivot"])
    mrep = mesh_report(mesh)
    extras = card_extras(g, th, res_w, res_h, opt, doc.get("name") or "", idx,
                         mesh=mesh)
    # UN SEUL rapport de maillage : celui qui part dans le fichier est celui
    # que le bordereau affiche. Deux appels à `mesh_report` donnaient deux
    # objets, et le volume en mm3 n'existait que dans l'un des deux.
    if isinstance(extras.get("mesh"), dict):
        mrep = extras["mesh"]
    props = props_of(opt["finish"])
    name = f"{slug_of(doc)}_c{idx + 1:02d}"
    dens = atlas_density(g, res_w, res_h, th, mesh)
    # Le pHYs se calcule sur le rapport EXACT, pas sur `px_per_mm` qui est
    # arrondi pour l'affichage : 15.94 au lieu de 15.9365 déplaçait le chunk de
    # 0,1 DPI et le fichier annonçait 404,9 quand l'écran disait 404,8. Deux
    # chiffres pour la même chose, c'est déjà un mensonge — et c'est le test
    # `test_chaque_png_porte_sa_definition_et_son_espace_de_couleur` qui l'a
    # attrapé, pas une relecture.
    ppm = (dens["front_px"][0] / g.trim_mm[0] if g.trim_mm[0] else 0.0,
           dens["front_px"][1] / g.trim_mm[1] if g.trim_mm[1] else 0.0)

    # ── LA TEXTURE MORTE, RETIRÉE ───────────────────────────────────────────
    # Mesuré sur le GLB du 11/08 : `emissiveFactor = [0,0,0]` ET
    # `emissiveTexture` pointant l'image 3 — 126 782 octets embarqués, soit
    # 3,01 % du fichier, qui par construction ne peuvent modifier AUCUN pixel
    # (glTF pose émission = facteur x texture, le produit est nul partout). On
    # livrait une liaison mathématiquement inerte pour afficher « 4 textures ».
    # Une finition qui n'émet pas n'embarque plus sa map : le compte de
    # textures devient une mesure au lieu d'un chiffre rond.
    dead: list[str] = []
    glb_maps, codecs = {}, {}
    for s in GLB_SLOTS:
        if s not in maps:
            continue
        if s == "emissive" and float(props.get("emissive_strength") or 0.0) <= 0.0:
            dead.append(s)
            continue
        glb_maps[s], codecs[s] = _encode(maps[s], s, opt, tuple(dens["dpi"]))
    # `in_glb` était la liste des emplacements POSSIBLES ; c'est maintenant la
    # liste de ceux qu'on écrit vraiment, et les écartés sont nommés.
    extras["maps"]["in_glb"] = list(glb_maps)
    extras["maps"]["skipped"] = dead
    if dead:
        # Pourquoi, en DONNÉE : le facteur qui annule la map, et où la map
        # reste disponible. Une phrase française de six lignes disait la même
        # chose, recopiée dans chaque fichier livré.
        extras["maps"]["skipped_reason"] = {
            "emissive_factor": 0.0, "still_in": "zip"}
    t1 = time.perf_counter()
    with _mesh_context(mesh):
        # CTX_MESH, pas "card" : la clé « card » peut appartenir à P5 et
        # rendrait alors un maillage au format d'usine (voir plus haut).
        # AUCUN uv_repeat : les îlots déborderaient (piège 12).
        raw = GB.build_glb(glb_maps, props, mesh=CTX_MESH, name=name,
                           stage_png=None, uv_repeat=None)
    # `closed` vient de la MESURE des arêtes, pas d'une hypothèse sur la forme.
    # LE MÊME écart de pivot part dans les CINQ formats : le GLB le porte sur la
    # translation du nœud (la géométrie ne bouge pas), OBJ / STL / 3MF n'ont pas
    # de nœud et le portent donc dans leurs positions. Une seule origine.
    glb = finalize_glb(raw, extras, scale, name=name, closed=mrep["closed"],
                       offset=pivot)
    t_glb = time.perf_counter() - t1

    out = out_dir(did, create=True)
    files: list[dict] = []
    zip_pngs: dict = {}
    depth: dict = {}

    def emit(fname: str, data: bytes, kind: str, label: str) -> None:
        (out / fname).write_bytes(data)
        files.append({"name": fname, "kind": kind, "label": label,
                      "bytes": len(data)})

    # Les PNG du ZIP sont encodés UNE fois et resservent à l'OBJ : deux
    # archives, les mêmes octets, aucune divergence possible entre les deux.
    t_deep = 0.0
    if {"zip", "obj"} & set(opt["formats"]):
        caveat = str(dens.get("edge_note") or "")
        # LES 16 BITS SONT DÉRIVÉS, PAS DILATÉS. La re-dérivation en virgule
        # flottante ne tourne que si la case est cochée — elle coûte des
        # secondes, elle ne doit rien coûter à qui ne la demande pas.
        deep = None
        if opt["bits16"]:
            t2 = time.perf_counter()
            deep = derive_deep(atlas, derive)
            t_deep = time.perf_counter() - t2
        for kind in map_names():
            img = maps.get(kind)
            if img is None:
                continue
            zip_pngs[kind], depth[kind] = map_png(
                img, kind, opt["bits16"], ppm, caveat,
                deep=(deep or {}).get(kind), ref8=img)

    if "glb" in opt["formats"]:
        emit(f"{name}.glb", glb, "glb",
             f"GLB — {len(glb_maps)} textures, géométrie + matériau, "
             f"{mrep['triangles']} triangles")
    if "gltf" in opt["formats"]:
        gltf = MS.glb_to_gltf(glb)
        emit(f"{name}.gltf", gltf, "gltf",
             "glTF autonome — buffer en data URI, aucun fichier à côté")
    if "zip" in opt["formats"]:
        # Le maillage joint est l'OBJ (25 Ko), pas une seconde copie du GLB
        # (4,2 Mo) : l'archive reste autonome et cesse d'être redondante.
        obj_txt, mtl_txt = build_obj(mesh, scale, name, extras,
                                     list(zip_pngs), pivot)
        zip_bytes = build_zip(doc, idx, zip_pngs, depth, f"{name}.obj",
                              {f"{name}.obj": obj_txt.encode("utf-8"),
                               f"{name}.mtl": mtl_txt.encode("utf-8")},
                              extras, report, opt, name)
        emit(f"{name}_maps.zip", zip_bytes, "zip",
             f"ZIP — {len(zip_pngs)} maps PNG (pHYs + espace couleur) "
             "+ manifest.json + le maillage OBJ")
    if "obj" in opt["formats"]:
        emit(f"{name}_obj.zip",
             build_obj_zip(mesh, scale, name, extras, zip_pngs, depth, report,
                           opt, pivot), "obj",
             "OBJ + MTL + maps, en millimètres — le repli universel")
    if "stl" in opt["formats"]:
        emit(f"{name}.stl", build_stl(mesh, scale, name, pivot), "stl",
             f"STL binaire, {mrep['triangles']} facettes en millimètres "
             "— impression 3D (aucune matière : le format n'en a pas)")
    if "3mf" in opt["formats"]:
        emit(f"{name}.3mf",
             build_3mf(mesh, scale, name, extras, maps.get("basecolor"), pivot),
             "3mf",
             f"3MF (ISO/ASTM 52915) — {mrep['triangles']} triangles en "
             "millimètres AVEC couleur par facette, norme ouverte "
             "d'impression 3D")
    if "ply" in opt["formats"]:
        emit(f"{name}.ply",
             build_ply(mesh, scale, name, extras, maps.get("basecolor"), pivot),
             "ply",
             f"PLY binaire, {mrep['vertices']} sommets en millimètres AVEC "
             "couleur par sommet, normales et UV — ce que ni le STL ni le DXF "
             "ne portent")
    if "dxf" in opt["formats"]:
        emit(f"{name}.dxf",
             build_dxf(mesh, scale, name, pivot).encode("ascii"), "dxf",
             f"DXF R12 — {mrep['triangles']} entités 3DFACE en millimètres "
             "($INSUNITS = 4), pour les chaînes CAO et découpe. Faces nues : "
             "ni UV ni matière, comme le STL")
    if "proof" in opt["formats"]:
        emit(f"{name}_controle.png",
             build_proof(maps, extras, res_w, res_h), "proof",
             f"Planche de contrôle — les {len(maps)} canaux côte à côte, "
             "aperçu 8 bits des maps livrées : de quoi les REGARDER sans "
             "ouvrir le ZIP")

    return {
        "index": idx,
        "name": name,
        "files": files,
        "bytes": sum(f["bytes"] for f in files),
        "glb": glb_report(glb),
        "codecs": codecs,
        "maps": report,
        "depth": depth,
        # La ligne 121 du cahier des charges, tranchée sur les octets livrés.
        "conformance": depth_verdict(depth),
        # Ce que deux livrables cochés ensemble se recopient, MESURÉ par
        # comparaison des entrées d'archive (nom + CRC), pas estimé.
        "redundancy": archive_overlap(out, files),
        "mesh": {"name": mesh.get("name"), "scale": scale, **mrep},
        "atlas": {"res": [res_w, res_h], "density": dens,
                  "bytes": src.stat().st_size},
        "size_mm": extras["card"]["size_mm"],
        "ms": {"maps": int(t_maps * 1000), "glb": int(t_glb * 1000),
               # Le prix des 16 bits réels, en secondes : dérivation flottante
               # + écriture + RELECTURE des octets. Affiché, jamais caché.
               "deep16": int(t_deep * 1000) + sum(
                   int((depth.get(k) or {}).get("ms16") or 0)
                   for k in ("height", "normal")),
               "deep16_derive": int(t_deep * 1000),
               "total": int((time.perf_counter() - t0) * 1000)},
    }


def archive_overlap(out: Path, files: list) -> dict:
    """CE QUE DEUX ARCHIVES COCHÉES ENSEMBLE SE RECOPIENT, mesuré.

    Reproche fondé du tour précédent : « les 8 PNG sont livrés DEUX fois ».
    C'est vrai, et pire que ça — le ZIP des maps embarque déjà l'OBJ et le MTL
    depuis la correction de la redondance du GLB, donc l'archive OBJ n'apporte
    plus une seule entrée nouvelle quand les deux sont cochées. On ne peut pas
    le corriger en fusionnant (chaque archive doit rester AUTONOME : des maps
    sans maillage ne se montent sur rien, un OBJ sans ses maps sort gris), mais
    on peut cesser d'afficher deux poids comme s'ils étaient deux contenus.

    On compare les entrées par NOM + CRC-32 — la mesure, pas la ressemblance.
    """
    zips = [f for f in files if f["name"].lower().endswith(".zip")]
    if len(zips) < 2:
        return {"pairs": [], "bytes": 0}
    lots: dict = {}
    for f in zips:
        p = out / f["name"]
        if not p.is_file():
            continue
        try:
            with zipfile.ZipFile(p) as z:
                lots[f["name"]] = {i.filename: (i.CRC, i.file_size)
                                   for i in z.infolist()}
        except (OSError, zipfile.BadZipFile):    # pragma: no cover
            continue
    pairs, total = [], 0
    noms = sorted(lots)
    for i in range(len(noms)):
        for j in range(i + 1, len(noms)):
            a, b = lots[noms[i]], lots[noms[j]]
            comm = [k for k in a if k in b and a[k][0] == b[k][0]]
            if not comm:
                continue
            oct_ = sum(a[k][1] for k in comm)
            total += oct_
            pairs.append({
                "a": noms[i], "b": noms[j],
                "identiques": len(comm), "entrees_a": len(a), "entrees_b": len(b),
                "bytes_decompresses": oct_,
                "tout": len(comm) == len(a) == len(b),
                "note": (f"{len(comm)} entree(s) identiques (nom + CRC) sur "
                         f"{len(a)} et {len(b)}"),
            })
    return {"pairs": pairs, "bytes": total}


def _png_entries(pngs: dict, depth: dict, report: dict) -> list:
    """La fiche d'un PNG de l'archive : poids, profondeur MESURÉE, chunks, et
    l'information qu'il porte. Une seule fonction pour les deux archives."""
    out = []
    for kind, data in pngs.items():
        d = depth.get(kind) or {}
        st = (report.get("maps") or {}).get(kind, {})
        lv = int(d.get("levels", 0) or 0)
        out.append({
            "name": f"{kind}.png", "bytes": len(data),
            "bits": d.get("bits", 8),
            "bits_container": d.get("bits_container", d.get("bits", 8)),
            "bits_source": d.get("bits_source", 8),
            "levels": lv,
            "levels_per_channel": d.get("levels_per_channel"),
            "bits_effective": d.get("bits_effective", 0.0),
            "widened": bool(d.get("widened")),
            "real16": bool(d.get("real16")),
            "deep": bool(d.get("deep")),
            "refused16": bool(d.get("refused16")),
            "accord_8": d.get("accord_8"),
            "levels_8": d.get("levels_8"),
            "lattice_pct": d.get("lattice_pct"),
            "verdict": d.get("verdict", ""),
            "measured_on": d.get("measured_on", ""),
            "chunks": png_chunk_types(data),
            "informative": bool(st.get("informative")),
            # « constante » était FAUX sur emissive : 217 niveaux distincts
            # portaient la mention « constante : aucune information ». Un seul
            # niveau, c'est constant ; 217, c'est faible, pas constant.
            "constant": lv == 1,
            "mean": st.get("mean"),
        })
    return out


def _manifest(extras: dict, entries: list, depth: dict, report: dict,
              opt: dict, mesh_file: str, schema: str) -> dict:
    """Le manifeste, identique de forme dans les deux archives."""
    return {
        "schema": schema,
        "card": extras["card"],
        "mesh": extras["mesh"],
        "mesh_file": mesh_file,
        "atlas": extras["atlas"],
        "render": extras["render"],
        "maps": {
            "expected": list(map_names()),
            "count": len(entries),
            "informative": sum(1 for e in entries if e["informative"]),
            "constant": sum(1 for e in entries if e.get("constant")),
            "files": entries,
            "depth": depth,
            "report": report,
        },
        "options": {k: opt.get(k) for k in
                    ("res", "finish", "bits16", "img", "jpeg_q", "formats")},
        # Ce qui a été DEMANDÉ en profondeur, ce qui est LIVRÉ, et la mesure
        # qui tranche entre les deux.
        "conformance": depth_verdict(depth),
    }


def build_zip(doc: dict, idx: int, pngs: dict, depth: dict, mesh_name: str,
              mesh_files: dict, extras: dict, report: dict, opt: dict,
              name: str) -> bytes:
    """Le ZIP : les 8 PNG nommés, le manifeste, le maillage, le mode d'emploi.

    Les PNG arrivent DÉJÀ encodés (`map_png`) : ils portent leur pHYs et leur
    espace de couleur, et chacun sa fiche de profondeur MESURÉE. C'est le même
    tableau d'octets qui part dans l'archive OBJ — deux archives, une seule
    vérité.

    LE MAILLAGE DE CETTE ARCHIVE N'EST PLUS LE GLB. Mesuré sur le lot du
    11/08 : le `.glb` était livré seul (4 208 876 o) ET recopié à l'identique
    dans ce ZIP — 4,2 Mo de redondance pure sur un bordereau de 30 Mo, pour
    zéro information nouvelle. L'archive doit rester AUTONOME (des maps sans
    maillage ne se montent sur rien) : elle embarque donc l'OBJ + MTL, qui
    pointent les PNG déjà présents à côté. 25 Ko au lieu de 4,2 Mo, et
    l'archive s'ouvre toujours seule."""
    buf = io.BytesIO()
    entries = _png_entries(pngs, depth, report)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for kind, data in pngs.items():
            z.writestr(f"{kind}.png", data)
        for fn, data in mesh_files.items():
            z.writestr(fn, data)
        man = _manifest(extras, entries, depth, report, opt, mesh_name,
                        MANIFEST_SCHEMA)
        man["deck"] = {"id": doc.get("id"), "name": doc.get("name")}
        z.writestr("manifest.json",
                   json.dumps(man, ensure_ascii=False, indent=2))
        z.writestr("LISEZMOI.txt", _readme(extras, entries, opt,
                                           mesh_file=mesh_name,
                                           conf=depth_verdict(depth)))
    return buf.getvalue()


def _readme(extras: dict, entries: list, opt: dict,
            mesh_file: str = "", conf: dict | None = None) -> str:
    """Le mode d'emploi, écrit POUR CELUI QUI MONTE LE FICHIER.

    Chaque nombre imprimé ici se relit sur les octets de l'archive. Le reste
    est ce qu'un intégrateur a besoin de savoir pour brancher les maps sans se
    tromper — pas un plaidoyer, et pas la signature de l'outil : la notice
    portait une bannière au nom du producteur, elle n'en porte plus."""
    c = extras["card"]
    d = extras["atlas"]["density"]
    m = extras["mesh"] or {}
    lines = [
        "EXPORT 3D",
        "=" * 62,
        f"Carte       : {c['label']}",
        f"Dimensions  : {c['size_mm'][0]} x {c['size_mm'][1]} x "
        f"{c['size_mm'][2]} mm (coupe finie, fond perdu deja massicote)",
        f"Maillage    : {m.get('triangles', '?')} triangles, "
        f"{m.get('vertices', '?')} sommets, "
        + ("solide FERME" if m.get("closed") else "surface ouverte")
        + f", {m.get('uv_islands', '?')} ilots UV MESURES "
        + f"({'+'.join(str(n) for n in (m.get('uv_islands_tri') or []))} tri)",
        f"Attributs   : {', '.join(m.get('attributes') or [])}",
        f"Impression  : "
        + ("IMPRIMABLE — solide ferme, normales vers l'exterieur, volume "
           f"{m.get('volume_mm3', '?')} mm3 (pave plein equivalent : "
           f"{m.get('volume_box_mm3', '?')} mm3, l'ecart est celui des coins "
           "arrondis)"
           if m.get("printable") else
           "NON IMPRIMABLE en l'etat : "
           + ("normales retournees (volume signe negatif)"
              if m.get("closed") else
              f"{m.get('free_edges', '?')} arete(s) libre(s)")),
        f"Finition    : {extras['render']['finish_label']}"
        f" — emission {extras['render']['emissive']}",
        f"Atlas       : {extras['atlas']['res'][0]} x "
        f"{extras['atlas']['res'][1]} px, "
        f"{m.get('atlas_rects', len(UV_ISLANDS))} rectangles reserves",
        (f"Maillage joint : {mesh_file}" if mesh_file else ""),
        "",
        "DEFINITION",
        f"  texels de l'ilot recto : {d['dpi'][0]} x {d['dpi'][1]} DPI "
        f"({d['front_px'][0]} x {d['front_px'][1]} px)",
        "    C'est la valeur ecrite dans le chunk pHYs de chaque PNG.",
        f"  source du rendu        : {d['dpi_source']} DPI "
        f"({d['source_px'][0]} x {d['source_px'][1]} px de coupe)",
        f"  information reelle     : {d['dpi_effective']} DPI — "
        + (f"la definition de la carte ({d['dpi_target']} DPI) est tenue."
           if d["print_ok"] else
           f"SOUS la definition de la carte ({d['dpi_target']} DPI)."),
        f"  L'ilot met la source a l'echelle x{d['upsample'][0]} en largeur et "
        f"x{d['upsample'][1]} en hauteur ;",
        f"  les texels ne sont pas carres (anisotropie {d['anisotropy']}x).",
        "  Tranche : " + str(d.get("edge_note") or ""),
        "",
        "PROFONDEUR DE height ET normal, RELEVEE DANS LES OCTETS DE CE ZIP",
        "  livre    : " + (", ".join(
            f"{k} {v.get('bits')} bits ({v.get('levels')} niveaux distincts)"
            for k, v in ((conf or {}).get("delivered") or {}).items()) or "-"),
        "  verdict  : " + str((conf or {}).get("verdict", "")),
        "  ecart    : " + (", ".join(
            f"{k} " + " / ".join(
                f"{c.get('moyen')} (max {c.get('max')})"
                for c in ((v.get('accord_8') or {}).get('par_canal') or []))
            for k, v in ((conf or {}).get("delivered") or {}).items()
            if v.get("accord_8")) or "-"),
        "             ecart en niveaux, canal par canal, entre la map 16 bits",
        "             requantifiee en 8 bits et la map 8 bits de reference.",
        # ── UNE BORNE INVENTEE, RETIREE ────────────────────────────────────
        # Cette notice ecrivait « un pas de 1 niveau sur X y deplace Z de 31,9
        # niveaux AU MAXIMUM ». Le chiffre etait faux, et il etait dementi par
        # la ligne juste au-dessus : sur cet export, l'ecart maximum mesure sur
        # le canal Z vaut 150 niveaux. La derivee exacte est dZ/dX = -x/z ; en
        # niveaux, l'amplification vaut |x/z| et elle N'EST PAS BORNEE (elle
        # diverge quand la normale approche le plan tangent). On ecrit donc la
        # formule, qui est vraie, et on renvoie au maximum MESURE ci-dessus,
        # au lieu d'une borne ronde que personne n'a calculee.
        "             Sur la normale, le canal Z porte le plus grand ecart :",
        "             il vaut sqrt(1 - x2 - y2), sa derivee en X vaut -x/z,",
        "             donc un pas de 1 niveau sur X deplace Z de |x/z|",
        "             niveaux — un facteur qui n'est pas borne et qui diverge",
        "             quand la normale approche le plan tangent (x2+y2 -> 1).",
        "             Le maximum atteint sur cet export est celui de la ligne",
        "             'ecart' ci-dessus.",
        "",
        "CONTENU  (profondeur et niveaux decodes dans le PNG livre : zlib +",
        "          defiltrage. niveaux = valeurs distinctes du canal le plus",
        "          riche.)",
    ]
    for e in entries:
        b = f"{e['bytes'] / 1024:.0f} Ko"
        if e.get("bits"):
            tail = (f"  {e['bits']} bits, {e.get('levels', 0)} niveaux "
                    f"({e.get('bits_effective', 0)} bits utiles)")
            if e.get("widened"):
                tail += ("  <- CONTENEUR 16 bits : "
                         f"{e.get('lattice_pct', 100.0)} % des echantillons "
                         "sur le reseau k*257")
            elif e.get("real16"):
                tail += (f"  <- 16 bits REELS : {e.get('levels', 0)} niveaux "
                         f"contre {e.get('levels_8', '?')} en 8 bits, "
                         f"{100.0 - float(e.get('lattice_pct') or 0.0):.1f} % "
                         "des echantillons HORS du reseau k*257")
            elif e.get("refused16"):
                tail += "  <- 16 bits demandes mais REFUSES (voir manifest.json)"
            # LE LIBELLE QUI MENTAIT : « constante : aucune information » etait
            # imprime sur emissive.png, qui porte 217 niveaux distincts. Une
            # map constante a UN niveau. Une map faible en porte beaucoup et
            # reste faible : ce sont deux phrases differentes.
            if e.get("constant"):
                tail += "  <- CONSTANTE : 1 seul niveau"
            elif not e.get("informative"):
                tail += (f"  <- faible : {e.get('levels', 0)} niveaux, "
                         "amplitude sous le seuil d'utilite")
        else:
            tail = "  maillage"
        lines.append(f"  {e['name']:<22s} {b:>10s}{tail}")
    lines += [
        "",
        "ESPACE DE COULEUR (chunk sRGB / gAMA ecrit dans chaque PNG)",
        "  basecolor et emissive : sRGB.",
        "  normal, roughness, metallic, ao, height, orm : LINEAIRES "
        "(gamma 1.0).",
        "",
        # ── LES QUATRE CONSEILS DE MONTAGE ──────────────────────────────────
        # Ils vivaient dans les `extras` du fichier, donc dans le GLB, dans le
        # glTF, dans les deux manifestes et dans les deux notices — la meme
        # prose recopiee six fois a l'interieur des octets livres. Elle a sa
        # place ICI, une fois, dans le document qui est fait pour etre lu.
        "MONTAGE DANS UN MOTEUR",
        "  Laissez metallicFactor et roughnessFactor a 1.0 : les niveaux sont",
        "  cuits dans les maps. glTF pose rugosite = roughnessFactor x",
        "  texture.G et metal = metallicFactor x texture.B ; reappliquer la",
        "  valeur du curseur la compterait deux fois.",
        "",
        "  Echantillonnez l'atlas en CLAMP_TO_EDGE. En REPEAT, le filtrage du",
        "  bord droit va chercher la colonne 0, c'est-a-dire l'autre face de",
        "  la carte.",
        "",
        f"  Emission de cette finition : {extras['render']['emissive']}. Les",
        "  finitions papier (mat, satine, vernis) sortent a 0 : une carte",
        "  imprimee n'emet pas de lumiere. Dorure et holographique gardent une",
        "  emission faible, sans quoi elles rendent grises hors HDRI.",
        "",
        "  height n'a pas d'equivalent en glTF coeur : il n'est que dans ce",
        "  ZIP. roughness, metallic et ao separes sont omis du GLB des qu'une",
        "  ORM existe (R = ao, G = rugosite, B = metal).",
    ]
    return "\n".join(lines) + "\n"


def build_deck_zip(doc: dict, rows: list, opt: dict) -> dict:
    """Le deck ENTIER dans un seul ZIP, avec son manifeste global."""
    did = doc["id"]
    out = out_dir(did, create=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for row in rows:
            for f in row["files"]:
                p = out / f["name"]
                if p.is_file():
                    z.writestr(f"{row['name']}/{f['name']}", p.read_bytes())
        z.writestr("manifest.json", json.dumps({
            "schema": DECK_MANIFEST_SCHEMA,
            "deck": {"id": did, "name": doc.get("name"),
                     "cards": len(rows)},
            "options": {k: opt[k] for k in ("res", "finish", "bits16", "img",
                                            "jpeg_q", "formats")},
            "files": [{"card": r["name"], "files": r["files"]} for r in rows],
        }, ensure_ascii=False, indent=2))
    data = buf.getvalue()
    fname = f"{slug_of(doc)}_deck.zip"
    (out / fname).write_bytes(data)
    return {"name": fname, "kind": "deck", "bytes": len(data),
            "label": f"Jeu complet — {len(rows)} carte(s), tous les formats"}


def build(doc: dict, opt: dict) -> dict:
    """Le bordereau complet d'un export, écrit sur disque et pesé."""
    did = doc["id"]
    have = atlas_indices(did)
    if not have:
        raise HTTPException(409, "Aucun atlas déposé pour ce jeu : composez "
                                 "l'atlas depuis l'écran avant d'exporter")
    # Une liste `cards` mal formée ne fait pas 500 : elle est filtrée sur ce
    # qui est réellement entier, et un filtre vide retombe sur ce qu'on a.
    asked = sorted({int(x) for x in (opt["cards"] or [])
                    if isinstance(x, (int, float)) and not isinstance(x, bool)
                    and math.isfinite(float(x))})
    want = [i for i in have if i in asked] if asked else list(have)
    if not want:
        want = list(have)
    if opt["scope"] != "deck":
        want = want[:1]
    want = want[:CARD_MAX]

    t0 = time.perf_counter()
    rows = [build_one(doc, i, opt) for i in want]
    files = [dict(f, card=r["name"]) for r in rows for f in r["files"]]
    if opt["scope"] == "deck" and len(rows) > 1:
        files.append(dict(build_deck_zip(doc, rows, opt), card=""))

    manifest = {
        "deck": {"id": did, "name": doc.get("name")},
        "scope": opt["scope"],
        "options": opt,
        "cards": rows,
        "files": files,
        "total_bytes": sum(f["bytes"] for f in files),
        "ms": int((time.perf_counter() - t0) * 1000),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        (gltf_dir(did, create=True) / "build.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8")
    except OSError as e:                       # pragma: no cover - disque plein
        logger.warning(f"cards/gltf: bordereau non écrit ({e})")
    return manifest


# ═══════════════════════════════════════════════════════════════════════════
# 6. ROUTES — chemins RELATIFS à /api/cards/{did}/gltf (règle 8)
# ═══════════════════════════════════════════════════════════════════════════
@router.get("/info")
async def get_info(did: str, res: str | None = None):
    """Tout ce que l'écran doit savoir SANS rien recalculer : les îlots, la
    densité réelle de la face, le compte de triangles du maillage « card »
    (et celui de la sphère, la preuve que l'enregistrement a pris — piège 9),
    les 8 maps, les finitions, les définitions.

    `res` sert la densité d'une définition QUELCONQUE (le champ numérique de
    l'écran, pas seulement les trois boutons) : c'est le backend qui la
    calcule, l'écran n'a aucune formule de pixel."""
    doc = _deck(did)
    g = _geom(doc)
    th = thickness_of(doc)
    mesh = card_mesh(g, solid_of(doc))
    stats = {}
    try:
        from app.services import gltf_builder as GB
        with _mesh_context(mesh):
            stats = {"card": GB.mesh_stats("card"),
                     "ctx": GB.mesh_stats(CTX_MESH),
                     "sphere": GB.mesh_stats("sphere")}
        stats["registered"] = CARD_MESH_REGISTERED
        stats["owner"] = card_builder_owner()
        stats["distinct"] = (stats["card"]["triangles"]
                             != stats["sphere"]["triangles"])
        stats["mesh_version"] = GB.MESH_VERSION
    except Exception as e:                     # pragma: no cover - env cassé
        logger.warning(f"cards/gltf: mesh_stats indisponible ({e})")
        stats = {"registered": False, "distinct": False}

    last = None
    try:
        p = gltf_dir(did) / "build.json"
        if p.is_file():
            last = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = None

    return {
        "geom": g.to_dict(),
        "thickness_mm": rnd(th, 3),
        "thickness_source": "solid" if isinstance(doc.get("solid"), dict)
                            and "thickness_mm" in doc["solid"] else "defaut",
        "size_mm": [rnd(g.trim_mm[0], 3), rnd(g.trim_mm[1], 3), rnd(th, 3)],
        "mesh": {**stats, **mesh_report(mesh),
                 "scale": physical_scale(mesh, g.trim_mm[1]),
                 "atlas_rects": len(UV_ISLANDS)},
        # LA VUE D'INSPECTION QUI MANQUAIT. Reproche répété et fondé : cet
        # écran demandait qu'on le croie sur ses îlots et ses UV sans jamais
        # savoir les MONTRER. On sert donc les triangles UV du maillage
        # LIVRÉ — l'écran les trace tels quels, il n'en calcule aucun.
        "uv_wire": {"tris": [[rnd(v, 5) for v in _uv_tri(mesh, t)]
                             for t in range(len(mesh.get("indices") or []) // 3)],
                    "note": ("Triangles UV du maillage livre, servis par le "
                             "backend : l'ecran ne recalcule aucune coordonnee.")},
        "atlas": {"islands_uv": {k: list(v) for k, v in UV_ISLANDS.items()},
                  "res_choices": list(RES_CHOICES),
                  "res_default": RES_DEFAULT,
                  "res_limits": [RES_MIN, RES_MAX],
                  # La définition à laquelle l'îlot cesse d'agrandir la coupe.
                  # Elle DÉPEND du format et du DPI du jeu : la calculer ici,
                  # une fois, évite que l'écran s'invente une formule.
                  "res_fit": res_fit(g),
                  "have": atlas_indices(did),
                  "density": {str(r): atlas_density(g, r, r, th, mesh)
                              for r in RES_CHOICES},
                  "density_ask": (None if res is None else
                                  {"res": clean_res(res),
                                   **atlas_density(g, clean_res(res),
                                                   clean_res(res), th, mesh)})},
        "maps": {"names": list(map_names()), "count": len(map_names()),
                 "in_glb": list(GLB_SLOTS)},
        # LA PROFONDEUR, MESURÉE SUR CE RUNTIME AVANT MÊME DE CONSTRUIRE.
        # « La source PBR est en 8 bits » ne se vérifiait sur rien ; ceci se
        # rejoue à chaque appel et publie l'erreur littérale de Pillow.
        "finishes": [{"id": k, "label": v["label"],
                      "roughness": v["roughness"], "metallic": v["metallic"],
                      "clearcoat": v["clearcoat"],
                      "emissive": float(v.get("emissive", 0.0)),
                      "sheen": float(v.get("sheen", 0.0)),
                      # Ce que la finition écrit RÉELLEMENT dans le fichier :
                      # l'écran n'a pas à le deviner, et il ne peut donc pas
                      # promettre une extension qui ne sortira pas.
                      "extensions": ([n for n, on in (
                          ("KHR_materials_clearcoat", v["clearcoat"] > 0.0),
                          ("KHR_materials_sheen", v.get("sheen", 0.0) > 0.0))
                          if on])}
                     for k, v in FINISHES.items()],
        "formats": list(FILE_FORMATS),
        "pivots": [
            {"id": "centre", "label": "Centre",
             "note": "origine au centre de la boîte englobante"},
            {"id": "bas", "label": "Posée debout",
             "note": "le bas de la carte à y = 0"},
            {"id": "dos", "label": "Couchée",
             "note": "le dos à z = 0, l'épaisseur au-dessus du plan"},
        ],
        # Qui porte le pivot, et comment. L'écran REPRENAIT cette liste à la
        # main et elle avait périmé (elle nommait trois formats sur cinq, le
        # PLY et le DXF étant sortis depuis). Elle vient d'ici, donc elle ne
        # peut plus dériver.
        "pivot_carriers": {"node": list(PIVOT_NODE_FORMATS),
                           "baked": list(PIVOT_BAKED_FORMATS)},
        "format_rows": [
            {"id": "glb", "label": "GLB",
             "note": "géométrie + matériau + textures, un seul fichier "
                     "(la texture émissive n'est embarquée que si la finition "
                     "émet vraiment)"},
            {"id": "gltf", "label": "glTF",
             "note": "le même en JSON, buffer en data URI — aucun .bin à côté"},
            {"id": "zip", "label": "ZIP des 8 maps",
             # Aucun poids en dur dans cette phrase : le bordereau pèse, et un
             # nombre qui ne vient pas d'une mesure n'a rien à faire à l'écran.
             "note": "les 8 PNG nommés, avec pHYs et espace de couleur, "
                     "+ manifest.json + le maillage OBJ — la géométrie, pas "
                     "une seconde copie du GLB"},
            {"id": "obj", "label": "OBJ + MTL",
             "note": "le repli universel, en mm, avec ses maps, son manifeste "
                     "et la même notice que le ZIP"},
            {"id": "stl", "label": "STL",
             "note": "facettes nues en mm pour l'impression 3D — le format "
                     "ne porte ni UV ni matière"},
            {"id": "3mf", "label": "3MF (couleur)",
             "note": "norme ouverte ISO/ASTM 52915 : millimètres inscrits "
                     "dans le fichier et COULEUR par facette, échantillonnée "
                     "sur la basecolor — ce que le STL ne sait pas porter"},
            {"id": "ply", "label": "PLY (couleur/sommet)",
             "note": "binaire, en mm, avec couleur PAR SOMMET, normales et UV "
                     "— la langue des chaînes de scan et des imprimantes "
                     "couleur ; ni le STL ni le DXF ne portent tout ça"},
            {"id": "dxf", "label": "DXF (3DFACE)",
             "note": "R12, entités 3DFACE en mm ($INSUNITS = 4), pour les "
                     "chaînes CAO et découpe. Faces nues : ni UV ni matière, "
                     "exactement comme le STL — il n'apporte pas plus, il "
                     "parle une autre langue"},
            {"id": "proof", "label": "Planche de contrôle",
             "note": "les 8 canaux côte à côte dans un PNG : regarder la "
                     "normale, l'AO et la hauteur sans ouvrir le ZIP"},
        ],
        # Ce qui n'est pas écrit est nommé AVEC SA RAISON, sans exception : une
        # page qui motive deux absences et en tait trois choisit son terrain.
        #
        # LE MOTIF DU DXF ÉTAIT FAUX et il est parti : cet écran écrivait
        # « format de DESSIN 2D », alors que le DXF porte des entités 3DFACE
        # depuis 1988. Un motif faux est pire qu'une absence — le format est
        # donc ÉCRIT (voir `build_dxf`) au lieu d'être refusé de travers. Il
        # ne reste ici que des absences dont la raison se vérifie.
        "formats_absents": [
            {"id": "fbx", "why": "format propriétaire Autodesk. L'ASCII 7.x "
                                 "s'écrit sans SDK — l'excuse « aucun "
                                 "écrivain libre » était trop commode — mais "
                                 "rien ici ne peut VÉRIFIER qu'un moteur "
                                 "ouvre ce qu'on écrirait, et cet écran ne "
                                 "livre que ce qu'il sait relire"},
            {"id": "usdz", "why": "l'aperçu AR ne se vérifie que sur un "
                                  "iPhone : livrer un USDZ non testé serait "
                                  "une promesse qu'on ne peut pas peser"},
            {"id": "blend", "why": "format interne de Blender, versionné avec "
                                   "le logiciel : l'écrire sans Blender c'est "
                                   "promettre une compatibilité qu'on ne peut "
                                   "pas tester — et Blender importe le .glb"},
        ],
        # LE COUPLAGE AVEC LA PIÈCE 06, RENDU VISIBLE. Il était mort en
        # silence : `derive_of` rendait l'enveloppe au lieu du sous-arbre, et
        # les douze curseurs de « Matières » n'avaient aucun effet sur le
        # fichier livré. Un couplage qu'on ne voit pas peut mourir sans bruit.
        "derive": {**derive_source(doc), "values": derive_of(doc),
                   "keys_known": list(derive_keys())},
        "img_formats": list(IMG_FORMATS),
        "thickness_limits": [THICKNESS_MM_MIN, THICKNESS_MM_MAX],
        # ── CE QUI SE MESURE, ET RIEN D'AUTRE ──────────────────────────────
        # Cette clé servait deux choses au même endroit : une auto-déclaration
        # (« 0 crédit, 0 compte, 0 plafond, 0 rétention ») et un relevé de
        # disque. La déclaration ne se vérifie sur rien, elle n'a donc plus à
        # être publiée ni imprimée : ce qui reste est ce que le dossier dit
        # tout de suite — combien de fichiers, quel poids, quel âge, et où.
        # Les quatre champs restent servis pour qui interroge l'API, mais
        # l'écran n'affiche que le relevé.
        "local": {"credits": 0, "account_required": False,
                  "monthly_cap": None, "retention_days": None,
                  "mesure": disk_evidence(did)},
        "last_build": last,
    }


@router.post("/atlas")
async def post_atlas(did: str, request: Request, i: str | None = None):
    """Dépose l'ATLAS composé par l'écran (corps = les octets PNG bruts).

    L'atlas vient du MOTEUR UNIQUE : `CF.renderCard` rend le recto et le verso
    à `geom.canvas_px`, l'écran les pose dans les trois îlots. Le backend ne
    redessine RIEN — c'est le risque n°2 de la spec (deux renderers = l'écran
    et le fichier divergent)."""
    doc = _deck(did)
    try:
        idx = int(float(i)) if i is not None else 0
    except (TypeError, ValueError):
        raise HTTPException(400, "L'index de carte doit être un entier")
    if idx < 0 or idx >= CARD_MAX:
        raise HTTPException(400, f"Index de carte hors bornes (0 à {CARD_MAX - 1})")
    data = await request.body()
    if not data:
        raise HTTPException(400, "Corps vide : l'atlas PNG est attendu tel quel")
    if len(data) > MAX_ATLAS_BYTES:
        raise HTTPException(400, f"Atlas trop lourd ({len(data) // 1024} Ko, "
                                 f"maximum {MAX_ATLAS_BYTES // 1024 // 1024} Mo)")

    def _write() -> dict:
        from PIL import Image
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                w, h = im.size
                fmt = (im.format or "").upper()
        except Exception:
            raise HTTPException(400, "Image illisible : PNG ou JPEG attendu")
        if w < 64 or h < 64:
            raise HTTPException(400, f"Atlas trop petit ({w}x{h}, minimum 64x64)")
        p = atlas_path(did, idx, create=True)
        if fmt == "PNG":
            p.write_bytes(data)
        else:
            with Image.open(io.BytesIO(data)) as im:
                im.convert("RGB").save(p, format="PNG")
        return {"index": idx, "res": [w, h], "bytes": p.stat().st_size,
                "format": fmt or "PNG"}

    try:
        info = await asyncio.to_thread(_write)
    except HTTPException:
        raise
    except OSError as e:
        logger.exception("cards/gltf: écriture de l'atlas impossible")
        raise HTTPException(500, f"Écriture de l'atlas impossible: {e}")
    g = _geom(doc)
    # Le maillage sert à MESURER le périmètre de la tranche (coins arrondis
    # compris) : sans lui, la densité de l'îlot de tranche retomberait sur le
    # rectangle à coins vifs, et l'écran afficherait un chiffre déduit là où
    # tous ses voisins sont mesurés.
    mesh = card_mesh(g, solid_of(doc))
    return {"atlas": {**info, "islands_px": islands_px(*info["res"]),
                      "density": atlas_density(g, *info["res"],
                                               thickness_of(doc), mesh),
                      "have": atlas_indices(did)}}


@router.get("/atlas")
async def get_atlas(did: str, i: str | None = None):
    """L'atlas déposé, tel quel — pour la vignette de l'écran et pour vérifier
    à l'oeil ce qui part dans le GLB."""
    _deck(did)
    try:
        idx = int(float(i)) if i is not None else 0
    except (TypeError, ValueError):
        raise HTTPException(400, "L'index de carte doit être un entier")
    p = atlas_path(did, idx)
    if not p.is_file():
        raise HTTPException(404, "Aucun atlas pour cette carte")
    return Response(content=p.read_bytes(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@router.post("/build")
async def post_build(did: str, body: dict | None = None):
    """CONSTRUIT tout, puis rend le BORDEREAU CHIFFRÉ.

    Les poids ne sont pas estimés : chaque fichier est écrit sur disque et pesé
    à l'octet. Même règle pour les profondeurs de PNG, la densité de l'atlas et
    l'état de la matière — tout ce que l'écran affiche est relu ici, sur les
    octets produits."""
    doc = _deck(did)
    opt = clean_options(body)
    try:
        return {"build": await asyncio.to_thread(build, doc, opt)}
    except HTTPException:
        raise
    except ModuleNotFoundError as e:
        raise HTTPException(503, f"Module requis absent: {e}")
    except MemoryError:
        raise HTTPException(409, "Mémoire insuffisante pour cette définition "
                                 "— essayez 2048 au lieu de 4096")
    except OSError as e:
        logger.exception("cards/gltf: écriture des livrables impossible")
        raise HTTPException(500, f"Écriture impossible: {e}")
    except Exception as e:
        logger.exception("cards/gltf: construction impossible")
        raise HTTPException(500, f"Construction impossible: {e}")


@router.get("/files")
async def get_files(did: str):
    """Le dernier bordereau, tel qu'il a été écrit. Rien n'expire, rien ne
    disparaît au bout de trois jours."""
    _deck(did)
    p = gltf_dir(did) / "build.json"
    if not p.is_file():
        return {"build": None, "files": []}
    try:
        man = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"build": None, "files": []}
    out = out_dir(did)
    files = []
    for f in man.get("files") or []:
        q = out / str(f.get("name") or "")
        if q.is_file():
            files.append({**f, "bytes": q.stat().st_size})
    return {"build": man, "files": files}


@router.get("/file/{name}")
async def get_file(did: str, name: str):
    """Un livrable, tel qu'il a été construit. Aucun badge PRO, aucun compte,
    aucun plafond : le fichier est déjà sur ce disque."""
    _deck(did)
    if not NAME_RE.match(name or ""):
        raise HTTPException(400, "Nom de fichier invalide")
    p = (out_dir(did) / name)
    if not p.is_file():
        raise HTTPException(404, "Fichier introuvable — reconstruisez l'export")
    media = {"glb": "model/gltf-binary", "gltf": "model/gltf+json",
             "zip": "application/zip", "stl": "model/stl",
             "3mf": "model/3mf", "ply": "model/ply",
             "dxf": "image/vnd.dxf",
             "png": "image/png"}.get(p.suffix.lstrip(".").lower(),
                                     "application/octet-stream")
    return Response(content=p.read_bytes(), media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{p.name}"',
        "Cache-Control": "no-store"})


@router.delete("/out")
async def delete_out(did: str):
    """Efface les livrables construits (pas les atlas). Utile pour repartir
    d'un bordereau propre."""
    _deck(did)
    import shutil
    d = out_dir(did)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)
    p = gltf_dir(did) / "build.json"
    try:
        if p.is_file():
            p.unlink()
    except OSError:
        pass
    return {"ok": True}
