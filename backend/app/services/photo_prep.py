# -*- coding: utf-8 -*-
"""Material Forge — préparer une PHOTO avant la dérivation (R10c P1).

Deux gestes, tous deux en **PIL pur** (le runtime embarqué n'a pas numpy) :

  `delight`    retire le DÉGRADÉ D'ÉCLAIRAGE cuit dans la photo. L'éclairage
               est estimé par un flou gaussien CYCLIQUE très large sur la
               luminance (`pbr_service.cyclic`), puis divisé — et la division
               se fait en domaine LOGARITHMIQUE, où elle devient une
               soustraction : deux `Image.point` et un `ImageChops.add`, soit
               trois passes en C au lieu d'une boucle Python sur 4 M pixels.
               Le résultat est NORMALISÉ : le gain vaut exactement 1 là où
               l'éclairage estimé égale sa propre moyenne, donc l'image ne
               s'assombrit ni ne s'éclaircit globalement.

  `straighten` redresse une surface photographiée de biais : quatre coins
               cliqués -> `Image.transform(..., Image.PERSPECTIVE, coeffs)`,
               les huit coefficients résolus par une élimination de Gauss 8x8
               à pivot partiel, en stdlib. (Écrit en T2 de ce plan.)

POURQUOI CE MODULE EXISTE — LE DÉFAUT, MESURÉ. `pbr_service._roughness` a déjà
corrigé un défaut de la même famille : la rugosité valait `1 - luminance`,
donc recopiait l'éclairage cuit dans la photo (corrélation -0,76 à -0,99 avec
la luminance de la base color, médiane -0,90). Le micro-contraste l'a réparé
POUR LA RUGOSITÉ. La BASE COLOR, elle, porte toujours l'ombre : elle part
telle quelle dans le moteur, qui la ré-éclaire — l'ombre est donc comptée deux
fois, et la matière s'effondre dès qu'on change d'ambiance. `lowfreq_sd` est
la mesure qui le dit : l'écart-type de la luminance BASSE FRÉQUENCE, en
niveaux 0-255. C'est ce chiffre-là que l'écran affiche avant et après, et
c'est lui que le banc épingle.

RÉFÉRENCE relue le 03/09/2026 (R10c) : Substance 3D Sampler expose « Delight
(AI powered) » sans aucun paramètre, et sa passe « Image to Material »
l'inclut. Nous n'avons ni GPU ni modèle : l'estimation basse fréquence est la
version honnête et BORNÉE du même geste — elle ne devine rien, elle retire ce
qui varie lentement, et elle se mesure.

CONTRAT PILLOW, prouvé au banc et jamais supposé :
  * `ImageChops.add(a, b, scale, offset)` vaut `(a + b) / scale + offset`,
    écrêté à 0-255 ;
  * `Image.transform(size, Image.PERSPECTIVE, (a..h))` lit, pour le pixel de
    SORTIE (X, Y), la source en
    `((aX + bY + c) / (gX + hY + 1), (dX + eY + f) / (gX + hY + 1))` — les
    coefficients vont donc de la DESTINATION vers la SOURCE.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageFilter

from app.services import pbr_service as PBR

__all__ = ["LOG_FLOOR", "LOG_LUT", "EXP_LUT", "clamp8",
           "DELIGHT_RADIUS_FRAC", "DELIGHT_STRENGTH",
           "lowfreq", "lowfreq_sd", "delight",
           "order_quad", "perspective_coeffs", "straighten"]

clamp8 = PBR.clamp8

# Plancher du logarithme, repris de `pbr_service._LOG_FLOOR` : sans lui,
# log(0) = -inf. 6/255 place le plancher deux niveaux au-dessus du noir JPEG
# typique, et donne une dynamique de 42:1 sur les 256 pas de la LUT.
LOG_FLOOR = 6.0
_K = -math.log(LOG_FLOOR / 255.0)          # ~3,749

# LOG_LUT : niveau 8 bits -> logarithme normalisé 0-255 (LOG_FLOOR -> 0,
# 255 -> 255). EXP_LUT est son inverse exact, à la quantification près (le banc
# mesure l'écart : 4 niveaux au pire, tout en haut de l'échelle, là où un pas
# de log couvre ~3,8 niveaux linéaires).
LOG_LUT = [clamp8(255.0 * (math.log(max(float(v), LOG_FLOOR) / 255.0) + _K) / _K)
           for v in range(256)]
EXP_LUT = [clamp8(255.0 * math.exp((u / 255.0) * _K - _K)) for u in range(256)]

# Rayon du flou d'estimation, en FRACTION du plus petit côté. 1/8 : à 2048 px
# cela fait sigma = 256 px. Plus petit, le flou commence à suivre le motif et
# le delighting mange le contraste de la matière ; plus grand, il ne suit plus
# la vignette d'un objectif grand-angle. C'est un réglage, borné, publié.
DELIGHT_RADIUS_FRAC = 0.125
DELIGHT_RADIUS_RANGE = (0.02, 0.40)
DELIGHT_STRENGTH = 1.0


def _f(raw, defaut: float, lo: float, hi: float) -> float:
    """Un nombre borné. Rien ne lève : l'entrée vient du réseau (doctrine
    `material_store` règle 2 — jamais de 500 sur un corps mal formé)."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return defaut
    if v != v or v in (float("inf"), float("-inf")):
        return defaut
    return lo if v < lo else hi if v > hi else v


def lowfreq(img: Image.Image,
            radius_frac: float = DELIGHT_RADIUS_FRAC) -> Image.Image:
    """L'ÉCLAIRAGE estimé : la luminance floutée CYCLIQUEMENT, très large.

    Cyclique et pas fermé : un flou à bord fermé invente une valeur hors cadre
    et pose un liseré tout autour de l'estimation — donc un liseré INVERSE sur
    l'image délightée, exactement au bord que `make_seamless` va ensuite
    recoller. Le banc le prouve par la seule propriété qui distingue les deux :
    sur le tore, délighter et rouler commutent."""
    lum = PBR.luminance(img.convert("RGB"))
    r = max(2.0, _f(radius_frac, DELIGHT_RADIUS_FRAC, *DELIGHT_RADIUS_RANGE)
            * min(lum.size))
    return PBR.cyclic(lum, ImageFilter.GaussianBlur(r), r * 3.0 + 1.0)


def lowfreq_sd(img: Image.Image,
               radius_frac: float = DELIGHT_RADIUS_FRAC) -> float:
    """Écart-type de la luminance BASSE FRÉQUENCE, en niveaux 0-255.

    LA mesure du delighting : elle chiffre le dégradé d'éclairage et rien
    d'autre (le grain est parti dans le flou). Calculée par histogramme —
    aucune boucle par pixel, aucun numpy — comme `pbr_service.stats`."""
    h = lowfreq(img, radius_frac).histogram()
    n = sum(h) or 1
    m = sum(i * c for i, c in enumerate(h)) / n
    var = sum((i - m) ** 2 * c for i, c in enumerate(h)) / n
    return round(math.sqrt(var), 3)


def delight(img: Image.Image, strength=DELIGHT_STRENGTH,
            radius_frac: float = DELIGHT_RADIUS_FRAC) -> Image.Image:
    """Retire le dégradé d'éclairage. Rend une image RGB, toujours.

    Le calcul, en une ligne : `sortie = source x moyenne(E) / E`, avec `E`
    l'éclairage estimé. En logarithme cela devient
    `log(sortie) = log(source) + (moyenne(log E) - log E)`, soit UNE carte
    d'écart signée (centrée sur 128) ajoutée aux trois canaux — la teinte ne
    bouge donc pas, seul le niveau. `strength` interpole entre 0 (rien) et 1
    (division pleine).
    """
    rgb = img.convert("RGB")
    k = _f(strength, DELIGHT_STRENGTH, 0.0, 1.0)
    if k <= 0.0:
        return rgb
    lg = lowfreq(rgb, radius_frac).point(LOG_LUT)
    h = lg.histogram()
    n = sum(h) or 1
    pivot = sum(i * c for i, c in enumerate(h)) / n
    # écart d'éclairage SIGNÉ, centré sur 128 : au-dessus du pivot on assombrit,
    # en dessous on éclaircit, et le gain vaut exactement 1 AU pivot — c'est ce
    # qui rend la division « normalisée » et empêche l'image de dériver.
    ecart = lg.point([clamp8(128.0 - k * (v - pivot)) for v in range(256)])
    return Image.merge("RGB", tuple(
        ImageChops.add(canal.point(LOG_LUT), ecart, 1.0, -128).point(EXP_LUT)
        for canal in rgb.split()))


# ── redressement de perspective ─────────────────────────────────────────────
#
# QUATRE COINS, PAS UN ANGLE. Une photo de mur prise de biais n'est pas une
# rotation : c'est une homographie, et aucun réglage à un paramètre ne la
# défait. Les quatre coins cliqués sur la photo suffisent à la déterminer
# entièrement — huit inconnues, huit équations.
#
# LE PIÈGE DE PILLOW, ET IL EST SILENCIEUX. `Image.transform(...,
# Image.PERSPECTIVE, coeffs)` va de la DESTINATION vers la SOURCE : pour le
# pixel de sortie (X, Y) il lit la source en ((aX+bY+c)/(gX+hY+1),
# (dX+eY+f)/(gX+hY+1)). Résoudre « source -> destination », le sens naturel
# quand on pense « je redresse ma photo », donne une image retournée sur
# elle-même SANS AUCUNE ERREUR — juste une bouillie plausible. Le système est
# donc monté avec les coins de DESTINATION en entrée, et le banc l'épingle en
# réappliquant la formule à la main.

_EPS = 1e-12


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Résout a·x = b par élimination de Gauss AVEC PIVOT PARTIEL. stdlib pur.

    Le pivot partiel n'est pas un raffinement : sans lui, un quadrilatère dont
    un côté est vertical met un zéro sur la diagonale et la division explose.
    """
    n = len(b)
    m = [list(ligne) + [b[i]] for i, ligne in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < _EPS:
            raise ValueError(
                "redressement impossible : les quatre coins sont alignés ou "
                "confondus — le système n'a pas de solution unique")
        m[col], m[piv] = m[piv], m[col]
        inv = 1.0 / m[col][col]
        for j in range(col, n + 1):
            m[col][j] *= inv
        for r in range(n):
            if r == col:
                continue
            f = m[r][col]
            if f:
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


def perspective_coeffs(src, dst) -> tuple:
    """Les huit coefficients attendus par `Image.PERSPECTIVE`.

    `src` = les quatre coins dans l'image SOURCE, `dst` = les quatre coins
    correspondants dans l'image de SORTIE, tous deux dans le MÊME ordre.
    Pour chaque paire ((X, Y) sortie -> (x, y) source), la formule de Pillow
    donne deux équations linéaires en (a…h) :

        x·(gX + hY + 1) = aX + bY + c
        y·(gX + hY + 1) = dX + eY + f
    """
    lignes, second = [], []
    for (X, Y), (x, y) in zip(dst, src):
        lignes.append([X, Y, 1.0, 0.0, 0.0, 0.0, -X * x, -Y * x])
        second.append(x)
        lignes.append([0.0, 0.0, 0.0, X, Y, 1.0, -X * y, -Y * y])
        second.append(y)
    if len(second) != 8:
        raise ValueError("redressement : quatre coins sont attendus de chaque "
                         f"côté (reçu {len(second) // 2})")
    return tuple(_solve(lignes, second))


def _aire(pts) -> float:
    """Aire du quadrilatère par le lacet de Gauss, toujours positive."""
    s = 0.0
    for i in range(4):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 4]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def order_quad(quad) -> list[tuple[float, float]]:
    """Les quatre coins remis dans l'ordre haut-gauche, haut-droit, bas-droit,
    bas-gauche — quel que soit l'ordre des clics.

    POURQUOI CE TRI EXISTE. Les coins arrivent d'un clic dans un canevas :
    rien ne garantit ni le sens ni le point de départ. Appariés dans le
    désordre, ils produisent une image RETOURNÉE, sans erreur et sans indice.
    On trie donc par angle autour du barycentre (avec y vers le bas, l'ordre
    croissant des angles est le sens horaire à l'écran), puis on fait tourner
    la liste pour commencer par le coin le plus haut à gauche.
    """
    pts = []
    for p in (quad or []):
        try:
            pts.append((float(p[0]), float(p[1])))
        except (TypeError, ValueError, IndexError):
            raise ValueError("redressement : chaque coin est une paire de "
                             "nombres [x, y]")
    if len(pts) != 4:
        raise ValueError(f"redressement : quatre coins sont attendus "
                         f"(reçu {len(pts)})")
    for i in range(4):
        for j in range(i + 1, 4):
            if math.dist(pts[i], pts[j]) < 1.0:
                raise ValueError("redressement : deux coins sont confondus "
                                 f"({pts[i]} et {pts[j]}) — cliquez quatre "
                                 "points distincts")
    cx = sum(p[0] for p in pts) / 4.0
    cy = sum(p[1] for p in pts) / 4.0
    pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    largeur = max(p[0] for p in pts) - min(p[0] for p in pts)
    hauteur = max(p[1] for p in pts) - min(p[1] for p in pts)
    if _aire(pts) < 0.05 * max(1.0, largeur * hauteur):
        raise ValueError("redressement : les quatre coins sont alignés ou "
                         "presque — la surface cliquée n'a pas d'aire")
    debut = min(range(4), key=lambda i: (pts[i][0] - cx) + (pts[i][1] - cy))
    return pts[debut:] + pts[:debut]


def straighten(img: Image.Image, quad, side: int,
               resample=Image.BICUBIC) -> Image.Image:
    """La surface délimitée par `quad` dans `img`, redressée en un carré de
    `side` px.

    CARRÉ, et c'est le contrat du dépôt, pas une facilité : une matière du
    Material Forge est carrée de bout en bout (`_mat_square` recadre déjà au
    centre, `RESOLUTIONS` ne liste que des carrés, le pavage suppose un
    rapport 1:1). Rendre ici un rectangle ferait entrer une exception que huit
    autres fonctions devraient porter.
    """
    coins = order_quad(quad)
    n = max(8, int(side))
    dst = [(0.0, 0.0), (n - 1.0, 0.0), (n - 1.0, n - 1.0), (0.0, n - 1.0)]
    return img.convert("RGB").transform(
        (n, n), Image.PERSPECTIVE, perspective_coeffs(coins, dst), resample)
