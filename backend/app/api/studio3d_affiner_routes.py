# -*- coding: utf-8 -*-
"""Routes de l'écran AFFINER du 3D Studio — t396 + t397 (31/10/2026). Préfixe /api/studio3d/affiner.

La peinture des poids et les corrections automatiques, LOCALES et gratuites (service `app.services.poids_corrections`,
Python pur) :
  - GET  /poids/{job}?version=N : le résumé de la peau pour l'écran (os : nom, parent, tête, rôle ; points soudés,
    sommets, arêtes, sommets sans poids). Les POIDS eux-mêmes, le front les lit dans le GLB par three.js
    (`skinIndex` / `skinWeight` de chaque SkinnedMesh) : ils y sont déjà, par sommet, et les renvoyer en JSON
    doublerait le transfert ;
  - POST /enregistrer/{job} {version, modifs: [{mesh, primitive, sommets, joints, poids}]} : les sommets repeints
    (indices de la peau, comme three.js) → une VERSION de plus (« poids_peints ») ;
  - POST /corriger/{job} {version, operation, os?, parametres?} : orphelins, confinement, epaules, coutures, guerison
    ou tout (le correctif en un clic) → une VERSION de plus (« poids_<operation> ») ; `parametres.apercu = true` rend
    le compte rendu sans rien écrire (le « Scan » des orphelins).
Aucune dépense, aucun fournisseur. Refus en français (400 / 404), traduits à la sortie (L10).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.studio3d_rig_routes import _version

router = APIRouter()


def _resume(data: bytes) -> dict:
    from app.services import poids_corrections as PC
    return PC.Peau(data).resume()


@router.get("/poids/{job}")
async def affiner_poids(job: str, version: int | None = None):
    """Le résumé de la peau de la version ouverte (la dernière par défaut). 400 : pas de peau, GLB hors périmètre."""
    j, v, nom, data = await asyncio.to_thread(_version, job, version)
    try:
        r = await asyncio.to_thread(_resume, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"job": j, "version": v, "fichier": nom, **r}


def _reponse(j: str, v: int, fiche: dict, rapport: dict) -> dict:
    return {"ok": True, "job": j, "depuis": v, "version": fiche.get("version"), "fichier": fiche.get("file"),
            "rapport": rapport, "url": f"/api/assets/3d/{Path(j).name}/version/{fiche.get('version')}"}


@router.post("/enregistrer/{job}")
async def affiner_enregistrer(job: str, body: dict | None = None):
    """Les poids peints → `model.v{n+1}.glb`. 400 : modifs invalides, pas de peau ; 404 : job ou version absents."""
    from app.services import poids_corrections as PC
    body = body if isinstance(body, dict) else {}
    if not isinstance(body.get("modifs"), list) or not body["modifs"]:
        raise HTTPException(400, "modifs : une liste non vide de {mesh, primitive, sommets, joints, poids} est attendue")
    j, v, nom, data = await asyncio.to_thread(_version, job, body.get("version"))
    try:
        sortie, rapport = await asyncio.to_thread(PC.ecrire_sommets, data, body["modifs"])
        fiche = await asyncio.to_thread(PC.ecrire, j, v, sortie, "poids_peints", rapport, nom)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _reponse(j, v, fiche, rapport)


@router.post("/corriger/{job}")
async def affiner_corriger(job: str, body: dict | None = None):
    """Une correction automatique → `model.v{n+1}.glb` (ou le seul compte rendu avec `parametres.apercu`)."""
    from app.services import poids_corrections as PC
    body = body if isinstance(body, dict) else {}
    op = body.get("operation")
    if op not in PC.OPERATIONS:
        raise HTTPException(400, f"opération inconnue « {str(op)[:40]} » : orphelins, confinement, epaules, coutures, "
                                 "guerison ou tout")
    os_ = body.get("os")
    if os_ is not None and not isinstance(os_, str):
        raise HTTPException(400, "os : le nom d'un os est attendu")
    params = body.get("parametres")
    if params is not None and not isinstance(params, dict):
        raise HTTPException(400, "parametres : un objet est attendu")
    j, v, nom, data = await asyncio.to_thread(_version, job, body.get("version"))
    try:
        sortie, rapport = await asyncio.to_thread(PC.corriger, data, op, os=os_, parametres=params)
        if sortie is None:
            return {"ok": True, "job": j, "depuis": v, "version": None, "apercu": True, "rapport": rapport}
        fiche = await asyncio.to_thread(PC.ecrire, j, v, sortie, "poids_" + op, rapport, nom)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _reponse(j, v, fiche, rapport)
