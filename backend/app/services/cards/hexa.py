# -*- coding: utf-8 -*-
"""Card Forge — t421 : le contour des cartes hexagonales, en millimètres.

Un hexagone régulier vit dans le rectangle de coupe (`trim_mm`) ; la toile, le
fond perdu et les pixels gardent la règle de `contract.py`. Ce module ne rend
AUCUN pixel : il rend des polygones, que l'aperçu, le gabarit, la planche en
nid d'abeille et les fichiers de découpe consomment.

REPÈRES. `CardGeom.contour_mm` est dans le repère de la COUPE (coin haut-gauche
du rectangle de coupe). Toutes les fonctions `*_toile_*` rendent leurs points
dans le repère de la TOILE (coin haut-gauche de l'image rendue, fond perdu
compris) : c'est le repère où l'on dessine. Le décalage coupe -> toile vient
de `bleed_off_px` (arrondi au pixel par la règle du contrat), pas de
`bleed_mm`, pour que le polygone tombe sur les mêmes pixels que la carte.

Le miroir exact de ce fichier est le bloc CF-HEX de frontend/cardforge/js/
core.js ; `test_cards_hexa.py` les confronte à 0,001 mm près.

Sans dépendance hors `contract`. Aucun import de framework web : les refus
HTTP vivent chez les routes.
"""
from __future__ import annotations

from .contract import CardGeom, MM_PER_INCH

__all__ = ["decale", "contour_coupe_toile_mm", "contour_toile_mm",
           "contour_sur_mm", "milieux_cotes_mm"]

Point = tuple[float, float]


def decale(points: list[Point], d_mm: float) -> list[Point]:
    """Décalage PERPENDICULAIRE d'un polygone convexe : chaque côté glisse de
    `d_mm` le long de sa normale, `d_mm` > 0 vers l'extérieur, < 0 vers
    l'intérieur ; chaque sommet est l'intersection des deux côtés décalés qui
    le touchent (donc une pointe d'hexagone avance de d / cos 30°, pas de d).

    Rend une liste VIDE si le décalage inverse le polygone (vers l'intérieur
    au-delà de l'apothème)."""
    n = len(points)
    if n < 3:
        return []
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n
    droites = []                       # (point d'ancrage, direction unitaire)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / ln, dy / ln
        nx, ny = uy, -ux
        if (((a[0] + b[0]) / 2 - cx) * nx + ((a[1] + b[1]) / 2 - cy) * ny) < 0:
            nx, ny = -nx, -ny           # la normale regarde vers l'extérieur
        droites.append(((a[0] + nx * d_mm, a[1] + ny * d_mm), (ux, uy)))
    out: list[Point] = []
    for i in range(n):
        (p, u), (q, v) = droites[i - 1], droites[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-12:
            return []
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    # un côté qui change de sens = polygone retourné
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        c, e = out[i], out[(i + 1) % n]
        if (b[0] - a[0]) * (e[0] - c[0]) + (b[1] - a[1]) * (e[1] - c[1]) <= 0:
            return []
    return out


def _decoupe(poly: list[Point], w: float, h: float) -> list[Point]:
    """Sutherland-Hodgman : `poly` découpé par le rectangle [0, w] x [0, h]."""
    def coupe(pts, dedans, croise):
        res = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            a, b = dedans(prev), dedans(cur)
            if a and b:
                res.append(cur)
            elif a and not b:
                res.append(croise(prev, cur))
            elif b and not a:
                res.append(croise(prev, cur))
                res.append(cur)
        return res

    def sur_x(x0):
        return lambda p, q: (x0, p[1] + (q[1] - p[1]) * (x0 - p[0]) / (q[0] - p[0]))

    def sur_y(y0):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (y0 - p[1]) / (q[1] - p[1]), y0)

    pts = list(poly)
    for dedans, croise in (
            (lambda p: p[0] >= 0.0, sur_x(0.0)),
            (lambda p: p[0] <= w, sur_x(w)),
            (lambda p: p[1] >= 0.0, sur_y(0.0)),
            (lambda p: p[1] <= h, sur_y(h))):
        if not pts:
            break
        pts = coupe(pts, dedans, croise)
    return pts


def _verifie(g: CardGeom) -> None:
    if g.forme != "hex":
        raise ValueError(
            "Le format %r n'est pas un hexagone : pas de contour hexagonal"
            % g.fmt)


def _origine_toile_mm(g: CardGeom) -> Point:
    """Coin haut-gauche de la coupe dans le repère de la toile, en mm."""
    k = MM_PER_INCH / g.dpi
    return (g.bleed_off_px[0] * k, g.bleed_off_px[1] * k)


def _vers_toile(g: CardGeom, pts: list[Point]) -> list[Point]:
    ox, oy = _origine_toile_mm(g)
    return [(x + ox, y + oy) for x, y in pts]


def contour_coupe_toile_mm(g: CardGeom) -> list[Point]:
    """Le trait de coupe, repère toile : les six sommets de `g.contour_mm`."""
    _verifie(g)
    return _vers_toile(g, g.contour_mm)


def contour_toile_mm(g: CardGeom) -> list[Point]:
    """Le contour du FOND PERDU, repère toile : la coupe décalée vers
    l'extérieur de `bleed_mm`, TRONQUÉE à la toile. Aux deux pointes le
    décalage dépasse la toile de 0,155 x fond perdu (0,46 mm pour 3 mm) : la
    troncature la rogne et laisse plus de 2,5 mm de fond perdu à la pointe.
    Le polygone passe alors de 6 à 8 sommets."""
    _verifie(g)
    k = MM_PER_INCH / g.dpi
    w, h = g.canvas_px[0] * k, g.canvas_px[1] * k
    # La toile est arrondie au pixel : sans fond perdu, un sommet de la coupe
    # peut la dépasser d'un demi-pixel. Ce dépassement-là est du bruit de
    # quantification, pas du fond perdu : on le ramène au bord au lieu de
    # fabriquer un sommet de plus. Celui des pointes (0,46 mm pour 3 mm) est
    # bien plus grand et reste tronqué.
    tol = k / 2
    pts = [(min(max(x, 0.0), w) if (-tol <= x <= w + tol) else x,
            min(max(y, 0.0), h) if (-tol <= y <= h + tol) else y)
           for x, y in _vers_toile(g, decale(g.contour_mm, g.bleed_mm))]
    return _decoupe(pts, w, h)


def contour_sur_mm(g: CardGeom) -> list[Point]:
    """La ZONE SÛRE, repère toile : la coupe décalée vers l'intérieur de
    `safe_mm` (liste vide si la zone sûre dépasse l'apothème)."""
    _verifie(g)
    return _vers_toile(g, decale(g.contour_mm, -g.safe_mm))


def milieux_cotes_mm(g: CardGeom) -> list[Point]:
    """Le milieu de chacun des six côtés de la COUPE, repère toile, dans
    l'ordre des côtés de `contour_mm` (côté i = sommet i -> sommet i + 1).
    C'est là que l'utilisateur place les symboles de liens."""
    pts = contour_coupe_toile_mm(g)
    return [((pts[i][0] + pts[(i + 1) % 6][0]) / 2,
             (pts[i][1] + pts[(i + 1) % 6][1]) / 2) for i in range(6)]
