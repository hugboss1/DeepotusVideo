# -*- coding: utf-8 -*-
"""P9 Forge 3D — géométrie et écriture de scène, PURES (zéro dépendance HTTP).

Couture intra-pièce actée par la revue finale de la 2a (legs 6) : forge3d.py
garde le contrat HTTP (routes, bornes, blocs miroir) et RÉEXPORTE ces noms —
les tests et l'API ne changent pas. Règle 8 inchangée : aucune importation
d'une autre pièce du lab.
"""
from __future__ import annotations

import json
import math
import struct


# ── LA GÉOMÉTRIE LOCALE — PLAN, RELIEF, MESURES ─────────────────────────────
# `quad_mesh`/`relief_mesh` produisent le maillage minimal qu'un traitement
# `plane`/`relief` du graphe fabrique ; `mesh_measures` en tire la preuve de
# fermeture/volume — COPIE LOCALE réduite du principe de `mesh_report` de P8
# (règle 8 : zéro import pièce->pièce, même patron que `_dpi_to_ppm`/`_num`
# de forge3d.py). Type commun aux trois : {positions, normals, uvs, indices},
# consommé plus loin par `write_scene_glb` (Task 3).
def quad_mesh(w_mm: float, h_mm: float,
             uv_window: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
             ) -> dict:
    """Un quad aux dimensions de la carte, normale +z. `uv_window`
    (u0, v0, u1, v1) — défaut plein 0..1, rétrocompatible — INSET les UV
    émises dans cette fenêtre au lieu de la texture entière : voir le
    commentaire-contrainte au point d'appel (`post_build3d`) sur la
    différence toile/coupe que cette fenêtre réconcilie."""
    u0, v0, u1, v1 = uv_window
    return {
        "positions": [0.0, 0.0, 0.0, w_mm, 0.0, 0.0, w_mm, h_mm, 0.0,
                      0.0, h_mm, 0.0],
        "normals": [0.0, 0.0, 1.0] * 4,
        "uvs": [u0, v1, u1, v1, u1, v0, u0, v0],   # v inversé (image)
        "indices": [0, 1, 2, 0, 2, 3],
        "closed": False,             # un plan n'est pas un solide
    }


def relief_mesh(alpha_img, w_mm: float, h_mm: float, depth_mm: float,
                base_mm: float, grid: int,
                uv_window: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
                ) -> dict:
    """LA DALLE EN RELIEF : une grille (grid x grid') dont la face du dessus
    est déplacée par l'alpha de la couche (0 -> base, 255 -> base+depth), face
    du dessous plate à z=0, murs périphériques — un solide FERMÉ PAR
    CONSTRUCTION : chaque arête appartient à exactement deux triangles parce
    que dessus, dessous et murs partagent leurs anneaux de bord. C'est
    l'« extrusion » gratuite v1 : un vrai suivi de contour (marching squares +
    triangulation à trous) viendra si le besoin le prouve.

    `alpha_img` doit déjà être la région de COUPE (pas la toile — c'est
    l'appelant, `post_build3d`, qui croppe avant d'appeler ici : cette
    fonction n'a pas la géométrie du deck pour le faire elle-même).
    `uv_window` (u0, v0, u1, v1) — défaut plein 0..1, rétrocompatible — INSET
    les UV dans cette fenêtre pour que la texture (le PNG de toile complet,
    octets intacts) se plaque correctement sur une géométrie qui, elle, ne
    couvre que la coupe.

    Préconditions : bornes garanties par `clean_graph` (base_mm/depth_mm/grid)
    — hors de ce chemin, base_mm=0 dégénère les murs et w_mm=0 divise par
    zéro."""
    u0, v0, u1, v1 = uv_window
    gx = max(2, int(grid))
    gy = max(2, int(round(grid * (h_mm / w_mm))))
    a = alpha_img.convert("L").resize((gx + 1, gy + 1))
    px = list(a.getdata())          # (gx+1)*(gy+1) échantillons

    def z_at(i, j):
        return base_mm + (px[j * (gx + 1) + i] / 255.0) * depth_mm

    pos, uv = [], []
    # dessus : (gx+1)*(gy+1) sommets déplacés
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, z_at(i, j)]
            uv += [u0 + (i / gx) * (u1 - u0), v0 + (j / gy) * (v1 - v0)]
    top = lambda i, j: j * (gx + 1) + i                      # noqa: E731
    n_top = (gx + 1) * (gy + 1)
    # dessous : mêmes (x, y), z=0 (UV répliquées, sans importance au dos)
    for j in range(gy + 1):
        for i in range(gx + 1):
            pos += [i / gx * w_mm, (1.0 - j / gy) * h_mm, 0.0]
            uv += [u0 + (i / gx) * (u1 - u0), v0 + (j / gy) * (v1 - v0)]
    bot = lambda i, j: n_top + j * (gx + 1) + i              # noqa: E731

    # WINDING : avec y=(1-j/gy)*h, j=0 est le HAUT de carte ; l'ordre ci-dessous
    # donne une aire signée POSITIVE vue de +z (normales dehors), prouvé par le
    # test (closed ET volume>0 sur silhouette à trou). Garde-fou : une inversion
    # UNIFORME du maillage garde closed=True et ne flippe QUE le signe du volume
    # — c'est l'assertion volume>0 qui protège contre une régression, pas closed.
    idx = []
    for j in range(gy):
        for i in range(gx):
            aa, bb = top(i, j), top(i + 1, j)
            cc, dd = top(i + 1, j + 1), top(i, j + 1)
            idx += [aa, cc, bb, aa, dd, cc]                  # dessus, +z
            a2, b2 = bot(i, j), bot(i + 1, j)
            c2, d2 = bot(i + 1, j + 1), bot(i, j + 1)
            idx += [a2, b2, c2, a2, c2, d2]                  # dessous, -z
    # murs : les 4 bords, quads entre anneau du dessus et anneau du dessous
    def wall(t1, t2, b1, b2):
        idx.extend([t1, b2, b1, t1, t2, b2])
    for i in range(gx):                                       # j=0 et j=gy
        wall(top(i, 0), top(i + 1, 0), bot(i, 0), bot(i + 1, 0))
        wall(top(i + 1, gy), top(i, gy), bot(i + 1, gy), bot(i, gy))
    for j in range(gy):                                       # i=0 et i=gx
        wall(top(0, j + 1), top(0, j), bot(0, j + 1), bot(0, j))
        wall(top(gx, j), top(gx, j + 1), bot(gx, j), bot(gx, j + 1))

    # normales : accumulation de normales de faces pondérées par l'aire sur
    # les sommets partagés ; connu : l'anneau de bord mélange mur et face,
    # l'arête du pourtour s'ombre adoucie — géométrie exacte, STL non affecté
    # (normales de facette recalculées).
    nrm = [0.0] * len(pos)
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
        ux, uy, uz = (pos[i1] - pos[i0], pos[i1 + 1] - pos[i0 + 1], pos[i1 + 2] - pos[i0 + 2])
        vx, vy, vz = (pos[i2] - pos[i0], pos[i2 + 1] - pos[i0 + 1], pos[i2 + 2] - pos[i0 + 2])
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for k in (i0, i1, i2):
            nrm[k] += cx; nrm[k + 1] += cy; nrm[k + 2] += cz
    for k in range(0, len(nrm), 3):
        ln = math.sqrt(nrm[k] ** 2 + nrm[k + 1] ** 2 + nrm[k + 2] ** 2) or 1.0
        nrm[k] /= ln; nrm[k + 1] /= ln; nrm[k + 2] /= ln
    # "closed": fermeture TOPOLOGIQUE, indépendante du contenu alpha —
    # prouvée une fois pour toutes par le test unitaire ; la route build3d
    # gate le STL sur ce drapeau au lieu de re-mesurer : 7 s + ~340 Mo de pic
    # par élément au grid max, mesuré en revue.
    return {"positions": pos, "normals": nrm, "uvs": uv, "indices": idx,
            "closed": True}


def mesh_measures(mesh: dict) -> dict:
    """Fermeture et volume signé, MESURES locales — copie du principe de
    `mesh_report` de P8 (règle 8 : pas d'import pièce->pièce), réduite aux
    deux chiffres dont l'artefact a besoin (closed, volume)."""
    pos, idx = mesh["positions"], mesh["indices"]
    edges: dict = {}
    vol = 0.0
    for t in range(0, len(idx) - 2, 3):
        tri = (idx[t], idx[t + 1], idx[t + 2])
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            ka = (round(pos[a * 3], 6), round(pos[a * 3 + 1], 6), round(pos[a * 3 + 2], 6))
            kb = (round(pos[b * 3], 6), round(pos[b * 3 + 1], 6), round(pos[b * 3 + 2], 6))
            e = (ka, kb) if ka <= kb else (kb, ka)
            edges[e] = edges.get(e, 0) + 1
        a3, b3, c3 = tri[0] * 3, tri[1] * 3, tri[2] * 3
        vol += (pos[a3] * (pos[b3 + 1] * pos[c3 + 2] - pos[b3 + 2] * pos[c3 + 1])
                - pos[a3 + 1] * (pos[b3] * pos[c3 + 2] - pos[b3 + 2] * pos[c3])
                + pos[a3 + 2] * (pos[b3] * pos[c3 + 1] - pos[b3 + 1] * pos[c3])) / 6.0
    closed = bool(edges) and all(n == 2 for n in edges.values())
    return {"closed": closed, "volume_mm3": vol,
            "triangles": len(idx) // 3, "vertices": len(pos) // 3}


# ── L'ASSEMBLAGE — UN document glTF binaire, écrit JUSTE (Task 3) ──────────
# `write_scene_glb` consomme le type commun de `quad_mesh`/`relief_mesh`
# (positions/normals/uvs/indices — `closed` et tout champ surnuméraire sont
# IGNORÉS) et produit un GLB PROPRE dès l'écriture : bornes d'accesseurs
# EXACTES (calculées sur les float32 réellement empaquetés, pas sur les
# float64 Python d'avant arrondi), AUCUN champ d'identité (generator,
# copyright, author, producer — ce writer n'en émet simplement jamais),
# samplers CLAMP_TO_EDGE, racine à l'échelle physique mm -> m (0.001), un
# enfant nommé par élément, translation z (mm) portée par le nœud de
# l'élément. À la différence du constructeur générique du dépôt
# (gltf_builder, qui exige des rustines post-hoc — finalize_glb de P8), rien
# ici n'est corrigé après coup.

# Clés d'`extras` qui nomment un producteur — COPIE LOCALE de gltf.py:198
# (règle 8, zéro import pièce->pièce) : filtrées ICI, dans le writer, pour
# que « zéro identité » reste vrai pour TOUT appelant, pas seulement celui
# qui pense à nettoyer son propre extras avant l'appel.
_IDENTITY_KEYS = ("generator", "producer", "author", "software", "application",
                  "copyright", "artist", "company", "vendor")


def write_scene_glb(elements: list, name: str, extras: dict) -> bytes:
    """UN document glTF multi-éléments, écrit JUSTE du premier coup :
    bornes exactes (calculées ici même sur les floats empaquetés), aucun champ
    d'identité (ce writer n'en émet simplement jamais), samplers CLAMP, racine
    à l'échelle physique mm->m, un enfant nommé par élément, translation z en
    mm portée par le nœud de l'élément. Textures : les PNG estampillés de la
    phase 1, embarqués tels quels (mêmes octets, mêmes SHA que le manifeste).

    Précondition : `elements` exige AU MOINS UN élément — un GLB à zéro
    élément est invalide au schéma glTF (minItems 1) ; la route build3d fait
    409 avant d'appeler ce writer (tâche 4)."""
    # zéro identité VRAIE pour tout appelant, pas seulement le nôtre
    extras = {k: v for k, v in (extras or {}).items() if k not in _IDENTITY_KEYS}
    buf = bytearray()
    views, accessors, images, textures, materials, meshes, nodes = [], [], [], [], [], [], []

    def pad4():
        while len(buf) % 4:
            buf.append(0)

    def add_view(data: bytes, target=None) -> int:
        pad4()
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(data),
                      **({"target": target} if target else {})})
        buf.extend(data)
        return len(views) - 1

    def add_accessor(vals, n, ctype, atype, target) -> int:
        data = struct.pack("<" + "f" * len(vals), *vals) if ctype == 5126 \
            else struct.pack("<" + "I" * len(vals), *vals)
        v = add_view(data, target)
        acc = {"bufferView": v, "componentType": ctype,
               "count": len(vals) // n, "type": atype}
        if ctype == 5126:
            # les bornes sont posées sur les float32 EXACTS : repasser par
            # struct garantit la valeur que le lecteur relira (un float
            # Python 64 bits arrondi en float32 changerait de valeur)
            packed = struct.unpack("<" + "f" * len(vals), data)
            acc["min"] = [min(packed[i::n]) for i in range(n)]
            acc["max"] = [max(packed[i::n]) for i in range(n)]
        accessors.append(acc)
        return len(accessors) - 1

    sampler = 0   # un seul sampler CLAMP
    for el in elements:
        m = el["mesh"]
        ip = add_accessor(m["positions"], 3, 5126, "VEC3", 34962)
        inm = add_accessor(m["normals"], 3, 5126, "VEC3", 34962)
        iuv = add_accessor(m["uvs"], 2, 5126, "VEC2", 34962)
        iix = add_accessor(m["indices"], 1, 5125, "SCALAR", 34963)
        v_png = add_view(el["png"])
        images.append({"bufferView": v_png, "mimeType": "image/png",
                       "name": el["name"]})
        textures.append({"sampler": sampler, "source": len(images) - 1})
        materials.append({
            "name": el["name"],
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": len(textures) - 1},
                "metallicFactor": 0.0, "roughnessFactor": 0.9},
            **({"alphaMode": "BLEND", "doubleSided": True} if el.get("alpha")
               else {})})
        meshes.append({"name": el["name"], "primitives": [{
            "attributes": {"POSITION": ip, "NORMAL": inm, "TEXCOORD_0": iuv},
            "indices": iix, "material": len(materials) - 1}]})
        nodes.append({"name": el["name"], "mesh": len(meshes) - 1,
                      **({"translation": [0.0, 0.0, float(el["z_mm"])]}
                         if el.get("z_mm") else {})})
    # PIÈGE DU SQUELETTE (auto-revue) : le buffer doit être aligné à 4 AVANT
    # que `buffers[0].byteLength` ne soit figé dans le JSON — la dernière
    # écriture de la boucle (un PNG, taille arbitraire) laisse `buf`
    # potentiellement désaligné. Padder ICI, avant de construire `doc`, pas
    # après l'avoir sérialisé : sinon le JSON porte un byteLength trop petit
    # (mesuré avant coup) pendant que le chunk BIN réellement écrit, lui,
    # est plus long (padding déjà ajouté) — total et byteLength dérivent l'un
    # de l'autre. Ici, `len(buf)` à la construction de `doc` EST déjà la
    # longueur finale du chunk BIN : plus rien ne l'allonge après.
    pad4()
    # extras posé aux DEUX etages (asset ET racine), assumé : les DCC gardent
    # node.extras en propriétés custom et JETTENT asset.extras (Blender) ;
    # three.js expose node.extras en userData — un seul emplacement ne
    # survivrait pas partout.
    racine = {"name": str(name)[:60], "scale": [0.001, 0.001, 0.001],
              "children": list(range(len(nodes))), "extras": extras}
    nodes.append(racine)
    doc = {"asset": {"version": "2.0", "extras": extras},
           "scene": 0, "scenes": [{"name": str(name)[:60], "nodes": [len(nodes) - 1]}],
           "nodes": nodes, "meshes": meshes, "materials": materials,
           "textures": textures, "images": images,
           "samplers": [{"wrapS": 33071, "wrapT": 33071}],
           "accessors": accessors, "bufferViews": views,
           "buffers": [{"byteLength": len(buf)}]}
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(buf)
    out = struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(buf), 0x004E4942) + bytes(buf)
    return out


# ── L'IMPRESSION 3D — STL LOCAL (Task 4) ────────────────────────────────────
# `_write_stl_binary` : copie RÉDUITE du principe de `gltf.py:build_stl`
# (règle 8, zéro import pièce->pièce, même patron que le reste de ce
# fichier) — positions déjà en MILLIMÈTRES (nos meshes locaux, contrairement
# à ceux de P8, ne portent pas d'échelle mesh->mm à part), en-tête 80 octets
# SANS nom d'outil (le nom de l'artefact, comme gltf.py:build_stl), une
# normale par facette recalculée depuis la géométrie (le format n'a ni UV ni
# matière). Le SEUL appelant (build3d) ne le convoque qu'après avoir vérifié
# que TOUS les éléments portent `closed: True` — gate sur le drapeau DÉCLARÉ
# par les constructeurs de maillage, jamais une re-mesure ici.
#
# DEUX PASSES (legs 6, revue finale 2a) : l'ancienne version accumulait
# chaque triangle dans une liste Python de tuples AVANT d'écrire — mesuré à
# ~160 Mo d'intermédiaires par relief au grid max. Ici, une première passe
# compte les triangles (pour dimensionner le buffer de sortie UNE fois),
# la seconde passe packe chaque facette DIRECTEMENT dedans (`struct.pack_into`,
# aucune structure intermédiaire) — même sortie, au bit près : le test de
# couture le prouve par égalité d'octets, pas par relecture du format.
def _write_stl_binary(elements: list, name: str) -> bytes:
    """STL binaire local, en millimètres, DEUX PASSES : compter d'abord le
    total de triangles (pour dimensionner le buffer de sortie UNE fois), puis
    packer chaque facette directement dedans — l'ancienne version
    matérialisait toute la géométrie en tuples Python avant d'écrire (~160 Mo
    d'intermédiaires par relief au grid max, mesuré en 2a). Même sortie, au
    bit près (couture legs 6, revue finale 2a). `z_mm` de chaque élément
    (l'écart de pile porté par SON nœud, comme dans le GLB) est appliqué aux
    positions puisque le format STL n'a pas de nœud pour le porter."""
    total = sum(len(el["mesh"]["indices"]) // 3 for el in elements)
    out = bytearray(84 + 50 * total)
    entete = f"{name} - millimetres - {total} triangles".encode(
        "ascii", "ignore")[:80]
    out[0:len(entete)] = entete
    struct.pack_into("<I", out, 80, total)
    off = 84
    for el in elements:
        pos, idx = el["mesh"]["positions"], el["mesh"]["indices"]
        z = float(el.get("z_mm") or 0.0)
        for t in range(0, len(idx) - 2, 3):
            a, b, c = idx[t] * 3, idx[t + 1] * 3, idx[t + 2] * 3
            ax, ay, az = pos[a], pos[a + 1], pos[a + 2] + z
            bx, by, bz = pos[b], pos[b + 1], pos[b + 2] + z
            cx, cy, cz = pos[c], pos[c + 1], pos[c + 2] + z
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            struct.pack_into("<12fH", out, off,
                             nx / ln, ny / ln, nz / ln,
                             ax, ay, az, bx, by, bz, cx, cy, cz, 0)
            off += 50
    return bytes(out)
