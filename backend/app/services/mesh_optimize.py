"""Mesh optimize — budgets de triangles pour les assets 3D (chantier 10a).

Simplification locale et gratuite via gltfpack (meshoptimizer), embarqué dans
bin/ comme ffmpeg et résolu par le PATH. Sortie : model.opt.glb à côté du
model.glb du job, plus optimize.json (stats avant/après persistées, relues par
l'UI au retour sur l'asset).

Choix : `-noq` (pas de quantization) — GLB sans extension, importable partout
(Unity, Godot, viewers) ; le budget de triangles est l'objectif, pas le poids
du fichier (les textures dominent). Passe qualité d'abord (-si R), puis passe
aggressive (-sa) uniquement si le résultat dépasse la cible de +15 %.
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

# Presets calqués sur la référence sorceress (Game Ready = défaut UI).
PRESETS = {
    "micro": 500,        # micro prop
    "small": 1000,       # small prop
    "prop": 2500,
    "detailed": 5000,    # detailed prop
    "game": 10000,       # game ready (défaut)
    "balanced": 25000,
    "high": 50000,       # high detail
    "ultra": 100000,
}
TARGET_MIN, TARGET_MAX = 100, 2_000_000
_GLB_MAGIC = 0x46546C67
_CHUNK_JSON = 0x4E4F534A


def _read_glb_json(path: Path) -> dict:
    """Chunk JSON d'un .glb (parse pur stdlib, données binaires ignorées)."""
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"{path.name}: fichier trop court pour un GLB")
    magic, version, _total = struct.unpack_from("<III", raw, 0)
    if magic != _GLB_MAGIC:
        raise ValueError(f"{path.name}: magic GLB invalide")
    if version != 2:
        raise ValueError(f"{path.name}: version glTF {version} non gérée")
    off = 12
    while off + 8 <= len(raw):
        clen, ctype = struct.unpack_from("<II", raw, off)
        off += 8
        if ctype == _CHUNK_JSON:
            return json.loads(raw[off:off + clen].decode("utf-8"))
        off += clen + (-clen % 4)
    raise ValueError(f"{path.name}: chunk JSON introuvable")


def glb_stats(path: Path) -> dict:
    """Triangles/vertices/meshes/materials d'un GLB. Les triangles sont
    comptés par primitive de mesh (mode TRIANGLES), pas par instance de
    node — identique pour nos assets mono-mesh."""
    g = _read_glb_json(path)
    acc = g.get("accessors", [])
    tris = verts = 0
    for mesh in g.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos = prim.get("attributes", {}).get("POSITION")
            if pos is not None and pos < len(acc):
                verts += int(acc[pos].get("count", 0))
            if prim.get("mode", 4) != 4:      # TRIANGLES uniquement
                continue
            idx = prim.get("indices")
            if idx is not None and idx < len(acc):
                tris += int(acc[idx].get("count", 0)) // 3
            elif pos is not None and pos < len(acc):
                tris += int(acc[pos].get("count", 0)) // 3
    return {"tris": tris, "verts": verts,
            "meshes": len(g.get("meshes", [])),
            "materials": len(g.get("materials", [])),
            "bytes": path.stat().st_size}


def _gltfpack() -> str:
    exe = shutil.which("gltfpack")
    if not exe:
        # Cherche aussi le bin/ de l'app même si le PATH du process ne l'a pas
        # (backend relancé à la main, service tiers, PATH tronqué).
        for cand in (Path(__file__).resolve().parents[3] / "bin" / "gltfpack.exe",
                     Path(__file__).resolve().parents[4] / "bin" / "gltfpack.exe"):
            if cand.is_file():
                return str(cand)
        raise RuntimeError(
            "Optimisation 3D indisponible : gltfpack est absent de cette "
            "installation. Réinstallez l'application pour l'obtenir.")
    return exe


def resolve_target(target_tris=None, preset: str | None = None) -> tuple[int, str | None]:
    """Cible en triangles depuis un preset ou une valeur libre (clampée)."""
    if preset is not None:
        if preset not in PRESETS:
            raise ValueError(
                f"preset inconnu: {preset!r} (attendu: {', '.join(PRESETS)})")
        return PRESETS[preset], preset
    if target_tris is None:
        return PRESETS["game"], "game"
    try:
        t = int(target_tris)
    except (TypeError, ValueError):
        raise ValueError(f"target_tris invalide: {target_tris!r}")
    return max(TARGET_MIN, min(TARGET_MAX, t)), None


def optimize_glb(job: str, target_tris=None, preset: str | None = None) -> dict:
    """Simplifie outputs/assets3d/{job}/model.glb vers model.opt.glb.
    Synchrone (quelques secondes) — la route l'exécute dans un executor."""
    d = settings.outputs_path / "assets3d" / Path(job).name
    src = d / "model.glb"
    if not src.is_file():
        raise FileNotFoundError("model.glb introuvable pour ce job")
    exe = _gltfpack()
    target, preset = resolve_target(target_tris, preset)

    before = glb_stats(src)
    ratio = max(0.001, min(1.0, target / max(1, before["tris"])))
    out = d / "model.opt.glb"

    def run(extra):
        r = subprocess.run(
            [exe, "-i", str(src), "-o", str(out),
             "-si", f"{ratio:.6f}", "-noq"] + extra,
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not out.is_file():
            raise RuntimeError(
                f"gltfpack a échoué ({r.returncode}): "
                f"{(r.stderr or r.stdout or '').strip()[:300]}")

    run([])
    after = glb_stats(out)
    aggressive = False
    if ratio < 1.0 and after["tris"] > target * 1.15:
        run(["-sa"])                      # passe 2 : atteint la cible
        after = glb_stats(out)
        aggressive = True

    info = {
        "before": before, "after": after,
        "target_tris": target, "preset": preset,
        "ratio": round(ratio, 6), "aggressive": aggressive,
        "reduction_pct": round(
            100.0 * (1 - after["tris"] / max(1, before["tris"])), 1),
        "file": "model.opt.glb",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (d / "optimize.json").write_text(
        json.dumps(info, indent=1), encoding="utf-8")
    return info
