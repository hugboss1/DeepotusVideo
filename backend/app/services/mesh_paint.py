# -*- coding: utf-8 -*-
"""Habiller un maillage d'une matière du Material Forge (R10c P2 « mon
modèle », puis D2 « une matière par partie »).

CE MODULE N'ÉCRIT AUCUN FICHIER. Il prend les octets d'un GLB et rend les
octets d'un autre. La seule plume qui DÉPOSE une version reste
`mesh_edit.ecrire_version` — doctrine de l'Établi : jamais d'écrasement,
toujours une version numérotée avec sa fiche.

POURQUOI DES PRIMITIVES, ET PAS DES NŒUDS. Un modèle Meshy arrive souvent en
un nœud UNIQUE portant plusieurs matériaux, un Tripo en plusieurs nœuds
(mesuré : c'est la raison d'être des trois granularités du panneau Parties de
l'Établi). Aucune granularité ne suffit seule, et la seule chose qui porte
réellement un `material` dans le format glTF est la PRIMITIVE. Les trois
entrées de l'écran s'y ramènent donc ici, une fois, au même endroit.

LES FACTEURS RESTENT À 1.0, et ce n'est pas un détail. glTF pose
`rugosité = roughnessFactor x texture.G` : nos niveaux sont déjà CUITS dans
les cartes (`material_store.bake_levels`), et poser en plus le curseur dans le
facteur les compterait deux fois — exactement le défaut que `render_block`
documente et que `gltf_builder` évite côté aperçu. Une seule chose décide de
la valeur, et c'est la carte.
"""
from __future__ import annotations

from app.services import mesh_edit, pbr_service as PBR

__all__ = ["CIBLES", "cibles", "materiau", "habiller", "BUDGET_MASQUES_100K",
           "masques", "masques_glb"]

CIBLES = ("tout", "noeud", "maillage", "materiau")


def _mime(data: bytes) -> str:
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    raise ValueError("habillage : une texture n'est ni PNG ni JPEG "
                     "(glTF n'accepte que ces deux-là)")


class _Tampon:
    """Le tampon binaire en construction, aligné sur 4 octets à chaque ajout.

    La spec glTF exige cet alignement pour les bufferViews ; sans lui, un
    lecteur strict refuse le fichier et un lecteur laxiste lit de travers —
    le second est pire."""

    def __init__(self, binc: bytes):
        self.morceaux = [bytes(binc)]
        self.taille = len(binc)

    def ajouter(self, data: bytes) -> tuple[int, int]:
        pad = (-self.taille) % 4
        if pad:
            self.morceaux.append(b"\x00" * pad)
            self.taille += pad
        debut = self.taille
        self.morceaux.append(bytes(data))
        self.taille += len(data)
        return debut, len(data)

    def octets(self) -> bytes:
        return b"".join(self.morceaux)


def _texture(doc: dict, tampon: _Tampon, data: bytes) -> int:
    """Ajoute une image au document et rend l'index de sa texture."""
    debut, n = tampon.ajouter(data)
    views = doc.setdefault("bufferViews", [])
    views.append({"buffer": 0, "byteOffset": debut, "byteLength": n})
    images = doc.setdefault("images", [])
    images.append({"bufferView": len(views) - 1, "mimeType": _mime(data)})
    samplers = doc.setdefault("samplers", [])
    if not samplers:
        # 9729 LINEAR, 9987 LINEAR_MIPMAP_LINEAR, 10497 REPEAT : le pavage est
        # la raison d'être d'une matière, un CLAMP la trahirait.
        samplers.append({"magFilter": 9729, "minFilter": 9987,
                         "wrapS": 10497, "wrapT": 10497})
    textures = doc.setdefault("textures", [])
    textures.append({"sampler": 0, "source": len(images) - 1})
    return len(textures) - 1


def materiau(doc: dict, tampon: _Tampon, nom: str, payload: dict) -> int:
    """Ajoute un matériau glTF portant les cartes fournies (octets PNG/JPEG
    déjà encodés, cartes déjà cuites) et rend son index."""
    pbr = {"baseColorFactor": [1.0, 1.0, 1.0, 1.0],
           "metallicFactor": 1.0, "roughnessFactor": 1.0}
    mat = {"name": (str(nom or "matière")[:64] or "matière"),
           "pbrMetallicRoughness": pbr, "doubleSided": True}
    if payload.get("basecolor"):
        pbr["baseColorTexture"] = {
            "index": _texture(doc, tampon, payload["basecolor"])}
    if payload.get("orm"):
        # UNE image, DEUX emplacements : c'est le contrat glTF (R = occlusion,
        # V = rugosité, B = métal), et le dupliquer coûterait le double du
        # poids pour les mêmes octets.
        i = _texture(doc, tampon, payload["orm"])
        pbr["metallicRoughnessTexture"] = {"index": i}
        mat["occlusionTexture"] = {"index": i}
    if payload.get("normal"):
        mat["normalTexture"] = {"index": _texture(doc, tampon,
                                                  payload["normal"])}
    if payload.get("emissive"):
        mat["emissiveTexture"] = {"index": _texture(doc, tampon,
                                                    payload["emissive"])}
        mat["emissiveFactor"] = [1.0, 1.0, 1.0]
    mats = doc.setdefault("materials", [])
    mats.append(mat)
    return len(mats) - 1


def _entier(v, quoi: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"habillage : {quoi} — un index entier à partir de 0 "
                         f"est attendu (reçu {v!r})")
    return v


def _mesh_sous(doc: dict, i: int, vus=None) -> set:
    """Les maillages portés par ce nœud ET par toute sa descendance.

    La descendance compte : cocher un nœud parent dans le panneau Parties est
    un geste naturel, et n'habiller que lui laisserait les enfants nus sans
    rien dire."""
    nodes = doc.get("nodes") or []
    if not (0 <= i < len(nodes)):
        raise ValueError(f"habillage : nœud {i} inconnu — le document en "
                         f"déclare {len(nodes)}")
    vus = set() if vus is None else vus
    if i in vus:
        return set()
    vus.add(i)
    out = set()
    n = nodes[i]
    if isinstance(n.get("mesh"), int):
        out.add(n["mesh"])
    for e in (n.get("children") or []):
        out |= _mesh_sous(doc, _entier(e, "enfant"), vus)
    return out


def cibles(doc: dict, cible, index) -> set:
    """Les couples (maillage, primitive) visés par une cible de l'écran."""
    meshes = doc.get("meshes") or []
    toutes = {(m, p) for m, mesh in enumerate(meshes)
              for p in range(len(mesh.get("primitives") or []))}
    c = str(cible or "").strip().lower()
    if c == "tout":
        return toutes
    if c == "noeud":
        gardes = _mesh_sous(doc, _entier(index, "index de nœud"))
        return {(m, p) for (m, p) in toutes if m in gardes}
    if c == "maillage":
        i = _entier(index, "index de maillage")
        if i >= len(meshes):
            raise ValueError(f"habillage : maillage {i} inconnu — le document "
                             f"en déclare {len(meshes)}")
        return {(m, p) for (m, p) in toutes if m == i}
    if c == "materiau":
        i = _entier(index, "index de matériau")
        n = len(doc.get("materials") or [])
        if i >= n:
            raise ValueError(f"habillage : matériau {i} inconnu — le document "
                             f"en déclare {n}")
        return {(m, p) for (m, p) in toutes
                if meshes[m]["primitives"][p].get("material") == i}
    raise ValueError(f"habillage : cible « {cible} » inconnue — attendu : "
                     f"{', '.join(CIBLES)}")


def habiller(data: bytes, lots) -> bytes:
    """Pose une matière sur chaque cible et rend les octets du GLB habillé.

    `lots` = liste de `{cible, index, mid, nom, maps}` où `maps` est un
    dictionnaire kind -> octets PNG déjà encodés et déjà cuits. Deux lots qui
    portent le même `mid` partagent UN matériau glTF : sinon un modèle à
    quarante pièces embarquerait quarante copies des mêmes textures.
    """
    doc, binc = mesh_edit.lire_glb(data)
    if not (doc.get("meshes") or []):
        raise ValueError("habillage : ce GLB ne contient aucun maillage")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("habillage : aucune matière à poser")
    tampons = doc.get("buffers") or []
    if len(tampons) != 1 or tampons[0].get("uri"):
        raise ValueError("habillage : ce GLB a un tampon externe ou multiple "
                         "— l'habillage n'y touche pas")

    tampon = _Tampon(binc)
    connus: dict = {}
    # LES CIBLES SE RÉSOLVENT TOUTES SUR LE DOCUMENT D'ORIGINE, avant la
    # moindre affectation (mesuré le 06/10 : résolues au fil de l'eau, un lot
    # « matériau 0 » placé après un lot « nœud 0 » ne trouvait plus aucune
    # primitive — le premier venait de les réaffecter — et le résultat
    # dépendait de l'ordre des lots).
    for lot in lots:
        if not isinstance(lot, dict):
            raise ValueError("habillage : chaque lot est un objet "
                             "{cible, index, mid, nom, maps}")
    resolus = [cibles(doc, lot.get("cible"), lot.get("index")) for lot in lots]
    for lot, vises in zip(lots, resolus):
        if not vises:
            raise ValueError(
                f"habillage : la cible « {lot.get('cible')} » "
                f"{lot.get('index')} ne porte aucune primitive")
        for (m, p) in sorted(vises):
            prim = doc["meshes"][m]["primitives"][p]
            if "TEXCOORD_0" not in (prim.get("attributes") or {}):
                raise ValueError(
                    f"habillage : la pièce (maillage {m}, primitive {p}) n'a "
                    "pas d'uv (TEXCOORD_0) — une matière ne peut pas s'y "
                    "plaquer. Dépliez-la d'abord (Meshy uv-unwrap).")
            if "KHR_draco_mesh_compression" in (prim.get("extensions") or {}):
                raise ValueError(
                    f"habillage : la pièce (maillage {m}, primitive {p}) est "
                    "compressée en Draco — décompressez d'abord (gltfpack).")
        cle = lot.get("mid") or lot.get("nom") or f"lot{len(connus)}"
        if cle not in connus:
            connus[cle] = materiau(doc, tampon, lot.get("nom") or str(cle),
                                   lot.get("maps") or {})
        for (m, p) in vises:
            doc["meshes"][m]["primitives"][p]["material"] = connus[cle]

    octets = tampon.octets()
    doc["buffers"] = [{"byteLength": len(octets)}]
    return mesh_edit.ecrire_glb(doc, octets)


# ── masques de cavités et d'arêtes (R10c D2) ────────────────────────────────
#
# CE QU'ON MESURE, ET CE QU'ON NE PROMET PAS. Une occlusion ambiante VRAIE se
# calcule par lancer de rayons ; en Python pur, sur 100 000 triangles, ce
# serait des minutes. On mesure donc la COURBURE, à trois échelles, et on
# l'appelle par son nom : « cavité » là où la surface se creuse, « arête » là
# où elle se casse. C'est ce dont l'usure a besoin — la crasse s'accumule dans
# les creux, la peinture s'écaille sur les arêtes — et c'est exactement le même
# raisonnement que `pbr_service._cavity`, qui mesure `flou(H) - H` plutôt que
# de lancer des rayons dans une image.
#
# L'ESTIMATEUR. Pour un sommet v de normale n(v), la moyenne sur ses voisins u
# de `dot(normalize(u - v), n(v))` est positive quand le voisinage remonte le
# long de la normale — donc quand v est au FOND de quelque chose — et négative
# quand il redescend, donc sur une saillie. Trois échelles (1, 2 et 3 anneaux)
# comme les trois octaves de l'AO de `pbr_service` : une seule échelle ne voit
# que les creux de sa propre taille.
#
# LE BUDGET EST MESURÉ, PAS ESPÉRÉ. Le banc chronomètre et rapporte à
# 100 000 triangles ; au-delà de la borne, il échoue.
BUDGET_MASQUES_100K = 12.0

_MASQUE_OCTAVES = ((1, 0.5), (2, 0.3), (3, 0.2))
_MASQUE_GAIN = 6.0          # même esprit que `pbr_service._AO_GAIN` : sans
                            # gain, la courbure d'un maillage dense est un
                            # centième et la carte sort blanche


def _souder(pos, idx):
    """Sommets soudés par position arrondie, et l'adjacence 1-anneau.

    SOUDER N'EST PAS FACULTATIF : un cube exporté a 24 sommets pour 8 coins
    (chaque face porte les siens, pour ses normales). Sans soudure, aucun
    sommet n'aurait de voisin d'une autre face, et une arête — qui EST la
    rencontre de deux faces — serait rigoureusement invisible."""
    cle_de, rep = {}, []
    for p in pos:
        k = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
        j = cle_de.get(k)
        if j is None:
            j = len(cle_de)
            cle_de[k] = j
        rep.append(j)
    n = len(cle_de)
    points = [None] * n
    for i, p in enumerate(pos):
        points[rep[i]] = (p[0], p[1], p[2])
    voisins = [set() for _ in range(n)]
    normales = [[0.0, 0.0, 0.0] for _ in range(n)]
    for t in range(0, len(idx) - 2, 3):
        a, b, c = rep[idx[t]], rep[idx[t + 1]], rep[idx[t + 2]]
        voisins[a].update((b, c))
        voisins[b].update((a, c))
        voisins[c].update((a, b))
        pa, pb, pc = points[a], points[b], points[c]
        u = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        v = (pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2])
        # produit vectoriel NON normalisé : sa longueur est deux fois l'aire,
        # donc la somme pondère naturellement par l'aire des faces
        nx = u[1] * v[2] - u[2] * v[1]
        ny = u[2] * v[0] - u[0] * v[2]
        nz = u[0] * v[1] - u[1] * v[0]
        for s in (a, b, c):
            normales[s][0] += nx
            normales[s][1] += ny
            normales[s][2] += nz
    return rep, points, voisins, normales


def _courbure(points, voisins, normales) -> list:
    """Courbure signée par sommet : > 0 dans un creux, < 0 sur une saillie."""
    import math
    out = [0.0] * len(points)
    for i, p in enumerate(points):
        n = normales[i]
        ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        if ln < 1e-12 or not voisins[i]:
            continue
        nx, ny, nz = n[0] / ln, n[1] / ln, n[2] / ln
        s = 0.0
        for j in voisins[i]:
            q = points[j]
            dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d < 1e-12:
                continue
            s += (dx * nx + dy * ny + dz * nz) / d
        out[i] = s / len(voisins[i])
    return out


def _lisser_anneau(valeurs, voisins, tours: int) -> list:
    """Moyenne sur le 1-anneau, répétée — l'équivalent discret du flou de
    `pbr_service`, et c'est ainsi qu'on obtient les échelles supérieures sans
    parcourir un k-anneau explicite (quadratique)."""
    cur = valeurs
    for _ in range(max(0, tours)):
        suiv = list(cur)
        for i, vs in enumerate(voisins):
            if vs:
                suiv[i] = (cur[i] + sum(cur[j] for j in vs)) / (len(vs) + 1.0)
        cur = suiv
    return cur


def _octets_masques(courbure, voisins) -> tuple:
    """(cavités, arêtes) en octets 0-255, cumulées sur trois échelles."""
    cav = [0.0] * len(courbure)
    are = [0.0] * len(courbure)
    for tours, poids in _MASQUE_OCTAVES:
        c = _lisser_anneau(courbure, voisins, tours - 1)
        for i, v in enumerate(c):
            if v > 0:
                cav[i] += poids * v
            else:
                are[i] -= poids * v
    def _o(x):
        return PBR.clamp8(255.0 * x * _MASQUE_GAIN)
    return [_o(v) for v in cav], [_o(v) for v in are]


def _primitives_lues(data: bytes):
    """(doc, binc, [(m, p, positions, indices)]) — par LE lecteur
    d'accesseurs du dépôt, `mesh_edit.lire_accesseur` (sparse compris). Le plan
    passait par deux alias de `print3d` : `print3d._accessor` délègue déjà à
    mesh_edit depuis T090, et le banc « un seul lecteur » voyait l'alias."""
    doc, binc = mesh_edit.lire_glb(data)
    lots = []
    for m, mesh in enumerate(doc.get("meshes") or []):
        for p, prim in enumerate(mesh.get("primitives") or []):
            if prim.get("mode", 4) != 4:
                continue
            pos = mesh_edit.lire_accesseur(doc, binc, prim["attributes"]["POSITION"],
                                           quoi="les masques")
            if "indices" in prim:
                idx = [v[0] for v in mesh_edit.lire_accesseur(doc, binc, prim["indices"],
                                                              quoi="les masques")]
            else:
                idx = list(range(len(pos)))
            lots.append((m, p, pos, idx))
    return doc, binc, lots


def masques(data: bytes) -> dict:
    """Statistiques de cavité et d'arête, primitive par primitive."""
    _doc, _binc, lots = _primitives_lues(data)
    if not lots:
        raise ValueError("masques : ce GLB ne contient aucune primitive "
                         "triangulaire")
    out, total = [], 0
    for (m, p, pos, idx) in lots:
        rep, points, voisins, normales = _souder(pos, idx)
        cav, are = _octets_masques(_courbure(points, voisins, normales),
                                   voisins)
        n = max(1, len(points))
        total += n
        out.append({"maillage": m, "primitive": p, "sommets": len(pos),
                    "soudes": len(points),
                    "cavite_moy": round(sum(cav) / n, 1),
                    "arete_moy": round(sum(are) / n, 1)})
    return {"primitives": out, "sommets": total}


def masques_glb(data: bytes) -> bytes:
    """Le même maillage avec un COLOR_0 par sommet : R = cavité, V = arête.

    APERÇU SEULEMENT, et jamais une version : c'est une lecture. Les couleurs
    de sommet sont le seul canal qui n'exige AUCUN dépliage UV — et un modèle
    généré par un moteur image → 3D n'en a pas toujours."""
    doc, binc, lots = _primitives_lues(data)
    if not lots:
        raise ValueError("masques : ce GLB ne contient aucune primitive "
                         "triangulaire")
    tampon = _Tampon(binc)
    # UN MATÉRIAU NEUTRE pour toutes les primitives (preuve 8799 du 06/10) : la
    # couleur de sommet se MULTIPLIE à la texture du matériau en place, et sur
    # un modèle déjà habillé le rouge et le vert se lisaient dans la rouille.
    # Blanc, mat, sans texture : R = cavité, V = arête, rien d'autre.
    mats = doc.setdefault("materials", [])
    mats.append({"name": "masques", "doubleSided": True,
                 "pbrMetallicRoughness": {"baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                                          "metallicFactor": 0.0, "roughnessFactor": 1.0}})
    neutre = len(mats) - 1
    for (m, p, pos, idx) in lots:
        doc["meshes"][m]["primitives"][p]["material"] = neutre
        rep, points, voisins, normales = _souder(pos, idx)
        cav, are = _octets_masques(_courbure(points, voisins, normales),
                                   voisins)
        octets = bytearray()
        for i in range(len(pos)):
            j = rep[i]
            octets += bytes((cav[j], are[j], 0, 255))
        debut, n = tampon.ajouter(bytes(octets))
        views = doc.setdefault("bufferViews", [])
        views.append({"buffer": 0, "byteOffset": debut, "byteLength": n})
        accs = doc.setdefault("accessors", [])
        accs.append({"bufferView": len(views) - 1, "componentType": 5121,
                     "normalized": True, "count": len(pos), "type": "VEC4"})
        doc["meshes"][m]["primitives"][p]["attributes"]["COLOR_0"] = \
            len(accs) - 1
    octets = tampon.octets()
    doc["buffers"] = [{"byteLength": len(octets)}]
    return mesh_edit.ecrire_glb(doc, octets)
