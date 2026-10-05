# -*- coding: utf-8 -*-
"""Creuser : doubler la peau vers l'intérieur, et DIRE où la paroi ne tient pas (tâche #89 PR E, plan-etabli T6 CORRIGÉ,
05/10/2026). Stdlib pure, sans numpy (absent du runtime embarqué).

CE QUE C'EST : une coque par décalage des sommets le long de leur normale, la peau intérieure retournée, ajoutée comme
une PRIMITIVE de plus du maillage — la peau extérieure garde ses UV, ses normales et sa texture, intactes.

QUATRE CORRECTIONS DU PLAN, décidées par l'utilisateur le 05/10 (« évider corrigé ») :
  * SOUDURE PAR POSITION avant tout : un GLB de générateur dédouble les sommets à chaque arête vive (une normale par
    face). Décaler ces copies chacune selon SA face déchirerait la peau intérieure aux arêtes. Les normales se
    calculent donc sur le maillage soudé (toutes primitives de la pièce ensemble), et chaque copie suit la normale
    commune de sa position.
  * MAILLAGE FERMÉ EXIGÉ : chaque arête soudée vue exactement deux fois. Une coque ouverte n'a pas d'intérieur ;
    creuser rendrait deux surfaces flottantes. Refus, avec le compte des arêtes fautives et le remède (« Réparer le
    maillage », trous cochés).
  * ÉPAISSEUR CONSTANTE, PLAFONNÉE : le décalage d'un sommet est paroi / min(n_sommet · n_face) sur ses faces — au
    coin d'un cube, √3 × paroi, si bien que la peau intérieure est à `paroi` de CHAQUE face (la normale moyenne seule
    donnait paroi / √3 aux coins). Sur une arête très vive ce facteur explose : il est PLAFONNÉ à `PLAFOND`, et les
    sommets plafonnés — où la paroi est plus mince que demandé — sont COMPTÉS et dits.
  * LA LIMITE EST DITE : dans un creux plus serré que la paroi, la peau intérieure se retourne et le solide
    s'auto-intersecte. On COMPTE les triangles dont la normale s'inverse (`effondres`) et on cherche par dichotomie
    la paroi la plus épaisse qui n'en produit aucun (`paroi_max`) ; une peau intérieure retournée EN ENTIER (volume
    de signe opposé) compte tous ses triangles. Ce n'est pas un décalage exact (il faudrait un champ de distance
    signée, donc des voxels, donc numpy) : une partie plus mince que deux parois, sur un corps par ailleurs épais, peut
    se traverser sans retourner ni triangle ni volume — `LIMITE` le dit dans chaque rapport.

UNITÉS : `paroi` est en unités du MONDE de la scène (ce que la page mesure). Chaque pièce la ramène à son repère
local par l'échelle de sa matrice monde — qui doit être UNIFORME, sinon une même paroi n'a pas la même épaisseur selon
l'axe : refus dit. L'orientation se lit au volume signé LOCAL (une transformation, miroir compris, envoie l'intérieur
sur l'intérieur) : un maillage aux normales rentrantes se creuse quand même vers le dedans.

Un maillage PARTAGÉ par un autre nœud est CLONÉ pour la pièce creusée : sinon creuser l'une creuserait l'autre, à une
échelle qui n'est peut-être pas la sienne.

`mesh_edit` RESTE LA SEULE PLUME : ce module compose un document et un tampon, il n'écrit aucun fichier.

BUDGET (plan : 100 352 triangles en moins de 20 s), MESURÉ le 05/10/2026 par tests/mesure_etabli_outils.py creuser :
tore de 100 352 triangles, paroi 0,05 : 1,9 s ; paroi 0,9 > rayon du tube 0,7, tout effondré, dichotomie complète :
5,2 s (paroi qui tient trouvée : 0,6996). Le modèle réel de 144 274 triangles est REFUSÉ — non fermé, 4 arêtes.
"""
from __future__ import annotations

import math

from app.services.mesh_cut import _ajouter_flottants, _ajouter_indices
from app.services.mesh_edit import lire_accesseur
from app.services.mesh_edit import _extraire_doc, _l, _mat_locale, _mat_mul, _monde_des_ancetres, ecrire_glb, lire_glb

MAX_TRIS = 200_000          # borne du budget mesuré (voir tests/mesure_etabli_outils.py creuser)
PLAFOND = 3.0               # décalage maximal d'un sommet, en parois (arête vive)
_PAS_DICHOTOMIE = 12
_TOL_SOUDURE = 1e-6         # fraction de la diagonale de la pièce
LIMITE = ("une partie plus mince que deux parois, sur une pièce par ailleurs épaisse, peut se traverser sans être "
          "comptée : vérifie les zones fines dans le slicer")


def _croix(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _volume(pos, tris):
    return sum((pos[a][0] * (pos[b][1] * pos[c][2] - pos[b][2] * pos[c][1])
                - pos[a][1] * (pos[b][0] * pos[c][2] - pos[b][2] * pos[c][0])
                + pos[a][2] * (pos[b][0] * pos[c][1] - pos[b][1] * pos[c][0])) / 6.0 for a, b, c in tris)


def souder_positions(pos, tol):
    """-> (positions uniques, carte sommet → index soudé). Par position SEULE : c'est la géométrie qu'on décale."""
    vus, uniques, carte = {}, [], []
    for p in pos:
        k = (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
        j = vus.get(k)
        if j is None:
            j = vus[k] = len(uniques)
            uniques.append(p)
        carte.append(j)
    return uniques, carte


def aretes_fautives(tris) -> int:
    """Arêtes (non orientées) vues un nombre de fois différent de deux : 0 = fermé et manifold."""
    c = {}
    for a, b, d in tris:
        for x, y in ((a, b), (b, d), (d, a)):
            k = (x, y) if x < y else (y, x)
            c[k] = c.get(k, 0) + 1
    return sum(1 for v in c.values() if v != 2)


def _angle(o, a, b):
    u = (a[0] - o[0], a[1] - o[1], a[2] - o[2])
    v = (b[0] - o[0], b[1] - o[1], b[2] - o[2])
    nu = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
    nv = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if nu < 1e-30 or nv < 1e-30:
        return 0.0
    return math.acos(max(-1.0, min(1.0, (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (nu * nv))))


def decalages(pos, tris, signe):
    """Le décalage UNITAIRE de chaque sommet (vers le dedans = −décalage) et le nombre de sommets plafonnés.
    Normale du sommet moyennée par ANGLE au sommet — et non par aire : la moyenne par aire dépend de la
    triangulation (mesuré 05/10 : au coin d'un cube dont une face porte deux triangles et l'autre un, elle penche et
    quatre coins sortaient « plafonnés » à tort). Facteur 1 / min(n_sommet · n_face), plafonné à PLAFOND."""
    acc = [[0.0, 0.0, 0.0] for _ in pos]
    faces = []
    for t in tris:
        a, b, c = pos[t[0]], pos[t[1]], pos[t[2]]
        n = _croix(a, b, c)
        d = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        f = None if d < 1e-30 else (n[0] * signe / d, n[1] * signe / d, n[2] * signe / d)
        faces.append(f)
        if f is None:
            continue
        for s, (o, x, y) in zip(t, ((a, b, c), (b, c, a), (c, a, b))):
            w = _angle(o, x, y)
            acc[s][0] += f[0] * w; acc[s][1] += f[1] * w; acc[s][2] += f[2] * w
    nv = []
    for n in acc:
        d = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        nv.append(None if d < 1e-30 else (n[0] / d, n[1] / d, n[2] / d))
    mini = [1.0] * len(pos)
    for t, f in zip(tris, faces):
        if f is None:
            continue
        for s in t:
            if nv[s] is not None:
                m = nv[s][0] * f[0] + nv[s][1] * f[1] + nv[s][2] * f[2]
                if m < mini[s]:
                    mini[s] = m
    out, plafonnes = [], 0
    for s, n in enumerate(nv):
        if n is None:
            out.append((0.0, 0.0, 0.0)); plafonnes += 1
            continue
        k = 1.0 / mini[s] if mini[s] > 1.0 / PLAFOND else PLAFOND
        if mini[s] <= 1.0 / PLAFOND:
            plafonnes += 1
        out.append((n[0] * k, n[1] * k, n[2] * k))
    return out, plafonnes


def _interieur(pos, dec, paroi):
    return [(p[0] - o[0] * paroi, p[1] - o[1] * paroi, p[2] - o[2] * paroi) for p, o in zip(pos, dec)]


def effondres(pos, dec, tris, paroi, signe=1.0) -> int:
    """Combien de triangles retournent leur normale sous ce décalage — ou TOUS si la peau intérieure entière s'est
    retournée : volume intérieur de signe opposé à l'extérieur. C'est le cas d'une plaque plus mince que deux parois
    (les deux faces se croisent par translation, aucune normale ne bascule) et du cube creusé au-delà de sa
    demi-arête (symétrie centrale : les normales restent les mêmes vecteurs)."""
    dedans = _interieur(pos, dec, paroi)
    if _volume(dedans, tris) * signe <= 0.0:
        return len(tris)
    n = 0
    for a, b, c in tris:
        av = _croix(pos[a], pos[b], pos[c])
        ap = _croix(dedans[a], dedans[b], dedans[c])
        if av[0] * ap[0] + av[1] * ap[1] + av[2] * ap[2] <= 0.0:
            n += 1
    return n


def _echelle_uniforme(m: list):
    """L'échelle d'une matrice monde glTF (colonne-majeure), ou None si elle n'est pas uniforme."""
    cols = [math.sqrt(m[k] ** 2 + m[k + 1] ** 2 + m[k + 2] ** 2) for k in (0, 4, 8)]
    if min(cols) <= 0 or max(cols) / min(cols) - 1.0 > 1e-6:
        return None
    return cols[0]


def creuser(data: bytes, noeuds, paroi):
    """(glb, rapport). `paroi` en unités du MONDE (> 0) ; `noeuds` None = toutes les pièces de la scène active."""
    from app.services import print3d
    if not isinstance(paroi, (int, float)) or isinstance(paroi, bool) or not math.isfinite(paroi) or paroi <= 0:
        raise ValueError("paroi : un nombre fini > 0 est attendu (en unités du modèle)")
    paroi = float(paroi)
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
                raise ValueError(f"noeud {i} sans maillage — aucune pièce à creuser")
    if not cibles:
        raise ValueError("aucune pièce à creuser dans la scène active")

    # ── lecture et jugement de TOUTES les pièces avant la moindre écriture ──────────────────────────────────────
    lues, total = [], 0
    for i in cibles:
        nd = nodes[i]
        nom = nd.get("name") or f"noeud_{i}"
        if nd.get("skin") is not None:
            raise ValueError(f"{nom} : pièce animée (skin) — ses sommets bougent avec l'armature, une paroi n'y a pas "
                             "d'épaisseur fixe")
        s = _echelle_uniforme(_mat_mul(_monde_des_ancetres(doc, i), _mat_locale(nd)))
        if s is None:
            raise ValueError(f"{nom} : échelle non uniforme — une même paroi n'aurait pas la même épaisseur selon "
                             "l'axe. Applique d'abord une échelle uniforme")
        prims = _l(_l(doc, "meshes")[nd["mesh"]], "primitives")
        pos, tris = [], []
        for pr in prims:
            attrs = pr.get("attributes") or {}
            if pr.get("mode", 4) != 4 or "POSITION" not in attrs:
                raise ValueError(f"{nom} : primitive non TRIANGLES ou sans POSITION — hors périmètre")
            if pr.get("targets"):
                raise ValueError(f"{nom} : morph targets — la forme change à l'animation, hors périmètre")
            p = lire_accesseur(doc, binc, attrs["POSITION"])
            idx = ([t[0] for t in lire_accesseur(doc, binc, pr["indices"])] if pr.get("indices") is not None
                   else list(range(len(p))))
            base = len(pos)
            pos += [tuple(float(c) for c in v) for v in p]
            tris += [(base + idx[k], base + idx[k + 1], base + idx[k + 2]) for k in range(0, len(idx) - 2, 3)]
        total += len(tris)
        if total > MAX_TRIS:
            raise ValueError(f"plus de {MAX_TRIS} triangles — le creusage dépasse son budget de temps mesuré. "
                             "Décime d'abord (bouton « Décimer »), puis creuse.")
        if not tris:
            raise ValueError(f"{nom} : aucun triangle")
        xs, ys, zs = [q[0] for q in pos], [q[1] for q in pos], [q[2] for q in pos]
        diag = math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2 + (max(zs) - min(zs)) ** 2) or 1.0
        uniques, carte = souder_positions(pos, _TOL_SOUDURE * diag)
        st = [(carte[a], carte[b], carte[c]) for a, b, c in tris]
        st = [t for t in st if len(set(t)) == 3]
        fautives = aretes_fautives(st)
        if fautives:
            raise ValueError(f"{nom} : maillage non fermé ({fautives} arête(s) de bord ou partagée(s) par plus de "
                             "deux faces) — une coque ouverte n'a pas d'intérieur. « Réparer le maillage », trous "
                             "cochés, puis creuse")
        lues.append((i, nom, s, uniques, st))

    # ── la coque ─────────────────────────────────────────────────────────────────────────────────────────────────
    tampon, pieces = bytearray(binc), []
    for i, nom, s, uniques, st in lues:
        nd, locale = nodes[i], paroi / s
        signe = 1.0 if _volume(uniques, st) >= 0 else -1.0
        dec, plafonnes = decalages(uniques, st, signe)
        eff = effondres(uniques, dec, st, locale, signe)
        bas = locale
        if eff:
            bas, haut = 0.0, locale
            for _ in range(_PAS_DICHOTOMIE):
                mid = (bas + haut) / 2
                if effondres(uniques, dec, st, mid, signe):
                    haut = mid
                else:
                    bas = mid
        partage = sorted(j for j in range(len(nodes)) if j != i and nodes[j].get("mesh") == nd["mesh"])
        if partage:                                    # cloné : creuser l'une ne creuse pas l'autre
            src = _l(doc, "meshes")[nd["mesh"]]
            doc["meshes"].append({**src, "primitives": [dict(p) for p in _l(src, "primitives")]})
            nd["mesh"] = len(doc["meshes"]) - 1
        mesh = doc["meshes"][nd["mesh"]]
        dedans = _interieur(uniques, dec, locale)
        interieure = {"attributes": {"POSITION": _ajouter_flottants(doc, tampon, dedans, 3, True)},
                      # TOUJOURS l'enroulement inverse de la peau extérieure : la coque reste cohérente avec elle,
                      # même quand le fichier a ses normales rentrantes (on n'y corrige pas l'extérieur : c'est le
                      # rôle de « Réparer le maillage »)
                      "indices": _ajouter_indices(doc, tampon, [(b, a, c) for a, b, c in st])}
        if "material" in mesh["primitives"][0]:
            interieure["material"] = mesh["primitives"][0]["material"]
        mesh["primitives"].append(interieure)
        pieces.append({"noeud_avant": i, "nom": nom, "triangles_avant": len(st), "triangles_interieurs": len(st),
                       "paroi": paroi, "echelle_monde": s, "effondres": eff, "paroi_max": round(bas * s, 12),
                       "plafonnes": plafonnes, "normales_rentrantes": signe < 0, "partage_avec": partage})
    doc["buffers"] = [{"byteLength": len(tampon)}]
    out, neuf, m_node = _extraire_doc(doc, bytes(tampon), racines)
    for p in pieces:
        p["noeud_apres"] = m_node.get(p["noeud_avant"])
    total_eff = sum(p["effondres"] for p in pieces)
    total_plaf = sum(p["plafonnes"] for p in pieces)
    dits = []
    if total_eff:
        dits.append(f"{total_eff} triangle(s) effondré(s) : la paroi est plus épaisse que le creux le plus serré, le "
                    "solide s'auto-intersecte")
    if total_plaf:
        dits.append(f"{total_plaf} sommet(s) sur arête vive : décalage plafonné à {PLAFOND:g} parois, la paroi y est "
                    "plus mince que demandé")
    rapport = {"paroi": paroi, "pieces": pieces,
               "paroi_max": min(p["paroi_max"] for p in pieces),
               "avertissement": " ; ".join(dits) or None, "limite": LIMITE}
    return ecrire_glb(out, neuf), rapport
