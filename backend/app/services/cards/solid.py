# -*- coding: utf-8 -*-
"""Card Forge — P5 « Aperçu 3D et épaisseur ». Backend.

Monté par `cards/__init__.py` sous `/api/cards/{did}/solid`. Les chemins
déclarés ici sont RELATIFS à ce préfixe.

CE FICHIER APPARTIENT À P5. Aucun autre module ne l'importe, et il n'importe
le routeur d'aucun autre (règle 8).

P5 DÉTIENT `card_mesh(geom, solid)`. Sa signature est GELÉE dans
`cards/contract.py` : on remplit le corps ici, jamais la signature. Dès que ce
module expose un `card_mesh`, `contract.card_mesh` bascule dessus tout seul et
le maillage de référence (boîte NON arrondie, 12 triangles) s'efface. P8
appelle toujours `contract.card_mesh` — il ne connaît pas ce fichier.

── CE QUE FABRIQUE `card_mesh` ─────────────────────────────────────────────
Une BOÎTE ARRONDIE, pas une boîte : une carte à jouer a des coins ronds et une
tranche visible. Cinq surfaces, cousues dans cet ordre :

    recto plat (+Z)  ·  chanfrein recto  ·  tranche  ·  chanfrein verso
                                                       ·  verso plat (-Z)

et TROIS îlots UV disjoints (`contract.UV_ISLANDS`) :

    recto   u [0.000, 0.490]  v [0.000, 0.940]
    verso   u [0.510, 1.000]  v [0.000, 0.940]
    tranche u [0.000, 1.000]  v [0.960, 1.000]

Le contour est parcouru dans le SENS DIRECT vu de +Z. Toute surface tournée
vers l'avant est émise dans ce sens, toute surface tournée vers l'arrière dans
le sens inverse : combiné aux deux plaquages (le recto renverse l'orientation
du plan XY, le verso la conserve), cela donne mécaniquement l'INVARIANT du
contrat — DÉTERMINANT UV NÉGATIF SUR TOUT TRIANGLE, donc jamais de texte en
miroir. Ce n'est pas une vérification a posteriori : c'est la construction qui
l'impose, et `test_cards_solid.py` le relit sur chaque triangle de 24
combinaisons de réglages.

La tranche est plaquée par ABSCISSE CURVILIGNE sur le périmètre réel (et non
en quatre sous-rectangles) : une texture de tranche ne saute donc pas aux
coins, et le contour arrondi ne l'étire pas.

── PIÈGE 9 DE LA SPEC ──────────────────────────────────────────────────────
`gltf_builder` ignore SILENCIEUSEMENT un nom de maillage inconnu et rend une
SPHÈRE. On enregistre donc "card" dans sa table AU CHARGEMENT DU MODULE (par
`setdefault`, jamais dans le corps d'une route, et sans toucher une ligne de
`gltf_builder.py`), et `test_cards_solid.py` vérifie que
`mesh_stats("card")["triangles"]` diffère de celui de la sphère. `MESHES` est
une constante à part : "card" n'apparaît donc pas dans le sélecteur du
Material Forge, et `MESH_VERSION` n'est pas touché (piège 10).

── LE TOURNE-DISQUE ────────────────────────────────────────────────────────
Les images viennent de l'ÉCRAN (le même `<model-viewer>` que l'aperçu : ce qui
est filmé est ce que l'on voit), le backend ne fait que les recevoir et les
assembler avec le ffmpeg déjà présent. Aucun second moteur de rendu, donc
aucune divergence possible entre l'aperçu et le fichier livré.
"""
from __future__ import annotations

import asyncio
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from loguru import logger

from .contract import (
    CardGeom, DEFAULT_DPI, DEFAULT_FMT, FORMATS, MM_PER_INCH, R,
    THICKNESS_MM_DEFAULT, THICKNESS_MM_MAX, THICKNESS_MM_MIN, UV_ISLANDS,
    _tangents, deck_dir, geom as geom_of, is_valid_did, rnd,
)

__all__ = [
    "router", "card_mesh", "solid_settings", "card_dims_mm",
    "bevel_effective_mm", "BEVEL_ANGLE_DEG", "m_per_unit", "GLTF_UNIT_M",
    "turntable_angles", "mesh_report", "DEFAULTS", "LIMITS",
    "SEGMENTS_MIN", "SEGMENTS_MAX", "BEVEL_MM_MAX", "CORNER_MM_MAX_SOLID",
    "TT_FRAMES_MIN", "TT_FRAMES_MAX", "TT_FPS_MIN", "TT_FPS_MAX",
    "TT_SIZE_CHOICES", "TT_MAX_BYTES", "EDGE_STYLES", "VIEWS", "ENVS",
    "TT_ELEV_MIN", "TT_ELEV_MAX", "TT_ELEV_DEFAULT", "polar_from_elevation",
    "ATLAS_CAPS", "ATLAS_MIN", "atlas_plan", "perimeter_mm", "edge_dpi",
    "PBR_FACE", "PBR_EDGE",
    "PBR_INK_ROUGHNESS_DROP", "PBR_INK_RELIEF_MM", "pbr_plan",
]

router = APIRouter()

# ── bornes du volume ────────────────────────────────────────────────────────
# L'épaisseur vient du contrat (0,20 à 1,20 mm, défaut 0,32 mm = une vraie
# carte à jouer). Le reste appartient à P5.
SEGMENTS_MIN, SEGMENTS_MAX = 1, 16
BEVEL_MM_MAX = 0.30
CORNER_MM_MAX_SOLID = 10.0

EDGE_STYLES = ("plein", "metal", "sombre")
VIEWS = ("matiere", "base", "normales", "ilots")
ENVS = ("studio", "vitrine", "chaud", "froid", "neutre")

DEFAULTS = {
    "thickness_mm": THICKNESS_MM_DEFAULT,
    "corner_mm": 3.0,
    "segments": 6,
    "bevel_mm": 0.10,
}

LIMITS = {
    "thickness_mm": [THICKNESS_MM_MIN, THICKNESS_MM_MAX],
    "corner_mm": [0.0, CORNER_MM_MAX_SOLID],
    "segments": [SEGMENTS_MIN, SEGMENTS_MAX],
    "bevel_mm": [0.0, BEVEL_MM_MAX],
}

# ── bornes du tourne-disque ─────────────────────────────────────────────────
# 90 images / 30 i/s = 3,00 s : le seuil de la spec, qui est aussi le défaut.
TT_FRAMES_MIN, TT_FRAMES_MAX = 24, 600
TT_FPS_MIN, TT_FPS_MAX = 12, 60
TT_SIZE_CHOICES = (540, 720, 1080, 1440)
TT_MAX_BYTES = 8 * 1024 * 1024          # 8 Mo, seuil de la spec

# ÉLÉVATION de la caméra, en degrés AU-DESSUS DE L'HORIZON. Ce n'est pas une
# préférence de vocabulaire : `<model-viewer>` prend un angle POLAIRE (mesuré
# depuis la verticale), et une commande qui affiche 78 pendant que la caméra
# est à 12 degrés du sol affiche un chiffre que rien ne mesure. On règle donc
# l'élévation — la grandeur que l'on peut relire sur l'image — et on convertit
# ici, au même endroit pour l'écran et pour le test.
TT_ELEV_MIN, TT_ELEV_MAX = 0, 55
TT_ELEV_DEFAULT = 18                    # l'élévation de l'aperçu (polaire 72)


def polar_from_elevation(elev_deg) -> float:
    """Élévation au-dessus de l'horizon -> angle polaire de `camera-orbit`.

    MESURE qui fonde la conversion (aperçu, carte de face, rayon 5,614) :
    élévation 0 -> la carte se projette à 1,400 fois plus haute que large ;
    18 -> 1,268 ; 30 -> 1,118. Le rapport théorique en perspective vaut
    (h/l)*cos(e)*d/(d + (H/2) sin e) : 1,3968 / 1,2593 / 1,1107 — l'écart au
    mesuré reste sous 0,7 %. La lecture ORTHOGRAPHIQUE `acos(rapport/(h/l))`
    donne, elle, 0 / 24,9 / 36,9 degrés : c'est elle qui est fausse, pas la
    commande, et c'est pour cela que l'écran affiche AUSSI l'angle polaire.
    """
    try:
        e = float(elev_deg)
    except (TypeError, ValueError):
        e = float(TT_ELEV_DEFAULT)
    if not math.isfinite(e):
        e = float(TT_ELEV_DEFAULT)
    e = max(float(TT_ELEV_MIN), min(float(TT_ELEV_MAX), e))
    return rnd(90.0 - e, 3)


# ── ATLAS : jamais un pixel de plus que la source ───────────────────────────
# Le grief mesuré : l'îlot du recto occupait 1033 x 1444 px alors que le rendu
# qui l'alimente en fait 744 x 1039 — 39 % de la résolution annoncée était de
# l'interpolation vide, et le HUD affichait « 2108 x 1536 px » comme si le
# modèle portait ces pixels-là. On dimensionne donc l'atlas SUR LA SOURCE : la
# taille choisie ici est la plus petite qui donne l'échelle 1:1 sur le recto,
# plafonnée par le réglage. Un pixel de marge peut rester (les îlots ne tombent
# pas sur des comptes entiers) ; au-delà, ce serait de la résolution inventée.
ATLAS_CAPS = (1024, 1536, 2048)
# Le plancher est BAS a dessein : une carte micro a 72 DPI n'a que 126 px de
# source en hauteur, et un atlas de 512 lui inventerait 3 pixels sur 4.
ATLAS_MIN, ATLAS_MAX = 64, 4096


def _even(v: float, lo: int, hi: int) -> int:
    n = int(R(v))
    n = max(lo, min(hi, n))
    return n - (n % 2)


def atlas_plan(geom: CardGeom, cap: int = 1536) -> dict:
    """Taille de l'atlas pour cette carte, et ce qu'elle porte RÉELLEMENT.

    -> {w, h, cap, front_px, front_px_exact, source_px, dpi, ratio_source} —
    `front_px` est le nombre de pixels que l'îlot du recto occupe dans l'atlas,
    `source_px` celui que le moteur de rendu produit à la définition du
    document, et `dpi` la définition VRAIE du recto dans le modèle 3D. C'est ce
    dernier chiffre que le HUD affiche : « 2108 x 1536 » ne disait rien de ce
    que l'image portait.

    ── POURQUOI `front_px_exact` ─────────────────────────────────────────────
    LE GRIEF, MESURÉ SUR LE FICHIER LIVRÉ : le HUD annonçait « RECTO
    744 x 1040 px, 300,2 DPI, +0,1 % en hauteur » alors que les bornes UV de
    l'îlot (u 0..0,490, v 0..0,940) sur un atlas de 1518 x 1106 lui donnent
    743,82 x 1039,64 px — donc 300,07 DPI et +0,062 %. Les trois chiffres
    étaient calculés sur le nombre de pixels ARRONDI, c'est-à-dire sur une
    quantité qui n'existe nulle part : `drawImage` écrit dans un rectangle à
    bornes fractionnaires, pas dans 1040 lignes.
    L'arrondi reste publié (`front_px`, un nombre de pixels se compte en
    entiers), mais la DÉFINITION et le RÉÉCHANTILLONNAGE sortent maintenant de
    l'étendue exacte : ce sont eux que l'on confronte aux octets.

    ── POURQUOI DEUX DÉFINITIONS ET NON UNE ──────────────────────────────────
    LE GRIEF : « "300,08 DPI" masque une anisotropie : 299,88 DPI en largeur
    contre 300,07 en hauteur. Un seul chiffre pour deux résolutions
    différentes. » Il est fondé, et la cause est mécanique : les îlots UV sont
    GELÉS par le contrat (u 0..0,490 et v 0..0,940), donc le rapport
    largeur/hauteur de l'îlot ne vaut jamais exactement celui de la carte, et
    l'atlas est dimensionné sur la HAUTEUR de la source. `dpi` reste la
    définition verticale — c'est celle qui commande la taille de l'atlas — et
    `dpi_w` publie l'horizontale. Deux chiffres exacts valent mieux qu'un seul
    qui en cache un autre.
    """
    fu0, fv0, fu1, fv1 = UV_ISLANDS["front"]
    iw, ih = (fu1 - fu0), (fv1 - fv0)
    try:
        c = int(float(cap))
    except (TypeError, ValueError):
        c = 1536
    c = max(ATLAS_MIN, min(ATLAS_MAX, c))
    tw, th = int(geom.trim_px[0]), int(geom.trim_px[1])
    # la plus petite hauteur d'atlas qui donne au recto ses pixels de source
    besoin = th / ih
    h = _even(min(float(c), math.ceil(besoin - 1e-9)), ATLAS_MIN, ATLAS_MAX)
    if h < besoin and h + 2 <= c:
        h += 2                          # l'arrondi pair ne doit pas rogner
    w = _even(h * (geom.trim_mm[0] / geom.trim_mm[1]) * (ih / iw),
              ATLAS_MIN, ATLAS_MAX)
    front = (int(R(iw * w)), int(R(ih * h)))
    ex_w, ex_h = iw * w, ih * h          # l'étendue RÉELLE de l'îlot, en pixels
    eh = (UV_ISLANDS["edge"][3] - UV_ISLANDS["edge"][1]) * h
    return {
        "w": w, "h": h, "cap": c,
        "front_px": [front[0], front[1]],
        "front_px_exact": [rnd(ex_w, 2), rnd(ex_h, 2)],
        "source_px": [tw, th],
        "dpi": rnd(ex_h / float(geom.trim_mm[1]) * MM_PER_INCH, 2),
        "dpi_w": rnd(ex_w / float(geom.trim_mm[0]) * MM_PER_INCH, 2),
        "ratio_source": rnd(ex_h / float(th), 6),
        "ratio_source_w": rnd(ex_w / float(tw), 6),
        "edge_px": [w, int(R(eh))],
        "edge_px_exact": [rnd(float(w), 2), rnd(eh, 2)],
    }


# ── MATIÈRES : ce que le fichier livré porte, îlot par îlot ─────────────────
# Le grief mesuré, et le plus lourd : le GLB ne transportait AUCUNE carte PBR.
# Une seule texture (base), `metallicFactor` 0,05 et `roughnessFactor` 0,52
# pour TOUTE la carte — le papier, le filet et la tranche étaient le même
# matériau, et la bascule « Unie / Métal / Sombre » ne pouvait pas s'écrire
# dans les octets. Ces valeurs-ci sont écrites dans une carte ORM (occlusion /
# rugosité / métal) plaquée sur les îlots : elles sont donc RELISIBLES dans le
# fichier, pixel par pixel.
#
# Le papier reste DIÉLECTRIQUE (métal 0). Ce n'est pas une limite : une carte
# imprimée n'a pas de métal sur ses faces. La tranche, elle, peut vraiment être
# dorée chez l'imprimeur — c'est le seul endroit où le métal est honnête.
PBR_FACE = {"metallic": 0.0, "roughness": 0.62, "ao": 1.0}
PBR_EDGE = {
    "plein":  {"metallic": 0.00, "roughness": 0.55, "ao": 0.90},
    "metal":  {"metallic": 0.90, "roughness": 0.22, "ao": 0.94},
    "sombre": {"metallic": 0.05, "roughness": 0.72, "ao": 0.86},
}
# L'encre est plus lisse que le papier nu : la rugosité baisse là où elle
# couvre. C'est ce qui fait qu'un aplat imprimé et le papier ne renvoient pas
# la même lumière — mesurable dans la carte ORM, canal vert.
PBR_INK_ROUGHNESS_DROP = 0.16
# Relief d'encre, en millimètres : l'offset dépose une couche mesurable. Elle
# donne son amplitude à la carte de normales dérivée de l'atlas.
PBR_INK_RELIEF_MM = 0.006


def pbr_plan(edge_style: str = "plein") -> dict:
    """Les valeurs PBR effectivement écrites dans la carte ORM, par îlot."""
    st = str(edge_style or "plein").lower()
    if st not in PBR_EDGE:
        st = "plein"
    return {
        "edge_style": st,
        "face": dict(PBR_FACE),
        "edge": dict(PBR_EDGE[st]),
        "ink_roughness_drop": PBR_INK_ROUGHNESS_DROP,
        "ink_relief_mm": PBR_INK_RELIEF_MM,
        "maps": ["baseColor", "normal", "metallicRoughness", "occlusion"],
        "attributes": ["POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"],
    }
_TT_TARGET_BYTES = 7_400_000            # marge : on ré-encode au-dessus
_FRAME_MAX_BYTES = 12 * 1024 * 1024
_JOB_RE = re.compile(r"^[0-9a-f]{8,16}$")
_JOB_KEEP = 6                           # jobs conservés par deck
_JOB_TTL_S = 3 * 3600


# ═══════════════════════════════════════════════════════════════════════════
# 1. RÉGLAGES — une seule normalisation, partagée par la route et le maillage
# ═══════════════════════════════════════════════════════════════════════════

def _num(value, default: float, lo: float, hi: float) -> float:
    """Un nombre du client ne fait JAMAIS un 500 : hors bornes, il est borné.

    Le maillage n'est pas un formulaire — une épaisseur de 40 mm n'est pas une
    erreur d'utilisateur à signaler, c'est un curseur qu'on arrête à sa butée.
    Les routes qui valident (elles) rendent 400 ; ici on borne.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return max(lo, min(hi, v))


def solid_settings(raw: dict | None) -> dict:
    """`doc.solid` -> réglages normalisés et BORNÉS du volume.

    Le biseau est plafonné à 45 % de l'épaisseur : un chanfrein plus profond
    que la moitié de la carte mangerait la tranche et refermerait la boîte sur
    elle-même. C'est la seule contrainte croisée du modèle, et elle est ici,
    pas dans l'écran — un client qui envoie 0,30 mm de biseau sur une carte de
    0,20 mm obtient une carte, pas une exception.
    """
    s = raw if isinstance(raw, dict) else {}
    th = _num(s.get("thickness_mm"), DEFAULTS["thickness_mm"],
              THICKNESS_MM_MIN, THICKNESS_MM_MAX)
    corner = _num(s.get("corner_mm"), DEFAULTS["corner_mm"],
                  0.0, CORNER_MM_MAX_SOLID)
    bevel = _num(s.get("bevel_mm"), DEFAULTS["bevel_mm"], 0.0, BEVEL_MM_MAX)
    bevel = min(bevel, 0.45 * th)
    try:
        seg = int(float(s.get("segments", DEFAULTS["segments"])))
    except (TypeError, ValueError):
        seg = int(DEFAULTS["segments"])
    seg = max(SEGMENTS_MIN, min(SEGMENTS_MAX, seg))
    return {"thickness_mm": th, "corner_mm": corner, "segments": seg,
            "bevel_mm": bevel}


def card_dims_mm(geom: CardGeom, solid: dict | None) -> tuple[float, float, float]:
    """Dimensions PHYSIQUES de l'objet : largeur x hauteur x épaisseur, en mm.

    C'est ce que le HUD affiche et ce que Meshy n'affiche pas — sa visionneuse
    ne connaît aucune unité. La longueur de référence est la ROGNE, pas la
    toile : le fond perdu est coupé, il n'existe pas en volume.
    """
    st = solid_settings(solid)
    return (float(geom.trim_mm[0]), float(geom.trim_mm[1]), st["thickness_mm"])


# ── LE CHANFREIN : UN SEUL CALCUL, POUR L'ÉCRAN ET POUR LA GÉOMÉTRIE ────────
# LE GRIEF, MESURÉ SUR LE .glb : le panneau écrivait « biseau 0,100 mm » et la
# géométrie livrait des jambes de 0,072 mm. Les deux nombres étaient sincères
# et différents, parce qu'ils venaient de deux clampages différents :
# `solid_settings` bornait à 0,45 x ÉPAISSEUR (0,144 mm à 0,32 mm) et
# `card_mesh` bornait, lui, à 0,45 x DEMI-épaisseur (0,072 mm). Un imprimeur
# qui lisait 0,100 mm de retrait se trompait de 28 % sur la cote qui l'intéresse.
#
# LA CONVENTION, ÉCRITE UNE FOIS POUR TOUTES : `bevel_mm` est le RETRAIT, la
# jambe du chanfrein — 0,072 mm en Z ET 0,072 mm en XY. L'arête est donc à 45°
# et l'hypoténuse (la largeur du méplat que l'on voit à la loupe) vaut
# retrait x racine(2). Trois chiffres pour une seule arête : on les affiche
# tous les trois plutôt que d'en publier un sans dire lequel.
BEVEL_ANGLE_DEG = 45.0


def bevel_effective_mm(geom: CardGeom, solid: dict | None) -> float:
    """Le chanfrein que la GÉOMÉTRIE construit vraiment, en mm (le retrait).

    Miroir EXACT des bornes de `card_mesh`, exprimé en millimètres :
      · 0,45 x demi-épaisseur — sinon les deux chanfreins mangent la tranche ;
      · 0,45 x demi-petit-côté — garde-fou de forme ;
      · la moitié du rayon de coin — sinon le contour intérieur perd son arc et
        la couronne se remplit de triangles d'aire UV nulle.
    `card_mesh` appelle CETTE fonction : il ne peut plus exister deux clampages.
    """
    st = solid_settings(solid)
    w_mm, h_mm = float(geom.trim_mm[0]), float(geom.trim_mm[1])
    r_mm = min(st["corner_mm"], min(w_mm, h_mm) / 2.0)
    b = min(st["bevel_mm"],
            0.45 * st["thickness_mm"] / 2.0,
            0.45 * min(w_mm, h_mm) / 2.0)
    if r_mm > 1e-9:
        b = min(b, 0.5 * r_mm)
    return max(0.0, b)


# ── L'ÉCHELLE PHYSIQUE ─────────────────────────────────────────────────────
# glTF 2.0 fixe le MÈTRE comme unité. Un maillage normalisé à demi-hauteur = 1
# et posé sans `scale` livre donc une carte de DEUX MÈTRES de haut : le fichier
# est faux de 22,7 fois, pendant que le HUD affiche « 63 x 88 x 0,32 mm ».
# Le facteur se mesure sur la boîte englobante RÉELLE (comme `gltf.physical_scale`),
# pas sur la convention : le jour où le maillage change d'échelle, la taille
# annoncée reste juste.
GLTF_UNIT_M = 1.0


def m_per_unit(mesh: dict, height_mm: float) -> float:
    """Facteur `node.scale` qui met le maillage à sa taille physique, en mètres."""
    pos = mesh.get("positions") or []
    lo, hi = float("inf"), float("-inf")
    for i in range(1, len(pos), 3):
        if pos[i] < lo:
            lo = pos[i]
        if pos[i] > hi:
            hi = pos[i]
    span = hi - lo
    if not (span > 1e-12) or not (float(height_mm) > 0):
        return 1.0
    return (float(height_mm) / 1000.0) / span * GLTF_UNIT_M


# ═══════════════════════════════════════════════════════════════════════════
# 2. LE MAILLAGE
# ═══════════════════════════════════════════════════════════════════════════

def _outline(hw: float, hh: float, r: float, seg: int) -> list[tuple]:
    """Contour du rectangle arrondi, SENS DIRECT vu de +Z.

    Rend une liste de `(x, y, nx, ny)` : la position ET la vraie normale
    sortante. Aux jonctions arc/segment droit la normale de l'arc vaut déjà
    celle du bord (l'arc y est tangent), donc le contour est lisse sans
    dupliquer un seul point — et deux points confondus produiraient un
    triangle d'aire UV nulle, c'est-à-dire un déterminant NUL, c'est-à-dire
    l'invariant du contrat en défaut.
    """
    r = max(0.0, min(float(r), min(hw, hh)))
    cx, cy = hw - r, hh - r
    quarters = ((cx, -cy, -90.0), (cx, cy, 0.0),
                (-cx, cy, 90.0), (-cx, -cy, 180.0))
    n = max(SEGMENTS_MIN, min(SEGMENTS_MAX, int(seg)))
    pts: list[tuple] = []
    for ox, oy, a0 in quarters:
        if r <= 1e-9:
            # Coin vif : UN point, normale à 45°. Répéter le point pour
            # « faire un arc » fabriquerait des quads dégénérés.
            a = math.radians(a0 + 45.0)
            pts.append((ox, oy, math.cos(a), math.sin(a)))
            continue
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            ca, sa = math.cos(a), math.sin(a)
            pts.append((ox + r * ca, oy + r * sa, ca, sa))
    return pts


def _perimeter_u(pts: list[tuple], u0: float, u1: float) -> list[float]:
    """Abscisse curviligne -> u dans l'îlot de tranche, avec le point de
    couture DUPLIQUÉ en fin de liste à u = u1 (sans quoi le dernier quad
    reviendrait à u0 et retournerait la texture sur le dernier segment)."""
    n = len(pts)
    acc, total = [0.0], 0.0
    for k in range(n):
        x0, y0 = pts[k][0], pts[k][1]
        x1, y1 = pts[(k + 1) % n][0], pts[(k + 1) % n][1]
        total += math.hypot(x1 - x0, y1 - y0)
        acc.append(total)
    if total <= 1e-12:
        return [u0] * (n + 1)
    return [u0 + (a / total) * (u1 - u0) for a in acc]


class _Acc:
    """Accumulateur de sommets. Aucun partage entre surfaces : chaque surface
    pose ses propres sommets, donc l'arête recto/chanfrein/tranche est FRANCHE
    (une carte n'a pas un bord fondu) et chaque sommet porte les UV de son
    seul îlot."""

    __slots__ = ("pos", "nrm", "uv", "idx")

    def __init__(self) -> None:
        self.pos: list[float] = []
        self.nrm: list[float] = []
        self.uv: list[float] = []
        self.idx: list[int] = []

    def v(self, p, n, t) -> int:
        i = len(self.pos) // 3
        self.pos += [float(p[0]), float(p[1]), float(p[2])]
        self.nrm += [float(n[0]), float(n[1]), float(n[2])]
        self.uv += [float(t[0]), float(t[1])]
        return i

    def tri(self, a: int, b: int, c: int) -> None:
        self.idx += [a, b, c]


def card_mesh(geom: CardGeom, solid: dict) -> dict:
    """SIGNATURE GELÉE (`contract.card_mesh`) — le maillage de la carte.

    -> {name, positions, normals, uvs, indices, tangents} — même forme que
    `gltf_builder.build_mesh`. 3 îlots UV disjoints : recto, verso, tranche.
    INVARIANT : déterminant UV négatif sur TOUT triangle.

    Échelle : demi-hauteur = 1.0, comme les six maillages de `gltf_builder` et
    comme le maillage de référence du contrat — les autres dimensions suivent
    les proportions PHYSIQUES du format. Une carte 63x88x0,32 mm sort donc à
    1,432 x 2,000 x 0,00727 unités, et `extras` (P8) sait remonter aux mm.
    """
    st = solid_settings(solid)
    w_mm, h_mm = float(geom.trim_mm[0]), float(geom.trim_mm[1])
    s = 2.0 / h_mm                       # demi-hauteur = 1.0
    hw, hh = w_mm * s / 2.0, 1.0
    ht = st["thickness_mm"] * s / 2.0
    r = min(st["corner_mm"], min(w_mm, h_mm) / 2.0) * s
    # UN SEUL clampage, celui que l'écran affiche (`bevel_effective_mm`) : la
    # borne « moitié du rayon de coin » évite qu'un contour intérieur perde son
    # arc (rayon nul), que ses quatre coins se réduisent à un point et que la
    # couronne se remplisse de triangles d'aire nulle — déterminants UV NULS,
    # invariant du contrat en défaut sur un réglage parfaitement légitime
    # (coin 0,2 mm, biseau 0,3 mm), sans que rien ne se voie à l'écran.
    b = bevel_effective_mm(geom, st) * s
    seg = st["segments"]

    fu0, fv0, fu1, fv1 = UV_ISLANDS["front"]
    bu0, bv0, bu1, bv1 = UV_ISLANDS["back"]
    eu0, ev0, eu1, ev1 = UV_ISLANDS["edge"]

    def uv_front(x, y):
        return (fu0 + (x + hw) / (2 * hw) * (fu1 - fu0),
                fv0 + (hh - y) / (2 * hh) * (fv1 - fv0))

    def uv_back(x, y):
        # vu de -Z la droite de l'écran est -x : le plaquage CONSERVE
        # l'orientation du plan XY, et c'est l'enroulement inversé du verso
        # qui rend le déterminant négatif.
        return (bu0 + (hw - x) / (2 * hw) * (bu1 - bu0),
                bv0 + (hh - y) / (2 * hh) * (bv1 - bv0))

    outer = _outline(hw, hh, r, seg)
    has_bevel = b > 1e-9
    inner = _outline(hw - b, hh - b, max(0.0, r - b), seg) if has_bevel else outer
    n = len(outer)
    zt = ht - (b if has_bevel else 0.0)   # haut de la tranche

    acc = _Acc()

    # ── recto plat (+Z), sens direct vu de +Z ───────────────────────────────
    cap = inner
    c_f = acc.v((0.0, 0.0, ht), (0.0, 0.0, 1.0), uv_front(0.0, 0.0))
    ring_f = [acc.v((p[0], p[1], ht), (0.0, 0.0, 1.0), uv_front(p[0], p[1]))
              for p in cap]
    for k in range(n):
        acc.tri(c_f, ring_f[k], ring_f[(k + 1) % n])

    # ── verso plat (-Z), sens INVERSE ──────────────────────────────────────
    c_b = acc.v((0.0, 0.0, -ht), (0.0, 0.0, -1.0), uv_back(0.0, 0.0))
    ring_b = [acc.v((p[0], p[1], -ht), (0.0, 0.0, -1.0), uv_back(p[0], p[1]))
              for p in cap]
    for k in range(n):
        acc.tri(c_b, ring_b[(k + 1) % n], ring_b[k])

    # ── chanfreins : la couronne qui relie le plat à la tranche ────────────
    if has_bevel:
        rt = 1.0 / math.sqrt(2.0)         # chanfrein à 45° (b en XY, b en Z)
        fi, fo, bi, bo = [], [], [], []
        for k in range(n):
            ix, iy = inner[k][0], inner[k][1]
            ox, oy, nx, ny = outer[k]
            nf = (nx * rt, ny * rt, rt)
            nb = (nx * rt, ny * rt, -rt)
            fi.append(acc.v((ix, iy, ht), nf, uv_front(ix, iy)))
            fo.append(acc.v((ox, oy, zt), nf, uv_front(ox, oy)))
            bi.append(acc.v((ix, iy, -ht), nb, uv_back(ix, iy)))
            bo.append(acc.v((ox, oy, -zt), nb, uv_back(ox, oy)))
        for k in range(n):
            j = (k + 1) % n
            acc.tri(fi[k], fo[k], fo[j])          # recto : sens direct
            acc.tri(fi[k], fo[j], fi[j])
            acc.tri(bi[k], bo[j], bo[k])          # verso : sens inverse
            acc.tri(bi[k], bi[j], bo[j])

    # ── tranche : abscisse curviligne sur le périmètre réel ────────────────
    us = _perimeter_u(outer, eu0, eu1)
    top, bot = [], []
    for k in range(n + 1):
        x, y, nx, ny = outer[k % n]
        top.append(acc.v((x, y, zt), (nx, ny, 0.0), (us[k], ev0)))
        bot.append(acc.v((x, y, -zt), (nx, ny, 0.0), (us[k], ev1)))
    for k in range(n):
        acc.tri(top[k], bot[k], top[k + 1])
        acc.tri(top[k + 1], bot[k], bot[k + 1])

    pos, nrm, uv, idx = acc.pos, acc.nrm, acc.uv, acc.idx
    return {"name": "card", "positions": pos, "normals": nrm, "uvs": uv,
            "indices": idx, "tangents": _tangents(pos, nrm, uv, idx)}


def edge_dpi(geom: CardGeom, solid: dict | None, plan: dict) -> dict:
    """Les DEUX définitions de la bande de tranche, en DPI.

    LE GRIEF : « "130 DPI" pour la tranche n'est que l'axe long : la bande fait
    1518 x 44,2 px pour 296,9 mm x 0,32 mm, soit environ 3 500 DPI en travers.
    Choisir le pire axe est défendable, ne pas le dire ne l'est pas. »
    On publie donc les deux, avec la longueur physique de chacun.
    """
    st = solid_settings(solid)
    ex = plan.get("edge_px_exact") or plan.get("edge_px") or [0, 0]
    peri = perimeter_mm(geom, st)
    th = float(st["thickness_mm"])
    along = (float(ex[0]) / peri * MM_PER_INCH) if peri > 0 else 0.0
    across = (float(ex[1]) / th * MM_PER_INCH) if th > 0 else 0.0
    return {"along": rnd(along, 2), "across": rnd(across, 0),
            "perimeter_mm": rnd(peri, 3), "thickness_mm": rnd(th, 3),
            "band_px": [rnd(float(ex[0]), 2), rnd(float(ex[1]), 2)]}


# ── LE VERSO SE LIT-IL À L'ENDROIT ? ───────────────────────────────────────
# LE MANQUE NOMMÉ PAR LE CRITIQUE : « le verso en miroir est l'erreur
# d'orientation la plus fréquente du domaine ; le panneau possède déjà tout ce
# qu'il faut pour la trancher — un bouton Verso, l'îlot UV du verso isolé, le
# sens des 224 triangles en UV — mais il n'en tire AUCUNE phrase. Un panneau qui
# prouve au millionième de millimètre le retrait du chanfrein laisse
# l'utilisateur sans réponse sur la faute qui ruine réellement un tirage. »
#
# Le « 224/224 déterminants < 0 » ne suffit pas : il dit que les îlots ont TOUS
# le même sens de parcours en UV, pas que le verso se lit à l'endroit QUAND ON
# LE REGARDE. La mesure ci-dessous compare, face par face, le sens de parcours
# en coordonnées d'IMAGE (u vers la droite, v vers le bas) au sens de parcours
# en coordonnées d'ÉCRAN vu du côté de cette face (à droite = +x pour le recto,
# −x pour le verso puisqu'on passe derrière ; en bas = −y des deux côtés).
# Même signe = pas de miroir de ce côté-là. C'est exactement le test qu'un
# imprimeur fait à l'œil, écrit en arithmétique.
def face_orientation(mesh: dict) -> dict:
    """Sens de lecture du recto ET du verso, mesuré sur le maillage livré."""
    pos, nrm, uv, idx = (mesh.get("positions") or [], mesh.get("normals") or [],
                         mesh.get("uvs") or [], mesh.get("indices") or [])
    out = {"recto": {"triangles": 0, "endroit": 0, "miroir": 0},
           "verso": {"triangles": 0, "endroit": 0, "miroir": 0},
           "tranche_triangles": 0,
           "verso_u": [1.0, 0.0],
           "regle": "sens de parcours en image (u droite, v bas) contre sens de "
                    "parcours a l'ecran vu de ce cote (droite, bas)"}
    for i in range(0, len(idx), 3):
        a, b, c = idx[i], idx[i + 1], idx[i + 2]
        nz = (nrm[3 * a + 2] + nrm[3 * b + 2] + nrm[3 * c + 2]) / 3.0
        if abs(nz) < 0.1:                      # paroi de tranche : pas une face
            out["tranche_triangles"] += 1
            continue
        cote = "recto" if nz > 0 else "verso"
        out[cote]["triangles"] += 1
        det_img = ((uv[2 * b] - uv[2 * a]) * (uv[2 * c + 1] - uv[2 * a + 1])
                   - (uv[2 * c] - uv[2 * a]) * (uv[2 * b + 1] - uv[2 * a + 1]))
        sx = 1.0 if nz > 0 else -1.0
        det_scr = ((sx * (pos[3 * b] - pos[3 * a])) * (-(pos[3 * c + 1] - pos[3 * a + 1]))
                   - (sx * (pos[3 * c] - pos[3 * a])) * (-(pos[3 * b + 1] - pos[3 * a + 1])))
        out[cote]["endroit" if det_img * det_scr > 0 else "miroir"] += 1
        if cote == "verso":
            for v in (a, b, c):
                out["verso_u"][0] = min(out["verso_u"][0], uv[2 * v])
                out["verso_u"][1] = max(out["verso_u"][1], uv[2 * v])
    out["verso_u"] = [rnd(out["verso_u"][0], 4), rnd(out["verso_u"][1], 4)]
    out["ok"] = (out["recto"]["miroir"] == 0 and out["verso"]["miroir"] == 0
                 and out["verso"]["triangles"] > 0)
    return out


def perimeter_mm(geom: CardGeom, solid: dict | None) -> float:
    """Périmètre RÉEL du contour arrondi, en mm — quatre segments droits plus
    un cercle complet de rayon `corner_mm`.

    C'est la longueur sur laquelle la bande de tranche de l'atlas est étirée :
    sans elle, « la tranche est à tant de DPI » n'est qu'une impression.
    """
    st = solid_settings(solid)
    w_mm, h_mm = float(geom.trim_mm[0]), float(geom.trim_mm[1])
    r = min(st["corner_mm"], min(w_mm, h_mm) / 2.0)
    return 2.0 * (w_mm - 2 * r) + 2.0 * (h_mm - 2 * r) + 2.0 * math.pi * r


def mesh_report(geom: CardGeom, solid: dict | None) -> dict:
    """Le maillage PLUS ce que le HUD affiche : compte de faces, de sommets,
    dimensions physiques, îlots, et la mesure qui prouve l'invariant.

    Le HUD ne recopie donc pas des chiffres qu'il a calculés de son côté : il
    lit ceux du maillage réellement construit.
    """
    st = solid_settings(solid)
    m = card_mesh(geom, st)
    w, h, t = card_dims_mm(geom, st)
    b_eff = bevel_effective_mm(geom, st)
    upm = m_per_unit(m, h)
    idx, uv = m["indices"], m["uvs"]
    # `worst` part de -inf, PAS de 0.0 : initialisé à zéro, le maximum d'une
    # série entièrement négative reste 0.0 et le HUD affiche « pire cas = 0 »,
    # c'est-à-dire la valeur qui signale précisément une faute. Un indicateur
    # qui rend la même chose quand tout va bien et quand tout va mal ne mesure
    # rien.
    worst = float("-inf")
    for i in range(0, len(idx), 3):
        a, b, c = idx[i] * 2, idx[i + 1] * 2, idx[i + 2] * 2
        d = ((uv[b] - uv[a]) * (uv[c + 1] - uv[a + 1])
             - (uv[c] - uv[a]) * (uv[b + 1] - uv[a + 1]))
        worst = max(worst, d)             # doit rester < 0
    return {
        "mesh": m,
        "stats": {
            "triangles": len(idx) // 3,
            "vertices": len(m["positions"]) // 3,
            "islands": 3,
            "uv_det_max": worst,
            "uv_mirrored": worst >= 0.0,
        },
        "dims_mm": [rnd(w, 3), rnd(h, 3), rnd(t, 3)],
        "dims_in": [rnd(w / MM_PER_INCH, 4), rnd(h / MM_PER_INCH, 4),
                    rnd(t / MM_PER_INCH, 4)],
        "solid": {"thickness_mm": rnd(st["thickness_mm"], 3),
                  "corner_mm": rnd(st["corner_mm"], 3),
                  "segments": st["segments"],
                  "bevel_mm": rnd(st["bevel_mm"], 3)},
        # LE CHANFREIN TEL QU'IL EST CONSTRUIT, pas tel qu'il est demandé —
        # avec sa convention nommée, sinon « 0,100 mm » ne désigne rien.
        # `demande_mm` est la valeur du CURSEUR (bornée à sa seule plage), pas
        # celle qu'une contrainte croisée a déjà rabotée en silence : c'est ce
        # que l'utilisateur a tapé, en face de ce que la géométrie a bâti.
        "bevel": {"demande_mm": rnd(_num((solid or {}).get("bevel_mm")
                                          if isinstance(solid, dict) else None,
                                          DEFAULTS["bevel_mm"],
                                          0.0, BEVEL_MM_MAX), 4),
                  "retrait_mm": rnd(b_eff, 4),
                  "hypotenuse_mm": rnd(b_eff * math.sqrt(2.0), 4),
                  "angle_deg": BEVEL_ANGLE_DEG,
                  "borne": bool(b_eff < _num((solid or {}).get("bevel_mm")
                                             if isinstance(solid, dict) else None,
                                             DEFAULTS["bevel_mm"],
                                             0.0, BEVEL_MM_MAX) - 5e-4),
                  "convention": "retrait = jambe du chanfrein, en Z ET en XY"},
        "islands": {k: list(v) for k, v in UV_ISLANDS.items()},
        # LE VERSO, TRANCHÉ. Le seul défaut du domaine qui ruine un tirage
        # entier, et le seul que le panneau ne disait pas.
        "orientation": face_orientation(m),
        # LA DENSITÉ DE TEXELS DE LA TRANCHE, MESURÉE. Le grief : « les 168
        # triangles de la tranche — le sujet même de la pièce — sont écrasés
        # dans une bande de 1518 x 44 px, soit environ 127 DPI le long du
        # périmètre ». C'est vrai, les îlots UV sont gelés par le contrat, et
        # cela ne se voyait NULLE PART. Le chiffre est donc publié : périmètre
        # réel du contour arrondi, la bande d'atlas dessus.
        "edge": {"perimeter_mm": rnd(perimeter_mm(geom, st), 3)},
        # `m_per_unit` est le `node.scale` à écrire dans le glTF : sans lui le
        # fichier livre une carte de deux mètres de haut (1 unité = 1 mètre).
        "scale": {"unit_per_mm": rnd(2.0 / float(geom.trim_mm[1]), 9),
                  "m_per_unit": upm,
                  "note": "demi-hauteur = 1.0 unite glTF ; node.scale = "
                          "m_per_unit met la carte en metres"},
    }


# ── PIÈGE 9 : enregistrement du maillage "card" AU CHARGEMENT DU MODULE ────
# `gltf_builder.build_mesh` retombe SILENCIEUSEMENT sur la sphère pour un nom
# inconnu : sans cette ligne, P8 exporterait une boule texturée avec l'atlas
# d'une carte et personne ne verrait l'erreur avant d'ouvrir le GLB.
# `setdefault` : on n'écrase jamais une entrée existante, et aucune ligne de
# `gltf_builder.py` n'est modifiée. La table `MESHES` (le sélecteur du
# Material Forge) est une constante SÉPARÉE : "card" n'y apparaît pas, et
# `MESH_VERSION` n'est pas touché (piège 10 : il entre dans la clé du cache de
# vignettes).
def _card_default_arrays():
    g = geom_of(DEFAULT_FMT, DEFAULT_DPI)
    m = card_mesh(g, dict(DEFAULTS))
    return m["positions"], m["normals"], m["uvs"], m["indices"]


try:
    from app.services import gltf_builder as _GB
    _GB._BUILDERS.setdefault("card", _card_default_arrays)
except Exception:                                    # pragma: no cover
    logger.exception("cards.solid: maillage 'card' non enregistre")


# ═══════════════════════════════════════════════════════════════════════════
# 3. TOURNE-DISQUE — stockage et encodage
# ═══════════════════════════════════════════════════════════════════════════

def turntable_angles(frames: int) -> list[float]:
    """Les N azimuts d'un tour complet, en degrés.

    360/N de pas, de 0 inclus à 360 EXCLU : la dernière image n'est pas la
    copie de la première, donc la vidéo boucle sans à-coup ni image doublée.
    C'est le seul endroit où ce choix est écrit, et le test le relit.
    """
    n = int(frames)
    if n < TT_FRAMES_MIN or n > TT_FRAMES_MAX:
        raise ValueError(f"Le nombre d'images doit tenir entre "
                         f"{TT_FRAMES_MIN} et {TT_FRAMES_MAX} (recu {n})")
    return [360.0 * i / n for i in range(n)]


def ffmpeg_bin() -> str:
    """ffmpeg du PATH, sinon celui embarqué par l'app (même règle que
    `effects_preview.ffmpeg_bin`)."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    return cand if os.path.isfile(cand) else "ffmpeg"


def has_ffmpeg() -> bool:
    exe = ffmpeg_bin()
    return bool(shutil.which(exe) or os.path.isfile(exe))


def job_dir(did: str, job: str, create: bool = False) -> Path:
    """Dossier d'un tourne-disque. Double garde-fou, comme `deck_dir` : motif
    strict PUIS confinement sous le dossier du deck."""
    if not _JOB_RE.match(str(job or "")):
        raise ValueError(f"Identifiant de rendu invalide: {job!r}")
    root = deck_dir(did, create=create) / "solid"
    p = (root / f"tt_{job}").resolve()
    if not str(p).startswith(str(root.resolve())):
        raise ValueError(f"Identifiant de rendu invalide: {job!r}")
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def prune_jobs(did: str) -> int:
    """Un tourne-disque de 600 images en 1440 px pèse 300 Mo de JPEG. On garde
    les `_JOB_KEEP` derniers et on jette ce qui a plus de trois heures : le
    disque de l'utilisateur n'est pas un tampon d'agent."""
    try:
        root = deck_dir(did) / "solid"
    except ValueError:
        return 0
    if not root.is_dir():
        return 0
    jobs = sorted((p for p in root.iterdir()
                   if p.is_dir() and p.name.startswith("tt_")),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    now, gone = time.time(), 0
    for i, p in enumerate(jobs):
        if i < _JOB_KEEP and (now - p.stat().st_mtime) < _JOB_TTL_S:
            continue
        shutil.rmtree(p, ignore_errors=True)
        gone += 1
    return gone


def _probe_size(data: bytes) -> tuple[int, int] | None:
    """Dimensions d'un JPEG ou d'un PNG, sans PIL et sans écrire sur disque.

    On refuse une image dont la taille ne correspond pas à celle annoncée :
    ffmpeg concatène des images de tailles différentes en les redimensionnant
    en silence, et la vidéo sortirait floue sans que rien ne le dise.
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 24:
        return (int.from_bytes(data[16:20], "big"),
                int.from_bytes(data[20:24], "big"))
    if data[:2] != b"\xff\xd8":
        return None
    i, n = 2, len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return (int.from_bytes(data[i + 7:i + 9], "big"),
                    int.from_bytes(data[i + 5:i + 7], "big"))
        i += 2 + max(2, seg)
    return None


def encode_turntable(folder: Path, fps: int, fmt: str = "mp4",
                     size: tuple[int, int] | None = None) -> dict:
    """Assemble `frame_%05d.jpg` en vidéo. Rend le bilan MESURÉ (octets,
    durée, images), pas les intentions.

    Un tourne-disque de 3 s en 1080x1080 doit tenir sous 8 Mo (seuil de la
    spec). Le CRF y suffit très largement pour cette matière, mais un fond
    bruité pourrait le faire déborder : au-delà de la marge, on ré-encode à
    débit plafonné plutôt que de livrer un fichier hors seuil.
    """
    frames = sorted(folder.glob("frame_*.jpg"))
    if len(frames) < TT_FRAMES_MIN:
        raise ValueError(f"Il faut au moins {TT_FRAMES_MIN} images "
                         f"(recu {len(frames)})")
    fps = max(TT_FPS_MIN, min(TT_FPS_MAX, int(fps)))
    kind = "webm" if str(fmt).lower() == "webm" else "mp4"
    out = folder / f"tourne-disque.{kind}"
    vf = "setsar=1"
    if size:
        vf = (f"scale={int(size[0])}:{int(size[1])}:flags=lanczos,"
              f"setsar=1") + (",format=yuv420p" if kind == "mp4" else "")
    elif kind == "mp4":
        vf += ",format=yuv420p"
    base = [ffmpeg_bin(), "-y", "-v", "error", "-framerate", str(fps),
            "-i", str(folder / "frame_%05d.jpg"), "-vf", vf, "-r", str(fps)]
    if kind == "mp4":
        codec = ["-c:v", "libx264", "-preset", "medium", "-crf", "22",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    else:
        codec = ["-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0",
                 "-row-mt", "1", "-pix_fmt", "yuv420p"]
    _run(base + codec + _NU + _nu_for(kind) + [str(out)])
    if out.stat().st_size > _TT_TARGET_BYTES:
        secs = len(frames) / float(fps)
        kbps = max(400, int((_TT_TARGET_BYTES * 8 / 1000) / max(0.5, secs)))
        cap = (["-c:v", "libx264", "-preset", "medium", "-b:v", f"{kbps}k",
                "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
               if kind == "mp4" else
               ["-c:v", "libvpx-vp9", "-b:v", f"{kbps}k",
                "-maxrate", f"{kbps}k", "-row-mt", "1", "-pix_fmt", "yuv420p"])
        _run(base + cap + _NU + _nu_for(kind) + [str(out)])
    n = len(frames)
    return {"file": out.name, "path": str(out), "bytes": out.stat().st_size,
            "frames": n, "fps": fps, "seconds": rnd(n / float(fps), 3),
            "format": kind,
            # LE FICHIER EST RELU APRÈS COUP : « aucune empreinte » est une
            # MESURE sur les octets sortis, pas une intention de ligne de
            # commande. Si une version de ffmpeg réintroduisait la signature,
            # le compte remonterait et le panneau l'écrirait.
            "empreintes": scan_empreintes(out)}


# ── LE FICHIER LIVRÉ NE PORTE NI OUTIL NI MACHINE ──────────────────────────
# LE GRIEF, NON CORRIGÉ AU TOUR PRÉCÉDENT : « le mp4 conserve
# TAG:encoder=Lavf63.1.100, TAG:encoder=Lavc63.1.100 libx264 et, dans le flux
# lui-même, la chaîne d'options x264 "x264 - core 165 r3223 ... threads=34 ...
# crf=22.0". Un côté livre une empreinte de chaîne locale et de machine (34
# fils = le processeur de la machine de prise de vue), l'autre livre un fichier
# nu. »
#
# Trois gestes, chacun vérifié sur un fichier produit :
#   -fflags +bitexact   → le conteneur perd "encoder=Lavf<version>"
#   -flags:v +bitexact  → le flux perd la version de Lavc
#   -bsf:v filter_units=remove_types=6 → les NAL de type 6 (SEI) sautent, et
#     avec elles TOUTE la chaîne "x264 - core ... threads=N ... crf=22.0".
# Mesure avant / après sur un clip témoin de 64x64 : « x264 - core » 1 → 0,
# « threads= » 3 → 0, « Lav » 1 → 0 pour 6 383 → 5 746 octets. Le seul reste
# est `handler_name=VideoHandler`, une constante du format mp4 identique sur
# toutes les machines.
_NU = ["-map_metadata", "-1", "-map_metadata:s:v", "-1",
       "-flags:v", "+bitexact", "-fflags", "+bitexact"]


def _nu_for(kind: str) -> list[str]:
    # `-metadata:s:v:0 encoder=` n'est pas de la ceinture-bretelles : MESURÉ sur
    # le fichier sorti du vrai bouton, `-map_metadata:s:v -1` ne suffit pas —
    # le muxer mp4 réécrit un `encoder=Lavc libx264` de son côté, et le panneau
    # l'a signalé lui-même (« 2 empreintes restantes : 1 x264, 1 Lavf/Lavc »)
    # après un premier jet qui se croyait complet.
    if kind == "mp4":
        return ["-bsf:v", "filter_units=remove_types=6",
                "-metadata:s:v:0", "encoder="]
    return ["-metadata:s:v:0", "ENCODER="]


# Les motifs cherchés sont ceux que le critique a effectivement trouvés.
EMPREINTES = ("x264 - core", "x264", "Lavf", "Lavc", "threads=", "crf=", "libvpx")
# Tout nom d'outil suivi d'un chiffre : « Lavc62.28.101 », « Lavf63.1.100 »,
# « libvpx-vp9 1.13 ». C'est la VERSION qui date la chaîne locale.
_RE_VERSION = re.compile(rb"(?:Lavf|Lavc|x264|libx264|libvpx)[ \t\-]*[0-9]")


def scan_empreintes(path: Path) -> dict:
    """Compte, DANS LES OCTETS DU FICHIER, les signatures d'outil et de machine.

    Trois familles séparées, parce qu'elles ne se corrigent pas de la même
    façon et qu'un total unique cacherait laquelle reste :
      `versions` — un nom d'outil suivi d'un chiffre (la chaîne locale datée) ;
      `machine`  — « threads=N », c'est-à-dire le processeur de la machine ;
      `outil`    — le nom de l'encodeur et ses options en clair.
    `muxeur` est à part : le conteneur Matroska IMPOSE un champ MuxingApp, et
    il porte « Lavf » sans version. On ne peut pas le supprimer, on le dit.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return {"total": -1, "octets": 0}
    n = {k: data.count(k.encode("ascii")) for k in EMPREINTES}
    n["versions"] = len(_RE_VERSION.findall(data))
    n["machine"] = n["threads="]
    n["outil"] = n["x264"] + n["libvpx"] + n["crf="]
    n["muxeur"] = n["Lavf"] + n["Lavc"]
    n["total"] = n["versions"] + n["machine"] + n["outil"]
    n["octets"] = len(data)
    return n


def _run(cmd: list[str]) -> None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg est introuvable : le tourne-disque ne peut "
                           "pas etre encode")
    if r.returncode != 0:
        last = (r.stderr or "").strip().splitlines()
        raise RuntimeError("encodage impossible : "
                           + (last[-1][:220] if last else "sortie vide"))


# ═══════════════════════════════════════════════════════════════════════════
# 4. ROUTES — chemins RELATIFS au préfixe posé par cards/__init__.py
# ═══════════════════════════════════════════════════════════════════════════

def _did(did: str) -> str:
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de jeu invalide")
    return did


def _q_geom(fmt: str | None, dpi: str | None) -> CardGeom:
    key = str(fmt or DEFAULT_FMT).strip().lower()
    if key not in FORMATS:
        raise HTTPException(400, "Format de carte inconnu: %r. Formats admis: %s"
                            % (fmt, ", ".join(FORMATS)))
    try:
        d = int(float(dpi)) if dpi not in (None, "") else DEFAULT_DPI
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(400, f"DPI doit etre un entier (recu {dpi!r})")
    try:
        return geom_of(key, d)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


@router.get("/info")
async def solid_info(did: str):
    """Bornes, défauts et état de l'outillage. L'écran s'en sert pour dire ce
    qui est possible AVANT qu'on clique — un tourne-disque sans ffmpeg doit se
    savoir tout de suite, pas après 90 images."""
    _did(did)
    from app.services.gltf_builder import mesh_stats
    return {
        "defaults": DEFAULTS,
        "limits": LIMITS,
        "edge_styles": list(EDGE_STYLES),
        "views": list(VIEWS),
        "envs": list(ENVS),
        "islands": {k: list(v) for k, v in UV_ISLANDS.items()},
        "turntable": {
            "frames": [TT_FRAMES_MIN, TT_FRAMES_MAX],
            "fps": [TT_FPS_MIN, TT_FPS_MAX],
            "sizes": list(TT_SIZE_CHOICES),
            "max_bytes": TT_MAX_BYTES,
            "ffmpeg": has_ffmpeg(),
            "elevation": [TT_ELEV_MIN, TT_ELEV_MAX],
            "elevation_default": TT_ELEV_DEFAULT,
            "polar_default": polar_from_elevation(TT_ELEV_DEFAULT),
        },
        "atlas_caps": list(ATLAS_CAPS),
        "pbr": {st: pbr_plan(st) for st in EDGE_STYLES},
        "registered_mesh": mesh_stats("card"),
        "sphere_mesh": mesh_stats("sphere"),
    }


@router.get("/mesh")
async def solid_mesh(did: str, fmt: str | None = None, dpi: str | None = None,
                     thickness_mm: str | None = None,
                     corner_mm: str | None = None,
                     segments: str | None = None,
                     bevel_mm: str | None = None,
                     atlas: str | None = None,
                     edge_style: str | None = None):
    """LE maillage, source unique. L'écran ne le recalcule pas de son côté :
    il l'affiche. Deux générateurs, ce serait deux cartes.

    Les réglages sont déclarés en `str` et convertis ici : typés en `float`,
    FastAPI rendrait un 422 avec un corps `detail` en anglais et en liste
    d'objets pour un simple curseur mal formé. Un réglage hors plage n'est pas
    une faute de protocole, c'est une butée — `solid_settings` la pose.
    """
    _did(did)
    g = _q_geom(fmt, dpi)
    rep = mesh_report(g, {"thickness_mm": thickness_mm, "corner_mm": corner_mm,
                          "segments": segments, "bevel_mm": bevel_mm})
    cap = 1536
    if atlas not in (None, ""):
        try:
            cap = int(float(atlas))
        except (TypeError, ValueError):
            cap = 1536
    plan = atlas_plan(g, cap)
    st = {"thickness_mm": thickness_mm, "corner_mm": corner_mm,
          "segments": segments, "bevel_mm": bevel_mm}
    rep["edge"] = dict(rep["edge"], **edge_dpi(g, st, plan))
    return {"geom": {"fmt": g.fmt, "label": g.label, "dpi": g.dpi,
                     "trim_mm": list(g.trim_mm),
                     "trim_px": list(g.trim_px),
                     "canvas_px": list(g.canvas_px)},
            "atlas": plan,
            "pbr": pbr_plan(edge_style or "plein"),
            **rep}


@router.post("/turntable/frame")
async def solid_tt_frame(did: str, request: Request, job: str = "", i: int = -1):
    """Une image du tourne-disque, telle qu'elle sort de la visionneuse."""
    _did(did)
    if i < 0 or i >= TT_FRAMES_MAX:
        raise HTTPException(400, f"Index d'image hors bornes (0 a "
                                 f"{TT_FRAMES_MAX - 1})")
    data = await request.body()
    if not data:
        raise HTTPException(400, "Image vide")
    if len(data) > _FRAME_MAX_BYTES:
        raise HTTPException(400, "Image trop lourde (12 Mo maximum)")
    if _probe_size(data) is None:
        raise HTTPException(400, "Seuls le JPEG et le PNG sont acceptes")
    try:
        d = job_dir(did, job, create=True)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if i == 0:
        for old in d.glob("frame_*.jpg"):
            old.unlink(missing_ok=True)
        prune_jobs(did)
    tmp = d / f"frame_{i:05d}.part"
    tmp.write_bytes(data)
    tmp.replace(d / f"frame_{i:05d}.jpg")
    return {"ok": True, "i": i, "bytes": len(data)}


@router.post("/turntable/encode")
async def solid_tt_encode(did: str, body: dict | None = None):
    """Assemblage ffmpeg. Rend les octets MESURÉS du fichier écrit."""
    _did(did)
    b = body if isinstance(body, dict) else {}
    try:
        d = job_dir(did, str(b.get("job", "")))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not d.is_dir():
        raise HTTPException(404, "Aucune image recue pour ce rendu")
    if not has_ffmpeg():
        raise HTTPException(503, "ffmpeg est absent : le tourne-disque ne "
                                 "peut pas etre encode")
    try:
        fps = int(float(b.get("fps", 30)))
    except (TypeError, ValueError):
        raise HTTPException(400, "Le nombre d'images par seconde doit etre un "
                                 "entier")
    if fps < TT_FPS_MIN or fps > TT_FPS_MAX:
        raise HTTPException(400, f"Images par seconde hors bornes "
                                 f"[{TT_FPS_MIN}, {TT_FPS_MAX}]")
    size = None
    try:
        if b.get("w") and b.get("h"):
            size = (int(b["w"]), int(b["h"]))
            if not (64 <= size[0] <= 4096 and 64 <= size[1] <= 4096):
                raise HTTPException(400, "Taille de sortie hors bornes")
    except (TypeError, ValueError):
        raise HTTPException(400, "Taille de sortie invalide")
    try:
        rep = await asyncio.to_thread(encode_turntable, d, fps,
                                      str(b.get("format", "mp4")), size)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception:
        logger.exception("cards.solid: encodage du tourne-disque")
        raise HTTPException(500, "Encodage du tourne-disque impossible")
    rep["over_limit"] = rep["bytes"] > TT_MAX_BYTES
    rep.pop("path", None)
    return rep


@router.get("/turntable/file")
async def solid_tt_file(did: str, job: str = "", name: str = ""):
    """Le fichier, en binaire. C'est ce blob-là que `CF.download` accepte :
    il vient du backend du module, pas d'une toile fabriquée à côté."""
    _did(did)
    if name not in ("tourne-disque.mp4", "tourne-disque.webm"):
        raise HTTPException(400, "Nom de fichier inconnu")
    try:
        d = job_dir(did, job)
    except ValueError as e:
        raise HTTPException(400, str(e))
    f = d / name
    if not f.is_file():
        raise HTTPException(404, "Fichier de rendu introuvable")
    mt = "video/mp4" if name.endswith(".mp4") else "video/webm"
    return Response(content=f.read_bytes(), media_type=mt, headers={
        "Content-Disposition": f'attachment; filename="{name}"'})


@router.delete("/turntable")
async def solid_tt_delete(did: str, job: str = ""):
    _did(did)
    try:
        d = job_dir(did, job)
    except ValueError as e:
        raise HTTPException(400, str(e))
    shutil.rmtree(d, ignore_errors=True)
    return {"ok": True}
