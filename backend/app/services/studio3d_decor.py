# -*- coding: utf-8 -*-
"""t402 (31/10/2026) — Décor › Accessoire : un élément généré dans l'onglet 3D (rocher, caisse, plante…) préparé pour
le décor d'un jeu. Gratuit et local.

`poser` : le pivot AU SOL (le bas de la boîte englobante à y = 0, centré en x et z) et, si demandée, la HAUTEUR RÉELLE
en mètres (mise à l'échelle uniforme). Même mécanique que `mesh_edit.reparer` — un nœud racine NEUF porte la
correction, les transformations existantes ne sont jamais réécrites —, écrite comme une version de plus par la route.
Le haut est Y (convention glTF ; un modèle couché se redresse d'abord dans l'Établi, « Réparer › axe haut »).

`budget` : le préréglage de triangles conseillé par RÔLE de décor (accessoire de premier plan, de fond, végétation
dense…), ramené aux préréglages de l'écran Préparer.
"""
from __future__ import annotations

HAUTEUR_MIN, HAUTEUR_MAX = 0.01, 500.0

# rôle → préréglage de Préparer (mesh_optimize.PRESETS) ; l'écran envoie vers Préparer avec ce préréglage allumé
ROLES = {
    "premier_plan": "detailed",     # 5 000 : un accessoire que la caméra approche
    "decor": "prop",                # 2 500 : un élément de décor courant
    "fond": "small",                # 1 000 : vu de loin
    "foule": "micro",               # 500 : répété des dizaines de fois (cailloux, touffes)
    "heros": "game",                # 10 000 : l'objet central d'une scène
}


def poser(data: bytes, hauteur_m: float | None = None) -> tuple[bytes, dict]:
    """(GLB posé au sol et à la hauteur demandée, mesures avant/après). ValueError pour une hauteur hors bornes ou un
    GLB illisible (compressé : `print3d.lire_glb_triangles` le dit)."""
    from app.services import mesh_edit, print3d
    if hauteur_m is not None:
        if isinstance(hauteur_m, bool) or not isinstance(hauteur_m, (int, float)):
            raise ValueError("hauteur_m attend un nombre de mètres")
        if not HAUTEUR_MIN <= float(hauteur_m) <= HAUTEUR_MAX:
            raise ValueError(f"hauteur_m hors de [{HAUTEUR_MIN}, {HAUTEUR_MAX}] m")
    tris = print3d.lire_glb_triangles(data)
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    h = y1 - y0
    if h <= 0:
        raise ValueError("modèle plat : aucune hauteur à mesurer")
    s = 1.0 if hauteur_m is None else float(hauteur_m) / h
    # p' = s·p + t : le bas à 0, le centre en x et z à 0
    t = [-s * (x0 + x1) / 2.0, -s * y0, -s * (z0 + z1) / 2.0]
    doc, binc = mesh_edit.lire_glb(data)
    ident = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    mesh_edit._envelopper(doc, mesh_edit._matrice(ident, s, t))
    sortie = mesh_edit.ecrire_glb(doc, binc)
    mesures = {"avant": {"hauteur": round(h, 6), "largeur": round(x1 - x0, 6), "profondeur": round(z1 - z0, 6),
                         "bas": round(y0, 6)},
               "apres": {"hauteur": round(h * s, 6), "largeur": round((x1 - x0) * s, 6),
                         "profondeur": round((z1 - z0) * s, 6), "bas": 0.0},
               "echelle": round(s, 9)}
    return sortie, mesures


def budget(role: str) -> dict:
    from app.services import mesh_optimize
    if role not in ROLES:
        raise ValueError(f"rôle inconnu : {role!r} (attendu : {', '.join(ROLES)})")
    p = ROLES[role]
    return {"role": role, "preset": p, "triangles": mesh_optimize.PRESETS[p]}
