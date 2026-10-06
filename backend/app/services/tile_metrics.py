# -*- coding: utf-8 -*-
"""Mesures des jeux de tuiles (plan 2026-09-03-plan-tuiles, P4). T2 (tâche t113)
n'en pose que le RACCORD des paires légales — le chiffre que la route rend ;
répétition et éclairage viendront avec la T7 du plan."""
from __future__ import annotations

from PIL import ImageChops, ImageStat

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
