# -*- coding: utf-8 -*-
"""Conversion de formats — T105, plan-moteurs-3d T5 (R10e P4).

CE QUI EST LOCAL ET GRATUIT :
  export  GLB courant -> OBJ+MTL(+PNG), STL, 3MF (millimètres, print3d), glTF autonome (material_store.glb_to_gltf)
  import  OBJ, glTF (gltfpack), STL (print3d), GLB -> un JOB neuf `import_<nom>_<id>` que l'Établi voit
Les briques existent déjà : `print3d` lit un GLB en triangles monde et écrit STL et 3MF ; `gltfpack 1.2` (embarqué)
lit .obj/.gltf/.glb et écrit .glb ; `mesh_textures` sort les images ; `material_store.glb_to_gltf` écrit un .gltf
à tampon embarqué (un seul fichier).

CE QUI NE L'EST PAS, ET POURQUOI : `gltfpack -h` ne sort NI fbx, NI usdz, NI blend. Le FBX est propriétaire et son
écriture libre est partielle (un FBX ASCII 7.x est lu par Unity et Unreal, refusé par Blender — de mémoire, non
vérifié). On ne l'écrit donc pas : ces trois formats passent par **Meshy convert**, 1 crédit par TÂCHE quel que soit
le nombre de formats (docs.meshy.ai/en/api/convert relue le 06/10/2026 : `model_url` ou `input_task_id`,
`target_formats` ∈ glb fbx obj usdz blend stl 3mf, réponse `model_urls`). Le devis le dit avant le clic.

Aucune conversion n'écrase le maillage : les sorties Meshy vivent dans `<job>/convert/`, les exports locaux partent
au téléchargement, et le GLB source ne bouge pas.
"""
from __future__ import annotations

import io
import json
import math
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path

LOCAL_EXPORT = ("obj", "stl", "3mf", "gltf")
LOCAL_IMPORT = ("obj", "stl", "glb", "gltf")
MESHY_EXPORT = ("fbx", "usdz", "blend")
CONVERT_BASE = "openapi/v1/convert"
MAX_IMPORT_OCTETS = 200 * 1024 * 1024
POURQUOI_PAS_LOCAL = (
    "gltfpack 1.2 (embarqué) n'écrit que .gltf et .glb. Le FBX est propriétaire et son écriture libre est partielle "
    "(un FBX ASCII est lu par Unity et Unreal, refusé par Blender) ; USDZ et BLEND n'ont pas d'écriture stdlib "
    "raisonnable. Ces trois-là passent par Meshy convert, 1 crédit par tâche.")


def capacites() -> dict:
    from app.services import meshy_service as MS
    return {"local_export": list(LOCAL_EXPORT), "local_import": list(LOCAL_IMPORT), "meshy": list(MESHY_EXPORT),
            "credits_meshy": MS.CREDITS_FLAT["convert"], "pourquoi_pas_local": POURQUOI_PAS_LOCAL}


# ── GLB -> OBJ + MTL ─────────────────────────────────────────────────────────

def _normale_monde(m, n):
    """La normale passe par la COFACTRICE de la partie linéaire (l'inverse-transposée à un facteur près) puis est
    renormalisée : juste même sous une échelle non uniforme ; la translation n'y entre jamais."""
    a, b, c, d, e, f, g, h, i = m[0], m[1], m[2], m[4], m[5], m[6], m[8], m[9], m[10]
    cof = (e * i - f * h, -(d * i - f * g), d * h - e * g,
           -(b * i - c * h), a * i - c * g, -(a * h - b * g),
           b * f - c * e, -(a * f - c * d), a * e - b * d)
    det = a * cof[0] + b * cof[1] + c * cof[2]
    x = cof[0] * n[0] + cof[3] * n[1] + cof[6] * n[2]
    y = cof[1] * n[0] + cof[4] * n[1] + cof[7] * n[2]
    z = cof[2] * n[0] + cof[5] * n[1] + cof[8] * n[2]
    lg = math.sqrt(x * x + y * y + z * z) or 1.0
    s = -1.0 if det < 0 else 1.0
    return (s * x / lg, s * y / lg, s * z / lg)


def _primitives(doc: dict, binc: bytes):
    """(nom du matériau, positions monde, normales monde, uv, indices) par primitive TRIANGLES de la scène. Réutilise
    les lecteurs de `print3d` (accesseurs bornés, matrices de nœuds) plutôt que d'en écrire un troisième."""
    from app.services.print3d import _accessor, _appliquer, _IDENTITE, _mat_locale, _mat_mul
    mats = doc.get("materials") or []
    out = []

    def _mesh(im, monde):
        for prim in doc["meshes"][im].get("primitives", []):
            if prim.get("mode", 4) != 4:
                raise ValueError(f"primitives TRIANGLES seulement (mode {prim.get('mode')}) — hors périmètre")
            att = prim.get("attributes") or {}
            pos = [_appliquer(monde, p) for p in _accessor(doc, binc, att["POSITION"])]
            nrm = [_normale_monde(monde, p) for p in _accessor(doc, binc, att["NORMAL"])] if "NORMAL" in att else []
            uv = _accessor(doc, binc, att["TEXCOORD_0"]) if "TEXCOORD_0" in att else []
            idx = [v[0] for v in _accessor(doc, binc, prim["indices"])] if "indices" in prim else list(range(len(pos)))
            mi = prim.get("material")
            nom = (mats[mi].get("name") if isinstance(mi, int) and mi < len(mats) else None) or "materiau"
            out.append((nom, pos, nrm, uv, idx))

    def _noeud(i, parent):
        node = doc["nodes"][i]
        monde = _mat_mul(parent, _mat_locale(node))
        if "mesh" in node:
            _mesh(node["mesh"], monde)
        for enfant in node.get("children", []):
            _noeud(enfant, monde)

    scenes = doc.get("scenes") or []
    for i in (scenes[doc.get("scene", 0)].get("nodes", []) if scenes else []):
        _noeud(i, _IDENTITE)
    return out


def _obj_et_mtl(doc, binc, base: str, textures: dict) -> tuple[str, str]:
    """Le .obj et le .mtl, en texte. Les indices OBJ sont GLOBAUX et commencent à 1 ; le v de glTF est compté du HAUT
    et celui d'OBJ du BAS, d'où le `1 - v` (sans lui, toutes les textures sortent retournées)."""
    from app.services.material_store import slug
    L = [f"# Deepotus — {base}.obj (converti depuis GLB, coordonnées monde)", f"mtllib {base}.mtl"]
    M = []
    vus = set()
    offset = 1
    for nom, pos, nrm, uv, idx in _primitives(doc, binc):
        for p in pos:
            L.append(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}")
        for t in uv:
            L.append(f"vt {t[0]:.6f} {1.0 - t[1]:.6f}")
        for n in nrm:
            L.append(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")
        s = slug(nom, fallback="materiau")
        L.append(f"usemtl {s}")
        if s not in vus:
            vus.add(s)
            M += [f"newmtl {s}", "Kd 1.000 1.000 1.000", "d 1.0", "illum 2"]
            tex = textures.get(nom) or {}
            if tex.get("basecolor"):
                M.append(f"map_Kd {tex['basecolor']}")
            if tex.get("normal"):
                M.append(f"map_Bump -bm 1.0 {tex['normal']}")     # Blender lit map_Bump comme carte de normales
            M.append("")
        for k in range(0, len(idx) - 2, 3):
            coins = []
            for j in (idx[k], idx[k + 1], idx[k + 2]):
                a = offset + j
                coins.append(f"{a}/{a if uv else ''}/{a if nrm else ''}".rstrip("/") if (uv or nrm) else str(a))
            L.append("f " + " ".join(coins))
        offset += len(pos)
    return "\n".join(L) + "\n", "\n".join(M) + "\n"


def exporter(job, fmt: str, *, version=None, cible_mm=None, nom: str = None) -> tuple[str, bytes]:
    """Un format local depuis le GLB courant (ou la version demandée). Rend (nom de fichier, octets) : `obj` est un
    ZIP (obj + mtl + textures), `stl`, `3mf` et `gltf` sont le fichier nu."""
    from app.services import material_store, mesh_edit, mesh_textures, print3d
    fmt = str(fmt or "").lower().lstrip(".")
    base = nom or Path(str(job)).name
    if fmt in MESHY_EXPORT:
        raise ValueError(f"{fmt} n'est pas écrit localement : {POURQUOI_PAS_LOCAL} Passe par la conversion Meshy — "
                         "1 crédit pour la tâche entière.")
    if fmt not in LOCAL_EXPORT:
        raise ValueError(f"format {fmt} inconnu — local : {', '.join(LOCAL_EXPORT)} ; par Meshy : "
                         f"{', '.join(MESHY_EXPORT)}")
    if cible_mm is not None:
        try:
            cible_mm = float(cible_mm)
        except (TypeError, ValueError):
            raise ValueError("cible_mm : un nombre de millimètres")
        if not 0.1 <= cible_mm <= 10_000:
            raise ValueError("cible_mm : entre 0,1 et 10 000 mm")
    src = mesh_textures.glb_cible(job, version)

    if fmt in ("stl", "3mf"):
        tris = print3d.mettre_a_l_echelle(print3d.lire_glb_triangles(src.read_bytes()), cible_mm)
        return f"{base}.{fmt}", (print3d.ecrire_stl(tris) if fmt == "stl" else print3d.ecrire_3mf(tris, nom=base))

    if fmt == "gltf":
        return f"{base}.gltf", material_store.glb_to_gltf(src.read_bytes())

    # obj : géométrie écrite ici, textures par mesh_textures (un seul encodeur, noms « standard »)
    doc, binc = mesh_edit.lire_glb(src.read_bytes())
    buf = io.BytesIO()
    textures: dict = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        try:
            _, arch = mesh_textures.exporter(job, naming="standard", resolution=2048, version=version, cuire=False)
        except ValueError:
            arch = None                    # maillage nu : OBJ sans map_Kd
        if arch is not None:
            meta = None
            with zipfile.ZipFile(io.BytesIO(arch)) as za:
                meta = json.loads(za.read("textures.json"))
                for m in meta["materiaux"]:
                    for f in m["fichiers"]:
                        if f["kind"] in ("basecolor", "normal"):
                            z.writestr(f["file"], za.read(f"{m['dossier']}/{f['file']}"))
                            textures.setdefault(m["nom"], {})[f["kind"]] = f["file"]
        obj, mtl = _obj_et_mtl(doc, binc, base, textures)
        z.writestr(f"{base}.obj", obj)
        z.writestr(f"{base}.mtl", mtl)
    return f"{base}_obj.zip", buf.getvalue()


# ── import : OBJ / STL / glTF / GLB -> GLB -> un job ─────────────────────────

def importer(data: bytes, nom_fichier: str) -> bytes:
    """Un fichier venu du dehors -> octets GLB relisibles. Refus parlant sur tout ce que ni print3d ni gltfpack ne
    savent lire."""
    from app.services import mesh_optimize, print3d
    ext = Path(str(nom_fichier)).suffix.lower().lstrip(".")
    data = bytes(data or b"")
    if not data:
        raise ValueError(f"fichier {ext or '?'} vide")
    if len(data) > MAX_IMPORT_OCTETS:
        raise ValueError(f"fichier de {len(data) // (1024 * 1024)} Mo : 200 Mo au plus")
    if ext == "glb":
        print3d.lire_glb_triangles(data)              # le refus parlant de print3d si ce n'est pas un GLB lisible
        return data
    if ext == "stl":
        tris = print3d.lire_stl(data)
        if not tris:
            raise ValueError("stl sans triangle")
        return print3d.glb_de_triangles(tris, Path(str(nom_fichier)).stem)
    if ext in ("obj", "gltf"):
        exe = mesh_optimize._gltfpack()
        with tempfile.TemporaryDirectory() as td:
            entree = Path(td) / f"entree.{ext}"
            entree.write_bytes(data)
            sortie = Path(td) / "sortie.glb"
            r = subprocess.run([exe, "-i", str(entree), "-o", str(sortie), "-noq", "-kn", "-km"],
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not sortie.is_file():
                raise ValueError(f"gltfpack n'a pas pu lire ce {ext} ({r.returncode}) : "
                                 f"{(r.stderr or r.stdout or '').strip()[:300]}")
            return sortie.read_bytes()
    raise ValueError(f"import {ext or '(sans extension)'} impossible en local — formats lus : "
                     f"{', '.join(LOCAL_IMPORT)}. {POURQUOI_PAS_LOCAL}")


def importer_job(data: bytes, nom_fichier: str) -> str:
    """Le fichier importé devient un job `import_<nom>_<id>` (model.glb + asset.json + report.json — le patron
    d'`adopter_meshy`) : l'Atelier fal, l'Établi et la Bibliothèque le voient comme un autre. Jamais d'écrasement."""
    from app.services import mesh_report
    from app.services.material_store import slug
    glb = importer(data, nom_fichier)
    stem = slug(Path(str(nom_fichier)).stem, fallback="modele").lower()[:32]
    job = f"import_{stem}_{uuid.uuid4().hex[:8]}"
    d = mesh_report.job_dir(job)
    d.mkdir(parents=True, exist_ok=False)
    (d / "model.glb").write_bytes(glb)
    from app.services import asset3d_service as A3
    # write_manifest date la fiche (created_at) : sans date, l'Atelier rangeait l'import EN DERNIER (vu sur 8799)
    A3.write_manifest(d, {"name": Path(str(nom_fichier)).stem, "engine": "import", "stage": "importe", "version": 1,
                          "source_file": Path(str(nom_fichier)).name})
    mesh_report.write_report(job, "model.glb", version=1, avec_silhouettes=False,
                             extra={"outil": "import", "operation": "import",
                                    "format": Path(str(nom_fichier)).suffix.lower().lstrip(".")})
    return job


# ── FBX / USDZ / BLEND : Meshy convert ───────────────────────────────────────

def devis_meshy(formats) -> dict:
    """1 crédit par TÂCHE, quel que soit le nombre de formats — même chiffre que pricing (kind asset3d_convert)."""
    from app.services import pricing
    voulus = sorted({str(f).lower().lstrip(".") for f in (formats or [])})
    if not voulus:
        raise ValueError("aucun format demandé")
    inconnus = [f for f in voulus if f not in MESHY_EXPORT]
    if inconnus:
        raise ValueError(f"la conversion Meshy sert {', '.join(MESHY_EXPORT)} — {', '.join(inconnus)} : local ou "
                         "inconnu")
    return {"formats": voulus, **pricing.estimate({"kind": "asset3d_convert", "via": "meshy"})}


async def convertir_par_meshy(job, formats, *, version=None, on_step=None) -> dict:
    """Envoie le GLB courant à `openapi/v1/convert` (URL du stockage fal, comme le rig) et rapatrie les binaires sous
    `convert/`. Un format absent de la réponse est DIT (`manquants`), jamais fatal."""
    from app.services import asset3d_service as A3
    from app.services import meshy_service as MS
    from app.services import mesh_report, mesh_textures
    devis = devis_meshy(formats)
    src = mesh_textures.glb_cible(job, version)

    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    await _step("Envoi du maillage", 15)
    url = await A3._upload(src)
    await _step("Conversion Meshy", 35)
    payload = {"model_url": url, "target_formats": devis["formats"]}
    tid = await MS.create_task(CONVERT_BASE, payload)
    await MS.record_created(tid, CONVERT_BASE, payload)
    tache = await A3._attendre_meshy(CONVERT_BASE, tid, on_step, depart=40, fin=85)
    await MS.record_state(tache, CONVERT_BASE)
    urls = tache.get("model_urls") or (tache.get("result") or {}).get("model_urls") or {}
    d = mesh_report.job_dir(job) / "convert"
    d.mkdir(parents=True, exist_ok=True)
    ecrits = []
    for f in devis["formats"]:
        u = urls.get(f)
        if not u:
            continue
        (d / f"model.{f}").write_bytes(await MS._fetch_url(u))
        ecrits.append(f"model.{f}")
    await _step("Complete", 100)
    return {"task_id": tid, "files": sorted(ecrits), "manquants": [f for f in devis["formats"]
                                                                   if f"model.{f}" not in ecrits]}


def fichiers_convertis(job) -> list[str]:
    from app.services import mesh_report
    d = mesh_report.job_dir(job) / "convert"
    return sorted(p.name for p in d.glob("model.*") if p.is_file()) if d.is_dir() else []
