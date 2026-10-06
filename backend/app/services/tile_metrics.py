# -*- coding: utf-8 -*-
"""Mesures des jeux de tuiles (plan 2026-09-03-plan-tuiles, P4). T2 (tâche t113)
n'en posait que le RACCORD des paires légales ; la T7 (tâche t115) ajoute la RÉPÉTITION et l'ÉCLAIRAGE, chacun
avec son seuil NOMMÉ et ses témoins exécutés (voir SEUILS)."""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageStat

from app.services import tile_ops as TO


def seam_pair(a, b, sens: str) -> float:
    """Raccord 0-100 entre le bord de `a` et le bord OPPOSÉ de `b`.
    `sens` = 'E' (droite de a contre gauche de b) ou 'S' (bas contre haut)."""
    A, B = a.convert("RGB"), b.convert("RGB")
    w, h = A.size
    if sens == "E":
        x, y = A.crop((w - 1, 0, w, h)), B.crop((0, 0, 1, h))
    elif sens == "S":
        x, y = A.crop((0, h - 1, w, h)), B.crop((0, 0, w, 1))
    else:
        raise ValueError(f"sens inconnu: {sens!r} (attendu 'E' ou 'S')")
    d = ImageStat.Stat(ImageChops.difference(x, y)).mean
    return round(sum(d) / len(d) / 255 * 100, 2)


def paires_legales(jeu: dict, sens: str):
    """Les couples d'index (ia, ib) dont les tuiles PEUVENT se toucher par
    `sens` : a doit porter le bit qui pointe vers b, et b le bit inverse."""
    bit_a, bit_b = (TO.E, TO.W) if sens == "E" else (TO.S, TO.N)
    v = jeu["variantes"]
    for i, ma in enumerate(jeu["cles"]):
        if not (ma & bit_a):
            continue
        for j, mb in enumerate(jeu["cles"]):
            if not (mb & bit_b):
                continue
            for ka in range(v):
                for kb in range(v):
                    yield i * v + ka, j * v + kb


def raccord_jeu(jeu: dict) -> float:
    """LE chiffre de P1 : le PIRE raccord parmi toutes les paires légales.

    MESURÉ le 06/10/2026 : la boucle naïve (seam_pair par paire) prenait 60 s pour
    236 tuiles de 512 px (57 800 paires). Or les bords ne dépendent que des arêtes
    et les variantes ne touchent que le cœur : les bandes de bord se RÉPÈTENT. On
    découpe donc chaque bande une fois, et on ne mesure chaque COUPLE de bandes
    distinctes qu'une fois — même chiffre au centième (banc
    test_raccord_du_jeu_exact_et_rapide), en une fraction de seconde."""
    tuiles = jeu["tuiles"]
    pire = 0.0
    for sens in ("E", "S"):
        bandes_a, bandes_b, vus = {}, {}, {}

        def bande(cache, i, cote_a):
            if i not in cache:
                t = tuiles[i].convert("RGB")
                w, h = t.size
                if sens == "E":
                    box = (w - 1, 0, w, h) if cote_a else (0, 0, 1, h)
                else:
                    box = (0, h - 1, w, h) if cote_a else (0, 0, w, 1)
                im = t.crop(box)
                cache[i] = (im.tobytes(), im)
            return cache[i]

        for ia, ib in paires_legales(jeu, sens):
            ka, xa = bande(bandes_a, ia, True)
            kb, xb = bande(bandes_b, ib, False)
            cle = (ka, kb)
            if cle not in vus:
                d = ImageStat.Stat(ImageChops.difference(xa, xb)).mean
                vus[cle] = round(sum(d) / len(d) / 255 * 100, 2)
            pire = max(pire, vus[cle])
    return round(pire, 2)


# ── les deux autres mesures (P4, tâche t115) ────────────────────────────────────────────────────────────────────────
#: Seuils NOMMÉS, calibrés sur des témoins EXÉCUTÉS avec le python embarqué (03/09, refaits le 06/10 au centième).
SEUILS = {
    #: raccord : le PIRE des paires légales. 0.00 sur un jeu de bruit miroir ; on tolère 1 point pour une matière
    #: au raccord imparfait.
    "raccord": 1.0,
    #: répétition : damier de période 2 → 100.00 (80.31 à 3 variantes) ; tirage auto-tuilé → 15 à 22.
    "repetition": 70.0,
    #: éclairage d'une tuile : aplat → 0.00 ; rampe pleine → 50.78 ; tuiles d'un jeu de bruit → 0.87 au pire.
    "eclairage": 8.0,
    #: écart d'éclairage entre la tuile la plus et la moins marquée du jeu.
    "ecart_eclairage": 5.0,
}


def eclairage_score(img, cellules: int = 8) -> float:
    """Gradient moyen d'éclairage d'une tuile, 0-100.

    La luminance est réduite à `cellules x cellules` par moyennes de blocs (Image.BOX), puis l'on mesure l'écart
    entre les moitiés gauche/droite et haut/bas ; le score est la NORME de ce gradient, normalisée 255 — une rampe
    verticale pèse autant qu'une horizontale, une diagonale s'ajoute en norme. Un éclairage cuit dans la texture se
    voit : rampe pleine 50.78, aplat 0.00, bruit miroir 0.00 (mesurés). Coût : `cote²` octets lus une fois."""
    g = img.convert("L").resize((cellules, cellules), Image.BOX)
    px = list(g.tobytes())           # `getdata` est déprécié depuis Pillow 12
    h = cellules // 2

    def moy(idx):
        return sum(px[i] for i in idx) / len(idx)

    gauche = moy([y * cellules + x for y in range(cellules) for x in range(h)])
    droite = moy([y * cellules + x for y in range(cellules) for x in range(h, cellules)])
    haut = moy([y * cellules + x for y in range(h) for x in range(cellules)])
    bas = moy([y * cellules + x for y in range(h, cellules) for x in range(cellules)])
    return round(math.hypot(gauche - droite, haut - bas) / 255 * 100, 2)


def eclairage_jeu(jeu: dict) -> tuple[float, float, list[dict]]:
    """(max, écart max − min, détail par tuile)."""
    par = [{"index": i, "eclairage": eclairage_score(t)} for i, t in enumerate(jeu["tuiles"])]
    vals = [p["eclairage"] for p in par]
    return round(max(vals), 2), round(max(vals) - min(vals), 2), par


def repetition_score(apercu, cases: int = 8, cote_reduit: int = 32) -> float:
    """Auto-corrélation par DÉCALAGES DE CASES ENTIÈRES sur l'aperçu, 0-100.

    L'aperçu est réduit en niveaux de gris à `cases x cote_reduit` px de côté ; pour chacun des `cases² − 1`
    décalages non nuls (cycliques), l'on mesure la différence absolue moyenne avec l'original. Le score vaut
    `100 x (1 − meilleur / moyenne)` : la normalisation par la moyenne distingue une vraie périodicité d'une simple
    parenté de teinte entre deux matières. 0 = aucun décalage n'apparie mieux que la moyenne ; 100 = un décalage
    apparie EXACTEMENT (damier de période 2 à une variante, ou aplat).

    Coût mesuré : 63 décalages sur 65 536 octets pour 8 x 8 ; 255 sur 262 144 pour 16 x 16, 0,8 s — deux appels PIL
    par décalage, aucun numpy."""
    n = cases * cote_reduit
    g = apercu.convert("L").resize((n, n), Image.BOX)
    ecarts = []
    for cy in range(cases):
        for cx in range(cases):
            if cx == 0 and cy == 0:
                continue
            d = ImageChops.difference(g, ImageChops.offset(g, cx * cote_reduit, cy * cote_reduit))
            ecarts.append(ImageStat.Stat(d).mean[0])
    moyenne = sum(ecarts) / len(ecarts)
    if moyenne <= 1e-6:              # image parfaitement uniforme
        return 100.0
    return round(max(0.0, 1 - min(ecarts) / moyenne) * 100, 2)


def verdict(mesures: dict) -> dict:
    """Un mot par mesure : `ok` ou `attention`. Aucune mesure n'est muette. Le seuil lui-même passe pour le raccord
    et l'éclairage (« au plus »), pas pour la répétition (« sous 70 »)."""
    return {
        "raccord": "ok" if mesures["raccord"] <= SEUILS["raccord"] else "attention",
        "repetition": "ok" if mesures["repetition"] < SEUILS["repetition"] else "attention",
        "eclairage": "ok" if mesures["eclairage_max"] <= SEUILS["eclairage"] else "attention",
        "ecart_eclairage": "ok" if mesures["ecart_eclairage"] <= SEUILS["ecart_eclairage"] else "attention",
    }
