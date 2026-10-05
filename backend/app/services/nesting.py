# -*- coding: utf-8 -*-
"""Ranger des empreintes sur un ou plusieurs plateaux (tâche #89 PR C, plan-etabli T5, 05/10/2026) — stdlib pure.

CE N'EST PAS `plaque.rangerEnEtageres`, ET C'EST LE POINT. Les étagères du navigateur étalent pour VOIR : elles ne
connaissent aucun plateau, ne tournent rien et ne débordent nulle part. Ici on range pour IMPRIMER — un plateau borné
(la cote du profil d'imprimante actif), un espacement, la rotation à plat quand elle fait gagner, et le débordement sur
un second plateau plutôt qu'un chevauchement silencieux.

L'ALGORITHME : squelette (« skyline ») bas-gauche. Le plateau est une suite de segments (x, largeur, hauteur) d'abord
plats ; chaque pièce est essayée à l'abscisse de chaque segment, dans ses deux orientations, et l'on retient la pose
dont le SOMMET est le plus bas (puis la plus à gauche). Linéaire en segments, donc mesurable et bornée — ce qu'un
MaxRects n'est pas en Python pur (sa liste de rectangles libres enfle en O(n²)).

L'ESPACEMENT EST PORTÉ PAR LA PIÈCE, pas par le plateau : chaque empreinte est gonflée de `marge` à droite et en haut,
et le plateau de `marge` aussi. Une pièce collée au bord garde sa marge vis-à-vis de ses voisines sans la perdre contre
la paroi.

L'UNITÉ EST CELLE DE L'APPELANT, et la page de l'Établi envoie des UNITÉS DU MODÈLE (le plateau du profil y est
converti par versUnites) : rien ici ne suppose des millimètres.

LES ZONES EXCLUES (la purge de la Centauri Carbon 2, 246–256 × 0–20 mm) : une zone collée au bord AVANT du plateau
(v0 = 0) est posée d'emblée comme une bosse du squelette, marge comprise — aucune pièce n'y entre. Une zone qui ne
touche pas ce bord ne se représente pas dans un squelette : elle est COMPTÉE dans `exclusions_ignorees` et la page le
dit. (Mesuré sur 8799 le 05/10 : sans cela une pièce se posait dans la purge.)
CE QU'IL NE FAIT PAS (dit) : le rangement est rectangulaire (boîtes englobantes), pas au contour vrai.

BUDGET (plan : 500 empreintes en moins de 1 s), MESURÉ par tests/mesure_etabli_outils.py nesting.
"""
from __future__ import annotations

MAX_PIECES = 1000          # borne du budget mesuré
MAX_PLATEAUX = 8


def _piece(p) -> tuple:
    if not isinstance(p, dict) or "cle" not in p:
        raise ValueError("chaque pièce attend `cle`, `l` et `p` (deux nombres > 0)")
    try:
        l, prof = float(p["l"]), float(p["p"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"pièce {p.get('cle')!r} : `l` et `p` attendent deux nombres > 0")
    if not (0 < l < float("inf")) or not (0 < prof < float("inf")):
        raise ValueError(f"pièce {p.get('cle')!r} : `l` et `p` doivent être finis et > 0")
    return p["cle"], l, prof


def _poser(skyline, largeur, profondeur, l, p):
    """La meilleure pose de (l, p) sur ce squelette, ou None. Rend (x, y)."""
    meilleur = None
    for i, (x, _w, _h) in enumerate(skyline):
        if x + l > largeur + 1e-9:
            continue
        reste, y, j = l, 0.0, i
        while reste > 1e-9 and j < len(skyline):
            y = max(y, skyline[j][2])
            reste -= skyline[j][1]
            j += 1
        if reste > 1e-9 or y + p > profondeur + 1e-9:
            continue          # l'empreinte dépasse le dernier segment, ou le fond
        if meilleur is None or (y, x) < (meilleur[1], meilleur[0]):
            meilleur = (x, y)
    return meilleur


def _fusionner(skyline, x, l, sommet):
    """Écrase l'intervalle [x, x+l] à la hauteur `sommet`, puis recolle les segments de même hauteur — sans quoi le
    squelette enflerait sans fin et le budget mesuré serait faux dès la centième pièce."""
    neuf = []
    for (sx, sw, sh) in skyline:
        if sx + sw <= x + 1e-9 or sx >= x + l - 1e-9:
            neuf.append((sx, sw, sh))
            continue
        # une POSE commence toujours au début d'un segment ; une ZONE EXCLUE, elle, tombe n'importe où :
        # le reste à gauche de x se garde aussi
        if sx < x - 1e-9:
            neuf.append((sx, x - sx, sh))
        if sx + sw > x + l + 1e-9:
            neuf.append((x + l, sx + sw - (x + l), sh))
    neuf.append((x, l, sommet))
    neuf.sort(key=lambda s: s[0])
    colle = []
    for s in neuf:
        if colle and abs(colle[-1][2] - s[2]) < 1e-12 and abs(colle[-1][0] + colle[-1][1] - s[0]) < 1e-9:
            colle[-1] = (colle[-1][0], colle[-1][1] + s[1], s[2])
        else:
            colle.append(s)
    return colle


def _squelette_initial(largeur: float, exclusions, m: float) -> tuple:
    """Le squelette d'un plateau neuf, avec ses zones exclues collées au bord avant posées comme des bosses (gonflées de
    la marge). -> (squelette, nombre de zones ignorées)."""
    sq, ignorees = [(0.0, largeur, 0.0)], 0
    for z in exclusions or ():
        u0, v0, u1, v1 = (float(c) for c in z)
        if v0 > 1e-9 or u1 <= u0 or v1 <= v0:
            ignorees += 1
            continue
        a, b = max(0.0, u0 - m), min(largeur, u1 + m)
        if b > a:
            sq = _fusionner(sq, a, b - a, v1 + m)
    return sq, ignorees


def ranger(pieces, plateau, marge=2.0, rotation=True, plateaux_max=MAX_PLATEAUX, exclusions=None):
    """Range `pieces` — [{cle, l, p}] — sur des plateaux de `plateau` = (L, P).

    -> {plateaux: [[{cle, u, v, rot, l, p}]], debordent: [cle], taux: [f], marge}. `u`/`v` : le COIN de l'empreinte
    depuis l'origine du plateau ; `rot` vaut 0 ou 90 (RELATIF : la pièce tourne de 90° par rapport à la pose mesurée) ;
    `l`/`p` sont les cotes reçues, non tournées. `exclusions` : rectangles [u0, v0, u1, v1] du plateau à éviter."""
    if not isinstance(pieces, list) or not pieces:
        raise ValueError("aucune pièce à ranger")
    if len(pieces) > MAX_PIECES:
        raise ValueError(f"{len(pieces)} pièces — au-delà de {MAX_PIECES} le rangement dépasse son budget de temps "
                         "mesuré ; range par lots")
    try:
        pl_l, pl_p = float(plateau[0]), float(plateau[1])
    except (IndexError, KeyError, TypeError, ValueError):
        raise ValueError("plateau attend deux nombres > 0 (largeur, profondeur)")
    if not (pl_l > 0) or not (pl_p > 0):
        raise ValueError("plateau attend deux nombres > 0 (largeur, profondeur)")
    try:
        m = float(marge)
    except (TypeError, ValueError):
        raise ValueError("marge attend un nombre ≥ 0")
    if not (m >= 0):
        raise ValueError("marge attend un nombre ≥ 0")
    n_max = max(1, min(MAX_PLATEAUX, int(plateaux_max)))
    zones = []
    for z in exclusions or ():
        try:
            u0, v0, u1, v1 = (float(c) for c in z)
        except (TypeError, ValueError):
            raise ValueError("exclusions attend des rectangles [u0, v0, u1, v1]")
        zones.append((u0, v0, u1, v1))
    initial, ignorees = _squelette_initial(pl_l + m, zones, m)
    cotes = [_piece(p) for p in pieces]
    ordre = sorted(cotes, key=lambda c: (-max(c[1], c[2]), -c[1] * c[2]))   # la plus grande dimension d'abord

    plateaux: list = []
    squelettes: list = []
    debordent: list = []
    for cle, l, p in ordre:
        gl, gp = l + m, p + m       # gonflée : l'espacement voyage avec la pièce
        essais = ((0, gl, gp),) + (((90, gp, gl),) if rotation else ())
        pose, k = None, 0
        while pose is None and k <= len(plateaux):
            if k == len(plateaux):
                # INUTILE D'OUVRIR UN PLATEAU DE PLUS quand le dernier est déjà vide : ce qui ne tient pas sur un
                # plateau nu ne tiendra sur aucun autre.
                if len(plateaux) >= n_max or (plateaux and not plateaux[-1]):
                    break
                plateaux.append([])
                squelettes.append(list(initial))
            for rot, a, b in essais:
                trouve = _poser(squelettes[k], pl_l + m, pl_p + m, a, b)
                if trouve and (pose is None or trouve[1] < pose[1]):
                    pose = (trouve[0], trouve[1], rot, a, b, k)
            k += 1
        if pose is None:
            debordent.append(cle)
            continue
        x, y, rot, a, b, k = pose
        squelettes[k] = _fusionner(squelettes[k], x, a, y + b)
        plateaux[k].append({"cle": cle, "u": x, "v": y, "rot": rot, "l": l, "p": p})
    while plateaux and not plateaux[-1]:
        plateaux.pop()
    aire = pl_l * pl_p
    taux = [round(sum(q["l"] * q["p"] for q in pk) / aire, 4) for pk in plateaux]
    return {"plateaux": plateaux, "debordent": debordent, "taux": taux, "marge": m, "exclusions_ignorees": ignorees}
