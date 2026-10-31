# -*- coding: utf-8 -*-
"""Routes du 3D Studio à écrans — t388 (31/10/2026). Préfixe /api/studio3d.

Tout est en LECTURE et gratuit : la galerie de l'écran Ouvrir, la fiche du modèle ouvert (bandeau commun à tous les
écrans) et les préréglages de l'écran Préparer. Les écritures passent par les routes déjà gardées : optimisation
(`/api/assets/3d/{job}/optimize`), versions de l'Établi (`/api/etabli/*`). Le service : `app.services.studio3d_ouvert`.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/modeles")
async def studio3d_modeles():
    """La galerie de l'écran Ouvrir, du plus récent au plus ancien (E/S disque : hors de la boucle d'événements)."""
    from app.services import studio3d_ouvert as SO
    return {"modeles": await asyncio.to_thread(SO.modeles)}


@router.get("/ouvert/{job}")
async def studio3d_ouvert(job: str, version: int | None = None):
    """La fiche du modèle ouvert : nom, moteur, versions, comptes, rig. 404 job ou version absents, 400 GLB illisible."""
    from app.services import studio3d_ouvert as SO
    try:
        return await asyncio.to_thread(SO.fiche, job, version)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/preparer/cibles")
async def studio3d_preparer_cibles():
    """Les préréglages de l'écran Préparer, du plus léger au plus lourd, avec leur budget en triangles."""
    from app.services import studio3d_ouvert as SO
    return {"cibles": SO.preparer_cibles()}
