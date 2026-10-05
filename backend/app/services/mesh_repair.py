# -*- coding: utf-8 -*-
"""Réparer en un clic — et DIRE ce qui a été fait (tâche #88 PR A, plan-etabli T1, 04/10/2026). Stdlib pure, sans
numpy (absent du runtime embarqué).

TOUT EST UNE RÉÉCRITURE D'INDEX : positions, UV, normales et tangentes restent ceux du fichier ; seul le tableau
d'indices de chaque primitive est refait, puis le document ressort compacté par `mesh_edit._extraire_doc`, comme le
couteau — `mesh_edit` reste la seule plume à GLB.

Cinq actions, dans cet ordre :
  * souder    — même position (à une tolérance relative à la diagonale) ET mêmes attributs : une couture UV n'est
                PAS un sommet confondu, elle reste ;
  * degeneres — triangles à deux positions égales (aire nulle par construction) ;
  * doublons  — même triplet de positions, quel que soit l'enroulement ;
  * normales  — enroulement cohérent par propagation sur les arêtes partagées, puis sens de chaque composante par son
                volume signé, CORRIGÉ du signe de la matrice monde du nœud (une échelle négative inverse le verdict) ;
                le compte est NET : un triangle retourné deux fois ne l'a pas été ;
  * trous     — bords dirigés sans jumelle → boucles → capuchon par les oreilles de `mesh_cut._trianguler`, orienté
                par −Newell de la boucle. DÉCISION DE L'UTILISATEUR (04/10) : DÉCOCHÉ par défaut à l'écran. Une boucle
                de plus de `TROU_MAX` points n'est pas bouchée (la triangulation est quadratique) et c'est DIT ; une
                oreille plate émet son triangle d'aire nulle VOLONTAIREMENT (sans lui l'arête du capuchon n'aurait pas
                de jumelle : jonction en T — voir `_trianguler`).

Un maillage partagé par plusieurs nœuds est réparé UNE fois ; le rapport nomme les nœuds qui le partagent.

BUDGET (plan : 100 352 triangles en moins de 20 s), MESURÉ le 04/10/2026 par tests/mesure_etabli_outils.py : tore de
100 352 triangles 2,1 s (défaut) / 2,4 s (tout) ; modèle réel de 144 274 triangles 3,3 s (11 trous bouchés, toujours
ouvert : des bords qui ne se referment pas seuls — le rapport le dit).
"""
from __future__ import annotations

from app.services.mesh_cut import _ajouter_indices, _base_du_plan, _trianguler
from app.services.mesh_edit import lire_accesseur
from app.services.mesh_edit import (_extraire_doc, _l, _mat_locale, _mat_mul, _monde_des_ancetres, ecrire_glb,
                                    lire_glb)

ACTIONS = ("souder", "doublons", "degeneres", "normales", "trous")
PAR_DEFAUT = ("souder", "doublons", "degeneres", "normales")      # « trous » : coché à la main
_TOL_SOUDURE = 1e-6          # fraction de la diagonale de la pièce
TROU_MAX = 2000              # points d'une boucle au-delà desquels on ne bouche pas (quadratique : ~0,9 s à 2 000)


def _volume(tris):
    return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0 for a, b, c in tris)


def souder(pos, attrs, idx, tol):
    """Indices réécrits vers le PREMIER sommet de même position (à tol) et mêmes attributs. -> (idx, soudés)."""
    vus, rep = {}, list(range(len(pos)))
    for i, p in enumerate(pos):
        k = (tuple(round(c / tol) for c in p),) + tuple(a[i] for a in attrs)
        rep[i] = vus.setdefault(k, i)
    utilises = set(idx)
    return [rep[i] for i in idx], sum(1 for i in utilises if rep[i] != i)


def degeneres(pos, tris):
    ok = [t for t in tris if len({pos[t[0]], pos[t[1]], pos[t[2]]}) == 3]
    return ok, len(tris) - len(ok)


def doublons(pos, tris):
    vus, ok = set(), []
    for t in tris:
        k = frozenset(pos[i] for i in t)
        if k not in vus:
            vus.add(k)
            ok.append(t)
    return ok, len(tris) - len(ok)


def _dirs(pos, t):
    return [(pos[t[e]], pos[t[(e + 1) % 3]]) for e in range(3)]


def _retourne(t):
    return (t[0], t[2], t[1])


def normales(pos, tris, inverse: bool = False):
    """Enroulement cohérent par composante connexe, puis volume signé positif (négatif si `inverse` : la matrice
    monde du nœud a un déterminant négatif). Une arête à plus de deux triangles (non-manifold) propage au premier
    venu. -> (tris, retournés NETS, non_manifold)."""
    tris, adj = [tuple(t) for t in tris], {}
    for n, t in enumerate(tris):
        for (a, b) in _dirs(pos, t):
            adj.setdefault(frozenset((a, b)), []).append(n)
    non_manifold = sum(1 for v in adj.values() if len(v) > 2)
    flip = [False] * len(tris)
    vus = [False] * len(tris)
    for depart in range(len(tris)):
        if vus[depart]:
            continue
        comp, pile, vus[depart] = [], [depart], True
        while pile:
            n = pile.pop()
            comp.append(n)
            for (a, b) in _dirs(pos, tris[n]):
                for m in adj[frozenset((a, b))]:
                    if vus[m] or m == n:
                        continue
                    if (a, b) in _dirs(pos, tris[m]):           # même sens sur l'arête partagée = incohérent
                        tris[m] = _retourne(tris[m])
                        flip[m] = not flip[m]
                    vus[m] = True
                    pile.append(m)
        v = _volume([tuple(pos[i] for i in tris[n]) for n in comp])
        if (v < 0) != inverse and v != 0:
            for n in comp:
                tris[n] = _retourne(tris[n])
                flip[n] = not flip[n]
    return tris, sum(flip), non_manifold


def trous(pos, tris, maxi: int = TROU_MAX):
    """-> (triangles ajoutés, rapport). Boucle = suite de bords dirigés a→b sans jumelle b→a ; un sommet à deux
    sorties est une JONCTION, dite et non bouchée."""
    ar = set()
    for t in tris:
        for e in _dirs(pos, t):
            ar.add(e)
    premier = {}
    for t in tris:
        for i in t:
            premier.setdefault(pos[i], i)
    suivant, sorties = {}, {}
    for (a, b) in ar:
        if (b, a) not in ar:
            sorties[a] = sorties.get(a, 0) + 1
            suivant[a] = b
    jonctions = {a for a, v in sorties.items() if v > 1}
    ajout, vus = [], set()
    r = {"bouches": 0, "non_bouches": 0, "triangles": 0, "raisons": [], "jonctions": len(jonctions)}
    for a0 in sorted(suivant):
        if a0 in vus:
            continue
        boucle, cur = [], a0
        while cur in suivant and cur not in vus:
            vus.add(cur)
            boucle.append(cur)
            cur = suivant[cur]
        if cur != a0 or len(boucle) < 3 or any(p in jonctions for p in boucle):
            r["non_bouches"] += 1
            r["raisons"].append(f"bord de {len(boucle)} point(s) qui ne se referme pas seul (jonction ou chaîne ouverte)")
            continue
        if len(boucle) > maxi:
            r["non_bouches"] += 1
            r["raisons"].append(f"boucle de {len(boucle)} points (plus de {maxi}) : trop longue pour la boucher ici")
            continue
        nw = [0.0, 0.0, 0.0]                                       # −Newell : la normale SORTANTE du capuchon
        for i in range(len(boucle)):
            p, q = boucle[i - 1], boucle[i]
            nw[0] -= (p[1] - q[1]) * (p[2] + q[2])
            nw[1] -= (p[2] - q[2]) * (p[0] + q[0])
            nw[2] -= (p[0] - q[0]) * (p[1] + q[1])
        ln = (nw[0] ** 2 + nw[1] ** 2 + nw[2] ** 2) ** 0.5
        if ln < 1e-24:
            r["non_bouches"] += 1
            r["raisons"].append("boucle d'aire nulle")
            continue
        n = (nw[0] / ln, nw[1] / ln, nw[2] / ln)
        e1, e2 = _base_du_plan(n)
        plan = [(p[0] * e1[0] + p[1] * e1[1] + p[2] * e1[2], p[0] * e2[0] + p[1] * e2[1] + p[2] * e2[2]) for p in boucle]
        t = _trianguler(plan)
        if t is None:
            r["non_bouches"] += 1
            r["raisons"].append(f"boucle de {len(boucle)} points non triangulable (gauche ou auto-intersectée)")
            continue
        # −Newell de la boucle (qui suit les bords de la surface) EST la normale sortante du capuchon, et
        # `_trianguler` rend toujours un enroulement direct dans (e1, e2) : aucun retournement à décider ici.
        cap = [(premier[boucle[i]], premier[boucle[j]], premier[boucle[k]]) for i, j, k in t]
        ajout += cap
        r["bouches"] += 1
        r["triangles"] += len(cap)
    return ajout, r


def _ferme(pos, tris):
    c = {}
    for t in tris:
        for (a, b) in _dirs(pos, t):
            k = (a, b) if a <= b else (b, a)
            c[k] = c.get(k, 0) + 1
    return all(v == 2 for v in c.values())


def _det3(m: list) -> float:
    """Déterminant de la partie 3×3 d'une matrice glTF colonne-majeure."""
    a, b, c = m[0], m[4], m[8]
    d, e, f = m[1], m[5], m[9]
    g, h, i = m[2], m[6], m[10]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def reparer(data: bytes, noeuds=None, actions=None):
    """(glb, rapport). `noeuds` None = toutes les pièces de la scène active ; `actions` None = PAR_DEFAUT."""
    from app.services import print3d
    actions = list(PAR_DEFAUT) if actions is None else list(actions)
    if not actions:
        raise ValueError("aucune action de réparation demandée")
    for a in actions:
        if a not in ACTIONS:
            raise ValueError(f"action inconnue : {a} (attendu {', '.join(ACTIONS)})")
    doc, binc = lire_glb(data)
    for ext in doc.get("extensionsRequired") or []:
        if ext in print3d._REFUS_EXTENSIONS:
            raise ValueError(print3d._REFUS_EXTENSIONS[ext])
    nodes = _l(doc, "nodes")
    scenes = doc.get("scenes") or [{"nodes": list(range(len(nodes)))}]
    racines = list(scenes[int(doc.get("scene", 0) or 0)].get("nodes") or [])
    dans, pile = [], list(racines)
    while pile:
        i = pile.pop()
        if i in dans or not (0 <= i < len(nodes)):
            continue
        dans.append(i)
        pile.extend(_l(nodes[i], "children"))
    if noeuds is None:
        cibles = sorted(i for i in dans if nodes[i].get("mesh") is not None)
    else:
        cibles = sorted({int(x) for x in noeuds})
        for i in cibles:
            if not (0 <= i < len(nodes)) or nodes[i].get("mesh") is None:
                raise ValueError(f"noeud {i} sans maillage — rien à réparer")
    if not cibles:
        raise ValueError("aucune pièce à réparer dans la scène active")
    tampon, rapport = bytearray(binc), {"actions": actions, "pieces": []}
    ferme_avant = ferme_apres = True
    faits = set()
    for i in cibles:
        mi = nodes[i]["mesh"]
        partage = sorted(j for j in range(len(nodes)) if j != i and nodes[j].get("mesh") == mi)
        piece = {"noeud_avant": i, "nom": nodes[i].get("name") or f"noeud_{i}", "soudes": 0, "doublons": 0,
                 "degeneres": 0, "retournes": 0, "non_manifold": 0, "trous": None, "partage_avec": partage,
                 "deja_repare": mi in faits}
        if mi in faits:                                    # un maillage partagé ne se répare qu'UNE fois
            rapport["pieces"].append(piece)
            continue
        faits.add(mi)
        inverse = _det3(_mat_mul(_monde_des_ancetres(doc, i), _mat_locale(nodes[i]))) < 0
        for pr in _l(_l(doc, "meshes")[mi], "primitives"):
            if pr.get("mode", 4) != 4:
                raise ValueError(f"noeud {i} : primitive non TRIANGLES — hors périmètre")
            attrs = pr.get("attributes") or {}
            if "POSITION" not in attrs:
                raise ValueError(f"noeud {i} : primitive sans POSITION")
            pos = lire_accesseur(doc, binc, attrs["POSITION"])
            autres = [lire_accesseur(doc, binc, attrs[k]) for k in sorted(attrs) if k != "POSITION"]
            idx = ([t[0] for t in lire_accesseur(doc, binc, pr["indices"])] if pr.get("indices") is not None
                   else list(range(len(pos))))
            if not pos:
                continue
            xs, ys, zs = [p[0] for p in pos], [p[1] for p in pos], [p[2] for p in pos]
            diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2 + (max(zs) - min(zs)) ** 2) ** 0.5 or 1.0
            tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]
            ferme_avant = ferme_avant and _ferme(pos, tris)
            if "souder" in actions:
                idx, n = souder(pos, autres, idx, _TOL_SOUDURE * diag)
                piece["soudes"] += n
                tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]
            if "degeneres" in actions:
                tris, n = degeneres(pos, tris)
                piece["degeneres"] += n
            if "doublons" in actions:
                tris, n = doublons(pos, tris)
                piece["doublons"] += n
            if "normales" in actions:
                tris, n, nm = normales(pos, tris, inverse)
                piece["retournes"] += n
                piece["non_manifold"] += nm
            if "trous" in actions:
                ajout, rt = trous(pos, tris)
                tris += ajout
                if piece["trous"] is None:
                    piece["trous"] = rt
                else:
                    piece["trous"] = {k: piece["trous"][k] + rt[k] for k in rt}
            if not tris:
                raise ValueError(f"noeud {i} : plus aucun triangle après réparation — rien n'est écrit")
            ferme_apres = ferme_apres and _ferme(pos, tris)
            pr["indices"] = _ajouter_indices(doc, tampon, tris)
        rapport["pieces"].append(piece)
    doc["buffers"] = [{"byteLength": len(tampon)}]
    out, neuf, m_node = _extraire_doc(doc, bytes(tampon), racines)
    for piece in rapport["pieces"]:
        piece["noeud_apres"] = m_node.get(piece["noeud_avant"])
    rapport.update({"ferme_avant": ferme_avant, "ferme_apres": ferme_apres})
    return ecrire_glb(out, neuf), rapport
