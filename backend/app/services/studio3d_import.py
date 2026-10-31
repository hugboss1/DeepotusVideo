# -*- coding: utf-8 -*-
"""t391 (31/10/2026) — l'écran Importer du 3D Studio : FBX (Mixamo et autres) et VRM (VRoid) en plus de GLB, glTF,
OBJ et STL. Local et gratuit.

- GLB, glTF, OBJ, STL : `mesh_convert.importer_job`, inchangé.
- VRM : un VRM 0.x / 1.0 EST un GLB (en-tête `glTF`, extension `VRM` / `VRMC_vrm`) — il entre tel quel, squelette
  humanoïde et matériaux compris ; les extensions VRM restent dans le document.
- FBX : converti en GLB par Blender en arrière-plan (`blender -b`, script FIXE, chemins passés en JSON), squelette,
  poids et animations gardés ; Blender introuvable → `BlenderIndisponible` (503), même règle que l'export FBX
  (`studio3d_export`, dont les coutures `_blender` / `_executer` sont reprises : un seul endroit trouve Blender).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from app.services import studio3d_export as SE

TAILLE_MAX = 200 * 1024 * 1024
EXT_DIRECTES = {".glb", ".gltf", ".obj", ".stl"}
EXT = EXT_DIRECTES | {".fbx", ".vrm"}

SCRIPT_FBX_GLB = r'''# DeepotusVideo — import FBX → GLB (t391). Script FIXE : seuls les chemins arrivent, en JSON, après « -- ».
import bpy, json, sys
a = json.loads(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=a["source"], automatic_bone_orientation=True)
bpy.ops.export_scene.gltf(filepath=a["sortie"], export_format="GLB", export_animations=True, export_skins=True)
print("DZIMPORT fin")
'''


class RefusImport(ValueError):
    """Un fichier que l'import refuse (→ 400)."""


def _fbx_vers_glb(data: bytes) -> bytes:
    e = SE._blender()
    if not e.get("dispo"):
        raise SE.BlenderIndisponible("Blender 4.2 ou plus récent est introuvable (BLENDER_PATH, Program Files ou "
                                     "PATH) — l'import FBX passe par lui ; installe-le depuis blender.org, c'est gratuit.")
    from app.config import settings
    tmp = settings.outputs_path / "assets3d" / f"_import_{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True)
    try:
        (tmp / "source.fbx").write_bytes(data)
        (tmp / "import.py").write_text(SCRIPT_FBX_GLB, encoding="utf-8")
        params = json.dumps({"source": str(tmp / "source.fbx"), "sortie": str(tmp / "sortie.glb")}, ensure_ascii=True)
        argv = [str(e["exe"]), "-b", "--factory-startup", "--python", str(tmp / "import.py"), "--", params]
        try:
            code, texte = SE._executer(argv, SE.DELAI_BLENDER_S)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Blender a dépassé {int(SE.DELAI_BLENDER_S)} s")
        produit = tmp / "sortie.glb"
        if code != 0 or not produit.is_file() or produit.stat().st_size == 0:
            fin = " ".join(texte.strip().splitlines()[-3:])[:300]
            raise RuntimeError(f"Blender n'a pas converti le FBX (code {code}) : {fin}")
        return produit.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def importer(data: bytes, nom_fichier: str) -> dict:
    """Le fichier devient un job ; rend {job, format, converti_par}."""
    from app.services import mesh_convert
    nom = Path(str(nom_fichier or "modele")).name
    ext = Path(nom).suffix.lower()
    if ext not in EXT:
        raise RefusImport(f"format {ext or '?'} non lu : GLB, glTF, OBJ, STL, FBX ou VRM")
    if not data:
        raise RefusImport("fichier vide")
    if len(data) > TAILLE_MAX:
        raise RefusImport(f"fichier de plus de {TAILLE_MAX // (1024 * 1024)} Mo")
    par = None
    if ext == ".vrm":
        if data[:4] != b"glTF":
            raise RefusImport("ce VRM n'est pas un GLB binaire")
        data, nom, par = data, Path(nom).stem + ".glb", "vrm"
    elif ext == ".fbx":
        data, nom, par = _fbx_vers_glb(data), Path(nom).stem + ".glb", "blender"
    job = mesh_convert.importer_job(data, nom)
    return {"job": job, "format": ext.lstrip("."), "converti_par": par}
