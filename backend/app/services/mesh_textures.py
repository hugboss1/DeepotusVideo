# -*- coding: utf-8 -*-
"""Textures d'un maillage exportées aux conventions moteur — T105, plan-moteurs-3d T4 (R10e P3).

La moitié du travail existe déjà et n'est PAS réécrite : `material_store` porte les six conventions (standard,
blender, unity_urp, unity_hdrp, unreal, godot), la MaskMap Unity, l'emplacement de destination de chaque fichier et
sa note vérifiée (R10c), et l'encodeur PNG par genre (`png_bytes`, 16 bits pour height et normal) ; `pbr_service`
dérive les cartes manquantes en PIL pur. Ce module fait le CHAÎNON qui manquait : sortir les images d'un GLB, les
ranger par matériau, les renommer, les redimensionner, cuire ce qui manque, écrire l'archive et son bordereau.

Deux limites dites franchement :
  - un GLB qui EXIGE une extension (KHR_draco_mesh_compression, EXT_meshopt_compression…) lève un refus parlant ;
    une image externe (uri) n'est pas allée chercher : le service promet d'être local ;
  - la cuisson locale part de la BASECOLOR, pas de la géométrie. Une AO cuite ainsi est une carte de MOTIF (cavités
    de la texture), pas une carte d'OBJET (cavités du maillage). C'est écrit dans le bordereau, à côté du fichier.

La source est le GLB COURANT du registre (comme la chaîne de LOD), sauf `version` demandée.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# canal glTF -> genre de carte du Forge (material_store.MAP_KINDS)
_CANAL_PAR_CLE = {
    "baseColorTexture": "basecolor",
    "metallicRoughnessTexture": "orm",   # glTF : G=rugosité, B=métal (R=AO quand occlusion partage l'image)
    "normalTexture": "normal",
    "occlusionTexture": "ao",
    "emissiveTexture": "emissive",
}
# ce qu'on sait cuire depuis la basecolor quand le moteur ne l'a pas livré
CUISSON = ("ao", "roughness", "metallic", "orm", "height")
# les genres qu'on regarde pour dire « il manque quoi »
SUIVIS = ("basecolor", "normal", "orm", "ao", "emissive")


def _job_dir(job):
    from app.services import mesh_report
    return mesh_report.job_dir(job)


def glb_cible(job, version=None) -> Path:
    """Le GLB courant du registre, ou `model.glb` (v1) / `model.v{n}.glb` quand une version est demandée."""
    from app.services import asset3d_service as A3
    d = _job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    if version is None:
        p = d / A3._glb_courant(job)
    else:
        v = int(version)
        p = d / ("model.glb" if v <= 1 else f"model.v{v}.glb")
    if not p.is_file():
        raise FileNotFoundError(f"{p.name} introuvable pour ce job")
    return p


def _images_du_doc(doc: dict, binc: bytes) -> list:
    """Les octets de chaque `images[i]`. None quand l'image est externe (uri) : elle n'est pas dans le fichier."""
    vues = doc.get("bufferViews") or []
    out: list = []
    for img in doc.get("images") or []:
        bv = img.get("bufferView")
        if not isinstance(bv, int) or not (0 <= bv < len(vues)):
            out.append(None)
            continue
        v = vues[bv]
        off = int(v.get("byteOffset") or 0)
        out.append(binc[off:off + int(v.get("byteLength") or 0)])
    return out


def _source_de_texture(doc: dict, ref):
    """Index d'image derrière une référence de texture d'un matériau."""
    if not isinstance(ref, dict):
        return None
    i = ref.get("index")
    tex = doc.get("textures") or []
    if not isinstance(i, int) or not (0 <= i < len(tex)):
        return None
    s = tex[i].get("source")
    return s if isinstance(s, int) else None


def _lire(job, version):
    from app.services import mesh_edit
    p = glb_cible(job, version)
    doc, binc = mesh_edit.lire_glb(p.read_bytes())
    for ext in doc.get("extensionsRequired") or []:
        raise ValueError(f"{p.name} exige l'extension {ext} : les images ne sont pas lisibles telles quelles. Passe "
                         "par une version non compressée — l'Établi en écrit une à chaque opération.")
    return p, doc, binc


def inventaire(job, *, version=None) -> dict:
    """Ce que le maillage porte VRAIMENT : par matériau, quel canal est câblé sur quelle image, sa taille en pixels
    et en octets — et ce qui manque."""
    from PIL import Image
    from app.services.material_store import MAP_KINDS, RESOLUTIONS, naming_catalog
    p, doc, binc = _lire(job, version)
    octets = _images_du_doc(doc, binc)
    materiaux = []
    presents: set = set()
    for i, mat in enumerate(doc.get("materials") or []):
        pbr = mat.get("pbrMetallicRoughness") or {}
        refs = {"baseColorTexture": pbr.get("baseColorTexture"),
                "metallicRoughnessTexture": pbr.get("metallicRoughnessTexture"),
                "normalTexture": mat.get("normalTexture"),
                "occlusionTexture": mat.get("occlusionTexture"),
                "emissiveTexture": mat.get("emissiveTexture")}
        canaux = {}
        for cle, ref in refs.items():
            src = _source_de_texture(doc, ref)
            if src is None or src >= len(octets) or octets[src] is None:
                continue
            genre = _CANAL_PAR_CLE[cle]
            data = octets[src]
            try:
                with Image.open(io.BytesIO(data)) as im:
                    canaux[genre] = {"image": src, "bytes": len(data), "px": [im.width, im.height]}
                presents.add(genre)
            except Exception as e:               # image illisible : le dire
                canaux[genre] = {"image": src, "bytes": len(data), "px": None, "erreur": str(e)}
        materiaux.append({"index": i, "nom": mat.get("name") or f"materiau_{i}", "canaux": canaux})
    return {"job": Path(str(job)).name, "file": p.name, "materiaux": materiaux,
            "manquants": sorted(set(SUIVIS) - presents), "resolutions": list(RESOLUTIONS),
            "conventions": [c["id"] for c in naming_catalog()], "map_kinds": list(MAP_KINDS)}


def exporter(job, *, naming: str = "standard", resolution: int = 2048, version=None,
             cuire: bool = True) -> tuple[str, bytes]:
    """L'archive : un dossier par matériau, des noms à la convention, la résolution demandée (liste blanche du
    Forge), la MaskMap pour Unity, et un bordereau qui dit où chaque fichier VA dans le moteur visé."""
    from PIL import Image
    from app.services import material_store as MS
    from app.services import pbr_service
    p, doc, binc = _lire(job, version)
    octets = _images_du_doc(doc, binc)
    naming = MS.clean_naming(naming)
    res = MS.clean_res(resolution)
    inv = inventaire(job, version=version)
    if not any(m["canaux"] for m in inv["materiaux"]):
        raise ValueError(f"{p.name} ne porte aucune texture : rien à exporter. Texture-le d'abord (retexture Meshy), "
                         "ou habille-le d'une matière du Forge.")
    voulus = MS.default_export_maps(naming)
    buf = io.BytesIO()
    meta_mats = []
    dossiers_pris: set = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for m in inv["materiaux"]:
            if not m["canaux"]:
                continue
            dossier = MS.slug(m["nom"], fallback=f"materiau_{m['index']}")
            if dossier in dossiers_pris:                 # deux matériaux de même nom : jamais un écrasement
                dossier = f"{dossier}_{m['index']}"
            dossiers_pris.add(dossier)
            maps: dict = {}
            for genre, info in m["canaux"].items():
                data = octets[info["image"]]
                if data is None or info.get("px") is None:
                    continue
                im = Image.open(io.BytesIO(data))
                im.load()
                maps[genre] = im
            cuits: list = []
            if cuire and "basecolor" in maps:
                besoin = [k for k in CUISSON if k in set(voulus) | {"orm"} and k not in maps]
                if besoin:
                    for k, img in pbr_service.derive_maps(maps["basecolor"].convert("RGB"), None,
                                                          want=besoin).items():
                        if k in besoin:
                            maps[k] = img
                            cuits.append(k)
            maps = pbr_service.resize_maps(maps, res)
            if naming in MS.UNITY_NAMINGS:
                mm = MS.build_maskmap(maps)
                if mm is not None:
                    maps[MS.MASKMAP] = mm
            noms = MS.naming_map(naming, dossier)
            livres = []
            for genre in list(voulus) + ([MS.MASKMAP] if MS.MASKMAP not in voulus else []):
                if genre not in maps or genre not in noms:
                    continue
                if genre == MS.MASKMAP:      # comme material_store.export_zip : png_bytes ne connaît pas la MaskMap
                    mbuf = io.BytesIO()
                    maps[genre].convert("RGBA").save(mbuf, format="PNG", optimize=False)
                    z.writestr(f"{dossier}/{noms[genre]}", mbuf.getvalue())
                else:
                    z.writestr(f"{dossier}/{noms[genre]}", MS.png_bytes(maps[genre], genre, 8))
                livres.append({"kind": genre, "file": noms[genre], "slot": MS.engine_slot(genre, naming),
                               "role": MS.map_role(genre, naming)})
            meta_mats.append({"nom": m["nom"], "dossier": dossier, "cuits": sorted(cuits), "fichiers": livres})
        meta = {"job": inv["job"], "file": inv["file"], "naming": naming,
                "label": MS.NAMING_LABELS.get(naming, naming), "resolution": res, "cuisson": bool(cuire),
                "materiaux": meta_mats,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        z.writestr("textures.json", json.dumps(meta, indent=1, ensure_ascii=False))
        z.writestr("BORDEREAU.txt", _bordereau(meta))
    return MS.export_filename({"name": Path(str(job)).name}, "zip", naming), buf.getvalue()


def _bordereau(meta: dict) -> str:
    from app.services.material_store import NAMING_NOTES
    L = [f"Textures du maillage — job {meta['job']} ({meta['file']})",
         f"Convention : {meta['label']} · résolution {meta['resolution']} px · {meta['created_at']}",
         "", NAMING_NOTES.get(meta["naming"], ""), ""]
    for m in meta["materiaux"]:
        L.append(f"[{m['nom']}] -> {m['dossier']}/")
        for f in m["fichiers"]:
            L.append(f"  {f['file']:<32} {f['slot']}")
            if f["role"]:
                L.append(f"  {'':<32} ({f['role']})")
        if m["cuits"]:
            L.append(f"  CUITES LOCALEMENT : {', '.join(m['cuits'])}. Dérivées de la basecolor en PIL : ce sont des "
                     "cartes de MOTIF (cavités de la texture), pas des cartes d'OBJET (cavités de la géométrie). "
                     "Utile, mais ce n'est pas un bake de maillage.")
        L.append("")
    return "\n".join(L) + "\n"
