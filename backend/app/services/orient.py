# -*- coding: utf-8 -*-
"""Auto-orient : PROPOSER des poses, classées, et laisser l'utilisateur trancher (tâche T092, plan-etabli T19).

CE MODULE N'ÉCRIT RIEN, et ce n'est pas une timidité. Le wiki d'OrcaSlicer (vérifié le 05/10/2026) l'écrit de son
propre outil : « Auto Orientation may not always find the best orientation for complex models. » Aucun score ne sait
quelle face l'utilisateur veut voir belle. On rend donc TROIS poses avec leurs chiffres, et c'est l'assise —
`mesh_edit.assise`, éprouvée depuis le lot B — qui applique celle qu'il choisit.

LES CANDIDATS SONT LES NORMALES DU MODÈLE, regroupées : une face pose sur le plateau, les directions qui valent la
peine d'être essayées sont celles des faces, regroupées par direction arrondie et pondérées par leur aire, plus les
six axes. Leur nombre est BORNÉ (`MAX_POSES`) quelle que soit la finesse du maillage : c'est ce qui rend le coût
prévisible (poses × sommets).

LA CONVENTION DE `bas` : la direction, dans le repère du modèle, qui regardera le plateau. Le point le plus BAS d'une
pose est donc celui qui va le plus loin DANS cette direction — le MAXIMUM de p·bas (le dessin du plan prenait le
minimum : il cherchait le plateau au plafond). Et `rotation`, la normale à envoyer à l'assise, EST `bas` : l'assise
amène la normale donnée vers (0, −1, 0) — le plan envoyait −bas, qui aurait posé la pièce sur la face opposée.

LES QUATRE CRITÈRES, ceux que le wiki nomme, avec des poids ÉCRITS ici et non cachés dans une formule :
  - surplomb : la part de la surface qui regarde le bas à moins de 45° de l'horizontale, en l'air (le pire) ;
  - contact : la part de la surface posée à plat sur le plateau (le meilleur) ;
  - compacité de l'appui : périmètre² / (4π·aire) — 1 pour un disque, beaucoup plus pour une bande fine, qui décolle.
    (Le plan prenait √aire, ce qui pénalisait un GRAND appui et contredisait le critère précédent.) ;
  - hauteur rapportée à la diagonale : une pièce haute vibre et dure plus longtemps.
"""
from __future__ import annotations

import math

from app.services import print3d

MAX_POSES = 64
MAX_TRIS = 400_000
SEUIL_SURPLOMB = 45.0        # degrés depuis l'horizontale (convention Prusa / OrcaSlicer)
QUANTUM = 12.0               # finesse du regroupement des directions, en degrés
# L'APPUI EST UNE BANDE, pas un plan : un modèle organique n'a AUCUNE face exactement à plat (mesuré le 05/10 sur le
# modèle réel 8ed6d533 : 0 % d'appui à toutes les poses avec un critère exact). Compte comme appui une face qui
# regarde le bas à moins de APPUI_ANGLE degrés, entièrement dans les APPUI_BANDE (fraction de la diagonale) du fond —
# l'épaisseur d'une première couche sur une pièce de quelques centimètres.
APPUI_ANGLE = 25.0
APPUI_BANDE = 0.005
# LES POIDS, ÉCRITS : ils se lisent et se discutent, ils ne se devinent pas. Un score plus BAS est meilleur.
POIDS = {"surplomb": 1.0, "contact": -0.6, "compacite": 0.15, "hauteur": 0.05}
_AXES = ((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, -1.0))


def _preparer(tris):
    """Sommets dédoublonnés (une projection par sommet et par pose, pas trois par triangle), et pour chaque triangle
    ses trois index, sa normale unitaire et son aire. Les triangles d'aire nulle n'ont pas de direction : écartés."""
    index, sommets, faces = {}, [], []
    for t in tris:
        a, b, c = t
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        d = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        if d < 1e-20:
            continue
        ids = []
        for p in t:
            k = index.get(p)
            if k is None:
                k = index[p] = len(sommets)
                sommets.append(p)
            ids.append(k)
        faces.append((ids[0], ids[1], ids[2], n[0] / d, n[1] / d, n[2] / d, d / 2.0))
    return sommets, faces


def _poses(faces):
    """Les directions candidates : les normales regroupées par direction arrondie, pondérées par l'aire, les plus
    « portantes » d'abord, plus les six axes. Au plus MAX_POSES."""
    pas = math.radians(QUANTUM)
    seaux: dict = {}
    for (_i, _j, _k, nx, ny, nz, aire) in faces:
        cle = (round(nx / pas), round(ny / pas), round(nz / pas))
        s = seaux.get(cle)
        if s is None:
            s = seaux[cle] = [0.0, 0.0, 0.0, 0.0]
        s[0] += aire
        s[1] += nx * aire
        s[2] += ny * aire
        s[3] += nz * aire
    poses = []
    for s in sorted(seaux.values(), key=lambda s: -s[0])[:MAX_POSES - len(_AXES)]:
        d = math.sqrt(s[1] * s[1] + s[2] * s[2] + s[3] * s[3])
        if d > 1e-12:
            poses.append((s[1] / d, s[2] / d, s[3] / d))
    for ax in _AXES:
        if all(p[0] * ax[0] + p[1] * ax[1] + p[2] * ax[2] < 0.999 for p in poses):
            poses.append(ax)
    return poses[:MAX_POSES]


def _perimetre(faces_contact, sommets):
    """Le périmètre de l'appui : les arêtes que UN SEUL triangle d'appui porte (une arête intérieure en a deux)."""
    compte: dict = {}
    for (i, j, k) in faces_contact:
        for a, b in ((i, j), (j, k), (k, i)):
            cle = (a, b) if a < b else (b, a)
            compte[cle] = compte.get(cle, 0) + 1
    total = 0.0
    for (a, b), n in compte.items():
        if n == 1:
            p, q = sommets[a], sommets[b]
            total += math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2)
    return total


def _noter(sommets, faces, bas, diag):
    bx, by, bz = bas
    h = [p[0] * bx + p[1] * by + p[2] * bz for p in sommets]
    hmax, hmin = max(h), min(h)
    tol = max(1e-6 * max(1.0, hmax - hmin), APPUI_BANDE * diag)
    cos_appui = math.cos(math.radians(APPUI_ANGLE))
    cos_seuil = math.cos(math.radians(90.0 - SEUIL_SURPLOMB))     # regarde le bas à moins de 45° de l'horizontale
    surplomb = contact = 0.0
    appui = []
    for (i, j, k, nx, ny, nz, aire) in faces:
        cosn = nx * bx + ny * by + nz * bz
        if cosn <= cos_seuil:
            continue                                   # regarde le ciel, ou assez debout pour se tenir
        if cosn > cos_appui and hmax - h[i] <= tol and hmax - h[j] <= tol and hmax - h[k] <= tol:
            contact += aire                            # dans la bande du fond : il porte
            appui.append((i, j, k))
        else:
            surplomb += aire                           # penché sous le seuil, en l'air
    compacite = (_perimetre(appui, sommets) ** 2 / (4.0 * math.pi * contact)) if contact > 0 else None
    return surplomb, contact, compacite, hmax - hmin


def candidats(data: bytes, noeuds, garder: int = 3) -> dict:
    """Rend {seuil_surplomb, poids, candidats: [{bas, contact, surplomb, part_contact, part_surplomb, compacite,
    hauteur, score, rotation}]}, les meilleurs d'abord, en unités du MODÈLE (aires et longueurs). `rotation` est la
    normale à envoyer telle quelle à `POST /etabli/assise`."""
    tris = print3d.lire_glb_triangles(data, noeuds)
    if len(tris) > MAX_TRIS:
        raise ValueError(f"{len(tris)} triangles — l'orientation automatique est bornée à {MAX_TRIS}. "
                         "Décime d'abord (onglet Fiche → Décimer).")
    sommets, faces = _preparer(tris)
    if not faces:
        raise ValueError("aucun triangle à orienter dans la sélection")
    total = sum(f[6] for f in faces)
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    diag = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2) or 1.0
    out = []
    for bas in _poses(faces):
        surplomb, contact, compacite, hauteur = _noter(sommets, faces, bas, diag)
        terme_compacite = min(1.0, (compacite - 1.0) / 10.0) if compacite is not None else 1.0
        score = (POIDS["surplomb"] * surplomb / total + POIDS["contact"] * contact / total
                 + POIDS["compacite"] * max(0.0, terme_compacite) + POIDS["hauteur"] * hauteur / diag)
        out.append({"bas": [round(c, 6) for c in bas], "contact": round(contact, 9), "surplomb": round(surplomb, 9),
                    "part_contact": round(contact / total, 6), "part_surplomb": round(surplomb / total, 6),
                    "compacite": None if compacite is None else round(compacite, 9),
                    "hauteur": round(hauteur, 9), "score": round(score, 6),
                    "rotation": [round(c, 9) for c in bas]})
    out.sort(key=lambda c: c["score"])
    return {"seuil_surplomb": SEUIL_SURPLOMB, "poids": dict(POIDS),
            "candidats": out[:max(1, min(int(garder), MAX_POSES))]}
