# -*- coding: utf-8 -*-
"""Routes de l'écran EXPORTER du 3D Studio — t400 (31/10/2026). Préfixe /api/studio3d/exporter.

Tout est LOCAL et GRATUIT. Service : `app.services.studio3d_export`. Les écritures sont des POST, donc sous la garde
des écritures de main.py (boucle locale) ; le corps ne porte jamais de chemin : (job, version, variante) suffisent.

  GET  /{job}?version=                 clips, os (rôles pour les hitboxes), Blender, exports déjà écrits
  POST /{job}/glb      {version?, variante: maillage|pose|animation, clip?, clips?, nom?}
  POST /{job}/threejs  {version?, clips?, nom?}            paquet .zip (GLB, manifeste, clips .clip.json, runtime)
  POST /{job}/fbx      {version?, variante?: maillage|animation, nom?}   Blender en arrière-plan ; 503 sans Blender
  GET  /{job}/fichier/{fichier}        un fichier de <job>/exports/
  GET  /impression/{dossier}/{fichier} le STL ou le 3MF d'un export d'impression (POST /api/print3d/from-assets3d)

Refus : 400 (nom, variante, clip, modèle sans animation), 404 (job, version, fichier), 503 (Blender absent).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

_MEDIA = {".glb": "model/gltf-binary", ".zip": "application/zip", ".fbx": "application/octet-stream",
          ".json": "application/json", ".md": "text/markdown", ".stl": "model/stl", ".3mf": "model/3mf"}


def _version(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise HTTPException(400, f"version « {v} » — un entier à partir de 1")
    return v


async def _appel(fn, *a, **k):
    from app.services import studio3d_export as SE
    try:
        return await asyncio.to_thread(fn, *a, **k)
    except SE.RefusExport as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except SE.BlenderIndisponible as e:
        raise HTTPException(503, str(e))
    except ValueError as e:                    # GLB illisible
        raise HTTPException(400, str(e))
    except RuntimeError as e:                  # Blender a échoué
        raise HTTPException(500, str(e))


@router.get("/impression/{dossier}/{fichier}")
async def exporter_impression(dossier: str, fichier: str):
    """Le STL ou le 3MF d'un export d'impression — par NOMS seuls, contenus dans le dossier d'impression."""
    from app.api.routes import _print3d_base
    for x in (dossier, fichier):
        if Path(x).name != x or x in ("", ".", ".."):
            raise HTTPException(400, "impression : nom invalide")
    if Path(fichier).suffix.lower() not in (".stl", ".3mf"):
        raise HTTPException(400, "impression : seuls .stl et .3mf sont servis")
    p = _print3d_base() / dossier / fichier
    if not p.is_file():
        raise HTTPException(404, "impression : fichier introuvable")
    return FileResponse(str(p), media_type=_MEDIA[p.suffix.lower()], filename=fichier)


@router.get("/{job}")
async def exporter_etat(job: str, version: int | None = None):
    from app.services import studio3d_export as SE
    return await _appel(SE.etat, job, _version(version))


@router.post("/{job}/glb")
async def exporter_glb(job: str, body: dict = None):
    from app.services import studio3d_export as SE
    body = body or {}
    return await _appel(SE.exporter_glb, job, _version(body.get("version")), str(body.get("variante") or ""),
                        clip=body.get("clip"), voulus=body.get("clips"), nom=body.get("nom"))


@router.post("/{job}/threejs")
async def exporter_threejs(job: str, body: dict = None):
    from app.services import studio3d_export as SE
    body = body or {}
    return await _appel(SE.exporter_paquet, job, _version(body.get("version")), nom=body.get("nom"),
                        voulus=body.get("clips"))


@router.post("/{job}/fbx")
async def exporter_fbx(job: str, body: dict = None):
    from app.services import studio3d_export as SE
    body = body or {}
    return await _appel(SE.exporter_fbx, job, _version(body.get("version")),
                        variante=str(body.get("variante") or "animation"), nom=body.get("nom"))


@router.get("/{job}/fichier/{fichier}")
async def exporter_fichier(job: str, fichier: str):
    from app.services import studio3d_export as SE
    p = await _appel(SE.chemin_fichier, job, fichier)
    return FileResponse(str(p), media_type=_MEDIA.get(p.suffix.lower(), "application/octet-stream"), filename=p.name)
