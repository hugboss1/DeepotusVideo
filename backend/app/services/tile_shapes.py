# -*- coding: utf-8 -*-
"""Formes de tuile : losange isométrique 2:1 et hexagone à sommet plat (plan 2026-09-03-plan-tuiles, P5 — tâche
t115).

UNE SEULE IDÉE : la texture d'une tuile de forme n'est pas la matière recadrée, c'est la matière envoyée sur le
RÉSEAU de la forme par une transformation affine. Les vecteurs du réseau deviennent des multiples entiers de la
taille de la matière : la texture est périodique sous le réseau PAR CONSTRUCTION, donc deux tuiles voisines montrent,
de part et d'autre de leur bord commun, la même texture continue (banc : les vraies tuiles RGBA posées sur le réseau
reproduisent le champ à 0 écart près).

CE QUE LE PLAN (03/09) NE MESURAIT PAS, MESURÉ LE 06/10 SUR SON PROPRE CODE :
  * sa mesure de raccord comparait le champ à LUI-MÊME décalé d'un vecteur du réseau : vraie par construction,
    quelle que soit la matière — un bruit BRUT, non raccordable, y rendait 0.0. Le réseau ne crée aucune couture ;
    la seule possible est celle de la MATIÈRE avec elle-même (`raccord_forme`), et c'est elle qu'on rend.
  * son masque (polygone PIL jusqu'à w-1, h-1) laissait 80 px de TROUS par losange 128 x 64 posé sur le réseau —
    autant de pixels de fond entre les tuiles dans le moteur — et ses hexagones se chevauchaient. Le masque est ici
    un test du CENTRE de chaque pixel en arithmétique ENTIÈRE, avec des arêtes « possédées » (une de chaque paire
    opposée) : posé sur le réseau, il couvre chaque pixel exactement une fois (banc, plusieurs tailles).
  * `3 * w // 4` tronquait le vecteur hexagonal pour une largeur non multiple de 4 (R = 55 → 82 au lieu de 82,5) :
    la largeur est ici toujours un multiple de 4.

PIL pur : `Image.transform(…, Image.AFFINE, …)` sur une matière pavée 5 x 5 (les coordonnées de la boîte englobante
débordent d'un demi-motif de chaque côté ; 5 x 5 couvre largement, pour 25 collages).
"""
from __future__ import annotations

import math

from PIL import Image

FORMES = ("carre", "iso", "hex")
#: taille du pavage de la matière source, en motifs
PAVAGE = 5


def dims_iso(cote: int = 64) -> tuple[int, int]:
    """Losange 2:1 — le rapport des .tres réels de Godot (128 x 64). Hauteur paire : le demi-pas h/2 reste entier."""
    h = max(8, int(cote) - (int(cote) % 2))
    return 2 * h, h


def dims_hex(rayon: int = 32) -> tuple[int, int]:
    """Hexagone à SOMMET PLAT : largeur 2R avec R PAIR (largeur multiple de 4, pour que le pas horizontal du réseau
    3w/4 soit entier), hauteur racine(3) x R arrondie au PAIR (pour que le demi-décalage h/2 le soit aussi)."""
    r = max(8, int(rayon))
    r += r % 2
    return 2 * r, 2 * round(math.sqrt(3) * r / 2)


def DEC_ISO(largeur: int, hauteur: int) -> dict[str, tuple[int, int]]:
    """Décalages de voisinage du réseau losange, en pixels ENTIERS."""
    w, h = largeur // 2, hauteur // 2
    return {"NE": (w, -h), "SE": (w, h), "SW": (-w, h), "NW": (-w, -h)}


def DEC_HEX(largeur: int, hauteur: int) -> dict[str, tuple[int, int]]:
    """Décalages du réseau hexagonal à sommet plat, en pixels ENTIERS (largeur multiple de 4)."""
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


def _sommets_x2(forme: str, w: int, h: int):
    """Sommets de la forme en DEMI-pixels (coordonnées x 2, toutes entières), dans le sens horaire de l'écran, et
    pour chaque arête (sommet i → i+1) si la tuile la POSSÈDE. Une arête de chaque paire opposée est possédée : un
    centre de pixel posé exactement sur un bord commun appartient à une seule des deux tuiles."""
    if forme == "iso":
        # haut → droite (NE) → bas (SE) → gauche (SW) → haut (NW) ; possédées : NE et NW
        return [(w, 0), (2 * w, h), (w, 2 * h), (0, h)], (True, False, False, True)
    if forme == "hex":
        # haut-gauche → haut-droite (N) → droite (NE) → bas-droite (SE) → bas-gauche (S) → gauche (SW) → (NW)
        return ([(w // 2, 0), (3 * w // 2, 0), (2 * w, h), (3 * w // 2, 2 * h), (w // 2, 2 * h), (0, h)],
                (True, True, False, False, False, True))
    raise ValueError(f"forme sans reseau propre: {forme!r}")


def masque_forme(forme: str, cote: int = 64) -> Image.Image:
    """Masque « L » BINAIRE de la forme : 255 si le CENTRE du pixel est dedans, 0 sinon.

    Test entier : le centre (x + ½, y + ½) devient (2x + 1, 2y + 1) en demi-pixels ; pour chaque arête orientée
    (a → b), le produit vectoriel (b − a) ∧ (p − a) est > 0 à l'intérieur (sens horaire, y vers le bas). Nul : le
    centre est SUR l'arête, et ne compte que si la tuile la possède."""
    w, h = dims(forme, cote)
    im = Image.new("L", (w, h), 0)
    if forme == "carre":
        im.paste(255, (0, 0, w, h))
        return im
    sommets, possede = _sommets_x2(forme, w, h)
    aretes = [(sommets[i], sommets[(i + 1) % len(sommets)], possede[i]) for i in range(len(sommets))]
    px = im.load()
    for y in range(h):
        py = 2 * y + 1
        for x in range(w):
            pxx = 2 * x + 1
            for (ax, ay), (bx, by), a_moi in aretes:
                c = (bx - ax) * (py - ay) - (by - ay) * (pxx - ax)
                if c < 0 or (c == 0 and not a_moi):
                    break
            else:
                px[x, y] = 255
    return im


def matiere_carree(mat: Image.Image, forme: str, cote: int = 64) -> Image.Image:
    """La matière ramenée au carré de la LARGEUR de la tuile : le pavage et la transformation lisent un seul côté."""
    w, _h = dims(forme, cote)
    return mat.convert("RGB").resize((w, w), Image.LANCZOS)


def _pave(mat: Image.Image, k: int = PAVAGE) -> Image.Image:
    s = mat.width
    g = Image.new("RGB", (k * s, k * s))
    for gy in range(k):
        for gx in range(k):
            g.paste(mat, (gx * s, gy * s))
    return g


def _coeffs(forme: str, s: int, w: int, h: int, ox: int, oy: int):
    """Coefficients AFFINE de PIL : le pixel (x, y) de la SORTIE lit la source en (a·x + b·y + c, d·x + e·y + f).
    `ox, oy` = position, dans la sortie, du coin haut-gauche de la tuile centrale.

    Iso : le carré unité (u, v) est envoyé sur le losange par (x, y) = ((u+v)·w/2, (v−u)·h/2 + h/2), d'où
    u = x/w − y/h + ½ et v = x/w + y/h − ½.
    Hex : le réseau est engendré par (3R/2, h/2) et (0, h) ; relativement au centre, u = (x − R)/(3R/2) et
    v = (y − h/2)/h − u/2."""
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


def texture_forme(mat: Image.Image, forme: str, cote: int = 64, taille=None, origine=(0, 0)) -> Image.Image:
    """La matière envoyée sur le réseau de la forme, en RGB (le CHAMP continu, sans découpe)."""
    w, h = dims(forme, cote)
    m = matiere_carree(mat, forme, cote)
    return _pave(m).transform(taille or (w, h), Image.AFFINE,
                              _coeffs(forme, m.width, w, h, origine[0], origine[1]), Image.NEAREST)


def tuile_forme(mat: Image.Image, forme: str, cote: int = 64) -> Image.Image:
    """La tuile RGBA : texture du réseau, découpée par le masque de forme (hors forme = transparent)."""
    tex = texture_forme(mat, forme, cote).convert("RGBA")
    tex.putalpha(masque_forme(forme, cote))
    return tex


def raccord_forme(mat: Image.Image, forme: str, cote: int = 64) -> float:
    """Raccord 0-100 d'une tuile de forme : celui de la MATIÈRE avec elle-même (droite contre gauche, bas contre
    haut), à la taille où le réseau la lit. Le réseau, périodique par construction, n'en ajoute aucun : une matière
    miroir rend 0.0, un bruit brut son propre raccord — le même chiffre qu'un jeu carré tiré de cette matière."""
    from app.services import tile_metrics as TM

    m = matiere_carree(mat, forme, cote)
    return max(TM.seam_pair(m, m, "E"), TM.seam_pair(m, m, "S"))
