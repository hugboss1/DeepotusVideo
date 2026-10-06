# -*- coding: utf-8 -*-
"""Générateurs paramétriques de matières, locaux et hors ligne (R10c D1).

CE QUE CE MODULE VEND, ET POURQUOI IL EXISTE. Substance est payant et lourd ;
un générateur de briques n'a besoin ni de l'un ni de l'autre. Dix motifs
réglables en direct, gratuits, sans clé, sans réseau — et SEAMLESS PAR
CONSTRUCTION, pas par correction a posteriori.

« PAR CONSTRUCTION » VEUT DIRE QUELQUE CHOSE DE PRÉCIS. `pixel_ops.make_seamless`
recoud une image après coup : elle mélange les bords, ce qui marche et ce qui
laisse une trace. Ici, rien à recoudre : tout motif est tracé NEUF FOIS, décalé
de -côté, 0 et +côté sur chaque axe (`cyclique`), et tout bruit part d'un
réseau PÉRIODIQUE bordé cycliquement avant agrandissement (`bruit`). Ce qui
sort d'un bord est exactement ce qui rentre par l'autre — c'est arithmétique,
pas statistique, et le banc le mesure au rapport de couture de `pbr_service`.

LE BUDGET EST UNE CONTRAINTE, PAS UN VŒU. Le runtime embarqué n'a pas numpy :
une boucle Python sur 1 048 576 pixels coûte plusieurs secondes, et six
octaves en coûteraient trente. Le procédé retenu ne fait donc de Python QUE
sur le petit réseau (au plus 256 x 256 tirages) ; tout le reste est du
`Image.resize` et de l'`ImageChops`, c'est-à-dire du C. Les budgets ci-dessous
sont mesurés par le banc, sur cette machine, et échouent s'ils sont dépassés.
"""
from __future__ import annotations

import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from app.services import pbr_service as PBR

__all__ = ["BUDGET_BRUIT_1024", "BUDGET_MOTIF_1024", "cells", "bruit",
           "etirer", "cyclique", "colorer", "GENERATEURS", "clean_params",
           "generer"]

# Budgets en secondes, à 1024x1024, sur le Python embarqué sans numpy.
BUDGET_BRUIT_1024 = 1.5
BUDGET_MOTIF_1024 = 2.5

_BORD = 2          # cellules de bordage : la portée du noyau bicubique est de
                   # 2 px côté source, donc 2 cellules couvrent tout


def cells(cote: int, voulu) -> int:
    """La taille de réseau réellement utilisable : la plus grande puissance de
    deux qui soit <= `voulu` ET qui DIVISE `cote`.

    Sans divisibilité exacte, le recadrage final ne retombe pas sur une
    période entière du réseau, et la tuile cesse d'être raccordable — c'est-à-
    dire que le seul argument mesurable du Material Forge tombe. On rend donc
    une valeur voisine plutôt que d'accepter la valeur demandée."""
    try:
        v = int(voulu)
    except (TypeError, ValueError):
        v = 8
    v = max(2, min(v, int(cote)))
    c = 2
    while c * 2 <= v:
        c *= 2
    while int(cote) % c:
        c //= 2
    return max(2, c)


def _lattice(n: int, graine: int) -> Image.Image:
    """Le réseau : n x n valeurs pseudo-aléatoires, en L. C'est le SEUL
    endroit où une boucle Python touche des pixels — n vaut 256 au pire."""
    rng = random.Random((int(graine) & 0x7FFFFFFF) * 2654435761 % (2 ** 61))
    return Image.frombytes("L", (n, n),
                           bytes(rng.randrange(256) for _ in range(n * n)))


def _octave(cote: int, n: int, graine: int) -> Image.Image:
    """Une octave : réseau périodique -> bordage cyclique -> agrandissement
    bicubique -> recadrage sur une période entière."""
    e = max(1, int(cote) // n)
    grand = PBR.wrap(_lattice(n, graine), _BORD).resize(
        ((n + 2 * _BORD) * e, (n + 2 * _BORD) * e), Image.BICUBIC)
    d = _BORD * e
    return grand.crop((d, d, d + cote, d + cote))


def _octave_naive(cote: int, n: int, graine: int) -> Image.Image:
    """LE TÉMOIN, gardé dans le module et exercé par le banc : la même octave
    SANS bordage cyclique. Aux bords, l'agrandissement bicubique prolonge le
    pixel de bord au lieu de lire l'autre côté, et la jonction se voit. Elle
    est ici pour que la différence soit MESURÉE, jamais racontée."""
    e = max(1, int(cote) // n)
    return _lattice(n, graine).resize((n * e, n * e), Image.BICUBIC).resize(
        (cote, cote), Image.BICUBIC)


def bruit(cote: int, cellules: int = 8, octaves: int = 5,
          persistance: float = 0.5, graine: int = 0) -> Image.Image:
    """Bruit de valeur fractal, seamless par construction.

    Les poids sont NORMALISÉS avant l'addition (et non divisés après) : sinon
    la somme des octaves saturerait à 255 dans `ImageChops.add`, et le motif
    reviendrait plat en haut de l'échelle sans que rien ne le signale."""
    n_oct = max(1, min(int(octaves), 8))
    p = max(0.05, min(0.95, float(persistance)))
    poids = [p ** k for k in range(n_oct)]
    somme = sum(poids) or 1.0
    total = None
    # CHAQUE OCTAVE EST ROULÉE d'un décalage cyclique pseudo-aléatoire (mesuré
    # le 06/10/2026). Sans lui, les bords de maille de TOUTES les octaves
    # tombent aux mêmes colonnes — tous les 32 px, et surtout AU BORD de la
    # tuile — ce qui dessine une grille faible et rend la jonction plus marquée
    # que l'intérieur : rapport de couture jusqu'à 1,98 sur 20 graines (moyenne
    # 1,36). Roulées, max 1,33 et moyenne 1,06. `ImageChops.offset` boucle sur
    # les bords : la périodicité n'est pas touchée.
    rng = random.Random(int(graine) * 7919 + 13)
    for k, w in enumerate(poids):
        n = cells(cote, int(cellules) * (2 ** k))
        oc = _octave(cote, n, int(graine) + 977 * k)
        oc = ImageChops.offset(oc, rng.randrange(cote), rng.randrange(cote))
        part = oc.point([PBR.clamp8(v * w / somme) for v in range(256)])
        total = part if total is None else ImageChops.add(total, part)
        if n >= cote:
            break
    return ImageOps.autocontrast(total, cutoff=1)


def etirer(img: Image.Image, kx: int = 1, ky: int = 1) -> Image.Image:
    """Étire un motif de kx en x et ky en y, EN GARDANT le raccord.

    Une réduction en BOX puis un agrandissement bicubique : la réduction d'une
    image périodique reste périodique, et l'agrandissement passe par le même
    bordage cyclique que les octaves. C'est ce qui fait un métal brossé (ky
    grand) ou un fil de bois (kx grand) sans casser la tuile."""
    w, h = img.size
    petit = img.resize((max(2, w // max(1, int(kx))),
                        max(2, h // max(1, int(ky)))), Image.BOX)
    p = 4
    grand = PBR.wrap(petit, p).resize(
        ((petit.size[0] + 2 * p) * max(1, w // petit.size[0]),
         (petit.size[1] + 2 * p) * max(1, h // petit.size[1])), Image.BICUBIC)
    dx = p * max(1, w // petit.size[0])
    dy = p * max(1, h // petit.size[1])
    return grand.crop((dx, dy, dx + w, dy + h))


def cyclique(cote: int, tracer, fond: int = 0) -> Image.Image:
    """Un canevas L où `tracer(draw, dx, dy)` est appelé NEUF FOIS, décalé de
    -côté, 0 et +côté sur chaque axe.

    Tout ce qui déborde d'un bord rentre par l'autre : la tuile est
    raccordable par arithmétique, et non par un mélange de bords qui laisse
    toujours une trace."""
    img = Image.new("L", (cote, cote), fond)
    d = ImageDraw.Draw(img)
    for dy in (-cote, 0, cote):
        for dx in (-cote, 0, cote):
            tracer(d, dx, dy)
    return img


def colorer(masque: Image.Image, sombre: str, clair: str) -> Image.Image:
    """Un masque L -> une base color RVB entre deux couleurs hex. `ImageOps.
    colorize` fait le dégradé en C, sans boucle."""
    def _rgb(h):
        s = str(h or "#808080").lstrip("#")
        s = "".join(c * 2 for c in s) if len(s) == 3 else s
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return ImageOps.colorize(masque.convert("L"), _rgb(sombre), _rgb(clair))


# ── les dix générateurs ─────────────────────────────────────────────────────
#
# CHACUN REND `basecolor` (RVB) ET `height` (L). Les six autres cartes se
# dérivent ensuite par `pbr_service.derive_maps`, exactement comme pour une
# photo : un générateur n'a aucune raison d'avoir son propre chemin de
# dérivation, et en avoir un ferait deux vérités.
#
# LA PÉRIODICITÉ EST IMPOSÉE PAR LES PARAMÈTRES, pas espérée. Les motifs se
# règlent en NOMBRE de rangs et de colonnes (des entiers), jamais en taille de
# brique : une brique de 37 px sur une tuile de 256 ne pave pas, et laisser
# l'utilisateur la choisir serait lui vendre un raccord qu'on ne peut pas
# tenir. Les angles de `rayures` sont pour la même raison une liste fermée.

def _lisser(masque: Image.Image, r: float) -> Image.Image:
    return PBR.cyclic(masque, ImageFilter.GaussianBlur(r), r * 3.0 + 1.0)


def _grain(cote: int, cellules: int, octaves: int, graine: int,
           force: float) -> Image.Image:
    """Un bruit ramené autour de 128 et atténué — le grain qu'on AJOUTE à un
    motif, sans le noyer."""
    b = bruit(cote, cellules, octaves, 0.55, graine)
    k = max(0.0, min(1.0, force))
    return b.point([PBR.clamp8(128.0 + (v - 128.0) * k) for v in range(256)])


def _melanger(masque: Image.Image, grain: Image.Image, part: float
              ) -> Image.Image:
    return Image.blend(masque, grain, max(0.0, min(1.0, part)))


def _briques(cote, p, graine):
    rangs, cols = int(p["rangs"]), int(p["colonnes"])
    h, w = cote / rangs, cote / cols
    j = max(1.0, p["joint"] * min(h, w))
    rng = random.Random(graine ^ 0x5EED)
    teintes = [rng.randrange(150, 250) for _ in range(rangs * cols + rangs)]

    def tracer(d, dx, dy):
        for r in range(-1, rangs + 1):
            y0 = r * h + dy
            off = (r % 2) * p["decalage"] * w
            for c in range(-1, cols + 2):
                x0 = c * w + off + dx
                d.rectangle([x0 + j / 2, y0 + j / 2,
                             x0 + w - j / 2, y0 + h - j / 2],
                            fill=teintes[(r * cols + c) % len(teintes)])

    masque = cyclique(cote, tracer, fond=40)
    hauteur = _lisser(masque, max(1.0, j * 0.35))
    return hauteur, _melanger(hauteur, _grain(cote, 16, 4, graine, 0.55), 0.35)


def _carrelage(cote, p, graine):
    n = int(p["cases"])
    t = cote / n
    j = max(1.0, p["joint"] * t)
    rng = random.Random(graine ^ 0xCA11)
    teintes = [rng.randrange(180, 252) for _ in range(n * n)]

    def tracer(d, dx, dy):
        for r in range(-1, n + 1):
            for c in range(-1, n + 1):
                d.rounded_rectangle(
                    [c * t + dx + j / 2, r * t + dy + j / 2,
                     (c + 1) * t + dx - j / 2, (r + 1) * t + dy - j / 2],
                    radius=max(1.0, p["arrondi"] * t * 0.2),
                    fill=teintes[(r * n + c) % len(teintes)])

    masque = cyclique(cote, tracer, fond=60)
    hauteur = _lisser(masque, max(1.0, j * 0.3))
    return hauteur, _melanger(hauteur, _grain(cote, 32, 3, graine, 0.35), 0.22)


def _planches(cote, p, graine):
    n = int(p["planches"])
    w = cote / n
    j = max(1.0, p["joint"] * w)

    def tracer(d, dx, dy):
        for c in range(-1, n + 1):
            d.rectangle([c * w + dx + j / 2, dy - cote,
                         (c + 1) * w + dx - j / 2, dy + 2 * cote], fill=210)

    masque = cyclique(cote, tracer, fond=50)
    # le fil du bois : un bruit étiré DANS le sens de la planche
    fil = etirer(bruit(cote, 8, 5, 0.6, graine), 1, max(2, int(p["fil"])))
    hauteur = _lisser(_melanger(masque, fil, 0.45), max(1.0, j * 0.3))
    return hauteur, hauteur


def _damier(cote, p, graine):
    n = int(p["cases"])
    t = cote / n

    def tracer(d, dx, dy):
        for r in range(-1, n + 1):
            for c in range(-1, n + 1):
                if (r + c) % 2:
                    continue
                d.rectangle([c * t + dx, r * t + dy,
                             (c + 1) * t + dx, (r + 1) * t + dy], fill=235)

    masque = cyclique(cote, tracer, fond=45)
    hauteur = _lisser(masque, max(1.0, p["bord"] * t * 0.1))
    return hauteur, _melanger(hauteur, _grain(cote, 32, 3, graine, 0.3), 0.18)


def _hexagones(cote, p, graine):
    # HEXAGONES LÉGÈREMENT ÉTIRÉS, ET C'EST ASSUMÉ : un hexagone RÉGULIER ne
    # pave pas un carré en nombre entier de mailles. On impose donc colonnes
    # et rangs entiers, et la maille s'étire de ce qu'il faut — le raccord
    # vaut mieux qu'une régularité que personne ne mesure.
    cols, rangs = int(p["colonnes"]), int(p["rangs"])
    w, h = cote / cols, cote / rangs
    j = max(1.0, p["joint"] * min(w, h) * 0.25)

    def hexa(d, cx, cy, fill):
        d.polygon([(cx - w / 2 + j, cy - h / 4), (cx, cy - h / 2 + j),
                   (cx + w / 2 - j, cy - h / 4), (cx + w / 2 - j, cy + h / 4),
                   (cx, cy + h / 2 - j), (cx - w / 2 + j, cy + h / 4)],
                  fill=fill)

    rng = random.Random(graine ^ 0x4E60)
    teintes = [rng.randrange(170, 250) for _ in range(cols * rangs + cols)]

    def tracer(d, dx, dy):
        for r in range(-1, rangs + 1):
            for c in range(-1, cols + 1):
                cx = (c + 0.5 * (r % 2)) * w + dx
                hexa(d, cx, (r + 0.5) * h + dy,
                     teintes[(r * cols + c) % len(teintes)])

    masque = cyclique(cote, tracer, fond=55)
    hauteur = _lisser(masque, max(1.0, j))
    return hauteur, _melanger(hauteur, _grain(cote, 24, 3, graine, 0.35), 0.2)


def _galets(cote, p, graine):
    n = max(4, int(p["densite"]))
    rng = random.Random(graine ^ 0x6A1E)
    pierres = [(rng.random() * cote, rng.random() * cote,
                cote / n * (0.45 + 0.55 * rng.random()),
                rng.randrange(150, 250)) for _ in range(n * n)]
    pierres.sort(key=lambda s: s[2])          # les grosses par-dessus

    def tracer(d, dx, dy):
        for x, y, r, t in pierres:
            d.ellipse([x - r + dx, y - r * 0.8 + dy,
                       x + r + dx, y + r * 0.8 + dy], fill=t)

    masque = cyclique(cote, tracer, fond=40)
    # `relief` pilote l'arrondi des galets : à 0,1 ils sont plats et nets, à
    # 1,0 ils bombent. Un réglage qui ne changerait rien serait un mensonge, et
    # le banc en attrape un par générateur.
    r = max(0.1, min(1.0, p["relief"]))
    hauteur = _lisser(masque, max(1.5, cote / n * 0.06 + cote / n * 0.20 * r))
    return hauteur, _melanger(hauteur, _grain(cote, 32, 4, graine, 0.5), 0.3)


def _metal_brosse(cote, p, graine):
    # Le brossage EST une anisotropie : un bruit fin étiré dans un sens.
    fin = bruit(cote, 64, 3, 0.6, graine)
    brosse = etirer(fin, 1, max(4, int(p["longueur"])))
    k = max(0.05, min(1.0, p["force"]))
    hauteur = brosse.point([PBR.clamp8(128.0 + (v - 128.0) * k)
                            for v in range(256)])
    large = bruit(cote, 4, 2, 0.5, graine + 7).point(
        [PBR.clamp8(128.0 + (v - 128.0) * 0.25) for v in range(256)])
    return hauteur, ImageChops.add(hauteur, large, 2.0, 0)


def _cuir(cote, p, graine):
    n = max(6, int(p["cellules"]))
    rng = random.Random(graine ^ 0xC01A)
    cells_ = [(rng.random() * cote, rng.random() * cote,
               cote / n * (0.5 + 0.6 * rng.random())) for _ in range(n * n)]

    def tracer(d, dx, dy):
        for x, y, r in cells_:
            d.ellipse([x - r + dx, y - r + dy, x + r + dx, y + r + dy],
                      fill=230)

    grosses = _lisser(cyclique(cote, tracer, fond=90), max(1.5, cote / n * 0.2))
    pores = _grain(cote, 96, 3, graine + 3, max(0.05, min(1.0, p["pores"])))
    hauteur = _melanger(grosses, pores, 0.35)
    return hauteur, hauteur


def _tissu(cote, p, graine):
    # ARMURE TOILE : un fil de chaîne sur deux passe au-dessus. Deux familles
    # de bandes et un damier qui décide laquelle domine — périodique par
    # construction dès que le nombre de fils divise le côté.
    n = int(p["fils"])
    t = cote / n

    def bandes(vertical):
        def tracer(d, dx, dy):
            for i in range(-1, n + 1):
                if vertical:
                    x = i * t + dx
                    d.rectangle([x + t * 0.12, dy - cote,
                                 x + t * 0.88, dy + 2 * cote], fill=235)
                else:
                    y = i * t + dy
                    d.rectangle([dx - cote, y + t * 0.12,
                                 dx + 2 * cote, y + t * 0.88], fill=235)
        return cyclique(cote, tracer, fond=60)

    def damier(d, dx, dy):
        for r in range(-1, n + 1):
            for c in range(-1, n + 1):
                if (r + c) % 2:
                    d.rectangle([c * t + dx, r * t + dy,
                                 (c + 1) * t + dx, (r + 1) * t + dy], fill=255)

    dessus = cyclique(cote, damier, fond=0)
    croise = Image.composite(bandes(True), bandes(False), dessus)
    hauteur = _lisser(croise, max(1.0, t * 0.18))
    return hauteur, _melanger(hauteur, _grain(cote, 96, 3, graine, 0.4), 0.25)


def _rayures(cote, p, graine):
    n = int(p["bandes"])
    t = cote / n
    ang = int(p["angle"])
    part = max(0.05, min(0.95, p["largeur"]))

    def tracer(d, dx, dy):
        for i in range(-2, 2 * n + 2):
            if ang == 0:
                d.rectangle([dx - cote, i * t + dy, dx + 2 * cote,
                             i * t + t * part + dy], fill=235)
            elif ang == 90:
                d.rectangle([i * t + dx, dy - cote,
                             i * t + t * part + dx, dy + 2 * cote], fill=235)
            else:
                s = 1 if ang == 45 else -1
                d.line([(i * t + dx - cote, dy - s * cote),
                        (i * t + dx + 2 * cote, dy + 2 * s * cote)],
                       fill=235, width=max(1, int(t * part)))

    masque = cyclique(cote, tracer, fond=55)
    hauteur = _lisser(masque, max(1.0, t * 0.12))
    return hauteur, _melanger(hauteur, _grain(cote, 48, 3, graine, 0.3), 0.2)


# `f` = flottant borné, `i` = entier borné, `e` = liste fermée, `c` = couleur.
GENERATEURS = [
    {"id": "briques", "label": "Briques", "sombre": "#3a2620", "clair": "#b2705a",
     "params": [{"k": "rangs", "type": "i", "min": 2, "max": 32, "def": 8},
                {"k": "colonnes", "type": "i", "min": 1, "max": 16, "def": 4},
                {"k": "joint", "type": "f", "min": 0.02, "max": 0.30, "def": 0.10},
                {"k": "decalage", "type": "f", "min": 0.0, "max": 0.5, "def": 0.5}]},
    {"id": "carrelage", "label": "Carrelage", "sombre": "#2b3138", "clair": "#cfd6dd",
     "params": [{"k": "cases", "type": "i", "min": 2, "max": 24, "def": 6},
                {"k": "joint", "type": "f", "min": 0.02, "max": 0.25, "def": 0.08},
                {"k": "arrondi", "type": "f", "min": 0.0, "max": 1.0, "def": 0.3}]},
    {"id": "planches", "label": "Planches", "sombre": "#3b2a18", "clair": "#c39a63",
     "params": [{"k": "planches", "type": "i", "min": 2, "max": 16, "def": 5},
                {"k": "joint", "type": "f", "min": 0.01, "max": 0.20, "def": 0.05},
                {"k": "fil", "type": "i", "min": 2, "max": 64, "def": 24}]},
    {"id": "damier", "label": "Damier", "sombre": "#1c1c20", "clair": "#e6e6ea",
     "params": [{"k": "cases", "type": "i", "min": 2, "max": 32, "def": 8},
                {"k": "bord", "type": "f", "min": 0.0, "max": 1.0, "def": 0.2}]},
    {"id": "hexagones", "label": "Hexagones", "sombre": "#242a2e", "clair": "#a9b6bf",
     "params": [{"k": "colonnes", "type": "i", "min": 2, "max": 20, "def": 6},
                {"k": "rangs", "type": "i", "min": 2, "max": 20, "def": 8},
                {"k": "joint", "type": "f", "min": 0.05, "max": 0.6, "def": 0.25}]},
    {"id": "galets", "label": "Galets", "sombre": "#2a2a28", "clair": "#b8b5ab",
     "params": [{"k": "densite", "type": "i", "min": 4, "max": 24, "def": 9},
                {"k": "relief", "type": "f", "min": 0.1, "max": 1.0, "def": 0.6}]},
    {"id": "metal_brosse", "label": "Métal brossé", "sombre": "#5a5f66", "clair": "#d7dce2",
     "params": [{"k": "longueur", "type": "i", "min": 4, "max": 128, "def": 48},
                {"k": "force", "type": "f", "min": 0.05, "max": 1.0, "def": 0.45}]},
    {"id": "cuir", "label": "Cuir", "sombre": "#2a1b14", "clair": "#8c5c3d",
     "params": [{"k": "cellules", "type": "i", "min": 6, "max": 40, "def": 16},
                {"k": "pores", "type": "f", "min": 0.1, "max": 1.0, "def": 0.6}]},
    {"id": "tissu", "label": "Tissu", "sombre": "#33384a", "clair": "#98a2bd",
     "params": [{"k": "fils", "type": "i", "min": 4, "max": 64, "def": 24}]},
    {"id": "rayures", "label": "Rayures", "sombre": "#1e2430", "clair": "#d5dbe6",
     "params": [{"k": "bandes", "type": "i", "min": 2, "max": 48, "def": 10},
                {"k": "largeur", "type": "f", "min": 0.1, "max": 0.9, "def": 0.5},
                {"k": "angle", "type": "e", "choix": (0, 45, 90, 135), "def": 0}]},
]

_FONCTIONS = {"briques": _briques, "carrelage": _carrelage,
              "planches": _planches, "damier": _damier,
              "hexagones": _hexagones, "galets": _galets,
              "metal_brosse": _metal_brosse, "cuir": _cuir,
              "tissu": _tissu, "rayures": _rayures}
_PAR_ID = {g["id"]: g for g in GENERATEURS}


def clean_params(gid: str, raw) -> dict:
    """Réglages complets et bornés. Ne lève jamais (même règle que
    `material_store.normalize_material`) : l'entrée vient du réseau."""
    g = _PAR_ID.get(str(gid or ""))
    if g is None:
        return {}
    src = raw if isinstance(raw, dict) else {}
    out = {}
    for c in g["params"]:
        v = src.get(c["k"])
        if c["type"] == "e":
            try:
                iv = int(v)
            except (TypeError, ValueError):
                iv = c["def"]
            out[c["k"]] = iv if iv in c["choix"] else c["def"]
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            fv = float(c["def"])
        if fv != fv or fv in (float("inf"), float("-inf")):
            fv = float(c["def"])
        fv = max(float(c["min"]), min(float(c["max"]), fv))
        out[c["k"]] = int(round(fv)) if c["type"] == "i" else round(fv, 4)
    return out


def generer(gid: str, cote: int, params: dict, graine: int = 0,
            sombre: str = "", clair: str = "") -> dict:
    """{basecolor, height} d'un générateur. Les six autres cartes se dérivent
    ensuite par `pbr_service.derive_maps` — un seul chemin de dérivation dans
    tout le produit."""
    g = _PAR_ID.get(str(gid or ""))
    if g is None:
        raise ValueError(f"générateur « {gid} » inconnu — connus : "
                         f"{', '.join(_PAR_ID)}")
    n = max(64, int(cote))
    hauteur, motif = _FONCTIONS[g["id"]](n, clean_params(g["id"], params),
                                         int(graine))
    return {"height": hauteur,
            "basecolor": colorer(motif, sombre or g["sombre"],
                                 clair or g["clair"])}
