# -*- coding: utf-8 -*-
"""Chirurgie de document glTF — la SEULE plume à GLB du chantier Établi.

Règle de l'option C (spec 2026-08-29-etabli-inspecteur-3d-design §2.1) : le
navigateur voit et manipule, Python écrit. Aucun GLB n'est jamais produit par
le client, de sorte que tout artefact reste versionné, fiché par mesh_report,
et vérifiable par le harnais.

Deux propriétés porteront la sûreté du module, et les bancs des tâches 3 et 5
de ce plan les épingleront (elles n'existent pas encore à la tâche 1) :

* `extraire` est une RECOPIE D'OCTETS, jamais un décodage de géométrie — les
  bufferViews retenus sont copiés tels quels. L'extraction fonctionne donc sur
  un GLB Draco ou meshopt, là où `print3d.lire_glb_triangles` refuse.
* `transformer` ne touche QUE le document JSON — le tampon binaire ressort
  identique octet pour octet, ce qui rend l'opération sûre sur 200 Mo.

Module sans `settings` : de la manipulation d'octets pure, testable sans
environnement.
"""
from __future__ import annotations

import json
import struct

_MAGIC = b"glTF"
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942


def lire_glb(data: bytes) -> tuple[dict, bytes]:
    """Les DEUX moitiés d'un GLB v2 : le document et son tampon.

    `mesh_report._gltf_json` ne rend que le JSON et `print3d` sert son propre
    décodeur ; la chirurgie a besoin des deux et de savoir les recoller.
    """
    if len(data) < 12 or data[:4] != _MAGIC:
        raise ValueError("magic GLB absent — ce fichier n'est pas un .glb")
    version, longueur = struct.unpack_from("<II", data, 4)
    if version != 2:
        raise ValueError(f"GLB v{version} non géré (v2 attendu)")
    doc: dict | None = None
    binc = b""
    off = 12
    # Borner par la longueur DÉCLARÉE dans l'en-tête, comme le fait déjà
    # `print3d._chunks`. Sans cette borne, des octets parasites après la fin
    # du conteneur (téléchargement rejoué, artefact d'un générateur tiers)
    # seraient lus comme des chunks : si les quatre suivants ressemblent à
    # `BIN\0`, le tampon déjà lu serait écrasé EN SILENCE. Un GLB de 200 Mo
    # venu de Meshy ou Tripo mérite mieux qu'une corruption muette.
    while off + 8 <= min(longueur, len(data)):
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        bloc = data[off:off + clen]
        if ctype == _CHUNK_JSON:
            doc = json.loads(bloc.decode("utf-8"))
        elif ctype == _CHUNK_BIN:
            binc = bloc
        off += clen + (-clen % 4)
    if doc is None:
        raise ValueError("chunk JSON introuvable")
    return doc, binc


def ecrire_glb(doc: dict, binc: bytes) -> bytes:
    """Recolle un document et son tampon. Les deux chunks sont alignés sur 4
    octets — le JSON par des espaces, le binaire par des zéros, comme l'exige
    la spec glTF 2.0."""
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    bn = bytes(binc) + b"\x00" * (-len(binc) % 4)
    total = 12 + 8 + len(js) + ((8 + len(bn)) if bn else 0)
    out = struct.pack("<4sII", _MAGIC, 2, total)
    out += struct.pack("<II", len(js), _CHUNK_JSON) + js
    if bn:
        out += struct.pack("<II", len(bn), _CHUNK_BIN) + bn
    return out


def _l(doc: dict, cle: str) -> list:
    """Un tableau glTF absent et un tableau vide se traitent pareil."""
    return doc.get(cle) or []


def rig_inventory(data: bytes) -> dict:
    """Os, hiérarchie, skins et clips — chunk JSON seulement.

    Instantané même sur un GLB de 200 Mo, et c'est le but : le panneau Rig doit
    pouvoir annoncer l'absence de squelette sans rien télécharger.

    CONTRAT À LIRE AVANT DE BÂTIR UN ARBRE DESSUS : `os` ne contient que les
    JOINTS. Un `os[].parent` peut donc désigner un nœud absent de la liste —
    c'est le cas courant des exports Blender ou Mixamo, où la racine
    d'armature (`skins[].skeleton`) porte le déplacement global sans être
    elle-même un os. Un consommateur doit traiter un `parent` introuvable
    comme une racine, jamais supposer qu'il se résout dans `os`.
    """
    doc, _ = lire_glb(data)
    nodes = _l(doc, "nodes")
    skins = _l(doc, "skins")

    parent: dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in _l(n, "children"):
            parent[c] = i

    joints: list[int] = []
    for s in skins:
        for j in _l(s, "joints"):
            if j not in joints:
                joints.append(j)

    os_: list[dict] = []
    for j in joints:
        n = nodes[j] if 0 <= j < len(nodes) else {}
        os_.append({
            "index": j,
            "nom": n.get("name") or f"os_{j}",
            "parent": parent.get(j),
            "enfants": [c for c in _l(n, "children") if c in joints],
        })

    clips = [{"nom": a.get("name") or f"clip_{i}",
              "canaux": len(_l(a, "channels"))}
             for i, a in enumerate(_l(doc, "animations"))]

    return {
        "a_squelette": bool(skins),
        "nb_os": len(joints),
        "os": os_,
        "skins": [{"nom": s.get("name") or f"skin_{i}",
                   "nb_joints": len(_l(s, "joints")),
                   "racine": s.get("skeleton")}
                  for i, s in enumerate(skins)],
        "clips": clips,
    }


_TAILLES = {"translation": 3, "rotation": 4, "scale": 3}
_TOLERANCE_QUATERNION = 1e-3


def transformer(data: bytes, transforms: dict) -> bytes:
    """Position / rotation / échelle de nœuds nommés.

    N'écrit QUE le document : le tampon binaire ressort identique octet pour
    octet, et le banc l'épingle. `matrix` est retiré du nœud touché — glTF
    interdit de porter à la fois une matrice et un TRS.

    Trois refus explicites plutôt que des corrections silencieuses, parce que
    cette fonction sera exposée par une route HTTP (tâche 8) qui ne traduit
    en 400 que les `ValueError` : entrée non-dictionnaire, clé de nœud non
    numérique, quaternion non normalisé. Normaliser un quaternion en douce
    masquerait un bug amont ; le refuser le montre.

    `scale` négatif ou nul passe DÉLIBÉRÉMENT : une échelle négative par axe
    est un TRS glTF valide (effet miroir). `reparer` refuse au contraire une
    échelle globale ≤ 0. Les deux fonctions n'ont pas la même politique, et
    c'est voulu — ne pas « harmoniser » sans y repenser.
    """
    if transforms is None:
        transforms = {}
    if not isinstance(transforms, dict):
        raise ValueError(
            "transforms attend un dictionnaire noeud -> TRS, reçu "
            f"{type(transforms).__name__}")
    doc, binc = lire_glb(data)
    nodes = _l(doc, "nodes")
    for cle, trs in transforms.items():
        try:
            i = int(cle)
        except (TypeError, ValueError):
            raise ValueError(f"clé de noeud non numérique : {cle!r}") from None
        if not (0 <= i < len(nodes)):
            raise ValueError(f"noeud {i} hors du document ({len(nodes)} noeuds)")
        n = nodes[i]
        n.pop("matrix", None)
        for champ, taille in _TAILLES.items():
            if champ not in trs:
                continue
            v = [float(x) for x in trs[champ]]
            if len(v) != taille:
                raise ValueError(f"{champ} attend {taille} valeurs, reçu {len(v)}")
            if champ == "rotation":
                # glTF exige un quaternion UNITAIRE. Non normalisé, il déforme
                # chez les lecteurs stricts et pas chez les autres : un bug qui
                # ne se voit qu'à l'export, donc à attraper à l'écriture.
                norme = sum(x * x for x in v) ** 0.5
                if abs(norme - 1.0) > _TOLERANCE_QUATERNION:
                    raise ValueError(
                        "rotation attend un quaternion normé [x,y,z,w] ; "
                        f"norme reçue {norme:.4f}")
            n[champ] = v
    return ecrire_glb(doc, binc)
