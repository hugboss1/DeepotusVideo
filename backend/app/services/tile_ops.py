# -*- coding: utf-8 -*-
"""Tuiles raccordables : table du blob, masques, assemblage (plan
2026-09-03-plan-tuiles, P1 — tâche t113).

NUMÉROTATION FIXÉE PAR LE PLAN — horaire depuis le nord :
    N=1, NE=2, E=4, SE=8, S=16, SW=32, W=64, NW=128
C'est exactement l'ordre du `wangid` de Tiled (« top, top-right, right,
bottom-right, bottom, bottom-left, left, top-left », doc.mapeditor.org), ce qui
rend l'export Tiled une lecture bit à bit. L'article de référence
(boristhebrave, relu le 06/10/2026) numérote autrement (topLeft=1, top=2…) :
la divergence est VOULUE, seule la règle et le compte en sont repris.

Un bit de COIN n'est retenu que si ses DEUX arêtes adjacentes sont posées
(règle citée : « The corner tiles are only relevant if both edge tiles are
solid ») : 47 voisinages distincts, plus la 48e tuile VIDE (« 47 solid and 1
empty »). La table est CALCULÉE (canon sur 0..255), jamais recopiée.

GARANTIE DE RACCORD : l'anneau extérieur (bande de `cote // 8` px) ne dépend
QUE des arêtes — les quatre bandes valent leur bit, les quatre carrés de coin
valent le OU des deux arêtes adjacentes. Deux voisines légales (chacune a le
bit qui pointe vers l'autre) présentent donc, sur la colonne partagée, de la
matière A des deux côtés : le raccord vaut celui de la matière avec elle-même,
soit 0.00 pour une matière miroir (mesuré au banc : 1156 paires E, 1156 paires
S, max 0.0). Le bit de coin ne façonne qu'une ENCOCHE strictement intérieure.

PIL pur : le python embarqué n'a pas numpy.
"""
from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw, ImageFilter

N, NE, E, SE, S, SW, W, NW = 1, 2, 4, 8, 16, 32, 64, 128
ORDRE = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
BITS = (N, NE, E, SE, S, SW, W, NW)
#: (bit du coin, arête A, arête B) — le coin ne vit que si A ET B sont posées
COINS = ((NE, N, E), (SE, E, S), (SW, S, W), (NW, W, N))
#: (nom, dx, dy, bit) — dx/dy en cases, y vers le bas
DIRS = (("N", 0, -1, N), ("NE", 1, -1, NE), ("E", 1, 0, E), ("SE", 1, 1, SE),
        ("S", 0, 1, S), ("SW", -1, 1, SW), ("W", -1, 0, W), ("NW", -1, -1, NW))

JEUX = ("blob47", "blob16")


def canon(m) -> int:
    """Voisinage 0..255 ramené à sa forme canonique."""
    m = int(m) & 255
    for coin, a, b in COINS:
        if m & coin and not (m & a and m & b):
            m &= ~coin
    return m & 255


BLOB47 = sorted({canon(m) for m in range(256)})
BLOB16 = sorted({m & (N | E | S | W) for m in range(256)})
TABLES = {"blob47": BLOB47, "blob16": BLOB16}
_INDEX = {jeu: {m: i for i, m in enumerate(t)} for jeu, t in TABLES.items()}


def cles(jeu: str = "blob47") -> list[int]:
    if jeu not in TABLES:
        raise ValueError(f"jeu inconnu: {jeu!r} (attendu {', '.join(JEUX)})")
    return TABLES[jeu]


def index_de(m, jeu: str = "blob47") -> int:
    """Index de tuile (0..46 ou 0..15) d'un voisinage quelconque."""
    cles(jeu)
    m = canon(m) if jeu == "blob47" else (int(m) & (N | E | S | W))
    return _INDEX[jeu][m]


def masque_blob(m, cote: int = 64) -> Image.Image:
    """Masque « L » : 255 = matière A (terrain), 0 = matière B (fond)."""
    m = canon(m)
    b = max(2, cote // 8)
    r = max(2, cote // 6)
    im = Image.new("L", (cote, cote), 0)
    d = ImageDraw.Draw(im)
    d.rectangle((b, b, cote - b - 1, cote - b - 1), fill=255)      # le noyau
    if m & N:
        d.rectangle((b, 0, cote - b - 1, b - 1), fill=255)
    if m & S:
        d.rectangle((b, cote - b, cote - b - 1, cote - 1), fill=255)
    if m & W:
        d.rectangle((0, b, b - 1, cote - b - 1), fill=255)
    if m & E:
        d.rectangle((cote - b, b, cote - 1, cote - b - 1), fill=255)
    # carrés de coin de l'anneau = OU des deux arêtes : c'est CE choix qui rend
    # la colonne partagée de deux voisines légales entièrement pleine
    if m & N or m & E:
        d.rectangle((cote - b, 0, cote - 1, b - 1), fill=255)
    if m & S or m & E:
        d.rectangle((cote - b, cote - b, cote - 1, cote - 1), fill=255)
    if m & S or m & W:
        d.rectangle((0, cote - b, b - 1, cote - 1), fill=255)
    if m & N or m & W:
        d.rectangle((0, 0, b - 1, b - 1), fill=255)
    # encoche du coin diagonal ABSENT — strictement à l'intérieur de l'anneau,
    # donc invisible pour le raccord
    for bit, a, c, (cx, cy) in ((NE, N, E, (cote - b - r, b + r)),
                                (SE, E, S, (cote - b - r, cote - b - r)),
                                (SW, S, W, (b + r, cote - b - r)),
                                (NW, W, N, (b + r, b + r))):
        if (m & a) and (m & c) and not (m & bit):
            d.ellipse((cx - r, cy - r, cx + r - 1, cy + r - 1), fill=0)
    return im


def masque_coeur(cote: int = 64) -> Image.Image:
    """Masque des VARIANTES (P3) : 255 au centre, 0 DUR sur l'anneau de
    `cote // 8` px. Une variante ne touche donc jamais le bord et le raccord
    des paires légales reste exactement 0."""
    b = max(2, cote // 8)
    m = Image.new("L", (cote, cote), 0)
    ImageDraw.Draw(m).rectangle((2 * b, 2 * b, cote - 2 * b - 1,
                                 cote - 2 * b - 1), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(b / 2))
    # le flou bave de quelques niveaux sur l'anneau : on le remet à 0 DUR
    d = ImageDraw.Draw(m)
    d.rectangle((0, 0, cote - 1, b - 1), fill=0)
    d.rectangle((0, cote - b, cote - 1, cote - 1), fill=0)
    d.rectangle((0, 0, b - 1, cote - 1), fill=0)
    d.rectangle((cote - b, 0, cote - 1, cote - 1), fill=0)
    return m


def varier(mat: Image.Image, coeur: Image.Image, dx: int,
           dy: int) -> Image.Image:
    """Matière perturbée par un décalage cyclique, mais SEULEMENT au cœur."""
    return Image.composite(ImageChops.offset(mat, dx, dy), mat, coeur)


def assembler_jeu(mat_a: Image.Image, mat_b: Image.Image, jeu: str = "blob47",
                  cote: int = 64, variantes: int = 1,
                  graine: int = 1) -> dict:
    """Le jeu complet : `len(cles) * variantes` tuiles + la tuile VIDE.

    L'index d'une tuile est `index_de(m) * variantes + k` ; la VIDE est la
    dernière (`len(cles) * variantes`). Les variantes ne touchent que le cœur
    (masque_coeur), donc le raccord des paires légales reste 0.00."""
    import random as _random

    table = cles(jeu)
    variantes = max(1, min(5, int(variantes)))
    cote = max(16, min(512, int(cote)))
    A = mat_a.convert("RGB").resize((cote, cote), Image.LANCZOS)
    B = mat_b.convert("RGB").resize((cote, cote), Image.LANCZOS)
    coeur = masque_coeur(cote)
    rng = _random.Random(int(graine))
    tuiles: list[Image.Image] = []
    for m in table:
        mq = masque_blob(m, cote)
        for k in range(variantes):
            if k == 0:
                a, b = A, B
            else:
                dx, dy = rng.randrange(cote), rng.randrange(cote)
                a, b = varier(A, coeur, dx, dy), varier(B, coeur, dx, dy)
            tuiles.append(Image.composite(a, b, mq))
    tuiles.append(B.copy())                       # la tuile VIDE, sans terrain
    return {"jeu": jeu, "cles": list(table), "cote": cote,
            "variantes": variantes, "graine": int(graine),
            "tuiles": tuiles, "vide": len(table) * variantes}


def atlas(jeu: dict, colonnes: int = 0):
    """(image RGB, colonnes, rangées). 8 colonnes par défaut pour blob47
    (48 = 8 x 6, la VIDE tombe pile en bas à droite), 4 pour blob16."""
    n = len(jeu["tuiles"])
    if not colonnes:
        colonnes = 8 if jeu["jeu"] == "blob47" else 4
    colonnes = max(1, int(colonnes))
    rangees = (n + colonnes - 1) // colonnes
    cote = jeu["cote"]
    img = Image.new("RGB", (colonnes * cote, rangees * cote), (0, 0, 0))
    for i, t in enumerate(jeu["tuiles"]):
        img.paste(t.convert("RGB"), ((i % colonnes) * cote,
                                     (i // colonnes) * cote))
    return img, colonnes, rangees


# ── auto-tuilage (P3, tâche t115) : UN moteur pour l'aperçu et, plus tard, le peintre (T12) ──────────────────────────
def carte_aleatoire(cases: int = 8, densite: float = 0.55,
                    graine: int = 1) -> list[list[int]]:
    """Grille booléenne de terrain (1 = matière A), rejouable à graine égale."""
    import random as _random

    rng = _random.Random(int(graine))
    d = min(1.0, max(0.0, float(densite)))
    return [[1 if rng.random() < d else 0 for _ in range(cases)]
            for _ in range(cases)]


def masque_voisins(grille, x: int, y: int, boucle: bool = True) -> int:
    """Le voisinage CANONIQUE de la case (x, y). `boucle=True` : la carte est un tore (l'aperçu) ;
    `boucle=False` : hors carte = vide (le peintre)."""
    h = len(grille)
    w = len(grille[0]) if h else 0
    m = 0
    for _, dx, dy, bit in DIRS:
        nx, ny = x + dx, y + dy
        if boucle:
            nx, ny = nx % w, ny % h
        elif not (0 <= nx < w and 0 <= ny < h):
            continue
        if grille[ny][nx]:
            m |= bit
    return canon(m)


def composer_carte(grille, jeu: dict, graine: int = 1, boucle: bool = True):
    """(image RGB de la carte, plan [[index de tuile]]).

    C'est Python qui compose, le navigateur ne fait que voir. La tuile d'une case de terrain est celle de son
    voisinage, plus une variante TIRÉE ; une case vide reçoit la VIDE. Le voisinage passe par `index_de`, qui le
    réduit aux quatre arêtes pour un blob16 — chercher le voisinage canonique brut dans `cles` lèverait une
    KeyError au premier coin posé (banc test_composer_carte_blob16_lit_les_aretes_seules)."""
    import random as _random

    v = jeu["variantes"]
    rng = _random.Random(int(graine))
    cote = jeu["cote"]
    h = len(grille)
    w = len(grille[0]) if h else 0
    img = Image.new("RGB", (w * cote, h * cote), (0, 0, 0))
    plan = []
    for y in range(h):
        ligne = []
        for x in range(w):
            if grille[y][x]:
                t = index_de(masque_voisins(grille, x, y, boucle), jeu["jeu"]) * v + rng.randrange(v)
            else:
                t = jeu["vide"]
            img.paste(jeu["tuiles"][t].convert("RGB"), (x * cote, y * cote))
            ligne.append(t)
        plan.append(ligne)
    return img, plan
