# -*- coding: utf-8 -*-
"""Card Forge — pièce 09, sidecar « objets du jeu » (tâche #87 PR B, plan-cartes T16-T17, 04/10/2026).

SIDECAR : aucun `router` (règle 8 — les routes vivent dans forge3d.py). De la géométrie en millimètres et un patron
de boîte ; l'écriture STL/3MF appartient à `print3d` (garde de plateau 256 mm qui AVERTIT sans interdire).

DÉCISIONS DE L'UTILISATEUR (04/10) : route HORS du graphe (les nœuds de Forge 3D ne changent pas) ; le jeton peut
porter le RELIEF de la carte ; le présentoir TIENT la carte (une rainure entre deux rails, sur un socle — le plan
posait deux plaques disjointes, sans fond) ; la boîte est une VRAIE tuck box (languette de collage, rabats
anti-poussière, couvercles à rabat rentrant — le plan dessinait un rectangle plié, qui ne ferme rien).

DEUX RÈGLES MÉCANIQUES, comptées par le banc :
  1. TOUT SOLIDE EST FERMÉ — chaque arête vue deux fois, une fois dans chaque sens. Un objet fait de plusieurs
     solides fermés qui se TOUCHENT (socle + rails, disque + relief) est légal : le trancheur les unit.
  2. TOUT REPOSE À z = 0.
`numpy` est ABSENT du runtime : trigonométrie stdlib, triangles ((x,y,z),(x,y,z),(x,y,z)) comme `print3d`.
"""
from __future__ import annotations

import math
from typing import Any

__all__ = ["DIAM_MM", "EP_MM", "COTES", "jeton", "jeton_relief", "pion", "presentoir", "fermeture",
           "epaisseur_deck_mm", "patron_boite", "JEU_MM_DEFAUT", "RABAT_MM_DEFAUT", "MARGE_MM"]

DIAM_MM = (5.0, 300.0)     # bornes d'un jeton
EP_MM = (0.6, 50.0)        # sous 0,6 mm, une buse de 0,4 ne tient pas
COTES = (8, 256)
RELIEF_MM = (0.2, 3.0)     # hauteur du relief au-dessus du jeton (la borne de forge3d_scene)
GRILLE = (32, 160)         # grille du relief : 160 suffit sur 25 mm (≈ 0,16 mm par maille)


def _borne(v: Any, lo_hi: tuple, quoi: str) -> float:
    lo, hi = lo_hi
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} doit être un nombre (mm)")
    if not math.isfinite(x) or x < lo or x > hi:
        raise ValueError(f"{quoi} doit tenir entre {lo:g} et {hi:g} mm (reçu {v!r})")
    return x


def _entier(v: Any, lo_hi: tuple, quoi: str) -> int:
    lo, hi = lo_hi
    try:
        x = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} doit être un entier")
    if x < lo or x > hi:
        raise ValueError(f"{quoi} doit tenir entre {lo} et {hi} (reçu {v!r})")
    return x


def _prisme(profil: list, ep: float, z0: float = 0.0) -> list:
    """Un profil CONVEXE (plan XY, sens direct) extrudé de `ep` à partir de `z0`. Fermé : couvercles en éventail
    depuis le centroïde (valable sur un convexe — ce fichier n'en produit pas d'autre)."""
    n = len(profil)
    cx = sum(p[0] for p in profil) / n
    cy = sum(p[1] for p in profil) / n
    z1 = z0 + ep
    tris = []
    for i in range(n):
        x0, y0 = profil[i]
        x1, y1 = profil[(i + 1) % n]
        tris.append(((cx, cy, z0), (x1, y1, z0), (x0, y0, z0)))       # dessous, normale -Z
        tris.append(((cx, cy, z1), (x0, y0, z1), (x1, y1, z1)))       # dessus, normale +Z
        tris.append(((x0, y0, z0), (x1, y1, z0), (x1, y1, z1)))       # tranche, vers l'extérieur
        tris.append(((x0, y0, z0), (x1, y1, z1), (x0, y0, z1)))
    return tris


def _cercle(diam: float, cotes: int) -> list:
    r = diam / 2.0
    return [(r * math.cos(2 * math.pi * k / cotes), r * math.sin(2 * math.pi * k / cotes)) for k in range(cotes)]


def _rect(x0: float, y0: float, x1: float, y1: float) -> list:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def fermeture(tris: list) -> int:
    """Le nombre d'arêtes OUVERTES (vues sans leur jumelle inverse). 0 = solide(s) fermé(s)."""
    aretes: dict = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b))
            aretes[k] = aretes.get(k, 0) + 1
    return sum(1 for k, n in aretes.items() if aretes.get((k[1], k[0]), 0) != n)


def jeton(diam_mm: Any = 25.0, ep_mm: Any = 3.0, cotes: Any = 64) -> list:
    """Un jeton rond (polygonal si `cotes` est petit), posé à z = 0."""
    d = _borne(diam_mm, DIAM_MM, "Le diamètre du jeton")
    e = _borne(ep_mm, EP_MM, "L'épaisseur du jeton")
    c = _entier(cotes, COTES, "Le nombre de côtés")
    return _prisme(_cercle(d, c), e)


def jeton_relief(image, diam_mm: Any = 30.0, ep_mm: Any = 2.0, relief_mm: Any = 0.8, grille: Any = 120,
                 cotes: Any = 96) -> list:
    """Un jeton qui porte le RELIEF d'une image (la carte) : le disque, et posé dessus un carré inscrit dont la
    hauteur suit la luminance (clair = haut). Deux solides fermés qui se touchent à z = ep."""
    from .forge3d_scene import relief_mesh
    d = _borne(diam_mm, (10.0, 300.0), "Le diamètre du jeton")
    e = _borne(ep_mm, EP_MM, "L'épaisseur du jeton")
    h = _borne(relief_mm, RELIEF_MM, "La hauteur du relief")
    g = _entier(grille, GRILLE, "La grille du relief")
    disque = _prisme(_cercle(d, _entier(cotes, COTES, "Le nombre de côtés")), e)
    im = image.convert("L")
    w, hh = im.size
    s = min(w, hh)
    if s < 8:
        raise ValueError("Image trop petite pour un relief (8 pixels au moins)")
    im = im.crop(((w - s) // 2, (hh - s) // 2, (w - s) // 2 + s, (hh - s) // 2 + s))   # le carré central
    cote = d / math.sqrt(2.0) * 0.92                    # inscrit dans le disque, avec un liseré
    m = relief_mesh(im, cote, cote, h, 0.1, g)
    pos, idx = m["positions"], m["indices"]
    dx = dy = -cote / 2.0

    def p(i):
        return (pos[3 * i] + dx, pos[3 * i + 1] + dy, pos[3 * i + 2] + e)
    relief = [(p(idx[k]), p(idx[k + 1]), p(idx[k + 2])) for k in range(0, len(idx), 3)]
    return disque + relief


def pion(diam_bas_mm: Any = 22.0, diam_haut_mm: Any = 16.0, ep_mm: Any = 3.0, etages: Any = 3, cotes: Any = 48) -> list:
    """Un pion en étages qui s'affinent du socle à la tête (socle LARGE : il tient debout). Disques empilés, fermés,
    qui se touchent."""
    db = _borne(diam_bas_mm, DIAM_MM, "Le diamètre du socle")
    dh = _borne(diam_haut_mm, DIAM_MM, "Le diamètre de la tête")
    if dh > db:
        raise ValueError("La tête est plus large que le socle : le pion basculerait (diam_haut_mm ≤ diam_bas_mm)")
    e = _borne(ep_mm, EP_MM, "L'épaisseur d'un étage")
    n = _entier(etages, (2, 12), "Le nombre d'étages")
    c = _entier(cotes, COTES, "Le nombre de côtés")
    out = []
    for k in range(n):
        dk = db + (dh - db) * k / (n - 1)
        out += _prisme(_cercle(dk, c), e, z0=k * e)
    return out


def presentoir(largeur_mm: Any = 74.0, profondeur_mm: Any = 30.0, socle_mm: Any = 3.0, rainure_mm: Any = 1.0,
               rail_mm: Any = 6.0, hauteur_rail_mm: Any = 8.0) -> list:
    """Un présentoir qui TIENT la carte : un socle, et dessus deux rails parallèles séparés par la rainure où la
    carte se glisse debout. La rainure vaut l'épaisseur de la carte plus le jeu d'impression."""
    L = _borne(largeur_mm, (20.0, 300.0), "La largeur du présentoir")
    P = _borne(profondeur_mm, (15.0, 300.0), "La profondeur du présentoir")
    S = _borne(socle_mm, (1.2, 20.0), "L'épaisseur du socle")
    R = _borne(rainure_mm, (0.5, 10.0), "La largeur de la rainure")
    W = _borne(rail_mm, (2.0, 50.0), "La largeur d'un rail")
    H = _borne(hauteur_rail_mm, (2.0, 60.0), "La hauteur des rails")
    if 2 * W + R > P:
        raise ValueError(f"Deux rails de {W:g} mm et la rainure de {R:g} mm ne tiennent pas dans {P:g} mm de profondeur")
    y0 = (P - R) / 2.0 - W
    socle = _prisme(_rect(0.0, 0.0, L, P), S)
    avant = _prisme(_rect(0.0, y0, L, y0 + W), H, z0=S)
    arriere = _prisme(_rect(0.0, y0 + W + R, L, y0 + 2 * W + R), H, z0=S)
    return socle + avant + arriere


# ── LA BOÎTE ─────────────────────────────────────────────────────────────────────────────────────────────────────
# Une boîte à la taille EXACTE du deck ne se ferme pas : le carton a une épaisseur et l'impression une tolérance. Le
# jeu est donc EXPLICITE, réglable, et il est écrit sur la feuille.
JEU_MM_DEFAUT = 1.0
RABAT_MM_DEFAUT = 15.0
MARGE_MM = 6.0             # marge non imprimable autour du développé


def epaisseur_deck_mm(cartes: Any, ep_carte_mm: Any) -> float:
    """L'épaisseur d'un paquet ; `ep_carte_mm` vient de la pièce 05 (doc.solid.thickness_mm) : on ne devine pas."""
    return max(0, int(cartes)) * float(ep_carte_mm)


def patron_boite(largeur_mm: Any, hauteur_mm: Any, epaisseur_deck: Any, jeu_mm: Any = JEU_MM_DEFAUT,
                 rabat_mm: Any = RABAT_MM_DEFAUT, feuilles: dict | None = None, feuille: str = "a4") -> dict:
    """Le développé d'une TUCK BOX. -> {boite_mm, developpe_mm, feuille, paysage, contour, plis}.

    Colonnes, de gauche à droite : DOS (L), FLANC (E), FACE (L), FLANC (E), LANGUETTE de collage. Rangées, de bas
    en haut : rabat rentrant (R), couvercle (E), CORPS (H), couvercle (E), rabat rentrant (R) — les couvercles et
    leurs rabats prolongent le DOS ; les flancs portent des rabats anti-poussière ; la face a une encoche pour le
    pouce. `contour` est UNE polyligne fermée (trait plein = couper), `plis` des segments (pointillés = plier).
    Unités : mm, origine en bas à gauche du développé."""
    L = _borne(largeur_mm, (20.0, 400.0), "La largeur de carte") + _borne(jeu_mm, (0.0, 5.0), "Le jeu")
    H = float(hauteur_mm) + float(jeu_mm)
    E = _borne(epaisseur_deck, (0.3, 150.0), "L'épaisseur du paquet") + float(jeu_mm)
    R = _borne(rabat_mm, (5.0, 60.0), "Le rabat")
    G = 10.0                                   # languette de collage
    g = 2.0                                    # son chanfrein
    D = min(E, H / 3.0)                        # rabats anti-poussière
    dl = min(2.0, E / 4.0)                     # leur dépouille
    x1, x2, x3, x4 = L, L + E, 2 * L + E, 2 * L + 2 * E
    y0 = R + E
    y1 = y0 + H
    dw, dh = x4 + G, y1 + E + R
    pouce = min(9.0, L / 5.0)                  # rayon de l'encoche
    cxp = (x2 + x3) / 2.0
    encoche = [(cxp + pouce * math.cos(math.pi * k / 12), y1 - pouce * math.sin(math.pi * k / 12)) for k in range(13)]
    contour = [(0.0, 0.0), (x1, 0.0), (x1, y0),
               (x1 + dl, y0 - D), (x2 - dl, y0 - D), (x2, y0),          # rabat anti-poussière bas, flanc 1
               (x3, y0),
               (x3 + dl, y0 - D), (x4 - dl, y0 - D), (x4, y0),          # rabat anti-poussière bas, flanc 2
               (x4 + G, y0 + g), (x4 + G, y1 - g), (x4, y1),            # languette de collage
               (x4 - dl, y1 + D), (x3 + dl, y1 + D), (x3, y1)]          # rabat anti-poussière haut, flanc 2
    contour += encoche                                                   # face : encoche du pouce, de x3 vers x2
    contour += [(x2, y1), (x2 - dl, y1 + D), (x1 + dl, y1 + D), (x1, y1),   # rabat anti-poussière haut, flanc 1
                (x1, dh), (0.0, dh), (0.0, 0.0)]
    plis = [[x, y0, x, y1] for x in (x1, x2, x3, x4)]                    # les quatre arêtes verticales
    plis += [[0.0, y0, x1, y0], [0.0, y1, x1, y1],                       # charnières des couvercles
             [0.0, y0 - E, x1, y0 - E], [0.0, y1 + E, x1, y1 + E],       # couvercle → rabat rentrant
             [x1, y0, x2, y0], [x1, y1, x2, y1], [x3, y0, x4, y0], [x3, y1, x4, y1]]   # rabats anti-poussière
    fs = feuilles or {"a4": (210.0, 297.0), "letter": (215.9, 279.4), "a3": (297.0, 420.0)}
    nom = str(feuille or "a4").lower()
    if nom not in fs:
        raise ValueError(f"Feuille inconnue : « {feuille} » ({', '.join(fs)})")

    def tient(f):
        fw, fh = fs[f]
        if dw + 2 * MARGE_MM <= fw and dh + 2 * MARGE_MM <= fh:
            return False
        if dh + 2 * MARGE_MM <= fw and dw + 2 * MARGE_MM <= fh:
            return True
        return None
    paysage = tient(nom)
    if paysage is None:
        autre = next((f for f in fs if tient(f) is not None), "")
        raise ValueError("Le développé fait %.1f x %.1f mm (marges de %g mm comprises : %.1f x %.1f) et ne tient pas sur "
                         "%s (%.1f x %.1f mm)%s." % (dw, dh, MARGE_MM, dw + 2 * MARGE_MM, dh + 2 * MARGE_MM, nom.upper(),
                                                     fs[nom][0], fs[nom][1],
                                                     " — %s conviendrait" % autre.upper() if autre
                                                     else " ; aucune feuille ne convient : réduisez le nombre de cartes"))
    return {"boite_mm": [round(L, 3), round(H, 3), round(E, 3)], "developpe_mm": [round(dw, 3), round(dh, 3)],
            "feuille": nom, "paysage": paysage, "jeu_mm": float(jeu_mm), "rabat_mm": R,
            "contour": contour, "plis": plis}
