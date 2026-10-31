# -*- coding: utf-8 -*-
"""t391 (31/10/2026) — l'écran Importer du 3D Studio : FBX (Mixamo et autres) et VRM (VRoid) en plus de GLB, glTF,
OBJ et STL. Local et gratuit.

- GLB, glTF, OBJ, STL : `mesh_convert.importer_job`, inchangé.
- VRM : un VRM 0.x / 1.0 EST un GLB (en-tête `glTF`, extension `VRM` / `VRMC_vrm`) — il entre tel quel, squelette
  humanoïde et matériaux compris ; les extensions VRM restent dans le document.
- FBX : converti en GLB par Blender en arrière-plan (`blender -b`, script FIXE, chemins passés en JSON), squelette,
  poids et animations gardés ; Blender introuvable → `BlenderIndisponible` (503), même règle que l'export FBX
  (`studio3d_export`, dont les coutures `_blender` / `_executer` sont reprises : un seul endroit trouve Blender).
- Daz Genesis 8 / 8.1 (t405) : le FBX d'une figure + le dossier `.images` voisin (Daz range les cartes des cheveux, du
  cuir chevelu et des cils en TIFF EXTERNES). Les textures sont posées À CÔTÉ du FBX, chemins relatifs gardés, pour que
  l'import FBX de Blender les résolve ; `file.find_missing_files` retrouve celles qu'un chemin absolu de la machine Daz
  désigne ailleurs. TIFF gardé : l'export glTF de Blender convertit lui-même en PNG/JPEG. Le squelette Daz est gardé
  entier ; le manifeste dit `source: daz-g8`, le nombre d'os et les textures trouvées / manquantes.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from app.services import studio3d_export as SE

TAILLE_MAX = 200 * 1024 * 1024
EXT_DIRECTES = {".glb", ".gltf", ".obj", ".stl"}
EXT = EXT_DIRECTES | {".fbx", ".vrm"}

# Daz Genesis 8 : bornes du dossier de textures (un G8 complet, peau + yeux + cheveux + cils, tient en ~60 cartes 4K)
TEXTURES_NB_MAX = 400
TEXTURE_TAILLE_MAX = 256 * 1024 * 1024
TEXTURES_TOTAL_MAX = 1536 * 1024 * 1024
EXT_TEXTURES = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp", ".tga", ".exr", ".hdr", ".webp"}
_SEGMENT_INTERDIT = re.compile(r'[<>:"|?*\x00-\x1f]')
# des os que seul un squelette Genesis 8 / 8.1 porte (noms Daz, gardés tels quels par l'import FBX)
OS_GENESIS8 = {"hip", "pelvis", "abdomenLower", "chestUpper", "lThighBend", "rThighBend", "lShldrBend", "rShldrBend"}

SCRIPT_FBX_GLB = r'''# DeepotusVideo — import FBX → GLB (t391, t405). Script FIXE : seuls les chemins arrivent, en JSON, après « -- ».
import bpy, json, os, sys
a = json.loads(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=a["source"], automatic_bone_orientation=True, use_image_search=True)
if a.get("textures"):
    # t405 : Daz écrit les chemins absolus de SA machine ; les cartes déposées sont à côté du FBX
    bpy.ops.file.find_missing_files(directory=a["textures"], find_all=False)
def _base(chemin):
    return os.path.basename(chemin.replace("\\", "/"))
images = [i for i in bpy.data.images if i.source in ("FILE", "SEQUENCE", "TILED") and i.filepath]
trouvees = sorted({_base(i.filepath) for i in images if os.path.isfile(bpy.path.abspath(i.filepath))})
manquantes = sorted({_base(i.filepath) for i in images if not os.path.isfile(bpy.path.abspath(i.filepath))})
noms_os = [b.name for o in bpy.data.objects if o.type == "ARMATURE" for b in o.data.bones]
bpy.ops.export_scene.gltf(filepath=a["sortie"], export_format="GLB", export_animations=True, export_skins=True)
if a.get("rapport"):
    with open(a["rapport"], "w", encoding="utf-8") as f:
        json.dump({"os": len(noms_os), "noms_os": noms_os[:2000], "trouvees": trouvees,
                   "manquantes": sorted(set(manquantes) - set(trouvees))}, f)
print("DZIMPORT fin")
'''


class RefusImport(ValueError):
    """Un fichier que l'import refuse (→ 400)."""


def _chemin_texture(nom: str) -> Path:
    """Le chemin RELATIF d'une texture déposée (`Genesis 8 Female.images/cils_D.tif`, venu de webkitRelativePath) :
    jamais absolu, jamais « .. », caractères interdits par Windows refusés — sinon RefusImport."""
    brut = str(nom or "")
    morceaux = [m for m in re.split(r"[\\/]+", brut) if m not in ("", ".")]
    if not morceaux or len(morceaux) > 6 or len(brut) > 260:
        raise RefusImport(f"nom de texture refusé : {brut[:80]}")
    for m in morceaux:
        if m == ".." or _SEGMENT_INTERDIT.search(m) or m.endswith((" ", ".")):
            raise RefusImport(f"nom de texture refusé : {brut[:80]}")
    if Path(morceaux[-1]).suffix.lower() not in EXT_TEXTURES:
        raise RefusImport(f"{morceaux[-1]} n'est pas une image (TIFF, PNG, JPEG, BMP, TGA, EXR, HDR, WebP)")
    return Path(*morceaux)


def _textures_valides(textures) -> list[tuple[Path, bytes]]:
    """Bornes du dossier (nombre, taille par fichier, total) ; un doublon de chemin ou un fichier vide est sauté."""
    textures = list(textures or [])
    if len(textures) > TEXTURES_NB_MAX:
        raise RefusImport(f"{len(textures)} textures : {TEXTURES_NB_MAX} au plus par import")
    sures, total, vus = [], 0, set()
    for nom, octets in textures:
        rel = _chemin_texture(nom)
        if len(octets) > TEXTURE_TAILLE_MAX:
            raise RefusImport(f"{rel.name} : plus de {TEXTURE_TAILLE_MAX // (1024 * 1024)} Mo")
        total += len(octets)
        if total > TEXTURES_TOTAL_MAX:
            raise RefusImport(f"textures : plus de {TEXTURES_TOTAL_MAX // (1024 * 1024)} Mo en tout")
        cle = rel.as_posix().lower()
        if octets and cle not in vus:
            vus.add(cle)
            sures.append((rel, octets))
    return sures


def _fbx_vers_glb(data: bytes, nom_fbx: str = "source.fbx", textures=None) -> tuple[bytes, dict]:
    """Le FBX (et ses textures, posées à côté) passe par Blender ; rend (GLB, rapport) — le rapport vaut {} si le
    script ne l'a pas écrit."""
    e = SE._blender()
    if not e.get("dispo"):
        raise SE.BlenderIndisponible("Blender 4.2 ou plus récent est introuvable (BLENDER_PATH, Program Files ou "
                                     "PATH) — l'import FBX passe par lui ; installe-le depuis blender.org, c'est gratuit.")
    from app.config import settings
    tmp = settings.outputs_path / "assets3d" / f"_import_{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True)
    try:
        modele = tmp / "modele"
        modele.mkdir()
        source = modele / nom_fbx
        source.write_bytes(data)
        for rel, octets in textures or []:
            cible = modele / rel
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(octets)
        (tmp / "import.py").write_text(SCRIPT_FBX_GLB, encoding="utf-8")
        params = {"source": str(source), "sortie": str(tmp / "sortie.glb"), "rapport": str(tmp / "rapport.json")}
        if textures:
            params["textures"] = str(modele)
        argv = [str(e["exe"]), "-b", "--factory-startup", "--python", str(tmp / "import.py"), "--",
                json.dumps(params, ensure_ascii=True)]
        try:
            code, texte = SE._executer(argv, SE.DELAI_BLENDER_S)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Blender a dépassé {int(SE.DELAI_BLENDER_S)} s")
        produit = tmp / "sortie.glb"
        if code != 0 or not produit.is_file() or produit.stat().st_size == 0:
            fin = " ".join(texte.strip().splitlines()[-3:])[:300]
            raise RuntimeError(f"Blender n'a pas converti le FBX (code {code}) : {fin}")
        rapport = {}
        if (tmp / "rapport.json").is_file():
            try:
                rapport = json.loads((tmp / "rapport.json").read_text(encoding="utf-8"))
            except ValueError:
                rapport = {}
        return produit.read_bytes(), (rapport if isinstance(rapport, dict) else {})
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
        data, nom, par = _fbx_vers_glb(data)[0], Path(nom).stem + ".glb", "blender"
    job = mesh_convert.importer_job(data, nom)
    return {"job": job, "format": ext.lstrip("."), "converti_par": par}


def importer_daz(data: bytes, nom_fichier: str, textures=None) -> dict:
    """Une figure Daz Genesis 8 / 8.1 exportée en FBX + son dossier de textures (liste de (chemin relatif, octets)).

    Rend {job, format, converti_par, source, os, genesis8, textures: {envoyees, trouvees, manquantes}}."""
    from app.services import asset3d_service as A3, mesh_convert, mesh_report
    nom = Path(str(nom_fichier or "figure.fbx").replace("\\", "/")).name
    if Path(nom).suffix.lower() != ".fbx":
        raise RefusImport("Daz Genesis 8 : le FBX exporté par Daz Studio est attendu (.fbx)")
    if not data:
        raise RefusImport("fichier vide")
    if len(data) > TAILLE_MAX:
        raise RefusImport(f"fichier de plus de {TAILLE_MAX // (1024 * 1024)} Mo")
    if _SEGMENT_INTERDIT.search(nom) or nom.endswith((" ", ".")):
        nom = "figure.fbx"
    sures = _textures_valides(textures)
    glb, rapport = _fbx_vers_glb(data, nom, sures)
    job = mesh_convert.importer_job(glb, Path(nom).stem + ".glb")
    nb_os = rapport.get("os")
    if not isinstance(nb_os, int):
        from app.services import studio3d_ouvert as SO
        nb_os = int((SO.fiche(job).get("rig") or {}).get("os") or 0)
    noms_os = set(rapport.get("noms_os") or [])
    genesis8 = len(OS_GENESIS8 & noms_os) >= 6
    tex = {"envoyees": len(sures), "trouvees": list(rapport.get("trouvees") or []),
           "manquantes": list(rapport.get("manquantes") or [])}
    try:
        m = A3.read_manifest(job)
    except FileNotFoundError:
        m = {}
    A3.write_manifest(mesh_report.job_dir(job), {
        **m, "source": "daz-g8", "os": nb_os, "genesis8_reconnu": genesis8, "textures_envoyees": tex["envoyees"],
        "textures_trouvees": tex["trouvees"], "textures_manquantes": tex["manquantes"]})
    return {"job": job, "format": "fbx", "converti_par": "blender", "source": "daz-g8", "os": nb_os,
            "genesis8": genesis8, "textures": tex}
