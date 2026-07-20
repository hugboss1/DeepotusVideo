"""Recette chantier 10a — mesh_optimize (budgets de triangles, gltfpack).

Lancé avec le python embarqué de l'app installée, gltfpack du bin de l'app sur
le PATH, et outputs isolé :

  set PATH=C:\\Users\\olivi\\AppData\\Local\\DeepotusVideoGen\\bin;%PATH%
  runtime\\python\\python.exe -m pytest backend/tests/test_mesh_optimize.py -v

Couvre : stats GLB exactes sur un tore synthétique aux comptes connus,
simplification vers la cible (vrai gltfpack, ±20 %), passe aggressive,
presets/clamps, erreurs (job absent, preset inconnu), GLB de sortie valide.
"""
import json
import math
import shutil
import struct
from pathlib import Path

import pytest

from app.config import settings
from app.services import mesh_optimize as MO


# ── GLB synthétique (pur stdlib) ─────────────────────────────────────────────

def build_torus_glb(path: Path, seg_u=100, seg_v=100, R=2.0, r=0.7):
    """Tore indexé : (seg_u*seg_v*2) triangles, ((seg_u+1)*(seg_v+1)) sommets.
    GLB 2.0 minimal mais conforme (min/max sur POSITION, padding des chunks)."""
    nu, nv = seg_u + 1, seg_v + 1
    pos = []
    for i in range(nu):
        u = 2 * math.pi * i / seg_u
        for j in range(nv):
            v = 2 * math.pi * j / seg_v
            x = (R + r * math.cos(v)) * math.cos(u)
            y = r * math.sin(v)
            z = (R + r * math.cos(v)) * math.sin(u)
            pos.extend((x, y, z))
    idx = []
    for i in range(seg_u):
        for j in range(seg_v):
            a = i * nv + j
            b = (i + 1) * nv + j
            idx.extend((a, b, a + 1, b, b + 1, a + 1))

    pos_b = struct.pack(f"<{len(pos)}f", *pos)
    idx_b = struct.pack(f"<{len(idx)}I", *idx)
    bin_chunk = pos_b + idx_b
    bin_chunk += b"\x00" * (-len(bin_chunk) % 4)

    xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(bin_chunk)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_b)},
            {"buffer": 0, "byteOffset": len(pos_b), "byteLength": len(idx_b)},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(pos) // 3,
             "type": "VEC3",
             "min": [min(xs), min(ys), min(zs)],
             "max": [max(xs), max(ys), max(zs)]},
            {"bufferView": 1, "componentType": 5125, "count": len(idx),
             "type": "SCALAR"},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1}]}],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_chunk)
    glb = struct.pack("<III", 0x46546C67, 2, total)
    glb += struct.pack("<II", len(js), 0x4E4F534A) + js
    glb += struct.pack("<II", len(bin_chunk), 0x004E4942) + bin_chunk
    path.write_bytes(glb)
    return {"tris": seg_u * seg_v * 2, "verts": nu * nv}


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(type(settings), "outputs_path",
                        property(lambda self: tmp_path))
    return tmp_path


@pytest.fixture
def torus_job(outputs):
    """Job asset3d synthétique 'j-torus' avec un model.glb de 20 000 tris."""
    d = outputs / "assets3d" / "j-torus"
    d.mkdir(parents=True)
    expected = build_torus_glb(d / "model.glb")
    return "j-torus", expected


# ── tests ────────────────────────────────────────────────────────────────────

def test_gltfpack_on_path():
    assert shutil.which("gltfpack"), \
        "gltfpack introuvable sur le PATH — préfixer avec le bin de l'app"


def test_glb_stats_exact(torus_job, outputs):
    job, expected = torus_job
    st = MO.glb_stats(outputs / "assets3d" / job / "model.glb")
    assert st["tris"] == expected["tris"] == 20000
    assert st["verts"] == expected["verts"] == 10201
    assert st["meshes"] == 1
    assert st["bytes"] > 0


def test_optimize_hits_target(torus_job, outputs):
    job, expected = torus_job
    info = MO.optimize_glb(job, target_tris=2000)
    assert info["before"]["tris"] == expected["tris"]
    # cible atteinte à ±20 % (grain de la simplification)
    assert info["after"]["tris"] <= 2000 * 1.2
    assert info["after"]["tris"] >= 200
    assert info["reduction_pct"] >= 85.0
    # la sortie est un GLB 2.0 valide, relu par notre propre parseur
    out = outputs / "assets3d" / job / "model.opt.glb"
    assert out.is_file()
    assert MO.glb_stats(out)["tris"] == info["after"]["tris"]
    # stats persistées et relisibles
    saved = json.loads((outputs / "assets3d" / job / "optimize.json")
                       .read_text(encoding="utf-8"))
    assert saved["after"]["tris"] == info["after"]["tris"]
    assert saved["target_tris"] == 2000


def test_optimize_preset_game(torus_job, outputs):
    job, _ = torus_job
    info = MO.optimize_glb(job, preset="game")
    assert info["preset"] == "game"
    assert info["target_tris"] == 10000
    assert info["after"]["tris"] <= 10000 * 1.2


def test_ratio_above_one_is_noop_copy(torus_job, outputs):
    """Cible au-dessus du modèle : ratio clampé à 1, repack sans simplification."""
    job, expected = torus_job
    info = MO.optimize_glb(job, target_tris=500000)
    assert info["ratio"] == 1.0
    assert info["after"]["tris"] == expected["tris"]


def test_resolve_target_clamps_and_defaults():
    assert MO.resolve_target(None, None) == (10000, "game")
    assert MO.resolve_target(50, None)[0] == MO.TARGET_MIN
    assert MO.resolve_target(99999999, None)[0] == MO.TARGET_MAX
    with pytest.raises(ValueError):
        MO.resolve_target(None, "nope")
    with pytest.raises(ValueError):
        MO.resolve_target("abc", None)


def test_missing_job_raises(outputs):
    with pytest.raises(FileNotFoundError):
        MO.optimize_glb("nope-123")


def test_path_traversal_neutralized(torus_job, outputs):
    """Path(job).name neutralise ../ : un job forgé est ramené à son basename
    et reste confiné à outputs/assets3d (même garde que les routes 9a)."""
    job, _ = torus_job
    info = MO.optimize_glb("../../" + job, target_tris=5000)
    # tout est resté DANS le dossier du job — rien écrit hors d'assets3d
    assert (outputs / "assets3d" / job / "model.opt.glb").is_file()
    assert info["after"]["tris"] <= 5000 * 1.2
    with pytest.raises(FileNotFoundError):
        MO.optimize_glb("..\\..\\windows")      # basename inexistant -> 404
