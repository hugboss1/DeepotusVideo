# -*- coding: utf-8 -*-
"""Impression 3D — le service `print3d` (plan 2026-08-27-impression-3d-slicer).

100 % LOCAL et 100 % PYTHON PUR (le style maison : gltf_builder écrit déjà
du GLB sans numpy, forge3d du STL) : lecteur GLB minimal → triangles MONDE,
écrivains STL binaire et 3MF (stdlib), mise à l'échelle en millimètres.
Le runtime embarqué n'a NI numpy NI trimesh (mesuré 27/08) et ignore
PYTHONPATH — aucune dépendance nouvelle ici, jamais.

Périmètre du lecteur (D2 du plan) : GLB v2 monolithique (JSON + BIN),
accessors POSITION float32 + indices u16/u32 (ou non indexé), hiérarchie de
nœuds à TRS/matrices COMPOSÉES, primitives TRIANGLES. Refus PARLANTS :
compressions (draco, meshopt — donc model.opt.glb), buffers externes,
primitives non triangulaires. Un GLB hors périmètre a toujours la voie
model.obj/model.stl du moteur quand elle existe.
"""
from __future__ import annotations

import json
import struct

# extensions de compression : illisibles sans décodeur — refus motivé
_REFUS_EXTENSIONS = {
    "KHR_draco_mesh_compression":
        "GLB compressé draco — hors périmètre du convertisseur local",
    "EXT_meshopt_compression":
        "GLB compressé meshopt (model.opt.glb est pour les moteurs de jeu) "
        "— prends model.glb, la source non compressée",
}


# ── matrices 4×4 (listes de 16, ROW-major interne) ───────────────────────────

_IDENTITE = [1.0, 0.0, 0.0, 0.0,
             0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0,
             0.0, 0.0, 0.0, 1.0]


def _mat_mul(a, b):
    out = [0.0] * 16
    for i in range(4):
        for j in range(4):
            out[i * 4 + j] = sum(a[i * 4 + k] * b[k * 4 + j]
                                 for k in range(4))
    return out


def _mat_de_gltf(m16):
    """glTF stocke COLONNE-majeur ; l'interne est ligne-majeur."""
    return [m16[j * 4 + i] for i in range(4) for j in range(4)]


def _mat_trs(node):
    t = node.get("translation") or [0.0, 0.0, 0.0]
    q = node.get("rotation") or [0.0, 0.0, 0.0, 1.0]
    s = node.get("scale") or [1.0, 1.0, 1.0]
    x, y, z, w = (float(v) for v in q)
    # rotation quaternion → 3×3 (convention glTF [x, y, z, w])
    r = [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
         2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
         2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]
    return [r[0] * s[0], r[1] * s[1], r[2] * s[2], float(t[0]),
            r[3] * s[0], r[4] * s[1], r[5] * s[2], float(t[1]),
            r[6] * s[0], r[7] * s[1], r[8] * s[2], float(t[2]),
            0.0, 0.0, 0.0, 1.0]


def _mat_locale(node):
    if "matrix" in node:
        return _mat_de_gltf([float(v) for v in node["matrix"]])
    return _mat_trs(node)


def _appliquer(m, p):
    x, y, z = p
    return (m[0] * x + m[1] * y + m[2] * z + m[3],
            m[4] * x + m[5] * y + m[6] * z + m[7],
            m[8] * x + m[9] * y + m[10] * z + m[11])


# ── GLB : chunks, accessors, parcours ────────────────────────────────────────

def _chunks(data: bytes):
    if len(data) < 12 or data[:4] != b"glTF":
        raise ValueError("GLB attendu (magic glTF absent)")
    version, longueur = struct.unpack_from("<II", data, 4)
    if version != 2:
        raise ValueError(f"GLB v2 attendu (v{version})")
    doc, binc = None, b""
    off = 12
    while off + 8 <= min(longueur, len(data)):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        off += 8
        chunk = data[off:off + clen]
        off += clen + ((4 - clen % 4) % 4)
        if ctype == b"JSON":
            doc = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            binc = chunk
    if doc is None:
        raise ValueError("GLB sans chunk JSON")
    return doc, binc


_TAILLE_COMPOSANT = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_NB_COMPOSANTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
_FMT = {5123: "H", 5125: "I", 5126: "f"}


def _accessor(doc, binc, i):
    a = doc["accessors"][i]
    ct, ty = a["componentType"], a["type"]
    if ct not in _FMT:
        raise ValueError(f"accessor: componentType {ct} hors périmètre")
    bv = doc["bufferViews"][a["bufferView"]]
    buf = doc["buffers"][bv.get("buffer", 0)]
    if "uri" in buf:
        raise ValueError("buffer externe (uri) — nos GLB sont monolithiques, "
                         "hors périmètre")
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    n = _NB_COMPOSANTS[ty]
    taille = _TAILLE_COMPOSANT[ct] * n
    stride = bv.get("byteStride") or taille
    fmt = "<" + _FMT[ct] * n
    out = []
    for k in range(a["count"]):
        out.append(struct.unpack_from(fmt, binc, base + k * stride))
    return out


def lire_glb_triangles(data: bytes):
    """GLB v2 → liste de triangles ((x,y,z)×3) en coordonnées MONDE.

    Refus parlants (ValueError) : compressions requises, buffers externes,
    primitives non TRIANGLES, composants hors float32/u16/u32.
    """
    doc, binc = _chunks(data)
    for ext in doc.get("extensionsRequired") or []:
        if ext in _REFUS_EXTENSIONS:
            raise ValueError(_REFUS_EXTENSIONS[ext])
    tris = []

    def _mesh(im, monde):
        for prim in doc["meshes"][im].get("primitives", []):
            if prim.get("mode", 4) != 4:
                raise ValueError("primitives TRIANGLES seulement "
                                 f"(mode {prim.get('mode')}) — hors périmètre")
            pos = _accessor(doc, binc, prim["attributes"]["POSITION"])
            pts = [_appliquer(monde, p) for p in pos]
            if "indices" in prim:
                idx = [v[0] for v in _accessor(doc, binc, prim["indices"])]
            else:
                idx = list(range(len(pts)))
            for k in range(0, len(idx) - 2, 3):
                tris.append((pts[idx[k]], pts[idx[k + 1]], pts[idx[k + 2]]))

    def _noeud(i, parent):
        node = doc["nodes"][i]
        monde = _mat_mul(parent, _mat_locale(node))
        if "mesh" in node:
            _mesh(node["mesh"], monde)
        for enfant in node.get("children", []):
            _noeud(enfant, monde)

    scenes = doc.get("scenes") or []
    racines = scenes[doc.get("scene", 0)].get("nodes", []) if scenes else []
    for i in racines:
        _noeud(i, _IDENTITE)
    return tris
