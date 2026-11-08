# -*- coding: utf-8 -*-
"""Card Forge — plateau hexagonal : géométrie de la grille de découpe.

Une image de plateau est découpée en tuiles hexagonales jointives. Ce module
ne fait que la géométrie (mm, pixels source) ; aucun format n'est recopié ici :
la mesure `p` (côté plat à côté plat) et l'orientation viennent de
`contract.FORMATS` / `contract.geom`. Miroir JS, mêmes formules :
`frontend/shared/dz-decoupe-hex-logique.js`.

Pointe en haut : pas horizontal `p`, pas vertical `0,75·h` (h = 2p/√3), les
rangées paires sont décalées de +p/2. Côté plat en haut : la transposée (les
colonnes paires sont décalées de +p/2 vers le bas, pas horizontal `0,75·h`).
Rang et colonne sont 1-based.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .contract import geom, is_hex
from .depuis_images import IMAGES_MAX

__all__ = ["COTE_MAX", "TUILES_MAX", "Grille", "grille", "cadrage_couvrant",
           "ppp_effectif"]

COTE_MAX = 30                 # colonnes ou rangées, au plus
TUILES_MAX = IMAGES_MAX       # = 500, le plafond d'un deck depuis des images


@dataclass(frozen=True)
class Grille:
    fmt: str
    colonnes: int
    rangees: int
    bleed_mm: float
    # (rang, colonne, x, y), 1-based, rangée par rangée
    centres_mm: tuple[tuple[int, int, float, float], ...]
    # étendue des contours de coupe + 2 × fond perdu
    largeur_mm: float
    hauteur_mm: float


def _entier(valeur, nom: str) -> int:
    if isinstance(valeur, bool) or int(valeur) != valeur:
        raise ValueError(f"{nom} doit être un entier (reçu {valeur!r})")
    return int(valeur)


def grille(fmt: str, colonnes: int, rangees: int,
           bleed_mm: float | None = None) -> Grille:
    """Grille hexagonale `colonnes` × `rangees` du format `fmt`.

    `bleed_mm=None` : fond perdu natif du format. Lève `ValueError` sur un
    format non hexagonal, un nombre de colonnes/rangées hors 1..COTE_MAX ou
    plus de TUILES_MAX tuiles, un fond perdu hors bornes."""
    cle = str(fmt or "").strip().lower()
    if not is_hex(cle):
        raise ValueError(f"Format non hexagonal : {fmt!r}")
    try:
        nc, nr = _entier(colonnes, "colonnes"), _entier(rangees, "rangées")
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError(str(e))
    if not (1 <= nc <= COTE_MAX and 1 <= nr <= COTE_MAX):
        raise ValueError(
            f"colonnes et rangées doivent tenir entre 1 et {COTE_MAX}")
    if nc * nr > TUILES_MAX:
        raise ValueError(f"{nc * nr} tuiles : {TUILES_MAX} au plus")

    g = geom(cle, bleed_mm=bleed_mm)      # valide aussi le fond perdu
    b = g.bleed_mm
    p = min(g.trim_mm)
    h = 2.0 * p / math.sqrt(3.0)
    pointe = g.orientation == "pointe"
    pas = 0.75 * h

    centres = []
    for r in range(1, nr + 1):
        for c in range(1, nc + 1):
            if pointe:
                x = b + p / 2 + (c - 1) * p + (p / 2 if r % 2 == 0 else 0.0)
                y = b + h / 2 + (r - 1) * pas
            else:
                x = b + h / 2 + (c - 1) * pas
                y = b + p / 2 + (r - 1) * p + (p / 2 if c % 2 == 0 else 0.0)
            centres.append((r, c, x, y))

    if pointe:
        largeur = nc * p + (p / 2 if nr > 1 else 0.0) + 2 * b
        hauteur = h + (nr - 1) * pas + 2 * b
    else:
        largeur = h + (nc - 1) * pas + 2 * b
        hauteur = nr * p + (p / 2 if nc > 1 else 0.0) + 2 * b
    return Grille(cle, nc, nr, b, tuple(centres), largeur, hauteur)


def cadrage_couvrant(src_w: int, src_h: int, ext_w: float, ext_h: float,
                     zoom: float = 1.0, x: float = 0.5,
                     y: float = 0.5) -> tuple[float, float, float, float]:
    """Rectangle (gauche, haut, largeur, hauteur) en pixels source, du rapport
    `ext_w/ext_h`. zoom=1 : le plus grand rectangle de ce rapport contenu dans
    l'image ; zoom>1 le divise ; `x`, `y` ∈ [0, 1] = position dans la course
    libre. zoom<1 est ramené à 1, x et y sont bornés."""
    rapport = ext_w / ext_h
    if src_w / src_h > rapport:
        w0, h0 = src_h * rapport, float(src_h)
    else:
        w0, h0 = float(src_w), src_w / rapport
    z = max(1.0, float(zoom))
    w, h = w0 / z, h0 / z
    fx = min(1.0, max(0.0, float(x)))
    fy = min(1.0, max(0.0, float(y)))
    return (fx * (src_w - w), fy * (src_h - h), w, h)


def ppp_effectif(rect_w_px: float, largeur_mm: float) -> float:
    """Points par pouce réels : pixels source du cadrage / largeur imprimée."""
    return rect_w_px / (largeur_mm / 25.4)
