# -*- coding: utf-8 -*-
"""t440 (lot M7 « Méthodes », 08/11/2026) — les contrôles LOCAUX de l'agent métier ARTISTE 2D DE JEU (méthodes
iso-cycles, scroll-courier, crimson-tower, pit-tactics, wang-tiles : « les modèles d'image ignorent la grille de
pixels », « égaliser taille et vitesse entre les directions »). Pillow seul, gratuits, sans réseau :

  analyser_pixel_art(chemin)                     la grille réelle (taille du bloc de pixels), le nombre de couleurs,
                                                 la transparence, et les verdicts « grille nette » / « palette tenue » ;
  verifier_planche(chemin, colonnes, lignes)     une planche de sprites découpée en cases : par case la boîte du sujet
                                                 (pixels non transparents), puis la dispersion de la HAUTEUR, de la
                                                 LIGNE DE SOL et du CENTRE — un cycle qui « saute » ou « grandit » se voit.
"""
from __future__ import annotations

import math
from collections import Counter

from app.services import briques as BR

MAX_COTE = 4096
PALETTE_MAX = 64          # au-delà, ce n'est plus une palette de pixel art tenue
ALPHA_SEUIL = 16


def _ouvrir(chemin: str):
    from PIL import Image
    p = BR.confiner(chemin)
    if BR.nature(p) != "image":
        raise ValueError("Ce contrôle porte sur une image.")
    with Image.open(p) as im:
        if max(im.size) > MAX_COTE:
            raise ValueError("Image trop grande pour ce contrôle (4096 px au plus).")
        return p, im.convert("RGBA")


def _runs(ligne: list) -> list[int]:
    out, n = [], 1
    for a, b in zip(ligne, ligne[1:]):
        if a == b:
            n += 1
        else:
            out.append(n)
            n = 1
    out.append(n)
    return out


def taille_bloc(im) -> int:
    """PUR — la taille du bloc de pixels : le PGCD des longueurs de plages de couleurs identiques, lignes et colonnes
    échantillonnées (1 = pas de grille agrandie). Les plages des bords (coupées) sont ignorées."""
    w, h = im.size
    px = im.load()
    g = 0
    pas_y = max(1, h // 48)
    pas_x = max(1, w // 48)
    for y in range(0, h, pas_y):
        r = _runs([px[x, y] for x in range(w)])
        for v in r[1:-1]:
            g = math.gcd(g, v)
    for x in range(0, w, pas_x):
        r = _runs([px[x, y] for y in range(h)])
        for v in r[1:-1]:
            g = math.gcd(g, v)
    return g or 1


def analyser_pixel_art(chemin: str) -> dict:
    p, im = _ouvrir(chemin)
    w, h = im.size
    couleurs = Counter(im.getdata())
    opaques = [c for c in couleurs if c[3] >= ALPHA_SEUIL]
    alpha = Counter(c[3] for c in couleurs)
    partiel = sum(n for a, n in alpha.items() if ALPHA_SEUIL <= a < 240) if alpha else 0
    bloc = taille_bloc(im)
    return {"chemin": str(p.relative_to(BR.racine())).replace("\\", "/"), "taille": [w, h], "bloc_px": bloc,
            "grille_logique": [w // bloc, h // bloc], "couleurs": len(opaques),
            "transparence": any(c[3] < ALPHA_SEUIL for c in couleurs),
            "pixels_semi_transparents": partiel,
            "grille_nette": bloc > 1, "palette_tenue": len(opaques) <= PALETTE_MAX,
            "conseils": ([] if bloc > 1 else ["aucune grille agrandie : pixelise sur une grille exacte (outil, pas modèle)"])
                        + ([] if len(opaques) <= PALETTE_MAX else [f"{len(opaques)} couleurs : réduis la palette"])
                        + ([] if not partiel else ["des pixels semi-transparents : bords à durcir (alpha 0 ou 255)"])}


def _ecart(vals: list[float]) -> float:
    if not vals:
        return 0.0
    m = sum(vals) / len(vals)
    return round(math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)), 2)


def verifier_planche(chemin: str, colonnes: int, lignes: int) -> dict:
    """{cases: [{i, boite, hauteur, sol, centre_x} | {i, vide}], hauteur/sol/centre: {min, max, ecart_type},
    verdict} ; « stable » si hauteur, sol et centre bougent de 2 px LOGIQUES au plus (2 × le bloc) : le rebond d'un
    pixel d'une marche est normal, un saut de trois ne l'est pas."""
    p, im = _ouvrir(chemin)
    if not (isinstance(colonnes, int) and isinstance(lignes, int)) or not (1 <= colonnes <= 64 and 1 <= lignes <= 64):
        raise ValueError("Colonnes et lignes : de 1 à 64.")
    w, h = im.size
    if w % colonnes or h % lignes:
        raise ValueError(f"La planche ({w}x{h}) ne se découpe pas en {colonnes}x{lignes} cases égales.")
    cw, ch = w // colonnes, h // lignes
    bloc = taille_bloc(im)
    alpha = im.getchannel("A").point(lambda a: 255 if a >= ALPHA_SEUIL else 0)
    cases, hs, sols, cxs = [], [], [], []
    for j in range(lignes):
        for i in range(colonnes):
            b = alpha.crop((i * cw, j * ch, (i + 1) * cw, (j + 1) * ch)).getbbox()
            n = j * colonnes + i
            if not b:
                cases.append({"i": n, "vide": True})
                continue
            hauteur, sol, cx = b[3] - b[1], b[3], (b[0] + b[2]) / 2
            cases.append({"i": n, "boite": list(b), "hauteur": hauteur, "sol": sol, "centre_x": cx})
            hs.append(hauteur); sols.append(sol); cxs.append(cx)
    if not hs:
        raise ValueError("Planche vide : aucune case n'a de pixel opaque (le fond doit être transparent).")
    tol = 2 * max(1, bloc)
    stats = {k: {"min": min(v), "max": max(v), "ecart_type": _ecart(v)} for k, v in
             (("hauteur", hs), ("sol", sols), ("centre_x", cxs))}
    problemes = [k for k, s in stats.items() if s["max"] - s["min"] > tol]
    return {"chemin": str(p.relative_to(BR.racine())).replace("\\", "/"), "case": [cw, ch], "bloc_px": bloc,
            "cases": cases[:400], "vides": sum(1 for c in cases if c.get("vide")), "stats": stats,
            "tolerance_px": tol, "verdict": "stable" if not problemes else "instable", "problemes": problemes}
