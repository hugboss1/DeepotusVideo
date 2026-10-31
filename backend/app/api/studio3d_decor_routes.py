# -*- coding: utf-8 -*-
"""Routes du Décor › Accessoire — t402 (31/10/2026). Préfixe /api/studio3d/decor. Locales et gratuites.

- GET  /roles : les rôles de décor et le préréglage de triangles conseillé pour chacun (vers l'écran Préparer) ;
- POST /poser : {job, version?, hauteur_m?} → le modèle posé au sol (pivot en bas, centré) et, si demandée, à sa
  hauteur réelle ; écrit une VERSION de plus par `mesh_edit.ecrire_version` (le registre garde `depuis`) ;
- POST /variantes : {job, version?, nombre 2-8, graine, rotation?, echelle_pct?, teinte?, luminosite?} → N JOBS neufs
  `<job>_var<k>` (le manifeste dit la source, la graine et le tirage) ; même graine = mêmes variantes, mêmes jobs ;
- POST /vent : {job, version?, courbe?, seuil?} → le masque de vent `_WIND` (hauteur normalisée), une VERSION de plus ;
- POST /cartes : {job, version?, atlas (PNG 4 × 2 vues, base64), plans 2|3} → l'imposteur `decor/cartes.v<N>.glb` ;
- GET  /cartes/{job}?version= : le télécharger ;
- POST /plateau : {job, version?, scene? | nom_scene?} → la version posée à l'origine (échelle 1) dans une scène du
  Plateau 3D, par les fonctions de route du Plateau (`scene3d_routes.creer / lire / modifier`, qui revérifient tout) ;
  sans `scene`, une scène neuve est créée. La LOD vient des routes existantes `/api/assets/3d/{job}/lod`.
Le service : `app.services.studio3d_decor`.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


async def _source(body: dict) -> tuple[dict, dict, bytes]:
    """(fiche du modèle ouvert, étape de la version, octets du GLB) — refus 400 / 404 dits."""
    from app.services import mesh_sources, studio3d_ouvert as SO
    job = Path(str(body.get("job") or "")).name
    if not job or job != str(body.get("job")):
        raise HTTPException(400, f"job « {body.get('job')} » : nom de dossier invalide")
    try:
        fiche = await asyncio.to_thread(SO.fiche, job, body.get("version"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    etape = next(v for v in fiche["versions"] if v["version"] == fiche["version"])
    data = (mesh_sources._jobs_dir() / job / etape["file"]).read_bytes()
    return fiche, etape, data


@router.get("/roles")
async def decor_roles():
    from app.services import studio3d_decor as SD
    return {"roles": [SD.budget(r) for r in SD.ROLES]}


@router.post("/poser")
async def decor_poser(body: dict):
    from app.services import mesh_edit, studio3d_decor as SD
    body = body or {}
    fiche, etape, data = await _source(body)
    try:
        sortie, mesures = await asyncio.to_thread(SD.poser, data, body.get("hauteur_m"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    fiche_v = await asyncio.to_thread(
        mesh_edit.ecrire_version, fiche["job"], sortie, operation="decor_poser",
        detail={"depuis": {"version": fiche["version"], "fichier": etape["file"]}, **mesures,
                "hauteur_m": body.get("hauteur_m")})
    return {"job": fiche["job"], "version": fiche_v.get("version"), "mesures": mesures}


@router.post("/variantes")
async def decor_variantes(body: dict):
    from app.services import studio3d_decor as SD, studio3d_ouvert as SO
    body = body or {}
    try:
        SD.reglages_variantes(body)                      # refus AVANT toute lecture de disque
    except ValueError as e:
        raise HTTPException(400, str(e))
    fiche, _etape, data = await _source(body)
    try:
        sortie = await asyncio.to_thread(SD.variantes, fiche["job"], fiche["version"], data, fiche["nom"], body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    for v in sortie:
        try:
            f = await asyncio.to_thread(SO.fiche, v["job"])
            v.update({"nom": f["nom"], "url": f["url"], "triangles": f["triangles"], "vignette": f["vignette"]})
        except (FileNotFoundError, ValueError):
            pass
    return {"source": {"job": fiche["job"], "version": fiche["version"]}, "variantes": sortie}


@router.post("/vent")
async def decor_vent(body: dict):
    from app.services import mesh_edit, studio3d_decor as SD
    body = body or {}
    fiche, etape, data = await _source(body)
    try:
        sortie, rapport = await asyncio.to_thread(SD.masque_vent, data, courbe=body.get("courbe", 1.5),
                                                  seuil=body.get("seuil", 0.0))
    except ValueError as e:
        raise HTTPException(400, str(e))
    fiche_v = await asyncio.to_thread(
        mesh_edit.ecrire_version, fiche["job"], sortie, operation="decor_vent",
        detail={"depuis": {"version": fiche["version"], "fichier": etape["file"]}, **rapport})
    return {"job": fiche["job"], "version": fiche_v.get("version"), "rapport": rapport}


def _dossier_cartes(job: str) -> Path:
    from app.services import mesh_sources
    return mesh_sources._jobs_dir() / Path(str(job)).name / "decor"


@router.post("/cartes")
async def decor_cartes(body: dict):
    from app.services import print3d, studio3d_decor as SD
    body = body or {}
    try:
        png = SD.lire_atlas(body.get("atlas"))
        plans = body.get("plans", 2)
        SD.faces_cartes(plans)
    except ValueError as e:
        raise HTTPException(400, str(e))
    fiche, _etape, data = await _source(body)
    try:
        bornes = await asyncio.to_thread(lambda: print3d.bbox(print3d.lire_glb_triangles(data)))
        glb = await asyncio.to_thread(SD.cartes, bornes, png, plans)
    except ValueError as e:
        raise HTTPException(400, str(e))
    d = _dossier_cartes(fiche["job"])
    d.mkdir(parents=True, exist_ok=True)
    nom = f"cartes.v{fiche['version']}.glb"
    (d / nom).write_bytes(glb)
    (d / f"cartes.v{fiche['version']}.png").write_bytes(png)
    return {"job": fiche["job"], "version": fiche["version"], "fichier": nom, "octets": len(glb),
            "plans": plans, "triangles": 4 * plans, "cadre": SD.cadre_cartes(bornes),
            "url": f"/api/studio3d/decor/cartes/{fiche['job']}?version={fiche['version']}"}


@router.get("/cartes/{job}")
async def decor_cartes_fichier(job: str, version: int = 1):
    p = _dossier_cartes(job) / f"cartes.v{int(version)}.glb"
    if not p.is_file():
        raise HTTPException(404, f"cartes absentes pour {Path(job).name} v{int(version)} : construis-les d'abord")
    return FileResponse(p, media_type="model/gltf-binary", filename=f"{Path(job).name}_cartes_v{int(version)}.glb")


@router.post("/plateau")
async def decor_plateau(body: dict):
    from app.services import scene3d_routes as SR, studio3d_decor as SD
    body = body or {}
    fiche, etape, data = await _source(body)
    try:
        mesure = await asyncio.to_thread(SR._offset_et_dims, data)
    except ValueError as e:
        raise HTTPException(415, f"maillage illisible : {e}")
    sid = str(body.get("scene") or "")
    if not sid:
        nom = " ".join(str(body.get("nom_scene") or "").split())[:120] or f"Décor · {fiche['nom']}"
        sid = (await SR.creer({"nom": nom}))["id"]
    scene = await SR.lire(sid)
    instances = scene["instances"]
    inst = SD.instance_plateau(fiche["job"], etape["file"], fiche["nom"], mesure["dims"], {i["id"] for i in instances})
    apres = await SR.modifier(sid, {"instances": instances + [inst]})
    return {"scene": sid, "nom": apres["nom"], "instance": inst, "instances": len(apres["instances"]),
            "url": f"/plateau/?scene={sid}"}
