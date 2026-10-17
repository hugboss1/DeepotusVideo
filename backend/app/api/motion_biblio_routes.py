# -*- coding: utf-8 -*-
"""Bibliothèque motion (t233, 17/10/2026) — /api/motion/biblio et /api/motion/skills/installer.

Boucle locale SEULEMENT, en lecture comme en écriture : la bibliothèque est celle du PC (imports collés par
l'utilisateur, skills installés dans son dossier de données). Le service est app.services.motion_biblio.
"""
from fastapi import APIRouter, HTTPException, Request

from app.services import motion_biblio as MB

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "La bibliothèque motion n'est accessible que depuis ce PC.")


def _http(e: Exception) -> HTTPException:
    statut = 403 if isinstance(e, PermissionError) else 404 if isinstance(e, LookupError) else \
        502 if isinstance(e, RuntimeError) else 400
    return HTTPException(statut, str(e))


async def _corps(request: Request) -> dict:
    try:
        corps = await request.json()
    except ValueError:
        corps = None
    if not isinstance(corps, dict):
        raise HTTPException(400, "Corps JSON attendu.")
    return corps


@router.get("/biblio")
async def lister(request: Request, nature: str | None = None, theme: str | None = None):
    _local(request)
    entrees = MB.lister(nature, theme)
    return {"entrees": [{k: v for k, v in e.items() if k != "original"} for e in entrees],
            "themes": list(MB.THEMES), "presets": list(MB.PRESETS), "easings": list(MB.EASINGS),
            "formats": list(MB.FORMATS), "licences": list(MB.LICENCES)}


@router.get("/biblio/{eid}")
async def lire(eid: str, request: Request):
    _local(request)
    try:
        return MB.lire(eid)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/biblio")
async def importer(request: Request):
    _local(request)
    corps = await _corps(request)
    try:
        return MB.importer_prompt(corps)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.patch("/biblio/{eid}")
async def modifier(eid: str, request: Request):
    _local(request)
    corps = await _corps(request)
    try:
        return MB.modifier(eid, corps)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/biblio/{eid}/revenir")
async def revenir(eid: str, request: Request):
    _local(request)
    try:
        return MB.revenir_original(eid)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.delete("/biblio/{eid}")
async def supprimer(eid: str, request: Request):
    _local(request)
    try:
        return MB.supprimer(eid)
    except (ValueError, LookupError, PermissionError) as e:
        raise _http(e) from None


@router.post("/skills/installer")
async def installer(request: Request):
    _local(request)
    corps = await _corps(request)
    try:
        return await MB.installer_skill(corps.get("source"))
    except (ValueError, LookupError, PermissionError, RuntimeError) as e:
        raise _http(e) from None
