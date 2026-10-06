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
  * il échantillonnait par `Image.transform(…, AFFINE, NEAREST)`, que Pillow calcule en VIRGULE FIXE par additions
    successives : l'erreur s'accumule le long de la ligne, et la tuile (origine 0) divergeait du champ (origine
    décalée) — 1 632 pixels sur un hexagone de 112 x 96, pire en grandissant ; seul le losange, aux coefficients
    entiers, y échappait. L'échantillonnage est ici EXACT (`texture_forme`) : coefficients rationnels, numérateurs
    entiers, plancher par division entière, modulo la matière. La texture d'un point ne dépend que du point.
"""
from __future__ import annotations

import math
from fractions import Fraction

from PIL import Image

FORMES = ("carre", "iso", "hex")


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
    """La matière ramenée au carré de la LARGEUR de la tuile : l'échantillonnage lit un seul côté."""
    w, _h = dims(forme, cote)
    return mat.convert("RGB").resize((w, w), Image.LANCZOS)


def _coeffs(forme: str, s: int, w: int, h: int):
    """Coefficients EXACTS (fractions) : le point (x, y) de la tuile, coin haut-gauche à l'origine, lit la matière
    de côté s en (A·x + B·y + C, D·x + E·y + F), modulo s.

    Iso : le carré unité (u, v) est envoyé sur le losange par (x, y) = ((u+v)·w/2, (v−u)·h/2 + h/2), d'où
    u = x/w − y/h + ½ et v = x/w + y/h − ½.
    Hex : le réseau est engendré par (3R/2, h/2) et (0, h) ; relativement au centre, u = (x − R)/(3R/2) et
    v = (y − h/2)/h − u/2.
    Chaque vecteur du réseau déplace (u, v) d'un multiple entier de s : banc des tuiles posées."""
    S = Fraction(s)
    if forme == "iso":
        return S / w, -S / h, S / 2, S / w, S / h, -S / 2
    if forme == "hex":
        r = Fraction(w, 2)
        return 2 * S / (3 * r), Fraction(0), -2 * S / 3, -S / (3 * r), S / h, -S / 6
    raise ValueError(f"forme sans reseau propre: {forme!r}")


def texture_forme(mat: Image.Image, forme: str, cote: int = 64, taille=None, origine=(0, 0)) -> Image.Image:
    """La matière envoyée sur le réseau de la forme, en RGB (le CHAMP continu, sans découpe). `origine` = position,
    dans la sortie, du coin haut-gauche de la tuile de référence.

    Échantillonnage EXACT au centre de chaque pixel : u·2Q et v·2Q sont des ENTIERS (Q = dénominateur commun des
    coefficients), le pixel source est leur plancher par division entière, modulo la matière — ni flottant, ni
    virgule fixe, ni pavage. Coût mesuré : tuile hexagonale de 1024 x 886 px, masque compris, 2,2 s."""
    w, h = dims(forme, cote)
    m = matiere_carree(mat, forme, cote)
    s = m.width
    A, B, C, D, E, F = _coeffs(forme, s, w, h)
    Q = math.lcm(*(c.denominator for c in (A, B, C, D, E, F)))
    a, b, c2 = int(A * Q), int(B * Q), int(2 * C * Q)
    d, e, f2 = int(D * Q), int(E * Q), int(2 * F * Q)
    q2 = 2 * Q
    W, H = taille or (w, h)
    ox, oy = origine
    src = m.tobytes()
    out = bytearray(W * H * 3)
    xs = [2 * (x - ox) + 1 for x in range(W)]          # 2 x (x − ox + ½) : le centre du pixel, en demi-pixels
    ua = [a * xx for xx in xs]
    va = [d * xx for xx in xs]
    j = 0
    for y in range(H):
        yy = 2 * (y - oy) + 1
        ub, vb = b * yy + c2, e * yy + f2
        for x in range(W):
            k = (((va[x] + vb) // q2) % s * s + ((ua[x] + ub) // q2) % s) * 3
            out[j:j + 3] = src[k:k + 3]
            j += 3
    return Image.frombytes("RGB", (W, H), bytes(out))


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
