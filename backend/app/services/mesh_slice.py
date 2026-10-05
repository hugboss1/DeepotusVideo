# -*- coding: utf-8 -*-
"""Aperçu de tranchage INDICATIF : la section du modèle à N hauteurs (tâche T091, plan-etabli T16).

CE QUE C'EST : l'intersection du maillage avec des plans horizontaux, rendue en SEGMENTS bruts. Pas de chaînage en
contours, pas d'orientation, pas de remplissage, pas de G-code — E1 l'a écarté et c'est le métier du slicer. Ce que
cela donne à voir, un modèle assemblé ne le montre pas : la forme réelle d'une section, et sa longueur (le périmètre
à parcourir à cette hauteur).

DES SEGMENTS ET NON DES CONTOURS, délibérément : chaîner demanderait de décider ce qu'on fait d'une arête non-manifold
ou d'un trou — exactement les défauts que la réparation sert à trouver. Un aperçu qui refuserait de s'afficher sur un
maillage abîmé serait muet au moment où l'on en a le plus besoin. Le viewer dessine des `LineSegments`, qui n'ont
besoin d'aucun ordre.

LE RANGEMENT PAR INTERVALLE EST CE QUI TIENT LE BUDGET : chaque triangle sait entre quelles couches il vit (de son
minimum à son maximum sur l'axe) et n'est testé que contre celles-là. Sans lui, 20 couches coûteraient 20 balayages.
"""
from __future__ import annotations

from app.services.mesh_edit import _l, _mat_locale, _mat_mul, _monde_des_ancetres, lire_accesseur, lire_glb

AXES = {"x": 0, "y": 1, "z": 2}
MAX_COUCHES = 500


def _monde(doc: dict, i: int) -> list:
    """La matrice monde d'un nœud : `_monde_des_ancetres` (garde contre un `children` cyclique) puis la locale —
    aucun calcul de chaîne neuf, `mesh_edit` demande UN SITE pour ce calcul."""
    return _mat_mul(_monde_des_ancetres(doc, i), _mat_locale(_l(doc, "nodes")[i]))


def _appliquer(m, p):
    """Un point par une matrice 4x4 en colonnes (translation comprise)."""
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


def trancher(data: bytes, noeuds, axe: str = "y", nombre: int = 20) -> dict:
    """Rend {axe, hauteur, pas, z_min, couches: [{z, segments, perimetre}]}, en unités du MONDE.

    Les couches sont posées au MILIEU de chaque tranche (`z0 + (k + 0,5)·pas`), jamais sur les faces extrêmes : un
    plan confondu avec la face du dessous rendrait une section dégénérée — le piège que le couteau a déjà payé."""
    from app.services import print3d
    if axe not in AXES:
        raise ValueError(f"axe « {axe} » — x, y ou z sont attendus")
    if not isinstance(nombre, int) or isinstance(nombre, bool) or not 1 <= nombre <= MAX_COUCHES:
        raise ValueError(f"couches : un entier entre 1 et {MAX_COUCHES}")
    a = AXES[axe]
    doc, binc = lire_glb(data)
    for ext in doc.get("extensionsRequired") or []:
        if ext in print3d._REFUS_EXTENSIONS:
            raise ValueError(print3d._REFUS_EXTENSIONS[ext])
    nodes = _l(doc, "nodes")
    cible = None if noeuds is None else {int(n) for n in noeuds}

    tris = []
    for i, nd in enumerate(nodes):
        if "mesh" not in nd or (cible is not None and i not in cible):
            continue
        m = _monde(doc, i)
        for prim in _l(doc, "meshes")[nd["mesh"]].get("primitives", []):
            if prim.get("mode", 4) != 4 or "POSITION" not in (prim.get("attributes") or {}):
                continue
            pos = [_appliquer(m, p) for p in lire_accesseur(doc, binc, prim["attributes"]["POSITION"])]
            idx = ([t[0] for t in lire_accesseur(doc, binc, prim["indices"])]
                   if prim.get("indices") is not None else list(range(len(pos))))
            for k in range(0, len(idx) - 2, 3):
                tris.append((pos[idx[k]], pos[idx[k + 1]], pos[idx[k + 2]]))
    if not tris:
        raise ValueError("aucun triangle à trancher dans la sélection")

    zmin = min(min(t[0][a], t[1][a], t[2][a]) for t in tris)
    zmax = max(max(t[0][a], t[1][a], t[2][a]) for t in tris)
    hauteur = zmax - zmin
    if hauteur <= 0:
        raise ValueError("le modèle est plat sur cet axe — rien à trancher")
    pas = hauteur / nombre
    plans = [zmin + (k + 0.5) * pas for k in range(nombre)]

    # LE RANGEMENT : chaque triangle dans les seules couches qu'il traverse
    seaux: list[list] = [[] for _ in range(nombre)]
    for t in tris:
        lo = min(t[0][a], t[1][a], t[2][a])
        hi = max(t[0][a], t[1][a], t[2][a])
        k0 = max(0, int((lo - zmin) / pas - 0.5))
        k1 = min(nombre - 1, int((hi - zmin) / pas + 0.5))
        for k in range(k0, k1 + 1):
            if lo <= plans[k] <= hi:
                seaux[k].append(t)

    couches = []
    for k, z in enumerate(plans):
        segments, perimetre = [], 0.0
        for t in seaux[k]:
            pts = []
            for e in range(3):
                p, q = t[e], t[(e + 1) % 3]
                dp, dq = p[a] - z, q[a] - z
                if (dp > 0) == (dq > 0) or dp == dq:
                    continue
                f = dp / (dp - dq)
                pts.append(tuple(round(p[c] + (q[c] - p[c]) * f, 6) for c in range(3)))
            if len(pts) == 2:
                segments.append([list(pts[0]), list(pts[1])])
                perimetre += sum((pts[0][c] - pts[1][c]) ** 2 for c in range(3)) ** 0.5
        couches.append({"z": round(z, 6), "segments": segments, "perimetre": round(perimetre, 6)})
    return {"axe": axe, "hauteur": round(hauteur, 6), "pas": round(pas, 6), "z_min": round(zmin, 6),
            "couches": couches}
