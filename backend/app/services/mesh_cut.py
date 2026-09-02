# -*- coding: utf-8 -*-
"""Le couteau de l'Établi — couper des pièces par un plan, et les REFERMER.

Séparé de mesh_edit.py à la revue du lot B : sept cents lignes de géométrie
pure qui n'ont besoin du socle que pour lire et recoller un GLB, marcher dans
la hiérarchie des nœuds et compacter le document. LA PLUME NE CHANGE PAS DE
MAIN : ce module compose un document et le rend à `mesh_edit.ecrire_glb` —
mesh_edit reste la seule plume à GLB du chantier, et `ecrire_version` le seul
dépôt d'une version.

Stdlib pure, sans numpy, sans `settings` : exécutable au banc sans
environnement, comme le socle. Le format du compte rendu que `couper` rend —
et que la route dépose dans le `source` de la fiche — est décrit en tête de
la section « le couteau », plus bas.
"""
from __future__ import annotations

import struct

from app.services.mesh_edit import (_extraire_doc, _l, _mat_locale, _mat_mul,
                                    _monde_des_ancetres, _parents, _unitaire,
                                    _vecteur3, ecrire_glb, lire_glb)


# ── lecture d'accesseurs : le chemin rapide du couteau ───────────────────────
# `print3d._accessor` déballe élément par élément et suffit à lire des
# triangles ; le couteau relit CHAQUE attribut de la pièce et la réécrit.
# `struct.iter_unpack` sur une vue serrée va UN PEU plus vite — mesuré par la
# revue sur les 72 128 sommets du cadre : 12,4 ms contre 18,1 ms (×1,46, soit
# 6 ms sur les 530 de la coupe), pas « bien plus ». Ce qui justifie un second
# lecteur n'est donc pas la vitesse mais la POLITIQUE : print3d ignore un
# accesseur `sparse` en silence, ici il est refusé en le disant, et le u8 des
# index (5121) est lu. L'unification des deux lecteurs attend le lot qui
# touchera print3d. Le pas explicite (`byteStride`) reste lu élément par
# élément.

_COMPOSANTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
               5125: ("I", 4), 5126: ("f", 4)}
_NB_COMPOSANTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
                  "MAT2": 4, "MAT3": 9, "MAT4": 16}


def _lire_accesseur(doc: dict, binc: bytes, i: int) -> list[tuple]:
    a = _l(doc, "accessors")[i]
    if a.get("sparse"):
        raise ValueError(f"accesseur {i} « sparse » — hors périmètre du couteau")
    if a.get("bufferView") is None:
        raise ValueError(f"accesseur {i} sans bufferView — hors périmètre du "
                         "couteau")
    ct, ty = a["componentType"], a["type"]
    if ct not in _COMPOSANTS or ty not in _NB_COMPOSANTS:
        raise ValueError(f"accesseur {i} : composant {ct} / type {ty} hors "
                         "périmètre")
    fmt, taille = _COMPOSANTS[ct]
    n = _NB_COMPOSANTS[ty]
    bv = _l(doc, "bufferViews")[a["bufferView"]]
    if "uri" in _l(doc, "buffers")[bv.get("buffer", 0)]:
        raise ValueError("buffer externe (uri) — nos GLB sont monolithiques, "
                         "hors périmètre")
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    serre = taille * n
    pas = bv.get("byteStride") or serre
    count = int(a["count"])
    if pas == serre:
        return list(struct.iter_unpack("<" + fmt * n,
                                       binc[base:base + count * serre]))
    f = "<" + fmt * n
    return [struct.unpack_from(f, binc, base + k * pas) for k in range(count)]


# ── le couteau : couper des pièces par un plan, et les REFERMER ──────────────
# La demande : « les outils couteau des slicers ». Le navigateur montre le plan
# et l'aperçu des deux moitiés (clipping three.js, rien n'y est fabriqué) ;
# ICI on coupe pour de vrai, en stdlib pure : chaque triangle traversé est
# découpé (POSITION, NORMAL, TEXCOORD et tout attribut flottant interpolés sur
# l'arête), les deux moitiés sont réparties, et chaque côté est REFERMÉ par un
# capuchon — segments de section → boucles → triangulation par oreilles. Une
# pièce imprimée doit être étanche : c'est tout l'objet de couper avant le
# slicer, et c'est pourquoi un capuchon qu'on ne sait pas poser SE DIT dans
# le compte rendu plutôt que de laisser une géométrie fausse en silence.
#
# CE QUE LE COMPTE RENDU DIT (le `source` de la fiche report.json, d'où
# /api/etabli/productions et l'onglet Établi de la Bibliothèque PEUVENT le
# lire — l'entrée n'en remonte que le nom) — site canonique du format ;
# routes.py n'en porte qu'un renvoi. DEUX ESPACES D'INDEX, NOMMÉS : `_avant`
# est un index de la version COUPÉE (celle que `depuis` désigne), `_apres` un
# index de la version NEUVE, compactée — la lignée a besoin des deux, et un
# même mot pour les deux faisait lire le mauvais nœud (revue : le sol était 1
# dans le compte rendu et 0 dans la version écrite).
#
#   { "outil": "etabli", "operation": "couper",
#     "depuis": { "version": N, "fichier": "model.vN.glb" },  posé par la route
#     "plan": { "point": [x, y, z], "normale": [x, y, z], "repere": "monde" },
#     "garder": "deux" | "a" | "b",   a = le côté vers lequel pointe la normale
#     "noeuds_avant": [i, …],        les index DEMANDÉS, dans la version coupée
#     "pieces": [ { "noeud_avant": i, "nom": "cadre", "triangles": N,
#                   "noeud_apres": null,   le nœud coupé n'existe plus — ou
#                                          l'index du contenant s'il reste
#                   "traversee": true,
#                   "cotes": { "a": { "noeud_apres": j,
#                                     "nom": "cadre_a", "triangles": Na,
#                                     "capuchon": { "pose": true,
#                                                   "triangles": k, "boucles": 1,
#                                                   "degeneres": d }
#                                       d triangles d'aire nulle, émis EXPRÈS
#                                       (une oreille plate, contre la jonction
#                                       en T) — un slicer les signale et les
#                                       répare seul ; on le dit plutôt que de
#                                       le laisser découvrir. Le long d'une
#                                       section RECTILIGNE, la moitié est
#                                       attendue : 319 sur 642 sur le cadre
#                                                | { "pose": false,
#                                                    "raison": "…",
#                                                    "boucles": 0, "ouvertes": 1 } },
#                              "b": { … } },
#                   "retire": [ "b" ],       les côtés que `garder` a écartés
#                   "contenant": true } ],   le nœud reste, SANS maillage, parce
#                                            qu'il a des enfants à garder
#     "capuchons": { "materiau": "le premier matériau de la pièce",
#                    "uv": [0, 0] } }
#   Une pièce que le plan ne traverse pas a `"traversee": false` et un seul
#   côté sous `"entier"` ; elle n'est pas renommée, mais son index CHANGE avec
#   le compactage — `noeud_apres` le dit. Si `garder` écarte ce côté-là, elle
#   est retirée (`retire`), ou réduite à un contenant si elle a des enfants.

_GARDER = ("deux", "a", "b")
_EPS_AIRE = 1e-12
# Le seuil de l'échelle : un sommet à moins de cette fraction de la diagonale
# de la pièce est RAMENÉ sur le plan avant classification (voir couper). Un
# ulp f32 à l'ordre 1 vaut 1,2e-7 ; à 1e-7, quelques ulp autour du plan sont
# tenus pour dessus.
_EPS_PLAN = 1e-7


class _Cote:
    """Un côté du plan pour UNE primitive : ses sommets (une colonne par
    attribut), ses triangles, et les deux tables qui évitent de dupliquer un
    sommet — les sommets d'origine par index, les points de section par clé
    d'arête."""
    __slots__ = ("cols", "tris", "orig", "inter")

    def __init__(self, nb_attrs: int):
        self.cols = [[] for _ in range(nb_attrs)]
        self.tris = []
        self.orig = {}
        self.inter = {}

    def sommet_orig(self, i: int, valeurs) -> int:
        k = self.orig.get(i)
        if k is None:
            k = len(self.cols[0])
            self.orig[i] = k
            for col, val in zip(self.cols, valeurs):
                col.append(val[i])
        return k

    def sommet_inter(self, cle, v) -> int:
        k = self.inter.get(cle)
        if k is None:
            k = len(self.cols[0])
            self.inter[cle] = k
            for col, x in zip(self.cols, v):
                col.append(x)
        return k

    def sommet_neuf(self, v) -> int:
        k = len(self.cols[0])
        for col, x in zip(self.cols, v):
            col.append(x)
        return k


def _plan_local(m: list, point, normale):
    """Le plan MONDE (point P, normale N) lu dans le repère LOCAL d'un nœud de
    matrice monde m (colonne-majeure) : d(p) = n_l · p + c_l vaut EXACTEMENT
    (W·p − P) · N. n_l = W_linᵀ · N — la transposée, et non l'inverse : ce
    qu'il faut pour une distance, et ce qui reste juste sous une échelle NON
    UNIFORME, où « tourner la normale » serait faux (le banc le mesure sur une
    boîte 1,3 × 0,7 × 0,4)."""
    nl = tuple(m[c * 4] * normale[0] + m[c * 4 + 1] * normale[1]
               + m[c * 4 + 2] * normale[2] for c in range(3))
    cl = ((m[12] - point[0]) * normale[0] + (m[13] - point[1]) * normale[1]
          + (m[14] - point[2]) * normale[2])
    return nl, cl


def _decouper_primitive(noms: list, valeurs: list, indices: list, d: list,
                        i_nrm, normale=None):
    """Répartit et découpe les triangles d'UNE primitive de part et d'autre
    du plan. Rend (côté a, côté b, segments de section, nombre de triangles
    COPLANAIRES) — les segments sont des paires de POSITIONS, pas d'index : la
    section se recoud par position, ce qui traverse les coutures UV (deux
    index pour un même point) et les frontières de primitives. Le compte des
    coplanaires sert à `couper` : une pièce traversée qui en porte est REFUSÉE
    (voir là-bas pourquoi la section ne se calcule pas).

    Le côté a est d ≥ 0 (le sens de la normale). Un sommet EXACTEMENT sur le
    plan compte donc côté a ; l'intersection d'une arête qui part de lui est
    lui-même (t = 0), et le triangle plat qui en naît est écarté — ce sont les
    deux seules concessions faites au cas dégénéré, et elles laissent la
    section juste.

    L'enroulement est CONSERVÉ : le sommet seul de son côté ouvre le triangle
    (seul, p, q) — une rotation cyclique de l'original —, et les deux
    triangles de l'autre côté se lisent (x1, p, q), (x1, q, x2).

    `normale` est la normale du plan en repère LOCAL : un triangle dont les
    trois sommets sont SUR le plan part du côté opposé à sa propre normale —
    c'est la peau d'un corps qui vit de l'autre côté. Sans elle, il part côté
    a comme tout « d ≥ 0 ».
    """
    ip = noms.index("POSITION")
    i_tan = noms.index("TANGENT") if "TANGENT" in noms else None
    pos = valeurs[ip]
    a, b = _Cote(len(noms)), _Cote(len(noms))
    points: dict = {}
    segments: list = []
    coplanaires = 0

    def inter(i: int, j: int):
        cle = (i, j) if i < j else (j, i)
        v = points.get(cle)
        if v is None:
            # L'interpolation part TOUJOURS de la plus petite POSITION, pas du
            # plus petit index : une couture UV porte la même arête sous deux
            # paires d'index, souvent dans l'ordre inverse, et a + (b − a)·t
            # ne vaut pas b + (a − b)·(1 − t) au dernier bit. Mesuré : sur le
            # cube du banc, la section restait une chaîne OUVERTE de neuf
            # arêtes non appariées, et aucun capuchon ne se posait.
            i0, j0 = (cle if pos[cle[0]] <= pos[cle[1]] else (cle[1], cle[0]))
            di, dj = d[i0], d[j0]
            t = di / (di - dj)
            v = []
            for k, val in enumerate(valeurs):
                vi, vj = val[i0], val[j0]
                x = tuple(u + (w - u) * t for u, w in zip(vi, vj))
                if k == i_nrm:
                    # une normale interpolée n'est plus unitaire — glTF les
                    # veut normées, et un lecteur strict s'en plaindrait
                    nn = (x[0] * x[0] + x[1] * x[1] + x[2] * x[2]) ** 0.5
                    if nn > 0:
                        x = (x[0] / nn, x[1] / nn, x[2] / nn)
                if k == i_tan and len(x) == 4:
                    # une tangente interpolée se renorme aussi, et son w (le
                    # sens de la bitangente) reste ±1 — jamais 0,4
                    nt = (x[0] * x[0] + x[1] * x[1] + x[2] * x[2]) ** 0.5
                    if nt > 0:
                        x = (x[0] / nt, x[1] / nt, x[2] / nt,
                             1.0 if x[3] >= 0 else -1.0)
                v.append(x)
            v = tuple(v)
            points[cle] = v
        return cle, v

    def plat(p0, p1, p2) -> bool:
        return p0 == p1 or p1 == p2 or p0 == p2

    for k in range(0, len(indices) - 2, 3):
        i0, i1, i2 = indices[k], indices[k + 1], indices[k + 2]
        s0, s1, s2 = d[i0] >= 0, d[i1] >= 0, d[i2] >= 0
        if s0 == s1 == s2:
            cote = a if s0 else b
            if (normale is not None and d[i0] == 0 and d[i1] == 0
                    and d[i2] == 0):
                # COPLANAIRE : le triangle est la PEAU d'un corps qui vit du
                # côté opposé à sa normale — il part de ce côté-là. Compté côté
                # a comme les autres « d ≥ 0 », il faisait d'une face confondue
                # avec le plan une pièce de volume nul, deux capuchons posés et
                # un compte rendu « traversée » (revue : le cube, plan y = 1 —
                # cube_a, 4 triangles, 2 arêtes non appariées). Du côté opposé
                # à sa normale, le cube entier part côté b et le refus « ne
                # traverse aucune pièce » parle.
                coplanaires += 1
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pos[i0], pos[i1], pos[i2]
                nx = (by - ay) * (cz - az) - (bz - az) * (cy - ay)
                ny = (bz - az) * (cx - ax) - (bx - ax) * (cz - az)
                nz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
                if nx * normale[0] + ny * normale[1] + nz * normale[2] > 0:
                    cote = b
            cote.tris.append((cote.sommet_orig(i0, valeurs),
                              cote.sommet_orig(i1, valeurs),
                              cote.sommet_orig(i2, valeurs)))
            continue
        if s0 == s1:
            seul, p, q, cote_seul = i2, i0, i1, s2
        elif s1 == s2:
            seul, p, q, cote_seul = i0, i1, i2, s0
        else:
            seul, p, q, cote_seul = i1, i2, i0, s1
        c1, v1 = inter(seul, p)
        c2, v2 = inter(seul, q)
        solo, autre = (a, b) if cote_seul else (b, a)
        if not plat(pos[seul], v1[ip], v2[ip]):
            solo.tris.append((solo.sommet_orig(seul, valeurs),
                              solo.sommet_inter(c1, v1),
                              solo.sommet_inter(c2, v2)))
        x1 = autre.sommet_inter(c1, v1)
        x2 = autre.sommet_inter(c2, v2)
        pp = autre.sommet_orig(p, valeurs)
        qq = autre.sommet_orig(q, valeurs)
        if not plat(v1[ip], pos[p], pos[q]):
            autre.tris.append((x1, pp, qq))
        if not plat(v1[ip], pos[q], v2[ip]):
            autre.tris.append((x1, qq, x2))
        if v1[ip] != v2[ip]:
            segments.append((v1[ip], v2[ip]))
    return a, b, segments, coplanaires


def _boucles(segments: list):
    """Recoud les segments de section en BOUCLES fermées et en CHAÎNES
    ouvertes, par position exacte. Rend (boucles, ouvertes) : des listes de
    positions. Une chaîne reste ouverte quand un bout n'a qu'un segment (la
    surface n'était pas fermée) ou quand un point en porte trois ou plus (une
    jonction : la section n'est pas une courbe simple). NUANCE, mesurée par la
    revue : sur une section en 8 (un point de degré quatre), les deux lobes se
    ferment chacun selon l'ordre de balayage — mieux que la règle ne le
    promet, et dépendant de cet ordre ; on le dit plutôt que de le garantir.
    Linéaire en le nombre de segments : 644 segments en 0,001 s."""
    ident: dict = {}
    pts: list = []
    aretes: list = []
    for p, q in segments:
        ia = ident.setdefault(p, len(pts))
        if ia == len(pts):
            pts.append(p)
        ib = ident.setdefault(q, len(pts))
        if ib == len(pts):
            pts.append(q)
        if ia != ib:
            aretes.append((ia, ib))
    voisins: dict = {}
    for e, (ia, ib) in enumerate(aretes):
        voisins.setdefault(ia, []).append(e)
        voisins.setdefault(ib, []).append(e)
    vus = [False] * len(aretes)

    def avancer(chaine: list):
        while True:
            cur = chaine[-1]
            inc = voisins[cur]
            if len(inc) != 2:
                return
            e = inc[1] if vus[inc[0]] else inc[0]
            if vus[e]:
                return
            vus[e] = True
            x, y = aretes[e]
            chaine.append(y if x == cur else x)
            if chaine[-1] == chaine[0]:
                return

    boucles, ouvertes = [], []
    for e0 in range(len(aretes)):
        if vus[e0]:
            continue
        vus[e0] = True
        chaine = list(aretes[e0])
        avancer(chaine)
        if chaine[-1] != chaine[0]:
            chaine.reverse()
            avancer(chaine)
        if chaine[-1] == chaine[0] and len(chaine) > 3:
            boucles.append([pts[i] for i in chaine[:-1]])
        else:
            ouvertes.append([pts[i] for i in chaine])
    return boucles, ouvertes


def _base_du_plan(n):
    """(e1, e2) orthonormés dans le plan de normale unitaire n."""
    k = min(range(3), key=lambda i: abs(n[i]))
    e = [0.0, 0.0, 0.0]
    e[k] = 1.0
    e1 = [e[i] - n[i] * n[k] for i in range(3)]
    l1 = (e1[0] * e1[0] + e1[1] * e1[1] + e1[2] * e1[2]) ** 0.5
    e1 = (e1[0] / l1, e1[1] / l1, e1[2] / l1)
    e2 = (n[1] * e1[2] - n[2] * e1[1], n[2] * e1[0] - n[0] * e1[2],
          n[0] * e1[1] - n[1] * e1[0])
    return e1, e2


def _dedans_polygone(pt, poly) -> bool:
    """Point dans un polygone 2D — lancer de rayon, pair/impair."""
    x, y = pt
    dedans = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i - 1]
        x1, y1 = poly[i]
        if (y0 > y) != (y1 > y):
            xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xi:
                dedans = not dedans
    return dedans


def _trianguler(poly: list):
    """Triangulation par OREILLES d'un polygone 2D simple. Rend la liste des
    triplets d'index, ou None quand aucune oreille ne se présente plus — un
    polygone auto-intersecté, typiquement. Les sommets réflexes sont tenus à
    part : ce sont les seuls qui puissent tomber dans une oreille, et les
    tester seuls ramène le coût au carré plutôt qu'au cube. QUADRATIQUE en la
    longueur de la boucle, donc — mesuré : un peigne de 1 001 points en 0,23 s,
    4 001 points en 3,6 s ; la section du cadre réel, 644 points, en 0,03 s."""
    n = len(poly)
    if n < 3:
        return None
    aire2 = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1]
                for i in range(n))
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    diag2 = (max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
    eps = _EPS_AIRE * diag2
    if abs(aire2) <= eps:
        return None
    idx = list(range(n))
    if aire2 < 0:
        idx.reverse()

    def croix(i, j, k):
        (ax, ay), (bx, by), (cx, cy) = poly[i], poly[j], poly[k]
        return (bx - ax) * (cy - by) - (by - ay) * (cx - bx)

    def dans_triangle(pt, i, j, k):
        (ax, ay), (bx, by), (cx, cy) = poly[i], poly[j], poly[k]
        px, py = pt
        d1 = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        d2 = (cx - bx) * (py - by) - (cy - by) * (px - bx)
        d3 = (ax - cx) * (py - cy) - (ay - cy) * (px - cx)
        return d1 >= -eps and d2 >= -eps and d3 >= -eps

    tris = []
    reflexes = set()
    m = len(idx)
    for k in range(m):
        if croix(idx[k - 1], idx[k], idx[(k + 1) % m]) < -eps:
            reflexes.add(idx[k])
    while len(idx) > 3:
        m = len(idx)
        choix = plate = None
        for k in range(m):
            ip, i, inx = idx[k - 1], idx[k], idx[(k + 1) % m]
            if i in reflexes:
                continue
            c = croix(ip, i, inx)
            if c > eps:
                if any(j not in (ip, i, inx) and dans_triangle(poly[j], ip, i, inx)
                       for j in reflexes):
                    continue
                choix = k
                break
            if plate is None and abs(c) <= eps:
                plate = k
        # Une oreille CONVEXE d'abord ; une oreille PLATE (trois points alignés,
        # le cas de chaque triangle traversé le long d'une face plane) ne se
        # coupe qu'à défaut, et ÉMET son triangle d'aire nulle. Retirée sans
        # triangle, l'arête (ip, inx) du capuchon n'aurait pas de jumelle sur
        # la paroi — une jonction en T. Mesuré sur le cadre du modèle réel :
        # 330 arêtes non appariées par moitié, et 3 sur le cube du banc.
        if choix is None:
            choix = plate
        if choix is None:
            return None
        k = choix
        ip, i, inx = idx[k - 1], idx[k], idx[(k + 1) % m]
        tris.append((ip, i, inx))
        del idx[k]
        m -= 1
        for j in (ip, inx):
            pos = idx.index(j)
            if croix(idx[pos - 1], j, idx[(pos + 1) % m]) < -eps:
                reflexes.add(j)
            else:
                reflexes.discard(j)
    tris.append(tuple(idx))
    return tris


def _capuchon(boucles: list, ouvertes: list, n_unit, vers, noms: list, i_nrm):
    """Les triangles du capuchon d'UN côté, à partir des boucles de la
    section, orientés vers `vers` (l'extérieur de ce côté : −n pour le côté a,
    +n pour le côté b). Rend (sommets, triangles, compte rendu) ; les sommets
    portent la normale du plan, un UV à (0, 0), une tangente dans le plan et
    des zéros pour tout autre attribut — c'est dit dans le compte rendu.

    Des boucles IMBRIQUÉES (une section à trou : un tube, un tore) ne se
    bouchent pas en v1 : boucher chacune remplirait le trou, ce qui serait
    une géométrie fausse. On ne pose rien et on le dit."""
    if not boucles:
        raison = ("surface ouverte : la section ne se referme pas "
                  f"({len(ouvertes)} chaîne(s) ouverte(s)) — rien à boucher"
                  if ouvertes else "le plan ne produit aucune section")
        return [], [], {"pose": False, "raison": raison, "boucles": 0,
                        "ouvertes": len(ouvertes)}
    e1, e2 = _base_du_plan(n_unit)
    plans2d = [[(p[0] * e1[0] + p[1] * e1[1] + p[2] * e1[2],
                 p[0] * e2[0] + p[1] * e2[1] + p[2] * e2[2]) for p in b]
               for b in boucles]
    for i, bi in enumerate(plans2d):
        for j, bj in enumerate(plans2d):
            if i != j and _dedans_polygone(bj[0], bi):
                return [], [], {
                    "pose": False,
                    "raison": f"{len(boucles)} boucles imbriquées (la section "
                              "a un trou) — le couteau v1 ne perce pas, "
                              "capuchon non posé",
                    "boucles": len(boucles), "ouvertes": len(ouvertes)}
    # L'ORIENTATION SE DÉCIDE UNE FOIS POUR TOUTE LA BOUCLE, jamais triangle
    # par triangle. `_trianguler` rend des triangles tournés dans le sens de la
    # base (e1, e2, n) — leur normale géométrique est +n ; on les retourne
    # tous si l'extérieur est −n. Juger chaque triangle à son produit
    # vectoriel semblait équivalent et ne l'est pas : le long d'une face plane,
    # la section aligne des centaines de points et les triangles en aiguille
    # ont une normale noyée dans le bruit — mesuré sur le cadre du modèle réel,
    # 371 arêtes du capuchon dans le MÊME sens que la paroi, donc non
    # appariées, sur une pièce pourtant fermée.
    inverser = (vers[0] * n_unit[0] + vers[1] * n_unit[1]
                + vers[2] * n_unit[2]) < 0
    sommets: list = []
    tris: list = []
    degeneres = 0
    for b3, b2 in zip(boucles, plans2d):
        t = _trianguler(b2)
        if t is None:
            return [], [], {
                "pose": False,
                "raison": "boucle de section non triangulable "
                          "(auto-intersection ?) — capuchon non posé",
                "boucles": len(boucles), "ouvertes": len(ouvertes)}
        base = len(sommets)
        for p in b3:
            v = []
            for k, nom in enumerate(noms):
                if nom == "POSITION":
                    v.append(p)
                elif k == i_nrm:
                    v.append(vers)
                elif nom == "TANGENT":
                    v.append((e1[0], e1[1], e1[2], 1.0))
                else:
                    v.append(None)      # comblé par des zéros à l'emballage
            sommets.append(v)
        xs = [p[0] for p in b2]
        ys = [p[1] for p in b2]
        eps = _EPS_AIRE * ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2)
        for (i, j, k) in t:
            # les triangles d'aire nulle sont COMPTÉS et dits : une oreille
            # plate émet le sien exprès (voir _trianguler), un slicer le répare
            (ax, ay), (bx, by), (cx, cy) = b2[i], b2[j], b2[k]
            if abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) <= eps:
                degeneres += 1
            if inverser:
                j, k = k, j
            tris.append((base + i, base + j, base + k))
    return sommets, tris, {"pose": True, "triangles": len(tris),
                           "boucles": len(boucles), "ouvertes": len(ouvertes),
                           "degeneres": degeneres}


def _ajouter_vue(doc: dict, tampon: bytearray, octets: bytes, cible: int) -> int:
    while len(tampon) % 4:
        tampon.append(0)
    doc.setdefault("bufferViews", []).append(
        {"buffer": 0, "byteOffset": len(tampon), "byteLength": len(octets),
         "target": cible})
    tampon += octets
    return len(doc["bufferViews"]) - 1


def _ajouter_flottants(doc: dict, tampon: bytearray, valeurs: list, n: int,
                       avec_bornes: bool) -> int:
    plat = [x for v in valeurs for x in v]
    vue = _ajouter_vue(doc, tampon, struct.pack("<%df" % len(plat), *plat),
                       34962)
    a = {"bufferView": vue, "componentType": 5126, "count": len(valeurs),
         "type": {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4"}[n]}
    if avec_bornes:
        a["min"] = [min(v[k] for v in valeurs) for k in range(n)]
        a["max"] = [max(v[k] for v in valeurs) for k in range(n)]
    doc.setdefault("accessors", []).append(a)
    return len(doc["accessors"]) - 1


def _ajouter_indices(doc: dict, tampon: bytearray, tris: list) -> int:
    plat = [i for t in tris for i in t]
    court = max(plat) < 65536
    fmt, ct = ("<%dH", 5123) if court else ("<%dI", 5125)
    vue = _ajouter_vue(doc, tampon, struct.pack(fmt % len(plat), *plat), 34963)
    doc["accessors"].append({"bufferView": vue, "componentType": ct,
                             "count": len(plat), "type": "SCALAR"})
    return len(doc["accessors"]) - 1


def couper(data: bytes, noeuds, point, normale, garder: str = "deux"):
    """Coupe les nœuds `noeuds` par le plan MONDE (point, normale) et rend
    (glb, compte rendu). Chaque nœud coupé devient DEUX nœuds `<nom>_a` et
    `<nom>_b` (a : le côté vers lequel pointe la normale), ou un seul si
    `garder` ≠ "deux", portant les mêmes matériaux et textures que l'original ;
    les capuchons prennent le premier matériau de la pièce, UV à (0, 0). Le
    format du compte rendu est décrit en tête de section.

    Refus parlants (ValueError, donc 400 à la route) : GLB compressé (Draco,
    meshopt — comme `print3d.lire_glb_triangles`), normale nulle, nœud hors du
    document ou hors de la scène active, nœud sans maillage (un contenant ne
    se coupe pas : retiens ses pièces), nœud qui est un os d'un skin,
    primitive non TRIANGLES, cibles de morphing, attribut non flottant (une
    peau JOINTS/WEIGHTS), et un plan qui ne traverse AUCUNE des pièces — un
    couteau qui n'a rien coupé n'écrit pas de version.

    Le document ressort COMPACTÉ par l'extraction de la scène entière : le
    maillage d'origine, orphelin, et ses tampons ne sont pas recopiés (le
    cadre du modèle réel pèse 4 Mo), et les nœuds sont renumérotés — le compte
    rendu donne les index de la version NEUVE. C'est pourquoi la coupe ne se
    met pas en file derrière des transformations : leurs index seraient faux.
    """
    from app.services import print3d

    if garder not in _GARDER:
        raise ValueError(f"garder attend deux, a ou b — reçu {garder!r}")
    n_monde = _unitaire(normale, "normale")
    p_monde = _vecteur3(point, "point")
    doc, binc = lire_glb(data)
    for ext in doc.get("extensionsRequired") or []:
        if ext in print3d._REFUS_EXTENSIONS:
            raise ValueError(print3d._REFUS_EXTENSIONS[ext])
    nodes = _l(doc, "nodes")
    try:
        demandes = sorted({int(x) for x in (noeuds or [])})
    except (TypeError, ValueError):
        raise ValueError("noeuds attend des index de nœud entiers") from None
    if not demandes:
        raise ValueError("aucune pièce retenue — le couteau ne tranche jamais "
                         "tout le modèle par défaut")
    scenes = doc.get("scenes") or [{"nodes": []}]
    isc = int(doc.get("scene", 0))
    if not (0 <= isc < len(scenes)):
        raise ValueError(f"scène active {isc} hors du document "
                         f"({len(scenes)} scènes)")
    racines = list(scenes[isc].get("nodes") or [])
    dans_scene: set[int] = set()
    pile = list(racines)
    while pile:
        i = pile.pop()
        if i in dans_scene or not (0 <= i < len(nodes)):
            continue
        dans_scene.add(i)
        pile.extend(_l(nodes[i], "children"))
    os_: set[int] = set()
    for s in _l(doc, "skins"):
        os_.update(_l(s, "joints"))
    for i in demandes:
        if not (0 <= i < len(nodes)):
            raise ValueError(f"noeud {i} hors du document ({len(nodes)} noeuds)")
        if i not in dans_scene:
            raise ValueError(f"noeud {i} hors de la scène active")
        if nodes[i].get("mesh") is None:
            raise ValueError(f"noeud {i} sans maillage — un contenant ne se "
                             "coupe pas, retiens ses pièces")
        if i in os_:
            raise ValueError(f"noeud {i} est un os (joint d'un skin) — hors "
                             "périmètre du couteau")

    tampon = bytearray(binc)
    rapport_pieces: list = []
    produits: dict = {}            # nœud demandé → nœuds neufs (avant compactage)
    traversee = False

    # Du plus PROFOND au moins profond : le remplacement d'un enfant se fait
    # dans la liste de son parent tant que celui-ci est encore l'original.
    par0 = _parents(nodes)

    def profondeur(i: int) -> int:
        k, vus = 0, set()
        while i in par0 and i not in vus:
            vus.add(i)
            i = par0[i]
            k += 1
        return k

    for i in sorted(demandes, key=profondeur, reverse=True):
        node = nodes[i]
        nom = node.get("name") or f"noeud_{i}"
        mesh = _l(doc, "meshes")[node["mesh"]]
        m = _mat_mul(_monde_des_ancetres(doc, i), _mat_locale(node))
        nl, cl = _plan_local(m, p_monde, n_monde)
        ln = (nl[0] ** 2 + nl[1] ** 2 + nl[2] ** 2) ** 0.5
        if ln < 1e-18:
            raise ValueError(f"noeud {i} : matrice monde dégénérée (échelle "
                             "nulle), le plan n'y a pas de sens")
        n_unit = (nl[0] / ln, nl[1] / ln, nl[2] / ln)
        if mesh.get("weights"):
            raise ValueError(f"noeud {i} ({nom}) : cibles de morphing — hors "
                             "périmètre du couteau")
        cotes = {"a": [], "b": []}          # une entrée par primitive
        segments_mesh: list = []
        total_tris = 0
        lectures: list = []
        for pr in _l(mesh, "primitives"):
            if pr.get("mode", 4) != 4:
                raise ValueError(f"noeud {i} ({nom}) : primitive non TRIANGLES "
                                 f"(mode {pr.get('mode')}) — hors périmètre")
            if pr.get("targets"):
                raise ValueError(f"noeud {i} ({nom}) : cibles de morphing — "
                                 "hors périmètre du couteau")
            attrs = pr.get("attributes") or {}
            if "POSITION" not in attrs:
                raise ValueError(f"noeud {i} ({nom}) : primitive sans POSITION")
            noms = sorted(attrs, key=lambda k: (k != "POSITION", k))
            valeurs = []
            for nom_attr in noms:
                ai = attrs[nom_attr]
                acc = _l(doc, "accessors")[ai]
                if acc.get("componentType") != 5126:
                    raise ValueError(
                        f"noeud {i} ({nom}) : attribut {nom_attr} en composant "
                        f"{acc.get('componentType')} — le couteau v1 n'interpole "
                        "que des flottants (un maillage peau reste entier)")
                valeurs.append(_lire_accesseur(doc, binc, ai))
            pos = valeurs[0]
            if pr.get("indices") is not None:
                indices = [t[0] for t in _lire_accesseur(doc, binc, pr["indices"])]
            else:
                indices = list(range(len(pos)))
            total_tris += len(indices) // 3
            lectures.append((pr, attrs, noms, valeurs, indices))

        # LE SEUIL DE L'ÉCHELLE : un sommet à quelques ulp f32 du plan est
        # RAMENÉ dessus avant classification, ce qui le route vers le cas exact
        # (l'intersection est le sommet lui-même, le triangle plat est écarté),
        # prouvé fermé. Classé par signe strict, il faisait des aiguilles qui
        # s'effondrent à l'écriture f32 — revue : plan à 1e-9 d'un sommet, 5
        # arêtes non appariées par moitié et des triangles plats dans la PAROI,
        # sous un compte rendu « fermé ». `d` vaut |n_l| fois la distance : le
        # seuil est mis à la même échelle. Et il est calculé sur la PIÈCE
        # entière, pas par primitive : la section se recoud par position à
        # travers les primitives, et un seuil par primitive pouvait ramener un
        # sommet partagé sur le plan d'un côté et pas de l'autre (chaîne
        # ouverte — dite, mais évitable).
        tous = [p for _, _, _, valeurs, _ in lectures for p in valeurs[0]]
        xs = [p[0] for p in tous]
        ys = [p[1] for p in tous]
        zs = [p[2] for p in tous]
        diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
                + (max(zs) - min(zs)) ** 2) ** 0.5
        seuil = _EPS_PLAN * diag * ln
        coplanaires = 0
        for pr, attrs, noms, valeurs, indices in lectures:
            pos = valeurs[0]
            d = [nl[0] * p[0] + nl[1] * p[1] + nl[2] * p[2] + cl for p in pos]
            d = [0.0 if abs(x) <= seuil else x for x in d]
            i_nrm = noms.index("NORMAL") if "NORMAL" in noms else None
            ca, cb, segs, copl = _decouper_primitive(noms, valeurs, indices, d,
                                                     i_nrm, nl)
            coplanaires += copl
            largeurs = [len(valeurs[k][0]) if valeurs[k] else
                        _NB_COMPOSANTS[_l(doc, "accessors")[attrs[nm]]["type"]]
                        for k, nm in enumerate(noms)]
            cotes["a"].append((noms, ca, pr, largeurs))
            cotes["b"].append((noms, cb, pr, largeurs))
            segments_mesh.extend(segs)

        piece = {"noeud_avant": i, "nom": nom, "triangles": total_tris}
        na = sum(len(c.tris) for _, c, _, _ in cotes["a"])
        nb = sum(len(c.tris) for _, c, _, _ in cotes["b"])
        if not na or not nb:
            entier = "a" if na else "b"
            piece["traversee"] = False
            piece["entier"] = entier
            garde = garder in ("deux", entier)
            piece["retire"] = [] if garde else [entier]
            rapport_pieces.append(piece)
            produits[i] = [i] if garde else []
            continue
        # UNE FACE CONFONDUE AVEC LE PLAN, DE LA MATIÈRE DES DEUX CÔTÉS : REFUS.
        # Les triangles coplanaires sont bien affectés (du côté opposé à leur
        # normale), mais les segments de section ne naissent que des triangles
        # FENDUS : sur une face qui n'est qu'une PARTIE de la frontière entre
        # les deux côtés — l'anneau d'une marche, un décrochement —, la boucle
        # est fausse (le rebord extérieur, alors que la vraie frontière court
        # au pied du bloc) et les deux capuchons se posaient dessus sous un
        # compte rendu « posé » (revue : marche 4×4×2 + 2×2×2, plan y = 2 —
        # une moitié de volume nul à 8 arêtes non appariées, l'autre à 12). La
        # section juste demanderait l'ADJACENCE (une arête entre un triangle
        # coplanaire et un triangle de l'autre côté) : lot ultérieur. D'ici là
        # on refuse en le disant ; le cube convexe, lui, tombe avant sur « ne
        # traverse aucune pièce » puisque tout part d'un seul côté.
        if coplanaires:
            raise ValueError(
                f"le plan est confondu avec une face de « {nom} » ({coplanaires} "
                "triangle(s) dans le plan) et il y a de la matière des deux côtés "
                "— décale-le d'un cheveu : une face confondue qui n'est qu'une "
                "partie de la frontière n'a pas de section calculable sans "
                "adjacence (lot ultérieur)")
        traversee = True
        piece["traversee"] = True
        boucles, ouvertes = _boucles(segments_mesh)
        piece["cotes"] = {}
        piece["retire"] = [c for c in ("a", "b") if garder not in ("deux", c)]
        neufs: list = []
        for cote in ("a", "b"):
            if garder not in ("deux", cote):
                continue
            vers = tuple(-x for x in n_unit) if cote == "a" else n_unit
            noms0, c0, _, largeurs0 = cotes[cote][0]
            i_nrm0 = noms0.index("NORMAL") if "NORMAL" in noms0 else None
            som_cap, tris_cap, bilan_cap = _capuchon(
                boucles, ouvertes, n_unit, vers, noms0, i_nrm0)
            if tris_cap:
                base = [c0.sommet_neuf([
                    x if x is not None else (0.0,) * largeurs0[k]
                    for k, x in enumerate(v)]) for v in som_cap]
                for (p, q, r) in tris_cap:
                    c0.tris.append((base[p], base[q], base[r]))
            primitives = []
            n_tris = 0
            for noms_p, cp, pr, largeurs_p in cotes[cote]:
                if not cp.tris:
                    continue
                n_tris += len(cp.tris)
                prim = {k: v for k, v in pr.items()
                        if k not in ("attributes", "indices", "targets")}
                prim["attributes"] = {
                    nom_attr: _ajouter_flottants(
                        doc, tampon, cp.cols[k], largeurs_p[k],
                        nom_attr == "POSITION")
                    for k, nom_attr in enumerate(noms_p)}
                prim["indices"] = _ajouter_indices(doc, tampon, cp.tris)
                primitives.append(prim)
            doc.setdefault("meshes", []).append(
                {"name": f"{mesh.get('name') or nom}_{cote}",
                 "primitives": primitives,
                 **({"extras": mesh["extras"]} if "extras" in mesh else {})})
            neuf = {k: v for k, v in node.items()
                    if k not in ("mesh", "children", "name", "skin")}
            neuf["name"] = f"{nom}_{cote}"
            neuf["mesh"] = len(doc["meshes"]) - 1
            nodes.append(neuf)
            j = len(nodes) - 1
            neufs.append(j)
            piece["cotes"][cote] = {"noeud_apres": j, "nom": neuf["name"],
                                    "triangles": n_tris, "capuchon": bilan_cap}
        enfants = list(_l(node, "children"))
        if enfants:
            if neufs:
                nodes[neufs[0]]["children"] = enfants
            else:
                # tout écarté par `garder`, mais des enfants à garder : le
                # nœud reste comme simple contenant, et le compte rendu le dit
                node.pop("mesh", None)
                piece["contenant"] = True
                neufs = [i]
        # le nœud d'origine cède sa place à ses moitiés — chez son parent, ou
        # parmi les racines de la scène
        par = _parents(nodes)
        liste = nodes[par[i]]["children"] if i in par else racines
        k = liste.index(i)
        liste[k:k + 1] = neufs
        produits[i] = neufs
        rapport_pieces.append(piece)

    if not traversee:
        raise ValueError("le plan ne traverse aucune des pièces retenues — "
                         "rien à couper")
    # les pièces entières écartées par `garder` — retirées, ou réduites à un
    # CONTENANT si elles ont des enfants : retirer le nœud emportait ses enfants
    # en silence, et `retire` ne le disait pas (revue : le sol et son enfant
    # au-dessus du plan, garder = a — l'enfant disparaissait). Même traitement
    # que la pièce traversée dont les deux côtés sont écartés.
    for piece in rapport_pieces:
        i = piece["noeud_avant"]
        if produits.get(i) != [] or nodes[i].get("mesh") is None:
            continue
        if _l(nodes[i], "children"):
            nodes[i].pop("mesh", None)
            piece["contenant"] = True
            continue
        par = _parents(nodes)
        liste = nodes[par[i]]["children"] if i in par else racines
        if i in liste:
            liste.remove(i)
    scenes[isc]["nodes"] = racines
    doc["scenes"] = scenes
    doc["buffers"] = [{"byteLength": len(tampon)}]

    # COMPACTAGE par l'extraction de la scène entière : l'orphelin et ses
    # tampons tombent, tout est renuméroté — et la carte des nœuds traduit le
    # compte rendu dans les index de la version neuve.
    out, neuf_bin, m_node = _extraire_doc(doc, bytes(tampon), racines)
    for piece in rapport_pieces:
        for c in (piece.get("cotes") or {}).values():
            c["noeud_apres"] = m_node.get(c["noeud_apres"])
        piece["noeud_apres"] = m_node.get(piece["noeud_avant"])
    rapport = {
        "plan": {"point": list(p_monde), "normale": list(n_monde),
                 "repere": "monde"},
        "garder": garder,
        "noeuds_avant": demandes,
        "pieces": sorted(rapport_pieces, key=lambda p: p["noeud_avant"]),
        "capuchons": {"materiau": "le premier matériau de la pièce",
                      "uv": [0, 0]},
    }
    return ecrire_glb(out, neuf_bin), rapport
