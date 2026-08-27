"""Impression 3D — le service print3d (plan 2026-08-27-impression-3d-slicer).

Phase 0 : lecteur GLB minimal PYTHON PUR (triangles monde, refus motivés
des compressions), écrivains STL binaire + 3MF (stdlib), échelle mm et
pose au sol, dossiers d'export + routes + ouverture slicer gardée.

Run: pytest tests/test_print3d.py -q
"""
import json as _json
import os
import pathlib
import struct
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── fabrique de GLB : le banc écrit ses fixtures à l'octet ───────────────────

def _glb(doc, bin_data=b""):
    j = _json.dumps(doc, separators=(",", ":")).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    chunks = struct.pack("<I", len(j)) + b"JSON" + j
    if bin_data:
        b = bin_data + b"\x00" * ((4 - len(bin_data) % 4) % 4)
        chunks += struct.pack("<I", len(b)) + b"BIN\x00" + b
    return b"glTF" + struct.pack("<II", 2, 12 + len(chunks)) + chunks


def _glb_cube_translate():
    """Cube 2×2×2 centré origine ; nœud parent translation x+10 ; l'enfant
    porte le maillage ET une MATRICE colonne-majeure z+5 — la composition
    parent×enfant est donc exercée, pas seulement lue."""
    pos = []
    for x in (-1, 1):
        for y in (-1, 1):
            for z in (-1, 1):
                pos += [x, y, z]
    idx = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1,
           2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3]
    vb = struct.pack("<24f", *pos)
    ib = struct.pack("<36H", *idx)
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [
            {"translation": [10, 0, 0], "children": [1]},
            {"matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 5, 1],
             "mesh": 0},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 8,
             "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 36,
             "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(vb)},
            {"buffer": 0, "byteOffset": len(vb), "byteLength": len(ib)},
        ],
        "buffers": [{"byteLength": len(vb) + len(ib)}],
    }
    return _glb(doc, vb + ib)


def _glb_ext_requise(nom):
    return _glb({"asset": {"version": "2.0"}, "extensionsRequired": [nom],
                 "scenes": [{"nodes": []}], "scene": 0})


# ── A. le lecteur GLB : triangles MONDE, refus motivés ───────────────────────

def test_le_lecteur_glb_sort_les_triangles_en_monde():
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_glb_cube_translate())
    assert len(tris) == 12
    xs = [v[0] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    assert min(xs) == pytest.approx(9.0) and max(xs) == pytest.approx(11.0)
    assert min(zs) == pytest.approx(4.0) and max(zs) == pytest.approx(6.0)


def test_le_lecteur_refuse_parlant_compressions_et_formes_hors_perimetre():
    from app.services import print3d as P3
    with pytest.raises(ValueError, match="meshopt"):
        P3.lire_glb_triangles(_glb_ext_requise("EXT_meshopt_compression"))
    with pytest.raises(ValueError, match="[Dd]raco"):
        P3.lire_glb_triangles(_glb_ext_requise("KHR_draco_mesh_compression"))
    with pytest.raises(ValueError, match="glTF"):
        P3.lire_glb_triangles(b"PAS-UN-GLB")
    # buffer externe (uri) : nos GLB sont monolithiques — refus parlant
    externe = _glb({"asset": {"version": "2.0"}, "scene": 0,
                    "scenes": [{"nodes": [0]}],
                    "nodes": [{"mesh": 0}],
                    "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                                "mode": 4}]}],
                    "accessors": [{"bufferView": 0, "componentType": 5126,
                                   "count": 3, "type": "VEC3"}],
                    "bufferViews": [{"buffer": 0, "byteOffset": 0,
                                     "byteLength": 36}],
                    "buffers": [{"uri": "ailleurs.bin", "byteLength": 36}]})
    with pytest.raises(ValueError, match="externe"):
        P3.lire_glb_triangles(externe)
    # primitives non triangulaires : hors périmètre, dit
    lignes = _glb_cube_translate().replace(b'"mode":4', b'"mode":1')
    with pytest.raises(ValueError, match="TRIANGLES"):
        P3.lire_glb_triangles(lignes)


def test_le_lecteur_lit_un_glb_du_producteur_maison():
    # le GLB que l'app produit ELLE-MÊME (Material Forge) se lit tel quel
    from app.services import print3d as P3
    from app.services.gltf_builder import build_glb
    glb = build_glb({}, {}, mesh="cube")
    tris = P3.lire_glb_triangles(glb)
    assert len(tris) >= 12
    xs = [v[0] for t in tris for v in t]
    assert max(xs) > min(xs)              # un volume, pas un point
