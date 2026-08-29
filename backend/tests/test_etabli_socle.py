"""L'Établi P1 — chirurgie GLB et chronologie des étapes
(plan 2026-08-29-etabli-p1-socle-serveur).

Le banc ne SORT jamais : les GLB sont fabriqués par gltf_builder et relus par
print3d, les deux lecteurs déjà éprouvés du dépôt.

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_socle.py
"""
import json
import os
import pathlib
import struct
import sys
import tempfile
import zlib

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _png1x1() -> bytes:
    """PNG RGBA 1x1 valide — déclenche le quad de sol de gltf_builder, donc
    un GLB à DEUX nœuds, deux matériaux et une texture."""
    def ch(tag: bytes, d: bytes) -> bytes:
        c = tag + d
        return (struct.pack(">I", len(d)) + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
            + ch(b"IEND", b""))


def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _cube_et_sol() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc",
                                  stage_png=_png1x1())


# ── A. lecture / écriture ────────────────────────────────────────────────────

def test_aller_retour_glb_ne_deforme_rien():
    from app.services import mesh_edit
    data = _cube()
    doc, binc = mesh_edit.lire_glb(data)
    refait = mesh_edit.ecrire_glb(doc, binc)
    doc2, bin2 = mesh_edit.lire_glb(refait)
    assert doc == doc2
    assert binc == bin2


def test_le_glb_reecrit_se_relit_par_print3d():
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    tris = print3d.lire_glb_triangles(mesh_edit.ecrire_glb(doc, binc))
    assert len(tris) == 12
    assert print3d.bbox(tris) == ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_un_fichier_qui_n_est_pas_un_glb_est_refuse_parlant():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="magic GLB"):
        mesh_edit.lire_glb(b"ceci n'est pas un GLB")
