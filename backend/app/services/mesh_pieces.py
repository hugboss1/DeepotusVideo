# -*- coding: utf-8 -*-
"""Pièces mobiles d'un maillage — t342 (lot Scenario B6, 29/10/2026).

Chez Scenario, « Tripo Segmentation » découpe une voiture en 33 pièces pour que les roues tournent. Ici, deux voies,
et la PREMIÈRE est locale et gratuite :

1. LES ÎLOTS (`analyser`, `separer`) : un maillage généré est souvent fait de morceaux qui ne se touchent pas — quatre
   roues, une caisse, un couvercle posé. Chaque composante connexe devient une pièce. La connexité est celle des
   POSITIONS soudées (deux sommets au même endroit sont un seul point), pas celle des index : une couture d'UV
   dédouble les sommets sans couper la matière, et la suivre découperait une roue en quartiers.
2. LA SEGMENTATION IA (`segmenter_par_ia`) : `tripo3d/tripo/segment` sur fal, payante, pour les pièces SOUDÉES que la
   connexité ne sépare pas. Page fal relue le 29/10/2026 (fal.ai/models/tripo3d/tripo/segment/llms.txt) : entrée
   `mesh_url` (GLB, OBJ, FBX, STL, 150 Mo au plus), sortie `model_mesh` (« May be GLB or FBX »), `model_urls`
   (glb, fbx, base_model, pbr_model), `part_names` (« when reported by Tripo »), `rendered_image`. Prix affiché
   « $0.01 per units » sans dire l'unité ; l'exemple de la doc Tripo (developers.tripo3d.com, mesh-segment) montre
   `credits_consumed: 40` → le devis compte 40 unités, soit 0,40 $ — une ESTIMATION, rapprochée par les plafonds.
   Le résultat repasse par `separer(par="noeuds")` : un nœud par pièce, pivot recentré, noms de Tripo.

Dans les deux cas, chaque pièce devient UN NŒUD à la racine, son ORIGINE (le pivot) au centre de sa boîte — l'axe
d'une roue, le milieu d'un couvercle — et ses sommets exprimés autour de lui : un moteur de jeu la fait tourner sur
elle-même sans rien régler. Les matières, UV, normales et couleurs SUIVENT (chaque attribut est recopié sommet par
sommet), contrairement au booléen qui n'écrit que de la géométrie. Refus parlants, AVANT tout calcul : compression
draco / meshopt / quantization (prendre la source), maillage riggé (segmenter AVANT le rig), cibles de morphose.

Module sans `settings` (sauf la voie IA) : de la manipulation d'octets pure. La plume reste `mesh_edit.ecrire_glb`.
"""
from __future__ import annotations

import math
import re
import struct

# ── réglages ─────────────────────────────────────────────────────────────────
MAX_PIECES = 64            # au-delà, les plus petites îlots se regroupent en « détails » : 300 boulons ne s'animent pas
MIN_TRIANGLES = 8          # sous ce compte, un îlot est un détail (un rivet, une écaille), pas une pièce mobile
SOUDURE = 1e-5             # deux sommets à moins de SOUDURE × diagonale du nœud sont le même point

ENDPOINT_IA = "tripo3d/tripo/segment"
UNITES_IA = 40             # exemple de la doc Tripo (credits_consumed) — estimation, voir l'en-tête
USD_UNITE_IA = 0.01        # page fal : « $0.01 per units »
MAX_OCTETS_IA = 150 * 1024 * 1024

_REFUS = {
    "KHR_draco_mesh_compression": "GLB compressé draco : prends la source non compressée (model.glb) pour la découper",
    "EXT_meshopt_compression": "GLB compressé meshopt : prends la source non compressée (model.glb) pour la découper",
    "KHR_mesh_quantization": "GLB quantifié : les positions ne sont pas en flottants, le pivot ne peut pas être recentré",
}

# Les noms proposés, par forme et par langue. Ce sont des DONNÉES (le nom du nœud dans le GLB), lues par le moteur de
# jeu : la langue est celle de l'interface au moment de l'analyse, et l'utilisateur les renomme avant d'écrire.
NOMS = {
    "corps": {"fr": "corps", "en": "body"},
    "roue": {"fr": "roue", "en": "wheel"},
    "couvercle": {"fr": "couvercle", "en": "lid"},
    "plaque": {"fr": "plaque", "en": "panel"},
    "tige": {"fr": "tige", "en": "rod"},
    "bloc": {"fr": "piece", "en": "part"},
    "details": {"fr": "details", "en": "details"},
}


# ── lecture ──────────────────────────────────────────────────────────────────

def _verifier(doc: dict) -> None:
    for ext in (doc.get("extensionsRequired") or []) + (doc.get("extensionsUsed") or []):
        if ext in _REFUS:
            raise ValueError(_REFUS[ext])
    if doc.get("skins"):
        raise ValueError("maillage riggé (squelette) : découpe les pièces AVANT le rig, sinon les poids des os ne "
                         "suivraient pas")
    for m in doc.get("meshes") or []:
        for p in m.get("primitives") or []:
            if p.get("targets"):
                raise ValueError("cibles de morphose (blend shapes) : hors périmètre de la découpe en pièces")
            if p.get("mode", 4) != 4:
                raise ValueError(f"primitive en mode {p.get('mode')} : seuls les TRIANGLES se découpent")
            if "POSITION" not in (p.get("attributes") or {}):
                raise ValueError("primitive sans POSITION")


def _noeuds_maillage(doc: dict):
    """[(index de nœud, matrice monde ligne-majeur)] des nœuds qui portent un maillage, dans l'ordre de la scène."""
    from app.services.print3d import _IDENTITE, _mat_locale, _mat_mul
    out, vus = [], set()

    def visiter(i, parent):
        if i in vus:
            raise ValueError("graphe de nœuds cyclique")
        vus.add(i)
        nd = doc["nodes"][i]
        monde = _mat_mul(parent, _mat_locale(nd))
        if "mesh" in nd:
            out.append((i, monde))
        for e in nd.get("children") or []:
            visiter(e, monde)

    scenes = doc.get("scenes") or []
    racines = scenes[doc.get("scene", 0)].get("nodes", []) if scenes else list(range(len(doc.get("nodes") or [])))
    for i in racines:
        visiter(i, _IDENTITE)
    return out


def _lire_primitives(doc: dict, binc: bytes, im: int) -> list[dict]:
    from app.services.mesh_edit import lire_accesseur
    prims = []
    for k, p in enumerate(doc["meshes"][im].get("primitives") or []):
        acc = doc["accessors"][p["attributes"]["POSITION"]]
        if acc.get("componentType") != 5126 or acc.get("type") != "VEC3":
            raise ValueError("POSITION hors flottants VEC3 : le pivot ne peut pas être recentré")
        pos = lire_accesseur(doc, binc, p["attributes"]["POSITION"], quoi="la découpe en pièces")
        if "indices" in p:
            idx = [v[0] for v in lire_accesseur(doc, binc, p["indices"], quoi="la découpe en pièces")]
        else:
            idx = list(range(len(pos)))
        tris = [(idx[j], idx[j + 1], idx[j + 2]) for j in range(0, len(idx) - 2, 3)]
        prims.append({"k": k, "prim": p, "pos": pos, "tris": tris})
    return prims


# ── les îlots ────────────────────────────────────────────────────────────────

def _ilots(prims: list[dict]) -> list[list[tuple[int, int]]]:
    """Composantes connexes d'un nœud, toutes primitives confondues (une roue faite d'un pneu et d'une jante en deux
    matières reste UNE roue). Rend des listes de (primitive, triangle) triées du plus gros îlot au plus petit."""
    pts = [p for pr in prims for p in pr["pos"]]
    if not pts:
        return []
    diag = math.dist([min(p[c] for p in pts) for c in range(3)], [max(p[c] for p in pts) for c in range(3)])
    pas = max(diag * SOUDURE, 1e-12)
    parent: dict = {}

    def trouver(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def unir(a, b):
        ra, rb = trouver(a), trouver(b)
        if ra != rb:
            parent[rb] = ra

    cle = {}
    for pr in prims:
        for v, p in enumerate(pr["pos"]):
            q = (round(p[0] / pas), round(p[1] / pas), round(p[2] / pas))
            cle[(pr["k"], v)] = q
    for pr in prims:
        for a, b, c in pr["tris"]:
            qa, qb, qc = cle[(pr["k"], a)], cle[(pr["k"], b)], cle[(pr["k"], c)]
            unir(qa, qb)
            unir(qa, qc)
    groupes: dict = {}
    for pr in prims:
        for t, (a, _b, _c) in enumerate(pr["tris"]):
            groupes.setdefault(trouver(cle[(pr["k"], a)]), []).append((pr["k"], t))
    return sorted(groupes.values(), key=len, reverse=True)


def _boite(pts):
    lo = [min(p[c] for p in pts) for c in range(3)]
    hi = [max(p[c] for p in pts) for c in range(3)]
    return lo, hi


def _forme(dims: list[float]) -> str:
    """La silhouette d'une boîte : un disque (b ≈ c, a mince) est une roue ; une dalle, une plaque ; une barre, une
    tige. Grossier et DIT comme tel : c'est une proposition de nom, l'utilisateur renomme avant d'écrire."""
    a, b, c = sorted(dims)
    if c <= 0:
        return "bloc"
    if b / c >= 0.8 and a / c <= 0.6:
        return "roue"
    if a <= 0.2 * b:
        return "plaque"
    if b <= 0.3 * c:
        return "tige"
    return "bloc"


def _decouper(data: bytes, *, par: str, min_triangles: int):
    from app.services.mesh_edit import lire_glb
    from app.services.print3d import _appliquer
    doc, binc = lire_glb(data)
    _verifier(doc)
    if par not in ("composantes", "noeuds"):
        raise ValueError(f"découpe « {par} » — composantes ou noeuds")
    pieces = []
    maillages = _noeuds_maillage(doc)
    for ni, monde in maillages:
        prims = _lire_primitives(doc, binc, doc["nodes"][ni]["mesh"])
        if par == "noeuds" and len(maillages) == 1 and len(prims) > 1:
            # un seul nœud à plusieurs primitives (une pièce par matière, comme certains GLB segmentés) : une pièce
            # par primitive
            groupes = [[(pr["k"], t) for t in range(len(pr["tris"]))] for pr in prims]
        elif par == "noeuds":
            groupes = [[(pr["k"], t) for pr in prims for t in range(len(pr["tris"]))]]
        else:
            groupes = _ilots(prims)
        gros = [g for g in groupes if len(g) >= min_triangles] if par == "composantes" else groupes
        petits = [x for g in groupes if len(g) < min_triangles for x in g] if par == "composantes" else []
        for g in gros:
            pieces.append({"noeud": ni, "monde": monde, "prims": prims, "tris": g, "forme": None})
        if petits:
            pieces.append({"noeud": ni, "monde": monde, "prims": prims, "tris": petits, "forme": "details"})
    pieces = [p for p in pieces if p["tris"]]
    if not pieces:
        raise ValueError("aucun triangle à découper")
    fusion = 0
    if len(pieces) > MAX_PIECES:
        # les plus petites rejoignent le « détails » de LEUR nœud : deux nœuds n'ont pas le même espace local, et
        # mêler leurs sommets sous un seul pivot déplacerait l'un des deux
        pieces.sort(key=lambda p: len(p["tris"]), reverse=True)
        garde, reste = pieces[:MAX_PIECES - 1], pieces[MAX_PIECES - 1:]
        fusion = len(reste)
        par_noeud: dict = {}
        for r in reste:
            d = par_noeud.setdefault(r["noeud"], {"noeud": r["noeud"], "monde": r["monde"], "prims": r["prims"],
                                                  "tris": [], "forme": "details"})
            d["tris"].extend(r["tris"])
        pieces = garde + list(par_noeud.values())
    # mesures : boîte LOCALE (le pivot, dans l'espace du nœud) et boîte MONDE (la forme et la place)
    for p in pieces:
        loc, mon = [], []
        pr = {x["k"]: x for x in p["prims"]}
        for k, t in p["tris"]:
            for v in pr[k]["tris"][t]:
                q = pr[k]["pos"][v]
                loc.append(q)
                mon.append(_appliquer(p["monde"], q))
        lo, hi = _boite(loc)
        p["pivot_local"] = [(lo[c] + hi[c]) / 2 for c in range(3)]
        wlo, whi = _boite(mon)
        p["boite_monde"] = (wlo, whi)
        p["pivot"] = [round((wlo[c] + whi[c]) / 2, 6) for c in range(3)]
        p["taille"] = [round(whi[c] - wlo[c], 6) for c in range(3)]
        p["n"] = len(p["tris"])
    # l'ordre de lecture : de la plus grande pièce à la plus petite, les « détails » en dernier. Par nœud, l'ordre
    # du fichier est GARDÉ : les `part_names` de Tripo lui correspondent un à un
    if par == "composantes":
        pieces.sort(key=lambda p: (p["forme"] == "details", -(p["taille"][0] * p["taille"][1] * p["taille"][2]), -p["n"]))
    return doc, binc, pieces, fusion


def _nommer(pieces: list[dict], langue: str) -> None:
    """Noms proposés : la plus grande pièce est le corps ; une plaque haute qui couvre la moitié de l'emprise est un
    couvercle ; le reste selon sa forme, numéroté."""
    lg = "en" if langue == "en" else "fr"
    tous = [c for p in pieces for c in (p["boite_monde"][0], p["boite_monde"][1])]
    lo, hi = _boite(tous)
    haut = hi[1] - lo[1]
    emprise = max((hi[0] - lo[0]) * (hi[2] - lo[2]), 1e-12)
    # la plus GRANDE (volume de sa boîte), pas la plus dense : une roue lissée porte plus de triangles qu'une caisse
    principale = max((p for p in pieces if p["forme"] != "details"),
                     key=lambda p: p["taille"][0] * p["taille"][1] * p["taille"][2], default=None)
    for p in pieces:
        if p["forme"] is None:
            f = _forme(p["taille"])
            if p is principale and len(pieces) > 1:
                f = "corps"
            elif f == "plaque" and haut > 0 and p["pivot"][1] >= lo[1] + 0.75 * haut \
                    and p["taille"][0] * p["taille"][2] >= 0.5 * emprise:
                f = "couvercle"
            p["forme"] = f
    vus: dict = {}
    for p in pieces:
        base = NOMS[p["forme"]][lg]
        vus[base] = vus.get(base, 0) + 1
    rang: dict = {}
    for p in pieces:
        base = NOMS[p["forme"]][lg]
        rang[base] = rang.get(base, 0) + 1
        p["nom"] = base if vus[base] == 1 else f"{base}_{rang[base]}"


def _resume(pieces):
    return [{"index": i, "nom": p["nom"], "forme": p["forme"], "triangles": p["n"],
             "pivot": p["pivot"], "taille": p["taille"]} for i, p in enumerate(pieces)]


def analyser(data: bytes, *, langue: str = "fr", min_triangles: int = MIN_TRIANGLES) -> dict:
    """LECTURE : les îlots du maillage et les noms proposés, sans rien écrire."""
    _doc, _binc, pieces, fusion = _decouper(data, par="composantes", min_triangles=_min(min_triangles))
    _nommer(pieces, langue)
    return {"pieces": _resume(pieces), "triangles": sum(p["n"] for p in pieces), "regroupees": fusion,
            "min_triangles": _min(min_triangles), "max_pieces": MAX_PIECES}


def _min(v) -> int:
    try:
        v = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"min_triangles « {v} » — un entier")
    if not 1 <= v <= 10_000:
        raise ValueError("min_triangles entre 1 et 10 000")
    return v


_NOM_SUR = re.compile(r"[^\w\-.]+", re.UNICODE)


def nom_sur(v, defaut: str) -> str:
    """Un nom de nœud lisible par Unity, Godot et Blender : lettres, chiffres, _ - . ; 64 caractères au plus."""
    s = _NOM_SUR.sub("_", str(v or "").strip()).strip("_.")[:64]
    return s or defaut


# ── écriture ─────────────────────────────────────────────────────────────────

def _fmt(acc: dict) -> tuple[str, int]:
    from app.services.mesh_edit import _COMPOSANTS, _NB_COMPOSANTS
    f, taille = _COMPOSANTS[acc["componentType"]]
    n = _NB_COMPOSANTS[acc["type"]]
    return "<" + f * n, taille * n


def separer(data: bytes, *, par: str = "composantes", noms=None, langue: str = "fr",
            min_triangles: int = MIN_TRIANGLES) -> tuple[bytes, dict]:
    """Écrit le GLB découpé : un nœud par pièce, à la racine, origine au centre de la pièce. `noms` (liste, dans
    l'ordre d'`analyser`) remplace les noms proposés ; un nom vide garde la proposition, un doublon prend un suffixe."""
    from app.services.mesh_edit import ecrire_glb, lire_accesseur
    from app.services.print3d import _mat_mul
    doc, binc, pieces, fusion = _decouper(data, par=par, min_triangles=_min(min_triangles))
    if par == "noeuds":   # le nom du nœud d'origine d'abord (Tripo nomme ses pièces), la forme sinon
        _nommer(pieces, langue)
        for p in pieces:
            nd = doc["nodes"][p["noeud"]]
            nm = nd.get("name") or (doc["meshes"][nd["mesh"]].get("name") if "mesh" in nd else None)
            if nm:
                p["nom"] = nm
    else:
        _nommer(pieces, langue)
    if noms is not None:
        if not isinstance(noms, list) or len(noms) > len(pieces):
            raise ValueError(f"noms : une liste de {len(pieces)} noms au plus, dans l'ordre de l'analyse")
        for p, n in zip(pieces, noms):
            if str(n or "").strip():
                p["nom"] = str(n)
    pris: dict = {}
    for i, p in enumerate(pieces):
        n = nom_sur(p["nom"], f"piece_{i + 1}")
        if n in pris:
            pris[n] += 1
            n = f"{n}_{pris[n]}"
        pris.setdefault(n, 1)
        p["nom"] = n

    out = bytearray()
    vues, acces, meshes, nodes = [], [], [], []

    def vue(octets: bytes, cible=None) -> int:
        while len(out) % 4:
            out.append(0)
        v = {"buffer": 0, "byteOffset": len(out), "byteLength": len(octets)}
        if cible:
            v["target"] = cible
        vues.append(v)
        out.extend(octets)
        return len(vues) - 1

    # les images embarquées suivent (textures) : leurs octets sont recopiés tels quels
    images = []
    for im in doc.get("images") or []:
        im = dict(im)
        if "bufferView" in im:
            bv = doc["bufferViews"][im["bufferView"]]
            debut = bv.get("byteOffset", 0)
            im["bufferView"] = vue(bytes(binc[debut:debut + bv["byteLength"]]))
        images.append(im)

    cache: dict = {}   # (primitive, accesseur) -> valeurs décodées, lues une fois

    def valeurs(im_, k, a):
        c = (im_, k, a)
        if c not in cache:
            cache[c] = lire_accesseur(doc, binc, a, quoi="la découpe en pièces")
        return cache[c]

    for p in pieces:
        c = p["pivot_local"]
        prims_out = []
        for s in (p,):
            im_ = doc["nodes"][s["noeud"]]["mesh"]
            pr = {x["k"]: x for x in s["prims"]}
            par_prim: dict = {}
            for k, t in s["tris"]:
                par_prim.setdefault(k, []).append(pr[k]["tris"][t])
            for k, tris in sorted(par_prim.items()):
                src = pr[k]["prim"]
                remap, ordre = {}, []
                for tri in tris:
                    for v in tri:
                        if v not in remap:
                            remap[v] = len(ordre)
                            ordre.append(v)
                attrs = {}
                for nom_a, ia in sorted(src["attributes"].items()):
                    a = doc["accessors"][ia]
                    vals = valeurs(im_, k, ia)
                    sel = [vals[v] for v in ordre]
                    if nom_a == "POSITION":
                        sel = [(q[0] - c[0], q[1] - c[1], q[2] - c[2]) for q in sel]
                    f, _ = _fmt(a)
                    octets = b"".join(struct.pack(f, *v) for v in sel)
                    na = {"bufferView": vue(octets, 34962), "componentType": a["componentType"],
                          "count": len(sel), "type": a["type"]}
                    if a.get("normalized"):
                        na["normalized"] = True
                    if nom_a == "POSITION":
                        na["min"] = [min(q[j] for q in sel) for j in range(3)]
                        na["max"] = [max(q[j] for q in sel) for j in range(3)]
                    acces.append(na)
                    attrs[nom_a] = len(acces) - 1
                idx = [remap[v] for tri in tris for v in tri]
                court = len(ordre) < 65536
                octets = struct.pack(("<%dH" if court else "<%dI") % len(idx), *idx)
                acces.append({"bufferView": vue(octets, 34963), "componentType": 5123 if court else 5125,
                              "count": len(idx), "type": "SCALAR"})
                np_ = {"attributes": attrs, "indices": len(acces) - 1, "mode": 4}
                if "material" in src:
                    np_["material"] = src["material"]
                prims_out.append(np_)
        meshes.append({"name": p["nom"], "primitives": prims_out})
        # la matrice monde du nœud d'origine, puis la translation vers le pivot : le monde ne bouge pas d'un iota
        t = [1.0, 0.0, 0.0, c[0], 0.0, 1.0, 0.0, c[1], 0.0, 0.0, 1.0, c[2], 0.0, 0.0, 0.0, 1.0]
        m = _mat_mul(p["monde"], t)
        noeud = {"name": p["nom"], "mesh": len(meshes) - 1}
        ident = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        if all(abs(m[i] - ident[i]) < 1e-12 for i in (0, 1, 2, 4, 5, 6, 8, 9, 10)):
            noeud["translation"] = [m[3], m[7], m[11]]
        else:
            noeud["matrix"] = [m[r * 4 + col] for col in range(4) for r in range(4)]   # colonne-majeur glTF
        nodes.append(noeud)

    while len(out) % 4:
        out.append(0)
    neuf = {"asset": {"version": "2.0", "generator": "Deepotus pièces mobiles (t342)"}, "scene": 0,
            "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
            "accessors": acces, "bufferViews": vues, "buffers": [{"byteLength": len(out)}]}
    for cle in ("materials", "textures", "samplers"):
        if doc.get(cle):
            neuf[cle] = doc[cle]
    if images:
        neuf["images"] = images
    ext = [e for e in (doc.get("extensionsUsed") or []) if e not in _REFUS]
    if ext:
        neuf["extensionsUsed"] = ext
    perdus = [i for i, nd in enumerate(doc.get("nodes") or []) if "mesh" not in nd and ("camera" in nd
                                                                                        or "extensions" in nd)]
    rapport = {"par": par, "pieces": _resume(pieces), "regroupees": fusion,
               "triangles": sum(p["n"] for p in pieces),
               "pivot": "origine de chaque pièce au centre de sa boîte (axe d'une roue, milieu d'un couvercle)",
               "matieres": "matières, UV, normales et couleurs recopiées sommet par sommet",
               "perdus": (f"{len(perdus)} nœud(s) sans maillage (caméra, lumière) non repris" if perdus else "")}
    return ecrire_glb(neuf, bytes(out)), rapport


# ── la voie IA (payante) ─────────────────────────────────────────────────────

def devis_ia() -> dict:
    """Le devis AVANT tout clic : le prix vient de la grille des tarifs (`pricing`, clé `tripo_segment_usd`,
    modifiable dans les Réglages), pas d'une constante d'ici."""
    from app.services import pricing
    e = pricing.estimate({"kind": "asset3d_segment"})
    return {"endpoint": ENDPOINT_IA, "usd": round(float(e["total_usd"]), 2), "lignes": e["breakdown"],
            "unites": UNITES_IA, "usd_unite": USD_UNITE_IA, "estimation": True, "max_octets": MAX_OCTETS_IA}


async def segmenter_par_ia(data: bytes) -> dict:
    """Envoie le GLB à Tripo (fal) et rapatrie le GLB segmenté. N'APPELER QU'APRÈS la garde des plafonds : c'est la
    route qui la pose (`_plafond`), et le recensement AST (test_plafonds_garde) le vérifie. Rend {glb, part_names,
    apercu}. Le FBX que Tripo peut rendre est refusé (on ne sait pas l'écrire) — on prend alors `model_urls.glb`."""
    import tempfile
    from pathlib import Path
    from app.services import asset3d_service as A3
    import fal_client
    if len(data) > MAX_OCTETS_IA:
        raise ValueError(f"maillage de {len(data) // (1024 * 1024)} Mo : Tripo en accepte 150 au plus")
    with tempfile.TemporaryDirectory(prefix="dzpieces_") as tmp:
        src = Path(tmp) / "source.glb"
        src.write_bytes(data)
        url = await A3._upload(src)
        try:
            res = await fal_client.subscribe_async(ENDPOINT_IA, arguments={"mesh_url": url}, with_logs=False)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"fal.ai : {e}") from e
        candidats = []
        mm = res.get("model_mesh") if isinstance(res, dict) else None
        if isinstance(mm, dict) and mm.get("url"):
            candidats.append(mm["url"])
        mu = res.get("model_urls") if isinstance(res, dict) else None
        if isinstance(mu, dict):
            for k in ("glb", "pbr_model", "base_model"):
                v = mu.get(k)
                if isinstance(v, dict) and v.get("url"):
                    candidats.append(v["url"])
        for u in candidats:
            dest = Path(tmp) / "segmente.glb"
            A3._download(u, dest)
            octets = dest.read_bytes()
            if octets[:4] == b"glTF":
                apercu = res.get("rendered_image") if isinstance(res, dict) else None
                return {"glb": octets, "part_names": [str(x) for x in (res.get("part_names") or [])],
                        "apercu": apercu.get("url") if isinstance(apercu, dict) else None}
        raise RuntimeError("Tripo n'a rendu aucun GLB (FBX seul ?) : la découpe n'a pas pu être relue")
