# -*- coding: utf-8 -*-
"""Routes du Décor › Accessoire — t402 (31/10/2026). Préfixe /api/studio3d/decor. Locales et gratuites.

- GET  /roles : les rôles de décor et le préréglage de triangles conseillé pour chacun (vers l'écran Préparer) ;
- POST /poser : {job, version?, hauteur_m?} → le modèle posé au sol (pivot en bas, centré) et, si demandée, à sa
  hauteur réelle ; écrit une VERSION de plus par `mesh_edit.ecrire_version` (le registre garde `depuis`). Le service :
  `app.services.studio3d_decor`.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/roles")
async def decor_roles():
    from app.services import studio3d_decor as SD
    return {"roles": [SD.budget(r) for r in SD.ROLES]}


@router.post("/poser")
async def decor_poser(body: dict):
    from app.services import mesh_edit, mesh_sources, studio3d_decor as SD, studio3d_ouvert as SO
    body = body or {}
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
    try:
        sortie, mesures = await asyncio.to_thread(SD.poser, data, body.get("hauteur_m"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    fiche_v = await asyncio.to_thread(
        mesh_edit.ecrire_version, job, sortie, operation="decor_poser",
        detail={"depuis": {"version": fiche["version"], "fichier": etape["file"]}, **mesures,
                "hauteur_m": body.get("hauteur_m")})
    return {"job": job, "version": fiche_v.get("version"), "mesures": mesures}
