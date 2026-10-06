# -*- coding: utf-8 -*-
"""Les connecteurs du couteau : téton, cheville, queue d'aronde (tâche T092, plan-etabli T17).

POSÉS APRÈS LA COUPE, sur les deux moitiés que le couteau vient d'écrire, et PAR BOOLÉENS (`mesh_boolean`) : c'est
la seule façon de rendre une femelle FERMÉE. Le dessin du plan retirait les facettes du capuchon sous le cercle puis
ajoutait un prisme : le trou en dents de scie ne rejoignait pas le bord du prisme, et la femelle sortait ouverte.

LES TROIS FORMES, comme OrcaSlicer les fait (wiki « Cut tool », relevé du 02/09) :
  - TÉTON (plug) : la moitié A gagne un cylindre qui entre dans B ; B perd un trou plus large ET plus profond du jeu.
  - CHEVILLE (dowel) : un trou dans CHACUNE des deux moitiés, et une GOUPILLE séparée — une pièce de plus.
  - QUEUE D'ARONDE (dovetail) : le profil (largeur, profondeur) est un trapèze ÉTROIT à la face de coupe et LARGE au
    fond, extrudé DANS le plan de coupe à travers toute la pièce : on l'assemble en la faisant COULISSER, et c'est
    l'élargissement en profondeur qui l'empêche de ressortir selon la normale. (Le plan enfonçait un prisme
    trapézoïdal selon la normale : il ressortait comme il était entré.)

LE SENS : la normale du plan pointe vers A (« a = le côté vers lequel pointe la normale », mesh_cut). Le téton SORT
de A vers −n, donc DANS l'espace de B — le plan le faisait pousser vers +n, dans sa propre moitié.

LE JEU EST PORTÉ PAR LA FEMELLE, jamais par le mâle : deux pièces imprimées à la même cote ne rentrent pas l'une dans
l'autre. Le connecteur est CENTRÉ sur la section (le barycentre du capuchon de A), et refusé s'il n'y tient pas ou si
la moitié qui le reçoit est trop mince pour sa profondeur.

CE QU'IL NE FAIT PAS, ET C'EST DIT : comme tout booléen, les moitiés réécrites perdent matériaux et UV, et leur
couture n'est pas soudée (« Réparer en un clic » la referme).
"""
from __future__ import annotations

import math

from app.services import mesh_boolean, print3d

TYPES = ("teton", "cheville", "aronde")
COTES = 24
ENTREE_ARONDE = 0.6          # la demi-largeur d'entrée de l'aronde, en fraction de son rayon (le fond vaut 1)


def _unit(v, quoi):
    ln = math.sqrt(sum(c * c for c in v))
    if not ln > 1e-12:
        raise ValueError(f"direction : {quoi} ne peut pas être nulle")
    return tuple(float(c) / ln for c in v)


def _croix(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _pt(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _oreilles(poly):
    """Triangulation d'un polygone SIMPLE (convexe ou non) par oreilles : des triplets d'index. Le profil de l'aronde
    est NON convexe (le col rejoint le trapèze par deux sommets rentrants) ; un éventail y débordait du profil — le
    volume restait juste, mais les triangles se recouvraient et le booléen rendait une surface ouverte."""
    aire = sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1]
               for k in range(len(poly)))
    ids = list(range(len(poly))) if aire > 0 else list(range(len(poly)))[::-1]
    tris = []

    def convexe(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 1e-15

    def dedans(p, a, b, c):
        d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        d2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
        d3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
        return d1 >= 0 and d2 >= 0 and d3 >= 0

    garde = 0
    while len(ids) > 3 and garde < 10000:
        garde += 1
        for k in range(len(ids)):
            i0, i1, i2 = ids[k - 1], ids[k], ids[(k + 1) % len(ids)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if not convexe(a, b, c):
                continue
            if any(dedans(poly[j], a, b, c) for j in ids if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            ids.pop(k)
            break
        else:
            raise ValueError("profil de connecteur non simple — triangulation impossible")
    tris.append(tuple(ids))
    return tris


def _extrusion(poly, origine, e1, e2, axe, w0, w1):
    """Le prisme FERMÉ engendré par `poly` (points 2D dans la base e1, e2 autour de `origine`) entre w0 et w1 le
    long de `axe`. Normales sortantes : l'enroulement est corrigé par le signe du volume.

    Le profil est d'abord mis dans le sens TRIGONOMÉTRIQUE : les faces des bouts (oreilles) le sont toujours, et des
    côtés tournés dans l'autre sens donnaient un solide incohérent — 1,28 de volume au lieu de 3,84, mesuré le 06/10."""
    if sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1]
           for k in range(len(poly))) < 0:
        poly = list(reversed(poly))
    m = len(poly)
    bas = [tuple(origine[c] + s * e1[c] + t * e2[c] + w0 * axe[c] for c in range(3)) for (s, t) in poly]
    haut = [tuple(origine[c] + s * e1[c] + t * e2[c] + w1 * axe[c] for c in range(3)) for (s, t) in poly]
    tris = []
    for k in range(m):
        k2 = (k + 1) % m
        tris += [(bas[k], bas[k2], haut[k2]), (bas[k], haut[k2], haut[k])]
    for (i, j, k) in _oreilles(poly):
        tris += [(bas[i], bas[k], bas[j]), (haut[i], haut[j], haut[k])]
    if mesh_boolean._volume(tris) < 0:
        tris = [(a, c, b) for (a, b, c) in tris]
    return tris


def _cercle(r):
    return [(r * math.cos(2 * math.pi * k / COTES), r * math.sin(2 * math.pi * k / COTES)) for k in range(COTES)]


def _base(n):
    """Deux directions du plan de coupe. `u` est la projection de l'axe monde le moins aligné avec la normale —
    déterministe, et c'est l'axe le long duquel l'aronde coulisse."""
    ax = min(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)), key=lambda a: abs(_pt(a, n)))
    u = _unit(tuple(ax[c] - _pt(ax, n) * n[c] for c in range(3)), "l'axe du plan")
    return u, _croix(n, u)


def _capuchon(tris, n, d0, tol):
    """Les triangles de A posés SUR le plan de coupe (son capuchon) : le barycentre de la section, et ses triangles."""
    cap = [t for t in tris if all(abs(_pt(n, p) - d0) <= tol for p in t)]
    aire, g = 0.0, [0.0, 0.0, 0.0]
    for (a, b, c) in cap:
        s = 0.5 * math.sqrt(sum(x * x for x in _croix(tuple(b[i] - a[i] for i in range(3)),
                                                         tuple(c[i] - a[i] for i in range(3)))))
        aire += s
        for i in range(3):
            g[i] += s * (a[i] + b[i] + c[i]) / 3.0
    if aire <= 0:
        return None, cap
    return tuple(x / aire for x in g), cap


def _dans_section(p2, cap2, tol):
    """Un point 2D (dans la base u, v) est-il dans un des triangles 2D de la section ?"""
    x, y = p2
    for (a, b, c) in cap2:
        e1 = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        e2 = (c[0] - b[0]) * (y - b[1]) - (c[1] - b[1]) * (x - b[0])
        e3 = (a[0] - c[0]) * (y - c[1]) - (a[1] - c[1]) * (x - c[0])
        if (e1 >= -tol and e2 >= -tol and e3 >= -tol) or (e1 <= tol and e2 <= tol and e3 <= tol):
            return True
    return False


def poser(data: bytes, noeud_a: int, noeud_b: int, point, normale, type_: str,
          rayon: float, hauteur: float, jeu: float):
    """Pose un connecteur entre les deux moitiés `noeud_a` (côté +normale) et `noeud_b` d'une coupe. Rend (GLB,
    rapport) ; les autres pièces du document suivent, chacune son nœud."""
    if type_ not in TYPES:
        raise ValueError(f"type de connecteur « {type_} » — {', '.join(TYPES)} sont attendus")
    if not all(isinstance(i, int) and not isinstance(i, bool) and i >= 0 for i in (noeud_a, noeud_b)) \
            or noeud_a == noeud_b:
        raise ValueError("un connecteur relie exactement deux nœuds distincts — les deux moitiés de la coupe")
    for nom, val in (("rayon", rayon), ("hauteur", hauteur)):
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val <= 0:
            raise ValueError(f"{nom} : un nombre fini > 0 est attendu")
    if not isinstance(jeu, (int, float)) or isinstance(jeu, bool) or not math.isfinite(jeu) or jeu < 0:
        raise ValueError("jeu : un nombre fini ≥ 0 est attendu")
    rayon, hauteur, jeu = float(rayon), float(hauteur), float(jeu)
    n = _unit(normale, "la normale du plan")
    o = tuple(float(c) for c in point)
    d0 = _pt(n, o)

    doc = print3d._chunks(data)[0]
    nodes = doc.get("nodes") or []
    for i in (noeud_a, noeud_b):
        if i >= len(nodes) or "mesh" not in nodes[i]:
            raise ValueError(f"nœud {i} : aucun maillage à connecter")
    ta, tb = print3d.lire_glb_triangles(data, [noeud_a]), print3d.lire_glb_triangles(data, [noeud_b])
    tous = [p for t in ta + tb for p in t]
    etendue = max(max(p[i] for p in tous) - min(p[i] for p in tous) for i in range(3)) or 1.0
    tol = 1e-6 * etendue
    centre, cap = _capuchon(ta, n, d0, tol)
    if centre is None:
        raise ValueError("aucun capuchon de A sur ce plan — un connecteur se pose sur la version que le couteau "
                         "vient d'écrire, capuchons posés")
    u, v = _base(n)
    cap2 = [tuple((_pt(tuple(p[c] - centre[c] for c in range(3)), u), _pt(tuple(p[c] - centre[c] for c in range(3)), v))
                  for p in t) for t in cap]
    # profondeurs disponibles de part et d'autre du plan
    prof_b = max(d0 - _pt(n, p) for t in tb for p in t)
    prof_a = max(_pt(n, p) - d0 for t in ta for p in t)
    delta = min(0.25 * hauteur, 0.25 * prof_a)                  # le chevauchement DANS l'autre moitié : il soude
    w0, w1 = ENTREE_ARONDE * rayon, rayon

    if type_ == "aronde":
        if w1 <= w0 + jeu:
            raise ValueError(f"jeu {jeu:g} trop grand pour cette queue d'aronde : le fond du tenon ({w1:g}) doit "
                             f"rester plus large que l'entrée de la rainure ({w0 + jeu:g}) — sans quoi elle ne retient "
                             "rien")
        empreinte = [(0.0, -(w1 + jeu)), (0.0, w1 + jeu), (0.0, 0.0)]
        besoin_b = hauteur + jeu
    else:
        empreinte = [(0.0, 0.0)] + _cercle(rayon + jeu)
        besoin_b = hauteur / 2 + jeu if type_ == "cheville" else hauteur + jeu
    if not all(_dans_section(p, cap2, 1e-9 * etendue * etendue) for p in empreinte):
        raise ValueError(f"le connecteur ne tient pas dans la section — rayon {rayon:g} (+ jeu {jeu:g}) déborde de la "
                         "face de coupe. Réduis le rayon.")
    if prof_b < besoin_b + jeu or (type_ == "cheville" and prof_a < besoin_b + jeu):
        raise ValueError(f"la moitié qui reçoit le connecteur est trop mince : {min(prof_a, prof_b):g} de profondeur "
                         f"pour {besoin_b:g} de trou. Réduis la hauteur.")

    MB = mesh_boolean.operer
    pieces = []
    if type_ == "teton":
        tenon = _extrusion(_cercle(rayon), centre, u, v, n, -hauteur, delta)
        trou = _extrusion(_cercle(rayon + jeu), centre, u, v, n, -(hauteur + jeu), delta)
        na, nb = MB(ta, tenon, "union"), MB(tb, trou, "difference")
        roles = [("male", noeud_a, ta, na), ("femelle", noeud_b, tb, nb)]
        goupille = None
    elif type_ == "cheville":
        moitie = hauteur / 2
        na = MB(ta, _extrusion(_cercle(rayon + jeu), centre, u, v, n, -delta, moitie + jeu), "difference")
        nb = MB(tb, _extrusion(_cercle(rayon + jeu), centre, u, v, n, -(moitie + jeu), delta), "difference")
        goupille = _extrusion(_cercle(rayon), centre, u, v, n, -moitie, moitie)
        roles = [("femelle", noeud_a, ta, na), ("femelle", noeud_b, tb, nb)]
    else:
        L = 2.0 * etendue                                        # à travers toute la pièce, rognée ensuite
        profil = [(-w0, delta), (w0, delta), (w0, 0.0), (w1, -hauteur), (-w1, -hauteur), (-w0, 0.0)]
        rainure = [(-(w0 + jeu), delta), (w0 + jeu, delta), (w0 + jeu, 0.0), (w1 + jeu, -(hauteur + jeu)),
                   (-(w1 + jeu), -(hauteur + jeu)), (-(w0 + jeu), 0.0)]
        # le profil vit dans le plan (v, n) ; l'extrusion suit u, et passe par le centre
        tenon = _extrusion(profil, centre, v, n, u, -L, L)
        tenon = MB(tenon, MB(ta, tb, "union"), "intersection")   # rogné au contour de la pièce
        na = MB(ta, tenon, "union")
        nb = MB(tb, _extrusion(rainure, centre, v, n, u, -L, L), "difference")
        roles = [("male", noeud_a, ta, na), ("femelle", noeud_b, tb, nb)]
        goupille = None

    for role, i, avant, apres in roles:
        if not apres:
            raise ValueError(f"le connecteur a vidé la pièce « {nodes[i].get('name') or i} » — rien n'en reste")
        pieces.append({"noeud": i, "nom": nodes[i].get("name") or f"nœud {i}", "role": role,
                       "volume_avant": round(mesh_boolean._volume(avant), 9),
                       "volume_apres": round(mesh_boolean._volume(apres), 9)})
    sorties = [(p["nom"], apres) for p, (_r, _i, _av, apres) in zip(pieces, roles)]
    if goupille is not None:
        sorties.append(("cheville", goupille))
        pieces.append({"noeud": None, "nom": "cheville", "role": "goupille",
                       "volume_avant": 0.0, "volume_apres": round(mesh_boolean._volume(goupille), 9)})
    autres = [(nodes[i].get("name") or f"nœud {i}", print3d.lire_glb_triangles(data, [i]))
              for i in range(len(nodes)) if "mesh" in nodes[i] and i not in (noeud_a, noeud_b)]
    sortie = print3d.glb_de_pieces(sorties + autres)
    rapport = {"type": type_, "rayon": rayon, "hauteur": hauteur, "jeu": jeu,
               "centre": [round(c, 9) + 0.0 for c in centre],
               "plan": {"point": list(o), "normale": list(n), "repere": "monde"},
               "pieces": pieces,
               "couture": "sommets non soudés le long des connecteurs — « Réparer en un clic » les referme",
               "matieres": "les moitiés réécrites perdent matériaux, textures et UV"}
    if type_ == "aronde":
        rapport.update({"demi_largeur_entree": w0, "demi_largeur_fond": w1, "coulisse": [round(c, 9) for c in u]})
    return sortie, rapport
