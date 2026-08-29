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
