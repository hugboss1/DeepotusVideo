# -*- coding: utf-8 -*-
"""Union, différence, intersection sur des triangles MONDE — stdlib pure (tâche T092, plan-etabli T18).

L'ALGORITHME, et pourquoi lui (le tableau des candidats écartés vit dans le plan, tâche 18, étape 1) : découpe LOCALE
puis classification. Exact (aucun arrondi de voxel), et son coût suit la TAILLE DE LA ZONE DE CONTACT, pas celle des
modèles.

  1. DÉCOUPE. Chaque triangle de A n'est découpé QUE par les triangles de B qui le coupent VRAIMENT (test des deux
     plans, après les boîtes, dans une grille 3D) : par le plan du triangle de B quand ils se croisent, par les trois
     plans d'ARÊTES du triangle de B quand ils sont COPLANAIRES — sans quoi une face commune ne serait jamais
     partagée en « recouvert » et « pas recouvert ». Idem pour B contre A. Aucun garde-fou qui arrête la découpe à
     mi-chemin (le dessin du plan s'arrêtait à 64 morceaux : un résultat faux, en silence).
  2. CLASSEMENT de chaque morceau par rapport à l'autre solide : posé SUR sa surface (coplanaire, même sens ou sens
     opposé), sinon DEDANS ou DEHORS par la parité d'un rayon parallèle à +x. Le rayon n'interroge que les triangles
     de la colonne (y, z) qu'il traverse — une grille 2D — et son origine est déplacée d'un pas minuscule et
     irrationnel en y et z : un rayon qui raserait une arête compterait mal, celui-ci ne rase rien.
  3. GARDE, selon l'opération — et les faces COPLANAIRES ont leur règle, que le plan n'avait pas (il aurait gardé
     les DEUX copies d'une face commune, et compté son volume deux fois) :
        union        : A dehors + A « même sens »         + B dehors
        intersection : A dedans + A « même sens »         + B dedans
        différence   : A dehors + A « sens opposé »       + B dedans, RETOURNÉ (il devient la paroi du creux)

CE QU'IL NE FAIT PAS, ET C'EST DIT : il ne recoud pas les sommets en T le long de la couture — les morceaux se
touchent bord à bord sans partager leurs sommets. Le résultat est fermé GÉOMÉTRIQUEMENT, pas au sens des index ;
« Réparer en un clic » (souder) le referme, et la route le dit.

LE BUDGET EST UNE CONSTANTE MESURÉE, PAS UNE ESPÉRANCE : `MAX_TRIS` vient de la mesure sur deux tores (voir
tests/mesure_etabli_outils.py booleen et le message de commit). Au-delà, on refuse en nommant le chiffre.
"""
from __future__ import annotations

import math

OPERATIONS = ("union", "difference", "intersection")
MAX_TRIS = 50_000


# ── petite géométrie ─────────────────────────────────────────────────────────
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _croix(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _point(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _normale(t):
    return _croix(_sub(t[1], t[0]), _sub(t[2], t[0]))


def _boite(t):
    a, b, c = t
    return (min(a[0], b[0], c[0]), min(a[1], b[1], c[1]), min(a[2], b[2], c[2]),
            max(a[0], b[0], c[0]), max(a[1], b[1], c[1]), max(a[2], b[2], c[2]))


class _Tri:
    """Un triangle de l'AUTRE solide, préparé une fois : normale unitaire, offset du plan, boîte."""
    __slots__ = ("t", "n", "d", "boite")

    def __init__(self, t):
        n = _normale(t)
        ln = math.sqrt(_point(n, n))
        self.t = t
        self.n = (n[0] / ln, n[1] / ln, n[2] / ln) if ln > 0 else (0.0, 0.0, 0.0)
        self.d = _point(self.n, t[0])
        self.boite = _boite(t)


class _Grille:
    """Grille de hachage (3D ou 2D) sur les boîtes des triangles — chaque requête ne voit que son voisinage."""

    def __init__(self, tris, axes, maille):
        self.axes, self.maille, self.cases = axes, maille, {}
        for k, u in enumerate(tris):
            for cle in self._cles(u.boite):
                self.cases.setdefault(cle, []).append(k)
        self.tris = tris

    def _cles(self, b):
        m = self.maille
        plages = [range(int(math.floor(b[a] / m)), int(math.floor(b[a + 3] / m)) + 1) for a in self.axes]
        if len(plages) == 3:
            return [(i, j, k) for i in plages[0] for j in plages[1] for k in plages[2]]
        return [(i, j) for i in plages[0] for j in plages[1]]

    def autour(self, b):
        vus = set()
        for cle in self._cles(b):
            for k in self.cases.get(cle, ()):
                vus.add(k)
        return [self.tris[k] for k in sorted(vus)]


# ── 1. la découpe ────────────────────────────────────────────────────────────
def _couper(t, n, d, eps):
    """`t` coupé par le plan n·x = d : la liste de ses morceaux (orientation gardée), `[t]` s'il ne le traverse pas."""
    s = [_point(n, p) - d for p in t]
    if all(x >= -eps for x in s) or all(x <= eps for x in s):
        return [t]
    pos, neg = [], []
    for k in range(3):
        p, q = t[k], t[(k + 1) % 3]
        sp, sq = s[k], s[(k + 1) % 3]
        if sp >= -eps:
            pos.append(p)
        if sp <= eps:
            neg.append(p)
        if (sp > eps and sq < -eps) or (sp < -eps and sq > eps):
            f = sp / (sp - sq)
            m = (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f, p[2] + (q[2] - p[2]) * f)
            pos.append(m)
            neg.append(m)
    out = []
    for poly in (pos, neg):
        for k in range(1, len(poly) - 1):
            tri = (poly[0], poly[k], poly[k + 1])
            n2 = _normale(tri)
            if _point(n2, n2) > eps * eps * eps * eps:
                out.append(tri)
    return out or [t]


def _rencontre(t, u: _Tri, eps):
    """Rend « croise », « coplanaire » ou None. Conservatif : un « croise » de trop coûte une découpe inutile,
    jamais un résultat faux."""
    bt = _boite(t)
    bu = u.boite
    if (bt[0] > bu[3] + eps or bu[0] > bt[3] + eps or bt[1] > bu[4] + eps or bu[1] > bt[4] + eps
            or bt[2] > bu[5] + eps or bu[2] > bt[5] + eps):
        return None
    s = [_point(u.n, p) - u.d for p in t]
    if all(abs(x) <= eps for x in s):
        return "coplanaire"
    if all(x >= -eps for x in s) or all(x <= eps for x in s):
        return None
    nt = _normale(t)
    lt = math.sqrt(_point(nt, nt))
    if lt == 0:
        return None
    nt = (nt[0] / lt, nt[1] / lt, nt[2] / lt)
    dt = _point(nt, t[0])
    r = [_point(nt, p) - dt for p in u.t]
    if all(x >= -eps for x in r) or all(x <= eps for x in r):
        return None
    return "croise"


def _decouper(tris, grille: _Grille, eps):
    out = []
    for t in tris:
        morceaux = [t]
        for u in grille.autour(_boite(t)):
            quoi = _rencontre(t, u, eps)
            if quoi is None:
                continue
            if quoi == "croise":
                plans = [(u.n, u.d)]
            else:
                # coplanaires : les trois plans d'ARÊTE du triangle de l'autre, perpendiculaires à sa face
                plans = []
                for k in range(3):
                    p, q = u.t[k], u.t[(k + 1) % 3]
                    m = _croix(u.n, _sub(q, p))
                    lm = math.sqrt(_point(m, m))
                    if lm > 0:
                        m = (m[0] / lm, m[1] / lm, m[2] / lm)
                        plans.append((m, _point(m, p)))
            for (n, d) in plans:
                suivant = []
                for mo in morceaux:
                    if quoi == "croise" and _rencontre(mo, u, eps) is None:
                        suivant.append(mo)       # ce morceau-là ne touche plus ce triangle : rien à couper
                    else:
                        suivant.extend(_couper(mo, n, d, eps))
                morceaux = suivant
        out.extend(morceaux)
    return out


# ── 2. le classement ─────────────────────────────────────────────────────────
def _dans_triangle(p, u: _Tri, tol):
    """`p` (déjà dans le plan de `u`) est-il dans le triangle, bords compris à `tol` près ?"""
    a, b, c = u.t
    for (x, y) in ((a, b), (b, c), (c, a)):
        if _point(_croix(_sub(y, x), _sub(p, x)), u.n) < -tol:
            return False
    return True


def _classer(morceau, proches: _Grille, colonnes: _Grille, eps, decal):
    """« meme », « oppose » (posé sur la surface de l'autre), sinon « dedans » / « dehors »."""
    a, b, c = morceau
    g = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0, (a[2] + b[2] + c[2]) / 3.0)
    nm = _normale(morceau)
    for u in proches.autour((g[0], g[1], g[2], g[0], g[1], g[2])):
        if abs(_point(u.n, g) - u.d) <= eps and _dans_triangle(g, u, eps * max(1.0, math.sqrt(_point(nm, nm)))):
            if abs(_point(u.n, nm)) > 0:
                return "meme" if _point(u.n, nm) > 0 else "oppose"
    # parité d'un rayon +x, origine décalée d'un pas irrationnel en (y, z)
    y, z = g[1] + decal[0], g[2] + decal[1]
    n_hits = 0
    for u in colonnes.autour((0.0, y, z, 0.0, y, z)):
        if abs(u.n[0]) < 1e-15:
            continue                                      # triangle parallèle au rayon
        (a0, a1, a2), (b0, b1, b2), (c0, c1, c2) = u.t
        # point (y, z) dans la projection yz du triangle (signes des trois arêtes)
        e1 = (b1 - a1) * (z - a2) - (b2 - a2) * (y - a1)
        e2 = (c1 - b1) * (z - b2) - (c2 - b2) * (y - b1)
        e3 = (a1 - c1) * (z - c2) - (a2 - c2) * (y - c1)
        if not ((e1 > 0 and e2 > 0 and e3 > 0) or (e1 < 0 and e2 < 0 and e3 < 0)):
            continue
        x = (u.d - u.n[1] * y - u.n[2] * z) / u.n[0]
        if x > g[0]:
            n_hits += 1
    return "dedans" if n_hits % 2 == 1 else "dehors"


def _retourner(t):
    return (t[0], t[2], t[1])


def _volume(tris):
    """Volume signé (divergence) : positif pour un solide fermé à normales sortantes."""
    return sum(_point(a, _croix(b, c)) for a, b, c in tris) / 6.0


def operer(a, b, operation: str):
    """`a` et `b` : des listes de triangles ((x,y,z)×3) MONDE, chacune un solide fermé à normales sortantes. Rend
    la liste de triangles du résultat (vide si rien ne reste)."""
    if operation not in OPERATIONS:
        raise ValueError(f"operation « {operation} » — {', '.join(OPERATIONS)} sont attendues")
    if len(a) > MAX_TRIS or len(b) > MAX_TRIS:
        raise ValueError(f"{max(len(a), len(b))} triangles — le budget mesuré du booléen est de {MAX_TRIS} "
                         "triangles par opérande. Décime d'abord (onglet Fiche → Décimer), puis recommence.")
    # À L'ENDROIT d'abord : un opérande aux normales rentrantes (volume négatif — le tore de test_mesh_optimize
    # l'est) donnerait un résultat retourné. La parité, elle, ne dépend pas de l'orientation.
    a = [_retourner(t) for t in a] if _volume(a) < 0 else list(a)
    b = [_retourner(t) for t in b] if _volume(b) < 0 else list(b)
    if not a or not b:
        return a + b if operation == "union" else ([] if operation == "intersection" else a)
    tous = [p for t in a for p in t] + [p for t in b for p in t]
    etendue = max(max(p[i] for p in tous) - min(p[i] for p in tous) for i in range(3)) or 1.0
    eps = 1e-9 * etendue
    decal = (1.2345678912e-7 * etendue, 2.7182818284e-7 * etendue)

    def preparer(tris):
        prep = [u for u in (_Tri(t) for t in tris) if u.n != (0.0, 0.0, 0.0)]
        taille = sum(max(u.boite[3] - u.boite[0], u.boite[4] - u.boite[1], u.boite[5] - u.boite[2])
                     for u in prep) / max(1, len(prep))
        maille = max(taille, etendue / 256.0, 1e-12)
        return _Grille(prep, (0, 1, 2), maille), _Grille(prep, (1, 2), maille)

    proches_a, colonnes_a = preparer(a)
    proches_b, colonnes_b = preparer(b)
    ma = _decouper(a, proches_b, eps)
    mb = _decouper(b, proches_a, eps)
    ka = [(t, _classer(t, proches_b, colonnes_b, eps, decal)) for t in ma]
    kb = [(t, _classer(t, proches_a, colonnes_a, eps, decal)) for t in mb]
    if operation == "union":
        return [t for t, k in ka if k in ("dehors", "meme")] + [t for t, k in kb if k == "dehors"]
    if operation == "intersection":
        return [t for t, k in ka if k in ("dedans", "meme")] + [t for t, k in kb if k == "dedans"]
    return [t for t, k in ka if k in ("dehors", "oppose")] + [_retourner(t) for t, k in kb if k == "dedans"]
