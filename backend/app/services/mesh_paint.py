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

from app.services import mesh_edit

__all__ = ["CIBLES", "cibles", "materiau", "habiller"]

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
    for lot in lots:
        if not isinstance(lot, dict):
            raise ValueError("habillage : chaque lot est un objet "
                             "{cible, index, mid, nom, maps}")
        vises = cibles(doc, lot.get("cible"), lot.get("index"))
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
